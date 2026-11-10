from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ai_paper_analysis import installer, tooling
from ai_paper_analysis.capabilities import capability_closure, list_tools, skill_capabilities

ROOT = Path(__file__).resolve().parents[1]


def test_skill_profiles_include_all_prerequisites() -> None:
    registry = list_tools(source_root=ROOT)
    assert set(skill_capabilities(["finder"], registry=registry)) == {
        "core",
        "sources",
        "pdf",
        "classification",
    }
    assert set(skill_capabilities(["comparator"], registry=registry)) == set(
        registry["capabilities"]
    )
    assert {"core", "sources", "pdf", "reports"} <= set(
        skill_capabilities(["interpreter"], registry=registry)
    )
    with pytest.raises(ValueError, match="Unknown"):
        capability_closure(["imaginary"], registry=registry)


def _fake_install(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(tooling.shutil, "which", lambda name: f"/fixture/{name}")

    def run(command, *, environment):
        calls.append(command)
        if command[1] == "venv":
            python = Path(command[-1]) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("fixture")

    monkeypatch.setattr(tooling, "_run", run)
    monkeypatch.setattr(tooling, "_capture", lambda *args, **kwargs: "typer==0.20.0")
    monkeypatch.setattr(
        tooling, "_doctor_record", lambda record, requested: {**record, "valid": True, "errors": []}
    )
    monkeypatch.setattr(
        tooling,
        "prepare_renderer",
        lambda *args, **kwargs: {"APA_RENDERER_ROOT": "/fixture/renderer"},
    )
    monkeypatch.setattr(tooling, "_render_probe", lambda record: None)
    return calls


def test_capability_install_adds_only_missing_groups_and_keeps_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake_install(monkeypatch)
    first = tooling.ensure_tools(["core", "pdf"], source_root=ROOT, cache_dir=tmp_path)
    second = tooling.ensure_tools(["reports"], source_root=ROOT, cache_dir=tmp_path)
    third = tooling.ensure_tools(["core"], source_root=ROOT, cache_dir=tmp_path)
    assert first["python"] == second["python"] == third["python"]
    assert second["installed"] == ["reports"]
    assert set(second["capabilities"]) == {"core", "pdf", "reports"}
    assert third["installed"] == []
    assert sum(command[1] == "venv" for command in calls) == 1
    assert sum(command[1:3] == ["pip", "install"] for command in calls) == 2
    assert all("--exact" not in command for command in calls)


def test_new_lock_keeps_existing_runtime_and_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_install(monkeypatch)
    source = tmp_path / "source"
    for relative, path in tooling._source_files(ROOT).items():
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    cache = tmp_path / "cache"
    first = tooling.ensure_tools(["core"], source_root=source, cache_dir=cache)
    with (source / "uv.lock").open("a") as stream:
        stream.write("\n# new compatible release lock\n")
    second = tooling.ensure_tools(["core"], source_root=source, cache_dir=cache)
    assert first["runtime_root"] != second["runtime_root"]
    assert Path(first["python"]).is_file()
    assert Path(first["entrypoint"]).is_file()
    assert Path(second["entrypoint"]).is_file()


def test_doctor_detects_modified_shared_code(tmp_path: Path) -> None:
    code = tooling._deploy_code(ROOT, tmp_path)
    record = {
        "code_root": str(code),
        "python": sys.executable,
        "capabilities": ["core"],
    }
    (code / "src" / "ai_paper_analysis" / "constants.py").write_text("# changed\n")
    result = tooling._doctor_record(record, ("core",))
    assert not result["valid"]
    assert any("modified" in error for error in result["errors"])
    assert tooling._deploy_code(ROOT, tmp_path) == code
    assert (code / "src" / "ai_paper_analysis" / "constants.py").read_bytes() == (
        ROOT / "src" / "ai_paper_analysis" / "constants.py"
    ).read_bytes()


def test_failed_report_selfcheck_keeps_previous_active_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_install(monkeypatch)
    first = tooling.ensure_tools(["core"], source_root=ROOT, cache_dir=tmp_path)

    def fail(record):
        raise tooling.ToolBootstrapError("browser cannot launch")

    monkeypatch.setattr(tooling, "_render_probe", fail)
    with pytest.raises(tooling.ToolBootstrapError, match="browser cannot launch"):
        tooling.ensure_tools(["reports"], source_root=ROOT, cache_dir=tmp_path)
    active = json.loads((tmp_path / "active.json").read_text())
    assert active["capabilities"] == ["core"]
    assert active["entrypoint"] == first["entrypoint"]


def _fake_tools(tmp_path: Path) -> dict:
    return {
        "valid": True,
        "capabilities": list(list_tools()["capabilities"]),
        "cache_dir": str(tmp_path / "cache"),
        "code_root": str(tmp_path / "code"),
        "python": sys.executable,
        "entrypoint": str(tmp_path / "code" / "apa.py"),
        "environment": {},
        "installed": [],
        "reused": [],
    }


def test_standalone_install_has_pointer_and_no_vendored_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installer, "_installed_plugin", lambda home: False)
    monkeypatch.setattr(installer, "ensure_tools", lambda *args, **kwargs: _fake_tools(tmp_path))
    result = installer.install(skills=["finder"], destination=tmp_path / "home", source=ROOT)
    skill = Path(result["skills"][0])
    assert (skill / "SKILL.md").is_file()
    assert (skill / ".apa-runtime.json").is_file()
    assert not (skill / "scripts" / "_vendor").exists()
    assert result["mode"] == "standalone"


def test_unmanaged_skill_conflict_is_detected_before_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installer, "_installed_plugin", lambda home: False)
    monkeypatch.setattr(
        installer, "ensure_tools", lambda *args, **kwargs: pytest.fail("must not install")
    )
    target = tmp_path / "skills" / "ai-paper-analysis-finder"
    target.mkdir(parents=True)
    (target / "notes.txt").write_text("user content")
    with pytest.raises(tooling.ToolBootstrapError, match="unmanaged"):
        installer.install(skills=["finder"], destination=tmp_path, source=ROOT)
    assert (target / "notes.txt").read_text() == "user content"


def test_plugin_uses_official_cli_and_archives_managed_standalone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installer, "_installed_plugin", lambda home: False)
    monkeypatch.setattr(installer, "ensure_tools", lambda *args, **kwargs: _fake_tools(tmp_path))
    home = tmp_path / "home"
    installer.install(skills=["finder"], destination=home, source=ROOT)
    plugin_root = tmp_path / "official-cache"
    shutil.copytree(ROOT / "plugins" / "ai-paper-analysis", plugin_root)
    calls: list[tuple[str, ...]] = []

    def codex(home, *args):
        calls.append(args)
        if args == ("marketplace", "list"):
            return {"marketplaces": []}
        if args[0] == "add":
            return {"installedPath": str(plugin_root)}
        return {}

    monkeypatch.setattr(installer, "_codex_json", codex)
    result = installer.install(plugin=True, destination=home, source=ROOT)
    assert result["mode"] == "plugin"
    assert ("marketplace", "add", str(ROOT)) in calls
    assert ("add", installer.PLUGIN_ID) in calls
    assert not (home / "skills" / "ai-paper-analysis-finder").exists()
    assert any((home / ".apa-backups").iterdir())
    assert all((Path(path) / ".apa-runtime.json").is_file() for path in result["skills"])


@pytest.mark.installation
@pytest.mark.skipif(
    os.environ.get("APA_RUN_INSTALL_TESTS") != "1", reason="explicit isolated installation test"
)
def test_real_install_increment_and_launch_outside_repository(tmp_path: Path) -> None:
    home = tmp_path / "home"
    cache = tmp_path / "tools"
    first = installer.install(skills=["finder"], destination=home, cache_dir=cache, source=ROOT)
    finder = home / "skills" / "ai-paper-analysis-finder"
    pointer = (finder / ".apa-runtime.json").read_bytes()
    assert "APA_RENDERER_ROOT" not in json.loads(pointer)["environment"]
    second = installer.install(
        skills=["interpreter", "comparator"], destination=home, cache_dir=cache, source=ROOT
    )
    assert first["tools"]["python"] == second["tools"]["python"]
    assert second["tools"]["installed"] == ["reports"]
    assert (finder / ".apa-runtime.json").read_bytes() == pointer
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("APA_", "PUPPETEER_"))
    }
    environment.pop("PYTHONPATH", None)
    launcher = finder / "scripts" / "apa.py"
    result = subprocess.run(
        [sys.executable, str(launcher), "providers"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["providers"]
    report = tmp_path / "report.md"
    shutil.copy2(ROOT / "tests" / "fixtures" / "portable-report.md", report)
    for command in ("prepare-report", "audit-paper-report"):
        checked = subprocess.run(
            [sys.executable, str(launcher), command, str(report)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        assert checked.returncode == 0, checked.stdout + checked.stderr
        payload = json.loads(checked.stdout)
        assert payload["valid"]
        stages = {stage["name"]: stage["status"] for stage in payload["stages"]}
        assert stages["mermaid"] == "passed"
        assert stages["renderer"] == ("pending" if command == "prepare-report" else "passed")
    assert (finder / ".apa-runtime.json").read_bytes() == pointer
    repeated = installer.install(skills=["finder"], destination=home, cache_dir=cache, source=ROOT)
    assert repeated["tools"]["installed"] == []
    assert tooling.doctor_tools(cache_dir=cache)["valid"]
    tools = second["tools"]
    environment.update(tools["environment"])
    renderer = Path(environment["APA_RENDERER_ROOT"]) / "scripts" / "render_report.mjs"
    process = subprocess.run(
        [shutil.which("node"), str(renderer), str(ROOT / "templates" / "paper-report.md")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert process.returncode == 0, process.stderr
    if shutil.which("codex"):
        plugin = installer.install(plugin=True, destination=home, cache_dir=cache, source=ROOT)
        assert plugin["mode"] == "plugin"
        assert not (home / "skills" / "ai-paper-analysis-finder").exists()
        plugin_launcher = Path(plugin["skills"][1]) / "scripts" / "apa.py"
        launched = subprocess.run(
            [sys.executable, str(plugin_launcher), "providers"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert launched.returncode == 0, launched.stderr
        assert json.loads(launched.stdout)["providers"]
