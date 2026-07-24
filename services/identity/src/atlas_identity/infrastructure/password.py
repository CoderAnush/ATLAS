"""Password hashing with Argon2."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

PASSWORD_POLICY = (
    "Password must be at least 10 characters and include upper, lower, digit, and symbol."
)


def validate_password_policy(password: str) -> None:
    """Raise ValueError when the password does not meet policy."""
    if len(password) < 10:
        raise ValueError(PASSWORD_POLICY)
    if not re.search(r"[A-Z]", password):
        raise ValueError(PASSWORD_POLICY)
    if not re.search(r"[a-z]", password):
        raise ValueError(PASSWORD_POLICY)
    if not re.search(r"\d", password):
        raise ValueError(PASSWORD_POLICY)
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError(PASSWORD_POLICY)


def hash_password(password: str) -> str:
    """Hash a password with Argon2."""
    validate_password_policy(password)
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True when the password matches the stored hash."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
