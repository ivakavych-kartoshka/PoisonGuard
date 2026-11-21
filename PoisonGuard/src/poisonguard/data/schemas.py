"""Validated schemas corresponding to the paper's state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class Channel(str, Enum):
    TYPED = "typed"
    SMS = "sms"
    NOTIFICATION = "notification"
    CALENDAR = "calendar"
    SHARE = "share"
    CLIPBOARD = "clipboard"
    SCREENSHOT = "screenshot"
    DERIVED = "derived"


class Decision(str, Enum):
    ALLOW = "allow"
    QUARANTINE = "quarantine"
    DENY = "deny"


class Sink(str, Enum):
    MEMORY = "memory"
    TRAIN = "train"


class NodeType(str, Enum):
    EVENT = "event"
    DECISION = "decision"
    MEMORY = "memory"
    EXAMPLE = "example"
    WINDOW = "window"
    CANDIDATE = "candidate"
    AUDIT = "audit"
    CHECKPOINT = "checkpoint"
    DECLASSIFICATION = "declassification"
    RECOVERY = "recovery"


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Event:
    """Paper Eq. (1): provenance-labelled event."""

    event_id: str
    payload: str
    capture_time: float
    app_id: str
    channel: Channel
    sender: str | None
    user_authored: bool | None
    parent_ids: tuple[str, ...] = ()
    schema_version: str = "1"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls, payload: str, capture_time: float, app_id: str, channel: Channel | str,
        sender: str | None = None, user_authored: bool | None = None,
        parent_ids: tuple[str, ...] = (), metadata: dict[str, Any] | None = None,
    ) -> "Event":
        channel = Channel(channel)
        if not payload or not app_id or capture_time < 0:
            raise ValueError("payload/app_id must be non-empty and capture_time nonnegative")
        canonical = {
            "payload": payload, "capture_time": capture_time, "app_id": app_id,
            "channel": channel.value, "sender": sender, "user_authored": user_authored,
            "parent_ids": list(parent_ids), "schema_version": "1", "metadata": metadata or {},
        }
        return cls(stable_digest(canonical), payload, capture_time, app_id, channel, sender,
                   user_authored, tuple(parent_ids), "1", metadata or {})

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["channel"] = self.channel.value
        result["parent_ids"] = list(self.parent_ids)
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Event":
        item = dict(value)
        item["channel"] = Channel(item["channel"])
        item["parent_ids"] = tuple(item.get("parent_ids", ()))
        return cls(**item)


@dataclass
class LineageNode:
    node_id: str
    node_type: NodeType
    logical_time: int
    valid: bool = True
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnvironmentRecord:
    code_version: str
    model_hash: str
    tokenizer_hash: str
    optimizer_hash: str
    policy_hash: str
    backend: str
    seed: int
    deterministic: bool = True

    @property
    def digest(self) -> str:
        return stable_digest(asdict(self))


@dataclass
class MemoryRecord:
    record_id: str
    text: str
    source_ids: tuple[str, ...]
    retrievable: bool = True


@dataclass
class Checkpoint:
    checkpoint_id: str
    parent_id: str | None
    logical_time: int
    parameters: list[float]
    source_ids: tuple[str, ...]
    environment_digest: str
    valid: bool = True


@dataclass
class AuditReport:
    audit_id: str
    candidate_id: str
    lineage_complete: bool
    behavior_score: float
    update_norm: float
    passed: bool
    reasons: tuple[str, ...]


@dataclass
class RecoveryCertificate:
    certificate_id: str
    revoked_roots: tuple[str, ...]
    invalidated_counts: dict[str, int]
    restored_checkpoint_id: str
    recovered_checkpoint_id: str
    replayed_event_ids: tuple[str, ...]
    environment_digest: str
    probe_digest: str
    exact: bool
    status: str
