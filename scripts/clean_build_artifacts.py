#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "frontend" / "dist",
    ROOT / "frontend" / "coverage",
    ROOT / "frontend" / "playwright-report",
    ROOT / "htmlcov",
]
for target in TARGETS:
    if target.exists() and target.resolve().is_relative_to(ROOT):
        shutil.rmtree(target)
