import os
import sys

# --- Start of sys.path modification ---
# Ensure lib_directory is added to sys.path absolutely first for this script's context
script_directory = os.path.dirname(os.path.abspath(__file__))
lib_directory = os.path.join(script_directory, "lib")
if lib_directory not in sys.path:
    sys.path.insert(0, lib_directory) # Try insert at the beginning again
# --- End of sys.path modification ---

# Imports from our 'lib' directory - these MUST be resolvable now
try:
    from gui_utils import resource_path, get_persistent_config_dir_path, TextRedirector
    from gui_config_manager import (
        save_config as save_app_config, 
        load_config as load_app_config, 
        get_default_config_values, 
        DEFAULT_PHOTOGRAPHER
    )
    from gui_workflow_runner import run_complete_image_processing_workflow
    import resize_ruler 
    import ruler_detector
    from stitch_images_adapter import process_tablet_subfolder
    from object_extractor import extract_and_save_center_object, extract_specific_contour_to_image_array, DEFAULT_EXTRACTED_OBJECT_FILENAME_SUFFIX as OBJECT_ARTIFACT_SUFFIX
    from remove_background import (
        create_foreground_mask_from_background as create_foreground_mask,
        select_contour_closest_to_image_center,
        select_ruler_like_contour_from_list as select_ruler_like_contour
    )
    from raw_processor import convert_raw_image_to_tiff
    from put_images_in_subfolders import group_and_move_files_to_subfolders as organize_to_subfolders
except ImportError as e:
    # This error handling for imports from lib is crucial
    # Determine the expected absolute path to lib for a more informative error message
    expected_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    # Attempt to show a Tkinter error box, but have a print fallback if Tkinter itself fails.
    try:
        root_err_tk = tk.Tk() # This line might fail if tk is not yet imported or if display is not available
        root_err_tk.withdraw()
        messagebox.showerror("Startup Error", f"Critical library module import failed: {e}\nAttempted to load from 'lib' package. Ensure 'lib' directory exists at '{expected_lib_path}' and contains all required modules and an __init__.py file.")
    except Exception: # Broad except because Tkinter might not be initializable
        print(f"ERROR: Critical library module import failed: {e}\nAttempted to load from 'lib' package. Ensure 'lib' directory exists at '{expected_lib_path}' and contains all required modules and an __init__.py file.")
    sys.exit(1)

# Standard library imports (can come after lib imports if there are no further dependencies from lib back to them at import time)
import cv2
import threading
import json
from tkinter import filedialog, messagebox, ttk # ttk should be here
import tkinter as tk # tk is used in the except block above, so it's fine here or earlier
from PIL import Image, ImageTk, ImageDraw

# Constants not related to save/load config can remain or be managed elsewhere if appropriate
ASSETS_SUBFOLDER = "assets"
ICON_FILENAME_ONLY = "eBL_logo.png"
RULER_1CM_FILENAME_ONLY = "BM_1cm_scale.tif"
RULER_2CM_FILENAME_ONLY = "BM_2cm_scale.tif"
RULER_5CM_FILENAME_ONLY = "BM_5cm_scale.tif"
ICON_FILE_ASSET_PATH = resource_path(
    os.path.join(ASSETS_SUBFOLDER, ICON_FILENAME_ONLY))
RULER_TEMPLATE_1CM_PATH_ASSET = resource_path(
    os.path.join(ASSETS_SUBFOLDER, RULER_1CM_FILENAME_ONLY))
RULER_TEMPLATE_2CM_PATH_ASSET = resource_path(
    os.path.join(ASSETS_SUBFOLDER, RULER_2CM_FILENAME_ONLY))
RULER_TEMPLATE_5CM_PATH_ASSET = resource_path(
    os.path.join(ASSETS_SUBFOLDER, RULER_5CM_FILENAME_ONLY))
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')
RAW_IMAGE_EXTENSION = '.cr2'
# DEFAULT_PHOTOGRAPHER is now imported
TEMP_EXTRACTED_RULER_FOR_SCALING_FILENAME = "temp_isolated_ruler.tif"

# CORRECTED: Ensure this matches the numeric mapping in stitch_config.STITCH_VIEW_PATTERNS_CONFIG
# stitch_config.py has: top: _03, bottom: _04
GUI_VIEW_ORIGINAL_SUFFIX_PATTERNS = {
    "obverse": "_01.", 
    "reverse": "_02.", 
    "top": "_03.",      # Was _04., changed to match stitch_config for consistency
    "bottom": "_04.",   # Was _03., changed to match stitch_config for consistency
    "left": "_05.",      # stitch_config has _05 for left
    "right": "_06."     # stitch_config has _06 for right
}

class ImageProcessorApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("eBL Photo Stitcher v0.2")
        self.root.geometry("600x780")
        
        self.config_file_path = os.path.join(get_persistent_config_dir_path(), "gui_config.json")

        self.input_folder_var = tk.StringVar()
        self.ruler_position_var = tk.StringVar() 
        self.photographer_var = tk.StringVar() 
        self.add_logo_var = tk.BooleanVar() 
        self.logo_path_var = tk.StringVar()
        self.museum_var = tk.StringVar() 
        self.progress_var = tk.DoubleVar(value=0.0)
        
        self._setup_icon()
        self._setup_styles()
        self._create_widgets()
        self.load_config() 
        self.on_museum_changed(None) 

    def _setup_icon(self):
        try:
            if os.path.exists(ICON_FILE_ASSET_PATH):
                self.root.iconphoto(False, tk.PhotoImage(
                    file=ICON_FILE_ASSET_PATH))
        except:
            pass

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10))
        style.configure("TFrame", padding=10)

    def _create_widgets(self):
        mf = ttk.Frame(self.root, padding="10")
        mf.pack(expand=True, fill=tk.BOTH)
        self._create_folder_selection_ui(mf)
        self._create_photographer_ui(mf)
        self._create_ruler_pos_ui(mf)
        self._create_logo_options_ui(mf)
        self._create_process_button_ui(mf)
        self._create_progress_bar_ui(mf)
        self._create_log_area_ui(mf)

    def _create_folder_selection_ui(self, p):
        f = ttk.LabelFrame(p, text="Input Folder", padding="10")
        f.pack(fill=tk.X, pady=5)
        ttk.Label(f, text="Image Source Folder:").pack(
            side=tk.LEFT, padx=(0, 5))
        self.fe = ttk.Entry(f, textvariable=self.input_folder_var, width=50)
        self.fe.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(f, text="Browse...",
                   command=self.browse_folder).pack(side=tk.LEFT)

    def _create_photographer_ui(self, p):
        f = ttk.LabelFrame(p, text="Metadata", padding="10")
        f.pack(fill=tk.X, pady=5)
        ttk.Label(f, text="Photographer:").pack(side=tk.LEFT, padx=(0, 5))
        self.pe = ttk.Entry(f, textvariable=self.photographer_var, width=40)
        self.pe.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def _create_ruler_pos_ui(self, p):
        f = ttk.LabelFrame(p, text="Ruler Options", padding="10")
        f.pack(fill=tk.X, pady=5)

        # Museum selection row
        museum_frame = ttk.Frame(f)
        museum_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(museum_frame, text="Museum:").pack(side=tk.LEFT, padx=(0, 5))
        self.museum_var = tk.StringVar(value="British Museum")
        self.museum_combo = ttk.Combobox(
            museum_frame, textvariable=self.museum_var, width=20,
            values=["British Museum", "Iraq Museum",
                    "eBL Ruler (CBS)", "Non-eBL Ruler (VAM)"]
        )
        self.museum_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.museum_combo.bind("<<ComboboxSelected>>", self.on_museum_changed)

        # Ruler position section
        ttk.Label(f, text="Click ruler location:").pack(anchor=tk.W)
        self.rcs, self.rcp, self.rbt = 120, 10, 25
        self.rc = tk.Canvas(f, width=self.rcs, height=self.rcs,
                            bg="lightgray", relief=tk.SUNKEN, borderwidth=1)
        self.rc.pack(pady=5)
        self.draw_ruler_selector() # Initial draw
        self.rc.bind("<Button-1>", self.on_ruler_canvas_click)
    
    def on_museum_changed(self, event):
        museum_selection = self.museum_var.get()
        print(f"Museum selected: {museum_selection}")
        if museum_selection == "Iraq Museum":
            self.ruler_position_var.set("bottom-left-fixed") 
        else:
            # If switching away from Iraq Museum and it was on the fixed pos, revert to a default like "top"
            if self.ruler_position_var.get() == "bottom-left-fixed":
                self.ruler_position_var.set("top")
        self.draw_ruler_selector() 
        if event: # Only save config if it's a user interaction, not initial setup
            self.save_config()

    def _create_logo_options_ui(self, p):
        f = ttk.LabelFrame(p, text="Logo Options", padding="10")
        f.pack(fill=tk.X, pady=5)
        self.alc = ttk.Checkbutton(
            f, text="Add Logo", variable=self.add_logo_var, command=self.toggle_logo_path_entry)
        self.alc.pack(anchor=tk.W)
        sf = ttk.Frame(f)
        sf.pack(fill=tk.X, pady=(0, 5), padx=(20, 0))
        ttk.Label(sf, text="Logo File:").pack(side=tk.LEFT, padx=(0, 5))
        self.lpe = ttk.Entry(
            sf, textvariable=self.logo_path_var, width=40, state=tk.DISABLED)
        self.lpe.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.blb = ttk.Button(sf, text="Browse...",
                              command=self.browse_logo_file, state=tk.DISABLED)
        self.blb.pack(side=tk.LEFT)

    def _create_process_button_ui(self, p):
        self.prb = ttk.Button(p, text="Start Processing",
                              command=self.start_processing_thread)
        self.prb.pack(pady=(15, 5), ipadx=10, ipady=5)

    def _create_progress_bar_ui(self, p):
        pf = ttk.Frame(p, padding="0 0 0 5")
        pf.pack(fill=tk.X)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            pf, orient="horizontal", length=100, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, expand=True)

    def _create_log_area_ui(self, p):
        f = ttk.LabelFrame(p, text="Log", padding="10")
        f.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lt = tk.Text(f, height=15, wrap=tk.WORD,
                          relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED)
        self.lt.pack(fill=tk.BOTH, expand=True)
        sys.stdout = TextRedirector(self.lt, "stdout")
        sys.stderr = TextRedirector(self.lt, "stderr")

    def toggle_logo_path_entry(self): state = tk.NORMAL if self.add_logo_var.get(
    ) else tk.DISABLED; self.lpe.config(state=state); self.blb.config(state=state)

    def browse_logo_file(self):
        init_dir = os.path.dirname(self.logo_path_var.get(
        )) if self.logo_path_var.get() else os.path.expanduser("~/Pictures")
        if not os.path.isdir(init_dir):
            init_dir = os.path.expanduser("~")
        fsel = filedialog.askopenfilename(
            initialdir=init_dir, title="Select Logo", filetypes=(("PNG", "*.png"), ("All", "*.*")))
        if fsel:
            self.logo_path_var.set(fsel)

    def draw_ruler_selector(self):
        self.rc.delete("all")
        s = self.rcs # canvas_size
        p = self.rcp # padding
        bt = self.rbt # band_thickness
        ox1, oy1, ox2, oy2 = p + bt, p + bt, s - p - bt, s - p - bt # Object box corners
        
        self.rc.create_rectangle(
            ox1, oy1, ox2, oy2, outline="gray", fill="whitesmoke", dash=(2, 2))
        self.rc.create_text(s / 2, s / 2, text="Object",
                            font=('Helvetica', 9, 'italic'), fill="gray")
        
        current_museum = self.museum_var.get()
        is_iraq_museum = (current_museum == "Iraq Museum")

        sp = self.ruler_position_var.get() # selected_position
        active_fill_color = "lightblue"
        selected_fill_color = "blue"
        disabled_fill_color = "#e0e0e0"
        iraq_fixed_fill_color = selected_fill_color 
        text_color = "black"
        nd = 4 # number of divisions for ticks
        lh, lv = ox2 - ox1, oy2 - oy1 # object box width and height

        top_fill = disabled_fill_color if is_iraq_museum else (selected_fill_color if sp == "top" else active_fill_color)
        bottom_fill = disabled_fill_color if is_iraq_museum else (selected_fill_color if sp == "bottom" else active_fill_color)
        left_fill = disabled_fill_color if is_iraq_museum else (selected_fill_color if sp == "left" else active_fill_color)
        right_fill = disabled_fill_color if is_iraq_museum else (selected_fill_color if sp == "right" else active_fill_color)

        # Top band
        self.rc.create_rectangle(ox1, p, ox2, p + bt, fill=top_fill, outline=text_color, tags="top_zone")
        if not is_iraq_museum:
            for i in range(nd + 1):
                x = ox1 + i * (lh / nd)
                self.rc.create_line(x, p, x, p + bt * .6, fill=text_color)
        
        # Bottom band
        self.rc.create_rectangle(ox1, oy2, ox2, oy2 + bt, fill=bottom_fill, outline=text_color, tags="bottom_zone")
        if not is_iraq_museum:
            for i in range(nd + 1):
                x = ox1 + i * (lh / nd)
                self.rc.create_line(x, oy2, x, oy2 + bt * .6, fill=text_color)

        # Left band
        self.rc.create_rectangle(p, oy1, p + bt, oy2, fill=left_fill, outline=text_color, tags="left_zone")
        if not is_iraq_museum:
            for i in range(nd + 1):
                y = oy1 + i * (lv / nd)
                self.rc.create_line(p, y, p + bt * .6, y, fill=text_color)

        # Right band
        self.rc.create_rectangle(ox2, oy1, ox2 + bt, oy2, fill=right_fill, outline=text_color, tags="right_zone")
        if not is_iraq_museum:
            for i in range(nd + 1):
                y = oy1 + i * (lv / nd)
                self.rc.create_line(ox2, y, ox2 + bt * .6, y, fill=text_color)

        if is_iraq_museum:
            # For Iraq Museum, draw a selected square in the bottom-left corner area
            # This square should fill the corner from the padding to the object box.
            cs_x1 = p # Outer padding edge on the left
            cs_y1 = oy2 # Top edge of the bottom band (aligned with object bottom)
            cs_x2 = p + bt # Inner edge of the left band (aligned with object left)
            cs_y2 = oy2 + bt # Bottom edge of the bottom band
            self.rc.create_rectangle(cs_x1, cs_y1, cs_x2, cs_y2, fill=iraq_fixed_fill_color, outline=text_color, tags="iraq_fixed_pos")
            # Optional: Add text to indicate it's fixed
            self.rc.create_text(p + bt/2, oy2 + bt/2, text="IM", font=('Helvetica', 7, 'bold'), fill="white")

    def on_ruler_canvas_click(self, event):
        current_museum = self.museum_var.get()
        if current_museum == "Iraq Museum":
            # Clicks are disabled for Iraq Museum as position is fixed
            print("Ruler position is fixed for Iraq Museum.")
            return 

        s, p, bt = self.rcs, self.rcp, self.rbt
        ox1, oy1, ox2, oy2 = p + bt, p + bt, s - p - bt, s - p - bt
        if ox1 <= event.x <= ox2 and p <= event.y < oy1:
            self.ruler_position_var.set("top")
        elif ox1 <= event.x <= ox2 and oy2 < event.y <= oy2 + bt:
            self.ruler_position_var.set("bottom")
        elif p <= event.x < ox1 and oy1 <= event.y <= oy2:
            self.ruler_position_var.set("left")
        elif ox2 < event.x <= ox2 + bt and oy1 <= event.y <= oy2:
            self.ruler_position_var.set("right")
        else:
            return
        self.draw_ruler_selector()
        print(f"Ruler pos: {self.ruler_position_var.get()}")

    def browse_folder(self):
        init_dir = self.input_folder_var.get()
        if not init_dir or not os.path.isdir(init_dir):
            try:
                sdir = os.path.dirname(os.path.abspath(sys.argv[0]))
                init_dir = sdir
            except:
                init_dir = os.path.expanduser("~")
        fsel = filedialog.askdirectory(initialdir=init_dir)
        if fsel:
            self.input_folder_var.set(fsel)

    def save_config(self):
        cfg_data = {
            "last_folder": self.input_folder_var.get(), 
            "last_ruler_position": self.ruler_position_var.get(),
            "last_photographer": self.photographer_var.get(), 
            "last_add_logo": self.add_logo_var.get(),
            "last_logo_path": self.logo_path_var.get(), 
            "last_museum": self.museum_var.get()
        }
        save_app_config(self.config_file_path, cfg_data)

    def load_config(self):
        loaded_cfg = load_app_config(self.config_file_path)
        defaults = get_default_config_values()
        
        self.input_folder_var.set(loaded_cfg.get("last_folder", defaults["last_folder"]))
        self.ruler_position_var.set(loaded_cfg.get("last_ruler_position", defaults["last_ruler_position"]))
        self.photographer_var.set(loaded_cfg.get("last_photographer", defaults["last_photographer"]))
        self.add_logo_var.set(loaded_cfg.get("last_add_logo", defaults["last_add_logo"]))
        self.logo_path_var.set(loaded_cfg.get("last_logo_path", defaults["last_logo_path"]))
        self.museum_var.set(loaded_cfg.get("last_museum", defaults["last_museum"]))
        
        self.toggle_logo_path_entry()

    def update_progress_bar(self, value): self.progress_var.set(
        value); self.root.update_idletasks()

    def processing_finished_ui_update(self):
        self.prb.config(state=tk.NORMAL)
        messagebox.showinfo("Processing Complete", "Workflow finished.")
        self.update_progress_bar(0)

    def start_processing_thread(self):
        fp = self.input_folder_var.get()
        rp = self.ruler_position_var.get()
        ph = self.photographer_var.get()
        al = self.add_logo_var.get()
        lp = self.logo_path_var.get()
        ms = self.museum_var.get()
        obm = "auto"        # Background mode is set to "auto" by default
        # The actual background detection logic is handled in gui_workflow_runner.py
        # based on the museum_selection parameter

        if not fp or not os.path.isdir(fp):
            messagebox.showerror("Error", "Select valid input folder.")
            return
        if al and (not lp or not os.path.isfile(lp)):
            messagebox.showerror(
                "Error", "Logo checked, but no valid logo file.")
            return
        self.save_config()
        self.lt.configure(state=tk.NORMAL)
        self.lt.delete('1.0', tk.END)
        self.lt.configure(state=tk.DISABLED)
        print(f"Starting processing with {ms} ruler...\n")
        self.prb.config(state=tk.DISABLED)
        self.update_progress_bar(0)

        threading.Thread(target=run_complete_image_processing_workflow,
                         args=(
                             fp,
                             rp,
                             ph,
                             obm,
                             al,
                             lp,
                             RAW_IMAGE_EXTENSION,
                             VALID_IMAGE_EXTENSIONS,
                             RULER_TEMPLATE_1CM_PATH_ASSET,
                             RULER_TEMPLATE_2CM_PATH_ASSET,
                             RULER_TEMPLATE_5CM_PATH_ASSET,
                             GUI_VIEW_ORIGINAL_SUFFIX_PATTERNS,
                             TEMP_EXTRACTED_RULER_FOR_SCALING_FILENAME,
                             OBJECT_ARTIFACT_SUFFIX,
                             self.update_progress_bar,
                             self.processing_finished_ui_update,
                             self.museum_var.get(),
                             self.root # ADDED: Pass the main app window as parent for dialogs
                         ),
                         daemon=True).start()


if __name__ == "__main__":
    modules_to_check = {
        "resize_ruler_module": resize_ruler,
        "ruler_detector_module": ruler_detector,
        "stitch_images.process_tablet_subfolder": process_tablet_subfolder if 'stitch_images' in sys.modules and hasattr(sys.modules['stitch_images'], 'process_tablet_subfolder') else None,
        "object_extractor.extract_and_save_center_object": extract_and_save_center_object if 'object_extractor' in sys.modules and hasattr(sys.modules['object_extractor'], 'extract_and_save_center_object') else None,
        "object_extractor.extract_specific_contour_to_image_array": extract_specific_contour_to_image_array if 'object_extractor' in sys.modules and hasattr(sys.modules['object_extractor'], 'extract_specific_contour_to_image_array') else None,
        # Check original name
        "remove_background.create_foreground_mask": create_foreground_mask if 'remove_background' in sys.modules and hasattr(sys.modules['remove_background'], 'create_foreground_mask_from_background') else None,
        "remove_background.select_contour_closest_to_image_center": select_contour_closest_to_image_center if 'remove_background' in sys.modules and hasattr(sys.modules['remove_background'], 'select_contour_closest_to_image_center') else None,
        # Check original name
        "remove_background.select_ruler_like_contour": select_ruler_like_contour if 'remove_background' in sys.modules and hasattr(sys.modules['remove_background'], 'select_ruler_like_contour_from_list') else None,
        "raw_processor.convert_raw_image_to_tiff": convert_raw_image_to_tiff if 'raw_processor' in sys.modules and hasattr(sys.modules['raw_processor'], 'convert_raw_image_to_tiff') else None,
        "put_images_in_subfolders.organize_files": organize_to_subfolders,  # This is an alias
        "gui_utils.resource_path": resource_path,  # From gui_utils
        "gui_utils.get_persistent_config_dir_path": get_persistent_config_dir_path,
        "gui_utils.TextRedirector_class": TextRedirector,
        "gui_workflow_runner.run_complete_image_processing_workflow": run_complete_image_processing_workflow if 'gui_workflow_runner' in sys.modules and hasattr(sys.modules['gui_workflow_runner'], 'run_complete_image_processing_workflow') else None
    }
    missing = [name for name, mod_or_func in modules_to_check.items()
               if mod_or_func is None]
    if missing:
        msg = "FATAL: Critical components missing:\n" + "\n".join(missing) + \
              "\nEnsure all .py files are in the same directory/Python path and error-free."
        try:
            root_chk = tk.Tk()
            root_chk.withdraw()
            messagebox.showerror("Startup Error", msg)
        except tk.TclError:
            print(msg)
        sys.exit(1)

    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
