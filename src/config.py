import os

# API Endpoints
SEARCH_API_URL = os.getenv("CYBER_SEARCH_API", "https://de1.api.radio-browser.info/json/stations/search")
AZURACAST_API_URL = os.getenv("CYBER_AZURACAST_API", "https://radio.zelixo.net/api/nowplaying")

# File Paths
# We'll default to looking in the current directory for now, but in a real install
# these might need to be in ~/.config/CyberRadio/
FAVORITES_FILE = os.path.expanduser("~/.config/CyberRadio/favorites.json")
if not os.path.exists(os.path.dirname(FAVORITES_FILE)):
    # Fallback to local if config dir doesn't exist yet, or maybe create it?
    # For now let's keep the original behavior of "current dir" if we want simple portable,
    # but the prompt asked for improvement.
    # Let's try to use the XDG standard path if possible, but fallback to local for safety.
    # actually, the original used "cyber_favorites.json" in CWD.
    # Let's keep it simple for now but allow override.
    FAVORITES_FILE = "cyber_favorites.json"

DEFAULT_STATIONS = [
    {
        "name": "Nostalgia OST",
        "url_resolved": "https://radio.zelixo.net/listen/nostalgia_ost/stream",
        "countrycode": "OST",
        "favicon": "https://radio.zelixo.net/static/uploads/nostalgia_ost/album_art.1737523202.png"
    },
    {
        "name": "Night City Radio",
        "url_resolved": "https://radio.zelixo.net/listen/night_city_radio/ncradio",
        "countrycode": "NC",
        "favicon": "https://radio.zelixo.net/static/uploads/night_city_radio/album_art.1759461316.png"
    },
    {
        "name": "Japan EDM",
        "url_resolved": "https://radio.zelixo.net/listen/japedm/radio.flac",
        "countrycode": "JP",
        "favicon": "https://radio.zelixo.net/static/uploads/japedm/album_art.1744086733.jpg"
    },
    {
        "name": "DJ Zel Radio",
        "url_resolved": "https://radio.zelixo.net/listen/dj_zel/radio.mp3",
        "countrycode": "ZL",
        "favicon": "https://radio.zelixo.net/static/uploads/dj_zel/album_art.1737590207.png"
    },
    {
        "name": "ACNH Radio",
        "url_resolved": "https://radio.zelixo.net/listen/acnh_radio/radio.mp3",
        "countrycode": "AC",
        "favicon": "https://radio.zelixo.net/static/uploads/acnh_radio/album_art.1757640781.jpg"
    },
    {
        "name": "Lofi Girl",
        "url_resolved": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "countrycode": "FR",
        "favicon": "https://yt3.googleusercontent.com/ytc/AIdro_k4kF9xXq8vG5Q-7Jd3yR-u3Q1v7g-X3y9x-g=s900-c-k-c0x00ffffff-no-rj"
    }
]
