from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont, ImageOps
import math

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

class FadeEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "fade"

    @property
    def display_name(self) -> str:
        return "Fade"

    @property
    def default_intensity(self) -> int:
        return 50 # Intensity 0-100. Controls how much of duration is fade.

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """
        Calculate fade durations based on intensity and caption duration.
        Intensity (0-100): 
            0 = No fade, fully visible.
            100 = Full fade in then immediate fade out (e.g. 50% duration fade-in, 50% fade-out).
            50 = e.g. 25% fade-in, 50% visible, 25% fade-out.
        """
        # Extract intensity from kwargs if not provided as parameter
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
            
        self.total_caption_frames = math.ceil(caption_natural_duration_sec * target_fps)
        if self.total_caption_frames <= 0: self.total_caption_frames = 1

        # Intensity determines proportion of time spent fading (split between in and out)
        fade_proportion = intensity / 100.0  # 0.0 to 1.0

        self.fade_in_frames = math.ceil((self.total_caption_frames * fade_proportion) / 2.0)
        self.fade_out_frames = self.fade_in_frames
        
        # Ensure fade_in + fade_out doesn't exceed total frames, adjust if necessary
        if self.fade_in_frames + self.fade_out_frames > self.total_caption_frames:
            self.fade_in_frames = math.floor(self.total_caption_frames / 2.0)
            self.fade_out_frames = self.total_caption_frames - self.fade_in_frames

        self.fully_visible_start_frame = self.fade_in_frames
        self.fade_out_start_frame = self.total_caption_frames - self.fade_out_frames
        
        # print(f"Fade Prep for cap frames {self.total_caption_frames}: FI {self.fade_in_frames}, FO {self.fade_out_frames}, VIS_START {self.fully_visible_start_frame}, FO_START {self.fade_out_start_frame}")

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, # Relative to caption start (0-indexed)
                  intensity: int, 
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int, 
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a fade effect by drawing text with varying alpha based on frame position.
        This effect handles its own text rendering like typewriter and shake.
        """
        # Ensure frame is RGBA mode
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
            
        # Create a new blank canvas since fade replaces all text rendering
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text:
            return blank_canvas
            
        if intensity == 0 or self.total_caption_frames == 0:
            # No fade, draw normally
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

        # Calculate alpha multiplier based on fade timing
        if current_frame_index < self.fully_visible_start_frame: # Fading In
            if self.fade_in_frames == 0: 
                alpha_multiplier = 1.0
            else: 
                alpha_multiplier = current_frame_index / float(self.fade_in_frames)
                # Smooth fade in with ease-in curve
                alpha_multiplier = alpha_multiplier * alpha_multiplier
        elif current_frame_index >= self.fade_out_start_frame: # Fading Out
            if self.fade_out_frames == 0: 
                alpha_multiplier = 0.0 # Fully faded if no fade out frames & past start
            else:
                progress_in_fade_out = current_frame_index - self.fade_out_start_frame
                alpha_multiplier = 1.0 - (progress_in_fade_out / float(self.fade_out_frames))
                # Smooth fade out with ease-out curve
                alpha_multiplier = 1.0 - ((1.0 - alpha_multiplier) ** 2)
        else: # Fully Visible
            alpha_multiplier = 1.0
        
        alpha_multiplier = max(0.0, min(1.0, alpha_multiplier)) # Clamp to 0.0-1.0
        
        # Debug logging (uncomment when needed)
        # if current_frame_index % 3 == 0:  # Log every 3rd frame
        #     print(f"Fade: frame {current_frame_index}/{self.total_caption_frames}, alpha={alpha_multiplier:.2f}, "
        #           f"fade_in_frames={self.fade_in_frames}, fade_out_start={self.fade_out_start_frame}")

        if alpha_multiplier == 0.0:
            # Return a fully transparent canvas
            return blank_canvas

        # Draw text on a temporary canvas first
        temp_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        draw_text_with_outline(
            ImageDraw.Draw(temp_canvas), 
            (text_anchor_x, text_anchor_y), 
            text,
            font, 
            font_color, 
            outline_color, 
            outline_width, 
            anchor="ms",
            max_width=int(frame_width * 0.9)
        )

        if alpha_multiplier == 1.0:
            return temp_canvas # Fully opaque

        # Apply alpha multiplier to the text canvas
        alpha_band = temp_canvas.split()[3] # Get the alpha band
        modified_alpha_band = alpha_band.point(lambda p: int(p * alpha_multiplier))
        temp_canvas.putalpha(modified_alpha_band)
        
        return temp_canvas