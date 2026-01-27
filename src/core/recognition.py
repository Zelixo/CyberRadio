import asyncio
import os
import tempfile
import logging
import subprocess
from shazamio import Shazam

logger = logging.getLogger(__name__)

class SongRecognizer:
    def __init__(self):
        pass

    async def _recognize_async(self, file_path):
        try:
            # Instantiate here to ensure it uses the current thread's event loop
            shazam = Shazam()
            out = await shazam.recognize(file_path)
            return out
        except Exception as e:
            logger.error(f"Shazam recognition failed: {e}")
            return None

    def identify(self, stream_url, duration=10):
        """
        Captures a snippet of the stream and attempts to identify it.
        Returns a dictionary with 'title', 'artist', 'art_url' or None.
        """
        temp_file = None
        try:
            # 1. Create a temporary file for the audio snippet
            # We use .mp3 suffix to help ffmpeg/shazam guess format if needed, though ffmpeg handles it.
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            temp_file = temp_path

            logger.info(f"Capturing {duration}s of audio from {stream_url} to {temp_file}...")

            # 2. Capture audio using ffmpeg
            # -y: overwrite output
            # -t: duration
            # -i: input url
            # -vn: no video
            # -acodec: copy (copy stream directly if possible) or libmp3lame
            # We'll re-encode to ensure a clean chunk for shazam
            cmd = [
                "ffmpeg",
                "-y",
                "-t", str(duration),
                "-i", stream_url,
                "-vn",
                "-f", "mp3",
                temp_file
            ]

            # Run ffmpeg (blocking, but this entire identify method will run in a thread)
            # Suppress output unless error
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

            # 3. Recognize using ShazamIO
            # specific loop handling for running async code from sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self._recognize_async(temp_file))

            if not result:
                return None

            # 4. Parse Result
            track = result.get('track', {})
            if not track:
                return None

            return {
                'title': track.get('title'),
                'artist': track.get('subtitle'),
                'art_url': track.get('images', {}).get('coverart'),
                'shazam_url': track.get('url')
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg capture failed: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"Identification error: {e}")
            return None
        finally:
            # Cleanup
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
