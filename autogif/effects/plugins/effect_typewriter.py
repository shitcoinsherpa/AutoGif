from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import math
import random

def parse_color_to_pil_format(color_input):
    """
    Converts various color formats to PIL-compatible format.
    Handles hex, rgb(), rgba(), and CSS color names.
    Returns hex string or RGB tuple.
    """
    if not color_input:
        return "#FFFFFF"
    
    color_str = str(color_input).strip()
    
    if color_str.startswith('#') and len(color_str) in [4, 7]:
        return color_str
    
    if color_str.startswith('rgba(') and color_str.endswith(')'):
        try:
            values_str = color_str[5:-1]
            values = [float(v.strip()) for v in values_str.split(',')]
            if len(values) >= 3:
                r, g, b = int(values[0]), int(values[1]), int(values[2])
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    if color_str.startswith('rgb(') and color_str.endswith(')'):
        try:
            values_str = color_str[4:-1]
            values = [float(v.strip()) for v in values_str.split(',')]
            if len(values) >= 3:
                r, g, b = int(values[0]), int(values[1]), int(values[2])
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    if isinstance(color_input, (tuple, list)) and len(color_input) >= 3:
        try:
            r, g, b = int(color_input[0]), int(color_input[1]), int(color_input[2])
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    
    return color_str

class TypewriterEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "typewriter"

    @property
    def display_name(self) -> str:
        return "Typewriter"

    @property
    def default_intensity(self) -> int:
        return 70

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """
        Pre-calculates typewriter timing with natural human rhythm variations.
        """
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        if text_length <= 0 or caption_natural_duration_sec <= 0:
            self.character_frames = []
            return
        
        text = kwargs.get('text', 'x' * text_length)
        
        # Intensity controls typing speed: 0-100 maps to 2-8 characters per second
        base_cps = 2.0 + (6.0 * (intensity / 100.0))
        
        # Calculate the frame when each character should appear
        self.character_frames = []
        current_time = 0.2  # Small initial delay
        
        for i, char in enumerate(text):
            # Convert current time to frame number
            frame_num = int(current_time * target_fps)
            self.character_frames.append(frame_num)
            
            # Calculate delay to next character (basic typewriter timing)
            char_delay = 1.0 / base_cps
            
            # Add slight pause after punctuation
            if char in '.,!?;:':
                char_delay += 0.3
            elif char == ' ':
                char_delay += 0.1
            
            # Add natural human variation (±20%)
            char_delay *= random.uniform(0.8, 1.2)
            
            current_time += char_delay
        
        # Scale timing to fit the caption duration if needed
        if self.character_frames:
            total_time_needed = current_time
            max_time_available = caption_natural_duration_sec * 0.9
            
            if total_time_needed > max_time_available:
                # Speed up to fit
                time_scale = max_time_available / total_time_needed
                self.character_frames = [int(frame * time_scale) for frame in self.character_frames]

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int, 
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, 
                  text_anchor_x: int, text_anchor_y: int,
                  **kwargs) -> Image.Image:
        
        # Ensure frame is RGBA mode
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create a new blank canvas
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text:
            return blank_canvas
        
        # Ensure prepare was called and we have character frames
        if not hasattr(self, 'character_frames') or not self.character_frames:
            self.prepare(12, 2.0, len(text), intensity, text=text)
        
        # Determine how many characters to show by checking frame timings
        num_chars_to_show = 0
        for i, target_frame in enumerate(self.character_frames):
            if current_frame_index >= target_frame:
                num_chars_to_show = i + 1
            else:
                break
        
        # Ensure we don't exceed text length
        num_chars_to_show = min(num_chars_to_show, len(text))
        displayed_text = text[:num_chars_to_show] if num_chars_to_show > 0 else ""
        
        # Add blinking cursor if we're still typing
        show_cursor = False
        if num_chars_to_show < len(text):
            # Cursor blinks every 20 frames (about 1.5 times per second at 12fps)
            if (current_frame_index // 20) % 2 == 0:
                show_cursor = True
        
        if show_cursor:
            displayed_text += "|"
        
        if not displayed_text:
            return blank_canvas

        # Convert colors to PIL format
        pil_font_color = parse_color_to_pil_format(font_color)
        pil_outline_color = parse_color_to_pil_format(outline_color)

        # Create drawing context on the blank canvas
        draw_context = ImageDraw.Draw(blank_canvas)

        # Draw the text
        try:
            if outline_width > 0:
                draw_context.text((text_anchor_x, text_anchor_y), displayed_text, font=font, fill=pil_font_color, anchor="ms", 
                          stroke_width=outline_width, stroke_fill=pil_outline_color)
            else:
                draw_context.text((text_anchor_x, text_anchor_y), displayed_text, font=font, fill=pil_font_color, anchor="ms")
        except TypeError:
            # Fallback for older PIL versions
            if outline_width > 0:
                for dx_o in range(-outline_width, outline_width + 1):
                    for dy_o in range(-outline_width, outline_width + 1):
                        if dx_o != 0 or dy_o != 0:
                            draw_context.text((text_anchor_x + dx_o, text_anchor_y + dy_o), displayed_text, font=font, fill=pil_outline_color, anchor="ms")
            draw_context.text((text_anchor_x, text_anchor_y), displayed_text, font=font, fill=pil_font_color, anchor="ms")
            
        return blank_canvas