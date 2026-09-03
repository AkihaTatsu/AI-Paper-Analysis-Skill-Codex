#!/usr/bin/env python3
"""Run the deterministic local pre-release gate with concise diagnostics."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = tuple(sorted((ROOT / "skills").glob("ai-paper-analysis*")))


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    detail: str = ""
    optional: bool = False


def _executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"Required executable is unavailable: {name}")
    return executable


def _run(
    name: str,
    command: list[str],
    log_root: Path,
    *,
    environment: dict[str, str] | None = None,
    optional: bool = False,
) -> Result:
    log = log_root / f"{len(tuple(log_root.iterdir())):02d}-{name.replace(' ', '-')}.log"
    with log.open("w", encoding="utf-8", newline="\n") as stream:
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if process.returncode == 0:
        return Result(name, True, optional=optional)
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    detail = "\n".join(lines[-20:]) or f"exit code {process.returncode}"
    return Result(name, False, detail, optional)


def _python_in(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _deterministic_steps(temporary: Path) -> list[Result]:
    uv = _executable("uv")
    npm = _executable("npm")
    node = _executable("node")
    logs = temporary / "logs"
    logs.mkdir()
    results: list[Result] = []

    results.append(_run("root lock", [uv, "lock", "--check"], logs))
    for skill in SKILLS:
        results.append(
            _run(
                f"lock {skill.name}",
                [uv, "lock", "--check", "--project", str(skill)],
                logs,
            )
        )
    results.append(
        _run(
            "development environment",
            [uv, "sync", "--extra", "dev", "--frozen"],
            logs,
        )
    )
    results.extend(
        (
            _run(
                "materialized sync",
                [uv, "run", "python", "scripts/sync_materialized.py", "--check"],
                logs,
            ),
            _run("tests", [uv, "run", "pytest", "-m", "not live"], logs),
            _run("ruff", [uv, "run", "ruff", "check", "."], logs),
            _run("mypy", [uv, "run", "mypy", "src"], logs),
            _run(
                "repository validation",
                [uv, "run", "python", "scripts/validate_repository.py"],
                logs,
            ),
            _run("node install", [npm, "ci", "--ignore-scripts"], logs),
            _run("markdownlint", [npm, "run", "lint:markdown"], logs),
            _run("Mermaid parser", [npm, "run", "test:mermaid-syntax"], logs),
        )
    )

    renderer_environment = os.environ.copy()
    try:
        from ai_paper_analysis.tooling import prepare_renderer

        renderer_environment.update(prepare_renderer(ROOT))
        renderer_root = Path(renderer_environment["APA_RENDERER_ROOT"])
        renderer = renderer_root / "scripts" / "render_report.mjs"
        renderer_environment["APA_PYTHON"] = sys.executable
        for template in ("paper-report.md", "category-report.md"):
            results.append(
                _run(
                    f"render {template}",
                    [node, str(renderer), str(ROOT / "templates" / template)],
                    logs,
                    environment=renderer_environment,
                )
            )
    except Exception as error:
        results.append(Result("renderer bootstrap", False, str(error)))

    site = temporary / "mkdocs-site"
    results.append(
        _run(
            "MkDocs strict",
            [uv, "run", "mkdocs", "build", "--strict", "--site-dir", str(site)],
            logs,
        )
    )

    distribution = temporary / "dist"
    results.append(_run("build distributions", [uv, "build", "--out-dir", str(distribution)], logs))
    wheels = sorted(distribution.glob("*.whl"))
    if len(wheels) != 1:
        results.append(Result("isolated wheel", False, "build did not produce exactly one wheel"))
        return results
    isolated = temporary / "wheel-environment"
    result = _run(
        "isolated environment",
        [uv, "venv", "--python", sys.executable, str(isolated)],
        logs,
    )
    results.append(result)
    if result.passed:
        isolated_python = _python_in(isolated)
        install = _run(
            "isolated wheel install",
            [uv, "pip", "install", "--python", str(isolated_python), str(wheels[0])],
            logs,
        )
        results.append(install)
        if install.passed:
            results.append(
                _run(
                    "isolated wheel smoke",
                    [str(isolated_python), "-m", "ai_paper_analysis.cli", "providers"],
                    logs,
                )
            )
    return results


def _live_steps(temporary: Path) -> list[Result]:
    uv = _executable("uv")
    logs = temporary / "live-logs"
    logs.mkdir()
    results: list[Result] = []
    for provider in ("crossref", "openalex", "arxiv"):
        output = temporary / f"{provider}.json"
        results.append(
            _run(
                f"live {provider}",
                [
                    uv,
                    "run",
                    "ai-paper-analysis-runtime",
                    "discover",
                    provider,
                    "causal representation learning",
                    str(output),
                    "--limit",
                    "1",
                ],
                logs,
                optional=True,
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also smoke-test public providers")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="ai-paper-analysis-release-") as raw:
        temporary = Path(raw)
        try:
            results = _deterministic_steps(temporary)
            if arguments.live:
                results.extend(_live_steps(temporary))
        except RuntimeError as error:
            print(f"FAIL prerequisites: {error}")
            return 1

    for result in results:
        label = "PASS" if result.passed else ("WARN" if result.optional else "FAIL")
        print(f"{label} {result.name}")
        if not result.passed and result.detail:
            print(result.detail)
    failures = [result for result in results if not result.passed and not result.optional]
    warnings = [result for result in results if not result.passed and result.optional]
    print(
        f"Summary: {len(results) - len(failures) - len(warnings)} passed, "
        f"{len(failures)} failed, {len(warnings)} live warnings."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
