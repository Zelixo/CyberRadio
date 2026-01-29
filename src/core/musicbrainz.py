import musicbrainzngs
import logging

logger = logging.getLogger(__name__)

# Set a user-agent for MusicBrainz API requests
musicbrainzngs.set_useragent("CyberRadio", "1.0", "https://github.com/Zelixo/CyberRadio")

def get_musicbrainz_url(artist, title):
    """
    Searches for a recording on MusicBrainz and returns its URL if found.
    """
    try:
        # Search for recordings that match the artist and title
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=1)
        
        if result['recording-list']:
            recording = result['recording-list'][0]
            mbid = recording['id']
            return f"https://musicbrainz.org/recording/{mbid}"
            
    except musicbrainzngs.MusicBrainzError as e:
        logger.error(f"MusicBrainz API error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during MusicBrainz search: {e}")
        
    return None
