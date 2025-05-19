import os
from typing import Dict, Any, Optional

from workflow.domain.models import WorkflowConfig


class StitchCoordinator:
    """Service for coordinating the stitching process"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
    
    def process_tablet_subfolder(self, subfolder_path: str, pixels_per_cm: float, 
                               ruler_image_path: str, subfolder_name: str) -> bool:
        """Process a tablet subfolder to create a stitched image"""
        try:
            from stitch_images_adapter import process_tablet_subfolder
            from stitch_config import MUSEUM_CONFIGS
            
            # Get background color from museum configuration
            museum_config = MUSEUM_CONFIGS.get(self.config.museum_selection, {})
            bg_color = museum_config.get("background_color", (0, 0, 0))
            
            # Process the tablet subfolder to create the stitched image
            result = process_tablet_subfolder(
                subfolder_path=subfolder_path,
                main_input_folder_path=self.config.source_folder_path,
                output_base_name=subfolder_name,
                pixels_per_cm=pixels_per_cm,
                photographer_name=self.config.photographer,
                ruler_image_for_scale_path=ruler_image_path,
                add_logo=self.config.add_logo,
                logo_path=self.config.logo_path if self.config.add_logo else None,
                object_extraction_background_mode=self.config.obj_bg_mode,
                stitched_bg_color=bg_color
            )
            
            return result is not None and isinstance(result, dict)
        except Exception as e:
            raise RuntimeError(f"Failed to process tablet subfolder: {e}")
    
    def find_tablet_views(self, subfolder_path: str, subfolder_name: str) -> Dict[str, str]:
        """Find and categorize tablet view images in a subfolder"""
        views = {}
        
        try:
            all_files = [f for f in os.listdir(subfolder_path) if os.path.isfile(os.path.join(subfolder_path, f))]
            
            for file_name in all_files:
                file_path = os.path.join(subfolder_path, file_name)
                
                # Check if this is a valid image file
                if not self._is_valid_image_file(file_name):
                    continue
                
                # Check for specific view patterns in the file name
                for view_key, suffix_pattern in self.config.view_original_suffix_patterns.items():
                    if file_name.startswith(subfolder_name + suffix_pattern[:-1]):
                        views[view_key] = file_path
                        break
            
            return views
        except Exception as e:
            raise RuntimeError(f"Failed to find tablet views: {e}")
    
    def _is_valid_image_file(self, filename: str) -> bool:
        """Check if a file is a valid image file based on extensions in the config"""
        filename_lower = filename.lower()
        return (filename_lower.endswith(self.config.raw_ext) or 
                any(filename_lower.endswith(ext) for ext in self.config.valid_img_exts))
