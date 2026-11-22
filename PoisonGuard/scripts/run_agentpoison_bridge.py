"""Run pinned AgentPoison trigger optimization against an OpenAI-compatible endpoint.

This bridge executes the pinned upstream script and records its native trigger
artifact. It never computes ASR, FQR, or utility and never emulates the attack.
Every output is labelled "not a paper result" until independently validated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ENTRYPOINT = "algo/trigger_optimization.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gpt-model", default="qwen2.5:7b-instruct")
    parser.add_argument("--num-iter", type=int, default=20)
    parser.add_argument("--num-grad-iter", type=int, default=5)
    parser.add_argument("--num-cand", type=int, default=20)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--eval-batch-size", type=int, default=8)
    parser.add_argument("--ppl-seq-batch", type=int, default=4)
    parser.add_argument("--target-batch-size", type=int, default=2)
    parser.add_argument("--target-sample-size", type=int, default=4)
    parser.add_argument("--retriever-path", required=True)
    parser.add_argument("--ppl-model-path", required=True)
    args = parser.parse_args()

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not base_url or not api_key:
        raise SystemExit(
            "AgentPoison bridge requires OPENAI_BASE_URL and OPENAI_API_KEY "
            "(local Ollama endpoint is acceptable)")

    repo_root = Path.cwd()
    if not (repo_root / ENTRYPOINT).is_file():
        raise SystemExit(f"pinned AgentPoison entrypoint missing: {repo_root / ENTRYPOINT}")

    input_manifest = Path(args.input_manifest)
    output_manifest = Path(args.output_manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_manifest.exists():
        raise SystemExit(f"refusing to overwrite bridge output: {output_manifest}")

    command = [
        sys.executable, ENTRYPOINT,
        "--agent", "qa",
        "--algo", "ap",
        "--model", "dpr-ctx_encoder-single-nq-base",
        "--save_dir", str(output_dir),
        "--seed", str(args.seed),
        "--use_gpt",
        "--gpt_model", args.gpt_model,
        "--num_iter", str(args.num_iter),
        "--num_grad_iter", str(args.num_grad_iter),
        "--num_cand", str(args.num_cand),
        "--num_adv_passage_tokens", "10",
        "--exclude_special",
        "--device", args.device,
        "--per_gpu_eval_batch_size", str(args.eval_batch_size),
        "--ppl_seq_batch", str(args.ppl_seq_batch),
        "--target_batch_size", str(args.target_batch_size),
        "--target_sample_size", str(args.target_sample_size),
        "--retriever_path", args.retriever_path,
        "--ppl_model_path", args.ppl_model_path,
    ]
    # Upstream names its run directory with str(datetime.now()), which contains
    # colons and is invalid on Windows. Patch only that expression at runtime
    # and restore the pinned file immediately afterwards. The clean-tree gate
    # runs before this bridge, so no permanent repository change is made.
    entrypoint = repo_root / ENTRYPOINT
    original_source = entrypoint.read_text(encoding="utf-8")
    unsafe = "str(datetime.datetime.now())"
    safe = "datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')"
    if unsafe not in original_source:
        raise SystemExit("upstream timestamp expression not found; refusing to patch blindly")
    entrypoint.write_text(original_source.replace(unsafe, safe), encoding="utf-8")

    # Upstream opens StrategyQA JSON with the platform default encoding. On
    # Windows that is cp1252 and fails on non-ASCII question text. Force UTF-8
    # mode for the child process without touching the pinned source.
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    started = datetime.now(timezone.utc)
    try:
        completed = subprocess.run(command, cwd=repo_root, env=child_env, check=False)
    finally:
        entrypoint.write_text(original_source, encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit(f"AgentPoison entrypoint failed with code {completed.returncode}")

    triggers = sorted(output_dir.rglob("trigger.json"))
    if not triggers:
        raise SystemExit("AgentPoison finished without writing trigger.json")
    trigger_path = triggers[-1]
    trigger = json.loads(trigger_path.read_text(encoding="utf-8"))

    payload = {
        "label": "AgentPoison trigger artifact via pinned upstream script, not a paper result",
        "paper_ready": False,
        "attack_family": "AgentPoison",
        "repository_role": "attack",
        "seed": args.seed,
        "input_manifest": str(input_manifest),
        "input_manifest_sha256": _sha256(input_manifest) if input_manifest.is_file() else "",
        "endpoint": base_url,
        "gpt_model": args.gpt_model,
        "command": command,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_artifact": str(trigger_path),
        "trigger_artifact_sha256": _sha256(trigger_path),
        "trigger": trigger,
        "note": (
            "Trigger optimization only. No ASR, FQR, utility, or rollback metric "
            "is computed by this bridge."
        ),
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
