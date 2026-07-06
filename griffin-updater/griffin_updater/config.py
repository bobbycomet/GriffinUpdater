"""
Central path/config constants for Griffin Updater.

Layout on disk:
  ~/.config/griffin-updater/my_apps.json      -> the user's local, editable app list
  ~/.config/griffin-updater/settings.json     -> app-wide settings
  ~/.config/systemd/user/griffin-updater-*    -> generated per-app service/timer units
  ~/.local/share/griffin-updater/state.json   -> last known / installed versions, timestamps
  ~/.local/share/griffin-updater/catalog_cache.json -> cached copy of the remote catalog
  ~/.local/share/griffin-updater/griffin-updater.log -> rolling log file
"""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()

CONFIG_DIR = HOME / ".config" / "griffin-updater"
DATA_DIR = HOME / ".local" / "share" / "griffin-updater"
SYSTEMD_USER_DIR = HOME / ".config" / "systemd" / "user"
DESKTOP_DIR = HOME / "Desktop"

MY_APPS_FILE = CONFIG_DIR / "my_apps.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

STATE_FILE = DATA_DIR / "state.json"
CATALOG_CACHE_FILE = DATA_DIR / "catalog_cache.json"
LOG_FILE = DATA_DIR / "griffin-updater.log"

# Where the app looks for the community catalog. Point this at the raw file
# in your Discordupdater repo (rename/relocate the repo any time; just update
# this constant, or override it from the in-app Settings dialog which writes
# a "catalog_url" key into settings.json).
DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/bobbycomet/GriffinUpdater/main/apps.json"
)

APP_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "griffin-updater.png"

UNIT_PREFIX = "griffin-updater"  # -> griffin-updater-<id>.service / .timer


def ensure_dirs() -> None:
    for d in (CONFIG_DIR, DATA_DIR, SYSTEMD_USER_DIR):
        d.mkdir(parents=True, exist_ok=True)


def python_executable() -> str:
    """Best-effort path to a python3 that can 'import griffin_updater'."""
    import sys

    return sys.executable or "/usr/bin/python3"
