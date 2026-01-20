import urllib.request
import urllib.parse
import json
import logging
import threading

logger = logging.getLogger(__name__)

# Simple in-memory cache: { "Artist - Title": "url_to_image" }
_art_cache = {}

def fetch_album_art(query_term):
    """
    Searches iTunes API for the given query (Artist - Title) and returns
    a high-res album art URL if found. Returns None otherwise.
    """
    if not query_term:
        return None

    if query_term in _art_cache:
        return _art_cache[query_term]

    try:
        # iTunes API expects terms separated by +
        encoded_query = urllib.parse.quote(query_term)
        url = f"https://itunes.apple.com/search?term={encoded_query}&entity=song&limit=1"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            
        if data.get('resultCount', 0) > 0:
            # Get artwork url, prefer 100x100 but we can hack it to get larger
            result = data['results'][0]
            art_url = result.get('artworkUrl100')
            
            if art_url:
                # iTunes normally serves 100x100, but we can change the path to get 600x600
                # e.g., .../100x100bb.jpg -> .../600x600bb.jpg
                high_res_url = art_url.replace('100x100', '600x600')
                _art_cache[query_term] = high_res_url
                logger.info(f"Found album art for '{query_term}'")
                return high_res_url

    except Exception as e:
        logger.warning(f"Metadata lookup failed for '{query_term}': {e}")
    
    # Cache failure as None to prevent retrying same bad query immediately? 
    # Maybe not, temporary network fail shouldn't be cached forever.
    # For now, let's just return None.
    return None
