import math
import random
from gi.repository import Gtk

class VectorCat(Gtk.DrawingArea):
    """A High-Fidelity Dynamic Long Cat (Kath Edition)."""
    def __init__(self):
        super().__init__()
        # Allow expanding
        self.set_hexpand(True)
        self.set_content_height(160)
        self.set_draw_func(self.draw_cat)

        self.tick_count = 0
        self.current_state = "idle"

        # Animation vars
        self.breathe_scale = 0.0
        self.head_bob = 0.0
        self.tail_sway = 0.0
        self.paw_swing = 0.0
        self.blink_timer = 0
        self.is_blinking = False
        self.wall_pulse = 0.0
        
        # Particles (x, y, age, type)
        self.particles = []

    def update(self, state):
        # Treat paused as idle for animation purposes
        anim_state = "idle" if state == "paused" else state
        self.current_state = state
        self.tick_count += 1

        # Wall pulse animation
        self.wall_pulse = (math.sin(self.tick_count * 0.1) + 1) / 2

        # Particle Logic
        if anim_state == "playing":
            if random.random() < 0.05: # Spawn chance
                p_type = "heart" if random.random() < 0.7 else "note"
                # Spawn near head
                self.particles.append([
                    random.uniform(-20, 20), # x offset relative to head
                    random.uniform(-10, 0),  # y offset
                    0,                       # age
                    p_type
                ])

        # Update particles
        alive_particles = []
        for p in self.particles:
            p[1] -= 0.5 # Float up
            p[2] += 1   # Age
            if p[2] < 100: # Max age
                alive_particles.append(p)
        self.particles = alive_particles

        if anim_state == "playing":
            # Bouncier Bob
            cycle = (self.tick_count % 16) / 16.0
            self.head_bob = math.sin(cycle * math.pi * 2) * 2.0

            # Smoother Tail
            self.tail_sway = math.sin(self.tick_count * 0.2) * 8

            # Paws Swing (Alternating)
            self.paw_swing = math.sin(self.tick_count * 0.25) * 4.0

            # Happy Eyes
            self.is_blinking = True

            # Excited breathe
            self.breathe_scale = math.sin(self.tick_count * 0.1) * 1.5

        else: # Idle (and Paused)
            # Sleepy breathe
            self.breathe_scale = math.sin(self.tick_count * 0.04) * 0.8

            # Lazy Tail
            self.tail_sway = math.sin(self.tick_count * 0.05) * 3

            # Head steady
            self.head_bob = 0

            # Paws steady
            self.paw_swing = 0

            # Blink
            self.blink_timer += 1
            if self.blink_timer > 150: # More frequent blinks
                self.is_blinking = True
                if self.blink_timer > 158:
                    self.is_blinking = False
                    self.blink_timer = 0
            else:
                self.is_blinking = False

        self.queue_draw()
        return True

    def draw_px(self, cr, x, y, w, h, color):
        """Draws a crisp rectangle."""
        cr.set_source_rgba(*color)
        cr.rectangle(x, y, w, h)
        cr.fill()
    
    def draw_heart(self, cr, x, y, s, alpha):
        """Draws a pixel heart."""
        cr.set_source_rgba(0.96, 0.76, 0.90, alpha) # Pink
        # shape:
        # . x . x .
        # x x x x x
        # x x x x x
        # . x x x .
        # . . x . .
        size = 2 * s
        cr.rectangle(x + size, y, size, size)
        cr.rectangle(x + 3*size, y, size, size)
        cr.rectangle(x, y + size, 5*size, 2*size)
        cr.rectangle(x + size, y + 3*size, 3*size, size)
        cr.rectangle(x + 2*size, y + 4*size, size, size)
        cr.fill()

    def draw_cat(self, area, cr, w, h):
        S = 3 # Scale

        # Kath/Catppuccin Palette
        C_BLUE = (0.54, 0.70, 0.98, 1.0) # #89b4fa (Blue)
        C_LAVENDER = (0.70, 0.80, 1.0, 1.0) # #b4befe (Lavender)
        C_PINK = (0.96, 0.76, 0.90, 1.0) # #f5c2e7 (Pink)
        C_MAUVE = (0.80, 0.65, 0.97, 1.0) # #cba6f7 (Mauve)
        C_WHITE = (0.80, 0.84, 0.96, 1.0) # #cdd6f4 (Text) - warm white
        C_DARK = (0.11, 0.11, 0.18, 1.0) # #1e1e2e (Base)
        C_BLACK = (0.07, 0.07, 0.11, 1.0) # #11111b (Crust)

        cx = w / 2
        cy = h / 2

        # Wall / Ledge position
        wall_y = cy + 10 * S

        # --- DYNAMIC BODY CALCULATION ---
        margin = 30
        max_body_w = max(40 * S, w - (margin * 2) - (50 * S))

        # Center body rect
        body_x = (w - max_body_w) / 2
        body_y = wall_y - 12 * S

        # --- WALL / LEDGE ---
        cr.set_source_rgba(0.80, 0.65, 0.97, 0.2 + (self.wall_pulse * 0.1)) # Mauve glow
        cr.rectangle(0, wall_y, w, 4*S)
        cr.fill()

        self.draw_px(cr, 0, wall_y, w, 2*S, C_MAUVE)

        for i in range(0, int(w), int(12*S)):
            self.draw_px(cr, i, wall_y + 2*S, 1*S, 2*S, C_PINK)

        # --- TAIL ---
        tail_root_x = body_x + max_body_w - (5 * S)
        tail_root_y = wall_y - 8 * S

        for i in range(14): # Longer tail
            tx = tail_root_x + (i * S * 0.7)
            ty = tail_root_y + (i * S * 1.3)
            sway = math.sin(i * 0.4 + self.tick_count * 0.1) * (self.tail_sway/3)
            self.draw_px(cr, tx + sway, ty, 3*S, 3*S, C_LAVENDER)

        # --- BODY ---
        chest_lift = self.breathe_scale * S

        # Main Block
        self.draw_px(cr, body_x, body_y - chest_lift, max_body_w, 12*S + chest_lift, C_BLUE)
        # Shading
        self.draw_px(cr, body_x, wall_y - 2*S, max_body_w, 2*S, C_LAVENDER)

        # White Belly
        self.draw_px(cr, body_x + 5*S, body_y - chest_lift + 2*S, max_body_w - 10*S, 6*S, C_WHITE)

        # --- BACK LEGS ---
        haunch_x = body_x + max_body_w - (8 * S)
        haunch_y = body_y - chest_lift + 2 * S
        self.draw_px(cr, haunch_x, haunch_y, 6*S, 8*S, C_BLUE)
        self.draw_px(cr, haunch_x + 1*S, haunch_y + 2*S, 4*S, 4*S, C_WHITE)

        foot_x = haunch_x + 2*S
        foot_y = wall_y - 2*S
        self.draw_px(cr, foot_x, foot_y, 5*S, 3*S, C_WHITE)
        self.draw_px(cr, foot_x + 3*S, foot_y + 1*S, 2*S, 1*S, C_PINK) # Pink beans

        # --- FRONT PAWS ---
        # Left
        lp_x = body_x + 5 * S + self.paw_swing * S
        lp_y = wall_y
        self.draw_px(cr, lp_x, lp_y, 4*S, 6*S, C_WHITE)
        self.draw_px(cr, lp_x + 1*S, lp_y + 4*S, 2*S, 2*S, C_PINK)

        # Right
        rp_swing = -self.paw_swing if self.current_state == "playing" else 0
        rp_x = body_x + 15 * S + rp_swing * S
        rp_y = wall_y
        self.draw_px(cr, rp_x, rp_y, 4*S, 6*S, C_WHITE)
        self.draw_px(cr, rp_x + 1*S, rp_y + 4*S, 2*S, 2*S, C_PINK)

        # --- HEAD ---
        cr.save()
        head_base_x = body_x - 5 * S
        head_base_y = body_y - 5 * S
        cr.translate(0, self.head_bob)

        # Head Shape
        self.draw_px(cr, head_base_x, head_base_y, 24*S, 18*S, C_BLUE)

        # Ears
        self.draw_px(cr, head_base_x + 2*S, head_base_y - 6*S, 6*S, 6*S, C_BLUE)
        self.draw_px(cr, head_base_x + 4*S, head_base_y - 4*S, 2*S, 4*S, C_PINK)

        self.draw_px(cr, head_base_x + 16*S, head_base_y - 6*S, 6*S, 6*S, C_BLUE)
        self.draw_px(cr, head_base_x + 18*S, head_base_y - 4*S, 2*S, 4*S, C_PINK)

        # Headphones
        self.draw_px(cr, head_base_x + 4*S, head_base_y - 7*S, 16*S, 3*S, C_DARK)
        self.draw_px(cr, head_base_x - 2*S, head_base_y + 2*S, 4*S, 10*S, C_DARK)
        self.draw_px(cr, head_base_x - 1*S, head_base_y + 4*S, 1*S, 6*S, C_PINK) # Glow
        self.draw_px(cr, head_base_x + 22*S, head_base_y + 2*S, 4*S, 10*S, C_DARK)
        self.draw_px(cr, head_base_x + 24*S, head_base_y + 4*S, 1*S, 6*S, C_PINK) # Glow

        # Face
        eye_y = head_base_y + 8*S
        eye_x_l = head_base_x + 6*S
        eye_x_r = head_base_x + 16*S

        if self.current_state == "playing" or self.is_blinking:
             # ^ ^ style eyes for maximum uwu
             # Left
             self.draw_px(cr, eye_x_l, eye_y, 1*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_l + 1*S, eye_y - 1*S, 2*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_l + 3*S, eye_y, 1*S, 1*S, C_BLACK)

             # Right
             self.draw_px(cr, eye_x_r, eye_y, 1*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_r + 1*S, eye_y - 1*S, 2*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_r + 3*S, eye_y, 1*S, 1*S, C_BLACK)
        else:
             # Rounder eyes
             self.draw_px(cr, eye_x_l + 1*S, eye_y - 1*S, 2*S, 3*S, C_BLACK)
             self.draw_px(cr, eye_x_r + 1*S, eye_y - 1*S, 2*S, 3*S, C_BLACK)

        # Blush
        self.draw_px(cr, head_base_x + 4*S, head_base_y + 11*S, 4*S, 2*S, C_PINK)
        self.draw_px(cr, head_base_x + 17*S, head_base_y + 11*S, 4*S, 2*S, C_PINK)

        # Nose
        self.draw_px(cr, head_base_x + 11*S, head_base_y + 11*S, 2*S, 1*S, C_BLACK)

        cr.restore()
        
        # --- PARTICLES ---
        # Draw particles relative to head center (approx)
        head_center_x = head_base_x + 12*S
        head_center_y = head_base_y + 6*S
        
        for p in self.particles:
            px = head_center_x + p[0]*S
            py = head_center_y + p[1]*S
            alpha = 1.0 - (p[2] / 100.0)
            if p[3] == "heart":
                self.draw_heart(cr, px, py, 1*S, alpha)
            else:
                # Small note square
                cr.set_source_rgba(0.80, 0.65, 0.97, alpha) # Mauve
                cr.rectangle(px, py, 3*S, 3*S)
                cr.fill()

class SpectrumVisualizer(Gtk.Box):
    """A physics-based spectrum visualizer simulation (Gravity + Beat)."""
    def __init__(self, bars=28):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.set_size_request(-1, 50)
        self.bars = []
        self.values = [0.0] * bars
        # velocity for falling effect
        self.velocities = [0.0] * bars
        self.tick_count = 0

        for _ in range(bars):
            vb = Gtk.LevelBar()
            vb.set_orientation(Gtk.Orientation.VERTICAL)
            vb.set_inverted(True)
            vb.set_mode(Gtk.LevelBarMode.CONTINUOUS)
            vb.set_min_value(0)
            vb.set_max_value(1)
            vb.set_hexpand(True)
            vb.add_css_class("vis-bar")
            self.append(vb)
            self.bars.append(vb)

    def update(self, is_playing):
        if not is_playing:
            for i, bar in enumerate(self.bars):
                # Simple linear decay
                self.values[i] = max(0, self.values[i] - 0.05)
                bar.set_value(self.values[i])
            return True

        self.tick_count += 0.25

        beat_trigger = math.sin(self.tick_count * 3) > 0.8

        for i in range(len(self.bars)):
            self.velocities[i] -= 0.04
            center_bias = 1.0 - (abs(i - len(self.bars)/2) / (len(self.bars)/2))
            energy = random.random()

            if beat_trigger and energy > 0.6:
                kick = energy * center_bias * 0.6
                self.velocities[i] = max(self.velocities[i], kick)

            sustained = (math.sin(self.tick_count + i * 0.5) + 1) / 2 * 0.1
            self.velocities[i] += sustained * 0.1

            self.values[i] += self.velocities[i]

            if self.values[i] < 0:
                self.values[i] = 0
                self.velocities[i] = 0

            if self.values[i] > 1.0:
                self.values[i] = 1.0
                self.velocities[i] = -0.1

            self.bars[i].set_value(self.values[i])

        return True
