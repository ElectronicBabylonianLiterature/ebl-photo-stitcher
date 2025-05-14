
import cv2
import numpy as np
import os
import sys
try:
    from remove_background import create_object_mask, select_center_contour, detect_dominant_corner_background
except ImportError:
    print("ERROR: Could not import from remove_background.py. Ensure it's in the same directory.")
    sys.exit(1)


DEFAULT_EXTRACTION_BACKGROUND_MODE = "auto"
DEFAULT_TARGET_OUTPUT_BACKGROUND_BGR = (0, 0, 0)
DEFAULT_FEATHER_RADIUS_PX = 5
DEFAULT_OUTPUT_FILENAME_SUFFIX = "_object.tif"
DEFAULT_BACKGROUND_COLOR_TOLERANCE = 40
DEFAULT_MIN_CONTOUR_AREA_FRACTION = 0.010


def get_mask_bounding_box(mask):
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not np.any(rows) or not np.any(cols):
        return None
    ymin, ymax = np.where(rows)[0][[0, -1]]
    xmin, xmax = np.where(cols)[0][[0, -1]]
    return xmin, ymin, xmax + 1, ymax + 1


def extract_and_save_object(
    input_image_path,
    extraction_background_mode=DEFAULT_EXTRACTION_BACKGROUND_MODE,
    output_background_color=DEFAULT_TARGET_OUTPUT_BACKGROUND_BGR,
    feather_radius=DEFAULT_FEATHER_RADIUS_PX,
    output_suffix=DEFAULT_OUTPUT_FILENAME_SUFFIX,
    color_tolerance=DEFAULT_BACKGROUND_COLOR_TOLERANCE,
    min_area_fraction=DEFAULT_MIN_CONTOUR_AREA_FRACTION
):
    print(f"  Extracting object from: {os.path.basename(input_image_path)}")

    original_image = cv2.imread(input_image_path)
    if original_image is None:
        raise FileNotFoundError(
            f"Could not load image for object extraction: {input_image_path}")

    actual_extraction_bg_color = None
    if extraction_background_mode == "auto":
        print("    Auto-detecting background color for extraction...")
        actual_extraction_bg_color = detect_dominant_corner_background(original_image)
    elif extraction_background_mode == "black":
        actual_extraction_bg_color = (0, 0, 0)
    elif extraction_background_mode == "white":
        actual_extraction_bg_color = (255, 255, 255)
    else:
        print(
            f"    Warning: Invalid extraction_background_mode '{extraction_background_mode}'. Defaulting to auto.")
        actual_extraction_bg_color = detect_dominant_corner_background(original_image)

    print(f"    Using extraction background color: {actual_extraction_bg_color}")
    print(f"    Output background color for new image: {output_background_color}")

    initial_object_mask = create_object_mask(
        original_image,
        actual_extraction_bg_color,
        color_tolerance
    )
    if initial_object_mask is None or np.sum(initial_object_mask) == 0:
        raise ValueError(
            "No objects found against the specified/detected extraction background.")

    selected_contour = select_center_contour(
        original_image,
        initial_object_mask,
        min_area_fraction
    )
    if selected_contour is None:
        raise ValueError("No suitable center object contour found meeting criteria.")

    print(f"    Selected center contour for extraction.")

    object_mask_final = np.zeros_like(initial_object_mask)
    cv2.drawContours(object_mask_final, [
                     selected_contour], -1, (255), thickness=cv2.FILLED)

    ksize = feather_radius * 4 + 1
    sigma = feather_radius * 0.8
    feathered_mask_raw = cv2.GaussianBlur(object_mask_final, (ksize, ksize), sigma)
    feathered_mask_normalized = feathered_mask_raw / 255.0
    feathered_mask_3channel = cv2.merge([feathered_mask_normalized] * 3)

    output_canvas_with_specified_bg = np.full_like(
        original_image, output_background_color, dtype=np.uint8)

    blended_image = (
        output_canvas_with_specified_bg.astype(
            np.float32) * (1.0 - feathered_mask_3channel)
        + original_image.astype(np.float32) * feathered_mask_3channel
    ).astype(np.uint8)

    bbox = get_mask_bounding_box(object_mask_final)
    if bbox is None:
        print("  Warning: Could not determine bounding box. Saving untrimmed.")
        cropped_image = blended_image
    else:
        xmin, ymin, xmax, ymax = bbox
        cropped_image = blended_image[ymin:ymax, xmin:xmax]
        print(
            f"    Trimmed extracted object to bounding box: x=[{xmin}:{xmax}], y=[{ymin}:{ymax}]")

    base, _ = os.path.splitext(input_image_path)
    output_filepath = f"{base}{output_suffix}"

    try:
        success = cv2.imwrite(output_filepath, cropped_image)
        if not success:
            raise IOError("cv2.imwrite failed to save extracted object.")
        print(f"    Successfully saved extracted object: {output_filepath}")
        return output_filepath
    except Exception as e:
        raise IOError(f"Error saving extracted object to {output_filepath}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage for direct testing: python object_extractor.py <path_to_image> [mode: auto/black/white]")
        sys.exit(1)

    test_image_path = sys.argv[1]
    test_mode = DEFAULT_EXTRACTION_BACKGROUND_MODE
    if len(sys.argv) > 2 and sys.argv[2].lower() in ["auto", "black", "white"]:
        test_mode = sys.argv[2].lower()

    if not os.path.exists(test_image_path):
        print(f"Error: Test image not found at {test_image_path}")
        sys.exit(1)

    print(f"--- Running Object Extractor Standalone Test ---")
    try:
        extract_and_save_object(test_image_path, extraction_background_mode=test_mode)
        print(f"--- Standalone Test Completed Successfully ---")
    except Exception as e:
        print(f"--- Standalone Test Failed: {e} ---")
        sys.exit(1)
