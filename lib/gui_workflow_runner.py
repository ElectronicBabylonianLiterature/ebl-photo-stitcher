import os
import time
import traceback
import glob

from workflow_imports import (
    organize_project_subfolders, process_tablet_subfolder,
    MUSEUM_CONFIGS, DEFAULT_BACKGROUND_DETECTION_COLOR_TOLERANCE,
    organize_files_func
)
from workflow_scale_detection import determine_pixels_per_cm
from workflow_object_processing import (
    prepare_ruler_image, extract_object_and_detect_background, extract_ruler_contour,
    process_other_views, process_intermediate_images
)
from workflow_ruler_generation import (
    select_ruler_template, generate_digital_ruler, prepare_other_views_list
)
from workflow_cleanup import cleanup_intermediate_files, cleanup_temp_files
from workflow_file_processing import find_ruler_and_views
from workflow_statistics import print_final_statistics
from extract_measurements import add_measurement_record, clear_fallback_comparisons
from extract_measurements_excel import finalize_measurements_with_comparison
from remove_background import get_museum_background_color

def run_complete_image_processing_workflow(
    source_folder_path,
    ruler_position,
    photographer_name,
    object_extraction_bg_mode,
    add_logo,
    logo_path,
    raw_ext_config,
    image_extensions_config,
    ruler_template_1cm_asset_path,
    ruler_template_2cm_asset_path,
    ruler_template_5cm_asset_path,
    view_file_patterns_config,
    temp_ruler_filename,
    object_artifact_suffix_config,
    progress_callback,
    finished_callback,
    museum_selection="British Museum",
    app_root_window=None,
    background_color_tolerance=None,
    use_measurements_from_database=False,
    measurements_dict=None,
    gradient_width_fraction=0.5,
    enable_hdr_processing=False,
    use_first_photo_measurements=False,
    force_manual_ruler=False
):
    """Main workflow orchestration function."""
    
    print(f"Workflow started for folder: {source_folder_path}")
    
    clear_fallback_comparisons()
    start_time = time.time()
    failed_objects = []

    if background_color_tolerance is None:
        background_color_tolerance = DEFAULT_BACKGROUND_DETECTION_COLOR_TOLERANCE

    progress_callback(2)

    image_extensions_tuple = tuple(ext.lower() for ext in image_extensions_config) + \
        ((raw_ext_config.lower(),) if isinstance(raw_ext_config, str)
         else tuple(r_ext.lower() for r_ext in raw_ext_config))

    rotation_angle = 0
    try:
        if app_root_window and hasattr(app_root_window, 'advanced_tab'):
            advanced_settings = app_root_window.advanced_tab.get_settings()
            rotation_angle = advanced_settings.get('rotation_angle', 0)
    except Exception as e:
        print(f"Warning: Could not get rotation settings: {e}")

    try:
        processed_subfolders = organize_project_subfolders(
            source_folder_path, image_extensions_tuple, organize_files_func)
    except Exception as e_org:
        print(f"   Workflow halted due to error during file organization: {e_org}")
        progress_callback(100)
        finished_callback()
        return

    if rotation_angle and rotation_angle > 0:
        print(f"Step 0a: Rotating images by {rotation_angle}°...")
        total_rotated = 0
        
        try:
            from image_rotation import rotate_images_in_folder
            
            for subfolder_path in processed_subfolders:
                subfolder_name = os.path.basename(subfolder_path)
                print(f"   Checking folder for rotation: {subfolder_name}")
                
                rotated_count = rotate_images_in_folder(
                    subfolder_path, rotation_angle, image_extensions_tuple)
                total_rotated += rotated_count
                
                if rotated_count > 0:
                    print(f"   Rotated {rotated_count} images in {subfolder_name}")
            
            if total_rotated > 0:
                print(f"   Rotation complete: {total_rotated} images rotated by {rotation_angle}°")
            else:
                print(f"   No images needed rotation")
            
        except ImportError:
            print("   Warning: Could not import rotation module. Skipping rotation.")
        except Exception as e:
            print(f"   Warning: Error during rotation: {e}")

    if enable_hdr_processing:
        print("Step 0b: HDR Processing...")

        try:
            from hdr_processor import should_use_hdr_processing, process_hdr_images
        except ImportError as e:
            print(f"   Warning: Could not import HDR processor: {e}")
            print("   Continuing without HDR processing...")
            enable_hdr_processing = False

        if enable_hdr_processing:

            original_subfolders = processed_subfolders.copy()
            updated_subfolders = []

            for subfolder_path in original_subfolders:
                subfolder_name = os.path.basename(subfolder_path)

                if should_use_hdr_processing(source_folder_path, subfolder_name):
                    print(f"   Applying HDR processing to {subfolder_name}...")
                    hdr_output_folder = process_hdr_images(
                        source_folder_path, subfolder_name)

                    if hdr_output_folder:

                        updated_subfolders.append(hdr_output_folder)
                        print(
                            f"   HDR processing completed for {subfolder_name} → {os.path.basename(hdr_output_folder)}")
                    else:
                        print(
                            f"   HDR processing failed for {subfolder_name}. Using original images.")
                        updated_subfolders.append(subfolder_path)
                else:
                    print(
                        f"   HDR processing not applicable for {subfolder_name}")
                    updated_subfolders.append(subfolder_path)

            processed_subfolders = updated_subfolders
            print(
                f"   HDR processing complete. Processing {len(processed_subfolders)} subfolder(s).")

    filtered_subfolders = []
    for subfolder_path in processed_subfolders:
        subfolder_name = os.path.basename(subfolder_path)
        if subfolder_name.startswith('_Final_'):
            print(f"   Skipping output folder: {subfolder_name}")
            continue
        filtered_subfolders.append(subfolder_path)
    
    processed_subfolders = filtered_subfolders

    processed_subfolders.sort(key=lambda path: os.path.basename(path))
    
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

    cached_px_per_cm = None
    cached_measurements_used = None
    cached_detected_bg_color = None
    cached_output_bg_color = None
    is_first_subfolder = True

    if use_first_photo_measurements:
        print("Using first photo measurements mode - ruler detection will only run on first image set")

    try:

        if app_root_window and hasattr(app_root_window, 'advanced_tab'):
            advanced_settings = app_root_window.advanced_tab.get_settings()
        else:

            advanced_settings = {
                'gradient_width_fraction': gradient_width_fraction,
                'background_color_tolerance': DEFAULT_BACKGROUND_DETECTION_COLOR_TOLERANCE,
                'add_logo': add_logo,
                'logo_path': logo_path
            }

        from ruler_detector import update_ruler_detection_settings
        update_ruler_detection_settings(advanced_settings)
        
    except Exception as e:
        print(f"Warning: Could not apply ruler detection settings: {e}")
    
    successful_presets = {}
    failed_folders = []

    for i, subfolder_path_item in enumerate(processed_subfolders):
        subfolder_name_item = os.path.basename(subfolder_path_item)
        print(
            f"Processing Subfolder {i+1}/{num_folders}: {subfolder_name_item}")

        current_prog_base = 10 + i * prog_per_folder
        progress_callback(current_prog_base)

        try:

            use_cached_measurements = use_first_photo_measurements and not is_first_subfolder

            if use_cached_measurements:
                print(
                    f"   Using cached measurements from first image set (px/cm: {cached_px_per_cm})")
                print(
                    f"   Using cached background colors - detected: {cached_detected_bg_color}, output: {cached_output_bg_color}")

            result = process_single_subfolder(
                subfolder_path_item, subfolder_name_item, image_extensions_tuple,
                view_file_patterns_config, object_artifact_suffix_config,
                temp_ruler_filename, raw_ext_config, ruler_position, museum_selection,
                use_measurements_from_database, measurements_dict, background_color_tolerance,
                object_extraction_bg_mode, ruler_template_1cm_asset_path,
                ruler_template_2cm_asset_path, ruler_template_5cm_asset_path,
                gradient_width_fraction, source_folder_path, photographer_name,
                add_logo, logo_path, current_prog_base, prog_per_folder, progress_callback,
                use_cached_measurements, cached_px_per_cm, cached_measurements_used,
                cached_detected_bg_color, cached_output_bg_color, app_root_window,
                force_manual_ruler
            )

            if result['success']:
                total_ok += 1
                cr2_conv_total += result['cr2_conversions']

                if use_first_photo_measurements and is_first_subfolder:
                    cached_px_per_cm = result.get('px_per_cm')
                    cached_measurements_used = result.get('measurements_used')
                    cached_detected_bg_color = result.get('detected_bg_color')
                    cached_output_bg_color = result.get('output_bg_color')
                    if cached_px_per_cm:
                        print(
                            f"   Cached px/cm ratio from first set: {cached_px_per_cm}")
                        print(
                            f"   Cached background colors - detected: {cached_detected_bg_color}, output: {cached_output_bg_color}")

            else:
                failed_objects.append(subfolder_name_item)
                total_err += 1

            is_first_subfolder = False

        except Exception as e:
            print(f"   ERROR processing set '{subfolder_name_item}': {e}")
            traceback.print_exc()
            failed_objects.append(subfolder_name_item)
            total_err += 1

    print_fallback_summary(successful_presets, failed_folders)

    print_final_statistics(start_time, total_ok, total_err,
                           cr2_conv_total, failed_objects)

    if total_ok > 0:
        cleanup_intermediate_files(
            processed_subfolders, object_artifact_suffix_config)

    try:
        finalize_measurements_with_comparison(source_folder_path, photographer_name)
    except Exception as e:
        print(f"Warning: Could not create measurement comparison file: {e}")

    progress_callback(100)
    finished_callback()


def process_single_subfolder(subfolder_path_item, subfolder_name_item, image_extensions_tuple,
                             view_file_patterns_config, object_artifact_suffix_config,
                             temp_extracted_ruler_filename_config, raw_ext_config,
                             ruler_position, museum_selection, use_measurements_from_database,
                             measurements_dict, background_color_tolerance, object_extraction_bg_mode,
                             ruler_template_1cm_asset_path, ruler_template_2cm_asset_path,
                             ruler_template_5cm_asset_path, gradient_width_fraction,
                             source_folder_path, photographer_name, add_logo, logo_path,
                             current_prog_base, prog_per_folder, progress_callback,
                             use_cached_measurements=False, cached_px_per_cm=None, cached_measurements_used=None,
                             cached_detected_bg_color=None, cached_output_bg_color=None,
                             app_instance=None, force_manual_ruler=False
):
    """Process a single subfolder."""

    result = {'success': False, 'cr2_conversions': 0}

    sub_steps = {"layout": 0.05, "scale": 0.15, "ruler_art": 0.1, "ruler_extract": 0.05,
                 "ruler_choice": 0.05, "ruler_resize": 0.1, "other_obj": 0.25, "stitch": 0.25}
    progress = 0.0

    all_files = [f for f in os.listdir(subfolder_path_item)
                 if os.path.isfile(os.path.join(subfolder_path_item, f))]

    ruler_for_scale_fp, orig_views_fps = find_ruler_and_views(
        subfolder_path_item, subfolder_name_item, all_files,
        image_extensions_tuple, view_file_patterns_config, object_artifact_suffix_config
    )

    if not ruler_for_scale_fp:
        print(f"   No ruler image found for {subfolder_name_item}. Skip.")
        return result

    progress += sub_steps["layout"] * prog_per_folder
    progress_callback(current_prog_base + progress)

    if use_cached_measurements and cached_px_per_cm is not None:
        print(f"   Using cached scale detection: {cached_px_per_cm} px/cm")
        px_cm_val = cached_px_per_cm
        measurements_used = cached_measurements_used
        cr2_conv_scale = 0
    else:
        from workflow_scale_detection import determine_pixels_per_cm_with_fallback
        px_cm_val, measurements_used, cr2_conv_scale, preset_used = determine_pixels_per_cm_with_fallback(
            subfolder_path_item, subfolder_name_item, ruler_for_scale_fp,
            raw_ext_config, museum_selection, ruler_position,
            use_measurements_from_database, measurements_dict, background_color_tolerance,
            app_instance, force_manual_ruler
        )

    result['cr2_conversions'] += cr2_conv_scale
    result['px_per_cm'] = px_cm_val
    result['measurements_used'] = measurements_used

    if px_cm_val is None:
        print(
            f"   ERROR: Could not determine ruler scale for {subfolder_name_item}. Skip.")
        return result

    progress += sub_steps["scale"] * prog_per_folder
    progress_callback(current_prog_base + progress)

    if use_cached_measurements:
        print(f"   Using cached measurements - still processing ruler image for object extraction")

        path_ruler_extract_img, tmp_ruler_conv_file = prepare_ruler_image(
            ruler_for_scale_fp, subfolder_path_item, raw_ext_config)

        if tmp_ruler_conv_file:
            result['cr2_conversions'] += 1

        art_fp, art_cont, detected_bg_color, output_bg_color = extract_object_and_detect_background(
            path_ruler_extract_img, object_extraction_bg_mode,
            object_artifact_suffix_config, museum_selection, ruler_position
        )
        should_recalculate = (use_measurements_from_database and measurements_dict and 
                            (measurements_used or px_cm_val == 100.0))
        
        print(f"   Scale recalculation check: use_db={use_measurements_from_database}, has_dict={measurements_dict is not None}, measurements_used={measurements_used}, px_cm={px_cm_val}")
        print(f"   Should recalculate: {should_recalculate}")
        
        if should_recalculate:
            from workflow_scale_detection import was_excel_measurement_used
            from extract_measurements import create_measurement_record_from_excel, calculate_scale_from_measurement_and_object
            from measurements_utils import get_tablet_width_from_measurements
            
            is_excel, tablet_id, tablet_width_cm = was_excel_measurement_used(
                subfolder_path_item, measurements_dict)
            
            if art_fp and os.path.exists(art_fp):
                if is_excel:
                    print(f"   Recalculating scale using final extracted object (Excel measurement)...")
                else:
                    print(f"   Recalculating scale using final extracted object (Sippar.json measurement)...")
                    tablet_width_cm = get_tablet_width_from_measurements(subfolder_path_item, measurements_dict)
                
                if tablet_width_cm and tablet_width_cm > 0:
                    try:
                        actual_px_cm_val = calculate_scale_from_measurement_and_object(
                            art_fp, tablet_width_cm, gap_pixels=50
                        )
                        px_cm_val = actual_px_cm_val
                        result['px_per_cm'] = px_cm_val
                        
                        if is_excel:
                            print(f"   Excel scale calculation complete: {px_cm_val:.2f} px/cm")
                            print(f"   Measurement record will be created after all objects are extracted")
                        else:
                            print(f"   ✓ Scale recalculated for Sippar.json measurement: {px_cm_val:.2f} px/cm")
                            
                    except Exception as e:
                        print(f"   ✗ Error recalculating scale from extracted object: {e}")
                        print(f"   Continuing with placeholder scale: {px_cm_val:.2f} px/cm")
        
        detected_bg_color = cached_detected_bg_color
        output_bg_color = cached_output_bg_color
        print(f"   Using cached background colors for {subfolder_name_item}")

        cleanup_temp_files(tmp_ruler_conv_file)

        chosen_ruler_tpl, custom_ruler_size_cm = select_ruler_template(
            museum_selection, art_fp, px_cm_val, ruler_template_1cm_asset_path,
            ruler_template_2cm_asset_path, ruler_template_5cm_asset_path
        )

        generate_digital_ruler(px_cm_val, chosen_ruler_tpl, subfolder_name_item,
                               subfolder_path_item, custom_ruler_size_cm)

        progress += (sub_steps["ruler_art"] + sub_steps["ruler_extract"]
                     + sub_steps["ruler_choice"] + sub_steps["ruler_resize"]) * prog_per_folder
        progress_callback(current_prog_base + progress)
    else:

        path_ruler_extract_img, tmp_ruler_conv_file = prepare_ruler_image(
            ruler_for_scale_fp, subfolder_path_item, raw_ext_config)

        if tmp_ruler_conv_file:
            result['cr2_conversions'] += 1

        art_fp, art_cont, detected_bg_color, output_bg_color = extract_object_and_detect_background(
            path_ruler_extract_img, object_extraction_bg_mode,
            object_artifact_suffix_config, museum_selection,
            ruler_position
        )
        should_recalculate = (use_measurements_from_database and measurements_dict and 
                            (measurements_used or px_cm_val == 100.0))
        
        print(f"   Scale recalculation check: use_db={use_measurements_from_database}, has_dict={measurements_dict is not None}, measurements_used={measurements_used}, px_cm={px_cm_val}")
        print(f"   Should recalculate: {should_recalculate}")
        
        if should_recalculate:
            from workflow_scale_detection import was_excel_measurement_used
            from extract_measurements import create_measurement_record_from_excel, calculate_scale_from_measurement_and_object
            from measurements_utils import get_tablet_width_from_measurements
            
            is_excel, tablet_id, tablet_width_cm = was_excel_measurement_used(
                subfolder_path_item, measurements_dict)
            
            if art_fp and os.path.exists(art_fp):
                if is_excel:
                    print(f"   Recalculating scale using final extracted object (Excel measurement)...")
                else:
                    print(f"   Recalculating scale using final extracted object (Sippar.json measurement)...")
                    tablet_width_cm = get_tablet_width_from_measurements(subfolder_path_item, measurements_dict)
                
                if tablet_width_cm and tablet_width_cm > 0:
                    try:
                        actual_px_cm_val = calculate_scale_from_measurement_and_object(
                            art_fp, tablet_width_cm, gap_pixels=50
                        )
                        px_cm_val = actual_px_cm_val
                        result['px_per_cm'] = px_cm_val
                        
                        if is_excel:
                            print(f"   ✓ Scale recalculated for Excel measurement: {px_cm_val:.2f} px/cm")
                            print(f"   Excel measurement record will be created after all objects are extracted")
                        else:
                            print(f"   ✓ Scale recalculated for Sippar.json measurement: {px_cm_val:.2f} px/cm")
                            
                    except Exception as e:
                        print(f"   ✗ Error recalculating scale from extracted object: {e}")
                        print(f"   Continuing with placeholder scale: {px_cm_val:.2f} px/cm")

        progress += sub_steps["ruler_art"] * prog_per_folder
        progress_callback(current_prog_base + progress)

        tmp_iso_ruler_fp = extract_ruler_contour(
            path_ruler_extract_img, detected_bg_color, art_cont,
            background_color_tolerance, temp_extracted_ruler_filename_config,
            subfolder_path_item
        )

        cleanup_temp_files(tmp_ruler_conv_file)

        progress += sub_steps["ruler_extract"] * prog_per_folder
        progress_callback(current_prog_base + progress)

        chosen_ruler_tpl, custom_ruler_size_cm = select_ruler_template(
            museum_selection, art_fp, px_cm_val, ruler_template_1cm_asset_path,
            ruler_template_2cm_asset_path, ruler_template_5cm_asset_path
        )

        progress += sub_steps["ruler_choice"] * prog_per_folder
        progress_callback(current_prog_base + progress)

        generate_digital_ruler(px_cm_val, chosen_ruler_tpl, subfolder_name_item,
                               subfolder_path_item, custom_ruler_size_cm)

        cleanup_temp_files(tmp_iso_ruler_fp)

        progress += sub_steps["ruler_resize"] * prog_per_folder
        progress_callback(current_prog_base + progress)

    result['detected_bg_color'] = detected_bg_color
    result['output_bg_color'] = output_bg_color

    print(f"   Finding other views to process for {subfolder_name_item}...")

    all_image_files = []
    for ext in image_extensions_tuple:
        pattern = os.path.join(subfolder_path_item, f"*{ext}")
        all_image_files.extend(glob.glob(pattern))
    from stitch_config import get_extended_intermediate_suffixes
    intermediate_suffix_patterns = get_extended_intermediate_suffixes()

    other_views_to_process_list = []

    for img_file in all_image_files:
        filename = os.path.basename(img_file)

        if img_file == ruler_for_scale_fp:
            continue

        if object_artifact_suffix_config in img_file:
            continue

        if 'temp_' in filename:
            continue

        if '_ruler.' in filename.lower():
            print(f"     Skipping ruler file: {filename}")
            continue
        is_intermediate = False
        for suffix in intermediate_suffix_patterns.keys():
            suffix_pattern = f"_{suffix}."
            if suffix_pattern.lower() in filename.lower():
                is_intermediate = True
                print(f"     Skipping intermediate view: {filename} (will be processed separately)")
                break

        if is_intermediate:
            continue

        other_views_to_process_list.append(img_file)
        print(f"     Added view: {filename}")

    print(f"   Found {len(other_views_to_process_list)} other views to process")
    print(
        f"   Other views: {[os.path.basename(f) for f in other_views_to_process_list]}")

    orig_other_views_list = prepare_other_views_list(
        None, orig_views_fps, ruler_for_scale_fp)

    combined_other_views = list(
        set(orig_other_views_list + other_views_to_process_list))

    cr2_conv_other = process_other_views(
        combined_other_views, subfolder_path_item, raw_ext_config,
        object_extraction_bg_mode, output_bg_color,
        object_artifact_suffix_config, museum_selection
    )
    result['cr2_conversions'] += cr2_conv_other
    
    if use_measurements_from_database and measurements_dict and measurements_used:
        from workflow_scale_detection import was_excel_measurement_used
        is_excel, tablet_id, tablet_width_cm = was_excel_measurement_used(
            subfolder_path_item, measurements_dict)
        
        print(f"     is_excel: {is_excel}, tablet_id: {tablet_id}")
        
        if is_excel:
            print("   Creating final Excel measurement record with all objects available...")
            try:
                from extract_measurements import create_measurement_record_from_excel, calculate_scale_from_measurement_and_object
                from measurements_utils import get_tablet_width_from_measurements
                obverse_object_pattern = f"{subfolder_name_item}_01_object.tif"
                obverse_object_path = os.path.join(subfolder_path_item, obverse_object_pattern)
                
                if os.path.exists(obverse_object_path):
                    print(f"   Using obverse image for measurement: {obverse_object_pattern}")
                    measurement_image_path = obverse_object_path
                else:
                    print(f"   Obverse image not found, using scale detection image: {os.path.basename(art_fp)}")
                    measurement_image_path = art_fp
                tablet_width_cm = get_tablet_width_from_measurements(subfolder_path_item, measurements_dict)
                
                if tablet_width_cm and tablet_width_cm > 0:
                    recalc_scale = calculate_scale_from_measurement_and_object(
                        measurement_image_path, tablet_width_cm, gap_pixels=50
                    )
                    
                    if recalc_scale and recalc_scale > 0:
                        px_cm_val = recalc_scale
                        result['px_per_cm'] = px_cm_val
                        print(f"   Confirmed scale using final objects: {px_cm_val:.2f} px/cm")
                        
                        success = create_measurement_record_from_excel(
                            measurement_image_path, px_cm_val, subfolder_name_item, measurements_dict, 
                            subfolder_path_item, gap_pixels=50
                        )
                        if success:
                            print(f"   ✓ Final Excel measurement record created for {subfolder_name_item}")
                            print(f"   Regenerating ruler with corrected Excel scale: {px_cm_val:.2f} px/cm")
                            
                            try:
                                chosen_ruler_tpl, custom_ruler_size_cm = select_ruler_template(
                                    museum_selection, measurement_image_path, px_cm_val, 
                                    ruler_template_1cm_asset_path, ruler_template_2cm_asset_path, 
                                    ruler_template_5cm_asset_path
                                )
                                ruler_success = generate_digital_ruler(
                                    px_cm_val, chosen_ruler_tpl, subfolder_name_item,
                                    subfolder_path_item, custom_ruler_size_cm
                                )
                                
                                if ruler_success:
                                    print(f"   ✓ Ruler regenerated with Excel-based scale: {px_cm_val:.2f} px/cm")
                                else:
                                    print(f"   ✗ Failed to regenerate ruler with corrected scale")
                                    
                            except Exception as ruler_e:
                                print(f"   ✗ Error regenerating ruler: {ruler_e}")
                        else:
                            print(f"   ✗ Failed to create final Excel measurement record for {subfolder_name_item}")
                    else:
                        print(f"   ✗ Could not recalculate scale with final objects")
                else:
                    print(f"   ✗ Could not get tablet width for final calculation")
                        
            except Exception as e:
                print(f"   ✗ Error creating final Excel measurement record: {e}")
        else:
            print(f"   No Excel measurements to process for {subfolder_name_item}")

    cr2_conv_intermediate = process_intermediate_images(
        all_files, subfolder_path_item, subfolder_name_item,
        image_extensions_tuple, object_artifact_suffix_config,
        combined_other_views, ruler_for_scale_fp, raw_ext_config,
        object_extraction_bg_mode, output_bg_color, museum_selection,
        gradient_width_fraction
    )
    result['cr2_conversions'] += cr2_conv_intermediate

    progress += sub_steps["other_obj"] * prog_per_folder

    stitched_output_bg_color = MUSEUM_CONFIGS.get(
        museum_selection, {}).get("background_color", (0, 0, 0))
    if museum_selection == "British Museum" or museum_selection == "Black background (Jena)":
        stitched_output_bg_color = output_bg_color

    process_tablet_subfolder(
        subfolder_path=subfolder_path_item,
        ruler_position=ruler_position,
        main_input_folder_path=source_folder_path,
        output_base_name=subfolder_name_item,
        pixels_per_cm=px_cm_val,
        photographer_name=photographer_name,
        ruler_image_for_scale_path=ruler_for_scale_fp,
        add_logo=add_logo,
        logo_path=logo_path if add_logo else None,
        object_extraction_background_mode=object_extraction_bg_mode,
        stitched_bg_color=stitched_output_bg_color,
        custom_layout=None,
        view_file_patterns_config=view_file_patterns_config,  
    )

    result['success'] = True

    return result

def print_fallback_summary(successful_presets, failed_folders):
    """Print summary of which ruler detection presets were successful"""
    
    print("\n" + "="*60)
    print("RULER DETECTION PRESET SUMMARY")
    print("="*60)
    
    if successful_presets:
        for preset_name, folders in successful_presets.items():
            if preset_name == "Current Settings":
                print(f"✓ Current Settings worked for {len(folders)} folders")
            else:
                print(f"⚠ Fallback '{preset_name}' used for {len(folders)} folders:")
                for folder in folders[:5]:
                    print(f"    - {folder}")
                if len(folders) > 5:
                    print(f"    ... and {len(folders) - 5} more")

        fallback_count = sum(len(folders) for preset, folders in successful_presets.items() 
                           if preset != "Current Settings")
        
        if fallback_count > 0:

            best_fallback = max(
                [(preset, folders) for preset, folders in successful_presets.items() 
                 if preset != "Current Settings"],
                key=lambda x: len(x[1]),
                default=(None, [])
            )
            
            if best_fallback[0]:
                print(f"\n💡 RECOMMENDATION:")
                print(f"   Consider changing your default settings to '{best_fallback[0]}'")
                print(f"   This preset worked for {len(best_fallback[1])} folders where current settings failed.")
                print(f"   You can apply this preset in Advanced tab > Quick Presets")
    
    if failed_folders:
        print(f"\n✗ Complete failure for {len(failed_folders)} folders:")
        for folder in failed_folders[:10]:
            print(f"    - {folder}")
        if len(failed_folders) > 10:
            print(f"    ... and {len(failed_folders) - 10} more")
        print(f"   These folders may need manual ruler positioning or measurements from database.")
    
    print("="*60)
