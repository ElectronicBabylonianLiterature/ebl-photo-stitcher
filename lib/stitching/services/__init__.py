"""
Services for the stitching package.
"""
from stitching.services.image_resizer import (
    resize_tablet_views_relative_to_obverse,
    get_image_dimension
)
from stitching.services.layout_manager import (
    calculate_stitching_canvas_layout,
    get_layout_bounding_box
)
from stitching.services.canvas_processor import (
    add_logo_to_image_array,
    crop_canvas_to_content_with_margin
)
from stitching.services.stitching_service import StitchingService
