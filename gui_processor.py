# Run: pyinstaller --name "eBLImageProcessor" --onefile --windowed --icon="eBL_Logo.ico" --add-data "assets:assets" gui_processor.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import json
import threading
import cv2

# --- Helper function to get correct asset paths (for bundled read-only assets) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # sys._MEIPASS is not defined, so running in development mode
        base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    return os.path.join(base_path, relative_path)

# --- Helper function to get user-specific config directory ---
APP_NAME_FOR_CONFIG = "eBLImageProcessor" # Used for creating a dedicated config folder

def get_persistent_config_dir():
    """Gets a user-specific directory for persistent application configuration."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        # APPDATA is usually C:\Users\<User>\AppData\Roaming
        app_data_dir = os.getenv("APPDATA", os.path.join(home, "AppData", "Roaming"))
    elif sys.platform == "darwin": # macOS
        app_data_dir = os.path.join(home, "Library", "Application Support")
    else: # Linux and other Unix-like
        app_data_dir = os.getenv("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    
    config_dir = os.path.join(app_data_dir, APP_NAME_FOR_CONFIG)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create config directory {config_dir}: {e}")
            # Fallback to saving config next to the script/executable (less ideal for one-file EXE)
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Running as bundled app
                 # For one-file EXE, sys.executable is the temp path, use its dir
                 # For one-folder EXE, sys.executable is in the main bundle dir
                 return os.path.dirname(sys.executable)
            else: # Running as script
                 return os.path.abspath(os.path.dirname(sys.argv[0]))
    return config_dir

# --- Import Project Modules ---
try:
    import resize_ruler
    import ruler_detector
    from image_merger import merge_object_and_ruler
    from object_extractor import extract_and_save_object
    from object_extractor import DEFAULT_OUTPUT_FILENAME_SUFFIX as OBJECT_SUFFIX
    from raw_processor import convert_cr2_to_tiff
except ImportError as e:
    try:
        root_check_startup = tk.Tk()
        root_check_startup.withdraw()
        messagebox.showerror(
            "Startup Error", f"ERROR: Failed to import one or more project modules: {e}\n\nPlease ensure all .py files are in the same directory or Python path.")
    except tk.TclError:
        print(f"ERROR: Failed to import one or more project modules: {e}")
        print("Please ensure all .py files are in the same directory or Python path.")
    sys.exit(1)

# --- Global Configurations ---
CONFIG_FILENAME_ONLY = "gui_config.json"
CONFIG_FILE_PATH = os.path.join(get_persistent_config_dir(), CONFIG_FILENAME_ONLY) # Persistent path

INPUT_SUBDIRECTORY_NAME = "Examples"

ASSETS_SUBFOLDER = "assets" # Assets are expected to be in this subfolder when bundled
ICON_FILENAME_ONLY = "eBL_logo.png"
RULER_1CM_FILENAME_ONLY = "BM_1cm_scale.tif"
RULER_2CM_FILENAME_ONLY = "BM_2cm_scale.tif"
RULER_5CM_FILENAME_ONLY = "BM_5cm_scale.tif"

# Construct full paths for bundled assets using resource_path
ICON_FILE_ASSET_PATH = resource_path(os.path.join(ASSETS_SUBFOLDER, ICON_FILENAME_ONLY))
RULER_TEMPLATE_1CM_PATH = resource_path(os.path.join(ASSETS_SUBFOLDER, RULER_1CM_FILENAME_ONLY))
RULER_TEMPLATE_2CM_PATH = resource_path(os.path.join(ASSETS_SUBFOLDER, RULER_2CM_FILENAME_ONLY))
RULER_TEMPLATE_5CM_PATH = resource_path(os.path.join(ASSETS_SUBFOLDER, RULER_5CM_FILENAME_ONLY))

VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')
RAW_IMAGE_EXTENSION = '.cr2'


class ImageProcessorApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("eBL Image Processor")
        self.root.geometry("600x650")

        try:
            if os.path.exists(ICON_FILE_ASSET_PATH): # Use asset path for icon
                photo = tk.PhotoImage(file=ICON_FILE_ASSET_PATH)
                self.root.iconphoto(False, photo)
                print(f"Icon '{ICON_FILENAME_ONLY}' loaded successfully from: {ICON_FILE_ASSET_PATH}")
            else:
                print(f"Warning: Icon file '{ICON_FILENAME_ONLY}' not found at resolved asset path: {ICON_FILE_ASSET_PATH}")
        except tk.TclError as e:
            print(f"Warning: Could not load icon '{ICON_FILENAME_ONLY}'. Tkinter error: {e}")
        except Exception as e:
            print(f"Warning: An unexpected error occurred while loading icon: {e}")

        self.input_folder_var = tk.StringVar()
        self.ruler_position_var = tk.StringVar(value="top")
        self.load_config() # Uses CONFIG_FILE_PATH

        style = ttk.Style()
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10))
        style.configure("TFrame", padding=10)
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))

        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        folder_frame = ttk.LabelFrame(main_frame, text="Input Folder", padding="10 10")
        folder_frame.pack(fill=tk.X, pady=(10, 5))
        ttk.Label(folder_frame, text="Select Image Folder:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.input_folder_var, width=50)
        self.folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.browse_button = ttk.Button(folder_frame, text="Browse...", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT)

        ruler_frame = ttk.LabelFrame(main_frame, text="Ruler Position", padding="10 10")
        ruler_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ruler_frame, text="Click to select ruler location (default: Top):").pack(anchor=tk.W)
        
        self.ruler_canvas_size = 120
        self.ruler_canvas_padding = 10
        self.ruler_bar_thickness = 25
        self.ruler_canvas = tk.Canvas(ruler_frame, width=self.ruler_canvas_size,
                                      height=self.ruler_canvas_size, bg="lightgray", relief=tk.SUNKEN, borderwidth=1)
        self.ruler_canvas.pack(pady=5)
        self.draw_ruler_selector()
        self.ruler_canvas.bind("<Button-1>", self.on_ruler_canvas_click)

        process_button = ttk.Button(main_frame, text="Start Processing", command=self.start_processing_thread)
        process_button.pack(pady=(15, 10), ipadx=10, ipady=5)

        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10 10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD,
                                relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def draw_ruler_selector(self):
        self.ruler_canvas.delete("all")
        s = self.ruler_canvas_size; p = self.ruler_canvas_padding; bar_t = self.ruler_bar_thickness
        obj_x1, obj_y1, obj_x2, obj_y2 = p + bar_t, p + bar_t, s - p - bar_t, s - p - bar_t
        self.ruler_canvas.create_rectangle(obj_x1, obj_y1, obj_x2, obj_y2, outline="gray", fill="whitesmoke", dash=(2, 2))
        self.ruler_canvas.create_text(s / 2, s / 2, text="Object", font=('Helvetica', 9, 'italic'), fill="gray")
        sel_pos, base_c, sel_c, tick_c, n_div = self.ruler_position_var.get(), "lightblue", "blue", "black", 4
        len_h, len_v = obj_x2 - obj_x1, obj_y2 - obj_y1
        self.ruler_canvas.create_rectangle(obj_x1, p, obj_x2, p + bar_t, fill=(sel_c if sel_pos == "top" else base_c), outline=tick_c, tags="top_zone")
        for i in range(n_div + 1): x = obj_x1 + i * (len_h / n_div); self.ruler_canvas.create_line(x, p, x, p + bar_t * 0.6, fill=tick_c)
        self.ruler_canvas.create_rectangle(obj_x1, obj_y2, obj_x2, obj_y2 + bar_t, fill=(sel_c if sel_pos == "bottom" else base_c), outline=tick_c, tags="bottom_zone")
        for i in range(n_div + 1): x = obj_x1 + i * (len_h / n_div); self.ruler_canvas.create_line(x, obj_y2, x, obj_y2 + bar_t * 0.6, fill=tick_c)
        self.ruler_canvas.create_rectangle(p, obj_y1, p + bar_t, obj_y2, fill=(sel_c if sel_pos == "left" else base_c), outline=tick_c, tags="left_zone")
        for i in range(n_div + 1): y = obj_y1 + i * (len_v / n_div); self.ruler_canvas.create_line(p, y, p + bar_t * 0.6, y, fill=tick_c)
        self.ruler_canvas.create_rectangle(obj_x2, obj_y1, obj_x2 + bar_t, obj_y2, fill=(sel_c if sel_pos == "right" else base_c), outline=tick_c, tags="right_zone")
        for i in range(n_div + 1): y = obj_y1 + i * (len_v / n_div); self.ruler_canvas.create_line(obj_x2, y, obj_x2 + bar_t * 0.6, y, fill=tick_c)

    def on_ruler_canvas_click(self, event):
        s, p, bar_t = self.ruler_canvas_size, self.ruler_canvas_padding, self.ruler_bar_thickness
        obj_x1, obj_y1, obj_x2, obj_y2 = p + bar_t, p + bar_t, s - p - bar_t, s - p - bar_t
        if obj_x1 <= event.x <= obj_x2 and p <= event.y < obj_y1: self.ruler_position_var.set("top")
        elif obj_x1 <= event.x <= obj_x2 and obj_y2 < event.y <= obj_y2 + bar_t: self.ruler_position_var.set("bottom")
        elif p <= event.x < obj_x1 and obj_y1 <= event.y <= obj_y2: self.ruler_position_var.set("left")
        elif obj_x2 < event.x <= obj_x2 + bar_t and obj_y1 <= event.y <= obj_y2: self.ruler_position_var.set("right")
        else: return
        self.draw_ruler_selector(); print(f"Ruler position set to: {self.ruler_position_var.get()}")

    def browse_folder(self):
        initial_dir = self.input_folder_var.get()
        if not initial_dir or not os.path.isdir(initial_dir):
            try:
                script_dir_for_browse = os.path.dirname(os.path.abspath(sys.argv[0]))
                potential_initial_dir = os.path.join(script_dir_for_browse, INPUT_SUBDIRECTORY_NAME)
                initial_dir = potential_initial_dir if os.path.isdir(potential_initial_dir) else script_dir_for_browse
            except Exception: initial_dir = os.path.expanduser("~")
        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        if folder_selected: self.input_folder_var.set(folder_selected)

    def save_config(self):
        config_data = {"last_folder": self.input_folder_var.get(), "last_ruler_position": self.ruler_position_var.get()}
        try:
            # Ensure the config directory exists (get_persistent_config_dir creates it)
            config_dir = get_persistent_config_dir() # Called to ensure creation
            with open(CONFIG_FILE_PATH, "w") as f: json.dump(config_data, f) # Use full path
            print(f"Configuration saved to: {CONFIG_FILE_PATH}")
        except IOError as e: print(f"Error: Could not save configuration to {CONFIG_FILE_PATH}: {e}")
        except Exception as e: print(f"Unexpected error saving configuration: {e}")


    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE_PATH): # Use full path
                with open(CONFIG_FILE_PATH, "r") as f:
                    config_data = json.load(f)
                    self.input_folder_var.set(config_data.get("last_folder", ""))
                    self.ruler_position_var.set(config_data.get("last_ruler_position", "top"))
                    print(f"Configuration loaded from: {CONFIG_FILE_PATH}")
            else:
                print(f"Configuration file not found at {CONFIG_FILE_PATH}. Using defaults.")
        except Exception as e: print(f"Warning: Could not load or parse {CONFIG_FILE_PATH}: {e}. Using defaults.")

    def start_processing_thread(self):
        folder_path = self.input_folder_var.get()
        ruler_pos = self.ruler_position_var.get()
        obj_bg_mode = "auto"
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Please select a valid input folder."); return
        self.save_config()
        self.log_text.configure(state=tk.NORMAL); self.log_text.delete('1.0', tk.END); self.log_text.configure(state=tk.DISABLED)
        print("Starting processing...\n")
        threading.Thread(target=self.run_main_workflow_from_gui, args=(folder_path, ruler_pos, obj_bg_mode), daemon=True).start()

    def run_main_workflow_from_gui(self, input_dir_from_gui, ruler_position_from_gui, object_bg_mode_from_gui):
        print(f"GUI initiated workflow in directory: {input_dir_from_gui}")
        print(f"Selected Ruler Position: {ruler_position_from_gui}")
        print(f"Object Extraction Background Mode: {object_bg_mode_from_gui} (fixed)")
        if not all(os.path.exists(p) for p in [RULER_TEMPLATE_1CM_PATH, RULER_TEMPLATE_2CM_PATH, RULER_TEMPLATE_5CM_PATH]):
            missing = [os.path.basename(p) for p in [RULER_TEMPLATE_1CM_PATH, RULER_TEMPLATE_2CM_PATH, RULER_TEMPLATE_5CM_PATH] if not os.path.exists(p)]
            msg = f"Missing ruler template files: {', '.join(missing)}. Ensure they are in the '{ASSETS_SUBFOLDER}' directory (bundled with the app)."
            print(f"ERROR: {msg}"); messagebox.showerror("Asset Error", msg); return
        print("-" * 50)
        success_count, error_count, cr2_conv = 0, 0, 0

        for filename in os.listdir(input_dir_from_gui):
            original_filepath = os.path.join(input_dir_from_gui, filename)
            current_processing_filepath = original_filepath
            is_temp_tiff_from_cr2 = False
            file_lower = filename.lower()

            if file_lower.endswith(RAW_IMAGE_EXTENSION):
                print(f"Found RAW: {filename}. Attempting conversion...")
                base_name_no_ext, _ = os.path.splitext(filename)
                temp_tiff_path = os.path.join(input_dir_from_gui, f"{base_name_no_ext}_from_raw.tif")
                try:
                    convert_cr2_to_tiff(original_filepath, temp_tiff_path)
                    current_processing_filepath = temp_tiff_path; is_temp_tiff_from_cr2 = True; cr2_conv += 1
                    print(f"  RAW conversion successful: {os.path.basename(temp_tiff_path)}")
                except Exception as raw_e: print(f"  ERROR converting RAW {filename}: {raw_e}"); error_count += 1; print("-" * 50); continue
            elif not file_lower.endswith(VALID_IMAGE_EXTENSIONS):
                if not os.path.isdir(original_filepath): print(f"Skipping unsupported file: {filename}")
                continue
            
            current_filename_for_skip_check = os.path.basename(current_processing_filepath)
            if (current_filename_for_skip_check.endswith(resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE + resize_ruler.OUTPUT_FILE_EXTENSION) or
                current_filename_for_skip_check.endswith("_merged.jpg") or
                current_filename_for_skip_check.endswith(OBJECT_SUFFIX)): 
                if not is_temp_tiff_from_cr2: print(f"Skipping previously generated: {current_filename_for_skip_check}")
                continue

            print(f"Processing image: {os.path.basename(current_processing_filepath)}")
            output_base_name = os.path.splitext(os.path.basename(original_filepath))[0]
            
            try:
                print("  Step 1: Detecting scale...")
                px_cm = ruler_detector.estimate_pixels_per_centimeter_from_ruler(current_processing_filepath, ruler_position=ruler_position_from_gui)
                print(f"    Scale detected: {px_cm:.2f} px/cm")

                print("  Step 2: Extracting object...")
                extracted_obj_fp = extract_and_save_object(current_processing_filepath, extraction_background_mode=object_bg_mode_from_gui)
                if not extracted_obj_fp or not os.path.exists(extracted_obj_fp): raise FileNotFoundError("Extracted object file not created.")
                print(f"    Object extracted to: {os.path.basename(extracted_obj_fp)}")

                print("  Step 3: Choosing and resizing ruler...")
                extracted_img = cv2.imread(extracted_obj_fp)
                if extracted_img is None: raise ValueError("Could not load extracted object.")
                obj_h, obj_w = extracted_img.shape[:2]
                obj_w_cm = obj_w / px_cm if px_cm > 0 else 0
                if obj_w_cm <= 0: raise ValueError("Invalid object physical width.")
                print(f"    Extracted object physical width: {obj_w_cm:.2f} cm")

                t1, t2 = resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["1cm"], resize_ruler.RULER_TARGET_PHYSICAL_WIDTHS_CM["2cm"]
                chosen_ruler_path = RULER_TEMPLATE_1CM_PATH if obj_w_cm < t1 else (RULER_TEMPLATE_2CM_PATH if obj_w_cm < t2 else RULER_TEMPLATE_5CM_PATH)
                print(f"    Selected ruler template: {os.path.basename(chosen_ruler_path)}")

                ruler_out_dir = os.path.dirname(original_filepath)
                ruler_base = output_base_name
                resized_ruler_name = (ruler_base.replace(resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH, resize_ruler.OUTPUT_FILENAME_SUFFIX_REPLACE, 1)
                                     if resize_ruler.OUTPUT_FILENAME_SUFFIX_SEARCH in ruler_base else ruler_base)
                ruler_out_fname = resized_ruler_name + resize_ruler.OUTPUT_FILE_EXTENSION
                resized_ruler_fp = os.path.join(ruler_out_dir, ruler_out_fname)

                resize_ruler.resize_and_save_ruler(px_cm, chosen_ruler_path, original_filepath)
                if not os.path.exists(resized_ruler_fp): raise FileNotFoundError(f"Resized ruler file not found: {resized_ruler_fp}")
                print(f"    Ruler resized: {os.path.basename(resized_ruler_fp)}")

                print("  Step 4: Merging object and ruler...")
                merge_object_and_ruler(extracted_obj_fp, resized_ruler_fp, output_base_name)
                print(f"    Merging successful for {output_base_name}_merged.jpg")
                success_count += 1
            except Exception as e:
                print(f"  ERROR processing {os.path.basename(original_filepath)}: {e}")
                error_count += 1
            finally:
                if is_temp_tiff_from_cr2 and os.path.exists(current_processing_filepath):
                    try: os.remove(current_processing_filepath); print(f"  Cleaned up temporary TIFF: {os.path.basename(current_processing_filepath)}")
                    except Exception as clean_e: print(f"  Warning: Could not clean up temp TIFF: {clean_e}")
                print("-" * 50)

        print("\n--- Processing Complete ---")
        print(f"RAW files converted: {cr2_conv}")
        print(f"Images fully processed successfully: {success_count}")
        print(f"Images with errors: {error_count}")
        print("---------------------------\n")

class TextRedirector(object):
    def __init__(self, widget, tag="stdout"): self.widget, self.tag = widget, tag
    def write(self, str_): self.widget.configure(state=tk.NORMAL); self.widget.insert(tk.END, str_, (self.tag,)); self.widget.see(tk.END); self.widget.configure(state=tk.DISABLED)
    def flush(self): pass

if __name__ == "__main__":
    modules_to_check = {
        "resize_ruler": resize_ruler, "ruler_detector": ruler_detector,
        "image_merger.merge_object_and_ruler": merge_object_and_ruler,
        "object_extractor.extract_and_save_object": extract_and_save_object,
        "raw_processor.convert_cr2_to_tiff": convert_cr2_to_tiff
    }
    missing = [name for name, mod in modules_to_check.items() if mod is None]
    if missing:
        msg = "FATAL: Critical components missing:\n" + "\n".join(missing) + \
              "\nEnsure all .py files are in the same directory/Python path and error-free."
        try: root_chk = tk.Tk(); root_chk.withdraw(); messagebox.showerror("Startup Error", msg)
        except tk.TclError: print(msg)
        sys.exit(1)
    
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
