import gi

# Ensure versions are set before any other sub-module imports Gtk/Adw
try:
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('GdkPixbuf', '2.0')
except ValueError as e:
    print(f"Critical Error: Missing dependencies. {e}")
    raise e
