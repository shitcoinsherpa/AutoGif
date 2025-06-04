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
        """Initialize shake parameters for smooth multi-frequency shake"""
        self.fps = target_fps
        
        # Create multiple frequency components for realistic shake
        # Like real hand tremor or earthquake motion
        self.shake_frequencies = [
            {'freq': 8.0, 'amp_scale': 1.0},    # Primary shake
            {'freq': 15.0, 'amp_scale': 0.6},   # Secondary tremor
            {'freq': 25.0, 'amp_scale': 0.3},   # Fine vibration
        ]
        
        # Random phase offsets for each frequency to avoid predictable patterns
        for freq_data in self.shake_frequencies:
            freq_data['x_phase'] = random.uniform(0, 2 * math.pi)
            freq_data['y_phase'] = random.uniform(0, 2 * math.pi)

    def _calculate_shake_offset(self, frame_time: float, intensity: int) -> tuple[float, float]:
        """Calculate smooth multi-frequency shake offset"""
        if intensity <= 0:
            return 0.0, 0.0
        
        # Base amplitude from intensity
        base_amplitude = (intensity / 100.0) * 8.0  # Max 8 pixels
        
        total_x = 0.0
        total_y = 0.0
        
        # Combine multiple frequency components
        for freq_data in self.shake_frequencies:
            # Calculate sine waves for this frequency
            x_component = math.sin(2 * math.pi * freq_data['freq'] * frame_time + freq_data['x_phase'])
            y_component = math.sin(2 * math.pi * freq_data['freq'] * frame_time + freq_data['y_phase'])
            
            # Scale by amplitude
            amplitude = base_amplitude * freq_data['amp_scale']
            total_x += x_component * amplitude
            total_y += y_component * amplitude
        
        # Add some randomness for less predictable motion (but keep it smooth)
        random_factor = 0.15  # 15% randomness
        noise_x = (random.random() - 0.5) * base_amplitude * random_factor
        noise_y = (random.random() - 0.5) * base_amplitude * random_factor
        
        return total_x + noise_x, total_y + noise_y

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int], 
                  current_frame_index: int, intensity: int, 
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, 
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a smooth, multi-frequency shake effect to the text.
        """
        # Ensure frame is RGBA mode
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create a new blank canvas since shake replaces all text rendering
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text:
            return blank_canvas

        # Ensure prepare was called
        if not hasattr(self, 'shake_frequencies'):
            self.prepare(12)
        
        # Calculate shake offset based on intensity and time
        if intensity <= 0:
            # No shake, draw normally
            offset_x, offset_y = 0.0, 0.0
        else:
            # Calculate smooth shake offset
            frame_time = current_frame_index / self.fps
            offset_x, offset_y = self._calculate_shake_offset(frame_time, intensity)
        
        # Apply shake offset to text position
        shaken_anchor_x = int(text_anchor_x + offset_x)
        shaken_anchor_y = int(text_anchor_y + offset_y)

        # Draw text at shaken position with multi-line support
        draw_text_with_outline(
            ImageDraw.Draw(blank_canvas), 
            (shaken_anchor_x, shaken_anchor_y), 
            text,
            font, 
            font_color, 
            outline_color, 
            outline_width, 
            anchor="ms",
            max_width=int(frame_width * 0.9)
        )
            
        return blank_canvas