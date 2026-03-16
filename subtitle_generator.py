import whisper
import os
import logging
import cv2
import textwrap
import sys
import torch
import gc
from translator import translate_batch
from utils import format_timestamp

logger = logging.getLogger(__name__)

class SubtitleGenerator:
    def __init__(self, model_size="small"):
        self.model_size = model_size
        self.model = None
        # Tự động phát hiện xem máy có Card NVIDIA (CUDA) không
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self):
        if self.model is None:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            model_path = os.path.join(base_path, "whisper", f"{self.model_size}.pt")
            
            logger.info(f"Đang tải Whisper model '{self.model_size}' lên phần cứng: [{self.device.upper()}]")
            
            if os.path.exists(model_path):
                self.model = whisper.load_model(model_path, device=self.device)
            else:
                self.model = whisper.load_model(self.model_size, device=self.device)

    def cleanup_memory(self):
        """Giải phóng RAM và VRAM sau khi xử lý xong video"""
        if self.device == "cuda":
            torch.cuda.empty_cache() # Trả lại VRAM cho Card màn hình
        gc.collect() # Trả lại RAM hệ thống
        logger.info("Đã dọn dẹp rác bộ nhớ thành công.")

    def generate_srt(self, video_path, output_srt_path, roi_new, target_lang='vi'):
        self.load_model()
        
        cap = cv2.VideoCapture(video_path)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if orig_w == 0: orig_w, orig_h = 1080, 1920

        _, _, w, h = roi_new
        if w == 0 or h == 0: 
            w, h = int(orig_w * 0.8), int(orig_h * 0.1)

        font_size = max(12, int(h / 2.5))
        chars_per_line = max(15, int(w / (font_size * 0.55))) 
        chars_per_line = int(chars_per_line * 0.95)

        try:
            # Bổ sung tham số chống ảo giác mạnh cho Whisper
            result = self.model.transcribe(
                video_path, 
                language="zh",
                condition_on_previous_text=False, # Cấm Whisper nhìn câu cũ để đoán câu mới
                compression_ratio_threshold=2.4,  # Loại bỏ văn bản lặp vô nghĩa
                logprob_threshold=-1.0,           
                no_speech_threshold=0.6           # Bỏ qua các đoạn không có tiếng người
            )
            raw_segments = result['segments']

            # ======================================================
            # LỚP LỌC ẢO GIÁC (HALLUCINATION FILTER) CHỐNG LẶP CÂU
            # ======================================================
            segments = []
            last_text = ""
            repeat_count = 0
            
            for seg in raw_segments:
                current_text = seg['text'].strip()
                if not current_text: 
                    continue # Bỏ qua câu trống
                
                # Kiểm tra lặp câu
                if current_text == last_text:
                    repeat_count += 1
                else:
                    repeat_count = 1
                    last_text = current_text
                    
                # Chỉ cho phép lặp lại tối đa 2 lần liên tiếp (Cho biểu cảm gọi tên tự nhiên)
                if repeat_count <= 2:
                    segments.append(seg)
                else:
                    logger.debug(f"Đã chặn 1 câu ảo giác lặp liên tục: {current_text}")
            # ======================================================

            original_texts = [seg['text'] for seg in segments]
            logger.info(f"Gom {len(original_texts)} câu sạch gửi đi dịch API...")
            translated_texts = translate_batch(original_texts, source_lang='zh-CN', target_lang=target_lang)

            segments_data = [] 
            srt_index = 1 
            
            with open(output_srt_path, "w", encoding="utf-8") as srt_file:
                for segment, text_translated in zip(segments, translated_texts):
                    start_sec = segment['start']
                    end_sec = segment['end']
                    
                    segments_data.append({'start': start_sec, 'end': end_sec, 'text': text_translated})
                    lines = textwrap.wrap(text_translated, width=chars_per_line)
                    
                    chunks = []
                    for i in range(0, len(lines), 2):
                        chunk = "\n".join(lines[i:i+2]) 
                        chunks.append(chunk)
                    
                    total_chars = sum(len(c.replace("\n", "")) for c in chunks)
                    total_duration = end_sec - start_sec
                    current_start = start_sec
                    
                    for chunk in chunks:
                        chunk_chars = len(chunk.replace("\n", ""))
                        chunk_duration = total_duration * (chunk_chars / total_chars) if total_chars > 0 else (total_duration / len(chunks))
                        current_end = current_start + chunk_duration
                        
                        srt_file.write(f"{srt_index}\n")
                        srt_file.write(f"{format_timestamp(current_start)} --> {format_timestamp(current_end)}\n")
                        srt_file.write(f"{chunk}\n\n")
                        
                        srt_index += 1
                        current_start = current_end 
            
            # Giải phóng RAM ngay lập tức sau khi xuất xong Subtitle
            self.cleanup_memory()
            return output_srt_path, segments_data
            
        except Exception as e:
            logger.exception(f"Lỗi tạo SRT: {e}")
            self.cleanup_memory()
            raise