import cv2
import numpy as np
import os

PADDING_FACTOR = 0.10
DEFAULT_BACKGROUND_COLOR_BGR = (0, 0, 0)


def merge_object_and_ruler(
    extracted_object_path,
    scaled_ruler_path,
    output_base_name,

    background_color=DEFAULT_BACKGROUND_COLOR_BGR,
    output_suffix="_merged.jpg",
    output_jpeg_quality=95
):
    print(
        f"  Merging Extracted Object '{os.path.basename(extracted_object_path)}' and Scaled Ruler '{os.path.basename(scaled_ruler_path)}'")

    try:

        img_object = cv2.imread(extracted_object_path)
        if img_object is None:
            raise ValueError(
                f"Failed to load extracted object image: {extracted_object_path}")
        if len(img_object.shape) == 2:
            img_object = cv2.cvtColor(img_object, cv2.COLOR_GRAY2BGR)
        elif len(img_object.shape) == 3 and img_object.shape[2] == 4:
            img_object = cv2.cvtColor(img_object, cv2.COLOR_BGRA2BGR)
        object_height_px, object_width_px = img_object.shape[:2]
        print(f"    Object image loaded: {object_width_px}x{object_height_px}")

        img_ruler = cv2.imread(scaled_ruler_path, cv2.IMREAD_UNCHANGED)
        if img_ruler is None:
            raise ValueError(f"Failed to load scaled ruler image: {scaled_ruler_path}")
        ruler_height_px, ruler_width_px = img_ruler.shape[:2]
        ruler_channels = img_ruler.shape[2] if len(img_ruler.shape) > 2 else 1
        print(
            f"    Scaled ruler loaded: {ruler_width_px}x{ruler_height_px}, Channels: {ruler_channels}")

        padding_px = int(round(ruler_height_px * PADDING_FACTOR))
        print(
            f"    Calculated padding: {padding_px}px ({PADDING_FACTOR*100:.0f}% of ruler height)")

        canvas_width_px = max(object_width_px, ruler_width_px)
        canvas_height_px = object_height_px + padding_px + ruler_height_px
        print(f"    Canvas dimensions: {canvas_width_px}x{canvas_height_px}")

        canvas = np.full((canvas_height_px, canvas_width_px, 3),
                         background_color, dtype=np.uint8)

        object_start_x = (canvas_width_px - object_width_px) // 2
        object_start_y = 0
        ruler_start_x = (canvas_width_px - ruler_width_px) // 2
        ruler_start_y = object_height_px + padding_px

        canvas[object_start_y: object_start_y + object_height_px,
               object_start_x: object_start_x + object_width_px] = img_object

        roi_height = min(ruler_height_px, canvas_height_px - ruler_start_y)
        roi_width = min(ruler_width_px, canvas_width_px - ruler_start_x)

        if roi_height <= 0 or roi_width <= 0:
            print("    Warning: Calculated ruler ROI is invalid. Skipping ruler paste.")
        else:
            ruler_target_roi = canvas[ruler_start_y: ruler_start_y
                                      + roi_height, ruler_start_x: ruler_start_x + roi_width]
            img_ruler_cropped = img_ruler[0:roi_height, 0:roi_width]

            if ruler_channels == 4:
                print("    Scaled ruler has alpha channel, performing alpha blending.")
                alpha_channel = img_ruler_cropped[:, :, 3] / 255.0
                alpha_mask_3channel = cv2.merge(
                    [alpha_channel, alpha_channel, alpha_channel])
                bgr_ruler = img_ruler_cropped[:, :, :3]
                blended_roi = cv2.convertScaleAbs(
                    bgr_ruler * alpha_mask_3channel + ruler_target_roi * (1.0 - alpha_mask_3channel))
                canvas[ruler_start_y: ruler_start_y + roi_height,
                       ruler_start_x: ruler_start_x + roi_width] = blended_roi
            elif ruler_channels == 3:
                print("    Scaled ruler is BGR, direct pasting.")
                canvas[ruler_start_y: ruler_start_y + roi_height,
                       ruler_start_x: ruler_start_x + roi_width] = img_ruler_cropped
            elif ruler_channels == 1:
                print("    Scaled ruler is Grayscale, converting to BGR for pasting.")
                bgr_ruler = cv2.cvtColor(img_ruler_cropped, cv2.COLOR_GRAY2BGR)
                canvas[ruler_start_y: ruler_start_y + roi_height,
                       ruler_start_x: ruler_start_x + roi_width] = bgr_ruler
            else:
                print(
                    f"    Warning: Unsupported number of channels ({ruler_channels}) in scaled ruler. Skipping paste.")

        output_dir = os.path.dirname(extracted_object_path)
        output_filename = f"{output_base_name}{output_suffix}"
        output_filepath = os.path.join(output_dir, output_filename)

        image_save_parameters = []
        if output_suffix.lower().endswith((".jpg", ".jpeg")):
            image_save_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), output_jpeg_quality]
        elif output_suffix.lower().endswith(".png"):
            pass

        success = cv2.imwrite(output_filepath, canvas, image_save_parameters)
        if not success:
            raise IOError(
                f"cv2.imwrite failed to save the merged image to {output_filepath}")
        print(f"    Successfully saved merged image: {output_filepath}")

    except Exception as e:
        print(
            f"  ERROR during merging process for {os.path.basename(extracted_object_path)}: {e}")
        raise e
