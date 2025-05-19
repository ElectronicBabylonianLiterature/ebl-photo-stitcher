"""
Domain models for stitching layout and configuration.
"""
from typing import Dict, Tuple, Optional, List, Any
import attr
import numpy as np


@attr.s(frozen=True)
class Dimension:
    """Represents image dimensions."""
    width: int = attr.ib()
    height: int = attr.ib()


@attr.s(frozen=True)
class Position:
    """Represents a position on the canvas."""
    x: int = attr.ib()
    y: int = attr.ib()


@attr.s(frozen=True)
class BoundingBox:
    """Represents a bounding box for stitched content."""
    min_x: int = attr.ib()
    min_y: int = attr.ib()
    max_x: int = attr.ib()
    max_y: int = attr.ib()
    
    @property
    def width(self) -> int:
        """Get the width of the bounding box."""
        return self.max_x - self.min_x
    
    @property
    def height(self) -> int:
        """Get the height of the bounding box."""
        return self.max_y - self.min_y


@attr.s(frozen=True)
class BackgroundSettings:
    """Background settings for the canvas."""
    color: Tuple[int, int, int] = attr.ib()


@attr.s(frozen=True)
class ResizeParams:
    """Parameters for resizing images."""
    axis: int = attr.ib()
    match_dim: int = attr.ib()


@attr.s(frozen=True)
class StitchingConfig:
    """Configuration for stitching."""
    view_separation_px: int = attr.ib()
    ruler_top_padding_px: int = attr.ib()
    canvas_padding: int = attr.ib(default=100)
    background_color: Tuple[int, int, int] = attr.ib(default=(0, 0, 0))
    
    @classmethod
    def default(cls) -> 'StitchingConfig':
        """Create a default stitching configuration."""
        return cls(
            view_separation_px=50,
            ruler_top_padding_px=100,
            canvas_padding=100,
            background_color=(0, 0, 0)
        )


@attr.s(frozen=True)
class LayoutCoordinates:
    """Represents the coordinates for an image on the canvas."""
    positions: Dict[str, Position] = attr.ib()
    
    def get(self, key: str) -> Optional[Position]:
        """Get position for a view key."""
        return self.positions.get(key)


@attr.s(frozen=True)
class CanvasSize:
    """Represents the size of the stitching canvas."""
    width: int = attr.ib()
    height: int = attr.ib()


@attr.s(frozen=True)
class LogoSettings:
    """Settings for logo placement on the image."""
    logo_path: str = attr.ib()
    max_width_fraction: float = attr.ib(default=0.8)  
    padding_above: int = attr.ib(default=30)
    padding_below: int = attr.ib(default=30)


@attr.s
class ImageLayout:
    """Manages the layout of images for stitching."""
    images: Dict[str, np.ndarray] = attr.ib()
    coordinates: LayoutCoordinates = attr.ib()
    canvas_size: CanvasSize = attr.ib()
    
    @classmethod
    def create_empty(cls) -> 'ImageLayout':
        """Create an empty image layout."""
        return cls(
            images={},
            coordinates=LayoutCoordinates({}),
            canvas_size=CanvasSize(0, 0)
        )
