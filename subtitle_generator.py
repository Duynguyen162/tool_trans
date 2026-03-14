import whisper
import os
import logging
import cv2
import textwrap
from translator import translate_text
from utils import format_timestamp

logger = logging.getLogger(__name__)

class SubtitleGenerator:
    def __init__(self, model_size="small"):
        self.model_size = model_size
        self.model = None

    def load_model(self):
        if self.model is None:
            logger.info(f"Đang tải model Whisper size '{self.model_size}' vào bộ nhớ...")
            self.model = whisper.load_model(self.model_size)

    def generate_srt(self, video_path, output_srt_path, roi_new, target_lang='vi'):
        self.load_model()
        
        # Đọc thông số video để tính sức chứa tối đa của khung Xanh bạn chọn
        cap = cv2.VideoCapture(video_path)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if orig_w == 0: orig_w, orig_h = 1080, 1920

        _, _, w, h = roi_new
        if w == 0 or h == 0: 
            w, h = int(orig_w * 0.8), int(orig_h * 0.1)

        # 1 dòng chỉ được phép dài tối đa chừng này chữ để không văng ra ngoài khung
        font_size = max(12, int(h / 2.5))
        chars_per_line = max(15, int(w / (font_size * 0.55))) 
        chars_per_line = int(chars_per_line * 0.95) # Trừ hao viền an toàn

        try:
            result = self.model.transcribe(video_path, language="zh")
            segments = result['segments']

            segments_data = [] 
            srt_index = 1 
            
            with open(output_srt_path, "w", encoding="utf-8") as srt_file:
                for segment in segments:
                    start_sec = segment['start']
                    end_sec = segment['end']
                    text_translated = translate_text(segment['text'], source_lang='zh-CN', target_lang=target_lang)
                    
                    segments_data.append({
                        'start': start_sec,
                        'end': end_sec,
                        'text': text_translated
                    })

                    # Băm văn bản thành các dòng nhỏ
                    lines = textwrap.wrap(text_translated, width=chars_per_line)
                    
                    # Gom cứ 2 dòng thành 1 khung hình thời gian
                    chunks = []
                    for i in range(0, len(lines), 2):
                        # Khác biệt là ta KHÔNG CHÈN XUỐNG DÒNG, để Libass tự xuống dòng
                        chunk = " ".join(lines[i:i+2]) 
                        chunks.append(chunk)
                    
                    total_chars = sum(len(c) for c in chunks)
                    total_duration = end_sec - start_sec
                    current_start = start_sec
                    
                    for chunk in chunks:
                        chunk_chars = len(chunk)
                        chunk_duration = total_duration * (chunk_chars / total_chars) if total_chars > 0 else (total_duration / len(chunks))
                        current_end = current_start + chunk_duration
                        
                        srt_file.write(f"{srt_index}\n")
                        srt_file.write(f"{format_timestamp(current_start)} --> {format_timestamp(current_end)}\n")
                        srt_file.write(f"{chunk}\n\n")
                        
                        srt_index += 1
                        current_start = current_end 
            
            return output_srt_path, segments_data
        except Exception as e:
            logger.exception(f"Lỗi tạo SRT: {e}")
            raise