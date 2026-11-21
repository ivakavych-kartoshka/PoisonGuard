"""Failure-loud adapter boundary for an external on-device trainer.

This module does not implement model math. It records the command, inputs,
outputs, and hashes needed to connect PoisonGuard's lineage state machine to a
pinned MobileFineTuner (or equivalent) build without pretending that a smoke
test is a paper result.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from poisonguard.utils.io import write_immutable_json


class ExternalTrainerUnavailable(RuntimeError):
    """Raised when a real trainer binary or required asset is not supplied."""


@dataclass(frozen=True)
class TrainingRunResult:
    trainer: str
    command: list[str]
    return_code: int
    stdout_path: Path
    stderr_path: Path
    output_dir: Path
    output_hashes: dict[str, str]
    duration_seconds: float | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_directory(root: Path) -> dict[str, str]:
    """Return relative-path -> SHA-256 for every file under ``root``."""
    if not root.is_dir():
        raise FileNotFoundError(f"training output directory does not exist: {root}")
    result: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        result[path.relative_to(root).as_posix()] = _sha256_file(path)
    return result


@dataclass
class MobileFineTunerTrainer:
    """Thin, failure-loud wrapper around a pinned MobileFineTuner binary."""

    binary: Path
    model_dir: Path | None = None
    timeout_seconds: int | None = None
    trainer_name: str = "MobileFineTuner"

    def _validate(self) -> None:
        if not self.binary.is_file():
            raise ExternalTrainerUnavailable(
                f"{self.trainer_name} binary not found: {self.binary}")
        if self.model_dir is not None and not self.model_dir.is_dir():
            raise ExternalTrainerUnavailable(
                f"{self.trainer_name} model directory not found: {self.model_dir}")

    def build_command(
        self,
        *,
        data_dir: Path | None = None,
        output_dir: Path,
        extra_args: Sequence[str] = (),
    ) -> list[str]:
        self._validate()
        command = [str(self.binary)]
        # Caller-supplied arguments are intentionally placed first so that a
        # wrapper such as ``python -c ...`` can consume its own options.
        command.extend(list(extra_args))
        if self.model_dir is not None:
            command.extend(["--model_dir", str(self.model_dir)])
        if data_dir is not None:
            command.extend(["--data_dir", str(data_dir)])
        command.extend(["--output_dir", str(output_dir)])
        return command

    def run(
        self,
        *,
        data_dir: Path | None = None,
        output_dir: Path,
        extra_args: Sequence[str] = (),
        env: Mapping[str, str] | None = None,
    ) -> TrainingRunResult:
        self._validate()
        if output_dir.exists():
            from poisonguard.utils.io import ArtifactExistsError

            raise ArtifactExistsError(
                f"refusing to reuse external trainer output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=False)
        command = self.build_command(data_dir=data_dir, output_dir=output_dir, extra_args=extra_args)
        stdout_path = output_dir / "stdout.log"
        stderr_path = output_dir / "stderr.log"
        import time

        started = time.monotonic()
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            completed = subprocess.run(
                command,
                stdout=stdout,
                stderr=stderr,
                env=dict(env) if env is not None else None,
                timeout=self.timeout_seconds,
                check=False,
            )
        duration = time.monotonic() - started
        if completed.returncode != 0:
            raise ExternalTrainerUnavailable(
                f"{self.trainer_name} failed with exit code {completed.returncode}; "
                f"see {stderr_path}")
        hashes = hash_directory(output_dir)
        result = TrainingRunResult(
            trainer=self.trainer_name,
            command=command,
            return_code=completed.returncode,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_dir=output_dir,
            output_hashes=hashes,
            duration_seconds=duration,
        )
        manifest = asdict(result)
        for key in ("stdout_path", "stderr_path", "output_dir"):
            manifest[key] = str(manifest[key])
        manifest["label"] = "external trainer run, not a paper result until independently validated"
        manifest["paper_ready"] = False
        write_immutable_json(output_dir / "training_run_manifest.json", manifest)
        return result
