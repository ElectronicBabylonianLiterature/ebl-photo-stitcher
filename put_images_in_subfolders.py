import os
import shutil
import re
from collections import defaultdict

FILENAME_PATTERN_FOR_SUBFOLDERING = re.compile(r"(.+)_(\d+)\.(.+)", re.IGNORECASE)

def group_and_move_files_to_subfolders(source_directory_path):
    if not os.path.isdir(source_directory_path):
        print(f"Error: Source directory '{source_directory_path}' not found.")
        return []

    files_grouped_by_base_name = defaultdict(list)
    matched_files_count = 0
    skipped_files_count = 0

    for item_name in os.listdir(source_directory_path):
        item_full_path = os.path.join(source_directory_path, item_name)
        if os.path.isfile(item_full_path):
            match_result = FILENAME_PATTERN_FOR_SUBFOLDERING.match(item_name)
            if match_result:
                base_name_key = match_result.group(1)
                files_grouped_by_base_name[base_name_key].append(item_full_path)
                matched_files_count += 1
            else:
                skipped_files_count += 1
    
    if not files_grouped_by_base_name:
        print(f"No files in '{source_directory_path}' matched pattern for subfoldering.")
        return []

    processed_subfolder_paths = []
    for base_name_key, list_of_file_paths in files_grouped_by_base_name.items():
        target_subfolder_path = os.path.join(source_directory_path, base_name_key)
        try:
            os.makedirs(target_subfolder_path, exist_ok=True)
            
            for file_path_to_move in list_of_file_paths:
                current_file_name = os.path.basename(file_path_to_move)
                destination_file_path = os.path.join(target_subfolder_path, current_file_name)
                if not (os.path.exists(destination_file_path) and \
                        os.path.samefile(file_path_to_move, destination_file_path)):
                    shutil.move(file_path_to_move, destination_file_path)
            
            if target_subfolder_path not in processed_subfolder_paths:
                 processed_subfolder_paths.append(target_subfolder_path)
        except OSError as os_err:
            print(f"OS Error processing subfolder '{target_subfolder_path}': {os_err}")
        except Exception as general_err:
            print(f"Unexpected error for base name '{base_name_key}': {general_err}")
            
    print(f"File organization: {len(processed_subfolder_paths)} subfolders processed.")
    print(f"  {matched_files_count} files matched pattern; {skipped_files_count} files skipped.")
    return processed_subfolder_paths
