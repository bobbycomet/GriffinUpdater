"""
Community catalog support.

The catalog is a plain apps.json hosted in your Discordupdater GitHub repo
(or wherever you point DEFAULT_CATALOG_URL / the in-app Settings override).
It's just a JSON array of app definitions in the same shape as an AppEntry,
minus the purely-local fields (enabled/schedule/state), so Griffin Updater
can turn a catalog row directly into an editable AppEntry when the user
clicks "Add".

apps.json schema:
{
  "version": 1,
  "apps": [
    {
      "id": "discord",
      "name": "Discord",
      "category": "deb",
      "source_type": "static_url",
      "url": "https://discord.com/api/download?platform=linux&format=deb",
      "version_regex": "",
      "package_name": "discord",
      "description": "Voice, video and text chat."
    },
    {
      "id": "opentabletdriver",
      "name": "OpenTabletDriver",
      "category": "deb",
      "source_type": "github_release",
      "github_owner": "OpenTabletDriver",
      "github_repo": "OpenTabletDriver",
      "asset_pattern": "x64\\.deb$",
      "package_name": "opentabletdriver",
      "description": "Open source tablet driver."
    }
  ]
}
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from . import config
from .models import AppEntry

TIMEOUT = 20

# Matches https://github.com/{owner}/{repo}/blob/{branch}/{path...}
_GITHUB_BLOB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)$"
)
# Matches https://github.com/{owner}/{repo}/raw/{branch}/{path...} (GitHub's own raw-redirect form)
_GITHUB_RAW_SHORT_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/raw/(?P<branch>[^/]+)/(?P<path>.+)$"
)


class CatalogError(Exception):
    pass


def normalize_catalog_url(url: str) -> str:
    """Turns a pasted-in github.com 'view file' link (.../blob/branch/path,
    what you get from just copying the address bar) into the raw content
    URL that actually returns JSON instead of an HTML page."""
    url = url.strip()
    for pattern in (_GITHUB_BLOB_RE, _GITHUB_RAW_SHORT_RE):
        m = pattern.match(url)
        if m:
            return (
                f"https://raw.githubusercontent.com/{m['owner']}/{m['repo']}"
                f"/{m['branch']}/{m['path']}"
            )
    return url


def get_catalog_url() -> str:
    if config.SETTINGS_FILE.exists():
        try:
            settings = json.loads(config.SETTINGS_FILE.read_text())
            return normalize_catalog_url(settings.get("catalog_url") or config.DEFAULT_CATALOG_URL)
        except (json.JSONDecodeError, OSError):
            pass
    return config.DEFAULT_CATALOG_URL


def set_catalog_url(url: str) -> None:
    config.ensure_dirs()
    settings: dict[str, Any] = {}
    if config.SETTINGS_FILE.exists():
        try:
            settings = json.loads(config.SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
    settings["catalog_url"] = normalize_catalog_url(url)
    config.SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def refresh_catalog() -> list[dict[str, Any]]:
    """Fetches the remote apps.json and caches it locally. Raises
    CatalogError on failure (caller should fall back to load_cached_catalog)."""
    url = get_catalog_url()
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "GriffinUpdater/1.0"})
    except requests.RequestException as exc:
        raise CatalogError(f"Could not reach {url}: {exc}") from exc

    if resp.status_code == 404:
        raise CatalogError(
            f"{url} returned 404 Not Found. Double check the file exists on that "
            f"branch, and that the URL points at raw file content (not a github.com "
            f"'blob' page - those get auto-converted, but only if they match the "
            f"standard .../blob/<branch>/<path> shape)."
        )
    if resp.status_code >= 400:
        raise CatalogError(f"{url} returned HTTP {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        snippet = resp.text.strip().replace("\n", " ")[:120] or "(empty response)"
        raise CatalogError(
            f"{url} did not return valid JSON ({exc}). Response started with: {snippet!r}"
        ) from exc

    if not isinstance(data, dict) or "apps" not in data:
        raise CatalogError(f"{url} returned JSON, but it's missing the top-level 'apps' list.")

    apps = data.get("apps", [])
    config.ensure_dirs()
    cache_payload = {"fetched_at": time.time(), "source_url": url, "apps": apps}
    config.CATALOG_CACHE_FILE.write_text(json.dumps(cache_payload, indent=2))
    return apps


def load_cached_catalog() -> list[dict[str, Any]]:
    if not config.CATALOG_CACHE_FILE.exists():
        return []
    try:
        data = json.loads(config.CATALOG_CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("apps", [])


def catalog_entry_to_app_entry(row: dict[str, Any]) -> AppEntry:
    """Converts a raw catalog row into a fresh, locally-owned AppEntry the
    user can then tweak (schedule, target dir, enabled, etc.) before saving."""
    entry = AppEntry.from_dict(row)
    entry.from_catalog = True
    entry.enabled = True
    return entry
