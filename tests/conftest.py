"""
Pytest fixtures and utilities for testing.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest
import numpy as np
import cv2
from PIL import Image

# Add lib directory to path
script_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lib_directory = os.path.join(script_directory, "lib")
if lib_directory not in sys.path:
    sys.path.insert(0, lib_directory)


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def examples_dir():
    """Return path to Examples directory."""
    examples_path = Path(__file__).parent.parent / "Examples"
    if not examples_path.exists():
        pytest.skip("Examples directory not found")
    return examples_path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    # Cleanup after test
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_image():
    """Create a sample test image (800x600 RGB)."""
    img = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
    return img


@pytest.fixture
def sample_image_with_ruler():
    """Create a sample image with a ruler-like object."""
    img = np.ones((600, 800, 3), dtype=np.uint8) * 200  # Gray background
    
    # Draw a ruler-like rectangle at the bottom
    cv2.rectangle(img, (50, 500), (750, 580), (255, 255, 255), -1)
    
    # Draw tick marks
    for i in range(10):
        x = 100 + i * 60
        cv2.line(img, (x, 500), (x, 520), (0, 0, 0), 2)
    
    return img


@pytest.fixture
def sample_ruler_image(temp_dir):
    """Create and save a sample ruler image file."""
    img = np.ones((600, 800, 3), dtype=np.uint8) * 200
    cv2.rectangle(img, (50, 500), (750, 580), (255, 255, 255), -1)
    
    ruler_path = temp_dir / "test_ruler.tif"
    cv2.imwrite(str(ruler_path), img)
    return ruler_path


@pytest.fixture
def sample_tablet_images(temp_dir):
    """Create sample tablet images (obverse, reverse, top, bottom)."""
    images = {}
    
    # Obverse
    img_obverse = np.ones((800, 600, 3), dtype=np.uint8) * 180
    cv2.putText(img_obverse, "Obverse", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    obverse_path = temp_dir / "tablet_01.jpg"
    cv2.imwrite(str(obverse_path), img_obverse)
    images['obverse'] = obverse_path
    
    # Reverse
    img_reverse = np.ones((800, 600, 3), dtype=np.uint8) * 160
    cv2.putText(img_reverse, "Reverse", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    reverse_path = temp_dir / "tablet_02.jpg"
    cv2.imwrite(str(reverse_path), img_reverse)
    images['reverse'] = reverse_path
    
    # Top
    img_top = np.ones((800, 600, 3), dtype=np.uint8) * 140
    cv2.putText(img_top, "Top", (250, 400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    top_path = temp_dir / "tablet_03.jpg"
    cv2.imwrite(str(top_path), img_top)
    images['top'] = top_path
    
    return images


@pytest.fixture
def mock_measurements_dict():
    """Create a mock measurements dictionary."""
    return {
        "TEST_TABLET_01": {
            "width": 5.2,
            "height": 7.3,
            "depth": 2.1
        },
        "TEST_TABLET_02": {
            "width": 6.5,
            "height": 8.0,
            "depth": 2.5
        }
    }


@pytest.fixture
def mock_config():
    """Create a mock configuration dictionary."""
    return {
        "photographer": "Test Photographer",
        "museum": "British Museum",
        "ruler_position": "bottom",
        "background_tolerance": 20,
        "enable_hdr": False
    }


class ImageTestHelper:
    """Helper class for image testing utilities."""
    
    @staticmethod
    def create_test_image(width=800, height=600, channels=3, color=None):
        """Create a test image with specified dimensions."""
        if color is None:
            return np.random.randint(0, 255, (height, width, channels), dtype=np.uint8)
        else:
            img = np.zeros((height, width, channels), dtype=np.uint8)
            img[:] = color
            return img
    
    @staticmethod
    def save_test_image(img, path, format='JPEG'):
        """Save test image to file."""
        if isinstance(img, np.ndarray):
            cv2.imwrite(str(path), img)
        else:
            img.save(str(path), format=format)
    
    @staticmethod
    def compare_images(img1, img2, tolerance=0):
        """Compare two images with optional tolerance."""
        if img1.shape != img2.shape:
            return False
        diff = np.abs(img1.astype(float) - img2.astype(float))
        return np.max(diff) <= tolerance
    
    @staticmethod
    def create_ruler_pattern(width=700, height=80, cm_marks=5):
        """Create a ruler pattern image."""
        ruler = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        pixels_per_cm = width / cm_marks
        for i in range(cm_marks + 1):
            x = int(i * pixels_per_cm)
            cv2.line(ruler, (x, 0), (x, height // 3), (0, 0, 0), 2)
            
            # Add smaller tick marks
            for j in range(1, 10):
                x_minor = int((i + j/10) * pixels_per_cm)
                if x_minor < width:
                    tick_height = height // 6 if j == 5 else height // 10
                    cv2.line(ruler, (x_minor, 0), (x_minor, tick_height), (0, 0, 0), 1)
        
        return ruler


@pytest.fixture
def image_helper():
    """Provide ImageTestHelper instance."""
    return ImageTestHelper()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual functions"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for module interactions"
    )
    config.addinivalue_line(
        "markers", "gui: GUI-related tests (may require display)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to run"
    )
