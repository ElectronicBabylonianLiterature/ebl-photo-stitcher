import cv2
import numpy as np
import os

def get_mask_bounding_box(mask_array):
    rows_with_true = np.any(mask_array, axis=1)
    cols_with_true = np.any(mask_array, axis=0)
    if not np.any(rows_with_true) or not np.any(cols_with_true):
        return None
    ymin, ymax = np.where(rows_with_true)[0][[0, -1]]
    xmin, xmax = np.where(cols_with_true)[0][[0, -1]]
    return xmin, ymin, xmax + 1, ymax + 1

def convert_to_bgr_if_needed(image_array):
    if image_array is None or image_array.size == 0: 
        return None # Explicitly return None for empty or None input
    
    if len(image_array.shape) == 2: # Grayscale
        converted = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
        return converted if converted.size > 0 else None
    elif len(image_array.shape) == 3 and image_array.shape[2] == 4: # BGRA
        return image_array # Return as is, paste_image_onto_canvas will handle alpha
    elif len(image_array.shape) == 3 and image_array.shape[2] == 3: # BGR
        return image_array
    
    print(f"Warning: Image has unsupported shape {image_array.shape}. Cannot convert to BGR.")
    return None # Return None for unhandled shapes

def resize_image_maintain_aspect(image_to_resize, target_dimension_px, match_axis, interpolation_method=cv2.INTER_AREA):
    if image_to_resize is None or image_to_resize.size == 0: 
        return None
    
    height, width = image_to_resize.shape[:2]
    if height == 0 or width == 0: 
        return None # Cannot resize image with zero dimension
    
    scale_factor = 1.0
    if match_axis == 0: # Match height
        if height != target_dimension_px: scale_factor = target_dimension_px / height
    elif match_axis == 1: # Match width
        if width != target_dimension_px: scale_factor = target_dimension_px / width
    else: 
        return image_to_resize # Invalid axis, return original (or None if it was None)
        
    if abs(scale_factor - 1.0) < 1e-3: # If scale factor is effectively 1
        return image_to_resize

    new_width = int(round(width * scale_factor))
    new_height = int(round(height * scale_factor))

    if new_width <= 0 or new_height <= 0: 
        print(f"Warning: Resize resulted in invalid dimensions ({new_width}x{new_height}).")
        return None # Return None for invalid resize dimensions
        
    resized_image = cv2.resize(image_to_resize, (new_width, new_height), interpolation=interpolation_method)
    return resized_image if resized_image.size > 0 else None


def paste_image_onto_canvas(canvas_array, image_to_paste, top_left_x, top_left_y):
    if image_to_paste is None or image_to_paste.size == 0 or canvas_array is None: return
    
    img_h, img_w = image_to_paste.shape[:2]
    canvas_h, canvas_w = canvas_array.shape[:2]

    y1_canvas, y2_canvas = top_left_y, top_left_y + img_h
    x1_canvas, x2_canvas = top_left_x, top_left_x + img_w

    if x1_canvas >= canvas_w or y1_canvas >= canvas_h or x2_canvas <= 0 or y2_canvas <= 0: return

    roi_y1_c = max(0, y1_canvas); roi_y2_c = min(canvas_h, y2_canvas)
    roi_x1_c = max(0, x1_canvas); roi_x2_c = min(canvas_w, x2_canvas)
    src_y1 = max(0, -y1_canvas); src_y2 = img_h - max(0, y2_canvas - canvas_h)
    src_x1 = max(0, -x1_canvas); src_x2 = img_w - max(0, x2_canvas - canvas_w)
    
    if roi_y1_c >= roi_y2_c or roi_x1_c >= roi_x2_c or src_y1 >= src_y2 or src_x1 >= src_x2: return

    img_cropped = image_to_paste[src_y1:src_y2, src_x1:src_x2]
    if img_cropped.size == 0: return

    target_roi = canvas_array[roi_y1_c:roi_y2_c, roi_x1_c:roi_x2_c]
    
    # Ensure shapes match for direct assignment or blending
    if target_roi.shape[0] != img_cropped.shape[0] or target_roi.shape[1] != img_cropped.shape[1]:
        # This can happen if the source image is larger than the available space in the clipped ROI
        # Adjust the cropped source image to fit the target ROI
        h_target_roi, w_target_roi = target_roi.shape[:2]
        if h_target_roi <= 0 or w_target_roi <=0 : return # Target ROI has no area
        
        img_cropped_resized = cv2.resize(img_cropped, (w_target_roi, h_target_roi), interpolation=cv2.INTER_AREA)
        if img_cropped_resized.size == 0: return
        img_cropped = img_cropped_resized # Use the resized version

    if len(img_cropped.shape) == 3 and img_cropped.shape[2] == 4: # BGRA
        alpha = img_cropped[:,:,3]/255.0; bgr = img_cropped[:,:,:3]
        for c in range(3): target_roi[:,:,c] = bgr[:,:,c]*alpha + target_roi[:,:,c]*(1.0-alpha)
    elif len(img_cropped.shape) == 3 and img_cropped.shape[2] == 3: target_roi[:] = img_cropped # BGR
    elif len(img_cropped.shape) == 2 : target_roi[:] = cv2.cvtColor(img_cropped, cv2.COLOR_GRAY2BGR) # Grayscale
