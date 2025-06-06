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

    @property
    def supports_word_level(self) -> bool:
        return True

    def prepare(self, **kwargs) -> None:
        """No preparation needed for rainbow effect"""
        pass

    def _split_text_into_lines(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Split text into lines that fit within max_width"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        # Create a temporary draw object for measuring text
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            try:
                bbox = temp_draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except AttributeError:
                # Fallback for older PIL versions
                line_width = temp_draw.textsize(test_line, font=font)[0]
            
            if line_width <= max_width or not current_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

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
            # No rainbow, draw normally with multi-line support
            draw_text_with_outline(
                ImageDraw.Draw(blank_canvas), 
                (text_anchor_x, text_anchor_y), 
                text,
                font, 
                font_color, 
                outline_color, 
                outline_width, 
                anchor="mm",
                max_width=int(frame_width * 0.9)
            )
            return blank_canvas
        
        # Rainbow parameters
        cycle_speed = (intensity / 100.0) * 3.0  # Speed of color cycling
        
        # Get FPS for animation timing
        fps = kwargs.get('target_fps', 12)
        time_offset = (current_frame_index / fps) * cycle_speed
        
        draw = ImageDraw.Draw(blank_canvas)
        
        # Split text into lines for multi-line support
        max_width = int(frame_width * 0.9)
        lines = self._split_text_into_lines(text, font, max_width)
        
        # Calculate line height and total height
        try:
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            line_height = bbox[3] - bbox[1]
        except AttributeError:
            line_height = draw.textsize("Ay", font=font)[1]
        
        total_height = len(lines) * line_height + (len(lines) - 1) * 4  # 4px line spacing
        
        # Calculate starting Y position based on anchor
        start_y = text_anchor_y - total_height // 2  # Center vertically
        
        # Count visible characters across all lines for color distribution
        visible_chars = sum(len([c for c in line if c != ' ']) for line in lines)
        char_index = 0
        
        # Draw each line
        for line_idx, line in enumerate(lines):
            line_y = start_y + line_idx * (line_height + 4)
            
            # Get line width to center it
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
            except AttributeError:
                line_width = draw.textsize(line, font=font)[0]
            
            # Starting x position for this line (centered)
            line_start_x = text_anchor_x - line_width // 2
            current_x = line_start_x
            
            # Draw each character in this line
            for i, char in enumerate(line):
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
                # Distribute colors across all visible characters
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
                
                # Draw character with outline at exact position
                char_x = current_x
                
                try:
                    draw.text((char_x, line_y), char, font=font, 
                             fill=char_color, anchor="lt",
                             stroke_width=outline_width, stroke_fill=char_outline_color)
                except (TypeError, AttributeError):
                    if outline_width > 0:
                        for dx in range(-outline_width, outline_width + 1):
                            for dy in range(-outline_width, outline_width + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((char_x + dx, line_y + dy), 
                                            char, font=font, fill=char_outline_color, anchor="lt")
                    draw.text((char_x, line_y), char, font=font, 
                             fill=char_color, anchor="lt")
                
                # Advance position
                current_x += char_width
                char_index += 1
        
        return blank_canvas