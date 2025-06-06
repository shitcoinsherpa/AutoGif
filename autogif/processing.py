import subprocess
import os
import re
from autogif import config
from faster_whisper import WhisperModel

def validate_time_format(time_str: str) -> bool:
    """Validates MM:SS.mmm format."""
    return bool(re.fullmatch(r"\d{2}:\d{2}\.\d{3}", time_str))

def time_to_seconds(time_str: str) -> float:
    """Converts MM:SS.mmm to seconds."""
    if not validate_time_format(time_str):
        raise ValueError("Invalid time format. Must be MM:SS.mmm")
    minutes, seconds_milliseconds = time_str.split(':')
    seconds, milliseconds = seconds_milliseconds.split('.')
    return int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000.0

def parse_color_to_pil_format(color_input):
    """
    Converts various color formats to PIL-compatible format.
    Handles hex, rgb(), rgba(), and CSS color names.
    Returns hex string or RGB tuple.
    """
    if not color_input:
        return "#FFFFFF"  # Default to white
    
    color_str = str(color_input).strip()
    
    # If it's already a hex color, return as-is
    if color_str.startswith('#') and len(color_str) in [4, 7]:
        return color_str
    
    # Handle rgba() format like "rgba(255, 0, 54.86158590292658, 1)"
    if color_str.startswith('rgba(') and color_str.endswith(')'):
        try:
            # Extract values from rgba(r, g, b, a)
            values_str = color_str[5:-1]  # Remove "rgba(" and ")"
            values = [float(v.strip()) for v in values_str.split(',')]
            if len(values) >= 3:
                r, g, b = int(values[0]), int(values[1]), int(values[2])
                # Clamp values to 0-255 range
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    # Handle rgb() format like "rgb(255, 0, 54)"
    if color_str.startswith('rgb(') and color_str.endswith(')'):
        try:
            values_str = color_str[4:-1]  # Remove "rgb(" and ")"
            values = [float(v.strip()) for v in values_str.split(',')]
            if len(values) >= 3:
                r, g, b = int(values[0]), int(values[1]), int(values[2])
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    # If it's a tuple or list, convert to hex
    if isinstance(color_input, (tuple, list)) and len(color_input) >= 3:
        try:
            r, g, b = int(color_input[0]), int(color_input[1]), int(color_input[2])
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    # If all else fails, assume it's a valid PIL color and return as-is
    # This handles CSS color names like "red", "blue", etc.
    return color_str

def download_video_segment(youtube_url: str, start_time: str, end_time: str, resolution: str, output_log_callback=None) -> tuple[str | None, str | None]:
    """
    Downloads a specific segment of a YouTube video using yt-dlp and ffmpeg.

    Args:
        youtube_url: The URL of the YouTube video.
        start_time: The start time of the segment (MM:SS.mmm).
        end_time: The end time of the segment (MM:SS.mmm).
        resolution: The target resolution (e.g., "480p", "720p").
        output_log_callback: A function to call with live output from the subprocess.

    Returns:
        A tuple (video_path, audio_path) or (None, None) if download fails.
    """
    if not os.path.exists(config.YT_DLP_PATH) or not os.path.exists(config.FFMPEG_PATH):
        if output_log_callback:
            output_log_callback("Error: yt-dlp or ffmpeg not found. Check resources directory.")
        return None, None

    if not validate_time_format(start_time) or not validate_time_format(end_time):
        if output_log_callback:
            output_log_callback("Error: Invalid start or end time format. Use MM:SS.mmm")
        return None, None

    try:
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)
        duration = end_seconds - start_seconds

        if duration <= 0:
            if output_log_callback:
                output_log_callback("Error: End time must be after start time.")
            return None, None
    except ValueError as e:
        if output_log_callback:
            output_log_callback(f"Error: {e}")
        return None, None

    # Ensure temp directory exists
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    base_filename = f"segment_{re.sub(r'[^a-zA-Z0-9]', '_', youtube_url[-11:])}_{start_time.replace(':', '').replace('.', '')}_{end_time.replace(':', '').replace('.', '')}"
    temp_full_video_path = os.path.join(config.TEMP_DIR, f"{base_filename}_full.mp4")
    video_output_path = os.path.join(config.TEMP_DIR, f"{base_filename}.mp4")
    audio_output_path = os.path.join(config.TEMP_DIR, f"{base_filename}.wav")

    if output_log_callback:
        output_log_callback(f"Starting download for {youtube_url} from {start_time} to {end_time} at {resolution}...")

    # For yt-dlp, resolution mapping: '240p' -> height=240, etc.
    height = resolution.replace('p', '')

    # Download full video then use ffmpeg to extract segment (most reliable method)
    cmd_video = [
        config.YT_DLP_PATH,
        "--quiet", "--no-warnings",
        "-f", f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best",
        "-o", temp_full_video_path,
        youtube_url
    ]
    
    try:
        process = subprocess.Popen(cmd_video, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=config.PROJECT_ROOT)
        if output_log_callback:
            output_log_callback("Downloading video...")
            for line in iter(process.stdout.readline, ''):
                output_log_callback(line.strip())
            process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0 or not os.path.exists(temp_full_video_path):
            if output_log_callback:
                output_log_callback("Error: Failed to download video.")
            return None, None
        
        # Use ffmpeg to extract the segment
        if output_log_callback:
            output_log_callback(f"Extracting segment from {start_time} to {end_time}...")
        
        cmd_extract = [
            config.FFMPEG_PATH,
            "-ss", start_time,                     # Seek to start time (ffmpeg accepts MM:SS.mmm format)
            "-i", temp_full_video_path,            # Input file
            "-t", str(duration),                   # Duration in seconds
            "-c", "copy",                          # Copy codecs (fast)
            "-avoid_negative_ts", "make_zero",    # Handle timestamp issues
            "-y",                                  # Overwrite
            video_output_path
        ]
        
        process_extract = subprocess.Popen(cmd_extract, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=config.PROJECT_ROOT)
        if output_log_callback:
            for line in iter(process_extract.stdout.readline, ''):
                output_log_callback(line.strip())
            process_extract.stdout.close()
        return_code_extract = process_extract.wait()
        
        # Clean up full video immediately
        if os.path.exists(temp_full_video_path):
            if output_log_callback:
                output_log_callback("Removing temporary full video file...")
            try:
                os.remove(temp_full_video_path)
            except Exception as e:
                if output_log_callback:
                    output_log_callback(f"Warning: Could not remove temp file: {e}")
        
        if return_code_extract != 0 or not os.path.exists(video_output_path):
            if output_log_callback:
                output_log_callback("Error: Failed to extract video segment.")
            return None, None
            
        if output_log_callback:
            output_log_callback(f"Video segment successfully created: {video_output_path}")

    except Exception as e:
        if output_log_callback:
            output_log_callback(f"Error during video download: {e}")
        # Clean up any temporary files
        if os.path.exists(temp_full_video_path):
            try: os.remove(temp_full_video_path)
            except: pass
        return None, None

    # Now extract audio from the downloaded video segment
    if output_log_callback:
        output_log_callback(f"Extracting audio from video segment...")
    cmd_audio_extract = [
        config.FFMPEG_PATH,
        "-i", video_output_path,
        "-vn",                    # No video
        "-acodec", "pcm_s16le",   # Standard WAV format
        "-ar", "16000",           # Whisper prefers 16kHz
        "-ac", "1",               # Mono
        "-y",                     # Overwrite output files
        audio_output_path
    ]

    try:
        process_audio = subprocess.Popen(cmd_audio_extract, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=config.PROJECT_ROOT)
        if output_log_callback:
            for line in iter(process_audio.stdout.readline, ''):
                output_log_callback(line.strip())
            process_audio.stdout.close()
        return_code_audio = process_audio.wait()

        if return_code_audio != 0:
            if output_log_callback:
                output_log_callback(f"ffmpeg audio extraction failed with exit code {return_code_audio}.")
            # Clean up downloaded video if audio extraction fails
            if os.path.exists(video_output_path): os.remove(video_output_path)
            return None, None
        if output_log_callback:
            output_log_callback(f"Audio extracted: {audio_output_path}")
        
        return video_output_path, audio_output_path

    except Exception as e:
        if output_log_callback:
            output_log_callback(f"Error during audio extraction: {e}")
        # Clean up downloaded video if audio extraction fails
        if os.path.exists(video_output_path): os.remove(video_output_path)
        return None, None

def transcribe_audio(audio_path: str, output_log_callback=None) -> list[dict]:
    """
    Transcribes audio using local Whisper binary and returns word-level timestamps.
    
    Args:
        audio_path: Path to the audio file (WAV format expected).
        output_log_callback: Optional callback for logging messages.
    
    Returns:
        List of dicts with word-level data: [{"word": str, "start": float, "end": float}, ...]
    """
    if output_log_callback:
        output_log_callback("Starting audio transcription with local Whisper binary...")
    
    if not os.path.exists(audio_path):
        if output_log_callback:
            output_log_callback(f"Error: Audio file not found: {audio_path}")
        return []
    
    # Look for local Whisper binary in resources
    whisper_binary_path = None
    possible_whisper_paths = [
        os.path.join(config.RESOURCES_DIR, "whisper-20240930", "whisper.exe" if os.name == 'nt' else "whisper"),
        os.path.join(config.RESOURCES_DIR, "whisper.exe" if os.name == 'nt' else "whisper"),
    ]
    
    for path in possible_whisper_paths:
        if os.path.exists(path):
            whisper_binary_path = path
            break
    
    if not whisper_binary_path:
        if output_log_callback:
            output_log_callback("Local Whisper binary not found, falling back to faster-whisper...")
        return transcribe_audio_fallback(audio_path, output_log_callback)
    
    try:
        if output_log_callback:
            output_log_callback(f"Using local Whisper binary: {whisper_binary_path}")
        
        # Create output JSON file path
        json_output_path = audio_path.replace('.wav', '_transcription.json')
        
        # Build whisper command with word timestamps
        cmd = [
            whisper_binary_path,
            audio_path,
            "--model", "base",
            "--language", "English", 
            "--output_format", "json",
            "--word_timestamps", "True",
            "--output_dir", os.path.dirname(json_output_path)
        ]
        
        if output_log_callback:
            output_log_callback("Running Whisper transcription...")
        
        # Run whisper
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1, universal_newlines=True, cwd=config.PROJECT_ROOT)
        
        if output_log_callback:
            for line in iter(process.stdout.readline, ''):
                line_stripped = line.strip()
                if line_stripped:
                    output_log_callback(f"Whisper: {line_stripped}")
            process.stdout.close()
        
        return_code = process.wait()
        
        if return_code != 0:
            if output_log_callback:
                output_log_callback(f"Whisper failed with exit code {return_code}, falling back to faster-whisper...")
            return transcribe_audio_fallback(audio_path, output_log_callback)
        
        # Read the JSON output
        if os.path.exists(json_output_path):
            import json
            with open(json_output_path, 'r', encoding='utf-8') as f:
                whisper_result = json.load(f)
            
            # Extract word-level data from Whisper JSON output
            word_data = []
            if 'segments' in whisper_result:
                for segment in whisper_result['segments']:
                    if 'words' in segment:
                        for word_info in segment['words']:
                            word_entry = {
                                "word": word_info.get('word', '').strip(),
                                "start": float(word_info.get('start', 0)),
                                "end": float(word_info.get('end', 0))
                            }
                            if word_entry["word"]:  # Only add non-empty words
                                word_data.append(word_entry)
            
            # Clean up JSON file
            try:
                os.remove(json_output_path)
            except:
                pass
            
            if output_log_callback:
                output_log_callback(f"Local Whisper transcription complete. Found {len(word_data)} words.")
                # Log first few words as sample
                if word_data:
                    sample_words = word_data[:5]
                    output_log_callback("Sample transcription:")
                    for w in sample_words:
                        output_log_callback(f"  '{w['word']}' @ {w['start']:.2f}s - {w['end']:.2f}s")
            
            return word_data
        else:
            if output_log_callback:
                output_log_callback("Whisper JSON output not found, falling back to faster-whisper...")
            return transcribe_audio_fallback(audio_path, output_log_callback)
            
    except Exception as e:
        if output_log_callback:
            output_log_callback(f"Error with local Whisper: {str(e)}, falling back to faster-whisper...")
        return transcribe_audio_fallback(audio_path, output_log_callback)

def transcribe_audio_fallback(audio_path: str, output_log_callback=None) -> list[dict]:
    """
    Fallback transcription using faster-whisper when local binary fails.
    """
    try:
        from faster_whisper import WhisperModel
        
        if output_log_callback:
            output_log_callback("Using faster-whisper fallback...")
        
        # Initialize the Whisper model
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        if output_log_callback:
            output_log_callback("Whisper model loaded. Processing audio...")
        
        # Transcribe with word-level timestamps
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            language="en",  # Force English detection
            word_timestamps=True,  # Critical for word-level timing
            vad_filter=True,  # Voice activity detection to remove silence
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        if output_log_callback:
            output_log_callback(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
        
        # Extract word-level data
        word_data = []
        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_entry = {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end
                    }
                    word_data.append(word_entry)
                    
                    # Log progress periodically
                    if len(word_data) % 10 == 0 and output_log_callback:
                        output_log_callback(f"Processed {len(word_data)} words...")
        
        if output_log_callback:
            output_log_callback(f"Fallback transcription complete. Found {len(word_data)} words.")
            
            # Log first few words as sample
            if word_data:
                sample_words = word_data[:5]
                output_log_callback("Sample transcription:")
                for w in sample_words:
                    output_log_callback(f"  '{w['word']}' @ {w['start']:.2f}s - {w['end']:.2f}s")
        
        return word_data
        
    except Exception as e:
        if output_log_callback:
            output_log_callback(f"Error during fallback transcription: {str(e)}")
            output_log_callback("Make sure faster-whisper is properly installed.")
        return []

def group_words_into_captions(word_segments: list[dict], max_chars: int = 80, max_duration_sec: float = 5.0, output_log_callback=None) -> list[dict]:
    """
    Groups word segments into captions based on sentence boundaries.
    ALWAYS breaks on sentence endings (periods, exclamation marks, question marks) 
    unless the resulting caption would be extremely short (< 0.5 seconds).
    Each caption will have 'text', 'start_time', 'end_time', 'words'.
    """
    if not word_segments:
        return []

    captions = []
    current_words_buffer = []
    current_text_buffer = ""
    current_start_time = 0.0

    def is_sentence_end(word: str) -> bool:
        """Check if word ends with sentence-ending punctuation"""
        return word.strip().endswith(('.', '!', '?'))

    for i, word_info in enumerate(word_segments):
        word_text = word_info["word"]
        word_start = word_info["start"]
        word_end = word_info["end"]

        if not current_words_buffer:  # Starting a new caption
            current_words_buffer.append(word_info)
            current_text_buffer = word_text
            current_start_time = word_start
        else:
            # Add the new word to see what the caption would look like
            potential_new_text = f"{current_text_buffer} {word_text}"
            potential_duration = word_end - current_start_time
            
            # Add the word to current caption
            current_words_buffer.append(word_info)
            current_text_buffer = potential_new_text

            # Check if we should break AFTER adding this word
            should_break = False
            break_reason = ""
            
            # Is this the last word? Must finalize
            is_last_word = (i == len(word_segments) - 1)
            if is_last_word:
                should_break = True
                break_reason = "end of text"
            
            # Does this word end a sentence?
            elif is_sentence_end(word_text):
                # Always break on sentence boundaries unless caption would be too short
                if potential_duration >= 0.5:  # Minimum 0.5 seconds
                    should_break = True
                    break_reason = "sentence boundary"
                # If too short, keep building (very rare case)
            
            # Extreme emergency break (should almost never happen)
            elif (len(potential_new_text) > max_chars * 5.0 or  # 400+ characters
                  potential_duration > max_duration_sec * 4.0):  # 20+ seconds
                should_break = True
                break_reason = "extreme limit exceeded"
                if output_log_callback:
                    output_log_callback(f"EMERGENCY: Breaking mid-sentence due to extreme limits: '{potential_new_text[:50]}...'")

            if should_break:
                # Finalize current caption
                captions.append({
                    "text": current_text_buffer,
                    "start_time": current_start_time,
                    "end_time": current_words_buffer[-1]["end"],
                    "words": list(current_words_buffer)
                })
                
                if output_log_callback:
                    output_log_callback(f"Caption break at {break_reason}: '{current_text_buffer}'")
                
                # Start new caption (empty, will be filled on next iteration)
                current_words_buffer = []
                current_text_buffer = ""
    
    if output_log_callback:
        output_log_callback(f"Grouped {len(word_segments)} words into {len(captions)} captions, breaking on sentence boundaries.")
        for idx, cap in enumerate(captions):
            output_log_callback(f"  Caption {idx+1}: '{cap['text']}'")

    return captions

def draw_text_with_outline(draw, position, text, font, font_color, outline_color, outline_width, anchor="mm", max_width=None):
    """Helper function to draw text with outline, handling different PIL versions, color formats, and multi-line text"""
    
    # Convert colors to PIL-compatible format
    pil_font_color = parse_color_to_pil_format(font_color)
    pil_outline_color = parse_color_to_pil_format(outline_color)
    
    # Handle multi-line text if max_width is specified
    if max_width and len(text) > 0:
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except AttributeError:
                # Fallback for older PIL versions
                line_width = draw.textsize(test_line, font=font)[0]
            
            if line_width <= max_width or not current_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate line height
        try:
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            line_height = bbox[3] - bbox[1]
        except AttributeError:
            line_height = draw.textsize("Ay", font=font)[1]
        
        # Calculate total text block height and adjust position
        total_height = len(lines) * line_height + (len(lines) - 1) * 4  # 4px line spacing
        
        # Adjust starting position based on anchor
        if anchor.endswith('s'):  # bottom anchor
            start_y = position[1] - total_height
        elif anchor.endswith('m'):  # middle anchor
            start_y = position[1] - total_height // 2
        else:  # top anchor
            start_y = position[1]
        
        # Draw each line
        for i, line in enumerate(lines):
            line_y = start_y + i * (line_height + 4)
            line_pos = (position[0], line_y)
            
            try:
                # Try modern PIL approach with stroke support
                if outline_width > 0:
                    draw.text(line_pos, line, font=font, fill=pil_font_color, anchor=anchor[0]+"t",
                             stroke_width=outline_width, stroke_fill=pil_outline_color)
                else:
                    draw.text(line_pos, line, font=font, fill=pil_font_color, anchor=anchor[0]+"t")
            except (TypeError, AttributeError):
                # Fallback for older PIL versions
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                outline_pos = (line_pos[0] + dx, line_pos[1] + dy)
                                draw.text(outline_pos, line, font=font, fill=pil_outline_color, anchor=anchor[0]+"t")
                draw.text(line_pos, line, font=font, fill=pil_font_color, anchor=anchor[0]+"t")
        
        return True
    
    # Single line text (original logic)
    try:
        # Try modern PIL approach with stroke support
        if hasattr(draw, "text") and hasattr(draw, "textbbox"):
            # Test if stroke_width parameter is supported
            draw.text(position, text, font=font, fill=pil_font_color, anchor=anchor,
                     stroke_width=outline_width, stroke_fill=pil_outline_color)
            return True
    except (TypeError, AttributeError):
        pass
    
    # Fallback to manual outline drawing for older PIL versions
    if outline_width > 0:
        # Draw outline by drawing text multiple times with offsets
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    outline_pos = (position[0] + dx, position[1] + dy)
                    draw.text(outline_pos, text, font=font, fill=pil_outline_color, anchor=anchor)
    
    # Draw main text
    draw.text(position, text, font=font, fill=pil_font_color, anchor=anchor)
    return True

def calculate_subtitle_duration(subtitles_data: list[dict]) -> float:
    """Calculate the total duration needed to display all subtitles."""
    if not subtitles_data:
        return 0.0
    
    # Find the latest end time among all words
    max_end_time = max(word["end"] for word in subtitles_data)
    return max_end_time

def calculate_required_frames(subtitles_data: list[dict], output_fps: int, buffer_seconds: float = 0.5) -> int:
    """Calculate the number of frames needed to display all subtitle data."""
    if not subtitles_data:
        return 1
    
    subtitle_duration = calculate_subtitle_duration(subtitles_data)
    total_duration_with_buffer = subtitle_duration + buffer_seconds
    required_frames = int(total_duration_with_buffer * output_fps) + 1  # +1 for inclusive end frame
    
    return required_frames

def generate_gif(
    video_path: str,
    subtitles_data: list[dict], # List of word dicts: {"word": ..., "start": ..., "end": ...}
    output_fps: int,
    target_height: int, # e.g. 480 for 480p
    typography_settings: dict, # {font_path, size, color, outline_color, outline_width}
    selected_effects: list[dict], # List of {"instance": effect_obj, "intensity": val, "enabled": bool}
    gif_filepath: str,
    output_log_callback=None,
    use_dithering: bool = False, # Disabled by default to avoid solarization
    loop_gif: bool = True, # Infinite repeat unless user disables (not in UI yet, but per spec)
    start_frame_num: int = 0, # 0-indexed, frame number of the *preview video*
    end_frame_num: int = -1   # 0-indexed, inclusive. -1 means to end of video
) -> str | None:
    """
    Generates the animated GIF with subtitles and effects from a selected frame range.

    Args:
        video_path: Path to the source video segment.
        subtitles_data: List of word timestamp dicts.
        output_fps: Target frames per second for the GIF.
        target_height: Target height for the GIF frames (e.g., 480 for 480p).
        typography_settings: Dict with font, size, color, outline details.
        selected_effects: List of effect configurations.
        gif_filepath: Full path for the output GIF.
        output_log_callback: Callback for logging messages.
        use_dithering: Whether to apply Floyd-Steinberg dithering (disabled by default to avoid solarization).
        loop_gif: Whether the GIF should loop infinitely.
        start_frame_num: 0-indexed, frame number of the *preview video*
        end_frame_num: 0-indexed, inclusive. -1 means to end of video

    Returns:
        Path to the generated GIF, or None on failure.
    """
    if output_log_callback: output_log_callback(f"Starting GIF generation for: {video_path}")

    # --- 1. Pre-processing & Setup ---
    if not os.path.exists(video_path):
        if output_log_callback: output_log_callback(f"Error: Video file not found: {video_path}")
        return None
    if not os.path.exists(config.FFMPEG_PATH):
        if output_log_callback: output_log_callback(f"Error: FFMPEG not found at {config.FFMPEG_PATH}")
        return None

    # Import necessary libraries for image manipulation (Pillow, OpenCV, imageio)
    try:
        import cv2
        from PIL import Image, ImageDraw, ImageFont
        import imageio
        import numpy as np
        import math
    except ImportError as e:
        if output_log_callback: output_log_callback(f"Error: Missing libraries for GIF generation (cv2, Pillow, imageio, numpy): {e}")
        return None

    # Group words into displayable captions (Section 6)
    if output_log_callback: output_log_callback(f"Grouping words into captions...")
    captions = group_words_into_captions(subtitles_data, max_chars=80, max_duration_sec=5.0, output_log_callback=output_log_callback)
    
    if subtitles_data:
        subtitle_end_time = calculate_subtitle_duration(subtitles_data)
        if output_log_callback:
            output_log_callback(f"Subtitle data extends to {subtitle_end_time:.2f}s")
        
        # Calculate the frame that should cover the last subtitle
        required_end_frame = math.ceil(subtitle_end_time * output_fps)
        
        # If end_frame_num is -1 or doesn't cover all subtitles, extend it
        if end_frame_num == -1 or (end_frame_num + 1) * (1.0 / output_fps) < subtitle_end_time:
            end_frame_num = required_end_frame
            if output_log_callback:
                output_log_callback(f"Extended end frame to {end_frame_num} to cover all subtitles")
    
    # Pre-calculate caption durations and padding needs
    for caption in captions:
        caption['natural_duration_sec'] = caption['end_time'] - caption['start_time']
        caption['required_min_duration_sec'] = max(2.0, 0.3 * len(caption.get('words', [])))
        caption['padding_needed_sec'] = max(0, caption['required_min_duration_sec'] - caption['natural_duration_sec'])
        caption['padding_applied'] = False # Flag to ensure padding is added only once
        if output_log_callback and caption['padding_needed_sec'] > 0:
            output_log_callback(f"Caption '{caption['text'][:20]}...' needs {caption['padding_needed_sec']:.2f}s padding.")

    # Load font
    font_name_from_settings = typography_settings.get("font_family", "Consolas") # Default to Consolas as per spec (Section 4)
    font_size = typography_settings.get("font_size_pt", 24)
    font_color = typography_settings.get("font_color_hex", "#00FF41")
    outline_color_hex = typography_settings.get("outline_color_hex", "#004400")
    outline_width = typography_settings.get("outline_width_px", 2)
    
    # Debug color formats
    if output_log_callback:
        output_log_callback(f"Font color input: {font_color} (type: {type(font_color)})")
        output_log_callback(f"Outline color input: {outline_color_hex} (type: {type(outline_color_hex)})")
    
    pil_font = None
    # Attempt to load the specified font from the bundled fonts directory
    potential_font_filenames = [
        f"{font_name_from_settings}.ttf", 
        f"{font_name_from_settings}.otf",
        font_name_from_settings # If the name itself includes extension
    ]

    font_path_loaded = None
    for fname in potential_font_filenames:
        prospective_path = os.path.join(config.FONTS_DIR, fname)
        if os.path.exists(prospective_path):
            try:
                pil_font = ImageFont.truetype(prospective_path, font_size)
                font_path_loaded = prospective_path
                if output_log_callback: output_log_callback(f"Successfully loaded font: {font_path_loaded} at size {font_size}pt")
                break
            except IOError as e:
                if output_log_callback: output_log_callback(f"Warning: Found font file {prospective_path} but failed to load: {e}")
                continue # Try next potential name
    
    if not pil_font:
        if output_log_callback: output_log_callback(f"Warning: Specified font '{font_name_from_settings}' not found in {config.FONTS_DIR}. Attempting fallback.")
        try:
            # Fallback to a very generic system font if bundled one fails (should not happen if fonts are bundled correctly)
            pil_font = ImageFont.truetype("arial.ttf", font_size) # Common fallback
            if output_log_callback: output_log_callback(f"Using fallback system font Arial at size {font_size}pt.")
        except IOError:
            # Load default font with smaller size as fallback
            pil_font = ImageFont.load_default()
            if output_log_callback: output_log_callback(f"CRITICAL: Fallback {font_name_from_settings} font not found. Using basic PIL default font. Please ensure fonts are correctly bundled.")

    # --- 2. Video Frame Processing ---
    if output_log_callback: output_log_callback("Opening video file with OpenCV...")
    cap = cv2.VideoCapture(video_path) # video_path is the *original* downloaded segment
    if not cap.isOpened():
        if output_log_callback: output_log_callback("Error: Could not open video file.")
        return None

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_source_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if source_fps <= 0: 
        if output_log_callback: output_log_callback(f"Warning: Source FPS is invalid ({source_fps}), assuming 25.")
        source_fps = 25 
    
    # Calculate proper time range that ensures all subtitle data is captured
    start_time_seconds = start_frame_num / output_fps
    
    # Calculate end time ensuring we capture all subtitle data
    if end_frame_num == -1:
        # Use the duration needed for all subtitle data plus buffer
        subtitle_duration = calculate_subtitle_duration(subtitles_data)
        end_time_seconds = subtitle_duration + 1.0  # Increased buffer to 1.0s
        # Update end_frame_num based on this calculation
        end_frame_num = math.ceil(end_time_seconds * output_fps)
    else:
        # User specified exact end frame - respect their choice
        # Convert frame number to time (end_frame_num is inclusive, so we need +1 to get the time AFTER the last frame)
        user_requested_end_time = (end_frame_num + 1) / output_fps
    
        # Only extend if subtitle data goes beyond user's request
        subtitle_duration = calculate_subtitle_duration(subtitles_data) if subtitles_data else 0
        if subtitle_duration > 0 and user_requested_end_time < subtitle_duration:
            end_time_seconds = subtitle_duration + 0.5  # Smaller buffer when extending
            end_frame_num = math.ceil(end_time_seconds * output_fps)
            if output_log_callback:
                output_log_callback(f"Extended end time from {user_requested_end_time:.2f}s to {end_time_seconds:.2f}s to cover subtitle ending at     {subtitle_duration:.2f}s")
        else:
            # Use exactly what the user requested, no extra buffer
            end_time_seconds = user_requested_end_time
    
    if output_log_callback:
        output_log_callback(f"Selected time range: {start_time_seconds:.2f}s to {end_time_seconds:.2f}s")
        output_log_callback(f"Processing subtitles in time range: {start_time_seconds:.2f}s to {end_time_seconds:.2f}s")
    
    # Filter subtitles to only include those within the selected time range
    active_subtitles = []
    for word_info in subtitles_data:
        word_start = word_info["start"]
        word_end = word_info["end"]
        # Include words that overlap with the selected time range
        if (word_start < end_time_seconds and word_end > start_time_seconds):
            active_subtitles.append(word_info)
    
    if output_log_callback:
        output_log_callback(f"Found {len(active_subtitles)} subtitle words in selected time range")
        for i, word in enumerate(active_subtitles[:5]):  # Log first 5 words
            output_log_callback(f"  Word {i+1}: '{word['word']}' @ {word['start']:.2f}s - {word['end']:.2f}s")
        if len(active_subtitles) > 5:
            last_word = active_subtitles[-1]
            output_log_callback(f"  Last word: '{last_word['word']}' @ {last_word['start']:.2f}s - {last_word['end']:.2f}s")
    
    # Now that we have source_fps, update the natural_end_source_frame_idx for each caption
    for caption in captions:
        caption['natural_end_source_frame_idx'] = int(caption['end_time'] * source_fps) 
    
    # skip_factor is based on original source_fps and target output_fps for the GIF
    # This determines which frames from the *original video* are candidates.
    gif_frame_skip_factor = max(1, int(np.ceil(source_fps / output_fps)))

    # Map frame numbers correctly to source video timing
    # We need to process frames from start_time_seconds to end_time_seconds
    actual_start_source_frame_idx = int(start_time_seconds * source_fps)
    actual_end_source_frame_idx = int(end_time_seconds * source_fps)
    
    # Ensure we don't exceed video bounds
    actual_end_source_frame_idx = min(actual_end_source_frame_idx, total_source_frames - 1)

    if actual_start_source_frame_idx >= total_source_frames or actual_start_source_frame_idx > actual_end_source_frame_idx:
        if output_log_callback: output_log_callback(f"Error: Invalid frame range after mapping to source. Start: {actual_start_source_frame_idx}, End: {actual_end_source_frame_idx}, Total: {total_source_frames}")
        cap.release()
        return None

    if output_log_callback: 
        output_log_callback(f"Source video: {source_width}x{source_height} @ {source_fps:.2f} FPS ({total_source_frames} frames)")
        output_log_callback(f"Target GIF: up to height {target_height} @ {output_fps} FPS")
        output_log_callback(f"Selected preview frame range: {start_frame_num} to {end_frame_num}")
        output_log_callback(f"Time range: {start_time_seconds:.2f}s to {end_time_seconds:.2f}s")
        output_log_callback(f"Mapping to source video frame range: {actual_start_source_frame_idx} to {actual_end_source_frame_idx} (inclusive)")
        output_log_callback(f"Source frame skip factor for GIF: {gif_frame_skip_factor}")
        if subtitles_data:
            last_word_end = max(word["end"] for word in subtitles_data)
            output_log_callback(f"Last subtitle word ends at: {last_word_end:.2f}s")
            expected_frames_needed = math.ceil(last_word_end * output_fps)
            output_log_callback(f"Expected frames needed to cover all subtitles: {expected_frames_needed}")

    # Separate effects into text effects and full-frame effects
    text_effects_configs = []
    full_frame_effects_configs = []
    
    for effect_config in selected_effects:
        if effect_config.get("enabled", False):
            instance = effect_config.get("instance")
            if instance:
                effect_config_dict = {
                    "instance": instance, 
                    "intensity": effect_config.get("intensity", 50),
                    "slug": instance.slug
                }
                
                # Check if this is a full-frame effect (like VHS/CRT)
                if instance.slug == "vhs-crt":
                    full_frame_effects_configs.append(effect_config_dict)
                else:
                    text_effects_configs.append(effect_config_dict)

    processed_frames_for_gif = []
    # frame_read_count tracks frames read from the *original* video segment.
    frame_read_count = 0 
    # gif_frame_count tracks frames *added* to the GIF (after skipping and deduplication).
    gif_frame_count = 0 
    # output_gif_frame_idx tracks conceptual *output* frames for the GIF (before deduplication, relative to start_frame_num)
    output_gif_frame_idx = 0

    if output_log_callback: output_log_callback("Processing video frames...")
    
    # Seek to the starting source frame if possible (OpenCV supports this)
    if actual_start_source_frame_idx > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, actual_start_source_frame_idx)
        frame_read_count = actual_start_source_frame_idx # Update our counter
        if output_log_callback: output_log_callback(f"Seeked source video to frame: {actual_start_source_frame_idx}")

    while True:
        # Check if we've reached the end of our desired range
        if frame_read_count > actual_end_source_frame_idx:
            if output_log_callback: output_log_callback(f"Reached end of selected source frame range ({actual_end_source_frame_idx}).")
            break # End of selected segment

        ret, frame = cap.read()
        if not ret:
            if output_log_callback: output_log_callback(f"Could not read frame {frame_read_count} from source, or end of video reached.")
            break
        
        # This frame (frame_read_count) is a candidate from the source video.
        # We now apply the gif_frame_skip_factor relative to the *start of our segment*.
        if (frame_read_count - actual_start_source_frame_idx) % gif_frame_skip_factor != 0:
            frame_read_count += 1
            continue # Skip this source frame based on target GIF FPS

        # Calculate the time of this frame based on its position in the source video
        current_source_frame_time = frame_read_count / source_fps

        # Keep video frame as RGB - don't convert to RGBA unnecessarily
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Resize frame (maintaining aspect ratio) to fit target_height
        original_width, original_height = pil_frame.size
        if original_height > target_height:
            aspect_ratio = original_width / original_height
            new_height = target_height
            new_width = int(new_height * aspect_ratio)
            pil_frame = pil_frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_width, new_height = original_width, original_height

        # Find active caption at this time - ALL effects use full captions
        active_caption = None
        active_caption_text_for_frame = None
        
        for caption in captions:
            if caption['start_time'] <= current_source_frame_time < caption['end_time']:
                active_caption = caption
                active_caption_text_for_frame = caption['text']
                break
        
        # Find words active at this specific time for word-level effects
        active_words_at_time = [
            word for word in active_subtitles 
            if word["start"] <= current_source_frame_time <= word["end"]
        ]
        
        if output_log_callback and output_gif_frame_idx % (output_fps * 2) == 0:  # Log every 2 seconds
            # Determine rendering mode for logging
            has_word_level_effects_enabled = any(
                hasattr(effect_config["instance"], "supports_word_level") and effect_config["instance"].supports_word_level
                for effect_config in text_effects_configs
            )
            has_explicit_word_effects = any(
                word.get("word_effects", {}).get("effects") 
                for word in active_words_at_time
            )
            effect_mode = "word-level" if (has_word_level_effects_enabled or has_explicit_word_effects) and active_caption else "caption-based"
            
            active_words_debug = [w["word"] for w in active_words_at_time]
            output_log_callback(f"GIF Frame {output_gif_frame_idx}: time={current_source_frame_time:.2f}s, mode={effect_mode}, active_words={active_words_debug}, text='{active_caption_text_for_frame[:30] if active_caption_text_for_frame else 'None'}...'")
        
        if active_caption_text_for_frame or active_words_at_time:
            try:
                # --- Text Rendering & Effects on a Separate Canvas --- 
                text_canvas = Image.new("RGBA", (new_width, new_height), (0,0,0,0))
                draw_on_text_canvas = ImageDraw.Draw(text_canvas)

                initial_text_anchor_x = new_width / 2
                initial_text_anchor_y = new_height * 0.90
                base_text_position_on_canvas = (int(initial_text_anchor_x), int(initial_text_anchor_y))

                try: # Outer try for all text rendering and effects on canvas
                    # Check if we should use word-level rendering
                    has_word_level_effects_enabled = any(
                        hasattr(effect_config["instance"], "supports_word_level") and effect_config["instance"].supports_word_level
                        for effect_config in text_effects_configs
                    )
                    
                    # Also check if any words have explicit word-level effects data (same as preview)
                    has_explicit_word_effects = any(
                        word.get("word_effects", {}).get("effects") 
                        for word in active_words_at_time
                    )
                    
                    use_word_level_rendering = has_word_level_effects_enabled or has_explicit_word_effects
                    
                    if use_word_level_rendering and active_caption:
                        # Use word-level rendering with complete caption words (same as preview)
                        complete_caption_words = active_caption.get('words', [])
                        
                        font_settings = {
                            "font": pil_font,
                            "font_color": font_color,
                            "outline_color": outline_color_hex,
                            "outline_width": outline_width
                        }
                        frame_settings = {
                            "frame_width": new_width,
                            "frame_height": new_height,
                            "base_y": int(initial_text_anchor_y),
                            "output_fps": output_fps
                        }
                        
                        text_canvas = render_word_level_effects(
                            complete_caption_words,
                            text_effects_configs,
                            text_canvas,
                            font_settings,
                            frame_settings,
                            output_gif_frame_idx,
                            output_log_callback
                        )
                    else:
                        # Standard caption-level rendering
                        # Only skip normal text rendering for certain effects (like typewriter)
                        skip_normal_text = False
                        word_level_effects = {"typewriter"}
                        for effect_config_item in text_effects_configs:
                            if effect_config_item["slug"] in word_level_effects:
                                skip_normal_text = True
                                break
                        
                        # 1. Draw initial text (with outline) on text_canvas ONLY if no text-drawing effect is active
                        if not skip_normal_text and active_caption_text_for_frame:
                            draw_text_with_outline(
                                draw_on_text_canvas, 
                                base_text_position_on_canvas, 
                                active_caption_text_for_frame,
                                pil_font, 
                                font_color, 
                                outline_color_hex, 
                                outline_width, 
                                anchor="ms",
                                max_width=int(new_width * 0.9)  # Allow text to use 90% of frame width
                            )

                        # 2. Apply caption-level text effects to text_canvas (only for non-word-level rendering)
                        current_canvas_for_effects = text_canvas 
                        if text_effects_configs and active_caption_text_for_frame: 
                            if output_log_callback and gif_frame_count % (output_fps * 5) == 0: 
                                output_log_callback(f"Applying caption-level text effects to text canvas for frame {gif_frame_count}...")
                        
                            # For effects, we need to find which caption this frame belongs to for proper timing
                            # active_caption is already set above based on effect type
                            
                            # Need to track when this caption started in the GIF frame sequence
                            caption_start_gif_frame_for_effect = 0
                            if active_caption:
                                for prev_cap in captions:
                                    if prev_cap == active_caption:
                                        break
                                    # Calculate frames this previous caption would have used
                                    prev_cap_natural_frames = int((prev_cap['end_time'] - prev_cap['start_time']) * output_fps)
                                    caption_start_gif_frame_for_effect += prev_cap_natural_frames
                            
                            relative_frame_idx_for_caption_effect = max(0, output_gif_frame_idx - caption_start_gif_frame_for_effect)

                            for effect_config_item in text_effects_configs:
                                effect_instance = effect_config_item["instance"]
                                effect_intensity = effect_config_item["intensity"]
                                effect_slug = effect_config_item["slug"]
                                
                                # Skip word-level effects in caption-level rendering
                                if hasattr(effect_instance, "supports_word_level") and effect_instance.supports_word_level:
                                    continue
                                
                                # Prepare the effect for this specific caption
                                try:
                                    if active_caption:
                                        effect_instance.prepare(
                                            target_fps=output_fps, 
                                            caption_natural_duration_sec=active_caption['natural_duration_sec'], 
                                            text_length=len(active_caption_text_for_frame),
                                            intensity=effect_intensity # Pass intensity to prepare as well, if needed by effect
                                        )
                                    else:
                                        # No active caption, use default values
                                        effect_instance.prepare(
                                            target_fps=output_fps, 
                                            caption_natural_duration_sec=1.0, 
                                            text_length=len(active_caption_text_for_frame),
                                            intensity=effect_intensity
                                        )
                                except Exception as e_prepare_dyn:
                                    if output_log_callback: output_log_callback(f"Error dynamically preparing effect {effect_slug}: {e_prepare_dyn}")
                                    continue # Skip this effect for this frame/caption

                                try:
                                    # Ensure canvas is RGBA before passing to effect
                                    if current_canvas_for_effects.mode != "RGBA":
                                        current_canvas_for_effects = current_canvas_for_effects.convert("RGBA")
                                        
                                    transformed_canvas = effect_instance.transform(
                                        frame_image=current_canvas_for_effects.copy(), 
                                        text=active_caption_text_for_frame, 
                                        base_position=base_text_position_on_canvas, 
                                        current_frame_index=relative_frame_idx_for_caption_effect, # Use relative index
                                        intensity=effect_intensity,
                                        font=pil_font, font_color=font_color, 
                                        outline_color=outline_color_hex, outline_width=outline_width,
                                        frame_width=new_width, frame_height=new_height, 
                                        text_anchor_x=initial_text_anchor_x, 
                                        text_anchor_y=initial_text_anchor_y,
                                        # Pass caption_start_gif_frame_for_effect if effects need to know their global start on GIF
                                        caption_start_frame_for_gif=caption_start_gif_frame_for_effect,
                                        target_fps=output_fps  # For pulsing effects
                                    )
                                    if transformed_canvas is not None and isinstance(transformed_canvas, Image.Image):
                                        # Ensure result is RGBA for consistent handling
                                        if transformed_canvas.mode != "RGBA":
                                            transformed_canvas = transformed_canvas.convert("RGBA")
                                        current_canvas_for_effects = transformed_canvas
                                except Exception as e_transform_canvas:
                                    if output_log_callback:
                                        output_log_callback(f"Error applying effect {effect_instance.display_name} to text canvas: {e_transform_canvas}")
                            
                            text_canvas = current_canvas_for_effects

                    # 3. Calculate bounding box and determine y_offset for text_canvas
                    y_offset_for_compositing = 0
                    bbox = text_canvas.getbbox()
                    if bbox:
                        content_bottom_y = bbox[3]
                        target_frame_bottom_edge = new_height - 1 
                        if content_bottom_y > target_frame_bottom_edge: 
                            y_offset_for_compositing = target_frame_bottom_edge - content_bottom_y 
                            if output_log_callback: 
                                output_log_callback(f"Text canvas content bottom: {content_bottom_y}, frame height: {new_height}. Shifting canvas by {y_offset_for_compositing}px.")
                    # If bbox is None (empty canvas), y_offset_for_compositing remains 0

                    # 4. Composite text_canvas onto pil_frame with the calculated y_offset
                    # Convert base frame to RGBA temporarily for compositing
                    pil_frame_rgba = pil_frame.convert("RGBA")
                    pil_frame_rgba.alpha_composite(text_canvas, (0, int(y_offset_for_compositing)))
                    # Convert back to RGB for final output
                    pil_frame = pil_frame_rgba.convert("RGB")
                except Exception as e_canvas_processing: # Catch errors from text drawing, effects, or bbox logic
                    if output_log_callback: output_log_callback(f"Error during text canvas processing: {e_canvas_processing}")
                    # pil_frame remains the clean video frame if canvas processing fails catastrophically before composite
            
            except Exception as e_text_render:
                if output_log_callback: output_log_callback(f"Error rendering text: {e_text_render}")

        # NOW APPLY FULL-FRAME EFFECTS (like VHS/CRT) to the complete frame with text composited
        if full_frame_effects_configs:
            for effect_config_item in full_frame_effects_configs:
                effect_instance = effect_config_item["instance"]
                effect_intensity = effect_config_item["intensity"]
                effect_slug = effect_config_item["slug"]
                
                try:
                    # Prepare the full-frame effect
                    effect_instance.prepare(
                        target_fps=output_fps, 
                        caption_natural_duration_sec=2.0,  # Default duration for full-frame effects
                        text_length=len(active_caption_text_for_frame) if active_caption_text_for_frame else 0,
                        intensity=effect_intensity
                    )
                    
                    # Apply the effect to the full frame (video + text)
                    pil_frame = effect_instance.transform(
                        frame_image=pil_frame,
                        text=active_caption_text_for_frame or "",
                        base_position=(new_width // 2, new_height // 2),
                        current_frame_index=output_gif_frame_idx,
                        intensity=effect_intensity,
                        font=pil_font,
                        font_color=font_color,
                        outline_color=outline_color_hex,
                        outline_width=outline_width,
                        frame_width=new_width,
                        frame_height=new_height,
                        text_anchor_x=new_width // 2,
                        text_anchor_y=int(new_height * 0.90),
                        target_fps=output_fps
                    )
                    
                    if output_log_callback and gif_frame_count % (output_fps * 5) == 0:
                        output_log_callback(f"Applied full-frame effect {effect_slug} to frame {gif_frame_count}")
                        
                except Exception as e_full_frame_effect:
                    if output_log_callback:
                        output_log_callback(f"Error applying full-frame effect {effect_slug}: {e_full_frame_effect}")

        # Keep frame as RGB - no palette conversion needed
        # This avoids solarization issues from palette conversion
        final_rgb_frame = pil_frame.convert("RGB")

        current_gif_frame_duration = 1.0 / output_fps
        padding_applied_this_frame = False

        # Apply padding logic based on the active caption
        if active_caption:
            for cap_idx, caption in enumerate(captions):
                if (caption == active_caption and 
                    not caption['padding_applied'] and 
                    caption['padding_needed_sec'] > 0 and
                    current_source_frame_time >= caption['end_time'] - (1.0 / output_fps)):  # Near end of caption
                    
                    padding_duration_for_this_caption = caption['padding_needed_sec']
                    current_gif_frame_duration += padding_duration_for_this_caption
                    captions[cap_idx]['padding_applied'] = True 
                    padding_applied_this_frame = True
                    if output_log_callback: 
                        output_log_callback(f"Applied {padding_duration_for_this_caption:.2f}s padding to GIF frame {output_gif_frame_idx} for caption '{caption['text'][:20]}...'")
                    break
        
        # Add frame to GIF (no duplicate detection)
        processed_frames_for_gif.append({"image": final_rgb_frame, "duration": current_gif_frame_duration})
        gif_frame_count += 1
        
        output_gif_frame_idx += 1 # This always increments for each frame *selected for processing* for the GIF

        if output_log_callback and output_gif_frame_idx % output_fps == 0: 
            output_log_callback(f"Processed up to GIF frame {output_gif_frame_idx} ({output_gif_frame_idx/output_fps:.1f}s). Total frames in GIF: {gif_frame_count}")
        
        frame_read_count += 1 # Crucial: increment after processing the current frame

    cap.release()
    if output_log_callback: output_log_callback(f"Finished processing video. Total GIF frames: {gif_frame_count}")

    # --- 4. GIF Saving (Section 7) ---
    if not processed_frames_for_gif:
        if output_log_callback: output_log_callback("Error: No frames were processed for the GIF.")
        return None

    if output_log_callback: output_log_callback(f"Saving GIF to {gif_filepath}...")
    try:
        # Separate frames and their calculated durations for imageio
        final_frames_list = [item["image"] for item in processed_frames_for_gif]
        final_durations_list = [item["duration"] for item in processed_frames_for_gif]

        if not final_frames_list:
            if output_log_callback: output_log_callback("Error: No frames in final list to save.")
            return None

        imageio.mimsave(gif_filepath, final_frames_list, duration=final_durations_list, loop=0 if loop_gif else 1)
        # loop=0 means infinite loop for imageio
        if output_log_callback: output_log_callback(f"GIF saved successfully: {gif_filepath}")
        return gif_filepath
    except Exception as e:
        if output_log_callback: output_log_callback(f"Error saving GIF: {e}")
        return None

def render_preview_video(
    video_path: str,
    subtitles_data: list[dict],
    output_fps: int,
    target_height: int, 
    typography_settings: dict,
    selected_effects: list[dict],
    preview_video_filepath: str,
    output_log_callback=None
) -> tuple[str | None, int]:
    """
    Renders the video segment with all subtitles and effects applied, outputting an MP4 video.
    This is similar to generate_gif but without GIF-specific optimizations and outputs MP4.

    Args:
        video_path: Path to the source video segment.
        subtitles_data: List of word timestamp dicts.
        output_fps: Target frames per second for the preview video.
        target_height: Target height for the preview video frames.
        typography_settings: Dict with font, size, color, outline details.
        selected_effects: List of effect configurations.
        preview_video_filepath: Full path for the output preview MP4 video.
        output_log_callback: Callback for logging messages.

    Returns:
        A tuple (path_to_preview_video, total_frames_in_preview) or (None, 0) on failure.
    """
    if output_log_callback: output_log_callback(f"Starting Preview Video generation for: {video_path}")

    # --- 1. Pre-processing & Setup (Similar to generate_gif) ---
    if not os.path.exists(video_path):
        if output_log_callback: output_log_callback(f"Error: Video file not found: {video_path}")
        return None, 0
    
    try:
        import cv2
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        import subprocess  # Added for ffmpeg call
        import math
    except ImportError as e:
        if output_log_callback: output_log_callback(f"Error: Missing libraries for video rendering (cv2, Pillow, numpy): {e}")
        return None, 0

    if output_log_callback: output_log_callback(f"Grouping words into captions for preview...")
    captions = group_words_into_captions(subtitles_data, max_chars=80, max_duration_sec=5.0, output_log_callback=output_log_callback)

    # Load font (copied from generate_gif, ensure it's robust)
    font_name_from_settings = typography_settings.get("font_family", "Consolas")
    font_size = typography_settings.get("font_size_pt", 24)
    font_color = typography_settings.get("font_color_hex", "#00FF41")
    outline_color_hex = typography_settings.get("outline_color_hex", "#004400")
    outline_width = typography_settings.get("outline_width_px", 2)
    
    # Debug color formats for preview too
    if output_log_callback:
        output_log_callback(f"Preview font color input: {font_color} (type: {type(font_color)})")
        output_log_callback(f"Preview outline color input: {outline_color_hex} (type: {type(outline_color_hex)})")
    
    pil_font = None
    potential_font_filenames = [f"{font_name_from_settings}.ttf", f"{font_name_from_settings}.otf", font_name_from_settings]
    for fname in potential_font_filenames:
        prospective_path = os.path.join(config.FONTS_DIR, fname)
        if os.path.exists(prospective_path):
            try:
                pil_font = ImageFont.truetype(prospective_path, font_size)
                if output_log_callback: output_log_callback(f"Preview: Loaded font: {prospective_path}")
                break
            except IOError: continue
    if not pil_font:
        try: pil_font = ImageFont.truetype("arial.ttf", font_size)
        except IOError: pil_font = ImageFont.load_default()
        if output_log_callback: output_log_callback(f"Preview: Using fallback/default font.")
    if not pil_font: # Absolute failure
        if output_log_callback: output_log_callback("CRITICAL ERROR: Could not load any font for preview.")
        return None, 0

    # --- 2. Video Frame Processing (Similar to generate_gif but writes to MP4) ---
    if output_log_callback: output_log_callback("Opening video file for preview processing...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        if output_log_callback: output_log_callback("Error: Could not open video file for preview.")
        return None, 0

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_source_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if source_fps <= 0: source_fps = 25 

    skip_factor = max(1, int(np.ceil(source_fps / output_fps)))
    
    # Calculate the required frames to cover all subtitle data
    required_frames = calculate_required_frames(subtitles_data, output_fps, buffer_seconds=1.0)  # Increased buffer
    max_possible_frames = int(total_source_frames / skip_factor)
    
    # Calculate end time for subtitle coverage
    end_time_seconds = 0
    if subtitles_data:
        subtitle_duration = calculate_subtitle_duration(subtitles_data)
        end_time_seconds = subtitle_duration + 1.0  # Increased buffer to 1.0s
    else:
        end_time_seconds = total_source_frames / source_fps
    
    # Use the minimum of required frames and maximum possible frames
    target_preview_frames = min(required_frames, max_possible_frames)
    
    if output_log_callback:
        subtitle_duration = calculate_subtitle_duration(subtitles_data)
        output_log_callback(f"Preview Source: {source_width}x{source_height}@{source_fps:.2f}FPS. Target: height {target_height}@{output_fps}FPS (skip: {skip_factor})")
        output_log_callback(f"Subtitle duration: {subtitle_duration:.2f}s, required frames: {required_frames}, target frames: {target_preview_frames}")

    # Prepare to write frames to a temporary directory
    import tempfile
    temp_frames_dir = tempfile.mkdtemp(prefix="autogif_preview_frames_")
    if output_log_callback: output_log_callback(f"Using temporary frames directory: {temp_frames_dir}")

    frame_read_count = 0
    preview_frame_count = 0

    # Separate effects into text effects and full-frame effects
    text_effects_configs = []
    full_frame_effects_configs = []
    
    for effect_config in selected_effects:
        if effect_config.get("enabled", False):
            instance = effect_config.get("instance")
            if instance:
                effect_config_dict = {
                    "instance": instance, 
                    "intensity": effect_config.get("intensity", 50),
                    "slug": instance.slug
                }
                
                # Check if this is a full-frame effect (like VHS/CRT)
                if instance.slug == "vhs-crt":
                    full_frame_effects_configs.append(effect_config_dict)
                else:
                    text_effects_configs.append(effect_config_dict)

    if output_log_callback: output_log_callback("Processing frames for preview video...")
    
    # --- 3. Main Frame Loop for Preview Video ---
    # Calculate target frames based on subtitle data, not just skip factor
    max_time_needed = end_time_seconds if subtitles_data else (total_source_frames / source_fps)
    max_source_frames_needed = min(int(max_time_needed * source_fps) + skip_factor, total_source_frames)  # Add buffer
    target_preview_frames = min(required_frames, int(max_source_frames_needed / skip_factor) + 1)
    
    if output_log_callback:
        output_log_callback(f"Max time needed: {max_time_needed:.2f}s, max source frames: {max_source_frames_needed}, target preview frames: {target_preview_frames}")
    
    frame_count_limit = target_preview_frames
    source_frame_limit = max_source_frames_needed
    
    while preview_frame_count < frame_count_limit and frame_read_count < source_frame_limit:
        ret, frame = cap.read()
        if not ret: 
            if output_log_callback: output_log_callback(f"End of video reached at frame {frame_read_count}")
            break
        
        # This frame (frame_read_count) is a candidate from the source video.
        # We now apply the skip_factor relative to the *start of our segment*.
        if frame_read_count % skip_factor != 0:
            frame_read_count += 1
            continue # Skip this source frame based on target preview FPS

        # Calculate time based on actual source frame position (same as GIF)
        current_source_frame_time = frame_read_count / source_fps
        
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        original_width, original_height = pil_frame.size
        if original_height > target_height:
            aspect_ratio = original_width / original_height
            new_height = target_height
            new_width = int(new_height * aspect_ratio)
            pil_frame = pil_frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_width, new_height = original_width, original_height

        # Find active caption at this time - ALL effects use full captions
        active_caption = None
        active_caption_text_for_frame = None
        
        for caption in captions:
            if caption['start_time'] <= current_source_frame_time < caption['end_time']:
                active_caption = caption
                active_caption_text_for_frame = caption['text']
                break
        # Find words active at this specific time for word-level effects (preview)
        active_words_at_time = [
            word for word in subtitles_data 
            if word["start"] <= current_source_frame_time <= word["end"]
        ]
        
        # Text & Effects rendering (using the separate canvas method from generate_gif)
        if active_caption_text_for_frame or active_words_at_time:
            text_canvas = Image.new("RGBA", (new_width, new_height), (0,0,0,0))
            draw_on_text_canvas = ImageDraw.Draw(text_canvas)
            initial_text_anchor_x = new_width / 2
            initial_text_anchor_y = new_height * 0.90
            base_text_position_on_canvas = (int(initial_text_anchor_x), int(initial_text_anchor_y))

            try: # Text drawing and effects on canvas
                # Initialize skip_normal_text early to avoid scope issues
                skip_normal_text = False
                
                # Check if we should use word-level rendering for preview
                # Use same logic as GIF rendering: check if word-level effects are enabled globally
                has_word_level_effects_enabled = any(
                    hasattr(effect_config["instance"], "supports_word_level") and effect_config["instance"].supports_word_level
                    for effect_config in text_effects_configs
                )
                
                # Also check if any words have explicit word-level effects data
                has_explicit_word_effects = any(
                    word.get("word_effects", {}).get("effects") 
                    for word in active_words_at_time
                )
                
                use_word_level_rendering = has_word_level_effects_enabled or has_explicit_word_effects
                
                if use_word_level_rendering and active_caption:
                    # Use word-level rendering for preview with complete caption words
                    skip_normal_text = True  # Word-level effects handle their own text rendering
                    complete_caption_words = active_caption.get('words', [])
                    
                    font_settings = {
                        "font": pil_font,
                        "font_color": font_color,
                        "outline_color": outline_color_hex,
                        "outline_width": outline_width
                    }
                    frame_settings = {
                        "frame_width": new_width,
                        "frame_height": new_height,
                        "base_y": int(initial_text_anchor_y),
                        "output_fps": output_fps
                    }
                    
                    text_canvas = render_word_level_effects(
                        complete_caption_words,
                        text_effects_configs,
                        text_canvas,
                        font_settings,
                        frame_settings,
                        preview_frame_count,
                        output_log_callback
                    )
                else:
                    # Standard caption-level rendering for preview
                    # Only skip normal text rendering for certain effects (like typewriter)
                    word_level_effects = {"typewriter"}
                    for effect_config_item in text_effects_configs:
                        if effect_config_item["slug"] in word_level_effects:
                            skip_normal_text = True
                            break
                
                # Use the fixed text drawing helper ONLY if no text-drawing effect is active
                if not skip_normal_text:
                    draw_text_with_outline(
                        draw_on_text_canvas, 
                        base_text_position_on_canvas, 
                        active_caption_text_for_frame,
                        pil_font, 
                        font_color, 
                        outline_color_hex, 
                        outline_width, 
                        anchor="ms",
                        max_width=int(new_width * 0.9)  # Allow text to use 90% of frame width
                    )

                current_canvas_for_effects = text_canvas
                
                # Find which caption this frame belongs to for proper timing
                # active_caption is already set above based on effect type
                
                # Calculate when this caption started in preview frame sequence
                caption_start_preview_frame = 0
                if active_caption:
                    caption_start_preview_frame = active_caption.get('_preview_start_frame', -1)
                    if caption_start_preview_frame == -1:
                        # First time seeing this caption, mark its start frame
                        active_caption['_preview_start_frame'] = preview_frame_count
                        caption_start_preview_frame = preview_frame_count
                
                relative_frame_idx = max(0, preview_frame_count - caption_start_preview_frame)
                
                # Apply caption-level text effects (skip word-level effects)
                for effect_config_item in text_effects_configs:
                    inst, intensity_val = effect_config_item["instance"], effect_config_item["intensity"]
                    
                    # Skip word-level effects in caption-level rendering (preview)
                    if hasattr(inst, "supports_word_level") and inst.supports_word_level:
                        continue
                    
                    # Prepare effect for this caption with all required parameters - MATCH GIF LOGIC
                    try:
                        if active_caption:
                            inst.prepare(
                                target_fps=output_fps, 
                                caption_natural_duration_sec=(active_caption['end_time'] - active_caption['start_time']), 
                                text_length=len(active_caption_text_for_frame), 
                                intensity=intensity_val
                            )
                        else:
                            # No active caption, use default values
                            inst.prepare(
                                target_fps=output_fps, 
                                caption_natural_duration_sec=1.0, 
                                text_length=len(active_caption_text_for_frame), 
                                intensity=intensity_val
                            )
                    except Exception as e_prep:
                        if output_log_callback: 
                            output_log_callback(f"Warning: Error preparing effect {inst.display_name} for preview: {e_prep}")
                        continue

                    try:
                        # Ensure canvas is RGBA before passing to effect - MATCH GIF LOGIC
                        if current_canvas_for_effects.mode != "RGBA":
                            current_canvas_for_effects = current_canvas_for_effects.convert("RGBA")
                            
                        transformed_canvas = inst.transform(
                            frame_image=current_canvas_for_effects.copy(), 
                            text=active_caption_text_for_frame, 
                            base_position=base_text_position_on_canvas, 
                            current_frame_index=relative_frame_idx, 
                            intensity=intensity_val,
                            font=pil_font, 
                            font_color=font_color, 
                            outline_color=outline_color_hex, 
                            outline_width=outline_width,
                            frame_width=new_width, 
                            frame_height=new_height, 
                            text_anchor_x=initial_text_anchor_x, 
                            text_anchor_y=initial_text_anchor_y,
                            caption_start_frame_for_gif=caption_start_preview_frame,
                            target_fps=output_fps  # For pulsing effects
                        )
                        if transformed_canvas and isinstance(transformed_canvas, Image.Image): 
                            # Ensure result is RGBA for consistent handling - MATCH GIF LOGIC
                            if transformed_canvas.mode != "RGBA":
                                transformed_canvas = transformed_canvas.convert("RGBA")
                            current_canvas_for_effects = transformed_canvas
                    except Exception as e_trans:
                        if output_log_callback:
                            output_log_callback(f"Warning: Error applying effect {inst.display_name} for preview: {e_trans}")
                    
                    text_canvas = current_canvas_for_effects

                # Calculate bounding box and y_offset
                y_offset_for_compositing = 0
                bbox = text_canvas.getbbox()
                if bbox:
                    content_bottom_y = bbox[3]
                    target_frame_bottom_edge = new_height - 1
                    if content_bottom_y > target_frame_bottom_edge: 
                        y_offset_for_compositing = target_frame_bottom_edge - content_bottom_y
                
                # Composite text onto frame
                # Convert base frame to RGBA temporarily for compositing
                pil_frame_rgba = pil_frame.convert("RGBA")
                pil_frame_rgba.alpha_composite(text_canvas, (0, int(y_offset_for_compositing)))
                # Convert back to RGB for final output
                pil_frame = pil_frame_rgba.convert("RGB")
            except Exception as e_render_preview:
                if output_log_callback: output_log_callback(f"Error rendering text/effects on frame for preview: {e_render_preview}")
        
        # NOW APPLY FULL-FRAME EFFECTS (like VHS/CRT) to the complete frame with text composited
        if full_frame_effects_configs:
            for effect_config_item in full_frame_effects_configs:
                effect_instance = effect_config_item["instance"]
                effect_intensity = effect_config_item["intensity"]
                effect_slug = effect_config_item["slug"]
                
                try:
                    # Prepare the full-frame effect
                    effect_instance.prepare(
                        target_fps=output_fps, 
                        caption_natural_duration_sec=2.0,  # Default duration for full-frame effects
                        text_length=len(active_caption_text_for_frame) if active_caption_text_for_frame else 0,
                        intensity=effect_intensity
                    )
                    
                    # Apply the effect to the full frame (video + text)
                    pil_frame = effect_instance.transform(
                        frame_image=pil_frame,
                        text=active_caption_text_for_frame or "",
                        base_position=(new_width // 2, new_height // 2),
                        current_frame_index=preview_frame_count,
                        intensity=effect_intensity,
                        font=pil_font,
                        font_color=font_color,
                        outline_color=outline_color_hex,
                        outline_width=outline_width,
                        frame_width=new_width,
                        frame_height=new_height,
                        text_anchor_x=new_width // 2,
                        text_anchor_y=int(new_height * 0.90),
                        target_fps=output_fps
                    )
                    
                    if output_log_callback and preview_frame_count % (output_fps * 5) == 0:
                        output_log_callback(f"Applied full-frame effect {effect_slug} to preview frame {preview_frame_count}")
                        
                except Exception as e_full_frame_effect:
                    if output_log_callback:
                        output_log_callback(f"Error applying full-frame effect {effect_slug} to preview: {e_full_frame_effect}")

        # Save frame as image file
        frame_filename = os.path.join(temp_frames_dir, f"frame_{preview_frame_count:06d}.png")
        pil_frame.convert("RGB").save(frame_filename, "PNG")
        preview_frame_count += 1
        frame_read_count += 1  # Increment after processing each frame
        
        if output_log_callback and preview_frame_count % (output_fps * 2) == 0:
            output_log_callback(f"Rendered {preview_frame_count} frames for preview video...")
            output_log_callback(f"Current time: {current_source_frame_time:.2f}s, active text: '{active_caption_text_for_frame[:30] if active_caption_text_for_frame else 'None'}...'")

    # --- 4. Finalize ---
    cap.release()
    
    if preview_frame_count == 0:
        if output_log_callback: output_log_callback("Error: No frames were rendered for preview.")
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(temp_frames_dir)
        except: pass
        return None, 0
    
    # Use ffmpeg from resources to create video from frames
    if output_log_callback: output_log_callback(f"Creating preview video from {preview_frame_count} frames using ffmpeg...")
    
    try:
        # Build ffmpeg command to create video from image sequence
        cmd_create_video = [
            config.FFMPEG_PATH,
            "-framerate", str(output_fps),
            "-i", os.path.join(temp_frames_dir, "frame_%06d.png"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",  # Overwrite output
            preview_video_filepath
        ]
        
        process = subprocess.Popen(cmd_create_video, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=config.PROJECT_ROOT)
        if output_log_callback:
            for line in iter(process.stdout.readline, ''):
                line_stripped = line.strip()
                if line_stripped:  # Only log non-empty lines
                    output_log_callback(line_stripped)
            process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            if output_log_callback: output_log_callback(f"ffmpeg video creation failed with exit code {return_code}.")
            preview_video_filepath = None
        else:
            if output_log_callback: output_log_callback(f"Preview video created successfully: {preview_video_filepath}")
            
    except Exception as e:
        if output_log_callback: output_log_callback(f"Error creating preview video with ffmpeg: {e}")
        preview_video_filepath = None
    finally:
        # Clean up temporary frames directory
        if output_log_callback: output_log_callback("Cleaning up temporary frames...")
        try:
            import shutil
            shutil.rmtree(temp_frames_dir)
        except Exception as e_cleanup:
            if output_log_callback: output_log_callback(f"Warning: Could not clean up temp frames: {e_cleanup}")
    
    if preview_video_filepath and os.path.exists(preview_video_filepath):
        return preview_video_filepath, preview_frame_count
    else:
        return None, 0

def render_word_level_effects(caption_words, text_effects_configs, text_canvas, font_settings, frame_settings, current_frame_index, output_log_callback=None):
    """
    Render complete caption with word-level effects applied to specific words.
    
    Args:
        caption_words: List of all word dictionaries in the complete caption
        text_effects_configs: List of enabled text effect configurations
        text_canvas: PIL Image canvas to draw on
        font_settings: Dictionary with font, color, and outline settings
        frame_settings: Dictionary with frame dimensions and positioning
        current_frame_index: Current frame index for effect animation
        output_log_callback: Logging function
    
    Returns:
        Modified text_canvas with word-level effects applied
    """
    if not caption_words:
        return text_canvas
    
    from PIL import Image, ImageDraw
    
    # Extract settings
    pil_font = font_settings["font"]
    default_font_color = font_settings["font_color"]
    outline_color = font_settings["outline_color"]
    outline_width = font_settings["outline_width"]
    
    frame_width = frame_settings["frame_width"]
    frame_height = frame_settings["frame_height"]
    base_y = frame_settings["base_y"]
    
    # Check if any word-level effects are enabled globally in the config
    has_word_level_effects_enabled = any(
        hasattr(effect_config["instance"], "supports_word_level") and effect_config["instance"].supports_word_level
        for effect_config in text_effects_configs
    )
    
    # Also check if any words have explicit word-level effects data
    has_explicit_word_effects = any(
        word.get("word_effects", {}).get("effects") 
        for word in caption_words
    )
    
    # Use word-level rendering if either condition is true
    use_word_level_rendering = has_word_level_effects_enabled or has_explicit_word_effects
    
    if not use_word_level_rendering:
        # No word-level effects, render as normal caption
        full_text = " ".join(word["word"] for word in caption_words)
        draw_text_with_outline(
            ImageDraw.Draw(text_canvas),
            (frame_width // 2, base_y),
            full_text,
            pil_font,
            default_font_color,
            outline_color,
            outline_width,
            anchor="ms",
            max_width=int(frame_width * 0.9)
        )
        return text_canvas
    
    # Create the full text to calculate positioning
    full_text = " ".join(word["word"] for word in caption_words)
    
    # Debug logging to identify extra characters
    if output_log_callback and current_frame_index % 30 == 0:
        output_log_callback(f"[DEBUG] Full caption text: '{full_text}'")
        output_log_callback(f"[DEBUG] Caption has {len(caption_words)} words:")
        for i, word in enumerate(caption_words):
            word_text = word["word"]
            output_log_callback(f"[DEBUG]   Word {i}: '{word_text}' (len={len(word_text)}, chars={[ord(c) for c in word_text]})")
    
    # Get text dimensions for positioning
    temp_draw = ImageDraw.Draw(text_canvas)
    try:
        bbox = temp_draw.textbbox((0, 0), "Ay", font=pil_font)  # Use standard text height
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback for older PIL versions
        text_height = temp_draw.textsize("Ay", font=pil_font)[1]
    
    # Find the active word-level effect (only use the first one)
    active_word_effect = None
    active_word_effect_intensity = 0
    for effect_config in text_effects_configs:
        if hasattr(effect_config["instance"], "supports_word_level") and effect_config["instance"].supports_word_level:
            active_word_effect = effect_config["instance"]
            active_word_effect_intensity = effect_config["intensity"]
            break
    
    # Calculate effect padding (shake effects need extra space)
    effect_padding = 8 if active_word_effect and active_word_effect.slug == "shake" else 5
    max_line_width = int(frame_width * 0.9) - (effect_padding * 2)  # Leave padding on both sides
    
    # Group words into lines based on available width
    lines = []
    current_line = []
    current_line_width = 0
    
    for word_data in caption_words:
        word_text = word_data["word"]
        
        # Get word dimensions
        try:
            word_bbox = temp_draw.textbbox((0, 0), word_text, font=pil_font)
            word_width = word_bbox[2] - word_bbox[0]
        except AttributeError:
            word_width = temp_draw.textsize(word_text, font=pil_font)[0]
        
        # Get space width
        try:
            space_width = temp_draw.textbbox((0, 0), " ", font=pil_font)[2]
        except AttributeError:
            space_width = temp_draw.textsize(" ", font=pil_font)[0]
        
        # Check if adding this word would exceed line width
        test_width = current_line_width + (space_width if current_line else 0) + word_width
        
        if test_width <= max_line_width or not current_line:  # Always add first word even if it's too wide
            current_line.append(word_data)
            current_line_width = test_width
        else:
            # Start new line
            if current_line:
                lines.append(current_line)
            current_line = [word_data]
            current_line_width = word_width
    
    # Add the last line
    if current_line:
        lines.append(current_line)
    
    # Calculate total text block height with proper line spacing
    line_spacing = 8  # Increased spacing for better readability with effects
    total_text_height = len(lines) * text_height + (len(lines) - 1) * line_spacing
    
    # Start with the original bottom positioning intent (base_y is typically 90% of frame height)
    # Only adjust if shake effects would cause text to overflow beyond frame bounds
    text_block_center_y = base_y
    
    # Calculate where the text block would be positioned
    text_block_top = text_block_center_y - total_text_height // 2
    text_block_bottom = text_block_center_y + total_text_height // 2
    
    # Apply safety adjustments only if needed (for shake effects that could overflow)
    if active_word_effect and active_word_effect.slug == "shake":
        # For shake effects, ensure text doesn't go outside safe bounds
        safe_top = effect_padding + text_height // 2
        safe_bottom = frame_height - effect_padding - text_height // 2
        
        # Only move text up if it would overflow at the bottom
        if text_block_bottom > safe_bottom:
            # Move the entire text block up to fit within safe bounds
            text_block_center_y = safe_bottom - total_text_height // 2
            
        # Don't let text go above safe top either
        if text_block_center_y - total_text_height // 2 < safe_top:
            text_block_center_y = safe_top + total_text_height // 2
    
    # Calculate final text block starting Y position
    text_block_start_y = text_block_center_y - total_text_height // 2
    
    # Render each line
    for line_index, line_words in enumerate(lines):
        # Calculate line width for centering
        line_width = 0
        for i, word_data in enumerate(line_words):
            word_text = word_data["word"]
            try:
                word_bbox = temp_draw.textbbox((0, 0), word_text, font=pil_font)
                word_w = word_bbox[2] - word_bbox[0]
            except AttributeError:
                word_w = temp_draw.textsize(word_text, font=pil_font)[0]
            
            line_width += word_w
            if i < len(line_words) - 1:  # Add space except after last word
                try:
                    space_w = temp_draw.textbbox((0, 0), " ", font=pil_font)[2]
                except AttributeError:
                    space_w = temp_draw.textsize(" ", font=pil_font)[0]
                line_width += space_w
        
        # Calculate starting X position for this line (centered)
        line_start_x = (frame_width - line_width) // 2
        current_x = line_start_x
        
        # Calculate Y position for this line
        line_y = text_block_start_y + line_index * (text_height + line_spacing)
        
        # Apply basic bounds checking to keep lines within frame
        line_y = max(text_height // 2, min(line_y, frame_height - text_height // 2))
        
        # Render each word in this line
        for word_index, word_data in enumerate(line_words):
            word_text = word_data["word"]
            
            # Get word dimensions for positioning
            try:
                word_bbox = temp_draw.textbbox((0, 0), word_text, font=pil_font)
                word_width = word_bbox[2] - word_bbox[0]
            except AttributeError:
                word_width = temp_draw.textsize(word_text, font=pil_font)[0]
            
            # Determine if this word should have effects and get per-word settings
            word_should_have_effects = False
            word_specific_color = None
            
            if active_word_effect:
                word_effects = word_data.get("word_effects", {})
                word_effect_settings = word_effects.get("effects", {})
                
                # Always check for custom color first, regardless of effect state
                word_specific_color = word_effects.get(f"{active_word_effect.slug}_color")
                
                if word_effect_settings:
                    # Word has explicit settings - use them
                    word_should_have_effects = word_effect_settings.get(active_word_effect.slug, False)
                    if output_log_callback and current_frame_index % 60 == 0:  # Log occasionally
                        output_log_callback(f"Word '{word_text}' explicit settings: {active_word_effect.slug}={word_should_have_effects}, color={word_specific_color}")
                else:
                    # Word has no explicit settings - apply global word-level effects by default
                    # This allows the initial workflow: enable globally, then selectively disable
                    global_word_effects_enabled = any(
                        hasattr(config["instance"], "supports_word_level") and config["instance"].supports_word_level
                        for config in text_effects_configs
                    )
                    word_should_have_effects = global_word_effects_enabled
                    if output_log_callback and current_frame_index % 60 == 0:  # Log occasionally
                        output_log_callback(f"Word '{word_text}' using global settings: {word_should_have_effects}, color={word_specific_color}")
            
            # Calculate word position (center of word)
            word_position = (current_x + word_width // 2, line_y)
            
            # Apply basic safety bounds for individual words (simpler approach)
            safe_x = max(word_width // 2, min(word_position[0], frame_width - word_width // 2))
            safe_y = max(text_height // 2, min(word_position[1], frame_height - text_height // 2))
            word_position = (safe_x, safe_y)
            
            if word_should_have_effects and active_word_effect:
                # Create individual canvas for this word with effect
                word_canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
                
                # Use word-specific color if available, otherwise use default
                word_font_color = word_specific_color if word_specific_color else default_font_color
                
                try:
                    # Prepare effect for this word
                    active_word_effect.prepare(
                        target_fps=frame_settings.get("output_fps", 12),
                        caption_natural_duration_sec=2.0,
                        text_length=len(word_text),
                        intensity=active_word_effect_intensity
                    )
                    
                    # Apply effect to this word
                    word_canvas = active_word_effect.transform(
                        frame_image=word_canvas,
                        text=word_text,
                        base_position=word_position,
                        current_frame_index=current_frame_index,
                        intensity=active_word_effect_intensity,
                        font=pil_font,
                        font_color=word_font_color,
                        outline_color=outline_color,
                        outline_width=outline_width,
                        text_anchor_x=word_position[0],
                        text_anchor_y=word_position[1],
                        frame_width=frame_width,
                        frame_height=frame_height,
                        target_fps=frame_settings.get("output_fps", 12)
                    )
                    
                    # Composite this word onto the main canvas
                    text_canvas.alpha_composite(word_canvas)
                    
                except Exception as e:
                    if output_log_callback:
                        output_log_callback(f"Error applying effect to word '{word_text}': {e}")
                    # Fallback: render word normally with word-specific color
                    draw_text_with_outline(
                        ImageDraw.Draw(text_canvas),
                        word_position,
                        word_text,
                        pil_font,
                        word_font_color,
                        outline_color,
                        outline_width,
                        anchor="mm"
                    )
            else:
                # Check if word has custom color even without effects
                word_font_color = word_specific_color if word_specific_color else default_font_color
                
                # Render word normally without effects but with custom color if specified
                draw_text_with_outline(
                    ImageDraw.Draw(text_canvas),
                    word_position,
                    word_text,
                    pil_font,
                    word_font_color,
                    outline_color,
                    outline_width,
                    anchor="mm"
                )
            
            # Move to next word position (add space)
            current_x += word_width
            if word_index < len(line_words) - 1:  # Add space except after last word in line
                try:
                    space_width = temp_draw.textbbox((0, 0), " ", font=pil_font)[2]
                except AttributeError:
                    space_width = temp_draw.textsize(" ", font=pil_font)[0]
                current_x += space_width
    
    # Debug logging
    if output_log_callback and current_frame_index % 30 == 0:
        words_with_effects = []
        words_with_custom_colors = []
        
        for word in caption_words:
            word_effects = word.get("word_effects", {})
            word_effect_settings = word_effects.get("effects", {})
            
            if active_word_effect:
                if word_effect_settings:
                    # Word has explicit settings - use them
                    if word_effect_settings.get(active_word_effect.slug, False):
                        words_with_effects.append(word["word"])
                    if word_effect_settings.get(f"{active_word_effect.slug}_color"):
                        words_with_custom_colors.append(word["word"])
                else:
                    # Word has no explicit settings - apply global word-level effects by default
                    global_word_effects_enabled = any(
                        hasattr(config["instance"], "supports_word_level") and config["instance"].supports_word_level
                        for config in text_effects_configs
                    )
                    if global_word_effects_enabled:
                        words_with_effects.append(word["word"])
        
        if active_word_effect:
            effect_info = f"Word-level rendering: '{full_text}' - effect '{active_word_effect.slug}' applied to: {words_with_effects}"
            if words_with_custom_colors:
                effect_info += f" | Custom colors on: {words_with_custom_colors}"
            output_log_callback(effect_info)
    
    return text_canvas

# Example usage (for testing, not part of the final app flow directly here)
if __name__ == '__main__':
    def log_message(message):
        print(message)

    # Create dummy executables for testing if they don't exist
    # In a real scenario, these must be present in resources/
    if not os.path.exists(config.YT_DLP_PATH):
        with open(config.YT_DLP_PATH, 'w') as f: f.write("#!/bin/bash\necho 'yt-dlp mock'\nexit 0")
        os.chmod(config.YT_DLP_PATH, 0o755)
    if not os.path.exists(config.FFMPEG_PATH):
        with open(config.FFMPEG_PATH, 'w') as f: f.write("#!/bin/bash\necho 'ffmpeg mock'\nexit 0")
        os.chmod(config.FFMPEG_PATH, 0o755)

    print(f"Using yt-dlp: {config.YT_DLP_PATH}")
    print(f"Using ffmpeg: {config.FFMPEG_PATH}")
    print(f"Temporary directory: {config.TEMP_DIR}")

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # A safe test video
    test_start = "00:00.500"
    test_end = "00:05.500"
    test_res = "360p"

    print(f"Attempting to download: {test_url} from {test_start} to {test_end} at {test_res}")
    video_file, audio_file = download_video_segment(test_url, test_start, test_end, test_res, log_message)

    if video_file and audio_file:
        print(f"\nSuccess! Video downloaded to: {video_file}")
        print(f"Audio extracted to: {audio_file}")
        # Clean up test files
        # os.remove(video_file)
        # os.remove(audio_file)
    else:
        print("\nDownload or extraction failed.")
