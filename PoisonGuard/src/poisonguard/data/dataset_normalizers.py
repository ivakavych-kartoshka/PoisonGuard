"""Dataset-specific normalizers for manually provisioned corpora.

These functions convert locally available raw files into the repository's canonical
event JSONL. They do not download data and do not invent labels beyond simple
source metadata.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .normalizer import normalize_event_record, write_jsonl
from .schemas import Channel


def _write_records(records: list[dict[str, Any]], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    events = [normalize_event_record(record) for record in records]
    write_jsonl(output, [event.to_dict() for event in events])
    return output


def normalize_aeslc_parquet(input_path: str | Path, output_path: str | Path,
                            limit: int | None = None) -> Path:
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError("pandas is required to normalize AESLC parquet") from error

    frame = pd.read_parquet(input_path)
    records: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        if limit is not None and len(records) >= limit:
            break
        body = str(row.get("email_body", "")).strip()
        if not body:
            continue
        records.append({
            "payload": body,
            "capture_time": float(len(records)),
            "app_id": "aeslc",
            "channel": Channel.TYPED.value,
            "sender": None,
            "user_authored": True,
            "parent_ids": [],
            "metadata": {
                "dataset": "aeslc",
                "source_index": int(index),
                "subject_line": str(row.get("subject_line", "")).strip(),
            },
        })
    return _write_records(records, output_path)


def normalize_sms_collection(input_path: str | Path, output_path: str | Path,
                             limit: int | None = None) -> Path:
    records: list[dict[str, Any]] = []
    with Path(input_path).open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            if limit is not None and len(records) >= limit:
                break
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            label, text = (part.strip() for part in parts)
            if not text:
                continue
            records.append({
                "payload": text,
                "capture_time": float(len(records)),
                "app_id": "sms",
                "channel": Channel.SMS.value,
                "sender": "sms_unknown",
                "user_authored": False,
                "parent_ids": [],
                "metadata": {
                    "dataset": "sms_spam_collection",
                    "source_line": line_number,
                    "label": label,
                },
            })
    return _write_records(records, output_path)


def normalize_personachat(input_path: str | Path, output_path: str | Path,
                         limit: int | None = None) -> Path:
    records: list[dict[str, Any]] = []
    persona_pattern = re.compile(r"^\d+\s+your persona:\s*(.*)$", re.IGNORECASE)

    def add(payload: str, role: str, metadata: dict[str, Any]) -> None:
        if limit is not None and len(records) >= limit:
            return
        if not payload.strip():
            return
        records.append({
            "payload": payload.strip(),
            "capture_time": float(len(records)),
            "app_id": "personachat",
            "channel": Channel.TYPED.value,
            "sender": None,
            "user_authored": role == "user",
            "parent_ids": [],
            "metadata": {"dataset": "personachat", "role": role, **metadata},
        })

    with Path(input_path).open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            if limit is not None and len(records) >= limit:
                break
            line = line.rstrip("\n")
            if not line.strip():
                continue
            persona_match = persona_pattern.match(line.strip())
            if persona_match:
                add(persona_match.group(1), "user",
                    {"source_line": line_number, "kind": "persona"})
                continue
            fields = line.split("\t")
            if len(fields) < 2:
                continue
            user_turn = fields[0].split(" ", 1)
            partner_turn = fields[1].split(" ", 1)
            user_text = user_turn[1] if (len(user_turn) == 2 and user_turn[0].isdigit()) else fields[0]
            partner_text = partner_turn[1] if (len(partner_turn) == 2 and partner_turn[0].isdigit()) else fields[1]
            add(user_text, "user", {"source_line": line_number, "kind": "dialogue_turn"})
            add(partner_text, "partner", {"source_line": line_number, "kind": "dialogue_turn"})
    return _write_records(records, output_path)


def normalize_lamp_json(
    input_path: str | Path,
    output_path: str | Path,
    outputs_path: str | Path | None = None,
    task: str = "LaMP",
    limit: int | None = None,
) -> Path:
    import json

    raw = Path(input_path).read_text(encoding="utf-8")
    # LaMP ships JSON with non-standard escaped apostrophes (\\').
    raw = re.sub(r"(?<!\\\\)\\\\'", "'", raw)
    questions = json.loads(raw)
    outputs_by_id: dict[str, str] = {}
    if outputs_path is not None and Path(outputs_path).is_file():
        with Path(outputs_path).open(encoding="utf-8") as handle:
            outputs = json.load(handle)
        if isinstance(outputs, dict):
            if "golds" in outputs and isinstance(outputs["golds"], list):
                outputs = outputs["golds"]
            else:
                outputs_by_id = {str(key): str(value) for key, value in outputs.items()}
                outputs = []
        if isinstance(outputs, list):
            for item in outputs:
                if isinstance(item, dict) and "id" in item:
                    outputs_by_id[str(item["id"])] = str(item.get("output", ""))
    records: list[dict[str, Any]] = []
    for item_index, item in enumerate(questions):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", item_index))
        profile_items = item.get("profile", [])
        if not isinstance(profile_items, list):
            profile_items = [profile_items]
        for profile_index, profile in enumerate(profile_items):
            if limit is not None and len(records) >= limit:
                break
            if not isinstance(profile, dict):
                profile = {"text": str(profile)}
            payload = (
                profile.get("text")
                or profile.get("abstract")
                or profile.get("title")
                or profile.get("content")
                or str(profile)
            )
            if not str(payload).strip():
                continue
            records.append({
                "payload": str(payload).strip(),
                "capture_time": float(len(records)),
                "app_id": "lamp",
                "channel": Channel.TYPED.value,
                "sender": None,
                "user_authored": True,
                "parent_ids": [],
                "metadata": {
                    "dataset": "lamp",
                    "task": task,
                    "item_id": item_id,
                    "profile_id": str(profile.get("id", profile_index)),
                    "input": str(item.get("input", "")),
                    "output": outputs_by_id.get(item_id, ""),
                    "source_index": item_index,
                    "profile_index": profile_index,
                },
            })
        if limit is not None and len(records) >= limit:
            break
    return _write_records(records, output_path)
