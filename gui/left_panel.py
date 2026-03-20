import customtkinter as ctk

class LeftPanel(ctk.CTkFrame):
    def __init__(self, master, app_state, callbacks):
        super().__init__(master, width=330, fg_color="#2B2B2B")
        self.app_state = app_state
        self.callbacks = callbacks
        self.pack_propagate(False)

        self.tabs = ctk.CTkTabview(self, width=330)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_list = self.tabs.add("Danh Sách Video")
        self.tab_settings = self.tabs.add("Cài Đặt Chuyên Sâu")

        self.setup_list_tab()
        self.setup_settings_tab()

    def setup_list_tab(self):
        self.video_list_frame = ctk.CTkScrollableFrame(self.tab_list, fg_color="transparent")
        self.video_list_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(self.video_list_frame, text="Vui lòng chọn Thư Mục Video Gốc.", text_color="gray").pack(pady=20)

    def setup_settings_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # --- Phụ Đề ---
        ctk.CTkLabel(scroll, text="Tùy Chỉnh Phụ Đề", font=("Segoe UI", 14, "bold"), text_color="#3B82F6").pack(anchor="w", pady=(5, 5))
        ctk.CTkCheckBox(scroll, text="Chèn Phụ Đề hiển thị lên video", variable=self.app_state['enable_subtitles']).pack(anchor="w", pady=(0, 10))
        
        style_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        style_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(style_frame, text="Màu chữ:").grid(row=0, column=0, padx=(0, 5))
        ctk.CTkOptionMenu(style_frame, variable=self.app_state['sub_color'], values=["Trắng", "Vàng", "Xanh lơ"], width=90).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(style_frame, text="Viền:").grid(row=0, column=2, padx=(10, 5))
        ctk.CTkOptionMenu(style_frame, variable=self.app_state['sub_outline'], values=["Mỏng", "Vừa", "Dày"], width=80).grid(row=0, column=3, padx=5)

        ctk.CTkLabel(scroll, text="Cỡ chữ & Vị trí: TỰ ĐỘNG", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(15, 0))
        ctk.CTkLabel(scroll, text="✓ Hệ thống tự tính toán cỡ chữ.\n✓ Tự động ngắt 2 dòng để vừa khít\n với hộp màu Xanh lá mà bạn vẽ.", 
                     text_color="gray", justify="left").pack(anchor="w", pady=(0, 15))

        # --- Âm Thanh ---
        ctk.CTkLabel(scroll, text="Tùy Chỉnh Âm Thanh", font=("Segoe UI", 14, "bold"), text_color="#3B82F6").pack(anchor="w", pady=(10, 5))
        ctk.CTkCheckBox(scroll, text="Tạo lồng tiếng AI tự động", variable=self.app_state['enable_dubbing']).pack(anchor="w", pady=5)
        
        # --- CODE THÊM MỚI: TẠO MENU CHỌN GIỌNG ---
        ctk.CTkLabel(scroll, text="Giọng lồng tiếng:").pack(anchor="w", pady=(5,0))
        ctk.CTkOptionMenu(scroll, variable=self.app_state['voice_selection'], values=["Nữ (Hoài My)", "Nam (Nam Minh)"]).pack(fill="x", pady=(0, 10))
        ctk.CTkCheckBox(scroll, text="Tắt toàn bộ âm thanh video gốc", variable=self.app_state['mute_original']).pack(anchor="w", pady=5)
        ctk.CTkLabel(scroll, text="Tăng/Giảm âm lượng lồng tiếng:").pack(anchor="w", pady=(5,0))
        ctk.CTkSlider(scroll, from_=0.5, to=5.0, variable=self.app_state['dub_volume']).pack(fill="x", pady=(0, 15))

        # --- Khác ---
        ctk.CTkLabel(scroll, text="Tùy Chọn Khác", font=("Segoe UI", 14, "bold"), text_color="#3B82F6").pack(anchor="w", pady=(10, 5))
        ctk.CTkCheckBox(scroll, text="Xóa video gốc sau khi xử lý xong", variable=self.app_state['delete_original']).pack(anchor="w", pady=5)

    def update_video_list(self, videos):
        for widget in self.video_list_frame.winfo_children():
            widget.destroy()
        if not videos:
            ctk.CTkLabel(self.video_list_frame, text="Không tìm thấy video hợp lệ.", text_color="gray").pack(pady=20)
            return
        for idx, video in enumerate(videos, 1):
            btn = ctk.CTkButton(self.video_list_frame, text=f"🎬 {video}", anchor="w", fg_color="transparent", 
                                hover_color="#3B82F6", text_color="white", command=lambda v=video: self.callbacks['load_video'](v))
            btn.pack(fill="x", pady=2)