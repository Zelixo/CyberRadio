#!/bin/bash

# Configuration
APP_DIR="$HOME/Apps/CyberRadio"
SOURCE_SCRIPT="native_radio.py"
DESKTOP_FILE="CyberRadio.desktop"
ICON_FILE="cyber-radio.png"

SYSTEM_DESKTOP_DIR="$HOME/.local/share/applications"
SYSTEM_ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}:: Installing Cyber Radio...${NC}"

# 1. Create Directory
if [ ! -d "$APP_DIR" ]; then
    echo "Creating app directory: $APP_DIR"
    mkdir -p "$APP_DIR"
fi

# 2. Copy App Script
if [ -f "$SOURCE_SCRIPT" ]; then
    echo "Copying application..."
    cp "$SOURCE_SCRIPT" "$APP_DIR/"
    chmod +x "$APP_DIR/$SOURCE_SCRIPT"
else
    echo "Error: $SOURCE_SCRIPT not found in current directory."
    exit 1
fi

# 3. Install Icon
if [ -f "$ICON_FILE" ]; then
    echo "Installing icon..."
    mkdir -p "$SYSTEM_ICON_DIR"
    cp "$ICON_FILE" "$SYSTEM_ICON_DIR/"
else
    echo "Warning: $ICON_FILE not found. App will use generic icon."
fi

# 4. Process and Install Desktop File
if [ -f "$DESKTOP_FILE" ]; then
    echo "Configuring desktop shortcut..."
    # Replace {HOME} placeholder with actual home path
    sed "s|{HOME}|$HOME|g" "$DESKTOP_FILE" > "$SYSTEM_DESKTOP_DIR/$DESKTOP_FILE"

    # Refresh database
    update-desktop-database "$SYSTEM_DESKTOP_DIR" 2>/dev/null
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    echo "Desktop shortcut installed to $SYSTEM_DESKTOP_DIR/$DESKTOP_FILE"
else
    echo "Warning: $DESKTOP_FILE not found. Skipping shortcut creation."
fi

echo -e "${GREEN}:: Installation Complete!${NC}"
echo "You can now find 'Cyber Radio' in your application menu with its custom icon."
echo "Or run it manually: python3 $APP_DIR/$SOURCE_SCRIPT"
