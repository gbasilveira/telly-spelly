"""Desktop environment detection utilities."""

import os
import shutil


def get_desktop_environment():
    """
    Detect the current desktop environment.

    Returns:
        str: 'kde', 'xfce', or 'unknown'
    """
    # Check XDG_CURRENT_DESKTOP environment variable
    xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()

    if 'kde' in xdg_desktop or 'plasma' in xdg_desktop:
        return 'kde'
    elif 'xfce' in xdg_desktop:
        return 'xfce'

    # Check KDE_FULL_SESSION
    if os.environ.get('KDE_FULL_SESSION'):
        return 'kde'

    # Check for XFCE-specific variables
    if os.environ.get('XFCE_SESSION'):
        return 'xfce'

    # Check for available tools as fallback
    if shutil.which('kwriteconfig6') or shutil.which('kwriteconfig5'):
        return 'kde'
    elif shutil.which('xfconf-query'):
        return 'xfce'

    return 'unknown'


def get_dbus_service_name(de=None):
    """
    Get the appropriate D-Bus service name for the desktop environment.

    Args:
        de: Desktop environment ('kde', 'xfce', or None to auto-detect)

    Returns:
        str: D-Bus service name
    """
    if de is None:
        de = get_desktop_environment()

    if de == 'kde':
        return 'org.kde.telly_spelly'
    else:
        # Use freedesktop for XFCE and unknown DEs
        return 'org.freedesktop.telly_spelly'
