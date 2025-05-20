import os
import re # Keep re for image_extensions tuple creation if needed by caller
from typing import List, Dict, Optional # ADDED IMPORT

def organize_project_subfolders(source_folder_path: str, image_extensions: tuple, organize_files_func) -> List[str]:
    """
    Checks for existing subfolders or organizes images into subfolders.
    Returns a list of paths to processable subfolders.
    """
    print("Step 0: Checking for existing subfolders or organizing images...")
    processed_subfolders = []

    images_in_root = False
    if os.path.isdir(source_folder_path):
        for item in os.listdir(source_folder_path):
            if os.path.isfile(os.path.join(source_folder_path, item)) and item.lower().endswith(image_extensions):
                images_in_root = True
                break
    
    subfolders_with_images = []
    if os.path.isdir(source_folder_path):
        potential_subdirs = [d for d in os.listdir(source_folder_path) if os.path.isdir(os.path.join(source_folder_path, d))]
        for subdir_name in potential_subdirs:
            subdir_path = os.path.join(source_folder_path, subdir_name)
            has_images = False
            for item in os.listdir(subdir_path):
                if os.path.isfile(os.path.join(subdir_path, item)) and item.lower().endswith(image_extensions):
                    has_images = True
                    break
            if has_images:
                subfolders_with_images.append(subdir_path)

    if not images_in_root and subfolders_with_images:
        print(f"   No images in root, but found {len(subfolders_with_images)} subfolder(s) with images. Skipping file organization step.")
        processed_subfolders = subfolders_with_images
    else:
        if images_in_root:
            print("   Images found in root folder. Running file organization...")
        elif not subfolders_with_images: # No images in root AND no subfolders with images
            print("   No images in root and no subfolders with images found. Running file organization...")
        # If images_in_root and subfolders_with_images, organization will also run.
        
        try:
            organized_paths = organize_files_func(source_folder_path)
            processed_subfolders = [os.path.join(source_folder_path, p) if not os.path.isabs(p) else p for p in organized_paths]
            
            if not processed_subfolders and images_in_root:
                print("   Organize_files returned no subfolders, but source folder contains images. Treating source as a single set.")
                processed_subfolders = [source_folder_path]
            elif not processed_subfolders and not images_in_root and not subfolders_with_images:
                print("   No image sets found after attempting organization.")
        except Exception as e:
            print(f"   ERROR during file organization: {e}")
            # Re-raise or handle as appropriate for the workflow to stop
            raise # Or return an empty list and let the caller handle
            
    return processed_subfolders

def determine_ruler_image_for_scaling(
    custom_layout_config: Optional[Dict], 
    orig_views_fps: dict, 
    image_files_for_layout: List, 
    pr02_reverse: Optional[str], 
    pr03_top: Optional[str], 
    pr04_bottom: Optional[str], 
    rel_count: int 
) -> Optional[str]:
    """Determines the file path of the image to be used for ruler scale detection."""
    ruler_for_scale_fp = None
    if custom_layout_config:
        if custom_layout_config.get("obverse"):
            ruler_for_scale_fp = custom_layout_config["obverse"]
        elif custom_layout_config.get("reverse"):
            ruler_for_scale_fp = custom_layout_config["reverse"]
        elif custom_layout_config.get("bottom"): # Typically, ruler is on obv, rev, or bottom
            ruler_for_scale_fp = custom_layout_config["bottom"]
        
        if not ruler_for_scale_fp: # If not found in primary slots, check any assigned image
            for view_designation, path_or_list in custom_layout_config.items():
                if isinstance(path_or_list, str) and os.path.exists(path_or_list):
                    ruler_for_scale_fp = path_or_list
                    print(f"   INFO: Using '{view_designation}' image from custom layout as ruler image (first available).")
                    break
                elif isinstance(path_or_list, list):
                    for item_path in path_or_list:
                        if os.path.exists(item_path):
                            ruler_for_scale_fp = item_path
                            print(f"   INFO: Using first image from '{view_designation}' list in custom layout as ruler image.")
                            break
                if ruler_for_scale_fp: break
        
        if not ruler_for_scale_fp and image_files_for_layout:
            ruler_for_scale_fp = image_files_for_layout[0]
            print(f"   WARNING: No specific ruler image identifiable from custom layout. Using first available image: {os.path.basename(ruler_for_scale_fp)} for scaling. This may be incorrect.")

    if not ruler_for_scale_fp: # Standard logic if no custom layout or custom layout didn't specify
        if rel_count == 2 and pr02_reverse:
            ruler_for_scale_fp = pr02_reverse
        elif rel_count >= 6 and pr03_top:
            ruler_for_scale_fp = pr03_top
        elif pr02_reverse:
            ruler_for_scale_fp = pr02_reverse
        elif pr03_top:
            ruler_for_scale_fp = pr03_top
        elif pr04_bottom:
            ruler_for_scale_fp = pr04_bottom
        elif orig_views_fps:
            ruler_for_scale_fp = (
                orig_views_fps.get("obverse") or
                orig_views_fps.get("reverse") or
                orig_views_fps.get("top") or
                orig_views_fps.get("bottom") or
                next(iter(orig_views_fps.values()), None)
            )
        
        if not ruler_for_scale_fp and image_files_for_layout:
            ruler_for_scale_fp = image_files_for_layout[0]
            print(f"   WARNING: Could not determine ruler image by standard patterns. Using first image found: {os.path.basename(ruler_for_scale_fp)} for scaling. This may be incorrect.")
            
    return ruler_for_scale_fp

