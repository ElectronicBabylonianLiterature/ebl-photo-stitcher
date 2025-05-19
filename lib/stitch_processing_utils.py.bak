import cv2
import numpy as np
import os
try:
    from image_utils import paste_image_onto_canvas, convert_to_bgr_if_needed, resize_image_maintain_aspect
except ImportError:
    print("ERROR: stitch_processing_utils.py - Could not import from image_utils.py")

    def paste_image_onto_canvas(
        *args, **kwargs): raise ImportError("paste_image_onto_canvas missing")

    def convert_to_bgr_if_needed(img): raise ImportError(
        "convert_to_bgr_if_needed missing")
    def resize_image_maintain_aspect(
        *args, **kwargs): raise ImportError("resize_image_maintain_aspect missing")


def resize_tablet_views_relative_to_obverse(loaded_images_dictionary):
    obverse_image = loaded_images_dictionary.get("obverse")
    if not isinstance(obverse_image, np.ndarray) or obverse_image.size == 0:
        raise ValueError(
            "Obverse image is not a valid NumPy array or is empty for resizing.")
    obv_h, obv_w = obverse_image.shape[:2]
    views_to_resize = {
        "left": {"axis": 0, "match_dim": obv_h}, "right": {"axis": 0, "match_dim": obv_h},
        "top": {"axis": 1, "match_dim": obv_w}, "bottom": {"axis": 1, "match_dim": obv_w},
        "reverse": {"axis": 1, "match_dim": obv_w}}
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


def calculate_stitching_canvas_layout(images_dict, view_separation_px, ruler_top_padding_px):
    obv_h = get_image_dimension(images_dict, "obverse", 0)
    obv_w = get_image_dimension(images_dict, "obverse", 1)
    if not (obv_h > 0 and obv_w > 0):
        raise ValueError(
            "Obverse image has zero dimensions in calculate_stitching_canvas_layout.")

    l_w = get_image_dimension(images_dict, "left", 1)
    r_w = get_image_dimension(images_dict, "right", 1)
    b_h = get_image_dimension(images_dict, "bottom", 0)
    rev_h = get_image_dimension(images_dict, "reverse", 0)
    t_h = get_image_dimension(images_dict, "top", 0)
    rul_h = get_image_dimension(images_dict, "ruler", 0)
    rul_w = get_image_dimension(images_dict, "ruler", 1)

    row1_w = l_w + (view_separation_px if l_w > 0 and obv_w > 0 else 0) + obv_w + \
        (view_separation_px if r_w > 0 and obv_w > 0 else 0) + r_w
    if row1_w == 0 and obv_w > 0:
        row1_w = obv_w

    canvas_w = max(row1_w, obv_w, get_image_dimension(images_dict, "bottom", 1),
                   get_image_dimension(images_dict, "reverse", 1), get_image_dimension(images_dict, "top", 1), rul_w) + 200

    current_height_sum = obv_h
    if b_h > 0:
        current_height_sum += view_separation_px + b_h
    if rev_h > 0:
        current_height_sum += view_separation_px + rev_h
    if t_h > 0:
        current_height_sum += view_separation_px + t_h
    if rul_h > 0:
        current_height_sum += ruler_top_padding_px + rul_h
    canvas_h = current_height_sum + 200

    layout_coords = {}
    y_curr = 50  # Stores (x,y) for actual image elements
    # Store bottom y coordinates separately for alignment reference
    view_bottom_y_coords = {}

    start_x_row1 = (
        canvas_w - row1_w)//2 if row1_w > 0 else (canvas_w - obv_w)//2

    current_x_offset_for_lor_row = start_x_row1  # Used for L-O-R placement
    if images_dict.get("left") is not None and images_dict.get("left").size > 0:
        layout_coords["left"] = (current_x_offset_for_lor_row, y_curr)
        current_x_offset_for_lor_row += l_w + view_separation_px

    # X where obverse actually starts
    obverse_x_actual_pos = current_x_offset_for_lor_row
    layout_coords["obverse"] = (obverse_x_actual_pos, y_curr)
    current_x_offset_for_lor_row += obv_w  # Advance past obverse

    if images_dict.get("right") is not None and images_dict.get("right").size > 0:
        layout_coords["right"] = (
            current_x_offset_for_lor_row + view_separation_px, y_curr)

    y_curr += obv_h  # Advance Y past the first row (obverse, left, right)
    view_bottom_y_coords["obverse"] = y_curr

    for vk in ["bottom", "reverse", "top"]:
        img_view = images_dict.get(vk)
        if img_view is not None and img_view.size > 0:
            y_curr += view_separation_px
            view_x_pos = obverse_x_actual_pos+(obv_w-img_view.shape[1])//2
            layout_coords[vk] = (view_x_pos, y_curr)
            y_curr += img_view.shape[0]
            view_bottom_y_coords[vk] = y_curr  # Store bottom y of this view

    if images_dict.get("ruler") is not None and images_dict.get("ruler").size > 0:
        y_curr += ruler_top_padding_px
        ruler_x_pos = obverse_x_actual_pos+(obv_w-rul_w)//2
        layout_coords["ruler"] = (ruler_x_pos, y_curr)
        view_bottom_y_coords["ruler"] = y_curr + rul_h  # Store ruler bottom

    # Align with bottom of reverse, or current_y if reverse not present
    y_align_for_rotated = view_bottom_y_coords.get("reverse", y_curr)

    for side_key, original_coord_key in [("left", "left"), ("right", "right")]:
        side_img = images_dict.get(side_key)
        if isinstance(side_img, np.ndarray) and side_img.size > 0:
            bgr_img = convert_to_bgr_if_needed(side_img)
            if isinstance(bgr_img, np.ndarray) and bgr_img.size > 0:
                rot_img = cv2.rotate(bgr_img, cv2.ROTATE_180)
                images_dict[side_key+"_rotated"] = rot_img
                # Use start_x_row1 for left_rotated's x if original 'left' wasn't placed
                # Use (obverse_x_actual_pos + obv_w) for right_rotated's x if original 'right' wasn't placed
                orig_x_val = layout_coords.get(
                    original_coord_key, (start_x_row1 if side_key == "left" else obverse_x_actual_pos + obv_w, 0))[0]
                layout_coords[side_key+"_rotated"] = (
                    orig_x_val, y_align_for_rotated - rot_img.shape[0])

    return int(canvas_w), int(canvas_h), layout_coords, images_dict


def get_layout_bounding_box(images_dict_with_positions, layout_coordinates):
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    found_any_placed_element = False
    # Iterate only over items with (x,y) tuples
    for key, (x_coord, y_coord) in layout_coordinates.items():
        image_array = images_dict_with_positions.get(key)
        if isinstance(image_array, np.ndarray) and image_array.size > 0:
            found_any_placed_element = True
            h_img, w_img = image_array.shape[:2]
            min_x = min(min_x, x_coord)
            min_y = min(min_y, y_coord)
            max_x = max(max_x, x_coord + w_img)
            max_y = max(max_y, y_coord + h_img)
    return (min_x, min_y, max_x, max_y) if found_any_placed_element else None


def add_logo_to_image_array(content_img_array, logo_image_path, canvas_bg_color, max_width_fraction, padding_above, padding_below):
    # (Unchanged)
    if not logo_image_path or not os.path.exists(logo_image_path):
        return content_img_array
    logo_original = cv2.imread(logo_image_path, cv2.IMREAD_UNCHANGED)
    if logo_original is None or logo_original.size == 0:
        return content_img_array
    content_h, content_w = content_img_array.shape[:2]
    loh, low = logo_original.shape[:2]
    logo_res = logo_original
    if low > 0 and content_w > 0 and low > content_w * max_width_fraction:
        nlw = int(content_w * max_width_fraction)
        sr = nlw/low if low > 0 else 1.0
        nlh = int(loh*sr)
        if nlw > 0 and nlh > 0:
            logo_res = cv2.resize(logo_original, (nlw, nlh),
                                  interpolation=cv2.INTER_AREA)
    lh, lw = logo_res.shape[:2]
    cnv_lw = max(content_w, lw)
    cnv_lh = content_h+padding_above+lh+padding_below
    cnv_w_logo = np.full((cnv_lh, cnv_lw, 3), canvas_bg_color, dtype=np.uint8)
    paste_image_onto_canvas(
        cnv_w_logo, content_img_array, (cnv_lw-content_w)//2, 0)
    paste_image_onto_canvas(cnv_w_logo, logo_res,
                            (cnv_lw-lw)//2, content_h+padding_above)
    return cnv_w_logo


def crop_canvas_to_content_with_margin(image_array_to_crop, background_color_bgr_tuple, margin_px_around):
    # (Unchanged)
    if image_array_to_crop is None or image_array_to_crop.size == 0:
        return image_array_to_crop
    grayscale_image = cv2.cvtColor(image_array_to_crop, cv2.COLOR_BGR2GRAY)
    if grayscale_image is None or grayscale_image.size == 0:
        return image_array_to_crop
    final_content_image = image_array_to_crop
    mean_bg_intensity = np.mean(background_color_bgr_tuple)
    lower_b, upper_b = (int(mean_bg_intensity+1),
                        255) if mean_bg_intensity < 128 else (0, int(mean_bg_intensity-1))
    if background_color_bgr_tuple == (0, 0, 0):
        lower_b, upper_b = 1, 255
    elif background_color_bgr_tuple == (255, 255, 255):
        lower_b, upper_b = 0, 254
    elif lower_b > upper_b:
        lower_b, upper_b = (int(mean_bg_intensity)+1,
                            255) if mean_bg_intensity < 128 else (0, int(mean_bg_intensity)-1)
    is_content_present = np.any(grayscale_image > (int(
        mean_bg_intensity) + 5 if mean_bg_intensity < 128 else int(mean_bg_intensity) - 5))
    if is_content_present:
        try:
            mask = cv2.inRange(grayscale_image, lower_b, upper_b)
            coords = cv2.findNonZero(mask)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                final_content_image = image_array_to_crop[y:y+h,
                                                          x:x+w] if w > 0 and h > 0 else final_content_image
        except cv2.error as e:
            print(f" Error during crop: {e}")
    ch, cw = final_content_image.shape[:2]
    if ch == 0 or cw == 0:
        return final_content_image
    oh, ow = ch+2*margin_px_around, cw+2*margin_px_around
    out_canvas = np.full(
        (oh, ow, 3), background_color_bgr_tuple, dtype=np.uint8)
    paste_image_onto_canvas(out_canvas, final_content_image,
                            margin_px_around, margin_px_around)
    return out_canvas
