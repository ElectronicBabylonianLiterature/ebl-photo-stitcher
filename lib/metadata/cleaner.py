import os
import cv2

class ImageCleaner:
    @staticmethod
    def clean_image_metadata(image_path: str) -> bool:
        try:
            file_ext = os.path.splitext(image_path.lower())[1]
            temp_file = os.path.splitext(image_path)[0] + "_clean" + file_ext
            
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            params = []
            if file_ext in ['.tif', '.tiff']:
                params = [cv2.IMWRITE_TIFF_COMPRESSION, 1]
            elif file_ext in ['.jpg', '.jpeg']:
                params = [cv2.IMWRITE_JPEG_QUALITY, 95]
            
            success = cv2.imwrite(temp_file, img, params) if params else cv2.imwrite(temp_file, img)
            
            if success and os.path.exists(temp_file):
                os.remove(image_path)
                os.rename(temp_file, image_path)
                return True
                
            return False
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    @staticmethod
    def clean_tiff_for_metadata(image_path: str) -> bool:
        try:
            temp_file = image_path + ".tmp"
            
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            success = cv2.imwrite(temp_file, img, [cv2.IMWRITE_TIFF_COMPRESSION, 1])
            
            if success and os.path.exists(temp_file):
                os.remove(image_path)
                os.rename(temp_file, image_path)
                return True
                
            return False
        except Exception:
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    @staticmethod
    def detect_problematic_metadata(image_path: str) -> bool:
        try:
            with open(image_path, 'rb') as f:
                file_start = f.read(1000)
                return b'{"shape"' in file_start
        except Exception:
            return False
