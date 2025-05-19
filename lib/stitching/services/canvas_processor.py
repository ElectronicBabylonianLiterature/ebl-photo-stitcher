"""
Service for processing the stitching canvas, adding logos, and cropping.
"""
import os
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any

from stitching.domain.models import LogoSettings, BoundingBox


def add_logo_to_image_array(
    content_img_array: np.ndarray,
    logo_settings: LogoSettings,
    canvas_bg_color: Tuple[int, int, int]
) -> np.ndarray:
    """
    Add a logo to the bottom of an image array.
    
    Args:
        content_img_array: The image to add the logo to
        logo_settings: Settings for logo placement
        canvas_bg_color: Background color for the canvas
        
    Returns:
        Image array with logo added at the bottom
    """
    try:
        from image_utils import paste_image_onto_canvas
        
        # If no logo path or it doesn't exist, return the original image
        if not logo_settings.logo_path or not os.path.exists(logo_settings.logo_path):
            return content_img_array
            
        # Load the logo
        logo_original = cv2.imread(logo_settings.logo_path, cv2.IMREAD_UNCHANGED)
        if logo_original is None or logo_original.size == 0:
            return content_img_array
        
        # Get dimensions
        content_h, content_w = content_img_array.shape[:2]
        logo_h, logo_w = logo_original.shape[:2]
        
        # Resize logo if necessary to fit within width constraint
        logo_res = logo_original
        if logo_w > 0 and content_w > 0 and logo_w > content_w * logo_settings.max_width_fraction:
            new_logo_w = int(content_w * logo_settings.max_width_fraction)
            scale_ratio = new_logo_w / logo_w if logo_w > 0 else 1.0
            new_logo_h = int(logo_h * scale_ratio)
            
            if new_logo_w > 0 and new_logo_h > 0:
                logo_res = cv2.resize(
                    logo_original, 
                    (new_logo_w, new_logo_h),
                    interpolation=cv2.INTER_AREA
                )
        
        # Get resized logo dimensions
        logo_h, logo_w = logo_res.shape[:2]
        
        # Create canvas with space for logo
        canvas_w = max(content_w, logo_w)
        canvas_h = content_h + logo_settings.padding_above + logo_h + logo_settings.padding_below
        canvas = np.full((canvas_h, canvas_w, 3), canvas_bg_color, dtype=np.uint8)
        
        # Paste the content image
        paste_image_onto_canvas(
            canvas, 
            content_img_array, 
            (canvas_w - content_w) // 2, 
            0
        )
        
        # Paste the logo
        paste_image_onto_canvas(
            canvas, 
            logo_res,
            (canvas_w - logo_w) // 2, 
            content_h + logo_settings.padding_above
        )
        
        return canvas
        
    except ImportError:
        raise ImportError("Failed to import paste_image_onto_canvas from image_utils")


def crop_canvas_to_content_with_margin(
    image_array: np.ndarray,
    background_color: Tuple[int, int, int],
    margin_px: int
) -> np.ndarray:
    """
    Crop a canvas to the content, adding a margin around it.
    
    Args:
        image_array: The image to crop
        background_color: Background color of the canvas
        margin_px: Margin to add around the content in pixels
        
    Returns:
        Cropped image with margin
    """
    try:
        from image_utils import paste_image_onto_canvas
        
        # Check for valid input
        if image_array is None or image_array.size == 0:
            return image_array
        
        # Convert to grayscale for finding content
        grayscale_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        if grayscale_image is None or grayscale_image.size == 0:
            return image_array
        
        # Initialize final image to the input
        final_content_image = image_array
        
        # Calculate threshold based on background color
        mean_bg_intensity = np.mean(background_color)
        
        # Set threshold bounds based on background intensity
        if background_color == (0, 0, 0):
            lower_b, upper_b = 1, 255
        elif background_color == (255, 255, 255):
            lower_b, upper_b = 0, 254
        elif mean_bg_intensity < 128:
            lower_b, upper_b = int(mean_bg_intensity + 1), 255
        else:
            lower_b, upper_b = 0, int(mean_bg_intensity - 1)
        
        # Check if there's content different from background
        is_content_present = np.any(grayscale_image > (
            int(mean_bg_intensity) + 5 if mean_bg_intensity < 128 
            else int(mean_bg_intensity) - 5
        ))
        
        # Find and crop to content if present
        if is_content_present:
            try:
                # Create mask of non-background pixels
                mask = cv2.inRange(grayscale_image, lower_b, upper_b)
                coords = cv2.findNonZero(mask)
                
                if coords is not None:
                    x, y, w, h = cv2.boundingRect(coords)
                    if w > 0 and h > 0:
                        final_content_image = image_array[y:y+h, x:x+w]
            except cv2.error as e:
                print(f" Error during crop: {e}")
        
        # Get dimensions of cropped content
        content_h, content_w = final_content_image.shape[:2]
        
        # If dimensions are invalid, return original
        if content_h == 0 or content_w == 0:
            return final_content_image
        
        # Create output canvas with margin
        output_h = content_h + 2 * margin_px
        output_w = content_w + 2 * margin_px
        output_canvas = np.full(
            (output_h, output_w, 3), 
            background_color, 
            dtype=np.uint8
        )
        
        # Paste content onto canvas with margin
        paste_image_onto_canvas(
            output_canvas, 
            final_content_image, 
            margin_px, 
            margin_px
        )
        
        return output_canvas
        
    except ImportError:
        raise ImportError("Failed to import paste_image_onto_canvas from image_utils")
