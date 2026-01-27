# Cyber Radio (Native GTK4)

A high-fidelity, synthwave-themed internet radio player for Linux.
Features a dynamic pixel-art cat visualization, physics-based spectrum analyzer, and AzuraCast API integration.

## Features
*   **Synthwave Aesthetic:** Custom GTK4 styling with a neon palette.
*   **Visualizations:** Custom "Vector Cat" and spectrum animations.
*   **Robust Playback:** Powered by MPV, supporting standard streams and YouTube (via yt-dlp).
*   **Station Management:** Add custom stations and manage favorites locally.

## Supported Distributions
The installer script currently supports automatic dependency installation for:
*   Arch Linux / Manjaro / EndeavourOS
*   Debian / Ubuntu / Linux Mint
*   Fedora

**Note on Song Identification:**
To use the "Identify Song" feature, you must install the `shazamio` library manually (as it is not typically in system repositories):
```bash
pip install shazamio --break-system-packages
# OR use a virtual environment
```

## Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/Zelixo/CyberRadio.git
    cd CyberRadio
    ```

2.  **Run the installer:**
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

    This will:
    *   Install system dependencies (requires `sudo`).
    *   Install the app to `~/Apps/CyberRadio`.
    *   Create a desktop shortcut and icon.

3.  **Launch:**
    Open "Cyber Radio" from your application menu.

## Manual Usage

You can run the application directly from the source directory without installing:

```bash
python3 native_radio.py
```

## Uninstallation

To remove the application and shortcuts (system dependencies will remain):

```bash
./uninstall.sh
```

## Project Structure
*   `src/`: Source code modules (UI, Core, Config).
*   `assets/`: Icons and CSS styles.
*   `native_radio.py`: Entry point script.
*   `install.sh` / `uninstall.sh`: Setup scripts.