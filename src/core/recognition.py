import os
import tempfile
import logging
import subprocess
import json
import shutil

logger = logging.getLogger(__name__)

class SongRecognizer:
    def __init__(self):
        self.has_songrec = shutil.which("songrec") is not None
        if not self.has_songrec:
            logger.warning("'songrec' not found. Identification will be disabled.")

    def identify(self, stream_url, duration=10):
        """
        Captures a snippet and identifies it using 'songrec'.
        """
        if not self.has_songrec:
            logger.error("Cannot identify: 'songrec' is not installed.")
            return {"error": "Install 'songrec' package"}

        temp_file = None
        try:
            # 1. Create a temporary file (songrec handles most formats, but mp3 is safe)
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            temp_file = temp_path

            logger.info(f"Capturing {duration}s of audio from {stream_url} to {temp_file}...")

            # 2. Capture audio using ffmpeg
            # songrec is robust, so we can just grab standard audio
            cmd = [
                "ffmpeg",
                "-y",
                "-t", str(duration),
                "-i", stream_url,
                "-vn",
                "-f", "mp3",
                temp_file
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.info("FFmpeg capture complete. Running songrec...")

            # 3. Call songrec
            # Command: songrec audio-file-to-recognized-song <file>
            res = subprocess.run(
                ["songrec", "audio-file-to-recognized-song", temp_file],
                capture_output=True,
                text=True
            )

            if res.returncode != 0:
                logger.error(f"songrec failed: {res.stderr}")
                return None

            # Output is JSON
            try:
                result = json.loads(res.stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse songrec output: {res.stdout}")
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
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    pass