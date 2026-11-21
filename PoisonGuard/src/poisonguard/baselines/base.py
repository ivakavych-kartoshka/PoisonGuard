from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BaselineResult:
    name: str
    metrics: dict[str, float]
    metadata: dict[str, Any]


class Baseline(ABC):
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> BaselineResult: ...
