import tkinter as tk
from tkinter import messagebox

def get_default_layout_structure():
    """
    Provides the initial empty layout.
    This method should be called by ComplexLayoutDialog.
    """
    return {
        "obverse": None, "reverse": None,
        "top": None, "bottom": None, "left": None, "right": None,
        "intermediate_obverse_top": [], "intermediate_obverse_bottom": [],
        "intermediate_obverse_left": [], "intermediate_obverse_right": [],
        "intermediate_reverse_top": [], "intermediate_reverse_bottom": [],
        "intermediate_reverse_left": [], "intermediate_reverse_right": [],
    }

def load_current_layout_into_ui(self):
    """
    Loads an existing layout into the UI.
    This method should be called by ComplexLayoutDialog.
    """
    # Unpack the existing layout including rotations if present
    if self.result_layout:
        for slot_name, assigned_value in self.result_layout.items():
            if isinstance(assigned_value, dict) and "path" in assigned_value:
                img_path = assigned_value["path"]
                # Always set rotation to 0 (removing rotation functionality)
                self.image_rotations[img_path] = 0
                
                if not self.layout_rectangles[slot_name]["is_sequence"]:
                    # This is a main slot
                    self.layout_rectangles[slot_name]["current_image"] = img_path
                    self._display_image_in_rectangle(slot_name, img_path)
                    # Hide from available list
                    if img_path in self.available_labels:
                        self.available_labels[img_path].master.pack_forget()
            elif isinstance(assigned_value, list): # Sequence slots
                # For sequences, we need to ensure images are hidden and indicators updated
                for item in assigned_value:
                    # Handle both string paths and dictionary items
                    if isinstance(item, dict) and "path" in item:
                        img_path = item["path"]
                    else:
                        img_path = item  # Assume it's a string path
                        
                    # Always set rotation to 0 (removing rotation functionality)
                    self.image_rotations[img_path] = 0
                    
                    if img_path in self.available_labels:
                        self.available_labels[img_path].master.pack_forget()
                    
        # After processing all assignments, refresh available images to reflect hidden ones
        self._populate_available_images()
        
        # Update sequence indicators
        for slot_key in self.layout_rectangles:
            if "intermediate" in slot_key:
                self._update_sequence_indicator(slot_key)
    
    # Initial populating of available images needs to happen after rotations are loaded
    # so that correct thumbnails are prepared.
    self._populate_available_images()


def on_ok(self):
    """
    Handles the validation and finalization of the layout.
    This method should be called by ComplexLayoutDialog.
    """
    # Final result_layout should store image path and its rotation
    final_layout = get_default_layout_structure()
    for slot_name, rect_data in self.layout_rectangles.items():
        if not rect_data["is_sequence"]:
            if rect_data["current_image"]:
                img_path = rect_data["current_image"]
                final_layout[slot_name] = {
                    "path": img_path,
                    "rotation": self.image_rotations.get(img_path, 0)
                }
        else: # Sequence slots
            sequence_items = self.result_layout.get(slot_name, [])
            final_layout[slot_name] = []
            
            for item in sequence_items:
                if isinstance(item, dict) and "path" in item:
                    # Item is already a dictionary with path
                    img_path = item["path"]
                    final_layout[slot_name].append({
                        "path": img_path,
                        "rotation": self.image_rotations.get(img_path, 0)
                    })
                elif isinstance(item, str):
                    # Item is just a path string
                    final_layout[slot_name].append({
                        "path": item,
                        "rotation": self.image_rotations.get(item, 0)
                    })
    
    self.result_layout = final_layout # Update the result layout with paths and rotations

    # Validate main views (obverse and reverse)
    main_faces = {"obverse": False, "reverse": False}
    if self.result_layout.get("obverse") and self.result_layout["obverse"]["path"]:
        main_faces["obverse"] = True
    if self.result_layout.get("reverse") and self.result_layout["reverse"]["path"]:
        main_faces["reverse"] = True

    # Check if there are any assignments at all
    has_any_assignment = False
    for key, value in self.result_layout.items():
        if isinstance(value, list) and value:  # Sequence slots
            has_any_assignment = True
            break
        elif isinstance(value, dict) and value.get("path"):  # Main slots
            has_any_assignment = True
            break

    # Warn if no images are assigned
    if not has_any_assignment:
        if not messagebox.askyesno(
            "No Images Assigned",
            "No images have been assigned to any layout slots. Continue with an empty layout?",
            parent=self
        ):
            return

    # Warn if neither obverse nor reverse is assigned
    elif not main_faces["obverse"] and not main_faces["reverse"]:
        if not messagebox.askyesno(
            "Layout Incomplete",
            "Neither Obverse nor Reverse main view is set. This might lead to unexpected results. Continue?",
            parent=self
        ):
            return

    # Check if intermediate sequences are assigned without their corresponding main views
    for face in ["obverse", "reverse"]:
        intermediate_keys_for_face = [
            f"intermediate_{face}_top",
            f"intermediate_{face}_bottom",
            f"intermediate_{face}_left",
            f"intermediate_{face}_right"
        ]
        has_intermediates_for_face = any(self.result_layout.get(key) for key in intermediate_keys_for_face)
        
        if has_intermediates_for_face and not main_faces[face]:
            messagebox.showwarning(
                "Layout Incomplete",
                f"Intermediate images are set for '{face.capitalize()}', but the main '{face.capitalize()}' view is not assigned.",
                parent=self
            )
            return

    # If all validations pass, set result ready and close the dialog
    self.result_ready_var.set(True)
    self.destroy()

def on_cancel(self):
    """
    Handles the cancellation of the dialog.
    This method should be called by ComplexLayoutDialog.
    """
    self.result_layout = None  # Indicate cancellation
    self.result_ready_var.set(True)
    self.destroy()