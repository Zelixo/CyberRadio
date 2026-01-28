import os
import tempfile
import logging
import subprocess
import json
import sys

logger = logging.getLogger(__name__)

class SongRecognizer:
    def __init__(self):
        pass

    def identify(self, stream_url, duration=10):
        """
        Captures a snippet of the stream and attempts to identify it.
        Returns a dictionary with 'title', 'artist', 'art_url' or None.
        """
        temp_file = None
        try:
            # 1. Create a temporary file
            # We use .wav with specific format to minimize processing in the wrapper
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            temp_file = temp_path

            logger.info(f"Capturing {duration}s of audio from {stream_url} to {temp_file}...")

            # 2. Capture audio using ffmpeg
            # Convert directly to Shazam-friendly format: 16kHz, Mono, PCM s16le
            cmd = [
                "ffmpeg",
                "-y",
                "-t", str(duration),
                "-i", stream_url,
                "-vn",
                "-ac", "1",        # Mono
                "-ar", "16000",    # 16kHz
                "-f", "wav",
                temp_file
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.info("FFmpeg capture complete (WAV 16k Mono). Calling wrapper...")

            # 3. Call wrapper script
            wrapper_path = os.path.join(os.path.dirname(__file__), "shazam_wrapper.py")
            
            # Run wrapper in a separate process to isolate crashes
            # We use sys.executable to ensure we use the same python interpreter
            res = subprocess.run(
                [sys.executable, wrapper_path, temp_file],
                capture_output=True,
                text=True
            )

            if res.returncode != 0:
                logger.error(f"Shazam wrapper failed (code {res.returncode}): {res.stderr}")
                return None

            try:
                result = json.loads(res.stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse wrapper output: {res.stdout}")
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