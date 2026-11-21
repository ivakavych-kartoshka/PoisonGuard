"""Algorithm 2: lineage rollback-and-replay."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Sequence
import numpy as np

from poisonguard.data.schemas import (
    Checkpoint, Decision, LineageNode, MemoryRecord, NodeType, RecoveryCertificate,
    Sink, stable_digest,
)

if TYPE_CHECKING:
    from .core import PoisonGuardEngine


def rollback_and_replay(engine: "PoisonGuardEngine", roots: Sequence[str],
                        probe_digest: str = "none") -> RecoveryCertificate:
    """Invalidate descendants, restore newest unaffected checkpoint, and replay.

    This implementation refuses non-deterministic or environment-mismatched replay,
    preserving the premises of the paper's exact-restoration theorem.
    """
    with engine._lock:
        if not roots:
            raise ValueError("at least one revoked root is required")
        if not engine.environment.deterministic:
            raise RuntimeError("exact replay unavailable: nondeterministic environment")
        affected = engine.graph.invalidate(roots)
        for record_id, record in engine.memory.items():
            if record_id in affected:
                record.retrievable = False
        for checkpoint_id, checkpoint in engine.checkpoints.items():
            if checkpoint_id in affected:
                checkpoint.valid = False

        ancestry: list[str] = []
        cursor: str | None = engine.active_checkpoint_id
        while cursor is not None:
            ancestry.append(cursor)
            cursor = engine.checkpoints[cursor].parent_id
        restored_id = next((item for item in ancestry
                            if item not in affected and engine.checkpoints[item].valid), None)
        if restored_id is None:
            restored_id = next(item for item, cp in engine.checkpoints.items() if cp.parent_id is None)
        restored = engine.checkpoints[restored_id]
        if restored.environment_digest != engine.environment.digest:
            raise RuntimeError("exact replay unavailable: environment digest mismatch")
        snapshot = engine.snapshots[restored_id]
        parameters = np.asarray(snapshot["parameters"], dtype=float).copy()
        memory = deepcopy(snapshot["memory"])
        eligible = list(snapshot["eligible"])
        replayed: list[str] = []
        cutoff = int(snapshot["logical_time"])

        for event_id in engine.event_order:
            if engine.event_time[event_id] <= cutoff or event_id in affected:
                continue
            replayed.append(event_id)
            decision = engine.decisions[event_id]
            event = engine.events[event_id]
            if decision[Sink.MEMORY] is Decision.ALLOW:
                record_id = stable_digest({"memory": event_id, "transform": "identity-v1"})
                memory[record_id] = MemoryRecord(record_id, event.payload, (event_id,))
            if decision[Sink.TRAIN] is Decision.ALLOW:
                eligible.append(event_id)

        used_sources: set[str] = set(restored.source_ids)
        for operation in engine.training_log:
            if operation["logical_time"] <= cutoff or not operation["promoted"]:
                continue
            selected = [item for item in operation["event_ids"]
                        if item not in affected and item in eligible]
            if selected:
                parameters = engine.trainer.train(parameters,
                                                  [engine.events[item] for item in selected],
                                                  operation["step_size"])
                used_sources.update(selected)

        engine.parameters = parameters
        engine.memory = memory
        engine.eligible = eligible
        recovered_id = stable_digest({"recovered_from": restored_id, "revoked": sorted(roots),
                                      "parameters": parameters.tolist(),
                                      "environment": engine.environment.digest})
        recovered = Checkpoint(recovered_id, restored_id, engine.logical_time,
                               parameters.tolist(), tuple(sorted(used_sources)),
                               engine.environment.digest)
        engine.checkpoints[recovered_id] = recovered
        engine.graph.add_node(LineageNode(recovered_id, NodeType.CHECKPOINT, engine.logical_time,
                                          attributes={"recovered": True,
                                                      "environment": engine.environment.digest}))
        engine.graph.add_edge(restored_id, recovered_id)
        for source in sorted(used_sources):
            if source in engine.graph.nodes and source not in affected:
                engine.graph.add_edge(source, recovered_id)
        engine.active_checkpoint_id = recovered_id
        engine._save_snapshot(recovered_id)
        certificate_id = stable_digest({"roots": sorted(roots), "restored": restored_id,
                                        "recovered": recovered_id, "replayed": replayed})
        certificate = RecoveryCertificate(
            certificate_id, tuple(roots), engine.graph.counts(affected), restored_id,
            recovered_id, tuple(replayed), engine.environment.digest, probe_digest,
            True, "complete",
        )
        engine.graph.add_node(LineageNode(certificate_id, NodeType.RECOVERY, engine.logical_time,
                                          attributes={"exact": True, "status": "complete"}))
        engine.graph.add_edge(recovered_id, certificate_id)
        return certificate
