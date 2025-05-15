import os
import sys
import cv2 

try:
    import resize_ruler # Module itself
    import ruler_detector
    from stitch_images import process_tablet_subfolder
    from object_extractor import extract_and_save_center_object, extract_specific_contour_to_image_array
    from remove_background import (
        create_foreground_mask_from_background as create_foreground_mask, 
        select_contour_closest_to_image_center, 
        select_ruler_like_contour_from_list as select_ruler_like_contour
    )
    from raw_processor import convert_raw_image_to_tiff 
    from put_images_in_subfolders import group_and_move_files_to_subfolders as organize_files
except ImportError as e:
    print(f"ERROR in gui_workflow_runner.py: Failed to import a processing module: {e}")
    def _placeholder_func(*args, **kwargs): print(f"Error: Missing module for {args[0] if args else 'operation'}")
    resize_ruler = type('module', (), {'resize_and_save_ruler_template': _placeholder_func})
    ruler_detector = type('module', (), {'estimate_pixels_per_centimeter_from_ruler': _placeholder_func})
    process_tablet_subfolder = _placeholder_func; extract_and_save_center_object = lambda *a, **kw: (None, None)
    extract_specific_contour_to_image_array = _placeholder_func; create_foreground_mask = _placeholder_func
    select_contour_closest_to_image_center = _placeholder_func; select_ruler_like_contour = _placeholder_func
    convert_raw_image_to_tiff = _placeholder_func; organize_files = lambda *a: []

def run_complete_image_processing_workflow(
    source_folder_path, gui_ruler_position, gui_photographer,
    gui_obj_bg_mode, gui_add_logo, gui_logo_path,
    raw_ext_config, valid_img_exts_config, 
    ruler_template_1cm_asset_path, 
    ruler_template_2cm_asset_path, 
    ruler_template_5cm_asset_path,
    view_original_suffix_patterns_config, 
    temp_extracted_ruler_filename_config, # This is "temp_isolated_ruler.tif"
    object_artifact_suffix_config,
    progress_callback, 
    finished_callback
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
        print(f"  ERROR file organization: {e}\n--- Halted ---"); progress_callback(100); finished_callback(); return
    
    num_folders = len(processed_subfolders)
    print(f"File organization complete. Targeting {num_folders} subfolder(s).")
    progress_callback(10); print("-" * 50)

    if num_folders == 0: print("No image sets to process."); progress_callback(100); finished_callback(); return

    total_ok, total_err, cr2_conv_total = 0, 0, 0
    prog_per_folder = 85.0 / num_folders if num_folders > 0 else 0


    for i, subfolder_path_item in enumerate(processed_subfolders):
        subfolder_name_item = os.path.basename(subfolder_path_item)
        print(f"Processing Subfolder {i+1}/{num_folders}: {subfolder_name_item}")
        
        current_prog_base = 10 + i * prog_per_folder
        progress_callback(current_prog_base)
        
        sub_steps_alloc = {"scale":0.15,"ruler_art":0.1,"ruler_part_extract":0.05, "digital_ruler_choice":0.05, "digital_ruler_resize":0.1,"other_obj":0.3,"stitch":0.25}
        accumulated_sub_progress = 0
        
        all_files = [f for f in os.listdir(subfolder_path_item) if os.path.isfile(os.path.join(subfolder_path_item, f))]
        ruler_for_scale_fp, rel_count = None, 0; pr02, pr03 = None, None; orig_views_fps = {}

        for fn in all_files:
            fn_low = fn.lower(); full_fp = os.path.join(subfolder_path_item, fn)
            if fn_low.endswith(raw_ext_config) or fn_low.endswith(valid_img_exts_config):
                rel_count +=1
                if "_02." in fn: pr02 = full_fp
                if "_03." in fn: pr03 = full_fp
                for vk, sp in view_original_suffix_patterns_config.items():
                    if fn.startswith(subfolder_name_item + sp[:-1]): orig_views_fps[vk] = full_fp; break
        
        if rel_count == 2 and pr02: ruler_for_scale_fp = pr02
        elif rel_count >= 6 and pr03: ruler_for_scale_fp = pr03
        elif pr02: ruler_for_scale_fp = pr02
        elif pr03: ruler_for_scale_fp = pr03

        if not ruler_for_scale_fp: print(f"  No ruler in {subfolder_name_item}. Skip."); total_err+=1; print("-"*40); continue
        
        try:
            curr_scale_fp, is_temp_s_file = ruler_for_scale_fp, False
            if curr_scale_fp.lower().endswith(raw_ext_config):
                tmp_s_fp=os.path.join(subfolder_path_item,f"{os.path.splitext(os.path.basename(curr_scale_fp))[0]}_rawscale.tif")
                convert_raw_image_to_tiff(curr_scale_fp,tmp_s_fp); curr_scale_fp,is_temp_s_file=tmp_s_fp,True; cr2_conv_total+=1
            
            px_cm_val = ruler_detector.estimate_pixels_per_centimeter_from_ruler(curr_scale_fp, ruler_position=gui_ruler_position)
            if is_temp_s_file and os.path.exists(curr_scale_fp): os.remove(curr_scale_fp)
            accumulated_sub_progress += sub_steps_alloc["scale"]; progress_callback(current_prog_base + accumulated_sub_progress)

            path_ruler_extract_img, tmp_ruler_extract_conv_file = ruler_for_scale_fp, None
            if path_ruler_extract_img.lower().endswith(raw_ext_config):
                tmp_ruler_extract_conv_file=os.path.join(subfolder_path_item,f"{os.path.splitext(os.path.basename(path_ruler_extract_img))[0]}_rawextract.tif")
                if not os.path.exists(tmp_ruler_extract_conv_file): convert_raw_image_to_tiff(path_ruler_extract_img,tmp_ruler_extract_conv_file)
                path_ruler_extract_img = tmp_ruler_extract_conv_file
            
            art_fp, art_cont = extract_and_save_center_object(path_ruler_extract_img, output_filename_suffix=object_artifact_suffix_config)
            accumulated_sub_progress += sub_steps_alloc["ruler_art"]; progress_callback(current_prog_base + accumulated_sub_progress)
            
            # Extract physical ruler part (still needed if you want to analyze it, but not for the _07.tif)
            ruler_loaded_arr = cv2.imread(path_ruler_extract_img)
            if ruler_loaded_arr is None: raise ValueError(f"Fail reload {path_ruler_extract_img}")
            bg_rem = (0,0,0) if gui_obj_bg_mode != "white" else (255,255,255)
            all_m = create_foreground_mask(ruler_loaded_arr, bg_rem, 40)
            all_c, _ = cv2.findContours(all_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            ruler_c = select_ruler_like_contour(all_c, ruler_loaded_arr.shape[1], ruler_loaded_arr.shape[0], excluded_obj_contour=art_cont)
            
            # This temp_iso_ruler_path is the extracted physical ruler part.
            # It is NO LONGER used as the input to resize_and_save_ruler_template for the _07.tif
            if ruler_c is not None:
                extracted_ruler_arr = extract_specific_contour_to_image_array(ruler_loaded_arr, ruler_c, (0,0,0), 5)
                temp_iso_ruler_path = os.path.join(subfolder_path_item, temp_extracted_ruler_filename_config)
                cv2.imwrite(temp_iso_ruler_path, extracted_ruler_arr)
                print(f"    Physical ruler part extracted to: {temp_iso_ruler_path} (for potential analysis, not for _07.tif)")
                # This temp_iso_ruler_path could be deleted later if not used by stitch_images
            else:
                print("    Warning: Could not isolate physical ruler part from ruler image.")
            if tmp_ruler_extract_conv_file and os.path.exists(tmp_ruler_extract_conv_file): os.remove(tmp_ruler_extract_conv_file)
            accumulated_sub_progress += sub_steps_alloc["ruler_part_extract"]; progress_callback(current_prog_base + accumulated_sub_progress)


            # Choose which DIGITAL BM_Xcm_scale.tif template to use
            art_img_check = cv2.imread(art_fp) # Artifact from the physical ruler image
            chosen_digital_template_asset_path = ruler_template_5cm_asset_path 
            if art_img_check is not None and px_cm_val > 0:
                art_w_cm_val = art_img_check.shape[1] / px_cm_val
                if art_w_cm_val > 0:
                     t1=resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["1cm"]; t2=resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["2cm"]; t5=resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["5cm"]
                     if art_w_cm_val < t2: chosen_digital_template_asset_path = ruler_template_1cm_asset_path
                     elif art_w_cm_val < t5: chosen_digital_template_asset_path = ruler_template_2cm_asset_path
            print(f"    Chosen digital template for scaling: {os.path.basename(chosen_digital_template_asset_path)}")
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_choice"]; progress_callback(current_prog_base + accumulated_sub_progress)
            
            # Scale the CHOSEN DIGITAL TEMPLATE and save as _07.tif
            final_resized_digital_ruler_path = resize_ruler.resize_and_save_ruler_template(
                pixels_per_centimeter_scale=px_cm_val,
                chosen_digital_ruler_template_path=chosen_digital_template_asset_path, # Path to BM_1cm/2cm/5cm_scale.tif asset
                # image_to_resize_path is removed from this call to match 4-arg function
                output_base_name=subfolder_name_item,
                output_directory_path=subfolder_path_item
            )
            if not os.path.exists(final_resized_digital_ruler_path): raise FileNotFoundError(f"Scaled digital ruler not found: {final_resized_digital_ruler_path}")
            print(f"    Digital ruler scaled and saved as: {os.path.basename(final_resized_digital_ruler_path)}")
            accumulated_sub_progress += sub_steps_alloc["digital_ruler_resize"]; progress_callback(current_prog_base + accumulated_sub_progress)
            
            num_other_views = len([v for v in orig_views_fps.values() if v != ruler_for_scale_fp])
            prog_per_other = sub_steps_alloc["other_obj"] / num_other_views if num_other_views > 0 else 0
            current_other_views_prog = 0

            for vk, o_fp in orig_views_fps.items():
                if o_fp == ruler_for_scale_fp: continue
                curr_o_path, is_temp_o = o_fp, False
                if o_fp.lower().endswith(raw_ext_config):
                    tmp_o_p=os.path.join(subfolder_path_item,f"{os.path.splitext(os.path.basename(o_fp))[0]}_rawobj_other.tif")
                    convert_raw_image_to_tiff(o_fp,tmp_o_p); curr_o_path,is_temp_o=tmp_o_p,True; cr2_conv_total+=1
                extract_and_save_center_object(curr_o_path, output_filename_suffix=object_artifact_suffix_config)
                if is_temp_o and os.path.exists(curr_o_path): os.remove(curr_o_path)
                current_other_views_prog += prog_per_other
                progress_callback(current_prog_base + accumulated_sub_progress + current_other_views_prog)
            accumulated_sub_progress += current_other_views_prog # Add total from this loop
            
            process_tablet_subfolder(
                subfolder_path_item, subfolder_name_item, px_cm_val, gui_photographer, ruler_for_scale_fp,
                add_logo=gui_add_logo, logo_path=gui_logo_path if gui_add_logo else None,
                object_extraction_background_mode=gui_obj_bg_mode )
            total_ok += 1
        except Exception as e: print(f"  ERROR processing set '{subfolder_name_item}': {e}"); total_err += 1
        finally:
            progress_callback(current_prog_base + prog_per_folder) 
            print("-" * 40)

    print(f"\n--- Processing Complete ---\nRAW converted: {cr2_conv_total}\nSets OK: {total_ok}\nSets Error: {total_err}\n")
    progress_callback(100); finished_callback()
