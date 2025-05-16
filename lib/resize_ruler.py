import cv2
import numpy as np
import os

RULER_TARGET_PHYSICAL_WIDTHS_CM = {
    "1cm": 1.752173913043478,
    "2cm": 2.802631578947368,
    "5cm": 5.955752212389381
}
OUTPUT_RULER_SUFFIX = "_07"
OUTPUT_RULER_FILE_EXTENSION = ".tif"
IMAGE_RESIZE_INTERPOLATION_METHOD = cv2.INTER_CUBIC


def resize_and_save_ruler_template(
    pixels_per_centimeter_scale,
    chosen_digital_ruler_template_path,
    output_base_name,
    output_directory_path
):
    if pixels_per_centimeter_scale <= 1:
        raise ValueError(
            f"Invalid pixels_per_centimeter: {pixels_per_centimeter_scale}")
    if not os.path.exists(chosen_digital_ruler_template_path):
        raise FileNotFoundError(
            f"Chosen digital ruler template file not found: {chosen_digital_ruler_template_path}")
    if not os.path.isdir(output_directory_path):
        raise NotADirectoryError(
            f"Output directory not found or is not a directory: {output_directory_path}")

    template_filename_lower = os.path.basename(
        chosen_digital_ruler_template_path).lower()
    target_physical_width_cm = None
    for key_cm_str, width_val_cm in RULER_TARGET_PHYSICAL_WIDTHS_CM.items():
        if key_cm_str in template_filename_lower:
            target_physical_width_cm = width_val_cm
            break
    if target_physical_width_cm is None:
        raise ValueError(
            f"Could not determine target cm size from chosen digital template: {template_filename_lower}")

    target_pixel_width = int(
        round(pixels_per_centimeter_scale * target_physical_width_cm))
    if target_pixel_width <= 0:
        raise ValueError(
            f"Calculated target pixel width ({target_pixel_width}) for digital ruler is invalid.")

    digital_ruler_image_array = cv2.imread(
        chosen_digital_ruler_template_path, cv2.IMREAD_UNCHANGED)
    if digital_ruler_image_array is None:
        raise ValueError(
            f"Could not load digital ruler template image from: {chosen_digital_ruler_template_path}")

    current_h_px, current_w_px = digital_ruler_image_array.shape[:2]
    if current_w_px <= 0 or current_h_px <= 0:
        raise ValueError(
            f"Invalid dimensions for digital ruler template: {current_w_px}x{current_h_px}")

    aspect_ratio_val = current_h_px / current_w_px if current_w_px > 0 else 0
    target_pixel_height = int(
        round(target_pixel_width * aspect_ratio_val)) if aspect_ratio_val > 0 else 0

    if target_pixel_width > 0 and target_pixel_height <= 0:
        target_pixel_height = 1
    if target_pixel_width <= 0 or target_pixel_height <= 0:
        raise ValueError(
            f"Final calculated target digital ruler dimensions invalid: {target_pixel_width}x{target_pixel_height}")

    resized_digital_ruler_img_array = cv2.resize(
        digital_ruler_image_array,
        (target_pixel_width, target_pixel_height),
        interpolation=IMAGE_RESIZE_INTERPOLATION_METHOD
    )

    output_ruler_filename = f"{output_base_name}{OUTPUT_RULER_SUFFIX}{OUTPUT_RULER_FILE_EXTENSION}"
    output_ruler_filepath = os.path.join(
        output_directory_path, output_ruler_filename)

    try:
        if not cv2.imwrite(output_ruler_filepath, resized_digital_ruler_img_array):
            raise IOError("cv2.imwrite failed for resized digital ruler.")
        print(
            f"    Successfully saved scaled digital ruler: {output_ruler_filepath}")
        return output_ruler_filepath
    except Exception as e:
        raise IOError(
            f"Error saving resized digital ruler to {output_ruler_filepath}: {e}")
