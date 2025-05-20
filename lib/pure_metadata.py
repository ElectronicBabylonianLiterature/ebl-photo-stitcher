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

# Try to import pyexiv2 modules (multiple possible package names)
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
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"      Error: File not found: {image_path}")
            return False
            
        # File extension check
        file_ext = os.path.splitext(image_path.lower())[1]
        if file_ext not in ['.tif', '.tiff', '.jpg', '.jpeg']:
            print(f"      Warning: Unsupported file format for piexif: {file_ext}")
        
        # Create a clean EXIF dictionary
        exif_dictionary = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
        # Set metadata fields with error handling
        try:
            exif_dictionary["0th"][piexif.ImageIFD.Artist] = f"{photographer_name} ({institution_name})".encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
            # Additional copyright tag for some readers
            exif_dictionary["0th"][40095] = copyright_text.encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.ImageDescription] = copyright_text.encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Software] = "eBL Photo Stitcher".encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.XResolution] = (image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.YResolution] = (image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.ResolutionUnit] = 2  # Inches
            
            # Additional metadata for Title field (some viewers use this)
            exif_dictionary["0th"][270] = image_title.encode('utf-8')  # Image Description
            
            # Dump exif data with enhanced error handling
            exif_bytes = piexif.dump(exif_dictionary)
            
            # Some image formats might require different handling
            try:
                piexif.insert(exif_bytes, image_path)
                print(f"      EXIF metadata applied successfully to {os.path.basename(image_path)} via piexif.")
                return True
            except Exception as insert_err:
                # For some JPEG files, piexif.insert might fail
                if file_ext in ['.jpg', '.jpeg']:
                    print(f"      Alternative method for JPEG metadata...")
                    # Read the image and write it back with metadata
                    img = cv2.imread(image_path)
                    if img is not None:
                        temp_path = f"{image_path}.temp"
                        if cv2.imwrite(temp_path, img):
                            try:
                                piexif.insert(exif_bytes, temp_path)
                                os.remove(image_path)
                                os.rename(temp_path, image_path)
                                print(f"      EXIF metadata applied successfully via alternative method.")
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

def clean_image_metadata(image_path):
    """Clean problematic metadata like shape data from the image"""
    temp_file_path = None  # Initialize for cleanup logic
    try:
        # Create a temporary file path with the original extension
        base, file_ext = os.path.splitext(image_path)
        # Ensure the temporary filename is distinct before overwriting
        temp_file_path = base + "_cleaning_temp" + file_ext

        img = cv2.imread(image_path)
        if img is None:
            print(f"      Warning: Could not read image to clean metadata: {image_path}")
            return False
        
        write_success = False
        # Save with appropriate parameters based on file type, using the original extension for the temp file
        if file_ext.lower() in ['.tif', '.tiff']:
            write_success = cv2.imwrite(temp_file_path, img, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
        elif file_ext.lower() in ['.jpg', '.jpeg']:
            # This branch may not be hit if clean_image_metadata is only called for TIFFs
            # from apply_all_metadata, but included for generality.
            write_success = cv2.imwrite(temp_file_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            # This case implies an unsupported file type for this cleaning function's specific parameters.
            # OpenCV's imwrite might still fail if it doesn't support writing this extension.
            print(f"      Warning: Attempting to clean metadata for an extension '{file_ext}' by simple re-save. OpenCV might not support writing this format.")
            write_success = cv2.imwrite(temp_file_path, img)
            
        if not write_success:
            print(f"      Warning: cv2.imwrite failed for temporary file: {temp_file_path}")
            if os.path.exists(temp_file_path): # Attempt to remove if partially created
                try:
                    os.remove(temp_file_path)
                except Exception as e_rem:
                    print(f"        Could not remove partially written temp file {temp_file_path}: {e_rem}")
            return False
            
        # If imwrite was successful, the temporary file should exist.
        # Replace original with cleaned version
        os.remove(image_path)
        os.rename(temp_file_path, image_path)
        print(f"      Successfully cleaned image metadata for {os.path.basename(image_path)}.")
        return True

    except Exception as clean_err:
        print(f"      Warning: Failed to clean image metadata for {os.path.basename(image_path)}: {clean_err}")
        # If temp file path was defined and exists, try to clean it up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_rem_err:
                 print(f"        Could not remove temp file {temp_file_path} during error cleanup: {e_rem_err}")
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
        print(f"Warning: Unsupported file format: {file_ext}. Only TIFF and JPEG are supported.")
        return False
    
    print(f"    Setting metadata for: {os.path.basename(image_path)}")
    
    # Try to fix any problematic metadata first
    try:
        # For TIFF files, check for shape data
        if is_tiff:
            with open(image_path, 'rb') as f:
                file_start = f.read(1000)  # Read first 1000 bytes to check
                if b'{"shape"' in file_start:
                    print("      Detected problematic shape data, cleaning...")
                    clean_image_metadata(image_path)
    except Exception as e:
        print(f"      Warning: Error checking for shape data: {e}")
    
    # If exiv2 module is available, use it for comprehensive metadata handling
    if pyexiv2:
        img = None # Initialize img to None for the finally block
        backup_path = None # Initialize backup_path for the finally block
        try:
            print(f"      Using {exiv2_module_name} for advanced metadata...")
            
            # Make a backup copy just in case
            try:
                backup_path = image_path + ".backup"
                shutil.copy2(image_path, backup_path)
            except Exception as e_backup:
                print(f"      Warning: Could not create backup for {image_path}: {e_backup}")
                backup_path = None # Ensure backup_path is None if creation failed
                
            # Open the image
            img = pyexiv2.Image(image_path) # Correct API for pyexiv2
            existing_exif = img.read_exif()
            existing_xmp = img.read_xmp()
            
            # Prepare new metadata dictionaries
            new_exif_data = {}
            new_xmp_data = {}
            
            # Set EXIF metadata
            new_exif_data['Exif.Image.Artist'] = f"{photographer_name} ({institution_name})"
            new_exif_data['Exif.Image.Copyright'] = copyright_text
            new_exif_data['Exif.Image.ImageDescription'] = image_title
            new_exif_data['Exif.Image.Software'] = "eBL Photo Stitcher"
            
            # pyexiv2 expects resolution as string "value/1"
            new_exif_data['Exif.Image.XResolution'] = f"{image_dpi}/1"
            new_exif_data['Exif.Image.YResolution'] = f"{image_dpi}/1"
            new_exif_data['Exif.Image.ResolutionUnit'] = '2'  # Inches, pyexiv2 expects string for some numeric tags
            
            # Set XMP metadata (Dublin Core)
            new_xmp_data['Xmp.dc.title'] = [{'lang': 'x-default', 'value': image_title}] # XMP often needs lang qualifier
            new_xmp_data['Xmp.dc.creator'] = [photographer_name]
            new_xmp_data['Xmp.dc.rights'] = [{'lang': 'x-default', 'value': copyright_text}]
            new_xmp_data['Xmp.dc.description'] = [{'lang': 'x-default', 'value': image_title}]
            
            # Set subjects/keywords
            new_xmp_data['Xmp.dc.subject'] = copyright_text
            
            # Set XMP metadata (Photoshop)
            new_xmp_data['Xmp.photoshop.Credit'] = credit_line_text
            new_xmp_data['Xmp.photoshop.Source'] = institution_name
            
            # Set XMP Rights Management metadata
            new_xmp_data['Xmp.xmpRights.Marked'] = 'True' # pyexiv2 often expects string booleans
            if usage_terms_text:
                new_xmp_data['Xmp.xmpRights.UsageTerms'] = [{'lang': 'x-default', 'value': usage_terms_text}]
            
            # Add additional metadata
            new_xmp_data['Xmp.xmp.MetadataDate'] = datetime.datetime.now().isoformat()
            
            # Write changes to file
            img.modify_exif(new_exif_data)
            img.modify_xmp(new_xmp_data)
            # IPTC data can be modified similarly if needed: img.modify_iptc(new_iptc_data)
            
            # Explicitly close the image to ensure file handles are released
            # This is done before removing the backup, in the main try block
            img.close()
            img = None # Set to None after successful close

            print(f"      All metadata (EXIF, XMP) applied successfully via {exiv2_module_name}.")
            
            # If we successfully wrote metadata and closed the image, remove the backup
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except Exception as e_rem_backup:
                    print(f"      Warning: Could not remove backup file {backup_path}: {e_rem_backup}")
                    
            return True
            
        except Exception as e:
            print(f"      Error applying metadata with {exiv2_module_name}: {e}")
            
            # If we had a backup and the operation failed, restore it
            if backup_path and os.path.exists(backup_path):
                try:
                    print("      Restoring backup due to metadata error...")
                    # Ensure img is closed before attempting to replace the file, if it was opened
                    if img is not None:
                        img.close()
                        img = None

                    if os.path.exists(image_path):
                        os.remove(image_path)
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                except Exception as e_restore:
                    print(f"      Error restoring backup for {image_path}: {e_restore}")
            
            # Fall back to piexif for basic EXIF
            print("      Falling back to piexif for basic EXIF...")
            return set_basic_exif_metadata(
                image_path, image_title, photographer_name, 
                institution_name, copyright_text, image_dpi
            )
        finally:
            # Ensure the image object is closed if it was opened and an unexpected error occurred
            # before the explicit close() in the try block, or if an error happened during backup removal.
            if img is not None:
                try:
                    img.close()
                except Exception as e_close_final:
                    print(f"      Warning: Error closing pyexiv2.Image in finally block: {e_close_final}")
            # Clean up backup file if it still exists and something went wrong before normal removal
            # This case is mostly for unexpected errors not covered by the main try/except for restoration.
            if backup_path and os.path.exists(backup_path) and not os.path.exists(image_path): # Original was deleted but not restored
                 try:
                    print(f"      Final cleanup: Restoring backup {backup_path} as original is missing.")
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                 except Exception as e_final_restore:
                    print(f"      Error in final backup restoration: {e_final_restore}")
            elif backup_path and os.path.exists(backup_path) and os.path.exists(image_path):
                 # If both exist, it implies the main logic for backup removal or restoration should have handled it.
                 # However, if an error occurred after successful metadata write but before backup removal, remove backup here.
                 # This is a bit of a safety net.
                 print(f"      Final cleanup: Removing lingering backup file {backup_path}.")
                 try:
                    os.remove(backup_path)
                 except Exception as e_final_remove_backup:
                    print(f"      Error in final backup removal: {e_final_remove_backup}")

    else:
        # Fall back to piexif for basic EXIF
        print("      No advanced metadata modules available, using piexif for basic EXIF.")
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name, 
            institution_name, copyright_text, image_dpi
        )
