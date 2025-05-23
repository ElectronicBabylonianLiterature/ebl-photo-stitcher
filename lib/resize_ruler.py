import cv2
import numpy as np
import os

try:
    import cairosvg
    from io import BytesIO
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False
    print("Warning: cairosvg not installed, SVG ruler support will be limited.")

RULER_TARGET_PHYSICAL_WIDTHS_CM = {
    "1cm": 1.752173913043478,
    "2cm": 2.802631578947368,
    "5cm": 5.955752212389381
}
OUTPUT_RULER_SUFFIX = "_07"
OUTPUT_RULER_FILE_EXTENSION = ".tif"
IMAGE_RESIZE_INTERPOLATION_METHOD = cv2.INTER_CUBIC

def svg_to_image(svg_file_path):
    """
    Convert SVG file to a NumPy array suitable for use with OpenCV.

    Args:
        svg_file_path: Path to the SVG file

    Returns:
        NumPy array representing the image
    """
    if not SVG_SUPPORT:
        raise ValueError(
            "SVG support is not available. Please install cairosvg module.")
    try:
        # Convert SVG to PNG in memory with 600 DPI for high resolution
        png_data = cairosvg.svg2png(url=svg_file_path, dpi=600)
        
        # Convert PNG bytes to numpy array
        png_bytes = BytesIO(png_data)
        
        # Read PNG bytes with OpenCV
        nparr = np.frombuffer(png_bytes.getvalue(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        
        # If the image has an alpha channel, convert to RGB
        if img.shape[2] == 4:
            # Get alpha channel
            alpha = img[:, :, 3]
            # Create a white background
            white_background = np.ones_like(img[:, :, :3], dtype=np.uint8) * 255
            # Get RGB channels
            rgb = img[:, :, :3]
            # Alpha blend
            alpha_factor = alpha[:, :, np.newaxis].astype(np.float32) / 255.0
            blended = (rgb * alpha_factor + white_background * (1 - alpha_factor)).astype(np.uint8)
            return blended
        
        return img
    except Exception as e:
        raise ValueError(f"Error converting SVG to image: {e}")

def resize_and_save_ruler_template(
    pixels_per_centimeter_scale,
    chosen_digital_ruler_template_path,
    output_base_name,
    output_directory_path,
    custom_ruler_size_cm=None
):
    """
    Resizes a digital ruler template to match the detected physical scale, 
    and saves it to the output directory.
    
    Args:
        pixels_per_centimeter_scale: The number of pixels per centimeter in the source image
        chosen_digital_ruler_template_path: Path to the digital ruler template to scale
        output_base_name: Base name for the output file
        output_directory_path: Directory to save the scaled ruler
        custom_ruler_size_cm: Optional, custom size of the ruler in cm (for SVG rulers)
    
    Returns:
        The path to the scaled ruler file that was created
    """
    if pixels_per_centimeter_scale <= 1:
        raise ValueError(
            f"Invalid pixels_per_centimeter: {pixels_per_centimeter_scale}")
    if not os.path.exists(chosen_digital_ruler_template_path):
        raise FileNotFoundError(
            f"Chosen digital ruler template file not found: {chosen_digital_ruler_template_path}")
    if not os.path.isdir(output_directory_path):
        raise NotADirectoryError(
            f"Output directory not found or is not a directory: {output_directory_path}")

    # If custom size is provided, use it directly
    if custom_ruler_size_cm is not None:
        target_physical_width_cm = custom_ruler_size_cm
    else:
        # For TIF files, determine size from filename as before
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

    # Check if the file is SVG or a regular image
    if chosen_digital_ruler_template_path.lower().endswith('.svg'):
        digital_ruler_image_array = svg_to_image(chosen_digital_ruler_template_path)
    else:
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