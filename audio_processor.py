import os
import logging
import subprocess
from gtts import gTTS

logger = logging.getLogger(__name__)

def get_audio_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, creationflags=creationflags)
        return float(result.stdout.strip())
    except:
        return 0.0

def create_dubbed_audio(segments_data, original_video_path, output_audio_path, target_lang='vi'):
    logger.info(f"Đang tạo track lồng tiếng ({target_lang})...")
    temp_files = []
    try:
        inputs = []
        filter_complex = []
        mix_inputs = ""
        
        for i, seg in enumerate(segments_data):
            text = seg['text']
            start_ms = int(seg['start'] * 1000)
            end_ms = int(seg['end'] * 1000)
            allowed_duration = (end_ms - start_ms) / 1000.0 
            
            if not text.strip(): continue
            
            temp_tts = f"temp_tts_{i}.mp3"
            try:
                tts = gTTS(text, lang=target_lang)
                tts.save(temp_tts)
                temp_files.append(temp_tts)
                
                inputs.extend(["-i", temp_tts])
                
                tts_duration = get_audio_duration(temp_tts)
                speed_ratio = 1.0
                
                if tts_duration > allowed_duration and allowed_duration > 0:
                    speed_ratio = min(tts_duration / allowed_duration, 2.5) 
                    
                if speed_ratio > 1.05:
                    filter_complex.append(f"[{i}:a]atempo={speed_ratio:.2f},adelay={start_ms}|{start_ms}[a{i}]")
                else:
                    filter_complex.append(f"[{i}:a]adelay={start_ms}|{start_ms}[a{i}]")
                    
                mix_inputs += f"[a{i}]"
                
            except Exception as e:
                logger.warning(f"Bỏ qua đoạn lỗi '{text[:10]}': {e}")
        
        if not temp_files: return False

        num_inputs = len(temp_files)
        if num_inputs == 1:
            filter_complex.append(f"{mix_inputs}anull[aout]")
        else:
            # QUAN TRỌNG: Thêm normalize=0 để âm lượng không bị chia nhỏ khi trộn nhiều file!
            filter_complex.append(f"{mix_inputs}amix=inputs={num_inputs}:duration=longest:dropout_transition=0:normalize=0[aout]")
        
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_complex), "-map", "[aout]", output_audio_path]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
        process.communicate()
        
        return process.returncode == 0
        
    except Exception as e:
        logger.error(f"Lỗi tạo lồng tiếng: {e}")
        return False
    finally:
        for f in temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass