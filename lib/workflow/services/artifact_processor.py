import os
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any, List

from workflow.domain.models import WorkflowConfig
from stitch_config import MUSEUM_CONFIGS


class ArtifactProcessor:
    """Service for processing artifact objects from images"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
    
    def extract_center_object(self, image_path: str) -> Tuple[str, Optional[np.ndarray]]:
        """Extract the center object (artifact) from the image"""
        try:
            from object_extractor import extract_and_save_center_object
            from remove_background import get_museum_background_color
            
            # Get the appropriate background color for the output based on museum
            output_bg_color = get_museum_background_color(museum_selection=self.config.museum_selection)
            
            # Extract the artifact
            artifact_path, artifact_contour = extract_and_save_center_object(
                image_path,
                source_background_detection_mode=self.config.obj_bg_mode,
                output_image_background_color=output_bg_color,
                output_filename_suffix=self.config.object_artifact_suffix,
                museum_selection=self.config.museum_selection
            )
            
            return artifact_path, artifact_contour
        except Exception as e:
            raise RuntimeError(f"Failed to extract center object: {e}")
    
    def calculate_artifact_dimensions(self, artifact_image_path: str, pixels_per_cm: float) -> Dict[str, float]:
        """Calculate the physical dimensions of the artifact in centimeters"""
        try:
            artifact_img = cv2.imread(artifact_image_path)
            if artifact_img is None:
                raise ValueError(f"Could not load artifact image: {artifact_image_path}")
                
            height, width = artifact_img.shape[:2]
            
            return {
                "width_cm": width / pixels_per_cm if pixels_per_cm > 0 else 0,
                "height_cm": height / pixels_per_cm if pixels_per_cm > 0 else 0
            }
        except Exception as e:
            raise RuntimeError(f"Failed to calculate artifact dimensions: {e}")
    
    def get_museum_config(self) -> Dict[str, Any]:
        """Get the museum-specific configuration"""
        return MUSEUM_CONFIGS.get(self.config.museum_selection, {})
