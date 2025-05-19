"""
Stitching package for the eBL Photo Stitcher application.

This package contains modules for handling the stitching of tablet images.
"""
from stitching.domain.models import (
    Dimension,
    Position,
    BoundingBox,
    BackgroundSettings,
    ResizeParams,
    StitchingConfig,
    LayoutCoordinates,
    CanvasSize,
    LogoSettings,
    ImageLayout
)
from stitching.services.stitching_service import StitchingService
