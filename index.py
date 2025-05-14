import os
import sys
import cv2 # Still needed for loading extracted object for width calculation

# --- Import Project Modules ---
try:
    import resize_ruler
    import ruler_detector # For estimate_pixels_per_centimeter_from_ruler
    from image_merger import merge_object_and_ruler
    from object_extractor import extract_and_save_object, DEFAULT_OUTPUT_FILENAME_SUFFIX as OBJECT_SUFFIX
    from raw_processor import convert_cr2_to_tiff
except ImportError as e:
    print(f"ERROR: Failed to import one or more project modules: {e}")
    print("Ensure all .py files (resize_ruler.py, ruler_detector.py, image_merger.py, object_extractor.py, raw_processor.py) are in the same directory or Python path.")
    sys.exit(1)

# --- Configuration (Copied from ruler_detector.py, can be centralized further if needed) ---
# Ruler Detection Config
RULER_ROI_TOP_FRACTION = 0.05 # Copied from ruler_detector settings
RULER_ROI_BOTTOM_FRACTION = 0.25
RULER_ANALYSIS_SCANLINE_COUNT = 7
RULER_MARK_BINARIZATION_THRESHOLD = 150
MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.08
MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.30
RULER_MARK_WIDTH_SIMILARITY_TOLERANCE = 0.40
MIN_ALTERNATING_MARKS_FOR_SCALE = 2

# General Config
INPUT_SUBDIRECTORY_NAME = "Examples"
RULER_TEMPLATE_1CM_PATH = "G:/My Drive/eBL_admin/Photos/BM_1cm_scale.tif"
RULER_TEMPLATE_2CM_PATH = "G:/My Drive/eBL_admin/Photos/BM_2cm_scale.tif"
RULER_TEMPLATE_5CM_PATH = "G:/My Drive/eBL_admin/Photos/BM_5cm_scale.tif"
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp') # CR2 handled separately
RAW_IMAGE_EXTENSION = '.cr2'

# Object Extractor Config (using defaults from object_extractor, can be overridden)
# from object_extractor import DEFAULT_TARGET_BACKGROUND_COLOR_BGR, DEFAULT_FEATHER_RADIUS_PX, etc.
# For this index.py, we'll use the defaults defined in object_extractor.py when calling it.


def main_workflow():
    # --- Initial Checks for Modules and Templates ---
    if not all([resize_ruler, ruler_detector, merge_object_and_ruler, extract_and_save_object, convert_cr2_to_tiff]):
        sys.exit("FATAL: One or more critical modules could not be loaded.")
    if not os.path.exists(RULER_TEMPLATE_1CM_PATH): sys.exit(f"FATAL: 1cm Ruler Template not found: {RULER_TEMPLATE_1CM_PATH}")
    if not os.path.exists(RULER_TEMPLATE_2CM_PATH): sys.exit(f"FATAL: 2cm Ruler Template not found: {RULER_TEMPLATE_2CM_PATH}")
    if not os.path.exists(RULER_TEMPLATE_5CM_PATH): sys.exit(f"FATAL: 5cm Ruler Template not found: {RULER_TEMPLATE_5CM_PATH}")

    # --- Setup Directories ---
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        input_dir = os.path.join(script_dir, INPUT_SUBDIRECTORY_NAME)
        if not os.path.isdir(input_dir): sys.exit(f"FATAL: Input directory not found: {input_dir}")
    except Exception as setup_e:
        sys.exit(f"FATAL: Error setting up directories: {setup_e}")

    print(f"Starting integrated workflow in directory: {input_dir}")
    # Display loaded configurations for clarity
    print(f"Ruler Templates: 1cm, 2cm, 5cm (paths configured)")
    print(f"Object Extraction Suffix: {OBJECT_SUFFIX}")
    print("-" * 50)

    # --- Counters for Summary ---
    files_processed_successfully = 0
    files_with_errors = 0
    cr2_conversions = 0
    
    # --- Process Each File ---
    for filename in os.listdir(input_dir):
        original_filepath = os.path.join(input_dir, filename)
        current_processing_filepath = original_filepath # This might change if CR2 is converted
        is_temp_tiff_from_cr2 = False

        # --- File Type Check and Initial Handling ---
        file_lower = filename.lower()
        if file_lower.endswith(RAW_IMAGE_EXTENSION):
            print(f"Found CR2: {filename}. Attempting conversion to TIFF...")
            base_name_no_ext, _ = os.path.splitext(filename)
            temp_tiff_path = os.path.join(input_dir, f"{base_name_no_ext}_from_cr2.tif")
            try:
                convert_cr2_to_tiff(original_filepath, temp_tiff_path)
                current_processing_filepath = temp_tiff_path
                is_temp_tiff_from_cr2 = True
                cr2_conversions += 1
                print(f"  CR2 conversion successful. Processing: {os.path.basename(temp_tiff_path)}")
            except Exception as cr2_e:
                print(f"  ERROR converting CR2 {filename}: {cr2_e}")
                files_with_errors += 1
                print("-" * 50)
                continue # Skip to next file
        elif not file_lower.endswith(VALID_IMAGE_EXTENSIONS):
            if not os.path.isdir(original_filepath):
                print(f"Skipping unsupported file type: {filename}")
            continue # Skip to next file
        
        # --- Check for already processed files (based on suffixes) ---
        # This check should happen *after* potential CR2 conversion
        current_filename_for_skip_check = os.path.basename(current_processing_filepath)
        if (current_filename_for_skip_check.endswith(resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE + resize_ruler.OUTPUT_FILE_EXTENSION) or
            current_filename_for_skip_check.endswith("_merged.jpg") or
            current_filename_for_skip_check.endswith(OBJECT_SUFFIX)):
            if not is_temp_tiff_from_cr2: # Don't log skip for the temp tiff itself if it matches
                 print(f"Skipping previously generated or intermediate file: {current_filename_for_skip_check}")
            if is_temp_tiff_from_cr2 and os.path.exists(current_processing_filepath):
                # Clean up temporary TIFF if we are skipping due to other generated files
                # This case is less likely if the main output files exist, but good for cleanup
                # os.remove(current_processing_filepath)
                # print(f"  Cleaned up temporary TIFF: {os.path.basename(current_processing_filepath)}")
                pass # Decided to keep temp tiff for now, could be useful for inspection
            continue


        print(f"Processing image: {os.path.basename(current_processing_filepath)}")
        
        # --- Workflow Steps ---
        pixels_per_centimeter = None
        extracted_object_filepath = None
        resized_ruler_filepath = None
        output_base_name_for_merge = os.path.splitext(os.path.basename(original_filepath))[0] # Use original base for final merge name

        try:
            # Step 1: Detect Scale (using current_processing_filepath)
            print("  Step 1: Detecting scale...")
            pixels_per_centimeter = ruler_detector.estimate_pixels_per_centimeter_from_ruler(current_processing_filepath)
            print(f"    Scale detected: {pixels_per_centimeter:.2f} px/cm")

            # Step 2: Extract Object (using current_processing_filepath)
            print("  Step 2: Extracting object...")
            # extract_and_save_object returns the path to the saved object file
            extracted_object_filepath = extract_and_save_object(current_processing_filepath)
            if not extracted_object_filepath or not os.path.exists(extracted_object_filepath):
                raise FileNotFoundError("Extracted object file not created or path not returned.")
            print(f"    Object extracted to: {os.path.basename(extracted_object_filepath)}")

            # Step 3: Choose and Resize Ruler
            print("  Step 3: Choosing and resizing ruler...")
            extracted_obj_img = cv2.imread(extracted_object_filepath)
            if extracted_obj_img is None:
                raise ValueError(f"Could not load extracted object image: {extracted_object_filepath}")
            obj_h, obj_w = extracted_obj_img.shape[:2]
            
            object_width_cm = obj_w / pixels_per_centimeter if pixels_per_centimeter > 0 else 0
            if object_width_cm <= 0: raise ValueError("Invalid calculated object physical width.")
            print(f"    Extracted object physical width: {object_width_cm:.2f} cm")

            threshold_1cm = resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["1cm"]
            threshold_2cm = resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["2cm"]

            if object_width_cm < threshold_1cm:
                chosen_ruler_template_path = RULER_TEMPLATE_1CM_PATH
            elif object_width_cm < threshold_2cm:
                chosen_ruler_template_path = RULER_TEMPLATE_2CM_PATH
            else:
                chosen_ruler_template_path = RULER_TEMPLATE_5CM_PATH
            print(f"    Selected ruler template: {os.path.basename(chosen_ruler_template_path)}")

            # Determine output path for resized ruler (based on original filename)
            ruler_output_dir = os.path.dirname(original_filepath)
            ruler_base_name_part = os.path.splitext(os.path.basename(original_filepath))[0]
            if resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH in ruler_base_name_part:
                 resized_ruler_name_part = ruler_base_name_part.replace(
                     resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH,
                     resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE, 1)
            else:
                 resized_ruler_name_part = ruler_base_name_part
            
            ruler_output_filename = resized_ruler_name_part + resize_ruler.OUTPUT_FILE_EXTENSION
            resized_ruler_filepath = os.path.join(ruler_output_dir, ruler_output_filename)

            # Pass original_filepath to resize_ruler for naming context of the _07.tif
            resize_ruler.resize_and_save_ruler(
                pixels_per_centimeter, chosen_ruler_template_path, original_filepath
            )
            if not os.path.exists(resized_ruler_filepath):
                 raise FileNotFoundError(f"Resized ruler file not found after saving: {resized_ruler_filepath}")
            print(f"    Ruler resized and saved to: {os.path.basename(resized_ruler_filepath)}")

            # Step 4: Merge Extracted Object and Scaled Ruler
            print("  Step 4: Merging object and ruler...")
            merge_object_and_ruler(
                extracted_object_filepath,
                resized_ruler_filepath,
                output_base_name_for_merge # Use original base name for the final _merged.jpg
            )
            print(f"    Merging successful for {output_base_name_for_merge}_merged.jpg")
            
            files_processed_successfully += 1

        except Exception as e:
            print(f"  ERROR processing {os.path.basename(original_filepath)}: {e}")
            files_with_errors += 1
        finally:
            # Clean up temporary TIFF file if one was created from CR2
            if is_temp_tiff_from_cr2 and os.path.exists(current_processing_filepath):
                try:
                    os.remove(current_processing_filepath)
                    print(f"  Cleaned up temporary TIFF: {os.path.basename(current_processing_filepath)}")
                except Exception as clean_e:
                    print(f"  Warning: Could not clean up temporary TIFF {current_processing_filepath}: {clean_e}")
            print("-" * 50)

    # --- Final Summary ---
    print("\nIntegrated Workflow Summary:")
    print(f"CR2 files converted to TIFF: {cr2_conversions}")
    print(f"Images fully processed successfully: {files_processed_successfully}")
    print(f"Images with errors during processing: {files_with_errors}")

if __name__ == "__main__":
    main_workflow()
