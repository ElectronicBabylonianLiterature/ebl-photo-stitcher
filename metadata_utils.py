import piexif
import datetime
import subprocess
import shutil
import os

def set_basic_exif_metadata(tiff_image_path, image_title, photographer_name, institution_name, copyright_text, image_dpi):
    try:
        try: exif_dictionary = piexif.load(tiff_image_path)
        except piexif.InvalidImageDataError: exif_dictionary = {"0th":{},"Exif":{},"GPS":{},"1st":{},"thumbnail":None}
        except Exception: exif_dictionary = {"0th":{},"Exif":{},"GPS":{},"1st":{},"thumbnail":None}

        exif_dictionary["0th"][piexif.ImageIFD.Artist] = photographer_name.encode('utf-8')
        exif_dictionary["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
        exif_dictionary["0th"][piexif.ImageIFD.ImageDescription] = image_title.encode('utf-8')
        exif_dictionary["0th"][piexif.ImageIFD.Software] = "eBL Image Processor Python Script".encode('utf-8')
        exif_dictionary["0th"][piexif.ImageIFD.XResolution] = (image_dpi, 1)
        exif_dictionary["0th"][piexif.ImageIFD.YResolution] = (image_dpi, 1)
        exif_dictionary["0th"][piexif.ImageIFD.ResolutionUnit] = 2 # Inches
        piexif.insert(piexif.dump(exif_dictionary), tiff_image_path)
    except Exception as e: print(f"      Warn: piexif metadata error: {e}")

def apply_xmp_metadata_via_exiftool(
    tiff_image_path, image_title, photographer_name, institution_name,
    credit_line_text, copyright_text, usage_terms_text
):
    if shutil.which("exiftool") is None:
        print("      Warn: exiftool not found. Skipping XMP metadata."); return False
    try:
        commands = ["exiftool","-overwrite_original","-L",f"-XMP-dc:Title={image_title}",
                    f"-XMP-dc:Creator={photographer_name}",f"-XMP-dc:Rights={copyright_text}",
                    f"-XMP-photoshop:Credit={credit_line_text}",f"-XMP-photoshop:Source={institution_name}",
                    f"-XMP-xmpRights:UsageTerms={usage_terms_text}", "-XMP-xmpRights:Marked=True",
                    tiff_image_path]
        result = subprocess.run(commands,capture_output=True,text=True,check=False,encoding='utf-8',errors='replace')
        if result.returncode != 0:
            print(f"      Warn: exiftool code {result.returncode}\nStdout: {result.stdout.strip()}\nStderr: {result.stderr.strip()}")
            return False
        print("      XMP metadata applied via exiftool.")
        return True
    except Exception as e: print(f"      ERROR applying XMP with exiftool: {e}"); return False
