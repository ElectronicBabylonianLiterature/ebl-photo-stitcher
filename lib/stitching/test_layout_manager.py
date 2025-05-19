"""
Test script to verify the refactored stitch_layout_manager implementation.

This script tests that the new implementation matches the behavior of the original.
"""
import sys
import os
import cv2
import numpy as np

# Add parent directory to path so we can import from lib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import both implementations for comparison
import stitch_layout_manager as old_module
import stitch_layout_manager_new as new_module


def test_get_image_dimension():
    """Test the get_image_dimension function."""
    # Create test image
    img = np.ones((100, 200, 3), dtype=np.uint8)
    images = {"test": img}
    
    # Test old implementation
    old_height = old_module.get_image_dimension(images, "test", 0)
    old_width = old_module.get_image_dimension(images, "test", 1)
    old_missing = old_module.get_image_dimension(images, "missing", 0)
    
    # Test new implementation
    new_height = new_module.get_image_dimension(images, "test", 0)
    new_width = new_module.get_image_dimension(images, "test", 1)
    new_missing = new_module.get_image_dimension(images, "missing", 0)
    
    # Check that results are the same
    print("Test get_image_dimension:")
    print(f"  Height: Old = {old_height}, New = {new_height}")
    print(f"  Width: Old = {old_width}, New = {new_width}")
    print(f"  Missing: Old = {old_missing}, New = {new_missing}")


def test_resize_tablet_views_for_layout():
    """Test the resize_tablet_views_for_layout function."""
    # Create test images
    obverse = np.ones((200, 100, 3), dtype=np.uint8) * 255
    left = np.zeros((300, 50, 3), dtype=np.uint8)
    right = np.ones((150, 75, 3), dtype=np.uint8) * 128
    
    # Create image dictionary
    images = {"obverse": obverse, "left": left, "right": right}
    
    # Test old implementation
    old_result = old_module.resize_tablet_views_for_layout(images.copy())
    
    # Test new implementation
    new_result = new_module.resize_tablet_views_for_layout(images.copy())
    
    # Check that results are the same
    print("\nTest resize_tablet_views_for_layout:")
    for key in images:
        old_shape = old_result[key].shape if old_result.get(key) is not None else None
        new_shape = new_result[key].shape if new_result.get(key) is not None else None
        print(f"  {key}: Old shape = {old_shape}, New shape = {new_shape}")


def test_calculate_stitching_layout():
    """Test the calculate_stitching_layout function."""
    # Create test images
    obverse = np.ones((200, 100, 3), dtype=np.uint8) * 255
    left = np.zeros((200, 50, 3), dtype=np.uint8)
    right = np.ones((200, 75, 3), dtype=np.uint8) * 128
    bottom = np.ones((100, 100, 3), dtype=np.uint8) * 200
    ruler = np.ones((30, 80, 3), dtype=np.uint8) * 220
    
    # Create image dictionary
    images = {
        "obverse": obverse,
        "left": left,
        "right": right,
        "bottom": bottom,
        "ruler": ruler
    }
    
    # Test old implementation
    old_w, old_h, old_coords, old_imgs = old_module.calculate_stitching_layout(
        images.copy(), 20, 30
    )
    
    # Test new implementation
    new_w, new_h, new_coords, new_imgs = new_module.calculate_stitching_layout(
        images.copy(), 20, 30
    )
    
    # Check that results are the same
    print("\nTest calculate_stitching_layout:")
    print(f"  Canvas Size: Old = ({old_w}, {old_h}), New = ({new_w}, {new_h})")
    print("  Coordinates:")
    for key in old_coords:
        print(f"    {key}: Old = {old_coords[key]}, New = {new_coords.get(key)}")


def test_get_layout_bounding_box():
    """Test the get_layout_bounding_box function."""
    # Create test images
    img1 = np.ones((100, 150, 3), dtype=np.uint8) * 255
    img2 = np.ones((80, 120, 3), dtype=np.uint8) * 128
    
    # Create image dictionary and layout coordinates
    images = {"img1": img1, "img2": img2}
    coords = {"img1": (50, 30), "img2": (200, 150)}
    
    # Test old implementation
    old_bbox = old_module.get_layout_bounding_box(images, coords)
    
    # Test new implementation
    new_bbox = new_module.get_layout_bounding_box(images, coords)
    
    # Check that results are the same
    print("\nTest get_layout_bounding_box:")
    print(f"  Old bbox = {old_bbox}")
    print(f"  New bbox = {new_bbox}")


if __name__ == "__main__":
    print("Starting tests...")
    test_get_image_dimension()
    test_resize_tablet_views_for_layout()
    test_calculate_stitching_layout()
    test_get_layout_bounding_box()
    print("\nAll tests completed.")
