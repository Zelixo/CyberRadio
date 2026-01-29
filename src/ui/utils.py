import urllib.request
import threading
import re
import os
from gi.repository import GdkPixbuf, Gdk, GLib, Gtk
import logging

logger = logging.getLogger(__name__)

def clean_metadata_title(title_str):
    """
    Cleans up metadata strings that contain structured key-value pairs.
    Example Input: 'Eagle-Eye Cherry - text="Save Tonight" song_spot="M" ...'
    Example Output: 'Eagle-Eye Cherry - Save Tonight'
    """
    if not title_str:
        return ""

    # Check for 'text="Title"' pattern
    match = re.search(r'text="([^"]+)"', title_str)
    if match:
        extracted_title = match.group(1)
        
        # Check if there is an artist prefix before ' - text='
        # We assume the separator is " - " before the structured part
        parts = title_str.split(' - text=')
        if len(parts) > 1:
            artist = parts[0].strip()
            return f"{artist} - {extracted_title}"
        
        # If no artist prefix, just return the title
        return extracted_title
        
    return title_str
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
            # Handle local files
            if os.path.exists(url):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(url)
                if size:
                    pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                GLib.idle_add(_cache_and_set_generic, url, texture, widget, loaded_textures_cache)
                return

            # Handle remote URLs
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CyberRadio/1.0)'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                # Get the final URL after all redirects
                final_url = resp.geturl()
                # Make a new request to the final URL to get the actual image data
                # This is necessary because GdkPixbuf.PixbufLoader might not handle redirects transparently
                if final_url != url:
                    req = urllib.request.Request(final_url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CyberRadio/1.0)'})
                    with urllib.request.urlopen(req, timeout=5) as final_resp:
                        data = final_resp.read()
                else:
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
