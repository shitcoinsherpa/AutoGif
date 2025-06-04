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

class SlamEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "slam"

    @property
    def display_name(self) -> str:
        return "Slam"

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
            # No slam, draw normally
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
        
        # Ensure slam is prepared
        if not hasattr(self, 'slam_frames'):
            # Set defaults if prepare wasn't called
            self.slam_frames = 15
            self.drop_height = 100
            self.max_shockwave_radius = 150
            self.bounce_dampening = 0.7
        
        draw = ImageDraw.Draw(blank_canvas)
        
        # Calculate slam animation progress
        if current_frame_index < self.slam_frames:
            slam_progress = current_frame_index / max(1, self.slam_frames)
            
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
            # Post-slam: text at rest
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
        if current_frame_index < self.slam_frames and shockwave_radius > 0:
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
        
        # Draw the slamming text
        enhanced_outline_width = outline_width + (2 if shockwave_radius > 0 else 0)
        
        try:
            draw.text((text_anchor_x, slam_text_y), text, font=scaled_font, fill=slam_color, 
                     anchor="ms", stroke_width=enhanced_outline_width, stroke_fill=slam_outline)
        except (TypeError, AttributeError):
            # Fallback for older PIL
            if enhanced_outline_width > 0:
                for dx in range(-enhanced_outline_width, enhanced_outline_width + 1):
                    for dy in range(-enhanced_outline_width, enhanced_outline_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((text_anchor_x + dx, slam_text_y + dy), text, 
                                    font=scaled_font, fill=slam_outline, anchor="ms")
            draw.text((text_anchor_x, slam_text_y), text, font=scaled_font, fill=slam_color, anchor="ms")
        
        # Add impact dust/debris particles
        if shockwave_radius > 30:
            import random
            # Set seed for consistent particles
            random.seed(hash(text) % 1000000 + current_frame_index // 2)
            
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