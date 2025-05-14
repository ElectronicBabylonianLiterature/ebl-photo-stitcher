
import cv2
import numpy as np
import math


def detect_dominant_corner_background(image_bgr, corner_size_fraction=0.1, brightness_threshold=127):
    """
    Detects if the dominant background color in the corners is light or dark.
    Args:
        image_bgr: The input image (BGR).
        corner_size_fraction: Fraction of image dimension for corner sample size.
        brightness_threshold: Threshold to distinguish light from dark.
    Returns:
        tuple: BGR color (0,0,0) for black or (255,255,255) for white.
    """
    h, w = image_bgr.shape[:2]
    cs = int(min(h, w) * corner_size_fraction)

    corners = [
        image_bgr[0:cs, 0:cs],
        image_bgr[0:cs, w - cs:w],
        image_bgr[h - cs:h, 0:cs],
        image_bgr[h - cs:h, w - cs:w]
    ]

    avg_brightness_list = []
    for corner in corners:
        if corner.size > 0:

            gray_corner = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)
            avg_brightness_list.append(np.mean(gray_corner))

    if not avg_brightness_list:
        print("    Warning: Could not sample corner brightness. Defaulting to black background detection.")
        return (0, 0, 0)

    overall_avg_brightness = np.mean(avg_brightness_list)
    print(f"    Overall average corner brightness: {overall_avg_brightness:.2f}")

    if overall_avg_brightness > brightness_threshold:
        print("    Detected predominantly LIGHT background from corners.")
        return (255, 255, 255)
    else:
        print("    Detected predominantly DARK background from corners.")
        return (0, 0, 0)


def create_object_mask(image_bgr, background_color_bgr, color_tolerance):
    """
    Creates a binary mask where the object(s) are white and background is black.
    """
    lower_bound = np.array([max(0, c - color_tolerance) for c in background_color_bgr])
    upper_bound = np.array([min(255, c + color_tolerance)
                           for c in background_color_bgr])

    background_pixel_mask = cv2.inRange(image_bgr, lower_bound, upper_bound)
    object_mask = cv2.bitwise_not(background_pixel_mask)

    kernel = np.ones((3, 3), np.uint8)
    object_mask_cleaned = cv2.morphologyEx(
        object_mask, cv2.MORPH_OPEN, kernel, iterations=2)
    object_mask_cleaned = cv2.morphologyEx(
        object_mask_cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)

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

    contours, _ = cv2.findContours(
        object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= total_image_area * min_area_fraction:
            valid_contours.append(contour)

    if not valid_contours:
        return None

    closest_contour = None
    min_distance_to_center = float('inf')

    for contour in valid_contours:
        M = cv2.moments(contour)
        if M["m00"] == 0:
            continue

        centroid_x = int(M["m10"] / M["m00"])
        centroid_y = int(M["m01"] / M["m00"])

        distance = math.sqrt((centroid_x - image_center_x)**2
                             + (centroid_y - image_center_y)**2)

        if distance < min_distance_to_center:
            min_distance_to_center = distance
            closest_contour = contour

    return closest_contour
