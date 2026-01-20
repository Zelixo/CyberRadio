#!/bin/bash

# Configuration
APP_DIR="$HOME/Apps/CyberRadio"
SOURCE_SCRIPT="native_radio.py"
DESKTOP_FILE="CyberRadio.desktop"

SYSTEM_DESKTOP_DIR="$HOME/.local/share/applications"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}:: Starting Cyber Radio Installation...${NC}"

# --- 1. DETECT OS & INSTALL DEPENDENCIES ---
echo -e "${YELLOW}:: Detecting Operating System...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}:: Cannot detect OS. Skipping dependency check.${NC}"
    OS="unknown"
fi

install_arch() {
    DEPENDENCIES=("python-gobject" "gtk4" "libadwaita" "mpv" "python-mpv" "yt-dlp")
    MISSING_PKGS=()
    for pkg in "${DEPENDENCIES[@]}"; do
        if ! pacman -Qi "$pkg" &> /dev/null; then
            MISSING_PKGS+=("$pkg")
        fi
    done
    
    if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
        echo ":: Installing missing dependencies: ${MISSING_PKGS[*]}"
        sudo pacman -S --noconfirm "${MISSING_PKGS[@]}"
    fi
}

install_debian() {
    DEPENDENCIES=("python3-gi" "libgtk-4-1" "libadwaita-1-0" "mpv" "python3-mpv" "yt-dlp")
    echo ":: Updating apt cache..."
    sudo apt update
    echo ":: Installing dependencies..."
    sudo apt install -y "${DEPENDENCIES[@]}"
}

install_fedora() {
    DEPENDENCIES=("python3-gobject" "gtk4" "libadwaita" "mpv" "python3-mpv" "yt-dlp")
    echo ":: Installing dependencies..."
    sudo dnf install -y "${DEPENDENCIES[@]}"
}

case $OS in
    arch|manjaro|endeavouros)
        echo ":: Detected Arch-based system."
        install_arch
        ;;
    debian|ubuntu|pop|linuxmint)
        echo ":: Detected Debian/Ubuntu-based system."
        install_debian
        ;;
    fedora)
        echo ":: Detected Fedora."
        install_fedora
        ;;
    *)
        echo -e "${YELLOW}:: Unsupported or unknown OS ($OS). Please ensure dependencies are installed manually:${NC}"
        echo "   GTK4, Libadwaita, Python GObject, MPV, Python-MPV, yt-dlp"
        ;;
esac

# --- 2. CREATE DIRECTORY ---
if [ ! -d "$APP_DIR" ]; then
    echo ":: Creating app directory: $APP_DIR"
    mkdir -p "$APP_DIR"
fi

# --- 3. COPY APPLICATION FILES ---
echo ":: Copying application files..."

# Copy Entry Point
if [ -f "$SOURCE_SCRIPT" ]; then
    cp "$SOURCE_SCRIPT" "$APP_DIR/"
    chmod +x "$APP_DIR/$SOURCE_SCRIPT"
else
    echo -e "${RED}Error: $SOURCE_SCRIPT not found.${NC}"
    exit 1
fi

# Copy Modules
if [ -d "src" ]; then
    rm -rf "$APP_DIR/src"
    cp -r "src" "$APP_DIR/"
else
    echo -e "${RED}Error: 'src' directory not found.${NC}"
    exit 1
fi

# Copy Assets
if [ -d "assets" ]; then
    rm -rf "$APP_DIR/assets"
    cp -r "assets" "$APP_DIR/"
else
    echo -e "${RED}Error: 'assets' directory not found.${NC}"
    exit 1
fi

# --- 4. INSTALL DESKTOP SHORTCUT ---
if [ -f "$DESKTOP_FILE" ]; then
    echo ":: Configuring desktop shortcut..."
    # Replace {HOME} placeholder with actual home path
    sed "s|{HOME}|$HOME|g" "$DESKTOP_FILE" > "$SYSTEM_DESKTOP_DIR/$DESKTOP_FILE"

    # Refresh databases
    update-desktop-database "$SYSTEM_DESKTOP_DIR" 2>/dev/null

    echo ":: Desktop shortcut installed."
else
    echo -e "${YELLOW}Warning: $DESKTOP_FILE not found.${NC}"
fi

echo -e "${GREEN}:: Installation Complete!${NC}"
echo "You can now run 'Cyber Radio' from your menu or via:"
echo "python3 $APP_DIR/$SOURCE_SCRIPT"
