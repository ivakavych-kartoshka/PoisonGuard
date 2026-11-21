from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence
import yaml


class ArtifactExistsError(RuntimeError):
    """Raised when an immutable artifact path is already occupied."""


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("configuration root must be a mapping")
    return value


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_json_text(value), encoding="utf-8")


def write_immutable_text(path: str | Path, text: str) -> Path:
    """Write a text artifact once; never overwrite an existing file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError as exc:
        raise ArtifactExistsError(f"refusing to overwrite immutable artifact: {target}") from exc
    return target


def write_immutable_json(path: str | Path, value: Any) -> Path:
    return write_immutable_text(path, _json_text(value))


def write_immutable_jsonl(path: str | Path, rows: Sequence[dict[str, Any]]) -> Path:
    text = "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows)
    return write_immutable_text(path, text)


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
