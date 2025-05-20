import tkinter as tk
from PIL import Image, ImageTk

def create_layout_visualization(self):
    """
    Defines and draws the layout rectangles on the canvas.
    This method should be called by ComplexLayoutDialog.
    """
    canvas_width = 750 # Adjusted for better spacing
    canvas_height = 650 # Adjusted for better spacing
    self.layout_canvas.config(width=canvas_width, height=canvas_height)
    
    padding = 20 # Increased padding
    central_size = 200 # Increased central size
    side_width = 60 # Increased side width
    side_height = 200 # Increased side height
    top_bottom_width = 180 # Increased top/bottom width
    top_bottom_height = 60 # Increased top/bottom height
    
    # Center point calculation
    center_x = canvas_width / 2
    center_y = canvas_height / 2 
    
    # Define coordinates for main views and their labels
    layout_elements = {
        "obverse": {"coords": (center_x - central_size/2, center_y - central_size/2, 
                               center_x + central_size/2, center_y + central_size/2), 
                    "label": "Obverse"},
        
        "reverse": {"coords": (center_x - central_size/2, center_y + central_size/2 + padding, 
                               center_x + central_size/2, center_y + central_size/2 + padding + central_size), 
                    "label": "Reverse"},
        
        "left": {"coords": (center_x - central_size/2 - padding - side_width, center_y - side_height/2, 
                            center_x - central_size/2 - padding, center_y + side_height/2), 
                 "label": "Left"},
        
        "right": {"coords": (center_x + central_size/2 + padding, center_y - side_height/2, 
                             center_x + central_size/2 + padding + side_width, center_y + side_height/2), 
                  "label": "Right"},
        
        "top": {"coords": (center_x - top_bottom_width/2, center_y - central_size/2 - padding - top_bottom_height, 
                            center_x + top_bottom_width/2, center_y - central_size/2 - padding), 
                "label": "Top"},
        
        "bottom": {"coords": (center_x - top_bottom_width/2, center_y + central_size/2 + padding*2 + central_size, 
                              center_x + top_bottom_width/2, center_y + central_size/2 + padding*2 + central_size + top_bottom_height), 
                   "label": "Bottom"},
    }
    
    # Intermediate sequence indicators
    oi_size = 30 
    
    layout_elements.update({
        "intermediate_obverse_top": {"coords": (layout_elements["obverse"]["coords"][0], layout_elements["obverse"]["coords"][1] - oi_size - 5, 
                                                layout_elements["obverse"]["coords"][0] + 100, layout_elements["obverse"]["coords"][1] - 5), 
                                     "label": "O-Top Seq"},
        "intermediate_obverse_bottom": {"coords": (layout_elements["obverse"]["coords"][0], layout_elements["obverse"]["coords"][3] + 5, 
                                                   layout_elements["obverse"]["coords"][0] + 100, layout_elements["obverse"]["coords"][3] + oi_size + 5), 
                                        "label": "O-Bottom Seq"},
        "intermediate_obverse_left": {"coords": (layout_elements["obverse"]["coords"][0] - oi_size - 5, layout_elements["obverse"]["coords"][1], 
                                                 layout_elements["obverse"]["coords"][0] - 5, layout_elements["obverse"]["coords"][1] + 100), 
                                       "label": "O-Left Seq"},
        "intermediate_obverse_right": {"coords": (layout_elements["obverse"]["coords"][2] + 5, layout_elements["obverse"]["coords"][1], 
                                                  layout_elements["obverse"]["coords"][2] + oi_size + 5, layout_elements["obverse"]["coords"][1] + 100), 
                                        "label": "O-Right Seq"},
        
        "intermediate_reverse_top": {"coords": (layout_elements["reverse"]["coords"][0], layout_elements["reverse"]["coords"][1] - oi_size - 5, 
                                                layout_elements["reverse"]["coords"][0] + 100, layout_elements["reverse"]["coords"][1] - 5), 
                                     "label": "R-Top Seq"},
        "intermediate_reverse_bottom": {"coords": (layout_elements["reverse"]["coords"][0], layout_elements["reverse"]["coords"][3] + 5, 
                                                   layout_elements["reverse"]["coords"][0] + 100, layout_elements["reverse"]["coords"][3] + oi_size + 5), 
                                        "label": "R-Bottom Seq"},
    })

    self.layout_rectangles = {}
    for slot_name, data in layout_elements.items():
        add_labeled_rectangle(self, slot_name, *data["coords"], custom_label=data["label"])

def add_labeled_rectangle(self, slot_name, x1, y1, x2, y2, custom_label=None):
    """
    Helper for drawing rectangles and labels.
    This method should be called by ComplexLayoutDialog.
    """
    rect_id = self.layout_canvas.create_rectangle(x1, y1, x2, y2, outline="black", width=2, fill="white")
    
    label_text = custom_label if custom_label else slot_name.capitalize()
    label_id = self.layout_canvas.create_text(x1 + 5, y1 + 5, text=label_text, anchor=tk.NW, font=("Arial", 8))
    
    self.layout_rectangles[slot_name] = {
        "rectangle": rect_id,
        "label": label_id,
        "coords": (x1, y1, x2, y2),
        "image_id": None,
        "current_image": None,
        "is_sequence": "intermediate" in slot_name
    }
    
    self.layout_canvas.tag_bind(rect_id, "<Button-1>", 
                                lambda e, sn=slot_name: self._on_rectangle_click(sn, e))
    # Also bind click to the label
    self.layout_canvas.tag_bind(label_id, "<Button-1>", 
                                lambda e, sn=slot_name: self._on_rectangle_click(sn, e))

def display_image_in_rectangle(self, slot_name, img_path):
    """
    Places images within the drawn rectangles.
    This method should be called by ComplexLayoutDialog.
    """
    rect_data = self.layout_rectangles[slot_name]
    if not rect_data:
        return
    
    # Remove existing image if any
    if rect_data["image_id"]:
        self.layout_canvas.delete(rect_data["image_id"])
    
    # Get coordinates of rectangle
    x1, y1, x2, y2 = rect_data["coords"]
    center_x = (x1 + x2) / 2
    
    # Calculate size to fit in rectangle (with padding for label)
    rect_width = x2 - x1
    rect_height = y2 - y1
    
    # Adjust for label space (approx 15-20 pixels from the top)
    display_area_height = rect_height - 20
    
    # Calculate optimal size for the thumbnail to fit within the rectangle
    # Maintain aspect ratio
    pil_image_original = Image.open(img_path)
    
    # Apply rotation to the image itself before calculating thumbnail size
    rotation_degrees = self.image_rotations.get(img_path, 0)
    if rotation_degrees != 0:
        pil_image_original = pil_image_original.rotate(rotation_degrees, expand=True)

    original_width, original_height = pil_image_original.size
    
    # Calculate scaling factor
    width_ratio = rect_width / original_width
    height_ratio = display_area_height / original_height
    
    fit_ratio = min(width_ratio, height_ratio)
    
    new_width = int(original_width * fit_ratio)
    new_height = int(original_height * fit_ratio)
    
    # Get thumbnail
    tk_thumb = self._get_tk_thumbnail(img_path, (new_width, new_height))
    
    if tk_thumb:
        # Create image on canvas, adjusting y for label
        img_id = self.layout_canvas.create_image(
            center_x, y1 + 10 + new_height // 2, # Position below the label area
            image=tk_thumb)
        
        # Store reference to prevent garbage collection
        rect_data["tk_image_ref"] = tk_thumb 
        rect_data["image_id"] = img_id
        
        # Change rectangle color to indicate it has an image
        self.layout_canvas.itemconfig(rect_data["rectangle"], fill="lightyellow")