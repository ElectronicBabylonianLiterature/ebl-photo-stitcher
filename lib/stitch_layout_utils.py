import cv2
import numpy as np
try:
    from image_utils import resize_image_maintain_aspect, convert_to_bgr_if_needed
except ImportError:
    print("FATAL ERROR: stitch_layout_utils.py cannot import from image_utils.py")
    def resize_image_maintain_aspect(*args): raise ImportError("resize_image_maintain_aspect missing")
    def convert_to_bgr_if_needed(img): return img

def resize_tablet_views_for_layout(loaded_images_dictionary):
    obverse_image = loaded_images_dictionary.get("obverse")
    if not isinstance(obverse_image, np.ndarray) or obverse_image.size == 0:
        raise ValueError("Obverse image is not valid for relative resizing.")
    obv_h, obv_w = obverse_image.shape[:2]

    resize_config = {
        "left": {"axis": 0, "match_dim": obv_h}, "right": {"axis": 0, "match_dim": obv_h},
        "top": {"axis": 1, "match_dim": obv_w}, "bottom": {"axis": 1, "match_dim": obv_w},
        "reverse": {"axis": 1, "match_dim": obv_w}
    }
    for view_key, params in resize_config.items():
        current_view = loaded_images_dictionary.get(view_key)
        if isinstance(current_view, np.ndarray) and current_view.size > 0:
            loaded_images_dictionary[view_key] = resize_image_maintain_aspect(
                current_view, params["match_dim"], params["axis"]
            )
        elif current_view is not None: # Not None, but not a usable array
            loaded_images_dictionary[view_key] = None
    return loaded_images_dictionary

def get_image_dimension(images_dict, key, axis_index):
    image = images_dict.get(key)
    if isinstance(image, np.ndarray) and image.ndim >= 2 and image.size > 0:
        return image.shape[axis_index]
    return 0

def calculate_stitching_layout_and_canvas(images_dict, view_separation_px, ruler_top_padding_px):
    obv_h = get_image_dimension(images_dict, "obverse", 0)
    obv_w = get_image_dimension(images_dict, "obverse", 1)
    if obv_h == 0 or obv_w == 0: raise ValueError("Obverse image has zero dimensions for layout.")

    l_w=get_image_dimension(images_dict,"left",1); r_w=get_image_dimension(images_dict,"right",1)
    b_h=get_image_dimension(images_dict,"bottom",0); rev_h=get_image_dimension(images_dict,"reverse",0)
    t_h=get_image_dimension(images_dict,"top",0); rul_h=get_image_dimension(images_dict,"ruler",0)
    rul_w=get_image_dimension(images_dict,"ruler",1)

    row1_w = l_w + (view_separation_px if l_w > 0 and obv_w > 0 else 0) + obv_w + \
             (view_separation_px if r_w > 0 and obv_w > 0 else 0) + r_w
    canvas_w = max(row1_w,obv_w,get_image_dimension(images_dict,"bottom",1), \
                   get_image_dimension(images_dict,"reverse",1),get_image_dimension(images_dict,"top",1),rul_w) + 200
    
    h_sum = obv_h
    for h_val in [b_h, rev_h, t_h]:
        if h_val > 0: h_sum += view_separation_px + h_val
    if rul_h > 0: h_sum += ruler_top_padding_px + rul_h
    canvas_h = h_sum + 200
    
    coords = {}; y_curr = 50
    start_x_row1 = (canvas_w - row1_w)//2 if row1_w > 0 else (canvas_w - obv_w)//2

    if images_dict.get("left") is not None and images_dict.get("left").size > 0:
        coords["left"]=(start_x_row1, y_curr)
    obv_x = start_x_row1 + (l_w + view_separation_px if l_w > 0 else 0)
    coords["obverse"]=(obv_x, y_curr)
    if images_dict.get("right") is not None and images_dict.get("right").size > 0:
        coords["right"]=(obv_x + obv_w + view_separation_px, y_curr)
    y_curr += obv_h
    
    for vk in ["bottom","reverse","top"]:
        img = images_dict.get(vk)
        if img is not None and img.size > 0: 
            y_curr+=view_separation_px; coords[vk]=((obv_x+(obv_w-img.shape[1])//2),y_curr); y_curr+=img.shape[0]; coords[vk+"_bottom_y"]=y_curr
    if images_dict.get("ruler") is not None and images_dict.get("ruler").size > 0: 
        y_curr+=ruler_top_padding_px; coords["ruler"]=((obv_x+(obv_w-rul_w)//2),y_curr)
    
    y_rot_align = coords.get("reverse_bottom_y", y_curr)
    for side_key, original_coord_key in [("left", "left"), ("right", "right")]:
        side_img = images_dict.get(side_key)
        if isinstance(side_img, np.ndarray) and side_img.size > 0:
            bgr_img = convert_to_bgr_if_needed(side_img)
            if bgr_img is not None and bgr_img.size > 0:
                rot_img = cv2.rotate(bgr_img, cv2.ROTATE_180)
                images_dict[side_key+"_rotated"] = rot_img
                orig_x = coords.get(original_coord_key, (0,0))[0] # Default to 0 if original not placed
                coords[side_key+"_rotated"] = (orig_x, y_rot_align - rot_img.shape[0])
                
    return int(canvas_w), int(canvas_h), coords, images_dict
