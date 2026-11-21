"""Run a pinned MobileFineTuner device smoke probe and write a labelled JSON.

This is a host-side harness for ``MobileFineTunerTrainer``. It does not emulate
model math; it launches the provisioned Android app, captures its logcat, and
records the resulting step timings. Its output is explicitly not a paper result.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

STEP_RE = re.compile(r"step\s+(\d+)/(\d+)\s+loss=([0-9.eE+-]+)\s+time=(\d+)ms")
RSS_RE = re.compile(r"RSS=(\d+)KB")
LOSS_RE = re.compile(r"lastLoss=([0-9.eE+-]+)")


def adb(device, *args, timeout=30):
    command = ["adb"]
    if device:
        command.extend(["-s", device])
    command.extend(args)
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=timeout, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout


def wait_for_completion(device, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        last = adb(device, "logcat", "-d", "-s", "PoisonGuardQwenStep:I")
        if "Qwen pilot OK:" in last or "training step failed" in last:
            return last
        time.sleep(0.5)
    raise TimeoutError("MobileFineTuner probe did not finish before timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--package", default="com.poisonguard.qwenstep")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    adb(args.device, "shell", "am", "force-stop", args.package)
    adb(args.device, "logcat", "-c")
    adb(args.device, "shell", "monkey", "-p", args.package,
        "-c", "android.intent.category.LAUNCHER", "1")
    log = wait_for_completion(args.device, args.timeout)
    if "training step failed" in log:
        raise RuntimeError(f"MobileFineTuner probe failed:\n{log}")

    steps = [int(match.group(4)) for match in STEP_RE.finditer(log)]
    if not steps:
        raise RuntimeError("no MobileFineTuner step records found in logcat")
    rss_match = RSS_RE.search(log)
    loss_match = LOSS_RE.search(log)

    payload = {
        "label": "external trainer probe on Xiaomi 13T, not a paper result",
        "paper_ready": False,
        "device": args.device,
        "package": args.package,
        "model_dir": args.model_dir,
        "data_dir": args.data_dir,
        "step_times_ms": steps,
        "step_count": len(steps),
        "last_loss": float(loss_match.group(1)) if loss_match else None,
        "peak_rss_kb": int(rss_match.group(1)) if rss_match else None,
        "note": "Synthetic token workload; no ASR, utility, or energy claim.",
    }
    (output_dir / "probe.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
