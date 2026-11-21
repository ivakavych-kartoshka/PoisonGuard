"""Sink-specific policy and least-trust inheritance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from poisonguard.data.schemas import Channel, Decision, Event, Sink, stable_digest


_ORDER = {Decision.ALLOW: 0, Decision.QUARANTINE: 1, Decision.DENY: 2}


@dataclass
class DefaultPolicy:
    typed_training: Decision = Decision.ALLOW
    remote_memory: Decision = Decision.QUARANTINE
    remote_training: Decision = Decision.DENY
    epoch: int = 0

    @property
    def digest(self) -> str:
        return stable_digest({"typed_training": self.typed_training.value,
                              "remote_memory": self.remote_memory.value,
                              "remote_training": self.remote_training.value,
                              "epoch": self.epoch})

    def decide(self, event: Event, sink: Sink, parent_decisions: Iterable[Decision] = ()) -> Decision:
        """Paper Eq. (3), with the illustrative default policy from Table 2."""
        if event.channel is Channel.TYPED and event.user_authored is True:
            own = Decision.ALLOW if sink is Sink.MEMORY else self.typed_training
        elif event.channel is Channel.DERIVED:
            own = Decision.QUARANTINE if sink is Sink.MEMORY else Decision.DENY
        else:
            own = self.remote_memory if sink is Sink.MEMORY else self.remote_training
        inherited = list(parent_decisions)
        return max([own, *inherited], key=_ORDER.__getitem__) if inherited else own

    def declassify(self, event: Event, sink: Sink, principal: str) -> dict[str, str]:
        if not principal:
            raise ValueError("a declassification principal is required")
        return {"event_id": event.event_id, "sink": sink.value, "principal": principal,
                "policy_digest": self.digest}
