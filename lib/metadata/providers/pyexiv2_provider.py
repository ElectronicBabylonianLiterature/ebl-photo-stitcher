import os
import shutil
from typing import Optional, Dict, Any

from metadata.domain import ImageMetadata
from metadata.providers.base import MetadataProvider
from metadata.cleaner import ImageCleaner

class PyExiv2Provider(MetadataProvider):
    def __init__(self):
        self.pyexiv2 = None
        try:
            import pyexiv2
            self.pyexiv2 = pyexiv2
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.pyexiv2 is not None and hasattr(self.pyexiv2, 'Image')
    
    def apply_metadata(self, image_path: str, metadata: ImageMetadata) -> bool:
        if not self.is_available():
            return False
            
        try:
            if not os.path.exists(image_path):
                return False
                
            file_ext = os.path.splitext(image_path.lower())[1]
            is_tiff = file_ext in ('.tif', '.tiff')
            
            backup_path = None
            try:
                backup_path = image_path + ".backup"
                shutil.copy2(image_path, backup_path)
            except Exception:
                backup_path = None
            
            if is_tiff:
                ImageCleaner.clean_tiff_for_metadata(image_path)
            
            exif_data = self._prepare_exif_data(metadata)
            xmp_data = self._prepare_xmp_data(metadata)
            
            img = self.pyexiv2.Image(image_path)
            
            try:
                img.clear_exif()
                img.clear_xmp()
                img.clear_iptc()
            except Exception:
                pass
            
            img.modify_exif(exif_data)
            img.modify_xmp(xmp_data)
            
            img.close()
            
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                
            return True
            
        except Exception:
            if backup_path and os.path.exists(backup_path):
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    shutil.copy2(backup_path, image_path)
                    os.remove(backup_path)
                except Exception:
                    pass
            return False
    
    def _prepare_exif_data(self, metadata: ImageMetadata) -> Dict[str, Any]:
        return {
            'Exif.Image.Artist': f"{metadata.photographer_name} ({metadata.institution_name})",
            'Exif.Image.Copyright': metadata.copyright_text,
            'Exif.Image.ImageDescription': metadata.title,
            'Exif.Image.Software': "eBL Photo Stitcher",
            'Exif.Image.XResolution': (metadata.image_dpi, 1),
            'Exif.Image.YResolution': (metadata.image_dpi, 1),
            'Exif.Image.ResolutionUnit': 2  # Inches
        }
    
    def _prepare_xmp_data(self, metadata: ImageMetadata) -> Dict[str, Any]:
        import datetime
        
        xmp_data = {
            'Xmp.dc.title': metadata.title,
            'Xmp.dc.creator': metadata.photographer_name,
            'Xmp.dc.rights': metadata.copyright_text,
            'Xmp.dc.description': metadata.title,
            'Xmp.dc.subject': f"cuneiform, tablet, {metadata.institution_name}",
            'Xmp.photoshop.Credit': metadata.credit_line_text,
            'Xmp.photoshop.Source': metadata.institution_name,
            'Xmp.xmpRights.Marked': "True"
        }
        
        if metadata.usage_terms_text:
            xmp_data['Xmp.xmpRights.UsageTerms'] = metadata.usage_terms_text
        
        xmp_data['Xmp.xmp.MetadataDate'] = datetime.datetime.now().isoformat()
        
        return xmp_data
