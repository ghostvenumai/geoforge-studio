from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from geoforge.core.security import (
    ensure_contained,
    protect_spreadsheet_cell,
    sanitize_filename,
    sha256_file,
    validate_extension,
)


@given(st.text(min_size=1))
def test_sanitized_filename_is_always_a_basename(value: str) -> None:
    result = sanitize_filename(value)
    assert Path(result).name == result
    assert "/" not in result and "\\" not in result
    assert result not in {"", ".", ".."}


def test_path_traversal_is_removed() -> None:
    assert sanitize_filename("../../secret.csv") == "secret.csv"
    assert sanitize_filename("..\\..\\secret.csv") == "secret.csv"


def test_extension_allowlist() -> None:
    assert validate_extension("data.parquet") == "parquet"
    with pytest.raises(ValueError, match="Unsupported"):
        validate_extension("payload.py")


def test_containment_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    assert ensure_contained(root / "file", root) == (root / "file").resolve()
    with pytest.raises(ValueError, match="escapes"):
        ensure_contained(root / ".." / "private", root)


@pytest.mark.parametrize("value", ["=1+1", "+SUM(A1)", "-2+3", "@cmd", "\tformula"])
def test_spreadsheet_formula_injection_is_neutralized(value: str) -> None:
    assert protect_spreadsheet_cell(value) == "'" + value


def test_sha256_is_repeatable(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"geoforge")
    assert sha256_file(path) == hashlib.sha256(b"geoforge").hexdigest()
