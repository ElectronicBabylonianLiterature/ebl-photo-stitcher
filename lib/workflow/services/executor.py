import os
from typing import Optional, List, Dict, Any, Tuple

from workflow.domain.models import (
    WorkflowConfig, 
    WorkflowResult, 
    RulerTemplates,
    StepAllocation,
    ProgressCallback,
    FinishedCallback
)
from workflow.services.file_organizer import FileOrganizer
from workflow.services.ruler_handler import RulerHandler
from workflow.services.artifact_processor import ArtifactProcessor
from workflow.services.image_processor import ImageProcessor
from workflow.services.stitch_coordinator import StitchCoordinator


class WorkflowExecutor:
    """Main service that orchestrates the entire workflow execution"""
    
    def __init__(
        self,
        config: WorkflowConfig,
        ruler_templates: RulerTemplates,
        progress_callback: ProgressCallback,
        finished_callback: FinishedCallback
    ):
        self.config = config
        self.ruler_templates = ruler_templates
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        
        # Initialize services
        self.file_organizer = FileOrganizer(config)
        self.ruler_handler = RulerHandler(config, ruler_templates)
        self.artifact_processor = ArtifactProcessor(config)
        self.image_processor = ImageProcessor(config)
        self.stitch_coordinator = StitchCoordinator(config)
        
        # Initialize step allocation
        self.step_allocation = StepAllocation()
        
        # Initialize result counters
        self.total_ok = 0
        self.total_err = 0
        self.cr2_conv_total = 0
    
    def execute(self) -> WorkflowResult:
        """Execute the complete image processing workflow"""
        print(f"Workflow started for folder: {self.config.source_folder_path}")
        self.progress_callback(2)
        
        # Step 0: Organize files into subfolders
        print("Step 0: Organizing images into subfolders...")
        try:
            processed_subfolders = self.file_organizer.organize_files()
        except Exception as e:
            print(f"  ERROR file organization: {e}\n--- Halted ---")
            self.progress_callback(100)
            self.finished_callback()
            return WorkflowResult(total_ok=0, total_err=0, cr2_conv_total=0)
        
        num_folders = len(processed_subfolders)
        print(f"File organization complete. Targeting {num_folders} subfolder(s).")
        self.progress_callback(10)
        print("-" * 50)
        
        if num_folders == 0:
            print("No image sets to process.")
            self.progress_callback(100)
            self.finished_callback()
            return WorkflowResult(total_ok=0, total_err=0, cr2_conv_total=0)
        
        # Calculate progress per folder
        prog_per_folder = 85.0 / num_folders if num_folders > 0 else 0
        
        # Process each subfolder
        for i, subfolder_path in enumerate(processed_subfolders):
            subfolder_name = os.path.basename(subfolder_path)
            print(f"Processing Subfolder {i+1}/{num_folders}: {subfolder_name}")
            
            # Calculate base progress for this folder
            current_prog_base = 10 + i * prog_per_folder
            self.progress_callback(int(current_prog_base))
            
            # Track accumulated sub-progress
            accumulated_sub_progress = 0.0
            
            try:
                # Find ruler image for scale
                ruler_image_path = self._find_ruler_image(subfolder_path, subfolder_name)
                
                if not ruler_image_path:
                    print(f"  No ruler in {subfolder_name}. Skip.")
                    self.total_err += 1
                    print("-" * 40)
                    continue
                
                # Process the ruler image
                result = self._process_subfolder(
                    subfolder_path, subfolder_name, ruler_image_path, 
                    current_prog_base, prog_per_folder
                )
                
                if result:
                    self.total_ok += 1
                else:
                    self.total_err += 1
                    
            except Exception as e:
                print(f"  ERROR processing set '{subfolder_name}': {e}")
                self.total_err += 1
            finally:
                self.progress_callback(int(current_prog_base + prog_per_folder))
                print("-" * 40)
        
        # Final report
        print(f"\n--- Processing Complete ---\n"
              f"RAW converted: {self.cr2_conv_total}\n"
              f"Sets OK: {self.total_ok}\n"
              f"Sets Error: {self.total_err}\n")
        
        self.progress_callback(100)
        self.finished_callback()
        
        return WorkflowResult(
            total_ok=self.total_ok,
            total_err=self.total_err,
            cr2_conv_total=self.cr2_conv_total
        )
    
    def _find_ruler_image(self, subfolder_path: str, subfolder_name: str) -> Optional[str]:
        """Find the ruler image in the subfolder"""
        all_files = [f for f in os.listdir(subfolder_path) 
                   if os.path.isfile(os.path.join(subfolder_path, f))]
        
        # Count relevant files
        rel_count = 0
        pr02 = None
        pr03 = None
        
        for file_name in all_files:
            file_name_lower = file_name.lower()
            full_path = os.path.join(subfolder_path, file_name)
            
            if (file_name_lower.endswith(self.config.raw_ext) or 
                any(file_name_lower.endswith(ext) for ext in self.config.valid_img_exts)):
                rel_count += 1
                
                if "_02." in file_name:
                    pr02 = full_path
                if "_03." in file_name:
                    pr03 = full_path
        
        # Decision logic for which ruler to use
        if rel_count == 2 and pr02:
            return pr02
        elif rel_count >= 6 and pr03:
            return pr03
        elif pr02:
            return pr02
        elif pr03:
            return pr03
        
        return None
    
    def _process_subfolder(self, subfolder_path: str, subfolder_name: str, 
                         ruler_image_path: str, current_prog_base: float, 
                         prog_per_folder: float) -> bool:
        """Process a single subfolder"""
        accumulated_sub_progress = 0.0
        
        # 1. Process ruler for scale calculation
        pixels_per_cm, accumulated_sub_progress = self._process_ruler_for_scale(
            ruler_image_path, subfolder_path, current_prog_base, 
            accumulated_sub_progress, prog_per_folder
        )
        
        # 2. Extract central artifact and ruler
        artifact_path, artifact_contour, ruler_image_array, accumulated_sub_progress = self._extract_artifact_and_ruler(
            ruler_image_path, subfolder_path, current_prog_base, 
            accumulated_sub_progress, prog_per_folder
        )
        
        # 3. Process ruler template
        accumulated_sub_progress = self._process_ruler_template(
            artifact_path, pixels_per_cm, subfolder_name, subfolder_path, 
            current_prog_base, accumulated_sub_progress, prog_per_folder
        )
        
        # 4. Process other views
        accumulated_sub_progress = self._process_other_views(
            ruler_image_path, subfolder_path, subfolder_name,
            current_prog_base, accumulated_sub_progress, prog_per_folder
        )
        
        # 5. Process tablet stitching
        success = self.stitch_coordinator.process_tablet_subfolder(
            subfolder_path, pixels_per_cm, ruler_image_path, subfolder_name
        )
        
        return success
    
    def _process_ruler_for_scale(self, ruler_path: str, subfolder_path: str, 
                               current_prog_base: float, accumulated_progress: float,
                               prog_per_folder: float) -> Tuple[float, float]:
        """Process ruler for scale calculation and return pixels per cm"""
        # If ruler is a RAW file, convert it first
        is_temp_file = False
        temp_file_path = None
        
        try:
            current_ruler_path = ruler_path
            
            if self.image_processor.is_raw_file(ruler_path):
                temp_file_path = self.image_processor.get_temp_conversion_path(ruler_path, "rawscale")
                self.image_processor.convert_raw_to_tiff(ruler_path, temp_file_path)
                current_ruler_path = temp_file_path
                is_temp_file = True
                self.cr2_conv_total += 1
            
            # Calculate pixels per cm from ruler
            pixels_per_cm = self.ruler_handler.estimate_pixels_per_cm(current_ruler_path)
            
            # Clean up temp file if needed
            if is_temp_file and temp_file_path and os.path.exists(temp_file_path):
                self.image_processor.delete_temp_file(temp_file_path)
            
            # Update progress
            accumulated_progress += self.step_allocation.scale * prog_per_folder
            self.progress_callback(int(current_prog_base + accumulated_progress))
            
            return pixels_per_cm, accumulated_progress
            
        except Exception as e:
            # Clean up temp file in case of error
            if is_temp_file and temp_file_path and os.path.exists(temp_file_path):
                self.image_processor.delete_temp_file(temp_file_path)
            raise RuntimeError(f"Failed to process ruler for scale: {e}")
    
    def _extract_artifact_and_ruler(self, ruler_path: str, subfolder_path: str, 
                                  current_prog_base: float, accumulated_progress: float, 
                                  prog_per_folder: float) -> Tuple[str, Optional[np.ndarray], np.ndarray, float]:
        """Extract artifact and ruler from the image"""
        # If ruler image is a RAW file, convert it first
        is_temp_file = False
        temp_file_path = None
        
        try:
            current_ruler_path = ruler_path
            
            if self.image_processor.is_raw_file(ruler_path):
                temp_file_path = self.image_processor.get_temp_conversion_path(ruler_path, "rawextract")
                self.image_processor.convert_raw_to_tiff(ruler_path, temp_file_path)
                current_ruler_path = temp_file_path
                is_temp_file = True
                self.cr2_conv_total += 1
            
            # Extract central artifact
            artifact_path, artifact_contour = self.artifact_processor.extract_center_object(current_ruler_path)
            
            # Update progress
            accumulated_progress += self.step_allocation.ruler_art * prog_per_folder
            self.progress_callback(int(current_prog_base + accumulated_progress))
            
            # Load the ruler image
            ruler_image_array = self.image_processor.load_image(current_ruler_path)
            
            # Extract ruler contour and create isolated ruler image
            ruler_contour = self.ruler_handler.extract_ruler_contour(
                ruler_image_array, artifact_contour, self.config.obj_bg_mode
            )
            
            temp_ruler_path = None
            if ruler_contour is not None:
                ruler_image = self.ruler_handler.extract_ruler_to_image(ruler_image_array, ruler_contour)
                temp_ruler_path = self.ruler_handler.save_extracted_ruler(ruler_image, subfolder_path)
            else:
                print("    Warning: Could not isolate physical ruler part.")
            
            # Clean up temp files
            if is_temp_file and temp_file_path and os.path.exists(temp_file_path):
                self.image_processor.delete_temp_file(temp_file_path)
            
            # Update progress
            accumulated_progress += self.step_allocation.ruler_part_extract * prog_per_folder
            self.progress_callback(int(current_prog_base + accumulated_progress))
            
            return artifact_path, artifact_contour, ruler_image_array, accumulated_progress
            
        except Exception as e:
            # Clean up temp files in case of error
            if is_temp_file and temp_file_path and os.path.exists(temp_file_path):
                self.image_processor.delete_temp_file(temp_file_path)
            raise RuntimeError(f"Failed to extract artifact and ruler: {e}")
    
    def _process_ruler_template(self, artifact_path: str, pixels_per_cm: float, 
                              subfolder_name: str, subfolder_path: str,
                              current_prog_base: float, accumulated_progress: float,
                              prog_per_folder: float) -> float:
        """Process and resize ruler template"""
        try:
            # Calculate artifact dimensions
            artifact_image = self.image_processor.load_image(artifact_path)
            artifact_width_cm = artifact_image.shape[1] / pixels_per_cm if pixels_per_cm > 0 else 0
            
            # Choose appropriate ruler template
            template_path, custom_size_cm = self.ruler_handler.choose_ruler_template(
                artifact_width_cm, pixels_per_cm
            )
            
            # Update progress
            accumulated_progress += self.step_allocation.digital_ruler_choice * prog_per_folder
            self.progress_callback(int(current_prog_base + accumulated_progress))
            
            # Resize ruler template
            self.ruler_handler.resize_ruler_template(
                pixels_per_cm, template_path, subfolder_name, subfolder_path, custom_size_cm
            )
            
            # Clean up any temporary files
            temp_ruler_path = os.path.join(subfolder_path, self.config.temp_extracted_ruler_filename)
            if os.path.exists(temp_ruler_path):
                self.image_processor.delete_temp_file(temp_ruler_path)
            
            # Update progress
            accumulated_progress += self.step_allocation.digital_ruler_resize * prog_per_folder
            self.progress_callback(int(current_prog_base + accumulated_progress))
            
            return accumulated_progress
            
        except Exception as e:
            raise RuntimeError(f"Failed to process ruler template: {e}")
    
    def _process_other_views(self, ruler_path: str, subfolder_path: str, subfolder_name: str,
                           current_prog_base: float, accumulated_progress: float,
                           prog_per_folder: float) -> float:
        """Process other views in the subfolder"""
        try:
            # Find all view images
            views = self.stitch_coordinator.find_tablet_views(subfolder_path, subfolder_name)
            
            # Filter out the ruler image
            other_views = [path for key, path in views.items() if path != ruler_path]
            num_other_views = len(other_views)
            
            if num_other_views == 0:
                return accumulated_progress + (self.step_allocation.other_obj * prog_per_folder)
            
            # Calculate progress per view
            prog_per_view = (self.step_allocation.other_obj * prog_per_folder) / num_other_views
            current_other_views_prog = 0.0
            
            # Process each view
            for view_path in other_views:
                # If the view is a RAW file, convert it first
                current_view_path = view_path
                is_temp_file = False
                
                if self.image_processor.is_raw_file(view_path):
                    temp_file_path = self.image_processor.get_temp_conversion_path(view_path, "rawobj_other")
                    self.image_processor.convert_raw_to_tiff(view_path, temp_file_path)
                    current_view_path = temp_file_path
                    is_temp_file = True
                    self.cr2_conv_total += 1
                
                # Extract artifact from this view
                self.artifact_processor.extract_center_object(current_view_path)
                
                # Clean up temp file if needed
                if is_temp_file and os.path.exists(current_view_path):
                    self.image_processor.delete_temp_file(current_view_path)
                
                # Update progress
                current_other_views_prog += prog_per_view
                self.progress_callback(int(current_prog_base + accumulated_progress + current_other_views_prog))
            
            return accumulated_progress + self.step_allocation.other_obj * prog_per_folder
            
        except Exception as e:
            raise RuntimeError(f"Failed to process other views: {e}")
