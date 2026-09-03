"""Versioned provider registry and deterministic public-API adapters."""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .contracts import load_json
from .credentials import resolve_credential
from .identifiers import normalize_arxiv_id, normalize_doi

_CREDENTIALS_FILE: ContextVar[Path | None] = ContextVar(
    "ai_paper_analysis_credentials_file", default=None
)


def _credential(name: str) -> str | None:
    return resolve_credential(name, encrypted_config=_CREDENTIALS_FILE.get())


class ProviderError(RuntimeError):
    """Base class for provider failures."""


class InteractiveProviderRequired(ProviderError):
    """Raised when a source requires an authorized browser or user action."""


@dataclass(frozen=True)
class Candidate:
    provider: str
    native_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str
    doi: str
    arxiv_id: str
    canonical_url: str
    pdf_url: str
    abstract: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def provider_registry() -> dict[str, dict[str, Any]]:
    """Return built-in providers keyed by stable provider ID."""

    payload = load_json("provider-registry.json")
    return {provider["id"]: provider for provider in payload["providers"]}


def _get_json(
    url: str,
    *,
    params: Mapping[str, str | int],
    headers: dict[str, str] | None,
    timeout_seconds: int,
    max_retries: int,
) -> Any:
    request_headers = {"User-Agent": "ai-paper-analysis/0.1.0"}
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(
                url,
                params=params,
                headers=request_headers,
                timeout=timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            last_error = error
            if attempt >= max_retries:
                break
            retry_after = None
            if isinstance(error, httpx.HTTPStatusError):
                retry_after = error.response.headers.get("Retry-After")
            delay = (
                int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 8)
            )
            time.sleep(delay)
    raise ProviderError(f"Provider request failed: {last_error}")


def _post_json(
    url: str,
    *,
    payload: Mapping[str, object],
    headers: dict[str, str] | None,
    timeout_seconds: int,
    max_retries: int,
) -> Any:
    request_headers = {"User-Agent": "ai-paper-analysis/0.1.0"}
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=request_headers,
                timeout=timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            last_error = error
            if attempt >= max_retries:
                break
            retry_after = None
            if isinstance(error, httpx.HTTPStatusError):
                retry_after = error.response.headers.get("Retry-After")
            delay = (
                int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 8)
            )
            time.sleep(delay)
    raise ProviderError(f"Provider request failed: {last_error}")


def _year(value: object) -> int | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1000 <= year <= 9999 else None


def _first_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    return ""


def _author_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        value = [value]
    names: list[str] = []
    for item in value:
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = str(
                item.get("name")
                or item.get("display_name")
                or item.get("fullName")
                or item.get("text")
                or ""
            )
        else:
            name = ""
        if name.strip():
            names.append(name.strip())
    return tuple(names)


def _doi_publisher(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    del limit, timeout, retries
    doi = normalize_doi(query)
    if not doi:
        raise ProviderError("DOI and Publisher Pages expects one DOI as its query")
    canonical_url = f"https://doi.org/{doi}"
    return [
        Candidate(
            provider="doi-publisher",
            native_id=doi,
            title="",
            authors=(),
            year=None,
            venue="",
            doi=doi,
            arxiv_id="",
            canonical_url=canonical_url,
            pdf_url="",
            abstract="",
        )
    ]


def _crossref(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://api.crossref.org/works",
        params={
            "query": query,
            "rows": limit,
            "select": "DOI,title,author,published,container-title,URL,abstract,link",
        },
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("message", {}).get("items", []):
        dates = item.get("published", {}).get("date-parts", [[]])
        links = item.get("link") or []
        pdf_url = next(
            (
                link.get("URL", "")
                for link in links
                if "pdf" in link.get("content-type", "").lower()
            ),
            "",
        )
        authors = tuple(
            " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part)
            for author in item.get("author", [])
        )
        doi = normalize_doi(item.get("DOI"))
        candidates.append(
            Candidate(
                provider="crossref",
                native_id=doi or item.get("URL", ""),
                title=(item.get("title") or [""])[0],
                authors=authors,
                year=_year(dates[0][0] if dates and dates[0] else None),
                venue=(item.get("container-title") or [""])[0],
                doi=doi,
                arxiv_id="",
                canonical_url=item.get("URL", ""),
                pdf_url=pdf_url,
                abstract=item.get("abstract", ""),
            )
        )
    return candidates


def _openalex(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://api.openalex.org/works",
        params={"search": query, "per-page": limit},
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("results", []):
        best = item.get("best_oa_location") or {}
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        candidates.append(
            Candidate(
                provider="openalex",
                native_id=item.get("id", ""),
                title=item.get("display_name", ""),
                authors=tuple(
                    authorship.get("author", {}).get("display_name", "")
                    for authorship in item.get("authorships", [])
                ),
                year=_year(item.get("publication_year")),
                venue=source.get("display_name", ""),
                doi=normalize_doi(item.get("doi")),
                arxiv_id="",
                canonical_url=primary.get("landing_page_url") or item.get("id", ""),
                pdf_url=best.get("pdf_url") or "",
                abstract="",
            )
        )
    return candidates


def _semantic_scholar(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    api_key = _credential("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"x-api-key": api_key} if api_key else None
    payload = _get_json(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,venue,externalIds,url,openAccessPdf,abstract",
        },
        headers=headers,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("data", []):
        identifiers = item.get("externalIds") or {}
        open_pdf = item.get("openAccessPdf") or {}
        candidates.append(
            Candidate(
                provider="semantic-scholar",
                native_id=item.get("paperId", ""),
                title=item.get("title", ""),
                authors=tuple(author.get("name", "") for author in item.get("authors", [])),
                year=_year(item.get("year")),
                venue=item.get("venue", ""),
                doi=normalize_doi(identifiers.get("DOI")),
                arxiv_id=normalize_arxiv_id(identifiers.get("ArXiv")),
                canonical_url=item.get("url", ""),
                pdf_url=open_pdf.get("url", ""),
                abstract=item.get("abstract") or "",
            )
        )
    return candidates


def _arxiv(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    url = f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}&start=0&max_results={limit}"
    last_error: Exception | None = None
    response: httpx.Response | None = None
    for attempt in range(retries + 1):
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            break
        except httpx.HTTPError as error:
            last_error = error
            if attempt >= retries:
                raise ProviderError(f"arXiv request failed: {last_error}") from error
            time.sleep(min(2**attempt, 8))
    if response is None:
        raise ProviderError(f"arXiv request failed: {last_error}")
    root = ET.fromstring(response.text)
    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    candidates: list[Candidate] = []
    for entry in root.findall("atom:entry", namespace):
        identifier_url = entry.findtext("atom:id", default="", namespaces=namespace)
        arxiv_id = normalize_arxiv_id(identifier_url)
        published = entry.findtext("atom:published", default="", namespaces=namespace)
        doi = entry.findtext("arxiv:doi", default="", namespaces=namespace)
        title = entry.findtext("atom:title", default="", namespaces=namespace)
        abstract = entry.findtext("atom:summary", default="", namespaces=namespace)
        candidates.append(
            Candidate(
                provider="arxiv",
                native_id=arxiv_id,
                title=" ".join(title.split()),
                authors=tuple(
                    author.findtext("atom:name", default="", namespaces=namespace)
                    for author in entry.findall("atom:author", namespace)
                ),
                year=_year(published[:4]),
                venue=entry.findtext("arxiv:journal_ref", default="", namespaces=namespace),
                doi=normalize_doi(doi),
                arxiv_id=arxiv_id,
                canonical_url=identifier_url,
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
                abstract=" ".join(abstract.split()),
            )
        )
    return candidates


def _europe_pmc(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={"query": query, "pageSize": limit, "format": "json"},
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("resultList", {}).get("result", []):
        pmcid = item.get("pmcid", "")
        authors = tuple(
            part.strip() for part in item.get("authorString", "").split(",") if part.strip()
        )
        article_url = f"https://europepmc.org/article/{item.get('source', '')}/{item.get('id', '')}"
        pdf_url = f"https://europepmc.org/articles/{pmcid}/bin/{pmcid}.pdf" if pmcid else ""
        candidates.append(
            Candidate(
                provider="europe-pmc",
                native_id=pmcid or item.get("id", ""),
                title=item.get("title", ""),
                authors=authors,
                year=_year(item.get("pubYear")),
                venue=item.get("journalTitle", ""),
                doi=normalize_doi(item.get("doi")),
                arxiv_id="",
                canonical_url=article_url,
                pdf_url=pdf_url,
                abstract="",
            )
        )
    return candidates


def _dblp(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://dblp.org/search/publ/api",
        params={"q": query, "h": limit, "format": "json"},
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    raw_hits = payload.get("result", {}).get("hits", {}).get("hit", [])
    hits = raw_hits if isinstance(raw_hits, list) else [raw_hits]
    candidates: list[Candidate] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        info = hit.get("info") or {}
        if not isinstance(info, dict):
            continue
        raw_authors = info.get("authors", {})
        if isinstance(raw_authors, dict):
            raw_authors = raw_authors.get("author", [])
        raw_ee = info.get("ee", "")
        external_links = raw_ee if isinstance(raw_ee, list) else [raw_ee]
        canonical_url = str(info.get("url") or "")
        pdf_url = next(
            (
                str(link)
                for link in external_links
                if isinstance(link, str) and link.lower().endswith(".pdf")
            ),
            "",
        )
        doi = normalize_doi(info.get("doi"))
        if not doi:
            doi_link = next(
                (
                    str(link)
                    for link in external_links
                    if isinstance(link, str) and "doi.org/" in link.lower()
                ),
                "",
            )
            doi = normalize_doi(doi_link)
        candidates.append(
            Candidate(
                provider="dblp",
                native_id=str(info.get("key") or canonical_url),
                title=str(info.get("title") or "").rstrip("."),
                authors=_author_names(raw_authors),
                year=_year(info.get("year")),
                venue=str(info.get("venue") or ""),
                doi=doi,
                arxiv_id="",
                canonical_url=canonical_url,
                pdf_url=pdf_url,
                abstract="",
            )
        )
    return candidates


def _hal(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://api.archives-ouvertes.fr/search/",
        params={
            "q": query,
            "rows": limit,
            "fl": (
                "halId_s,title_s,authFullName_s,producedDateY_i,docType_s,"
                "doiId_s,uri_s,fileMain_s,abstract_s"
            ),
        },
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("response", {}).get("docs", []):
        if not isinstance(item, dict):
            continue
        candidates.append(
            Candidate(
                provider="hal",
                native_id=str(item.get("halId_s") or ""),
                title=_first_text(item.get("title_s")),
                authors=_author_names(item.get("authFullName_s", [])),
                year=_year(item.get("producedDateY_i")),
                venue=str(item.get("docType_s") or ""),
                doi=normalize_doi(item.get("doiId_s")),
                arxiv_id="",
                canonical_url=str(item.get("uri_s") or ""),
                pdf_url=str(item.get("fileMain_s") or ""),
                abstract=_first_text(item.get("abstract_s")),
            )
        )
    return candidates


def _zenodo(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    payload = _get_json(
        "https://zenodo.org/api/records",
        params={"q": query, "size": limit},
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("hits", {}).get("hits", []):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") or {}
        files = item.get("files") or []
        pdf_url = ""
        for file_record in files:
            if not isinstance(file_record, dict):
                continue
            key = str(file_record.get("key") or "")
            if key.lower().endswith(".pdf"):
                links = file_record.get("links") or {}
                if isinstance(links, dict):
                    pdf_url = str(
                        links.get("download") or links.get("content") or links.get("self") or ""
                    )
                break
        links = item.get("links") or {}
        canonical_url = (
            str(links.get("html") or links.get("self") or "") if isinstance(links, dict) else ""
        )
        creators = metadata.get("creators", []) if isinstance(metadata, dict) else []
        publication_date = (
            str(metadata.get("publication_date") or "") if isinstance(metadata, dict) else ""
        )
        candidates.append(
            Candidate(
                provider="zenodo",
                native_id=str(item.get("id") or ""),
                title=str(metadata.get("title") or "") if isinstance(metadata, dict) else "",
                authors=_author_names(creators),
                year=_year(publication_date[:4]),
                venue="Zenodo",
                doi=normalize_doi(metadata.get("doi")) if isinstance(metadata, dict) else "",
                arxiv_id="",
                canonical_url=canonical_url,
                pdf_url=pdf_url,
                abstract=(
                    str(metadata.get("description") or "") if isinstance(metadata, dict) else ""
                ),
            )
        )
    return candidates


def _core(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    api_key = _credential("CORE_API_KEY")
    if not api_key:
        raise ProviderError("CORE_API_KEY is required for CORE discovery")
    payload = _post_json(
        "https://api.core.ac.uk/v3/search/works",
        payload={"q": query, "limit": limit},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout_seconds=timeout,
        max_retries=retries,
    )
    candidates: list[Candidate] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        raw_authors = item.get("authors", [])
        download_url = str(item.get("downloadUrl") or "")
        identifiers = item.get("identifiers") or {}
        doi = normalize_doi(item.get("doi"))
        if not doi and isinstance(identifiers, dict):
            doi = normalize_doi(identifiers.get("doi"))
        published_date = str(item.get("publishedDate") or "")
        fulltext_urls = item.get("sourceFulltextUrls") or []
        canonical_url = (
            str(fulltext_urls[0]) if isinstance(fulltext_urls, list) and fulltext_urls else ""
        )
        journals = item.get("journals") or []
        venue = str(item.get("publisher") or "")
        if not venue and isinstance(journals, list) and journals:
            first_journal = journals[0]
            venue = (
                str(first_journal.get("title") or "")
                if isinstance(first_journal, dict)
                else str(first_journal)
            )
        candidates.append(
            Candidate(
                provider="core",
                native_id=str(item.get("id") or ""),
                title=str(item.get("title") or ""),
                authors=_author_names(raw_authors),
                year=_year(item.get("yearPublished") or published_date[:4]),
                venue=venue,
                doi=doi,
                arxiv_id="",
                canonical_url=canonical_url,
                pdf_url=download_url,
                abstract=str(item.get("abstract") or ""),
            )
        )
    return candidates


def _unpaywall(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    del limit
    doi = normalize_doi(query)
    email = _credential("UNPAYWALL_EMAIL")
    if not doi:
        raise ProviderError("Unpaywall expects one DOI as its query")
    if not email:
        raise ProviderError("UNPAYWALL_EMAIL is required for Unpaywall resolution")
    payload = _get_json(
        f"https://api.unpaywall.org/v2/{quote(doi, safe='')}",
        params={"email": email},
        headers=None,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    best = payload.get("best_oa_location") or {}
    authors = payload.get("z_authors") or []
    return [
        Candidate(
            provider="unpaywall",
            native_id=doi,
            title=str(payload.get("title") or ""),
            authors=_author_names(authors),
            year=_year(payload.get("year")),
            venue=str(payload.get("journal_name") or ""),
            doi=doi,
            arxiv_id="",
            canonical_url=str(best.get("url_for_landing_page") or f"https://doi.org/{doi}"),
            pdf_url=str(best.get("url_for_pdf") or ""),
            abstract="",
        )
    ]


def _configured_scholar(query: str, limit: int, timeout: int, retries: int) -> list[Candidate]:
    endpoint = os.environ.get("APA_GOOGLE_SCHOLAR_API_URL")
    if not endpoint:
        raise ProviderError("APA_GOOGLE_SCHOLAR_API_URL is required for Scholar batch discovery")
    token = _credential("APA_GOOGLE_SCHOLAR_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    payload = _get_json(
        endpoint,
        params={"q": query, "limit": limit},
        headers=headers,
        timeout_seconds=timeout,
        max_retries=retries,
    )
    items = payload.get("results", payload.get("organic_results", []))
    candidates: list[Candidate] = []
    for item in items:
        raw_authors = item.get("authors")
        authors = tuple(raw_authors) if isinstance(raw_authors, list) else ()
        candidates.append(
            Candidate(
                provider="google-scholar-api",
                native_id=str(item.get("result_id") or item.get("id") or item.get("link") or ""),
                title=item.get("title", ""),
                authors=authors,
                year=_year(item.get("year") or item.get("publication_year")),
                venue=item.get("publication", ""),
                doi=normalize_doi(item.get("doi")),
                arxiv_id=normalize_arxiv_id(item.get("arxiv_id")),
                canonical_url=item.get("link", ""),
                pdf_url=item.get("pdf_url", ""),
                abstract=item.get("snippet", ""),
            )
        )
    return candidates


ADAPTERS: dict[str, Callable[[str, int, int, int], list[Candidate]]] = {
    "doi-publisher": _doi_publisher,
    "crossref": _crossref,
    "openalex": _openalex,
    "semantic-scholar": _semantic_scholar,
    "arxiv": _arxiv,
    "unpaywall": _unpaywall,
    "europe-pmc": _europe_pmc,
    "dblp": _dblp,
    "hal": _hal,
    "zenodo": _zenodo,
    "core": _core,
    "google-scholar-api": _configured_scholar,
}


def discover(
    provider_id: str,
    query: str,
    *,
    limit: int = 20,
    timeout_seconds: int = 60,
    max_retries: int = 3,
    credentials_file: Path | None = None,
) -> list[Candidate]:
    """Search one deterministic API or report that interactive access is required."""

    registry = provider_registry()
    if provider_id not in registry:
        raise ProviderError(f"Unknown provider: {provider_id}")
    token = _CREDENTIALS_FILE.set(credentials_file)
    try:
        if provider_id in ADAPTERS:
            return ADAPTERS[provider_id](query, limit, timeout_seconds, max_retries)
        provider = registry[provider_id]
        raise InteractiveProviderRequired(
            f"{provider['name']} requires a purpose-built resolver or an explicitly "
            "authorized browser session"
        )
    finally:
        _CREDENTIALS_FILE.reset(token)


def write_candidates(path: Path, candidates: list[Candidate]) -> None:
    """Write candidates as deterministic UTF-8 JSONL."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
