"""
Adapter module for the refactored stitch_layout_manager functionality.

This module provides the same interface as the original stitch_layout_manager.py
but uses the new implementation from the stitching package.
"""
import cv2
import numpy as np

from stitch_config import (
    STITCH_VIEW_GAP_PX,
    STITCH_RULER_PADDING_PX
)

from stitching.domain.models import StitchingConfig
from stitching.services.image_resizer import (
    resize_tablet_views_relative_to_obverse as _resize_views,
    get_image_dimension as _get_dimension
)
from stitching.services.layout_manager import (
    calculate_stitching_canvas_layout as _calculate_layout,
    get_layout_bounding_box as _get_bounding_box
)


def get_image_dimension(images_dict, key, axis_index):
    """
    Get height or width dimension of an image from the dictionary.
    
    Args:
        images_dict: Dictionary of images
        key: Key for the image to measure
        axis_index: Axis to measure (0 for height, 1 for width)
        
    Returns:
        Dimension value or 0 if image is invalid
    """
    return _get_dimension(images_dict, key, axis_index)


def resize_tablet_views_for_layout(loaded_images_dictionary):
    """
    Resize all tablet views to match the dimensions of the obverse.
    
    This ensures consistent visual appearance in the stitched output.
    
    Args:
        loaded_images_dictionary: Dictionary of images keyed by view name
        
    Returns:
        Dictionary with resized images
    """
    return _resize_views(loaded_images_dictionary)


def calculate_stitching_layout(images_dict, view_gap_px=STITCH_VIEW_GAP_PX, ruler_padding_px=STITCH_RULER_PADDING_PX):
    """
    Calculate the canvas dimensions and coordinates for placing each image.
    
    Args:
        images_dict: Dictionary of images keyed by view name
        view_gap_px: Gap between views in pixels
        ruler_padding_px: Padding above ruler in pixels
        
    Returns:
        Tuple containing canvas width, canvas height, coordinate map, and images dictionary with rotated views
    """
    # Create config for the layout calculation
    config = StitchingConfig(
        view_separation_px=view_gap_px,
        ruler_top_padding_px=ruler_padding_px
    )
    
    return _calculate_layout(images_dict, config)


def get_layout_bounding_box(images_dict, layout_coords):
    """
    Calculate the bounding box that contains all placed images.
    
    Args:
        images_dict: Dictionary of images
        layout_coords: Dictionary mapping view keys to (x,y) coordinates
        
    Returns:
        Tuple (min_x, min_y, max_x, max_y) if there are valid elements, None otherwise
    """
    bbox = _get_bounding_box(images_dict, layout_coords)
    if bbox:
        return (bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
    return None
