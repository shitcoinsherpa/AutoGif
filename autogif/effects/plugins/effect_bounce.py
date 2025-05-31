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

class BounceEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "bounce"

    @property
    def display_name(self) -> str:
        return "Bounce"

    @property
    def default_intensity(self) -> int:
        return 60

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """Calculate bounce timing for the caption duration"""
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        self.fps = max(1, target_fps)  # Ensure fps is at least 1
        self.total_frames = max(1, math.ceil(caption_natural_duration_sec * target_fps))
        
        # Intensity controls how much of the caption duration is used for bouncing
        # Higher intensity = longer bounce time
        bounce_duration_factor = 0.5 + (0.4 * (intensity / 100.0))  # 50% to 90% of duration
        self.bounce_frames = max(1, int(self.total_frames * bounce_duration_factor))
        
        # Calculate bounce parameters
        self.gravity = 0.8 + (0.4 * (intensity / 100.0))  # Gravity strength (increased for visibility)
        self.damping = 0.6  # Energy loss on bounce (reduced for more bounces)
        self.initial_velocity = -20 - (15 * (intensity / 100.0))  # Initial upward velocity (increased)

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a bounce effect where letters drop and bounce into position.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No bounce, draw normally
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
        
        # Ensure prepare was called
        if not hasattr(self, 'bounce_frames'):
            # If prepare wasn't called properly, set defaults
            self.fps = 12
            self.bounce_frames = 20
            self.gravity = 1.0
            self.damping = 0.6
            self.initial_velocity = -25
        
        # Convert colors
        pil_font_color = parse_color_to_pil_format(font_color)
        pil_outline_color = parse_color_to_pil_format(outline_color)
        
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
        
        # Draw each character with bounce
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
            
            # Calculate bounce offset for this character
            # Stagger the bounce timing for each character
            # Scale delay based on text length so all characters start within bounce window
            total_chars = len(text)
            # Ensure all characters start bouncing within first 30% of bounce frames
            max_delay_frames = max(1, int(self.bounce_frames * 0.3))
            char_delay = int((i / max(1, total_chars - 1)) * max_delay_frames) if total_chars > 1 else 0
            char_frame = max(0, current_frame_index - char_delay)
            
            y_offset = 0
            if char_frame < self.bounce_frames:
                # Simplified bounce physics for better visibility
                t = char_frame / float(self.fps)
                
                # Calculate position using damped harmonic motion
                # This creates a bouncing effect that gradually settles
                bounce_height = 100 + (50 * (intensity / 100.0))  # Start height
                frequency = 3.0  # Bounces per second
                damping_factor = 3.0  # How quickly it settles
                
                # Exponentially decaying sine wave
                decay = math.exp(-damping_factor * t)
                bounce = -bounce_height * decay * abs(math.sin(frequency * math.pi * t))
                
                y_offset = bounce
            else:
                # After bounce animation completes, text stays at rest position
                y_offset = 0
            
            # Character position
            char_y = text_anchor_y + y_offset
            
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
                draw.text((char_center_x, char_y), char, font=font, 
                         fill=pil_font_color, anchor="ms",
                         stroke_width=outline_width, stroke_fill=pil_outline_color)
            except (TypeError, AttributeError):
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((char_center_x + dx, char_y + dy), 
                                        char, font=font, fill=pil_outline_color, anchor="ms")
                draw.text((char_center_x, char_y), char, font=font, 
                         fill=pil_font_color, anchor="ms")
            
            # Advance position
            current_x += char_width
        
        return blank_canvas 