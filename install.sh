#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="telly-spelly"
VENV_DIR="$SCRIPT_DIR/.venv"

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Telly Spelly Installer           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo

# Check system dependencies
check_dependencies() {
    local missing=()

    echo -e "${YELLOW}Checking system dependencies...${NC}"

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

    # Check for uv (preferred) or venv
    if command -v uv &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} uv found (will use for fast installation)"
        USE_UV=1
    elif python3 -c "import venv" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} venv module found"
        USE_UV=0
    else
        missing+=("python3-venv")
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

    # Check for pkg-config itself
    if ! command -v pkg-config &> /dev/null; then
        missing+=("pkg-config")
    fi

    echo

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing system dependencies:${NC}"
        for dep in "${missing[@]}"; do
            echo -e "  ${RED}✗${NC} $dep"
        done
        echo
        echo -e "${YELLOW}Please install them first with:${NC}"
        echo -e "  ${GREEN}sudo apt install ${missing[*]}${NC}"
        echo
        echo -e "On Fedora/RHEL:"
        echo -e "  ${GREEN}sudo dnf install python3-devel portaudio-devel dbus-devel glib2-devel${NC}"
        echo
        echo -e "On Arch:"
        echo -e "  ${GREEN}sudo pacman -S python portaudio dbus glib2${NC}"
        echo
        return 1
    fi

    echo -e "${GREEN}All system dependencies are met!${NC}"
    return 0
}

# Create virtual environment and install Python packages
install_python_deps() {
    echo
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"

    if [ "$USE_UV" = "1" ]; then
        uv venv "$VENV_DIR"
        echo -e "${YELLOW}Installing Python packages with uv...${NC}"
        uv pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        python3 -m venv "$VENV_DIR"
        echo -e "${YELLOW}Installing Python packages with pip...${NC}"
        "$VENV_DIR/bin/pip" install --upgrade pip
        "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    fi

    echo -e "${GREEN}Python packages installed!${NC}"
}

# Install desktop entry
install_desktop_entry() {
    echo
    echo -e "${YELLOW}Installing desktop entry...${NC}"

    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir"

    # Generate desktop file with correct paths
    cat > "$desktop_dir/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=Telly Spelly
Comment=Voice to text transcription using Whisper
Exec=$VENV_DIR/bin/python $SCRIPT_DIR/main.py
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

    update-desktop-database "$desktop_dir" 2>/dev/null || true

    echo -e "${GREEN}Desktop entry installed!${NC}"
}

# Register XFCE4 global shortcuts
register_xfce_shortcuts() {
    echo
    echo -e "${YELLOW}Registering XFCE4 keyboard shortcuts...${NC}"

    local toggle_cmd="dbus-send --session --type=method_call --dest=org.freedesktop.telly_spelly /TellySpelly org.freedesktop.telly_spelly.ToggleRecording"

    # Check if xfconf-query is available
    if ! command -v xfconf-query &> /dev/null; then
        echo -e "  ${YELLOW}!${NC} xfconf-query not found, skipping automatic shortcut registration"
        echo -e "  ${YELLOW}!${NC} You can manually add shortcuts in Settings → Keyboard → Application Shortcuts"
        echo -e "  ${YELLOW}→${NC} Command: $toggle_cmd"
        echo -e "  ${YELLOW}→${NC} Shortcut: Ctrl+Alt+R"
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
        echo -e "${GREEN}XFCE4 shortcuts registered!${NC}"
        echo -e "  ${GREEN}✓${NC} Ctrl+Alt+R: Toggle Recording"
    else
        echo -e "  ${YELLOW}!${NC} Could not register shortcut automatically"
        echo -e "  ${YELLOW}→${NC} Please add manually in Settings → Keyboard → Application Shortcuts"
        echo -e "  ${YELLOW}→${NC} Command: $toggle_cmd"
        echo -e "  ${YELLOW}→${NC} Shortcut: Ctrl+Alt+R"
    fi
}

# Print success message
print_success() {
    echo
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Installation Complete!           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo
    echo -e "You can now:"
    echo -e "  1. Launch ${GREEN}Telly Spelly${NC} from your application menu"
    echo -e "  2. Or run: ${GREEN}$VENV_DIR/bin/python $SCRIPT_DIR/main.py${NC}"
    echo
    echo -e "${YELLOW}To configure keyboard shortcuts:${NC}"
    echo -e "  Go to ${GREEN}System Settings → Shortcuts → Custom Shortcuts${NC}"
    echo -e "  Add a new shortcut with command:"
    echo -e "  ${GREEN}dbus-send --session --type=method_call --dest=org.kde.telly_spelly /TellySpelly org.kde.telly_spelly.ToggleRecording${NC}"
    echo
    echo -e "${YELLOW}To uninstall:${NC}"
    echo -e "  ${GREEN}$SCRIPT_DIR/uninstall.sh${NC}"
    echo
}

# Install icon
install_icon() {
    echo
    echo -e "${YELLOW}Installing application icon...${NC}"

    local icon_dir="$HOME/.local/share/icons/hicolor/scalable/apps"
    mkdir -p "$icon_dir"

    # Create a simple SVG icon if none exists
    if [ ! -f "$SCRIPT_DIR/telly-spelly.svg" ]; then
        cat > "$icon_dir/telly-spelly.svg" << 'SVGEOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
  <circle cx="24" cy="24" r="20" fill="#e74c3c"/>
  <circle cx="24" cy="24" r="12" fill="#c0392b"/>
  <circle cx="24" cy="24" r="6" fill="#ecf0f1"/>
</svg>
SVGEOF
    else
        cp "$SCRIPT_DIR/telly-spelly.svg" "$icon_dir/"
    fi

    # Update icon cache
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    echo -e "${GREEN}Icon installed!${NC}"
}

# Main installation
main() {
    if ! check_dependencies; then
        exit 1
    fi

    install_python_deps
    install_icon
    install_desktop_entry
    register_xfce_shortcuts
    print_success
}

main "$@"
