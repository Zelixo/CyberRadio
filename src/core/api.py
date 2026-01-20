import urllib.request
import urllib.parse
import json
import logging
from src.config import SEARCH_API_URL, AZURACAST_API_URL

logger = logging.getLogger(__name__)

def search_stations(query):
    try:
        params = urllib.parse.urlencode({'name': query, 'limit': 20})
        url = f"{SEARCH_API_URL}?{params}"
        logger.debug(f"Searching: {url}")
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

def fetch_azuracast_nowplaying():
    try:
        with urllib.request.urlopen(AZURACAST_API_URL) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"Azuracast fetch failed: {e}")
        return []
