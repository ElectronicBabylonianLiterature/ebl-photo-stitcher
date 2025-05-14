import rawpy
import imageio
import os


def convert_cr2_to_tiff(cr2_path, output_tiff_path):
    """
    Converts a CR2 RAW image to a 16-bit TIFF file with minimal processing.
    """
    print(
        f"  Converting CR2: {os.path.basename(cr2_path)} to TIFF: {os.path.basename(output_tiff_path)}")
    try:
        with rawpy.imread(cr2_path) as raw:

            rgb = raw.postprocess(
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AAHD,
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,







            )

            imageio.imwrite(output_tiff_path, rgb, format='TIFF')
        print(f"    Successfully converted CR2 to TIFF: {output_tiff_path}")
        return output_tiff_path
    except rawpy.LibRawNoThumbnailError:
        print(
            f"  Warning: LibRawNoThumbnailError for {cr2_path}. Trying to process without thumbnail data.")

        raise
    except rawpy.LibRawUnsupportedThumbnailError:
        print(
            f"  Warning: LibRawUnsupportedThumbnailError for {cr2_path}. Trying to process.")
        raise
    except Exception as e:
        print(f"  ERROR during CR2 to TIFF conversion for {cr2_path}: {e}")
        raise
