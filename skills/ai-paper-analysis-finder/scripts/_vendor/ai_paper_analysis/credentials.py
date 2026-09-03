"""Credential resolution without plaintext persistence or logging."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml


class CredentialError(RuntimeError):
    """Raised when a configured credential source cannot be used safely."""


def credentials_file(
    *, explicit: Path | None = None, target_root: Path | None = None
) -> Path | None:
    """Resolve one explicit or target-scoped encrypted credential file."""

    if explicit is not None:
        return explicit.expanduser().resolve()
    if target_root is None:
        return None
    candidate = target_root.expanduser().resolve() / ".ai-paper-analysis" / "credentials.sops.yaml"
    return candidate if candidate.is_file() else None


def decrypt_sops(path: Path) -> dict[str, Any]:
    """Decrypt a SOPS+age mapping into memory."""

    executable = shutil.which("sops")
    age = shutil.which("age")
    if not executable or not age:
        raise CredentialError("SOPS and age are required for encrypted project credentials")
    process = subprocess.run(
        [executable, "--decrypt", "--output-type", "yaml", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise CredentialError("SOPS could not decrypt the configured credential file")
    payload = yaml.safe_load(process.stdout)
    if not isinstance(payload, dict):
        raise CredentialError("Decrypted credential payload must be a mapping")
    return payload


def resolve_credential(
    name: str,
    *,
    encrypted_config: Path | None = None,
) -> str | None:
    """Resolve an environment override before an encrypted project value."""

    if value := os.environ.get(name):
        return value
    if encrypted_config and encrypted_config.is_file():
        payload = decrypt_sops(encrypted_config)
        value = payload.get(name)
        if value is not None and not isinstance(value, str):
            raise CredentialError(f"Credential {name} must be a string")
        return value
    return None
