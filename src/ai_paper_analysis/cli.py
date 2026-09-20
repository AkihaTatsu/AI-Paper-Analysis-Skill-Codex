"""English CLI shared by the package and capability-scoped Skill entrypoints."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, NoReturn, TypeVar, cast

import typer

from .constants import DEFAULT_NETWORK

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
tools_app = typer.Typer(no_args_is_help=True)
app.add_typer(tools_app, name="tools")
Command = TypeVar("Command", bound=Callable[..., object])


def _allowed_commands() -> set[str] | None:
    configured = os.environ.get("APA_SKILL_COMMANDS")
    return {value for value in configured.split(",") if value} if configured else None


def _register(name: str) -> Callable[[Command], Command]:
    """Register commands included by the current capability-scoped Skill."""

    allowed = _allowed_commands()
    if allowed is not None and name not in allowed:
        return lambda function: function

    def decorate(function: Command) -> Command:
        @wraps(function)
        def guarded(*args: Any, **kwargs: Any) -> object:
            _require_command_capabilities(name, kwargs)
            return function(*args, **kwargs)

        return cast(Command, app.command(name)(guarded))

    return decorate


def _missing_tools(missing: list[str]) -> NoReturn:
    repair = "tools ensure " + " ".join(f"--capability {name}" for name in missing)
    _emit(
        {
            "error": {
                "kind": "missing-tools",
                "message": "Required shared capabilities are not ready. Run this CLI with: "
                + repair,
                "missing_capabilities": missing,
                "repair_command": repair,
            }
        }
    )
    raise typer.Exit(1)


def _require_command_capabilities(name: str, arguments: dict[str, Any]) -> None:
    from .capabilities import capability_closure, list_tools

    registry = list_tools()
    commands = {
        "providers": ("sources",),
        "discover": ("sources",),
        "download-pdf": ("pdf",),
        "validate-pdf": ("pdf",),
        "read-pdf": ("pdf",),
        "render-pdf-pages": ("pdf",),
        "validate-classification": ("classification",),
        "prepare-report": ("reports",),
        "lookup-evidence-cache": ("core",),
        "record-evidence-cache": ("core",),
        "fix-mermaid-direction": ("reports",),
        "audit-markdown": ("reports",),
        "audit-paper-report": ("reports",),
        "audit-category-report": ("classification", "reports"),
    }
    required = set(commands.get(name, ("core",)))
    if name == "validate-classification" and arguments.get("comparison_ready"):
        required.update(("pdf", "reports"))
    if name == "audit-category-report" and (
        arguments.get("classification") is not None or arguments.get("taxonomy") is not None
    ):
        required.add("pdf")
    missing: list[str] = []
    for capability in capability_closure(required, registry=registry):
        for module in registry["capabilities"][capability]["imports"]:
            try:
                available = importlib.util.find_spec(module) is not None
            except (ImportError, ValueError, AttributeError):
                available = False
            if not available:
                missing.append(capability)
                break
    if missing:
        _missing_tools(missing)
    if "reports" in required:
        _load_compatible_renderer_environment()


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


def _load_compatible_renderer_environment() -> None:
    """Discover an installed capability added after this Skill's fixed pointer.

    Only metadata is read here. Actual tool availability remains the concern of
    the corresponding audit stage, and the running code version never changes.
    """
    if os.environ.get("APA_RENDERER_ROOT"):
        return
    from .capabilities import list_tools
    from .tooling import ToolBootstrapError, _read_json, cache_root, renderer_source, source_root

    record = _read_json(cache_root() / "active.json")
    try:
        source = source_root()
        lock_digest = hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest()[:20]
        if (
            record.get("api_version") != list_tools()["api_version"]
            or record.get("lock_digest") != lock_digest
            or "reports" not in record.get("capabilities", [])
        ):
            return
        expected = renderer_source()
        active_source = Path(record["code_root"]) / "renderer"
        for name in (
            "package.json",
            "package-lock.json",
            ".markdownlint-cli2.yaml",
            "scripts/check_mermaid.mjs",
            "scripts/render_report.mjs",
        ):
            if (expected / name).read_bytes() != (active_source / name).read_bytes():
                return
    except (OSError, ValueError, KeyError, TypeError, ToolBootstrapError):
        return
    environment = record.get("environment", {})
    if not isinstance(environment, dict):
        return
    for key in ("APA_RENDERER_ROOT", "PUPPETEER_CACHE_DIR", "PUPPETEER_EXECUTABLE_PATH"):
        if isinstance(environment.get(key), str):
            os.environ.setdefault(key, environment[key])
    try:
        versions = json.loads(os.environ.get("APA_TOOL_VERSIONS", "{}"))
    except ValueError:
        versions = {}
    if isinstance(versions, dict) and isinstance(record.get("versions"), dict):
        for key in ("node", "browser"):
            if key in record["versions"]:
                versions[key] = record["versions"][key]
        os.environ["APA_TOOL_VERSIONS"] = json.dumps(versions, sort_keys=True)


def _ensure_renderer(*, require_browser: bool = True) -> None:
    _load_compatible_renderer_environment()
    configured = os.environ.get("APA_RENDERER_ROOT", "")
    root = Path(configured)
    browser = Path(os.environ.get("PUPPETEER_EXECUTABLE_PATH", ""))
    if not configured or not (root / "scripts" / "check_mermaid.mjs").is_file() or (
        require_browser and not browser.is_file()
    ):
        _missing_tools(["reports"])


@tools_app.command("list")
def tools_list() -> None:
    """Describe shared capabilities and independent Skill requirements."""
    from .capabilities import list_tools

    _emit(list_tools())


@tools_app.command("ensure")
def tools_ensure(
    capability: Annotated[list[str], typer.Option("--capability")],
    source_root: Path | None = None,
    cache_dir: Path | None = None,
) -> None:
    """Add missing compatible tools and verify readiness."""
    from .tooling import ensure_tools

    try:
        result = ensure_tools(capability, source_root=source_root, cache_dir=cache_dir)
        _emit(result)
        if not result["valid"]:
            raise typer.Exit(1)
    except (OSError, ValueError, RuntimeError) as error:
        _fail("tool-install", error)


@tools_app.command("doctor")
def tools_doctor(
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
    cache_dir: Path | None = None,
) -> None:
    """Check installed tools without treating a stale marker as success."""
    from .tooling import doctor_tools

    result = doctor_tools(capability, cache_dir=cache_dir)
    _emit(result)
    if not result["valid"]:
        raise typer.Exit(1)


@_register("read-pdf")
def read_pdf_command(path: Path, pages: str | None = None, output: Path | None = None) -> None:
    """Read original PDF text with explicit one-based page locators."""
    from .pdf_read import read_pdf

    try:
        result = read_pdf(path, pages=pages)
        if output:
            from .artifacts import write_json_atomic

            write_json_atomic(output, result)
            _emit({"output": str(output), "page_count": result["page_count"]})
        else:
            _emit(result)
    except (OSError, ValueError) as error:
        _fail("pdf-read", error)


@_register("render-pdf-pages")
def render_pdf_pages_command(path: Path, output: Path, pages: str, dpi: int = 144) -> None:
    """Render selected original pages for visual verification."""
    from .pdf_read import render_pdf_pages

    try:
        _emit(render_pdf_pages(path, output, pages=pages, dpi=dpi))
    except (OSError, ValueError) as error:
        _fail("pdf-render", error)


@_register("prepare-report")
def prepare_report_command(
    path: Path,
    report_kind: str = "paper",
    dry_run: bool = False,
    publication_path: Path | None = None,
    render: Annotated[bool, typer.Option(help="Run complete rendering after repairs.")] = False,
    evidence: Annotated[
        list[Path] | None,
        typer.Option("--evidence", help="Completed evidence-cache packet; repeat as needed."),
    ] = None,
    forbid_literal: Annotated[
        list[str] | None,
        typer.Option(
            "--forbid-literal", help="Previously identified exact text that must be gone."
        ),
    ] = None,
    coverage_matrix: Annotated[
        Path | None,
        typer.Option(help="Temporary section-bound evidence coverage matrix."),
    ] = None,
    review_issues: Annotated[
        Path | None,
        typer.Option(help="Consolidated review issues with automatic closure checks."),
    ] = None,
) -> None:
    """Repair deterministic defects in a complete draft and collect residual issues."""
    from .report_prepare import prepare_report

    try:
        result = prepare_report(
            path,
            report_kind=report_kind,
            dry_run=dry_run,
            publication_path=publication_path,
            render=render,
            evidence_paths=tuple(evidence or ()),
            forbidden_literals=tuple(forbid_literal or ()),
            coverage_matrix=coverage_matrix,
            review_issues=review_issues,
        )
        _emit(result.to_dict())
        if not result.valid:
            raise typer.Exit(1)
    except (OSError, ValueError) as error:
        _fail("report-prepare", error)


@_register("lookup-evidence-cache")
def lookup_evidence_cache_command(
    target_root: Path,
    source: Path,
    source_class: str,
    coverage_fingerprint: str,
) -> None:
    """Look up concise evidence by source bytes, policy, class, and coverage scope."""

    from .evidence_cache import lookup_evidence_cache

    try:
        result = lookup_evidence_cache(
            target_root, source, source_class, coverage_fingerprint
        )
        _emit(result)
        if not result["hit"]:
            raise typer.Exit(2)
    except (OSError, ValueError) as error:
        _fail("evidence-cache", error)


@_register("record-evidence-cache")
def record_evidence_cache_command(
    target_root: Path,
    source: Path,
    source_class: str,
    coverage_fingerprint: str,
    evidence: Path,
) -> None:
    """Validate and atomically record one concise, fully covered evidence packet."""

    from .evidence_cache import record_evidence_cache

    try:
        _emit(
            record_evidence_cache(
                target_root,
                source,
                source_class,
                coverage_fingerprint,
                _load_object(evidence),
            )
        )
    except (OSError, ValueError) as error:
        _fail("evidence-cache", error)


@_register("record-content-review")
def record_content_review_command(
    report: Path,
    assessment: Path,
    output: Path,
    source: Annotated[list[Path], typer.Option("--source")],
    report_kind: str = "paper",
    publication_path: Path | None = None,
) -> None:
    """Bind an already performed semantic assessment to the reviewed file version."""
    from .artifacts import write_json_atomic
    from .content_review import create_content_review

    try:
        result = create_content_review(
            report,
            _load_object(assessment),
            tuple(source),
            report_kind=report_kind,
            publication_path=publication_path,
        )
        write_json_atomic(output, result)
        _emit({"output": str(output), "content_status": result["content_status"]})
    except (OSError, ValueError) as error:
        _fail("content-review", error)


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
    content_review: Path | None = None,
) -> None:
    """Record paths for one published formal artifact."""

    from .artifacts import record_artifact_state

    state_path = record_artifact_state(
        target_root,
        artifact,
        artifact_kind=artifact_kind,
        run_id=run_id,
        sources=tuple(sources or ()),
        content_review=_load_object(content_review) if content_review else None,
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


@_register("fix-mermaid-direction")
def fix_mermaid_direction_command(path: Path, dry_run: bool = False) -> None:
    """Estimate TB/LR dimensions and fix directions in one Markdown file."""

    _ensure_renderer(require_browser=False)
    from .markdown_audit import fix_mermaid_direction

    try:
        _emit(fix_mermaid_direction(path, dry_run=dry_run))
    except (OSError, UnicodeError, ValueError) as error:
        _fail("mermaid-direction", error)


@_register("audit-markdown")
def audit_markdown_command(
    path: Path,
    report_kind: str = "generic",
    publication_path: Path | None = None,
) -> None:
    """Audit portable Markdown, mathematics, Mermaid, and numbered sections."""

    from .markdown_audit import audit_markdown

    audit = audit_markdown(path, report_kind=report_kind, publication_path=publication_path)
    _emit(
        {
            "valid": audit.valid,
            "path": audit.path,
            "errors": audit.errors,
            "warnings": audit.warnings,
            "diagnostics": audit.to_dict()["diagnostics"],
            "stages": audit.to_dict()["stages"],
        }
    )
    if not audit.valid:
        raise typer.Exit(1)


@_register("audit-paper-report")
def audit_paper_report_command(
    report: Path,
    content_review: Path | None = None,
    publication_path: Path | None = None,
) -> None:
    """Audit a paper report without encoding content ledgers."""

    from .report_audit import audit_paper_report

    audit = audit_paper_report(
        report,
        content_review=_load_object(content_review) if content_review else None,
        publication_path=publication_path,
    )
    _emit(
        {
            "valid": audit.valid,
            "format_status": audit.format_status,
            "content_status": audit.content_status,
            "publication_ready": audit.publication_ready,
            "comparison_ready": audit.valid and audit.content_status == "complete",
            "diagnostics": audit.markdown.get("diagnostics", ()),
            "stages": audit.markdown.get("stages", ()),
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
    content_review: Path | None = None,
    publication_path: Path | None = None,
) -> None:
    """Audit a category report, relationships, and optional comparison inputs."""

    from .classification import validate_classification
    from .markdown_audit import AuditContext
    from .report_audit import audit_category_report

    context = AuditContext()
    audit = audit_category_report(
        report,
        relationships,
        publication_path=publication_path,
        content_review=_load_object(content_review) if content_review else None,
        context=context,
    )
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
            audit_context=context,
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
            "content_status": audit.content_status,
            "publication_ready": input_ready and audit.content_status in {"complete", "partial"},
            "diagnostics": audit.markdown.get("diagnostics", ()),
            "stages": audit.markdown.get("stages", ()),
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
