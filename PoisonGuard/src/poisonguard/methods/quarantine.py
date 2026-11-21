from dataclasses import dataclass, field


@dataclass
class QuarantineStore:
    """Non-serving evidence namespace."""
    object_ids: list[str] = field(default_factory=list)

    def add(self, object_id: str) -> None:
        if object_id not in self.object_ids:
            self.object_ids.append(object_id)

    def release(self, object_id: str) -> None:
        self.object_ids.remove(object_id)
