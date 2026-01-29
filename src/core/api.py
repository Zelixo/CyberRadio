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
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CyberRadio/1.0)'})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

def fetch_azuracast_nowplaying():
    try:
        req = urllib.request.Request(AZURACAST_API_URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; CyberRadio/1.0)'})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"Azuracast fetch failed: {e}")
        return []
