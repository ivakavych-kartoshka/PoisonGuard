"""Collect a labelled on-device Qwen step-time pilot via adb.

This is a system microbenchmark only. It does not run attacks, baselines, an
evaluation harness, or an external power monitor. Its output is explicitly
labelled as not a paper result.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from poisonguard.metrics.aggregation import median_iqr_count

STEP_RE = re.compile(r"step\s+(\d+)/(\d+)\s+loss=([0-9.eE+-]+)\s+time=(\d+)ms")
RSS_RE = re.compile(r"RSS=(\d+)KB")
LOSS_RE = re.compile(r"lastLoss=([0-9.eE+-]+)")


def adb(device: str | None, *args: str, timeout: int = 30) -> str:
    command = ["adb"]
    if device:
        command.extend(["-s", device])
    command.extend(args)
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=timeout, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout


def battery_state(device: str | None) -> dict[str, Any]:
    text = adb(device, "shell", "dumpsys", "battery")
    result: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return {
        "level": _as_int(result.get("level")),
        "status": result.get("status"),
        "usb_powered": result.get("USB powered"),
        "ac_powered": result.get("AC powered"),
        "voltage_mv": _as_int(result.get("voltage")),
        "temperature_tenths_c": _as_int(result.get("temperature")),
    }


TEMPERATURE_RE = re.compile(
    r"Temperature\{mValue=([0-9.]+),\s*mType=\d+,\s*mName=([A-Z_]+),")


def thermal_state(device: str | None) -> dict[str, Any]:
    text = adb(device, "shell", "dumpsys", "thermalservice")
    temperatures = {
        match.group(2): float(match.group(1))
        for match in TEMPERATURE_RE.finditer(text)
    }
    return {
        "temperatures_c": temperatures,
        "skin_temperature_c": temperatures.get("SKIN"),
        "battery_temperature_c": temperatures.get("BATTERY"),
        "soc_temperature_c": temperatures.get("SOC"),
        "thermal_status_line": next(
            (line.strip() for line in text.splitlines() if line.strip().startswith("Thermal Status:")),
            None,
        ),
    }


def _as_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip()) if value is not None else None
    except ValueError:
        return None


def wait_for_completion(device: str | None, timeout_seconds: int) -> str:
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        last = adb(device, "logcat", "-d", "-s", "PoisonGuardQwenStep:I")
        if "Qwen pilot OK:" in last or "training step failed" in last:
            return last
        time.sleep(0.5)
    raise TimeoutError("Qwen step pilot did not finish before timeout")


def parse_run(log: str, seed: int) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for match in STEP_RE.finditer(log):
        steps.append({
            "index": int(match.group(1)),
            "total": int(match.group(2)),
            "loss": float(match.group(3)),
            "time_ms": int(match.group(4)),
        })
    if not steps:
        raise ValueError("no step records found in logcat")
    rss_match = RSS_RE.search(log)
    final_loss = LOSS_RE.search(log)
    return {
        "seed": seed,
        "steps": steps,
        "step_times_ms": [step["time_ms"] for step in steps],
        "losses": [step["loss"] for step in steps],
        "last_loss": float(final_loss.group(1)) if final_loss else steps[-1]["loss"],
        "peak_rss_kb": int(rss_match.group(1)) if rss_match else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="9DBQFE8LEEWWYHYD")
    parser.add_argument("--package", default="com.poisonguard.qwenstep")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--output", default="outputs/qwen_step_pilot_3seed/qwen_step_pilot.json")
    args = parser.parse_args()

    runs: list[dict[str, Any]] = []
    for seed in range(1, args.runs + 1):
        adb(args.device, "shell", "am", "force-stop", args.package)
        adb(args.device, "logcat", "-c")
        before_battery = battery_state(args.device)
        before_thermal = thermal_state(args.device)
        adb(args.device, "shell", "monkey", "-p", args.package,
            "-c", "android.intent.category.LAUNCHER", "1")
        log = wait_for_completion(args.device, args.timeout)
        if "training step failed" in log:
            raise RuntimeError(f"pilot failed on seed {seed}\n{log}")
        run = parse_run(log, seed)
        run["battery_before"] = before_battery
        run["battery_after"] = battery_state(args.device)
        run["thermal_before"] = before_thermal
        run["thermal_after"] = thermal_state(args.device)
        runs.append(run)

    all_times = [time_ms for run in runs for time_ms in run["step_times_ms"]]
    payload = {
        "label": "on-device Qwen2.5-0.5B LoRA step microbenchmark, not a paper result",
        "paper_ready": False,
        "device": "Xiaomi 13T (2306EPN60G)",
        "device_id": args.device,
        "android_release": "16",
        "package": args.package,
        "model": "Qwen2.5-0.5B-Instruct",
        "workload": "synthetic token ids, sequence length 8, batch size 1",
        "runs": runs,
        "summary": {
            "run_count": len(runs),
            "step_count": len(all_times),
            "step_time_ms": median_iqr_count(all_times),
            "peak_rss_kb": median_iqr_count(
                [run["peak_rss_kb"] for run in runs if run["peak_rss_kb"] is not None]),
        },
        "energy": {
            "source": "external_power_monitor_not_available",
            "joules": None,
            "note": "Android counters are secondary and cannot support an energy claim.",
        },
        "note": (
            "No attack, baseline, evaluation set, or task utility was run. "
            "This pilot informs feasibility and timeout planning only."
        ),
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
