from stitch_images import process_tablet_subfolder

# Export all the constants that might be used elsewhere
try:
    from stitch_config import (
        STITCH_VIEW_PATTERNS_CONFIG,
        STITCH_OUTPUT_DPI,
        STITCH_BACKGROUND_COLOR,
        STITCH_TIFF_COMPRESSION,
        STITCH_FINAL_MARGIN_PX,
        STITCH_VIEW_GAP_PX,
        STITCH_RULER_PADDING_PX,
        STITCH_LOGO_MAX_WIDTH_FRACTION,
        STITCH_LOGO_PADDING_ABOVE,
        STITCH_LOGO_PADDING_BELOW,
        JPEG_SAVE_QUALITY,
        FINAL_TIFF_SUBFOLDER_NAME,
        FINAL_JPG_SUBFOLDER_NAME
    )
except ImportError as e:
    print(f"Warning: Could not import constants from stitch_config: {e}")

# This approach allows for a seamless migration without breaking existing code

def process_tablet_subfolder(source_folder_path, object_bg_mode="auto",
                          museum_selection="British Museum", is_complex_layout=False):
    """
    Process a tablet subfolder to create a layout and stitch the views together.
    
    Args:
        source_folder_path: Path to the tablet subfolder
        object_bg_mode: Background removal mode
        museum_selection: Museum selection for scaling
        is_complex_layout: Whether to use complex layout mode
    
    Returns:
        Path to the stitched image
    """
    # ... existing code ...
    
    # For complex layout, use the interactive dialog
    if is_complex_layout:
        # First, extract objects from all images if they haven't been already
        object_extracted_paths = {}
        for img_path in image_paths:
            # Generate the object-extracted filename
            img_dir = os.path.dirname(img_path)
            img_filename = os.path.basename(img_path)
            img_base, img_ext = os.path.splitext(img_filename)
            object_path = os.path.join(img_dir, f"{img_base}_object{img_ext}")
            
            # Extract object if it doesn't exist
            if not os.path.exists(object_path):
                try:
                    extract_and_save_center_object(img_path, object_path)
                    object_extracted_paths[img_path] = object_path
                except Exception as e:
                    print(f"Failed to extract object from {img_path}: {e}")
                    # Use original if extraction fails
                    object_extracted_paths[img_path] = img_path
            else:
                object_extracted_paths[img_path] = object_path
        
        root = get_tk_root()
        dialog = ComplexLayoutDialog(root, image_paths, current_layout, 
                                    object_extracted_paths=object_extracted_paths)
        # ... rest of the function ...
