from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_results(input_path: str | Path, output_path: str | Path) -> Path:
    with Path(input_path).open(encoding="utf-8") as handle:
        result = json.load(handle)
    methods = result.get("methods") or result.get("evaluation", {}).get("methods")
    if not methods:
        raise ValueError("input contains no method results")
    names = [item["method"].replace("_", "\n") for item in methods]
    false_admission = [item["false_admission_rate"] for item in methods]
    false_quarantine = [item["false_quarantine_rate"] for item in methods]
    x = range(len(names))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - 0.18 for i in x], false_admission, 0.36, label="False admission")
    ax.bar([i + 0.18 for i in x], false_quarantine, 0.36, label="False quarantine")
    ax.set_xticks(list(x), names)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("Synthetic smoke-test output, not a paper result")
    ax.legend()
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return target
