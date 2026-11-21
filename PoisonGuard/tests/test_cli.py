import os
from pathlib import Path
import subprocess
import sys


def test_cli_help_and_demo(tmp_path) -> None:  # type: ignore[no-untyped-def]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    help_run = subprocess.run([sys.executable, "-m", "poisonguard.cli", "--help"],
                              env=env, capture_output=True, text=True, check=False)
    assert help_run.returncode == 0 and "demo" in help_run.stdout
    assert "real experiment protocol stage" in help_run.stdout
    demo = subprocess.run([sys.executable, "scripts/run_synthetic_demo.py", "--config",
                           "configs/synthetic_demo.yaml", "--output", str(tmp_path)],
                          env=env, capture_output=True, text=True, check=False)
    assert demo.returncode == 0, demo.stderr
    assert (tmp_path / "results.json").exists() and (tmp_path / "metrics.png").exists()
