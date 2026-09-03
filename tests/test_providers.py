from __future__ import annotations

import pytest

from ai_paper_analysis import providers
from ai_paper_analysis.providers import InteractiveProviderRequired, discover, provider_registry


def test_registry_is_finite_and_explicit() -> None:
    registry = provider_registry()
    assert "crossref" in registry
    assert "google-scholar-api" in registry
    assert registry["google-scholar-api"]["direct_crawl"] is False
    assert registry["authorized-chinese"]["access"] == (
        "explicit_authorization_and_existing_session"
    )


def test_interactive_provider_never_falls_back_to_scraping() -> None:
    with pytest.raises(InteractiveProviderRequired):
        discover("authorized-commercial", "fixture")


def test_dblp_adapter_normalizes_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        providers,
        "_get_json",
        lambda *args, **kwargs: {
            "result": {
                "hits": {
                    "hit": [
                        {
                            "info": {
                                "key": "conf/example/Paper26",
                                "title": "A Test Paper.",
                                "authors": {"author": [{"text": "Ada Example"}, "Bo Example"]},
                                "year": "2026",
                                "venue": "ExampleConf",
                                "ee": "https://doi.org/10.1000/EXAMPLE",
                                "url": "https://dblp.org/rec/conf/example/Paper26",
                            }
                        }
                    ]
                }
            }
        },
    )

    result = discover("dblp", "test")

    assert result[0].doi == "10.1000/example"
    assert result[0].authors == ("Ada Example", "Bo Example")
    assert result[0].year == 2026


def test_unpaywall_requires_contact_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
    with pytest.raises(providers.ProviderError, match="UNPAYWALL_EMAIL"):
        discover("unpaywall", "10.1000/example")


def test_encrypted_provider_credential_is_forwarded_without_persistence(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    encrypted = tmp_path / "credentials.sops.yaml"
    encrypted.write_text("fixture\n", encoding="utf-8")
    observed: dict[str, object] = {}

    def credential(name: str, *, encrypted_config=None):
        observed["credential"] = (name, encrypted_config)
        return "secret-value"

    def get_json(url: str, **kwargs):
        observed["headers"] = kwargs["headers"]
        return {"data": []}

    monkeypatch.setattr(providers, "resolve_credential", credential)
    monkeypatch.setattr(providers, "_get_json", get_json)

    assert discover("semantic-scholar", "fixture", credentials_file=encrypted) == []
    assert observed["credential"] == ("SEMANTIC_SCHOLAR_API_KEY", encrypted)
    assert observed["headers"] == {"x-api-key": "secret-value"}
