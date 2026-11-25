"""Resumable experiment orchestrator for PoisonGuard.

Supports graceful interruption (Ctrl+C), persistent checkpointing, incremental
execution across multiple sessions, ADB health/thermal checks, and automatic
skipping of already-completed tasks.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = REPO_ROOT / "outputs"
STATE_FILE = OUTPUTS_DIR / "resumable_state.json"
PYTHON_EXE = sys.executable

AGENTPOISON_PYTHON = Path(r"D:\NCKH\MobileSYS\attack_baselines\venvs\agentpoison\Scripts\python.exe")
AGENTPOISON_REPO = Path(r"D:\NCKH\MobileSYS\attack_baselines\AgentPoison")

# Ensure adb is accessible
ADB_DIR = r"C:\Users\Lenovo\AppData\Local\Android\Sdk\platform-tools"
if os.path.isdir(ADB_DIR) and ADB_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ADB_DIR + os.pathsep + os.environ.get("PATH", "")


@dataclass
class TaskRecord:
    task_id: str
    description: str
    command: list[str]
    cwd: str | None = None
    env_vars: dict[str, str] = field(default_factory=dict)
    required_outputs: list[str] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, INTERRUPTED
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float = 0.0
    error: str | None = None
    device_required: bool = False


class StateManager:
    def __init__(self, state_path: Path = STATE_FILE):
        self.state_path = state_path
        self.data: dict[str, Any] = {"tasks": {}, "version": "1.0", "updated_at": None, "label": "resumable experiment state, not a paper result"}
        self.load()

    def load(self) -> None:
        if self.state_path.is_file():
            try:
                self.data = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[WARN] Failed to load existing state file ({e}), starting fresh.")
                self.data = {"tasks": {}, "version": "1.0", "updated_at": None}

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.state_path)

    def get_task_status(self, task_id: str) -> str:
        return self.data.get("tasks", {}).get(task_id, {}).get("status", "PENDING")

    def update_task(self, record: TaskRecord) -> None:
        self.data["tasks"][record.task_id] = asdict(record)
        self.save()

    def mark_completed(self, task_id: str, duration: float) -> None:
        if task_id in self.data["tasks"]:
            self.data["tasks"][task_id]["status"] = "COMPLETED"
            self.data["tasks"][task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.data["tasks"][task_id]["duration_seconds"] = duration
            self.data["tasks"][task_id]["error"] = None
            self.save()

    def mark_failed(self, task_id: str, error: str) -> None:
        if task_id in self.data["tasks"]:
            self.data["tasks"][task_id]["status"] = "FAILED"
            self.data["tasks"][task_id]["error"] = error
            self.save()

    def mark_interrupted(self, task_id: str) -> None:
        if task_id in self.data["tasks"]:
            self.data["tasks"][task_id]["status"] = "INTERRUPTED"
            self.save()


def check_adb_device(device_id: str = "9DBQFE8LEEWWYHYD") -> bool:
    """Verify ADB device is connected and responsive."""
    try:
        proc = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        lines = proc.stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == device_id and parts[1] == "device":
                return True
        # Try reconnecting
        print(f"[ADB] Device {device_id} not seen. Attempting 'adb reconnect'...")
        subprocess.run(["adb", "reconnect"], capture_output=True, timeout=10)
        time.sleep(2)
        proc2 = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        for line in proc2.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == device_id and parts[1] == "device":
                return True
        return False
    except Exception as e:
        print(f"[ADB Error] Failed to query ADB: {e}")
        return False


def get_device_soc_temp(device_id: str = "9DBQFE8LEEWWYHYD") -> float | None:
    """Read SOC temperature from thermal service (Current HAL reading, avoiding stale cache)."""
    try:
        proc = subprocess.run(
            ["adb", "-s", device_id, "shell", "dumpsys", "thermalservice"],
            capture_output=True, text=True, timeout=10
        )
        in_hal = False
        import re
        for line in proc.stdout.splitlines():
            if "Current temperatures from HAL:" in line:
                in_hal = True
                continue
            if in_hal:
                if line.strip().startswith("Current cooling devices"):
                    break
                if "mName=SOC" in line or "mName=soc" in line:
                    m = re.search(r"mValue=([0-9.]+)", line)
                    if m:
                        return float(m.group(1))
    except Exception:
        pass
    return None


def cool_down_if_needed(device_id: str = "9DBQFE8LEEWWYHYD", threshold_c: float = 60.0, wait_seconds: int = 40) -> None:
    """Rest phone if SOC temperature is too high to prevent thermal throttling."""
    temp = get_device_soc_temp(device_id)
    if temp and temp > threshold_c:
        print(f"[THERMAL NOTICE] Phone SOC temperature is {temp:.1f}°C (> {threshold_c}°C).")
        print(f"[THERMAL NOTICE] Resting for {wait_seconds}s to avoid thermal throttling...")
        time.sleep(wait_seconds)


def ensure_config_exists(config_path: Path, template_path: Path, seed: int) -> None:
    """Generate seed-specific config if it does not exist yet."""
    if not config_path.is_file() and template_path.is_file():
        import re
        text = template_path.read_text(encoding="utf-8")
        text = re.sub(r"seed:\s*\d+", f"seed: {seed}", text)
        text = re.sub(r"outputs/[a-zA-Z0-9_]+seed\d+(_v\d+)?", f"outputs/{config_path.stem}", text)
        config_path.write_text(text, encoding="utf-8")
        print(f"[CONFIG AUTO-GEN] Generated {config_path.name} from {template_path.name}")


def ensure_aggregate_config(agg_cfg_path: Path, seeds: list[int], file_prefix: str) -> None:
    """Ensure aggregation config lists all executed seeds."""
    import re
    if agg_cfg_path.is_file():
        text = agg_cfg_path.read_text(encoding="utf-8")
        results_lines = "\n".join(f"    - outputs/{file_prefix}{s}.json" for s in seeds)
        new_text = re.sub(r"results:\n(\s*-\s*outputs/[^\n]+\n)+", f"results:\n{results_lines}\n", text)
        agg_cfg_path.write_text(new_text, encoding="utf-8")


def clean_partial_target_if_interrupted(task: TaskRecord) -> None:
    """Wipe dirty incomplete target directory so _require_empty_target does not raise ArtifactExistsError."""
    import shutil
    for out in task.required_outputs:
        p = REPO_ROOT / out
        parent = p.parent
        if parent != REPO_ROOT and parent != OUTPUTS_DIR:
            if parent.is_dir() and not (p.is_file() and p.stat().st_size > 0):
                print(f"[CLEANUP] Cleaning partial directory from interrupted task: {parent.name}")
                shutil.rmtree(parent, ignore_errors=True)
                parent.mkdir(parents=True, exist_ok=True)


def build_plan_tasks(plan: str = "fast") -> list[TaskRecord]:
    """Define the ordered sequence of experiment tasks."""
    tasks: list[TaskRecord] = []
    seeds = [1, 2, 3] if plan == "fast" else [1, 2, 3, 4, 5]

    # Stage 1: Dataset normalization check / verification
    tasks.append(TaskRecord(
        task_id="data_normalize_check",
        description="Verify normalized datasets exist",
        command=[PYTHON_EXE, "-m", "poisonguard.cli", "validate-data", "--input", "datas/aeslc/poisonguard_events.jsonl"],
        cwd=str(REPO_ROOT),
        required_outputs=["datas/aeslc/poisonguard_events.jsonl"]
    ))

    # Stage 2: System Microbenchmark on Xiaomi 13T (3-5 seeds)
    for s in seeds:
        cfg = OUTPUTS_DIR / f"sys_run_seed{s}.yaml"
        ensure_config_exists(cfg, OUTPUTS_DIR / "sys_run_seed1.yaml", s)
        tasks.append(TaskRecord(
            task_id=f"sys_run_seed{s}",
            description=f"Device systems run seed {s} via MobileFineTuner on Xiaomi 13T",
            command=[PYTHON_EXE, "-m", "poisonguard.cli", "real", "--stage", "run", "--config", f"outputs/sys_run_seed{s}.yaml"],
            cwd=str(REPO_ROOT),
            required_outputs=[f"outputs/sys_run_seed{s}/real_run_manifest.json"],
            device_required=True
        ))

    # Stage 3: Systems Aggregation
    agg_sys_cfg = OUTPUTS_DIR / "aggregate_systems_config.yaml"
    ensure_aggregate_config(agg_sys_cfg, seeds, "measured_systems_seed")
    tasks.append(TaskRecord(
        task_id="aggregate_systems",
        description="Aggregate systems measurements across seeds",
        command=[PYTHON_EXE, "-m", "poisonguard.cli", "real", "--stage", "aggregate", "--config", "outputs/aggregate_systems_config.yaml"],
        cwd=str(REPO_ROOT),
        required_outputs=["outputs/aggregate_systems/real_metrics_aggregate.json"]
    ))

    # Stage 4: AgentPoison Trigger Generation (per seed)
    for s in seeds:
        cfg = OUTPUTS_DIR / f"agentpoison_run_seed{s}_v2.yaml"
        ensure_config_exists(cfg, OUTPUTS_DIR / "agentpoison_run_seed1_v2.yaml", s)
        tasks.append(TaskRecord(
            task_id=f"agentpoison_trigger_seed{s}",
            description=f"Generate AgentPoison trigger artifacts (seed {s})",
            command=[
                PYTHON_EXE, "-m", "poisonguard.cli", "real",
                "--stage", "run", "--config", f"outputs/agentpoison_run_seed{s}_v2.yaml"
            ],
            cwd=str(REPO_ROOT),
            env_vars={"OPENAI_BASE_URL": "http://localhost:11434/v1", "OPENAI_API_KEY": "ollama", "PYTHONUTF8": "1"},
            required_outputs=[f"outputs/agentpoison_run_seed{s}_v2/attacks/agentpoison.json"]
        ))

    # Stage 5: AgentPoison ASR Evaluation (per seed)
    py_bin = str(AGENTPOISON_PYTHON) if AGENTPOISON_PYTHON.is_file() else PYTHON_EXE
    asr_script = str(REPO_ROOT / "scripts" / "run_agentpoison_asr_bridge.py")
    for s in seeds:
        trigger_path = str(OUTPUTS_DIR / f"agentpoison_run_seed{s}_v2" / "attacks" / "agentpoison.json")
        manifest_path = str(OUTPUTS_DIR / f"measured_agentpoison_seed{s}.json")
        work_path = str(OUTPUTS_DIR / f"asr_seed{s}_v2")
        tasks.append(TaskRecord(
            task_id=f"agentpoison_asr_seed{s}",
            description=f"Measure AgentPoison ASR before/after on StrategyQA (seed {s})",
            command=[
                py_bin, asr_script,
                "--trigger-file", trigger_path,
                "--output-manifest", manifest_path,
                "--work-dir", work_path,
                "--seed", str(s),
                "--repo-root", str(AGENTPOISON_REPO),
                "--retriever-path", "C:/Users/Lenovo/.cache/huggingface/hub/models--facebook--dpr-ctx_encoder-single-nq-base/snapshots/bb21a3c2b1656d60c6a8e920283bc40dabddadb8",
            ],
            cwd=str(AGENTPOISON_REPO),
            env_vars={"OPENAI_BASE_URL": "http://localhost:11434/v1", "OPENAI_API_KEY": "ollama", "PYTHONUTF8": "1"},
            required_outputs=[f"outputs/measured_agentpoison_seed{s}.json"]
        ))

    # Stage 6: Attack Aggregation
    agg_ap_cfg = OUTPUTS_DIR / "aggregate_agentpoison_config.yaml"
    ensure_aggregate_config(agg_ap_cfg, seeds, "measured_agentpoison_seed")
    tasks.append(TaskRecord(
        task_id="aggregate_agentpoison",
        description="Aggregate AgentPoison ASR & utility across seeds",
        command=[PYTHON_EXE, "-m", "poisonguard.cli", "real", "--stage", "aggregate", "--config", "outputs/aggregate_agentpoison_config.yaml"],
        cwd=str(REPO_ROOT),
        required_outputs=["outputs/aggregate_agentpoison/real_metrics_aggregate.json"]
    ))

    return tasks


class ResumableOrchestrator:
    def __init__(self, plan: str = "fast", device_id: str = "9DBQFE8LEEWWYHYD"):
        self.plan = plan
        self.device_id = device_id
        self.state_mgr = StateManager()
        self.tasks = build_plan_tasks(plan)
        self.current_process: subprocess.Popen | None = None
        self.interrupted = False

        # Register signal handler for graceful Ctrl+C
        signal.signal(signal.SIGINT, self._handle_interrupt)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        print("\n\n" + "=" * 65)
        print("[INTERRUPT RECEIVED] Safely stopping current task...")
        self.interrupted = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
        print("[STATE SAVED] Progress checkpointed. You can resume anytime!")
        print("=" * 65 + "\n")
        sys.exit(0)

    def is_task_already_done(self, task: TaskRecord) -> bool:
        """Check both state record and physical file presence."""
        all_exist = bool(task.required_outputs)
        for out in task.required_outputs:
            p = REPO_ROOT / out
            if not p.is_file() or p.stat().st_size == 0:
                all_exist = False
                break

        if all_exist:
            if self.state_mgr.get_task_status(task.task_id) != "COMPLETED":
                self.state_mgr.mark_completed(task.task_id, 0.0)
            return True

        status = self.state_mgr.get_task_status(task.task_id)
        return status == "COMPLETED"

    def show_status(self) -> None:
        print("\n" + "=" * 75)
        print(f"POISONGUARD EXPERIMENT RUNNER — STATUS (Plan: {self.plan.upper()})")
        print("=" * 75)
        completed = 0
        total = len(self.tasks)
        for i, t in enumerate(self.tasks, 1):
            done = self.is_task_already_done(t)
            if done:
                completed += 1
                status_str = "[COMPLETED]"
            else:
                saved_status = self.state_mgr.get_task_status(t.task_id)
                status_str = f"[{saved_status}]"

            duration = self.state_mgr.data.get("tasks", {}).get(t.task_id, {}).get("duration_seconds", 0.0)
            time_str = f"({duration:.1f}s)" if duration > 0 else ""
            print(f" {i:2d}. {status_str:13s} {t.task_id:30s} {time_str}")
        print("-" * 75)
        pct = (completed / total) * 100 if total > 0 else 0
        print(f" Progress: {completed}/{total} tasks complete ({pct:.1f}%).")
        print("=" * 75 + "\n")

    def run(self, retry_failed: bool = False) -> None:
        self.show_status()
        total = len(self.tasks)

        for idx, task in enumerate(self.tasks, 1):
            if self.interrupted:
                break

            # Check if already completed
            if self.is_task_already_done(task) and not retry_failed:
                print(f"[{idx}/{total}] SKIP: {task.task_id} (already completed)")
                continue

            # If device is required, check ADB
            if task.device_required:
                if not check_adb_device(self.device_id):
                    print(f"\n[ERROR] Device {self.device_id} is NOT detected via ADB!")
                    print("Please connect the device or enable USB debugging, then re-run.")
                    self.state_mgr.mark_failed(task.task_id, "Device not detected via ADB")
                    return
                # Check thermals
                cool_down_if_needed(self.device_id)

            # Clean any dirty artifacts from prior interrupted attempts
            clean_partial_target_if_interrupted(task)

            # Record task starting
            task.started_at = datetime.now(timezone.utc).isoformat()
            task.status = "RUNNING"
            self.state_mgr.update_task(task)

            print(f"\n[{idx}/{total}] STARTING: {task.task_id}")
            print(f"        Desc: {task.description}")
            print(f"        Cmd:  {' '.join(task.command)}")

            # Prepare environment
            env = os.environ.copy()
            src_dir = str(REPO_ROOT / "src")
            current_pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{current_pp}" if current_pp else src_dir
            env.update(task.env_vars)
            cwd = task.cwd or str(REPO_ROOT)

            t0 = time.monotonic()
            try:
                self.current_process = subprocess.Popen(
                    task.command, cwd=cwd, env=env, text=True
                )
                ret = self.current_process.wait()
                duration = time.monotonic() - t0

                if ret == 0:
                    # Verify outputs
                    missing = []
                    for out in task.required_outputs:
                        p = REPO_ROOT / out
                        if not p.is_file() or p.stat().st_size == 0:
                            missing.append(out)
                    if missing:
                        err_msg = f"Task returned 0 but output missing: {missing}"
                        print(f"[FAIL] {err_msg}")
                        self.state_mgr.mark_failed(task.task_id, err_msg)
                    else:
                        print(f"[DONE] {task.task_id} finished successfully in {duration:.1f}s.")
                        self.state_mgr.mark_completed(task.task_id, duration)
                else:
                    err_msg = f"Process exited with non-zero code {ret}"
                    print(f"[FAIL] {task.task_id}: {err_msg}")
                    self.state_mgr.mark_failed(task.task_id, err_msg)
                    print("\n[STOPPING] Halting execution to preserve integrity.")
                    print("Resolve the issue and re-run this script to resume.")
                    return

            except KeyboardInterrupt:
                self._handle_interrupt(None, None)
            except Exception as exc:
                err_msg = str(exc)
                print(f"[ERROR] Exception running {task.task_id}: {err_msg}")
                self.state_mgr.mark_failed(task.task_id, err_msg)
                return

        print("\n" + "=" * 65)
        print("[SUCCESS] All planned tasks have been completed!")
        print("=" * 65 + "\n")
        self.show_status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", choices=["fast", "full"], default="fast",
                        help="fast (3 seeds, pilot scale) or full (5 seeds, paper scale)")
    parser.add_argument("--device", default="9DBQFE8LEEWWYHYD",
                        help="Android device ID for ADB commands")
    parser.add_argument("--status", action="store_true",
                        help="Print current progress table and exit")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Retry previously failed tasks")
    parser.add_argument("--reset", action="store_true",
                        help="Reset progress state and start from scratch")
    args = parser.parse_args()

    if args.reset:
        if STATE_FILE.is_file():
            STATE_FILE.unlink()
            print(f"[RESET] Deleted {STATE_FILE}. Progress reset.")
        else:
            print("[RESET] No state file found. Already clean.")
        return 0

    orchestrator = ResumableOrchestrator(plan=args.plan, device_id=args.device)

    if args.status:
        orchestrator.show_status()
        return 0

    orchestrator.run(retry_failed=args.retry_failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
