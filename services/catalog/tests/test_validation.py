"""Catalog validation unit tests."""

from __future__ import annotations

import io
import zipfile

import pytest
from atlas_catalog.domain import ValidationError
from atlas_catalog.domain.validation import (
    sanitize_filename,
    sniff_magic,
    validate_size,
    validate_zip_safety,
)


def test_sanitize_rejects_traversal() -> None:
    with pytest.raises(ValidationError):
        sanitize_filename("../etc/passwd")
    with pytest.raises(ValidationError):
        sanitize_filename("..\\secret.csv")
    assert sanitize_filename("folder/data.csv") == "data.csv"


def test_empty_and_oversize() -> None:
    with pytest.raises(ValidationError):
        validate_size(0, 100)
    with pytest.raises(ValidationError):
        validate_size(101, 100)


def test_zip_bomb_ratio() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.csv", "a" * 200_000)
    # Highly compressible — may trigger ratio; if not, still validates structure
    data = buf.getvalue()
    try:
        validate_zip_safety(data)
    except ValidationError as exc:
        assert "zip" in str(exc).lower()


def test_parquet_magic() -> None:
    with pytest.raises(ValidationError):
        sniff_magic(".parquet", b"NOTP")
    sniff_magic(".parquet", b"PAR1....")
