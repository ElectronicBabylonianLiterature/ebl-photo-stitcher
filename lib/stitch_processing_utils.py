import cv2
import numpy as np
import os
try:
    from image_utils import paste_image_onto_canvas, convert_to_bgr_if_needed, resize_image_maintain_aspect
except ImportError:
    print("ERROR: stitch_processing_utils.py - Could not import from image_utils.py")
    def paste_image_onto_canvas(*args): raise ImportError("paste_image_onto_canvas missing")
    def convert_to_bgr_if_needed(img): return img
    def resize_image_maintain_aspect(*args): raise ImportError("resize_image_maintain_aspect missing")

def resize_tablet_views_relative_to_obverse(loaded_images_dictionary):
    obverse_image = loaded_images_dictionary.get("obverse")
    if not isinstance(obverse_image, np.ndarray) or obverse_image.size == 0:
        raise ValueError("Obverse image is not a valid NumPy array or is empty for resizing.")
    obv_h, obv_w = obverse_image.shape[:2]

    views_to_resize = {
        "left": {"axis": 0, "match_dim": obv_h}, 
        "right": {"axis": 0, "match_dim": obv_h},
        "top": {"axis": 1, "match_dim": obv_w}, 
        "bottom": {"axis": 1, "match_dim": obv_w},
        "reverse": {"axis": 1, "match_dim": obv_w}
    }
    for view_key, resize_params in views_to_resize.items():
        current_view_image = loaded_images_dictionary.get(view_key)
        if isinstance(current_view_image, np.ndarray) and current_view_image.size > 0:
            loaded_images_dictionary[view_key] = resize_image_maintain_aspect(
                current_view_image, resize_params["match_dim"], resize_params["axis"]
            )
        elif current_view_image is not None: 
            loaded_images_dictionary[view_key] = None
    return loaded_images_dictionary

def get_image_dimension(images_dict, key, axis_index):
    image = images_dict.get(key)
    if isinstance(image, np.ndarray) and image.ndim >= 2 and image.size > 0:
        return image.shape[axis_index]
    return 0

def calculate_stitching_canvas_layout(images_dict, view_gap_px, ruler_padding_px):
    obv_h = get_image_dimension(images_dict, "obverse", 0)
    obv_w = get_image_dimension(images_dict, "obverse", 1)
    if obv_h == 0 or obv_w == 0: 
        raise ValueError("Obverse image has zero dimensions in calculate_stitching_canvas_layout.")

    l_w=get_image_dimension(images_dict,"left",1); r_w=get_image_dimension(images_dict,"right",1)
    b_h=get_image_dimension(images_dict,"bottom",0); rev_h=get_image_dimension(images_dict,"reverse",0)
    t_h=get_image_dimension(images_dict,"top",0); rul_h=get_image_dimension(images_dict,"ruler",0)
    rul_w=get_image_dimension(images_dict,"ruler",1)

    row1_w = l_w + (view_gap_px if l_w > 0 and obv_w > 0 else 0) + obv_w + \
             (view_gap_px if r_w > 0 and obv_w > 0 else 0) + r_w
    
    canvas_w = max(row1_w, obv_w, get_image_dimension(images_dict,"bottom",1), \
                   get_image_dimension(images_dict,"reverse",1), get_image_dimension(images_dict,"top",1),rul_w) + 200
    
    current_height_sum = obv_h
    if b_h > 0: current_height_sum += view_gap_px + b_h
    if rev_h > 0: current_height_sum += view_gap_px + rev_h
    if t_h > 0: current_height_sum += view_gap_px + t_h
    if rul_h > 0: current_height_sum += ruler_padding_px + rul_h
    canvas_h = current_height_sum + 200
    
    coords = {}; y_curr = 50
    start_x_row1 = (canvas_w - row1_w) // 2 if row1_w > 0 else (canvas_w - obv_w) // 2

    if images_dict.get("left") is not None and images_dict.get("left").size > 0:
        coords["left"]=(start_x_row1, y_curr)
    
    obverse_x_pos = start_x_row1 + (l_w + view_gap_px if l_w > 0 else 0)
    coords["obverse"]=(obverse_x_pos, y_curr)
    
    if images_dict.get("right") is not None and images_dict.get("right").size > 0:
        coords["right"]=(obverse_x_pos + obv_w + view_gap_px, y_curr)
    y_curr += obv_h
    
    for vk in ["bottom","reverse","top"]:
        img_view = images_dict.get(vk)
        if img_view is not None and img_view.size > 0: 
            y_curr+=view_gap_px; coords[vk]=((obverse_x_pos+(obv_w-img_view.shape[1])//2),y_curr); y_curr+=img_view.shape[0]; coords[vk+"_bottom_y"]=y_curr
    
    if images_dict.get("ruler") is not None and images_dict.get("ruler").size > 0: 
        y_curr+=ruler_padding_px; coords["ruler"]=((obverse_x_pos+(obv_w-rul_w)//2),y_curr)
    
    y_rot_align = coords.get("reverse_bottom_y", y_curr)
    
    left_img_for_rot = images_dict.get("left")
    if isinstance(left_img_for_rot, np.ndarray) and left_img_for_rot.size > 0: 
        img_data = convert_to_bgr_if_needed(left_img_for_rot) 
        if img_data is not None and img_data.size > 0:
            l_rot=cv2.rotate(img_data,cv2.ROTATE_180); images_dict["left_rotated"]=l_rot; 
            coords["left_rotated"]=(coords.get("left",(0,0))[0],y_rot_align-l_rot.shape[0])
            
    right_img_for_rot = images_dict.get("right")
    if isinstance(right_img_for_rot, np.ndarray) and right_img_for_rot.size > 0:
        img_data = convert_to_bgr_if_needed(right_img_for_rot)
        if img_data is not None and img_data.size > 0:
            r_rot=cv2.rotate(img_data,cv2.ROTATE_180); images_dict["right_rotated"]=r_rot; 
            coords["right_rotated"]=(coords.get("right",(0,0))[0],y_rot_align-r_rot.shape[0])
            
    return int(canvas_w), int(canvas_h), coords, images_dict

def add_logo_to_image_array(content_img_array, logo_image_path, canvas_bg_color, max_width_fraction, padding_above, padding_below):
    if not logo_image_path or not os.path.exists(logo_image_path): return content_img_array
    logo_original_bgr_or_bgra = cv2.imread(logo_image_path, cv2.IMREAD_UNCHANGED)
    if logo_original_bgr_or_bgra is None or logo_original_bgr_or_bgra.size == 0: return content_img_array
    
    content_h, content_w = content_img_array.shape[:2]; loh, low = logo_original_bgr_or_bgra.shape[:2]; logo_res = logo_original_bgr_or_bgra
    if low > content_w * max_width_fraction and low > 0 and content_w > 0: 
        nlw = int(content_w * max_width_fraction); sr = nlw/low if low > 0 else 1.0; nlh = int(loh*sr)
        if nlw>0 and nlh>0: logo_res = cv2.resize(logo_original_bgr_or_bgra,(nlw,nlh),interpolation=cv2.INTER_AREA)
    
    lh, lw = logo_res.shape[:2]
    cnv_lw=max(content_w,lw); cnv_lh=content_h+padding_above+lh+padding_below
    cnv_w_logo=np.full((cnv_lh,cnv_lw,3),canvas_bg_color,dtype=np.uint8)
    paste_image_onto_canvas(cnv_w_logo,content_img_array,(cnv_lw-content_w)//2,0)
    paste_image_onto_canvas(cnv_w_logo,logo_res,(cnv_lw-lw)//2,content_h+padding_above)
    return cnv_w_logo

def crop_canvas_to_content_with_margin(image_array_to_crop, background_color_bgr, margin_px_around):
    if image_array_to_crop is None or image_array_to_crop.size == 0: return image_array_to_crop
    
    grayscale_image = cv2.cvtColor(image_array_to_crop, cv2.COLOR_BGR2GRAY)
    if grayscale_image is None or grayscale_image.size == 0 : # Check conversion result
        print("      Warning: Grayscale conversion failed or resulted in empty image for cropping.")
        return image_array_to_crop # Return original if grayscale fails

    final_content_image = image_array_to_crop 
    
    # Determine min_bg_val as a simple integer
    if isinstance(background_color_bgr, (list, tuple, np.ndarray)) and len(background_color_bgr) > 0:
        min_bg_val = int(np.min(background_color_bgr))
    elif isinstance(background_color_bgr, (int, float)):
        min_bg_val = int(background_color_bgr)
    else: # Fallback if background_color_bgr is unexpected type
        print(f"      Warning: Unexpected background_color_bgr type: {type(background_color_bgr)}. Defaulting min_bg_val to 0.")
        min_bg_val = 0
    
    lower_bound_for_inrange = int(min_bg_val + 1) # Explicitly cast to int
    upper_bound_for_inrange = 255 # This is already an int

    # Debug prints
    # print(f"        DEBUG crop: grayscale_image.shape={grayscale_image.shape}, .dtype={grayscale_image.dtype}")
    # print(f"        DEBUG crop: lowerb={lower_bound_for_inrange} (type: {type(lower_bound_for_inrange)})")
    # print(f"        DEBUG crop: upperb={upper_bound_for_inrange} (type: {type(upper_bound_for_inrange)})")

    # Check if any pixel is significantly different from background
    if np.any(grayscale_image > (min_bg_val + 5)): 
        try:
            foreground_pixel_mask = cv2.inRange(grayscale_image, lower_bound_for_inrange, upper_bound_for_inrange)
            content_pixel_coordinates = cv2.findNonZero(foreground_pixel_mask)
            if content_pixel_coordinates is not None: 
                x_coord, y_coord, width_val, height_val = cv2.boundingRect(content_pixel_coordinates)
                if width_val > 0 and height_val > 0: 
                    final_content_image = image_array_to_crop[y_coord : y_coord + height_val, x_coord : x_coord + width_val]
        except cv2.error as e:
            print(f"      ERROR during cv2.inRange or cv2.findNonZero in crop: {e}")
            print(f"        grayscale_image.shape={grayscale_image.shape}, .dtype={grayscale_image.dtype}")
            print(f"        lowerb={lower_bound_for_inrange}, upperb={upper_bound_for_inrange}")
            # Fallback to not cropping if inRange fails
            final_content_image = image_array_to_crop


    content_h, content_w = final_content_image.shape[:2]
    if content_h == 0 or content_w == 0: return final_content_image

    output_canvas_h = content_h + 2 * margin_px_around
    output_canvas_w = content_w + 2 * margin_px_around
    
    output_canvas_final = np.full((output_canvas_h, output_canvas_w, 3), background_color_bgr, dtype=np.uint8)
    paste_image_onto_canvas(output_canvas_final, final_content_image, margin_px_around, margin_px_around)
    return output_canvas_final
