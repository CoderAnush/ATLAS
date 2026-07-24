"""Filename and payload validation helpers (no I/O heavy analysis)."""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from pathlib import PurePosixPath

from atlas_catalog.domain import (
    ALLOWED_MIMES,
    EXTENSION_TO_FORMAT,
    MAX_ZIP_ENTRIES,
    MAX_ZIP_UNCOMPRESSED_BYTES,
    MAX_ZIP_UNCOMPRESSED_RATIO,
    MIME_BY_EXTENSION,
    SUPPORTED_EXTENSIONS,
    DatasetFormat,
    ValidationError,
)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._()\- ]{0,240}$")
_TRAVERSAL = re.compile(r"(^|[\\/])\.\.([\\/]|$)")


def sanitize_filename(filename: str) -> str:
    """Reject path traversal / control chars and return basename only."""
    if not filename or not filename.strip():
        raise ValidationError("filename is required")
    raw = filename.strip().replace("\\", "/")
    if "\x00" in raw or _TRAVERSAL.search(raw):
        raise ValidationError("malicious filename rejected")
    name = PurePosixPath(raw).name
    if not name or name in {".", ".."}:
        raise ValidationError("malicious filename rejected")
    if not _SAFE_NAME.match(name):
        raise ValidationError("filename contains unsupported characters")
    return name


def extension_of(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(f"unsupported extension: {ext or '(none)'}")
    return ext


def format_of(filename: str) -> DatasetFormat:
    return EXTENSION_TO_FORMAT[extension_of(filename)]


def validate_mime(ext: str, content_type: str | None) -> str:
    expected = MIME_BY_EXTENSION[ext]
    if content_type is None or not content_type.strip():
        return expected
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_MIMES:
        raise ValidationError(f"unsupported mime type: {mime}")
    return mime if mime != "application/octet-stream" else expected


def validate_size(size: int, max_bytes: int) -> None:
    if size <= 0:
        raise ValidationError("empty file rejected")
    if size > max_bytes:
        raise ValidationError(f"file exceeds maximum upload size ({max_bytes} bytes)")


def sha256_fileobj(stream: io.BufferedIOBase, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def detect_text_encoding(sample: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            sample.decode(enc)
            return "utf-8" if enc.startswith("utf-8") else enc
        except UnicodeDecodeError:
            continue
    raise ValidationError("unsupported encoding")


def validate_zip_safety(path_or_bytes: str | bytes) -> None:
    """Detect zip bombs via entry count and compression ratio."""
    opener = (
        zipfile.ZipFile(io.BytesIO(path_or_bytes))
        if isinstance(path_or_bytes, bytes)
        else zipfile.ZipFile(path_or_bytes)
    )
    with opener as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ValidationError("zip bomb suspected: too many entries")
        compressed = sum(i.compress_size for i in infos) or 1
        uncompressed = sum(i.file_size for i in infos)
        if uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise ValidationError("zip bomb suspected: uncompressed size too large")
        if uncompressed / compressed > MAX_ZIP_UNCOMPRESSED_RATIO:
            raise ValidationError("zip bomb suspected: compression ratio too high")
        for info in infos:
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in PurePosixPath(name).parts:
                raise ValidationError("zip contains path traversal entry")
            # Nested member must be a supported dataset if it looks like a data file
            base = PurePosixPath(name).name
            if not base or base.endswith("/"):
                continue
            ext = os.path.splitext(base)[1].lower()
            if ext and ext not in SUPPORTED_EXTENSIONS - {".zip"}:
                # Allow non-data junk only if empty-ish; otherwise reject unknown payloads
                if ext not in {".txt", ".md", ".csv", ".tsv", ".json", ".xlsx", ".parquet"}:
                    if ext not in SUPPORTED_EXTENSIONS:
                        raise ValidationError(f"zip contains unsupported member: {base}")


def sniff_magic(ext: str, head: bytes) -> None:
    """Lightweight corruption checks by magic bytes / structure."""
    if not head:
        raise ValidationError("empty or corrupted file")
    if ext == ".zip" and head[:2] != b"PK":
        raise ValidationError("corrupted zip file")
    if ext == ".xlsx" and head[:2] != b"PK":
        raise ValidationError("corrupted excel file")
    if ext == ".parquet" and head[:4] != b"PAR1":
        # Some writers omit footer-only; require PAR1 magic at start
        raise ValidationError("corrupted parquet file")
    if ext == ".json":
        sample = head.lstrip()
        if not sample or sample[0:1] not in (b"{", b"["):
            raise ValidationError("corrupted or invalid json")
