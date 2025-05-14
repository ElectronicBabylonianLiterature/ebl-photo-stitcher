# ruler_detector.py (Module for scale detection)
import cv2
import numpy as np
import os

# --- Configuration: Ruler Detection ---
# These are the settings that were last confirmed by the user
RULER_ROI_TOP_FRACTION = 0.05
RULER_ROI_BOTTOM_FRACTION = 0.25
RULER_ANALYSIS_SCANLINE_COUNT = 7
RULER_MARK_BINARIZATION_THRESHOLD = 150
MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.08
MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.30
RULER_MARK_WIDTH_SIMILARITY_TOLERANCE = 0.40
MIN_ALTERNATING_MARKS_FOR_SCALE = 2


# --- Helper Functions (Ruler Detection Only) ---
def extract_pixel_runs_from_scanline(scanline_pixel_data, binarization_threshold_value):
    binary_scanline = np.where(scanline_pixel_data < binarization_threshold_value, 0, 255)
    pixel_runs = []
    if binary_scanline.size == 0: return pixel_runs
    current_run_color_type = None
    current_run_start_index = 0
    for i, pixel_value in enumerate(binary_scanline):
        pixel_color_type = 'black' if pixel_value == 0 else 'white'
        if current_run_color_type is None:
            current_run_color_type = pixel_color_type
            current_run_start_index = i
        elif pixel_color_type != current_run_color_type:
            run_width_pixels = i - current_run_start_index
            if run_width_pixels > 0:
                pixel_runs.append({
                    'type': current_run_color_type, 'start_index': current_run_start_index,
                    'end_index': i - 1, 'width_pixels': run_width_pixels
                })
            current_run_color_type = pixel_color_type
            current_run_start_index = i
    if current_run_color_type is not None:
        run_width_pixels = len(binary_scanline) - current_run_start_index
        if run_width_pixels > 0:
            pixel_runs.append({
                'type': current_run_color_type, 'start_index': current_run_start_index,
                'end_index': len(binary_scanline) - 1, 'width_pixels': run_width_pixels
            })
    return pixel_runs

def estimate_pixels_per_centimeter_from_ruler(image_filepath):
    input_image = cv2.imread(image_filepath)
    if input_image is None: raise FileNotFoundError(f"Input image not found: {image_filepath}")
    
    # Using constants defined in this module
    image_height_pixels, image_width_pixels = input_image.shape[:2]
    ruler_roi_start_y = int(image_height_pixels * RULER_ROI_TOP_FRACTION)
    ruler_roi_end_y = int(image_height_pixels * RULER_ROI_BOTTOM_FRACTION)

    if not (0 <= ruler_roi_start_y < ruler_roi_end_y <= image_height_pixels):
        raise ValueError(f"Invalid ROI y=[{ruler_roi_start_y}, {ruler_roi_end_y}] for image height {image_height_pixels}")
    
    ruler_strip_roi_color = input_image[ruler_roi_start_y:ruler_roi_end_y, :]
    if ruler_strip_roi_color.size == 0: raise ValueError("Ruler ROI empty.")
    
    ruler_strip_roi_grayscale = cv2.cvtColor(ruler_strip_roi_color, cv2.COLOR_BGR2GRAY)
    roi_height_pixels, roi_width_pixels = ruler_strip_roi_grayscale.shape
    if roi_width_pixels == 0: raise ValueError("Ruler ROI width zero.")
    
    candidate_cm_widths_in_pixels = []
    min_mark_width_px = roi_width_pixels * MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION
    max_mark_width_px = roi_width_pixels * MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION
    
    for i in range(RULER_ANALYSIS_SCANLINE_COUNT):
        scanline_y_coordinate = int(roi_height_pixels * ((i + 0.5) / RULER_ANALYSIS_SCANLINE_COUNT))
        current_scanline_data = ruler_strip_roi_grayscale[scanline_y_coordinate, :]
        pixel_runs_on_scanline = extract_pixel_runs_from_scanline(current_scanline_data, RULER_MARK_BINARIZATION_THRESHOLD)
        
        if not pixel_runs_on_scanline or len(pixel_runs_on_scanline) < MIN_ALTERNATING_MARKS_FOR_SCALE:
            continue
            
        for j in range(len(pixel_runs_on_scanline) - (MIN_ALTERNATING_MARKS_FOR_SCALE - 1)):
            if pixel_runs_on_scanline[j]['type'] == 'black': # Assuming rulers start with black or have black marks
                initial_mark_width = pixel_runs_on_scanline[j]['width_pixels']
                if not (min_mark_width_px <= initial_mark_width <= max_mark_width_px):
                    continue
                
                current_valid_sequence_widths = [initial_mark_width]
                is_sequence_valid = True
                for k in range(1, MIN_ALTERNATING_MARKS_FOR_SCALE):
                    prev_mark = pixel_runs_on_scanline[j + k - 1]
                    curr_mark = pixel_runs_on_scanline[j + k]
                    if curr_mark['type'] == prev_mark['type']:
                        is_sequence_valid = False; break
                    mark_width = curr_mark['width_pixels']
                    if not (min_mark_width_px <= mark_width <= max_mark_width_px):
                        is_sequence_valid = False; break
                    if not (abs(mark_width - initial_mark_width) <= initial_mark_width * RULER_MARK_WIDTH_SIMILARITY_TOLERANCE):
                        is_sequence_valid = False; break
                    current_valid_sequence_widths.append(mark_width)
                
                if is_sequence_valid:
                    average_cm_width = np.mean(current_valid_sequence_widths)
                    candidate_cm_widths_in_pixels.append(average_cm_width)
                    
    if not candidate_cm_widths_in_pixels:
        raise ValueError("No consistent ruler mark pattern found that meets all criteria.")
        
    estimated_pixels_per_cm = np.median(candidate_cm_widths_in_pixels)
    if estimated_pixels_per_cm <= 1:
        raise ValueError(f"Estimated pixels_per_cm ({estimated_pixels_per_cm:.2f}) is too small to be valid.")
        
    return float(estimated_pixels_per_cm) # Only returns scale now
