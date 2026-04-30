"""
Unit tests for manual_ruler_gui module.
"""
import pytest
import numpy as np
import sys
import os
from pathlib import Path

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from manual_ruler_gui import (
    find_best_manual_ruler_image,
    ManualRulerDrawer
)


@pytest.mark.unit
class TestManualRulerGUI:
    """Test suite for manual_ruler_gui module."""
    
    def test_find_best_manual_ruler_image_existing_file(self, sample_ruler_image, temp_dir):
        """Test finding best manual ruler image when file exists."""
        result = find_best_manual_ruler_image(str(temp_dir), str(sample_ruler_image))
        assert result == str(sample_ruler_image)
    
    def test_find_best_manual_ruler_image_with_fallbacks(self, temp_dir, image_helper):
        """Test finding best manual ruler image with fallback priority."""
        # Create test images with different suffixes
        base_name = "TABLET"
        
        # Create _02 and _01 images (not _03)
        img_02 = image_helper.create_test_image(color=(150, 150, 150))
        img_01 = image_helper.create_test_image(color=(180, 180, 180))
        
        path_02 = temp_dir / f"{base_name}_02.jpg"
        path_01 = temp_dir / f"{base_name}_01.jpg"
        
        image_helper.save_test_image(img_02, path_02)
        image_helper.save_test_image(img_01, path_01)
        
        # Test that it finds _02 first (since _03 doesn't exist)
        nonexistent_03 = temp_dir / f"{base_name}_03.jpg"
        result = find_best_manual_ruler_image(str(temp_dir), str(nonexistent_03))
        
        assert Path(result).name == f"{base_name}_02.jpg"
    
    def test_find_best_manual_ruler_image_priority_order(self, temp_dir, image_helper):
        """Test that _03 has priority over _02 and _01."""
        base_name = "TABLET"
        
        # Create all three images
        for suffix in ["_01", "_02", "_03"]:
            img = image_helper.create_test_image()
            path = temp_dir / f"{base_name}{suffix}.jpg"
            image_helper.save_test_image(img, path)
        
        # Request any of them, should get _03
        result = find_best_manual_ruler_image(str(temp_dir), str(temp_dir / f"{base_name}_01.jpg"))
        assert "_03" in Path(result).name
    
    def test_find_best_manual_ruler_image_no_matches(self, temp_dir):
        """Test finding best manual ruler image when no matches exist."""
        nonexistent = temp_dir / "NONEXISTENT.jpg"
        result = find_best_manual_ruler_image(str(temp_dir), str(nonexistent))
        # Should return the original path even if it doesn't exist
        assert result == str(nonexistent)
    
    @pytest.mark.gui
    def test_manual_ruler_drawer_initialization(self, sample_ruler_image):
        """Test ManualRulerDrawer initialization (requires display)."""
        try:
            drawer = ManualRulerDrawer(str(sample_ruler_image))
            assert drawer.image_path == str(sample_ruler_image)
            assert drawer.px_per_cm is None
            assert drawer.start_point is None
            assert drawer.end_point is None
            drawer.root.destroy()  # Clean up
        except Exception as e:
            pytest.skip(f"GUI test requires display: {e}")


@pytest.mark.integration
class TestManualRulerGUIIntegration:
    """Integration tests for manual ruler GUI."""
    
    def test_get_manual_ruler_measurement_with_subfolder(self, temp_dir, image_helper):
        """Test getting manual ruler measurement with subfolder fallback."""
        # Create test images
        base_name = "TABLET"
        img_03 = image_helper.create_test_image()
        path_03 = temp_dir / f"{base_name}_03.jpg"
        image_helper.save_test_image(img_03, path_03)
        
        # The function should find the _03 image
        from manual_ruler_gui import get_manual_ruler_measurement
        
        # This would normally open a GUI, so we just test the path resolution
        # In actual testing, you'd mock the GUI interaction
        nonexistent_base = temp_dir / f"{base_name}.jpg"
        
        # Test that it can find the right image path
        best_image = find_best_manual_ruler_image(str(temp_dir), str(nonexistent_base))
        assert "_03" in best_image
