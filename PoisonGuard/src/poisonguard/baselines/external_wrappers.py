"""Failure-loud wrappers for published attacks and external baselines.

These classes never emulate a published method. They validate a manually
pinned repository, record its provenance, and execute only an explicitly
configured command. Without that command they raise ``ExternalDependencyUnavailable``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from poisonguard.baselines.base import BaselineResult
from poisonguard.utils.io import ArtifactExistsError, write_immutable_json

__all__ = [
    "ExternalDependencyUnavailable",
    "ExternalBaseline",
    "ExternalAttackAdapter",
    "RepositoryProvenance",
    "AMemGuardAdapter",
    "ApproximateUnlearningAdapter",
    "AgentPoisonAdapter",
    "MINJAAdapter",
    "MemGhostAdapter",
    "MemoryGraftAdapter",
    "build_attack_adapter",
    "build_baseline_adapter",
    "repository_provenance",
]


class ExternalDependencyUnavailable(RuntimeError):
    """Raised when a published implementation or its pinned command is unavailable."""


@dataclass
class RepositoryProvenance:
    root: str | None
    exists: bool
    is_git: bool
    commit: str | None = None
    dirty: bool | None = None
    remote: str | None = None
    archive_sha256: str | None = None
    expected_commit: str | None = None
    commit_matches: bool | None = None
    expected_archive_sha256: str | None = None
    archive_hash_matches: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def repository_provenance(
    root: str | Path | None,
    expected_commit: str | None = None,
    expected_archive_sha256: str | None = None,
) -> RepositoryProvenance:
    """Inspect a manually provisioned repository without downloading anything."""
    expected_commit = _normalize_commit(expected_commit)
    expected_archive = str(expected_archive_sha256).lower() if expected_archive_sha256 else None
    if root is None:
        return RepositoryProvenance(
            None, False, False, expected_commit=expected_commit,
            expected_archive_sha256=expected_archive)
    path = Path(root)
    if not path.is_dir():
        return RepositoryProvenance(
            str(path), False, False, expected_commit=expected_commit,
            expected_archive_sha256=expected_archive)
    git = shutil.which("git")
    is_git = git is not None and (path / ".git").exists()
    commit: str | None = None
    dirty: bool | None = None
    remote: str | None = None
    if is_git:
        assert git is not None
        try:
            commit = subprocess.check_output(
                [git, "-C", str(path), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
            status = subprocess.check_output(
                [git, "-C", str(path), "status", "--porcelain"],
                text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
            remote = subprocess.check_output(
                [git, "-C", str(path), "config", "--get", "remote.origin.url"],
                text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            is_git = False
        else:
            dirty = bool(status)
            remote = remote or None
    archive_sha256 = None
    if expected_archive is not None:
        archive_sha256 = _directory_digest(path)
    commit_matches = None
    if expected_commit is not None:
        commit_matches = bool(commit) and _normalize_commit(commit) == expected_commit
    archive_matches = None
    if expected_archive is not None:
        archive_matches = archive_sha256 == expected_archive
    return RepositoryProvenance(
        str(path), True, is_git, commit, dirty, remote, archive_sha256,
        expected_commit, commit_matches, expected_archive, archive_matches)


@dataclass
class ExternalBaseline:
    name: str
    repository_root: str | Path | None = None
    command: tuple[str, ...] = ()
    expected_commit: str | None = None
    expected_archive_sha256: str | None = None

    def provenance(self) -> dict[str, Any]:
        return repository_provenance(
            self.repository_root, self.expected_commit,
            self.expected_archive_sha256).to_dict()

    def validate_repository(self) -> RepositoryProvenance:
        provenance = repository_provenance(
            self.repository_root, self.expected_commit,
            self.expected_archive_sha256)
        if not provenance.exists:
            raise ExternalDependencyUnavailable(
                f"{self.name} repository is not provisioned: {self.repository_root}")
        if provenance.commit_matches is False:
            raise ExternalDependencyUnavailable(
                f"{self.name} commit pin mismatch: expected {provenance.expected_commit}, "
                f"found {provenance.commit}")
        if provenance.expected_commit is not None and provenance.dirty:
            raise ExternalDependencyUnavailable(
                f"{self.name} repository is dirty; pinned commit requires a clean tree")
        if provenance.archive_hash_matches is False:
            raise ExternalDependencyUnavailable(
                f"{self.name} repository hash mismatch: expected "
                f"{provenance.expected_archive_sha256}, found {provenance.archive_sha256}")
        return provenance

    def _command(self, config: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
        command = list(self.command) or list(config.get("command", ()))
        if not command:
            raise ExternalDependencyUnavailable(
                f"{self.name} has no pinned executable command. Implement and validate "
                "its repository-specific adapter before running it.")
        return _render_command(command, context)

    def run(
        self, input_manifest: Path, output_dir: Path, config: Mapping[str, Any]
    ) -> BaselineResult:
        """Run a pinned external baseline or fail loudly."""
        provenance = self.validate_repository()
        if output_dir.exists():
            raise ArtifactExistsError(
                f"refusing to reuse baseline output directory: {output_dir}")
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=False)
        context = _command_context(config, input_manifest=input_manifest,
                                   output_dir=output_dir)
        command = self._command(config, context)
        started = datetime.now(timezone.utc)
        stdout_path = output_dir / "stdout.log"
        stderr_path = output_dir / "stderr.log"
        with stdout_path.open("w", encoding="utf-8") as stdout, \
                stderr_path.open("w", encoding="utf-8") as stderr:
            completed = subprocess.run(
                command,
                cwd=self.repository_root,
                stdout=stdout,
                stderr=stderr,
                check=False,
                timeout=int(config.get("timeout_seconds", 3600)),
            )
        if completed.returncode != 0:
            raise ExternalDependencyUnavailable(
                f"{self.name} failed with exit code {completed.returncode}; see {stderr_path}")
        manifest = {
            "label": "external baseline run, not a paper result until independently validated",
            "name": self.name,
            "repository": provenance.to_dict(),
            "command": command,
            "seed": config.get("seed"),
            "input_manifest": str(input_manifest),
            "input_manifest_sha256": _sha256_path(input_manifest),
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_files": _hash_directory(output_dir),
        }
        write_immutable_json(output_dir / f"{_slug(self.name)}_manifest.json", manifest)
        return BaselineResult(self.name, {}, manifest)


@dataclass
class ExternalAttackAdapter:
    attack_family: str
    repository_root: str | Path | None = None
    command: tuple[str, ...] = ()
    expected_commit: str | None = None
    expected_archive_sha256: str | None = None

    def provenance(self) -> dict[str, Any]:
        return repository_provenance(
            self.repository_root, self.expected_commit,
            self.expected_archive_sha256).to_dict()

    def validate_repository(self) -> RepositoryProvenance:
        provenance = repository_provenance(
            self.repository_root, self.expected_commit,
            self.expected_archive_sha256)
        if not provenance.exists:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} repository is not provisioned: {self.repository_root}")
        if provenance.commit_matches is False:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} commit pin mismatch: expected "
                f"{provenance.expected_commit}, found {provenance.commit}")
        if provenance.expected_commit is not None and provenance.dirty:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} repository is dirty; pinned commit requires a clean tree")
        if provenance.archive_hash_matches is False:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} repository hash mismatch: expected "
                f"{provenance.expected_archive_sha256}, found {provenance.archive_sha256}")
        return provenance

    def _command(self, config: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
        command = list(self.command) or list(config.get("command", ()))
        if not command:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} has no pinned executable command. Implement and "
                "validate its repository-specific adapter before running it.")
        return _render_command(command, context)

    def generate(
        self, benign_manifest: Path, output_manifest: Path,
        config: Mapping[str, Any]
    ) -> Path:
        """Generate an attack manifest using a pinned implementation."""
        provenance = self.validate_repository()
        if output_manifest.exists():
            raise ArtifactExistsError(
                f"refusing to overwrite attack output manifest: {output_manifest}")
        output_manifest.parent.mkdir(parents=True, exist_ok=True)
        raw_output = output_manifest.parent / f".{output_manifest.stem}.raw{output_manifest.suffix}"
        if raw_output.exists():
            raise ArtifactExistsError(
                f"refusing to overwrite raw attack output: {raw_output}")
        context = _command_context(
            config, input_manifest=benign_manifest, output_manifest=raw_output,
            output_dir=output_manifest.parent)
        command = self._command(config, context)
        stdout_path = output_manifest.parent / "stdout.log"
        stderr_path = output_manifest.parent / "stderr.log"
        started = datetime.now(timezone.utc)
        with stdout_path.open("w", encoding="utf-8") as stdout, \
                stderr_path.open("w", encoding="utf-8") as stderr:
            completed = subprocess.run(
                command,
                cwd=self.repository_root,
                stdout=stdout,
                stderr=stderr,
                check=False,
                timeout=int(config.get("timeout_seconds", 3600)),
            )
        if completed.returncode != 0:
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} failed with exit code {completed.returncode}; "
                f"see {stderr_path}")
        if not raw_output.is_file():
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} completed but did not write {raw_output}")
        payload = json.loads(raw_output.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ExternalDependencyUnavailable(
                f"{self.attack_family} output is not a JSON object")
        payload.setdefault(
            "label", "external attack output, not a paper result until independently validated")
        payload.setdefault("attack_family", self.attack_family)
        payload.setdefault("repository", provenance.to_dict())
        payload.setdefault("command", command)
        payload.setdefault("seed", config.get("seed"))
        payload.setdefault("benign_manifest", str(benign_manifest))
        payload.setdefault("benign_manifest_sha256", _sha256_path(benign_manifest))
        payload.setdefault("started_at_utc", started.isoformat())
        payload.setdefault("finished_at_utc", datetime.now(timezone.utc).isoformat())
        write_immutable_json(output_manifest, payload)
        return output_manifest


class AMemGuardAdapter(ExternalBaseline):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("A-MemGuard", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


class ApproximateUnlearningAdapter(ExternalBaseline):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("NPO/approximate unlearning", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


class AgentPoisonAdapter(ExternalAttackAdapter):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("AgentPoison", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


class MINJAAdapter(ExternalAttackAdapter):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("MINJA", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


class MemGhostAdapter(ExternalAttackAdapter):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("MemGhost", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


class MemoryGraftAdapter(ExternalAttackAdapter):
    def __init__(
        self,
        repository_root: str | Path | None = None,
        command: Sequence[str] = (),
        expected_commit: str | None = None,
        expected_archive_sha256: str | None = None,
    ) -> None:
        super().__init__("MemoryGraft", repository_root, tuple(command),
                         expected_commit, expected_archive_sha256)


ATTACK_ADAPTERS = {
    "agentpoison": AgentPoisonAdapter,
    "minja": MINJAAdapter,
    "memghost": MemGhostAdapter,
    "memorygraft": MemoryGraftAdapter,
    "agent_poison": AgentPoisonAdapter,
    "memory_graft": MemoryGraftAdapter,
}

BASELINE_ADAPTERS = {
    "amemguard": AMemGuardAdapter,
    "a_memguard": AMemGuardAdapter,
    "npo": ApproximateUnlearningAdapter,
    "approximate_unlearning": ApproximateUnlearningAdapter,
}


def build_attack_adapter(name: str, spec: Mapping[str, Any]) -> ExternalAttackAdapter:
    key = str(name).strip().lower().replace(" ", "").replace("-", "")
    adapter = ATTACK_ADAPTERS.get(key)
    if adapter is None:
        raise ExternalDependencyUnavailable(f"unknown external attack adapter: {name}")
    return adapter(
        repository_root=spec.get("repository_root") or spec.get("root"),
        command=tuple(spec.get("command", ())),
        expected_commit=spec.get("expected_commit"),
        expected_archive_sha256=spec.get("expected_archive_sha256"),
    )


def build_baseline_adapter(name: str, spec: Mapping[str, Any]) -> ExternalBaseline:
    key = str(name).strip().lower().replace(" ", "").replace("-", "")
    adapter = BASELINE_ADAPTERS.get(key)
    if adapter is None:
        raise ExternalDependencyUnavailable(f"unknown external baseline adapter: {name}")
    return adapter(
        repository_root=spec.get("repository_root") or spec.get("root"),
        command=tuple(spec.get("command", ())),
        expected_commit=spec.get("expected_commit"),
        expected_archive_sha256=spec.get("expected_archive_sha256"),
    )


def _command_context(
    config: Mapping[str, Any],
    *,
    input_manifest: Path | None = None,
    output_manifest: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    context = dict(config.get("template_values", {}) or {})
    context.setdefault("seed", config.get("seed", 0))
    context.setdefault("input_manifest", str(input_manifest) if input_manifest else "")
    context.setdefault("output_manifest", str(output_manifest) if output_manifest else "")
    context.setdefault("output_dir", str(output_dir) if output_dir else "")
    return context


def _render_command(command: Sequence[str], context: Mapping[str, Any]) -> list[str]:
    rendered: list[str] = []
    for item in command:
        try:
            rendered.append(str(item).format_map(context))
        except KeyError as exc:
            raise ExternalDependencyUnavailable(
                f"missing command template value: {exc.args[0]}") from exc
    return rendered


def _normalize_commit(value: str | None) -> str | None:
    return str(value).strip().lower() if value else None


def _sha256_path(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_directory(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.is_dir():
        return result
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        result[path.relative_to(root).as_posix()] = _sha256_path(path)
    return result


def _directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, file_hash in _hash_directory(root).items():
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
