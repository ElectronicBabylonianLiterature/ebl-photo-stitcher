import tkinter as tk
import os

def record_action(self, action_type, *args):
    """
    Records an action for undo functionality.
    This method should be called by ComplexLayoutDialog.
    """
    self.action_history.append((action_type, args))

def undo_last_action(self):
    """
    Undoes the last recorded action.
    This method should be called by ComplexLayoutDialog.
    """
    if not self.action_history:
        self.status_bar.config(text="No actions to undo.")
        return

    last_action = self.action_history.pop()
    action_type = last_action[0]
    args = last_action[1]

    if action_type == "assign":
        slot_name, old_img_data, new_img_data = args
        
        # New image was assigned, so clear it from the slot
        if self.layout_rectangles[slot_name]["image_id"]:
            self.layout_canvas.delete(self.layout_rectangles[slot_name]["image_id"])
            self.layout_rectangles[slot_name]["image_id"] = None
        self.layout_rectangles[slot_name]["current_image"] = None
        self.result_layout[slot_name] = None
        
        if new_img_data and new_img_data["path"] in self.available_labels:
            self.available_labels[new_img_data["path"]].master.pack(pady=3, padx=3, fill=tk.X)

        # Revert to old_img_data (re-assign or make empty)
        if old_img_data:
            old_img_path = old_img_data["path"]
            old_rotation = old_img_data["rotation"]
            self.image_rotations[old_img_path] = old_rotation
            self._display_image_in_rectangle(slot_name, old_img_path)
            self.layout_rectangles[slot_name]["current_image"] = old_img_path
            self.result_layout[slot_name] = old_img_data # Store dict with path and rotation
            if old_img_path in self.available_labels:
                self.available_labels[old_img_path].master.pack_forget()
        else:
            self.layout_canvas.itemconfig(self.layout_rectangles[slot_name]["rectangle"], fill="white")
        self.status_bar.config(text=f"Undo: Assignment for {slot_name} reverted.")
            
    elif action_type == "unassign":
        slot_name, img_data = args
        img_path = img_data["path"]
        rotation = img_data["rotation"]
        
        # Re-assign the image to the slot
        self.image_rotations[img_path] = rotation # Restore rotation
        self.result_layout[slot_name] = img_data # Store dict with path and rotation
        self.layout_rectangles[slot_name]["current_image"] = img_path
        self._display_image_in_rectangle(slot_name, img_path)
        if img_path in self.available_labels:
            self.available_labels[img_path].master.pack_forget()
        self.status_bar.config(text=f"Undo: Image re-assigned to {slot_name}.")
            
    elif action_type == "add_sequence":
        slot_key, img_data, original_idx = args
        img_path = img_data["path"]
        current_sequence = self.result_layout.get(slot_key, [])
        
        # Ensure current_sequence contains dictionaries
        processed_sequence = []
        for item in current_sequence:
            if isinstance(item, dict) and "path" in item:
                processed_sequence.append(item)
            else: # Assume it's just a path
                processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

        if img_data in processed_sequence: # Check by full item (path+rotation)
            processed_sequence.remove(img_data)
            self.result_layout[slot_key] = processed_sequence
            self._update_sequence_indicator(slot_key)
            if img_path in self.available_labels:
                self.available_labels[img_path].master.pack(pady=3, padx=3, fill=tk.X)
            self.status_bar.config(text=f"Undo: Removed image from {slot_key} sequence.")
                
    elif action_type == "remove_sequence":
        slot_key, img_data, original_idx = args
        img_path = img_data["path"]
        rotation = img_data["rotation"]
        current_sequence = self.result_layout.get(slot_key, [])
        
        # Ensure current_sequence contains dictionaries
        processed_sequence = []
        for item in current_sequence:
            if isinstance(item, dict) and "path" in item:
                processed_sequence.append(item)
            else: # Assume it's just a path
                processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

        processed_sequence.insert(original_idx, img_data)
        self.result_layout[slot_key] = processed_sequence
        self.image_rotations[img_path] = rotation # Restore rotation for this image
        self._update_sequence_indicator(slot_key)
        if img_path in self.available_labels:
            self.available_labels[img_path].master.pack_forget() # Re-hide if it was made available
        self.status_bar.config(text=f"Undo: Added image back to {slot_key} sequence.")

    elif action_type == "move_sequence":
        slot_key, img_data, old_idx, new_idx = args
        img_path = img_data["path"]
        current_sequence = self.result_layout.get(slot_key, [])
        
        # Ensure current_sequence contains dictionaries
        processed_sequence = []
        for item in current_sequence:
            if isinstance(item, dict) and "path" in item:
                processed_sequence.append(item)
            else: # Assume it's just a path
                processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

        if img_data in processed_sequence: # Ensure image is still there
            processed_sequence.remove(img_data)
            processed_sequence.insert(old_idx, img_data)
            self.result_layout[slot_key] = processed_sequence
            self.status_bar.config(text=f"Undo: Moved image back in {slot_key} sequence.")

    elif action_type == "rotate":
        img_path, old_rotation, new_rotation = args
        self.image_rotations[img_path] = old_rotation
        # Force regeneration of thumbnails
        keys_to_delete = [k for k in self.tk_thumbnails_cache if k[0] == img_path]
        for k in keys_to_delete:
            del self.tk_thumbnails_cache[k]
        
        self._populate_available_images()
        # If the image is currently assigned to a slot, update it there too
        for slot_name, rect_data in self.layout_rectangles.items():
            if rect_data["current_image"] == img_path:
                self._display_image_in_rectangle(slot_name, img_path)
                break
        self.status_bar.config(text=f"Undo: Rotated {os.path.basename(img_path)} back.")