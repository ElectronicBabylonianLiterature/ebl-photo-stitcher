"""
Pure Python metadata handling module.
This module uses pyexiv2 to handle all types of metadata (EXIF, XMP, IPTC) when available.
"""

import os
import sys
import datetime
import piexif
import cv2
import shutil

# Try to import pyexiv2 - modern version
pyexiv2 = None
exiv2_module_name = None

try:
    import pyexiv2
    exiv2_module_name = "pyexiv2"
    print("Imported pyexiv2 module successfully")
    
    # Check which API style the imported module uses
    if hasattr(pyexiv2, 'Image'):
        print("Using modern pyexiv2 API with Image class")
    else:
        print("WARNING: The installed pyexiv2 module doesn't provide the expected API")
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
            exif_dictionary["0th"][piexif.ImageIFD.ImageDescription] = image_title.encode('utf-8')
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
    try:
        # Create a temporary file path with correct extension
        file_ext = os.path.splitext(image_path.lower())[1]
        temp_file = os.path.splitext(image_path)[0] + "_clean" + file_ext
        
        # Read and write the image to clean metadata
        img = cv2.imread(image_path)
        if img is None:
            print(f"      Warning: Could not read image to clean metadata: {image_path}")
            return False
            
        # Save with appropriate parameters based on file type
        if file_ext in ['.tif', '.tiff']:
            # For TIFF files
            success = cv2.imwrite(temp_file, img, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
        elif file_ext in ['.jpg', '.jpeg']:
            # For JPEG files
            success = cv2.imwrite(temp_file, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            # For other file types
            success = cv2.imwrite(temp_file, img)
        
        if success and os.path.exists(temp_file):
            # Replace original with cleaned version
            os.remove(image_path)
            os.rename(temp_file, image_path)
            print(f"      Successfully cleaned image metadata.")
            return True
        else:
            print(f"      Failed to write cleaned image to {temp_file}")
            # Try alternative approach with modern pyexiv2 if available
            if pyexiv2 and hasattr(pyexiv2, 'Image'):
                try:
                    print(f"      Trying pyexiv2 to clear metadata...")
                    img = pyexiv2.Image(image_path)
                    img.clear_exif()
                    img.clear_xmp()
                    img.clear_iptc()
                    img.close()
                    print(f"      Successfully cleared metadata with pyexiv2.")
                    return True
                except Exception as pyexiv_err:
                    print(f"      Failed to clear metadata with pyexiv2: {pyexiv_err}")
        
        return False
    except Exception as clean_err:
        print(f"      Warning: Failed to clean image metadata: {clean_err}")
        # If temp file exists but something failed, try to clean up
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
            
        # Try alternative approach with modern pyexiv2 if available
        if pyexiv2 and hasattr(pyexiv2, 'Image'):
            try:
                print(f"      Trying pyexiv2 to clear metadata...")
                img = pyexiv2.Image(image_path)
                img.clear_exif()
                img.clear_xmp()
                img.clear_iptc()
                img.close()
                print(f"      Successfully cleared metadata with pyexiv2.")
                return True
            except Exception as pyexiv_err:
                print(f"      Failed to clear metadata with pyexiv2: {pyexiv_err}")
                
        return False

def apply_metadata_with_pyexiv2(
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
    Apply metadata using pyexiv2 with special handling for TIFF and JPEG files.
    Using the modern pyexiv2 API with Image class.
    """
    try:
        print(f"      Using {exiv2_module_name} for metadata...")
        
        # Special handling for TIFF files - we'll use a different approach
        file_ext = os.path.splitext(image_path.lower())[1]
        is_tiff = file_ext in ('.tif', '.tiff')
        
        # Make a backup copy just in case
        backup_path = None
        try:
            backup_path = image_path + ".backup"
            shutil.copy2(image_path, backup_path)
        except Exception as backup_err:
            print(f"      Warning: Could not create backup: {backup_err}")
            backup_path = None
            
        # For TIFF files, use a clean-and-rebuild approach
        if is_tiff:
            # First clean the file to remove any problematic metadata
            clean_image_metadata(image_path)
            
        # Modern pyexiv2 API uses the Image class
        if hasattr(pyexiv2, 'Image'):
            # Use modern pyexiv2 API
            try:
                print("      Using pyexiv2.Image API")
                img = pyexiv2.Image(image_path)
                
                # Prepare EXIF data dictionary
                exif_data = {
                    'Exif.Image.Artist': f"{photographer_name} ({institution_name})",
                    'Exif.Image.Copyright': copyright_text,
                    'Exif.Image.ImageDescription': image_title,
                    'Exif.Image.Software': "eBL Photo Stitcher",
                    'Exif.Image.XResolution': (image_dpi, 1),
                    'Exif.Image.YResolution': (image_dpi, 1),
                    'Exif.Image.ResolutionUnit': 2  # Inches
                }
                
                # Prepare XMP data dictionary
                xmp_data = {
                    'Xmp.dc.title': image_title,
                    'Xmp.dc.creator': photographer_name,
                    'Xmp.dc.rights': copyright_text,
                    'Xmp.dc.description': image_title,
                    'Xmp.photoshop.Credit': credit_line_text,
                    'Xmp.photoshop.Source': institution_name,
                    'Xmp.xmpRights.Marked': "True"
                }
                
                if usage_terms_text:
                    xmp_data['Xmp.xmpRights.UsageTerms'] = usage_terms_text
                
                xmp_data['Xmp.xmp.MetadataDate'] = datetime.datetime.now().isoformat()
                
                # First clear existing metadata
                try:
                    img.clear_exif()
                    img.clear_xmp()
                    img.clear_iptc()
                except Exception as clear_err:
                    print(f"      Warning: Could not clear existing metadata: {clear_err}")
                
                # Set new metadata
                img.modify_exif(exif_data)
                img.modify_xmp(xmp_data)
                
                # Save changes
                img.close()
                print(f"      Successfully applied metadata via {exiv2_module_name} Image API.")
                
                # If we successfully wrote metadata, remove the backup
                if backup_path and os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                    except:
                        pass
                        
                return True
                
            except Exception as img_err:
                print(f"      Error using Image API: {img_err}")
                # Continue to fallback approach
                pass
        
        # If we got here, we couldn't use the modern API or it failed
        print("      WARNING: Modern pyexiv2.Image API not available. Falling back to piexif.")
        
        # If we had a backup and the operation failed, restore it
        if backup_path and os.path.exists(backup_path):
            try:
                print("      Restoring backup...")
                if os.path.exists(image_path):
                    os.remove(image_path)
                shutil.copy2(backup_path, image_path)
                os.remove(backup_path)
            except Exception as restore_err:
                print(f"      Error restoring backup: {restore_err}")
        
        # Fall back to piexif for basic EXIF
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name, 
            institution_name, copyright_text, image_dpi
        )
    except Exception as e:
        print(f"      Error applying metadata with {exiv2_module_name}: {e}")
        
        # If we had a backup, restore it
        if backup_path and os.path.exists(backup_path):
            try:
                print("      Restoring backup due to error...")
                if os.path.exists(image_path):
                    os.remove(image_path)
                shutil.copy2(backup_path, image_path)
                os.remove(backup_path)
            except:
                pass
                
        # Fall back to piexif
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name, 
            institution_name, copyright_text, image_dpi
        )

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
        # Try applying metadata with pyexiv2 first
        success = apply_metadata_with_pyexiv2(
            image_path, image_title, photographer_name, institution_name,
            credit_line_text, copyright_text, usage_terms_text, image_dpi
        )
        
        if success:
            return True
        
        # If pyexiv2 failed, fall back to piexif
        print("      Falling back to piexif for basic EXIF...")
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name, 
            institution_name, copyright_text, image_dpi
        )
    else:
        # Fall back to piexif for basic EXIF if pyexiv2 is not available
        print("      No advanced metadata modules available, using piexif for basic EXIF.")
        return set_basic_exif_metadata(
            image_path, image_title, photographer_name, 
            institution_name, copyright_text, image_dpi
        )
