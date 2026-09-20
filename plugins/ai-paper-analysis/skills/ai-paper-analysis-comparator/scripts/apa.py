#!/usr/bin/env python3
"""Shared-tool launcher for ai-paper-analysis-comparator; no sibling Skill is required."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

skill_root = Path(__file__).resolve().parents[1]
if configured := os.environ.get("APA_CACHE_DIR"):
    cache = Path(configured).expanduser()
elif os.name == "nt":
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    cache = base / "ai-paper-analysis"
elif sys.platform == "darwin":
    cache = Path.home() / "Library" / "Caches" / "ai-paper-analysis"
else:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ai-paper-analysis"
pointer = skill_root / ".apa-runtime.json"
if not pointer.is_file():
    pointer = cache / "active.json"
try:
    record = json.loads(pointer.read_text(encoding="utf-8"))
    python, entrypoint = record["python"], record["entrypoint"]
    if not Path(python).is_file() or not Path(entrypoint).is_file():
        raise ValueError("Shared runtime is missing")
except (OSError, ValueError, KeyError, TypeError):
    print("Run the repository installer: python scripts/install.py"
          " --skill ai-paper-analysis-comparator", file=sys.stderr)
    raise SystemExit(1) from None

environment = os.environ.copy()
environment.pop("APA_SKILL_COMMANDS", None)
environment.update(record["environment"])
os.execve(python, [python, entrypoint, *sys.argv[1:]], environment)
