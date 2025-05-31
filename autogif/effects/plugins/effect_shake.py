from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random

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

class ShakeEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "shake"

    @property
    def display_name(self) -> str:
        return "Shake"

    @property
    def default_intensity(self) -> int:
        return 50

    def prepare(self, target_fps: int, **kwargs) -> None:
        pass

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int], 
                  current_frame_index: int, intensity: int, 
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, 
                  text_anchor_x: int, text_anchor_y: int,
                  **kwargs) -> Image.Image:
        """
        Applies a shake effect to the text by rendering it at a randomly offset position.
        """
        
        # Convert colors to PIL format
        pil_font_color = parse_color_to_pil_format(font_color)
        pil_outline_color = parse_color_to_pil_format(outline_color)
        
        # Create drawing context
        draw = ImageDraw.Draw(frame_image, "RGBA")

        # Calculate shake offset based on intensity
        max_offset = intensity / 10.0 
        if max_offset <= 0:
            # No shake, draw normally
            try:
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, anchor="ms", 
                         stroke_width=outline_width, stroke_fill=pil_outline_color)
            except TypeError:
                # Fallback for older PIL versions
                if outline_width > 0:
                    for dx_o in range(-outline_width, outline_width + 1):
                        for dy_o in range(-outline_width, outline_width + 1):
                            if dx_o != 0 or dy_o != 0:
                                draw.text((text_anchor_x + dx_o, text_anchor_y + dy_o), text, font=font, fill=pil_outline_color, anchor="ms")
                draw.text((text_anchor_x, text_anchor_y), text, font=font, fill=pil_font_color, anchor="ms")
            return frame_image

        # Generate random shake offset
        offset_x = random.uniform(-max_offset, max_offset)
        offset_y = random.uniform(-max_offset, max_offset)

        shaken_anchor_x = int(text_anchor_x + offset_x)
        shaken_anchor_y = int(text_anchor_y + offset_y)

        # Draw text at shaken position
        try:
            draw.text((shaken_anchor_x, shaken_anchor_y), text, font=font, fill=pil_font_color, anchor="ms", 
                     stroke_width=outline_width, stroke_fill=pil_outline_color)
        except TypeError:
            # Fallback for older PIL versions
            if outline_width > 0:
                for dx_o in range(-outline_width, outline_width + 1):
                    for dy_o in range(-outline_width, outline_width + 1):
                        if dx_o != 0 or dy_o != 0:
                            draw.text((shaken_anchor_x + dx_o, shaken_anchor_y + dy_o), text, font=font, fill=pil_outline_color, anchor="ms")
            draw.text((shaken_anchor_x, shaken_anchor_y), text, font=font, fill=pil_font_color, anchor="ms")
            
        return frame_image
