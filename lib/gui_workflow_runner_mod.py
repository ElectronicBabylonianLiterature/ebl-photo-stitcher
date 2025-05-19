# filepath: d:\GitRepo\ebl-photo-stitcher\lib\gui_workflow_runner.py
"""
This module provides the main function for running the image processing workflow from the GUI.
It uses the refactored workflow implementation behind the scenes.
"""

from workflow.runner import run_complete_image_processing_workflow


def run_complete_image_processing_workflow(
    source_folder_path, gui_ruler_position, gui_photographer,
    gui_obj_bg_mode, gui_add_logo, gui_logo_path,
    raw_ext_config, valid_img_exts_config,
    ruler_template_1cm_asset_path,
    ruler_template_2cm_asset_path,
    ruler_template_5cm_asset_path,
    view_original_suffix_patterns_config,
    temp_extracted_ruler_filename_config,
    object_artifact_suffix_config,
    progress_callback,
    finished_callback,
    museum_selection="British Museum"
):
    """
    Run the complete image processing workflow.
    
    This function is kept for backward compatibility and delegates to the new implementation.
    
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
    return run_complete_image_processing_workflow(
        source_folder_path=source_folder_path,
        gui_ruler_position=gui_ruler_position,
        gui_photographer=gui_photographer,
        gui_obj_bg_mode=gui_obj_bg_mode,
        gui_add_logo=gui_add_logo,
        gui_logo_path=gui_logo_path,
        raw_ext_config=raw_ext_config,
        valid_img_exts_config=valid_img_exts_config,
        ruler_template_1cm_asset_path=ruler_template_1cm_asset_path,
        ruler_template_2cm_asset_path=ruler_template_2cm_asset_path,
        ruler_template_5cm_asset_path=ruler_template_5cm_asset_path,
        view_original_suffix_patterns_config=view_original_suffix_patterns_config,
        temp_extracted_ruler_filename_config=temp_extracted_ruler_filename_config,
        object_artifact_suffix_config=object_artifact_suffix_config,
        progress_callback=progress_callback,
        finished_callback=finished_callback,
        museum_selection=museum_selection
    )
