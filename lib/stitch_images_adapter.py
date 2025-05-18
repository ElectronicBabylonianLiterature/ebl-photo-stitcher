from stitch_images import process_tablet_subfolder

# Export all the constants that might be used elsewhere
try:
    from stitch_config import (
        STITCH_VIEW_PATTERNS_CONFIG,
        STITCH_OUTPUT_DPI,
        STITCH_BACKGROUND_COLOR,
        STITCH_TIFF_COMPRESSION,
        STITCH_FINAL_MARGIN_PX,
        STITCH_VIEW_GAP_PX,
        STITCH_RULER_PADDING_PX,
        STITCH_LOGO_MAX_WIDTH_FRACTION,
        STITCH_LOGO_PADDING_ABOVE,
        STITCH_LOGO_PADDING_BELOW,
        JPEG_SAVE_QUALITY,
        FINAL_TIFF_SUBFOLDER_NAME,
        FINAL_JPG_SUBFOLDER_NAME
    )
except ImportError as e:
    print(f"Warning: Could not import constants from stitch_config: {e}")

# This approach allows for a seamless migration without breaking existing code
