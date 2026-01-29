import sys
import os
import logging
import argparse
from gi.repository import Adw, Gio, Gtk, Gdk

from src.ui.main_window import MainWindow
from src.core.ipc import IPCHandler

logger = logging.getLogger(__name__)

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
        
        # Calculate CSS path relative to this file
        # __file__ = src/app.py
        # dirname = src
        # dirname = project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        css_path = os.path.join(project_root, "assets", "style.css")
        
        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            logger.error(f"Failed to load CSS from {css_path}: {e}")

        win = self.props.active_window
        if not win: win = MainWindow(application=self)
        win.present()

def main():
    parser = argparse.ArgumentParser(description="Cyber Radio")
    parser.add_argument("--play-pause", action="store_true", help="Toggle play/pause")
    parser.add_argument("--next-station", action="store_true", help="Play the next station in the list")
    parser.add_argument("--prev-station", action="store_true", help="Play the previous station in the list")
    args = parser.parse_args()

    command = None
    if args.play_pause:
        command = "play-pause"
    elif args.next_station:
        command = "next-station"
    elif args.prev_station:
        command = "prev-station"

    if command:
        if IPCHandler.send_command(command):
            print(f"Sent command: {command}")
            sys.exit(0)
        else:
            print("Failed to send command. Is Cyber Radio running?")
            sys.exit(1)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = CyberRadioApp()
    app.run(sys.argv)
