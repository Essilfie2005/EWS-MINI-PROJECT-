"""
Anonymisation utilities – SHA-256 salted hashing for student IDs.
"""

from __future__ import annotations

import hashlib

from app.config import get_settings


def hash_student_id(raw_id: str, salt: str | None = None) -> str:
    """
    Produce a deterministic SHA-256 hex digest from a student ID + salt.

    Parameters
    ----------
    raw_id : str
        Original student identifier (e.g. "STU-20240012").
    salt : str, optional
        Override salt; defaults to ``settings.HASH_SALT``.

    Returns
    -------
    str
        64-character lowercase hex digest.
    """
    if salt is None:
        salt = get_settings().HASH_SALT
    payload = f"{salt}:{raw_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def mask_id(anon_id: str, visible: int = 8) -> str:
    """
    Return a partially masked version of an anon_id for display.

    Example
    -------
    >>> mask_id("abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    'abcdef12...67890'
    """
    if len(anon_id) <= visible * 2:
        return anon_id
    return f"{anon_id[:visible]}...{anon_id[-5:]}"
