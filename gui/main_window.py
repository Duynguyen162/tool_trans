import customtkinter as ctk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import threading
import os
import logging
import cv2

from utils import get_video_files
from subtitle_generator import SubtitleGenerator
from video_processor import VideoProcessor
from audio_processor import create_dubbed_audio

from gui.top_bar import TopBar
from gui.left_panel import LeftPanel
from gui.preview_panel import PreviewPanel
from gui.bottom_panel import BottomPanel

logger = logging.getLogger(__name__)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Phần Mềm Dịch & Lồng Tiếng Video Tự Động")
        self.geometry("1200x800")
        self.minsize(1000, 600)

        # KHO LƯU TRỮ TỌA ĐỘ (CỐ ĐỊNH THEO MÀN HÌNH CANVAS 720x405)
        self.video_custom_rois = {} 
        self.global_fallback_canvas_rois = { 
            "canvas_old": (0, 0, 0, 0), 
            "canvas_new": (0, 0, 0, 0)
        }
        self.current_selected_video = None
        
        self.app_state = {
            'input_folder': "", 'output_folder': "", 'video_files': [],
            'current_video': None, 'process_mode': 'all',
            'roi_old': (0, 0, 0, 0), 'roi_new': (0, 0, 0, 0),
            'lang_var': ctk.StringVar(value="Tiếng Việt"),
            'LANG_MAP': {"Tiếng Việt": "vi", "Tiếng Anh": "en", "Tiếng Hàn": "ko", "Tiếng Nhật": "ja", "Tiếng Trung": "zh-CN"},
            'enable_subtitles': ctk.BooleanVar(value=True),
            'sub_color': ctk.StringVar(value="Trắng"),      
            'sub_outline': ctk.StringVar(value="Vừa"),      
            'enable_dubbing': ctk.BooleanVar(value=False),
            # --- THÊM 2 DÒNG NÀY VÀO ---
            'voice_selection': ctk.StringVar(value="Nữ (Hoài My)"),
            'VOICE_MAP': {"Nữ (Hoài My)": "vi-VN-HoaiMyNeural", "Nam (Nam Minh)": "vi-VN-NamMinhNeural"},

            'mute_original': ctk.BooleanVar(value=False),
            'dub_volume': ctk.DoubleVar(value=1.5),
            'delete_original': ctk.BooleanVar(value=False)
        }
        self.is_processing = False

        self.sub_generator = SubtitleGenerator()
        self.vid_processor = VideoProcessor()
        self.setup_layout()

    def setup_layout(self):
        callbacks_top = {
            'select_input': self.select_input, 'select_output': self.select_output,
            'start_single': self.start_single, 'start_all': self.start_all, 'cancel': self.cancel_processing
        }
        self.top_bar = TopBar(self, self.app_state, callbacks_top)
        self.top_bar.pack(side="top", fill="x")

        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(side="top", fill="both", expand=True)

        callbacks_left = {
            'load_video': self.preview_video
        }
        self.left_panel = LeftPanel(body_frame, self.app_state, callbacks_left)
        self.left_panel.pack(side="left", fill="y", padx=(10, 5), pady=10)

        callbacks_preview = {'update_regions': self.update_regions}
        self.preview_panel = PreviewPanel(body_frame, callbacks_preview)
        self.preview_panel.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        self.bottom_panel = BottomPanel(self)
        self.bottom_panel.pack(side="bottom", fill="x")

    def select_input(self):
        folder = fd.askdirectory()
        if folder:
            self.app_state['input_folder'] = folder
            self.app_state['video_files'] = get_video_files(folder)
            self.top_bar.update_labels(in_path=folder, out_path=None)
            self.left_panel.update_video_list(self.app_state['video_files'])
            if self.app_state['video_files']:
                self.preview_video(self.app_state['video_files'][0])

    def select_output(self):
        folder = fd.askdirectory()
        if folder:
            self.app_state['output_folder'] = folder
            self.top_bar.update_labels(in_path=None, out_path=folder)

    # --- HÀM THÔNG MINH: TÌM TỌA ĐỘ KẾ THỪA TỪ VIDEO PHÍA TRÊN ---
    def get_fallback_for_video(self, video_file):
        try:
            idx = self.app_state['video_files'].index(video_file)
        except ValueError:
            return self.global_fallback_canvas_rois["canvas_old"], self.global_fallback_canvas_rois["canvas_new"]
            
        # Tìm ngược lên trên danh sách xem có video nào đã được set tay chưa
        for i in range(idx - 1, -1, -1):
            prev_vid = self.app_state['video_files'][i]
            if prev_vid in self.video_custom_rois:
                return self.video_custom_rois[prev_vid]["canvas_old"], self.video_custom_rois[prev_vid]["canvas_new"]
                
        # Nếu trên nó không có video nào set, thì lấy mặc định chung
        return self.global_fallback_canvas_rois["canvas_old"], self.global_fallback_canvas_rois["canvas_new"]

    # --- HÀM QUY ĐỔI: TỪ MÀN HÌNH RA KÍCH THƯỚC VIDEO THỰC TẾ TRƯỚC KHI RENDER ---
    def canvas_to_real_roi(self, canvas_roi, video_path):
        cx, cy, cw, ch = canvas_roi
        if cw == 0 or ch == 0: return (0, 0, 0, 0)
        
        cap = cv2.VideoCapture(video_path)
        orig_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        orig_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()
        if orig_w == 0 or orig_h == 0: orig_w, orig_h = 1080, 1920
        
        canvas_w, canvas_h = 720, 405
        target_ratio = canvas_w / canvas_h
        orig_aspect = orig_w / orig_h
        
        if orig_aspect > target_ratio:
            scale = canvas_w / orig_w
            offset_x = 0
            offset_y = (canvas_h - int(orig_h * scale)) // 2
        else:
            scale = canvas_h / orig_h
            offset_x = (canvas_w - int(orig_w * scale)) // 2
            offset_y = 0
            
        adj_x1, adj_y1 = max(0, cx - offset_x), max(0, cy - offset_y)
        adj_x2, adj_y2 = min(canvas_w - offset_x, cx + cw - offset_x), min(canvas_h - offset_y, cy + ch - offset_y)
        
        real_x, real_y = int(adj_x1 / scale), int(adj_y1 / scale)
        real_w, real_h = int((adj_x2 - adj_x1) / scale), int((adj_y2 - adj_y1) / scale)
        
        return (real_x, real_y, max(0, real_w), max(0, real_h))

    def preview_video(self, filename):
        self.app_state['current_video'] = filename 
        path = os.path.join(self.app_state['input_folder'], filename)
        
        # 1. Tìm khung Canvas kế thừa (từ video phía trên hoặc đã vẽ)
        fallback_old, fallback_new = self.get_fallback_for_video(filename)

        custom_data = self.video_custom_rois.get(filename, {})
        canvas_old_to_draw = custom_data.get("canvas_old", fallback_old)
        canvas_new_to_draw = custom_data.get("canvas_new", fallback_new)

        # 2. Bơm tọa độ Cố định Màn Hình vào Preview Panel
        self.preview_panel.canvas_roi_old = canvas_old_to_draw
        self.preview_panel.canvas_roi_new = canvas_new_to_draw
        
        # 3. Load Video (Màn hình sẽ xóa bóng mờ cũ và vẽ lại khung mới duy nhất)
        self.preview_panel.load_video(path, filename)

    def update_regions(self, canvas_old, canvas_new):
        current_vid = self.app_state['current_video']
        if current_vid:
            if current_vid not in self.video_custom_rois:
                self.video_custom_rois[current_vid] = {}
            
            # Lưu tọa độ Canvas cho video này
            self.video_custom_rois[current_vid]["canvas_old"] = canvas_old
            self.video_custom_rois[current_vid]["canvas_new"] = canvas_new

            # Set làm mặc định phòng hờ
            self.global_fallback_canvas_rois["canvas_old"] = canvas_old
            self.global_fallback_canvas_rois["canvas_new"] = canvas_new
            logger.info(f"Đã lưu tọa độ Màn hình cho video: {current_vid}")

    def start_single(self):
        if not self.app_state['current_video']:
            self.update_progress("⚠️ Lỗi: Chưa có video nào đang được hiển thị!", 0)
            return
        self.start_processing(mode='single')

    def start_all(self):
        self.start_processing(mode='all')

    def start_processing(self, mode='all'):
        if not self.app_state['video_files'] or not self.app_state['output_folder']:
            self.update_progress("⚠️ Lỗi: Thiếu thư mục đầu vào hoặc đầu ra!", 0)
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn đầy đủ thư mục Gốc và Nơi Lưu.")
            return
        
        self.preview_panel.release_video()
        
        self.app_state['process_mode'] = mode
        self.is_processing = True
        self.top_bar.set_processing_state(True)
        threading.Thread(target=self.process_loop, daemon=True).start()

    def process_loop(self):
        videos_to_process = [self.app_state['current_video']] if self.app_state['process_mode'] == 'single' else self.app_state['video_files']
        total = len(videos_to_process)
        lang_code = self.app_state['LANG_MAP'].get(self.app_state['lang_var'].get(), "vi")

        need_ai_text = self.app_state['enable_subtitles'].get() or self.app_state['enable_dubbing'].get()

        for i, video_file in enumerate(videos_to_process, start=1):
            if not self.is_processing: break
            
            in_path = os.path.join(self.app_state['input_folder'], video_file)
            out_path = os.path.join(self.app_state['output_folder'], f"out_{video_file}")
            srt_path = os.path.join(self.app_state['output_folder'], f"{os.path.splitext(video_file)[0]}.srt")

            # 1. Tìm vị trí Canvas Kế thừa hoặc Đã vẽ
            fallback_old, fallback_new = self.get_fallback_for_video(video_file)
            custom_data = self.video_custom_rois.get(video_file, {})
            current_canvas_old = custom_data.get("canvas_old", fallback_old)
            current_canvas_new = custom_data.get("canvas_new", fallback_new)

            # 2. CHUYỂN ĐỔI: TỪ MÀN HÌNH VÀO TỌA ĐỘ VIDEO THỰC ĐỂ RENDER
            real_roi_old = self.canvas_to_real_roi(current_canvas_old, in_path)
            real_roi_new = self.canvas_to_real_roi(current_canvas_new, in_path)

            segments_data = []

            try:
                if need_ai_text:
                    self.update_progress(f"[{i}/{total}] Đang tách âm thanh và dịch phụ đề...", (i-1)/total)
                    srt_path, segments_data = self.sub_generator.generate_srt(in_path, srt_path, roi_new=real_roi_new, target_lang=lang_code)
                    if not self.is_processing: break
                
                dubbed_audio_path = None
                if self.app_state['enable_dubbing'].get():
                    self.update_progress(f"[{i}/{total}] Đang tạo lồng tiếng AI tự động...", (i-0.7)/total)
                    dub_path = os.path.join(self.app_state['output_folder'], f"dub_{video_file}.wav")
                    
                    # --- ĐÃ SỬA: LẤY GIỌNG TỪ UI TRUYỀN VÀO ---
                    selected_voice_name = self.app_state['voice_selection'].get()
                    voice_code = self.app_state['VOICE_MAP'].get(selected_voice_name, "vi-VN-HoaiMyNeural")
                    
                    if create_dubbed_audio(segments_data, in_path, dub_path, target_lang=lang_code, voice=voice_code):
                        dubbed_audio_path = dub_path

                if not self.is_processing: break

                self.update_progress(f"[{i}/{total}] Đang xuất Video (Render)...", (i-0.4)/total)
                success = self.vid_processor.process_video(
                    in_path, out_path, srt_path, 
                    real_roi_old, real_roi_new, 
                    self.app_state['delete_original'].get(),
                    dubbed_audio_path,
                    self.app_state['mute_original'].get(),
                    self.app_state['dub_volume'].get(),
                    self.app_state['enable_subtitles'].get(),
                    self.app_state['sub_color'].get(),
                    self.app_state['sub_outline'].get()
                )

                if dubbed_audio_path and os.path.exists(dubbed_audio_path):
                    os.remove(dubbed_audio_path)

            except Exception as e:
                logger.error(f"Lỗi khi xử lý video {video_file}: {e}")
                continue

        if self.is_processing:
            self.update_progress("✅ Đã hoàn thành toàn bộ quá trình xử lý!", 1.0)
            self.after(0, lambda: messagebox.showinfo("Hoàn Thành", "Quá trình Render video đã hoàn thành xuất sắc!"))
        else:
            self.update_progress("❌ Quá trình xử lý đã bị người dùng hủy.", 0.0)

        self.top_bar.set_processing_state(False)
        self.is_processing = False

    def update_progress(self, text, value):
        self.after(0, lambda: self.bottom_panel.update_progress(text, value))

    def cancel_processing(self):
        self.is_processing = False
        self.vid_processor.cancel()