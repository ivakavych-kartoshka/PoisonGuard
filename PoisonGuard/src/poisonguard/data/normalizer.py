"""Normalization helpers for manually provisioned datasets.

These helpers do not download data. They validate and canonicalize records into
the repository's event schema so that supplied IDs cannot be trusted blindly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from .schemas import Channel, Event
from poisonguard.utils.io import write_jsonl
from poisonguard.utils.validation import require_local_path


REQUIRED_FIELDS = ("payload", "capture_time", "app_id", "channel")


def normalize_event_record(record: dict[str, Any]) -> Event:
    """Validate one raw record and return a canonical Event."""
    if not isinstance(record, dict):
        raise ValueError("event record must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    parents = record.get("parent_ids", ()) or ()
    if isinstance(parents, str):
        parents = (parents,)
    metadata = record.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    return Event.create(
        payload=str(record["payload"]),
        capture_time=float(record["capture_time"]),
        app_id=str(record["app_id"]),
        channel=Channel(record["channel"]),
        sender=record.get("sender"),
        user_authored=record.get("user_authored"),
        parent_ids=tuple(str(parent) for parent in parents),
        metadata=metadata,
    )


def iter_normalized_records(path: str | Path) -> Iterator[Event]:
    source = require_local_path(path, "raw event JSONL")
    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield normalize_event_record(json.loads(line))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid raw event at line {line_number}: {error}") from error


def normalize_jsonl(input_path: str | Path, output_path: str | Path) -> Path:
    """Canonicalize a raw JSONL file into ``poisonguard_events.jsonl``."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    events = list(iter_normalized_records(input_path))
    write_jsonl(output, [event.to_dict() for event in events])
    return output


def validate_manifest(path: str | Path) -> int:
    """Return the number of events in a normalized manifest."""
    from .adapters import JsonlEventAdapter

    return sum(1 for _ in JsonlEventAdapter(path).iter_events())