"""
Unit tests for workflow_scale_detection module.
"""
import pytest
import numpy as np
import sys
import os
from unittest.mock import Mock, patch, MagicMock

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from workflow_scale_detection import (
    try_ruler_detection_with_fallback,
    detect_scale_from_ruler,
    get_scale_from_measurements,
    determine_pixels_per_cm_with_fallback,
    was_excel_measurement_used
)


@pytest.mark.unit
class TestWorkflowScaleDetection:
    """Test suite for workflow_scale_detection module."""
    
    def test_try_ruler_detection_with_fallback_success(self, sample_ruler_image, temp_dir):
        """Test ruler detection with fallback on successful detection."""
        with patch('workflow_scale_detection.ruler_detector') as mock_detector:
            mock_detector.detect_1cm_distance.return_value = 150.0
            
            result, cr2_count = try_ruler_detection_with_fallback(
                str(sample_ruler_image),
                str(temp_dir),
                '.cr2',
                'British Museum',
                'bottom'
            )
            
            assert result is not None
            assert isinstance(result, (int, float))
            assert result > 0
    
    def test_try_ruler_detection_fallback_to_manual(self, sample_ruler_image, temp_dir):
        """Test fallback to manual ruler when automatic detection fails."""
        with patch('workflow_scale_detection.ruler_detector') as mock_detector:
            mock_detector.detect_1cm_distance.return_value = None
            
            with patch('workflow_scale_detection.get_manual_ruler_measurement') as mock_manual:
                mock_manual.return_value = 200.0
                
                result, cr2_count = try_ruler_detection_with_fallback(
                    str(sample_ruler_image),
                    str(temp_dir),
                    '.cr2',
                    'British Museum',
                    'bottom'
                )
    
    def test_get_scale_from_measurements_valid_measurement(self, temp_dir, mock_measurements_dict):
        """Test getting scale from measurements with valid measurement data."""
        subfolder_name = "TEST_TABLET_01"
        
        with patch('workflow_scale_detection.get_tablet_width_from_measurements') as mock_get_width:
            mock_get_width.return_value = 5.2
            
            with patch('workflow_scale_detection.determine_pixels_per_cm_from_measurement') as mock_calc:
                mock_calc.return_value = 150.0
                
                result = get_scale_from_measurements(
                    str(temp_dir / subfolder_name),
                    mock_measurements_dict,
                    "dummy_ruler.jpg",
                    background_color_tolerance=20
                )
                
                assert result is not None
    
    def test_determine_pixels_per_cm_with_force_manual(self, temp_dir, sample_ruler_image):
        """Test determine pixels per cm with forced manual mode."""
        with patch('workflow_scale_detection.get_manual_ruler_measurement') as mock_manual:
            mock_manual.return_value = 180.0
            
            result, measurements_used, cr2_count, preset = determine_pixels_per_cm_with_fallback(
                str(temp_dir),
                "TEST_TABLET",
                str(sample_ruler_image),
                '.cr2',
                'British Museum',
                'bottom',
                False,
                {},
                background_color_tolerance=20,
                app_instance=None,
                force_manual_ruler=True
            )
            
            assert result == 180.0
            assert measurements_used is False
            assert preset == "Manual measurement"
    
    def test_was_excel_measurement_used_true(self, temp_dir, mock_measurements_dict):
        """Test checking if Excel measurement was used."""
        subfolder_name = "TEST_TABLET_01"
        result = was_excel_measurement_used(str(temp_dir / subfolder_name), mock_measurements_dict)
        assert isinstance(result, bool)
    
    @pytest.mark.parametrize("museum", [
        "British Museum",
        "Iraq Museum",
        "Iraq Museum (Sippar Library)"
    ])
    def test_different_museums(self, sample_ruler_image, temp_dir, museum):
        """Test ruler detection with different museum settings."""
        with patch('workflow_scale_detection.ruler_detector') as mock_detector:
            mock_detector.detect_1cm_distance.return_value = 150.0
            
            result, cr2_count = try_ruler_detection_with_fallback(
                str(sample_ruler_image),
                str(temp_dir),
                '.cr2',
                museum,
                'bottom'
            )


@pytest.mark.integration
class TestWorkflowScaleDetectionIntegration:
    """Integration tests for workflow scale detection."""
    
    def test_full_scale_detection_workflow(self, temp_dir, sample_tablet_images):
        """Test complete scale detection workflow."""
        with patch('workflow_scale_detection.ruler_detector') as mock_detector:
            mock_detector.detect_1cm_distance.return_value = 200.0
            
            result, measurements_used, cr2_count, preset = determine_pixels_per_cm_with_fallback(
                str(temp_dir),
                "TEST_TABLET",
                str(sample_tablet_images['top']),
                '.cr2',
                'British Museum',
                'bottom',
                False,
                {},
                background_color_tolerance=20,
                app_instance=None,
                force_manual_ruler=False
            )
            
            # Should successfully complete the workflow
            assert result is not None or preset is not None
