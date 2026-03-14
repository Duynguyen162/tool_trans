import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import cv2

class EmbeddedPreviewWidget(ctk.CTkFrame):
    def __init__(self, master, on_regions_updated, **kwargs):
        super().__init__(master, **kwargs)
        self.on_regions_updated = on_regions_updated
        
        self.video_path = None
        self.cap = None
        self.target_aspect_ratio = 16 / 9
        self.canvas_w = 640
        self.canvas_h = int(self.canvas_w / self.target_aspect_ratio)

        self.orig_w = self.orig_h = 0
        self.scale = 1.0 
        self.offset_x = self.offset_y = 0 
        
        self.mode = None 
        self.roi_old = (0, 0, 0, 0)
        self.roi_new = (0, 0, 0, 0)
        
        self.font_size = 24
        self.preview_text = "Văn bản mẫu" 
        
        self.start_x = self.start_y = 0
        self.current_rect = None
        
        self.setup_ui()

    def set_font_size(self, size):
        self.font_size = size
        self.show_frame_at_time(self.slider.get())

    def set_preview_text(self, text):
        self.preview_text = text if text.strip() else "Văn bản mẫu"
        self.show_frame_at_time(self.slider.get())

    def setup_ui(self):
        self.canvas = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
        self.canvas.pack(pady=(10, 5))
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        self.slider = ctk.CTkSlider(self, from_=0, to=10, command=self.on_slider_move)
        self.slider.set(0)
        self.slider.pack(fill="x", padx=20, pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)
        self.btn_blur = ctk.CTkButton(btn_frame, text="1. Chọn Vùng Blur Cũ", command=lambda: self.set_mode('blur'))
        self.btn_blur.grid(row=0, column=0, padx=10)
        self.btn_text = ctk.CTkButton(btn_frame, text="2. Chọn Vùng Text Mới", command=lambda: self.set_mode('text'))
        self.btn_text.grid(row=0, column=1, padx=10)

    def load_video(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.orig_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.orig_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if self.orig_w > 0 and self.orig_h > 0:
            orig_aspect = self.orig_w / self.orig_h
            if orig_aspect > self.target_aspect_ratio:
                self.scale = self.canvas_w / self.orig_w
                scaled_h = int(self.orig_h * self.scale)
                self.offset_x = 0
                self.offset_y = (self.canvas_h - scaled_h) // 2
            else:
                self.scale = self.canvas_h / self.orig_h
                scaled_w = int(self.orig_w * self.scale)
                self.offset_y = 0
                self.offset_x = (self.canvas_w - scaled_w) // 2
            self.show_frame_at_time(0)
            self.slider.set(0)

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
            
            self.canvas.delete("all") # <--- QUAN TRỌNG: Xóa sạch canvas trước khi vẽ để tránh chữ đè nhau
            self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
            self.redraw_regions()

    def set_mode(self, mode):
        self.mode = mode
        if mode == 'blur':
            self.btn_blur.configure(fg_color="green")
            self.btn_text.configure(fg_color=["#3a7ebf", "#1f538d"])
        else:
            self.btn_text.configure(fg_color="green")
            self.btn_blur.configure(fg_color=["#3a7ebf", "#1f538d"])

    def on_mouse_down(self, event):
        if not self.mode: return
        self.start_x, self.start_y = event.x, event.y
        color = "red" if self.mode == 'blur' else "cyan"
        self.current_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=color, width=2)

    def on_mouse_drag(self, event):
        if not self.mode or not self.current_rect: return
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if not self.mode or not self.current_rect: return
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        adj_x1, adj_y1 = max(0, x1 - self.offset_x), max(0, y1 - self.offset_y)
        adj_x2, adj_y2 = min(self.canvas_w - self.offset_x, x2 - self.offset_x), min(self.canvas_h - self.offset_y, y2 - self.offset_y)
        real_x, real_y = int(adj_x1 / self.scale), int(adj_y1 / self.scale)
        real_w, real_h = int((adj_x2 - adj_x1) / self.scale), int((adj_y2 - adj_y1) / self.scale)
        
        if self.mode == 'blur': self.roi_old = (real_x, real_y, real_w, real_h)
        elif self.mode == 'text': self.roi_new = (real_x, real_y, real_w, real_h)
            
        self.canvas.delete(self.current_rect)
        self.current_rect = None
        self.mode = None
        self.btn_blur.configure(fg_color=["#3a7ebf", "#1f538d"])
        self.btn_text.configure(fg_color=["#3a7ebf", "#1f538d"])
        self.show_frame_at_time(self.slider.get())
        self.on_regions_updated(self.roi_old, self.roi_new)

    def redraw_regions(self):
        if self.roi_old[2] > 0:
            rx, ry, rw, rh = self.roi_old
            x1, y1 = rx * self.scale + self.offset_x, ry * self.scale + self.offset_y
            x2, y2 = (rx + rw) * self.scale + self.offset_x, (ry + rh) * self.scale + self.offset_y
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)
            self.canvas.create_text(x1, y1-10, text="Blur", fill="red", anchor="w")
            
        if self.roi_new[2] > 0:
            rx, ry, rw, rh = self.roi_new
            x1, y1 = rx * self.scale + self.offset_x, ry * self.scale + self.offset_y
            x2, y2 = (rx + rw) * self.scale + self.offset_x, (ry + rh) * self.scale + self.offset_y
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="cyan", width=2)
            
            preview_font_size = max(8, int(self.font_size * self.scale))
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            self.canvas.create_text(center_x, center_y, text=self.preview_text, fill="white", font=("Arial", preview_font_size, "bold"), anchor="center")