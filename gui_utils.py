import os
import sys
import tkinter as tk

APP_NAME_FOR_CONFIG = "eBLImageProcessor" 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    return os.path.join(base_path, relative_path)

def get_persistent_config_dir_path():
    home_dir = os.path.expanduser("~")
    if sys.platform == "win32":
        app_data_env = os.getenv("APPDATA", os.path.join(home_dir, "AppData", "Roaming"))
    elif sys.platform == "darwin":
        app_data_env = os.path.join(home_dir, "Library", "Application Support")
    else: 
        app_data_env = os.getenv("XDG_CONFIG_HOME", os.path.join(home_dir, ".config"))
    
    config_directory = os.path.join(app_data_env, APP_NAME_FOR_CONFIG)
    
    if not os.path.exists(config_directory):
        try:
            os.makedirs(config_directory, exist_ok=True)
        except OSError: 
            print(f"Warning: Could not create config directory {config_directory}.")
            if getattr(sys, 'frozen', False):
                 return os.path.dirname(sys.executable)
            return os.path.abspath(os.path.dirname(sys.argv[0]))
    return config_directory

class TextRedirector:
    def __init__(self, text_widget, tag_name="stdout"):
        self.widget = text_widget
        self.tag = tag_name

    def write(self, string_to_write):
        self.widget.configure(state=tk.NORMAL)
        self.widget.insert(tk.END, string_to_write, (self.tag,))
        self.widget.see(tk.END)
        self.widget.configure(state=tk.DISABLED)
        self.widget.update_idletasks() 

    def flush(self):
        pass
