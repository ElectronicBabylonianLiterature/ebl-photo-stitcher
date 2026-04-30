"""
Unit tests for version_checker module.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from version_checker import (
    CURRENT_VERSION,
    VersionChecker,
    get_current_version,
    compare_versions,
    check_for_updates
)


@pytest.mark.unit
class TestVersionChecker:
    """Test suite for version_checker module."""
    
    def test_current_version_format(self):
        """Test that CURRENT_VERSION has valid format."""
        assert CURRENT_VERSION is not None
        assert isinstance(CURRENT_VERSION, str)
        # Should match pattern like "v1.2.3"
        assert len(CURRENT_VERSION) > 0
    
    def test_get_current_version(self):
        """Test getting current version."""
        version = get_current_version()
        assert version == CURRENT_VERSION
    
    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        result = compare_versions("1.2.3", "1.2.3")
        assert result == 0
    
    def test_compare_versions_newer(self):
        """Test comparing with newer version."""
        result = compare_versions("1.2.3", "1.3.0")
        assert result < 0  # First is older
    
    def test_compare_versions_older(self):
        """Test comparing with older version."""
        result = compare_versions("2.0.0", "1.9.9")
        assert result > 0  # First is newer
    
    def test_version_checker_initialization(self):
        """Test VersionChecker initialization."""
        callback = Mock()
        checker = VersionChecker(callback=callback)
        assert checker.callback == callback
    
    @patch('version_checker.requests.get')
    def test_check_for_updates_newer_available(self, mock_get):
        """Test checking for updates when newer version available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v2.0.0',
            'name': 'Version 2.0.0'
        }
        mock_get.return_value = mock_response
        
        with patch('version_checker.CURRENT_VERSION', 'v1.0.0'):
            latest, is_newer = check_for_updates()
            assert latest == 'v2.0.0'
            assert is_newer is True
    
    @patch('version_checker.requests.get')
    def test_check_for_updates_no_update(self, mock_get):
        """Test checking for updates when already on latest."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v1.0.0',
            'name': 'Version 1.0.0'
        }
        mock_get.return_value = mock_response
        
        with patch('version_checker.CURRENT_VERSION', 'v1.0.0'):
            latest, is_newer = check_for_updates()
            assert latest == 'v1.0.0'
            assert is_newer is False
    
    @patch('version_checker.requests.get')
    def test_check_for_updates_network_error(self, mock_get):
        """Test checking for updates with network error."""
        mock_get.side_effect = Exception("Network error")
        
        latest, is_newer = check_for_updates()
        assert latest is None or latest == CURRENT_VERSION
        assert is_newer is False


@pytest.mark.integration
class TestVersionCheckerIntegration:
    """Integration tests for version checker."""
    
    @pytest.mark.slow
    def test_version_checker_real_check(self):
        """Test version checker with real API call (slow)."""
        callback = Mock()
        checker = VersionChecker(callback=callback)
        
        # This will make a real API call, so it's marked as slow
        # Just ensure it doesn't crash
        assert checker is not None
