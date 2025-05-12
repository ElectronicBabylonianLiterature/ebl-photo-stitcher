# ruler_detector.py
import cv2
import numpy as np
import os

# --- Configuration for Ruler Detection ---
# Region of Interest (ROI) definition: Where to look for the ruler.
# These fractions are relative to the image height, measured from the TOP.
RULER_ROI_VERTICAL_START_FRACTION = 0.02  # Start looking 2% down from the top edge
RULER_ROI_VERTICAL_END_FRACTION = 0.15    # Stop looking 15% down from the top edge

# Ruler analysis parameters
RULER_ANALYSIS_SCANLINE_COUNT = 7       # How many horizontal lines to check within the ROI
RULER_SCANLINE_BINARIZATION_THRESHOLD = 150 # Pixel value threshold to distinguish dark/light marks
MIN_EXPECTED_CM_SEGMENT_WIDTH_AS_ROI_FRACTION = 0.10 # Smallest expected width of a 1cm mark (black or white) relative to ROI width
MAX_EXPECTED_CM_SEGMENT_WIDTH_AS_ROI_FRACTION = 0.30 # Largest expected width of a 1cm mark
RULER_SEGMENT_WIDTH_SIMILARITY_TOLERANCE_FRACTION = 0.40 # How much variation is allowed between consecutive detected cm marks
MIN_CONSECUTIVE_ALTERNATING_SEGMENTS_FOR_CM_ESTIMATION = 3 # Need at least 3 alternating (black/white/black or white/black/white) segments of similar width

def extract_pixel_runs_from_scanline(scanline_pixel_data, binarization_threshold_value):
    """Analyzes a single row of pixels, converting it to black/white and finding consecutive runs."""
    # Binarize: Pixels below threshold become 0 (black), others 255 (white)
    binary_scanline = np.where(scanline_pixel_data < binarization_threshold_value, 0, 255)

    pixel_runs = []
    if binary_scanline.size == 0:
        return pixel_runs

    current_run_color_type = None
    current_run_start_index = 0

    # Iterate through the binarized scanline
    for i, pixel_value in enumerate(binary_scanline):
        pixel_color_type = 'black' if pixel_value == 0 else 'white'

        if current_run_color_type is None:
            # Start of the first run
            current_run_color_type = pixel_color_type
            current_run_start_index = i
        elif pixel_color_type != current_run_color_type:
            # Color changed, end the previous run
            run_width_pixels = i - current_run_start_index
            if run_width_pixels > 0: # Only record runs with actual width
                pixel_runs.append({
                    'type': current_run_color_type,
                    'start_index': current_run_start_index,
                    'end_index': i - 1,
                    'width_pixels': run_width_pixels
                })
            # Start the new run
            current_run_color_type = pixel_color_type
            current_run_start_index = i

    # Record the last run after the loop finishes
    if current_run_color_type is not None:
        run_width_pixels = len(binary_scanline) - current_run_start_index
        if run_width_pixels > 0:
            pixel_runs.append({
                'type': current_run_color_type,
                'start_index': current_run_start_index,
                'end_index': len(binary_scanline) - 1,
                'width_pixels': run_width_pixels
            })
    return pixel_runs

def estimate_pixels_per_centimeter_from_ruler(image_filepath):
    """
    Loads an image, analyzes the top region for ruler markings (alternating black/white cm segments),
    and estimates the number of pixels that correspond to one centimeter.
    """
    input_image = cv2.imread(image_filepath)
    if input_image is None:
        raise FileNotFoundError(f"Input image not found or could not be read at: {image_filepath}")

    image_height_pixels, image_width_pixels = input_image.shape[:2]

    # Define the vertical ROI based on fractions from the TOP
    ruler_roi_start_y = int(image_height_pixels * RULER_ROI_VERTICAL_START_FRACTION)
    ruler_roi_end_y = int(image_height_pixels * RULER_ROI_VERTICAL_END_FRACTION)

    # Basic validation for ROI coordinates
    if not (0 <= ruler_roi_start_y < ruler_roi_end_y <= image_height_pixels):
        raise ValueError(f"Invalid ROI y-coordinates [{ruler_roi_start_y}, {ruler_roi_end_y}] for image height {image_height_pixels}.")

    # Extract the ROI
    ruler_strip_roi_color = input_image[ruler_roi_start_y:ruler_roi_end_y, :]
    if ruler_strip_roi_color.size == 0:
        raise ValueError("Calculated Ruler ROI is empty or invalid.")

    # Convert ROI to grayscale for analysis
    ruler_strip_roi_grayscale = cv2.cvtColor(ruler_strip_roi_color, cv2.COLOR_BGR2GRAY)
    roi_height_pixels, roi_width_pixels = ruler_strip_roi_grayscale.shape

    if roi_width_pixels == 0:
         raise ValueError("Ruler ROI width is zero.")

    candidate_cm_widths_in_pixels = []
    # Calculate expected segment width range in pixels based on ROI width
    min_segment_width_pixels = roi_width_pixels * MIN_EXPECTED_CM_SEGMENT_WIDTH_AS_ROI_FRACTION
    max_segment_width_pixels = roi_width_pixels * MAX_EXPECTED_CM_SEGMENT_WIDTH_AS_ROI_FRACTION

    print(f"Analyzing ROI: y=[{ruler_roi_start_y}:{ruler_roi_end_y}], width={roi_width_pixels}px")
    print(f"Expected cm segment width range: [{min_segment_width_pixels:.1f} - {max_segment_width_pixels:.1f}] pixels")

    # Analyze multiple horizontal scanlines within the ROI
    for i in range(RULER_ANALYSIS_SCANLINE_COUNT):
        # Distribute scanlines evenly within the ROI height
        scanline_y_coordinate = int(roi_height_pixels * ((i + 0.5) / RULER_ANALYSIS_SCANLINE_COUNT))
        current_scanline_data = ruler_strip_roi_grayscale[scanline_y_coordinate, :]

        # Find runs of black/white pixels on this scanline
        pixel_runs_on_scanline = extract_pixel_runs_from_scanline(current_scanline_data, RULER_SCANLINE_BINARIZATION_THRESHOLD)

        # Need enough runs to potentially find the required consecutive segments
        if not pixel_runs_on_scanline or len(pixel_runs_on_scanline) < MIN_CONSECUTIVE_ALTERNATING_SEGMENTS_FOR_CM_ESTIMATION:
            #print(f"Scanline {i}: Not enough pixel runs ({len(pixel_runs_on_scanline)}) found.")
            continue

        # Search for sequences of alternating colors with similar widths
        # (We check sequences starting with black marks, assuming typical ruler pattern)
        for j in range(len(pixel_runs_on_scanline) - (MIN_CONSECUTIVE_ALTERNATING_SEGMENTS_FOR_CM_ESTIMATION - 1)):
            # Check if the first segment in the potential sequence is black
            if pixel_runs_on_scanline[j]['type'] == 'black':
                initial_segment_width = pixel_runs_on_scanline[j]['width_pixels']

                # Check if the first segment's width is within the expected range for a 1cm mark
                if not (min_segment_width_pixels <= initial_segment_width <= max_segment_width_pixels):
                    continue # This segment is too small or too large, skip

                # Now check the subsequent segments for alternating color and similar width
                current_valid_sequence_widths = [initial_segment_width]
                is_sequence_valid = True

                for k in range(1, MIN_CONSECUTIVE_ALTERNATING_SEGMENTS_FOR_CM_ESTIMATION):
                    if (j + k) >= len(pixel_runs_on_scanline): # Should not happen due to outer loop range, but good practice
                        is_sequence_valid = False; break

                    previous_segment_in_sequence = pixel_runs_on_scanline[j + k - 1]
                    current_segment_in_sequence = pixel_runs_on_scanline[j + k]

                    # Check for alternating color
                    if current_segment_in_sequence['type'] == previous_segment_in_sequence['type']:
                        is_sequence_valid = False; break # Sequence broken (e.g., black-black)

                    # Check width constraints for the current segment
                    segment_width = current_segment_in_sequence['width_pixels']
                    if not (min_segment_width_pixels <= segment_width <= max_segment_width_pixels):
                        is_sequence_valid = False; break # Segment width out of range

                    # Check similarity: width must be close to the *first* segment's width in the sequence
                    if not (abs(segment_width - initial_segment_width) <= initial_segment_width * RULER_SEGMENT_WIDTH_SIMILARITY_TOLERANCE_FRACTION):
                        is_sequence_valid = False; break # Width differs too much

                    # If checks pass, add width to the list for this sequence
                    current_valid_sequence_widths.append(segment_width)

                # If the inner loop completed without breaking, we found a valid sequence
                if is_sequence_valid:
                    # Calculate the average width of the segments in this valid sequence
                    average_cm_width_of_sequence = np.mean(current_valid_sequence_widths)
                    candidate_cm_widths_in_pixels.append(average_cm_width_of_sequence)
                    # print(f"Scanline {i}: Found valid sequence at index {j}, avg width: {average_cm_width_of_sequence:.2f}px")
                    # Optimization: If we find one sequence, we can potentially stop checking the rest of this scanline,
                    # but checking all might give more robust results if there are multiple patterns.
                    # For now, we collect all candidates.

    # After checking all scanlines, evaluate the findings
    if not candidate_cm_widths_in_pixels:
        raise ValueError("Could not find any consistent alternating segment pattern matching the criteria for CM estimation in the ROI.")

    # Use the median of all found candidate widths as the final estimate
    # Median is generally more robust to outliers than the mean
    estimated_pixels_per_cm = np.median(candidate_cm_widths_in_pixels)

    if estimated_pixels_per_cm <= 1: # Basic sanity check
         raise ValueError(f"Estimated pixels_per_cm ({estimated_pixels_per_cm:.2f}) is too small to be valid.")

    print(f"Found {len(candidate_cm_widths_in_pixels)} candidate CM width estimates.")
    print(f"Final estimated Pixels per CM: {estimated_pixels_per_cm:.2f}")
    return float(estimated_pixels_per_cm)

# --- Example Usage ---
if __name__ == "__main__":
    # Replace with the path to your image that has the ruler at the top
    source_image_file = "add_virtual_logo_example_ruler_at_top.jpg" # IMPORTANT: Use an image with ruler at the top!

    if not os.path.exists(source_image_file):
        print(f"FATAL: Source image '{source_image_file}' not found.")
    else:
        try:
            px_per_cm = estimate_pixels_per_centimeter_from_ruler(source_image_file)
            print(f"\nSuccessfully estimated: {px_per_cm:.2f} pixels per centimeter.")
            # In a real application, you would pass this value to the next script/function.
        except (FileNotFoundError, ValueError, Exception) as e:
            print(f"\nError during ruler detection: {e}")