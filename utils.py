import os
import math
import logging

logger = logging.getLogger(__name__)

def get_video_files(folder_path):
    """Lấy danh sách các file video hợp lệ từ folder."""
    valid_exts = {'.mp4', '.mkv', '.mov'}
    try:
        files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in valid_exts]
        logger.info(f"Quét thư mục '{folder_path}' -> Tìm thấy {len(files)} file video hợp lệ.")
        return files
    except Exception as e:
        logger.error(f"Lỗi khi quét thư mục {folder_path}: {e}", exc_info=True)
        return []

def format_timestamp(seconds):
    """Chuyển đổi giây sang định dạng HH:MM:SS,mmm cho file SRT."""
    calc_hrs = int(math.floor(seconds / 3600))
    calc_mins = int(math.floor((seconds % 3600) / 60))
    calc_secs = int(math.floor(seconds % 60))
    calc_msecs = int(round((seconds - math.floor(seconds)) * 1000))
    return f"{calc_hrs:02d}:{calc_mins:02d}:{calc_secs:02d},{calc_msecs:03d}"

def format_ffmpeg_path(path):
    """Sửa lỗi đường dẫn cho filter subtitles của FFmpeg trên Windows."""
    return path.replace("\\", "/").replace(":", "\\:")