\
import os
import json

# Moved from gui_app.py
CONFIG_FILENAME_ONLY = "gui_config.json"
# get_persistent_config_dir_path will be imported from gui_utils in gui_app.py
# For now, to make this module self-contained for definition, we might need a placeholder
# or assume it's passed in, or that this module is only called by gui_app.py which handles the path.
# Let's assume functions here will receive the full config_file_path.

DEFAULT_PHOTOGRAPHER = "Ivor Kerslake" # Also from gui_app.py

def save_config(config_file_path, config_data):
    """Saves the configuration data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        with open(config_file_path, "w") as f:
            json.dump(config_data, f, indent=4) # Added indent for readability
        print(f"Config saved: {config_file_path}")
        return True
    except Exception as e:
        print(f"Error saving config to {config_file_path}: {e}")
        return False

def load_config(config_file_path):
    """Loads configuration data from a JSON file."""
    config_data = {}
    try:
        if os.path.exists(config_file_path):
            with open(config_file_path, "r") as f:
                config_data = json.load(f)
            print(f"Config loaded: {config_file_path}")
    except Exception as e:
        print(f"Warn: Could not load config from {config_file_path}: {e}")
        # Return empty or default if load fails, calling function will handle defaults
    return config_data

def get_default_config_values():
    """Returns a dictionary of default configuration values."""
    return {
        "last_folder": "",
        "last_ruler_position": "top",
        "last_photographer": DEFAULT_PHOTOGRAPHER,
        "last_add_logo": False,
        "last_logo_path": "",
        "last_museum": "British Museum"
    }
