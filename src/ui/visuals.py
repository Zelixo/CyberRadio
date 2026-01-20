import math
import random
from gi.repository import Gtk

class VectorCat(Gtk.DrawingArea):
    """A High-Fidelity Dynamic Long Cat."""
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

    def update(self, state):
        # Treat paused as idle for animation purposes
        anim_state = "idle" if state == "paused" else state
        self.current_state = state
        self.tick_count += 1

        # Wall pulse animation
        self.wall_pulse = (math.sin(self.tick_count * 0.1) + 1) / 2

        if anim_state == "playing":
            # Fast Bob
            cycle = (self.tick_count % 8) / 8.0
            self.head_bob = math.sin(cycle * math.pi * 2) * 1.5

            # Fast Tail
            self.tail_sway = math.sin(self.tick_count * 0.3) * 6

            # Paws Swing (Alternating)
            self.paw_swing = math.sin(self.tick_count * 0.25) * 3.0

            # Happy Eyes
            self.is_blinking = True

            # Normal breathe (relaxed while vibing)
            self.breathe_scale = math.sin(self.tick_count * 0.05) * 1.0

        else: # Idle (and Paused)
            # Slow breathe
            self.breathe_scale = math.sin(self.tick_count * 0.05) * 1.0

            # Slow Tail
            self.tail_sway = math.sin(self.tick_count * 0.05) * 4

            # Head steady
            self.head_bob = 0

            # Paws steady
            self.paw_swing = 0

            # Blink
            self.blink_timer += 1
            if self.blink_timer > 200:
                self.is_blinking = True
                if self.blink_timer > 205:
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

    def draw_cat(self, area, cr, w, h):
        S = 3 # Scale

        # Colors
        C_CYAN = (0.0, 0.9, 1.0, 1.0)
        C_CYAN_DIM = (0.0, 0.6, 0.7, 1.0)
        C_PINK = (1.0, 0.0, 1.0, 1.0)
        C_WHITE = (1.0, 1.0, 1.0, 1.0)
        C_DARK = (0.1, 0.1, 0.15, 1.0)
        C_BLACK = (0.05, 0.05, 0.1, 1.0)

        cx = w / 2
        cy = h / 2

        # Wall / Ledge position
        wall_y = cy + 10 * S

        # --- DYNAMIC BODY CALCULATION ---
        # Calculate available width minus padding for head(left) and tail(right)
        # Head takes ~50px, Tail takes ~50px.
        # We want margin from widget edges.
        margin = 30

        max_body_w = max(40 * S, w - (margin * 2) - (50 * S))

        # Center body rect
        body_x = (w - max_body_w) / 2
        body_y = wall_y - 12 * S

        # --- WALL / LEDGE ---
        # Spans full width now
        cr.set_source_rgba(0.0, 0.9, 1.0, 0.2 + (self.wall_pulse * 0.2))
        cr.rectangle(0, wall_y, w, 4*S)
        cr.fill()

        self.draw_px(cr, 0, wall_y, w, 2*S, C_CYAN)

        # Ticks on bar
        for i in range(0, int(w), int(10*S)):
            self.draw_px(cr, i, wall_y + 2*S, 1*S, 2*S, C_CYAN_DIM)

        # --- TAIL (Behind, Anchored Right) ---
        tail_root_x = body_x + max_body_w - (5 * S)
        tail_root_y = wall_y - 8 * S

        # Procedural pixel tail based on angle
        for i in range(12):
            tx = tail_root_x + (i * S * 0.8)
            # Dangle down
            ty = tail_root_y + (i * S * 1.5)
            # Sway physics
            sway = math.sin(i * 0.5 + self.tick_count * 0.1) * (self.tail_sway/4)

            self.draw_px(cr, tx + sway, ty, 3*S, 3*S, C_PINK)

        # --- BODY (Elastic Long) ---
        # Breathe effect (Chest rises/falls)
        chest_lift = self.breathe_scale * S

        # Main Block (Stretched)
        self.draw_px(cr, body_x, body_y - chest_lift, max_body_w, 12*S + chest_lift, C_CYAN)
        # Shading bottom
        self.draw_px(cr, body_x, wall_y - 2*S, max_body_w, 2*S, C_CYAN_DIM)

        # White Belly (Stretched)
        self.draw_px(cr, body_x + 5*S, body_y - chest_lift + 2*S, max_body_w - 10*S, 6*S, C_WHITE)

        # --- BACK LEGS (Anchored Right) ---
        haunch_x = body_x + max_body_w - (8 * S)
        haunch_y = body_y - chest_lift + 2 * S
        self.draw_px(cr, haunch_x, haunch_y, 6*S, 8*S, C_CYAN)
        self.draw_px(cr, haunch_x + 1*S, haunch_y + 2*S, 4*S, 4*S, C_WHITE)

        # Back foot resting on wall
        foot_x = haunch_x + 2*S
        foot_y = wall_y - 2*S
        self.draw_px(cr, foot_x, foot_y, 5*S, 3*S, C_WHITE)
        self.draw_px(cr, foot_x + 3*S, foot_y + 1*S, 2*S, 1*S, C_PINK)

        # --- FRONT PAWS (Anchored Left, Swinging) ---
        # Left Paw
        lp_x = body_x + 5 * S + self.paw_swing * S
        lp_y = wall_y
        self.draw_px(cr, lp_x, lp_y, 4*S, 6*S, C_WHITE) # Dangle
        self.draw_px(cr, lp_x + 1*S, lp_y + 4*S, 2*S, 2*S, C_PINK) # Toe beans

        # Right Paw
        rp_swing = -self.paw_swing if self.current_state == "playing" else 0
        rp_x = body_x + 15 * S + rp_swing * S
        rp_y = wall_y
        self.draw_px(cr, rp_x, rp_y, 4*S, 6*S, C_WHITE) # Dangle
        self.draw_px(cr, rp_x + 1*S, rp_y + 4*S, 2*S, 2*S, C_PINK) # Toe beans

        # --- HEAD (Anchored Left) ---
        cr.save()
        # Head pivot
        head_base_x = body_x - 5 * S
        head_base_y = body_y - 5 * S

        # Apply Head Bob
        cr.translate(0, self.head_bob)

        # Head Shape (Pixel Blob)
        self.draw_px(cr, head_base_x, head_base_y, 24*S, 18*S, C_CYAN)

        # Ears
        self.draw_px(cr, head_base_x + 2*S, head_base_y - 6*S, 6*S, 6*S, C_CYAN) # L
        self.draw_px(cr, head_base_x + 4*S, head_base_y - 4*S, 2*S, 4*S, C_PINK) # L Inner

        self.draw_px(cr, head_base_x + 16*S, head_base_y - 6*S, 6*S, 6*S, C_CYAN) # R
        self.draw_px(cr, head_base_x + 18*S, head_base_y - 4*S, 2*S, 4*S, C_PINK) # R Inner

        # Headphones Band
        self.draw_px(cr, head_base_x + 4*S, head_base_y - 7*S, 16*S, 3*S, C_DARK)
        # Cans
        self.draw_px(cr, head_base_x - 2*S, head_base_y + 2*S, 4*S, 10*S, C_DARK)
        self.draw_px(cr, head_base_x - 1*S, head_base_y + 4*S, 1*S, 6*S, C_PINK) # Glow
        self.draw_px(cr, head_base_x + 22*S, head_base_y + 2*S, 4*S, 10*S, C_DARK) # R
        self.draw_px(cr, head_base_x + 24*S, head_base_y + 4*S, 1*S, 6*S, C_PINK) # Glow

        # Face
        eye_y = head_base_y + 8*S
        eye_x_l = head_base_x + 6*S
        eye_x_r = head_base_x + 16*S

        # Eyes logic
        if self.current_state == "playing" or self.is_blinking:
             # ^ ^  or - -
             self.draw_px(cr, eye_x_l, eye_y, 4*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_l + 1*S, eye_y - 1*S, 2*S, 1*S, C_BLACK)

             self.draw_px(cr, eye_x_r, eye_y, 4*S, 1*S, C_BLACK)
             self.draw_px(cr, eye_x_r + 1*S, eye_y - 1*S, 2*S, 1*S, C_BLACK)

        # Paused is now treated like Idle/Normal
        else:
             # Normal . .
             self.draw_px(cr, eye_x_l + 1*S, eye_y, 2*S, 2*S, C_BLACK)
             self.draw_px(cr, eye_x_r + 1*S, eye_y, 2*S, 2*S, C_BLACK)

        # Cheeks
        self.draw_px(cr, head_base_x + 4*S, head_base_y + 12*S, 3*S, 2*S, C_PINK)
        self.draw_px(cr, head_base_x + 17*S, head_base_y + 12*S, 3*S, 2*S, C_PINK)

        # Nose
        self.draw_px(cr, head_base_x + 11*S, head_base_y + 11*S, 2*S, 1*S, C_BLACK)

        cr.restore()

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
