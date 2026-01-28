import logging
import threading
import json
import os
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from src.config import FAVORITES_FILE, DEFAULT_STATIONS
from src.core.player import AudioPlayer
from src.core.api import search_stations, fetch_azuracast_nowplaying
from src.core.metadata import fetch_album_art
from src.core.recognition import SongRecognizer
from src.ui.visuals import VectorCat
from src.ui.dialogs import AddStationDialog
from src.ui.utils import load_image_into, clean_metadata_title

logger = logging.getLogger(__name__)

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
        self.recognizer = SongRecognizer()

        # --- TOAST OVERLAY & ROOT BOX ---
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(root_box)

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

        recognize_btn = Gtk.Button(icon_name="audio-input-microphone-symbolic")
        recognize_btn.set_tooltip_text("Identify Song (Shazam)")
        recognize_btn.connect("clicked", self.on_recognize_clicked)
        header_bar.pack_end(recognize_btn)

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

        logger.info(f"Tuning into: {url}")
        self.station_label.set_label(name)
        self.track_label.set_label("Connecting...")

        load_image_into(favicon, self.art_picture, self._loaded_textures)

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
            load_image_into(target_art, self.art_picture, self._loaded_textures)

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
                load_image_into(favicon, icon, self._loaded_textures, size=24)

            row_content.add_prefix(icon)
            row_content.station_data = station

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", lambda b, s=station: self.delete_favorite_direct(s))
            
            edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
            edit_btn.add_css_class("flat")
            edit_btn.connect("clicked", lambda b, s=station: self.on_edit_clicked(s))

            row_content.add_suffix(edit_btn)
            row_content.add_suffix(del_btn)

            list_row = Gtk.ListBoxRow()
            list_row.set_child(row_content)
            self.list_box.append(list_row)

    # --- RECOGNITION LOGIC ---
    def on_recognize_clicked(self, btn):
        if not self.current_station_data:
            self._show_toast("Play a station first!")
            return

        self._show_toast("Listening (approx. 10s)...")
        url = self.current_station_data.get('url_resolved') or self.current_station_data.get('url')
        threading.Thread(target=self._perform_recognition, args=(url,), daemon=True).start()

    def _perform_recognition(self, stream_url):
        result = self.recognizer.identify(stream_url)
        GLib.idle_add(self._on_recognition_complete, result)

    def _on_recognition_complete(self, result):
        if not result:
            self._show_toast("Could not identify song.")
            return

        if "error" in result:
             self._show_toast(result["error"])
             return

        title = result.get('title', 'Unknown')
        artist = result.get('artist', 'Unknown')
        self._show_toast(f"Found: {artist} - {title}")
        
        # Optional: Update UI immediately if user wants, but Toast is safer for now.
        # We could also copy to clipboard here.

    def _show_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(4)
        self.toast_overlay.add_toast(toast)

    def on_mpv_metadata(self, track_name):
        if not self.is_azuracast:
            cleaned_name = clean_metadata_title(track_name)
            self.track_label.set_label(cleaned_name)
            # Trigger dynamic art lookup
            threading.Thread(target=self._update_dynamic_art, args=(cleaned_name,), daemon=True).start()

    def _update_dynamic_art(self, track_name):
        art_url = fetch_album_art(track_name)
        if art_url:
             GLib.idle_add(load_image_into, art_url, self.art_picture, self._loaded_textures)
        else:
             # Fallback to station logo if no art found for this track
             if self.current_station_data:
                 logo = self.current_station_data.get('favicon')
                 GLib.idle_add(load_image_into, logo, self.art_picture, self._loaded_textures)

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
        data = search_stations(query)
        GLib.idle_add(self._populate_list, data)

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

    def on_edit_clicked(self, station_data):
        AddStationDialog(self, self.add_custom_station, station_data=station_data).present()

    def add_custom_station(self, data, old_data=None):
        if old_data:
            # Update existing
            for i, fav in enumerate(self.favorites):
                if fav.get('url_resolved') == old_data.get('url_resolved'):
                    self.favorites[i] = data
                    break
        else:
            self.favorites.append(data)
            
        self.save_favorites()
        if not self.search_entry.get_text():
            self._populate_list(self.favorites)
        
        # If we updated the currently playing station, update the UI
        if self.current_station_data and old_data and self.current_station_data.get('url_resolved') == old_data.get('url_resolved'):
            self.current_station_data = data
            self.station_label.set_label(data.get('name'))
            load_image_into(data.get('favicon'), self.art_picture, self._loaded_textures)

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
        data = fetch_azuracast_nowplaying()
        for s in data:
            if s.get('station', {}).get('shortcode') in url:
                np = s.get('now_playing', {}).get('song', {})
                GLib.idle_add(self.apply_azuracast_update, np.get('text'), np.get('art'), url)
