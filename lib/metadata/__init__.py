from metadata.domain import ImageMetadata
from metadata.service import MetadataService

_metadata_service = MetadataService()

def apply_metadata(
    image_path: str, 
    title: str, 
    photographer_name: str, 
    institution_name: str, 
    credit_line_text: str, 
    copyright_text: str, 
    usage_terms_text=None, 
    image_dpi=600
) -> bool:
    metadata = ImageMetadata(
        title=title,
        photographer_name=photographer_name,
        institution_name=institution_name,
        credit_line_text=credit_line_text,
        copyright_text=copyright_text,
        usage_terms_text=usage_terms_text,
        image_dpi=image_dpi
    )
    
    return _metadata_service.apply_metadata(image_path, metadata)

__all__ = ['ImageMetadata', 'apply_metadata']