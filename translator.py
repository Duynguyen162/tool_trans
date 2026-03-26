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
        # ======================================================
        # TÍNH NĂNG MỚI: ĐỌC NGỮ CẢNH TỪ FILE BÊN NGOÀI (MINI-RAG)
        # ======================================================
        extra_context = ""
        context_file = "ngu_canh.txt"
        if os.path.exists(context_file):
            try:
                with open(context_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        extra_context = f"""
--------------------------------
[SPECIAL CONTEXT FOR THIS VIDEO]
--------------------------------
{content}
"""
            except Exception as e:
                logger.warning(f"Không thể đọc file ngữ cảnh: {e}")
        # ======================================================

        
        # GẮN FULL SIÊU PROMPT CỦA BẠN VÀO ĐÂY
        # Gắn Context nếu có file ngu_canh.txt (Từ bước trước)
        extra_context_str = f"\n--------------------------------\n[SPECIAL CONTEXT FOR THIS VIDEO]\n--------------------------------\n{extra_context}\n" if extra_context else ""

        prompt = f"""You are an elite subtitle translator and localization expert.

Your task is to translate dialogue subtitles from {source_lang} to {target}.
The subtitles come from speech recognition (STT), so they may contain noise, repetitions, or fragmented sentences.
{extra_context_str}
Follow the rules below carefully.

--------------------------------
CONTEXT & TONE INFERENCE
--------------------------------
Before translating, read the entire batch to infer:
- The storyline and setting.
- The relationship, power dynamic, and intimacy between speakers.
- The emotional tone (casual, formal, angry, joking, sarcastic, etc.).
Do NOT translate line-by-line in a vacuum. Use this context to weave a coherent dialogue.

--------------------------------
UNIVERSAL LOCALIZATION RULES (TARGET: {target})
--------------------------------
You must act as a native speaker and cultural expert of {target}.
1. Register & Politeness: Dynamically adjust the formality, honorifics, and politeness levels based on the speakers' inferred relationships, exactly as a native {target} speaker would.
2. Pronouns & Titles: Choose the most natural subjective/objective pronouns and addressing terms specific to {target} culture.
3. Gender & Grammar Agreement: Ensure correct grammatical gender, subject-verb agreement, and syntax rules native to {target}.
4. Idioms & Transcreation: Do NOT translate idioms, jokes, or cultural references literally. Replace them with equivalent natural expressions in {target} that evoke the same emotion and meaning.

--------------------------------
NATURAL SPOKEN SUBTITLE FORMAT
--------------------------------
- The output must flow like real, everyday spoken dialogue, not a textbook.
- Use natural conversational fillers, contractions, or colloquialisms appropriate for the tone.
- Subtitles must be concise. Favor shorter, impactful phrasing over wordy literal translations to ensure readability on screen.

--------------------------------
ANTI-STT NOISE CLEANING
--------------------------------
- Clean up unnatural STT repetitions (e.g., "hello hello hello", "wait wait wait").
- Allow a maximum of 1-2 repetitions ONLY if it naturally expresses emotion (e.g., panic, excitement).
- Fix fragmented sentences caused by STT pauses.

--------------------------------
SEGMENT PRESERVATION
--------------------------------
- Each input line (ID) MUST produce exactly ONE output line.
- Do NOT merge lines. Do NOT split lines.
- Do NOT translate proper names (people, places, brands) unless a widely accepted localization exists in {target}.
- Keep sound tags completely unchanged (e.g., [LAUGHING], [DOOR SLAMS]).

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------
Return ONLY the translated subtitles. No conversational filler. No markdown blocks. No explanations.
Keep the exact format:
ID|translated text

CRITICAL CONSTRAINTS:
- Do NOT change or reorder the ID numbers.
- Do NOT use the pipe symbol "|" inside the translated text itself.
- If a source line is empty or contains only punctuation/unintelligible noise, return the ID with an empty string (e.g., 2|).

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