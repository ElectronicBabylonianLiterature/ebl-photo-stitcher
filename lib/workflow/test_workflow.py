"""
This is a test script to verify that our refactored workflow works as expected.
"""

import sys
import os
from gui_workflow_runner_new import run_complete_image_processing_workflow

# Add parent directory to path so we can import from lib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test configuration
SOURCE_FOLDER = r"d:\GitRepo\ebl-photo-stitcher\Examples\TIFF"
RULER_POSITION = "top"
PHOTOGRAPHER = "Test Photographer"
OBJ_BG_MODE = "auto"
ADD_LOGO = False
LOGO_PATH = None
RAW_EXT = ".cr2"
VALID_IMG_EXTS = [".jpg", ".jpeg", ".tiff", ".tif", ".png"]
TEMPLATE_1CM = r"d:\GitRepo\ebl-photo-stitcher\assets\BM_1cm_scale.tif"
TEMPLATE_2CM = r"d:\GitRepo\ebl-photo-stitcher\assets\BM_2cm_scale.tif"
TEMPLATE_5CM = r"d:\GitRepo\ebl-photo-stitcher\assets\BM_5cm_scale.tif"
VIEW_SUFFIX_PATTERNS = {
    "obverse": "_01.",
    "reverse": "_02.",
    "left": "_03.",
    "right": "_04.",
    "top": "_05.",
    "bottom": "_06."
}
TEMP_RULER_FILENAME = "temp_ruler_extracted.png"
OBJ_ARTIFACT_SUFFIX = "_artifact.png"
MUSEUM = "British Museum"

# Define callbacks
def progress_callback(percentage):
    print(f"Progress: {percentage}%")

def finished_callback():
    print("Processing finished!")

# Run the workflow
if __name__ == "__main__":
    print("Running workflow test...")
    run_complete_image_processing_workflow(
        SOURCE_FOLDER,
        RULER_POSITION,
        PHOTOGRAPHER,
        OBJ_BG_MODE,
        ADD_LOGO,
        LOGO_PATH,
        RAW_EXT,
        VALID_IMG_EXTS,
        TEMPLATE_1CM,
        TEMPLATE_2CM,
        TEMPLATE_5CM,
        VIEW_SUFFIX_PATTERNS,
        TEMP_RULER_FILENAME,
        OBJ_ARTIFACT_SUFFIX,
        progress_callback,
        finished_callback,
        MUSEUM
    )
