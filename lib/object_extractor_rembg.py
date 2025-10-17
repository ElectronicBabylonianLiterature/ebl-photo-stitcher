import cv2
import numpy as np
import os
import sys
import shutil
import time
from rembg import remove
from PIL import Image, ImageOps
from object_extractor import DEFAULT_BACKGROUND_DETECTION_COLOR_TOLERANCE


def _download_with_progress(url, destination, max_retries=3):
    """Download a file with progress reporting and retry logic."""
    import requests
    from tqdm import tqdm
    try:
        import signal
        has_signal = True
    except ImportError:
        has_signal = False
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Download timed out")
    
    print(f"  Downloading U2NET model from {url}")
    print(f"  This is a large file (~176MB) and may take several minutes.")
    print(f"  If download hangs, it will timeout after 10 minutes and retry up to {max_retries} times.")

    for attempt in range(max_retries):
        if attempt > 0:
            print(f"  Retry attempt {attempt + 1}/{max_retries}...")
        
        temp_destination = destination + ".download"
        
        try:
            # Set up timeout signal (Unix/Linux/Mac only)
            if has_signal and hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(600)  # 10 minute timeout
            
            # Use shorter initial timeout, but allow for connection retries
            response = requests.get(url, stream=True, timeout=(30, 60))
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            
            downloaded_size = 0
            last_progress_time = time.time()

            with open(temp_destination, 'wb') as f, tqdm(
                desc="  Downloading",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(chunk_size=64 * 1024):  # Smaller chunks
                    if data:
                        size = f.write(data)
                        bar.update(size)
                        downloaded_size += size
                        
                        # Check for stalled download
                        current_time = time.time()
                        if current_time - last_progress_time > 120:  # 2 minutes without progress
                            raise TimeoutError("Download stalled - no progress for 2 minutes")
                        last_progress_time = current_time

            # Disable timeout signal
            if has_signal and hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

            # Verify file size
            if total_size > 0 and downloaded_size < total_size * 0.95:
                raise RuntimeError(f"Download incomplete: {downloaded_size}/{total_size} bytes")

            shutil.move(temp_destination, destination)
            print(f"  Download complete! Model saved to {destination}")
            return True

        except (requests.exceptions.RequestException, TimeoutError, RuntimeError) as e:
            print(f"  Download attempt {attempt + 1} failed: {e}")
            
            # Clean up partial download
            if os.path.exists(temp_destination):
                os.remove(temp_destination)
            
            # Disable timeout signal
            if has_signal and hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"  All {max_retries} download attempts failed.")
                return False

        except Exception as e:
            print(f"  Unexpected error during download: {e}")
            
            # Clean up and disable timeout
            if os.path.exists(temp_destination):
                os.remove(temp_destination)
            if has_signal and hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            return False

    return False


def _validate_model_file(model_path):
    """Validate that the model file is complete and correct."""
    try:
        if not os.path.exists(model_path):
            return False
        
        # Check file size (u2net.onnx should be approximately 176MB)
        file_size = os.path.getsize(model_path)
        expected_size = 176681672  # Exact size of u2net.onnx
        size_tolerance = 1024 * 1024  # 1MB tolerance
        
        if abs(file_size - expected_size) > size_tolerance:
            print(f"  Warning: Model file size ({file_size} bytes) doesn't match expected size ({expected_size} bytes)")
            print("  The file may be corrupted or incomplete.")
            return False
        
        # Try to read the first few bytes to make sure it's not corrupted
        with open(model_path, 'rb') as f:
            header = f.read(16)
            if len(header) < 16:
                print("  Warning: Model file appears to be too small or corrupted.")
                return False
        
        return True
        
    except Exception as e:
        print(f"  Error validating model file: {e}")
        return False


def _ensure_local_model():
    """Ensures the U2NET model exists in the expected location."""
    user_home = os.path.expanduser("~")
    model_dir = os.path.join(user_home, ".u2net")
    model_path = os.path.join(model_dir, "u2net.onnx")

    # Check if model already exists and is valid
    if _validate_model_file(model_path):
        return True
    elif os.path.exists(model_path):
        print("  Existing model file appears to be corrupted. Re-downloading...")
        os.remove(model_path)

    os.makedirs(model_dir, exist_ok=True)

    # Get the base directory for assets
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    assets_model_path = os.path.join(base_dir, "assets", "u2net.onnx")

    # Try to copy from assets first
    if _validate_model_file(assets_model_path):
        print(f"  Copying U2NET model from local assets")
        try:
            shutil.copy2(assets_model_path, model_path)
            if _validate_model_file(model_path):
                return True
            else:
                print("  Error: Copied model file failed validation")
        except Exception as e:
            print(f"  Error copying model: {e}")

    # Download from internet as fallback
    url = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
    
    print("\n" + "="*60)
    print("  U2NET AI Model Required")
    print("="*60)
    print("  The AI-powered object extraction requires downloading")
    print("  the U2NET model (~176MB) from the internet.")
    print("\n  This download may take several minutes depending on")
    print("  your internet connection speed.")
    print("="*60)
    
    # Give user a chance to cancel if they prefer manual download
    try:
        # Check if we're running in an interactive environment
        if sys.stdin.isatty():
            user_input = input("\n  Continue with automatic download? (y/n) [y]: ").strip().lower()
            if user_input in ['n', 'no']:
                print("\n  Skipping automatic download.")
                success = False
            else:
                success = _download_with_progress(url, model_path)
        else:
            # Non-interactive environment (GUI), proceed with download
            print("\n  Proceeding with automatic download...")
            success = _download_with_progress(url, model_path)
    except (KeyboardInterrupt, EOFError):
        print("\n  Download cancelled by user.")
        success = False

    if success and _validate_model_file(model_path):
        return True

    if not success:
        print("\n" + "="*80)
        print("  ERROR: Could not download the U2NET model automatically.")
        print("  This model is required for AI-powered object extraction.")
        print("\n  MANUAL DOWNLOAD INSTRUCTIONS:")
        print("  1. Open your web browser and go to:")
        print("     https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx")
        print("  2. Download the u2net.onnx file (approximately 176MB)")
        print("  3. Save it to one of these locations:")
        print(f"     - Primary location: {model_path}")
        print(f"     - Alternative: {assets_model_path}")
        print("\n  TROUBLESHOOTING:")
        print("  - If the download is slow, try using a download manager")
        print("  - If the GitHub link doesn't work, search for 'rembg u2net.onnx' online")
        print("  - Make sure you have a stable internet connection")
        print("  - The file should be exactly 176,681,672 bytes")
        print("\n  After downloading, restart the application and try again.")
        print("="*80 + "\n")

    return success


def extract_and_save_center_object(
    input_image_filepath,
    source_background_detection_mode="auto",
    output_image_background_color=(0, 0, 0),
    feather_radius_px=10,
    output_filename_suffix="_object.tif",
    min_object_area_as_image_fraction=0.01,
    object_contour_smoothing_kernel_size=3,
    museum_selection=None
):
    """
    Extract the object closest to the center among the two largest objects.

    Args:
        input_image_filepath: Path to the input image
        output_image_background_color: BGR tuple for background color (OpenCV format)
        output_filename_suffix: Suffix for the output filename

    Returns:
        Tuple of (output_filepath, dummy_contour) for compatibility
    """
    print(
        f"  Extracting center object from: {os.path.basename(input_image_filepath)} using rembg")
    start_time = time.time()

    if not isinstance(output_image_background_color, (tuple, list)):
        print(f"    Warning: output_image_background_color is not a tuple/list: {type(output_image_background_color)}, using default (0,0,0)")
        output_image_background_color = (0, 0, 0)

    if not _ensure_local_model():
        raise RuntimeError(
            "U2NET model is required but could not be downloaded or found.")

    try:
        if input_image_filepath.lower().endswith(('.tif', '.tiff')):
            img_bgr = cv2.imread(input_image_filepath, cv2.IMREAD_COLOR)
            if img_bgr is None:
                raise ValueError(f"OpenCV could not load TIFF file: {input_image_filepath}")
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            input_img = Image.fromarray(img_rgb)
        else:
            input_img = Image.open(input_image_filepath)
            input_img.load()
    except Exception as e:
        raise FileNotFoundError(
            f"Could not load image for object extraction: {input_image_filepath} - {e}")

    output_img = remove(input_img)
    
    try:
        input_img.close()
    except Exception:
        pass

    alpha = np.array(output_img.getchannel('A'))
    custom_alpha_tolerance = DEFAULT_BACKGROUND_DETECTION_COLOR_TOLERANCE * 2

    binary_mask = (alpha > custom_alpha_tolerance).astype(np.uint8) * 255

    kernel = np.ones((3, 3), np.uint8)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary_mask, connectivity=8)

    if num_labels <= 1:
        print("    Warning: No objects detected in the image!")
        bbox = (0, 0, output_img.width, output_img.height)

        selected_object_mask = binary_mask
    else:

        center_x = output_img.width / 2
        center_y = output_img.height / 2

        obj_data = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            cx, cy = centroids[i]

            distance_to_center = np.sqrt((cx - center_x)**2 + (cy - center_y)**2)
            obj_data.append((i, area, distance_to_center))

        obj_data.sort(key=lambda x: x[1], reverse=True)

        largest_objects = obj_data[:min(2, len(obj_data))]
        print(f"    Found {num_labels-1} separate objects")

        if len(largest_objects) == 1:

            selected_label = largest_objects[0][0]
            print(f"    Only one object found - using it")
        else:

            if largest_objects[0][2] <= largest_objects[1][2]:

                selected_label = largest_objects[0][0]
                print(f"    Two largest objects found - selecting the one closer to center")
            else:

                selected_label = largest_objects[1][0]
                print(f"    Two largest objects found - selecting the one closer to center")

        selected_object_mask = np.zeros_like(binary_mask)
        selected_object_mask[labels == selected_label] = 255

        y_indices, x_indices = np.where(selected_object_mask > 0)
        if len(y_indices) == 0:
            print("    Warning: No valid objects found!")
            bbox = (0, 0, output_img.width, output_img.height)
        else:
            x_min, x_max = np.min(x_indices), np.max(x_indices)
            y_min, y_max = np.min(y_indices), np.max(y_indices)

            padding = 10
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(output_img.width, x_max + padding)
            y_max = min(output_img.height, y_max + padding)

            bbox = (x_min, y_min, x_max, y_max)

    selected_mask_pil = Image.fromarray(selected_object_mask)

    filtered_output = Image.new('RGBA', output_img.size, (0, 0, 0, 0))
    filtered_output.paste(output_img, (0, 0), selected_mask_pil)

    cropped_img = filtered_output.crop(bbox)

    if not isinstance(output_image_background_color, (tuple, list)) or len(output_image_background_color) != 3:
        output_image_background_color = (0, 0, 0)
    
    bg_color_rgb = (int(output_image_background_color[2]),
                    int(output_image_background_color[1]),
                    int(output_image_background_color[0]))

    bg_img = Image.new('RGB', cropped_img.size, bg_color_rgb)

    bg_img.paste(cropped_img, (0, 0), cropped_img)

    base_filepath, _ = os.path.splitext(input_image_filepath)
    output_image_filepath = f"{base_filepath}{output_filename_suffix}"

    try:
        file_ext = os.path.splitext(output_image_filepath)[1].lower()
        if file_ext in ['.tif', '.tiff']:
            bg_img.save(output_image_filepath, format='TIFF')
        elif file_ext in ['.jpg', '.jpeg']:
            bg_img.save(output_image_filepath, format='JPEG')
        elif file_ext == '.png':
            bg_img.save(output_image_filepath, format='PNG')
        else:
            bg_img.save(output_image_filepath)
            
        elapsed = time.time() - start_time
        print(
            f"    Successfully saved extracted artifact: {output_image_filepath} (took {elapsed:.2f}s)")

        dummy_contour = np.array(
            [[[0, 0]], [[0, 1]], [[1, 1]], [[1, 0]]], dtype=np.int32)
        
        try:
            output_img.close()
            selected_mask_pil.close()
            filtered_output.close()
            cropped_img.close()
            bg_img.close()
        except Exception:
            pass
        
        return output_image_filepath, dummy_contour
    except Exception as e:
        try:
            output_img.close()
        except Exception:
            pass
        raise IOError(
            f"Error saving extracted artifact to {output_image_filepath}: {e}")
