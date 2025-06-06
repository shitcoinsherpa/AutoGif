from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor

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

class NeonEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "neon"

    @property
    def display_name(self) -> str:
        return "Neon"

    @property
    def supports_word_level(self) -> bool:
        return True

    @property
    def default_intensity(self) -> int:
        return 80 # Controls glow spread/brightness

    def prepare(self, **kwargs) -> None:
        pass # Stateless

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, # Outline might be part of the neon look or base
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        
        # Ensure frame is RGBA mode
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
            
        # Create a new blank canvas since neon replaces all text rendering
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text:
            return blank_canvas
            
        if intensity <= 0:
            # Draw standard text if no intensity (effect still handles drawing)
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

        # Neon effect with multiple glow layers for authentic look
        core_text_color_pil = parse_color_to_pil_format(font_color)
        
        # Parse the color to get RGB values for brightness adjustment
        if core_text_color_pil.startswith('#'):
            r = int(core_text_color_pil[1:3], 16)
            g = int(core_text_color_pil[3:5], 16)
            b = int(core_text_color_pil[5:7], 16)
        else:
            # Fallback to white if not hex
            r, g, b = 255, 255, 255
        
        # Create slightly brighter version for glow (increase by 10-15%)
        bright_r = min(255, int(r * 1.1 + 20))
        bright_g = min(255, int(g * 1.1 + 20))
        bright_b = min(255, int(b * 1.1 + 20))
        bright_glow_color = f"#{bright_r:02x}{bright_g:02x}{bright_b:02x}"

        # Intensity controls the overall glow strength
        glow_strength = intensity / 100.0  # 0.0 to 1.0
        
        # Create two subtle glow layers
        # Layer 1: Outer soft glow
        if glow_strength > 0.2:
            outer_glow_layer = Image.new("RGBA", (frame_width, frame_height), (0,0,0,0))
            draw_outer = ImageDraw.Draw(outer_glow_layer)
            
            # Draw text for outer glow
            draw_text_with_outline(
                draw_outer, 
                (text_anchor_x, text_anchor_y), 
                text,
                font, 
                core_text_color_pil, 
                core_text_color_pil, 
                max(2, outline_width), 
                anchor="mm",
                max_width=int(frame_width * 0.9)
            )
            
            # Apply moderate blur for outer glow
            outer_blur_radius = 3.0 + (2.0 * glow_strength)  # 3-5 pixels
            outer_glow_blurred = outer_glow_layer.filter(ImageFilter.GaussianBlur(radius=outer_blur_radius))
            
            # Reduce opacity of outer glow
            outer_glow_blurred.putalpha(outer_glow_blurred.getchannel('A').point(lambda x: x * 0.6))
            blank_canvas = Image.alpha_composite(blank_canvas, outer_glow_blurred)
        
        # Layer 2: Inner bright glow
        if glow_strength > 0.3:
            inner_glow_layer = Image.new("RGBA", (frame_width, frame_height), (0,0,0,0))
            draw_inner = ImageDraw.Draw(inner_glow_layer)
            
            # Draw with the bright color
            draw_text_with_outline(
                draw_inner, 
                (text_anchor_x, text_anchor_y), 
                text,
                font, 
                bright_glow_color, 
                bright_glow_color, 
                outline_width, 
                anchor="mm",
                max_width=int(frame_width * 0.9)
            )
            
            # Light blur for inner glow
            inner_blur_radius = 1.5 + (1.5 * glow_strength)  # 1.5-3 pixels
            inner_glow_blurred = inner_glow_layer.filter(ImageFilter.GaussianBlur(radius=inner_blur_radius))
            
            # Reduce opacity based on intensity
            inner_glow_blurred.putalpha(inner_glow_blurred.getchannel('A').point(lambda x: x * (0.4 + 0.2 * glow_strength)))
            blank_canvas = Image.alpha_composite(blank_canvas, inner_glow_blurred)
        
        # Final layer: Draw the crisp text on top
        # Keep original color for readability
        final_text_color = core_text_color_pil
        
        draw_text_with_outline(
            ImageDraw.Draw(blank_canvas), 
            (text_anchor_x, text_anchor_y), 
            text,
            font, 
            final_text_color, 
            parse_color_to_pil_format(outline_color) if glow_strength < 0.5 else bright_glow_color, 
            outline_width, 
            anchor="mm",
            max_width=int(frame_width * 0.9)
        )

        return blank_canvas