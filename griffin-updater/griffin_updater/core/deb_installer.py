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


def install_deb(deb_path: Path) -> None:
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


def check_and_install(entry, resolved) -> tuple[bool, str]:
    """Returns (did_install, message)."""
    current = get_installed_version(entry.effective_package_name())
    from .version import is_newer

    if current and not is_newer(resolved.version, current):
        return False, f"{entry.name} is already up to date ({current})."

    deb_path = download_deb(resolved.download_url)
    install_deb(deb_path)
    return True, f"{entry.name} updated to {resolved.version}."
