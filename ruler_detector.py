# ruler_detector.py (Updated Workflow)
import cv2
import numpy as np
import os
import sys

# --- Module Imports with Error Handling ---
try:
    import resize_ruler
except ImportError:
    print("ERROR: Could not import the 'resize_ruler.py' module.")
    resize_ruler = None

try:
    # Import the renamed function from image_merger
    from image_merger import merge_object_and_ruler
except ImportError:
    print("ERROR: Could not import 'merge_object_and_ruler' from image_merger.py.")
    merge_object_and_ruler = None

try:
    from object_extractor import extract_and_save_object
    from object_extractor import (
        DEFAULT_TARGET_BACKGROUND_COLOR_BGR,
        DEFAULT_FEATHER_RADIUS_PX,
        DEFAULT_OUTPUT_FILENAME_SUFFIX,
        DEFAULT_BACKGROUND_COLOR_TOLERANCE,
        DEFAULT_MIN_CONTOUR_AREA_FRACTION
    )
except ImportError:
    print("ERROR: Could not import 'extract_and_save_object' from object_extractor.py.")
    extract_and_save_object = None


# --- Configuration: Ruler Detection ---
RULER_ROI_TOP_FRACTION = 0.05
RULER_ROI_BOTTOM_FRACTION = 0.25
RULER_ANALYSIS_SCANLINE_COUNT = 7
RULER_MARK_BINARIZATION_THRESHOLD = 150
MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.08
MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.30
RULER_MARK_WIDTH_SIMILARITY_TOLERANCE = 0.40
MIN_ALTERNATING_MARKS_FOR_SCALE = 2

# --- Configuration: General ---
INPUT_SUBDIRECTORY_NAME = "Examples"
RULER_TEMPLATE_2CM_PATH = "G:/My Drive/eBL_admin/Photos/BM_2cm_scale.tif"
RULER_TEMPLATE_5CM_PATH = "G:/My Drive/eBL_admin/Photos/BM_5cm_scale.tif"
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif')


# --- Helper Functions (Ruler Detection Only) ---
def extract_pixel_runs_from_scanline(scanline_pixel_data, binarization_threshold_value):
    # (Code from previous version - unchanged)
    binary_scanline = np.where(scanline_pixel_data < binarization_threshold_value, 0, 255)
    pixel_runs = []
    if binary_scanline.size == 0: return pixel_runs
    current_run_color_type = None
    current_run_start_index = 0
    for i, pixel_value in enumerate(binary_scanline):
        pixel_color_type = 'black' if pixel_value == 0 else 'white'
        if current_run_color_type is None:
            current_run_color_type = pixel_color_type
            current_run_start_index = i
        elif pixel_color_type != current_run_color_type:
            run_width_pixels = i - current_run_start_index
            if run_width_pixels > 0:
                pixel_runs.append({
                    'type': current_run_color_type, 'start_index': current_run_start_index,
                    'end_index': i - 1, 'width_pixels': run_width_pixels
                })
            current_run_color_type = pixel_color_type
            current_run_start_index = i
    if current_run_color_type is not None:
        run_width_pixels = len(binary_scanline) - current_run_start_index
        if run_width_pixels > 0:
            pixel_runs.append({
                'type': current_run_color_type, 'start_index': current_run_start_index,
                'end_index': len(binary_scanline) - 1, 'width_pixels': run_width_pixels
            })
    return pixel_runs

def estimate_pixels_per_centimeter_from_ruler(image_filepath):
    # (Code from previous version - unchanged)
    input_image = cv2.imread(image_filepath)
    if input_image is None: raise FileNotFoundError(f"Input image not found: {image_filepath}")
    image_height_pixels, image_width_pixels = input_image.shape[:2]
    ruler_roi_start_y = int(image_height_pixels * RULER_ROI_TOP_FRACTION)
    ruler_roi_end_y = int(image_height_pixels * RULER_ROI_BOTTOM_FRACTION)
    if not (0 <= ruler_roi_start_y < ruler_roi_end_y <= image_height_pixels): raise ValueError(f"Invalid ROI y=[{ruler_roi_start_y}, {ruler_roi_end_y}]")
    ruler_strip_roi_color = input_image[ruler_roi_start_y:ruler_roi_end_y, :]
    if ruler_strip_roi_color.size == 0: raise ValueError("Ruler ROI empty.")
    ruler_strip_roi_grayscale = cv2.cvtColor(ruler_strip_roi_color, cv2.COLOR_BGR2GRAY)
    roi_height_pixels, roi_width_pixels = ruler_strip_roi_grayscale.shape
    if roi_width_pixels == 0: raise ValueError("Ruler ROI width zero.")
    candidate_cm_widths_in_pixels = []
    min_mark_width_px = roi_width_pixels * MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION
    max_mark_width_px = roi_width_pixels * MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION
    for i in range(RULER_ANALYSIS_SCANLINE_COUNT):
        scanline_y_coordinate = int(roi_height_pixels * ((i + 0.5) / RULER_ANALYSIS_SCANLINE_COUNT))
        current_scanline_data = ruler_strip_roi_grayscale[scanline_y_coordinate, :]
        pixel_runs_on_scanline = extract_pixel_runs_from_scanline(current_scanline_data, RULER_MARK_BINARIZATION_THRESHOLD)
        if not pixel_runs_on_scanline or len(pixel_runs_on_scanline) < MIN_ALTERNATING_MARKS_FOR_SCALE: continue
        for j in range(len(pixel_runs_on_scanline) - (MIN_ALTERNATING_MARKS_FOR_SCALE - 1)):
            if pixel_runs_on_scanline[j]['type'] == 'black':
                initial_mark_width = pixel_runs_on_scanline[j]['width_pixels']
                if not (min_mark_width_px <= initial_mark_width <= max_mark_width_px): continue
                current_valid_sequence_widths = [initial_mark_width]
                is_sequence_valid = True
                for k in range(1, MIN_ALTERNATING_MARKS_FOR_SCALE):
                    prev_mark = pixel_runs_on_scanline[j + k - 1]
                    curr_mark = pixel_runs_on_scanline[j + k]
                    if curr_mark['type'] == prev_mark['type']: is_sequence_valid = False; break
                    mark_width = curr_mark['width_pixels']
                    if not (min_mark_width_px <= mark_width <= max_mark_width_px): is_sequence_valid = False; break
                    if not (abs(mark_width - initial_mark_width) <= initial_mark_width * RULER_MARK_WIDTH_SIMILARITY_TOLERANCE): is_sequence_valid = False; break
                    current_valid_sequence_widths.append(mark_width)
                if is_sequence_valid:
                    average_cm_width = np.mean(current_valid_sequence_widths)
                    candidate_cm_widths_in_pixels.append(average_cm_width)
    if not candidate_cm_widths_in_pixels: raise ValueError("No consistent ruler mark pattern found.")
    estimated_pixels_per_cm = np.median(candidate_cm_widths_in_pixels)
    if estimated_pixels_per_cm <= 1: raise ValueError(f"Estimated px/cm too small: {estimated_pixels_per_cm:.2f}")
    # Return only scale now, width isn't needed directly here anymore
    return float(estimated_pixels_per_cm)


# --- Main Workflow ---
if __name__ == "__main__":
    # --- Initial Checks ---
    if resize_ruler is None: sys.exit("FATAL: Resizing module not loaded.")
    if merge_object_and_ruler is None: sys.exit("FATAL: Merging function not loaded.") # Check renamed function
    if extract_and_save_object is None: sys.exit("FATAL: Object extraction function not loaded.")
    if not os.path.exists(RULER_TEMPLATE_2CM_PATH): sys.exit(f"FATAL: 2cm Ruler Template not found: {RULER_TEMPLATE_2CM_PATH}")
    if not os.path.exists(RULER_TEMPLATE_5CM_PATH): sys.exit(f"FATAL: 5cm Ruler Template not found: {RULER_TEMPLATE_5CM_PATH}")

    # --- Setup Directories ---
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        input_dir = os.path.join(script_dir, INPUT_SUBDIRECTORY_NAME)
        if not os.path.isdir(input_dir): sys.exit(f"FATAL: Input directory not found: {input_dir}")
    except Exception as setup_e:
        sys.exit(f"FATAL: Error setting up directories: {setup_e}")

    # --- Start Processing ---
    print(f"Starting integrated workflow in directory: {input_dir}")
    print(f"Ruler Templates: 2cm='{os.path.basename(RULER_TEMPLATE_2CM_PATH)}', 5cm='{os.path.basename(RULER_TEMPLATE_5CM_PATH)}'")
    print(f"Object Extraction: Background={DEFAULT_TARGET_BACKGROUND_COLOR_BGR}, Feather={DEFAULT_FEATHER_RADIUS_PX}px")
    print("-" * 40)

    total_success_count = 0
    step1_error_count = 0 # Scale detection
    step2_error_count = 0 # Object extraction
    step3_error_count = 0 # Ruler resize
    step4_error_count = 0 # Merge

    # --- Process Each File ---
    for filename in os.listdir(input_dir):
        source_image_filepath = os.path.join(input_dir, filename)

        # --- Skipping Logic ---
        is_valid_input_file = (os.path.isfile(source_image_filepath) and
                               filename.lower().endswith(VALID_IMAGE_EXTENSIONS))
        is_generated_ruler = filename.endswith(resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE + resize_ruler.OUTPUT_FILE_EXTENSION)
        is_generated_merge = filename.endswith("_merged.jpg")
        is_generated_object = filename.endswith(DEFAULT_OUTPUT_FILENAME_SUFFIX)

        if not is_valid_input_file or is_generated_ruler or is_generated_merge or is_generated_object:
            if not os.path.isdir(source_image_filepath) and is_valid_input_file:
                 print(f"Skipping previously generated file: {filename}")
            elif not is_valid_input_file and not os.path.isdir(source_image_filepath):
                 print(f"Skipping file (invalid type or extension): {filename}")
            continue
        # --- End Skipping Logic ---

        print(f"Processing: {filename}")
        pixels_per_centimeter = None
        extracted_object_path = None
        resized_ruler_output_path = None
        output_base_name = ""
        step1_ok = False
        step2_ok = False
        step3_ok = False
        step4_ok = False

        # --- Step 1: Detect Scale from Original Image ---
        try:
            pixels_per_centimeter = estimate_pixels_per_centimeter_from_ruler(source_image_filepath)
            print(f"  Step 1: Detected scale: {pixels_per_centimeter:.2f} px/cm")
            step1_ok = True
        except (FileNotFoundError, ValueError, Exception) as scale_e:
            print(f"  ERROR during Scale Detection (Step 1): {scale_e}")
            step1_error_count += 1
            print("-" * 40)
            continue # Skip to next file if scale detection fails

        # --- Step 2: Extract Object ---
        try:
            extract_and_save_object(source_image_filepath)
            # Construct the expected path for the extracted object
            original_name_part, _ = os.path.splitext(os.path.basename(source_image_filepath))
            output_base_name = original_name_part # Store base name for merge step
            extracted_object_filename = f"{output_base_name}{DEFAULT_OUTPUT_FILENAME_SUFFIX}"
            extracted_object_path = os.path.join(os.path.dirname(source_image_filepath), extracted_object_filename)
            if not os.path.exists(extracted_object_path):
                 raise FileNotFoundError("Extracted object file not found after saving.")
            print(f"  Step 2: Object extraction successful.")
            step2_ok = True
        except (FileNotFoundError, ValueError, IOError, Exception) as extract_e:
            print(f"  ERROR during Object Extraction (Step 2): {extract_e}")
            step2_error_count += 1
            # Continue processing even if object extraction fails, maybe merge original? No, let's stop this file.
            print("-" * 40)
            continue # Skip to next file if object extraction fails

        # --- Step 3: Choose and Resize Ruler (Based on Extracted Object Size) ---
        try:
            # Load extracted object to get its dimensions
            extracted_obj_img = cv2.imread(extracted_object_path)
            if extracted_obj_img is None:
                raise ValueError("Could not reload extracted object image to get dimensions.")
            obj_h, obj_w = extracted_obj_img.shape[:2]

            # Calculate physical width of the *extracted object*
            object_width_cm = obj_w / pixels_per_centimeter if pixels_per_centimeter > 0 else 0
            if object_width_cm <= 0: raise ValueError("Invalid calculated object physical width.")
            print(f"  Step 3a: Extracted object physical width: {object_width_cm:.2f} cm")

            chosen_ruler_template_path = RULER_TEMPLATE_2CM_PATH if object_width_cm < 5.0 else RULER_TEMPLATE_5CM_PATH
            print(f"  Step 3b: Selected ruler template: {os.path.basename(chosen_ruler_template_path)}")

            # Determine expected output path for the resized ruler
            original_dir = os.path.dirname(source_image_filepath)
            if resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH in output_base_name:
                 resized_ruler_name_part = output_base_name.replace(
                     resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH,
                     resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE, 1
                )
            else:
                 resized_ruler_name_part = output_base_name

            expected_ruler_output_filename = resized_ruler_name_part + resize_ruler.OUTPUT_FILE_EXTENSION
            expected_ruler_output_path = os.path.join(original_dir, expected_ruler_output_filename)

            # Perform resizing using original image path for context/naming
            resize_ruler.resize_and_save_ruler(
                pixels_per_centimeter, chosen_ruler_template_path, source_image_filepath
            )
            resized_ruler_output_path = expected_ruler_output_path # Store path if successful
            if not os.path.exists(resized_ruler_output_path):
                 raise FileNotFoundError("Resized ruler file not found after saving.")
            print(f"  Step 3c: Ruler resizing successful.")
            step3_ok = True

        except (FileNotFoundError, ValueError, IOError, Exception) as resize_e:
            print(f"  ERROR during Ruler Resizing (Step 3): {resize_e}")
            step3_error_count += 1
            resized_ruler_output_path = None # Ensure path is None on error

        # --- Step 4: Merge Extracted Object and Scaled Ruler ---
        # Only proceed if previous steps yielding necessary files were successful
        if step1_ok and step2_ok and step3_ok and extracted_object_path and resized_ruler_output_path:
            try:
                merge_object_and_ruler(extracted_object_path, resized_ruler_output_path, output_base_name)
                step4_ok = True
                print(f"  Step 4: Merging successful.")
            except Exception as merge_e:
                print(f"  ERROR during Merge (Step 4): {merge_e}")
                step4_error_count += 1
        elif not (step1_ok and step2_ok and step3_ok):
             print("  Skipping Merge (Step 4) due to previous errors.")
        elif not extracted_object_path:
             print("  Skipping Merge (Step 4): Extracted object path missing.")
             step4_error_count += 1 # Count as error if expected file is missing
        elif not resized_ruler_output_path:
             print("  Skipping Merge (Step 4): Resized ruler path missing.")
             step4_error_count += 1 # Count as error if expected file is missing


        # --- Update Overall Success Count ---
        if step1_ok and step2_ok and step3_ok and step4_ok:
             total_success_count += 1

        print("-" * 40)

    # --- Final Summary ---
    print("\nIntegrated Workflow Summary:")
    print(f"Images fully processed successfully (All Steps OK): {total_success_count}")
    print(f"Errors during Scale Detection (Step 1): {step1_error_count}")
    print(f"Errors during Object Extraction (Step 2): {step2_error_count}")
    print(f"Errors during Ruler Resizing (Step 3): {step3_error_count}")
    print(f"Errors during Merge (Step 4): {step4_error_count}")

