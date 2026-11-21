"""Directly specified policy/state-machine baselines."""

from poisonguard.data.schemas import Decision, Event, Sink
from poisonguard.methods.policy import DefaultPolicy


class NoDefensePolicy(DefaultPolicy):
    def decide(self, event: Event, sink: Sink, parent_decisions=()) -> Decision:  # type: ignore[no-untyped-def]
        return Decision.ALLOW


class MemoryOnlyPolicy(DefaultPolicy):
    """Sanitize remote memory but leave adapter selection unprotected."""
    def decide(self, event: Event, sink: Sink, parent_decisions=()) -> Decision:  # type: ignore[no-untyped-def]
        if sink is Sink.MEMORY and not event.user_authored:
            return Decision.QUARANTINE
        return Decision.ALLOW


class ProvenanceOnlyPolicy(DefaultPolicy):
    """Default origin policy; runners using this baseline intentionally omit recovery."""


class SharedLineageWithoutQuarantinePolicy(NoDefensePolicy):
    """All data reaches training; lineage can support later rollback."""


class QuarantineWithoutRollbackPolicy(DefaultPolicy):
    """Admission/audit policy whose runner intentionally performs no recovery."""
