import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import cv2

class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, callbacks):
        super().__init__(master, fg_color="#1E1E1E")
        self.callbacks = callbacks
        self.video_path = None
        self.cap = None
        self.is_playing = False
        
        self.scale = 1.0 
        self.offset_x = self.offset_y = 0 
        self.mode = None 
        self.roi_old = (0, 0, 0, 0)
        self.roi_new = (0, 0, 0, 0)
        
        # --- ĐÃ SỬA: BIẾN LƯU TỌA ĐỘ CỐ ĐỊNH TRÊN MÀN HÌNH ---
        self.canvas_roi_old = (0, 0, 0, 0) 
        self.canvas_roi_new = (0, 0, 0, 0) 
        
        self.start_x = self.start_y = 0
        self.current_rect = None

        self.setup_ui()

    def setup_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        
        self.lbl_info = ctk.CTkLabel(header, text="Chưa tải video nào", font=("Segoe UI", 16, "bold"))
        self.lbl_info.pack(side="left")

        self.btn_play = ctk.CTkButton(header, text="▶ Phát", width=90, command=self.toggle_play)
        self.btn_play.pack(side="right", padx=5)

        self.canvas_w, self.canvas_h = 720, 405
        self.canvas = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h, bg="#000000", highlightthickness=0)
        self.canvas.pack(pady=10)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=10)

        self.slider = ctk.CTkSlider(controls, from_=0, to=10, command=self.on_slider_move)
        self.slider.pack(fill="x", pady=(0, 15))

        self.btn_old = ctk.CTkButton(controls, text="[ ĐỎ ] Chọn vùng CHỮ CŨ (để làm mờ)", 
                                     fg_color="#EF4444", hover_color="#DC2626", command=lambda: self.set_mode('blur'))
        self.btn_old.pack(side="left", expand=True, padx=5)

        self.btn_new = ctk.CTkButton(controls, text="[ XANH ] Chọn vùng CHỮ MỚI (để chèn sub)", 
                                     fg_color="#10B981", hover_color="#059669", command=lambda: self.set_mode('text'))
        self.btn_new.pack(side="left", expand=True, padx=5)

    def load_video(self, video_path, filename):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps else 0
        mins, secs = int(duration // 60), int(duration % 60)
        
        display_name = filename if len(filename) <= 45 else filename[:25] + "..." + filename[-15:]
        
        self.lbl_info.configure(text=f"Video: {display_name}  |  Thời lượng: {mins:02d}:{secs:02d}")
        self.slider.configure(to=min(10, duration))

        self.orig_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.orig_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if self.orig_w > 0 and self.orig_h > 0:
            target_ratio = self.canvas_w / self.canvas_h
            orig_aspect = self.orig_w / self.orig_h
            if orig_aspect > target_ratio:
                self.scale = self.canvas_w / self.orig_w
                self.offset_x, self.offset_y = 0, (self.canvas_h - int(self.orig_h * self.scale)) // 2
            else:
                self.scale = self.canvas_h / self.orig_h
                self.offset_x, self.offset_y = (self.canvas_w - int(self.orig_w * self.scale)) // 2, 0
                
            self.show_frame_at_time(0)
            self.slider.set(0)

    def release_video(self):
        self.is_playing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.canvas.delete("all")
        
    def toggle_play(self):
        if not self.cap: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.configure(text="⏸ Tạm Dừng")
            self.play_loop()
        else:
            self.btn_play.configure(text="▶ Phát")

    def play_loop(self):
        if self.is_playing:
            new_val = self.slider.get() + 0.1
            if new_val <= self.slider.cget("to"):
                self.slider.set(new_val)
                self.show_frame_at_time(new_val)
                self.after(100, self.play_loop)
            else:
                self.toggle_play()

    def on_slider_move(self, value):
        self.show_frame_at_time(value)

    def show_frame_at_time(self, time_sec):
        if not self.cap or not self.cap.isOpened(): return
        self.cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_orig = Image.fromarray(frame_rgb)
            final_img = Image.new("RGB", (self.canvas_w, self.canvas_h), "black")
            scaled_w, scaled_h = int(self.orig_w * self.scale), int(self.orig_h * self.scale)
            img_resized = img_orig.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            final_img.paste(img_resized, (self.offset_x, self.offset_y))
            self.photo = ImageTk.PhotoImage(image=final_img)
            
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
            self.redraw_regions()

    def set_mode(self, mode):
        self.mode = mode
        if mode == 'blur':
            self.btn_old.configure(fg_color="#991B1B") 
            self.btn_new.configure(fg_color="#10B981")
        else:
            self.btn_new.configure(fg_color="#065F46") 
            self.btn_old.configure(fg_color="#EF4444")

    def on_mouse_down(self, event):
        if not self.mode: return
        self.start_x, self.start_y = event.x, event.y
        color = "#EF4444" if self.mode == 'blur' else "#10B981"
        self.current_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=color, width=3)

    def on_mouse_drag(self, event):
        if not self.mode or not self.current_rect: return
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if not self.mode or not self.current_rect: return
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        
        # ĐÃ SỬA: LƯU TỌA ĐỘ MÀN HÌNH (CANVAS)
        cx, cy, cw, ch = x1, y1, x2-x1, y2-y1
        
        if self.mode == 'blur': 
            self.canvas_roi_old = (cx, cy, cw, ch)
        elif self.mode == 'text': 
            self.canvas_roi_new = (cx, cy, cw, ch)
            
        self.canvas.delete(self.current_rect)
        self.current_rect = None
        self.mode = None
        self.btn_old.configure(fg_color="#EF4444")
        self.btn_new.configure(fg_color="#10B981")
        self.show_frame_at_time(self.slider.get())
        
        # TRUYỀN TỌA ĐỘ MÀN HÌNH (CANVAS) VỀ MAIN ĐỂ LƯU
        self.callbacks['update_regions'](self.canvas_roi_old, self.canvas_roi_new)

    def redraw_regions(self):
        # VẼ DỰA TRÊN TỌA ĐỘ MÀN HÌNH CỐ ĐỊNH, KHÔNG BỊ TỤT LỆCH DÙ VIDEO CÓ ĐỔI SIZE
        if self.canvas_roi_old[2] > 0:
            cx, cy, cw, ch = self.canvas_roi_old
            self.canvas.create_rectangle(cx, cy, cx+cw, cy+ch, outline="#EF4444", width=3)
            self.canvas.create_text(cx, cy-10, text="VÙNG XÓA CHỮ", fill="#EF4444", anchor="w", font=("Segoe UI", 10, "bold"))
            
        if self.canvas_roi_new[2] > 0:
            cx, cy, cw, ch = self.canvas_roi_new
            self.canvas.create_rectangle(cx, cy, cx+cw, cy+ch, outline="#10B981", width=3)
            self.canvas.create_text(cx, cy-10, text="VÙNG HIỂN THỊ PHỤ ĐỀ", fill="#10B981", anchor="w", font=("Segoe UI", 10, "bold"))