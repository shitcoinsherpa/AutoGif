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

def get_enabled_word_level_effects(effect_components_list):
    """Get a list of word-level effects that are currently enabled."""
    enabled_word_effects = []
    
    # The effect_components_list contains pairs of (enable_checkbox, intensity_slider)
    # for each effect in AVAILABLE_EFFECTS order
    for i in range(len(AVAILABLE_EFFECTS)):
        effect_plugin = AVAILABLE_EFFECTS[i]
        if hasattr(effect_plugin, 'supports_word_level') and effect_plugin.supports_word_level:
            # Get the current value of the enable checkbox
            enable_idx = i * 2  # Each effect has enable + intensity = 2 components
            if enable_idx < len(effect_components_list):
                enable_component = effect_components_list[enable_idx]
                # Note: We can't directly check component values here since this runs at setup
                # We'll need to handle this in the event handlers
                enabled_word_effects.append(effect_plugin)
    
    return enabled_word_effects

def generate_dynamic_dataframe_columns(*effect_args):
    """Generate DataFrame columns based on enabled word-level effects."""
    base_columns = ["Word", "Start (s)", "End (s)"]
    base_datatypes = ["str", "number", "number"]
    
    # Check which word-level effects are enabled
    enabled_word_effects = []
    num_effects = len(AVAILABLE_EFFECTS)
    
    if len(effect_args) >= num_effects * 2:
        for i in range(num_effects):
            effect_plugin = AVAILABLE_EFFECTS[i]
            enable_idx = i * 2
            is_enabled = effect_args[enable_idx] if enable_idx < len(effect_args) else False
            
            if (hasattr(effect_plugin, 'supports_word_level') and 
                effect_plugin.supports_word_level and is_enabled):
                enabled_word_effects.append(effect_plugin)
    
    # Add columns for each enabled word-level effect
    dynamic_columns = base_columns.copy()
    dynamic_datatypes = base_datatypes.copy()
    
    for effect in enabled_word_effects:
        column_name = f"{effect.display_name}"
        dynamic_columns.append(column_name)
        dynamic_datatypes.append("bool")  # Checkbox for enabling effect on this word
    
    # Add word color column if any word-level effects are enabled
    if enabled_word_effects:
        dynamic_columns.append("Word Color")
        dynamic_datatypes.append("str")  # Color picker
    
    return dynamic_columns, dynamic_datatypes



def get_active_word_level_effect(enabled_effect_args):
    """Get the currently active word-level effect (only one can be active at a time)."""
    if not enabled_effect_args or len(enabled_effect_args) < len(AVAILABLE_EFFECTS) * 2:
        return None
    
    for i in range(len(AVAILABLE_EFFECTS)):
        effect_plugin = AVAILABLE_EFFECTS[i]
        enable_idx = i * 2
        is_enabled = enabled_effect_args[enable_idx] if enable_idx < len(enabled_effect_args) else False
        
        if (hasattr(effect_plugin, 'supports_word_level') and 
            effect_plugin.supports_word_level and is_enabled):
            return effect_plugin
    
    return None

def update_word_level_controls(word_data, enabled_effect_args, word_control_rows, word_effects_section, active_effect_display, current_font_color=None, skip_colors=False):
    """Update the word-level control components based on current data and active effect."""
    
    active_effect = get_active_word_level_effect(enabled_effect_args)
    
    # Prepare updates for all UI components
    updates = {}
    
    if not active_effect or not word_data:
        # Hide the entire word effects section
        updates[word_effects_section] = gr.update(visible=False)
        return updates
    
    # Show the word effects section and set the active effect
    updates[word_effects_section] = gr.update(visible=True)
    updates[active_effect_display] = gr.update(value=f"**Active Effect:** {active_effect.display_name}")
    
    # Use current font color if provided, otherwise fall back to saved settings
    default_color = current_font_color if current_font_color else APP_SETTINGS.typography.font_color_hex
    
    # Update word control rows
    for i, control_row in enumerate(word_control_rows):
        if i < len(word_data):
            # Show this row and populate with word data
            word = word_data[i]
            updates[control_row["row"]] = gr.update(visible=True)
            updates[control_row["label"]] = gr.update(value=f"**{word['word']}** ({word['start']:.2f}s - {word['end']:.2f}s)")
            updates[control_row["checkbox"]] = gr.update(value=True)  # Default to enabled
            
            # Only update color if not skipping (to preserve user selections)
            if not skip_colors:
                # Check if word has existing color data
                if "word_effects" in word and f"{active_effect.slug}_color" in word["word_effects"]:
                    # Use the existing custom color
                    existing_color = word["word_effects"][f"{active_effect.slug}_color"]
                    updates[control_row["color"]] = gr.update(value=existing_color)
                else:
                    # Use default color for new words
                    updates[control_row["color"]] = gr.update(value=default_color)
            else:
                # Return empty update to maintain order
                updates[control_row["color"]] = gr.update()
        else:
            # Hide unused rows
            updates[control_row["row"]] = gr.update(visible=False)
    
    return updates

def create_enhanced_subtitle_dataframe(word_data, enabled_effect_args=None):
    """Create basic DataFrame for word timing data only."""
    if not word_data:
        return pd.DataFrame(columns=["Word", "Start (s)", "End (s)"])
    
    df = pd.DataFrame(word_data)
    df.columns = ["Word", "Start (s)", "End (s)"]
    return df

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
            # Basic DataFrame for word text and timing only
            subtitles_df = gr.DataFrame(
                headers=["Word", "Start (s)", "End (s)"],
                datatype=["str", "number", "number"],
                label="Editable Subtitles",
                interactive=True, 
                row_count=(0, "dynamic")
            )
            
            # Word-level effect controls (shown only when a word-level effect is enabled)
            with gr.Column(visible=False) as word_effects_section:
                active_effect_display = gr.Markdown("**Active Effect:** None")
                
                # Collapsible accordion for word-level controls to save space
                with gr.Accordion("🎯 Per-Word Effect Control (Click to expand)", open=False) as word_accordion:
                    gr.Markdown("**Default:** All words use the global effect. Uncheck specific words to remove effects from them.")
                    
                    # Pre-create controls for up to 100 words (handle longer GIFs)
                    word_control_rows = []
                    for i in range(100):
                        with gr.Row(visible=False) as word_row:
                            word_label = gr.Markdown("")
                            word_checkbox = gr.Checkbox(label="Enable", value=True, interactive=True)
                            word_color = gr.ColorPicker(label="Color", value=APP_SETTINGS.typography.font_color_hex, interactive=True)
                            word_control_rows.append({
                                "row": word_row,
                                "label": word_label,
                                "checkbox": word_checkbox,
                                "color": word_color
                            })
                    
                    gr.Markdown("💡 **Tip:** Uncheck words like 'the', 'a', 'was' to only apply effects to important words!")

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
        # Prepare initial state with word-level controls hidden
        initial_word_control_updates = update_word_level_controls([], effect_args_preview, word_control_rows, word_effects_section, active_effect_display)
        
        initial_ui_state = {
            log_output: "\n".join(log_messages),
            subtitles_df: create_enhanced_subtitle_dataframe([], effect_args_preview),
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
        
        # Add word control updates to initial state
        initial_ui_state.update(initial_word_control_updates)

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

        # Create enhanced DataFrame with dynamic columns based on enabled word-level effects
        subtitles_df_result = create_enhanced_subtitle_dataframe(word_data, effect_args_preview)
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

        # Apply default word-level effects for initial preview
        if word_data:
            active_effect = get_active_word_level_effect(effect_args_preview)
            if active_effect:
                # For initial preview, apply the global word-level effect to all words by default
                for i, word_entry in enumerate(word_data):
                    word_entry["word_effects"] = {
                        "effects": {active_effect.slug: True},
                        f"{active_effect.slug}_color": font_color_hex  # Use current UI color, not APP_SETTINGS
                    }

        # Prepare word-level control updates
        word_control_updates = update_word_level_controls(word_data, effect_args_preview, word_control_rows, word_effects_section, active_effect_display, font_color_hex, skip_colors=False)
        
        # Combine all updates
        all_updates = {
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
        
        # Add word control updates
        all_updates.update(word_control_updates)
        
        return all_updates

    # --- Handler for Regenerating Preview with Edited Subtitles ---
    def handle_regenerate_preview(original_video_path, edited_subtitles_df, 
                                  fps_val, resolution_choice, 
                                  font_family_val, font_size_str, font_color_hex, 
                                  outline_color_hex_val, outline_width_val,
                                  *all_args,
                                  progress=gr.Progress(track_tqdm=True)):
        
        # Split the arguments: first part is effect args, rest are word control values
        num_effect_args = len(AVAILABLE_EFFECTS) * 2
        effect_args_regen = all_args[:num_effect_args]
        word_control_values = all_args[num_effect_args:]  # checkbox, color pairs for each word
        
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
            active_effect = get_active_word_level_effect(effect_args_regen)
            
            for _, row in edited_subtitles_df.iterrows():
                word_entry = {
                    "word": str(row["Word"]), 
                    "start": float(row["Start (s)"]), 
                    "end": float(row["End (s)"])
                }
                
                # Only apply word-level effects to words that have been explicitly configured
                # Don't automatically apply to all words when regenerating
                # (Word effects should only be applied when explicitly set via word controls)
                
                word_data.append(word_entry)
            
            # Apply word control settings using actual checkbox and color values
            if word_data:
                active_effect = get_active_word_level_effect(effect_args_regen)
                if active_effect:
                    log_to_gradio(f"Processing {len(word_data)} words with {len(word_control_values)} control values for effect '{active_effect.slug}'")
                    # Parse word control values (checkbox, color pairs)
                    for i, word_entry in enumerate(word_data):
                        # Each word has 2 control values: checkbox (bool) and color (str)
                        checkbox_index = i * 2
                        color_index = i * 2 + 1
                        
                        if checkbox_index < len(word_control_values) and color_index < len(word_control_values):
                            word_enabled = word_control_values[checkbox_index]  # True/False from checkbox
                            word_color = word_control_values[color_index]        # Color string from color picker
                            log_to_gradio(f"Word '{word_entry['word']}' (index {i}): checkbox={word_enabled}, color={word_color}")
                            
                            # Check if the word color is different from the global color
                            # If it's the same or appears to be a default gray, use the current global color
                            use_global_color = False
                            try:
                                # Parse word color to check if it's default/gray
                                word_color_parsed = word_color.replace("rgba(", "").replace(")", "").split(",")
                                if len(word_color_parsed) >= 3:
                                    r, g, b = float(word_color_parsed[0]), float(word_color_parsed[1]), float(word_color_parsed[2])
                                    # If all RGB values are close to gray (240-255 range), use global color instead
                                    if 240 <= r <= 255 and 240 <= g <= 255 and 240 <= b <= 255:
                                        use_global_color = True
                            except:
                                use_global_color = True
                            
                            # Use global color if word color appears to be default, otherwise use word color
                            final_color = font_color_hex if use_global_color else word_color
                            
                            # Always create word_effects structure, but set enabled based on checkbox
                            word_entry["word_effects"] = {
                                "effects": {active_effect.slug: word_enabled},  # True or False based on checkbox
                                f"{active_effect.slug}_color": final_color
                            }
                            
                            if word_enabled:
                                log_to_gradio(f"Applied {active_effect.slug} to '{word_entry['word']}' with color {final_color}")
                            else:
                                log_to_gradio(f"Disabled {active_effect.slug} for '{word_entry['word']}'")
                        else:
                            # If no control values available, use global settings
                            word_entry["word_effects"] = {
                                "effects": {active_effect.slug: True},  # Default to enabled when no controls
                                f"{active_effect.slug}_color": font_color_hex  # Use current global color
                            }
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

        # Process subtitle data - CRITICAL: Use stored data with word effects, not DataFrame
        subtitles_data = []
        if current_subtitles_data and len(current_subtitles_data) > 0:
            # Use the stored subtitle data that contains word effects
            subtitles_data = current_subtitles_data
            log_to_gradio(f"Using stored subtitle data with word effects for GIF generation ({len(subtitles_data)} words).")
        elif subtitles_input_df is not None and not subtitles_input_df.empty:
            # Fallback: rebuild from DataFrame if no stored data (but this loses word effects)
            log_to_gradio("Warning: No stored subtitle data available, rebuilding from DataFrame (word effects will be lost).")
            for i, (_, row) in enumerate(subtitles_input_df.iterrows()):
                try: 
                    word_entry = {
                        "word": str(row["Word"]), 
                        "start": float(row["Start (s)"]), 
                        "end": float(row["End (s)"])
                    }
                    subtitles_data.append(word_entry)
                except (KeyError, ValueError) as e: 
                    log_to_gradio(f"Error processing subtitle row: {e}")
                    return "\n".join(log_messages), None, gr.update(visible=False)
        else:
            log_to_gradio("Error: No subtitle data available for GIF generation.")
            return "\n".join(log_messages), None, gr.update(visible=False)

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
        current_subtitles_data_state,
        word_effects_section,
        active_effect_display
    ]
    
    # Add all word control components to outputs
    for control_row in word_control_rows:
        fetch_outputs.extend([
            control_row["row"],
            control_row["label"],
            control_row["checkbox"],
            control_row["color"]
        ])

    fetch_button.click(
        fn=handle_fetch_transcribe_and_preview,
        inputs=fetch_inputs,
        outputs=fetch_outputs
    )

    # Handler for syncing subtitle table edits with word-level controls
    def handle_subtitle_table_change(edited_subtitles_df, font_color_from_ui, current_word_data, *effect_args):
        """Sync subtitle table edits with word-level controls."""
        
        # Create a map of existing word effects by word text for preservation
        existing_effects = {}
        if current_word_data:
            for word in current_word_data:
                if "word_effects" in word:
                    existing_effects[word["word"]] = word["word_effects"]
        
        # Convert DataFrame to word data format
        word_data = []
        if edited_subtitles_df is not None and not edited_subtitles_df.empty:
            for _, row in edited_subtitles_df.iterrows():
                try:
                    word_entry = {
                        "word": str(row["Word"]), 
                        "start": float(row["Start (s)"]), 
                        "end": float(row["End (s)"])
                    }
                    
                    # Preserve existing word effects if they exist
                    if word_entry["word"] in existing_effects:
                        word_entry["word_effects"] = existing_effects[word_entry["word"]]
                    
                    word_data.append(word_entry)
                except (KeyError, ValueError):
                    continue
        
        # Update word controls with the edited data
        word_control_updates = update_word_level_controls(
            word_data, effect_args, word_control_rows, word_effects_section, active_effect_display, font_color_from_ui, skip_colors=True
        )
        
        # Convert dictionary updates to list format for Gradio
        result_list = []
        
        # Add word control updates in order
        for control_row in word_control_rows:
            result_list.append(word_control_updates.get(control_row["row"], gr.update()))
            result_list.append(word_control_updates.get(control_row["label"], gr.update()))
            result_list.append(word_control_updates.get(control_row["checkbox"], gr.update()))
            result_list.append(word_control_updates.get(control_row["color"], gr.update()))
        
        # Add section visibility and active effect display
        result_list.append(word_control_updates.get(word_effects_section, gr.update()))
        result_list.append(word_control_updates.get(active_effect_display, gr.update()))
        
        return result_list

    # Helper function to apply word control settings to word data
    def apply_word_control_settings_to_data(word_data, word_control_rows, active_effect):
        """Apply current word control checkbox and color settings to word data."""
        if not active_effect or not word_data:
            return word_data
        
        # Create a copy of word_data to modify
        updated_word_data = []
        
        for i, word_entry in enumerate(word_data):
            # Copy the word entry
            updated_word_entry = word_entry.copy()
            
            # Apply word-level effects to all words by default when globally enabled
            # Users can then selectively disable via word controls
            word_effects = {active_effect.slug: True}  # Default to enabled for all words
            word_color = APP_SETTINGS.typography.font_color_hex
            
            updated_word_entry["word_effects"] = {
                "effects": word_effects,
                f"{active_effect.slug}_color": word_color
            }
            
            updated_word_data.append(updated_word_entry)
        
        return updated_word_data

    # Inputs for regenerate_preview_button (include word control components)
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
    
    # Add all word control components as inputs so we can read their current values
    for control_row in word_control_rows:
        regenerate_inputs.extend([
            control_row["checkbox"],
            control_row["color"]
        ])
    
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
    
    # Set up subtitle table change handler to sync with word controls
    sync_inputs = [subtitles_df, font_color, current_subtitles_data_state] + effect_components_list
    sync_outputs = []
    for control_row in word_control_rows:
        sync_outputs.extend([
            control_row["row"],
            control_row["label"],
            control_row["checkbox"],
            control_row["color"]
        ])
    sync_outputs.extend([word_effects_section, active_effect_display])
    
    subtitles_df.change(
        fn=handle_subtitle_table_change,
        inputs=sync_inputs,
        outputs=sync_outputs
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
