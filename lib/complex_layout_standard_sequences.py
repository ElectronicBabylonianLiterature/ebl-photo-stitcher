import os
from stitch_config import STITCH_VIEW_PATTERNS_CONFIG

def apply_standard_sequence(image_paths, num_photos):
    """
    Applies a standard sequence layout based on the number of photos.
    
    Args:
        image_paths: List of available image paths
        num_photos: Number of photos detected
    
    Returns:
        A dictionary with the layout configuration
    """
    # Sort image paths by filename to ensure consistent ordering
    sorted_paths = sorted(image_paths, key=lambda x: os.path.basename(x).lower())
    
    # Create an empty layout structure
    layout = {
        "obverse": None, "reverse": None, "top": None, "bottom": None, "left": None, "right": None,
        "intermediate_obverse_left": [], "intermediate_obverse_right": [],
        "intermediate_obverse_top": [], "intermediate_obverse_bottom": [],
        "intermediate_reverse_left": [], "intermediate_reverse_right": [],
        "intermediate_reverse_top": [], "intermediate_reverse_bottom": []
    }
    
    # Standard order based on STITCH_VIEW_PATTERNS_CONFIG
    standard_order = [
        ("obverse", STITCH_VIEW_PATTERNS_CONFIG["obverse"]),
        ("reverse", STITCH_VIEW_PATTERNS_CONFIG["reverse"]),
        ("top", STITCH_VIEW_PATTERNS_CONFIG["top"]),
        ("bottom", STITCH_VIEW_PATTERNS_CONFIG["bottom"]),
        ("left", STITCH_VIEW_PATTERNS_CONFIG["left"]),
        ("right", STITCH_VIEW_PATTERNS_CONFIG["right"])
    ]
    
    # Match image paths to standard order based on filename patterns
    matched_indices = []
    
    # First, try to match the standard patterns
    for position, pattern in standard_order:
        for i, path in enumerate(sorted_paths):
            if i in matched_indices:
                continue
                
            # Get the basename without extension
            basename = os.path.splitext(os.path.basename(path))[0]
            
            # Look for pattern match
            if pattern in basename:
                layout[position] = {"path": path, "rotation": 0}
                matched_indices.append(i)
                break
    
    # Handle special cases based on number of photos
    if num_photos == 4:
        # Case 2c: For 4 photos, use them in the standard order
        # This is already handled by the pattern matching above
        pass
        
    elif num_photos == 8:
        # Case 2a: For 8 photos, place first 6 in standard order
        # and place 07 as intermediate left and 08 as intermediate right
        remaining = [p for i, p in enumerate(sorted_paths) if i not in matched_indices]
        
        if len(remaining) >= 2:
            # Add the 7th photo as intermediate left (between obverse and left)
            layout["intermediate_obverse_left"] = [{"path": remaining[0], "rotation": 0}]
            
            # Add the 8th photo as intermediate right (between obverse and right)
            layout["intermediate_obverse_right"] = [{"path": remaining[1], "rotation": 0}]
    
    # Case 2b is handled by default - any unmatched photos remain in the left panel
    
    return layout

    """
    Returns a description of how the standard sequence will be applied.
    
    Args:
        num_photos: Number of photos detected
    
    Returns:
        A string describing the standard sequence
    """
    if num_photos == 4:
        return "4 photos detected - using standard order for main views"
    elif num_photos == 8:
        return "8 photos detected - using first 6 in standard order, with 7th as intermediate left and 8th as intermediate right"
    else:
        return f"{num_photos} photos detected - using first 6 in standard order, remaining photos will be available for placement"