"""English CLI shared by the package and capability-scoped Skill entrypoints."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, NoReturn, TypeVar

import typer

from .constants import DEFAULT_NETWORK

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
Command = TypeVar("Command", bound=Callable[..., object])


def _allowed_commands() -> set[str] | None:
    configured = os.environ.get("APA_SKILL_COMMANDS")
    return {value for value in configured.split(",") if value} if configured else None


def _register(name: str) -> Callable[[Command], Command]:
    """Register commands included by the current capability-scoped Skill."""

    allowed = _allowed_commands()
    if allowed is not None and name not in allowed:
        return lambda function: function
    return app.command(name)


def _emit(payload: object) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _fail(kind: str, error: Exception) -> NoReturn:
    _emit({"error": {"kind": kind, "message": " ".join(str(error).split())[:500]}})
    raise typer.Exit(1)


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise typer.BadParameter("Expected a JSON object")
    return payload


def _ensure_renderer() -> None:
    if os.environ.get("APA_RENDERER_ROOT"):
        return
    from .tooling import ToolBootstrapError, prepare_renderer

    try:
        os.environ.update(prepare_renderer())
    except ToolBootstrapError as error:
        _fail("renderer-bootstrap", error)


@_register("providers")
def list_providers() -> None:
    """List the finite built-in provider registry."""

    from .providers import provider_registry

    _emit({"schema_version": "1.0.0", "providers": list(provider_registry().values())})


@_register("validate-spec")
def validate_spec_command(spec: Path, require_confirmation: bool = True) -> None:
    """Validate a run specification and its confirmation state."""

    from .run_spec import validate_run_spec

    validation = validate_run_spec(_load_object(spec), require_confirmation=require_confirmation)
    _emit({"valid": validation.valid, "errors": validation.errors})
    if not validation.valid:
        raise typer.Exit(1)


@_register("init-run")
def init_run(spec: Path) -> None:
    """Create the minimal persistent state for one confirmed specification."""

    from .artifacts import ensure_target_layout, write_json_atomic
    from .run_spec import load_confirmed_run_spec

    payload = load_confirmed_run_spec(spec)
    paths = ensure_target_layout(Path(payload["target_root"]), payload["run_id"])
    write_json_atomic(paths["run_root"] / "run-spec.json", payload)
    write_json_atomic(
        paths["run_root"] / "status.json",
        {
            "schema_version": "1.0.0",
            "run_id": payload["run_id"],
            "status": "active",
            "updated_at": payload["approved_at"],
        },
    )
    _emit({name: str(path) for name, path in paths.items()})


@_register("discover")
def discover_command(
    provider: str,
    query: str,
    output: Path,
    limit: int = 20,
    timeout_seconds: int = DEFAULT_NETWORK["timeout_seconds"],
    max_retries: int = DEFAULT_NETWORK["max_retries"],
    credentials_file: Path | None = None,
    target_root: Path | None = None,
) -> None:
    """Discover candidates through one deterministic public or configured API."""

    from .credentials import CredentialError
    from .credentials import credentials_file as resolve_file
    from .providers import ProviderError, discover, write_candidates

    configured = resolve_file(explicit=credentials_file, target_root=target_root)
    try:
        candidates = discover(
            provider,
            query,
            limit=limit,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            credentials_file=configured,
        )
    except CredentialError as error:
        _fail("credential", error)
    except ProviderError as error:
        _fail("provider", error)
    write_candidates(output, candidates)
    _emit({"provider": provider, "count": len(candidates), "output": str(output)})


@_register("create-temp")
def create_temp_command(run_id: str) -> None:
    """Create one strictly scoped system-temporary run workspace."""

    from .temporary import create_temporary_workspace

    workspace = create_temporary_workspace(run_id)
    _emit({"temporary_workspace": str(workspace)})


@_register("cleanup-temp")
def cleanup_temp_command(workspace: Path) -> None:
    """Remove one recognized system-temporary run workspace."""

    from .temporary import remove_temporary_workspace

    deleted = remove_temporary_workspace(workspace)
    _emit({"temporary_workspace": str(workspace.resolve()), "deleted_files": deleted})


@_register("download-pdf")
def download_pdf_command(
    url: str,
    destination: Path,
    timeout_seconds: int = DEFAULT_NETWORK["timeout_seconds"],
    max_retries: int = DEFAULT_NETWORK["max_retries"],
    max_pdf_mib: int = DEFAULT_NETWORK["max_pdf_mib"],
) -> None:
    """Download a bounded staged PDF from an approved URL."""

    from .pdf import PdfValidationError, download_pdf

    try:
        result = download_pdf(
            url,
            destination,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            max_pdf_mib=max_pdf_mib,
        )
    except (PdfValidationError, ValueError) as error:
        _fail("pdf-download", error)
    _emit({"path": str(result)})


@_register("validate-pdf")
def validate_pdf_command(
    pdf: Path,
    expected_title: str | None = None,
    expected_doi: str | None = None,
    max_pdf_mib: int = DEFAULT_NETWORK["max_pdf_mib"],
) -> None:
    """Run structural and identity preflight on a staged PDF."""

    from .pdf import validate_pdf

    audit = validate_pdf(
        pdf,
        expected_title=expected_title,
        expected_doi=expected_doi,
        max_pdf_mib=max_pdf_mib,
    )
    _emit(audit.to_dict())
    if not audit.valid:
        raise typer.Exit(1)


@_register("artifact-name")
def artifact_name(
    title: str,
    first_author: str,
    year: str,
    doi: str = "",
    arxiv_id: str = "",
    native_id: str = "",
) -> None:
    """Build a stable paper ID and paired artifact stem."""

    from .identifiers import artifact_stem, stable_paper_id

    paper_id = stable_paper_id(doi=doi, arxiv_id=arxiv_id, native_id=native_id)
    _emit(
        {
            "paper_id": paper_id,
            "stem": artifact_stem(
                year=year,
                first_author=first_author,
                title=title,
                paper_id=paper_id,
            ),
        }
    )


@_register("publish")
def publish(source: Path, destination: Path) -> None:
    """Atomically publish one already validated artifact without overwriting."""

    from .artifacts import atomic_publish

    result = atomic_publish(source, destination)
    _emit({"destination": str(result.destination)})


@_register("promote-revision")
def promote_revision(
    current: Path,
    candidate: Path,
    archive_root: Path,
    archive_retention: int = 1,
) -> None:
    """Archive and atomically promote an approved formal-artifact revision."""

    from .artifacts import archive_and_promote

    result = archive_and_promote(
        current,
        candidate,
        archive_root,
        archive_retention=archive_retention,
    )
    _emit({"destination": str(result.destination), "archive_retention": archive_retention})


@_register("record-state")
def record_state_command(
    target_root: Path,
    artifact: Path,
    artifact_kind: str,
    run_id: str,
    sources: Annotated[list[Path] | None, typer.Option("--source")] = None,
) -> None:
    """Record paths for one published formal artifact."""

    from .artifacts import record_artifact_state

    state_path = record_artifact_state(
        target_root,
        artifact,
        artifact_kind=artifact_kind,
        run_id=run_id,
        sources=tuple(sources or ()),
    )
    _emit({"state": str(state_path)})


@_register("validate-classification")
def validate_classification_command(
    csv_path: Path,
    taxonomy_path: Path,
    target_root: Path | None = None,
    comparison_ready: bool = False,
) -> None:
    """Validate CSV, taxonomy, paths, and comparison eligibility."""

    from .classification import validate_classification

    audit = validate_classification(
        csv_path,
        taxonomy_path,
        target_root=target_root,
        require_comparison_ready=comparison_ready,
    )
    _emit(audit.__dict__)
    if not audit.valid:
        raise typer.Exit(1)


@_register("audit-markdown")
def audit_markdown_command(path: Path, report_kind: str = "generic") -> None:
    """Audit portable Markdown, mathematics, Mermaid, and numbered sections."""

    _ensure_renderer()
    from .markdown_audit import audit_markdown

    audit = audit_markdown(path, report_kind=report_kind)
    _emit(
        {
            "valid": audit.valid,
            "path": audit.path,
            "errors": audit.errors,
            "warnings": audit.warnings,
        }
    )
    if not audit.valid:
        raise typer.Exit(1)


@_register("audit-paper-report")
def audit_paper_report_command(report: Path) -> None:
    """Audit a paper report without encoding content ledgers."""

    _ensure_renderer()
    from .report_audit import audit_paper_report

    audit = audit_paper_report(report)
    _emit(
        {
            "valid": audit.valid,
            "format_status": audit.format_status,
            "content_status": audit.content_status,
            "errors": audit.errors,
            "warnings": audit.markdown.get("warnings", ()),
        }
    )
    if not audit.valid:
        raise typer.Exit(1)


@_register("audit-category-report")
def audit_category_report_command(
    report: Path,
    relationships: Path,
    classification: Path | None = None,
    taxonomy: Path | None = None,
    target_root: Path | None = None,
) -> None:
    """Audit a category report, relationships, and optional comparison inputs."""

    _ensure_renderer()
    from .classification import validate_classification
    from .report_audit import audit_category_report

    audit = audit_category_report(report, relationships)
    classification_valid: bool | None = None
    classification_errors: tuple[str, ...] = ()
    if classification is not None or taxonomy is not None:
        if classification is None or taxonomy is None or target_root is None:
            _fail(
                "arguments",
                ValueError("classification, taxonomy, and target_root must be supplied together"),
            )
        inputs = validate_classification(
            classification,
            taxonomy,
            target_root=target_root,
            require_comparison_ready=True,
        )
        classification_valid = inputs.valid
        classification_errors = inputs.errors
    errors = (*audit.errors, *classification_errors)
    input_ready = audit.valid and classification_valid is not False
    _emit(
        {
            "valid": not errors,
            "format_status": audit.format_status,
            "relationship_valid": audit.relationship_valid,
            "classification_valid": classification_valid,
            "input_ready": input_ready,
            "errors": errors,
            "warnings": audit.markdown.get("warnings", ()),
        }
    )
    if errors:
        raise typer.Exit(1)


@_register("cleanup-run")
def cleanup_run_command(target_root: Path, run_id: str) -> None:
    """Delete one strictly scoped completed run directory."""

    from .cleanup import cleanup_run

    deleted = cleanup_run(target_root, run_id)
    _emit({"run_id": run_id, "deleted_files": deleted})


if __name__ == "__main__":
    app()
