"""
Unit tests for image_utils module.
"""
import pytest
import numpy as np
import cv2
import sys
import os

# Add lib to path
lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from image_utils import (
    load_image,
    save_image,
    resize_image,
    get_image_dimensions,
    convert_color_space,
    validate_image_path
)


@pytest.mark.unit
class TestImageUtils:
    """Test suite for image_utils module."""
    
    def test_load_image_success(self, sample_ruler_image):
        """Test loading an image successfully."""
        img = load_image(str(sample_ruler_image))
        assert img is not None
        assert isinstance(img, np.ndarray)
        assert len(img.shape) == 3  # RGB image
    
    def test_load_image_invalid_path(self):
        """Test loading image with invalid path."""
        with pytest.raises(Exception):
            load_image("/nonexistent/path/image.jpg")
    
    def test_save_image_success(self, sample_image, temp_dir):
        """Test saving an image successfully."""
        output_path = temp_dir / "output.jpg"
        save_image(sample_image, str(output_path))
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_resize_image_by_scale(self, sample_image):
        """Test resizing image by scale factor."""
        resized = resize_image(sample_image, scale=0.5)
        assert resized.shape[0] == sample_image.shape[0] // 2
        assert resized.shape[1] == sample_image.shape[1] // 2
    
    def test_resize_image_by_dimensions(self, sample_image):
        """Test resizing image to specific dimensions."""
        target_width, target_height = 400, 300
        resized = resize_image(sample_image, width=target_width, height=target_height)
        assert resized.shape[1] == target_width
        assert resized.shape[0] == target_height
    
    def test_get_image_dimensions(self, sample_image):
        """Test getting image dimensions."""
        height, width, channels = get_image_dimensions(sample_image)
        assert height == sample_image.shape[0]
        assert width == sample_image.shape[1]
        assert channels == sample_image.shape[2]
    
    def test_convert_color_space_rgb_to_gray(self, sample_image):
        """Test converting from RGB to grayscale."""
        gray = convert_color_space(sample_image, 'RGB2GRAY')
        assert len(gray.shape) == 2
    
    def test_convert_color_space_bgr_to_rgb(self, sample_image):
        """Test converting from BGR to RGB."""
        rgb = convert_color_space(sample_image, 'BGR2RGB')
        assert rgb.shape == sample_image.shape
    
    def test_validate_image_path_valid(self, sample_ruler_image):
        """Test validating a valid image path."""
        assert validate_image_path(str(sample_ruler_image)) is True
    
    def test_validate_image_path_invalid(self):
        """Test validating an invalid image path."""
        assert validate_image_path("/nonexistent/image.jpg") is False
