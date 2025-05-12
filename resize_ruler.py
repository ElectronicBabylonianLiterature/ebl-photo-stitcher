import cv2
import numpy as np
import os

RULER_TARGET_PHYSICAL_WIDTHS_CM = {
    "2cm": 2.69,
    "5cm": 5.69
}
OUTPUT_FILENAME_SUFFIX_SEARCH = "_02"
OUTPUT_FILENAME_SUFFIX_REPLACE = "_07"
OUTPUT_FILE_EXTENSION = ".tif"
RESIZE_INTERPOLATION_METHOD = cv2.INTER_CUBIC

def resize_and_save_ruler(pixels_per_centimeter, ruler_template_path, reference_image_path):
    if pixels_per_centimeter <= 1:
        raise ValueError(f"Invalid pixels_per_centimeter: {pixels_per_centimeter}")
    if not os.path.exists(ruler_template_path):
        raise FileNotFoundError(f"Ruler template file not found: {ruler_template_path}")
    if not os.path.exists(os.path.dirname(reference_image_path)):
         raise FileNotFoundError(f"Directory for reference image not found: {os.path.dirname(reference_image_path)}")

    ruler_filename_lower = os.path.basename(ruler_template_path).lower()
    target_physical_width_cm = None
    for key, value in RULER_TARGET_PHYSICAL_WIDTHS_CM.items():
        if key in ruler_filename_lower:
            target_physical_width_cm = value
            break

    if target_physical_width_cm is None:
        raise ValueError(f"Could not determine target cm size from template filename: {ruler_filename_lower}")

    target_pixel_width = int(round(pixels_per_centimeter * target_physical_width_cm))
    if target_pixel_width <= 0:
        raise ValueError(f"Calculated target pixel width ({target_pixel_width}) is invalid.")

    ruler_template_image = cv2.imread(ruler_template_path, cv2.IMREAD_UNCHANGED)
    if ruler_template_image is None:
        raise ValueError(f"Could not load ruler template image: {ruler_template_path}")

    template_height_px, template_width_px = ruler_template_image.shape[:2]
    if template_width_px <= 0 or template_height_px <= 0:
         raise ValueError(f"Invalid dimensions for ruler template image: {template_width_px}x{template_height_px}")

    aspect_ratio = template_height_px / template_width_px
    target_pixel_height = int(round(target_pixel_width * aspect_ratio))
    if target_pixel_height <= 0:
        raise ValueError(f"Calculated target pixel height ({target_pixel_height}) is invalid.")

    resized_ruler_image = cv2.resize(
        ruler_template_image,
        (target_pixel_width, target_pixel_height),
        interpolation=RESIZE_INTERPOLATION_METHOD
    )

    reference_dir = os.path.dirname(reference_image_path)
    reference_base_name = os.path.basename(reference_image_path)
    reference_name_part, _ = os.path.splitext(reference_base_name)

    if OUTPUT_FILENAME_SUFFIX_SEARCH in reference_name_part:
         output_name_part = reference_name_part.replace(
             OUTPUT_FILENAME_SUFFIX_SEARCH, OUTPUT_FILENAME_SUFFIX_REPLACE, 1
         )
    else:
         output_name_part = reference_name_part

    output_filename = output_name_part + OUTPUT_FILE_EXTENSION
    output_filepath = os.path.join(reference_dir, output_filename)

    try:
        success = cv2.imwrite(output_filepath, resized_ruler_image)
        if not success:
             raise IOError("cv2.imwrite failed to save the resized ruler image.")
        print(f"    Successfully saved resized ruler: {output_filepath}")
    except Exception as e:
        raise IOError(f"Error saving resized ruler image to {output_filepath}: {e}")