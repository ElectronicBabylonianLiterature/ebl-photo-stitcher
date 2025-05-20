import tkinter as tk
from tkinter import ttk, messagebox
import os

def show_sequence_dialog(self, slot_key):
    """
    Manages the pop-up dialog for sequence images.
    This method should be called by ComplexLayoutDialog.
    """
    sequence_images_data = self.result_layout.get(slot_key, [])
    
    dialog = tk.Toplevel(self)
    dialog.title(f"Manage {slot_key.replace('_', ' ').capitalize()} Sequence")
    dialog.transient(self)
    dialog.grab_set()
    
    ttk.Label(dialog, text=f"Images in {slot_key.replace('_', ' ').capitalize()}:").pack(pady=5, padx=10)
    
    listbox_frame = ttk.Frame(dialog)
    listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    listbox = tk.Listbox(listbox_frame, height=6, selectmode=tk.SINGLE)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    
    # Populate listbox (display only the basename)
    for item in sequence_images_data:
        listbox.insert(tk.END, os.path.basename(item["path"]))
    
    buttons_frame = ttk.Frame(dialog)
    buttons_frame.pack(fill=tk.X, padx=10, pady=5)
    
    add_button = ttk.Button(buttons_frame, text="Add Current Selection", 
                            command=lambda: add_selected_to_sequence(self, slot_key, dialog, listbox))
    add_button.pack(side=tk.LEFT, padx=5)
    
    remove_button = ttk.Button(buttons_frame, text="Remove Selected", 
                                command=lambda: remove_from_sequence(self, slot_key, listbox, dialog))
    remove_button.pack(side=tk.LEFT, padx=5)

    move_up_button = ttk.Button(buttons_frame, text="Move Up", command=lambda: move_sequence_item(self, slot_key, listbox, -1))
    move_up_button.pack(side=tk.LEFT, padx=5)

    move_down_button = ttk.Button(buttons_frame, text="Move Down", command=lambda: move_sequence_item(self, slot_key, listbox, 1))
    move_down_button.pack(side=tk.LEFT, padx=5)

    close_button = ttk.Button(buttons_frame, text="Close", command=dialog.destroy)
    close_button.pack(side=tk.RIGHT, padx=5)
    
    # Center dialog
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = self.winfo_rootx() + (self.winfo_width() // 2) - (width // 2)
    y = self.winfo_rooty() + (self.winfo_height() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.wait_window(dialog) # Wait for this dialog to close

def add_selected_to_sequence(self, slot_key, dialog, listbox_widget):
    """
    Adds an image to a sequence.
    This method should be called by ComplexLayoutDialog.
    """
    if not self.selected_image_path:
        messagebox.showinfo("No Image Selected", "Please select an image from the available images first.", parent=dialog)
        return
    
    # Check if image is used in a main slot
    for slot_name, rect_data in self.layout_rectangles.items():
        if not rect_data["is_sequence"] and rect_data["current_image"] == self.selected_image_path:
            messagebox.showwarning("Image In Use", 
                                   f"Image is already assigned to main view '{slot_name}'. Cannot add to sequence.", 
                                   parent=dialog)
            return
    
    # Add to sequence
    current_sequence = self.result_layout.get(slot_key, [])
    
    # Ensure current_sequence contains dictionaries with "path" and "rotation"
    # Convert if it's still just paths from an older layout
    processed_sequence = []
    for item in current_sequence:
        if isinstance(item, dict) and "path" in item:
            processed_sequence.append(item)
        else: # Assume it's just a path
            processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

    # Check if image is already in the sequence (by path)
    if any(item["path"] == self.selected_image_path for item in processed_sequence):
        messagebox.showinfo("Already In Sequence", "This image is already in the sequence.", parent=dialog)
        return
    
    new_item = {"path": self.selected_image_path, "rotation": self.image_rotations.get(self.selected_image_path, 0)}

    # Record action for undo: (action_type, slot_key, image_path, rotation, index_added_at)
    self._record_action("add_sequence", slot_key, new_item, len(processed_sequence))

    processed_sequence.append(new_item)
    self.result_layout[slot_key] = processed_sequence
    
    # Hide the image from available list
    if self.selected_image_path in self.available_labels:
        self.available_labels[self.selected_image_path].master.pack_forget() # Hide the frame containing label and button
    
    # Update sequence count indicator
    update_sequence_indicator(self, slot_key)
    
    # Update the listbox in the current dialog
    listbox_widget.insert(tk.END, os.path.basename(self.selected_image_path))
    listbox_widget.yview_moveto(1.0) # Scroll to bottom

    self._on_thumbnail_click(None) # Deselect the image
    self.status_bar.config(text=f"Added image to {slot_key} sequence.")

def remove_from_sequence(self, slot_key, listbox, dialog):
    """
    Removes an image from a sequence.
    This method should be called by ComplexLayoutDialog.
    """
    selected_indices = listbox.curselection()
    if not selected_indices:
        messagebox.showinfo("No Selection", "Please select an image to remove.", parent=dialog)
        return
    
    idx = selected_indices[0]
    current_sequence = self.result_layout.get(slot_key, [])
    
    if idx >= len(current_sequence):
        return
    
    # Ensure current_sequence contains dictionaries
    processed_sequence = []
    for item in current_sequence:
        if isinstance(item, dict) and "path" in item:
            processed_sequence.append(item)
        else: # Assume it's just a path
            processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

    removed_item = processed_sequence.pop(idx)
    removed_img_path = removed_item["path"]
    
    self.result_layout[slot_key] = processed_sequence
    
    # Record action for undo: (action_type, slot_key, image_dict, index_removed_from)
    self._record_action("remove_sequence", slot_key, removed_item, idx)

    # Make the image available again
    if removed_img_path in self.available_labels:
        self.available_labels[removed_img_path].master.pack(pady=3, padx=3, fill=tk.X)
    
    # Update sequence count indicator
    update_sequence_indicator(self, slot_key)
    
    # Refresh the listbox
    listbox.delete(0, tk.END)
    for item in processed_sequence:
        listbox.insert(tk.END, os.path.basename(item["path"]))
    
    self.status_bar.config(text=f"Removed image from {slot_key} sequence.")

def move_sequence_item(self, slot_key, listbox, direction):
    """
    Reorders images within a sequence.
    This method should be called by ComplexLayoutDialog.
    """
    selected_indices = listbox.curselection()
    if not selected_indices:
        return
    idx = selected_indices[0]
    
    current_sequence = self.result_layout.get(slot_key, [])
    if not current_sequence:
        return
    
    # Ensure current_sequence contains dictionaries
    processed_sequence = []
    for item in current_sequence:
        if isinstance(item, dict) and "path" in item:
            processed_sequence.append(item)
        else: # Assume it's just a path
            processed_sequence.append({"path": item, "rotation": self.image_rotations.get(item, 0)})

    new_idx = idx + direction
    if 0 <= new_idx < len(processed_sequence):
        img_item_to_move = processed_sequence.pop(idx)
        processed_sequence.insert(new_idx, img_item_to_move)
        self.result_layout[slot_key] = processed_sequence
        
        # Record action for undo: (action_type, slot_key, image_dict, old_index, new_index)
        self._record_action("move_sequence", slot_key, img_item_to_move, idx, new_idx)

        # Refresh listbox
        listbox.delete(0, tk.END)
        for item in processed_sequence:
            listbox.insert(tk.END, os.path.basename(item["path"]))
        listbox.selection_set(new_idx)
        listbox.see(new_idx) # Ensure the moved item is visible
        self.status_bar.config(text=f"Moved image in {slot_key} sequence.")

def update_sequence_indicator(self, slot_key):
    """
    Updates the visual count on sequence slots.
    This method should be called by ComplexLayoutDialog.
    """
    rect_data = self.layout_rectangles.get(slot_key)
    if not rect_data: return
    
    sequence_count = len(self.result_layout.get(slot_key, []))
    
    # Update the label to show count
    label_text = f"{slot_key.replace('intermediate_', '').replace('_', ' ').capitalize()} ({sequence_count})"
    self.layout_canvas.itemconfig(rect_data["label"], text=label_text)
    
    # Change background color based on whether there are images
    fill_color = "lightblue" if sequence_count > 0 else "white"
    self.layout_canvas.itemconfig(rect_data["rectangle"], fill=fill_color)