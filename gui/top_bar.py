import customtkinter as ctk

class TopBar(ctk.CTkFrame):
    def __init__(self, master, app_state, callbacks):
        super().__init__(master, fg_color="#1E1E1E", corner_radius=0)
        self.app_state = app_state
        self.callbacks = callbacks

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)

        # Trái: Chọn Folder
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.btn_in = ctk.CTkButton(folder_frame, text="📂 Chọn Video Gốc (Input)", command=self.callbacks['select_input'], width=150)
        self.btn_in.grid(row=0, column=0, padx=(0, 10))
        self.lbl_in = ctk.CTkLabel(folder_frame, text="Chưa chọn...", text_color="gray", width=200, anchor="w")
        self.lbl_in.grid(row=0, column=1, padx=(0, 20))

        self.btn_out = ctk.CTkButton(folder_frame, text="📂 Chọn Nơi Lưu (Output)", command=self.callbacks['select_output'], width=150)
        self.btn_out.grid(row=0, column=2, padx=(0, 10))
        self.lbl_out = ctk.CTkLabel(folder_frame, text="Chưa chọn...", text_color="gray", width=200, anchor="w")
        self.lbl_out.grid(row=0, column=3)

        # Phải: Ngôn ngữ & Nút bấm thực thi
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=2, padx=15, pady=10, sticky="e")

        ctk.CTkLabel(action_frame, text="Dịch sang:").pack(side="left", padx=10)
        lang_menu = ctk.CTkOptionMenu(action_frame, variable=self.app_state['lang_var'], 
                                      values=list(self.app_state['LANG_MAP'].keys()), width=120)
        lang_menu.pack(side="left", padx=(0, 20))

        # NÚT MỚI: Chỉ xử lý 1 video
        self.btn_start_single = ctk.CTkButton(action_frame, text="▶ XỬ LÝ 1 VIDEO NÀY", font=("Segoe UI", 12, "bold"),
                                       command=self.callbacks['start_single'], fg_color="#3B82F6", hover_color="#2563EB")
        self.btn_start_single.pack(side="left", padx=5)

        # Nút cũ: Xử lý tất cả
        self.btn_start_all = ctk.CTkButton(action_frame, text="▶ XỬ LÝ TẤT CẢ", font=("Segoe UI", 12, "bold"),
                                       command=self.callbacks['start_all'], fg_color="#10B981", hover_color="#059669")
        self.btn_start_all.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(action_frame, text="⏹ HỦY BỎ", font=("Segoe UI", 12, "bold"),
                                        command=self.callbacks['cancel'], fg_color="#EF4444", hover_color="#DC2626", state="disabled")
        self.btn_cancel.pack(side="left", padx=5)

    def update_labels(self, in_path, out_path):
        if in_path: self.lbl_in.configure(text=in_path)
        if out_path: self.lbl_out.configure(text=out_path)

    def set_processing_state(self, is_processing):
        state = "disabled" if is_processing else "normal"
        self.btn_in.configure(state=state)
        self.btn_out.configure(state=state)
        self.btn_start_single.configure(state="disabled" if is_processing else "normal")
        self.btn_start_all.configure(state="disabled" if is_processing else "normal")
        self.btn_cancel.configure(state="normal" if is_processing else "disabled")