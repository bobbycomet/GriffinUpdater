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
                 pick the asset matching a pattern. With "include pre-releases"
                 enabled we list recent releases instead (GitHub's /latest
                 endpoint never returns pre-releases) and take the newest
                 non-draft release that has a matching asset.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlsplit

import requests

from .. import __version__
from .sysproc import host_env

DEFAULT_VERSION_REGEX = r"(\d+(?:\.\d+){1,3}(?:-\d+)?)"
USER_AGENT = f"GriffinUpdater/{__version__} (+https://github.com/bobbycomet)"
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


def _github_get(api_url: str, owner: str, repo: str, include_prereleases: bool):
    try:
        resp = requests.get(
            api_url, timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        )
    except requests.RequestException as exc:
        raise VersionResolutionError(f"Could not reach GitHub API: {exc}") from exc

    if resp.status_code == 404:
        hint = "" if include_prereleases else (
            " If this project only publishes pre-releases, enable "
            "'Include pre-releases' for this app."
        )
        raise VersionResolutionError(f"No releases found for {owner}/{repo}.{hint}")
    if resp.status_code == 403:
        raise VersionResolutionError("GitHub API rate-limited this request. Try again later.")
    if resp.status_code >= 400:
        raise VersionResolutionError(f"GitHub API returned HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise VersionResolutionError(f"GitHub API returned invalid JSON: {exc}") from exc


def resolve_github_release(owner: str, repo: str, asset_pattern: str,
                           include_prereleases: bool = False) -> ResolvedVersion:
    if not (owner and repo):
        raise VersionResolutionError("GitHub owner/repo not set.")

    if include_prereleases:
        data = _github_get(
            f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=30",
            owner, repo, True,
        )
        if not isinstance(data, list):
            raise VersionResolutionError(f"Unexpected GitHub API response for {owner}/{repo}.")
        # Newest first (GitHub's ordering); drafts are always excluded.
        releases = [r for r in data if not r.get("draft")]
        if not releases:
            raise VersionResolutionError(f"No published releases found for {owner}/{repo}.")
    else:
        releases = [_github_get(
            f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
            owner, repo, False,
        )]

    return _pick_release_asset(releases, f"{owner}/{repo}", asset_pattern)


def _gitea_api_url(host: str, owner: str, repo: str, endpoint: str) -> str:
    host = host.strip().rstrip("/") or "codeberg.org"
    if "://" not in host:
        host = f"https://{host}"
    parsed = urlsplit(host)
    if (parsed.scheme not in ("http", "https") or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise VersionResolutionError(f"Invalid Gitea host '{host}'.")
    base_path = parsed.path.rstrip("/")
    release_url = (
        f"{parsed.scheme}://{parsed.netloc}{base_path}/api/v1/repos/"
        f"{quote(owner, safe='')}/{quote(repo, safe='')}/releases"
    )
    if endpoint.startswith("?"):
        return release_url + endpoint
    return f"{release_url}/{endpoint}" if endpoint else release_url


def _gitea_get(api_url: str, owner: str, repo: str, include_prereleases: bool):
    try:
        resp = requests.get(
            api_url, timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
    except requests.RequestException as exc:
        raise VersionResolutionError(f"Could not reach Gitea API: {exc}") from exc

    if resp.status_code == 404:
        hint = "" if include_prereleases else (
            " If this project only publishes pre-releases, enable "
            "'Include pre-releases' for this app."
        )
        raise VersionResolutionError(f"No releases found for {owner}/{repo}.{hint}")
    if resp.status_code >= 400:
        raise VersionResolutionError(f"Gitea API returned HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise VersionResolutionError(f"Gitea API returned invalid JSON: {exc}") from exc


def resolve_gitea_release(host: str, owner: str, repo: str, asset_pattern: str,
                          include_prereleases: bool = False) -> ResolvedVersion:
    if not (owner and repo):
        raise VersionResolutionError("Gitea owner/repo not set.")

    if include_prereleases:
        data = _gitea_get(
            _gitea_api_url(host, owner, repo, "?limit=30"),
            owner, repo, True,
        )
        if not isinstance(data, list):
            raise VersionResolutionError(f"Unexpected Gitea API response for {owner}/{repo}.")
        releases = [release for release in data if not release.get("draft")]
        if not releases:
            raise VersionResolutionError(f"No published releases found for {owner}/{repo}.")
    else:
        releases = [_gitea_get(
            _gitea_api_url(host, owner, repo, "latest"),
            owner, repo, False,
        )]

    return _pick_release_asset(releases, f"{owner}/{repo}", asset_pattern)


def _pick_release_asset(releases: list[dict], repo_label: str,
                        asset_pattern: str) -> ResolvedVersion:
    pattern = asset_pattern.strip() or r".*\.(deb|AppImage)$"
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise VersionResolutionError(f"Invalid asset filename pattern '{pattern}': {exc}") from exc

    # Newest release that actually contains a matching asset.
    for rel in releases:
        for asset in rel.get("assets", []) or []:
            name = asset.get("name", "")
            if regex.search(name):
                tag = str(rel.get("tag_name", "")).lstrip("vV")
                if not tag:
                    tag = _extract_version(name, DEFAULT_VERSION_REGEX) or "unknown"
                download_url = asset.get("browser_download_url")
                if not download_url:
                    continue
                return ResolvedVersion(
                    version=tag,
                    download_url=download_url,
                    filename=name,
                )

    seen = [a.get("name", "?") for r in releases[:3] for a in (r.get("assets") or [])]
    raise VersionResolutionError(
        f"No release asset in {repo_label} matched pattern '{pattern}'. "
        f"Available assets: {', '.join(seen) or '(no assets)'}"
    )


def resolve(entry) -> ResolvedVersion:
    """entry: models.AppEntry"""
    if entry.source_type == "github_release":
        return resolve_github_release(
            entry.github_owner, entry.github_repo, entry.asset_pattern,
            getattr(entry, "include_prereleases", False),
        )
    if entry.source_type == "gitea_release":
        return resolve_gitea_release(
            entry.gitea_host, entry.gitea_owner, entry.gitea_repo,
            entry.asset_pattern, entry.include_prereleases,
        )
    return resolve_static_url(entry.url, entry.version_regex)


# --------------------------------------------------------------------------
# Version comparison
# --------------------------------------------------------------------------

# "1.1.0-beta.2", "2.0rc1", "0.9.0_alpha" ... -> base "1.1.0", pre "beta.2"
_PRERELEASE_RE = re.compile(
    r"^(?P<base>.*?\d)[-_.]?(?P<pre>(?:alpha|beta|rc|pre|preview|dev)(?![a-z]).*)$",
    re.IGNORECASE,
)


def _split_prerelease(v: str) -> tuple[str, Optional[str]]:
    m = _PRERELEASE_RE.match(v.strip())
    if m:
        return m.group("base"), m.group("pre")
    return v.strip(), None


def _dpkg_form(v: str) -> str:
    """Rewrite '1.1.0-beta.1' as '1.1.0~beta.1' so dpkg sorts it *before*
    1.1.0. Without this, dpkg reads '-beta.1' as a Debian revision, which
    makes the pre-release look newer than the final release."""
    base, pre = _split_prerelease(v)
    return f"{base}~{pre}" if pre else v


def _py_compare_key(v: str):
    base, pre = _split_prerelease(v)
    nums = tuple(int(p) for p in re.findall(r"\d+", base))
    if not nums:
        return None
    if pre is None:
        return (nums, 1, ())
    return (nums, 0, tuple(int(p) for p in re.findall(r"\d+", pre)))


def is_newer(new_version: str, old_version: Optional[str]) -> bool:
    """Best-effort version comparison. Prefers dpkg for deb-style strings
    (with pre-release tags normalised so 1.1.0-rc1 < 1.1.0), falls back to a
    pure-Python compare, falls back to string inequality."""
    if not old_version:
        return True
    if new_version == old_version:
        return False

    try:
        result = subprocess.run(
            ["dpkg", "--compare-versions", _dpkg_form(new_version), "gt", _dpkg_form(old_version)],
            capture_output=True, env=host_env(),
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        pass

    nk, ok = _py_compare_key(new_version), _py_compare_key(old_version)
    if nk is not None and ok is not None:
        return nk > ok

    return new_version != old_version
