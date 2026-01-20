import sys
import os
import logging
from gi.repository import Adw, Gio, Gtk, Gdk

from src.ui.main_window import MainWindow

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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = CyberRadioApp()
    app.run(sys.argv)
