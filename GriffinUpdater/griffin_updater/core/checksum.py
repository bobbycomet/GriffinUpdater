from __future__ import annotations

import hashlib
from pathlib import Path


class ChecksumMismatchError(Exception):
    pass


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: Path, expected: str) -> None:
    """Raises ChecksumMismatchError (and does NOT delete the file - callers
    decide cleanup) if `expected` is set and doesn't match. No-op if
    `expected` is blank, since checksum pinning is opt-in per app."""
    expected = (expected or "").strip().lower()
    if not expected:
        return
    actual = sha256_of(path)
    if actual != expected:
        raise ChecksumMismatchError(
            f"SHA-256 mismatch: expected {expected}, got {actual}. "
            f"Refusing to install - the file may have changed upstream or been tampered with."
        )
