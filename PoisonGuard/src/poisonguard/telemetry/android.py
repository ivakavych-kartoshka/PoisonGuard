"""Importer for Android device telemetry captured during experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from poisonguard.metrics.aggregation import median_iqr_count
from poisonguard.utils.io import sha256_file
from poisonguard.utils.validation import require_local_path


REQUIRED_FIELDS = ("device", "training_step_ms", "peak_rss_kb")
OPTIONAL_NUMERIC_FIELDS = ("temperature_c", "battery_level", "energy_j")


class AndroidTelemetryImporter:
    def __init__(self, path: str | Path) -> None:
        self.path = require_local_path(path, "Android telemetry JSON")

    @property
    def sha256(self) -> str:
        return sha256_file(self.path)

    def load(self) -> list[dict[str, Any]]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "records" in payload:
            records = payload["records"]
        elif isinstance(payload, dict):
            records = [payload]
        elif isinstance(payload, list):
            records = payload
        else:
            raise ValueError("Android telemetry must be an object or list of objects")
        if not isinstance(records, list):
            raise ValueError("Android telemetry records must be a list")
        for index, item in enumerate(records, 1):
            if not isinstance(item, dict):
                raise ValueError(f"telemetry item {index} must be an object")
            missing = [field for field in REQUIRED_FIELDS if field not in item]
            if missing:
                raise ValueError(f"telemetry item {index} missing: {', '.join(missing)}")
            for field in OPTIONAL_NUMERIC_FIELDS:
                if field in item and item[field] is not None:
                    try:
                        float(item[field])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            f"telemetry item {index} has invalid {field}: {item[field]}"
                        ) from exc
        return records

    @staticmethod
    def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
        steps = [float(record["training_step_ms"]) for record in records]
        rss = [float(record["peak_rss_kb"]) for record in records]
        summary: dict[str, Any] = {
            "count": len(records),
            "training_step_ms": {
                "min": min(steps) if steps else None,
                "max": max(steps) if steps else None,
                "mean": sum(steps) / len(steps) if steps else None,
            },
            "peak_rss_kb": {
                "min": min(rss) if rss else None,
                "max": max(rss) if rss else None,
                "mean": sum(rss) / len(rss) if rss else None,
            },
        }
        for field in OPTIONAL_NUMERIC_FIELDS:
            values = [float(record[field]) for record in records if record.get(field) is not None]
            summary[field] = median_iqr_count(values)
        devices = sorted({str(record.get("device", "")) for record in records if record.get("device")})
        summary["devices"] = devices
        return summary
