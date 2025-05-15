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
        add_logo_to_image_array, 
        crop_canvas_to_content_with_margin
    )
    from image_utils import paste_image_onto_canvas 
    from metadata_utils import set_basic_exif_metadata, apply_xmp_metadata_via_exiftool
except ImportError as e:
    print(f"CRITICAL ERROR in stitch_images.py: Could not import local utils: {e}")
    raise

STITCH_VIEW_PATTERNS_CONFIG = {
    "obverse":"_01", # Pattern part for NAME<pattern_part>_object.tif
    "reverse":"_02",
    "bottom":"_04", # User updated this from _04
    "top":"_03",    # User updated this from _03
    "right":"_06",  # User updated this from _06
    "left":"_05",   # User updated this from _05
    "ruler": ""     # Added "ruler". The pattern part is not used by load_images_for_stitching_process's ruler logic
                    # as it specifically looks for SCALED_RULER_FILE_SUFFIX (_07.tif)
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

def process_tablet_subfolder(
    subfolder_path, output_base_name, pixels_per_cm, photographer_name,
    ruler_image_for_scale_path, # Original path of image used for scale (e.g. _02.tif) - for context
    add_logo=False, logo_path=None, output_dpi=STITCH_OUTPUT_DPI,
    stitched_bg_color=STITCH_BACKGROUND_COLOR, final_margin=STITCH_FINAL_MARGIN_PX,
    tiff_compression=STITCH_TIFF_COMPRESSION, 
    view_gap_px_override=None, 
    object_extraction_background_mode="auto" 
):
    print(f"  Stitching for tablet: {output_base_name}")

    current_view_gap = STITCH_VIEW_GAP_PX if view_gap_px_override is None else view_gap_px_override
    print(f"    Using view gap: {current_view_gap}px")

    # This will now iterate through all keys in STITCH_VIEW_PATTERNS_CONFIG, including "ruler"
    loaded_images = load_images_for_stitching_process(subfolder_path, output_base_name, STITCH_VIEW_PATTERNS_CONFIG)
    
    if loaded_images.get("obverse") is None: 
        raise ValueError("Stitching requires obverse_object.tif (or equivalent for 'obverse' key)")
    if loaded_images.get("ruler") is None:
        print(f"      Critical Warning: Scaled ruler image ('{output_base_name}_07.tif') was not loaded. Final image will not have a ruler.")
        # Decide if this should be fatal or allow proceeding. For now, it will proceed.

    resized_images = resize_tablet_views_relative_to_obverse(loaded_images) # Resizes views, ruler should be fine
    
    canvas_w, canvas_h, layout_coords, images_to_paste_dict = calculate_stitching_canvas_layout(
        resized_images, current_view_gap, STITCH_RULER_PADDING_PX
    )
    
    stitched_canvas = np.full((canvas_h, canvas_w, 3), stitched_bg_color, dtype=np.uint8)
    for view_key, coords_tuple in layout_coords.items():
        img_to_paste = images_to_paste_dict.get(view_key)
        if img_to_paste is not None: 
            paste_image_onto_canvas(stitched_canvas, img_to_paste, coords_tuple[0], coords_tuple[1])

    content_after_views = crop_canvas_to_content_with_margin(stitched_canvas, stitched_bg_color, 0)
    img_before_margin = content_after_views
    if add_logo:
        img_before_margin = add_logo_to_image_array(
            content_after_views, logo_path, stitched_bg_color,
            STITCH_LOGO_MAX_WIDTH_FRACTION, STITCH_LOGO_PADDING_ABOVE, STITCH_LOGO_PADDING_BELOW
        )
    
    final_output_image = crop_canvas_to_content_with_margin(img_before_margin, stitched_bg_color, final_margin)
    
    output_filename_tif = f"{output_base_name}_stitched.tif"
    output_filepath_tif = os.path.join(subfolder_path, output_filename_tif)
    print(f"    Saving final stitched TIFF: {output_filepath_tif}")
    try:
        comp_arg_imageio = None
        if tiff_compression.lower() == 'lzw': comp_arg_imageio = 'tiff_lzw'
        elif tiff_compression.lower() == 'zip' or tiff_compression.lower() == 'deflate': comp_arg_imageio = 'tiff_deflate'
        
        imageio.imwrite(
            output_filepath_tif, 
            cv2.cvtColor(final_output_image, cv2.COLOR_BGR2RGB), 
            format='TIFF',
            compression=comp_arg_imageio
        )
        print(f"      Successfully saved TIFF (image data): {output_filename_tif}")
    except Exception as e: 
        print(f"ERROR saving stitched TIFF with imageio: {e}")
        try:
            cv2.imwrite(output_filepath_tif, final_output_image)
            print(f"      Saved TIFF via cv2 (fallback). Metadata/DPI might be limited.")
        except Exception as cv2_e:
            print(f"      ERROR saving final TIFF with cv2 fallback: {cv2_e}")
            raise

    output_filename_jpg = f"{output_base_name}_stitched.jpg"
    output_filepath_jpg = os.path.join(subfolder_path, output_filename_jpg)
    print(f"    Saving final stitched JPG: {output_filepath_jpg}")
    try:
        cv2.imwrite(output_filepath_jpg, final_output_image, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_SAVE_QUALITY])
        print(f"      Successfully saved JPG: {output_filename_jpg} with quality {JPEG_SAVE_QUALITY}")
    except Exception as e:
        print(f"      ERROR saving final JPG: {e}")

    print(f"    Setting metadata for TIFF: {output_filename_tif}...")
    year = str(datetime.date.today().year); copyright_notice_text = f"© {year} {STITCH_INSTITUTION}"
    
    set_basic_exif_metadata(output_filepath_tif, output_base_name, photographer_name, STITCH_INSTITUTION, copyright_notice_text, output_dpi)
    
    apply_xmp_metadata_via_exiftool(
        tiff_image_path=output_filepath_tif, 
        image_title=output_base_name, 
        photographer_name=photographer_name,
        institution_name=STITCH_INSTITUTION, 
        credit_line_text=STITCH_CREDIT_LINE,
        copyright_text=copyright_notice_text, 
        usage_terms_text=STITCH_XMP_USAGE_TERMS
    )
    
    print(f"  Finished processing and stitching for tablet: {output_base_name}")
    return output_filepath_tif, output_filepath_jpg
