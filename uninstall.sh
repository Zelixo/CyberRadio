#!/bin/bash

# Configuration
APP_DIR="$HOME/Apps/CyberRadio"
DESKTOP_FILE="CyberRadio.desktop"
ICON_FILE="cyber-radio.png"

SYSTEM_DESKTOP_FILE="$HOME/.local/share/applications/$DESKTOP_FILE"
SYSTEM_ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/$ICON_FILE"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}:: Cyber Radio Uninstaller${NC}"
echo "This will remove Cyber Radio and its components from your user directory."
read -p "Are you sure? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo ":: Uninstall cancelled."
    exit 1
fi

# --- 1. REMOVE APPLICATION DIRECTORY ---
if [ -d "$APP_DIR" ]; then
    echo ":: Removing application directory: $APP_DIR"
    rm -rf "$APP_DIR"
else
    echo -e "${YELLOW}:: Application directory not found (already removed?)${NC}"
fi

# --- 2. REMOVE DESKTOP SHORTCUT ---
if [ -f "$SYSTEM_DESKTOP_FILE" ]; then
    echo ":: Removing desktop shortcut..."
    rm "$SYSTEM_DESKTOP_FILE"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
else
    echo -e "${YELLOW}:: Desktop shortcut not found.${NC}"
fi

# --- 3. REMOVE ICON ---
if [ -f "$SYSTEM_ICON_FILE" ]; then
    echo ":: Removing icon..."
    rm "$SYSTEM_ICON_FILE"
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
else
    echo -e "${YELLOW}:: Icon not found.${NC}"
fi

echo -e "${GREEN}:: Uninstallation Complete.${NC}"
echo "Note: Dependencies installed via your package manager were NOT removed."
