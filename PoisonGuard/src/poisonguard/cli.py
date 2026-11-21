from __future__ import annotations

import argparse
from pathlib import Path

from poisonguard.data.adapters import JsonlEventAdapter
from poisonguard.utils.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="poisonguard", description="PoisonGuard research reference implementation")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the synthetic smoke test")
    demo.add_argument("--config", default="configs/synthetic_demo.yaml")
    demo.add_argument("--output")
    experiment = sub.add_parser("experiment", help="run a configured lightweight stage")
    experiment.add_argument("--config", required=True)
    experiment.add_argument("--stage", choices=["calibrate", "evaluate", "ablate"], required=True)
    experiment.add_argument("--output")
    plot = sub.add_parser("plot", help="plot an existing result JSON")
    plot.add_argument("--input", required=True)
    plot.add_argument("--output", required=True)
    validate = sub.add_parser("validate-data", help="validate normalized event JSONL")
    validate.add_argument("--input", required=True)
    real = sub.add_parser("real", help="real experiment protocol stage")
    real.add_argument("--config", required=True)
    real.add_argument("--stage", choices=["assets", "probe", "policy", "run", "aggregate"],
                      required=True)
    real.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    if args.command == "demo":
        from poisonguard.experiments.runner import run_synthetic_demo
        output = run_synthetic_demo(args.config, args.output)
    elif args.command == "experiment":
        from poisonguard.experiments.runner import run_stage
        output = run_stage(args.config, args.stage, args.output)
    elif args.command == "plot":
        from poisonguard.experiments.plot_results import plot_results
        output = plot_results(args.input, args.output)
    elif args.command == "real":
        from poisonguard.experiments.real_runner import (
            aggregate_real_metrics,
            run_real_asset_check,
            run_real_policy_simulation,
            run_real_protocol,
            run_real_training_probe,
        )
        stages = {
            "assets": run_real_asset_check,
            "probe": run_real_training_probe,
            "policy": run_real_policy_simulation,
            "run": run_real_protocol,
            "aggregate": aggregate_real_metrics,
        }
        output = stages[args.stage](args.config, args.output)
    else:
        count = sum(1 for _ in JsonlEventAdapter(Path(args.input)).iter_events())
        print(f"validated {count} events")
        return 0
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
