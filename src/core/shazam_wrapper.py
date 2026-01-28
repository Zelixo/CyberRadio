import asyncio
import sys
import json
import logging

# Configure logging to stderr so we don't pollute stdout (which is for JSON)
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

async def recognize(file_path):
    try:
        from shazamio import Shazam
        shazam = Shazam()
        result = await shazam.recognize(file_path)
        print(json.dumps(result))
    except Exception as e:
        # Print error as JSON so parent can parse it if needed, or just exit non-zero
        error_res = {"error": str(e)}
        print(json.dumps(error_res))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python3 shazam_wrapper.py <audio_file>\n")
        sys.exit(1)

    file_path = sys.argv[1]
    
    try:
        asyncio.run(recognize(file_path))
    except Exception as e:
        sys.stderr.write(f"Wrapper crashed: {e}\n")
        sys.exit(1)

