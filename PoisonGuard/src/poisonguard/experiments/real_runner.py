"""Honest scaffolding and protocol runner for real experiments.

This module never fabricates paper results. It validates manually provisioned
assets, prepares deterministic input manifests from normalized real events,
invokes only explicitly pinned external commands, and records immutable run
manifests. Metrics are aggregated in a separate step from explicit measured
result files; no value is inferred from synthetic data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from poisonguard.baselines.external_wrappers import (
    build_attack_adapter,
    build_baseline_adapter,
)
from poisonguard.data.adapters import JsonlEventAdapter
from poisonguard.data.schemas import Sink, stable_digest
from poisonguard.methods.core import PoisonGuardEngine
from poisonguard.metrics.ingestion import aggregate_measurements, load_measurements
from poisonguard.metrics.metrics import (
    admission_rate,
    false_quarantine_rate,
)
from poisonguard.models.external_trainer import (
    MobileFineTunerTrainer,
    hash_directory,
)
from poisonguard.telemetry.android import AndroidTelemetryImporter
from poisonguard.utils.io import (
    ArtifactExistsError,
    load_config,
    sha256_file,
    write_immutable_json,
    write_immutable_jsonl,
    write_json,
)


class RealExperimentNotReady(RuntimeError):
    """Raised when a real run is requested without all required assets."""


@dataclass(frozen=True)
class AssetStatus:
    name: str
    path: str | None
    exists: bool
    required: bool


def _path_from_config(config: dict[str, Any], dotted: str) -> Path | None:
    current: Any = config
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if current is None:
        return None
    return Path(str(current))


def _value_from_config(config: Mapping[str, Any], dotted: str, default: Any = None) -> Any:
    current: Any = config
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _digest_value(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def _render_arguments(arguments: Sequence[Any], context: Mapping[str, Any]) -> list[str]:
    rendered: list[str] = []
    for item in arguments:
        try:
            rendered.append(str(item).format_map(context))
        except KeyError as exc:
            raise RealExperimentNotReady(
                f"missing command template value: {exc.args[0]}") from exc
    return rendered


def validate_real_assets(config: dict[str, Any]) -> list[AssetStatus]:
    """Return the status of every asset needed for a real experiment."""
    statuses: list[AssetStatus] = []

    data_root = _path_from_config(config, "data.root")
    statuses.append(AssetStatus("data_root", str(data_root) if data_root else None,
                                bool(data_root and data_root.is_dir()), True))
    if data_root is not None and data_root.is_dir():
        statuses.append(AssetStatus(
            "normalized_events", str(data_root / "poisonguard_events.jsonl"),
            (data_root / "poisonguard_events.jsonl").is_file(), True))

    model_root = _path_from_config(config, "model.root")
    statuses.append(AssetStatus("model_root", str(model_root) if model_root else None,
                                bool(model_root and model_root.is_dir()), True))
    if model_root is not None and model_root.is_dir():
        statuses.append(AssetStatus("model_config", str(model_root / "config.json"),
                                    (model_root / "config.json").is_file(), True))
        statuses.append(AssetStatus("model_weights", str(model_root / "model.safetensors"),
                                    (model_root / "model.safetensors").is_file(), True))

    trainer_binary = _path_from_config(config, "external.trainer_binary")
    statuses.append(AssetStatus("trainer_binary", str(trainer_binary) if trainer_binary else None,
                                bool(trainer_binary and trainer_binary.is_file()), True))

    for section in ("attacks", "baselines"):
        specs = _value_from_config(config, f"external.{section}", {}) or {}
        if not isinstance(specs, Mapping):
            continue
        for name, spec in specs.items():
            if not isinstance(spec, Mapping):
                continue
            root = spec.get("repository_root") or spec.get("root")
            root_path = Path(str(root)) if root else None
            statuses.append(AssetStatus(
                f"{section}.{name}.repository_root", str(root_path) if root_path else None,
                bool(root_path and root_path.is_dir()), True))
            command = spec.get("command")
            statuses.append(AssetStatus(
                f"{section}.{name}.command",
                "configured" if command else None, bool(command), True))

    telemetry_path = _path_from_config(config, "external.telemetry.path")
    if telemetry_path is not None:
        statuses.append(AssetStatus(
            "telemetry", str(telemetry_path), telemetry_path.is_file(), True))

    for name, dotted in {
        "amemguard_root": "external.amemguard_root",
        "approximate_unlearning_root": "external.approximate_unlearning_root",
        "android_harness_root": "external.android_harness_root",
    }.items():
        path = _path_from_config(config, dotted)
        statuses.append(AssetStatus(name, str(path) if path else None,
                                    bool(path and path.exists()), False))

    return statuses


def missing_required_assets(config: dict[str, Any]) -> list[AssetStatus]:
    return [status for status in validate_real_assets(config)
            if status.required and not status.exists]


def _require_ready(config: dict[str, Any]) -> None:
    missing = missing_required_assets(config)
    if missing:
        raise RealExperimentNotReady(
            "missing required real-experiment assets: " +
            ", ".join(status.name for status in missing))


def _require_empty_target(target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        raise ArtifactExistsError(
            f"refusing to reuse non-empty real experiment output directory: {target}")
    target.mkdir(parents=True, exist_ok=True)


def run_real_asset_check(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/real_asset_check"))
    target.mkdir(parents=True, exist_ok=True)
    statuses = validate_real_assets(config)
    missing = missing_required_assets(config)
    payload = {
        "label": "real asset check, not a paper result",
        "config": str(config_path),
        "assets": [asdict(status) for status in statuses],
        "ready": not missing,
        "missing_required": [status.name for status in missing],
    }
    output = target / "real_asset_check.json"
    write_json(output, payload)
    return output


def run_real_training_probe(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    """Run one external trainer probe and record its manifest.

    This is deliberately not a benchmark. It proves only that the pinned trainer
    can execute on the supplied data/model and lets the run be hashed.
    """
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/real_probe"))
    target.mkdir(parents=True, exist_ok=True)

    _require_ready(config)

    data_root = _path_from_config(config, "data.root")
    model_root = _path_from_config(config, "model.root")
    trainer_binary = _path_from_config(config, "external.trainer_binary")
    trainer = MobileFineTunerTrainer(
        binary=trainer_binary,  # type: ignore[arg-type]
        model_dir=model_root,
        timeout_seconds=int(config.get("real", {}).get("timeout_seconds", 3600)),
    )
    extra_args = list(config.get("real", {}).get("extra_args", []))
    if not extra_args:
        extra_args = list(config.get("external", {}).get("trainer_args", []))
    result = trainer.run(data_dir=data_root, output_dir=target / "trainer_output",
                         extra_args=extra_args)

    manifest = {
        "label": "real trainer probe, not a paper result",
        "config": str(config_path),
        "trainer": result.trainer,
        "command": result.command,
        "return_code": result.return_code,
        "duration_seconds": result.duration_seconds,
        "output_hashes": result.output_hashes,
        "note": "No ASR, utility, recovery, or systems metric is computed by this probe.",
    }
    output = target / "real_training_probe.json"
    write_json(output, manifest)
    return output


def _benign_event(event: Any) -> bool:
    label = str(event.metadata.get("label", "")).lower()
    return event.user_authored is True or label in {"ham", "benign", "clean", "nonspam"}


def run_real_policy_simulation(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    """Run PoisonGuard's reference policy over a normalized real event manifest.

    This is a policy/lifecycle simulation. It does not train a model, run an
    attack, or produce ASR/utility results for the paper.
    """
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/real_policy_simulation"))
    target.mkdir(parents=True, exist_ok=True)

    data_root = _path_from_config(config, "data.root")
    if data_root is None or not data_root.is_dir():
        raise RealExperimentNotReady("data.root must be a provisioned directory")
    manifest = data_root / "poisonguard_events.jsonl"
    if not manifest.is_file():
        raise RealExperimentNotReady(f"normalized event manifest not found: {manifest}")
    events = sorted(JsonlEventAdapter(manifest).iter_events(),
                    key=lambda event: (event.capture_time, event.event_id))

    from poisonguard.data.schemas import EnvironmentRecord

    environment_record = EnvironmentRecord(
        code_version="poisonguard-reference",
        model_hash=str(config.get("model", {}).get("hash", "unspecified")),
        tokenizer_hash=str(config.get("model", {}).get("tokenizer_hash", "unspecified")),
        optimizer_hash="reference-policy-simulation",
        policy_hash=stable_digest(config.get("policy", {})),
        backend="reference-policy-simulation",
        seed=int(config.get("seed", 0)),
        deterministic=True,
    )
    engine = PoisonGuardEngine(environment_record)

    benign_memory_decisions = []
    benign_training_decisions = []
    all_memory_decisions = []
    all_training_decisions = []
    for event in events:
        decisions = engine.ingest(event)
        memory_decision = decisions[Sink.MEMORY]
        training_decision = decisions[Sink.TRAIN]
        all_memory_decisions.append(memory_decision)
        all_training_decisions.append(training_decision)
        if _benign_event(event):
            benign_memory_decisions.append(memory_decision)
            benign_training_decisions.append(training_decision)

    laundering_successes = 0
    laundering_failures = 0
    for record_id in list(engine.memory):
        try:
            engine.create_training_example_from_memory(record_id)
            laundering_successes += 1
        except ValueError:
            laundering_failures += 1

    payload = {
        "label": "real policy simulation on normalized events, not a paper result",
        "config": str(config_path),
        "events": len(events),
        "memory_admission_rate": admission_rate(all_memory_decisions),
        "training_admission_rate": admission_rate(all_training_decisions),
        "memory_false_quarantine_rate": false_quarantine_rate(benign_memory_decisions),
        "training_false_quarantine_rate": false_quarantine_rate(benign_training_decisions),
        "benign_event_count": len(benign_memory_decisions),
        "memory_records": len(engine.memory),
        "training_eligible_events": len(engine.eligible),
        "laundering_edges_created": laundering_successes,
        "laundering_edges_blocked": laundering_failures,
        "active_checkpoint_id": engine.active_checkpoint_id,
        "state_digest": engine.state_digest(),
        "note": "No ASR, clean utility, model quality, or systems metric is computed.",
    }
    output = target / "real_policy_simulation.json"
    write_json(output, payload)
    return output


def prepare_real_input(config: dict[str, Any], target: Path) -> dict[str, Any]:
    """Create a deterministic, immutable input manifest from normalized events."""
    data_root = _path_from_config(config, "data.root")
    if data_root is None or not data_root.is_dir():
        raise RealExperimentNotReady("data.root must be a provisioned directory")
    source = data_root / "poisonguard_events.jsonl"
    if not source.is_file():
        raise RealExperimentNotReady(f"normalized event manifest not found: {source}")

    events = sorted(JsonlEventAdapter(source).iter_events(),
                    key=lambda event: (event.capture_time, event.event_id))
    channels = config.get("data", {}).get("channels")
    if channels:
        wanted = {str(channel) for channel in channels}
        events = [event for event in events if event.channel.value in wanted]
    limit = config.get("data", {}).get("event_limit")
    if limit is not None:
        events = events[:int(limit)]
    if not events:
        raise RealExperimentNotReady("event selection produced zero events")

    events_path = target / "input_events.jsonl"
    write_immutable_jsonl(events_path, [event.to_dict() for event in events])
    ids_digest = hashlib.sha256(
        "".join(f"{event.event_id}\n" for event in events).encode("utf-8")).hexdigest()
    payload = {
        "label": "normalized real input manifest, not a paper result",
        "config_digest": _digest_value(config),
        "source_events": str(source),
        "source_events_sha256": sha256_file(source),
        "input_events": str(events_path),
        "input_events_sha256": sha256_file(events_path),
        "event_count": len(events),
        "event_ids_sha256": ids_digest,
        "channels": sorted({event.channel.value for event in events}),
        "seed": config.get("seed"),
    }
    write_immutable_json(target / "input_manifest.json", payload)
    return payload


def run_real_protocol(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    """Prepare inputs, run pinned commands, and write an immutable run manifest.

    No metric is computed here. Every external method must be configured with a
    repository root and an executable command; otherwise loading fails loudly.
    """
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/real_protocol"))
    _require_ready(config)
    _require_empty_target(target)

    input_payload = prepare_real_input(config, target)
    manifest_path = target / "input_manifest.json"
    model_root = _path_from_config(config, "model.root")
    trainer_binary = _path_from_config(config, "external.trainer_binary")
    seed = config.get("seed", 0)
    context = {
        "seed": seed,
        "output_dir": str(target),
        "input_manifest": str(manifest_path),
        "input_events": input_payload["input_events"],
        "data_root": str(_path_from_config(config, "data.root")),
        "model_dir": str(model_root),
        "model_hash": str(config.get("model", {}).get("hash", "unspecified")),
        "lora_rank": config.get("model", {}).get("lora_rank"),
        "sequence_length": config.get("model", {}).get("sequence_length"),
        "batch_size": config.get("model", {}).get("batch_size"),
    }

    attack_records: list[dict[str, Any]] = []
    attack_specs = config.get("external", {}).get("attacks", {}) or {}
    for name, spec in attack_specs.items():
        adapter = build_attack_adapter(name, spec)
        merged = dict(spec)
        merged.setdefault("seed", seed)
        merged["template_values"] = dict(context)
        output = target / "attacks" / f"{_slug(name)}.json"
        adapter.generate(manifest_path, output, merged)
        attack_records.append({
            "name": name,
            "path": str(output),
            "sha256": sha256_file(output),
            "provenance": adapter.provenance(),
        })

    baseline_records: list[dict[str, Any]] = []
    baseline_specs = config.get("external", {}).get("baselines", {}) or {}
    for name, spec in baseline_specs.items():
        adapter = build_baseline_adapter(name, spec)
        merged = dict(spec)
        merged.setdefault("seed", seed)
        merged["template_values"] = dict(context)
        output_dir = target / "baselines" / _slug(name)
        adapter.run(manifest_path, output_dir, merged)
        baseline_records.append({
            "name": name,
            "path": str(output_dir),
            "command": list(spec.get("command", ())),
            "provenance": adapter.provenance(),
        })

    extra_args = _render_arguments(
        config.get("external", {}).get("trainer_args", []) or [], context)
    trainer = MobileFineTunerTrainer(
        binary=trainer_binary,  # type: ignore[arg-type]
        model_dir=model_root,
        timeout_seconds=int(config.get("external", {}).get("timeout_seconds", 3600)),
    )
    trainer_result = trainer.run(
        data_dir=target, output_dir=target / "trainer_output", extra_args=extra_args)

    telemetry_record: dict[str, Any] | None = None
    telemetry_spec = config.get("external", {}).get("telemetry", {}) or {}
    telemetry_path = telemetry_spec.get("path")
    if telemetry_path:
        importer = AndroidTelemetryImporter(telemetry_path)
        records = importer.load()
        summary = AndroidTelemetryImporter.summarize(records)
        expected = telemetry_spec.get("expected_device")
        observed = summary.get("devices", [])
        telemetry_record = {
            "path": str(telemetry_path),
            "sha256": importer.sha256,
            "summary": summary,
            "expected_device": expected,
            "expected_device_matches": (
                expected in observed if expected is not None else None),
        }

    metric_files: list[dict[str, str]] = []
    for raw_path in config.get("metrics", {}).get("results", []) or []:
        path = Path(str(raw_path))
        if not path.is_file():
            raise RealExperimentNotReady(f"configured measured result file missing: {path}")
        metric_files.append({"path": str(path), "sha256": sha256_file(path)})

    manifest = {
        "label": "real experiment run manifest, not a paper result until independently validated",
        "paper_ready": False,
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "config_digest": _digest_value(config),
        "seed": seed,
        "input": input_payload,
        "assets": [asdict(status) for status in validate_real_assets(config)],
        "attacks": attack_records,
        "baselines": baseline_records,
        "trainer": {
            "name": trainer_result.trainer,
            "command": trainer_result.command,
            "return_code": trainer_result.return_code,
            "duration_seconds": trainer_result.duration_seconds,
            "output_hashes": trainer_result.output_hashes,
        },
        "telemetry": telemetry_record,
        "metric_files": metric_files,
        "output_files_excluding_manifest": hash_directory(target),
        "note": (
            "External commands ran only from explicit config pins. No ASR, utility, "
            "rollback, or systems metric is computed by this stage."
        ),
    }
    output = target / "real_run_manifest.json"
    write_immutable_json(output, manifest)
    return output


def aggregate_real_metrics(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    """Aggregate only explicit measured external result files."""
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/real_protocol"))
    target.mkdir(parents=True, exist_ok=True)

    metric_config = config.get("metrics", {}) or {}
    measurements = load_measurements(
        metric_config.get("results", []) or [],
        required_fields=metric_config.get("required_fields", []) or [],
    )
    payload = aggregate_measurements(measurements)
    payload["config"] = str(config_path)
    payload["config_sha256"] = sha256_file(config_path)

    run_manifest = target / "real_run_manifest.json"
    if run_manifest.is_file():
        payload["run_manifest"] = str(run_manifest)
        payload["run_manifest_sha256"] = sha256_file(run_manifest)

    telemetry_spec = config.get("external", {}).get("telemetry", {}) or {}
    telemetry_path = telemetry_spec.get("path")
    if telemetry_path:
        importer = AndroidTelemetryImporter(telemetry_path)
        payload["telemetry"] = {
            "path": str(telemetry_path),
            "sha256": importer.sha256,
            "summary": AndroidTelemetryImporter.summarize(importer.load()),
        }

    output = target / "real_metrics_aggregate.json"
    write_immutable_json(output, payload)
    return output
