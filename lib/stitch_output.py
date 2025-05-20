# Output management for the stitching process
import cv2 
import numpy as np
import os
import imageio
import datetime
import time # Import time for sleep
from stitch_config import (
    FINAL_TIFF_SUBFOLDER_NAME,
    FINAL_JPG_SUBFOLDER_NAME,
    JPEG_SAVE_QUALITY,
    STITCH_INSTITUTION,
    STITCH_CREDIT_LINE,
    STITCH_XMP_USAGE_TERMS
)

try:
    from pure_metadata import apply_all_metadata, set_basic_exif_metadata
except ImportError as e:
    print(f"CRITICAL ERROR in stitch_output.py: Could not import metadata utils: {e}")
    raise

def save_stitched_output(
    final_image, 
    main_input_folder_path, 
    output_base_name,
    photographer_name,
    output_dpi
):
    """Save stitched output in both TIFF and JPG formats with metadata."""
    if not isinstance(final_image, np.ndarray) or final_image.size == 0:
        raise ValueError("Invalid image for saving")

    # Define output paths and directories
    final_tiff_output_dir = os.path.join(main_input_folder_path, FINAL_TIFF_SUBFOLDER_NAME)
    final_jpg_output_dir = os.path.join(main_input_folder_path, FINAL_JPG_SUBFOLDER_NAME)
    os.makedirs(final_tiff_output_dir, exist_ok=True)
    os.makedirs(final_jpg_output_dir, exist_ok=True)

    tiff_filepath = os.path.join(final_tiff_output_dir, f"{output_base_name}.tif")
    jpg_filepath = os.path.join(final_jpg_output_dir, f"{output_base_name}.jpg")

    # Save TIFF
    print(f"    Attempting to save TIFF to: {tiff_filepath}")
    tiff_save_success = save_tiff_output(final_image, tiff_filepath)

    # Save JPG
    print(f"    Attempting to save JPG to: {jpg_filepath}")
    jpg_save_success = save_jpg_output(final_image, jpg_filepath)

    # ADD A SMALL DELAY before attempting metadata operations, especially for TIFF
    if tiff_save_success or jpg_save_success:
        print("    Brief pause before metadata application...")
        time.sleep(0.5) # Wait for 0.5 seconds

    # Set metadata if TIFF save was successful
    if tiff_save_success:
        apply_metadata(tiff_filepath, output_base_name, photographer_name, output_dpi)
    else:
        print(f"    Skipping metadata for TIFF as save failed: {os.path.basename(tiff_filepath)}")

    # Set metadata if JPG save was successful
    if jpg_save_success:
        apply_metadata(jpg_filepath, output_base_name, photographer_name, output_dpi)
    else:
        print(f"    Skipping metadata for JPG as save failed: {os.path.basename(jpg_filepath)}")
    
    return (tiff_filepath if tiff_save_success else None, 
            jpg_filepath if jpg_save_success else None)

def save_tiff_output(image, output_path):
    """Save image as TIFF format using primary and fallback methods."""
    try:
        # Convert BGR to RGB for imageio
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if image_rgb is None or image_rgb.size == 0:
            raise ValueError("Color conversion failed")

        imageio.imwrite(output_path, image_rgb, format='TIFF')
        print(f"      Successfully saved TIFF (image data): {os.path.basename(output_path)}")
        return True
    except Exception as e_imageio: 
        print(f"ERROR saving stitched TIFF with imageio: {e_imageio}")
        
        # Fallback to OpenCV
        try: 
            print(f"      Attempting fallback cv2.imwrite for TIFF: {output_path}")
            if not cv2.imwrite(output_path, image):
                 raise IOError("cv2.imwrite for TIFF fallback returned False.")
            print(f"      Saved TIFF via cv2 (fallback).")
            return True
        except Exception as e_cv2_tiff:
            print(f"      ERROR saving final TIFF with cv2 fallback: {e_cv2_tiff}")
            return False

def save_jpg_output(image, output_path):
    """Save image as JPEG format."""
    try:
        if not cv2.imwrite(output_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_SAVE_QUALITY]):
            raise IOError("cv2.imwrite for JPG returned False.")
        print(f"      Successfully saved JPG: {os.path.basename(output_path)} with quality {JPEG_SAVE_QUALITY}")
        return True
    except Exception as e_jpg:
        print(f"      ERROR saving final JPG: {e_jpg}")
        return False

def apply_metadata(image_path, output_base_name, photographer_name, output_dpi):
    """Apply EXIF and XMP metadata to the image file."""
    print(f"    Setting metadata for: {os.path.basename(image_path)}...")
    year = str(datetime.date.today().year)
    photographer_name_with_institution=f"{photographer_name} ({STITCH_INSTITUTION})"
    
    # Use the pure Python metadata handling
    metadata_applied = apply_all_metadata(
        image_path, 
        image_title=output_base_name, 
        photographer_name=photographer_name_with_institution,
        institution_name=STITCH_INSTITUTION, 
        credit_line_text=STITCH_CREDIT_LINE,
        copyright_text=STITCH_CREDIT_LINE,
        usage_terms_text=STITCH_XMP_USAGE_TERMS,
        image_dpi=output_dpi
    )
    
    # Fall back to basic EXIF metadata if the pure Python approach fails
    if not metadata_applied:
        print("      Falling back to basic EXIF metadata.")
        set_basic_exif_metadata(
            image_path, 
            output_base_name, 
            photographer_name_with_institution,
            STITCH_CREDIT_LINE,
            STITCH_INSTITUTION,
            output_dpi
        )
