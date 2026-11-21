from pathlib import Path

import pytest

from poisonguard.baselines.external_wrappers import (
    AMemGuardAdapter,
    AgentPoisonAdapter,
    ExternalDependencyUnavailable,
    MemoryGraftAdapter,
    repository_provenance,
)


def test_unprovisioned_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(ExternalDependencyUnavailable):
        AMemGuardAdapter(tmp_path / "missing").validate_repository()


def test_repository_provenance_for_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x", encoding="utf-8")
    provenance = repository_provenance(root)
    assert provenance.exists is True
    assert provenance.is_git is False


def test_attack_adapter_without_command_raises(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    adapter = AgentPoisonAdapter(root)
    with pytest.raises(ExternalDependencyUnavailable):
        adapter.generate(tmp_path / "in.json", tmp_path / "out.json", {})


def test_memory_graft_adapter_without_command_raises(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    adapter = MemoryGraftAdapter(root)
    with pytest.raises(ExternalDependencyUnavailable):
        adapter.generate(tmp_path / "in.json", tmp_path / "out.json", {})