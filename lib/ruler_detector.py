import cv2
import numpy as np
import os

ROI_VERTICAL_START_FRACTION = 0.0
ROI_VERTICAL_END_FRACTION = 0.25
ROI_HORIZONTAL_START_FRACTION = 0.02
ROI_HORIZONTAL_END_FRACTION = 0.15

ANALYSIS_SCANLINE_COUNT = 7
MARK_BINARIZATION_THRESHOLD = 150
MIN_EXPECTED_MARK_WIDTH_AS_ROI_FRACTION = 0.04
MAX_EXPECTED_MARK_WIDTH_AS_ROI_FRACTION = 0.30
MARK_WIDTH_SIMILARITY_TOLERANCE_FRACTION = 0.40
MIN_ALTERNATING_MARKS_FOR_SCALE_ESTIMATION = 2

def extract_pixel_runs_from_scanline_data(scanline_data_array, binarization_cutoff_value):
    binarized_scanline_array = np.where(scanline_data_array < binarization_cutoff_value, 0, 255)
    list_of_pixel_runs = []
    if binarized_scanline_array.size == 0:
        return list_of_pixel_runs
    
    current_run_color_value = None
    current_run_start_position = 0
    for index, pixel_intensity_value in enumerate(binarized_scanline_array):
        current_pixel_color_type = 'black' if pixel_intensity_value == 0 else 'white'
        if current_run_color_value is None:
            current_run_color_value = current_pixel_color_type
            current_run_start_position = index
        elif current_pixel_color_type != current_run_color_value:
            run_width_in_pixels = index - current_run_start_position
            if run_width_in_pixels > 0:
                list_of_pixel_runs.append({
                    'type': current_run_color_value, 'start_index': current_run_start_position,
                    'end_index': index - 1, 'width_pixels': run_width_in_pixels
                })
            current_run_color_value = current_pixel_color_type
            current_run_start_position = index
            
    if current_run_color_value is not None:
        run_width_in_pixels = len(binarized_scanline_array) - current_run_start_position
        if run_width_in_pixels > 0:
            list_of_pixel_runs.append({
                'type': current_run_color_value, 'start_index': current_run_start_position,
                'end_index': len(binarized_scanline_array) - 1, 'width_pixels': run_width_in_pixels
            })
    return list_of_pixel_runs

def estimate_pixels_per_centimeter_from_ruler(image_file_path, ruler_position="top"): # ruler_position parameter IS DEFINED HERE
    input_image_array = cv2.imread(image_file_path)
    if input_image_array is None:
        raise FileNotFoundError(f"Image file not found: {image_file_path}")

    image_height_px, image_width_px = input_image_array.shape[:2]
    region_of_interest_color = None
    roi_scan_dimension_length_px = 0

    if ruler_position == "top":
        y_start_coord = int(image_height_px * ROI_VERTICAL_START_FRACTION)
        y_end_coord = int(image_height_px * ROI_VERTICAL_END_FRACTION)
        if not (0 <= y_start_coord < y_end_coord <= image_height_px):
            raise ValueError(f"Invalid TOP ROI Y coordinates: [{y_start_coord},{y_end_coord}]")
        region_of_interest_color = input_image_array[y_start_coord:y_end_coord, :]
        roi_scan_dimension_length_px = region_of_interest_color.shape[1]
    elif ruler_position == "bottom":
        y_start_coord = int(image_height_px * (1 - ROI_VERTICAL_END_FRACTION))
        y_end_coord = int(image_height_px * (1 - ROI_VERTICAL_START_FRACTION))
        if not (0 <= y_start_coord < y_end_coord <= image_height_px):
            raise ValueError(f"Invalid BOTTOM ROI Y coordinates: [{y_start_coord},{y_end_coord}]")
        region_of_interest_color = input_image_array[y_start_coord:y_end_coord, :]
        roi_scan_dimension_length_px = region_of_interest_color.shape[1]
    elif ruler_position == "left":
        x_start_coord = int(image_width_px * ROI_HORIZONTAL_START_FRACTION)
        x_end_coord = int(image_width_px * ROI_HORIZONTAL_END_FRACTION)
        if not (0 <= x_start_coord < x_end_coord <= image_width_px):
            raise ValueError(f"Invalid LEFT ROI X coordinates: [{x_start_coord},{x_end_coord}]")
        region_of_interest_color = input_image_array[:, x_start_coord:x_end_coord]
        roi_scan_dimension_length_px = region_of_interest_color.shape[0]
    elif ruler_position == "right":
        x_start_coord = int(image_width_px * (1 - ROI_HORIZONTAL_END_FRACTION))
        x_end_coord = int(image_width_px * (1 - ROI_HORIZONTAL_START_FRACTION))
        if not (0 <= x_start_coord < x_end_coord <= image_width_px):
            raise ValueError(f"Invalid RIGHT ROI X coordinates: [{x_start_coord},{x_end_coord}]")
        region_of_interest_color = input_image_array[:, x_start_coord:x_end_coord]
        roi_scan_dimension_length_px = region_of_interest_color.shape[0]
    else:
        raise ValueError(f"Invalid ruler_position specified: {ruler_position}")

    if region_of_interest_color.size == 0:
        raise ValueError(f"Ruler ROI is empty for position '{ruler_position}'.")
    
    region_of_interest_gray = cv2.cvtColor(region_of_interest_color, cv2.COLOR_BGR2GRAY)
    roi_primary_dim_px, roi_secondary_dim_px = region_of_interest_gray.shape

    candidate_mark_widths_list_px = []
    min_allowable_mark_width_px = roi_scan_dimension_length_px * MIN_EXPECTED_MARK_WIDTH_AS_ROI_FRACTION
    max_allowable_mark_width_px = roi_scan_dimension_length_px * MAX_EXPECTED_MARK_WIDTH_AS_ROI_FRACTION

    for i in range(ANALYSIS_SCANLINE_COUNT):
        current_scanline_pixel_data = None
        if ruler_position in ["top", "bottom"]:
            scanline_coordinate = int(roi_primary_dim_px * ((i + 0.5) / ANALYSIS_SCANLINE_COUNT))
            current_scanline_pixel_data = region_of_interest_gray[scanline_coordinate, :]
        elif ruler_position in ["left", "right"]:
            scanline_coordinate = int(roi_secondary_dim_px * ((i + 0.5) / ANALYSIS_SCANLINE_COUNT))
            current_scanline_pixel_data = region_of_interest_gray[:, scanline_coordinate]

        if current_scanline_pixel_data is None or current_scanline_pixel_data.size == 0: continue
        
        pixel_runs_on_current_scanline = extract_pixel_runs_from_scanline_data(current_scanline_pixel_data, MARK_BINARIZATION_THRESHOLD)
        if not pixel_runs_on_current_scanline or len(pixel_runs_on_current_scanline) < MIN_ALTERNATING_MARKS_FOR_SCALE_ESTIMATION:
            continue

        for j in range(len(pixel_runs_on_current_scanline) - (MIN_ALTERNATING_MARKS_FOR_SCALE_ESTIMATION - 1)):
            if pixel_runs_on_current_scanline[j]['type'] == 'black':
                initial_mark_width_px = pixel_runs_on_current_scanline[j]['width_pixels']
                if not (min_allowable_mark_width_px <= initial_mark_width_px <= max_allowable_mark_width_px):
                    continue
                
                current_sequence_mark_widths_px = [initial_mark_width_px]
                is_valid_mark_sequence = True
                for k in range(1, MIN_ALTERNATING_MARKS_FOR_SCALE_ESTIMATION):
                    previous_mark = pixel_runs_on_current_scanline[j + k - 1]
                    current_mark = pixel_runs_on_current_scanline[j + k]
                    if current_mark['type'] == previous_mark['type']: is_valid_mark_sequence = False; break
                    
                    current_mark_width_px = current_mark['width_pixels']
                    if not (min_allowable_mark_width_px <= current_mark_width_px <= max_allowable_mark_width_px):
                        is_valid_mark_sequence = False; break
                    if not (abs(current_mark_width_px - initial_mark_width_px) <= initial_mark_width_px * MARK_WIDTH_SIMILARITY_TOLERANCE_FRACTION):
                        is_valid_mark_sequence = False; break
                    current_sequence_mark_widths_px.append(current_mark_width_px)
                
                if is_valid_mark_sequence:
                    average_mark_width_for_sequence_px = np.mean(current_sequence_mark_widths_px)
                    candidate_mark_widths_list_px.append(average_mark_width_for_sequence_px)
                    
    if not candidate_mark_widths_list_px:
        raise ValueError("No consistent ruler mark pattern found meeting all criteria.")
        
    estimated_pixels_per_cm_value = np.median(candidate_mark_widths_list_px)
    if estimated_pixels_per_cm_value <= 1:
        raise ValueError(f"Estimated pixels_per_cm ({estimated_pixels_per_cm_value:.2f}) is too small.")
    
    return float(estimated_pixels_per_cm_value)
