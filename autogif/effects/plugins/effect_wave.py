from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import math

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

class WaveEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "wave"

    @property
    def display_name(self) -> str:
        return "Wave"

    @property
    def default_intensity(self) -> int:
        return 60

    def prepare(self, **kwargs) -> None:
        """No preparation needed for wave effect"""
        pass

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a wave effect where each letter moves up and down in a sine wave pattern.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No wave effect, draw normally
            draw = ImageDraw.Draw(blank_canvas)
            pil_font_color = parse_color_to_pil_format(font_color)
            pil_outline_color = parse_color_to_pil_format(outline_color)
            
            try:
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, 
                         anchor="ms", stroke_width=outline_width, stroke_fill=pil_outline_color)
            except (TypeError, AttributeError):
                # Fallback for older PIL
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((text_anchor_x + dx, text_anchor_y + dy), text, 
                                        font=font, fill=pil_outline_color, anchor="ms")
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, anchor="ms")
            
            return blank_canvas
        
        # Wave parameters
        wave_amplitude = (intensity / 100.0) * 30  # Max 30 pixels up/down (increased for visibility)
        wave_frequency = 0.15  # How many waves across the text
        wave_speed = 2.0  # Speed of wave animation
        
        # Get FPS for animation timing
        fps = kwargs.get('target_fps', 12)
        if fps <= 0:
            fps = 12  # Fallback if fps is invalid
        time_offset = (current_frame_index / fps) * wave_speed
        
        # Convert colors
        pil_font_color = parse_color_to_pil_format(font_color)
        pil_outline_color = parse_color_to_pil_format(outline_color)
        
        # Calculate starting position for character-by-character rendering
        draw = ImageDraw.Draw(blank_canvas)
        
        # Get text width to center it properly
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            total_text_width = bbox[2] - bbox[0]
        except AttributeError:
            total_text_width = draw.textsize(text, font=font)[0]
        
        # Starting x position (left side of centered text)
        start_x = text_anchor_x - total_text_width // 2
        current_x = start_x
        
        # Draw each character with wave offset
        for i, char in enumerate(text):
            if char == ' ':
                # Handle spaces - just advance position
                try:
                    bbox = draw.textbbox((0, 0), ' ', font=font)
                    space_width = bbox[2] - bbox[0]
                except AttributeError:
                    space_width = draw.textsize(' ', font=font)[0]
                current_x += space_width
                continue
            
            # Calculate wave offset for this character
            wave_position = i * wave_frequency + time_offset
            y_offset = math.sin(wave_position) * wave_amplitude
            
            # Character position
            char_x = current_x
            char_y = text_anchor_y + y_offset
            
            # Draw character with outline
            try:
                # Get character width for proper spacing
                bbox = draw.textbbox((0, 0), char, font=font)
                char_width = bbox[2] - bbox[0]
                
                # Draw with stroke if supported
                draw.text((char_x + char_width // 2, char_y), char, font=font, 
                         fill=pil_font_color, anchor="ms",
                         stroke_width=outline_width, stroke_fill=pil_outline_color)
            except (TypeError, AttributeError):
                # Fallback for older PIL
                try:
                    char_width = draw.textsize(char, font=font)[0]
                except:
                    char_width = 10  # Fallback width
                
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((char_x + char_width // 2 + dx, char_y + dy), 
                                        char, font=font, fill=pil_outline_color, anchor="ms")
                draw.text((char_x + char_width // 2, char_y), char, font=font, 
                         fill=pil_font_color, anchor="ms")
            
            # Advance position
            current_x += char_width
        
        return blank_canvas 