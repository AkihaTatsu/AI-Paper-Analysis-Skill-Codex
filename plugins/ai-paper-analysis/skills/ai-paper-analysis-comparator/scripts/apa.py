#!/usr/bin/env python3
"""Generated capability-scoped entrypoint for ai-paper-analysis-comparator."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = Path(__file__).resolve()
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "_vendor"))

COMMANDS = (
    "validate-spec",
    "init-run",
    "create-temp",
    "cleanup-temp",
    "publish",
    "promote-revision",
    "record-state",
    "validate-classification",
    "audit-markdown",
    "audit-category-report",
    "cleanup-run",
)
RENDERER_COMMANDS = (
    "validate-classification",
    "audit-markdown",
    "audit-category-report",
)

if os.environ.get("APA_BOOTSTRAPPED") != "1":
    from ai_paper_analysis.tooling import reexecute_skill

    reexecute_skill(
        skill_root=SKILL_ROOT,
        entrypoint=ENTRYPOINT,
        skill_name="ai-paper-analysis-comparator",
        commands=COMMANDS,
        renderer_commands=RENDERER_COMMANDS,
    )

os.environ.setdefault("APA_CONTRACTS_DIR", str(SKILL_ROOT / "references" / "contracts"))
os.environ.setdefault("APA_SKILL_COMMANDS", ",".join(COMMANDS))
os.environ.setdefault("APA_SKILL_NAME", "ai-paper-analysis-comparator")

from ai_paper_analysis.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
