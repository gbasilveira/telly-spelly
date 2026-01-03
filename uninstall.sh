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

echo -e "${YELLOW}╔══════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║     Telly Spelly Uninstaller         ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════╝${NC}"
echo

# Stop running instances
echo -e "${YELLOW}Stopping running instances...${NC}"
pkill -f "python.*$SCRIPT_DIR/main.py" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Done"

# Remove desktop entry
echo -e "${YELLOW}Removing desktop entry...${NC}"
rm -f "$HOME/.local/share/applications/$APP_NAME.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Desktop entry removed"

# Remove icon
echo -e "${YELLOW}Removing icon...${NC}"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/telly-spelly.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Icon removed"

# Remove XFCE4 shortcuts
echo -e "${YELLOW}Removing XFCE4 shortcuts...${NC}"
if command -v xfconf-query &> /dev/null; then
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>r" -r 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Shortcuts removed"
else
    echo -e "  ${YELLOW}!${NC} xfconf-query not found, shortcuts may need manual removal"
    echo -e "  ${YELLOW}→${NC} Remove manually from Settings → Keyboard → Application Shortcuts"
fi

# Remove virtual environment
echo -e "${YELLOW}Removing virtual environment...${NC}"
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo -e "  ${GREEN}✓${NC} Virtual environment removed"
else
    echo -e "  ${YELLOW}!${NC} Virtual environment not found (already removed?)"
fi

# Remove cached Whisper models (optional)
echo
read -p "Remove cached Whisper models (~1.5GB)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$HOME/.cache/whisper" ]; then
        rm -rf "$HOME/.cache/whisper"
        echo -e "  ${GREEN}✓${NC} Whisper cache removed"
    else
        echo -e "  ${YELLOW}!${NC} No Whisper cache found"
    fi
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Uninstallation Complete!         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo
echo -e "The source files in ${GREEN}$SCRIPT_DIR${NC} were kept."
echo -e "To remove them completely: ${RED}rm -rf $SCRIPT_DIR${NC}"
echo
