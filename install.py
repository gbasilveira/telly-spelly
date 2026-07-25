#!/usr/bin/env python3
"""Install Telly Spelly.

Builds a reproducible, locked virtual environment with uv (pinned Python
+ dependencies from uv.lock, including torch and openai-whisper), then
wires the app into ~/.local via link.py (launcher, desktop entry, icon).

Because uv provisions its own Python interpreter and all dependencies are
pinned in uv.lock, the install no longer depends on whatever
/usr/bin/python3 the distro ships, so system Python upgrades cannot break
it.

Prerequisite: uv (https://astral.sh/uv). The installer aborts with
instructions if uv is missing.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent


def ensure_uv():
    if shutil.which("uv") is None:
        print("ERROR: uv is not installed. Install it first:\n")
        print("    curl -LsSf https://astral.sh/uv/install.sh | sh\n")
        print("Then re-run this installer.")
        return False
    return True


def uv_sync():
    """Create .venv from the lockfile (pinned Python + dependencies)."""
    print("Building locked environment with `uv sync`...")
    try:
        subprocess.check_call(["uv", "sync"], cwd=REPO_DIR)
        return True
    except subprocess.CalledProcessError as e:
        print(f"`uv sync` failed: {e}")
        return False


def link():
    """Symlink the app into ~/.local (launcher, desktop entry, icon)."""
    print("Linking into ~/.local ...")
    try:
        subprocess.check_call(
            [sys.executable, str(REPO_DIR / "link.py"), "link"]
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"link.py failed: {e}")
        return False


def main():
    print("Telly Spelly installer\n")
    if not ensure_uv():
        return 1
    if not uv_sync():
        return 1
    if not link():
        return 1

    print("\nInstallation complete.")
    print("Launch 'Telly Spelly' from your application menu, or run "
          "`telly-spelly`.")
    print("You may need to log out and back in for the menu entry to appear.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)
