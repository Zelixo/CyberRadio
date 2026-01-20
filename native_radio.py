import sys
import gi
import logging
import threading
import json
import urllib.request
import urllib.parse
import os
import random
import math
import time

# Ensure we are using the correct versions of GTK and Adwaita
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import Gtk, Adw, GLib, Gio, GObject, Gdk, GdkPixbuf

# Import MPV for audio
try:
    import mpv
except ImportError:
    print("Error: python-mpv not found. Please install it via pacman or pip.")
    sys.exit(1)

# --- CONSTANTS ---
SEARCH_API_URL = "https://de1.api.radio-browser.info/json/stations/search"
AZURACAST_API_URL = "https://radio.zelixo.net/api/nowplaying"
FAVORITES_FILE = "cyber_favorites.json"

DEFAULT_STATIONS = [
    {
        "name": "Nostalgia OST",
        "url_resolved": "https://radio.zelixo.net/listen/nostalgia_ost/stream",
        "countrycode": "OST",
        "favicon": "https://radio.zelixo.net/static/uploads/nostalgia_ost/album_art.1737523202.png"
    },
    {
        "name": "Night City Radio",
        "url_resolved": "https://radio.zelixo.net/listen/night_city_radio/ncradio",
        "countrycode": "NC",
        "favicon": "https://radio.zelixo.net/static/uploads/night_city_radio/album_art.1759461316.png"
    },
    {
        "name": "Japan EDM",
        "url_resolved": "https://radio.zelixo.net/listen/japedm/radio.flac",
        "countrycode": "JP",
        "favicon": "https://radio.zelixo.net/static/uploads/japedm/album_art.1744086733.jpg"
    },
    {
        "name": "DJ Zel Radio",
        "url_resolved": "https://radio.zelixo.net/listen/dj_zel/radio.mp3",
        "countrycode": "ZL",
        "favicon": "https://radio.zelixo.net/static/uploads/dj_zel/album_art.1737590207.png"
    },
    {
        "name": "ACNH Radio",
        "url_resolved": "https://radio.zelixo.net/listen/acnh_radio/radio.mp3",
        "countrycode": "AC",
        "favicon": "https://radio.zelixo.net/static/uploads/acnh_radio/album_art.1757640781.jpg"
    },
    {
        "name": "Lofi Girl",
        "url_resolved": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "countrycode": "FR",
        "favicon": "https://yt3.googleusercontent.com/ytc/AIdro_k4kF9xXq8vG5Q-7Jd3yR-u3Q1v7g-X3y9x-g=s900-c-k-c0x00ffffff-no-rj"
    }
]

# --- CUSTOM CSS (SYNTHWAVE THEME) ---
CYBER_CSS = b"""
.cyber-window {
    background-color: #050510;
    color: #e0e0ff;
}

/* Sidebar styling */
.sidebar-box {
    background-color: #08080c;
    border-right: 1px solid #1a1a2e;
}

.boxed-list {
    background-color: transparent;
    color: #e0e0ff;
}

row:selected {
    background-color: #2a0033;
    color: #00f3ff;
    border-left: 2px solid #ff00ff;
}

/* Player Area */
.player-container {
    background: linear-gradient(160deg, #0f0f20 0%, #050510 100%);
    padding: 20px;
}

.track-title {
    color: #ff00ff;
    font-weight: 900;
    font-size: 22px;
    text-shadow: 0 0 12px rgba(255, 0, 255, 0.4);
}

.station-name {
    color: #00f3ff;
    font-weight: bold;
    font-size: 14px;
    opacity: 0.8;
    margin-bottom: 10px;
}

/* Buttons */
button.suggested-action {
    background: linear-gradient(135deg, #bd00ff 0%, #00f3ff 100%);
    color: #000000;
    font-weight: 800;
    border: none;
    box-shadow: 0 0 20px rgba(189, 0, 255, 0.3);
}

button.suggested-action:hover {
    box-shadow: 0 0 30px rgba(0, 243, 255, 0.6);
}

/* Sliders */
scale trough {
    background-color: #2a2a40;
    min-height: 4px;
    border-radius: 2px;
}

scale highlight {
    background: linear-gradient(to right, #ff00ff, #00f3ff);
    border-radius: 2px;
}
"""

class AudioPlayer:
    """Handles MPV logic independently."""
    def __init__(self, on_metadata_change, on_discontinuity=None):
        self.mpv = mpv.MPV(
            video=False,
            ytdl=True,
            log_handler=self._mpv_log,
            cache='yes'
        )
        self.mpv.set_loglevel('info')
        self.on_metadata_change = on_metadata_change
        self.on_discontinuity = on_discontinuity

        self.mpv.observe_property('media-title', self._handle_metadata)
        self.mpv.observe_property('icy-title', self._handle_metadata)

    def _mpv_log(self, level, prefix, text):
        if "Linearizing discontinuity" in text:
            if self.on_discontinuity:
                GLib.idle_add(self.on_discontinuity)
            return
        if level in ['warn', 'error', 'info']:
            print(f"[MPV {level}] {prefix}: {text}")

    def play(self, url):
        try:
            self.mpv.play(url)
            self.mpv.pause = False
        except Exception as e:
            print(f"ERROR: MPV Play failed: {e}")

    def pause(self):
        self.mpv.cycle('pause')

    def stop(self):
        self.mpv.stop()

    def set_volume(self, volume):
        self.mpv.volume = volume

    def get_is_paused(self):
        return self.mpv.pause if hasattr(self.mpv, 'pause') else False

    def _handle_metadata(self, _name, value):
        if value:
            GLib.idle_add(self.on_metadata_change, value)

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

class AddStationDialog(Adw.Window):
    def __init__(self, parent_window, on_save_callback):
        super().__init__(modal=True, transient_for=parent_window)
        self.set_title("Add Custom Station")
        self.set_default_size(400, 300)
        self.on_save = on_save_callback

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)
        self.set_content(box)

        label = Gtk.Label(label="Enter Station Details")
        label.add_css_class("title-1")
        box.append(label)

        self.name_entry = Adw.EntryRow(title="Station Name")
        self.url_entry = Adw.EntryRow(title="Stream URL")

        group = Adw.PreferencesGroup()
        group.add(self.name_entry)
        group.add(self.url_entry)
        box.append(group)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns_box.set_halign(Gtk.Align.CENTER)
        box.append(btns_box)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        btns_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Add Station")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")
        save_btn.connect("clicked", self.on_save_clicked)
        btns_box.append(save_btn)

    def on_save_clicked(self, btn):
        name = self.name_entry.get_text()
        url = self.url_entry.get_text()
        if name and url:
            station_data = {
                "name": name,
                "url_resolved": url,
                "countrycode": "Custom",
                "url": url,
                "favicon": None
            }
            self.on_save(station_data)
            self.close()

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Cyber Radio")
        self.set_default_size(700, 500)
        self.set_size_request(650, 550)
        self.add_css_class("cyber-window")

        # State
        self.favorites = self.load_favorites()
        self.ensure_defaults()
        self.current_station_data = None
        self.is_azuracast = False
        self._discontinuity_timer = None
        self._loaded_textures = {}

        # --- ROOT BOX ---
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root_box)

        # --- HEADER BAR ---
        header_bar = Adw.HeaderBar()
        root_box.append(header_bar)

        toggle_btn = Gtk.Button(icon_name="sidebar-show-symbolic")
        toggle_btn.set_tooltip_text("Toggle Sidebar")
        toggle_btn.connect("clicked", self.on_toggle_sidebar)
        header_bar.pack_start(toggle_btn)

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.add_css_class("dim-label")
        header_bar.set_title_widget(self.status_label)

        # --- FLAP (SIDEBAR LAYOUT) ---
        self.flap = Adw.Flap()
        self.flap.set_property("reveal-flap", True)
        self.flap.set_property("fold-policy", Adw.FlapFoldPolicy.NEVER)
        root_box.append(self.flap)

        # ==========================
        # 1. SIDEBAR (The List)
        # ==========================
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar_box.add_css_class("sidebar-box")

        # Narrower Sidebar and Locked Width
        sidebar_box.set_size_request(220, -1)
        sidebar_box.set_hexpand(False)

        sidebar_box.set_margin_top(10)
        sidebar_box.set_margin_start(5)
        sidebar_box.set_margin_end(0)
        sidebar_box.set_margin_bottom(10)

        # Controls (Add)
        sidebar_ctrls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        sidebar_ctrls.set_margin_start(10)
        sidebar_ctrls.set_margin_end(10)

        lbl = Gtk.Label(label="LIBRARY")
        lbl.add_css_class("dim-label")
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)
        sidebar_ctrls.append(lbl)

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.set_tooltip_text("Add Custom Station")
        add_btn.connect("clicked", self.on_add_custom_clicked)
        add_btn.add_css_class("flat")
        sidebar_ctrls.append(add_btn)

        sidebar_box.append(sidebar_ctrls)

        # Search
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.set_margin_start(5)
        self.search_entry.set_margin_end(5)
        self.search_entry.connect("activate", self.on_search_activate)
        self.search_entry.connect("search-changed", self.on_search_changed)
        sidebar_box.append(self.search_entry)

        # List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(True)
        self.list_box.connect("row-activated", self.on_station_selected)

        scrolled.set_child(self.list_box)
        sidebar_box.append(scrolled)

        self.flap.set_flap(sidebar_box)

        # ==========================
        # 2. CONTENT (The Player)
        # ==========================
        main_scroll = Gtk.ScrolledWindow()
        main_scroll.set_vexpand(True)
        main_scroll.set_hexpand(True)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.add_css_class("player-container")
        content_box.set_valign(Gtk.Align.CENTER)
        content_box.set_halign(Gtk.Align.FILL)

        # --- Album Art Area ---
        art_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        art_box.set_halign(Gtk.Align.CENTER)
        art_box.set_size_request(250, 250)
        art_box.set_margin_bottom(20)

        self.art_picture = Gtk.Picture()
        self.art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self.art_picture.set_hexpand(True)
        self.art_picture.set_vexpand(True)
        self.art_picture.set_filename("invalid-path")

        art_frame = Gtk.Frame()
        art_frame.set_child(self.art_picture)
        art_frame.set_hexpand(True)
        art_frame.set_vexpand(True)

        art_box.append(art_frame)
        content_box.append(art_box)

        # --- Info Area ---
        self.track_label = Gtk.Label(label="Select Station")
        self.track_label.add_css_class("track-title")
        self.track_label.set_wrap(True)
        self.track_label.set_justify(Gtk.Justification.CENTER)
        self.track_label.set_max_width_chars(30)
        content_box.append(self.track_label)

        self.station_label = Gtk.Label(label="Ready")
        self.station_label.add_css_class("station-name")
        content_box.append(self.station_label)

        # --- THE VECTOR CAT (Replacing Visualizer) ---
        self.vector_cat = VectorCat()
        self.vector_cat.set_margin_top(10)
        self.vector_cat.set_margin_bottom(20)
        content_box.append(self.vector_cat)

        # --- Controls ---
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        btn_row.set_halign(Gtk.Align.CENTER)

        # Volume
        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vol_icon = Gtk.Image.new_from_icon_name("audio-volume-medium-symbolic")
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(50)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.set_size_request(100, -1)
        self.vol_scale.connect("value-changed", self.on_volume_changed)
        vol_box.append(vol_icon)
        vol_box.append(self.vol_scale)

        # Play
        self.play_btn = Gtk.Button(icon_name="media-playback-start-symbolic")
        self.play_btn.add_css_class("suggested-action")
        self.play_btn.add_css_class("circular")
        self.play_btn.set_size_request(64, 64)
        self.play_btn.set_action_name("app.toggle_play")

        # Fav
        self.fav_btn_player = Gtk.Button(icon_name="non-starred-symbolic")
        self.fav_btn_player.add_css_class("circular")
        self.fav_btn_player.set_size_request(40, 40)
        self.fav_btn_player.set_tooltip_text("Toggle Favorite")
        self.fav_btn_player.connect("clicked", self.on_favorite_clicked)

        btn_row.append(vol_box)
        btn_row.append(self.play_btn)
        btn_row.append(self.fav_btn_player)

        content_box.append(btn_row)

        main_scroll.set_child(content_box)
        self.flap.set_content(main_scroll)

        # --- INIT ---
        self._populate_list(self.favorites)
        self.player = AudioPlayer(self.on_mpv_metadata, self.on_mpv_discontinuity)
        self.player.set_volume(50)

        GLib.timeout_add_seconds(5, self._poll_tick)
        GLib.timeout_add(30, self._update_visualizer_loop)

    def ensure_defaults(self):
        if not self.favorites:
            self.favorites = DEFAULT_STATIONS.copy()
            self.save_favorites()
            return

        updated = False
        defaults_map = {s['url_resolved']: s for s in DEFAULT_STATIONS}

        for fav in self.favorites:
            url = fav.get('url_resolved')
            if url in defaults_map:
                default_data = defaults_map[url]
                if 'favicon' not in fav or fav['favicon'] != default_data.get('favicon'):
                    fav['favicon'] = default_data.get('favicon')
                    updated = True

        existing_urls = {f.get('url_resolved') for f in self.favorites}
        for s in DEFAULT_STATIONS:
            if s['url_resolved'] not in existing_urls:
                self.favorites.append(s)
                updated = True

        if updated:
            self.save_favorites()
            if hasattr(self, 'list_box'):
                self._populate_list(self.favorites)

    def on_toggle_sidebar(self, btn):
        current = self.flap.get_reveal_flap()
        self.flap.set_reveal_flap(not current)

    # --- UI UPDATERS ---
    def _update_visualizer_loop(self):
        # Determine cat state
        is_playing = self.player and not self.player.get_is_paused() and self.current_station_data
        is_paused = self.player and self.player.get_is_paused() and self.current_station_data

        if is_playing:
            state = "playing"
        elif is_paused:
            state = "paused"
        else:
            state = "idle"

        self.vector_cat.update(state)
        return True

    def load_image_into(self, url, widget, size=None):
        if not url:
            if isinstance(widget, Gtk.Picture):
                widget.set_paintable(None)
            return

        if url in self._loaded_textures:
             self._set_texture(widget, self._loaded_textures[url])
             return

        def worker():
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()

                loader = GdkPixbuf.PixbufLoader()
                loader.write(data)
                loader.close()
                pixbuf = loader.get_pixbuf()

                if size:
                    pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)

                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                GLib.idle_add(self._cache_and_set_generic, url, texture, widget)
            except Exception as e:
                # print(f"Failed to load image {url}: {e}")
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _cache_and_set_generic(self, url, texture, widget):
        self._loaded_textures[url] = texture
        try:
            self._set_texture(widget, texture)
        except:
            pass

    def _set_texture(self, widget, texture):
        if isinstance(widget, Gtk.Picture):
            widget.set_paintable(texture)
        elif isinstance(widget, Gtk.Image):
            widget.set_from_paintable(texture)

    # --- PLAYER LOGIC ---
    def _play_station(self, station_data):
        url = station_data.get('url_resolved') or station_data.get('url')
        name = station_data.get('name')
        favicon = station_data.get('favicon')

        if not url: return

        if self.current_station_data and self.current_station_data.get('url_resolved') == url:
             return

        self.current_station_data = station_data
        self.is_azuracast = "radio.zelixo.net" in url

        print(f"DEBUG: Tuning into: {url}")
        self.station_label.set_label(name)
        self.track_label.set_label("Connecting...")

        self.load_image_into(favicon, self.art_picture)

        self.player.play(url)
        self.play_btn.set_icon_name("media-playback-pause-symbolic")

        if self.is_azuracast:
             self.track_label.set_label("Loading metadata...")

        self.check_is_favorite(url)

    def apply_azuracast_update(self, song_text, art_url, stream_url):
        if song_text:
             self.track_label.set_label(song_text)
        if self.current_station_data and self.current_station_data.get('url_resolved') == stream_url:
            target_art = art_url
            if not target_art:
                target_art = self.current_station_data.get('favicon')
            self.load_image_into(target_art, self.art_picture)

    # --- LIST LOGIC ---
    def _populate_list(self, stations):
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None: break
            self.list_box.remove(row)

        for station in stations:
            row_content = Adw.ActionRow()
            name = station.get("name")
            country = station.get("countrycode") or "??"
            url = station.get("url_resolved") or station.get("url")
            favicon = station.get("favicon")

            if not url: continue

            row_content.set_title(name)
            if len(name) > 15:
                row_content.set_tooltip_text(name)

            icon = Gtk.Image()
            icon.set_pixel_size(24)
            icon.set_from_icon_name("audio-x-generic-symbolic")

            if favicon:
                self.load_image_into(favicon, icon, size=24)

            row_content.add_prefix(icon)
            row_content.station_data = station

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", lambda b, s=station: self.delete_favorite_direct(s))
            row_content.add_suffix(del_btn)

            list_row = Gtk.ListBoxRow()
            list_row.set_child(row_content)
            self.list_box.append(list_row)

    def on_mpv_metadata(self, track_name):
        if not self.is_azuracast:
            self.track_label.set_label(track_name)

    def on_station_selected(self, box, row):
        if row and row.get_child().station_data:
            self._play_station(row.get_child().station_data)

    def on_favorite_clicked(self, btn):
        if not self.current_station_data: return
        url = self.current_station_data.get('url_resolved')
        exists = any(f.get('url_resolved') == url for f in self.favorites)
        if exists:
            self.favorites = [f for f in self.favorites if f.get('url_resolved') != url]
            self.fav_btn_player.set_icon_name("non-starred-symbolic")
        else:
            self.favorites.append(self.current_station_data)
            self.fav_btn_player.set_icon_name("starred-symbolic")
        self.save_favorites()
        if not self.search_entry.get_text():
            self._populate_list(self.favorites)

    def check_is_favorite(self, url):
        exists = any(f.get('url_resolved') == url for f in self.favorites)
        icon = "starred-symbolic" if exists else "non-starred-symbolic"
        self.fav_btn_player.set_icon_name(icon)

    def on_search_activate(self, entry):
        query = entry.get_text()
        if query:
            threading.Thread(target=self._perform_search, args=(query,), daemon=True).start()

    def _perform_search(self, query):
        try:
            params = urllib.parse.urlencode({'name': query, 'limit': 20})
            with urllib.request.urlopen(f"{SEARCH_API_URL}?{params}") as r:
                data = json.loads(r.read().decode())
                GLib.idle_add(self._populate_list, data)
        except: pass

    def on_search_changed(self, entry):
        if not entry.get_text():
            self._populate_list(self.favorites)

    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
             try: return json.load(open(FAVORITES_FILE))
             except: pass
        return []

    def save_favorites(self):
        json.dump(self.favorites, open(FAVORITES_FILE, "w"), indent=2)

    def delete_favorite_direct(self, s):
        self.favorites = [f for f in self.favorites if f['url_resolved'] != s['url_resolved']]
        self.save_favorites()

        if not self.search_entry.get_text():
            self._populate_list(self.favorites)

        if self.current_station_data and self.current_station_data['url_resolved'] == s['url_resolved']:
             self.check_is_favorite(s['url_resolved'])

    def on_volume_changed(self, scale):
        self.player.set_volume(scale.get_value())

    def on_add_custom_clicked(self, btn):
        AddStationDialog(self, self.add_custom_station).present()

    def add_custom_station(self, data):
        self.favorites.append(data)
        self.save_favorites()
        if not self.search_entry.get_text():
            self._populate_list(self.favorites)

    def toggle_play(self):
        if self.current_station_data:
            paused = self.player.get_is_paused()
            if paused: self.player.pause()
            else: self.player.pause()
            self.play_btn.set_icon_name("media-playback-pause-symbolic" if paused else "media-playback-start-symbolic")

    # Polling logic
    def _poll_tick(self):
        if self.current_station_data and self.is_azuracast:
            threading.Thread(target=self._fetch_azuracast, args=(self.current_station_data['url_resolved'],), daemon=True).start()
        return True

    def on_mpv_discontinuity(self):
        if self.is_azuracast and self.current_station_data:
             if self._discontinuity_timer: GLib.source_remove(self._discontinuity_timer)
             self._discontinuity_timer = GLib.timeout_add_seconds(2, self._force_api_update)

    def _force_api_update(self):
        self._discontinuity_timer = None
        if self.current_station_data:
             threading.Thread(target=self._fetch_azuracast, args=(self.current_station_data['url_resolved'],), daemon=True).start()
        return False

    def _fetch_azuracast(self, url):
        try:
            with urllib.request.urlopen(AZURACAST_API_URL) as r:
                data = json.loads(r.read().decode())
                for s in data:
                    if s.get('station', {}).get('shortcode') in url:
                        np = s.get('now_playing', {}).get('song', {})
                        GLib.idle_add(self.apply_azuracast_update, np.get('text'), np.get('art'), url)
        except: pass

class CyberRadioApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_application_id("com.example.CyberRadio")
        action = Gio.SimpleAction.new("toggle_play", None)
        action.connect("activate", self.on_toggle_play_action)
        self.add_action(action)

    def on_toggle_play_action(self, action, param):
        win = self.props.active_window
        if win: win.toggle_play()

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        provider = Gtk.CssProvider()
        provider.load_from_data(CYBER_CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = self.props.active_window
        if not win: win = MainWindow(application=self)
        win.present()

if __name__ == "__main__":
    app = CyberRadioApp()
    app.run(sys.argv)
