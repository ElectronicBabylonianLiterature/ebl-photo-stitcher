import os
import cv2
try:
    from image_utils import convert_to_bgr_if_needed
except ImportError:
    print("FATAL ERROR: stitch_file_utils.py cannot import from image_utils.py")
    def convert_to_bgr_if_needed(img): return img # Fallback

OBJECT_FILE_SUFFIX = "_object.tif"
SCALED_RULER_FILE_SUFFIX = "_07.tif" # Assuming this is the final scaled ruler

def find_processed_image_file(subfolder_path, base_name, view_specific_part, general_suffix):
    target_filename = f"{base_name}{view_specific_part}{general_suffix}"
    path = os.path.join(subfolder_path, target_filename)
    if os.path.exists(path): return path
    if view_specific_part.startswith("_0") and len(view_specific_part) == 3: # e.g., "_01"
        alt_part = "_" + view_specific_part[2] # e.g., "_1"
        alt_filename = f"{base_name}{alt_part}{general_suffix}"
        alt_path = os.path.join(subfolder_path, alt_filename)
        if os.path.exists(alt_path): return alt_path
    return None

def load_images_for_stitching_process(subfolder_path, image_base_name, view_to_file_pattern_map):
    loaded_image_arrays = {}
    all_files_in_directory = os.listdir(subfolder_path) 

    for view_name_key, filename_pattern_part in view_to_file_pattern_map.items():
        image_file_path = None
        if view_name_key == "ruler":
            # Ruler uses a different naming convention: base_name + _07.tif
            image_file_path = find_processed_image_file(subfolder_path, image_base_name, "", SCALED_RULER_FILE_SUFFIX)
        else:
            # Views are expected as: base_name + view_pattern_part + _object.tif
            image_file_path = find_processed_image_file(subfolder_path, image_base_name, filename_pattern_part, OBJECT_FILE_SUFFIX)
        
        current_image_array = None
        if image_file_path and os.path.exists(image_file_path):
            raw_image_array = cv2.imread(image_file_path, cv2.IMREAD_UNCHANGED)
            if raw_image_array is not None:
                current_image_array = convert_to_bgr_if_needed(raw_image_array) 
                if current_image_array is not None:
                    print(f"      Stitch - Loaded {view_name_key}: {os.path.basename(image_file_path)}")
                else:
                    # This case implies convert_to_bgr_if_needed returned None or failed for a valid image
                    print(f"      Warn: Stitch - Failed to convert/process {view_name_key} from {image_file_path}")
            else:
                print(f"      Warn: Stitch - Failed to load {view_name_key} from {image_file_path}")
        else:
            # This means find_processed_image_file returned None or the path didn't exist
            print(f"      Warn: Stitch - {view_name_key} file not found (expected pattern part: {filename_pattern_part})")
        loaded_image_arrays[view_name_key] = current_image_array
    return loaded_image_arrays
