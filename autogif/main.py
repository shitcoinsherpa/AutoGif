import gradio as gr
import os
import importlib.util
import inspect
import pandas as pd # For DataFrame
from autogif.effects.effect_base import EffectBase
from autogif import processing # Import the new processing module
from autogif import config # For paths, if needed directly in UI (e.g. for initial checks)
from autogif import user_settings # Import user settings module
from datetime import datetime
import math

# --- Plugin Loading (Should be defined here in main.py) ---
def load_effects(plugins_folder: str) -> list[EffectBase]: # Takes full path now
    """Loads effect plugins from the specified folder."""
    effects = []
    if not os.path.exists(plugins_folder):
        print(f"Warning: Effects plugin folder not found: {plugins_folder}")
        return effects

    for filename in os.listdir(plugins_folder):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            module_path = os.path.join(plugins_folder, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(f"autogif.effects.plugins.{module_name}", module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        if inspect.isclass(attribute) and \
                           issubclass(attribute, EffectBase) and \
                           attribute is not EffectBase:
                            effects.append(attribute()) 
                            # print(f"Loaded effect: {attribute().display_name}") # Verbose
            except Exception as e:
                print(f"Error loading plugin {module_name} from {module_path}: {e}")
    if not effects:
        print(f"No effects loaded from {plugins_folder}. Check plugin files.")
    else:
        print(f"Successfully loaded {len(effects)} effects.")
    return effects

def calculate_frame_range_for_subtitles(subtitles_data: list[dict], output_fps: int, buffer_seconds: float = 0.5) -> tuple[int, int]:
    """Calculate the frame range needed to display all subtitle data."""
    if not subtitles_data:
        return 0, 0
    
    # Find the extent of subtitle data
    min_start_time = min(word["start"] for word in subtitles_data)
    max_end_time = max(word["end"] for word in subtitles_data)
    
    # Calculate frame range with buffer
    start_frame = max(0, int(min_start_time * output_fps))
    end_frame = int(math.ceil((max_end_time + buffer_seconds) * output_fps))
    
    return start_frame, end_frame

# --- Load User Settings & Initialize --- 
APP_SETTINGS = user_settings.load_user_settings()
# Call the local load_effects function, passing the correct path from config
AVAILABLE_EFFECTS = load_effects(config.EFFECTS_PLUGINS_DIR) 
APP_SETTINGS = user_settings.initialize_effect_settings(APP_SETTINGS, AVAILABLE_EFFECTS)
# Save immediately if initialization changed anything (e.g. new effects added)
# This isn't strictly necessary here unless initialize_effect_settings actually adds new plugin defaults
# and we want those persisted even if the app is closed before any other save operation.
# user_settings.save_user_settings(APP_SETTINGS) # Optional: save after init

# Theme colors and styles
matrix_theme = gr.themes.Base(
    primary_hue=gr.themes.colors.green,
    secondary_hue=gr.themes.colors.green,
    neutral_hue=gr.themes.colors.gray,
    font=[gr.themes.GoogleFont("Inconsolata"), "monospace", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("Inconsolata"), "monospace", "sans-serif"],
).set(
    body_background_fill="#000000",
    body_text_color="#00FF41",
    button_primary_background_fill="#004400",
    button_primary_text_color="#00FF41",
    button_secondary_background_fill="#001100",
    button_secondary_text_color="#00FF41",
    input_background_fill="#001100",
    input_border_color="#004400",
    slider_color="#00FF41",
    block_background_fill="#000000",
    block_border_width="0px",
    block_label_background_fill="#000000",
    block_label_text_color="#00FF41",
    # table_border_color="#004400", # This one might be okay, but let's test without table specifics first
    # table_even_row_background_fill="#000000", # Removed
    # table_odd_row_background_fill="#001100",  # Removed
    # table_row_text_color="#00FF41",        # Removed
    # table_header_background_fill="#001100", # Removed
    # table_header_text_color="#00FF41",       # Removed
    # TODO: Add blinking cursor and scanlines via CSS if Gradio theme allows
    # For scanlines, a subtle repeating linear gradient or background image might work.
    # For blinking cursor, CSS animation on focused text inputs.
)

# --- Main App Definition (Modified) ---
with gr.Blocks(theme=matrix_theme, title="AutoGIF") as app:
    gr.Markdown("# AutoGIF") 
    current_video_file_path_state = gr.State(value=None) # Original fetched video
    preview_video_path_state = gr.State(value=None)      # Path to the styled preview MP4
    total_frames_in_preview_state = gr.State(value=0) # Total frames in the preview MP4
    current_subtitles_data_state = gr.State(value=[])   # Store subtitle data for frame range calculation

    with gr.Row():
        with gr.Column(scale=1): # Left column for controls
            gr.Markdown("## Controls")
            youtube_url = gr.Textbox(label="YouTube URL", placeholder="https://www.youtube.com/watch?v=...", value=APP_SETTINGS.last_youtube_url)
            with gr.Row():
                start_time = gr.Textbox(label="Start Time (MM:SS.mmm)", placeholder="00:00.000", value=APP_SETTINGS.last_start_time)
                end_time = gr.Textbox(label="End Time (MM:SS.mmm)", placeholder="00:00.000", value=APP_SETTINGS.last_end_time)
            fps = gr.Slider(minimum=1, maximum=30, value=APP_SETTINGS.last_fps, step=1, label="FPS")
            resolution = gr.Dropdown(
                label="Resolution", 
                choices=["240p", "360p", "480p", "720p", "1080p"], 
                value=APP_SETTINGS.last_resolution
            )
            
            gr.Markdown("### Typography")
            font_family = gr.Dropdown(
                label="Font Family", 
                choices=["Consolas", "IBM VGA 8x16", "JetBrains Mono NL", "Fira Code", "Impact"], 
                value=APP_SETTINGS.typography.font_family
            )
            font_size = gr.Dropdown(
                label="Font Size (pt)", 
                choices=[str(i) for i in range(12, 73, 2)], 
                value=str(APP_SETTINGS.typography.font_size_pt) # Ensure value is string for dropdown
            )
            font_color = gr.ColorPicker(label="Font Color", value=APP_SETTINGS.typography.font_color_hex)
            outline_color = gr.ColorPicker(label="Outline Color", value=APP_SETTINGS.typography.outline_color_hex)
            outline_width = gr.Number(label="Outline Width (px)", value=APP_SETTINGS.typography.outline_width_px, minimum=0, maximum=8, step=1)

            gr.Markdown("### Subtitle Effects")
            effect_inputs = {} 
            effect_components_list = []
            if not AVAILABLE_EFFECTS:
                gr.Markdown("No effects found. Place effect plugins in 'autogif/effects/plugins/'.")
            else:
                with gr.Group(): 
                    for effect_plugin in AVAILABLE_EFFECTS: # Iterate using discovered plugins
                        # Get saved setting for this effect, or use plugin default if not found (should be handled by initialize_effect_settings)
                        effect_setting = APP_SETTINGS.effects.get(
                            effect_plugin.slug, 
                            user_settings.EffectSetting(enabled=True, intensity=effect_plugin.default_intensity)
                        )
                        with gr.Row():
                            effect_enable = gr.Checkbox(label=effect_plugin.display_name, value=effect_setting.enabled) 
                            effect_intensity = gr.Slider(
                                minimum=0, maximum=100, value=effect_setting.intensity, 
                                step=1, label="Intensity", show_label=False 
                            )
                            effect_inputs[effect_plugin.slug] = {
                                "enable": effect_enable,
                                "intensity": effect_intensity,
                                "instance": effect_plugin 
                            }
                            effect_components_list.extend([effect_enable, effect_intensity])
            
            fetch_button = gr.Button("Fetch & Transcribe Video")
            regenerate_preview_button = gr.Button("Regenerate Preview with Edited Subtitles", visible=False)

            gr.Markdown("### Subtitle Table")
            subtitles_df = gr.DataFrame(
                headers=["Word", "Start (s)", "End (s)"],
                datatype=["str", "number", "number"],
                label="Editable Subtitles",
                interactive=True, 
                row_count=(0, "dynamic")
            )

        with gr.Column(scale=1): # Right column for log, preview, and GIF controls
            gr.Markdown("## Build Log")
            log_output = gr.Textbox(
                label="Log", 
                lines=5,  # Show 5 lines
                max_lines=10,  # Maximum 10 lines before scrollbar
                autoscroll=True, 
                interactive=False, 
                placeholder="Build process messages will appear here..."
            )
            gr.Markdown("## Styled Video Preview")
            styled_preview_video = gr.Video(label="Preview", interactive=False)
            
            with gr.Row():
                gif_start_frame_input = gr.Number(label="GIF Start Frame", value=0, precision=0, interactive=True, minimum=0)
                gif_end_frame_input = gr.Number(label="GIF End Frame", value=0, precision=0, interactive=True, minimum=0)
            total_preview_frames_display = gr.Textbox(label="Total Preview Frames", value="0", interactive=False)
            
            generate_button = gr.Button("Generate GIF from Selected Frames")
            
            gr.Markdown("## Final GIF Output") # For the actual generated GIF
            gif_preview_output = gr.Image(label="Generated GIF", interactive=False, type="filepath")
            download_button = gr.File(label="Download GIF", interactive=False, visible=False)

    # --- Utility function to gather current settings for saving ---
    def gather_current_ui_settings_for_save(url_val, start_time_val, end_time_val, fps_ui_val, res_val, 
                                          font_fam_val, font_sz_val, font_col_val, 
                                          outline_col_val, outline_w_val, 
                                          *active_effect_args):
        current_settings = user_settings.UserSettings(
            last_youtube_url=url_val,
            last_start_time=start_time_val,
            last_end_time=end_time_val,
            last_fps=int(fps_ui_val),
            last_resolution=res_val,
            typography=user_settings.TypographySettings(
                font_family=font_fam_val,
                font_size_pt=int(font_sz_val),
                font_color_hex=font_col_val,
                outline_color_hex=outline_col_val,
                outline_width_px=int(outline_w_val)
            ),
            effects={}
        )
        num_discovered_effects = len(AVAILABLE_EFFECTS)
        if len(active_effect_args) == num_discovered_effects * 2:
            for i in range(num_discovered_effects):
                plugin = AVAILABLE_EFFECTS[i]
                is_enabled = active_effect_args[i*2]
                intensity_val = active_effect_args[i*2 + 1]
                current_settings.effects[plugin.slug] = user_settings.EffectSetting(enabled=is_enabled, intensity=int(intensity_val))
        return current_settings

    # --- Handler for Fetch, Transcribe, and Auto-Preview (Modified to save settings) ---
    def handle_fetch_transcribe_and_preview(url, start_time_str, end_time_str, 
                                            fps_val, resolution_choice, 
                                            font_family_val, font_size_str, font_color_hex, 
                                            outline_color_hex_val, outline_width_val, 
                                            *effect_args_preview, 
                                            progress=gr.Progress(track_tqdm=True)):
        # Save current UI settings before processing
        # The *effect_args_preview needs to be correctly passed here from the main inputs list
        current_settings_to_save = gather_current_ui_settings_for_save(
            url, start_time_str, end_time_str, fps_val, resolution_choice,
            font_family_val, font_size_str, font_color_hex, outline_color_hex_val, outline_width_val,
            *effect_args_preview
        )
        user_settings.save_user_settings(current_settings_to_save)
        APP_SETTINGS = current_settings_to_save # Update global APP_SETTINGS in memory too
        
        log_messages = []
        def log_to_gradio(message):
            if isinstance(message, str):
                cleaned_message = message.strip()
                if cleaned_message: log_messages.append(cleaned_message)

        log_to_gradio("Fetch, Transcribe & Preview process started. Settings saved.")
        initial_ui_state = {
            log_output: "\n".join(log_messages),
            subtitles_df: pd.DataFrame(columns=["Word", "Start (s)", "End (s)"]),
            current_video_file_path_state: None,
            styled_preview_video: None,
            gif_start_frame_input: gr.update(interactive=False, value=0, maximum=0),
            gif_end_frame_input: gr.update(interactive=False, value=0, maximum=0),
            total_preview_frames_display: "0",
            regenerate_preview_button: gr.update(visible=False),
            preview_video_path_state: None,
            total_frames_in_preview_state: 0,
            current_subtitles_data_state: []
        }

        if not url or not url.startswith("http"): 
            log_to_gradio("Error: Please enter a valid YouTube URL.")
            return initial_ui_state
        
        original_video_segment_path, audio_path = processing.download_video_segment(
            url, start_time_str, end_time_str, resolution_choice, log_to_gradio
        )

        if not original_video_segment_path or not audio_path:
            log_to_gradio("Error: Failed to download video segment or extract audio.")
            if original_video_segment_path and os.path.exists(original_video_segment_path): os.remove(original_video_segment_path)
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)
            initial_ui_state[log_output] = "\n".join(log_messages)
            return initial_ui_state
        
        word_data = processing.transcribe_audio(audio_path, log_to_gradio)
        if audio_path and os.path.exists(audio_path): 
            log_to_gradio(f"Cleaning up temporary audio file: {audio_path}")
            os.remove(audio_path)

        if not word_data:
            log_to_gradio("Error: Transcription failed.")
            if original_video_segment_path and os.path.exists(original_video_segment_path): os.remove(original_video_segment_path)
            initial_ui_state[log_output] = "\n".join(log_messages)
            return initial_ui_state

        subtitles_df_result = pd.DataFrame(word_data)
        subtitles_df_result.columns = ["Word", "Start (s)", "End (s)"]
        log_to_gradio("Transcription successful. Proceeding to render styled preview...")

        # CRITICAL FIX: Calculate proper frame range based on subtitle data
        try:
            preview_fps = int(fps_val)
            preview_target_height = int(resolution_choice.replace("p", ""))
            preview_font_size_pt = int(font_size_str)
            
            # Calculate frame range to cover all subtitle data
            start_frame, end_frame = calculate_frame_range_for_subtitles(word_data, preview_fps, buffer_seconds=0.5)
            
            # Log the calculation for debugging
            if word_data:
                subtitle_duration = max(word["end"] for word in word_data)
                log_to_gradio(f"Subtitle data extends to {subtitle_duration:.2f}s, setting end frame to {end_frame}")
            
        except ValueError as e:
            log_to_gradio(f"Error: Invalid numeric value for preview settings (FPS, Res, Font Size): {e}")
            if original_video_segment_path and os.path.exists(original_video_segment_path): os.remove(original_video_segment_path)
            initial_ui_state[log_output] = "\n".join(log_messages)
            initial_ui_state[subtitles_df] = subtitles_df_result
            initial_ui_state[current_video_file_path_state] = original_video_segment_path # Keep it for potential manual GIF gen
            initial_ui_state[current_subtitles_data_state] = word_data
            return initial_ui_state

        preview_typography_settings = {
            "font_family": font_family_val, "font_size_pt": preview_font_size_pt,
            "font_color_hex": font_color_hex, "outline_color_hex": outline_color_hex_val,
            "outline_width_px": int(outline_width_val)
        }
        preview_selected_effects = []
        num_effects = len(AVAILABLE_EFFECTS)
        if len(effect_args_preview) == num_effects * 2:
            for i in range(num_effects):
                if effect_args_preview[i*2]: 
                    preview_selected_effects.append({"instance": AVAILABLE_EFFECTS[i], "intensity": int(effect_args_preview[i*2+1]), "enabled": True})
        
        preview_vid_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        preview_mp4_filename = f"AutoGIF_Preview_{preview_vid_ts}.mp4"
        preview_mp4_filepath = os.path.join(config.TEMP_DIR, preview_mp4_filename)

        rendered_preview_path, total_preview_frames = processing.render_preview_video(
            original_video_segment_path, word_data, preview_fps, preview_target_height,
            preview_typography_settings, preview_selected_effects, preview_mp4_filepath, log_to_gradio
        )

        if not rendered_preview_path:
            log_to_gradio("Error: Styled preview video generation failed.")
            # original_video_segment_path is kept in current_video_file_path_state for potential manual GIF gen attempt
            initial_ui_state[log_output] = "\n".join(log_messages)
            initial_ui_state[subtitles_df] = subtitles_df_result
            initial_ui_state[current_video_file_path_state] = original_video_segment_path
            initial_ui_state[regenerate_preview_button] = gr.update(visible=True)
            initial_ui_state[current_subtitles_data_state] = word_data
            return initial_ui_state

        log_to_gradio(f"Styled preview video generated: {rendered_preview_path} with {total_preview_frames} frames.")
        
        # Allow generous maximum for user padding - 50% more frames than needed
        padding_buffer = int(end_frame * 0.5)  # 50% padding allowance
        max_frame = end_frame + padding_buffer

        return {
            log_output: "\n".join(log_messages),
            subtitles_df: subtitles_df_result,
            current_video_file_path_state: original_video_segment_path,
            styled_preview_video: rendered_preview_path,
            gif_start_frame_input: gr.update(interactive=True, value=start_frame, maximum=max_frame),
            gif_end_frame_input: gr.update(interactive=True, value=end_frame, maximum=max_frame),
            total_preview_frames_display: str(total_preview_frames),
            regenerate_preview_button: gr.update(visible=True),
            preview_video_path_state: rendered_preview_path,
            total_frames_in_preview_state: total_preview_frames,
            current_subtitles_data_state: word_data
        }

    # --- Handler for Regenerating Preview with Edited Subtitles ---
    def handle_regenerate_preview(original_video_path, edited_subtitles_df, 
                                  fps_val, resolution_choice, 
                                  font_family_val, font_size_str, font_color_hex, 
                                  outline_color_hex_val, outline_width_val,
                                  *effect_args_regen,
                                  progress=gr.Progress(track_tqdm=True)):
        
        log_messages = []
        def log_to_gradio(message):
            if isinstance(message, str):
                cleaned_message = message.strip()
                if cleaned_message: log_messages.append(cleaned_message)

        log_to_gradio("Regenerating preview with edited subtitles...")

        # Validate inputs
        if not original_video_path or not os.path.exists(original_video_path):
            log_to_gradio("Error: No original video available for preview regeneration.")
            return (
                "\n".join(log_messages), 
                None, 
                gr.update(interactive=False, value=0, maximum=0), 
                gr.update(interactive=False, value=0, maximum=0), 
                "0", 
                None, 
                0,
                []
            )

        # Convert edited subtitles DataFrame to word data format
        if edited_subtitles_df is None or edited_subtitles_df.empty:
            log_to_gradio("Error: No subtitle data available for preview regeneration.")
            return (
                "\n".join(log_messages), 
                None, 
                gr.update(interactive=False, value=0, maximum=0), 
                gr.update(interactive=False, value=0, maximum=0), 
                "0", 
                None, 
                0,
                []
            )

        word_data = []
        try:
            for _, row in edited_subtitles_df.iterrows():
                word_data.append({
                    "word": str(row["Word"]), 
                    "start": float(row["Start (s)"]), 
                    "end": float(row["End (s)"])
                })
        except Exception as e:
            log_to_gradio(f"Error processing edited subtitles: {e}")
            return (
                "\n".join(log_messages), 
                None, 
                gr.update(interactive=False, value=0, maximum=0), 
                gr.update(interactive=False, value=0, maximum=0), 
                "0", 
                None, 
                0,
                []
            )

        try:
            preview_fps = int(fps_val)
            preview_target_height = int(resolution_choice.replace("p", ""))
            preview_font_size_pt = int(font_size_str)
            
            # CRITICAL FIX: Calculate proper frame range for regenerated preview
            start_frame, end_frame = calculate_frame_range_for_subtitles(word_data, preview_fps, buffer_seconds=0.5)
            
            # Log the calculation for debugging
            if word_data:
                subtitle_duration = max(word["end"] for word in word_data)
                log_to_gradio(f"Regenerated preview: Subtitle data extends to {subtitle_duration:.2f}s, setting end frame to {end_frame}")
                
        except ValueError as e:
            log_to_gradio(f"Error: Invalid numeric values: {e}")
            return (
                "\n".join(log_messages), 
                None, 
                gr.update(interactive=False, value=0, maximum=0), 
                gr.update(interactive=False, value=0, maximum=0), 
                "0", 
                None, 
                0,
                []
            )

        # Prepare typography and effects settings (same as fetch handler)
        preview_typography_settings = {
            "font_family": font_family_val, "font_size_pt": preview_font_size_pt,
            "font_color_hex": font_color_hex, "outline_color_hex": outline_color_hex_val,
            "outline_width_px": int(outline_width_val)
        }
        
        preview_selected_effects = []
        num_effects = len(AVAILABLE_EFFECTS)
        if len(effect_args_regen) == num_effects * 2:
            for i in range(num_effects):
                if effect_args_regen[i*2]: 
                    preview_selected_effects.append({
                        "instance": AVAILABLE_EFFECTS[i], 
                        "intensity": int(effect_args_regen[i*2+1]), 
                        "enabled": True
                    })

        # Generate new preview
        preview_vid_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        preview_mp4_filename = f"AutoGIF_Preview_Regen_{preview_vid_ts}.mp4"
        preview_mp4_filepath = os.path.join(config.TEMP_DIR, preview_mp4_filename)

        rendered_preview_path, total_preview_frames = processing.render_preview_video(
            original_video_path, word_data, preview_fps, preview_target_height,
            preview_typography_settings, preview_selected_effects, preview_mp4_filepath, log_to_gradio
        )

        if not rendered_preview_path:
            log_to_gradio("Error: Preview regeneration failed.")
            return (
                "\n".join(log_messages), 
                None, 
                gr.update(interactive=False, value=0, maximum=0), 
                gr.update(interactive=False, value=0, maximum=0), 
                "0", 
                None, 
                0,
                []
            )

        log_to_gradio(f"Preview successfully regenerated with {total_preview_frames} frames.")

        # Allow generous maximum for user padding - 50% more frames than needed
        padding_buffer = int(end_frame * 0.5)  # 50% padding allowance
        max_frame = end_frame + padding_buffer

        return (
            "\n".join(log_messages),
            rendered_preview_path,
            gr.update(interactive=True, value=start_frame, maximum=max_frame),
            gr.update(interactive=True, value=end_frame, maximum=max_frame),
            str(total_preview_frames),
            rendered_preview_path,
            total_preview_frames,
            word_data
        )

    # --- Handler for Generate GIF (Modified to save settings) ---
    def handle_generate_gif(original_video_file_path_from_state, subtitles_input_df, 
                            gif_fps_val, gif_resolution_str, 
                            gif_font_family_val, gif_font_size_str, gif_font_color_hex, 
                            gif_outline_color_hex_val, gif_outline_width_val, 
                            gif_start_frame, gif_end_frame,
                            total_frames_preview_val, # Value from total_frames_in_preview_state
                            preview_video_file_path_val, # Value from preview_video_path_state
                            current_subtitles_data, # Value from current_subtitles_data_state
                            *gif_effect_args, 
                            progress=gr.Progress(track_tqdm=True)):
        global APP_SETTINGS # Declare global for update
        # Save current UI settings before processing
        current_settings_to_save = gather_current_ui_settings_for_save(
            APP_SETTINGS.last_youtube_url, # Preserve last URL from global settings, not current input
            APP_SETTINGS.last_start_time, # Preserve last times
            APP_SETTINGS.last_end_time,
            gif_fps_val, gif_resolution_str, # These are GIF specific for this run
            gif_font_family_val, gif_font_size_str, gif_font_color_hex, 
            gif_outline_color_hex_val, gif_outline_width_val,
            *gif_effect_args
        )
        # Overwrite parts that are specific to this GIF generation from the UI
        # The URL, start/end time for *next* session are not updated by GIF generation itself.
        # But FPS, resolution, typo, effects for *next* session default ARE updated by GIF generation.
        user_settings.save_user_settings(current_settings_to_save)
        APP_SETTINGS = current_settings_to_save # Update global

        log_messages = []
        def log_to_gradio(message):
            if isinstance(message, str): 
                cleaned_message = message.strip()
                if cleaned_message: log_messages.append(cleaned_message)

        log_to_gradio("Generate GIF (from selected frames) button clicked. Settings Updated.")

        if not original_video_file_path_from_state or not os.path.exists(original_video_file_path_from_state):
            log_to_gradio("Error: No original video file available. Please Fetch & Transcribe first.")
            return "\n".join(log_messages), None, gr.update(visible=False)

        # CRITICAL FIX: Use subtitle data from state for frame range validation
        subtitles_data = []
        if subtitles_input_df is not None and not subtitles_input_df.empty:
            for _index, row in subtitles_input_df.iterrows():
                try: 
                    subtitles_data.append({
                        "word": str(row["Word"]), 
                        "start": float(row["Start (s)"]), 
                        "end": float(row["End (s)"])
                    })
                except (KeyError, ValueError): 
                    log_to_gradio("Error: Subtitle data invalid.")
                    return "\n".join(log_messages), None, gr.update(visible=False)
        elif current_subtitles_data:
            # Fallback to stored subtitle data
            subtitles_data = current_subtitles_data
            log_to_gradio("Using stored subtitle data for GIF generation.")

        try:
            target_gif_fps = int(gif_fps_val)
            target_gif_height = int(gif_resolution_str.replace("p", ""))
            gif_font_size_pt = int(gif_font_size_str)
            start_frame_num = int(gif_start_frame)
            end_frame_num = int(gif_end_frame)
        except ValueError as e:
            log_to_gradio(f"Error: Invalid numeric value in GIF settings: {e}")
            return "\n".join(log_messages), None, gr.update(visible=False)
        
        # CRITICAL FIX: Validate frame range against subtitle data
        if subtitles_data:
            recommended_start, recommended_end = calculate_frame_range_for_subtitles(subtitles_data, target_gif_fps, buffer_seconds=0.5)
            subtitle_duration = max(word["end"] for word in subtitles_data)
            
            # Extend end frame if it doesn't cover all subtitle data
            if end_frame_num < recommended_end:
                log_to_gradio(f"Extending end frame from {end_frame_num} to {recommended_end} to cover all subtitles (duration: {subtitle_duration:.2f}s)")
                end_frame_num = recommended_end
        
        if start_frame_num < 0 or end_frame_num < start_frame_num:
            log_to_gradio(f"Error: Invalid frame selection (Start: {start_frame_num}, End: {end_frame_num}).")
            return "\n".join(log_messages), None, gr.update(visible=False)

        gif_typography_settings = {
            "font_family": gif_font_family_val, "font_size_pt": gif_font_size_pt,
            "font_color_hex": gif_font_color_hex, "outline_color_hex": gif_outline_color_hex_val,
            "outline_width_px": int(gif_outline_width_val)
        }
        gif_selected_effects = []
        num_effects = len(AVAILABLE_EFFECTS)
        if len(gif_effect_args) == num_effects * 2:
            for i in range(num_effects):
                if gif_effect_args[i*2]: 
                    gif_selected_effects.append({"instance": AVAILABLE_EFFECTS[i], "intensity": int(gif_effect_args[i*2+1]), "enabled": True})
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        gif_filename = f"AutoGIF-{timestamp}.gif"
        gif_filepath = os.path.join(config.TEMP_DIR, gif_filename)

        log_to_gradio(f"Generating GIF from frame {start_frame_num} to {end_frame_num}...")

        generated_gif_path = processing.generate_gif(
            video_path=original_video_file_path_from_state,
            subtitles_data=subtitles_data, output_fps=target_gif_fps, target_height=target_gif_height,
            typography_settings=gif_typography_settings, selected_effects=gif_selected_effects,
            gif_filepath=gif_filepath, output_log_callback=log_to_gradio,
            start_frame_num=start_frame_num, end_frame_num=end_frame_num
        )
        
        # Cleanup original fetched video segment after successful GIF generation
        if generated_gif_path and os.path.exists(generated_gif_path):
            if original_video_file_path_from_state and os.path.exists(original_video_file_path_from_state):
                try: os.remove(original_video_file_path_from_state)
                except Exception as e: log_to_gradio(f"Warning: could not delete original segment {original_video_file_path_from_state}: {e}")
            # Also cleanup the styled preview MP4 as it's now stale
            # Need to get preview_video_path_state. For now, assuming it might not be available if user interacts weirdly.
            # A more robust way is to pass preview_video_path_state as an input to handle_generate_gif if we always want to clean it.
            # For this iteration, we'll leave the preview file. It gets overwritten on next fetch anyway.
            
            log_to_gradio("GIF Generation Successful!")
            return "\n".join(log_messages), generated_gif_path, gr.update(value=generated_gif_path, visible=True)
        else:
            log_to_gradio("Error: GIF Generation Failed.")
            return "\n".join(log_messages), None, gr.update(visible=False)

    # Inputs for fetch_button (now includes all settings for preview rendering)
    fetch_inputs = [
        youtube_url, start_time, end_time, 
        fps, resolution, 
        font_family, font_size, font_color, 
        outline_color, outline_width
    ] + effect_components_list
    
    fetch_outputs = [
        log_output, 
        subtitles_df, 
        current_video_file_path_state, 
        styled_preview_video, 
        gif_start_frame_input, 
        gif_end_frame_input,
        total_preview_frames_display,
        regenerate_preview_button,
        preview_video_path_state,
        total_frames_in_preview_state,
        current_subtitles_data_state
    ]

    fetch_button.click(
        fn=handle_fetch_transcribe_and_preview,
        inputs=fetch_inputs,
        outputs=fetch_outputs
    )

    # Inputs for regenerate_preview_button
    regenerate_inputs = [
        current_video_file_path_state,
        subtitles_df,
        fps, 
        resolution,
        font_family, 
        font_size, 
        font_color, 
        outline_color, 
        outline_width
    ] + effect_components_list
    
    regenerate_outputs = [
        log_output,
        styled_preview_video,
        gif_start_frame_input,
        gif_end_frame_input,
        total_preview_frames_display,
        preview_video_path_state,
        total_frames_in_preview_state,
        current_subtitles_data_state
    ]

    regenerate_preview_button.click(
        fn=handle_regenerate_preview,
        inputs=regenerate_inputs,
        outputs=regenerate_outputs
    )

    # Inputs for generate_button (now includes frame selectors and all settings for GIF)
    generate_inputs = [
        current_video_file_path_state, 
        subtitles_df, 
        fps, 
        resolution,
        font_family, 
        font_size, 
        font_color, 
        outline_color, 
        outline_width,
        gif_start_frame_input, 
        gif_end_frame_input,
        total_frames_in_preview_state, # Added to inputs
        preview_video_path_state,       # Added to inputs
        current_subtitles_data_state    # Added to inputs
    ] + effect_components_list 
    
    generate_outputs = [log_output, gif_preview_output, download_button]

    generate_button.click(
        fn=handle_generate_gif, 
        inputs=generate_inputs, 
        outputs=generate_outputs
    )

if __name__ == "__main__":
    # Ensure directories exist (from config, called here for startup)
    config.ensure_directories_exist()
    # Basic executable checks (from config)
    if not os.path.exists(config.YT_DLP_PATH):
        print(f"CRITICAL: yt-dlp not found at {config.YT_DLP_PATH}")
    if not os.path.exists(config.FFMPEG_PATH):
        print(f"CRITICAL: ffmpeg not found at {config.FFMPEG_PATH}")

    print("Attempting to launch Gradio app...") # Added for diagnostics
    app.launch(debug=True) # Removed show_error_details

    # If you want to add more checks or actions after launching the app, you can do so here
    # For example, you can add a check for the availability of the Gradio app
    if not app.is_running():
        print("Gradio app failed to start. Please check the logs for more information.")
    else:
        print("Gradio app started successfully!")
