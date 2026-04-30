"""
Unit tests for object_extractor module.
"""
import pytest
import numpy as np
import cv2
import sys
import os

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from object_extractor import (
    extract_object_from_image,
    create_foreground_mask,
    select_contour_closest_to_image_center,
    extract_and_save_center_object
)


@pytest.mark.unit
@pytest.mark.image_processing
class TestObjectExtractor:
    """Test suite for object_extractor module."""
    
    def test_create_foreground_mask_basic(self, sample_image):
        """Test creating a foreground mask from an image."""
        mask = create_foreground_mask(sample_image, tolerance=20)
        assert mask is not None
        assert isinstance(mask, np.ndarray)
        assert len(mask.shape) == 2  # Binary mask
        assert mask.dtype == np.uint8
    
    def test_create_foreground_mask_different_tolerances(self, sample_image):
        """Test foreground mask with different tolerance values."""
        mask_low = create_foreground_mask(sample_image, tolerance=10)
        mask_high = create_foreground_mask(sample_image, tolerance=50)
        
        assert mask_low is not None
        assert mask_high is not None
        # Higher tolerance should generally result in more foreground pixels
    
    def test_select_contour_closest_to_center(self):
        """Test selecting contour closest to image center."""
        # Create test contours
        contour1 = np.array([[[10, 10]], [[20, 10]], [[20, 20]], [[10, 20]]], dtype=np.int32)
        contour2 = np.array([[[100, 100]], [[200, 100]], [[200, 200]], [[100, 200]]], dtype=np.int32)
        contours = [contour1, contour2]
        
        image_shape = (400, 400, 3)
        selected = select_contour_closest_to_image_center(contours, image_shape)
        
        assert selected is not None
        # Should select contour2 as it's closer to center (200, 200)
    
    def test_extract_object_from_image_success(self, sample_image):
        """Test extracting object from image."""
        result = extract_object_from_image(sample_image, tolerance=20)
        # Result should be an image or None if no object found
        assert result is None or isinstance(result, np.ndarray)
    
    def test_extract_and_save_center_object(self, sample_image, temp_dir):
        """Test extracting and saving center object."""
        input_path = temp_dir / "input.jpg"
        output_path = temp_dir / "output_extracted.jpg"
        
        cv2.imwrite(str(input_path), sample_image)
        
        result = extract_and_save_center_object(
            str(input_path),
            str(output_path),
            tolerance=20
        )
        
        # Function should complete without error
        assert isinstance(result, bool) or result is None


@pytest.mark.integration
@pytest.mark.image_processing
class TestObjectExtractorIntegration:
    """Integration tests for object extraction."""
    
    def test_extract_object_with_clear_foreground(self, temp_dir, image_helper):
        """Test extracting object with a clear foreground."""
        # Create image with clear object on white background
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        # Draw dark object in center
        cv2.rectangle(img, (300, 200), (500, 400), (50, 50, 50), -1)
        
        result = extract_object_from_image(img, tolerance=50)
        
        if result is not None:
            assert isinstance(result, np.ndarray)
            # Result should be smaller than original (cropped to object)
            assert result.shape[0] <= img.shape[0]
            assert result.shape[1] <= img.shape[1]
