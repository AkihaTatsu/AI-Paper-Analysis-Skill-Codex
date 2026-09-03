from __future__ import annotations

from pathlib import Path

import pytest

from ai_paper_analysis import credentials
from ai_paper_analysis.cleanup import cleanup_run
from ai_paper_analysis.credentials import CredentialError, credentials_file, resolve_credential


def test_cleanup_removes_only_the_named_run(tmp_path: Path) -> None:
    run = tmp_path / ".ai-paper-analysis" / "runs" / "run-1"
    other = tmp_path / ".ai-paper-analysis" / "runs" / "run-2"
    run.mkdir(parents=True)
    other.mkdir(parents=True)
    (run / "audit.json").write_text("{}", encoding="utf-8")

    assert cleanup_run(tmp_path, "run-1") == 1
    assert not run.exists()
    assert other.exists()


def test_cleanup_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        cleanup_run(tmp_path, "../outside")


def test_environment_credential_has_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_API_KEY", "temporary-value")
    assert resolve_credential("FIXTURE_API_KEY") == "temporary-value"


def test_target_scoped_encrypted_credentials_are_discovered(tmp_path: Path) -> None:
    encrypted = tmp_path / ".ai-paper-analysis" / "credentials.sops.yaml"
    encrypted.parent.mkdir()
    encrypted.write_text("sops: {}\n", encoding="utf-8")

    assert credentials_file(target_root=tmp_path) == encrypted.resolve()


def test_sops_source_requires_both_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    encrypted = tmp_path / "credentials.sops.yaml"
    encrypted.write_text("sops: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        credentials.shutil,
        "which",
        lambda name: "/fixture/sops" if name == "sops" else None,
    )

    with pytest.raises(CredentialError, match="SOPS and age"):
        credentials.decrypt_sops(encrypted)
