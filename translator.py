import os
import time
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
# HÀM DỊCH THEO MẺ (ĐÃ TÍCH HỢP CHIA CHUNK VÀ FULL PROMPT)
# ==========================================
def translate_batch(text_list, source_lang='zh-CN', target_lang='vi'):
    global current_key_index, client

    if not text_list: return []

    lang_map = {"vi": "Vietnamese", "en": "English", "ko": "Korean", "ja": "Japanese", "zh-CN": "Chinese"}
    target = lang_map.get(target_lang, "Vietnamese")
    
    final_result_list = []
    
    # -------------------------------------------------------------
    # SỰ LỰA CHỌN VÀNG: 60 câu ~ 3 phút phim (Đủ ngữ cảnh, không bị cắt cụt)
    batch_size = 60  
    # -------------------------------------------------------------

    # Băm nhỏ mảng lớn thành nhiều mảng nhỏ
    for batch_start in range(0, len(text_list), batch_size):
        chunk = text_list[batch_start:batch_start + batch_size]
        
        # 1. Tạo chuỗi gửi đi cho mẻ hiện tại
        input_data = ""
        for i, text in enumerate(chunk):
            # Tính chỉ số ID thật của video để AI không bị loạn
            real_index = batch_start + i
            input_data += f"{real_index}|{text}\n"

        # GẮN FULL SIÊU PROMPT CỦA BẠN VÀO ĐÂY
        prompt = f"""You are an elite subtitle translator and localization expert.

Your task is to translate dialogue subtitles from {source_lang} to {target}.

The subtitles come from speech recognition (STT), so they may contain noise,
repetitions, or fragmented sentences.

Follow the rules below carefully.

--------------------------------
CONTEXT UNDERSTANDING
--------------------------------

Before translating, read the entire batch of subtitles to infer:

- the storyline
- the relationship between speakers
- emotional tone
- whether the speech is casual, formal, angry, joking, etc.

Use this context to produce natural translations.

Do NOT translate each line independently without considering context.

--------------------------------
RELATIONSHIP-AWARE LANGUAGE
--------------------------------

Adapt the translation style to the cultural norms of the target language.

Examples:

Vietnamese:
choose natural pronouns depending on relationship
(anh/em, tao/mày, cậu/tớ, chú/cháu, con/mẹ...)

Japanese:
use appropriate politeness level (casual / polite / honorific)

Korean:
adapt speech level and honorific usage

Chinese:
use natural conversational tone

English:
use natural spoken English

Avoid robotic or overly formal language unless the context requires it.

--------------------------------
NATURAL SPOKEN LANGUAGE
--------------------------------

The output must sound like real spoken dialogue.

Prefer conversational phrasing.

Use natural particles, slang, or contractions when appropriate.

Avoid literal word-for-word translation.

--------------------------------
SUBTITLE STYLE
--------------------------------

Subtitles must be easy to read.

Prefer shorter spoken sentences.

Avoid unnecessary filler words.

The translation should feel natural when read aloud or used for dubbing.

--------------------------------
ANTI-STT NOISE CLEANING
--------------------------------

Speech recognition may produce errors such as:

hello hello hello hello
wait wait wait wait

Clean up unnatural repetition.

Allow a maximum of 1–2 repetitions if it expresses emotion.

--------------------------------
SEGMENT PRESERVATION
--------------------------------

Each input line must produce exactly ONE output line.

Do NOT merge lines.
Do NOT split lines.

--------------------------------
PROPER NAMES
--------------------------------

Do NOT translate names of people, places, or brands unless a widely accepted translation exists.

Examples:

John → John  
New York → New York  
YouTube → YouTube  

--------------------------------
SOUND EFFECTS
--------------------------------

If the subtitle contains sound tags such as:

[LAUGHING]
[DOOR SLAMS]
[MUSIC]

Keep them unchanged.

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------

Return ONLY the translated subtitles.

Keep the exact format:

ID|translated text

CRITICAL:
- Do NOT add explanations, markdown, or extra text.
- Do NOT change the ID numbers.
- Do NOT use the pipe symbol "|" inside the translated text itself.
- If a source line is empty or contains only punctuation, return the ID with an empty string (e.g., 2|).

--------------------------------
INPUT
--------------------------------

{input_data}"""

        chunk_success = False

        # --- THUẬT TOÁN BẢO VỆ API KEY THÔNG MINH ---
        # Cho phép thử lại tối đa (Số key * 2) lần. Ví dụ bạn có 2 key, nó sẽ thử 4 lần (chờ tổng cộng 40s) rồi mới bỏ cuộc.
        max_attempts = max(1, len(API_KEYS) * 2) 

        for attempt in range(max_attempts):
            if client is None:
                break
                
            try:
                logger.info(f"Đang dịch từ câu {batch_start} đến {batch_start + len(chunk)} (Bằng Key {current_key_index + 1})...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                
                if response.text:
                    res_text = response.text.strip()
                    translated_dict = {}
                    for line in res_text.split('\n'):
                        line = line.strip()
                        if '|' in line:
                            parts = line.split('|', 1)
                            if parts[0].strip().isdigit():
                                translated_dict[int(parts[0].strip())] = parts[1].strip()
                    
                    for i in range(len(chunk)):
                        real_index = batch_start + i
                        final_result_list.append(translated_dict.get(real_index, chunk[i])) 
                    
                    chunk_success = True
                    
                    # GIỮ NHỊP ĐỘ: Nghỉ 4 giây sau mỗi lần dịch thành công (Khoảng 15 mẻ/phút = Chuẩn Limit Google)
                    time.sleep(4)
                    break # Dịch thành công thì thoát vòng lặp retry để làm mẻ tiếp theo
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # NẾU BỊ QUÁ TẢI (429) -> CHỜ VÀ XOAY VÒNG KEY CHỨ KHÔNG XÓA KEY
                if "429" in error_msg or "quota" in error_msg or "too many" in error_msg or "exhausted" in error_msg:
                    logger.warning(f"⚠️ Key {current_key_index + 1} bị quá tải/Limit. Đang chờ 10s để server nhả IP...")
                    time.sleep(10) # Bắt buộc chờ 10s để Google reset Limit
                    
                    # Phép toán '%' giúp xoay vòng tròn: Key 1 -> Key 2 -> Key 3 -> Quay lại Key 1
                    if len(API_KEYS) > 1:
                        current_key_index = (current_key_index + 1) % len(API_KEYS)
                        logger.info(f"🔄 Tạm xoay vòng sang Key {current_key_index + 1} để san sẻ tải...")
                        init_client()
                else:
                    logger.error(f"❌ Lỗi Gemini không xác định: {e}")
                    time.sleep(3)
                    if len(API_KEYS) > 1:
                        current_key_index = (current_key_index + 1) % len(API_KEYS)
                        init_client()

        # Fallback: Chỉ khi nào thử đi thử lại chán chê mà server vẫn sập, mới phải lôi Google Translate ra xài
        if not chunk_success:
            logger.info("Đang dịch mẻ này bằng Google Translate...")
            try:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                for t in chunk:
                    final_result_list.append(translator.translate(t))
            except Exception as e:
                logger.error(f"Lỗi Google Translate: {e}")
                final_result_list.extend(chunk)

    return final_result_list