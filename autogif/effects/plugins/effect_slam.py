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

class SlamEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "slam"

    @property
    def display_name(self) -> str:
        return "Slam"

    @property
    def supports_word_level(self) -> bool:
        return True

    @property
    def default_intensity(self) -> int:
        return 75

    def prepare(self, target_fps: int, caption_natural_duration_sec: float, text_length: int, intensity: int = None, **kwargs) -> None:
        """Calculate slam animation timing"""
        if intensity is None:
            intensity = kwargs.get('intensity', self.default_intensity)
        
        self.fps = max(1, target_fps)
        total_frames = max(1, math.ceil(caption_natural_duration_sec * target_fps))
        
        # Slam animation happens quickly at the start
        slam_duration_factor = 0.2 + (0.3 * (intensity / 100.0))  # 20-50% of duration
        self.slam_frames = max(3, int(total_frames * slam_duration_factor))
        
        # Impact parameters
        self.drop_height = 50 + (intensity / 100.0) * 100  # How far text drops from
        self.max_shockwave_radius = 80 + (intensity / 100.0) * 120  # Max shockwave size
        self.bounce_dampening = 0.7  # How much bounce reduces each time

    def transform(self, frame_image: Image.Image, text: str, base_position: tuple[int, int],
                  current_frame_index: int, intensity: int,
                  font: ImageFont.FreeTypeFont, font_color: str, 
                  outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int,
                  **kwargs) -> Image.Image:
        """
        Applies a slam effect where text drops down and impacts with shockwaves.
        """
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")
        
        # Create blank canvas for text
        blank_canvas = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        
        if not text or intensity == 0:
            # No slam, draw normally with multi-line support
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
        
        # Ensure slam is prepared
        if not hasattr(self, 'slam_frames'):
            # Set defaults if prepare wasn't called
            self.slam_frames = 15
            self.drop_height = 100
            self.max_shockwave_radius = 150
            self.bounce_dampening = 0.7
        
        draw = ImageDraw.Draw(blank_canvas)
        
        # Calculate slam animation progress using time-based approach
        # This allows word-level effects to work regardless of global frame index
        frame_time = current_frame_index / max(1, self.fps)
        slam_duration = self.slam_frames / max(1, self.fps)
        
        if frame_time < slam_duration:
            slam_progress = frame_time / max(0.1, slam_duration)
            
            # Phase 1: Drop (first 60% of slam)
            if slam_progress < 0.6:
                drop_progress = slam_progress / 0.6
                
                # Accelerating drop (gravity effect)
                gravity_factor = drop_progress * drop_progress  # Quadratic acceleration
                y_offset = -self.drop_height * (1.0 - gravity_factor)
                
                # No shockwave during drop
                shockwave_radius = 0
                text_scale = 1.0
                
            # Phase 2: Impact and bounce (last 40% of slam)
            else:
                impact_progress = (slam_progress - 0.6) / 0.4
                
                # Bounce effect with dampening
                bounce_cycles = 2  # Number of bounces
                bounce_value = math.sin(impact_progress * bounce_cycles * math.pi)
                bounce_height = self.drop_height * 0.3 * bounce_value * (1.0 - impact_progress)
                
                y_offset = -bounce_height * self.bounce_dampening
                
                # Shockwave expanding from impact
                shockwave_radius = impact_progress * self.max_shockwave_radius
                
                # Text compression on impact
                if impact_progress < 0.3:
                    compression_factor = 1.0 - (impact_progress / 0.3) * 0.2  # Compress by 20%
                    text_scale = compression_factor
                else:
                    text_scale = 0.8 + ((impact_progress - 0.3) / 0.7) * 0.2  # Restore to normal
        else:
            # Create repeating slam cycles for word-level effects
            # Add a pause between slams and repeat the animation
            slam_cycle_duration = slam_duration + 2.0  # 2 second pause between slams
            cycle_time = frame_time % slam_cycle_duration
            
            if cycle_time < slam_duration:
                # We're in a slam cycle, recalculate progress
                slam_progress = cycle_time / max(0.1, slam_duration)
                
                # Phase 1: Drop (first 60% of slam)
                if slam_progress < 0.6:
                    drop_progress = slam_progress / 0.6
                    
                    # Accelerating drop (gravity effect)
                    gravity_factor = drop_progress * drop_progress  # Quadratic acceleration
                    y_offset = -self.drop_height * (1.0 - gravity_factor)
                    
                    # No shockwave during drop
                    shockwave_radius = 0
                    text_scale = 1.0
                    
                # Phase 2: Impact and bounce (last 40% of slam)
                else:
                    impact_progress = (slam_progress - 0.6) / 0.4
                    
                    # Bounce effect with dampening
                    bounce_cycles = 2  # Number of bounces
                    bounce_value = math.sin(impact_progress * bounce_cycles * math.pi)
                    bounce_height = self.drop_height * 0.3 * bounce_value * (1.0 - impact_progress)
                    
                    y_offset = -bounce_height * self.bounce_dampening
                    
                    # Shockwave expanding from impact
                    shockwave_radius = impact_progress * self.max_shockwave_radius
                    
                    # Text compression on impact
                    if impact_progress < 0.3:
                        compression_factor = 1.0 - (impact_progress / 0.3) * 0.2  # Compress by 20%
                        text_scale = compression_factor
                    else:
                        text_scale = 0.8 + ((impact_progress - 0.3) / 0.7) * 0.2  # Restore to normal
            else:
                # Between slam cycles: text at rest
                y_offset = 0
                shockwave_radius = 0
                text_scale = 1.0
        
        # Draw shockwave rings
        if shockwave_radius > 10:
            # Multiple concentric shockwave rings
            for ring in range(3):
                ring_radius = shockwave_radius - (ring * 25)
                if ring_radius > 0:
                    # Ring opacity fades as it expands
                    ring_alpha = int(150 * (1.0 - (shockwave_radius / self.max_shockwave_radius)) * (1.0 - ring * 0.3))
                    if ring_alpha > 0:
                        ring_color = (255, 200, 100, ring_alpha)  # Orange impact color
                        
                        # Draw ring (ellipse outline)
                        ring_thickness = 2 + ring
                        for t in range(ring_thickness):
                            try:
                                draw.ellipse([
                                    text_anchor_x - ring_radius - t, text_anchor_y - ring_radius - t + y_offset,
                                    text_anchor_x + ring_radius + t, text_anchor_y + ring_radius + t + y_offset
                                ], outline=ring_color)
                            except:
                                pass  # Skip if drawing fails
        
        # Calculate text position with slam offset
        slam_text_y = text_anchor_y + y_offset
        
        # Create scaled font for impact compression
        if text_scale != 1.0:
            try:
                current_font_size = font.size if hasattr(font, 'size') else 24
                scaled_size = max(8, int(current_font_size * text_scale))
                if hasattr(font, 'path') and font.path:
                    scaled_font = ImageFont.truetype(font.path, scaled_size)
                else:
                    scaled_font = font
            except:
                scaled_font = font
        else:
            scaled_font = font
        
        # Enhanced coloring during impact
        original_color = parse_color_to_pil_format(font_color)
        if shockwave_radius > 0:
            # Make text more intense/red during impact
            if original_color.startswith('#'):
                r = int(original_color[1:3], 16)
                g = int(original_color[3:5], 16)
                b = int(original_color[5:7], 16)
            else:
                r, g, b = 255, 255, 255
            
            impact_factor = shockwave_radius / self.max_shockwave_radius
            impact_r = min(255, int(r + impact_factor * (255 - r)))
            impact_g = max(0, int(g * (1.0 - impact_factor * 0.3)))
            impact_b = max(0, int(b * (1.0 - impact_factor * 0.5)))
            slam_color = f"#{impact_r:02x}{impact_g:02x}{impact_b:02x}"
            slam_outline = "#8B0000"  # Dark red outline during impact
        else:
            slam_color = original_color
            slam_outline = parse_color_to_pil_format(outline_color)
        
        # Draw the slamming text with multi-line support
        enhanced_outline_width = outline_width + (2 if shockwave_radius > 0 else 0)
        
        draw_text_with_outline(
            draw, 
            (text_anchor_x, slam_text_y), 
            text,
            scaled_font, 
            slam_color, 
            slam_outline, 
            enhanced_outline_width, 
            anchor="mm",
            max_width=int(frame_width * 0.9)
        )
        
        # Add impact dust/debris particles
        if shockwave_radius > 30:
            import random
            # Set seed for consistent particles based on time
            time_seed = int(frame_time * 100) // 2  # Change every 0.02 seconds
            random.seed(hash(text) % 1000000 + time_seed)
            
            num_particles = int(10 + (intensity / 100.0) * 20)
            for i in range(num_particles):
                # Particle position around impact point
                angle = random.random() * 2 * math.pi
                distance = random.random() * shockwave_radius * 0.8
                
                particle_x = text_anchor_x + math.cos(angle) * distance
                particle_y = slam_text_y + math.sin(angle) * distance * 0.5  # Flatten vertically
                
                # Particle properties
                particle_size = random.randint(1, 3)
                particle_alpha = int(random.randint(100, 200) * (1.0 - shockwave_radius / self.max_shockwave_radius))
                
                if particle_alpha > 0:
                    # Dust/debris color (brown/gray)
                    gray_value = random.randint(80, 150)
                    particle_color = (gray_value, gray_value - 20, gray_value - 40, particle_alpha)
                    
                    try:
                        draw.ellipse([
                            particle_x - particle_size, particle_y - particle_size,
                            particle_x + particle_size, particle_y + particle_size
                        ], fill=particle_color)
                    except:
                        pass  # Skip if drawing fails
        
        return blank_canvas