import cv2 
import numpy as np
import os
import imageio
import datetime
import piexif 
import subprocess
import shutil

try:
    from stitch_file_utils import load_images_for_stitching_process
    from stitch_processing_utils import (
        resize_tablet_views_relative_to_obverse, 
        calculate_stitching_canvas_layout,
        get_layout_bounding_box, 
        add_logo_to_image_array, 
        crop_canvas_to_content_with_margin 
    )
    from image_utils import paste_image_onto_canvas 
    from metadata_utils import set_basic_exif_metadata, apply_xmp_metadata_via_exiftool
except ImportError as e:
    print(f"CRITICAL ERROR in stitch_images.py: Could not import local utils: {e}")
    raise

STITCH_VIEW_PATTERNS_CONFIG = { 
    "obverse":"_01","reverse":"_02","bottom":"_04", 
    "top":"_03", "right":"_06", "left":"_05", "ruler": "" 
}
STITCH_INSTITUTION = "LMU Munich"
STITCH_CREDIT_LINE = "The image was produced with funding from the European Research Council (ERC) under the European Union’s Horizon Europe research and innovation programme (Grant agreement No. 101171038). Grant Acronym RECC (DOI: 10.3030/101171038). Published under a CC BY NC 4.0 license."
STITCH_XMP_USAGE_TERMS = f"Contact {STITCH_INSTITUTION} for usage rights."
STITCH_OUTPUT_DPI = 600
STITCH_BACKGROUND_COLOR = (0,0,0)
STITCH_TIFF_COMPRESSION = "lzw" 
STITCH_FINAL_MARGIN_PX = 100 
STITCH_VIEW_GAP_PX = 100 
STITCH_RULER_PADDING_PX = 100 
STITCH_LOGO_MAX_WIDTH_FRACTION = 0.70
STITCH_LOGO_PADDING_ABOVE = 30
STITCH_LOGO_PADDING_BELOW = 30
JPEG_SAVE_QUALITY = 85 
FINAL_TIFF_SUBFOLDER_NAME = "_Final_TIFF"
FINAL_JPG_SUBFOLDER_NAME = "_Final_JPG"

def process_tablet_subfolder(
    subfolder_path, 
    main_input_folder_path, 
    output_base_name, 
    pixels_per_cm, 
    photographer_name,
    ruler_image_for_scale_path, 
    add_logo=False, 
    logo_path=None, 
    output_dpi=STITCH_OUTPUT_DPI,
    stitched_bg_color=STITCH_BACKGROUND_COLOR, 
    final_margin=STITCH_FINAL_MARGIN_PX,
    tiff_compression="none", # Defaulting to none, as imageio handles it based on backend
    view_gap_px_override=None, 
    object_extraction_background_mode="auto" 
):
    print(f"  Stitching for tablet: {output_base_name}")
    current_view_gap = STITCH_VIEW_GAP_PX if view_gap_px_override is None else view_gap_px_override
    current_ruler_padding = STITCH_RULER_PADDING_PX 

    loaded_images = load_images_for_stitching_process(subfolder_path, output_base_name, STITCH_VIEW_PATTERNS_CONFIG)
    if loaded_images.get("obverse") is None: raise ValueError("Stitching requires obverse_object.tif")

    resized_images = resize_tablet_views_relative_to_obverse(loaded_images)
    canvas_w, canvas_h, layout_coords, images_to_paste_dict = calculate_stitching_canvas_layout(
        resized_images, current_view_gap, current_ruler_padding
    )
    
    stitched_canvas_initial = np.full((canvas_h, canvas_w, 3), stitched_bg_color, dtype=np.uint8)
    for view_key, coords_tuple in layout_coords.items():
        img_to_paste = images_to_paste_dict.get(view_key) 
        if img_to_paste is not None: 
            paste_image_onto_canvas(stitched_canvas_initial, img_to_paste, coords_tuple[0], coords_tuple[1])

    layout_bbox = get_layout_bounding_box(images_to_paste_dict, layout_coords) 
    if layout_bbox:
        min_x, min_y, max_x, max_y = layout_bbox
        min_x = max(0, min_x); min_y = max(0, min_y)
        max_x = min(canvas_w, max_x); max_y = min(canvas_h, max_y)
        if max_x > min_x and max_y > min_y:
            content_after_layout_crop = stitched_canvas_initial[min_y:max_y, min_x:max_x]
        else: content_after_layout_crop = stitched_canvas_initial
    else: content_after_layout_crop = stitched_canvas_initial
    
    img_before_final_margin = content_after_layout_crop
    if add_logo:
        img_before_final_margin = add_logo_to_image_array(
            content_after_layout_crop, logo_path, stitched_bg_color,
            STITCH_LOGO_MAX_WIDTH_FRACTION, STITCH_LOGO_PADDING_ABOVE, STITCH_LOGO_PADDING_BELOW
        )
    
    final_output_image_for_saving = crop_canvas_to_content_with_margin(img_before_final_margin, stitched_bg_color, final_margin)
    
    # --- Define output paths and names clearly before try blocks ---
    current_output_base_name = output_base_name # Use a local variable for clarity
    
    final_tiff_output_dir = os.path.join(main_input_folder_path, FINAL_TIFF_SUBFOLDER_NAME)
    final_jpg_output_dir = os.path.join(main_input_folder_path, FINAL_JPG_SUBFOLDER_NAME)
    os.makedirs(final_tiff_output_dir, exist_ok=True)
    os.makedirs(final_jpg_output_dir, exist_ok=True)

    local_output_filename_tif = f"{current_output_base_name}.tif"
    local_output_filepath_tif = os.path.join(final_tiff_output_dir, local_output_filename_tif)
    
    local_output_filename_jpg = f"{current_output_base_name}.jpg"
    local_output_filepath_jpg = os.path.join(final_jpg_output_dir, local_output_filename_jpg)

    # --- Save TIFF ---
    print(f"    Attempting to save TIFF to: {local_output_filepath_tif}")
    if not isinstance(final_output_image_for_saving, np.ndarray) or final_output_image_for_saving.size == 0:
        print(f"      ERROR: final_output_image_for_saving is invalid before TIFF save. Shape: {getattr(final_output_image_for_saving, 'shape', 'N/A')}")
        raise ValueError("final_output_image_for_saving is invalid before TIFF save.")
    
    tiff_save_success = False
    try:
        image_to_save_rgb_for_tiff = cv2.cvtColor(final_output_image_for_saving, cv2.COLOR_BGR2RGB)
        if image_to_save_rgb_for_tiff is None or image_to_save_rgb_for_tiff.size == 0:
            raise ValueError("cv2.cvtColor resulted in an invalid image for TIFF saving.")

        imageio.imwrite(local_output_filepath_tif, image_to_save_rgb_for_tiff, format='TIFF')
        print(f"      Successfully saved TIFF (image data): {local_output_filename_tif}")
        tiff_save_success = True
    except Exception as e_imageio: 
        print(f"ERROR saving stitched TIFF with imageio: {e_imageio}") # Print the actual imageio error
        try: 
            print(f"      Attempting fallback cv2.imwrite for TIFF: {local_output_filepath_tif}")
            if not cv2.imwrite(local_output_filepath_tif, final_output_image_for_saving):
                 raise IOError("cv2.imwrite for TIFF fallback returned False.")
            print(f"      Saved TIFF via cv2 (fallback).")
            tiff_save_success = True # Fallback succeeded
        except Exception as e_cv2_tiff:
            print(f"      ERROR saving final TIFF with cv2 fallback: {e_cv2_tiff}")
            # If both fail, the original e_imageio will be raised by the calling try-except in gui_workflow_runner

    # --- Save JPEG ---
    print(f"    Attempting to save JPG to: {local_output_filepath_jpg}")
    if not isinstance(final_output_image_for_saving, np.ndarray) or final_output_image_for_saving.size == 0:
        print(f"      ERROR: final_output_image_for_saving is invalid before JPG save. Shape: {getattr(final_output_image_for_saving, 'shape', 'N/A')}")
    else:
        try:
            if not cv2.imwrite(local_output_filepath_jpg, final_output_image_for_saving, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_SAVE_QUALITY]):
                raise IOError("cv2.imwrite for JPG returned False.")
            print(f"      Successfully saved JPG: {local_output_filename_jpg} with quality {JPEG_SAVE_QUALITY}")
        except Exception as e_jpg:
            print(f"      ERROR saving final JPG: {e_jpg}")

    # --- Set Metadata (only if TIFF save was successful) ---
    if tiff_save_success:
        print(f"    Setting metadata for TIFF: {local_output_filename_tif}...")
        year = str(datetime.date.today().year); copyright = f"© {year} {STITCH_INSTITUTION}"
        set_basic_exif_metadata(local_output_filepath_tif, current_output_base_name, photographer_name, STITCH_INSTITUTION, copyright, output_dpi)
        apply_xmp_metadata_via_exiftool(local_output_filepath_tif, image_title=current_output_base_name, photographer_name=photographer_name,
                                       institution_name=STITCH_INSTITUTION, credit_line_text=STITCH_CREDIT_LINE,
                                       copyright_text=copyright, usage_terms_text=STITCH_XMP_USAGE_TERMS)
    else:
        print(f"    Skipping metadata for TIFF as save failed: {local_output_filename_tif}")
    
    print(f"  Finished processing and stitching for tablet: {current_output_base_name}")
    return local_output_filepath_tif if tiff_save_success else None, local_output_filepath_jpg if os.path.exists(local_output_filepath_jpg) else None
