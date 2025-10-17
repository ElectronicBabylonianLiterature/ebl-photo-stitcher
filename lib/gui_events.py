"""Event handlers for the eBL Photo Stitcher application."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import threading


class EventHandlers:
    """Event handlers for UI interactions."""

    @staticmethod
    def toggle_logo_path_entry(add_logo_var, logo_path_entry, browse_logo_btn):
        """Enable/disable logo path entry based on checkbox state."""
        state = tk.NORMAL if add_logo_var.get() else tk.DISABLED
        logo_path_entry.config(state=state)
        browse_logo_btn.config(state=state)

    @staticmethod
    def browse_logo_file(root, logo_path_var):
        """Browse and select a logo file."""
        init_dir = os.path.dirname(logo_path_var.get()) if logo_path_var.get(
        ) else os.path.expanduser("~/Pictures")
        if not os.path.isdir(init_dir):
            init_dir = os.path.expanduser("~")

        file_selected = filedialog.askopenfilename(
            initialdir=init_dir,
            title="Select Logo",
            filetypes=(("PNG", "*.png"), ("All", "*.*"))
        )

        if file_selected:
            logo_path_var.set(file_selected)

    @staticmethod
    def handle_ruler_canvas_click(event, canvas_params, ruler_position_var, museum_var, draw_ruler_callback):
        """Handle clicks on the ruler position canvas."""
        current_museum = museum_var.get()
        if current_museum == "Iraq Museum" or current_museum == "Iraq Museum (Sippar Library)":

            print("Ruler position is fixed for Iraq Museum.")
            return

        s = canvas_params['size']
        p = canvas_params['padding']
        bt = canvas_params['band_thickness']

        ox1, oy1, ox2, oy2 = p + bt, p + bt, s - p - bt, s - p - bt

        if ox1 <= event.x <= ox2 and p <= event.y < oy1:
            ruler_position_var.set("top")
        elif ox1 <= event.x <= ox2 and oy2 < event.y <= oy2 + bt:
            ruler_position_var.set("bottom")
        elif p <= event.x < ox1 and oy1 <= event.y <= oy2:
            ruler_position_var.set("left")
        elif ox2 < event.x <= ox2 + bt and oy1 <= event.y <= oy2:
            ruler_position_var.set("right")
        else:
            return

        draw_ruler_callback()
        print(f"Ruler pos: {ruler_position_var.get()}")

    @staticmethod
    def handle_museum_change(event, museum_var, ruler_position_var, measurements_checkbox,
                             measurements_loaded, draw_ruler_callback, save_config_callback=None):
        """Handle museum selection changes."""
        museum_selection = museum_var.get()
        print(f"Museum selected: {museum_selection}")

        if museum_selection == "Iraq Museum" or museum_selection == "Iraq Museum (Sippar Library)":
            ruler_position_var.set("bottom-left-fixed")
        else:

            if ruler_position_var.get() == "bottom-left-fixed":
                ruler_position_var.set("top")

        if museum_selection == "British Museum" and measurements_loaded:

            measurements_checkbox.state(['!disabled'])
        else:

            measurements_checkbox.state(['disabled'])

        draw_ruler_callback()

        if event and save_config_callback:
            save_config_callback()

    @staticmethod
    def browse_input_folder(input_folder_var):
        """Browse for input folder."""
        init_dir = input_folder_var.get()
        if not init_dir or not os.path.isdir(init_dir):
            try:
                script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                init_dir = script_dir
            except:
                init_dir = os.path.expanduser("~")

        folder_selected = filedialog.askdirectory(initialdir=init_dir)
        if folder_selected:
            input_folder_var.set(folder_selected)

    @staticmethod
    def start_processing_workflow(app_instance, workflow_function, processing_params):
        """Start the processing workflow with given parameters."""

        fp = processing_params['input_folder']
        rp = processing_params['ruler_position']
        ph = processing_params['photographer_name']
        al = processing_params['add_logo']
        lp = processing_params['logo_path']
        ms = processing_params['museum_selection']
        use_measurements = processing_params['use_measurements']
        obm = "auto"
        gradient_width = processing_params['gradient_width']
        bg_tolerance = processing_params['bg_tolerance']

        if not fp or not os.path.isdir(fp):
            messagebox.showerror("Error", "Please select a valid input folder.")
            return

        if al and (not lp or not os.path.isfile(lp)):
            messagebox.showerror(
                "Error", "Logo checkbox is checked, but no valid logo file is selected.")
            return

        app_instance.save_config()

        app_instance.lt.configure(state=tk.NORMAL)
        app_instance.lt.delete('1.0', tk.END)
        app_instance.lt.configure(state=tk.DISABLED)

        print(f"Starting processing with {ms} ruler...")
        if use_measurements:
            print(f"Using measurements from database when available.")
        print("")

        app_instance.prb.config(state=tk.DISABLED)
        app_instance.update_progress_bar(0)

        app_instance.configure_museum_settings(ms)

        def run_workflow():
            try:
                workflow_function(
                    processing_params['input_folder'],
                    processing_params['ruler_position'],
                    processing_params['photographer_name'],
                    "auto",
                    processing_params['add_logo'],
                    processing_params['logo_path'],
                    app_instance.RAW_IMAGE_EXTENSION,
                    app_instance.VALID_IMAGE_EXTENSIONS,
                    app_instance.RULER_TEMPLATE_1CM_PATH_ASSET,
                    app_instance.RULER_TEMPLATE_2CM_PATH_ASSET,
                    app_instance.RULER_TEMPLATE_5CM_PATH_ASSET,
                    app_instance.STITCH_VIEW_PATTERNS_WITH_EXT,
                    app_instance.TEMP_EXTRACTED_RULER_FOR_SCALING_FILENAME,
                    app_instance.OBJECT_ARTIFACT_SUFFIX,
                    app_instance.update_progress_bar,
                    app_instance.processing_finished_ui_update,
                    processing_params['museum_selection'],
                    app_instance.root,
                    processing_params['bg_tolerance'],
                    processing_params['use_measurements'],
                    app_instance.measurements_dict if processing_params['use_measurements'] else None,
                    processing_params['gradient_width'],
                    processing_params['enable_hdr']
                )
            except Exception as e:
                print(f"Error in workflow: {e}")
                messagebox.showerror("Processing Error", str(e))
            finally:
                app_instance.prb.config(state=tk.NORMAL)

        threading.Thread(
            target=run_workflow,
            daemon=True
        ).start()

    @staticmethod
    def debug_measurements_loading(app_instance, assets_path, measurements_filename="sippar.json"):
        """Debug function to test loading the measurements file."""
        from gui_utils import resource_path
        import json

        measurements_file = resource_path(
            os.path.join(assets_path, measurements_filename))

        if os.path.exists(measurements_file):
            try:
                from measurements_utils import load_measurements_from_json
                app_instance.measurements_dict = load_measurements_from_json(
                    measurements_file)
                app_instance.measurements_loaded = len(
                    app_instance.measurements_dict) > 0
                print(
                    f"Loaded {len(app_instance.measurements_dict)} measurements from {measurements_filename}")

                if app_instance.measurements_loaded and hasattr(app_instance, "measurements_checkbox"):
                    app_instance.measurements_checkbox.state(['!disabled'])

                    for child in app_instance.measurements_checkbox.master.winfo_children():
                        if isinstance(child, ttk.Label) and "(sippar.json not found" in child.cget("text"):
                            child.destroy()
            except Exception as e:
                print(f"Error reloading measurements: {e}")
