"""Run-specification validation and confirmation gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import load_json, validate_instance


class UnconfirmedRunSpecError(ValueError):
    """Raised when execution is attempted without a valid confirmation."""


@dataclass(frozen=True)
class RunSpecValidation:
    valid: bool
    errors: tuple[str, ...]


def validate_run_spec(
    spec: dict[str, Any], *, require_confirmation: bool = True
) -> RunSpecValidation:
    """Validate schema and confirmation invariants."""

    errors = validate_instance(spec, "run-spec.schema.json")
    target_root_value = spec.get("target_root")
    if isinstance(target_root_value, str):
        target_root = Path(target_root_value).expanduser()
        if not target_root.is_absolute():
            errors.append("target_root must be an absolute path")

    workflows = spec.get("workflows")
    if isinstance(workflows, list):
        expected_order = [
            name for name in ("finder", "interpreter", "comparator") if name in workflows
        ]
        if workflows != expected_order:
            errors.append("workflows must follow finder, interpreter, comparator order")
        if spec.get("approval_stage") == "target_acquisition" and workflows != ["finder"]:
            errors.append("target_acquisition approval may execute only the finder workflow")

    registry_payload = load_json("provider-registry.json")
    registry = {provider["id"] for provider in registry_payload["providers"]}
    finder = spec.get("finder")
    if isinstance(finder, dict):
        for provider in finder.get("providers", []):
            if provider not in registry:
                errors.append(f"finder.providers contains unknown provider: {provider}")
        stop_policy = finder.get("stop_policy")
        if isinstance(stop_policy, dict) and stop_policy.get("mode") == "target_count":
            target = stop_policy.get("target_accepted")
            cap = stop_policy.get("candidate_cap")
            if isinstance(target, int) and isinstance(cap, int) and target > cap:
                errors.append("finder.stop_policy target_accepted must not exceed candidate_cap")
        if finder.get("classification_requested") is True and (
            not finder.get("taxonomy_id") or not finder.get("taxonomy_version")
        ):
            errors.append(
                "finder taxonomy_id and taxonomy_version are required when "
                "classification is requested"
            )

    interpreter = spec.get("interpreter")
    if isinstance(interpreter, dict):
        budget = interpreter.get("future_work_budget")
        if isinstance(budget, dict) and budget.get("mode") == "search":
            for provider in budget.get("providers", []):
                if provider not in registry:
                    errors.append(
                        "interpreter.future_work_budget.providers contains unknown "
                        f"provider: {provider}"
                    )
            target = budget.get("target_per_direction")
            cap = budget.get("candidate_cap_per_direction")
            if isinstance(target, int) and isinstance(cap, int) and target > cap:
                errors.append(
                    "interpreter.future_work_budget target_per_direction must not exceed "
                    "candidate_cap_per_direction"
                )

    comparator = spec.get("comparator")
    if isinstance(comparator, dict) and isinstance(target_root_value, str):
        root = Path(target_root_value).expanduser().resolve()
        expected_paths = {
            "classification_path": root / "classification.csv",
            "taxonomy_path": root / "taxonomy.json",
        }
        for field, expected in expected_paths.items():
            value = comparator.get(field)
            if isinstance(value, str) and Path(value).expanduser().resolve() != expected:
                errors.append(f"comparator.{field} must be {expected}")

    if (
        isinstance(finder, dict)
        and finder.get("keep_staging") is True
        and isinstance(finder.get("staging_output_dir"), str)
    ):
        staging = Path(finder["staging_output_dir"]).expanduser()
        if not staging.is_absolute():
            errors.append("staging_output_dir must be an absolute path")
        elif isinstance(target_root_value, str):
            hidden = Path(target_root_value).expanduser().resolve() / ".ai-paper-analysis"
            resolved_staging = staging.resolve()
            if resolved_staging == hidden or resolved_staging.is_relative_to(hidden):
                errors.append("staging_output_dir must be outside .ai-paper-analysis")
    if require_confirmation and spec.get("question_tool_confirmed") is not True:
        errors.append("question_tool_confirmed must be true before execution")
    return RunSpecValidation(not errors, tuple(errors))


def load_confirmed_run_spec(path: Path) -> dict[str, Any]:
    """Load a run specification and reject invalid or unconfirmed content."""

    spec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise UnconfirmedRunSpecError("Run specification must be a JSON object")
    validation = validate_run_spec(spec)
    if not validation.valid:
        joined = "\n".join(f"- {error}" for error in validation.errors)
        raise UnconfirmedRunSpecError(f"Run specification is not executable:\n{joined}")
    return spec
