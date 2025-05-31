from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont, ImageChops
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

class GlitchEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "glitch"

    @property
    def display_name(self) -> str:
        return "Glitch"

    @property
    def default_intensity(self) -> int:
        return 50

    def prepare(self, **kwargs) -> None:
        """Initialize random seed for consistent glitches per caption"""
        # Use a seed based on the text content for reproducible glitches
        text = kwargs.get('text', '')
        self.random_seed = hash(text) % 1000000

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a digital glitch effect with RGB channel separation and corruption.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No glitch, draw normally
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
        
        # Set up random with consistent seed
        rng = random.Random(self.random_seed + current_frame_index)
        
        # Glitch parameters based on intensity
        glitch_probability = intensity / 100.0
        max_offset = int(5 + (intensity / 100.0) * 15)  # Max RGB separation
        
        # Determine if this frame should glitch
        should_glitch = rng.random() < glitch_probability * 0.5  # 50% chance at max intensity (increased for visibility)
        
        if not should_glitch:
            # Draw normal text most of the time
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
        
        # Create RGB channel separation effect
        # Draw text in separate color channels with offsets
        red_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        green_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        blue_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        # Random offsets for each channel
        red_offset_x = rng.randint(-max_offset, max_offset)
        red_offset_y = rng.randint(-max_offset//2, max_offset//2)
        green_offset_x = rng.randint(-max_offset, max_offset)
        green_offset_y = rng.randint(-max_offset//2, max_offset//2)
        blue_offset_x = rng.randint(-max_offset, max_offset)
        blue_offset_y = rng.randint(-max_offset//2, max_offset//2)
        
        # Draw red channel
        draw_red = ImageDraw.Draw(red_canvas)
        try:
            draw_red.text((text_anchor_x + red_offset_x, text_anchor_y + red_offset_y), 
                         text, font=font, fill=(255, 0, 0, 255), anchor="ms")
        except:
            draw_red.text((text_anchor_x + red_offset_x, text_anchor_y + red_offset_y), 
                         text, font=font, fill=(255, 0, 0, 255))
        
        # Draw green channel
        draw_green = ImageDraw.Draw(green_canvas)
        try:
            draw_green.text((text_anchor_x + green_offset_x, text_anchor_y + green_offset_y), 
                           text, font=font, fill=(0, 255, 0, 255), anchor="ms")
        except:
            draw_green.text((text_anchor_x + green_offset_x, text_anchor_y + green_offset_y), 
                           text, font=font, fill=(0, 255, 0, 255))
        
        # Draw blue channel
        draw_blue = ImageDraw.Draw(blue_canvas)
        try:
            draw_blue.text((text_anchor_x + blue_offset_x, text_anchor_y + blue_offset_y), 
                          text, font=font, fill=(0, 0, 255, 255), anchor="ms")
        except:
            draw_blue.text((text_anchor_x + blue_offset_x, text_anchor_y + blue_offset_y), 
                          text, font=font, fill=(0, 0, 255, 255))
        
        # Combine channels with additive blending
        blank_canvas = ImageChops.add(blank_canvas, red_canvas)
        blank_canvas = ImageChops.add(blank_canvas, green_canvas)
        blank_canvas = ImageChops.add(blank_canvas, blue_canvas)
        
        # Add digital noise/corruption
        if rng.random() < 0.5:  # 50% chance of additional corruption
            # Draw some corrupted blocks
            draw_corrupt = ImageDraw.Draw(blank_canvas)
            num_blocks = rng.randint(1, 3)
            
            for _ in range(num_blocks):
                block_x = text_anchor_x + rng.randint(-50, 50)
                block_y = text_anchor_y + rng.randint(-20, 20)
                block_width = rng.randint(20, 60)
                block_height = rng.randint(5, 15)
                
                # Random glitch color
                glitch_color = (
                    rng.randint(0, 255),
                    rng.randint(0, 255),
                    rng.randint(0, 255),
                    rng.randint(100, 200)
                )
                
                draw_corrupt.rectangle(
                    [block_x, block_y, block_x + block_width, block_y + block_height],
                    fill=glitch_color
                )
        
        return blank_canvas 