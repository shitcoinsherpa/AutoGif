from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import math
import random
from datetime import datetime, timedelta

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

class VHSCRTEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "vhs-crt"

    @property
    def display_name(self) -> str:
        return "VHS/CRT"

    @property
    def supports_word_level(self) -> bool:
        return False

    @property
    def default_intensity(self) -> int:
        return 60

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """
        Prepare VHS/CRT effect parameters.
        This is a whole-frame effect that doesn't depend on text timing.
        """
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        self.fps = target_fps
        self.intensity = intensity
        
        # VHS characteristics based on intensity
        self.scanline_intensity = intensity / 100.0
        self.chromatic_aberration = (intensity / 100.0) * 3.0  # 0-3 pixel offset
        self.noise_level = (intensity / 100.0) * 0.15  # 0-15% noise
        self.barrel_distortion = (intensity / 100.0) * 0.02  # Subtle barrel effect
        
        # Show timecode if intensity > 50 (lowered threshold)
        self.show_timecode = intensity > 50
        
        # Generate some random static patterns for authenticity
        self.static_patterns = []
        for _ in range(10):
            pattern = []
            for _ in range(random.randint(8, 20)):  # More static points
                pattern.append({
                    'x': random.random(),
                    'y': random.random(),
                    'intensity': random.uniform(0.4, 1.0)  # Brighter static
                })
            self.static_patterns.append(pattern)

    def _apply_scanlines(self, image: Image.Image, intensity: float) -> Image.Image:
        """Apply CRT-style horizontal scan lines"""
        if intensity <= 0:
            return image
        
        width, height = image.size
        scanline_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(scanline_overlay)
        
        # Create scan lines - every 2-3 pixels
        scanline_spacing = 2 if intensity > 0.7 else 3
        # FIXED: Increased scanline opacity significantly
        scanline_opacity = int(255 * intensity * 0.8)  # Was 0.3, now 0.8 for much more visible lines
        
        for y in range(0, height, scanline_spacing):
            # Alternate between darker and lighter lines for realism
            if y % (scanline_spacing * 2) == 0:
                opacity = scanline_opacity
            else:
                opacity = int(scanline_opacity * 0.7)
            
            draw.line([0, y, width, y], fill=(0, 0, 0, opacity))
        
        # Apply subtle vertical phosphor effect (more visible)
        if intensity > 0.5:  # Lowered threshold
            for x in range(0, width, 3):
                draw.line([x, 0, x, height], fill=(0, 0, 0, int(scanline_opacity * 0.4)))  # Increased from 0.2
        
        return Image.alpha_composite(image.convert("RGBA"), scanline_overlay)

    def _apply_chromatic_aberration(self, image: Image.Image, offset: float, frame_index: int) -> Image.Image:
        """Apply RGB channel separation for VHS-style chromatic aberration"""
        if offset <= 0:
            return image
        
        # Add slight time-based variation for authentic VHS wobble
        time_wobble = math.sin(frame_index * 0.15) * 0.8  # Increased wobble
        actual_offset = offset + time_wobble
        
        # Split into RGB channels
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        r, g, b = image.split()
        
        # Create new image to composite channels with offsets
        result = Image.new("RGB", image.size, (0, 0, 0))
        
        # Red channel - shift right
        red_offset = int(actual_offset)
        if red_offset > 0:
            red_shifted = Image.new("L", image.size, 0)
            red_shifted.paste(r, (red_offset, 0))
        else:
            red_shifted = r
        
        # Green channel - no shift (reference)
        green_shifted = g
        
        # Blue channel - shift left
        blue_offset = int(-actual_offset)
        if blue_offset < 0:
            blue_shifted = Image.new("L", image.size, 0)
            blue_shifted.paste(b, (blue_offset, 0))
        else:
            blue_shifted = b
        
        # Recombine channels
        result = Image.merge("RGB", (red_shifted, green_shifted, blue_shifted))
        
        return result

    def _apply_barrel_distortion(self, image: Image.Image, distortion: float) -> Image.Image:
        """
        Simulate CRT barrel distortion with stronger vignette effect
        """
        if distortion <= 0:
            return image
        
        width, height = image.size
        
        # Create stronger vignette effect to simulate CRT curvature
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        
        center_x, center_y = width // 2, height // 2
        max_distance = math.sqrt(center_x**2 + center_y**2)
        
        # Create more pronounced radial gradient for vignette
        for y in range(0, height, 2):  # Skip every other row for performance
            for x in range(0, width, 2):  # Skip every other column
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                # Stronger effect at edges
                edge_factor = (distance / max_distance) ** 1.5  # More pronounced curve
                darkness = int(255 * distortion * edge_factor * 0.8)  # Increased from 0.4
                if darkness > 0:
                    # Draw 2x2 blocks for efficiency
                    draw.rectangle([x, y, x+1, y+1], fill=(0, 0, 0, darkness))
        
        # Apply vignette
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        result = Image.alpha_composite(image, vignette)
        
        return result

    def _add_vhs_noise(self, image: Image.Image, noise_level: float, frame_index: int) -> Image.Image:
        """Add VHS-style noise and static"""
        if noise_level <= 0:
            return image
        
        width, height = image.size
        noise_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(noise_overlay)
        
        # Use frame index to cycle through static patterns
        pattern_index = frame_index % len(self.static_patterns)
        current_pattern = self.static_patterns[pattern_index]
        
        # More aggressive noise
        for static_point in current_pattern:
            if random.random() < noise_level * 2.0:  # Increased probability
                x = int(static_point['x'] * width)
                y = int(static_point['y'] * height)
                intensity = static_point['intensity']
                
                # Random noise color (usually white/gray)
                noise_color = random.choice([
                    (255, 255, 255, int(255 * intensity)),  # White static
                    (200, 200, 255, int(255 * intensity * 0.8)),  # Blue tint
                    (255, 200, 200, int(255 * intensity * 0.8)),  # Red tint
                ])
                
                # Draw noise as larger rectangles for VHS look
                size = random.randint(1, 4)  # Increased size
                draw.rectangle([x, y, x + size, y + size], fill=noise_color)
        
        # More frequent horizontal lines (VHS tracking issues)
        if random.random() < noise_level * 0.8:  # Increased from 0.3
            y = random.randint(0, height)
            thickness = random.randint(1, 4)  # Thicker lines
            opacity = int(255 * noise_level)  # Increased opacity
            draw.rectangle([0, y, width, y + thickness], fill=(255, 255, 255, opacity))
        
        return Image.alpha_composite(image.convert("RGBA"), noise_overlay)

    def _add_timecode(self, image: Image.Image, frame_index: int) -> Image.Image:
        """Add retro VHS-style timecode overlay"""
        if not self.show_timecode:
            return image
        
        # Calculate fake timecode based on frame
        total_seconds = frame_index / max(self.fps, 1)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int((total_seconds * max(self.fps, 1)) % max(self.fps, 1))
        
        timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
        
        # Add fake date/time
        fake_date = "12/25/1987"  # Retro date
        
        # Create overlay
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # FIXED: Better font handling and sizing
        try:
            font_size = max(16, image.height // 30)  # Larger font size
            # Try to use a more authentic monospace font
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # FIXED: Better positioning - top right instead of bottom
        margin = 15
        text_width = len(timecode) * (font_size // 2)  # Estimate text width
        x = image.width - text_width - margin
        y = margin  # Top of screen instead of bottom
        
        # Draw more prominent background box for readability
        box_padding = 8  # Increased padding
        
        # Calculate text bounds more accurately
        try:
            text_bbox = draw.textbbox((x, y), timecode, font=font)
            date_bbox = draw.textbbox((x, y + 20), fake_date, font=font)
        except:
            # Fallback for older PIL versions
            text_width_est = len(timecode) * 8
            text_height_est = 16
            text_bbox = (x, y, x + text_width_est, y + text_height_est)
            date_bbox = (x, y + 20, x + len(fake_date) * 8, y + 36)
        
        full_bbox = (
            min(text_bbox[0], date_bbox[0]) - box_padding,
            text_bbox[1] - box_padding,
            max(text_bbox[2], date_bbox[2]) + box_padding,
            date_bbox[3] + box_padding
        )
        
        # More prominent background
        draw.rectangle(full_bbox, fill=(0, 0, 0, 220))  # Darker background
        draw.rectangle(full_bbox, outline=(80, 80, 80, 255), width=1)  # Border
        
        # Draw timecode text with better colors
        draw.text((x, y), timecode, fill=(255, 255, 0, 255), font=font)  # Bright yellow
        draw.text((x, y + 20), fake_date, fill=(255, 255, 255, 255), font=font)  # White
        
        return Image.alpha_composite(image.convert("RGBA"), overlay)

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Apply VHS/CRT effect to the entire frame.
        This effect works on the full frame regardless of text content.
        """
        # Ensure prepare was called
        if not hasattr(self, 'scanline_intensity'):
            self.prepare(12, 2.0, len(text or ""), intensity)
        
        # Work with the input frame (which may already have text/effects applied)
        result = frame_image.copy()
        
        if intensity == 0:
            return result
        
        # Apply effects in realistic order (how VHS/CRT would degrade signal)
        
        # 1. Chromatic aberration (signal degradation)
        if self.chromatic_aberration > 0.5:  # Only apply if significant
            result = self._apply_chromatic_aberration(result, self.chromatic_aberration, current_frame_index)
        
        # 2. VHS noise and static (early in pipeline so scanlines go over it)
        result = self._add_vhs_noise(result, self.noise_level, current_frame_index)
        
        # 3. Barrel distortion (CRT screen curvature)
        if self.barrel_distortion > 0.01:  # Only apply if significant
            result = self._apply_barrel_distortion(result, self.barrel_distortion)
        
        # 4. Scan lines (CRT display characteristic) - Applied last so they're most visible
        result = self._apply_scanlines(result, self.scanline_intensity)
        
        # 5. Timecode overlay (VHS recording feature)
        result = self._add_timecode(result, current_frame_index)
        
        # 6. Final color adjustment for VHS look
        if intensity > 30:
            # Convert to RGB for color enhancement
            if result.mode == "RGBA":
                result = result.convert("RGB")
            
            # Slightly desaturate and add warmth
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(0.9)  # Reduce saturation slightly
            
            # Add slight sepia/warm tint
            r, g, b = result.split()
            # Boost red/yellow slightly, reduce blue
            r = ImageEnhance.Brightness(r).enhance(1.03)
            g = ImageEnhance.Brightness(g).enhance(1.01)
            b = ImageEnhance.Brightness(b).enhance(0.97)
            result = Image.merge("RGB", (r, g, b))
        
        return result