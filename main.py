import logging
import sys
import customtkinter as ctk
from gui.main_window import MainWindow
import logging

# ==========================================
# CẤU HÌNH LOGGING CHUYÊN NGHIỆP
# ==========================================
logging.basicConfig(
    level=logging.DEBUG, # Ghi lại mọi thứ từ DEBUG, INFO, WARNING đến ERROR
    format='%(asctime)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("app_debug.log", encoding="utf-8", mode="w"), # Ghi đè file log mỗi lần mở app
        logging.StreamHandler() # Vẫn in ra màn hình Terminal
    ]
)
logger = logging.getLogger(__name__)

def setup_logging():
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler("app_debug.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Khởi động Video Subtitler & Dubbing Studio...")
    
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    app = MainWindow()
    app.mainloop()