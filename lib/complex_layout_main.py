import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
import json # Added for pretty printing of the final layout

# Import extracted functions with new names
from lib.complex_layout_image_utils import prepare_thumbnails, get_tk_thumbnail, rotate_image, add_rotate_overlay
from lib.complex_layout_layout_drawing import create_layout_visualization, add_labeled_rectangle, display_image_in_rectangle
from lib.complex_layout_dialog_logic import get_default_layout_structure, load_current_layout_into_ui, on_ok, on_cancel
from lib.complex_layout_sequence_manager import show_sequence_dialog, add_selected_to_sequence, remove_from_sequence, move_sequence_item, update_sequence_indicator
from lib.complex_layout_undo_manager import record_action, undo_last_action
from lib.complex_layout_standard_sequences import apply_standard_sequence


class ComplexLayoutDialog(tk.Toplevel):
    def __init__(self, parent, image_paths, current_layout=None, thumbnail_size=(200,200)):
        super().__init__(parent)
        self.transient(parent)
        self.title("Define Complex Photo Layout")
        self.parent_app = parent
        self.image_paths = image_paths
        
        # Add a variable to track dialog completion
        self.result_ready_var = tk.BooleanVar(value=False)
        
        # Initialize result_layout with default or provided structure
        self.result_layout = get_default_layout_structure()
        self.image_rotations = {path: 0 for path in self.image_paths} # Rotation is kept at 0 for all images

        # Apply standard sequence based on number of photos
        num_photos = len(image_paths)
        if num_photos in [4, 7, 8, 9] or num_photos > 9:
            # Use our standard sequence logic
            self.result_layout = apply_standard_sequence(self.image_paths, num_photos)
            
        elif current_layout:
            # Only use current_layout if no standard sequence was applied
            # Deep copy current_layout to avoid modifying the original dict directly
            for key, value in current_layout.items():
                if isinstance(value, dict) and "path" in value: # Main slots
                    self.result_layout[key] = value.copy()
                    self.image_rotations[value["path"]] = 0  # Force rotation to 0
                elif isinstance(value, list): # Sequence slots
                    self.result_layout[key] = [item.copy() if isinstance(item, dict) else {"path": item, "rotation": 0} for item in value]
                    for item in value:
                        if isinstance(item, dict) and "path" in item:
                            self.image_rotations[item["path"]] = 0  # Force rotation to 0
                        else: # Handle old format where sequence items were just paths
                             self.image_rotations[item] = 0

        self.thumbnail_size = thumbnail_size
        self.pil_images_cache = {}
        self.tk_thumbnails_cache = {}
        self.layout_rectangles = {} # Initialize layout_rectangles here
        
        # Bind extracted functions as methods - remove rotate_image binding
        self._prepare_thumbnails = prepare_thumbnails.__get__(self)
        self._get_tk_thumbnail = get_tk_thumbnail.__get__(self)
        
        self._create_layout_visualization = create_layout_visualization.__get__(self)
        self._add_labeled_rectangle = add_labeled_rectangle.__get__(self)
        self._display_image_in_rectangle = display_image_in_rectangle.__get__(self)

        self._get_default_layout_structure = get_default_layout_structure.__get__(self)
        self._load_current_layout_into_ui = load_current_layout_into_ui.__get__(self)
        self._on_ok = on_ok.__get__(self)
        self._on_cancel = on_cancel.__get__(self)

        self._show_sequence_dialog = show_sequence_dialog.__get__(self)
        self._add_selected_to_sequence = add_selected_to_sequence.__get__(self)
        self._remove_from_sequence = remove_from_sequence.__get__(self)
        self._move_sequence_item = move_sequence_item.__get__(self)
        self._update_sequence_indicator = update_sequence_indicator.__get__(self)
        
        self._record_action = record_action.__get__(self)
        self._undo_last_action = undo_last_action.__get__(self)
        
        self.undo_stack = []
        self.available_labels = {}
        self.selected_image_path = None
        
        self._setup_ui()
        self._load_current_layout_into_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()
        self.update_idletasks() 
        parent_x = self.parent_app.winfo_rootx()
        parent_y = self.parent_app.winfo_rooty()
        parent_width = self.parent_app.winfo_width()
        parent_height = self.parent_app.winfo_height()
        
        dialog_width = self.winfo_reqwidth() if self.winfo_reqwidth() > 1 else 900
        dialog_height = self.winfo_reqheight() if self.winfo_reqheight() > 1 else 700
        x_pos = parent_x + (parent_width // 2) - (dialog_width // 2)
        y_pos = parent_y + (parent_height // 2) - (dialog_height // 2)
        self.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")

        self.wait_window(self)
        
    def _populate_available_images(self):
        # Clear existing images first if repopulating
        for widget in self.scrollable_frame_available.winfo_children():
            widget.destroy()
        
        for img_path in self.image_paths:
            # Check if the image is already assigned to a main slot or a sequence
            is_assigned = False
            # Check main slots
            for slot_data in self.layout_rectangles.values():
                if slot_data["current_image"] == img_path:
                    is_assigned = True
                    break
            if is_assigned: continue # Skip if in a main slot

            # Check sequence slots
            for seq_list in self.result_layout.values():
                if isinstance(seq_list, list):
                    for item in seq_list:
                        if isinstance(item, dict) and item.get("path") == img_path:
                            is_assigned = True
                            break
                if is_assigned: break
            if is_assigned: continue # Skip if in a sequence

            frame = ttk.Frame(self.scrollable_frame_available, relief=tk.RAISED, borderwidth=1)
            frame.pack(pady=3, padx=3, fill=tk.X)

            tk_thumb = self._get_tk_thumbnail(img_path, add_rotate_icon=False)  # No rotation icon
            if tk_thumb:
                img_container = ttk.Frame(frame)
                img_container.pack(side=tk.LEFT, padx=2, pady=2)
                
                img_label = ttk.Label(img_container, image=tk_thumb, cursor="hand2")
                img_label.pack()
                
                # Bind regular click for selection
                img_label.bind("<Button-1>", lambda e, p=img_path: self._on_thumbnail_click(p))
                
                # Remove right-click binding for rotation
                
                # Add filename label
                filename_label = ttk.Label(frame, text=os.path.basename(img_path)[:25])
                filename_label.pack(side=tk.LEFT, padx=5)
                
                self.available_labels[img_path] = filename_label
            else:
                error_label = ttk.Label(frame, text=f"Error loading {os.path.basename(img_path)}", 
                                        foreground="red", background="lightgrey")
                error_label.pack(side=tk.LEFT, padx=2, pady=2)
                self.available_labels[img_path] = error_label # Store the label widget for errors too

    def _setup_ui(self):
        container = ttk.Frame(self, padding="10")
        container.pack(expand=True, fill=tk.BOTH)

        # Left panel for available images
        available_panel = ttk.LabelFrame(container, text="Available Images", padding="5")
        available_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10), ipadx=5, ipady=5)
        
        canvas_available = tk.Canvas(available_panel, borderwidth=0, width=self.thumbnail_size[0] + 60) # Increased width for rotate button
        scrollbar_available = ttk.Scrollbar(available_panel, orient="vertical", command=canvas_available.yview)
        self.scrollable_frame_available = ttk.Frame(canvas_available)

        self.scrollable_frame_available.bind(
            "<Configure>", 
            lambda e: canvas_available.configure(scrollregion=canvas_available.bbox("all"))
        )
        canvas_available.create_window((0, 0), window=self.scrollable_frame_available, anchor="nw")
        canvas_available.configure(yscrollcommand=scrollbar_available.set)

        self.available_labels = {} 
        self._populate_available_images() # Call the bound method

        canvas_available.pack(side="left", fill="y", expand=False)
        scrollbar_available.pack(side="right", fill="y")

        # Right panel - Layout visualization as per the image
        layout_panel = ttk.Frame(container, padding="5") 
        layout_panel.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)          # Add Undo button with arrow icon at the top right of the layout panel
        undo_button_frame = ttk.Frame(layout_panel)
        undo_button_frame.pack(fill=tk.X, anchor=tk.NE)
        # Use tk.Button instead of ttk.Button to support font parameter
        undo_button = tk.Button(undo_button_frame, text="↶", command=self._undo_last_action, 
                              width=2, font=("Arial", 14), relief=tk.RAISED)
        undo_button.pack(side=tk.RIGHT, pady=5)
        
        # Add tooltip for the undo button
        undo_tooltip = ttk.Label(undo_button_frame, text="Undo Last Action", background="lightyellow")
        
        def show_tooltip(event):
            x, y, _, _ = undo_button.bbox("all")
            x += undo_button.winfo_rootx() - 80  # Adjust x position
            y += undo_button.winfo_rooty() + 20  # Adjust y position
            undo_tooltip.place(x=x, y=y)
            
        def hide_tooltip(event):
            undo_tooltip.place_forget()
            
        undo_button.bind("<Enter>", show_tooltip)
        undo_button.bind("<Leave>", hide_tooltip)
        
        self.action_history = [] # To store actions for undo

        # Create a canvas for the layout
        self.layout_canvas = tk.Canvas(layout_panel, bg="white", bd=1, relief=tk.SUNKEN)
        self.layout_canvas.pack(expand=True, fill=tk.BOTH)
        
        # Setup the layout rectangles as per the image
        self._create_layout_visualization()
        
        # Button panel
        button_panel = ttk.Frame(self, padding="5") 
        button_panel.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,10), padx=5)
        
        self.status_bar = ttk.Label(button_panel, text="Click an image, then click a rectangle to assign it.")
        self.status_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ok_button = ttk.Button(button_panel, text="OK", command=self._on_ok, width=10)
        ok_button.pack(side=tk.RIGHT, padx=(0,5)) 
        cancel_button = ttk.Button(button_panel, text="Cancel", command=self._on_cancel, width=10)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        self.selected_image_path = None # Only store selected image for click-based assignment
        
        # Load current layout
        self._load_current_layout_into_ui()

    def _on_thumbnail_click(self, img_path):
        if self.selected_image_path:
            # Deselect previous
            if self.selected_image_path in self.available_labels:
                self.available_labels[self.selected_image_path].config(relief=tk.FLAT, background='SystemButtonFace')
        
        self.selected_image_path = img_path
        if img_path: # Only highlight if an image is actually selected
            self.available_labels[img_path].config(relief=tk.SUNKEN, background='lightblue')
            self.status_bar.config(text=f"Selected {os.path.basename(img_path)}. Now click a layout slot to assign.")
        else: # Deselected
            self.status_bar.config(text="Click an image, then click a rectangle to assign it.")


    def _on_rectangle_click(self, slot_name, event):
        """Handle clicks on rectangles."""
        rect_data = self.layout_rectangles.get(slot_name)
        if not rect_data: return
        
        if rect_data["is_sequence"]:
            # For sequences, show images in a separate dialog
            self._show_sequence_dialog(slot_name)
        elif self.selected_image_path:
            # If an image is selected, assign it to this slot
            self._assign_image_to_slot(slot_name, self.selected_image_path)
            self._on_thumbnail_click(None) # Deselect the image after assignment
        elif rect_data["current_image"]:
            # If slot has an image and no image is selected, unassign it automatically
            # Remove the confirmation dialog since the interaction is now more intuitive
            self._unassign_image_from_slot(slot_name)
            self.status_bar.config(text=f"Removed image from {slot_name.capitalize()}. Select from left panel to reassign.")

    def _assign_image_to_slot(self, slot_name, img_path):
        """Assign an image to a main slot."""
        # Check if image is already used in another main slot
        for s_name, rect_data in self.layout_rectangles.items():
            if not rect_data["is_sequence"] and rect_data["current_image"] == img_path and s_name != slot_name:
                messagebox.showwarning("Image In Use", 
                                    f"Image is already assigned to '{s_name.capitalize()}'. Unassign it first.", 
                                    parent=self)
                return
        
        # Record previous state for undo
        previous_assignment_path = self.result_layout.get(slot_name)
        previous_assignment_data = None
        if isinstance(previous_assignment_path, dict) and "path" in previous_assignment_path:
            previous_assignment_data = previous_assignment_path
        elif isinstance(previous_assignment_path, str): # Old format, convert to dict
            previous_assignment_data = {"path": previous_assignment_path, "rotation": self.image_rotations.get(previous_assignment_path, 0)}

        new_assignment_data = {"path": img_path, "rotation": self.image_rotations.get(img_path, 0)}

        if previous_assignment_data != new_assignment_data: # Only record if change happens
            self._record_action("assign", slot_name, previous_assignment_data, new_assignment_data)

        # Remove from any sequence
        for key in self.result_layout.keys():
            if isinstance(self.result_layout[key], list):
                # We need to iterate and remove based on the 'path' key in dictionary items
                initial_len = len(self.result_layout[key])
                self.result_layout[key] = [
                    item for item in self.result_layout[key] 
                    if not (isinstance(item, dict) and item.get("path") == img_path)
                ]
                if len(self.result_layout[key]) < initial_len:
                    self._update_sequence_indicator(key)
        
        # Check if current slot already has an image
        rect_data = self.layout_rectangles[slot_name]
        current_img_path = rect_data["current_image"]
        if current_img_path:
            # Unassign the current image (make it available again in the left panel)
            self._make_image_available_in_leftpanel(current_img_path)
            
            # Remove the current image from canvas
            if rect_data["image_id"]:
                self.layout_canvas.delete(rect_data["image_id"])
                rect_data["image_id"] = None
        
        # Assign new image
        self.layout_rectangles[slot_name]["current_image"] = img_path
        self.result_layout[slot_name] = {"path": img_path, "rotation": self.image_rotations.get(img_path, 0)}
        
        # Display the image in the rectangle
        self._display_image_in_rectangle(slot_name, img_path)
        
        # Hide the image from available list when assigned to any view
        self._hide_image_from_leftpanel(img_path)
        
        self.status_bar.config(text=f"Assigned {os.path.basename(img_path)} to {slot_name.capitalize}.")
    
    def get_layout_config(self):
        """
        Returns the final layout configuration after the dialog is closed.
        This method should be called after the dialog is destroyed to get the result.
        
        Returns:
            The layout configuration dictionary or None if canceled
        """
        return self.result_layout
