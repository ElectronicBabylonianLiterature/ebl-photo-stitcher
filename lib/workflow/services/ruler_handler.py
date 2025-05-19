import os
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

from workflow.domain.models import WorkflowConfig, RulerTemplates


class RulerHandler:
    """Service for handling ruler detection, extraction, and processing"""
    
    def __init__(self, config: WorkflowConfig, ruler_templates: RulerTemplates):
        self.config = config
        self.ruler_templates = ruler_templates
    
    def estimate_pixels_per_cm(self, ruler_image_path: str) -> float:
        """Calculate pixels per centimeter from ruler image"""
        try:
            from ruler_detector import estimate_pixels_per_centimeter_from_ruler
            return estimate_pixels_per_centimeter_from_ruler(
                ruler_image_path, ruler_position=self.config.ruler_position
            )
        except Exception as e:
            raise RuntimeError(f"Failed to estimate pixels per centimeter: {e}")
    
    def extract_ruler_contour(self, image_array: np.ndarray, 
                            artifact_contour: Optional[np.ndarray] = None, 
                            bg_mode: str = "auto") -> Optional[np.ndarray]:
        """Extract the ruler contour from the image"""
        try:
            from remove_background import (
                create_foreground_mask_from_background as create_foreground_mask,
                select_ruler_like_contour_from_list as select_ruler_like_contour
            )
            
            # Determine background color for mask creation
            bg_color = (0, 0, 0) if bg_mode != "white" else (255, 255, 255)
            
            # Create foreground mask
            mask = create_foreground_mask(image_array, bg_color, 40)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Select ruler-like contour, excluding artifact contour
            ruler_contour = select_ruler_like_contour(
                contours, 
                image_array.shape[1], 
                image_array.shape[0], 
                excluded_obj_contour=artifact_contour
            )
            
            return ruler_contour
        except Exception as e:
            raise RuntimeError(f"Failed to extract ruler contour: {e}")
    
    def extract_ruler_to_image(self, image_array: np.ndarray, ruler_contour: np.ndarray) -> np.ndarray:
        """Extract the ruler to a separate image array"""
        try:
            from object_extractor import extract_specific_contour_to_image_array
            return extract_specific_contour_to_image_array(
                image_array, ruler_contour, (0, 0, 0), 5
            )
        except Exception as e:
            raise RuntimeError(f"Failed to extract ruler to image: {e}")
    
    def save_extracted_ruler(self, ruler_array: np.ndarray, subfolder_path: str) -> str:
        """Save the extracted ruler image to the specified subfolder"""
        if ruler_array is None:
            raise ValueError("No ruler array provided")
            
        output_path = os.path.join(subfolder_path, self.config.temp_extracted_ruler_filename)
        cv2.imwrite(output_path, ruler_array)
        return output_path
    
    def choose_ruler_template(self, artifact_width_cm: float, pixels_per_cm: float) -> Tuple[str, Optional[float]]:
        """Choose the appropriate ruler template based on artifact size"""
        # Default template and custom size
        chosen_ruler_tpl = self.ruler_templates.ruler_template_5cm
        custom_ruler_size_cm = None
        
        if self.config.museum_selection == "British Museum":
            from resize_ruler import RULER_TARGET_PHYSICAL_WIDTHS_CM
            t1 = RULER_TARGET_PHYSICAL_WIDTHS_CM["1cm"]
            t2 = RULER_TARGET_PHYSICAL_WIDTHS_CM["2cm"]
            
            if artifact_width_cm < t1:
                chosen_ruler_tpl = self.ruler_templates.ruler_template_1cm
            elif artifact_width_cm < t2:
                chosen_ruler_tpl = self.ruler_templates.ruler_template_2cm
                
        elif self.config.museum_selection == "Iraq Museum":
            chosen_ruler_tpl = os.path.join(os.path.dirname(self.ruler_templates.ruler_template_1cm), 
                                          "IM_photo_ruler.svg")
            custom_ruler_size_cm = 4.599
            
        elif self.config.museum_selection == "eBL Ruler (CBS)":
            chosen_ruler_tpl = os.path.join(os.path.dirname(self.ruler_templates.ruler_template_1cm), 
                                          "General_eBL_photo_ruler.svg")
            custom_ruler_size_cm = 4.317
            
        elif self.config.museum_selection == "Non-eBL Ruler (VAM)":
            chosen_ruler_tpl = os.path.join(os.path.dirname(self.ruler_templates.ruler_template_1cm), 
                                          "General_External_photo_ruler.svg")
            custom_ruler_size_cm = 3.248
            
        return chosen_ruler_tpl, custom_ruler_size_cm
        
    def resize_ruler_template(self, pixels_per_cm: float, template_path: str, 
                            subfolder_name: str, subfolder_path: str,
                            custom_ruler_size_cm: Optional[float] = None) -> None:
        """Resize the ruler template based on calculated scale"""
        try:
            from resize_ruler import resize_and_save_ruler_template
            resize_and_save_ruler_template(
                pixels_per_cm, 
                template_path, 
                subfolder_name, 
                subfolder_path,
                custom_ruler_size_cm=custom_ruler_size_cm
            )
        except Exception as e:
            raise RuntimeError(f"Failed to resize ruler template: {e}")
