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

DEFAULT_BLEND_OVERLAP_PX = 50 # Default overlap for gradient blending

def _blend_images_horizontally(base_image_segment, new_image_segment, overlap_px):
    """Blends the new_image_segment onto the right side of base_image_segment with a horizontal gradient."""
    if base_image_segment is None or new_image_segment is None:
        return new_image_segment if base_image_segment is None else base_image_segment
    if overlap_px <= 0:
        return np.concatenate((base_image_segment, new_image_segment), axis=1)

    h = min(base_image_segment.shape[0], new_image_segment.shape[0])
    base_w = base_image_segment.shape[1]
    new_w = new_image_segment.shape[1]

    # Ensure images are at least overlap_px wide for meaningful blend
    if base_w < overlap_px or new_w < overlap_px:
        # Not enough width to overlap, just concatenate
        return np.concatenate((base_image_segment[:, :base_w-overlap_px if base_w > overlap_px else 0], new_image_segment), axis=1)


    # Crop to common height
    base_segment_cropped = base_image_segment[:h, :]
    new_segment_cropped = new_image_segment[:h, :]
    
    # Define overlapping regions
    base_overlap = base_segment_cropped[:, base_w - overlap_px:]
    new_overlap = new_segment_cropped[:, :overlap_px]

    # Create gradient mask
    alpha = np.linspace(0, 1, overlap_px)[np.newaxis, :, np.newaxis] # Shape (1, overlap_px, 1)
    
    # Blend
    blended_overlap = cv2.addWeighted(base_overlap.astype(np.float32), 1 - alpha, new_overlap.astype(np.float32), alpha, 0).astype(np.uint8)
    
    # Combine non-overlapping part of base, blended overlap, and non-overlapping part of new
    non_overlap_base = base_segment_cropped[:, :base_w - overlap_px]
    non_overlap_new = new_segment_cropped[:, overlap_px:]
    
    result = np.concatenate((non_overlap_base, blended_overlap, non_overlap_new), axis=1)
    return result

def _blend_images_vertically(base_image_segment, new_image_segment, overlap_px):
    """Blends the new_image_segment onto the bottom side of base_image_segment with a vertical gradient."""
    if base_image_segment is None or new_image_segment is None:
        return new_image_segment if base_image_segment is None else base_image_segment
    if overlap_px <= 0:
        return np.concatenate((base_image_segment, new_image_segment), axis=0)

    w = min(base_image_segment.shape[1], new_image_segment.shape[1])
    base_h = base_image_segment.shape[0]
    new_h = new_image_segment.shape[0]

    if base_h < overlap_px or new_h < overlap_px:
        return np.concatenate((base_image_segment[:base_h-overlap_px if base_h > overlap_px else 0, :], new_image_segment), axis=0)

    base_segment_cropped = base_image_segment[:, :w]
    new_segment_cropped = new_image_segment[:, :w]

    base_overlap = base_segment_cropped[base_h - overlap_px:, :]
    new_overlap = new_segment_cropped[:overlap_px, :]

    alpha = np.linspace(0, 1, overlap_px)[:, np.newaxis, np.newaxis] # Shape (overlap_px, 1, 1)
    
    blended_overlap = cv2.addWeighted(base_overlap.astype(np.float32), 1 - alpha, new_overlap.astype(np.float32), alpha, 0).astype(np.uint8)
    
    non_overlap_base = base_segment_cropped[:base_h - overlap_px, :]
    non_overlap_new = new_segment_cropped[overlap_px:, :]
    
    result = np.concatenate((non_overlap_base, blended_overlap, non_overlap_new), axis=0)
    return result

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
    object_extraction_background_mode="auto",
    custom_layout=None
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
    loaded_images = load_images_for_stitching_process(
        subfolder_path, 
        output_base_name, 
        STITCH_VIEW_PATTERNS_CONFIG,
        custom_layout=custom_layout 
    )
    if not loaded_images or loaded_images.get("obverse") is None and (custom_layout is None or custom_layout.get("obverse") is None): 
        print(f"Warning/Error: Stitching requires a primary image (e.g. 'obverse'). Loaded: {list(loaded_images.keys()) if loaded_images else 'None'}")
        if not loaded_images: 
             raise ValueError("No images loaded for stitching, cannot proceed.")

    # Step 2: Process images for consistency
    resized_images = resize_tablet_views_for_layout(loaded_images)
    
    # Step 3: Calculate layout for placing images
    canvas_w, canvas_h, layout_coords, images_to_paste_dict = calculate_stitching_layout(
        resized_images, current_view_gap, current_ruler_padding, custom_layout=custom_layout
    )
    
    # Step 4: Create initial canvas and place images
    final_image = create_stitched_canvas(
        canvas_w, canvas_h, 
        images_to_paste_dict, 
        layout_coords, 
        stitched_bg_color,
        custom_layout=custom_layout
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

def create_stitched_canvas(canvas_width, canvas_height, images_dict, layout_coords, bg_color, custom_layout=None, blend_overlap_px=DEFAULT_BLEND_OVERLAP_PX):
    """
    Create a blank canvas and place all images according to the calculated layout.
    Handles single images and sequences of intermediate images with gradient blending.
    Then crop to content bounds.
    """
    # Create initial canvas with background color
    canvas = np.full((canvas_height, canvas_width, 3), bg_color, dtype=np.uint8)
    
    processed_view_segments = {} # To store the fully stitched segment for each view_key

    # Place each image or sequence onto the canvas
    for view_key, coords_tuple in layout_coords.items():
        image_data = images_dict.get(view_key) 
        if image_data is None: 
            continue

        start_x, start_y = coords_tuple[0], coords_tuple[1]

        if isinstance(image_data, list): # It's an intermediate sequence
            current_segment = None
            blend_axis = 'horizontal' # Default
            if "left" in view_key.lower() or "right" in view_key.lower():
                blend_axis = 'vertical'
            
            for i, img_in_sequence in enumerate(image_data):
                if img_in_sequence is None: continue
                if i == 0:
                    current_segment = img_in_sequence
                else:
                    if blend_axis == 'horizontal':
                        current_segment = _blend_images_horizontally(current_segment, img_in_sequence, blend_overlap_px)
                    else: # vertical
                        current_segment = _blend_images_vertically(current_segment, img_in_sequence, blend_overlap_px)
            
            if current_segment is not None:
                paste_image_onto_canvas(canvas, current_segment, start_x, start_y)
                processed_view_segments[view_key] = (current_segment, start_x, start_y)

        else: # It's a single image
            img_to_paste = image_data
            paste_image_onto_canvas(canvas, img_to_paste, start_x, start_y)
            processed_view_segments[view_key] = (img_to_paste, start_x, start_y)
    
    # Crop canvas to actual content based on the originally calculated layout_coords and image dimensions
    min_x_coord, min_y_coord = canvas_width, canvas_height
    max_x_coord, max_y_coord = 0, 0
    
    if not processed_view_segments: # No images pasted
        return canvas # Return empty or bg-filled canvas

    for seg_img, seg_x, seg_y in processed_view_segments.values():
        min_x_coord = min(min_x_coord, seg_x)
        min_y_coord = min(min_y_coord, seg_y)
        max_x_coord = max(max_x_coord, seg_x + seg_img.shape[1])
        max_y_coord = max(max_y_coord, seg_y + seg_img.shape[0])

    # Ensure valid bounds
    min_x_coord = max(0, min_x_coord)
    min_y_coord = max(0, min_y_coord)
    max_x_coord = min(canvas_width, max_x_coord)
    max_y_coord = min(canvas_height, max_y_coord)

    if max_x_coord > min_x_coord and max_y_coord > min_y_coord:
        return canvas[min_y_coord:max_y_coord, min_x_coord:max_x_coord]
    
    return canvas # Should ideally not happen if images were pasted
