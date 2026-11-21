# EC2 Experiment Guide

1. Choose an instance and encrypted volume appropriate to the real model; this repository itself is CPU-safe and GPU-optional.
2. Install Python 3.11+, clone/copy the repository, create a virtual environment, and run `pip install -e '.[dev]'` followed by `pytest -q`.
3. Manually acquire datasets under their licenses. Normalize them to the layout in `data_format.md`; do not place credentials in YAML or the repository.
4. Manually provision model/tokenizer checkpoints and record their cryptographic hashes and licenses. Implement/pin the external LoRA trainer interface before selecting it in config.
5. Clone external attack/baseline repositories manually, pin commits, inspect licenses, and implement the wrappers described in `baseline_adapters.md`.
6. Copy `configs/experiment_template.yaml` to a run-specific config. Set `data.root`, model roots, backend, ranks, seeds, policy/audit parameters, output directory, and external roots. Keep calibration probes independent of attack evaluation.
7. Run calibration first, inspect its manifest, then evaluation and ablation. Use at least five training seeds as recommended by the paper; choose final counts from pilot variance/power analysis.
8. Generate plots only from completed JSON result files and preserve raw logs, configs, environment manifests, lineage snapshots, failures, and exclusions.

```bash
python scripts/run_experiment.py --config configs/my_ec2_run.yaml --stage calibrate
python scripts/run_experiment.py --config configs/my_ec2_run.yaml --stage evaluate
python scripts/run_experiment.py --config configs/my_ec2_run.yaml --stage ablate
python scripts/make_plots.py --input outputs/my_run/evaluate_results.json --output outputs/my_run/metrics.png
```

The generic synthetic runner remains separate from real execution. For a real run, copy `configs/real_experiment_template.yaml`, fill every `null` with a manually provisioned path/command, then use `poisonguard real --stage assets|run|aggregate`. The real runner consumes normalized `poisonguard_events.jsonl`, invokes only pinned external commands, writes immutable manifests, and aggregates only explicit measured result files. `AndroidTelemetryImporter` records device traces; Android counter values are secondary and energy claims require `external_power_monitor`. EC2 can run model/benchmark computation, but actual mobile latency, temperature, throttling, and background-job behavior still require researcher-owned phones.
