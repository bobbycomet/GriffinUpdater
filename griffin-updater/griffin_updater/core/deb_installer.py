"""
.deb install logic - the generalized version of discord-updater.sh's install step.

Privilege elevation uses pkexec (PolicyKit) instead of raw sudo, so it works
cleanly from a GUI session and pops the standard auth dialog, consistent with
Griffin Persona's elevation model.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import requests

from .version import USER_AGENT, TIMEOUT


class DebInstallError(Exception):
    pass


def get_installed_version(package_name: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", package_name],
            capture_output=True, text=True,
        )
    except FileNotFoundError as exc:
        raise DebInstallError("dpkg-query not found - is this a Debian/Ubuntu system?") from exc
    version = result.stdout.strip()
    return version or None


def download_deb(url: str) -> Path:
    fd, path_str = tempfile.mkstemp(prefix="griffin-updater-", suffix=".deb")
    path = Path(path_str)
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT * 6,
                           headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            with open(fd, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    if chunk:
                        f.write(chunk)
    except requests.RequestException as exc:
        path.unlink(missing_ok=True)
        raise DebInstallError(f"Download failed: {exc}") from exc
    return path


def install_deb(deb_path: Path) -> subprocess.CompletedProcess:
    """Installs via pkexec apt-get install -y <path>, which resolves deps
    (unlike a bare dpkg -i)."""
    try:
        result = subprocess.run(
            ["pkexec", "apt-get", "install", "-y", str(deb_path)],
            capture_output=True, text=True,
        )
    except FileNotFoundError as exc:
        raise DebInstallError("pkexec not found - install policykit-1.") from exc
    finally:
        deb_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise DebInstallError(
            f"apt-get install failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result


def get_deb_package_name(deb_path: Path) -> Optional[str]:
    """Reads the real 'Package:' field out of the .deb's control data, so we
    can tell the user when their configured package_name doesn't match what
    dpkg will actually register it as (the #1 cause of 'always reinstalls',
    since dpkg-query against the wrong name always comes back empty)."""
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", str(deb_path), "Package"], capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    name = result.stdout.strip()
    return name or None


def get_deb_version(deb_path: Path) -> Optional[str]:
    """Reads the real 'Version:' field out of the .deb's control data. This
    can drift from the GitHub release tag if a project forgets to bump its
    control file / changelog version when cutting a release - in which case
    trusting the tag alone would cause an endless reinstall loop."""
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", str(deb_path), "Version"], capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    version = result.stdout.strip()
    return version or None


def check_and_install(entry, resolved) -> tuple[bool, str]:
    """Returns (did_install, message)."""
    current = get_installed_version(entry.effective_package_name())
    from .version import is_newer

    if current and not is_newer(resolved.version, current):
        return False, f"{entry.name} is already up to date ({current})."

    deb_path = download_deb(resolved.download_url)
    real_pkg_name = get_deb_package_name(deb_path)
    real_deb_version = get_deb_version(deb_path)

    mismatch_note = ""
    if real_pkg_name and real_pkg_name != entry.effective_package_name():
        mismatch_note = (
            f" NOTE: configured package_name '{entry.effective_package_name()}' doesn't "
            f"match this .deb's actual package name '{real_pkg_name}' - dpkg will never "
            f"find it under the configured name, so every check will look like a fresh "
            f"install. Edit this app and set Package name to '{real_pkg_name}' to fix it."
        )

    # The release tag (resolved.version) can drift from what the .deb's own
    # control file claims, if a build forgot to bump it. If the file we just
    # downloaded already matches what's installed, stop here instead of
    # reinstalling the identical package forever.
    if real_deb_version and current and not is_newer(real_deb_version, current):
        deb_path.unlink(missing_ok=True)
        return False, (
            f"{entry.name} is already up to date ({current}). NOTE: the upstream "
            f"release is tagged '{resolved.version}' but the .deb itself is still "
            f"built as version '{real_deb_version}' - its control file/changelog "
            f"version wasn't bumped to match the release tag, so this will keep "
            f"looking 'outdated' by tag until that's fixed upstream."
        )

    install_result = install_deb(deb_path)

    verify_name = real_pkg_name or entry.effective_package_name()
    post_version = get_installed_version(verify_name)
    if post_version:
        verify_note = f" (confirmed: dpkg now shows {verify_name} = {post_version}.)"
        if real_deb_version and real_deb_version != resolved.version:
            verify_note += (
                f" NOTE: release tag says '{resolved.version}' but the .deb's own "
                f"version is '{real_deb_version}' - bump the control file/changelog "
                f"version to match the tag on your next release, or this will keep "
                f"reinstalling every check."
            )
    else:
        apt_output = (install_result.stdout + install_result.stderr).strip()
        snippet = apt_output[-300:] if apt_output else "(apt-get produced no output)"
        verify_note = (
            f" WARNING: apt-get reported success, but dpkg-query still can't find "
            f"'{verify_name}' installed right afterward. This usually means the "
            f"install didn't actually complete (missing dependencies, a postinst "
            f"script error, architecture mismatch, or the package removing/purging "
            f"itself). apt-get's own output (last 300 chars): {snippet}"
        )

    return True, f"{entry.name} updated to {resolved.version}.{mismatch_note}{verify_note}"
