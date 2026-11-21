from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from poisonguard.data.synthetic import generate_synthetic_events
from poisonguard.utils.io import load_config, write_json, write_jsonl
from .common import LABEL, run_metadata
from .plot_results import plot_results
from .run_ablation import run_ablation
from .run_calibration import run_calibration
from .run_evaluation import run_evaluation


def run_stage(config_path: str | Path, stage: str, output_dir: str | Path | None = None) -> Path:
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/run"))
    target.mkdir(parents=True, exist_ok=True)
    if stage == "calibrate":
        result: dict[str, Any] = run_calibration(config)
    elif stage == "evaluate":
        result = run_evaluation(config)
    elif stage == "ablate":
        result = run_ablation(config)
    else:
        raise ValueError(f"unknown stage: {stage}")
    output = target / f"{stage}_results.json"
    write_json(output, result)
    write_json(target / f"{stage}_metadata.json", run_metadata(config, str(config_path)))
    shutil.copyfile(config_path, target / f"{stage}_config.yaml")
    return output


def run_synthetic_demo(config_path: str | Path, output_dir: str | Path | None = None) -> Path:
    config_path = Path(config_path)
    config = load_config(config_path)
    target = Path(output_dir or config.get("output_dir", "outputs/synthetic_demo"))
    target.mkdir(parents=True, exist_ok=True)
    calibration = run_calibration(config)
    evaluation = run_evaluation(config)
    payload = {"label": LABEL, "calibration": calibration, "evaluation": evaluation}
    result_path = target / "results.json"
    write_json(result_path, payload)
    events, poison_ids = generate_synthetic_events(
        int(config.get("seed", 7)), int(config["synthetic"]["benign_count"]),
        int(config["synthetic"]["poison_count"]))
    write_jsonl(target / "events.jsonl", [event.to_dict() for event in events])
    write_json(target / "manifest.json", {"label": LABEL, "result": "results.json",
                                           "events": "events.jsonl", "plot": "metrics.png",
                                           "poison_event_ids": sorted(poison_ids)})
    write_json(target / "metadata.json", run_metadata(config, str(config_path)))
    shutil.copyfile(config_path, target / "config.yaml")
    plot_results(result_path, target / "metrics.png")
    return result_path
