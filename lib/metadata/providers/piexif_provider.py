import piexif
import os
import cv2
from metadata.domain import ImageMetadata
from metadata.providers.base import MetadataProvider


class PiexifProvider(MetadataProvider):
    def is_available(self) -> bool:
        return True
    
    def apply_metadata(self, image_path: str, metadata: ImageMetadata) -> bool:
        try:
            if not os.path.exists(image_path):
                return False
                
            file_ext = os.path.splitext(image_path.lower())[1]
            if file_ext not in ['.tif', '.tiff', '.jpg', '.jpeg']:
                return False
            
            exif_dictionary = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            exif_dictionary["0th"][piexif.ImageIFD.Artist] = f"{metadata.photographer_name} ({metadata.institution_name})".encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Copyright] = metadata.copyright_text.encode('utf-8')
            exif_dictionary["0th"][40095] = metadata.copyright_text.encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.ImageDescription] = metadata.title.encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.Software] = "eBL Photo Stitcher".encode('utf-8')
            exif_dictionary["0th"][piexif.ImageIFD.XResolution] = (metadata.image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.YResolution] = (metadata.image_dpi, 1)
            exif_dictionary["0th"][piexif.ImageIFD.ResolutionUnit] = 2  # Inches
            exif_dictionary["0th"][270] = metadata.title.encode('utf-8')  # Image Description
            
            exif_bytes = piexif.dump(exif_dictionary)
            
            piexif.insert(exif_bytes, image_path)
            return True
            
        except Exception:
            return False
