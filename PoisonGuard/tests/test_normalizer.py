import json
from pathlib import Path

from poisonguard.data.normalizer import (
    normalize_event_record,
    normalize_jsonl,
    validate_manifest,
)
from poisonguard.data.schemas import Channel


def test_normalize_event_record_generates_id() -> None:
    event = normalize_event_record({
        "payload": "hello",
        "capture_time": 1.0,
        "app_id": "com.test",
        "channel": "typed",
        "sender": None,
        "user_authored": True,
        "parent_ids": [],
        "metadata": {"k": "v"},
    })
    assert event.channel == Channel.TYPED
    assert event.payload == "hello"
    assert len(event.event_id) == 64


def test_normalize_jsonl_round_trip(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    raw.write_text(json.dumps({
        "payload": "hi",
        "capture_time": 2.0,
        "app_id": "app",
        "channel": "sms",
    }) + "\n", encoding="utf-8")
    out = normalize_jsonl(raw, tmp_path / "out" / "poisonguard_events.jsonl")
    assert out.is_file()
    assert validate_manifest(out) == 1


def test_normalize_missing_field_raises() -> None:
    try:
        normalize_event_record({"payload": "x", "app_id": "a", "channel": "typed"})
    except ValueError as error:
        assert "capture_time" in str(error)
    else:
        raise AssertionError("expected ValueError")