from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
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

class BrushStrokeEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "brush-stroke"

    @property
    def display_name(self) -> str:
        return "Brush Stroke"

    @property
    def default_intensity(self) -> int:
        return 75

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """
        Prepare brush stroke animation using the actual caption timing from subtitles.
        """
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        self.fps = target_fps
        self.intensity = intensity
        
        # Get actual caption timing - this comes from the subtitle processing
        # The caption start/end times are already calculated by the grouping function
        self.caption_start_time = kwargs.get('caption_start_time', 0.0)
        self.caption_end_time = kwargs.get('caption_end_time', caption_natural_duration_sec)
        self.caption_duration = self.caption_end_time - self.caption_start_time
        
        # Animation timing based on intensity
        # Lower intensity = slower animation (uses more of caption time)
        # Higher intensity = faster animation (uses less of caption time)
        animation_speed_factor = 0.4 + (intensity / 100.0) * 0.4  # 0.4 to 0.8 of caption duration
        self.animation_duration = max(0.5, self.caption_duration * animation_speed_factor)
        
        # Animation starts immediately when caption starts
        self.animation_start_time = self.caption_start_time
        self.animation_end_time = self.animation_start_time + self.animation_duration
        
        # Make sure animation doesn't go past caption end
        if self.animation_end_time > self.caption_end_time:
            self.animation_end_time = self.caption_end_time
            self.animation_duration = self.animation_end_time - self.animation_start_time

    def _create_progressive_mask(self, width: int, height: int, progress: float) -> Image.Image:
        """
        Create a smooth progressive mask that reveals text from left to right.
        """
        mask = Image.new("L", (width, height), 0)  # Start fully transparent
        
        if progress <= 0:
            return mask
        
        draw = ImageDraw.Draw(mask)
        
        # Progressive left-to-right reveal with soft edge
        reveal_x = int(width * progress)
        
        if reveal_x > 0:
            # Fill revealed area
            draw.rectangle([0, 0, reveal_x, height], fill=255)
            
            # Add soft edge for brush-like effect
            soft_edge_width = max(6, int(width * 0.04))  # 4% of width
            
            if reveal_x < width and soft_edge_width > 0:
                # Create gradient edge
                for i in range(soft_edge_width):
                    if reveal_x + i < width:
                        # Fade from solid to transparent
                        fade_opacity = int(255 * (1.0 - (i / soft_edge_width)) ** 1.5)  # Smooth fade
                        draw.line([reveal_x + i, 0, reveal_x + i, height], fill=fade_opacity)
        
        # Add subtle brush texture
        if progress > 0.1:
            # Random vertical streaks for brush texture
            num_streaks = max(2, int(reveal_x * 0.015))
            for _ in range(num_streaks):
                x = random.randint(0, min(reveal_x, width-1))
                streak_height = random.randint(height//6, height//3)
                streak_y = random.randint(0, height - streak_height)
                streak_opacity = random.randint(180, 220)
                
                # Draw vertical streak
                for y in range(streak_y, min(streak_y + streak_height, height)):
                    if 0 <= x < width and 0 <= y < height:
                        current_pixel = mask.getpixel((x, y))
                        # Only brighten, don't darken
                        new_opacity = max(current_pixel, streak_opacity)
                        draw.point((x, y), fill=new_opacity)
        
        return mask

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Apply smooth brush stroke write-on effect using actual subtitle timing.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No brush effect, draw normally
            draw_text_with_outline(
                ImageDraw.Draw(blank_canvas), 
                (text_anchor_x, text_anchor_y), 
                text,
                font, 
                font_color, 
                outline_color, 
                outline_width, 
                anchor="ms",
                max_width=int(frame_width * 0.9)
            )
            return blank_canvas
        
        # Get current time based on frame index and FPS
        current_time = current_frame_index / self.fps
        
        # Ensure prepare was called with timing info
        if not hasattr(self, 'animation_start_time'):
            # Fallback if prepare wasn't called with proper timing
            self.prepare(12, 2.0, len(text), intensity, 
                        caption_start_time=0.0, 
                        caption_end_time=2.0)
        
        # Calculate animation progress based on actual time
        if current_time < self.animation_start_time:
            # Animation hasn't started yet
            progress = 0.0
        elif current_time >= self.animation_end_time:
            # Animation completed - show full text
            progress = 1.0
        else:
            # Currently animating
            time_into_animation = current_time - self.animation_start_time
            progress = time_into_animation / max(0.1, self.animation_duration)
            
            # Apply easing for smooth acceleration/deceleration
            # Ease-in-out cubic for natural motion
            if progress < 0.5:
                progress = 4 * progress * progress * progress
            else:
                progress = 1 - 4 * (1 - progress) ** 3
        
        # Clamp progress
        progress = max(0.0, min(1.0, progress))
        
        # Create full text image first
        full_text_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        draw_text_with_outline(
            ImageDraw.Draw(full_text_canvas), 
            (text_anchor_x, text_anchor_y), 
            text,
            font, 
            font_color, 
            outline_color, 
            outline_width, 
            anchor="ms",
            max_width=int(frame_width * 0.9)
        )
        
        if progress >= 1.0:
            # Animation complete, return full text
            return full_text_canvas
        
        if progress <= 0.0:
            # Animation not started, return empty canvas
            return blank_canvas
        
        # Get text bounding box for mask sizing
        bbox = full_text_canvas.getbbox()
        if not bbox:
            return blank_canvas
        
        text_left, text_top, text_right, text_bottom = bbox
        text_width = text_right - text_left
        text_height = text_bottom - text_top
        
        # Create progressive reveal mask
        brush_mask = self._create_progressive_mask(text_width + 40, text_height + 20, progress)
        
        # Apply mask to text
        result_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        # Position mask over text area
        mask_x = max(0, text_left - 20)
        mask_y = max(0, text_top - 10)
        
        # Create alpha mask for the entire canvas
        full_alpha_mask = Image.new("L", frame_image.size, 0)
        full_alpha_mask.paste(brush_mask, (mask_x, mask_y))
        
        # Apply mask to full text image
        masked_text = full_text_canvas.copy()
        
        # Convert brush mask to alpha channel
        text_pixels = list(masked_text.getdata())
        mask_pixels = list(full_alpha_mask.getdata())
        
        new_pixels = []
        for i, (r, g, b, a) in enumerate(text_pixels):
            mask_value = mask_pixels[i] if i < len(mask_pixels) else 0
            # Apply mask to alpha channel
            new_alpha = int((a * mask_value) / 255)
            new_pixels.append((r, g, b, new_alpha))
        
        masked_text.putdata(new_pixels)
        
        return masked_text