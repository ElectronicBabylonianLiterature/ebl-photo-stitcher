import cv2
import numpy as np
import os
try:
    from image_utils import paste_image_onto_canvas, convert_to_bgr_if_needed
except ImportError:
    print("ERROR: image_merger.py - Could not import from image_utils.py")
    # Depending on how this module is used, you might want to sys.exit(1)
    # For now, allow it to be imported but functions might fail if image_utils is missing.
    paste_image_onto_canvas = None 
    convert_to_bgr_if_needed = None


DEFAULT_PADDING_AS_RULER_HEIGHT_FRACTION = 0.10
DEFAULT_CANVAS_BACKGROUND_BGR_COLOR = (0, 0, 0)
DEFAULT_OUTPUT_IMAGE_SUFFIX = "_merged.jpg"
DEFAULT_JPEG_OUTPUT_QUALITY = 95

def merge_extracted_object_and_scaled_ruler(
    extracted_object_image_path,
    scaled_ruler_image_path,
    output_file_base_name,
    padding_as_ruler_height_fraction=DEFAULT_PADDING_AS_RULER_HEIGHT_FRACTION,
    canvas_background_bgr_color=DEFAULT_CANVAS_BACKGROUND_BGR_COLOR,
    output_image_suffix=DEFAULT_OUTPUT_IMAGE_SUFFIX,
    jpeg_output_quality=DEFAULT_JPEG_OUTPUT_QUALITY
):
    if paste_image_onto_canvas is None or convert_to_bgr_if_needed is None:
        raise ImportError("image_utils.py functions not imported correctly in image_merger.py")

    print(f"  Merging: {os.path.basename(extracted_object_image_path)} + {os.path.basename(scaled_ruler_image_path)}")

    object_image_bgr = convert_to_bgr_if_needed(cv2.imread(extracted_object_image_path))
    ruler_image_bgra_or_bgr = cv2.imread(scaled_ruler_image_path, cv2.IMREAD_UNCHANGED)

    if object_image_bgr is None:
        raise ValueError(f"Failed to load object: {extracted_object_image_path}")
    if ruler_image_bgra_or_bgr is None:
        raise ValueError(f"Failed to load ruler: {scaled_ruler_image_path}")

    obj_h_px, obj_w_px = object_image_bgr.shape[:2]
    ruler_h_px, ruler_w_px = ruler_image_bgra_or_bgr.shape[:2]

    calculated_padding_px = int(round(ruler_h_px * padding_as_ruler_height_fraction))

    final_canvas_width_px = max(obj_w_px, ruler_w_px)
    final_canvas_height_px = obj_h_px + calculated_padding_px + ruler_h_px
    
    output_canvas = np.full((final_canvas_height_px, final_canvas_width_px, 3), canvas_background_bgr_color, dtype=np.uint8)

    obj_start_x = (final_canvas_width_px - obj_w_px) // 2
    obj_start_y = 0
    paste_image_onto_canvas(output_canvas, object_image_bgr, obj_start_x, obj_start_y)

    ruler_start_x = (final_canvas_width_px - ruler_w_px) // 2
    ruler_start_y = obj_h_px + calculated_padding_px
    paste_image_onto_canvas(output_canvas, ruler_image_bgra_or_bgr, ruler_start_x, ruler_start_y)
    
    output_directory = os.path.dirname(extracted_object_image_path)
    output_filename = f"{output_file_base_name}{output_image_suffix}"
    output_filepath = os.path.join(output_directory, output_filename)

    save_params = []
    if output_image_suffix.lower().endswith((".jpg", ".jpeg")):
        save_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_output_quality]
    
    if not cv2.imwrite(output_filepath, output_canvas, save_params):
        raise IOError(f"Failed to save merged image to {output_filepath}")
    print(f"    Successfully saved merged image: {output_filepath}")
    return output_filepath
