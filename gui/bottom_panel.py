import customtkinter as ctk
import logging

class GUILogHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def emit(self, record):
        msg = self.format(record)
        self.textbox.after(0, self.append_text, msg)

    def append_text(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

class BottomPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#1E1E1E", corner_radius=0)
        self.logs_visible = False
        self.setup_ui()
        self.setup_logging()

    def setup_ui(self):
        # Progress section
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=15, pady=10)

        self.lbl_status = ctk.CTkLabel(prog_frame, text="Hệ thống đã sẵn sàng", font=("Segoe UI", 14))
        self.lbl_status.pack(side="left")

        self.btn_toggle_log = ctk.CTkButton(prog_frame, text="Hiện nhật ký lỗi ▼", width=120, fg_color="#3B82F6", command=self.toggle_logs)
        self.btn_toggle_log.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 10))

        # Log Textbox (Ẩn mặc định)
        self.log_textbox = ctk.CTkTextbox(self, height=150, fg_color="#000000", text_color="#A9B7C6", font=("Consolas", 12))

    def setup_logging(self):
        gui_handler = GUILogHandler(self.log_textbox)
        formatter = logging.Formatter("%(asctime)s - %(message)s", "%H:%M:%S")
        gui_handler.setFormatter(formatter)
        gui_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(gui_handler)

    def toggle_logs(self):
        self.logs_visible = not self.logs_visible
        if self.logs_visible:
            self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            self.btn_toggle_log.configure(text="Ẩn nhật ký lỗi ▲")
        else:
            self.log_textbox.pack_forget()
            self.btn_toggle_log.configure(text="Hiện nhật ký lỗi ▼")

    def update_progress(self, text, value):
        self.lbl_status.configure(text=text)
        self.progress_bar.set(value)