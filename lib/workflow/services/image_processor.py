import os
import cv2
import numpy as np
from typing import Optional, List, Dict, Any

from workflow.domain.models import WorkflowConfig


class ImageProcessor:
    """Service for handling image conversion and processing"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
    
    def convert_raw_to_tiff(self, raw_file_path: str, output_path: str) -> str:
        """Convert a RAW image file to TIFF format"""
        try:
            from raw_processor import convert_raw_image_to_tiff
            
            if not os.path.exists(output_path):
                convert_raw_image_to_tiff(raw_file_path, output_path)
                
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to convert RAW to TIFF: {e}")
    
    def is_raw_file(self, file_path: str) -> bool:
        """Check if a file is a RAW image file"""
        return file_path.lower().endswith(self.config.raw_ext)
    
    def get_temp_conversion_path(self, raw_file_path: str, suffix: str = "") -> str:
        """Generate a temporary path for a converted RAW file"""
        base_name = os.path.splitext(os.path.basename(raw_file_path))[0]
        folder_path = os.path.dirname(raw_file_path)
        suffix_to_use = suffix if suffix else "converted"
        
        return os.path.join(folder_path, f"{base_name}_{suffix_to_use}.tif")
    
    def load_image(self, image_path: str) -> np.ndarray:
        """Load an image file into a NumPy array"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        return img
    
    def delete_temp_file(self, file_path: str) -> bool:
        """Delete a temporary file if it exists"""
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {file_path}: {e}")
        return False
