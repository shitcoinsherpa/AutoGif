from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import math
import re

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

class TypewriterEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "typewriter"

    @property
    def display_name(self) -> str:
        return "Typewriter"

    @property
    def default_intensity(self) -> int:
        return 70 # Higher intensity means faster typing

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """
        Pre-calculates characters per frame or total frames for the effect for a given caption.
        This ensures the typewriter effect completes within the available caption duration.
        Intensity controls the portion of caption duration used for typing animation.
        """
        # Extract intensity from kwargs if not provided as parameter
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        if text_length <= 0 or caption_natural_duration_sec <= 0:
            self.total_animation_frames_for_caption = 1
            self.chars_per_frame = text_length  # Show all text immediately
            return
        
        # Calculate available frames for this caption
        total_caption_frames = max(1, math.ceil(caption_natural_duration_sec * target_fps))
        
        # Intensity (0-100) controls what portion of the caption duration is used for typing
        # 100 = use almost all duration for typing (95%)
        # 50 = use half duration for typing (50%) 
        # 0 = use minimal duration for typing (10%)
        typing_duration_factor = 0.1 + (0.85 * (intensity / 100.0))  # Range: 0.1 to 0.95
        
        # Calculate frames available for the typing animation
        self.total_animation_frames_for_caption = max(1, math.floor(total_caption_frames * typing_duration_factor))
        
        # Calculate characters per frame to ensure completion within available frames
        # We want to show all characters by the end of the animation frames
        self.chars_per_frame = text_length / max(1, self.total_animation_frames_for_caption)
        
        # Ensure we show at least 1 character per frame after the first frame
        if self.chars_per_frame < 1.0 and self.total_animation_frames_for_caption > 1:
            # If we have more frames than characters, spread characters evenly
            self.frames_per_char = self.total_animation_frames_for_caption / text_length
        else:
            self.frames_per_char = None
        
        # Debug logging (commented out for production)
        # print(f"Typewriter Prep: text_len={text_length}, cap_dur={caption_natural_duration_sec:.2f}s, "
        #       f"cap_frames={total_caption_frames}, typing_frames={self.total_animation_frames_for_caption}, "
        #       f"chars_per_frame={self.chars_per_frame:.2f}, intensity={intensity}")

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, # This is the frame index *within the current caption's display time*
                  intensity: int, 
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, 
                  text_anchor_x: int, text_anchor_y: int,
                  # kwargs from main render loop
                  caption_start_frame_for_gif: int = 0, # The GIF frame index where this caption *starts* appearing
                  **kwargs) -> Image.Image:
        
        # Ensure frame is RGBA mode
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create a new blank canvas since typewriter replaces all text rendering
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text:
            return blank_canvas
        
        # Calculate how many characters to display based on animation progress
        if current_frame_index >= self.total_animation_frames_for_caption:
            # Animation complete, show all text
            num_chars_to_display = len(text)
        else:
            if hasattr(self, 'frames_per_char') and self.frames_per_char is not None:
                # More frames than characters - show characters at intervals
                num_chars_to_display = min(len(text), max(1, math.floor(current_frame_index / self.frames_per_char) + 1))
            else:
                # Calculate characters based on frames and chars_per_frame
                if current_frame_index == 0:
                    num_chars_to_display = max(1, math.ceil(self.chars_per_frame))
                else:
                    num_chars_to_display = min(len(text), math.ceil((current_frame_index + 1) * self.chars_per_frame))
        
        # Ensure we don't exceed text length and show at least some characters
        num_chars_to_display = max(0, min(len(text), num_chars_to_display))
        
        displayed_text = text[:num_chars_to_display] if num_chars_to_display > 0 else ""

        if not displayed_text:
            return blank_canvas # Return blank canvas if no text to display yet

        # Convert colors to PIL format using local function
        pil_font_color = parse_color_to_pil_format(font_color)
        pil_outline_color = parse_color_to_pil_format(outline_color)

        # Create a new drawing context on the blank canvas
        draw_context = ImageDraw.Draw(blank_canvas)

        # Check if modern stroke is available
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
