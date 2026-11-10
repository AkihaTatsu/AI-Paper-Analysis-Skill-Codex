from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from ai_paper_analysis import classification, cli, tooling
from ai_paper_analysis.capabilities import list_tools


def _hide_module(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    original = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *args: None if name == missing else original(name, *args),
    )
    monkeypatch.setattr(
        tooling, "ensure_tools", lambda *args, **kwargs: pytest.fail("no implicit installation")
    )


def test_comparison_ready_reports_missing_capability_before_reading_inputs(monkeypatch) -> None:
    _hide_module(monkeypatch, "markdown_it")
    monkeypatch.setattr(
        classification,
        "validate_classification",
        lambda *args, **kwargs: pytest.fail("must preflight first"),
    )
    result = CliRunner().invoke(
        cli.app, ["validate-classification", "missing.csv", "missing.json", "--comparison-ready"]
    )
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["kind"] == "missing-tools"
    assert error["missing_capabilities"] == ["reports"]
    assert error["repair_command"] == "tools ensure --capability reports"


def test_basic_classification_does_not_require_report_tools(monkeypatch) -> None:
    _hide_module(monkeypatch, "markdown_it")
    monkeypatch.setattr(
        classification,
        "validate_classification",
        lambda *args, **kwargs: SimpleNamespace(valid=True, errors=[], row_count=0),
    )
    result = CliRunner().invoke(cli.app, ["validate-classification", "input.csv", "taxonomy.json"])
    assert result.exit_code == 0, result.exception
    assert json.loads(result.stdout)["valid"]


def test_sources_preflight_covers_yaml_credentials(monkeypatch) -> None:
    _hide_module(monkeypatch, "yaml")
    result = CliRunner().invoke(cli.app, ["providers"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["missing_capabilities"] == ["sources"]


def test_missing_renderer_never_bootstraps_during_task(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("APA_RENDERER_ROOT", raising=False)
    monkeypatch.delenv("PUPPETEER_EXECUTABLE_PATH", raising=False)
    monkeypatch.setattr(tooling, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(
        tooling, "prepare_renderer", lambda *args, **kwargs: pytest.fail("no implicit installation")
    )
    report = tmp_path / "report.md"
    report.write_text("# Report\n")
    result = CliRunner().invoke(cli.app, ["fix-mermaid-direction", str(report)])
    assert result.exit_code == 1
    assert (
        json.loads(result.stdout)["error"]["repair_command"] == "tools ensure --capability reports"
    )


def _compatible_active_renderer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    source = tmp_path / "code"
    renderer = source / "renderer"
    (renderer / "scripts").mkdir(parents=True)
    (source / "uv.lock").write_text("locked requirements")
    for name in (
        "package.json",
        "package-lock.json",
        ".markdownlint-cli2.yaml",
        "scripts/check_mermaid.mjs",
        "scripts/render_report.mjs",
    ):
        (renderer / name).write_text(name)
    record = {
        "api_version": list_tools()["api_version"],
        "lock_digest": hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest()[:20],
        "capabilities": ["core", "reports"],
        "code_root": str(source),
        "environment": {
            "APA_RENDERER_ROOT": str(tmp_path / "installed-renderer"),
            "PUPPETEER_CACHE_DIR": str(tmp_path / "browsers"),
            "PUPPETEER_EXECUTABLE_PATH": str(tmp_path / "missing-browser"),
            "APA_CODE_ROOT": "must not replace the running source",
        },
        "versions": {
            "python": "other python", "node": "node version", "browser": "browser version"
        },
    }
    monkeypatch.setattr(cli.os, "environ", {"APA_TOOL_VERSIONS": '{"python":"original python"}'})
    monkeypatch.setattr(tooling, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(tooling, "source_root", lambda: source)
    monkeypatch.setattr(tooling, "renderer_source", lambda: renderer)
    monkeypatch.setattr(
        tooling, "ensure_tools", lambda *args, **kwargs: pytest.fail("no implicit installation")
    )
    monkeypatch.setattr(
        cli, "_ensure_renderer", lambda *args, **kwargs: pytest.fail("no premature tool checks")
    )
    (tmp_path / "active.json").write_text(json.dumps(record))
    return record


def test_incremental_reports_hydrates_old_entrypoint_without_checking_browser(
    tmp_path, monkeypatch
) -> None:
    record = _compatible_active_renderer(tmp_path, monkeypatch)
    cli._require_command_capabilities("validate-classification", {"comparison_ready": True})
    assert cli.os.environ["APA_RENDERER_ROOT"] == record["environment"]["APA_RENDERER_ROOT"]
    assert cli.os.environ["PUPPETEER_EXECUTABLE_PATH"].endswith("missing-browser")
    assert "APA_CODE_ROOT" not in cli.os.environ
    assert json.loads(cli.os.environ["APA_TOOL_VERSIONS"]) == {
        "python": "original python", "node": "node version", "browser": "browser version"
    }


@pytest.mark.parametrize("mismatch", ["api_version", "lock_digest", "renderer"])
def test_active_renderer_from_incompatible_version_is_not_adopted(
    tmp_path, monkeypatch, mismatch
) -> None:
    record = _compatible_active_renderer(tmp_path, monkeypatch)
    if mismatch == "renderer":
        other = tmp_path / "other-code"
        (other / "renderer").mkdir(parents=True)
        (other / "renderer" / "package.json").write_text("different version")
        record["code_root"] = str(other)
    else:
        record[mismatch] = "incompatible"
    (tmp_path / "active.json").write_text(json.dumps(record))
    cli._require_command_capabilities("prepare-report", {})
    assert "APA_RENDERER_ROOT" not in cli.os.environ


def test_preparation_keeps_basic_gate_when_installed_browser_is_missing(
    tmp_path, monkeypatch
) -> None:
    _compatible_active_renderer(tmp_path, monkeypatch)
    report = tmp_path / "incomplete.md"
    report.write_text("# Draft\n\n```mermaid\nflowchart LR\n A --> B\n```\n")
    result = CliRunner().invoke(cli.app, ["prepare-report", str(report)])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    stages = {stage["name"]: stage["status"] for stage in payload["stages"]}
    assert stages["basic"] == "failed"
    assert stages["mermaid"] == "passed" and stages["renderer"] == "skipped"
