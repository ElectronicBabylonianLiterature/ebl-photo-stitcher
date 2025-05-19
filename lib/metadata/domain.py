from __future__ import annotations
import attr
from typing import Optional, List

@attr.s(frozen=True)
class ImageMetadata:
    title: str = attr.ib()
    photographer_name: str = attr.ib()
    institution_name: str = attr.ib()
    credit_line_text: str = attr.ib()
    copyright_text: str = attr.ib()
    usage_terms_text: Optional[str] = attr.ib(default=None)
    image_dpi: int = attr.ib(default=600)
    
    @classmethod
    def create(
        cls, 
        title: str, 
        photographer_name: str,
        institution_name: str,
        credit_line_text: str,
        copyright_text: str,
        usage_terms_text: Optional[str] = None,
        image_dpi: int = 600
    ) -> ImageMetadata:
        return cls(
            title=title,
            photographer_name=photographer_name,
            institution_name=institution_name,
            credit_line_text=credit_line_text,
            copyright_text=copyright_text,
            usage_terms_text=usage_terms_text,
            image_dpi=image_dpi
        )

@attr.s(frozen=True)
class ExifData:
    artist: str = attr.ib()
    copyright: str = attr.ib()
    description: str = attr.ib()
    software: str = attr.ib(default="eBL Photo Stitcher")
    x_resolution: tuple = attr.ib()
    y_resolution: tuple = attr.ib()
    resolution_unit: int = attr.ib(default=2)  # Inches

@attr.s(frozen=True)
class XmpData:
    title: str = attr.ib()
    creator: str = attr.ib()
    rights: str = attr.ib()
    description: str = attr.ib()
    credit: str = attr.ib()
    source: str = attr.ib()
    subjects: List[str] = attr.ib(factory=list)
    marked: bool = attr.ib(default=True)
    usage_terms: Optional[str] = attr.ib(default=None)
    date: str = attr.ib()
