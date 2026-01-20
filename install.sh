#!/bin/bash

# Configuration
APP_DIR="$HOME/Apps/CyberRadio"
SOURCE_SCRIPT="native_radio.py"
DESKTOP_FILE="CyberRadio.desktop"
ICON_FILE="cyber-radio.svg"

SYSTEM_DESKTOP_DIR="$HOME/.local/share/applications"
SYSTEM_ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# Dependencies list (Arch Linux package names)
DEPENDENCIES=("python-gobject" "gtk4" "libadwaita" "mpv" "python-mpv" "yt-dlp")

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}:: Starting Cyber Radio Installation...${NC}"

# --- 1. DEPENDENCY CHECK ---
echo -e "${YELLOW}:: Checking system dependencies...${NC}"
MISSING_PKGS=()

for pkg in "${DEPENDENCIES[@]}"; do
    if ! pacman -Qi "$pkg" &> /dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    echo -e "${RED}:: Missing packages found: ${MISSING_PKGS[*]}${NC}"
    echo ":: Attempting to install missing dependencies (requires sudo)..."

    if sudo pacman -S --noconfirm "${MISSING_PKGS[@]}"; then
        echo -e "${GREEN}:: Dependencies installed successfully.${NC}"
    else
        echo -e "${RED}:: Failed to install dependencies. Please install them manually and run this script again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}:: All dependencies are installed.${NC}"
fi

# --- 2. CREATE DIRECTORY ---
if [ ! -d "$APP_DIR" ]; then
    echo ":: Creating app directory: $APP_DIR"
    mkdir -p "$APP_DIR"
fi

# --- 3. COPY APPLICATION ---
if [ -f "$SOURCE_SCRIPT" ]; then
    echo ":: Copying application script..."
    cp "$SOURCE_SCRIPT" "$APP_DIR/"
    chmod +x "$APP_DIR/$SOURCE_SCRIPT"
else
    echo -e "${RED}Error: $SOURCE_SCRIPT not found in current directory.${NC}"
    exit 1
fi

# --- 4. INSTALL ICON ---
if [ -f "$ICON_FILE" ]; then
    echo ":: Installing icon..."
    mkdir -p "$SYSTEM_ICON_DIR"
    cp "$ICON_FILE" "$SYSTEM_ICON_DIR/"
else
    echo -e "${YELLOW}Warning: $ICON_FILE not found. App will use generic system icon.${NC}"
fi

# --- 5. INSTALL DESKTOP SHORTCUT ---
if [ -f "$DESKTOP_FILE" ]; then
    echo ":: Configuring desktop shortcut..."
    # Replace {HOME} placeholder with actual home path
    sed "s|{HOME}|$HOME|g" "$DESKTOP_FILE" > "$SYSTEM_DESKTOP_DIR/$DESKTOP_FILE"

    # Refresh databases
    update-desktop-database "$SYSTEM_DESKTOP_DIR" 2>/dev/null
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    echo ":: Desktop shortcut installed to $SYSTEM_DESKTOP_DIR/$DESKTOP_FILE"
else
    echo -e "${YELLOW}Warning: $DESKTOP_FILE not found. Skipping shortcut creation.${NC}"
fi

echo -e "${GREEN}:: Installation Complete!${NC}"
echo "You can now find 'Cyber Radio' in your application menu."
echo "Or run it manually: python3 $APP_DIR/$SOURCE_SCRIPT"
