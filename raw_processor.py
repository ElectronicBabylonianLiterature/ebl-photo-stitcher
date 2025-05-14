import rawpy
import imageio # For saving TIFF
import os

def convert_cr2_to_tiff(cr2_path, output_tiff_path):
    """
    Converts a CR2 RAW image to a 16-bit TIFF file with minimal processing.
    """
    print(f"  Converting CR2: {os.path.basename(cr2_path)} to TIFF: {os.path.basename(output_tiff_path)}")
    try:
        with rawpy.imread(cr2_path) as raw:
            # Basic parameters for a 'neutral' conversion
            # Disabling auto_bright and no_auto_scale helps get closer to raw data
            # Use camera white balance if available
            # Outputting 16-bit for better quality TIFF
            # Demosaicing algorithm can be chosen based on quality/speed needs
            # AAHD is generally good quality.
            rgb = raw.postprocess(
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AAHD,
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,
                # For sharpening: rawpy doesn't have a direct "set sharpening to 0"
                # The best approach is to use a demosaic algorithm that doesn't inherently sharpen much
                # and avoid auto-enhancements. Further sharpening control would typically be
                # in a dedicated RAW developer.
                # We are aiming for a less processed image here.
                # params.sharpen_threshold and params.sharpen_amount could be explored if needed,
                # but default behavior with AAHD and no_auto_bright is often less sharpened.
            )
            
            # imageio expects channels-last format (height, width, channels)
            # rawpy output is typically (height, width, 3)
            imageio.imwrite(output_tiff_path, rgb, format='TIFF')
        print(f"    Successfully converted CR2 to TIFF: {output_tiff_path}")
        return output_tiff_path
    except rawpy.LibRawNoThumbnailError:
        print(f"  Warning: LibRawNoThumbnailError for {cr2_path}. Trying to process without thumbnail data.")
        # Attempt to process without thumbnail-dependent features if possible, or re-raise
        # For now, we'll let it fail if it's critical, but this indicates a potentially problematic CR2.
        raise
    except rawpy.LibRawUnsupportedThumbnailError:
        print(f"  Warning: LibRawUnsupportedThumbnailError for {cr2_path}. Trying to process.")
        raise
    except Exception as e:
        print(f"  ERROR during CR2 to TIFF conversion for {cr2_path}: {e}")
        raise # Re-raise the exception to be caught by the main orchestrator
