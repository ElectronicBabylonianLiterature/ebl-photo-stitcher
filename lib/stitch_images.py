# Main stitching module - coordinates the tablet image stitching process
import cv2 
import numpy as np
import os

try:
    from stitch_file_utils import load_images_for_stitching_process
    from stitch_layout_manager import (
        resize_tablet_views_for_layout,
        calculate_stitching_layout,
        get_layout_bounding_box
    )
    from stitch_enhancement_utils import (
        add_logo_to_image_array,
        crop_canvas_to_content_with_margin
    )
    from stitch_output import save_stitched_output
    from stitch_config import (
        STITCH_VIEW_PATTERNS_CONFIG,
        STITCH_BACKGROUND_COLOR,
        STITCH_FINAL_MARGIN_PX,
        STITCH_VIEW_GAP_PX,
        STITCH_RULER_PADDING_PX,
        STITCH_OUTPUT_DPI,
        STITCH_LOGO_MAX_WIDTH_FRACTION,
        STITCH_LOGO_PADDING_ABOVE,
        STITCH_LOGO_PADDING_BELOW
    )
    from image_utils import paste_image_onto_canvas
except ImportError as e:
    print(f"CRITICAL ERROR in stitch_images.py: Could not import local utils: {e}")
    raise

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
    tiff_compression="none",
    view_gap_px_override=None, 
    object_extraction_background_mode="auto" 
):
    """
    Main function to stitch together tablet images from a subfolder.
    
    Processes images from a tablet subfolder, applies resizing,
    arranges them in a layout, and creates a composite image.
    """
    print(f"  Stitching for tablet: {output_base_name}")
    
    # Setup parameters
    current_view_gap = STITCH_VIEW_GAP_PX if view_gap_px_override is None else view_gap_px_override
    current_ruler_padding = STITCH_RULER_PADDING_PX 

    # Step 1: Load all required images
    loaded_images = load_images_for_stitching_process(subfolder_path, output_base_name, STITCH_VIEW_PATTERNS_CONFIG)
    if loaded_images.get("obverse") is None: 
        raise ValueError("Stitching requires obverse_object.tif")

    # Step 2: Process images for consistency
    resized_images = resize_tablet_views_for_layout(loaded_images)
    
    # Step 3: Calculate layout for placing images
    canvas_w, canvas_h, layout_coords, images_to_paste_dict = calculate_stitching_layout(
        resized_images, current_view_gap, current_ruler_padding
    )
    
    # Step 4: Create initial canvas and place images
    final_image = create_stitched_canvas(
        canvas_w, canvas_h, 
        images_to_paste_dict, 
        layout_coords, 
        stitched_bg_color
    )
    
    # Step 5: Apply enhancements (logo, margins)
    if add_logo and logo_path:
        final_image = add_logo_to_image_array(
            final_image, logo_path, stitched_bg_color,
            STITCH_LOGO_MAX_WIDTH_FRACTION, STITCH_LOGO_PADDING_ABOVE, STITCH_LOGO_PADDING_BELOW
        )
    
    final_image = crop_canvas_to_content_with_margin(final_image, stitched_bg_color, final_margin)
    
    # Step 6: Save output images and apply metadata
    tiff_path, jpg_path = save_stitched_output(
        final_image, 
        main_input_folder_path, 
        output_base_name,
        photographer_name,
        output_dpi
    )
    
    print(f"  Finished processing and stitching for tablet: {output_base_name}")
    return tiff_path, jpg_path

def create_stitched_canvas(canvas_width, canvas_height, images_dict, layout_coords, bg_color):
    """
    Create a blank canvas and place all images according to the calculated layout.
    Then crop to content bounds.
    """
    # Create initial canvas with background color
    canvas = np.full((canvas_height, canvas_width, 3), bg_color, dtype=np.uint8)
    
    # Place each image onto the canvas at its specified position
    for view_key, coords_tuple in layout_coords.items():
        img_to_paste = images_dict.get(view_key) 
        if img_to_paste is not None: 
            paste_image_onto_canvas(canvas, img_to_paste, coords_tuple[0], coords_tuple[1])
    
    # Crop canvas to actual content
    layout_bbox = get_layout_bounding_box(images_dict, layout_coords) 
    if layout_bbox:
        min_x, min_y, max_x, max_y = layout_bbox
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(canvas_width, max_x)
        max_y = min(canvas_height, max_y)
        
        if max_x > min_x and max_y > min_y:
            return canvas[min_y:max_y, min_x:max_x]
    
    return canvas
