# Coordinate layout calculation for tablet image components
import cv2
import numpy as np
try:
    from image_utils import resize_image_maintain_aspect, convert_to_bgr_if_needed
except ImportError:
    print("FATAL ERROR: stitch_layout_manager.py cannot import from image_utils.py")
    def resize_image_maintain_aspect(*args): raise ImportError("resize_image_maintain_aspect missing")
    def convert_to_bgr_if_needed(img): return img
    
from stitch_config import (
    STITCH_VIEW_GAP_PX,
    STITCH_RULER_PADDING_PX
)

def get_image_dimension(image_or_list, axis_index, blend_overlap_px=0):
    """Get height or width dimension of an image or a list of images (calculating post-blend dimension for lists)."""
    if isinstance(image_or_list, np.ndarray) and image_or_list.ndim >= 2 and image_or_list.size > 0:
        return image_or_list.shape[axis_index]
    elif isinstance(image_or_list, list) and image_or_list:
        if not image_or_list: return 0
        # For a list, calculate the dimension after hypothetical blending.
        # Axis_index: 0 for height, 1 for width.
        if axis_index == 0: # Vertical blending - sum of heights minus overlaps, width is min width
            total_height = 0
            min_common_width = float('inf')
            for i, img in enumerate(image_or_list):
                if not isinstance(img, np.ndarray) or img.size == 0: continue
                total_height += img.shape[0]
                min_common_width = min(min_common_width, img.shape[1])
                if i > 0: total_height -= blend_overlap_px
            # The final width of a vertically blended sequence is min_common_width
            # This function is asked for a single dimension, so if axis_index is 1 (width) for a vertical blend:
            # return min_common_width if min_common_width != float('inf') else 0
            # However, the primary use here is to get the length along the blending axis.
            return total_height
        else: # Horizontal blending - sum of widths minus overlaps, height is min height
            total_width = 0
            min_common_height = float('inf')
            for i, img in enumerate(image_or_list):
                if not isinstance(img, np.ndarray) or img.size == 0: continue
                total_width += img.shape[1]
                min_common_height = min(min_common_height, img.shape[0])
                if i > 0: total_width -= blend_overlap_px
            # The final height of a horizontally blended sequence is min_common_height
            # return min_common_height if min_common_height != float('inf') else 0
            return total_width
    return 0

def resize_tablet_views_for_layout(loaded_images_dictionary):
    """
    Resize all tablet views. If obverse is present, other main views are resized relative to it.
    Handles single images and lists of images (sequences).
    """
    obverse_image_data = loaded_images_dictionary.get("obverse")
    
    # Determine obverse dimensions (could be single image or sequence)
    # For sequences, the 'obverse' itself isn't typically a sequence that needs blending for this purpose.
    # We assume 'obverse' if present, is a single image or the primary image of a set.
    # If 'obverse' itself could be a sequence to be blended, its primary image should be used for ref dims.
    obv_h, obv_w = 0, 0
    if isinstance(obverse_image_data, np.ndarray) and obverse_image_data.size > 0:
        obv_h, obv_w = obverse_image_data.shape[:2]
    elif isinstance(obverse_image_data, list) and obverse_image_data and isinstance(obverse_image_data[0], np.ndarray):
        # If obverse is a list (e.g. from custom layout), use the first image for reference dimensions.
        obv_h, obv_w = obverse_image_data[0].shape[:2]
        print("      Resize: 'obverse' is a list, using first image for reference dimensions.")

    if obv_h == 0 or obv_w == 0:
        # If no valid obverse, we cannot do relative resizing. 
        # Images will be used as-is or a default size could be applied.
        # For now, let's print a warning and proceed without relative resizing for other views.
        print("      Warn: Obverse image not valid for relative resizing. Skipping relative resize of other views.")
        # We still need to process lists if they exist, just not relative to obverse.
        # The function should still return the dictionary, possibly with original sizes or individually processed lists.
        # Let's ensure all images in lists are at least processed, even if not resized relative to obverse.
        processed_dict = {}
        for view_key, image_data_item in loaded_images_dictionary.items():
            if isinstance(image_data_item, list):
                processed_list = [img for img in image_data_item if isinstance(img, np.ndarray) and img.size > 0]
                processed_dict[view_key] = processed_list if processed_list else None
            elif isinstance(image_data_item, np.ndarray) and image_data_item.size > 0:
                processed_dict[view_key] = image_data_item
            else:
                processed_dict[view_key] = None
        return processed_dict

    # Standard resize config relative to obverse
    resize_config = {
        # view_key: {axis_to_match_obverse_dim, obverse_dim_to_match}
        "left": {"axis": 0, "match_dim": obv_h},   # Match obverse height
        "right": {"axis": 0, "match_dim": obv_h},  # Match obverse height
        "top": {"axis": 1, "match_dim": obv_w},    # Match obverse width
        "bottom": {"axis": 1, "match_dim": obv_w}, # Match obverse width
        "reverse": {"axis": 1, "match_dim": obv_w} # Match obverse width
        # Intermediate sequences will also be resized based on these rules if their keys match.
        # E.g., "obverse_top_intermediate_sequence" would align with "top" rule if not explicitly handled.
    }

    output_resized_images = {}
    for view_key, image_data in loaded_images_dictionary.items():
        if view_key == "obverse": # Obverse is the reference, already handled
            output_resized_images[view_key] = obverse_image_data
            continue

        params = None
        # Find matching resize rule (e.g. "obverse_top_intermediate" uses "top" rule)
        for r_key, r_params in resize_config.items():
            if r_key in view_key: # Simple substring match, might need refinement
                params = r_params
                break
        if not params and "ruler" not in view_key: # Ruler is not typically resized relative to obverse
             # If no specific rule, and not obverse or ruler, decide a default or skip.
             # For now, keep original if no rule applies (e.g. for custom arbitrary view names)
            print(f"      Resize: No specific resize rule for '{view_key}'. Keeping original.")
            output_resized_images[view_key] = image_data
            continue
        elif "ruler" in view_key:
            output_resized_images[view_key] = image_data # Keep ruler as is
            continue

        if isinstance(image_data, np.ndarray) and image_data.size > 0:
            output_resized_images[view_key] = resize_image_maintain_aspect(
                image_data, params["match_dim"], params["axis"]
            )
        elif isinstance(image_data, list):
            resized_sequence = []
            for img_in_seq in image_data:
                if isinstance(img_in_seq, np.ndarray) and img_in_seq.size > 0:
                    resized_img = resize_image_maintain_aspect(
                        img_in_seq, params["match_dim"], params["axis"]
                    )
                    resized_sequence.append(resized_img)
                else:
                    resized_sequence.append(None) # Keep placeholder for failed loads
            output_resized_images[view_key] = [rs for rs in resized_sequence if rs is not None] if any(rs is not None for rs in resized_sequence) else None
        elif image_data is not None: # Was loaded, but not array or list (should not happen)
            output_resized_images[view_key] = None
            print(f"      Warn: Resize - Unexpected data type for {view_key}: {type(image_data)}")
        else:
            output_resized_images[view_key] = None # Was None initially
            
    return output_resized_images

def calculate_stitching_layout(images_dict, view_gap_px=STITCH_VIEW_GAP_PX, ruler_padding_px=STITCH_RULER_PADDING_PX, custom_layout=None, blend_overlap_px=0):
    """
    Calculate the canvas dimensions and coordinates for placing each image or blended sequence.
    Returns canvas dimensions, coordinate map, and the input images_dict.
    MODIFIED to handle sequences and use their post-blending dimensions for layout.
    The layout logic is still based on a standard 6-view + ruler concept but uses actual
    dimensions from images_dict (which could be single images or blended sequences).
    
    Also adds rotated left and right views next to the reverse view.
    """
    
    # Helper to determine which dimension is primary for a sequence based on key naming
    def get_sequence_primary_axis(view_key_for_seq):
        if "left" in view_key_for_seq.lower() or "right" in view_key_for_seq.lower():
            return 0 # Vertical blending, primary dimension is height
        return 1 # Horizontal blending, primary dimension is width

    # Get dimensions of main tablet views, considering they might be sequences
    obv_data = images_dict.get("obverse")
    obv_h = get_image_dimension(obv_data, 0, blend_overlap_px if isinstance(obv_data, list) and get_sequence_primary_axis("obverse") == 0 else 0)
    obv_w = get_image_dimension(obv_data, 1, blend_overlap_px if isinstance(obv_data, list) and get_sequence_primary_axis("obverse") == 1 else 0)

    if obv_h == 0 or obv_w == 0:
        # Try to find any other primary image if 'obverse' is missing/invalid and custom_layout is used
        if custom_layout:
            for key, data in images_dict.items():
                if data is not None: # Found an alternative primary image
                    print(f"      Layout: 'obverse' missing/invalid. Using '{key}' as primary for layout ref.")
                    obv_data = data
                    obv_h = get_image_dimension(obv_data, 0, blend_overlap_px if isinstance(obv_data, list) and get_sequence_primary_axis(key) == 0 else 0)
                    obv_w = get_image_dimension(obv_data, 1, blend_overlap_px if isinstance(obv_data, list) and get_sequence_primary_axis(key) == 1 else 0)
                    # It's important that this alternative key is treated like 'obverse' in subsequent logic.
                    # This simplified fallback might not be robust enough for all custom layouts.
                    # For now, we assume the layout algorithm below can adapt if obv_h, obv_w are set from another key.
                    # A better way would be for custom_layout to specify the 'main reference view'.
                    break
        if obv_h == 0 or obv_w == 0: # Still no valid primary image
            raise ValueError("A primary image (e.g., 'obverse' or other from custom_layout) with valid dimensions is required for layout.")

    # Get dimensions for other views, using get_image_dimension which handles lists (sequences)
    # The key for get_sequence_primary_axis should be the actual key from images_dict
    l_w = get_image_dimension(images_dict.get("left"), 1, blend_overlap_px if isinstance(images_dict.get("left"), list) and get_sequence_primary_axis("left") == 1 else 0)
    r_w = get_image_dimension(images_dict.get("right"), 1, blend_overlap_px if isinstance(images_dict.get("right"), list) and get_sequence_primary_axis("right") == 1 else 0)
    b_h = get_image_dimension(images_dict.get("bottom"), 0, blend_overlap_px if isinstance(images_dict.get("bottom"), list) and get_sequence_primary_axis("bottom") == 0 else 0)
    rev_h = get_image_dimension(images_dict.get("reverse"), 0, blend_overlap_px if isinstance(images_dict.get("reverse"), list) and get_sequence_primary_axis("reverse") == 0 else 0)
    t_h = get_image_dimension(images_dict.get("top"), 0, blend_overlap_px if isinstance(images_dict.get("top"), list) and get_sequence_primary_axis("top") == 0 else 0)
    
    # Get left and right heights for vertical alignment with reverse
    l_h = get_image_dimension(images_dict.get("left"), 0, blend_overlap_px if isinstance(images_dict.get("left"), list) and get_sequence_primary_axis("left") == 0 else 0)
    r_h = get_image_dimension(images_dict.get("right"), 0, blend_overlap_px if isinstance(images_dict.get("right"), list) and get_sequence_primary_axis("right") == 0 else 0)
    
    rul_h = get_image_dimension(images_dict.get("ruler"), 0) # Ruler is assumed to be a single image
    rul_w = get_image_dimension(images_dict.get("ruler"), 1)

    # Calculate first row width (left + obverse + right)
    # This assumes 'left', 'obverse', 'right' are the keys for the main horizontal arrangement.
    # If custom_layout uses different keys, this part needs to be more dynamic.
    row1_w = 0
    main_horizontal_views = [("left", l_w), ("obverse", obv_w), ("right", r_w)]
    active_in_row1 = 0
    for key, width_val in main_horizontal_views:
        if images_dict.get(key) is not None: # Check if the view exists
            if active_in_row1 > 0: row1_w += view_gap_px
            row1_w += width_val
            active_in_row1 +=1
    if active_in_row1 == 0: row1_w = obv_w # Fallback if only obverse is somehow considered

    # Determine actual widths for centering calculations for views below obverse
    # These use the post-blend width if they are horizontal sequences, or their natural width if single/vertical.
    bottom_w = get_image_dimension(images_dict.get("bottom"), 1, blend_overlap_px if isinstance(images_dict.get("bottom"), list) and get_sequence_primary_axis("bottom") == 1 else 0)
    reverse_w = get_image_dimension(images_dict.get("reverse"), 1, blend_overlap_px if isinstance(images_dict.get("reverse"), list) and get_sequence_primary_axis("reverse") == 1 else 0)
    top_w = get_image_dimension(images_dict.get("top"), 1, blend_overlap_px if isinstance(images_dict.get("top"), list) and get_sequence_primary_axis("top") == 1 else 0)

    # Calculate reverse row width (left_rotated + reverse + right_rotated)
    # Only include left/right if they exist
    rev_row_w = reverse_w
    if images_dict.get("left") is not None: 
        rev_row_w += l_w + view_gap_px
    if images_dict.get("right") is not None:
        rev_row_w += r_w + view_gap_px

    # Find maximum width needed for canvas
    # Consider all views that are laid out horizontally or centered.
    potential_canvas_widths = [row1_w, obv_w, rev_row_w]
    if bottom_w > 0: potential_canvas_widths.append(bottom_w)
    if top_w > 0: potential_canvas_widths.append(top_w)
    if rul_w > 0: potential_canvas_widths.append(rul_w)
    
    canvas_w = max(potential_canvas_widths) if potential_canvas_widths else obv_w # Fallback to obv_w
    canvas_w += 200  # Add margins (e.g., 100px each side)

    # Calculate total height needed
    h_sum = obv_h # Start with obverse height
    views_below_obverse = [("bottom", b_h), ("reverse", rev_h), ("top", t_h)] # Order matters for layout
    for key, height_val in views_below_obverse:
        if images_dict.get(key) is not None and height_val > 0:
            h_sum += view_gap_px + height_val
    if images_dict.get("ruler") is not None and rul_h > 0:
        h_sum += ruler_padding_px + rul_h
    canvas_h = h_sum + 200  # Add margins (e.g., 100px each side)
    
    coords = {}
    rotation_flags = {}  # Track which views need to be rotated
    y_curr = 100  # Starting Y margin
    
    # Center the main horizontal row (left-obverse-right)
    start_x_row1 = (canvas_w - row1_w) // 2 if row1_w > 0 else (canvas_w - obv_w) // 2
    current_x_in_row1 = start_x_row1

    if images_dict.get("left") is not None:
        coords["left"] = (current_x_in_row1, y_curr)
        rotation_flags["left"] = False  # Not rotated in original position
        current_x_in_row1 += l_w + view_gap_px
    
    # Obverse is positioned relative to left, or centered if left is not present
    obv_x_final = current_x_in_row1 if images_dict.get("left") is not None else (canvas_w - obv_w) // 2
    
    if images_dict.get("obverse") is not None: # Should always be true due to checks above
        coords["obverse"] = (obv_x_final, y_curr)
        current_x_in_row1 = obv_x_final + obv_w + view_gap_px
    else: # Should not happen if initial checks are robust
        current_x_in_row1 = (canvas_w - 0) // 2 # Placeholder if obverse somehow vanishes

    if images_dict.get("right") is not None:
        coords["right"] = (current_x_in_row1, y_curr)
        rotation_flags["right"] = False  # Not rotated in original position
        
    y_curr += obv_h # Advance Y position past the main row (obverse height)
    
    # Position bottom view
    if images_dict.get("bottom") is not None and b_h > 0:
        y_curr += view_gap_px
        # Center this view under the obverse footprint
        bottom_x_pos = obv_x_final + (obv_w - bottom_w) // 2 
        coords["bottom"] = (bottom_x_pos, y_curr)
        y_curr += b_h
    
    # Position reverse view with rotated left and right views
    if images_dict.get("reverse") is not None and rev_h > 0:
        y_curr += view_gap_px
        
        # Center the reverse row (left_rotated + reverse + right_rotated)
        rev_row_start_x = (canvas_w - rev_row_w) // 2
        current_x_in_rev_row = rev_row_start_x
        
        # Position rotated left view (if left exists)
        if images_dict.get("left") is not None:
            coords["left_rotated"] = (current_x_in_rev_row, y_curr + (rev_h - l_h) // 2)  # Vertically centered to reverse
            rotation_flags["left_rotated"] = True  # Mark for rotation
            current_x_in_rev_row += l_w + view_gap_px
        
        # Position reverse view
        reverse_x_pos = current_x_in_rev_row
        coords["reverse"] = (reverse_x_pos, y_curr)
        current_x_in_rev_row += reverse_w + view_gap_px
        
        # Position rotated right view (if right exists)
        if images_dict.get("right") is not None:
            coords["right_rotated"] = (current_x_in_rev_row, y_curr + (rev_h - r_h) // 2)  # Vertically centered to reverse
            rotation_flags["right_rotated"] = True  # Mark for rotation
        
        y_curr += rev_h
    
    # Position top view
    if images_dict.get("top") is not None and t_h > 0:
        y_curr += view_gap_px
        top_x_pos = obv_x_final + (obv_w - top_w) // 2
        coords["top"] = (top_x_pos, y_curr)
        y_curr += t_h
            
    # Position ruler view
    if images_dict.get("ruler") is not None and rul_h > 0:
        y_curr += ruler_padding_px
        ruler_x_pos = obv_x_final + (obv_w - rul_w) // 2
        coords["ruler"] = (ruler_x_pos, y_curr)
        y_curr += rul_h # Add ruler height to y_curr for canvas height calculation

    # Adjust canvas height based on final y_curr + margin
    canvas_h = y_curr + 100 

    # Create the rotated views for placement next to reverse
    modified_images_dict = dict(images_dict)
    
    # Add rotated copies of left and right to be placed next to reverse
    if images_dict.get("left") is not None:
        left_img = images_dict["left"]
        if isinstance(left_img, np.ndarray) and left_img.size > 0:
            # Rotate 180 degrees
            left_rotated = cv2.rotate(left_img, cv2.ROTATE_180)
            modified_images_dict["left_rotated"] = left_rotated
    
    if images_dict.get("right") is not None:
        right_img = images_dict["right"]
        if isinstance(right_img, np.ndarray) and right_img.size > 0:
            # Rotate 180 degrees
            right_rotated = cv2.rotate(right_img, cv2.ROTATE_180)
            modified_images_dict["right_rotated"] = right_rotated

    return int(canvas_w), int(canvas_h), coords, modified_images_dict

def get_layout_bounding_box(images_dict, layout_coords):
    """
    Calculate the bounding box that contains all placed images.
    Returns (min_x, min_y, max_x, max_y) if there are valid elements, None otherwise.
    """
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    found_any_placed_element = False
    
    # Find boundaries of all placed images
    for key, (x_coord, y_coord) in layout_coords.items():
        image_array = images_dict.get(key)
        if isinstance(image_array, np.ndarray) and image_array.size > 0:
            found_any_placed_element = True
            h_img, w_img = image_array.shape[:2]
            min_x = min(min_x, x_coord)
            min_y = min(min_y, y_coord)
            max_x = max(max_x, x_coord + w_img)
            max_y = max(max_y, y_coord + h_img)
            
    return (min_x, min_y, max_x, max_y) if found_any_placed_element else None