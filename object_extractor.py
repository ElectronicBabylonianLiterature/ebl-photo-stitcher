# object_extractor.py (Select Center Object)
import cv2
import numpy as np
import os
import sys
import math # Needed for distance calculation

# --- Default Configuration (can be overridden by caller) ---
DEFAULT_TARGET_BACKGROUND_COLOR_BGR = (0, 0, 0)
DEFAULT_FEATHER_RADIUS_PX = 5
DEFAULT_OUTPUT_FILENAME_SUFFIX = "_object.tif"
DEFAULT_BACKGROUND_COLOR_TOLERANCE = 40
DEFAULT_MIN_CONTOUR_AREA_FRACTION = 0.010

# --- Helper Function ---
def get_mask_bounding_box(mask):
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not np.any(rows) or not np.any(cols):
        return None
    ymin, ymax = np.where(rows)[0][[0, -1]]
    xmin, xmax = np.where(cols)[0][[0, -1]]
    return xmin, ymin, xmax + 1, ymax + 1

# --- Main Extraction Function (Modified) ---
def extract_and_save_object(
    input_image_path,
    background_color=DEFAULT_TARGET_BACKGROUND_COLOR_BGR,
    feather_radius=DEFAULT_FEATHER_RADIUS_PX,
    output_suffix=DEFAULT_OUTPUT_FILENAME_SUFFIX,
    color_tolerance=DEFAULT_BACKGROUND_COLOR_TOLERANCE,
    min_area_fraction=DEFAULT_MIN_CONTOUR_AREA_FRACTION
):
    print(f"  Extracting object from: {os.path.basename(input_image_path)}")
    original_image = cv2.imread(input_image_path)
    if original_image is None:
        raise FileNotFoundError(f"Could not load image for object extraction: {input_image_path}")
    h, w = original_image.shape[:2]
    image_center_x = w / 2
    image_center_y = h / 2
    total_pixels = h * w

    # --- Find potential object contours ---
    lower_bound = np.array([max(0, c - color_tolerance) for c in background_color])
    upper_bound = np.array([min(255, c + color_tolerance) for c in background_color])
    background_mask = cv2.inRange(original_image, lower_bound, upper_bound)
    object_mask_initial = cv2.bitwise_not(background_mask)

    kernel = np.ones((3, 3), np.uint8)
    object_mask_cleaned = cv2.morphologyEx(object_mask_initial, cv2.MORPH_OPEN, kernel, iterations=2)
    object_mask_cleaned = cv2.morphologyEx(object_mask_cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(object_mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No object contours found.")

    # --- Select Contour Closest to Center ---
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= total_pixels * min_area_fraction:
            valid_contours.append(contour)

    if not valid_contours:
         raise ValueError(f"No contours found meeting minimum area requirement ({min_area_fraction*100:.1f}%).")

    closest_contour = None
    min_distance_to_center = float('inf')

    for contour in valid_contours:
        # Calculate the centroid of the contour
        M = cv2.moments(contour)
        if M["m00"] == 0: # Avoid division by zero for invalid contours
            continue
        centroid_x = int(M["m10"] / M["m00"])
        centroid_y = int(M["m01"] / M["m00"])

        # Calculate distance from image center to contour centroid
        distance = math.sqrt((centroid_x - image_center_x)**2 + (centroid_y - image_center_y)**2)

        if distance < min_distance_to_center:
            min_distance_to_center = distance
            closest_contour = contour

    if closest_contour is None:
        # This should theoretically not happen if valid_contours is not empty
        raise ValueError("Could not determine the contour closest to the center.")

    print(f"    Selected contour closest to center (distance: {min_distance_to_center:.1f}px).")

    # --- Proceed with the selected contour ---
    object_mask_final = np.zeros_like(object_mask_cleaned)
    cv2.drawContours(object_mask_final, [closest_contour], -1, (255), thickness=cv2.FILLED)

    ksize = feather_radius * 4 + 1
    sigma = feather_radius * 0.8
    feathered_mask_raw = cv2.GaussianBlur(object_mask_final, (ksize, ksize), sigma)
    feathered_mask_normalized = feathered_mask_raw / 255.0
    feathered_mask_3channel = cv2.merge([feathered_mask_normalized] * 3)

    output_canvas = np.full_like(original_image, background_color, dtype=np.uint8)
    blended_image = (
        output_canvas.astype(np.float32) * (1.0 - feathered_mask_3channel) +
        original_image.astype(np.float32) * feathered_mask_3channel
    ).astype(np.uint8)

    bbox = get_mask_bounding_box(object_mask_final)
    if bbox is None:
        print("  Warning: Could not determine bounding box for object. Saving untrimmed.")
        cropped_image = blended_image
    else:
        xmin, ymin, xmax, ymax = bbox
        cropped_image = blended_image[ymin:ymax, xmin:xmax]

    base, _ = os.path.splitext(input_image_path)
    output_filepath = f"{base}{output_suffix}"

    try:
        success = cv2.imwrite(output_filepath, cropped_image)
        if not success:
            raise IOError("cv2.imwrite failed to save extracted object.")
        print(f"    Successfully saved extracted object: {output_filepath}")
    except Exception as e:
        raise IOError(f"Error saving extracted object to {output_filepath}: {e}")


# --- Optional: Standalone execution for testing this module ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage for direct testing: python object_extractor.py <path_to_image>")
        sys.exit(1)

    test_image_path = sys.argv[1]
    if not os.path.exists(test_image_path):
         print(f"Error: Test image not found at {test_image_path}")
         sys.exit(1)

    print(f"--- Running Object Extractor Standalone Test ---")
    try:
        extract_and_save_object(test_image_path) # Use default settings
        print(f"--- Standalone Test Completed Successfully ---")
    except Exception as e:
        print(f"--- Standalone Test Failed: {e} ---")
        sys.exit(1)
