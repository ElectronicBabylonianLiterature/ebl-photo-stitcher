"""
This module provides the main entry point for running the image processing workflow.
It uses the refactored workflow module to execute the complete process.
"""

import os
from typing import Optional, Callable, Any, Dict

from workflow.domain.models import (
    WorkflowConfig, 
    RulerTemplates, 
    ProgressCallback, 
    FinishedCallback
)
from workflow.services.executor import WorkflowExecutor


def run_complete_image_processing_workflow(
    source_folder_path: str,
    gui_ruler_position: str,
    gui_photographer: str,
    gui_obj_bg_mode: str,
    gui_add_logo: bool,
    gui_logo_path: Optional[str],
    raw_ext_config: str,
    valid_img_exts_config: list,
    ruler_template_1cm_asset_path: str,
    ruler_template_2cm_asset_path: str,
    ruler_template_5cm_asset_path: str,
    view_original_suffix_patterns_config: Dict[str, str],
    temp_extracted_ruler_filename_config: str,
    object_artifact_suffix_config: str,
    progress_callback: ProgressCallback,
    finished_callback: FinishedCallback,
    museum_selection: str = "British Museum"
) -> None:
    """
    Run the complete image processing workflow using the refactored workflow module.
    
    Args:
        source_folder_path: Path to the source folder containing images
        gui_ruler_position: Position of the ruler in the images
        gui_photographer: Name of the photographer
        gui_obj_bg_mode: Background mode for object extraction
        gui_add_logo: Whether to add a logo to the output
        gui_logo_path: Path to the logo image
        raw_ext_config: File extension for RAW image files
        valid_img_exts_config: List of valid image file extensions
        ruler_template_1cm_asset_path: Path to the 1cm ruler template
        ruler_template_2cm_asset_path: Path to the 2cm ruler template
        ruler_template_5cm_asset_path: Path to the 5cm ruler template
        view_original_suffix_patterns_config: Dictionary mapping view names to file suffix patterns
        temp_extracted_ruler_filename_config: Name for temporary extracted ruler file
        object_artifact_suffix_config: Suffix for extracted object files
        progress_callback: Callback function for reporting progress
        finished_callback: Callback function for reporting completion
        museum_selection: Selected museum configuration
    """
    # Create the workflow configuration
    config = WorkflowConfig(
        source_folder_path=source_folder_path,
        ruler_position=gui_ruler_position,
        photographer=gui_photographer,
        obj_bg_mode=gui_obj_bg_mode,
        add_logo=gui_add_logo,
        logo_path=gui_logo_path,
        raw_ext=raw_ext_config,
        valid_img_exts=valid_img_exts_config,
        view_original_suffix_patterns=view_original_suffix_patterns_config,
        temp_extracted_ruler_filename=temp_extracted_ruler_filename_config,
        object_artifact_suffix=object_artifact_suffix_config,
        museum_selection=museum_selection
    )
    
    # Create ruler templates configuration
    ruler_templates = RulerTemplates(
        ruler_template_1cm=ruler_template_1cm_asset_path,
        ruler_template_2cm=ruler_template_2cm_asset_path,
        ruler_template_5cm=ruler_template_5cm_asset_path
    )
    
    # Create and execute the workflow
    executor = WorkflowExecutor(
        config=config,
        ruler_templates=ruler_templates,
        progress_callback=progress_callback,
        finished_callback=finished_callback
    )
    
    executor.execute()
