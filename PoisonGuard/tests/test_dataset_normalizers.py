import json
from pathlib import Path

import pandas as pd

from poisonguard.data.dataset_normalizers import (
    normalize_aeslc_parquet,
    normalize_lamp_json,
    normalize_personachat,
    normalize_sms_collection,
)
from poisonguard.data.adapters import JsonlEventAdapter


def test_normalize_aeslc_parquet(tmp_path: Path) -> None:
    frame = pd.DataFrame({
        "email_body": ["Hello world", ""],
        "subject_line": ["Greeting", "Empty"],
    })
    source = tmp_path / "aeslc.parquet"
    frame.to_parquet(source, index=False)
    output = normalize_aeslc_parquet(source, tmp_path / "aeslc.jsonl")
    events = list(JsonlEventAdapter(output).iter_events())
    assert len(events) == 1
    assert events[0].payload == "Hello world"
    assert events[0].channel.value == "typed"
    assert events[0].metadata["subject_line"] == "Greeting"


def test_normalize_sms_collection(tmp_path: Path) -> None:
    source = tmp_path / "sms.tsv"
    source.write_text("ham\tHello there\nspam\tWin now\n", encoding="utf-8")
    output = normalize_sms_collection(source, tmp_path / "sms.jsonl")
    events = list(JsonlEventAdapter(output).iter_events())
    assert len(events) == 2
    assert events[0].channel.value == "sms"
    assert events[0].metadata["label"] == "ham"
    assert events[1].metadata["label"] == "spam"


def test_normalize_personachat(tmp_path: Path) -> None:
    source = tmp_path / "persona.txt"
    source.write_text(
        "1 your persona: I like tea.\n"
        "2 hello there\tI am fine\tcandidate one|candidate two\n",
        encoding="utf-8",
    )
    output = normalize_personachat(source, tmp_path / "persona.jsonl")
    events = list(JsonlEventAdapter(output).iter_events())
    assert len(events) == 3
    assert events[0].payload == "I like tea."
    assert events[1].payload == "hello there"
    assert events[2].payload == "I am fine"
    assert events[1].user_authored is True
    assert events[2].user_authored is False


def test_normalize_lamp_json(tmp_path: Path) -> None:
    questions = [
        {
            "id": "user-1",
            "input": "Write a headline.",
            "profile": [
                {"id": "p1", "text": "Earlier article one."},
                {"id": "p2", "text": "Earlier article two."},
            ],
        }
    ]
    outputs = [{"id": "user-1", "output": "Expected headline."}]
    q_path = tmp_path / "questions.json"
    o_path = tmp_path / "outputs.json"
    q_path.write_text(json.dumps(questions), encoding="utf-8")
    o_path.write_text(json.dumps(outputs), encoding="utf-8")
    output = normalize_lamp_json(q_path, tmp_path / "lamp.jsonl", outputs_path=o_path)
    events = list(JsonlEventAdapter(output).iter_events())
    assert len(events) == 2
    assert events[0].payload == "Earlier article one."
    assert events[0].metadata["item_id"] == "user-1"
    assert events[0].metadata["output"] == "Expected headline."
