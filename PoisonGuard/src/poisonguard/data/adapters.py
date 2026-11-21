"""Local-file adapters. They validate provisioned assets and never download data."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Iterator

from .schemas import Event
from poisonguard.utils.validation import require_local_path


class DatasetAdapter(ABC):
    @abstractmethod
    def iter_events(self) -> Iterator[Event]: ...


class JsonlEventAdapter(DatasetAdapter):
    def __init__(self, path: str | Path) -> None:
        self.path = require_local_path(path, "event JSONL")

    def iter_events(self) -> Iterator[Event]:
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    yield Event.from_dict(json.loads(line))
                except (ValueError, TypeError, KeyError) as error:
                    raise ValueError(f"invalid event at line {line_number}: {error}") from error


class ProvisionedDatasetAdapter(DatasetAdapter):
    """Manifest-based boundary for LaMP, PersonaChat, AESLC, or licensed SMS data."""
    def __init__(self, root: str | Path, dataset_name: str) -> None:
        self.root = require_local_path(root, f"{dataset_name} root")
        self.dataset_name = dataset_name

    def iter_events(self) -> Iterator[Event]:
        manifest = require_local_path(self.root / "poisonguard_events.jsonl",
                                      f"normalized {self.dataset_name} manifest")
        yield from JsonlEventAdapter(manifest).iter_events()


class AndroidIngressAdapter:
    def capture(self, raw_item: object) -> Event:
        raise NotImplementedError(
            "Android ingress requires a privileged/test-harness integration; see docs/data_format.md")
