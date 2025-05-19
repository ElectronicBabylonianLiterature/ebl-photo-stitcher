"""
This module provides the main entry point for running the image processing workflow from the GUI.
It uses the refactored workflow module to execute the complete process.
"""

from workflow.runner import run_complete_image_processing_workflow as run_workflow
import sys


def run_complete_image_processing_workflow(*args, **kwargs):
    """
    Wrapper function that forwards calls to the refactored workflow implementation.
    This maintains backward compatibility with existing code.
    
    All parameters are passed directly to the new implementation.
    """
    return run_workflow(*args, **kwargs)
