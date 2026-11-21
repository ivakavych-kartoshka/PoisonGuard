# PoisonGuard

Reference implementation for *PoisonGuard: Provenance-Carried Data Selection and Lineage Rollback for Poison-Resilient On-Device SLM Personalization*.

PoisonGuard protects two persistent personalization sinks—retrieval memory and LoRA adapters—using authenticated provenance, sink-specific admission, shared typed lineage, candidate quarantine/audit, atomic promotion, and deterministic rollback-and-replay. The local implementation is a state-machine reference with a lightweight numerical adapter simulator; it is designed to be extended with Android and real SLM backends.

> **Result warning:** No paper-level experimental results are claimed by this repository unless real benchmark outputs are generated and their provenance is recorded. All included/generated demo outputs are labeled “synthetic smoke-test output, not a paper result.”
>
> **Provisioning warning:** This repository does not automatically download datasets or run paper-level experiments. Real experiments are intended to be executed on EC2 after the required datasets, benchmarks, models, and credentials are manually provisioned.

## Quick start

Python 3.11+ is the supported runtime.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m poisonguard.cli --help
python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml
python -m pytest -q
```

The demo writes only computed synthetic artifacts under `outputs/synthetic_demo/`: normalized events, captured config and metadata, JSON results, manifest, and a labeled PNG plot.

## Paper-to-code map

| Paper object | Implementation |
|---|---|
| Eq. 1 provenance event | `data/schemas.py::Event` |
| Eq. 2 LoRA update | `models/adapters.py::apply_lora` |
| Eq. 3 sink policy / least-trust inheritance | `methods/policy.py::DefaultPolicy` |
| Shared typed DAG | `methods/lineage.py::LineageGraph` |
| Algorithm 1 admission/quarantine/promotion | `methods/core.py::PoisonGuardEngine` |
| Algorithm 2 rollback-and-replay | `methods/rollback.py::rollback_and_replay` |
| Eqs. 10–14 and experimental metrics | `metrics/` |
| Protocol, calibration, ablations, plots | `experiments/` and `scripts/` |

The complete row-level mapping is in `audits/paper_to_code_traceability.csv`.

## Implemented algorithms and metrics

Algorithm 1 binds events to immutable IDs, records independent memory/training decisions, creates memory or quarantine entries, forms lineage-complete windows, trains candidates in a non-serving namespace, applies lineage/behavior/update audits, and promotes only with an epoch/head check. Algorithm 2 invalidates the inclusive descendant closure, restores the newest unaffected snapshot, verifies the environment digest, replays admissible events and training windows in logical order, swaps the recovered head, and emits a recovery certificate.

Metrics include ASR, laundering persistence, false quarantine/admission, admission and retrieval rates, accuracy, binary F1, parameter and output-distribution distances, bootstrap intervals, median/IQR/count, the contaminated-displacement bound, storage bound, and the deployment-objective evaluator. Hardware energy/thermal readings are external inputs, not fabricated values.

## Baselines

Implemented policy/state-machine baselines are no defense, memory-only sanitization, provenance without recovery, shared lineage without quarantine, quarantine without rollback, and exact clean replay/full retraining behavior. `baselines/external_wrappers.py` defines failure-loud adapters for A-MemGuard, NPO/approximate unlearning, and released attack implementations. Krum, Bulyan, FLTrust, FLAME, geometric-median aggregation, and FoolsGold are intentionally not implemented because the paper treats these multi-client methods as structurally inapplicable contrasts.

## Configuration and commands

YAML controls seed, output location, data/model backend, audit thresholds, training step size, synthetic counts, and policy choices. Config files are data only and cannot execute shell commands.

```bash
python scripts/run_experiment.py --config configs/experiment_template.yaml --stage calibrate
python scripts/run_experiment.py --config configs/experiment_template.yaml --stage evaluate
python scripts/run_experiment.py --config configs/experiment_template.yaml --stage ablate
python scripts/make_plots.py --input outputs/synthetic_demo/results.json --output outputs/synthetic_demo/replot.png
python -m poisonguard.cli validate-data --input /path/to/poisonguard_events.jsonl
```

## Real-data and EC2 use

LaMP, PersonaChat, AESLC, and the exact licensed Enron/SMS release must be acquired manually. Normalize each source to `poisonguard_events.jsonl`, set `data.root`, and pin a real trainer/model adapter before changing `mode`. No code path downloads a model or dataset. See `docs/data_format.md` and `docs/ec2_experiment_guide.md` for layout, manifest, licensing, and staged-run instructions.

## Real experiment workflow

Real runs are gated on manually provisioned assets. `configs/real_experiment_template.yaml`
contains explicit `null` placeholders for the trainer binary, attack/baseline
repositories, commands, commits or archive hashes, and telemetry file. No command
downloads or emulates a published method.

```bash
# 1. Asset gate (fails loudly; writes no metrics)
poisonguard real --config configs/real_experiment_template.yaml --stage assets

# 2. Prepare inputs and invoke pinned external commands; immutable manifests only
poisonguard real --config configs/real_experiment_template.yaml --stage run

# 3. Aggregate ONLY explicit measured result files
poisonguard real --config configs/real_experiment_template.yaml --stage aggregate
```

`--stage policy` runs the reference policy over normalized events without a
model. Every JSON artifact in `outputs/` carries a label containing
`not a paper result`; `tests/test_result_integrity.py` enforces this.
Energy values are used only when `energy.source` is `external_power_monitor`;
Android counter values are recorded as secondary data.

## On-device system pilot

`scripts/collect_qwen_step_pilot.py` collects repeated Qwen2.5-0.5B LoRA step
timings, RSS, and thermal/battery snapshots over adb. The output is labelled
`not a paper result` and contains no attack, baseline, utility, or energy claim.

## Repository layout

```text
configs/                 reproducible YAML configurations
src/poisonguard/         package: data, methods, models, metrics, baselines, experiments
scripts/                 demo, staged experiment, and plotting entry points
tests/                   offline unit and smoke tests
examples/synthetic_data/ example-only configuration
docs/                    formats, adapters, translation notes, EC2/reproducibility guides
audits/                  paper mapping, math, gaps, and result-integrity records
outputs/                 generated artifacts (ignored except .gitkeep)
```

## Reproducibility, limits, and gaps

Every runner captures its config, config digest, seed, interpreter/platform metadata, and a synthetic/real flag. Exact recovery is refused when the deterministic-environment premise is false or its digest mismatches. Tests require no network, model, or external data.

This repository does not establish OS-authenticated provenance, durable crash transactions, production concurrency, SLM quality, attack-detection efficacy, phone latency/energy/thermal cost, or benchmark superiority. Origin is not intent; retyping and unidentified poison remain residual risks. Payload erasure can also remove the data required for exact replay. Full gaps and author-confirmation items are tracked in `audits/implementation_gaps.md` and `TODO_IMPLEMENTATION.md`.
