from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_paper_analysis.cli import app
from ai_paper_analysis.run_spec import (
    UnconfirmedRunSpecError,
    load_confirmed_run_spec,
    validate_run_spec,
)


def valid_spec(tmp_path: Path) -> dict[str, object]:
    spec: dict[str, object] = {
        "schema_version": "2.0.0",
        "run_id": "20260828T010203Z-abcdef12",
        "workflows": ["finder"],
        "target_root": str(tmp_path),
        "output_language": "English",
        "finder": {
            "research_topic": "portable research fixtures",
            "inclusion_criteria": ["Contains a complete method"],
            "exclusion_criteria": ["Metadata-only record"],
            "bounds": {
                "date_from": None,
                "date_to": None,
                "languages": [],
                "paper_types": [],
            },
            "providers": ["crossref", "openalex"],
            "access_mode": "public_only",
            "stop_policy": {
                "mode": "target_count",
                "target_accepted": 2,
                "candidate_cap": 10,
            },
            "classification_requested": False,
            "ocr": "ask_if_needed",
            "keep_staging": False,
            "network_defaults": {
                "per_host_concurrency": 2,
                "timeout_seconds": 60,
                "max_retries": 3,
                "max_pdf_mib": 200,
            },
            "credential_sources": ["environment", "browser_session", "sops_age"],
        },
        "subagents_authorized": False,
        "revision_mode": "none",
        "plan_confirmed": True,
        "approved_at": "2026-08-28T01:02:03Z",
    }
    return spec


def test_confirmed_spec_round_trip(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    validation = validate_run_spec(spec)
    assert validation.valid, validation.errors
    path = tmp_path / "run-spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    loaded = load_confirmed_run_spec(path)
    assert loaded["run_id"] == spec["run_id"]
    assert loaded["execution_preferences"] == {
        "draft_model_policy": "fastest_suitable",
        "evidence_cache": "project",
    }


def test_execution_preferences_are_optional_and_reject_unknown_values(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    assert validate_run_spec(spec).valid
    spec["execution_preferences"] = {
        "draft_model_policy": "fastest_suitable",
        "evidence_cache": "disabled",
    }
    assert validate_run_spec(spec).valid
    preferences = spec["execution_preferences"]
    assert isinstance(preferences, dict)
    preferences["draft_model_policy"] = "hard-coded-model"
    assert not validate_run_spec(spec).valid


def test_unconfirmed_spec_is_rejected(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["plan_confirmed"] = False
    validation = validate_run_spec(spec)
    assert not validation.valid
    path = tmp_path / "run-spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(UnconfirmedRunSpecError):
        load_confirmed_run_spec(path)


def test_draft_can_be_checked_but_cannot_start_execution(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["plan_confirmed"] = False
    spec.pop("approved_at")
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    runner = CliRunner()
    checked = runner.invoke(app, ["validate-spec", str(path), "--no-require-confirmation"])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["valid"]
    assert runner.invoke(app, ["init-run", str(path)]).exit_code != 0
    assert not (tmp_path / ".ai-paper-analysis").exists()


def test_confirmed_plan_requires_approval_time(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec.pop("approved_at")
    validation = validate_run_spec(spec)
    assert not validation.valid
    assert any("approved_at" in error for error in validation.errors)


def interpreter_settings() -> dict[str, object]:
    return {
        "future_work_budget": {"mode": "none"},
        "analogy_scenario": "A cook follows written recipes in a kitchen.",
        "source_limitation_policy": "target_characterization_only",
        "ocr": "disabled",
    }


def test_one_confirmation_starts_combined_workflows_with_deferred_facts(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["workflows"] = ["finder", "interpreter", "comparator"]
    spec["interpreter"] = interpreter_settings()
    spec["comparator"] = {
        "classification_path": str(tmp_path / "classification.csv"),
        "taxonomy_path": str(tmp_path / "taxonomy.json"),
        "category_selection": ["methods"],
        "everyday_scenario": "A cook follows written recipes in a kitchen.",
    }
    path = tmp_path / "accepted-plan.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    result = CliRunner().invoke(app, ["init-run", str(path)])
    assert result.exit_code == 0, result.output
    saved = tmp_path / ".ai-paper-analysis" / "runs" / str(spec["run_id"]) / "run-spec.json"
    assert json.loads(saved.read_text())["workflows"] == spec["workflows"]

    # Derived inputs can be recorded without changing the accepted scope or approval.
    settings = spec["interpreter"]
    assert isinstance(settings, dict)
    settings.update(input_refs=["doi:10.1000/target"], novelty_comparison_refs=[])
    assert validate_run_spec(spec).valid


def test_interpretation_without_discovery_requires_target_inputs(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["workflows"] = ["interpreter"]
    spec.pop("finder")
    settings = interpreter_settings()
    spec["interpreter"] = settings
    assert not validate_run_spec(spec).valid
    settings["input_refs"] = ["doi:10.1000/target"]
    assert validate_run_spec(spec).valid


def test_old_staged_spec_is_rejected(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["schema_version"] = "1.0.0"
    spec["approval_stage"] = "target_acquisition"
    spec["question_tool_confirmed"] = spec.pop("plan_confirmed")
    assert not validate_run_spec(spec).valid


def test_init_run_writes_only_minimal_persistent_run_files(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    path = tmp_path / "approved-spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")

    result = CliRunner().invoke(app, ["init-run", str(path)])

    assert result.exit_code == 0, result.output
    run_root = tmp_path / ".ai-paper-analysis" / "runs" / str(spec["run_id"])
    assert (run_root / "run-spec.json").is_file()
    assert (run_root / "status.json").is_file()
    assert (run_root / "candidates").is_dir()
    assert not (run_root / "staging").exists()
    assert not (run_root / "revision").exists()
    assert {path.suffix for path in run_root.rglob("*") if path.is_file()} == {".json"}


def test_retained_staging_requires_visible_absolute_destination(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    finder = spec["finder"]
    assert isinstance(finder, dict)
    finder["keep_staging"] = True
    finder["staging_output_dir"] = str(tmp_path / ".ai-paper-analysis" / "staging")
    hidden_validation = validate_run_spec(spec)
    assert not hidden_validation.valid
    assert "staging_output_dir must be outside .ai-paper-analysis" in hidden_validation.errors

    finder["staging_output_dir"] = str(tmp_path / "retained-staging")
    visible_validation = validate_run_spec(spec)
    assert visible_validation.valid, visible_validation.errors


def test_plan_requires_workflow_specific_settings(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["workflows"] = ["interpreter"]
    spec.pop("finder")
    validation = validate_run_spec(spec)
    assert not validation.valid
    assert any("interpreter" in error for error in validation.errors)


def test_target_count_cannot_exceed_candidate_cap(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    finder = spec["finder"]
    assert isinstance(finder, dict)
    finder["stop_policy"] = {
        "mode": "target_count",
        "target_accepted": 11,
        "candidate_cap": 10,
    }
    validation = validate_run_spec(spec)
    assert not validation.valid
    assert any("must not exceed" in error for error in validation.errors)


def test_comparator_uses_standard_root_manifest_paths(tmp_path: Path) -> None:
    spec = valid_spec(tmp_path)
    spec["workflows"] = ["comparator"]
    spec.pop("finder")
    spec["comparator"] = {
        "classification_path": str(tmp_path / "nested" / "classification.csv"),
        "taxonomy_path": str(tmp_path / "taxonomy.json"),
        "category_selection": ["methods"],
        "subcategory_assignments": [
            {
                "paper_id": "doi:10.1000/example",
                "category_id": "methods",
                "subcategory_id": "methods-core",
            }
        ],
        "everyday_scenario": "A cook follows written recipes in a kitchen.",
    }

    validation = validate_run_spec(spec)

    assert not validation.valid
    assert any("classification_path" in error for error in validation.errors)
