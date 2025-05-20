import os
import math
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw

def prepare_thumbnails(self):
    """
    Handles loading, resizing, and caching PIL and Tkinter images.
    This method should be called by ComplexLayoutDialog.
    """
    for img_path in self.image_paths:
        try:
            # Always load fresh PIL image for rotation handling
            image = Image.open(img_path)
            # Apply initial rotation if loaded from existing layout or previously rotated
            if self.image_rotations.get(img_path):
                image = image.rotate(self.image_rotations[img_path], expand=True)

            image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            self.pil_images_cache[img_path] = image
        except Exception as e:
            print(f"Error loading thumbnail for {img_path}: {e}")
            error_img = Image.new('RGB', self.thumbnail_size, color = 'lightgrey')
            try:
                draw = ImageDraw.Draw(error_img)
                draw.text((5, 5), "Error", fill="red")
            except Exception:
                pass
            self.pil_images_cache[img_path] = error_img

def add_rotate_overlay(self, img):
    """
    Adds a circular arrow overlay to the top-right corner of an image.
    This method should be called by ComplexLayoutDialog.
    """
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Define the circle size and position (top-right corner)
    # Use a larger circle radius - minimum 24 pixels or relative to image size
    circle_radius = max(24, min(img_copy.width, img_copy.height) // 8)
    circle_x = img_copy.width - circle_radius - 8  # 8 pixels from right edge
    circle_y = circle_radius + 8  # 8 pixels from top edge
    
    # Draw circular background with higher contrast and better opacity
    draw.ellipse(
        [(circle_x - circle_radius, circle_y - circle_radius), 
         (circle_x + circle_radius, circle_y + circle_radius)], 
        fill=(30, 30, 30, 220)
    )
    
    # Use more points for smoother circle
    num_points = 16
    arrow_points = []
    
    # Generate a smoother circular path (3/4 of a circle)
    for i in range(num_points):
        # Calculate angle for this point (going clockwise)
        angle = 2 * 3.14159 * i / num_points
        
        # Skip the last quarter to leave room for arrow
        if i < int(num_points * 0.75):
            # Calculate point on circle - improved math for better arc positioning
            x = circle_x + int((circle_radius * 0.7) * math.cos(angle + 3.14159 / 2))
            y = circle_y + int((circle_radius * 0.7) * math.sin(angle + 3.14159 / 2))
            arrow_points.append((x, y))
    
    # Draw the circular path with thicker lines for better visibility
    if len(arrow_points) >= 2:
        for i in range(len(arrow_points) - 1):
            draw.line([arrow_points[i], arrow_points[i+1]], fill=(255, 255, 255), width=max(3, circle_radius // 8))
    
    # Draw a larger, more visible arrowhead at the end
    arrowhead_size = circle_radius // 2
    
    # Position for the arrowhead (pointing to complete the circle)
    last_point = arrow_points[-1] if arrow_points else (circle_x, circle_y - circle_radius * 0.7)
    # Calculate angle of last segment for proper arrow orientation
    angle = math.atan2(last_point[1] - circle_y, last_point[0] - circle_x)
    
    # Calculate arrow tip and corners
    arrow_tip_x = last_point[0] + int(arrowhead_size * math.cos(angle))
    arrow_tip_y = last_point[1] + int(arrowhead_size * math.sin(angle))
    
    # Calculate points perpendicular to the arrow direction for the back of the arrowhead
    perp_angle1 = angle + math.pi/2
    perp_angle2 = angle - math.pi/2
    
    draw.polygon([
        (arrow_tip_x, arrow_tip_y),  # Arrow tip
        (last_point[0] + int((arrowhead_size/2) * math.cos(perp_angle1)), 
         last_point[1] + int((arrowhead_size/2) * math.sin(perp_angle1))),  # Side point 1
        (last_point[0] + int((arrowhead_size/2) * math.cos(perp_angle2)), 
         last_point[1] + int((arrowhead_size/2) * math.sin(perp_angle2))),  # Side point 2
    ], fill=(255, 255, 255))
    
    return img_copy

def get_tk_thumbnail(self, img_path, size=None, add_rotate_icon=True):
    """
    Retrieves/creates Tkinter-compatible thumbnails.
    This method should be called by ComplexLayoutDialog.
    """
    if size is None:
        size = self.thumbnail_size
    cache_key = (img_path, size, self.image_rotations.get(img_path, 0), add_rotate_icon) # Include rotation in cache key
    
    if cache_key not in self.tk_thumbnails_cache:
        if img_path in self.pil_images_cache:
            pil_image = Image.open(img_path) # Re-open original image
            rotation_degrees = self.image_rotations.get(img_path, 0)
            if rotation_degrees != 0:
                pil_image = pil_image.rotate(rotation_degrees, expand=True) # Apply rotation
            
            pil_image.thumbnail(size, Image.Resampling.LANCZOS) # Resize for thumbnail            # Add rotate overlay if requested
            if add_rotate_icon:
                # Use the function directly instead of through self
                # Make sure we have imported math for the circular calculations
                try:
                    pil_image = add_rotate_overlay(self, pil_image)
                except Exception as e:
                    print(f"Error adding rotate overlay: {e}")
            
            self.tk_thumbnails_cache[cache_key] = ImageTk.PhotoImage(pil_image)
        else:
            return None
    return self.tk_thumbnails_cache[cache_key]

def rotate_image(self, img_path):
    """
    Handles rotation logic and updates UI.
    This method should be called by ComplexLayoutDialog.
    """
    current_rotation = self.image_rotations.get(img_path, 0)
    new_rotation = (current_rotation + 90) % 360
    self.image_rotations[img_path] = new_rotation
    
    try:
        # Always re-open the original image to avoid quality loss from multiple rotations
        original_image = Image.open(img_path)
        
        # Apply the full rotation in one step
        if new_rotation != 0:
            rotated_image = original_image.rotate(new_rotation, expand=True, resample=Image.Resampling.BICUBIC)
        else:
            rotated_image = original_image.copy()
            
        # Create a thumbnail version for the cache
        thumbnail_copy = rotated_image.copy()
        thumbnail_copy.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
        
        # Update the cache with the new thumbnail
        self.pil_images_cache[img_path] = thumbnail_copy
        
    except Exception as e:
        print(f"Error rotating image {img_path}: {e}")
    
    # Clear ALL thumbnail cache entries for this image to force re-generation
    keys_to_delete = [k for k in self.tk_thumbnails_cache if k[0] == img_path]
    for k in keys_to_delete:
        del self.tk_thumbnails_cache[k]
    
    # Update the thumbnail in the available images list
    self._populate_available_images() # Re-populate to refresh all thumbnails
    
    # If the image is currently assigned to any slots, update all of them
    # Modified to update all slots that might use this image
    updated_slots = []
    for slot_name, rect_data in self.layout_rectangles.items():
        if rect_data["current_image"] == img_path:
            self._display_image_in_rectangle(slot_name, img_path)
            updated_slots.append(slot_name)
    
    # Record action for undo
    self._record_action("rotate", img_path, current_rotation, new_rotation)
    
    if updated_slots:
        self.status_bar.config(text=f"Rotated {os.path.basename(img_path)} by 90° in {', '.join(updated_slots)}.")
    else:
        self.status_bar.config(text=f"Rotated {os.path.basename(img_path)} by 90°.")