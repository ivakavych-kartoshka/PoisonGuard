from __future__ import annotations

from datetime import datetime, timezone
import platform
import sys
from typing import Any
import numpy as np

from poisonguard.data.schemas import EnvironmentRecord, stable_digest


LABEL = "synthetic smoke-test output, not a paper result"


def environment_from_config(config: dict[str, Any]) -> EnvironmentRecord:
    seed = int(config.get("seed", 7))
    policy_hash = stable_digest(config.get("policy", {}))
    return EnvironmentRecord("poisonguard-0.1.0", "synthetic-vector-base",
                             "synthetic-tokenizer", "deterministic-mean-update",
                             policy_hash, "numpy-cpu", seed, True)


def run_metadata(config: dict[str, Any], config_path: str) -> dict[str, Any]:
    return {"label": LABEL, "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": config_path, "config_digest": stable_digest(config),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "numpy": np.__version__, "seed": int(config.get("seed", 7)),
            "real_experiment": False, "network_downloads": False}
