from __future__ import annotations

from pathlib import Path

import pytest

from ai_paper_analysis.temporary import (
    create_temporary_workspace,
    remove_temporary_workspace,
)


def test_temporary_workspace_is_random_and_removable(tmp_path: Path) -> None:
    first = create_temporary_workspace("run-1", temporary_root=tmp_path)
    second = create_temporary_workspace("run-1", temporary_root=tmp_path)
    assert first != second
    assert first.parent == tmp_path.resolve()
    (first / "one-off.mjs").write_text("temporary", encoding="utf-8")
    (first / "instructions.md").write_text("Accepted task constraints", encoding="utf-8")
    nested = first / "sources" / "renders"
    nested.mkdir(parents=True)
    (nested.parent / "paper.pdf").write_bytes(b"temporary source fixture")
    (nested / "page.png").write_bytes(b"temporary render fixture")
    original = tmp_path / "user-paper.pdf"
    original.write_bytes(b"existing user file")
    (second / "instructions.md").write_text("Other task", encoding="utf-8")

    assert remove_temporary_workspace(first, temporary_root=tmp_path) == 4
    assert not first.exists()
    assert (second / "instructions.md").read_text() == "Other task"
    assert original.read_bytes() == b"existing user file"


def test_temporary_cleanup_rejects_unrecognized_directory(tmp_path: Path) -> None:
    unrecognized = tmp_path / "ordinary-directory"
    unrecognized.mkdir()

    with pytest.raises(ValueError, match="unrecognized"):
        remove_temporary_workspace(unrecognized, temporary_root=tmp_path)

    assert unrecognized.exists()
