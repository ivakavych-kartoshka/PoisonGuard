from __future__ import annotations

from pathlib import Path


def require_local_path(path: str | Path, label: str) -> Path:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(f"{label} not found at {target}; provision it manually (no download occurs)")
    return target
