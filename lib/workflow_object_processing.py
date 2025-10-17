import os
import cv2
from workflow_imports import (
    extract_and_save_center_object, convert_raw_image_to_tiff,
    process_intermediate_image_with_mask, get_extended_intermediate_suffixes,
    create_foreground_mask, select_ruler_like_contour,
    extract_specific_contour_to_image_array, detect_dominant_corner_background_color,
    get_museum_background_color
)


def prepare_ruler_image(ruler_for_scale_fp, subfolder_path_item, raw_ext_config):
    """Prepare ruler image, converting from RAW if needed."""
    path_ruler_extract_img, tmp_ruler_extract_conv_file = ruler_for_scale_fp, None

    if path_ruler_extract_img.lower().endswith(raw_ext_config):
        tmp_ruler_extract_conv_file = os.path.join(
            subfolder_path_item,
            f"{os.path.splitext(os.path.basename(path_ruler_extract_img))[0]}.tif"
        )
        if not os.path.exists(tmp_ruler_extract_conv_file):
            convert_raw_image_to_tiff(path_ruler_extract_img,
                                      tmp_ruler_extract_conv_file)
        path_ruler_extract_img = tmp_ruler_extract_conv_file

    return path_ruler_extract_img, tmp_ruler_extract_conv_file


def extract_object_and_detect_background(path_ruler_extract_img, object_extraction_bg_mode,
                                         object_artifact_suffix_config, museum_selection,
                                         ruler_position="bottom"):
    """Extract center object(s) and detect background color."""
    img_for_bg_detection = cv2.imread(path_ruler_extract_img)
    if img_for_bg_detection is None:
        raise ValueError(f"Failed to load image for background detection: {path_ruler_extract_img}")

    detected_bg_color_from_image = detect_dominant_corner_background_color(img_for_bg_detection)
    output_bg_color = get_museum_background_color(
        museum_selection=museum_selection, detected_bg_color=detected_bg_color_from_image)

    if object_extraction_bg_mode == 'rembg':
        from object_extractor_rembg import extract_and_save_center_object
    else:
        from object_extractor import extract_and_save_center_object
        
    art_fp, art_cont = extract_and_save_center_object(
        path_ruler_extract_img,
        source_background_detection_mode=object_extraction_bg_mode,
        output_image_background_color=output_bg_color,
        output_filename_suffix=object_artifact_suffix_config,
        museum_selection=museum_selection
    )
    
    return art_fp, art_cont, detected_bg_color_from_image, output_bg_color


def extract_ruler_contour(path_ruler_extract_img, detected_bg_color_from_image,
                          art_cont, background_color_tolerance,
                          temp_extracted_ruler_filename_config, subfolder_path_item):
    """
    Extract ruler contour and save isolated ruler image.

    Returns:
        str: Path to temporary isolated ruler file or None
    """
    import time
    import os
    
    if not os.path.exists(path_ruler_extract_img):
        raise ValueError(f"File does not exist: {path_ruler_extract_img}")
    
    ruler_loaded_arr = cv2.imread(path_ruler_extract_img, cv2.IMREAD_COLOR)
    
    if ruler_loaded_arr is None:
        time.sleep(0.5)
        ruler_loaded_arr = cv2.imread(path_ruler_extract_img, cv2.IMREAD_COLOR)
    
    if ruler_loaded_arr is None:
        raise ValueError(f"Fail reload {path_ruler_extract_img}")

    all_m = create_foreground_mask(
        ruler_loaded_arr, detected_bg_color_from_image, background_color_tolerance)
    all_c, _ = cv2.findContours(all_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ruler_c = select_ruler_like_contour(
        all_c, ruler_loaded_arr.shape[1], ruler_loaded_arr.shape[0],
        excluded_obj_contour=art_cont)

    tmp_iso_ruler_fp = None
    if ruler_c is not None:
        ext_ruler_arr = extract_specific_contour_to_image_array(
            ruler_loaded_arr, ruler_c, detected_bg_color_from_image, 5)
        tmp_iso_ruler_fp = os.path.join(
            subfolder_path_item, temp_extracted_ruler_filename_config)
        cv2.imwrite(tmp_iso_ruler_fp, ext_ruler_arr)
    else:
        print("     Warning: Could not isolate physical ruler part.")

    return tmp_iso_ruler_fp


def process_other_views(other_views_to_process_list, subfolder_path_item, raw_ext_config,
                        object_extraction_bg_mode, output_bg_color,
                        object_artifact_suffix_config, museum_selection):
    """
    Process other view images (non-ruler images).

    Returns:
        int: Number of CR2 conversions performed
    """
    cr2_conv_count = 0

    for o_fp_to_extract in other_views_to_process_list:
        curr_o_path, is_temp_o = o_fp_to_extract, False

        if o_fp_to_extract.lower().endswith(raw_ext_config):
            tmp_o_p = os.path.join(
                subfolder_path_item,
                f"{os.path.splitext(os.path.basename(o_fp_to_extract))[0]}.tif"
            )
            convert_raw_image_to_tiff(o_fp_to_extract, tmp_o_p)
            curr_o_path, is_temp_o = tmp_o_p, True
            cr2_conv_count += 1

        extract_and_save_center_object(
            curr_o_path,
            source_background_detection_mode=object_extraction_bg_mode,
            output_image_background_color=output_bg_color,
            output_filename_suffix=object_artifact_suffix_config,
            museum_selection=museum_selection
        )

        if is_temp_o and os.path.exists(curr_o_path):
            os.remove(curr_o_path)

    return cr2_conv_count


def process_intermediate_images(all_files_in_subfolder, subfolder_path_item, subfolder_name_item,
                                image_extensions_tuple, object_artifact_suffix_config,
                                other_views_to_process_list, ruler_for_scale_fp, raw_ext_config,
                                object_extraction_bg_mode, output_bg_color, museum_selection,
                                gradient_width_fraction):
    """
    Process intermediate images with suffix patterns.

    Returns:
        int: Number of CR2 conversions performed
    """
    print(f"   Processing intermediate images for {subfolder_name_item}...")

    intermediate_suffix_patterns = get_extended_intermediate_suffixes()
    cr2_conv_count = 0

    for img_file in all_files_in_subfolder:
        if not img_file.lower().endswith(image_extensions_tuple):
            continue

        if object_artifact_suffix_config in img_file:
            continue

        file_basename = os.path.basename(img_file)
        is_intermediate = False
        matched_suffix = None

        for suffix in intermediate_suffix_patterns.keys():
            suffix_pattern = f"_{suffix}."
            if suffix_pattern.lower() in file_basename.lower():
                is_intermediate = True
                matched_suffix = suffix
                break

        if is_intermediate:
            print(f"   Processing intermediate image: {file_basename} (suffix: {matched_suffix})")
            img_path = os.path.join(subfolder_path_item, file_basename)

            if img_path in other_views_to_process_list or img_path == ruler_for_scale_fp:
                print(f"   Skipping {file_basename} as it was already processed as a main view")
                continue

            curr_path, is_temp = img_path, False
            if img_path.lower().endswith(raw_ext_config):
                tmp_path = os.path.join(
                    subfolder_path_item,
                    f"{os.path.splitext(os.path.basename(img_path))[0]}.tif"
                )
                convert_raw_image_to_tiff(img_path, tmp_path)
                curr_path, is_temp = tmp_path, True
                cr2_conv_count += 1

            try:
                extract_and_save_center_object(
                    curr_path,
                    source_background_detection_mode=object_extraction_bg_mode,
                    output_image_background_color=output_bg_color,
                    output_filename_suffix=object_artifact_suffix_config,
                    museum_selection=museum_selection
                )

                object_filepath = f"{os.path.splitext(curr_path)[0]}{object_artifact_suffix_config}"
                if os.path.exists(object_filepath):
                    process_intermediate_image_with_mask(
                        object_filepath,
                        background_color=output_bg_color,
                        gradient_width_fraction=gradient_width_fraction
                    )
                    print(f"   Successfully processed intermediate image: {file_basename}")
                else:
                    print(f"   Warning: Object file not created for {file_basename}: {object_filepath}")

            except Exception as e:
                print(f"   Error processing {file_basename}: {e}")

            if is_temp and os.path.exists(curr_path):
                os.remove(curr_path)

    return cr2_conv_count
