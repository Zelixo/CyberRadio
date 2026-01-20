import sys
import logging
import mpv
from gi.repository import GLib

logger = logging.getLogger(__name__)

class AudioPlayer:
    """Handles MPV logic independently."""
    def __init__(self, on_metadata_change, on_discontinuity=None):
        try:
            self.mpv = mpv.MPV(
                video=False,
                ytdl=True,
                log_handler=self._mpv_log,
                cache='yes'
            )
        except Exception as e:
            logger.critical(f"Failed to initialize MPV: {e}")
            raise e

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
        
        # Map MPV levels to Python logging levels
        if level == 'fatal':
            logger.critical(f"[MPV] {prefix}: {text}")
        elif level == 'error':
            logger.error(f"[MPV] {prefix}: {text}")
        elif level == 'warn':
            logger.warning(f"[MPV] {prefix}: {text}")
        elif level == 'info':
            logger.info(f"[MPV] {prefix}: {text}")
        else:
            logger.debug(f"[MPV] {prefix}: {text}")

    def play(self, url):
        try:
            logger.info(f"Playing URL: {url}")
            self.mpv.play(url)
            self.mpv.pause = False
        except Exception as e:
            logger.error(f"MPV Play failed: {e}")

    def pause(self):
        logger.debug("Toggling pause")
        self.mpv.cycle('pause')

    def stop(self):
        logger.info("Stopping playback")
        self.mpv.stop()

    def set_volume(self, volume):
        self.mpv.volume = volume

    def get_is_paused(self):
        return self.mpv.pause if hasattr(self.mpv, 'pause') else False

    def _handle_metadata(self, _name, value):
        if value:
            GLib.idle_add(self.on_metadata_change, value)
