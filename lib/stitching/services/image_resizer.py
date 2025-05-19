"""
Service for resizing images during the stitching process.
"""
from typing import Dict, Any, Optional, Tuple
import numpy as np

from stitching.domain.models import ResizeParams


def resize_tablet_views_relative_to_obverse(loaded_images_dictionary: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """
    Resize all non-obverse tablet views to be proportional to the obverse view.
    
    Args:
        loaded_images_dictionary: Dictionary of images keyed by view name
        
    Returns:
        Dictionary of resized images
    
    Raises:
        ValueError: If the obverse image is invalid
    """
    try:
        from image_utils import resize_image_maintain_aspect
        
        # Check that the obverse image is valid
        obverse_image = loaded_images_dictionary.get("obverse")
        if not isinstance(obverse_image, np.ndarray) or obverse_image.size == 0:
            raise ValueError("Obverse image is not a valid NumPy array or is empty for resizing.")
        
        # Get dimensions of obverse image
        obv_h, obv_w = obverse_image.shape[:2]
        
        # Define resize parameters for each view
        views_to_resize = {
            "left": {"axis": 0, "match_dim": obv_h}, 
            "right": {"axis": 0, "match_dim": obv_h},
            "top": {"axis": 1, "match_dim": obv_w}, 
            "bottom": {"axis": 1, "match_dim": obv_w},
            "reverse": {"axis": 1, "match_dim": obv_w}
        }
        
        # Resize each view
        for view_key, resize_params in views_to_resize.items():
            current_view_image = loaded_images_dictionary.get(view_key)
            
            if isinstance(current_view_image, np.ndarray) and current_view_image.size > 0:
                loaded_images_dictionary[view_key] = resize_image_maintain_aspect(
                    current_view_image, 
                    resize_params["match_dim"], 
                    resize_params["axis"]
                )
            elif current_view_image is not None:
                # If the image is not valid, set it to None
                loaded_images_dictionary[view_key] = None
                
        return loaded_images_dictionary
        
    except ImportError:
        raise ImportError("Failed to import resize_image_maintain_aspect from image_utils")


def get_image_dimension(images_dict: Dict[str, np.ndarray], key: str, axis_index: int) -> int:
    """
    Get the dimension of an image along a specific axis.
    
    Args:
        images_dict: Dictionary of images
        key: Key for the image
        axis_index: Index of the axis (0 for height, 1 for width)
        
    Returns:
        Dimension value or 0 if the image is invalid
    """
    image = images_dict.get(key)
    if isinstance(image, np.ndarray) and image.ndim >= 2 and image.size > 0:
        return image.shape[axis_index]
    return 0
