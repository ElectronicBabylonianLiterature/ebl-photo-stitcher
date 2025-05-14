import cv2
import numpy as np
import os


RULER_ROI_VERTICAL_START_FRACTION = 0
RULER_ROI_VERTICAL_END_FRACTION = 0.25

RULER_ROI_HORIZONTAL_START_FRACTION = 0.02
RULER_ROI_HORIZONTAL_END_FRACTION = 0.15

RULER_ANALYSIS_SCANLINE_COUNT = 7
RULER_MARK_BINARIZATION_THRESHOLD = 150
MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.08
MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION = 0.30
RULER_MARK_WIDTH_SIMILARITY_TOLERANCE = 0.40
MIN_ALTERNATING_MARKS_FOR_SCALE = 2


def extract_pixel_runs_from_scanline(scanline_pixel_data, binarization_threshold_value):
    binary_scanline = np.where(
        scanline_pixel_data < binarization_threshold_value, 0, 255)
    pixel_runs = []
    if binary_scanline.size == 0:
        return pixel_runs
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


def estimate_pixels_per_centimeter_from_ruler(image_filepath, ruler_position="top"):
    """
    Estimates pixels per centimeter from a ruler in an image.
    Args:
        image_filepath (str): Path to the image.
        ruler_position (str): "top", "bottom", "left", or "right".
    Returns:
        float: Estimated pixels per centimeter.
    """
    print(f"    Estimating scale with ruler at: {ruler_position}")
    input_image = cv2.imread(image_filepath)
    if input_image is None:
        raise FileNotFoundError(f"Input image not found: {image_filepath}")

    image_height_pixels, image_width_pixels = input_image.shape[:2]
    ruler_strip_roi_grayscale = None
    roi_scan_dimension_px = 0

    if ruler_position == "top":
        roi_start_y = int(image_height_pixels * RULER_ROI_VERTICAL_START_FRACTION)
        roi_end_y = int(image_height_pixels * RULER_ROI_VERTICAL_END_FRACTION)
        if not (0 <= roi_start_y < roi_end_y <= image_height_pixels):
            raise ValueError(f"Invalid TOP ROI y=[{roi_start_y}, {roi_end_y}]")
        ruler_strip_roi_color = input_image[roi_start_y:roi_end_y, :]
        roi_scan_dimension_px = ruler_strip_roi_color.shape[1]
    elif ruler_position == "bottom":
        roi_start_y = int(image_height_pixels * (1 - RULER_ROI_VERTICAL_END_FRACTION))
        roi_end_y = int(image_height_pixels * (1 - RULER_ROI_VERTICAL_START_FRACTION))
        if not (0 <= roi_start_y < roi_end_y <= image_height_pixels):
            raise ValueError(f"Invalid BOTTOM ROI y=[{roi_start_y}, {roi_end_y}]")
        ruler_strip_roi_color = input_image[roi_start_y:roi_end_y, :]
        roi_scan_dimension_px = ruler_strip_roi_color.shape[1]
    elif ruler_position == "left":
        roi_start_x = int(image_width_pixels * RULER_ROI_HORIZONTAL_START_FRACTION)
        roi_end_x = int(image_width_pixels * RULER_ROI_HORIZONTAL_END_FRACTION)
        if not (0 <= roi_start_x < roi_end_x <= image_width_pixels):
            raise ValueError(f"Invalid LEFT ROI x=[{roi_start_x}, {roi_end_x}]")
        ruler_strip_roi_color = input_image[:, roi_start_x:roi_end_x]
        roi_scan_dimension_px = ruler_strip_roi_color.shape[0]
    elif ruler_position == "right":
        roi_start_x = int(image_width_pixels * (1 - RULER_ROI_HORIZONTAL_END_FRACTION))
        roi_end_x = int(image_width_pixels * (1 - RULER_ROI_HORIZONTAL_START_FRACTION))
        if not (0 <= roi_start_x < roi_end_x <= image_width_pixels):
            raise ValueError(f"Invalid RIGHT ROI x=[{roi_start_x}, {roi_end_x}]")
        ruler_strip_roi_color = input_image[:, roi_start_x:roi_end_x]
        roi_scan_dimension_px = ruler_strip_roi_color.shape[0]
    else:
        raise ValueError(
            f"Invalid ruler_position: {ruler_position}. Must be top, bottom, left, or right.")

    if ruler_strip_roi_color.size == 0:
        raise ValueError(f"Ruler ROI empty for position '{ruler_position}'.")
    ruler_strip_roi_grayscale = cv2.cvtColor(ruler_strip_roi_color, cv2.COLOR_BGR2GRAY)

    roi_dim1_px, roi_dim2_px = ruler_strip_roi_grayscale.shape

    candidate_cm_widths_in_pixels = []
    min_mark_width_px = roi_scan_dimension_px * MIN_EXPECTED_MARK_WIDTH_ROI_FRACTION
    max_mark_width_px = roi_scan_dimension_px * MAX_EXPECTED_MARK_WIDTH_ROI_FRACTION

    for i in range(RULER_ANALYSIS_SCANLINE_COUNT):
        current_scanline_data = None
        if ruler_position in ["top", "bottom"]:
            scanline_coord = int(
                roi_dim1_px * ((i + 0.5) / RULER_ANALYSIS_SCANLINE_COUNT))
            current_scanline_data = ruler_strip_roi_grayscale[scanline_coord, :]
        elif ruler_position in ["left", "right"]:
            scanline_coord = int(
                roi_dim2_px * ((i + 0.5) / RULER_ANALYSIS_SCANLINE_COUNT))
            current_scanline_data = ruler_strip_roi_grayscale[:, scanline_coord]

        if current_scanline_data is None or current_scanline_data.size == 0:
            continue

        pixel_runs_on_scanline = extract_pixel_runs_from_scanline(
            current_scanline_data, RULER_MARK_BINARIZATION_THRESHOLD)
        if not pixel_runs_on_scanline or len(pixel_runs_on_scanline) < MIN_ALTERNATING_MARKS_FOR_SCALE:
            continue

        for j in range(len(pixel_runs_on_scanline) - (MIN_ALTERNATING_MARKS_FOR_SCALE - 1)):
            if pixel_runs_on_scanline[j]['type'] == 'black':
                initial_mark_width = pixel_runs_on_scanline[j]['width_pixels']
                if not (min_mark_width_px <= initial_mark_width <= max_mark_width_px):
                    continue

                current_valid_sequence_widths = [initial_mark_width]
                is_sequence_valid = True
                for k in range(1, MIN_ALTERNATING_MARKS_FOR_SCALE):
                    prev_mark = pixel_runs_on_scanline[j + k - 1]
                    curr_mark = pixel_runs_on_scanline[j + k]
                    if curr_mark['type'] == prev_mark['type']:
                        is_sequence_valid = False
                        break
                    mark_width = curr_mark['width_pixels']
                    if not (min_mark_width_px <= mark_width <= max_mark_width_px):
                        is_sequence_valid = False
                        break
                    if not (abs(mark_width - initial_mark_width) <= initial_mark_width * RULER_MARK_WIDTH_SIMILARITY_TOLERANCE):
                        is_sequence_valid = False
                        break
                    current_valid_sequence_widths.append(mark_width)

                if is_sequence_valid:
                    average_cm_width = np.mean(current_valid_sequence_widths)
                    candidate_cm_widths_in_pixels.append(average_cm_width)

    if not candidate_cm_widths_in_pixels:
        raise ValueError(
            "No consistent ruler mark pattern found that meets all criteria.")
    estimated_pixels_per_cm = np.median(candidate_cm_widths_in_pixels)
    if estimated_pixels_per_cm <= 1:
        raise ValueError(f"Estimated px/cm too small: {estimated_pixels_per_cm:.2f}")

    return float(estimated_pixels_per_cm)
