import os
import logging
from google import genai
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

# ==========================================
# CƠ CHẾ XOAY VÒNG API KEY
# ==========================================
API_KEYS = []
KEY_FILE = "api_keys.txt"

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        API_KEYS = [line.strip() for line in f if line.strip()]

current_key_index = 0
client = None

def init_client():
    global client, current_key_index
    if API_KEYS and current_key_index < len(API_KEYS):
        try:
            client = genai.Client(api_key=API_KEYS[current_key_index])
            logger.info(f"Đã load Gemini API Key thứ {current_key_index + 1}/{len(API_KEYS)}")
            return True
        except Exception as e:
            logger.error(f"Lỗi cấu hình API Key thứ {current_key_index + 1}: {e}")
            return False
    return False

init_client()

# ==========================================
# HÀM DỊCH THEO MẺ (GẮN ID MAPPING)
# ==========================================
def translate_batch(text_list, source_lang='zh-CN', target_lang='vi'):
    global current_key_index, client

    if not text_list: return []

    lang_map = {"vi": "Vietnamese", "en": "English", "ko": "Korean", "ja": "Japanese", "zh-CN": "Chinese"}
    target = lang_map.get(target_lang, "Vietnamese")
    
    # 1. Tạo chuỗi gửi đi có đánh số thứ tự (ID)
    input_data = ""
    for i, text in enumerate(text_list):
        input_data += f"{i}|{text}\n"

    prompt = f"""
You are a professional subtitle translator. Translate the following {source_lang} texts to {target}.
CRITICAL RULES:
1. Maintain the EXACT format with the ID and the pipe symbol '|'.
2. Do not add any markdown, intro, or outro.
3. ANTI-HALLUCINATION: If a text contains unnatural looping words (e.g. a word repeating 4-5 times endlessly due to AI speech-to-text errors), CLEAN IT UP. Translate it naturally as if a human spoke it (maximum 1 or 2 repetitions for emphasis).

Input:
{input_data}
"""

    # 2. Vòng lặp chống lỗi API & Xoay vòng Key
    while client is not None and current_key_index < len(API_KEYS):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response.text:
                res_text = response.text.strip()
                
                # 3. Bóc tách kết quả dựa trên mã ID
                translated_dict = {}
                for line in res_text.split('\n'):
                    line = line.strip()
                    if '|' in line:
                        parts = line.split('|', 1)
                        if parts[0].strip().isdigit():
                            translated_dict[int(parts[0].strip())] = parts[1].strip()
                
                # 4. Ráp lại thành mảng theo đúng thứ tự mốc thời gian video
                result_list = []
                for i in range(len(text_list)):
                    # Lấy câu đã dịch, nếu AI lỡ bỏ sót dòng nào thì lấy lại câu gốc tiếng Trung
                    result_list.append(translated_dict.get(i, text_list[i])) 
                
                return result_list
                
        except Exception as e:
            logger.warning(f"Key thứ {current_key_index + 1} hết Quota hoặc lỗi: {e}")
            current_key_index += 1
            if current_key_index < len(API_KEYS):
                logger.info(f"Đang tự động đổi sang API Key thứ {current_key_index + 1}...")
                init_client()
            else:
                logger.warning("Hết sạch API Key. Lùi về Google Translate.")
                client = None

    # Fallback: Google Translate dự phòng
    logger.info("Đang dịch bằng Google Translate (Từng câu)...")
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return [translator.translate(t) for t in text_list]
    except Exception as e:
        logger.error(f"Lỗi Google Translate: {e}")
        return text_list