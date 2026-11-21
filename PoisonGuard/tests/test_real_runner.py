import json
import sys
from pathlib import Path

import pytest

import yaml

from poisonguard.experiments.real_runner import (
    RealExperimentNotReady,
    aggregate_real_metrics,
    prepare_real_input,
    run_real_asset_check,
    run_real_policy_simulation,
    run_real_protocol,
    run_real_training_probe,
    validate_real_assets,
)
from poisonguard.metrics.ingestion import (
    MeasurementIncomplete,
    aggregate_measurements,
    load_measurements,
)
from poisonguard.utils.io import ArtifactExistsError, write_immutable_json


def _write_config(tmp_path: Path, ready: bool) -> Path:
    data_root = tmp_path / "data"
    model_root = tmp_path / "model"
    data_root.mkdir(exist_ok=True)
    model_root.mkdir(exist_ok=True)
    if ready:
        (data_root / "poisonguard_events.jsonl").write_text("{}\n", encoding="utf-8")
        (model_root / "config.json").write_text("{}", encoding="utf-8")
        (model_root / "model.safetensors").write_bytes(b"x")
    trainer = tmp_path / "trainer.py"
    trainer.write_text("print('ok')\n", encoding="utf-8")
    config = {
        "output_dir": str(tmp_path / "out"),
        "data": {"root": str(data_root)},
        "model": {"root": str(model_root)},
        "external": {"trainer_binary": str(trainer)},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_validate_reports_missing_assets(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=False)
    import yaml

    config = yaml.safe_load(config_path.read_text())
    statuses = validate_real_assets(config)
    missing = [s.name for s in statuses if s.required and not s.exists]
    assert "normalized_events" in missing
    assert "model_config" in missing


def test_asset_check_writes_json(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=False)
    output = run_real_asset_check(config_path, tmp_path / "check")
    payload = json.loads(output.read_text())
    assert payload["ready"] is False
    assert "not a paper result" in payload["label"]


def test_probe_raises_when_not_ready(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=False)
    with pytest.raises(RealExperimentNotReady):
        run_real_training_probe(config_path, tmp_path / "probe")


def test_probe_runs_with_fake_trainer(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    # Replace trainer binary with Python interpreter and a -c script.
    import yaml

    config = yaml.safe_load(config_path.read_text())
    code = (
        "import pathlib, sys\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--output_dir') + 1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'adapter.bin').write_bytes(b'abc')\n"
    )
    trainer = tmp_path / "trainer.py"
    trainer.write_text(code, encoding="utf-8")
    config["external"]["trainer_binary"] = sys.executable
    config.setdefault("real", {})["extra_args"] = ["-c", code]
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    output = run_real_training_probe(config_path, tmp_path / "probe")
    payload = json.loads(output.read_text())
    assert payload["return_code"] == 0
    assert "adapter.bin" in payload["output_hashes"]
    assert "not a paper result" in payload["label"]


def test_policy_simulation_runs_on_normalized_events(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    import yaml

    config = yaml.safe_load(config_path.read_text())
    data_root = Path(config["data"]["root"])
    (data_root / "poisonguard_events.jsonl").write_text(
        json.dumps({
            "event_id": "e1",
            "payload": "hello",
            "capture_time": 1.0,
            "app_id": "app",
            "channel": "typed",
            "sender": None,
            "user_authored": True,
            "parent_ids": [],
            "schema_version": "1",
            "metadata": {"label": "benign"},
        }) + "\n",
        encoding="utf-8",
    )
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    output = run_real_policy_simulation(config_path, tmp_path / "simulation")
    payload = json.loads(output.read_text())
    assert payload["events"] == 1
    assert payload["memory_false_quarantine_rate"] == 0.0
    assert "not a paper result" in payload["label"]


def _valid_event(event_id: str, channel: str = "typed") -> dict:
    return {
        "event_id": event_id,
        "payload": "hello " + event_id,
        "capture_time": 1.0,
        "app_id": "app",
        "channel": channel,
        "sender": None,
        "user_authored": True,
        "parent_ids": [],
        "schema_version": "1",
        "metadata": {"label": "benign"},
    }


def test_prepare_real_input_is_deterministic_and_filtered(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data_root = Path(config["data"]["root"])
    with (data_root / "poisonguard_events.jsonl").open("w", encoding="utf-8") as handle:
        for item in (_valid_event("b", "sms"), _valid_event("a", "typed")):
            handle.write(json.dumps(item) + "\n")
    config["data"]["channels"] = ["typed"]
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    target = tmp_path / "prepared"
    target.mkdir()
    payload = prepare_real_input(config, target)
    assert payload["event_count"] == 1
    assert payload["channels"] == ["typed"]
    assert (target / "input_events.jsonl").is_file()
    assert (target / "input_manifest.json").is_file()
    with pytest.raises(ArtifactExistsError):
        prepare_real_input(config, target)


def test_write_immutable_json_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    write_immutable_json(target, {"label": "not a paper result"})
    with pytest.raises(ArtifactExistsError):
        write_immutable_json(target, {"label": "not a paper result"})


def test_protocol_refuses_nonempty_output_directory(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    target = tmp_path / "protocol"
    target.mkdir()
    (target / "old.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactExistsError):
        run_real_protocol(config_path, target)


def test_protocol_fails_when_attack_command_missing(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data_root = Path(config["data"]["root"])
    (data_root / "poisonguard_events.jsonl").write_text(
        json.dumps(_valid_event("e1")) + "\n", encoding="utf-8")
    repo = tmp_path / "attack_repo"
    repo.mkdir()
    config["external"]["attacks"] = {"agentpoison": {"repository_root": str(repo), "command": []}}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(RealExperimentNotReady, match="command"):
        run_real_protocol(config_path, tmp_path / "protocol")


def test_protocol_and_aggregation_run_pinned_fake_commands(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data_root = Path(config["data"]["root"])
    (data_root / "poisonguard_events.jsonl").write_text(
        json.dumps(_valid_event("e1")) + "\n", encoding="utf-8")

    attack_repo = tmp_path / "attack_repo"
    baseline_repo = tmp_path / "baseline_repo"
    attack_repo.mkdir()
    baseline_repo.mkdir()
    attack_script = tmp_path / "attack.py"
    attack_script.write_text(
        "import json, sys\n"
        "json.dump({'attack_family': 'AgentPoison', 'poisoned': 1},\n"
        "          open(sys.argv[1], 'w', encoding='utf-8'))\n",
        encoding="utf-8",
    )
    baseline_script = tmp_path / "baseline.py"
    baseline_script.write_text(
        "import json, pathlib, sys\n"
        "root = pathlib.Path(sys.argv[1])\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        "(root / 'result.json').write_text('{}', encoding='utf-8')\n",
        encoding="utf-8",
    )
    config["external"]["attacks"] = {
        "agentpoison": {
            "repository_root": str(attack_repo),
            "command": [sys.executable, str(attack_script), "{output_manifest}"],
        }
    }
    config["external"]["baselines"] = {
        "amemguard": {
            "repository_root": str(baseline_repo),
            "command": [sys.executable, str(baseline_script), "{output_dir}"],
        }
    }
    config["external"]["trainer_binary"] = sys.executable
    trainer_code = (
        "import pathlib, sys\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--output_dir') + 1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'adapter.bin').write_bytes(b'abc')\n"
    )
    config["external"]["trainer_args"] = ["-c", trainer_code]

    telemetry_path = tmp_path / "telemetry.json"
    telemetry_path.write_text(json.dumps({
        "label": "device pilot telemetry, not a paper result",
        "records": [{"device": "Xiaomi 13T", "training_step_ms": 3800,
                     "peak_rss_kb": 2100000, "temperature_c": 34.0}],
    }), encoding="utf-8")
    config["external"]["telemetry"] = {"path": str(telemetry_path),
                                       "expected_device": "Xiaomi 13T"}

    measured = tmp_path / "measured.json"
    measured.write_text(json.dumps({
        "label": "measured external result, not a paper result until independently validated",
        "defense": "PoisonGuard",
        "attack_family": "AgentPoison",
        "seed": 42,
        "metrics": {
            "asr_before": 0.8,
            "asr_after": 0.1,
            "fqr": 0.02,
            "clean_utility": 0.9,
            "utility_after": 0.88,
            "rollback": {"exact": True, "elapsed_ms": 120, "storage_kb": 16},
        },
        "energy": {"source": "external_power_monitor", "joules": 3.5},
    }), encoding="utf-8")
    config["metrics"] = {"results": [str(measured)], "required_fields": ["metrics.asr_after"]}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    output = run_real_protocol(config_path, tmp_path / "protocol")
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["paper_ready"] is False
    assert "not a paper result" in manifest["label"]
    assert len(manifest["attacks"]) == 1
    assert len(manifest["baselines"]) == 1
    assert manifest["telemetry"]["expected_device_matches"] is True
    assert manifest["metric_files"][0]["sha256"]

    summary_path = aggregate_real_metrics(config_path, tmp_path / "protocol")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["result_count"] == 1
    assert summary["summary"]["asr_reduction"]["median"] == pytest.approx(0.7)
    assert summary["summary"]["energy_j_external"]["count"] == 1
    assert summary["summary"]["rollback_exact"]["rate"] == 1.0
    assert "not a paper result" in summary["label"]


def test_aggregation_fails_without_measured_results(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, ready=True)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["metrics"] = {"results": []}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(MeasurementIncomplete, match="no measured result files"):
        aggregate_real_metrics(config_path, tmp_path / "empty_aggregate")


def test_aggregation_fails_on_missing_required_field(tmp_path: Path) -> None:
    measured = tmp_path / "measured.json"
    measured.write_text(json.dumps({
        "label": "measured external result, not a paper result until independently validated",
        "defense": "PoisonGuard",
        "attack_family": "AgentPoison",
        "seed": 1,
        "metrics": {"asr_before": 0.7, "asr_after": 0.2},
    }), encoding="utf-8")
    with pytest.raises(MeasurementIncomplete, match="metrics.fqr"):
        load_measurements([measured], required_fields=["metrics.fqr"])


def test_aggregation_keeps_android_energy_secondary(tmp_path: Path) -> None:
    measured = tmp_path / "measured.json"
    measured.write_text(json.dumps({
        "label": "measured external result, not a paper result until independently validated",
        "defense": "PoisonGuard",
        "attack_family": "AgentPoison",
        "seed": 1,
        "metrics": {"asr_before": 0.7, "asr_after": 0.2,
                    "rollback": {"exact": False}},
        "energy": {"source": "android_battery_counters", "joules": 4.2},
    }), encoding="utf-8")
    summary = aggregate_measurements(load_measurements([measured]))
    assert summary["summary"]["energy_j_external"]["count"] == 0
    assert summary["summary"]["energy_j_android_secondary"]["median"] == pytest.approx(4.2)
