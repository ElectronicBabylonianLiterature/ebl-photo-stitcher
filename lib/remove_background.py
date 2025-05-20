import cv2
import numpy as np
import math

import cv2
import numpy as np

def detect_dominant_corner_background_color(image_bgr_array, corner_fraction=0.7, brightness_threshold=127, museum_selection=None):
    # This function should now return the actual average BGR color of the corners.
    # The brightness_threshold parameter might become less relevant for determining the *color*,
    # but could still be used for a logic like "if it's very dark, treat it as black background, otherwise compute average color".
    # For now, let's just compute the average color.

    img_height, img_width = image_bgr_array.shape[:2]
    sample_size = int(min(img_height, img_width) * corner_fraction)

    corner_sections_list = [
        image_bgr_array[0:sample_size, 0:sample_size],
        image_bgr_array[0:sample_size, img_width - sample_size:img_width],
        image_bgr_array[img_height - sample_size:img_height, 0:sample_size],
        image_bgr_array[img_height - sample_size:img_height, img_width - sample_size:img_width]
    ]

    all_corner_pixels = []
    for section in corner_sections_list:
        if section.size > 0:
            # Reshape to a list of pixels (each pixel is a BGR tuple)
            reshaped_section = section.reshape(-1, 3)
            all_corner_pixels.extend(reshaped_section)

    if not all_corner_pixels:
        return (0, 0, 0) # Fallback if no valid corner sections

    # Convert to a NumPy array for easier averaging
    all_corner_pixels_np = np.array(all_corner_pixels)

    # Calculate the mean BGR values across all sampled corner pixels
    average_bgr_color = np.mean(all_corner_pixels_np, axis=0).astype(int)

    # Ensure the values are within the 0-255 range
    average_bgr_color_tuple = tuple(np.clip(average_bgr_color, 0, 255))

    return average_bgr_color_tuple

# The get_museum_background_color function would also need to be adjusted
# to respect the detected_bg_color more often, or have its own logic for output background.
# For now, if you want the output to be the detected background, you'd ensure
# that get_museum_background_color actually uses detected_bg_color for all cases
# or for a specific "original background" setting.
# For example, if you wanted the *output* background to always be white unless
# it's the British Museum and the detected background was dark:

def get_museum_background_color(museum_selection=None, detected_bg_color=(0, 0, 0)):
    # This function determines the FINAL background color for the output image.
    # It can be different from the *detected* background color used for removal.

    # If the detected background is dark, and it's British Museum or no museum specified,
    # we might want to keep it dark.
    if museum_selection is None or museum_selection == "British Museum":
        # Check if the detected color is 'dark' (e.g., average brightness less than 100)
        # Convert detected_bg_color to grayscale to check brightness
        # Note: A simple average of BGR is a rough brightness estimate
        if np.mean(detected_bg_color) < 100: # Example threshold for "dark"
            return detected_bg_color
        else:
            return (255, 255, 255) # Otherwise, make it white for British Museum / None if it's not dark
    else:
        # For all other museums, force white output background
        return (255, 255, 255)
    
def create_foreground_mask_from_background( # THIS IS THE CORRECT FUNCTION NAME
    image_bgr_array, background_bgr_color_tuple, color_similarity_tolerance
):
    low_bound = np.array([max(0, c - color_similarity_tolerance) for c in background_bgr_color_tuple])
    high_bound = np.array([min(255, c + color_similarity_tolerance) for c in background_bgr_color_tuple])
    
    background_only_mask = cv2.inRange(image_bgr_array, low_bound, high_bound)
    foreground_objects_mask = cv2.bitwise_not(background_only_mask)
    
    morphology_kernel = np.ones((3, 3), np.uint8)
    cleaned_foreground_mask = cv2.morphologyEx(foreground_objects_mask, cv2.MORPH_OPEN, morphology_kernel, iterations=2)
    cleaned_foreground_mask = cv2.morphologyEx(cleaned_foreground_mask, cv2.MORPH_CLOSE, morphology_kernel, iterations=2)
    return cleaned_foreground_mask

def select_contour_closest_to_image_center(
    image_bgr_array, foreground_objects_mask, min_contour_area_as_image_fraction
):
    img_height, img_width = image_bgr_array.shape[:2]
    img_center_x, img_center_y = img_width / 2, img_height / 2
    img_total_area = img_height * img_width
    
    contours_found, _ = cv2.findContours(foreground_objects_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours_found: return None
    
    qualifying_contours = [
        cnt for cnt in contours_found 
        if cv2.contourArea(cnt) >= img_total_area * min_contour_area_as_image_fraction
    ]
    if not qualifying_contours: return None
    
    best_contour, shortest_distance = None, float('inf')
    for contour_candidate in qualifying_contours:
        moments_data = cv2.moments(contour_candidate)
        if moments_data["m00"] == 0: continue 
        
        centroid_x_pos = int(moments_data["m10"] / moments_data["m00"])
        centroid_y_pos = int(moments_data["m01"] / moments_data["m00"])
        
        current_distance = math.sqrt((centroid_x_pos - img_center_x)**2 + (centroid_y_pos - img_center_y)**2)
        if current_distance < shortest_distance:
            shortest_distance, best_contour = current_distance, contour_candidate
    return best_contour

def select_ruler_like_contour_from_list(
    list_of_all_contours, image_pixel_width, image_pixel_height, 
    excluded_obj_contour=None, min_aspect_ratio_for_ruler=2.5, 
    max_width_fraction_of_image=0.95, min_width_fraction_of_image=0.05,
    min_height_fraction_of_image=0.01, max_height_fraction_of_image=0.25
):
    plausible_ruler_contours = []
    for current_contour in list_of_all_contours:
        if excluded_obj_contour is not None and \
           cv2.matchShapes(current_contour, excluded_obj_contour, cv2.CONTOURS_MATCH_I1, 0.0) < 0.1:
            continue 
            
        x_val, y_val, width_val, height_val = cv2.boundingRect(current_contour)
        if width_val == 0 or height_val == 0: continue
        
        actual_aspect_ratio = float(width_val) / height_val if width_val > height_val else float(height_val) / width_val
        width_as_image_fraction = float(width_val) / image_pixel_width
        height_as_image_fraction = float(height_val) / image_pixel_height
        
        is_plausible_width = min_width_fraction_of_image < width_as_image_fraction < max_width_fraction_of_image
        is_plausible_height = min_height_fraction_of_image < height_as_image_fraction < max_height_fraction_of_image
        
        if actual_aspect_ratio >= min_aspect_ratio_for_ruler and is_plausible_width and is_plausible_height:
            plausible_ruler_contours.append({"contour": current_contour, "area": cv2.contourArea(current_contour)})
            
    if not plausible_ruler_contours: return None
    plausible_ruler_contours.sort(key=lambda c: c["area"], reverse=True) 
    return plausible_ruler_contours[0]["contour"]
