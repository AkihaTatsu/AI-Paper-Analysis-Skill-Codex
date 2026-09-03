from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ai_paper_analysis import tooling


def _fake_runtime_run(calls: list[list[str]]):
    def run(command: list[str], *, environment: dict[str, str]) -> None:
        calls.append(command)
        target = Path(environment["UV_PROJECT_ENVIRONMENT"])
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("fixture\n", encoding="utf-8")

    return run


def test_child_then_router_reuses_compatible_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(tooling, "cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(tooling.shutil, "which", lambda name: f"/fixture/{name}")
    monkeypatch.setattr(tooling, "_run", _fake_runtime_run(calls))

    child_python = tooling.prepare_skill_runtime(tmp_path / "finder")
    router_python = tooling.prepare_skill_runtime(tmp_path / "router")

    assert child_python == router_python
    assert len(calls) == 1


def test_concurrent_bootstrap_installs_runtime_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    base_run = _fake_runtime_run(calls)

    def delayed_run(command: list[str], *, environment: dict[str, str]) -> None:
        time.sleep(0.05)
        base_run(command, environment=environment)

    monkeypatch.setattr(tooling, "cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(tooling.shutil, "which", lambda name: f"/fixture/{name}")
    monkeypatch.setattr(tooling, "_run", delayed_run)

    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = list(pool.map(tooling.prepare_skill_runtime, (tmp_path / "a", tmp_path / "b")))

    assert paths[0] == paths[1]
    assert len(calls) == 1


def test_renderer_is_separate_lazy_layer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "renderer-source"
    (source / "scripts").mkdir(parents=True)
    for name in ("package.json", "package-lock.json", ".markdownlint-cli2.yaml"):
        (source / name).write_text("{}\n", encoding="utf-8")
    for name in ("check_mermaid.mjs", "render_report.mjs"):
        (source / "scripts" / name).write_text("// fixture\n", encoding="utf-8")

    commands: list[list[str]] = []
    monkeypatch.setattr(tooling, "cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(tooling.shutil, "which", lambda name: f"/fixture/{name}")
    monkeypatch.setattr(tooling, "_system_browser", lambda: "/fixture/chromium")
    monkeypatch.setattr(
        tooling,
        "_run",
        lambda command, *, environment: commands.append(command),
    )

    first = tooling.prepare_renderer(source)
    (source / "scripts" / "render_report.mjs").write_text(
        "// compatible update\n", encoding="utf-8"
    )
    second = tooling.prepare_renderer(source)

    assert first == second
    assert first["PUPPETEER_EXECUTABLE_PATH"] == "/fixture/chromium"
    assert len(commands) == 1
    assert commands[0][1:3] == ["ci", "--ignore-scripts"]
    renderer_root = Path(second["APA_RENDERER_ROOT"])
    assert (renderer_root / "scripts" / "render_report.mjs").read_text(
        encoding="utf-8"
    ) == "// compatible update\n"


def test_cache_keeps_current_and_one_previous_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "runtime"
    versions = [parent / f"v{number}" for number in range(1, 4)]
    for number, version in enumerate(versions, start=1):
        version.mkdir(parents=True)
        (version / "manifest.json").write_text(
            json.dumps({"kind": "runtime", "api_version": str(number)}),
            encoding="utf-8",
        )
        os.utime(version, (number, number))

    tooling._prune_versions(parent, versions[-1])

    assert not versions[0].exists()
    assert versions[1].exists()
    assert versions[2].exists()
