import os
from typing import List, Optional, Callable
from workflow.domain.models import WorkflowConfig


class FileOrganizer:
    """Service for organizing files into tablet-specific subfolders"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
    
    def organize_files(self) -> List[str]:
        """Organize image files into subfolders and return the list of processed subfolder paths"""
        try:
            from put_images_in_subfolders import group_and_move_files_to_subfolders
            
            processed_subfolders = group_and_move_files_to_subfolders(self.config.source_folder_path)
            
            # If no subfolders were created but there are valid images in the source folder,
            # treat the source folder itself as a subfolder to process
            if not processed_subfolders and os.path.isdir(self.config.source_folder_path) and \
               any(self._is_valid_image_file(f) for f in os.listdir(self.config.source_folder_path)):
                processed_subfolders = [self.config.source_folder_path]
                
            return processed_subfolders
        except Exception as e:
            raise RuntimeError(f"Error organizing files: {e}")
    
    def _is_valid_image_file(self, filename: str) -> bool:
        """Check if a file is a valid image file based on extensions in the config"""
        filename_lower = filename.lower()
        return (filename_lower.endswith(self.config.raw_ext) or 
                any(filename_lower.endswith(ext) for ext in self.config.valid_img_exts))
