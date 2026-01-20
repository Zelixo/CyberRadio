Cyber Radio (Native GTK4)

A high-fidelity, synthwave-themed internet radio player for Linux.
Features a dynamic pixel-art cat visualization, physics-based spectrum analyzer, and AzuraCast API integration.

Dependencies (Arch Linux)

Ensure you have the required system libraries and Python packages installed:

sudo pacman -S python-gobject gtk4 libadwaita mpv python-mpv yt-dlp


python-gobject / gtk4 / libadwaita: The UI toolkit.

mpv: The audio engine.

python-mpv: Python bindings for MPV.

yt-dlp: Required for playing the "Lofi Girl" YouTube stream.

Installation

Place native_radio.py, CyberRadio.desktop, and install.sh in the same folder.

Run the installer script:

chmod +x install.sh
./install.sh


This will:

Create a folder at ~/Apps/CyberRadio.

Move the application script there.

Install the Desktop Shortcut to your system menu.

Manual Usage

You can always run the app directly from the terminal:

python3 native_radio.py
