"""
Facade service for stitching functionality.

This module serves as the main entry point for the stitching functionality,
combining the different services into a cohesive workflow.
"""
import numpy as np
from typing import Dict, Tuple, Optional, Any

from stitching.domain.models import (
    StitchingConfig, 
    LayoutCoordinates,
    Position,
    CanvasSize,
    BoundingBox,
    LogoSettings
)
from stitching.services.image_resizer import resize_tablet_views_relative_to_obverse
from stitching.services.layout_manager import (
    calculate_stitching_canvas_layout,
    get_layout_bounding_box
)
from stitching.services.canvas_processor import (
    add_logo_to_image_array,
    crop_canvas_to_content_with_margin
)


class StitchingService:
    """
    Facade service for coordinating the stitching process.
    """
    
    def __init__(self, config: Optional[StitchingConfig] = None):
        """
        Initialize the stitching service with a configuration.
        
        Args:
            config: Stitching configuration or None to use default
        """
        self.config = config or StitchingConfig.default()
    
    def resize_views(self, images: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Resize all tablet views to be proportional to the obverse view.
        
        Args:
            images: Dictionary of images keyed by view name
            
        Returns:
            Dictionary of resized images
        """
        return resize_tablet_views_relative_to_obverse(images)
    
    def calculate_layout(
        self, 
        images: Dict[str, np.ndarray]
    ) -> Tuple[int, int, Dict[str, Tuple[int, int]], Dict[str, np.ndarray]]:
        """
        Calculate the layout for stitching images together.
        
        Args:
            images: Dictionary of resized images
            
        Returns:
            Tuple containing canvas width, canvas height, layout coordinates, and updated images
        """
        return calculate_stitching_canvas_layout(images, self.config)
    
    def get_content_bounding_box(
        self,
        images: Dict[str, np.ndarray],
        layout_coordinates: Dict[str, Tuple[int, int]]
    ) -> Optional[BoundingBox]:
        """
        Get the bounding box that contains all visible elements in the layout.
        
        Args:
            images: Dictionary of images
            layout_coordinates: Dictionary of coordinates for each image
            
        Returns:
            A BoundingBox object or None if no elements were found
        """
        return get_layout_bounding_box(images, layout_coordinates)
    
    def add_logo(
        self,
        image: np.ndarray,
        logo_path: str,
        max_width_fraction: float = 0.8,
        padding_above: int = 30,
        padding_below: int = 30
    ) -> np.ndarray:
        """
        Add a logo to the bottom of an image.
        
        Args:
            image: The image to add the logo to
            logo_path: Path to the logo image
            max_width_fraction: Maximum width of the logo as a fraction of the image width
            padding_above: Padding above the logo in pixels
            padding_below: Padding below the logo in pixels
            
        Returns:
            Image with logo added at the bottom
        """
        logo_settings = LogoSettings(
            logo_path=logo_path,
            max_width_fraction=max_width_fraction,
            padding_above=padding_above,
            padding_below=padding_below
        )
        return add_logo_to_image_array(image, logo_settings, self.config.background_color)
    
    def crop_to_content(
        self,
        image: np.ndarray,
        margin_px: int = 50
    ) -> np.ndarray:
        """
        Crop an image to its content and add a margin.
        
        Args:
            image: The image to crop
            margin_px: Margin to add around the content in pixels
            
        Returns:
            Cropped image with margin
        """
        return crop_canvas_to_content_with_margin(
            image, 
            self.config.background_color,
            margin_px
        )
    
    def create_stitching_canvas(
        self,
        width: int,
        height: int
    ) -> np.ndarray:
        """
        Create an empty canvas for stitching.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            
        Returns:
            Empty canvas as a NumPy array
        """
        return np.full(
            (height, width, 3),
            self.config.background_color,
            dtype=np.uint8
        )
