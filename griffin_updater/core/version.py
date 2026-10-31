"""
Version resolution.

Two strategies, mirroring the two ways developers ship "latest" downloads:

1. static_url  - a URL that always resolves (via HTTP redirect) to the current
                 file, e.g. Discord's "?platform=linux&format=deb" endpoint.
                 We follow redirects and pull the version out of the final
                 URL/filename with a regex.

2. github_release - a GitHub repo whose release asset filenames change with
                 every version (e.g. opentabletdriver_0.6.7-1_x64.deb), so a
                 fixed URL goes stale the moment a new version ships. We ask
                 the GitHub Releases API for the *actual* latest release and
                 pick the asset matching a pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests

DEFAULT_VERSION_REGEX = r"(\d+(?:\.\d+){1,3}(?:-\d+)?)"
USER_AGENT = "GriffinUpdater/1.0 (+https://github.com/bobbycomet)"
TIMEOUT = 20


class VersionResolutionError(Exception):
    pass


@dataclass
class ResolvedVersion:
    version: str
    download_url: str
    filename: str


def _extract_version(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    if not m:
        return None
    return m.group(1) if m.groups() else m.group(0)


def resolve_static_url(url: str, version_regex: str = "") -> ResolvedVersion:
    pattern = version_regex.strip() or DEFAULT_VERSION_REGEX
    try:
        resp = requests.get(
            url, stream=True, allow_redirects=True, timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.close()
    except requests.RequestException as exc:
        raise VersionResolutionError(f"Could not reach {url}: {exc}") from exc

    if resp.status_code >= 400:
        raise VersionResolutionError(f"{url} returned HTTP {resp.status_code}")

    final_url = resp.url
    filename = final_url.rstrip("/").split("/")[-1].split("?")[0]

    version = _extract_version(final_url, pattern) or _extract_version(filename, pattern)
    if not version:
        # Some servers expose the real filename only in Content-Disposition
        cd = resp.headers.get("Content-Disposition", "")
        version = _extract_version(cd, pattern)
    if not version:
        raise VersionResolutionError(
            f"Resolved {url} -> {final_url} but couldn't find a version "
            f"using pattern '{pattern}'. Try setting a custom version regex."
        )
    return ResolvedVersion(version=version, download_url=final_url, filename=filename)


def resolve_github_release(owner: str, repo: str, asset_pattern: str) -> ResolvedVersion:
    if not (owner and repo):
        raise VersionResolutionError("GitHub owner/repo not set.")
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        resp = requests.get(
            api_url, timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        )
    except requests.RequestException as exc:
        raise VersionResolutionError(f"Could not reach GitHub API: {exc}") from exc

    if resp.status_code == 404:
        raise VersionResolutionError(f"No releases found for {owner}/{repo}.")
    if resp.status_code == 403:
        raise VersionResolutionError("GitHub API rate-limited this request. Try again later.")
    if resp.status_code >= 400:
        raise VersionResolutionError(f"GitHub API returned HTTP {resp.status_code}")

    data = resp.json()
    tag = str(data.get("tag_name", "")).lstrip("vV")
    assets = data.get("assets", []) or []

    pattern = asset_pattern.strip() or r".*\.(deb|AppImage)$"
    chosen = None
    for asset in assets:
        aname = asset.get("name", "")
        if re.search(pattern, aname, re.IGNORECASE):
            chosen = asset
            break

    if not chosen:
        available = ", ".join(a.get("name", "?") for a in assets) or "(no assets)"
        raise VersionResolutionError(
            f"No release asset in {owner}/{repo} matched pattern '{pattern}'. "
            f"Available assets: {available}"
        )

    if not tag:
        tag = _extract_version(chosen["name"], DEFAULT_VERSION_REGEX) or "unknown"

    return ResolvedVersion(
        version=tag,
        download_url=chosen["browser_download_url"],
        filename=chosen["name"],
    )


def resolve(entry) -> ResolvedVersion:
    """entry: models.AppEntry"""
    if entry.source_type == "github_release":
        return resolve_github_release(entry.github_owner, entry.github_repo, entry.asset_pattern)
    return resolve_static_url(entry.url, entry.version_regex)


def is_newer(new_version: str, old_version: Optional[str]) -> bool:
    """Best-effort version comparison. Prefers dpkg for deb-style strings,
    falls back to a tuple-of-ints compare, falls back to string inequality."""
    if not old_version:
        return True
    if new_version == old_version:
        return False

    try:
        import subprocess

        result = subprocess.run(
            ["dpkg", "--compare-versions", new_version, "gt", old_version],
            capture_output=True,
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        pass

    def to_tuple(v: str):
        parts = re.findall(r"\d+", v)
        return tuple(int(p) for p in parts) if parts else None

    nt, ot = to_tuple(new_version), to_tuple(old_version)
    if nt is not None and ot is not None:
        return nt > ot

    return new_version != old_version
