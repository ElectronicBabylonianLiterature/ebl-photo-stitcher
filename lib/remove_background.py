import cv2
import numpy as np
import math

def detect_dominant_corner_background_color(image_bgr_array, corner_fraction=0.1, brightness_threshold=127):
    img_height, img_width = image_bgr_array.shape[:2]
    sample_size = int(min(img_height, img_width) * corner_fraction)
    
    corner_sections_list = [
        image_bgr_array[0:sample_size, 0:sample_size],
        image_bgr_array[0:sample_size, img_width - sample_size:img_width],
        image_bgr_array[img_height - sample_size:img_height, 0:sample_size],
        image_bgr_array[img_height - sample_size:img_height, img_width - sample_size:img_width]
    ]
    
    brightness_values = []
    for section in corner_sections_list:
        if section.size > 0:
            gray_section = cv2.cvtColor(section, cv2.COLOR_BGR2GRAY)
            brightness_values.append(np.mean(gray_section))
            
    if not brightness_values: return (0, 0, 0) 
    
    average_overall_brightness = np.mean(brightness_values)
    return (255, 255, 255) if average_overall_brightness > brightness_threshold else (0, 0, 0)

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
