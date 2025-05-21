import os
import sys
import cv2
import tkinter as tk 
import re 
import traceback # Added for error printing

try:
    import resize_ruler
    import ruler_detector
    from stitch_images_adapter import process_tablet_subfolder
    from stitch_config import MUSEUM_CONFIGS
    from object_extractor import extract_and_save_center_object, extract_specific_contour_to_image_array
    from remove_background import (
        create_foreground_mask_from_background as create_foreground_mask,
        select_contour_closest_to_image_center,
        select_ruler_like_contour_from_list as select_ruler_like_contour,
        get_museum_background_color, 
        detect_dominant_corner_background_color 
    )
    from raw_processor import convert_raw_image_to_tiff
    from put_images_in_subfolders import group_and_move_files_to_subfolders as organize_files_func # Renamed for clarity
    import ruler_detector_iraq_museum
    # Import new helper functions
    from workflow_processing_steps import organize_project_subfolders, determine_ruler_image_for_scaling
except ImportError as e:
    print(
        f"ERROR in gui_workflow_runner.py: Failed to import a processing module: {e}")
    def _placeholder_func(
        *args, **kwargs): print(f"Error: Missing module for {args[0] if args else 'operation'}")
    resize_ruler = type(
        'module', (), {'resize_and_save_ruler_template': _placeholder_func})
    ruler_detector = type(
        'module', (), {'estimate_pixels_per_centimeter_from_ruler': _placeholder_func})
    process_tablet_subfolder = _placeholder_func
    extract_and_save_center_object = lambda *a, **kw: (None, None)
    extract_specific_contour_to_image_array = _placeholder_func
    create_foreground_mask = _placeholder_func
    select_contour_closest_to_image_center = _placeholder_func
    select_ruler_like_contour = _placeholder_func
    convert_raw_image_to_tiff = _placeholder_func
    organize_files_func = lambda *a: [] # Placeholder for the renamed import
    organize_project_subfolders = lambda *a, **kw: []
    determine_ruler_image_for_scaling = lambda *a, **kw: None
    detect_dominant_corner_background_color = lambda *a, **kw: (0,0,0) # Placeholder for new import

def run_complete_image_processing_workflow(
    source_folder_path, gui_ruler_position, gui_photographer,
    gui_obj_bg_mode, gui_add_logo, gui_logo_path,
    raw_ext_config, valid_img_exts_config,
    ruler_template_1cm_asset_path,
    ruler_template_2cm_asset_path,
    ruler_template_5cm_asset_path,
    view_original_suffix_patterns_config,
    temp_extracted_ruler_filename_config,
    object_artifact_suffix_config,
    progress_callback,
    finished_callback,
    museum_selection="British Museum",
    app_root_window=None,
    app_instance=None  # Add this parameter to access the processing_running flag
):
    from lib.complex_layout_main import ComplexLayoutDialog

    print(f"Workflow started for folder: {source_folder_path}")
    progress_callback(2)

    # Prepare all image extensions for checking
    image_extensions_tuple = tuple(ext.lower() for ext in valid_img_exts_config) + \
                           ((raw_ext_config.lower(),) if isinstance(raw_ext_config, str) else tuple(r_ext.lower() for r_ext in raw_ext_config))

    try:
        processed_subfolders = organize_project_subfolders(source_folder_path, image_extensions_tuple, organize_files_func)
    except Exception as e_org:
        # If organize_project_subfolders re-raises, it's caught here.
        print(f"   Workflow halted due to error during file organization: {e_org}")
        progress_callback(100)
        finished_callback()
        return

    num_folders = len(processed_subfolders)
    print(f"File organization complete. Targeting {num_folders} subfolder(s).")
    progress_callback(10)
    print("-" * 50)

    if num_folders == 0:
        print("No image sets to process.")
        progress_callback(100)
        finished_callback()
        return

    total_ok, total_err, cr2_conv_total = 0, 0, 0
    prog_per_folder = 85.0 / num_folders if num_folders > 0 else 0

    # The main loop for subfolders - add check after each subfolder
    for i, subfolder_path_item in enumerate(processed_subfolders):
        # Check if processing should stop
        if app_instance and not app_instance.processing_running:
            print("Processing stopped by user.")
            finished_callback()
            return
            
        subfolder_name_item = os.path.basename(subfolder_path_item)
        print(
            f"Processing Subfolder {i+1}/{num_folders}: {subfolder_name_item}")

        current_prog_base = 10 + i * prog_per_folder
        progress_callback(current_prog_base)

        sub_steps_alloc = {"layout_dialog": 0.05, "scale": 0.15, "ruler_art": 0.1, "ruler_part_extract": 0.05,
                           "digital_ruler_choice": 0.05, "digital_ruler_resize": 0.1, "other_obj": 0.25, "stitch": 0.25}
        accumulated_sub_progress = 0.0

        all_files_in_subfolder = [f for f in os.listdir(subfolder_path_item) if os.path.isfile(
            os.path.join(subfolder_path_item, f))]
        
        image_files_for_layout = []
        for f_name in all_files_in_subfolder:
            if f_name.lower().endswith(image_extensions_tuple):
                image_files_for_layout.append(os.path.join(subfolder_path_item, f_name))
        
        custom_layout_config = None
        typical_counts = [1, 2, 6] 
        if len(image_files_for_layout) not in typical_counts and len(image_files_for_layout) > 0:
            print(f"   Subfolder {subfolder_name_item} has {len(image_files_for_layout)} images, prompting for custom layout.")
            root_tk_window = app_root_window
            if not root_tk_window: 
                if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'redirector') and hasattr(sys.stdout.redirector, 'widget'):
                    widget = sys.stdout.redirector.widget
                    if widget:
                        try:
                            root_tk_window = widget.winfo_toplevel()
                        except tk.TclError:
                            pass 
            
            if root_tk_window:
                try:
                    # Properly create and wait for the dialog
                    dialog = ComplexLayoutDialog(parent=root_tk_window, image_paths=image_files_for_layout)
                    
                    # Use grab_set to make the dialog modal
                    dialog.grab_set()
                    
                    # Wait for the dialog to be complete
                    root_tk_window.wait_variable(dialog.result_ready_var)
                    
                    # Get the result
                    custom_layout_config = dialog.get_layout_config()
                    
                    if custom_layout_config:
                        print(f"   Custom layout defined for {subfolder_name_item}")
                    else:
                        print(f"   Custom layout cancelled for {subfolder_name_item}.")
                except Exception as e:
                    print(f"   Error showing complex layout dialog: {e}")
                    custom_layout_config = None
                    
        accumulated_sub_progress += sub_steps_alloc["layout_dialog"] * prog_per_folder
        progress_callback(current_prog_base + accumulated_sub_progress)

        rel_count = 0
        pr02_reverse, pr03_top, pr04_bottom = None, None, None
        orig_views_fps = {}

        for fn in all_files_in_subfolder: 
            fn_low = fn.lower()
            full_fp = os.path.join(subfolder_path_item, fn)
            if fn_low.endswith(image_extensions_tuple): 
                if object_artifact_suffix_config not in fn and \
                   "_scaled_ruler." not in fn and \
                   "temp_isolated_ruler" not in fn and \
                   not fn_low.endswith("_rawscale.tif"): 
                    rel_count += 1

                if "reverse" in view_original_suffix_patterns_config and view_original_suffix_patterns_config["reverse"] in fn_low:
                    pr02_reverse = full_fp
                if "top" in view_original_suffix_patterns_config and view_original_suffix_patterns_config["top"] in fn_low:
                    pr03_top = full_fp
                if "bottom" in view_original_suffix_patterns_config and view_original_suffix_patterns_config["bottom"] in fn_low:
                    pr04_bottom = full_fp
                
                for vk, sp_pattern_suffix in view_original_suffix_patterns_config.items():
                    if not sp_pattern_suffix: 
                        continue
                    core_pattern = os.path.splitext(sp_pattern_suffix)[0] 
                    expected_prefix_in_filename = subfolder_name_item + core_pattern
                    
                    if fn_low.startswith(expected_prefix_in_filename.lower()):
                         orig_views_fps[vk] = full_fp

        ruler_for_scale_fp = determine_ruler_image_for_scaling(
            custom_layout_config, orig_views_fps, image_files_for_layout, 
            pr02_reverse, pr03_top, pr04_bottom, rel_count
        )

        if not ruler_for_scale_fp:
            print(f"   No ruler image found for {subfolder_name_item}. Skip.")
            total_err += 1
            print("-"*40)
            continue

        try:
            curr_scale_fp, is_temp_s_file = ruler_for_scale_fp, False
            if curr_scale_fp.lower().endswith(raw_ext_config):
                tmp_s_fp = os.path.join(
                    subfolder_path_item, f"{os.path.splitext(os.path.basename(curr_scale_fp))[0]}_rawscale.tif")
                convert_raw_image_to_tiff(curr_scale_fp, tmp_s_fp)
                curr_scale_fp, is_temp_s_file = tmp_s_fp, True
                cr2_conv_total += 1

            if museum_selection == "Iraq Museum":
                print(f"   Using Iraq Museum specific ruler detector for {os.path.basename(curr_scale_fp)}...")
                px_cm_val = ruler_detector_iraq_museum.detect_1cm_distance_iraq(curr_scale_fp)
                if px_cm_val is None or px_cm_val <= 0:
                    raise ValueError("Iraq Museum ruler detection failed to return a valid pixels/cm value.")
                print(f"     Iraq Museum ruler detector returned px/cm: {px_cm_val}")
            else:
                px_cm_val = ruler_detector.estimate_pixels_per_centimeter_from_ruler(
                    curr_scale_fp, ruler_position=gui_ruler_position)
            
            if is_temp_s_file and os.path.exists(curr_scale_fp):
                os.remove(curr_scale_fp)
            accumulated_sub_progress += sub_steps_alloc["scale"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            path_ruler_extract_img, tmp_ruler_extract_conv_file = ruler_for_scale_fp, None
            if path_ruler_extract_img.lower().endswith(raw_ext_config):
                tmp_ruler_extract_conv_file = os.path.join(
                    subfolder_path_item, f"{os.path.splitext(os.path.basename(path_ruler_extract_img))[0]}.tif")
                if not os.path.exists(tmp_ruler_extract_conv_file):
                    convert_raw_image_to_tiff(
                        path_ruler_extract_img, tmp_ruler_extract_conv_file)
                path_ruler_extract_img = tmp_ruler_extract_conv_file
            
            img_for_bg_detection = cv2.imread(path_ruler_extract_img)
            if img_for_bg_detection is None:
                raise ValueError(f"Failed to load image for background detection: {path_ruler_extract_img}")
            
            detected_bg_color_from_image = detect_dominant_corner_background_color(img_for_bg_detection)
            
            output_bg_color = get_museum_background_color(museum_selection=museum_selection, detected_bg_color=detected_bg_color_from_image)
            
            art_fp, art_cont = extract_and_save_center_object(
                path_ruler_extract_img, 
                source_background_detection_mode=gui_obj_bg_mode, 
                output_image_background_color=output_bg_color,
                output_filename_suffix=object_artifact_suffix_config,
                museum_selection=museum_selection
            )
            
            accumulated_sub_progress += sub_steps_alloc["ruler_art"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            ruler_loaded_arr = cv2.imread(path_ruler_extract_img)
            if ruler_loaded_arr is None:
                raise ValueError(f"Fail reload {path_ruler_extract_img}")
            
            all_m = create_foreground_mask(ruler_loaded_arr, detected_bg_color_from_image, 40)
            all_c, _ = cv2.findContours(
                all_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            ruler_c = select_ruler_like_contour(
                all_c, ruler_loaded_arr.shape[1], ruler_loaded_arr.shape[0], excluded_obj_contour=art_cont)

            tmp_iso_ruler_fp = None
            if ruler_c is not None:
                ext_ruler_arr = extract_specific_contour_to_image_array(
                    ruler_loaded_arr, ruler_c, detected_bg_color_from_image, 5) 
                tmp_iso_ruler_fp = os.path.join(
                    subfolder_path_item, temp_extracted_ruler_filename_config)
                cv2.imwrite(tmp_iso_ruler_fp, ext_ruler_arr)
            else:
                print("     Warning: Could not isolate physical ruler part.")
            if tmp_ruler_extract_conv_file and os.path.exists(tmp_ruler_extract_conv_file):
                os.remove(tmp_ruler_extract_conv_file)
            accumulated_sub_progress += sub_steps_alloc["ruler_part_extract"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)
            
            art_img_chk = cv2.imread(art_fp)
            chosen_ruler_tpl = ruler_template_5cm_asset_path
            custom_ruler_size_cm = None
            
            if museum_selection == "British Museum":
                if art_img_chk is not None and px_cm_val > 0:
                    art_w_cm_val = art_img_chk.shape[1] / px_cm_val
                    if art_w_cm_val > 0:
                        t1 = resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["1cm"]
                        t2 = resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["2cm"]
                        if art_w_cm_val < t1:
                            chosen_ruler_tpl = ruler_template_1cm_asset_path
                        elif art_w_cm_val < t2:
                            chosen_ruler_tpl = ruler_template_2cm_asset_path
            elif museum_selection == "Iraq Museum":
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "IM_photo_ruler.svg")
                custom_ruler_size_cm = 4.599
                print(f"Using Iraq Museum ruler: {chosen_ruler_tpl}")
            elif museum_selection == "eBL Ruler (CBS)":
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "General_eBL_photo_ruler.svg")
                custom_ruler_size_cm = 4.317
                print(f"Using eBL Ruler (CBS): {chosen_ruler_tpl}")
            elif museum_selection == "Non-eBL Ruler (VAM)":
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "General_External_photo_ruler.svg")
                custom_ruler_size_cm = 3.248
                print(f"Using Non-eBL Ruler (VAM): {chosen_ruler_tpl}")
            
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_choice"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            try:
                resize_ruler.resize_and_save_ruler_template(
                    px_cm_val, 
                    chosen_ruler_tpl, 
                    subfolder_name_item, 
                    subfolder_path_item, 
                    custom_ruler_size_cm=custom_ruler_size_cm
                )
                print(f"    Successfully generated/resized digital ruler: {chosen_ruler_tpl} for {subfolder_name_item}.")
            except Exception as e_ruler_gen:
                print(f"    ERROR during digital ruler generation/resizing: {e_ruler_gen}")

            if tmp_iso_ruler_fp and os.path.exists(tmp_iso_ruler_fp):
                os.remove(tmp_iso_ruler_fp)
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_resize"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            other_views_to_process_list = []
            if custom_layout_config:
                all_custom_assigned_paths = set()
                for key, value in custom_layout_config.items():
                    if isinstance(value, str) and value: 
                        all_custom_assigned_paths.add(value)
                    elif isinstance(value, list):
                        for item_path in value:
                            if item_path: all_custom_assigned_paths.add(item_path)
                
                other_views_to_process_list = [p for p in all_custom_assigned_paths if p != ruler_for_scale_fp]
            else:
                other_views_to_process_list = [
                    fp_other for fp_other in orig_views_fps.values() if fp_other != ruler_for_scale_fp]
            
            num_other_views = len(other_views_to_process_list)
            prog_per_other_view = (
                sub_steps_alloc["other_obj"] * prog_per_folder) / num_other_views if num_other_views > 0 else 0
            current_other_views_prog = 0.0

            for idx_other, o_fp_to_extract in enumerate(other_views_to_process_list):
                curr_o_path, is_temp_o = o_fp_to_extract, False
                if o_fp_to_extract.lower().endswith(raw_ext_config):
                    tmp_o_p = os.path.join(
                        subfolder_path_item, f"{os.path.splitext(os.path.basename(o_fp_to_extract))[0]}.tif")
                    convert_raw_image_to_tiff(o_fp_to_extract, tmp_o_p)
                    curr_o_path, is_temp_o = tmp_o_p, True
                    cr2_conv_total += 1
                extract_and_save_center_object(
                    curr_o_path, 
                    source_background_detection_mode=gui_obj_bg_mode,
                    output_image_background_color=output_bg_color, 
                    output_filename_suffix=object_artifact_suffix_config,
                    museum_selection=museum_selection
                )
                    
                if is_temp_o and os.path.exists(curr_o_path):
                    os.remove(curr_o_path)
                current_other_views_prog += prog_per_other_view
                progress_callback(
                    current_prog_base + accumulated_sub_progress + current_other_views_prog)
            accumulated_sub_progress += sub_steps_alloc["other_obj"] * prog_per_folder 
            
            stitched_output_bg_color = MUSEUM_CONFIGS.get(museum_selection, {}).get("background_color", (0, 0, 0))
            if museum_selection == "British Museum": 
                stitched_output_bg_color = output_bg_color

            process_tablet_subfolder(
                subfolder_path=subfolder_path_item,
                main_input_folder_path=source_folder_path,
                output_base_name=subfolder_name_item,
                pixels_per_cm=px_cm_val,
                photographer_name=gui_photographer,
                ruler_image_for_scale_path=ruler_for_scale_fp, 
                add_logo=gui_add_logo,
                logo_path=gui_logo_path if gui_add_logo else None,
                object_extraction_background_mode=gui_obj_bg_mode, 
                stitched_bg_color=stitched_output_bg_color, 
                custom_layout=custom_layout_config 
            )
            total_ok += 1
        except Exception as e:
            print(f"   ERROR processing set '{subfolder_name_item}': {e}")
            traceback.print_exc() # Add this to print the full traceback
            total_err += 1
        finally:
            progress_callback(current_prog_base + prog_per_folder)
            print("-" * 40)

    print(
        f"\n--- Processing Complete ---\nRAW converted: {cr2_conv_total}\nSets OK: {total_ok}\nSets Error: {total_err}\n")
    progress_callback(100)
    finished_callback()