import cv2
import numpy as np
import os
try:
    from image_utils import paste_image_onto_canvas
except ImportError:
    print("ERROR: stitch_enhancement_utils.py - Could not import from image_utils.py")
    def paste_image_onto_canvas(*args): raise ImportError("paste_image_onto_canvas missing")

def add_logo_to_image_array(
    content_img_array, logo_image_path, canvas_bg_color, 
    max_width_fraction, padding_above, padding_below
):
    if not logo_image_path or not os.path.exists(logo_image_path): return content_img_array
    logo_original = cv2.imread(logo_image_path, cv2.IMREAD_UNCHANGED)
    if logo_original is None or logo_original.size == 0: return content_img_array
    
    content_h, content_w = content_img_array.shape[:2]
    logo_h_orig, logo_w_orig = logo_original.shape[:2]
    logo_resized = logo_original

    if logo_w_orig > content_w * max_width_fraction and logo_w_orig > 0 and content_w > 0:
        target_logo_w = int(content_w * max_width_fraction)
        scale = target_logo_w / logo_w_orig if logo_w_orig > 0 else 1.0
        target_logo_h = int(logo_h_orig * scale)
        if target_logo_w > 0 and target_logo_h > 0:
            logo_resized = cv2.resize(logo_original, (target_logo_w, target_logo_h), interpolation=cv2.INTER_AREA)
    
    final_logo_h, final_logo_w = logo_resized.shape[:2]
    canvas_w_new = max(content_w, final_logo_w)
    canvas_h_new = content_h + padding_above + final_logo_h + padding_below
    
    canvas_with_logo = np.full((canvas_h_new, canvas_w_new, 3), canvas_bg_color, dtype=np.uint8)
    paste_image_onto_canvas(canvas_with_logo, content_img_array, (canvas_w_new - content_w) // 2, 0)
    paste_image_onto_canvas(canvas_with_logo, logo_resized, (canvas_w_new - final_logo_w) // 2, content_h + padding_above)
    return canvas_with_logo

def crop_canvas_to_content_with_margin(
    image_array_to_crop, background_color_bgr_tuple, margin_px_around
):
    if image_array_to_crop is None or image_array_to_crop.size == 0: return image_array_to_crop
    
    grayscale_img = cv2.cvtColor(image_array_to_crop, cv2.COLOR_BGR2GRAY)
    if grayscale_img is None or grayscale_img.size == 0: return image_array_to_crop

    final_content_img = image_array_to_crop 
    min_bg_intensity = int(np.min(background_color_bgr_tuple)) if isinstance(background_color_bgr_tuple, (list, tuple, np.ndarray)) and len(background_color_bgr_tuple) > 0 else (int(background_color_bgr_tuple) if isinstance(background_color_bgr_tuple, (int, float)) else 0)
    
    lower_intensity_bound = int(min_bg_intensity + 1)
    upper_intensity_bound = 255
    
    if np.any(grayscale_img > (min_bg_intensity + 5)): 
        try:
            foreground_mask_pixels = cv2.inRange(grayscale_img, lower_intensity_bound, upper_intensity_bound)
            content_coords = cv2.findNonZero(foreground_mask_pixels)
            if content_coords is not None: 
                x, y, w, h = cv2.boundingRect(content_coords)
                if w > 0 and h > 0: 
                    final_content_img = image_array_to_crop[y : y + h, x : x + w]
        except cv2.error as e:
            print(f"      OpenCV Error during crop: {e}") # Keep original if error
            final_content_img = image_array_to_crop
            
    content_h_px, content_w_px = final_content_img.shape[:2]
    if content_h_px == 0 or content_w_px == 0: return final_content_img

    output_h_px = content_h_px + 2 * margin_px_around
    output_w_px = content_w_px + 2 * margin_px_around
    
    output_canvas = np.full((output_h_px, output_w_px, 3), background_color_bgr_tuple, dtype=np.uint8)
    paste_image_onto_canvas(output_canvas, final_content_img, margin_px_around, margin_px_around)
    return output_canvas
