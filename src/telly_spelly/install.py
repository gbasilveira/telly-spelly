#!/usr/bin/env python3
"""Install desktop integration for Telly Spelly (icon, desktop entry, shortcuts for KDE/XFCE)"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

try:
    from .desktop_env import get_desktop_environment, get_dbus_service_name
except ImportError:
    # Fallback for when running directly
    import desktop_env
    get_desktop_environment = desktop_env.get_desktop_environment
    get_dbus_service_name = desktop_env.get_dbus_service_name


# Detect desktop environment
DESKTOP_ENV = get_desktop_environment()
DBUS_SERVICE = get_dbus_service_name(DESKTOP_ENV)

# Desktop entry categories based on DE
if DESKTOP_ENV == 'kde':
    CATEGORIES = "AudioVideo;Audio;Utility;Qt;KDE;"
else:
    CATEGORIES = "AudioVideo;Audio;Utility;Qt;XFCE;"

DESKTOP_ENTRY = f"""[Desktop Entry]
Name=Telly Spelly
Comment=Voice to text transcription using Whisper
Exec=telly-spelly
Icon=telly-spelly
Terminal=false
Type=Application
Categories={CATEGORIES}
Keywords=voice;speech;transcription;whisper;
X-DBUS-ServiceName={DBUS_SERVICE}

Actions=ToggleRecording;

[Desktop Action ToggleRecording]
Name=Toggle Recording
Exec=dbus-send --session --type=method_call --dest={DBUS_SERVICE} /TellySpelly {DBUS_SERVICE}.ToggleRecording
Icon=media-record
"""

SHORTCUT_ENTRY = f"""[Desktop Entry]
Name=Telly Spelly
Comment=Voice to text transcription

[Desktop Action ToggleRecording]
Name=Toggle Recording
Exec=dbus-send --session --type=method_call --dest={DBUS_SERVICE} /TellySpelly {DBUS_SERVICE}.ToggleRecording
"""


def get_package_dir():
    """Get the directory where this package is installed"""
    return Path(__file__).parent


def is_desktop_integration_installed():
    """Check if desktop integration is already installed"""
    desktop_file = Path.home() / ".local/share/applications/telly-spelly.desktop"
    icon_file = Path.home() / ".local/share/icons/hicolor/128x128/apps/telly-spelly.png"
    return desktop_file.exists() and icon_file.exists()


def install_silent():
    """Install desktop integration silently (no output). Returns True if installed."""
    if is_desktop_integration_installed():
        return False

    install_icon_silent()
    install_desktop_entry_silent()
    install_kde_shortcuts_silent()
    return True


def install_icon_silent():
    """Install the application icon silently"""
    icon_dest = Path.home() / ".local/share/icons/hicolor/128x128/apps"
    icon_dest.mkdir(parents=True, exist_ok=True)

    icon_sources = [
        get_package_dir() / "telly-spelly.png",
        get_package_dir().parent.parent / "telly-spelly.png",
        Path.cwd() / "telly-spelly.png",
    ]

    for src in icon_sources:
        if src.exists():
            shutil.copy(src, icon_dest / "telly-spelly.png")
            break

    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(Path.home() / ".local/share/icons/hicolor")],
            capture_output=True
        )
    except FileNotFoundError:
        pass


def install_desktop_entry_silent():
    """Install the desktop entry silently"""
    apps_dir = Path.home() / ".local/share/applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = apps_dir / "telly-spelly.desktop"
    desktop_file.write_text(DESKTOP_ENTRY)

    try:
        subprocess.run(["update-desktop-database", str(apps_dir)], capture_output=True)
    except FileNotFoundError:
        pass


def install_shortcuts_silent():
    """Install keyboard shortcuts silently based on desktop environment"""
    if DESKTOP_ENV == 'kde':
        install_kde_shortcuts_silent()
    else:
        install_xfce_shortcuts_silent()


def install_kde_shortcuts_silent():
    """Install KDE shortcut configuration silently"""
    shortcuts_dir = Path.home() / ".local/share/kglobalaccel"
    shortcuts_dir.mkdir(parents=True, exist_ok=True)

    shortcut_file = shortcuts_dir / "telly-spelly.desktop"
    shortcut_file.write_text(SHORTCUT_ENTRY)

    # Use kwriteconfig to set shortcut (works on both KDE 5 and 6)
    kwriteconfig = "kwriteconfig6" if shutil.which("kwriteconfig6") else "kwriteconfig5"
    try:
        subprocess.run([
            kwriteconfig, "--file", "kglobalshortcutsrc",
            "--group", "telly-spelly.desktop",
            "--key", "ToggleRecording",
            "Ctrl+Alt+R,Ctrl+Alt+R,Toggle Recording"
        ], capture_output=True)
        subprocess.run([
            kwriteconfig, "--file", "kglobalshortcutsrc",
            "--group", "telly-spelly.desktop",
            "--key", "_k_friendly_name",
            "Telly Spelly"
        ], capture_output=True)
    except FileNotFoundError:
        # Fallback: write directly to config file
        kglobal_rc = Path.home() / ".config/kglobalshortcutsrc"
        shortcut_config = """
[telly-spelly.desktop]
ToggleRecording=Ctrl+Alt+R,Ctrl+Alt+R,Toggle Recording
_k_friendly_name=Telly Spelly
"""
        if kglobal_rc.exists():
            content = kglobal_rc.read_text()
            if "[telly-spelly.desktop]" not in content:
                with open(kglobal_rc, "a") as f:
                    f.write(shortcut_config)
        else:
            kglobal_rc.write_text(shortcut_config.strip() + "\n")

    # Reload kglobalaccel to pick up new shortcuts
    try:
        kquitapp = "kquitapp6" if shutil.which("kquitapp6") else "kquitapp5"
        kstart = "kstart6" if shutil.which("kstart6") else "kstart5"
        subprocess.run([kquitapp, "kglobalaccel"], capture_output=True, timeout=5)
        subprocess.run([kstart, "kglobalaccel6" if "6" in kstart else "kglobalaccel5"],
                      capture_output=True, timeout=5)
    except Exception:
        pass


def install_xfce_shortcuts_silent():
    """Install XFCE4 shortcut configuration silently"""
    try:
        # Use xfconf-query to set up keyboard shortcut
        shortcut_command = f"dbus-send --session --type=method_call --dest={DBUS_SERVICE} /TellySpelly {DBUS_SERVICE}.ToggleRecording"

        subprocess.run([
            "xfconf-query", "-c", "xfce4-keyboard-shortcuts",
            "-p", "/commands/custom/<Primary><Alt>r",
            "-n", "-t", "string", "-s", shortcut_command
        ], capture_output=True, check=False)
    except FileNotFoundError:
        # xfconf-query not available, skip silent installation
        pass


def install_icon():
    """Install the application icon"""
    icon_dest = Path.home() / ".local/share/icons/hicolor/128x128/apps"
    icon_dest.mkdir(parents=True, exist_ok=True)

    # Look for icon in package directory or current directory
    icon_sources = [
        get_package_dir() / "telly-spelly.png",
        get_package_dir().parent.parent / "telly-spelly.png",
        Path.cwd() / "telly-spelly.png",
    ]

    icon_src = None
    for src in icon_sources:
        if src.exists():
            icon_src = src
            break

    if icon_src:
        shutil.copy(icon_src, icon_dest / "telly-spelly.png")
        print(f"✓ Icon installed to {icon_dest}")
    else:
        print("⚠ Icon file not found, using system theme icon")

    # Update icon cache
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(Path.home() / ".local/share/icons/hicolor")],
            capture_output=True
        )
    except FileNotFoundError:
        pass


def install_desktop_entry():
    """Install the desktop entry"""
    apps_dir = Path.home() / ".local/share/applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = apps_dir / "telly-spelly.desktop"
    desktop_file.write_text(DESKTOP_ENTRY)

    # Update desktop database
    try:
        subprocess.run(["update-desktop-database", str(apps_dir)], capture_output=True)
    except FileNotFoundError:
        pass

    print(f"✓ Desktop entry installed to {desktop_file}")


def install_shortcuts():
    """Install keyboard shortcuts based on desktop environment"""
    print(f"\nDetected desktop environment: {DESKTOP_ENV.upper()}")

    if DESKTOP_ENV == 'kde':
        install_kde_shortcuts()
    else:
        install_xfce_shortcuts()


def install_kde_shortcuts():
    """Install KDE shortcut configuration"""
    shortcuts_dir = Path.home() / ".local/share/kglobalaccel"
    shortcuts_dir.mkdir(parents=True, exist_ok=True)

    shortcut_file = shortcuts_dir / "telly-spelly.desktop"
    shortcut_file.write_text(SHORTCUT_ENTRY)

    # Use kwriteconfig to set shortcut (works on both KDE 5 and 6)
    kwriteconfig = "kwriteconfig6" if shutil.which("kwriteconfig6") else "kwriteconfig5"
    try:
        subprocess.run([
            kwriteconfig, "--file", "kglobalshortcutsrc",
            "--group", "telly-spelly.desktop",
            "--key", "ToggleRecording",
            "Ctrl+Alt+R,Ctrl+Alt+R,Toggle Recording"
        ], capture_output=True)
        subprocess.run([
            kwriteconfig, "--file", "kglobalshortcutsrc",
            "--group", "telly-spelly.desktop",
            "--key", "_k_friendly_name",
            "Telly Spelly"
        ], capture_output=True)
        print("✓ KDE shortcut Ctrl+Alt+R configured")
        print("  (You can modify this in System Settings → Shortcuts)")
    except FileNotFoundError:
        # Fallback: write directly to config file
        kglobal_rc = Path.home() / ".config/kglobalshortcutsrc"
        shortcut_config = """
[telly-spelly.desktop]
ToggleRecording=Ctrl+Alt+R,Ctrl+Alt+R,Toggle Recording
_k_friendly_name=Telly Spelly
"""
        if kglobal_rc.exists():
            content = kglobal_rc.read_text()
            if "[telly-spelly.desktop]" not in content:
                with open(kglobal_rc, "a") as f:
                    f.write(shortcut_config)
                print("✓ KDE shortcut Ctrl+Alt+R configured")
            else:
                print("✓ KDE shortcut already configured")
        else:
            kglobal_rc.write_text(shortcut_config.strip() + "\n")
            print("✓ KDE shortcut Ctrl+Alt+R configured")

    # Reload kglobalaccel to pick up new shortcuts
    try:
        kquitapp = "kquitapp6" if shutil.which("kquitapp6") else "kquitapp5"
        kstart = "kstart6" if shutil.which("kstart6") else "kstart5"
        subprocess.run([kquitapp, "kglobalaccel"], capture_output=True, timeout=5)
        subprocess.run([kstart, "kglobalaccel6" if "6" in kstart else "kglobalaccel5"],
                      capture_output=True, timeout=5)
    except Exception:
        pass


def install_xfce_shortcuts():
    """Install XFCE4 shortcut configuration"""
    shortcut_command = f"dbus-send --session --type=method_call --dest={DBUS_SERVICE} /TellySpelly {DBUS_SERVICE}.ToggleRecording"

    try:
        # Use xfconf-query to set up keyboard shortcut
        subprocess.run([
            "xfconf-query", "-c", "xfce4-keyboard-shortcuts",
            "-p", "/commands/custom/<Primary><Alt>r",
            "-n", "-t", "string", "-s", shortcut_command
        ], capture_output=True, check=False)
        print("✓ XFCE4 shortcut Ctrl+Alt+R configured")
        print("  (You can modify this in Settings → Keyboard → Application Shortcuts)")
    except FileNotFoundError:
        print("⚠ xfconf-query not found. Please configure shortcuts manually:")
        print("  1. Open Settings → Keyboard → Application Shortcuts")
        print("  2. Click 'Add' and use command:")
        print(f"     {shortcut_command}")
        print("  3. Press Ctrl+Alt+R when prompted")


def main():
    """Main install function"""
    print("Installing Telly Spelly desktop integration...\n")

    install_icon()
    install_desktop_entry()
    install_shortcuts()

    print("\n✓ Installation complete!")
    print("\nTo start Telly Spelly:")
    print("  - Run 'telly-spelly' from terminal")
    print("  - Or find 'Telly Spelly' in your application menu")
    print("  - Use Ctrl+Alt+R to toggle recording")

    return 0


def uninstall():
    """Remove desktop integration"""
    print("Removing Telly Spelly desktop integration...\n")

    files_to_remove = [
        Path.home() / ".local/share/applications/telly-spelly.desktop",
        Path.home() / ".local/share/icons/hicolor/128x128/apps/telly-spelly.png",
    ]

    # Remove shortcuts based on desktop environment
    if DESKTOP_ENV == 'kde':
        # Remove KDE shortcut
        kwriteconfig = "kwriteconfig6" if shutil.which("kwriteconfig6") else "kwriteconfig5"
        try:
            if shutil.which(kwriteconfig):
                subprocess.run([
                    kwriteconfig, "--file", "kglobalshortcutsrc",
                    "--group", "telly-spelly.desktop",
                    "--delete"
                ], capture_output=True, check=False)
                print("✓ Removed KDE shortcut")
        except Exception:
            pass
        # Also remove kglobalaccel file
        kglobalaccel_file = Path.home() / ".local/share/kglobalaccel/telly-spelly.desktop"
        if kglobalaccel_file.exists():
            kglobalaccel_file.unlink()
    else:
        # Remove XFCE4 shortcut
        try:
            subprocess.run([
                "xfconf-query", "-c", "xfce4-keyboard-shortcuts",
                "-p", "/commands/custom/<Primary><Alt>r",
                "-r"
            ], capture_output=True, check=False)
            print("✓ Removed XFCE4 shortcut")
        except FileNotFoundError:
            pass

    for f in files_to_remove:
        if f.exists():
            f.unlink()
            print(f"✓ Removed {f}")

    print("\n✓ Uninstall complete!")

    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        sys.exit(uninstall())
    sys.exit(main())
