import urllib.request
import threading
from gi.repository import GdkPixbuf, Gdk, GLib, Gtk
import logging

logger = logging.getLogger(__name__)

def load_image_into(url, widget, loaded_textures_cache, size=None):
    if not url:
        if isinstance(widget, Gtk.Picture):
            widget.set_paintable(None)
        return

    if url in loaded_textures_cache:
         _set_texture(widget, loaded_textures_cache[url])
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
            GLib.idle_add(_cache_and_set_generic, url, texture, widget, loaded_textures_cache)
        except Exception as e:
            logger.warning(f"Failed to load image {url}: {e}")
            pass

    threading.Thread(target=worker, daemon=True).start()

def _cache_and_set_generic(url, texture, widget, cache):
    cache[url] = texture
    try:
        _set_texture(widget, texture)
    except:
        pass

def _set_texture(widget, texture):
    if isinstance(widget, Gtk.Picture):
        widget.set_paintable(texture)
    elif isinstance(widget, Gtk.Image):
        widget.set_from_paintable(texture)
