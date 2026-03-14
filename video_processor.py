import subprocess
import os
import logging
import cv2
import re
from utils import format_ffmpeg_path

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.process = None
        self.is_cancelled = False

    def check_audio_stream(self, video_path):
        cmd = ["ffprobe", "-i", video_path, "-show_streams", "-select_streams", "a", "-loglevel", "error"]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
            return len(result.stdout.strip()) > 0
        except:
            return False

    def convert_time_to_ass(self, srt_time):
        try:
            h, m, s_ms = srt_time.strip().split(':')
            s, ms = s_ms.split(',')
            return f"{int(h)}:{m}:{s}.{ms[:2]}"
        except:
            return "0:00:00.00"

    def create_ass_file(self, srt_path, ass_path, orig_w, orig_h, roi_new, sub_color, sub_outline):
        x, y, w, h = roi_new
        if w == 0 or h == 0: 
            x, y, w, h = int(orig_w * 0.1), int(orig_h * 0.8), int(orig_w * 0.8), int(orig_h * 0.1)

        margin_l = x
        margin_r = orig_w - (x + w)
        margin_v = orig_h - (y + h)
        font_size = max(12, int(h / 2.5)) 

        # Đổi màu tiếng Việt sang mã ASS
        color_map = {
            "Trắng": "&H00FFFFFF",
            "Vàng": "&H0000FFFF",
            "Xanh lơ": "&H00FFFF00"
        }
        primary_color = color_map.get(sub_color, "&H00FFFFFF")

        # Đổi viền sang Pixel
        outline_map = {"Mỏng": "1", "Vừa": "2", "Dày": "4"}
        outline_val = outline_map.get(sub_outline, "2")

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {orig_w}
PlayResY: {orig_h}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline_val},0,2,{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        blocks = re.split(r'\n\n+', content)
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                times = lines[1].split(' --> ')
                if len(times) == 2:
                    start = self.convert_time_to_ass(times[0])
                    end = self.convert_time_to_ass(times[1])
                    text = " ".join([l.strip() for l in lines[2:] if l.strip()])
                    ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        return ass_path

    def process_video(self, input_video, output_video, srt_file, roi_old, roi_new, delete_original, 
                      dubbed_audio_path=None, mute_original=False, dub_volume=1.5,
                      enable_subtitles=True, sub_color="Trắng", sub_outline="Vừa"):
        self.is_cancelled = False
        
        cap = cv2.VideoCapture(input_video)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if orig_w == 0: orig_w, orig_h = 1080, 1920 

        filters = []
        x_old, y_old, w_old, h_old = roi_old
        if w_old > 0 and h_old > 0:
            blur_filter = f"[0:v]crop={w_old}:{h_old}:{x_old}:{y_old},boxblur=20:5[b];[0:v][b]overlay={x_old}:{y_old}[v_blur]"
            filters.append(blur_filter)
            in_stream = "[v_blur]"
        else:
            in_stream = "[0:v]"

        ass_file = None
        # Chỉ tạo filter chèn Subtitle nếu người dùng BẬT tính năng này
        if enable_subtitles and os.path.exists(srt_file):
            ass_file = srt_file.replace('.srt', '.ass')
            self.create_ass_file(srt_file, ass_file, orig_w, orig_h, roi_new, sub_color, sub_outline)
            ass_escaped = format_ffmpeg_path(ass_file)
            sub_filter = f"{in_stream}subtitles='{ass_escaped}'[v_out]"
            filters.append(sub_filter)
        else:
            filters.append(f"{in_stream}copy[v_out]") # Nếu không sub, copy luồng cũ sang v_out

        cmd = ["ffmpeg", "-y", "-i", input_video]
        
        has_original_audio = self.check_audio_stream(input_video)
        audio_map_flag = None

        if dubbed_audio_path and os.path.exists(dubbed_audio_path):
            cmd.extend(["-i", dubbed_audio_path])
            if has_original_audio and not mute_original:
                filters.append(f"[0:a]volume=0.15[a_base];[1:a]volume={dub_volume:.1f}[a_dub];[a_base][a_dub]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_out]")
                audio_map_flag = "[a_out]"
            else:
                filters.append(f"[1:a]volume={dub_volume:.1f}[a_out]")
                audio_map_flag = "[a_out]"
        else:
            if has_original_audio and not mute_original:
                audio_map_flag = "0:a" 

        filter_complex = ";".join(filters)
        cmd.extend(["-filter_complex", filter_complex, "-map", "[v_out]"])
        
        if audio_map_flag: cmd.extend(["-map", audio_map_flag, "-c:a", "aac"])
        else: cmd.append("-an")
        
        cmd.extend(["-c:v", "libx264", output_video])

        logger.debug(f"Chạy FFmpeg tổng hợp: {' '.join(cmd)}")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            self.process.communicate()

            if self.is_cancelled:
                if os.path.exists(output_video): os.remove(output_video)
                return False

            if delete_original and os.path.exists(input_video): os.remove(input_video)
            
            if ass_file and os.path.exists(ass_file): os.remove(ass_file)
            return True

        except Exception as e:
            logger.exception(f"Exception FFmpeg: {e}")
            raise

    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
            self.process.kill()