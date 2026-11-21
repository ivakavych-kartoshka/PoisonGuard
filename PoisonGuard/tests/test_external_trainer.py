import sys
from pathlib import Path

import pytest

from poisonguard.models.external_trainer import (
    ExternalTrainerUnavailable,
    MobileFineTunerTrainer,
    hash_directory,
)


def test_missing_binary_raises(tmp_path: Path) -> None:
    trainer = MobileFineTunerTrainer(binary=tmp_path / "missing.exe")
    with pytest.raises(ExternalTrainerUnavailable):
        trainer.build_command(output_dir=tmp_path / "out")


def test_missing_model_dir_raises(tmp_path: Path) -> None:
    binary = tmp_path / "trainer.py"
    binary.write_text("print('ok')\n", encoding="utf-8")
    trainer = MobileFineTunerTrainer(binary=binary, model_dir=tmp_path / "missing_model")
    with pytest.raises(ExternalTrainerUnavailable):
        trainer.build_command(output_dir=tmp_path / "out")


def test_build_command_includes_paths(tmp_path: Path) -> None:
    binary = tmp_path / "trainer.py"
    binary.write_text("print('ok')\n", encoding="utf-8")
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "out"
    trainer = MobileFineTunerTrainer(binary=binary, model_dir=model_dir)
    command = trainer.build_command(data_dir=data_dir, output_dir=out_dir, extra_args=("--smoke", "1"))
    assert str(binary) in command
    assert "--model_dir" in command
    assert str(model_dir) in command
    assert "--data_dir" in command
    assert str(data_dir) in command
    assert "--output_dir" in command
    assert str(out_dir) in command
    assert "--smoke" in command and command[command.index("--smoke") + 1] == "1"


def test_run_success_hashes_output(tmp_path: Path) -> None:
    code = (
        "import pathlib, sys\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--output_dir') + 1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'adapter.bin').write_bytes(b'abc')\n"
        "print('trained')\n"
    )
    out_dir = tmp_path / "outputs"
    trainer = MobileFineTunerTrainer(binary=Path(sys.executable), timeout_seconds=30)
    result = trainer.run(output_dir=out_dir, extra_args=("-c", code))
    assert (out_dir / "adapter.bin").read_bytes() == b"abc"
    assert "adapter.bin" in result.output_hashes
    assert result.return_code == 0
    assert (out_dir / "training_run_manifest.json").is_file()


def test_run_failure_raises(tmp_path: Path) -> None:
    code = "import sys; print('boom', file=sys.stderr); raise SystemExit(7)\n"
    out_dir = tmp_path / "outputs"
    trainer = MobileFineTunerTrainer(binary=Path(sys.executable))
    with pytest.raises(ExternalTrainerUnavailable):
        trainer.run(output_dir=out_dir, extra_args=("-c", code))


def test_hash_directory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("x", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"\x00\x01")
    hashes = hash_directory(root)
    assert set(hashes) == {"a.txt", "nested/b.bin"}
    assert all(len(value) == 64 for value in hashes.values())
