import logging
from deep_translator import GoogleTranslator

# Khởi tạo logger cho file này
logger = logging.getLogger(__name__)

def translate_text(text, source_lang='zh-CN', target_lang='vi'):
    """Dịch text từ tiếng Trung sang tiếng Việt."""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as e:
        # Ghi log chi tiết lỗi dịch thuật kèm traceback
        logger.error(f"Lỗi dịch thuật với đoạn text '{text[:30]}...': {e}", exc_info=True)
        return text # Trả về text gốc nếu API bị lỗi để tránh crash tiến trình