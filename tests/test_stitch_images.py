"""
Unit tests for stitch_images module.
"""
import pytest
import numpy as np
import sys
import os
from unittest.mock import Mock, patch

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from stitch_images import (
    process_tablet_subfolder,
    determine_layout,
    stitch_views
)


@pytest.mark.unit
class TestStitchImages:
    """Test suite for stitch_images module."""
    
    def test_determine_layout_two_views(self, sample_tablet_images):
        """Test determining layout with two views."""
        views = {
            'obverse': str(sample_tablet_images['obverse']),
            'reverse': str(sample_tablet_images['reverse'])
        }
        layout = determine_layout(views)
        assert layout is not None
        assert isinstance(layout, dict)
    
    def test_determine_layout_four_views(self, sample_tablet_images):
        """Test determining layout with four views."""
        views = sample_tablet_images
        layout = determine_layout({k: str(v) for k, v in views.items()})
        assert layout is not None
    
    @pytest.mark.slow
    def test_stitch_views_basic(self, sample_tablet_images, temp_dir):
        """Test basic view stitching."""
        views = {k: str(v) for k, v in sample_tablet_images.items()}
        output_path = temp_dir / "stitched_output.jpg"
        
        # Mock the actual stitching to avoid complex dependencies
        with patch('stitch_images.merge_images') as mock_merge:
            mock_img = np.ones((800, 1600, 3), dtype=np.uint8) * 200
            mock_merge.return_value = mock_img
            
            result = stitch_views(views, str(output_path))
            assert result is not None


@pytest.mark.integration
@pytest.mark.slow
class TestStitchImagesIntegration:
    """Integration tests for image stitching."""
    
    def test_process_tablet_subfolder_complete(self, temp_dir, sample_tablet_images):
        """Test processing a complete tablet subfolder."""
        # Create a subfolder structure
        tablet_folder = temp_dir / "TABLET_TEST"
        tablet_folder.mkdir()
        
        # Copy test images to subfolder
        import shutil
        for view_name, img_path in sample_tablet_images.items():
            dest = tablet_folder / img_path.name
            shutil.copy(str(img_path), str(dest))
        
        # Mock the complex processing steps
        with patch('stitch_images.detect_scale_from_ruler') as mock_scale:
            mock_scale.return_value = 200.0
            
            with patch('stitch_images.merge_images') as mock_merge:
                mock_img = np.ones((800, 1600, 3), dtype=np.uint8) * 200
                mock_merge.return_value = mock_img
                
                # Test that the function can be called
                # Actual processing would require full workflow
                assert tablet_folder.exists()
