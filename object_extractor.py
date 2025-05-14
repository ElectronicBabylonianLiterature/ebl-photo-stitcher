# object_extractor.py
import cv2
import numpy as np
import os
import sys
# Assuming remove_background.py is in the same directory or Python path
try:
    from remove_background import create_object_mask, select_center_contour
except ImportError:
    print("ERROR: Could not import from remove_background.py. Ensure it's in the same directory.")
    sys.exit(1)


# --- Default Configuration (can be overridden by caller) ---
DEFAULT_TARGET_BACKGROUND_COLOR_BGR = (0, 0, 0) # This is the color the object will be placed ON
DEFAULT_EXTRACTION_BACKGROUND_COLOR_BGR = (0, 0, 0) # This is the color TO REMOVE from original
DEFAULT_FEATHER_RADIUS_PX = 5
DEFAULT_OUTPUT_FILENAME_SUFFIX = "_object.tif" # User specified this suffix previously
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

# --- Main Extraction Function ---
def extract_and_save_object(
    input_image_path,
    extraction_background_color=DEFAULT_EXTRACTION_BACKGROUND_COLOR_BGR, # Background to remove
    output_background_color=DEFAULT_TARGET_BACKGROUND_COLOR_BGR,       # Background for the new image
    feather_radius=DEFAULT_FEATHER_RADIUS_PX,
    output_suffix=DEFAULT_OUTPUT_FILENAME_SUFFIX,
    color_tolerance=DEFAULT_BACKGROUND_COLOR_TOLERANCE,
    min_area_fraction=DEFAULT_MIN_CONTOUR_AREA_FRACTION
):
    print(f"  Extracting object from: {os.path.basename(input_image_path)}")
    print(f"    Removing background color: {extraction_background_color}")
    print(f"    Output background color: {output_background_color}")

    original_image = cv2.imread(input_image_path)
    if original_image is None:
        raise FileNotFoundError(f"Could not load image for object extraction: {input_image_path}")

    # Step 1: Create initial mask of all objects against the specified background
    initial_object_mask = create_object_mask(
        original_image,
        extraction_background_color,
        color_tolerance
    )
    if initial_object_mask is None or np.sum(initial_object_mask) == 0 : # Check if mask is empty
        raise ValueError("No objects found against the specified extraction background.")

    # Step 2: Select the center-most contour
    selected_contour = select_center_contour(
        original_image,
        initial_object_mask,
        min_area_fraction
    )
    if selected_contour is None:
        raise ValueError("No suitable center object contour found meeting criteria.")
    
    print(f"    Selected center contour for extraction.")

    # Step 3: Create a final mask using only the selected contour
    object_mask_final = np.zeros_like(initial_object_mask)
    cv2.drawContours(object_mask_final, [selected_contour], -1, (255), thickness=cv2.FILLED)

    # Step 4: Apply Feathering to the Final Mask
    ksize = feather_radius * 4 + 1 
    sigma = feather_radius * 0.8 
    feathered_mask_raw = cv2.GaussianBlur(object_mask_final, (ksize, ksize), sigma)
    feathered_mask_normalized = feathered_mask_raw / 255.0
    feathered_mask_3channel = cv2.merge([feathered_mask_normalized] * 3)

    # Step 5: Create Output Canvas and Blend
    # The output canvas will have the 'output_background_color'
    output_canvas = np.full_like(original_image, output_background_color, dtype=np.uint8)
    
    blended_image = (
        output_canvas.astype(np.float32) * (1.0 - feathered_mask_3channel) +
        original_image.astype(np.float32) * feathered_mask_3channel
    ).astype(np.uint8)

    # Step 6: Trim the Image
    bbox = get_mask_bounding_box(object_mask_final) # Trim based on the non-feathered selected object
    if bbox is None:
        print("  Warning: Could not determine bounding box for object. Saving untrimmed.")
        cropped_image = blended_image
    else:
        xmin, ymin, xmax, ymax = bbox
        cropped_image = blended_image[ymin:ymax, xmin:xmax]
        print(f"    Trimmed extracted object to bounding box: x=[{xmin}:{xmax}], y=[{ymin}:{ymax}]")

    # Step 7: Save the Result
    base, _ = os.path.splitext(input_image_path)
    output_filepath = f"{base}{output_suffix}"

    try:
        success = cv2.imwrite(output_filepath, cropped_image)
        if not success:
            raise IOError("cv2.imwrite failed to save extracted object.")
        print(f"    Successfully saved extracted object: {output_filepath}")
        return output_filepath # Return the path of the saved file
    except Exception as e:
        raise IOError(f"Error saving extracted object to {output_filepath}: {e}")


# --- Optional: Standalone execution for testing this module ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage for direct testing: python object_extractor.py <path_to_image> [background_r] [background_g] [background_b]")
        sys.exit(1)

    test_image_path = sys.argv[1]
    test_extraction_bg = DEFAULT_EXTRACTION_BACKGROUND_COLOR_BGR
    test_output_bg = DEFAULT_TARGET_BACKGROUND_COLOR_BGR

    if len(sys.argv) == 5:
        try:
            r, g, b = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
            test_extraction_bg = (b, g, r) # OpenCV uses BGR
            test_output_bg = (b,g,r) # For testing, make them same
            print(f"Using custom background for test: BGR {test_extraction_bg}")
        except ValueError:
            print("Invalid background color arguments. Using default.")


    if not os.path.exists(test_image_path):
         print(f"Error: Test image not found at {test_image_path}")
         sys.exit(1)

    print(f"--- Running Object Extractor Standalone Test ---")
    try:
        extract_and_save_object(
            test_image_path,
            extraction_background_color=test_extraction_bg,
            output_background_color=test_output_bg
            )
        print(f"--- Standalone Test Completed Successfully ---")
    except Exception as e:
        print(f"--- Standalone Test Failed: {e} ---")
        sys.exit(1)
