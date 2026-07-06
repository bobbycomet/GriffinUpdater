"""
AppImage install logic.

Unlike .deb packages, AppImages aren't registered with dpkg, so "the
installed version" has no OS-level source of truth. We track it ourselves
in state.json (see state.py), keyed by app id, and keep the previous file's
path so it can be deleted once the new one lands.
"""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import requests

from .version import USER_AGENT, TIMEOUT


class AppImageInstallError(Exception):
    pass


def download_appimage(url: str) -> Path:
    fd, path_str = tempfile.mkstemp(prefix="griffin-updater-", suffix=".AppImage")
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
        raise AppImageInstallError(f"Download failed: {exc}") from exc
    return path


def install_appimage(
    tmp_path: Path,
    target_dir: str,
    desired_filename: str,
    resolved_filename: str,
    old_path: str = "",
    delete_old: bool = True,
) -> Path:
    target_dir_p = Path(target_dir).expanduser()
    target_dir_p.mkdir(parents=True, exist_ok=True)

    # Priority: explicit user override > the real filename from the release
    # asset/URL > (last resort) whatever the temp download file was named.
    final_name = desired_filename.strip() or resolved_filename.strip() or tmp_path.name
    final_path = target_dir_p / final_name

    if delete_old and old_path:
        old_p = Path(old_path).expanduser()
        if old_p.exists() and old_p != final_path:
            try:
                old_p.unlink()
            except OSError:
                pass

    tmp_path.replace(final_path)

    # make executable
    st = os.stat(final_path)
    os.chmod(final_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return final_path


def check_and_install(entry, resolved, last_version: str, last_path: str) -> tuple[bool, str, str]:
    """Returns (did_install, message, new_installed_path)."""
    from .version import is_newer

    if last_version and not is_newer(resolved.version, last_version):
        return False, f"{entry.name} is already up to date ({last_version}).", last_path

    tmp_path = download_appimage(resolved.download_url)
    final_path = install_appimage(
        tmp_path,
        entry.appimage_target_dir,
        entry.appimage_filename,
        resolved.filename,
        old_path=last_path,
        delete_old=entry.delete_old_appimage,
    )
    return True, f"{entry.name} updated to {resolved.version}.", str(final_path)
