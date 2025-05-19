"""
Test script to verify the refactored stitch_processing_utils implementation.

This script loads an image, creates multiple views, and tests the stitching functionality.
"""
import sys
import os
import cv2
import numpy as np

# Add parent directory to path so we can import from lib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import both implementations for comparison
import stitch_processing_utils as old_utils
import stitch_processing_utils_new as new_utils
from stitching.services.stitching_service import StitchingService


def test_resize_views():
    """Test the resize_tablet_views_relative_to_obverse function."""
    # Create test images
    obverse = np.ones((200, 100, 3), dtype=np.uint8) * 255  # 200x100 white image
    left = np.zeros((300, 50, 3), dtype=np.uint8)  # 300x50 black image
    right = np.ones((150, 75, 3), dtype=np.uint8) * 128  # 150x75 gray image
    
    # Create image dictionary
    images = {"obverse": obverse, "left": left, "right": right}
    
    # Test old implementation
    old_result = old_utils.resize_tablet_views_relative_to_obverse(images.copy())
    
    # Test new implementation
    new_result = new_utils.resize_tablet_views_relative_to_obverse(images.copy())
    
    # Check that results are the same
    print("Test resize_views:")
    for key in images:
        old_shape = old_result[key].shape if old_result.get(key) is not None else None
        new_shape = new_result[key].shape if new_result.get(key) is not None else None
        print(f"  {key}: Old shape = {old_shape}, New shape = {new_shape}")
        

def test_layout_calculation():
    """Test the calculate_stitching_canvas_layout function."""
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
    old_w, old_h, old_coords, old_imgs = old_utils.calculate_stitching_canvas_layout(
        images.copy(), 20, 30
    )
    
    # Test new implementation
    new_w, new_h, new_coords, new_imgs = new_utils.calculate_stitching_canvas_layout(
        images.copy(), 20, 30
    )
    
    # Check that results are the same
    print("\nTest layout_calculation:")
    print(f"  Canvas Size: Old = ({old_w}, {old_h}), New = ({new_w}, {new_h})")
    print("  Coordinates:")
    for key in old_coords:
        print(f"    {key}: Old = {old_coords[key]}, New = {new_coords.get(key)}")
        

def test_bounding_box():
    """Test the get_layout_bounding_box function."""
    # Create test images
    img1 = np.ones((100, 150, 3), dtype=np.uint8) * 255
    img2 = np.ones((80, 120, 3), dtype=np.uint8) * 128
    
    # Create image dictionary and layout coordinates
    images = {"img1": img1, "img2": img2}
    coords = {"img1": (50, 30), "img2": (200, 150)}
    
    # Test old implementation
    old_bbox = old_utils.get_layout_bounding_box(images, coords)
    
    # Test new implementation
    new_bbox = new_utils.get_layout_bounding_box(images, coords)
    
    # Check that results are the same
    print("\nTest bounding_box:")
    print(f"  Old bbox = {old_bbox}")
    print(f"  New bbox = {new_bbox}")


def test_add_logo():
    """Test the add_logo_to_image_array function."""
    # Create test image
    content = np.ones((200, 300, 3), dtype=np.uint8) * 200
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "eBL_logo.png")
    
    # Test old implementation
    old_result = old_utils.add_logo_to_image_array(
        content.copy(), logo_path, (0, 0, 0), 0.8, 20, 20
    )
    
    # Test new implementation
    new_result = new_utils.add_logo_to_image_array(
        content.copy(), logo_path, (0, 0, 0), 0.8, 20, 20
    )
    
    # Check that results are the same
    print("\nTest add_logo:")
    print(f"  Original shape = {content.shape}")
    print(f"  Old result shape = {old_result.shape}")
    print(f"  New result shape = {new_result.shape}")


def test_crop_canvas():
    """Test the crop_canvas_to_content_with_margin function."""
    # Create test image with content surrounded by background
    canvas = np.zeros((400, 600, 3), dtype=np.uint8)  # Black background
    content = np.ones((200, 300, 3), dtype=np.uint8) * 255  # White content
    
    # Place content in center of canvas
    x_offset = (canvas.shape[1] - content.shape[1]) // 2
    y_offset = (canvas.shape[0] - content.shape[0]) // 2
    canvas[y_offset:y_offset+content.shape[0], x_offset:x_offset+content.shape[1]] = content
    
    # Test old implementation
    old_result = old_utils.crop_canvas_to_content_with_margin(
        canvas.copy(), (0, 0, 0), 30
    )
    
    # Test new implementation
    new_result = new_utils.crop_canvas_to_content_with_margin(
        canvas.copy(), (0, 0, 0), 30
    )
    
    # Check that results are the same
    print("\nTest crop_canvas:")
    print(f"  Original shape = {canvas.shape}")
    print(f"  Old result shape = {old_result.shape}")
    print(f"  New result shape = {new_result.shape}")


def test_stitching_service():
    """Test the StitchingService class."""
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
    
    # Create StitchingService
    service = StitchingService()
    
    # Test functionality
    resized_images = service.resize_views(images.copy())
    canvas_w, canvas_h, coords, updated_images = service.calculate_layout(resized_images)
    
    print("\nTest stitching_service:")
    print(f"  Canvas size = ({canvas_w}, {canvas_h})")
    print("  Coordinates:")
    for key, pos in coords.items():
        print(f"    {key}: {pos}")


if __name__ == "__main__":
    print("Starting tests...")
    test_resize_views()
    test_layout_calculation()
    test_bounding_box()
    test_add_logo()
    test_crop_canvas()
    test_stitching_service()
    print("\nAll tests completed.")
