"""
Archive install logic - for apps distributed as a plain .zip / .tar.xz /
.tar.gz containing a standalone binary (no .deb, no AppImage), e.g. Godot.

Unlike AppImages, these don't come as a single self-contained file: the
archive might contain just one bare executable at its root (Godot's
"standard" build) or a folder with the executable plus supporting files
(Godot's "mono"/.NET build, which needs its GodotSharp/ runtime alongside
it). This installer treats both the same way: extract the whole archive
into a folder, then locate the actual executable inside it.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import requests

from .version import USER_AGENT, TIMEOUT
from .checksum import verify_sha256, ChecksumMismatchError


class ArchiveInstallError(Exception):
    pass


def _guess_suffix(url: str, filename: str) -> str:
    name = (filename or url).lower()
    for suffix in (".tar.xz", ".tar.gz", ".tar.bz2", ".tgz", ".zip"):
        if name.endswith(suffix):
            return suffix
    return ".zip"  # sane default; Godot and most similar tools ship zips


def download_archive(url: str, filename_hint: str = "") -> Path:
    suffix = _guess_suffix(url, filename_hint)
    fd, path_str = tempfile.mkstemp(prefix="griffin-updater-", suffix=suffix)
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
        raise ArchiveInstallError(f"Download failed: {exc}") from exc
    return path


def _extract_zip(archive_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(dest_dir)
        # zipfile doesn't restore Unix permission bits on its own - without
        # this, the extracted Godot binary (or anything else) loses its
        # executable bit and won't run.
        for info in zf.infolist():
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                target = dest_dir / info.filename
                if target.exists():
                    try:
                        os.chmod(target, mode)
                    except OSError:
                        pass


def _extract_tar(archive_path: Path, dest_dir: Path) -> None:
    with tarfile.open(archive_path) as tf:
        tf.extractall(dest_dir, filter="data")


def extract_archive(archive_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = archive_path.name.lower()
    try:
        if name.endswith(".zip"):
            _extract_zip(archive_path, dest_dir)
        elif name.endswith((".tar.xz", ".tar.gz", ".tar.bz2", ".tgz")):
            _extract_tar(archive_path, dest_dir)
        else:
            raise ArchiveInstallError(f"Don't know how to extract {archive_path.name}")
    except (zipfile.BadZipFile, tarfile.TarError) as exc:
        raise ArchiveInstallError(f"Could not extract {archive_path.name}: {exc}") from exc


def find_executable(dest_dir: Path, pattern: str) -> Path:
    """Locates the real binary inside an extracted archive.

    If a pattern is given, it's matched (re.search) against each file's
    name (not full path) - use this for anything where the filename
    changes per version, e.g. r'^Godot_v[\\d.]+-stable(_mono)?_linux' -
    or just r'^Godot' since it only needs to be unambiguous.

    If no pattern is given, falls back to: is there exactly one file with
    an executable bit set? If so, use it. Otherwise, raise with a list of
    candidates so the user can set an explicit pattern.
    """
    all_files = [p for p in dest_dir.rglob("*") if p.is_file()]
    if not all_files:
        raise ArchiveInstallError(f"Archive extracted to {dest_dir} but contained no files.")

    pattern_matched_nothing = False
    if pattern.strip():
        regex = re.compile(pattern.strip())
        matches = [p for p in all_files if regex.search(p.name)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(str(m.relative_to(dest_dir)) for m in matches[:10])
            raise ArchiveInstallError(
                f"Executable pattern '{pattern}' matched {len(matches)} files "
                f"(expected exactly one): {names}. Tighten the pattern."
            )
        # pattern matched nothing - fall through to the exec-bit heuristic
        # below so a slightly-wrong pattern doesn't hard-fail forever, but
        # the eventual error (if that also comes up empty/ambiguous) says
        # so explicitly instead of leaving you to guess why the pattern
        # "didn't work."
        pattern_matched_nothing = True

    executable_candidates = [
        p for p in all_files
        if os.stat(p).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    ]
    if len(executable_candidates) == 1:
        return executable_candidates[0]

    all_names = ", ".join(str(p.relative_to(dest_dir)) for p in all_files[:20])
    pattern_note = (
        f" Your executable pattern '{pattern}' didn't match any extracted "
        f"filename - check it against what's actually in this archive." 
        if pattern_matched_nothing else ""
    )
    raise ArchiveInstallError(
        f"Couldn't uniquely identify the executable in the extracted archive."
        f"{pattern_note} Set (or fix) an 'Executable pattern' on this app. "
        f"Files found: {all_names}"
    )


def install_archive(
    archive_path: Path,
    install_dir: str,
    subdir_name: str,
    executable_pattern: str,
    delete_old: bool,
    symlink_name: str,
    version: str,
) -> tuple[Path, Path, Optional[Path]]:
    """Returns (install_subdir, executable_path, symlink_path_or_None)."""
    base_dir = Path(install_dir).expanduser()
    base_dir.mkdir(parents=True, exist_ok=True)

    folder_name = subdir_name.strip() or archive_path.stem
    if delete_old:
        target_subdir = base_dir / folder_name
        if target_subdir.exists():
            shutil.rmtree(target_subdir, ignore_errors=True)
    else:
        # Keep every version side by side instead of overwriting.
        target_subdir = base_dir / f"{folder_name}-{version}"
        if target_subdir.exists():
            shutil.rmtree(target_subdir, ignore_errors=True)

    extract_archive(archive_path, target_subdir)
    archive_path.unlink(missing_ok=True)

    executable = find_executable(target_subdir, executable_pattern)
    st = os.stat(executable)
    os.chmod(executable, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    symlink_path = None
    if symlink_name.strip():
        symlink_path = base_dir / symlink_name.strip()
        if symlink_path.is_symlink() or symlink_path.exists():
            symlink_path.unlink()
        symlink_path.symlink_to(executable)

    return target_subdir, executable, symlink_path


def check_and_install(
    entry, resolved, last_version: str, last_install_dir: str, last_executable_path: str = ""
) -> tuple[bool, str, str, str]:
    """Returns (did_install, message, new_installed_subdir_path, new_executable_path)."""
    from .version import is_newer

    still_present = bool(last_executable_path) and Path(last_executable_path).expanduser().exists()

    if last_version and still_present and not is_newer(resolved.version, last_version):
        return False, f"{entry.name} is already up to date ({last_version}).", last_install_dir, last_executable_path

    missing_note = ""
    if last_version and not still_present:
        missing_note = (
            f" NOTE: the previously installed executable ('{last_executable_path}') "
            f"is no longer there - reinstalling even though the version tag didn't change."
        )

    archive_path = download_archive(resolved.download_url, resolved.filename)

    try:
        verify_sha256(archive_path, entry.sha256)
    except ChecksumMismatchError as exc:
        archive_path.unlink(missing_ok=True)
        raise ArchiveInstallError(str(exc)) from exc

    target_subdir, executable, symlink_path = install_archive(
        archive_path,
        entry.archive_install_dir,
        entry.archive_subdir_name,
        entry.archive_executable_pattern,
        entry.archive_delete_old,
        entry.archive_symlink_name,
        resolved.version,
    )

    where = str(symlink_path) if symlink_path else str(executable)
    message = f"{entry.name} updated to {resolved.version}. Installed at {where}.{missing_note}"
    return True, message, str(target_subdir), str(executable)
