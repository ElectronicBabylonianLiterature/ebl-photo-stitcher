import datetime
from metadata.domain import ImageMetadata, ExifData, XmpData

class MetadataFactory:
    @staticmethod
    def create_exif_data(metadata: ImageMetadata) -> ExifData:
        artist = f"{metadata.photographer_name} ({metadata.institution_name})"
        
        return ExifData(
            artist=artist,
            copyright=metadata.copyright_text, 
            description=metadata.title,
            software="eBL Photo Stitcher",
            x_resolution=(metadata.image_dpi, 1),
            y_resolution=(metadata.image_dpi, 1),
            resolution_unit=2  # Inches
        )
    
    @staticmethod
    def create_xmp_data(metadata: ImageMetadata) -> XmpData:
        date = datetime.datetime.now().isoformat()
        subjects = ["cuneiform", "tablet", metadata.institution_name]
        
        return XmpData(
            title=metadata.title,
            creator=metadata.photographer_name,
            rights=metadata.copyright_text,
            description=metadata.title,
            credit=metadata.credit_line_text,
            source=metadata.institution_name,
            subjects=subjects,
            marked=True,
            usage_terms=metadata.usage_terms_text,
            date=date
        )
