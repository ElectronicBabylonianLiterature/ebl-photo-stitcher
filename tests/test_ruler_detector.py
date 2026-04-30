"""
Unit tests for ruler_detector module.
"""
import pytest
import numpy as np
import cv2
import sys
import os

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from ruler_detector import (
    detect_1cm_distance,
    find_ruler_in_image,
    extract_ruler_region,
    calculate_pixels_per_cm
)


@pytest.mark.unit
@pytest.mark.ruler_detection
class TestRulerDetector:
    """Test suite for ruler_detector module."""
    
    def test_detect_1cm_distance_with_valid_ruler(self, sample_image_with_ruler):
        """Test detecting 1cm distance on a valid ruler image."""
        result = detect_1cm_distance(sample_image_with_ruler)
        assert result is not None
        assert isinstance(result, (int, float))
        assert result > 0
    
    def test_detect_1cm_distance_no_ruler(self, sample_image):
        """Test detecting 1cm distance when no ruler is present."""
        result = detect_1cm_distance(sample_image)
        # Should return None or raise exception when no ruler found
        assert result is None or isinstance(result, (int, float))
    
    def test_find_ruler_in_image(self, sample_image_with_ruler):
        """Test finding ruler contour in image."""
        contours = find_ruler_in_image(sample_image_with_ruler)
        assert contours is not None
        assert len(contours) > 0
    
    def test_extract_ruler_region(self, sample_image_with_ruler):
        """Test extracting ruler region from image."""
        ruler_region = extract_ruler_region(sample_image_with_ruler)
        assert ruler_region is not None
        assert isinstance(ruler_region, np.ndarray)
    
    def test_calculate_pixels_per_cm(self):
        """Test calculating pixels per cm from known distance."""
        px_distance = 100
        cm_distance = 1.0
        px_per_cm = calculate_pixels_per_cm(px_distance, cm_distance)
        assert px_per_cm == 100.0
    
    @pytest.mark.parametrize("ruler_position", ["bottom", "left", "right", "top"])
    def test_detect_ruler_different_positions(self, sample_image_with_ruler, ruler_position):
        """Test ruler detection with different ruler positions."""
        result = detect_1cm_distance(sample_image_with_ruler, ruler_position=ruler_position)
        # Should handle different positions gracefully
        assert result is None or isinstance(result, (int, float))


@pytest.mark.integration
@pytest.mark.ruler_detection
@pytest.mark.slow
class TestRulerDetectorIntegration:
    """Integration tests for ruler detector with real images."""
    
    def test_detect_ruler_on_example_images(self, examples_dir):
        """Test ruler detection on example images if available."""
        test_images = list(examples_dir.rglob("*_02.jpg")) + list(examples_dir.rglob("*_03.jpg"))
        
        if not test_images:
            pytest.skip("No example images found for testing")
        
        # Test on first few images
        for img_path in test_images[:3]:
            img = cv2.imread(str(img_path))
            if img is not None:
                result = detect_1cm_distance(img)
                # Just ensure it doesn't crash, result may vary
                assert result is None or (isinstance(result, (int, float)) and result > 0)
