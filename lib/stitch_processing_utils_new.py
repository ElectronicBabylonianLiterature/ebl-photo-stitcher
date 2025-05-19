"""
Adapter for the stitch_processing_utils functionality.

This module maintains the same API as the original stitch_processing_utils.py
but delegates to the new modular implementation.
"""
import cv2
import numpy as np
import os
from typing import Dict, Tuple, Optional, Any

from stitching.services.image_resizer import (
    resize_tablet_views_relative_to_obverse as _resize_tablet_views,
    get_image_dimension as _get_image_dimension
)
from stitching.services.layout_manager import (
    calculate_stitching_canvas_layout as _calculate_layout,
    get_layout_bounding_box as _get_layout_bbox
)
from stitching.services.canvas_processor import (
    add_logo_to_image_array as _add_logo,
    crop_canvas_to_content_with_margin as _crop_canvas
)
from stitching.domain.models import (
    StitchingConfig,
    LogoSettings
)

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


# Maintain the original function signatures for backward compatibility
def resize_tablet_views_relative_to_obverse(loaded_images_dictionary):
    """
    Resize all non-obverse tablet views to be proportional to the obverse view.
    
    Args:
        loaded_images_dictionary: Dictionary of images keyed by view name
        
    Returns:
        Dictionary of resized images
    """
    return _resize_tablet_views(loaded_images_dictionary)


def get_image_dimension(images_dict, key, axis_index):
    """
    Get the dimension of an image along a specific axis.
    
    Args:
        images_dict: Dictionary of images
        key: Key for the image
        axis_index: Index of the axis (0 for height, 1 for width)
        
    Returns:
        Dimension value or 0 if the image is invalid
    """
    return _get_image_dimension(images_dict, key, axis_index)


def calculate_stitching_canvas_layout(images_dict, view_separation_px, ruler_top_padding_px):
    """
    Calculate the layout for stitching images together.
    
    Args:
        images_dict: Dictionary of images keyed by view name
        view_separation_px: Separation between views in pixels
        ruler_top_padding_px: Padding above the ruler in pixels
        
    Returns:
        Tuple containing canvas width, canvas height, layout coordinates, and updated images
    """
    # Create a config with the specified parameters
    config = StitchingConfig(
        view_separation_px=view_separation_px,
        ruler_top_padding_px=ruler_top_padding_px,
        canvas_padding=100
    )
    
    return _calculate_layout(images_dict, config)


def get_layout_bounding_box(images_dict_with_positions, layout_coordinates):
    """
    Get the bounding box that contains all visible elements in the layout.
    
    Args:
        images_dict_with_positions: Dictionary of images
        layout_coordinates: Dictionary of coordinates for each image
        
    Returns:
        Tuple containing min_x, min_y, max_x, max_y or None if no elements were found
    """
    bbox = _get_layout_bbox(images_dict_with_positions, layout_coordinates)
    if bbox:
        return (bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
    return None


def add_logo_to_image_array(content_img_array, logo_image_path, canvas_bg_color, max_width_fraction, padding_above, padding_below):
    """
    Add a logo to the bottom of an image array.
    
    Args:
        content_img_array: The image to add the logo to
        logo_image_path: Path to the logo image
        canvas_bg_color: Background color for the canvas
        max_width_fraction: Maximum width of the logo as a fraction of the image width
        padding_above: Padding above the logo in pixels
        padding_below: Padding below the logo in pixels
        
    Returns:
        Image array with logo added at the bottom
    """
    logo_settings = LogoSettings(
        logo_path=logo_image_path,
        max_width_fraction=max_width_fraction,
        padding_above=padding_above,
        padding_below=padding_below
    )
    
    return _add_logo(content_img_array, logo_settings, canvas_bg_color)


def crop_canvas_to_content_with_margin(image_array_to_crop, background_color_bgr_tuple, margin_px_around):
    """
    Crop a canvas to the content, adding a margin around it.
    
    Args:
        image_array_to_crop: The image to crop
        background_color_bgr_tuple: Background color of the canvas
        margin_px_around: Margin to add around the content in pixels
        
    Returns:
        Cropped image with margin
    """
    return _crop_canvas(
        image_array_to_crop, 
        background_color_bgr_tuple,
        margin_px_around
    )
