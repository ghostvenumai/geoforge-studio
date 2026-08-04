from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
ALLOWED_EXTENSIONS = {".csv", ".json", ".jsonl", ".ndjson", ".parquet", ".xlsx"}


def sanitize_filename(filename: str) -> str:
    """Return a display-safe basename without traversal or control characters."""
    basename = Path(filename.replace("\\", "/")).name
    normalized = unicodedata.normalize("NFKC", basename)
    cleaned = "".join(char for char in normalized if unicodedata.category(char) != "Cc")
    cleaned = SAFE_FILENAME.sub("_", cleaned).strip("._")
    if not cleaned:
        cleaned = "upload"
    stem = Path(cleaned).stem[:100] or "upload"
    suffix = Path(cleaned).suffix.lower()[:16]
    return f"{stem}{suffix}"


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed extensions: {allowed}")
    return suffix.lstrip(".")


def ensure_contained(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("Path escapes the configured storage root")
    return resolved_path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def protect_spreadsheet_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
