import logging
import threading
import json
import os
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from src.config import FAVORITES_FILE, DEFAULT_STATIONS
from src.core.player import AudioPlayer
from src.core.api import search_stations, fetch_azuracast_nowplaying
from src.core.metadata import fetch_album_art
from src.core.musicbrainz import get_musicbrainz_url
from src.core.recognition import SongRecognizer
from src.ui.visuals import VectorCat
from src.core.ipc import IPCHandler
from src.ui.dialogs import AddStationDialog, IdentifiedSongsDialog
from src.ui.utils import load_image_into, clean_metadata_title, update_now_playing_file

logger = logging.getLogger(__name__)

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Cyber Radio")
        self.set_default_size(750, 450) # Wider, shorter
        self.set_size_request(700, 400)
        self.add_css_class("cyber-window")

        # State
        self.favorites = self.load_favorites()
        self.ensure_defaults()
        self.current_station_data = None
        self.is_azuracast = False
        self._discontinuity_timer = None
        self._loaded_textures = {}
        self.recognizer = SongRecognizer()
        self.identified_songs = []

        # --- TOAST OVERLAY ---
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # --- MAIN SPLIT LAYOUT ---
        # A single horizontal box split into Sidebar (Left) and Player (Right)
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.toast_overlay.set_child(main_box)

        # ==========================
        # 1. SIDEBAR (Left Panel)
        # ==========================
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.sidebar.add_css_class("sidebar-box")
        self.sidebar.set_size_request(320, -1) # Wider sidebar for bigger cards
        self.sidebar.set_hexpand(False)
        self.sidebar.set_vexpand(True) # Maximize height
        main_box.append(self.sidebar)

        # Sidebar Header: Search + Add
        sb_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", self.on_search_activate)
        self.search_entry.connect("search-changed", self.on_search_changed)
        sb_header.append(self.search_entry)

        add_btn = Gtk.Button(label="") # F067
        add_btn.add_css_class("flat")
        add_btn.set_tooltip_text("Add Custom Station")
        add_btn.connect("clicked", self.on_add_custom_clicked)
        sb_header.append(add_btn)

        self.sidebar.append(sb_header)

        # Station Grid (FlowBox)
        # Replaces ScrolledWindow/ListBox for a fixed page grid
        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.FILL) # Fill vertical space
        self.flow_box.set_vexpand(True) # Push Nav Box down
        self.flow_box.set_min_children_per_line(2)
        self.flow_box.set_max_children_per_line(2)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_row_spacing(10)
        self.flow_box.set_column_spacing(10)
        self.flow_box.set_homogeneous(True)
        
        # Container to hold flowbox (expandable)
        grid_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        grid_container.set_vexpand(True)
        grid_container.set_hexpand(True)
        grid_container.append(self.flow_box)

        # Navigation Footer (External to FlowBox)
        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.nav_box.set_halign(Gtk.Align.FILL)
        self.nav_box.set_valign(Gtk.Align.END)
        self.nav_box.set_margin_bottom(5)
        self.nav_box.set_margin_start(5)
        self.nav_box.set_margin_end(5)

        self.prev_btn = Gtk.Button(label="") # F053
        self.prev_btn.add_css_class("nav-btn-compact")
        self.prev_btn.set_hexpand(True)
        self.prev_btn.connect("clicked", self.on_page_prev)
        self.nav_box.append(self.prev_btn)

        self.next_btn = Gtk.Button(label="") # F054
        self.next_btn.add_css_class("nav-btn-compact")
        self.next_btn.set_hexpand(True)
        self.next_btn.connect("clicked", self.on_page_next)
        self.nav_box.append(self.next_btn)

        grid_container.append(self.nav_box)
        
        self.sidebar.append(grid_container)

        # ==========================
        # 2. PLAYER (Right Panel)
        # ==========================
        self.player_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.player_box.add_css_class("player-container")
        self.player_box.set_hexpand(True)
        main_box.append(self.player_box)

        # --- Top Bar (Status) ---
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_bar.set_margin_bottom(10)
        
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_hexpand(True)
        self.status_label.set_halign(Gtk.Align.START)
        top_bar.append(self.status_label)

        rec_btn = Gtk.Button(label="") # F0C2 (Cloud/Identified)
        rec_btn.add_css_class("flat")
        rec_btn.set_tooltip_text("Show Identified Songs")
        rec_btn.connect("clicked", self.on_show_identified_songs)
        top_bar.append(rec_btn)

        self.player_box.append(top_bar)

        # --- Visuals (Vector Cat) ---
        self.vector_cat = VectorCat()
        self.vector_cat.set_content_height(120) # Compact height
        self.vector_cat.set_vexpand(True) # Take available space but don't force scroll
        self.player_box.append(self.vector_cat)

        # --- Track Info & Art (Horizontal Layout) ---
        info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        info_row.set_margin_top(10)
        info_row.set_margin_bottom(15)
        info_row.set_halign(Gtk.Align.FILL)

        # Art (Thumbnail)
        self.art_picture = Gtk.Picture()
        self.art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self.art_picture.set_size_request(64, 64)
        
        # Art Button wrapper
        self.art_btn = Gtk.Button()
        self.art_btn.add_css_class("flat")
        self.art_btn.set_child(self.art_picture)
        self.art_btn.set_tooltip_text("Click to Identify Song")
        self.art_btn.connect("clicked", self.on_recognize_clicked)
        
        art_frame = Gtk.Frame()
        art_frame.add_css_class("art-frame") # We'll style this to be round/pill
        art_frame.set_child(self.art_btn)
        info_row.append(art_frame)

        # Text Info
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_valign(Gtk.Align.CENTER)
        
        self.track_label = Gtk.Label(label="Select Station")
        self.track_label.add_css_class("track-title")
        self.track_label.set_halign(Gtk.Align.START)
        self.track_label.set_ellipsize(3) # Ellipsize at end
        self.track_label.set_max_width_chars(25)
        text_box.append(self.track_label)

        self.station_label = Gtk.Label(label="Ready")
        self.station_label.add_css_class("station-name")
        self.station_label.set_halign(Gtk.Align.START)
        text_box.append(self.station_label)

        info_row.append(text_box)
        self.player_box.append(info_row)

        # --- Controls (Bottom Row) ---
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        controls_row.set_halign(Gtk.Align.FILL)
        controls_row.set_valign(Gtk.Align.END)

        # Volume
        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vol_label = Gtk.Label(label="") # F028
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(50)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.connect("value-changed", self.on_volume_changed)
        vol_box.append(vol_label)
        vol_box.append(self.vol_scale)
        vol_box.set_hexpand(True) # Fill left space
        controls_row.append(vol_box)

        # Play/Pause (Center-ish)
        self.play_btn = Gtk.Button(label="") # F04B
        self.play_btn.add_css_class("suggested-action")
        self.play_btn.set_size_request(50, 50)
        self.play_btn.set_action_name("app.toggle_play")
        controls_row.append(self.play_btn)

        # Favorite (Right)
        self.fav_btn_player = Gtk.Button(label="") # F006 (Non-star)
        self.fav_btn_player.add_css_class("flat") # Make it subtle
        self.fav_btn_player.set_tooltip_text("Toggle Favorite")
        self.fav_btn_player.connect("clicked", self.on_favorite_clicked)
        controls_row.append(self.fav_btn_player)

        self.player_box.append(controls_row)

        # --- INIT ---
        self.current_page = 0
        self.ITEMS_PER_PAGE = 4 # 4 Big Stations
        
        self._populate_grid(self.favorites)
        self.player = AudioPlayer(self.on_mpv_metadata, self.on_mpv_discontinuity)
        self.player.set_volume(50)

        self.ipc_handler = IPCHandler(self)
        self.ipc_handler.create_socket()

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
                # Update existing fields from default data
                if 'favicon' not in fav or fav['favicon'] != default_data.get('favicon'):
                    fav['favicon'] = default_data.get('favicon')
                    updated = True
                if 'id' not in fav and 'id' in default_data:
                    fav['id'] = default_data['id']
                    updated = True
                if 'shortcode' not in fav and 'shortcode' in default_data:
                    fav['shortcode'] = default_data['shortcode']
                    updated = True

        existing_urls = {f.get('url_resolved') for f in self.favorites}
        for s in DEFAULT_STATIONS:
            if s['url_resolved'] not in existing_urls:
                self.favorites.append(s)
                updated = True

        if updated:
            self.save_favorites()
            if hasattr(self, 'flow_box'):
                self._populate_grid(self.favorites)

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
        self.play_btn.set_label("") # Pause F04C

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

    # --- LIST/GRID LOGIC ---
    def _populate_grid(self, stations):
        # Clear existing
        self.flow_box.remove_all()

        total_items = len(stations)
        start_idx = self.current_page * self.ITEMS_PER_PAGE
        end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_items)
        
        page_items = stations[start_idx:end_idx]

        for station in page_items:
            # Card Container
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2) # Tighter spacing
            card.add_css_class("station-card")
            card.set_size_request(-1, 190) # Taller to fit vertical text
            
            # Icon
            icon = Gtk.Image()
            icon.add_css_class("station-icon")
            icon.set_pixel_size(100) # Slightly smaller to give room for big text
            favicon = station.get("favicon")
            if favicon:
                load_image_into(favicon, icon, self._loaded_textures, size=100)
            else:
                icon.set_from_icon_name("audio-x-generic-symbolic")
            card.append(icon)

            # Label (Vertical Stack)
            raw_name = station.get("name", "Unknown")
            stacked_name = raw_name.replace(" ", "\n")
            
            lbl = Gtk.Label(label=stacked_name)
            lbl.add_css_class("station-label")
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_wrap(True)
            card.append(lbl)

            # Click Controller
            gesture = Gtk.GestureClick()
            gesture.set_button(0) # All buttons
            gesture.connect("pressed", lambda g, n, x, y, s=station: self._on_grid_item_clicked(g, n, x, y, s))
            card.add_controller(gesture)
            
            self.flow_box.append(card)

        # Update external Nav Buttons
        self._update_nav_buttons(total_items)

    def _update_nav_buttons(self, total_items):
        start_idx = self.current_page * self.ITEMS_PER_PAGE
        end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_items)
        
        # Prev: Enabled if not on first page
        self.prev_btn.set_sensitive(self.current_page > 0)
        
        # Next: Enabled if there are more items after this page
        self.next_btn.set_sensitive(end_idx < total_items)

    def _on_grid_item_clicked(self, gesture, n_press, x, y, station):
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_PRIMARY: # Left Click
            self._play_station(station)
        elif button == Gdk.BUTTON_SECONDARY: # Right Click
            self._show_context_menu(station, gesture)

    def _show_context_menu(self, station, gesture):
        popover = Gtk.Popover()
        popover.set_parent(gesture.get_widget())
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(5)
        box.set_margin_end(5)
        
        edit_btn = Gtk.Button(label="Edit Station")
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", lambda b: (self.on_edit_clicked(station), popover.popdown()))
        box.append(edit_btn)
        
        del_btn = Gtk.Button(label="Delete Station")
        del_btn.add_css_class("destructive-action") # Red
        del_btn.connect("clicked", lambda b: (self.delete_favorite_direct(station), popover.popdown()))
        box.append(del_btn)
        
        popover.set_child(box)
        popover.popup()

    def on_page_prev(self, btn):
        if self.current_page > 0:
            self.current_page -= 1
            if self.search_entry.get_text():
                 # Re-search to get filtered list
                 self._perform_search(self.search_entry.get_text())
            else:
                 self._populate_grid(self.favorites)

    def on_page_next(self, btn):
        # Check boundary? We do it lazily by re-populating
        self.current_page += 1
        if self.search_entry.get_text():
             self._perform_search(self.search_entry.get_text())
        else:
             self._populate_grid(self.favorites)

    # --- RECOGNITION LOGIC ---
    def on_recognize_clicked(self, btn):
        if not self.current_station_data:
            self._show_toast("Play a station first!")
            return

        self._show_toast("Listening (approx. 10s)...")
        # Visual feedback
        self.track_label.set_label("Scanning...")
        
        url = self.current_station_data.get('url_resolved') or self.current_station_data.get('url')
        threading.Thread(target=self._perform_recognition, args=(url,), daemon=True).start()

    def _perform_recognition(self, stream_url):
        result = self.recognizer.identify(stream_url)
        GLib.idle_add(self._on_recognition_complete, result)

    def _on_recognition_complete(self, result):
        if not result:
            self._show_toast("Could not identify song.")
            # Restore unknown state or previous
            if self.current_station_data:
                 self.track_label.set_text(self.current_station_data.get('name', 'Unknown'))
            return

        if "error" in result:
             self._show_toast(result["error"])
             if self.current_station_data:
                 self.track_label.set_text(self.current_station_data.get('name', 'Unknown'))
             return

        title = result.get('title', 'Unknown')
        artist = result.get('artist', 'Unknown')
        art_url = result.get('art_url')

        self._show_toast(f"Found: {artist} - {title}")

        # Get MusicBrainz URL in a separate thread to not block the UI
        threading.Thread(target=self._add_identified_song, args=(title, artist, art_url), daemon=True).start()

        # --- Temporary UI Update ---
        # Store original state
        self.original_track_label = self.track_label.get_text()
        self.original_art_paintable = self.art_picture.get_paintable()
        self.original_station_label = self.station_label.get_text()

        # Update Player UI
        self.track_label.set_text(title) 
        self.station_label.set_text(artist)
        if art_url:
            load_image_into(art_url, self.art_picture, self._loaded_textures)


        # Schedule the UI to revert back after 10 seconds
        GLib.timeout_add_seconds(10, self._revert_recognition_display)

    def _revert_recognition_display(self):
        """Restores the UI to its state before the song recognition."""
        if hasattr(self, 'original_track_label'):
            self.track_label.set_text(self.original_track_label)
        if hasattr(self, 'original_station_label'):
            self.station_label.set_text(self.original_station_label)
        if hasattr(self, 'original_art_paintable'):
            self.art_picture.set_paintable(self.original_art_paintable)
        return False # Important: return False to stop the timer from repeating



    def _add_identified_song(self, title, artist, art_url):
        musicbrainz_url = get_musicbrainz_url(artist, title)
        
        song_data = {
            "title": title,
            "artist": artist,
            "art_url": art_url,
            "musicbrainz_url": musicbrainz_url
        }
        
        self.identified_songs.append(song_data)
        
        # Also show a toast that the song has been identified and added
        GLib.idle_add(self._show_toast, f"Identified & Added: {artist} - {title}")



    def on_show_identified_songs(self, btn):
        dialog = IdentifiedSongsDialog(self, self.identified_songs)
        dialog.present()

    def _show_toast(self, message):
        safe_message = GLib.markup_escape_text(message)
        toast = Adw.Toast.new(safe_message)
        toast.set_timeout(4)
        self.toast_overlay.add_toast(toast)

    def on_mpv_metadata(self, track_name):
        if not self.is_azuracast:
            cleaned_name = clean_metadata_title(track_name)
            self.track_label.set_label(cleaned_name)
            update_now_playing_file(cleaned_name)
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
            self.fav_btn_player.set_label("") # Non-star F006
        else:
            self.favorites.append(self.current_station_data)
            self.fav_btn_player.set_label("") # Star F005
        self.save_favorites()
        if not self.search_entry.get_text():
            self._populate_grid(self.favorites)

    def check_is_favorite(self, url):
        exists = any(f.get('url_resolved') == url for f in self.favorites)
        icon = "" if exists else "" # F005 vs F006
        self.fav_btn_player.set_label(icon)

    def on_search_activate(self, entry):
        self.current_page = 0 # Reset page on new search
        query = entry.get_text()
        if query:
            threading.Thread(target=self._perform_search, args=(query,), daemon=True).start()

    def _perform_search(self, query):
        data = search_stations(query)
        GLib.idle_add(self._populate_grid, data)

    def on_search_changed(self, entry):
        if not entry.get_text():
            self.current_page = 0
            self._populate_grid(self.favorites)

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
            self._populate_grid(self.favorites)

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
            self._populate_grid(self.favorites)
        
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
            self.play_btn.set_label("" if paused else "") # F04C (Pause) if playing, F04B (Play) if paused

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
        station_id = self.current_station_data.get('id')
        if not station_id:
            logger.warning(f"No Azuracast ID found for current station: {self.current_station_data.get('name')}")
            return

        for s in data:
            if s.get('station', {}).get('id') == station_id:
                np_song = s.get('now_playing', {}).get('song', {})
                song_text = np_song.get('text')
                art_url = np_song.get('art')
                logger.debug(f"[_fetch_azuracast] Calling apply_azuracast_update with text='{song_text}', art='{art_url}'")
                GLib.idle_add(self.apply_azuracast_update, song_text, art_url, url)
                return

    def handle_ipc_command(self, command):
        if command == "play-pause":
            self.toggle_play()
        elif command == "next-station":
            self._play_next_station()
        elif command == "prev-station":
            self._play_prev_station()

    def _play_next_station(self):
        if not self.current_station_data:
            return
        
        current_url = self.current_station_data.get('url_resolved')
        try:
            current_index = [s.get('url_resolved') for s in self.favorites].index(current_url)
            next_index = (current_index + 1) % len(self.favorites)
            self._play_station(self.favorites[next_index])
        except ValueError:
            # Current station not in favorites, play the first one
            if self.favorites:
                self._play_station(self.favorites[0])

    def _play_prev_station(self):
        if not self.current_station_data:
            return

        current_url = self.current_station_data.get('url_resolved')
        try:
            current_index = [s.get('url_resolved') for s in self.favorites].index(current_url)
            prev_index = (current_index - 1 + len(self.favorites)) % len(self.favorites)
            self._play_station(self.favorites[prev_index])
        except ValueError:
            # Current station not in favorites, play the first one
            if self.favorites:
                self._play_station(self.favorites[0])

    def apply_azuracast_update(self, song_text, art_url, stream_url):
        logger.debug(f"[apply_azuracast_update] Received text='{song_text}', art='{art_url}' for stream='{stream_url}'")
        if song_text:
             self.track_label.set_label(song_text)
             update_now_playing_file(song_text)
        if self.current_station_data and self.current_station_data.get('url_resolved') == stream_url:
            target_art = art_url
            if not target_art:
                target_art = self.current_station_data.get('favicon')
            logger.debug(f"[apply_azuracast_update] Loading album art from '{target_art}'")
            load_image_into(target_art, self.art_picture, self._loaded_textures)
