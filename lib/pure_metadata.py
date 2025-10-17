"""
Pure Python metadata handling module.
This module uses pyexiv2 or pyexiv2 to handle all types of metadata (EXIF, XMP, IPTC) when available.
"""

import os
import sys
import datetime
import piexif
import cv2
import shutil
import time

pyexiv2 = None
exiv2_module_name = None

try:
    import pyexiv2
    exiv2_module_name = "pyexiv2"
except ImportError:
    print("Warning: pyexiv2 not installed. Some metadata functionality will be limited.")
    print("To install: pip install pyexiv2")


def is_exiv2_available():
    """Check if any exiv2 module is available."""
    return pyexiv2 is not None


def set_basic_exif_metadata(image_path, image_title, photographer_name, institution_name, copyright_text, image_dpi):
    """
    Set basic EXIF metadata using piexif (fallback method).
    This is used when pyexiv2 is not available.
    Works with both TIFF and JPEG files.
    """
    try:

        if not os.path.exists(image_path):
            print(f"      Error: File not found: {image_path}")
            return False

        file_ext = os.path.splitext(image_path.lower())[1]
        if file_ext not in ['.tif', '.tiff', '.jpg', '.jpeg']:
            print(f"      Warning: Unsupported file format for piexif: {file_ext}")

        exif_dictionary = {"0th": {}, "Exif": {},
                           "GPS": {}, "1st": {}, "thumbnail": None}

        try:
            exif_dictionary["0th"][piexif.ImageIFD.Artist] = f"{photographer_name} ({institution_name})".encode(
                'utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode(
                'utf-8')

            exif_dictionary["0th"][40095] = copyright_text.encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.ImageDescription] = copyright_text.encode(
                'utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Software] = "eBL Photo Stitcher".encode(
                'utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.XResolution] = (image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.YResolution] = (image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.ResolutionUnit] = 2

            exif_dictionary["0th"][270] = image_title.encode('utf-8')

            exif_bytes = piexif.dump(exif_dictionary)

            try:
                piexif.insert(exif_bytes, image_path)
                print(
                    f"      EXIF metadata applied successfully to {os.path.basename(image_path)} via piexif.")
                return True
            except Exception as insert_err:

                if file_ext in ['.jpg', '.jpeg']:
                    print(f"      Alternative method for JPEG metadata...")

                    img = cv2.imread(image_path)
                    if img is not None:
                        temp_path = f"{image_path}.temp"
                        if cv2.imwrite(temp_path, img):
                            try:
                                piexif.insert(exif_bytes, temp_path)
                                os.remove(image_path)
                                os.rename(temp_path, image_path)
                                print(
                                    f"      EXIF metadata applied successfully via alternative method.")
                                return True
                            except Exception as alt_err:
                                print(f"      Error with alternative method: {alt_err}")
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                return False
                raise insert_err

        except Exception as field_error:
            print(f"      Warn: Error setting specific EXIF field: {field_error}")
            return False
    except Exception as e:
        print(f"      Warn: piexif metadata error: {e}")
        return False


def apply_all_metadata(
    image_path,
    image_title,
    photographer_name,
    institution_name,
    credit_line_text,
    copyright_text,
    usage_terms_text=None,
    image_dpi=600
):
    """
    Apply all metadata (EXIF, XMP, IPTC) using pyexiv2 when available.
    Falls back to piexif for basic EXIF if pyexiv2 is not available.
    Works with both TIFF and JPG files.

    Returns True if successful, False otherwise.
    """
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        return False

    file_ext = os.path.splitext(image_path.lower())[1]
    is_tiff = file_ext in ('.tif', '.tiff')
    is_jpeg = file_ext in ('.jpg', '.jpeg')

    if not (is_tiff or is_jpeg):
        print(
            f"Warning: Unsupported file format: {file_ext}. Only TIFF and JPEG are supported.")
        return False

    if pyexiv2:
        img = None
        backup_path = None
        try:
            import time
            
            time.sleep(0.1)

            try:
                backup_path = image_path + ".backup"
                shutil.copy2(image_path, backup_path)
            except Exception as e_backup:
                print(
                    f"      Warning: Could not create backup for {image_path}: {e_backup}")
                backup_path = None

            img = pyexiv2.Image(image_path)
            existing_exif = img.read_exif()
            existing_xmp = img.read_xmp()

            new_exif_data = {}
            new_xmp_data = {}

            new_exif_data['Exif.Image.Artist'] = f"{photographer_name}"
            new_exif_data['Exif.Image.Copyright'] = copyright_text
            new_exif_data['Exif.Image.ImageDescription'] = image_title
            new_exif_data['Exif.Image.Software'] = "eBL Photo Stitcher"

            new_exif_data['Exif.Image.XResolution'] = f"{image_dpi}/1"
            new_exif_data['Exif.Image.YResolution'] = f"{image_dpi}/1"
            new_exif_data['Exif.Image.ResolutionUnit'] = '2'

            new_xmp_data['Xmp.dc.title'] = image_title
            new_xmp_data['Xmp.dc.creator'] = [photographer_name]
            new_xmp_data['Xmp.dc.rights'] = copyright_text
            new_xmp_data['Xmp.dc.description'] = image_title

            new_xmp_data['Xmp.dc.subject'] = copyright_text

            new_xmp_data['Xmp.photoshop.Credit'] = credit_line_text
            new_xmp_data['Xmp.photoshop.Source'] = institution_name

            new_xmp_data['Xmp.xmpRights.Marked'] = 'True'
            if usage_terms_text:
                new_xmp_data['Xmp.xmpRights.UsageTerms'] = [
                    {'lang': 'x-default', 'value': usage_terms_text}]

            new_xmp_data['Xmp.xmp.MetadataDate'] = datetime.datetime.now().isoformat()

            try:
                img.modify_exif(new_exif_data)
            except Exception as e_exif:
                print(f"      Warning: Could not modify EXIF: {e_exif}")
            
            try:
                img.modify_xmp(new_xmp_data)
            except Exception as e_xmp:
                print(f"      Warning: Could not modify XMP: {e_xmp}")

            try:
                img.close()
            except Exception as e_close:
                print(f"      Warning: Error closing image: {e_close}")
            finally:
                img = None

            print(
                f"      All metadata (EXIF, XMP) applied successfully via {exiv2_module_name}.")

            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except Exception as e_rem_backup:
                    print(
                        f"      Warning: Could not remove backup file {backup_path}: {e_rem_backup}")

            return True

        except Exception as e:
            print(f"      Error applying metadata with {exiv2_module_name}: {e}")
            import traceback
            traceback.print_exc()

            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
                finally:
                    img = None
            
            if backup_path and os.path.exists(backup_path):
                try:
                    print("      Restoring backup due to metadata error...")

                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                        except Exception as e_del:
                            print(f"      Warning: Could not delete corrupted file: {e_del}")
                            import time
                            time.sleep(0.5)
                            try:
                                os.remove(image_path)
                            except Exception:
                                pass
                    
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                except Exception as e_restore:
                    print(f"      Error restoring backup for {image_path}: {e_restore}")

            print("      Falling back to piexif for basic EXIF...")
            return set_basic_exif_metadata(
                image_path, image_title, photographer_name,
                institution_name, copyright_text, image_dpi
            )
        finally:

            if img is not None:
                try:
                    img.close()
                except Exception as e_close_final:
                    print(
                        f"      Warning: Error closing pyexiv2.Image in finally block: {e_close_final}")

            if backup_path and os.path.exists(backup_path) and not os.path.exists(image_path):
                try:
                    print(
                        f"      Final cleanup: Restoring backup {backup_path} as original is missing.")
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                except Exception as e_final_restore:
                    print(f"      Error in final backup restoration: {e_final_restore}")
            elif backup_path and os.path.exists(backup_path) and os.path.exists(image_path):

                print(
                    f"      Final cleanup: Removing lingering backup file {backup_path}.")
                try:
                    os.remove(backup_path)
                except Exception as e_final_remove_backup:
                    print(
                        f"      Error in final backup removal: {e_final_remove_backup}")

    else:

        print("      No advanced metadata modules available, using piexif for basic EXIF.")
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name,
            institution_name, copyright_text, image_dpi
        )
