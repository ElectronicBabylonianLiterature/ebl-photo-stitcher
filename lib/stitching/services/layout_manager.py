"""
Service for managing the layout of images during stitching.
"""
from typing import Dict, Tuple, Optional, Any, List
import cv2
import numpy as np

from stitching.domain.models import (
    LayoutCoordinates, 
    Position, 
    CanvasSize, 
    BoundingBox,
    StitchingConfig
)
from stitching.services.image_resizer import get_image_dimension


def calculate_stitching_canvas_layout(
    images_dict: Dict[str, np.ndarray], 
    config: StitchingConfig
) -> Tuple[int, int, Dict[str, Tuple[int, int]], Dict[str, np.ndarray]]:
    """
    Calculate the layout for stitching images together.
    
    Args:
        images_dict: Dictionary of images keyed by view name
        config: Stitching configuration
        
    Returns:
        Tuple containing:
        - Canvas width
        - Canvas height
        - Layout coordinates dictionary
        - Updated images dictionary with rotated views
        
    Raises:
        ValueError: If the obverse image has zero dimensions
    """
    try:
        from image_utils import convert_to_bgr_if_needed
        
        # Get dimensions of obverse image
        obv_h = get_image_dimension(images_dict, "obverse", 0)
        obv_w = get_image_dimension(images_dict, "obverse", 1)
        
        if not (obv_h > 0 and obv_w > 0):
            raise ValueError("Obverse image has zero dimensions in calculate_stitching_canvas_layout.")
        
        # Get dimensions of other views
        l_w = get_image_dimension(images_dict, "left", 1)
        r_w = get_image_dimension(images_dict, "right", 1)
        b_h = get_image_dimension(images_dict, "bottom", 0)
        rev_h = get_image_dimension(images_dict, "reverse", 0)
        t_h = get_image_dimension(images_dict, "top", 0)
        rul_h = get_image_dimension(images_dict, "ruler", 0)
        rul_w = get_image_dimension(images_dict, "ruler", 1)
        
        # Calculate width of first row (left, obverse, right)
        row1_w = l_w + (config.view_separation_px if l_w > 0 and obv_w > 0 else 0) + obv_w + \
                (config.view_separation_px if r_w > 0 and obv_w > 0 else 0) + r_w
        
        if row1_w == 0 and obv_w > 0:
            row1_w = obv_w
        
        # Calculate canvas width
        canvas_w = max(
            row1_w, 
            obv_w, 
            get_image_dimension(images_dict, "bottom", 1),
            get_image_dimension(images_dict, "reverse", 1), 
            get_image_dimension(images_dict, "top", 1), 
            rul_w
        ) + config.canvas_padding * 2
        
        # Calculate canvas height
        current_height_sum = obv_h
        if b_h > 0:
            current_height_sum += config.view_separation_px + b_h
        if rev_h > 0:
            current_height_sum += config.view_separation_px + rev_h
        if t_h > 0:
            current_height_sum += config.view_separation_px + t_h
        if rul_h > 0:
            current_height_sum += config.ruler_top_padding_px + rul_h
            
        canvas_h = current_height_sum + config.canvas_padding * 2
        
        # Initialize layout coordinates
        layout_coords = {}
        y_curr = config.canvas_padding // 2  # Starting y position
        view_bottom_y_coords = {}  # Store bottom y coordinates for alignment
        
        # Calculate starting x position for first row
        start_x_row1 = (canvas_w - row1_w) // 2 if row1_w > 0 else (canvas_w - obv_w) // 2
        
        # Layout left, obverse, right views (first row)
        current_x_offset = start_x_row1
        
        # Place left view
        if images_dict.get("left") is not None and images_dict.get("left").size > 0:
            layout_coords["left"] = (current_x_offset, y_curr)
            current_x_offset += l_w + config.view_separation_px
        
        # Place obverse view
        obverse_x_pos = current_x_offset
        layout_coords["obverse"] = (obverse_x_pos, y_curr)
        current_x_offset += obv_w
        
        # Place right view
        if images_dict.get("right") is not None and images_dict.get("right").size > 0:
            layout_coords["right"] = (current_x_offset + config.view_separation_px, y_curr)
        
        # Advance below first row
        y_curr += obv_h
        view_bottom_y_coords["obverse"] = y_curr
        
        # Place bottom, reverse, and top views
        for view_key in ["bottom", "reverse", "top"]:
            img_view = images_dict.get(view_key)
            if img_view is not None and img_view.size > 0:
                y_curr += config.view_separation_px
                view_x_pos = obverse_x_pos + (obv_w - img_view.shape[1]) // 2
                layout_coords[view_key] = (view_x_pos, y_curr)
                y_curr += img_view.shape[0]
                view_bottom_y_coords[view_key] = y_curr
        
        # Place ruler
        if images_dict.get("ruler") is not None and images_dict.get("ruler").size > 0:
            y_curr += config.ruler_top_padding_px
            ruler_x_pos = obverse_x_pos + (obv_w - rul_w) // 2
            layout_coords["ruler"] = (ruler_x_pos, y_curr)
            view_bottom_y_coords["ruler"] = y_curr + rul_h
        
        # Create rotated side views
        y_align_for_rotated = view_bottom_y_coords.get("reverse", y_curr)
        
        for side_key, original_coord_key in [("left", "left"), ("right", "right")]:
            side_img = images_dict.get(side_key)
            if isinstance(side_img, np.ndarray) and side_img.size > 0:
                bgr_img = convert_to_bgr_if_needed(side_img)
                if isinstance(bgr_img, np.ndarray) and bgr_img.size > 0:
                    rot_img = cv2.rotate(bgr_img, cv2.ROTATE_180)
                    images_dict[side_key + "_rotated"] = rot_img
                    
                    # Calculate x position for rotated view
                    orig_x_val = layout_coords.get(
                        original_coord_key, 
                        (start_x_row1 if side_key == "left" else obverse_x_pos + obv_w, 0)
                    )[0]
                    
                    # Place rotated view
                    layout_coords[side_key + "_rotated"] = (
                        orig_x_val, 
                        y_align_for_rotated - rot_img.shape[0]
                    )
        
        return int(canvas_w), int(canvas_h), layout_coords, images_dict
        
    except ImportError:
        raise ImportError("Failed to import convert_to_bgr_if_needed from image_utils")


def get_layout_bounding_box(
    images_dict: Dict[str, np.ndarray], 
    layout_coordinates: Dict[str, Tuple[int, int]]
) -> Optional[BoundingBox]:
    """
    Get the bounding box that contains all visible elements in the layout.
    
    Args:
        images_dict: Dictionary of images
        layout_coordinates: Dictionary of coordinates for each image
        
    Returns:
        A BoundingBox object or None if no elements were found
    """
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    found_any_placed_element = False
    
    # Iterate over each placed image
    for key, (x_coord, y_coord) in layout_coordinates.items():
        image_array = images_dict.get(key)
        
        if isinstance(image_array, np.ndarray) and image_array.size > 0:
            found_any_placed_element = True
            h_img, w_img = image_array.shape[:2]
            
            min_x = min(min_x, x_coord)
            min_y = min(min_y, y_coord)
            max_x = max(max_x, x_coord + w_img)
            max_y = max(max_y, y_coord + h_img)
    
    if found_any_placed_element:
        return BoundingBox(
            min_x=int(min_x),
            min_y=int(min_y),
            max_x=int(max_x),
            max_y=int(max_y)
        )
    
    return None
