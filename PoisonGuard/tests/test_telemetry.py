import json
from pathlib import Path

import pytest

from poisonguard.telemetry.android import AndroidTelemetryImporter


def test_load_list(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.json"
    path.write_text(json.dumps([{
        "device": "Xiaomi 13T",
        "training_step_ms": 3800,
        "peak_rss_kb": 2100000,
    }]), encoding="utf-8")
    records = AndroidTelemetryImporter(path).load()
    assert len(records) == 1
    summary = AndroidTelemetryImporter.summarize(records)
    assert summary["count"] == 1
    assert summary["training_step_ms"]["mean"] == 3800


def test_missing_field_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"device": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        AndroidTelemetryImporter(path).load()