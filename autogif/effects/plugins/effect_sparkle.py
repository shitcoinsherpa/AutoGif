from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont
import random
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

class SparkleEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "sparkle"

    @property
    def display_name(self) -> str:
        return "Sparkle"

    @property
    def default_intensity(self) -> int:
        return 65

    def prepare(self, **kwargs) -> None:
        """Initialize sparkle particles"""
        # Generate consistent sparkles based on text  
        text = kwargs.get('text', '')
        if not text:
            # Use a default seed if no text provided
            self.random_seed = 12345
        else:
            self.random_seed = hash(text) % 1000000
        
        # Create sparkle particles
        rng = random.Random(self.random_seed)
        intensity = kwargs.get('intensity', self.default_intensity)
        
        # Number of sparkles based on intensity
        num_sparkles = int(5 + (intensity / 100.0) * 20)  # 5-25 sparkles
        
        self.sparkles = []
        for i in range(num_sparkles):
            sparkle = {
                'x_offset': rng.randint(-100, 100),
                'y_offset': rng.randint(-40, 40),
                'phase': rng.random() * 2 * math.pi,
                'frequency': 0.5 + rng.random() * 2.0,  # 0.5-2.5 Hz
                'size': rng.randint(2, 6),
                'style': rng.choice(['star', 'dot', 'plus'])
            }
            self.sparkles.append(sparkle)

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Adds magical sparkles around the text.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas since sparkle is now a text-drawing effect
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No sparkles, just draw text normally
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
        
        # Ensure sparkles are prepared for this text
        if not hasattr(self, 'last_caption_text') or self.last_caption_text != text:
            self.last_caption_text = text
            self.prepare(text=text, intensity=intensity)
        
        # Draw the text first
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
        
        # Get FPS for animation
        fps = kwargs.get('target_fps', 12)
        time = current_frame_index / fps
        
        # Now draw sparkles on the canvas
        for sparkle in self.sparkles:
            # Calculate sparkle brightness (pulsing)
            brightness = math.sin(sparkle['phase'] + time * sparkle['frequency'] * 2 * math.pi)
            brightness = (brightness + 1) / 2  # Normalize to 0-1
            
            # Skip if too dim
            if brightness < 0.3:
                continue
            
            # Sparkle position
            x = text_anchor_x + sparkle['x_offset']
            y = text_anchor_y + sparkle['y_offset']
            
            # Sparkle color (white to yellow gradient based on brightness)
            r = 255
            g = int(255 - (1 - brightness) * 50)  # Yellow tint when bright
            b = int(255 - (1 - brightness) * 100)  # More yellow when bright
            alpha = int(brightness * 255)
            sparkle_color = (r, g, b, alpha)
            
            size = sparkle['size'] * brightness
            
            # Draw sparkle based on style
            if sparkle['style'] == 'star':
                # Four-pointed star
                points = []
                for angle in [0, 90, 180, 270]:
                    rad = math.radians(angle)
                    points.append((
                        x + math.cos(rad) * size,
                        y + math.sin(rad) * size
                    ))
                
                # Draw lines from center to each point
                for point in points:
                    draw.line([x, y, point[0], point[1]], fill=sparkle_color, width=1)
                
                # Draw diagonal lines for 8-pointed star
                for angle in [45, 135, 225, 315]:
                    rad = math.radians(angle)
                    end_x = x + math.cos(rad) * size * 0.7
                    end_y = y + math.sin(rad) * size * 0.7
                    draw.line([x, y, end_x, end_y], fill=sparkle_color, width=1)
                
            elif sparkle['style'] == 'dot':
                # Simple circle
                draw.ellipse([x - size/2, y - size/2, x + size/2, y + size/2], 
                           fill=sparkle_color)
                
            else:  # 'plus'
                # Plus sign
                draw.line([x - size, y, x + size, y], fill=sparkle_color, width=2)
                draw.line([x, y - size, x, y + size], fill=sparkle_color, width=2)
        
        return blank_canvas 