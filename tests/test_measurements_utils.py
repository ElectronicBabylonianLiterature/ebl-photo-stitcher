"""
Unit tests for measurements_utils module.
"""
import pytest
import json
import sys
import os

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from measurements_utils import (
    load_measurements_from_json,
    get_tablet_width_from_measurements,
    save_measurements_to_json
)


@pytest.mark.unit
class TestMeasurementsUtils:
    """Test suite for measurements_utils module."""
    
    def test_load_measurements_from_json_valid(self, temp_dir):
        """Test loading measurements from valid JSON file."""
        test_data = {
            "TABLET_01": {"width": 5.2, "height": 7.3, "depth": 2.1},
            "TABLET_02": {"width": 6.5, "height": 8.0, "depth": 2.5}
        }
        
        json_path = temp_dir / "measurements.json"
        with open(json_path, 'w') as f:
            json.dump(test_data, f)
        
        loaded = load_measurements_from_json(str(json_path))
        assert loaded == test_data
        assert "TABLET_01" in loaded
        assert loaded["TABLET_01"]["width"] == 5.2
    
    def test_load_measurements_from_json_invalid_file(self):
        """Test loading measurements from non-existent file."""
        result = load_measurements_from_json("/nonexistent/measurements.json")
        assert result is None or result == {}
    
    def test_get_tablet_width_from_measurements_exists(self, mock_measurements_dict):
        """Test getting tablet width when measurement exists."""
        width = get_tablet_width_from_measurements("TEST_TABLET_01", mock_measurements_dict)
        assert width == 5.2
    
    def test_get_tablet_width_from_measurements_not_exists(self, mock_measurements_dict):
        """Test getting tablet width when measurement doesn't exist."""
        width = get_tablet_width_from_measurements("NONEXISTENT_TABLET", mock_measurements_dict)
        assert width is None
    
    def test_save_measurements_to_json(self, temp_dir, mock_measurements_dict):
        """Test saving measurements to JSON file."""
        output_path = temp_dir / "output_measurements.json"
        
        save_measurements_to_json(mock_measurements_dict, str(output_path))
        
        assert output_path.exists()
        
        # Verify the saved data
        with open(output_path, 'r') as f:
            loaded = json.load(f)
        
        assert loaded == mock_measurements_dict
    
    def test_measurements_dict_structure(self, mock_measurements_dict):
        """Test that measurements dictionary has correct structure."""
        for tablet_name, measurements in mock_measurements_dict.items():
            assert isinstance(tablet_name, str)
            assert isinstance(measurements, dict)
            assert "width" in measurements
            assert isinstance(measurements["width"], (int, float))


@pytest.mark.integration
class TestMeasurementsUtilsIntegration:
    """Integration tests for measurements utilities."""
    
    def test_load_save_roundtrip(self, temp_dir, mock_measurements_dict):
        """Test loading and saving measurements maintains data integrity."""
        json_path = temp_dir / "roundtrip.json"
        
        # Save
        save_measurements_to_json(mock_measurements_dict, str(json_path))
        
        # Load
        loaded = load_measurements_from_json(str(json_path))
        
        # Compare
        assert loaded == mock_measurements_dict
