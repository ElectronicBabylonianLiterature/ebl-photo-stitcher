"""
This module provides the main function for running the image processing workflow from the GUI.
It uses the refactored workflow implementation behind the scenes.
"""

from workflow.runner import run_complete_image_processing_workflow


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
    museum_selection="British Museum"
):
    print(f"Workflow started for folder: {source_folder_path}")
    progress_callback(2)

    print("Step 0: Organizing images into subfolders...")
    try:
        processed_subfolders = organize_files(source_folder_path)
        if not processed_subfolders and os.path.isdir(source_folder_path) and \
           any(f.lower().endswith(valid_img_exts_config) or f.lower().endswith(raw_ext_config) for f in os.listdir(source_folder_path)):
            processed_subfolders = [source_folder_path]
    except Exception as e:
        print(f"  ERROR file organization: {e}\n--- Halted ---")
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

    for i, subfolder_path_item in enumerate(processed_subfolders):
        subfolder_name_item = os.path.basename(subfolder_path_item)
        print(
            f"Processing Subfolder {i+1}/{num_folders}: {subfolder_name_item}")

        current_prog_base = 10 + i * prog_per_folder
        progress_callback(current_prog_base)

        sub_steps_alloc = {"scale": 0.15, "ruler_art": 0.1, "ruler_part_extract": 0.05,
                           "digital_ruler_choice": 0.05, "digital_ruler_resize": 0.1, "other_obj": 0.3, "stitch": 0.25}
        accumulated_sub_progress = 0.0

        all_files = [f for f in os.listdir(subfolder_path_item) if os.path.isfile(
            os.path.join(subfolder_path_item, f))]
        ruler_for_scale_fp, rel_count = None, 0
        pr02, pr03 = None, None
        orig_views_fps = {}

        for fn in all_files:
            fn_low = fn.lower()
            full_fp = os.path.join(subfolder_path_item, fn)
            if fn_low.endswith(raw_ext_config) or fn_low.endswith(valid_img_exts_config):
                rel_count += 1
                if "_02." in fn:
                    pr02 = full_fp
                if "_03." in fn:
                    pr03 = full_fp
                for vk, sp in view_original_suffix_patterns_config.items():
                    if fn.startswith(subfolder_name_item + sp[:-1]):
                        orig_views_fps[vk] = full_fp
                        break

        if rel_count == 2 and pr02:
            ruler_for_scale_fp = pr02
        elif rel_count >= 6 and pr03:
            ruler_for_scale_fp = pr03
        elif pr02:
            ruler_for_scale_fp = pr02
        elif pr03:
            ruler_for_scale_fp = pr03

        if not ruler_for_scale_fp:
            print(f"  No ruler in {subfolder_name_item}. Skip.")
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
                    subfolder_path_item, f"{os.path.splitext(os.path.basename(path_ruler_extract_img))[0]}_rawextract.tif")
                if not os.path.exists(tmp_ruler_extract_conv_file):
                    convert_raw_image_to_tiff(
                        path_ruler_extract_img, tmp_ruler_extract_conv_file)
                path_ruler_extract_img = tmp_ruler_extract_conv_file            # Use the museum selection to get the appropriate background color
            # The actual background detection for removing backgrounds will still use auto-detection
            # But the output background color will be set based on the museum selection
            output_bg_color = get_museum_background_color(museum_selection=museum_selection)
            
            # Extract the central object with the appropriate background
            art_fp, art_cont = extract_and_save_center_object(
                path_ruler_extract_img, 
                source_background_detection_mode=gui_obj_bg_mode,
                output_image_background_color=output_bg_color,
                output_filename_suffix=object_artifact_suffix_config,
                museum_selection=museum_selection)
            
            accumulated_sub_progress += sub_steps_alloc["ruler_art"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            ruler_loaded_arr = cv2.imread(path_ruler_extract_img)
            if ruler_loaded_arr is None:
                raise ValueError(f"Fail reload {path_ruler_extract_img}")
            bg_rem = (0, 0, 0) if gui_obj_bg_mode != "white" else (
                255, 255, 255)
            all_m = create_foreground_mask(ruler_loaded_arr, bg_rem, 40)
            all_c, _ = cv2.findContours(
                all_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            ruler_c = select_ruler_like_contour(
                all_c, ruler_loaded_arr.shape[1], ruler_loaded_arr.shape[0], excluded_obj_contour=art_cont)

            tmp_iso_ruler_fp = None
            if ruler_c is not None:
                ext_ruler_arr = extract_specific_contour_to_image_array(
                    ruler_loaded_arr, ruler_c, (0, 0, 0), 5)
                tmp_iso_ruler_fp = os.path.join(
                    subfolder_path_item, temp_extracted_ruler_filename_config)
                cv2.imwrite(tmp_iso_ruler_fp, ext_ruler_arr)
            else:
                print("    Warning: Could not isolate physical ruler part.")
            if tmp_ruler_extract_conv_file and os.path.exists(tmp_ruler_extract_conv_file):
                os.remove(tmp_ruler_extract_conv_file)
            accumulated_sub_progress += sub_steps_alloc["ruler_part_extract"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)
            art_img_chk = cv2.imread(art_fp)
            chosen_ruler_tpl = ruler_template_5cm_asset_path
            custom_ruler_size_cm = None
            
            # Handle different museum ruler selections
            if museum_selection == "British Museum":
                # Use British Museum ruler selection logic
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
                # Use Iraq Museum SVG ruler
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "IM_photo_ruler.svg")
                custom_ruler_size_cm = 4.599
                print(f"Using Iraq Museum ruler: {chosen_ruler_tpl}")
            elif museum_selection == "eBL Ruler (CBS)":
                # Use eBL Ruler
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "General_eBL_photo_ruler.svg")
                custom_ruler_size_cm = 4.317
                print(f"Using eBL Ruler (CBS): {chosen_ruler_tpl}")
            elif museum_selection == "Non-eBL Ruler (VAM)":
                # Use Non-eBL Ruler
                chosen_ruler_tpl = os.path.join(os.path.dirname(ruler_template_1cm_asset_path), "General_External_photo_ruler.svg")
                custom_ruler_size_cm = 3.248
                print(f"Using Non-eBL Ruler (VAM): {chosen_ruler_tpl}")
            
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_choice"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

            resize_ruler.resize_and_save_ruler_template(
                px_cm_val, chosen_ruler_tpl, subfolder_name_item, subfolder_path_item, 
                custom_ruler_size_cm=custom_ruler_size_cm)
            if tmp_iso_ruler_fp and os.path.exists(tmp_iso_ruler_fp):
                os.remove(tmp_iso_ruler_fp)
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_resize"] * \
                prog_per_folder
            progress_callback(current_prog_base + accumulated_sub_progress)

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
                        subfolder_path_item, f"{os.path.splitext(os.path.basename(o_fp_to_extract))[0]}_rawobj_other.tif")
                    convert_raw_image_to_tiff(o_fp_to_extract, tmp_o_p)
                    curr_o_path, is_temp_o = tmp_o_p, True
                    cr2_conv_total += 1                # Use the same background settings for all object extractions
                extract_and_save_center_object(
                    curr_o_path, 
                    source_background_detection_mode=gui_obj_bg_mode,
                    output_image_background_color=output_bg_color,
                    output_filename_suffix=object_artifact_suffix_config,
                    museum_selection=museum_selection)
                    
                if is_temp_o and os.path.exists(curr_o_path):
                    os.remove(curr_o_path)
                current_other_views_prog += prog_per_other_view
                progress_callback(
                    current_prog_base + accumulated_sub_progress + current_other_views_prog)
            accumulated_sub_progress += sub_steps_alloc["other_obj"]
              # Get background color from museum configuration
            bg_color = MUSEUM_CONFIGS.get(museum_selection, {}).get("background_color", (0, 0, 0))
            
            process_tablet_subfolder(
                subfolder_path=subfolder_path_item,
                main_input_folder_path=source_folder_path,
                output_base_name=subfolder_name_item,
                pixels_per_cm=px_cm_val,
                photographer_name=gui_photographer,
                ruler_image_for_scale_path=ruler_for_scale_fp,
                add_logo=gui_add_logo,
                logo_path=gui_logo_path if gui_add_logo else None,
                object_extraction_background_mode=gui_obj_bg_mode,  # Use standard mode, setting is now handled internally
                stitched_bg_color=bg_color
                # view_gap_px_override is not passed, so stitch_images.py will use its default
            )
            total_ok += 1
        except Exception as e:
            print(f"  ERROR processing set '{subfolder_name_item}': {e}")
            total_err += 1
        finally:
            progress_callback(current_prog_base + prog_per_folder)
            print("-" * 40)

    print(
        f"\n--- Processing Complete ---\nRAW converted: {cr2_conv_total}\nSets OK: {total_ok}\nSets Error: {total_err}\n")
    progress_callback(100)
    finished_callback()
