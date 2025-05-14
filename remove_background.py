import cv2
import numpy as np
import math

def create_object_mask(image_bgr, background_color_bgr, color_tolerance):
    """
    Creates a binary mask where the object(s) are white and background is black.
    """
    lower_bound = np.array([max(0, c - color_tolerance) for c in background_color_bgr])
    upper_bound = np.array([min(255, c + color_tolerance) for c in background_color_bgr])
    
    # Create a mask where 'True' (or 255) indicates a pixel *close* to the background color
    background_pixel_mask = cv2.inRange(image_bgr, lower_bound, upper_bound)
    
    # Invert the mask to get the object(s) mask (object pixels are white 255)
    object_mask = cv2.bitwise_not(background_pixel_mask)

    # Optional: Clean up mask (remove small noise and fill small holes)
    kernel = np.ones((3, 3), np.uint8)
    object_mask_cleaned = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, kernel, iterations=2)
    object_mask_cleaned = cv2.morphologyEx(object_mask_cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return object_mask_cleaned

def select_center_contour(image_bgr, object_mask, min_area_fraction):
    """
    Selects the contour from the object_mask that is closest to the image center
    and meets the minimum area requirement.
    """
    h, w = image_bgr.shape[:2]
    image_center_x = w / 2
    image_center_y = h / 2
    total_image_area = h * w

    contours, _ = cv2.findContours(object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None # No contours found

    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= total_image_area * min_area_fraction:
            valid_contours.append(contour)

    if not valid_contours:
         return None # No contours meet minimum area

    closest_contour = None
    min_distance_to_center = float('inf')

    for contour in valid_contours:
        M = cv2.moments(contour)
        if M["m00"] == 0: continue # Avoid division by zero
        
        centroid_x = int(M["m10"] / M["m00"])
        centroid_y = int(M["m01"] / M["m00"])
        
        distance = math.sqrt((centroid_x - image_center_x)**2 + (centroid_y - image_center_y)**2)
        
        if distance < min_distance_to_center:
            min_distance_to_center = distance
            closest_contour = contour
            
    return closest_contour
