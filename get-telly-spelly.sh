#!/bin/bash
#
# Telly Spelly Installer
#
# Run with:
#   curl -sSL https://raw.githubusercontent.com/Dronakurl/telly-spelly/main/get-telly-spelly.sh | bash
#
# Or:
#   wget -qO- https://raw.githubusercontent.com/Dronakurl/telly-spelly/main/get-telly-spelly.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_NAME="telly-spelly"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
REPO_URL="https://github.com/Dronakurl/telly-spelly.git"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Telly Spelly Installer                      ║${NC}"
echo -e "${GREEN}║     Voice-to-text transcription for XFCE4               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running on a supported system
check_system() {
    if [[ ! "$XDG_CURRENT_DESKTOP" =~ (XFCE|xfce) ]]; then
        echo -e "${YELLOW}Warning: XFCE4 not detected. Telly Spelly is designed for XFCE4.${NC}"
        echo -e "${YELLOW}It may still work, but some features might not be available.${NC}"
        echo
    fi
}

# Check and install system dependencies
check_dependencies() {
    local missing=()

    echo -e "${BLUE}Step 1/4: Checking system dependencies...${NC}"
    echo

    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    else
        echo -e "  ${GREEN}✓${NC} Python 3 found: $(python3 --version)"
    fi

    # Check for pip
    if ! python3 -m pip --version &> /dev/null; then
        missing+=("python3-pip")
    else
        echo -e "  ${GREEN}✓${NC} pip found"
    fi

    # Check for venv
    if ! python3 -c "import venv" &> /dev/null; then
        missing+=("python3-venv")
    else
        echo -e "  ${GREEN}✓${NC} venv module found"
    fi

    # Check for git
    if ! command -v git &> /dev/null; then
        missing+=("git")
    else
        echo -e "  ${GREEN}✓${NC} git found"
    fi

    # Check for pkg-config
    if ! command -v pkg-config &> /dev/null; then
        missing+=("pkg-config")
    else
        echo -e "  ${GREEN}✓${NC} pkg-config found"
    fi

    # Check for portaudio (required for PyAudio)
    if ! pkg-config --exists portaudio-2.0 2>/dev/null; then
        if ! [ -f /usr/include/portaudio.h ]; then
            missing+=("portaudio19-dev")
        else
            echo -e "  ${GREEN}✓${NC} PortAudio found"
        fi
    else
        echo -e "  ${GREEN}✓${NC} PortAudio found"
    fi

    # Check for D-Bus development files (for dbus-python)
    if ! pkg-config --exists dbus-1 2>/dev/null; then
        missing+=("libdbus-1-dev")
    else
        echo -e "  ${GREEN}✓${NC} D-Bus development files found"
    fi

    # Check for GLib (for dbus-python)
    if ! pkg-config --exists glib-2.0 2>/dev/null; then
        missing+=("libglib2.0-dev")
    else
        echo -e "  ${GREEN}✓${NC} GLib found"
    fi

    echo

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing system dependencies:${NC}"
        for dep in "${missing[@]}"; do
            echo -e "  ${RED}✗${NC} $dep"
        done
        echo
        echo -e "${YELLOW}Please install them first:${NC}"
        echo
        echo -e "${BLUE}Ubuntu/Debian:${NC}"
        echo -e "  ${GREEN}sudo apt install ${missing[*]}${NC}"
        echo
        echo -e "${BLUE}Fedora:${NC}"
        echo -e "  ${GREEN}sudo dnf install python3-devel portaudio-devel dbus-devel glib2-devel git${NC}"
        echo
        echo -e "${BLUE}Arch Linux:${NC}"
        echo -e "  ${GREEN}sudo pacman -S python portaudio dbus glib2 git${NC}"
        echo
        echo -e "After installing dependencies, run this installer again."
        exit 1
    fi

    echo -e "${GREEN}All system dependencies are met!${NC}"
}

# Download the application
download_app() {
    echo
    echo -e "${BLUE}Step 2/4: Downloading Telly Spelly...${NC}"
    echo

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    if [ -d "$INSTALL_DIR/.git" ]; then
        echo -e "  Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --quiet
    else
        echo -e "  Cloning repository..."
        rm -rf "$INSTALL_DIR"
        git clone --quiet --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi

    echo -e "  ${GREEN}✓${NC} Downloaded to $INSTALL_DIR"
}

# Create virtual environment and install Python packages
install_python_deps() {
    echo
    echo -e "${BLUE}Step 3/4: Installing Python packages...${NC}"
    echo
    echo -e "  This may take a few minutes (downloading Whisper model ~1.5GB)..."
    echo

    local venv_dir="$INSTALL_DIR/.venv"

    # Check if uv is available (faster)
    if command -v uv &> /dev/null; then
        echo -e "  Using uv for fast installation..."
        uv venv "$venv_dir"
        cd "$INSTALL_DIR"
        uv pip install -r requirements.txt
    else
        echo -e "  Creating virtual environment..."
        python3 -m venv "$venv_dir"
        echo -e "  Installing packages with pip..."
        "$venv_dir/bin/pip" install --quiet --upgrade pip
        "$venv_dir/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    fi

    echo -e "  ${GREEN}✓${NC} Python packages installed"
}

# Install desktop integration
install_desktop_integration() {
    echo
    echo -e "${BLUE}Step 4/4: Setting up desktop integration...${NC}"
    echo

    local venv_dir="$INSTALL_DIR/.venv"
    local desktop_dir="$HOME/.local/share/applications"
    local icon_dir="$HOME/.local/share/icons/hicolor/scalable/apps"

    mkdir -p "$desktop_dir"
    mkdir -p "$icon_dir"

    # Install icon
    if [ -f "$INSTALL_DIR/telly-spelly.svg" ]; then
        cp "$INSTALL_DIR/telly-spelly.svg" "$icon_dir/"
    else
        # Create a simple SVG icon
        cat > "$icon_dir/telly-spelly.svg" << 'SVGEOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
  <circle cx="24" cy="24" r="20" fill="#e74c3c"/>
  <circle cx="24" cy="24" r="12" fill="#c0392b"/>
  <circle cx="24" cy="24" r="6" fill="#ecf0f1"/>
</svg>
SVGEOF
    fi
    echo -e "  ${GREEN}✓${NC} Icon installed"

    # Create desktop file
    cat > "$desktop_dir/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=Telly Spelly
Comment=Voice to text transcription using Whisper
Exec=$venv_dir/bin/python $INSTALL_DIR/main.py
Icon=telly-spelly
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Utility;
Keywords=voice;speech;transcription;whisper;
X-DBUS-ServiceName=org.kde.telly_spelly

Actions=StartRecording;StopRecording;ToggleRecording;

[Desktop Action StartRecording]
Name=Start Recording
Exec=dbus-send --session --type=method_call --dest=org.kde.telly_spelly /TellySpelly org.kde.telly_spelly.StartRecording
Icon=media-record

[Desktop Action StopRecording]
Name=Stop Recording
Exec=dbus-send --session --type=method_call --dest=org.kde.telly_spelly /TellySpelly org.kde.telly_spelly.StopRecording
Icon=media-playback-stop

[Desktop Action ToggleRecording]
Name=Toggle Recording
Exec=dbus-send --session --type=method_call --dest=org.kde.telly_spelly /TellySpelly org.kde.telly_spelly.ToggleRecording
Icon=media-record
EOF
    echo -e "  ${GREEN}✓${NC} Desktop entry installed"

    # Update desktop database
    update-desktop-database "$desktop_dir" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    # Register XFCE4 shortcuts
    register_xfce_shortcuts
}

# Register XFCE4 global shortcuts
register_xfce_shortcuts() {
    local toggle_cmd="dbus-send --session --type=method_call --dest=org.freedesktop.telly_spelly /TellySpelly org.freedesktop.telly_spelly.ToggleRecording"

    # Check if xfconf-query is available
    if ! command -v xfconf-query &> /dev/null; then
        echo -e "  ${YELLOW}!${NC} xfconf-query not found, shortcuts need manual setup"
        echo -e "  ${YELLOW}→${NC} Add in Settings → Keyboard → Application Shortcuts"
        return
    fi

    # Register shortcut with XFCE4
    xfconf-query -c xfce4-keyboard-shortcuts \
        -p "/commands/custom/<Primary><Alt>r" \
        -n -t string -s "$toggle_cmd" 2>/dev/null || \
    xfconf-query -c xfce4-keyboard-shortcuts \
        -p "/commands/custom/<Primary><Alt>r" \
        -s "$toggle_cmd" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Keyboard shortcuts registered (Ctrl+Alt+R)"
    else
        echo -e "  ${YELLOW}!${NC} Could not register shortcuts automatically"
    fi
}

# Print success message
print_success() {
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Installation Complete!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}How to use:${NC}"
    echo -e "  1. Launch ${GREEN}Telly Spelly${NC} from your application menu"
    echo -e "  2. Or press ${GREEN}Ctrl+Alt+R${NC} to toggle recording (after launching)"
    echo -e "  3. Speak, then press ${GREEN}Ctrl+Alt+R${NC} again to stop"
    echo -e "  4. The transcribed text is copied to your clipboard"
    echo
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "  • Right-click the tray icon → Settings"
    echo -e "  • Keyboard shortcuts: System Settings → Shortcuts → Telly Spelly"
    echo
    echo -e "${BLUE}To uninstall:${NC}"
    echo -e "  ${GREEN}$INSTALL_DIR/uninstall.sh${NC}"
    echo
    echo -e "${YELLOW}Note: You may need to log out and back in for shortcuts to work.${NC}"
    echo
}

# Main installation
main() {
    check_system
    check_dependencies
    download_app
    install_python_deps
    install_desktop_integration
    print_success
}

main "$@"
