import cv2
import numpy as np
import os
import piexif
import datetime
import subprocess
import shutil
try:
    from image_utils import paste_image_onto_canvas, convert_to_bgr_if_needed, resize_image_maintain_aspect
except ImportError:
    print("ERROR: stitch_utils.py - Could not import from image_utils.py")
    def paste_image_onto_canvas(*args): raise ImportError("paste_image_onto_canvas missing")
    def convert_to_bgr_if_needed(img): return img
    def resize_image_maintain_aspect(*args): raise ImportError("resize_image_maintain_aspect missing")

OBJECT_FILE_SUFFIX = "_object.tif"
SCALED_RULER_FILE_SUFFIX = "_07.tif"

def find_processed_image_file(subfolder_path, base_name, view_specific_part, general_suffix):
    target_filename = f"{base_name}{view_specific_part}{general_suffix}"
    path = os.path.join(subfolder_path, target_filename)
    if os.path.exists(path): return path
    if view_specific_part.startswith("_0") and len(view_specific_part) == 3:
        alt_part = "_" + view_specific_part[2]
        alt_filename = f"{base_name}{alt_part}{general_suffix}"
        alt_path = os.path.join(subfolder_path, alt_filename)
        if os.path.exists(alt_path): return alt_path
    return None

def load_images_for_stitching(subfolder_path, base_name, view_file_patterns_config):
    images = {}
    all_files = os.listdir(subfolder_path)
    for key, pattern_part in view_file_patterns_config.items():
        fp = None
        if key == "ruler":
            fp = find_processed_image_file(subfolder_path, base_name, "", SCALED_RULER_FILE_SUFFIX)
        else:
            fp = find_processed_image_file(subfolder_path, base_name, pattern_part, OBJECT_FILE_SUFFIX)
        
        if fp:
            img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
            images[key] = convert_to_bgr_if_needed(img) if img is not None else None
            if images[key] is None: print(f"      Warn: Stitch - Failed to load {key} from {fp}")
        else: images[key] = None; print(f"      Warn: Stitch - {key} file not found.")
    return images

def resize_views_for_stitching(images_dict):
    obv = images_dict.get("obverse")
    if obv is None: raise ValueError("Obverse image required for relative resizing.")
    obv_h, obv_w = obv.shape[:2]
    resize_map = {"left":(0,obv_h),"right":(0,obv_h),"top":(1,obv_w),"bottom":(1,obv_w),"reverse":(1,obv_w)}
    for key, (axis, dim) in resize_map.items():
        if images_dict.get(key) is not None:
            images_dict[key] = resize_image_maintain_aspect(images_dict[key], dim, axis)
    return images_dict

def calculate_layout_and_canvas_size(images, gap_px, ruler_pad_px):
    def get_dim(k, ax): return images.get(k).shape[ax] if images.get(k) is not None else 0
    obv_h,obv_w=get_dim("obverse",0),get_dim("obverse",1)
    l_w,r_w=get_dim("left",1),get_dim("right",1)
    b_h,rev_h,t_h=get_dim("bottom",0),get_dim("reverse",0),get_dim("top",0)
    rul_h,rul_w=get_dim("ruler",0),get_dim("ruler",1)

    row1_w = l_w + (gap_px if l_w and obv_w else 0) + obv_w + (gap_px if r_w and obv_w else 0) + r_w
    canvas_w = max(row1_w,obv_w,get_dim("bottom",1),get_dim("reverse",1),get_dim("top",1),rul_w) + 200
    canvas_h = obv_h + sum(gap_px+h for h in [b_h,rev_h,t_h] if h>0) + (ruler_pad_px+rul_h if rul_h>0 else 0) + 200
    
    coords = {}; y_curr = 50
    start_x_row1 = (canvas_w - (l_w+(gap_px if l_w else 0)+obv_w+(gap_px if r_w else 0)+r_w))//2
    if images.get("left"): coords["left"]=(start_x_row1, y_curr)
    coords["obverse"]=(start_x_row1+(l_w+gap_px if l_w else 0), y_curr)
    if images.get("right"): coords["right"]=(coords["obverse"][0]+obv_w+gap_px, y_curr)
    y_curr += obv_h
    for vk in ["bottom","reverse","top"]:
        if images.get(vk): y_curr+=gap_px; coords[vk]=((coords["obverse"][0]+(obv_w-images[vk].shape[1])//2),y_curr); y_curr+=images[vk].shape[0]; coords[vk+"_bottom_y"]=y_curr
    if images.get("ruler"): y_curr+=ruler_pad_px; coords["ruler"]=((coords["obverse"][0]+(obv_w-rul_w)//2),y_curr)
    
    y_rot_align = coords.get("reverse_bottom_y", y_curr)
    if images.get("left"): l_rot=cv2.rotate(convert_to_bgr_if_needed(images["left"]),cv2.ROTATE_180); images["left_rotated"]=l_rot; coords["left_rotated"]=(coords.get("left",(0,0))[0],y_rot_align-l_rot.shape[0])
    if images.get("right"): r_rot=cv2.rotate(convert_to_bgr_if_needed(images["right"]),cv2.ROTATE_180); images["right_rotated"]=r_rot; coords["right_rotated"]=(coords.get("right",(0,0))[0],y_rot_align-r_rot.shape[0])
    return int(canvas_w), int(canvas_h), coords, images

def add_logo_to_image(content_img, logo_path, bg_color, max_w_frac, pad_above, pad_below):
    if not logo_path or not os.path.exists(logo_path): print("Warn: Logo path invalid."); return content_img
    logo_orig = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    if logo_orig is None: print(f"Warn: Could not load logo: {logo_path}"); return content_img
    
    ch, cw = content_img.shape[:2]; loh, low = logo_orig.shape[:2]; logo_res = logo_orig
    if low > cw * max_w_frac and low > 0:
        nlw = int(cw * max_w_frac); sr = nlw/low; nlh = int(loh*sr)
        if nlw>0 and nlh>0: logo_res = cv2.resize(logo_orig,(nlw,nlh),interpolation=cv2.INTER_AREA)
    
    lh, lw = logo_res.shape[:2]
    cnv_lw=max(cw,lw); cnv_lh=ch+pad_above+lh+pad_below
    cnv_w_logo=np.full((cnv_lh,cnv_lw,3),bg_color,dtype=np.uint8)
    paste_image_onto_canvas(cnv_w_logo,content_img,(cnv_lw-cw)//2,0)
    paste_image_onto_canvas(cnv_w_logo,logo_res,(cnv_lw-lw)//2,ch+pad_above)
    return cnv_w_logo

def crop_and_add_final_margin(image_array, bg_color, margin_px):
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    content = image_array
    if np.any(gray > np.min(bg_color) + 5): # Check if there is content
        mask = cv2.inRange(gray, np.min(bg_color) + 1, 255)
        coords = cv2.findNonZero(mask)
        if coords is not None:
            x, y, w_c, h_c = cv2.boundingRect(coords)
            content = image_array[y:y + h_c, x:x + w_c]
    
    h_content, w_content = content.shape[:2]
    final_h = h_content + 2 * margin_px
    final_w = w_content + 2 * margin_px
    final_canvas = np.full((final_h, final_w, 3), bg_color, dtype=np.uint8)
    paste_image_onto_canvas(final_canvas, content, margin_px, margin_px)
    return final_canvas

def set_piexif_metadata(image_path, title, photographer, institution, copyright, dpi):
    try: exif_data = piexif.load(image_path)
    except: exif_data = {"0th":{},"Exif":{},"GPS":{},"1st":{},"thumbnail":None}
    exif_data["0th"][piexif.ImageIFD.Artist] = photographer.encode('utf-8')
    exif_data["0th"][piexif.ImageIFD.Copyright] = copyright.encode('utf-8')
    exif_data["0th"][piexif.ImageIFD.ImageDescription] = title.encode('utf-8')
    exif_data["0th"][piexif.ImageIFD.Software] = "eBL Img Proc Python".encode('utf-8')
    exif_data["0th"][piexif.ImageIFD.XResolution]=(dpi,1); exif_data["0th"][piexif.ImageIFD.YResolution]=(dpi,1)
    exif_data["0th"][piexif.ImageIFD.ResolutionUnit]=2 # Inches
    try: piexif.insert(piexif.dump(exif_data), image_path)
    except Exception as e: print(f"Warn piexif: {e}")

def apply_xmp_with_exiftool(img_path, title, photographer, institution, credit, copyright, usage):
    if shutil.which("exiftool") is None: print("Warn: exiftool not found. Skipping XMP."); return
    try:
        cmd = ["exiftool","-overwrite_original","-L",f"-XMP-dc:Title={title}",f"-XMP-dc:Creator={photographer}",
               f"-XMP-dc:Rights={copyright}",f"-XMP-photoshop:Credit={credit}",
               f"-XMP-photoshop:Source={institution}",f"-XMP-xmpRights:UsageTerms={usage}",
               "-XMP-xmpRights:Marked=True",img_path]
        res=subprocess.run(cmd,capture_output=True,text=True,check=False,encoding='utf-8',errors='replace')
        if res.returncode!=0:print(f"Warn: exiftool code {res.returncode}\n{res.stderr.strip()}")
        else: print("XMP metadata applied via exiftool.")
    except Exception as e: print(f"ERROR applying XMP: {e}")
