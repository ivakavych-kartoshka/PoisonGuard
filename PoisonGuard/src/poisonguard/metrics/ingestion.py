"""Ingestion of measured external result files.

This module never synthesizes, imputes, or interpolates an experimental value.
A missing metric stays missing. If a caller explicitly requires a field, loading
fails instead of filling a placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from poisonguard.metrics.aggregation import median_iqr_count
from poisonguard.utils.io import sha256_file

__all__ = [
    "MeasurementIncomplete",
    "Measurement",
    "load_measurements",
    "aggregate_measurements",
]

_MISSING = object()

_NUMERIC_FIELDS = (
    "metrics.asr_before",
    "metrics.asr_after",
    "metrics.fqr",
    "metrics.false_admission_rate",
    "metrics.clean_utility",
    "metrics.utility_after",
    "metrics.utility_delta",
    "metrics.laundering_persistence",
    "metrics.rollback.elapsed_ms",
    "metrics.rollback.storage_kb",
    "metrics.systems.training_step_ms",
    "metrics.systems.peak_rss_kb",
    "metrics.systems.temperature_c",
    "metrics.systems.energy_j",
)


class MeasurementIncomplete(RuntimeError):
    """Raised when a required measured field is absent or malformed."""


@dataclass(frozen=True)
class Measurement:
    path: str
    sha256: str
    label: str
    defense: str
    attack_family: str
    seed: int | None
    payload: dict[str, Any]

    def get(self, dotted: str) -> Any:
        value: Any = self.payload
        for part in dotted.split("."):
            if not isinstance(value, Mapping) or part not in value:
                return _MISSING
            value = value[part]
        return value

    def numeric(self, dotted: str) -> float | None:
        value = self.get(dotted)
        if value is _MISSING or isinstance(value, bool):
            return None
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        return result if result == result and result not in (float("inf"), float("-inf")) else None


def _as_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_file():
        raise MeasurementIncomplete(f"measured result file not found: {path}")
    return path


def load_measurements(
    paths: Sequence[str | Path],
    *,
    required_fields: Sequence[str] = (),
) -> list[Measurement]:
    """Load explicit measured result files and validate their identity fields."""
    if not paths:
        raise MeasurementIncomplete("no measured result files were configured")
    measurements: list[Measurement] = []
    for raw_path in paths:
        path = _as_path(raw_path)
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MeasurementIncomplete(f"cannot read measured result {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise MeasurementIncomplete(f"measured result must be a JSON object: {path}")
        label = str(payload.get("label", ""))
        if not label:
            raise MeasurementIncomplete(f"measured result has no label: {path}")
        if not isinstance(payload.get("metrics"), Mapping):
            raise MeasurementIncomplete(f"measured result has no metrics object: {path}")
        defense = payload.get("defense")
        attack_family = payload.get("attack_family")
        if not isinstance(defense, str) or not defense:
            raise MeasurementIncomplete(f"measured result has no defense name: {path}")
        if not isinstance(attack_family, str) or not attack_family:
            raise MeasurementIncomplete(f"measured result has no attack family: {path}")
        seed = payload.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError) as exc:
                raise MeasurementIncomplete(f"invalid seed in {path}: {seed}") from exc
        measurement = Measurement(
            path=path.as_posix(),
            sha256=sha256_file(path),
            label=label,
            defense=defense,
            attack_family=attack_family,
            seed=seed,
            payload=payload,
        )
        missing = [field for field in required_fields if measurement.get(field) is _MISSING]
        if missing:
            raise MeasurementIncomplete(
                f"{path} is missing required measured fields: {', '.join(missing)}")
        measurements.append(measurement)
    return measurements


def _energy_from(measurement: Measurement) -> tuple[float | None, float | None, str | None]:
    energy = measurement.get("energy")
    if energy is _MISSING or not isinstance(energy, Mapping):
        return None, None, None
    source = str(energy.get("source", "")).strip().lower()
    value = energy.get("joules", energy.get("energy_j"))
    if isinstance(value, bool):
        value = None
    try:
        joules = float(value) if value is not None else None
    except (TypeError, ValueError):
        joules = None
    if source == "external_power_monitor":
        return joules, None, source
    if source in {"android_battery_counters", "battery_counters", "android"}:
        return None, joules, source
    return None, None, source or None


def aggregate_measurements(measurements: Sequence[Measurement]) -> dict[str, Any]:
    """Aggregate only the values present in explicit measured files."""
    if not measurements:
        raise MeasurementIncomplete("cannot aggregate an empty measurement set")

    per_result: list[dict[str, Any]] = []
    primary_energy: list[float] = []
    secondary_energy: list[float] = []
    energy_sources: set[str] = set()

    for measurement in measurements:
        row: dict[str, Any] = {
            "path": measurement.path,
            "sha256": measurement.sha256,
            "label": measurement.label,
            "defense": measurement.defense,
            "attack_family": measurement.attack_family,
            "seed": measurement.seed,
            "values": {},
            "missing": [],
        }
        for field in _NUMERIC_FIELDS:
            value = measurement.numeric(field)
            if value is None:
                row["missing"].append(field)
            else:
                row["values"][field] = value

        before = measurement.numeric("metrics.asr_before")
        after = measurement.numeric("metrics.asr_after")
        if before is not None and after is not None:
            row["values"]["asr_reduction"] = before - after
            if before:
                row["values"]["asr_relative_reduction"] = (before - after) / before
            else:
                row["missing"].append("asr_relative_reduction")

        utility_before = measurement.numeric("metrics.clean_utility")
        utility_after = measurement.numeric("metrics.utility_after")
        if utility_before is not None and utility_after is not None:
            row["values"]["utility_delta"] = utility_after - utility_before

        primary, secondary, source = _energy_from(measurement)
        if source is not None:
            energy_sources.add(source)
        if primary is not None:
            row["values"]["energy_j_external"] = primary
            primary_energy.append(primary)
        else:
            row["missing"].append("energy_j_external")
        if secondary is not None:
            row["values"]["energy_j_android_secondary"] = secondary
            secondary_energy.append(secondary)

        rollback_exact = measurement.get("metrics.rollback.exact")
        if isinstance(rollback_exact, bool):
            row["values"]["rollback_exact"] = rollback_exact
        else:
            row["missing"].append("metrics.rollback.exact")
        per_result.append(row)

    summary: dict[str, Any] = {}
    keys = sorted(
        {key for row in per_result for key in row["values"] if key not in {"rollback_exact"}}
        | {"energy_j_external", "energy_j_android_secondary"}
    )
    for key in keys:
        values = [row["values"][key] for row in per_result if key in row["values"]]
        summary[key] = median_iqr_count(values)
    exact_values = [row["values"]["rollback_exact"] for row in per_result
                    if "rollback_exact" in row["values"]]
    summary["rollback_exact"] = {
        "count": len(exact_values),
        "true": sum(1 for value in exact_values if value),
        "rate": (sum(1 for value in exact_values if value) / len(exact_values)) if exact_values else None,
    }
    summary["energy_j_external"]["source_policy"] = "external_power_monitor only"
    summary["energy_j_android_secondary"]["source_policy"] = (
        "Android counter data is secondary and is not an energy claim")

    return {
        "label": "aggregated measured external results, not a paper result until independently validated",
        "paper_ready": False,
        "result_count": len(measurements),
        "defenses": sorted({measurement.defense for measurement in measurements}),
        "attack_families": sorted({measurement.attack_family for measurement in measurements}),
        "seeds": sorted({measurement.seed for measurement in measurements if measurement.seed is not None}),
        "energy_sources": sorted(energy_sources),
        "source_files": [
            {"path": measurement.path, "sha256": measurement.sha256}
            for measurement in measurements
        ],
        "per_result": per_result,
        "summary": summary,
        "notes": [
            "No value is interpolated from synthetic, conceptual, or counterfactual data.",
            "Missing measured fields remain absent from summary aggregates.",
            "Android battery counters are reported only as secondary data.",
        ],
    }
