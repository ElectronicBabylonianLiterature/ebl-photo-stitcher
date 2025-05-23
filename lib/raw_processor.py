import rawpy
import imageio
import os
import numpy as np

try:
    import lensfunpy
    LENSFUN_AVAILABLE = True
except ImportError:
    LENSFUN_AVAILABLE = False
    print("Warning: lensfunpy library not found. Lens corrections will be skipped.")
    print("         To enable lens corrections, please install it: pip install lensfunpy")
    print("         You may also need to install the Lensfun database on your system.")


def apply_lens_correction_if_available(raw_image_obj, image_rgb_array):
    if not LENSFUN_AVAILABLE:
        return image_rgb_array
    try:
        database = lensfunpy.Database()
        
        # Get camera make and model directly from rawpy object attributes
        cam_manufacturer = getattr(raw_image_obj, 'camera_manufacturer', getattr(raw_image_obj, 'make', ''))
        cam_model_name = getattr(raw_image_obj, 'camera_model', getattr(raw_image_obj, 'model', ''))
        
        # Get lens information
        lens_model_name = ''  # Initialize

        # Attempt 1: from specific lens_make and lens_model attributes on raw_image_obj
        _lens_make_attr = getattr(raw_image_obj, 'lens_make', '')
        _lens_model_attr = getattr(raw_image_obj, 'lens_model', '')
        if _lens_make_attr or _lens_model_attr:
            lens_model_name = f"{_lens_make_attr} {_lens_model_attr}".strip()

        # Attempt 2: from raw_image_obj.lens object (if Attempt 1 failed or produced an empty string)
        # This part of the logic was mostly fine but is now a fallback.
        if not lens_model_name and hasattr(raw_image_obj, 'lens') and raw_image_obj.lens:
            lens_obj = raw_image_obj.lens
            if hasattr(lens_obj, 'name') and lens_obj.name:
                lens_model_name = lens_obj.name
            elif hasattr(lens_obj, 'model') and lens_obj.model:  # Fallback within lens object
                lens_model_name = lens_obj.model

        if not cam_manufacturer or not cam_model_name:
            print("      Lensfun: Camera maker or model not found in RAW metadata. Skipping correction.")
            return image_rgb_array

        camera_matches = database.find_cameras(cam_manufacturer, cam_model_name)
        if not camera_matches:
            print(f"      Lensfun: Camera '{cam_manufacturer} {cam_model_name}' not found in DB. Skipping.")
            return image_rgb_array
        camera = camera_matches[0] 

        found_lens_profile = None
        if lens_model_name and lens_model_name.strip() not in ["Unknown", "", "None"]:
            lens_matches = database.find_lenses(camera, lens_model_name)
            if lens_matches: 
                found_lens_profile = lens_matches[0]
            else: # Try a more generic search if exact match fails
                print(f"      Lensfun: Exact lens '{lens_model_name}' not found, trying broader search...")
                all_lenses_for_cam = database.find_lenses(camera)
                for l in all_lenses_for_cam:
                    if lens_model_name.lower() in l.model.lower() or l.model.lower() in lens_model_name.lower():
                        found_lens_profile = l
                        print(f"      Lensfun: Found potential lens match: {l.model}")
                        break
        
        if not found_lens_profile:
            print(f"      Lensfun: Lens '{lens_model_name}' for '{camera.model}' not found in Lensfun DB. Skipping.")
            return image_rgb_array

        print(f"      Lensfun: Applying corrections for Camera: {camera.model}, Lens: {found_lens_profile.model}")
        height, width = image_rgb_array.shape[:2]
        crop_factor = camera.crop_factor if camera.crop_factor > 0 else 1.0 
        
        focal_length = raw_image_obj.focal_length if hasattr(raw_image_obj, 'focal_length') and raw_image_obj.focal_length else found_lens_profile.min_focal
        aperture = raw_image_obj.aperture if hasattr(raw_image_obj, 'aperture') and raw_image_obj.aperture else found_lens_profile.min_aperture
        # Distance is often not in EXIF for general photos, using a large default.
        # Some cameras might store it, rawpy might expose it via exif_info if parsed.
        distance = 1000 

        modifier = lensfunpy.Modifier(found_lens_profile, crop_factor, width, height)
        
        # Corrected initialize parameters
        # The pixel_format and mode might vary slightly based on lensfunpy version.
        # Common is FLOAT, and mode can often be inferred or set to ALL.
        modifier.initialize(focal_length, aperture, distance, pixel_format=lensfunpy.PixelFormat.FLOAT, mode=lensfunpy.CorrectionMode.ALL)

        image_float32 = image_rgb_array.astype(np.float32) / (2**raw_image_obj.output_bps - 1) # Normalize based on output_bps
        
        # Apply corrections - check your lensfunpy version for exact method names if these fail
        # Some versions use apply_แก้ไข()
        # For clarity, applying geometry first, then color.
        corrected_image_float32 = modifier.apply_geometry_distortion(image_float32)
        corrected_image_float32 = modifier.apply_color_modification(corrected_image_float32) # Handles TCA and vignetting
        
        # Convert back to original bit depth using a standard type
        corrected_rgb_array = (np.clip(corrected_image_float32, 0.0, 1.0) * (2**raw_image_obj.output_bps -1)).astype(np.uint16)
        print("      Lensfun: Corrections applied.")
        return corrected_rgb_array
    except Exception as e:
        print(f"      Lensfun: Error during lens correction: {e}. Returning uncorrected image.")
        return image_rgb_array


def convert_raw_image_to_tiff(raw_image_input_path, tiff_output_path):
    print(f"  Converting RAW: {os.path.basename(raw_image_input_path)} to TIFF: {os.path.basename(tiff_output_path)}")
    try:
        with rawpy.imread(raw_image_input_path) as raw_data:
            # First try with auto brightness and scaling
            try:
                params = rawpy.Params(
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AAHD,
                    use_camera_wb=True,
                    no_auto_bright=False,
                    no_auto_scale=False,
                    output_bps=16,
                    bright=1.0
                )
                
                # Try to set sharpen threshold if available
                if hasattr(params, 'sharpen_threshold'):
                    params.sharpen_threshold = 3000
                
                rgb_pixels = raw_data.postprocess(params=params)
                
            except Exception as proc_error:
                print(f"    Warning: First processing attempt failed ({proc_error}), trying with no auto scaling")
                # Fallback to more conservative processing
                params = rawpy.Params(
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AAHD,
                    use_camera_wb=True,
                    no_auto_bright=True,
                    no_auto_scale=True,
                    output_bps=16,
                    bright=1.0
                )
                rgb_pixels = raw_data.postprocess(params=params)
                # Manually scale if needed
                rgb_pixels = (rgb_pixels / rgb_pixels.max() * (2**16-1)).astype(np.uint16)
            
            processed_rgb_pixels = apply_lens_correction_if_available(raw_data, rgb_pixels)
            
            imageio.imwrite(tiff_output_path, processed_rgb_pixels, format='TIFF')
        print(f"    Successfully converted RAW to TIFF: {tiff_output_path}")
        return tiff_output_path
    except rawpy.LibRawIOError as e: 
        print(f"  ERROR during RAW conversion (I/O or format issue) for {raw_image_input_path}: {e}")
        raise 
    except Exception as e:
        print(f"  ERROR during RAW to TIFF conversion for {raw_image_input_path}: {e}")
        raise
