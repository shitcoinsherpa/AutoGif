from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import colorsys

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

class RainbowEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "rainbow"

    @property
    def display_name(self) -> str:
        return "Rainbow"

    @property
    def default_intensity(self) -> int:
        return 80

    def prepare(self, **kwargs) -> None:
        """No preparation needed for rainbow effect"""
        pass

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a rainbow color cycling effect to the text.
        Each character gets a different color from the rainbow spectrum.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No rainbow, draw normally
            draw = ImageDraw.Draw(blank_canvas)
            pil_font_color = parse_color_to_pil_format(font_color)
            pil_outline_color = parse_color_to_pil_format(outline_color)
            
            try:
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, 
                         anchor="ms", stroke_width=outline_width, stroke_fill=pil_outline_color)
            except (TypeError, AttributeError):
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((text_anchor_x + dx, text_anchor_y + dy), text, 
                                        font=font, fill=pil_outline_color, anchor="ms")
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, anchor="ms")
            
            return blank_canvas
        
        # Rainbow parameters
        cycle_speed = (intensity / 100.0) * 3.0  # Speed of color cycling
        
        # Get FPS for animation timing
        fps = kwargs.get('target_fps', 12)
        time_offset = (current_frame_index / fps) * cycle_speed
        
        draw = ImageDraw.Draw(blank_canvas)
        
        # Get text dimensions
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            total_text_width = bbox[2] - bbox[0]
        except AttributeError:
            total_text_width = draw.textsize(text, font=font)[0]
        
        # Starting x position (left side of centered text)
        start_x = text_anchor_x - total_text_width // 2
        current_x = start_x
        
        # Count visible characters for color distribution
        visible_chars = len([c for c in text if c != ' '])
        char_index = 0
        
        # Draw each character with rainbow color
        for i, char in enumerate(text):
            if char == ' ':
                # Handle spaces
                try:
                    bbox = draw.textbbox((0, 0), ' ', font=font)
                    space_width = bbox[2] - bbox[0]
                except AttributeError:
                    space_width = draw.textsize(' ', font=font)[0]
                current_x += space_width
                continue
            
            # Calculate rainbow color for this character
            # Distribute colors across the text
            hue_offset = char_index / max(1, visible_chars - 1) if visible_chars > 1 else 0
            hue = (hue_offset + time_offset) % 1.0
            
            # Convert HSV to RGB
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)  # Full saturation and value
            char_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
            # Use darker version for outline
            outline_r, outline_g, outline_b = colorsys.hsv_to_rgb(hue, 1.0, 0.5)
            char_outline_color = f"#{int(outline_r*255):02x}{int(outline_g*255):02x}{int(outline_b*255):02x}"
            
            # Get character width
            try:
                bbox = draw.textbbox((0, 0), char, font=font)
                char_width = bbox[2] - bbox[0]
            except AttributeError:
                try:
                    char_width = draw.textsize(char, font=font)[0]
                except:
                    char_width = 10
            
            # Draw character with outline
            char_center_x = current_x + char_width // 2
            
            try:
                draw.text((char_center_x, text_anchor_y), char, font=font, 
                         fill=char_color, anchor="ms",
                         stroke_width=outline_width, stroke_fill=char_outline_color)
            except (TypeError, AttributeError):
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((char_center_x + dx, text_anchor_y + dy), 
                                        char, font=font, fill=char_outline_color, anchor="ms")
                draw.text((char_center_x, text_anchor_y), char, font=font, 
                         fill=char_color, anchor="ms")
            
            # Advance position
            current_x += char_width
            char_index += 1
        
        return blank_canvas 