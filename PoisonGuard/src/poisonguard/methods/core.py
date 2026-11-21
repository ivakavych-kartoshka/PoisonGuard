"""PoisonGuard Algorithms 1 and 2 as a deterministic reference state machine."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import threading
from typing import Any, Sequence
import numpy as np

from poisonguard.data.schemas import (
    AuditReport, Checkpoint, Decision, EnvironmentRecord, Event, LineageNode,
    MemoryRecord, NodeType, RecoveryCertificate, Sink, stable_digest,
)
from poisonguard.methods.lineage import LineageGraph
from poisonguard.methods.policy import DefaultPolicy
from poisonguard.models.adapters import DeterministicAdapterTrainer
from poisonguard.models.audits import AuditThresholds, audit_signals


class PoisonGuardEngine:
    """Reference implementation of provenance admission, quarantine, and recovery.

    Atomic operations use a process lock. Production Android deployments require
    a durable transactional store and recovery barrier.
    """

    def __init__(self, environment: EnvironmentRecord, policy: DefaultPolicy | None = None,
                 trainer: DeterministicAdapterTrainer | None = None) -> None:
        if not environment.deterministic:
            raise ValueError("reference engine requires a deterministic environment")
        self.environment = environment
        self.policy = policy or DefaultPolicy()
        self.trainer = trainer or DeterministicAdapterTrainer()
        self.graph = LineageGraph()
        self.events: dict[str, Event] = {}
        self.event_order: list[str] = []
        self.event_time: dict[str, int] = {}
        self.decisions: dict[str, dict[Sink, Decision]] = {}
        self.memory: dict[str, MemoryRecord] = {}
        self.training_examples: dict[str, tuple[str, ...]] = {}
        self.eligible: list[str] = []
        self.training_quarantine: list[str] = []
        self.ingress_quarantine: list[str] = []
        self.parameters = np.zeros(self.trainer.dimension, dtype=float)
        self.candidates: dict[str, dict[str, Any]] = {}
        self.checkpoints: dict[str, Checkpoint] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.training_log: list[dict[str, Any]] = []
        self.logical_time = 0
        self._lock = threading.RLock()
        base_id = stable_digest({"base": environment.model_hash, "environment": environment.digest})
        base = Checkpoint(base_id, None, 0, self.parameters.tolist(), (), environment.digest)
        self.checkpoints[base_id] = base
        self.active_checkpoint_id = base_id
        self.graph.add_node(LineageNode(base_id, NodeType.CHECKPOINT, 0,
                                        attributes={"base": True, "environment": environment.digest}))
        self._save_snapshot(base_id)

    def _tick(self) -> int:
        self.logical_time += 1
        return self.logical_time

    def _save_snapshot(self, checkpoint_id: str) -> None:
        self.snapshots[checkpoint_id] = {
            "parameters": self.parameters.copy(), "memory": deepcopy(self.memory),
            "eligible": list(self.eligible), "training_quarantine": list(self.training_quarantine),
            "logical_time": self.logical_time,
        }

    def ingest(self, event: Event) -> dict[Sink, Decision]:
        """Algorithm 1 lines 1-12 and paper Eqs. (6)-(7)."""
        with self._lock:
            if event.event_id in self.events:
                return dict(self.decisions[event.event_id])
            missing = set(event.parent_ids) - self.events.keys()
            if missing:
                raise ValueError(f"derived event has unknown parents: {sorted(missing)}")
            now = self._tick()
            self.events[event.event_id] = event
            self.event_order.append(event.event_id)
            self.event_time[event.event_id] = now
            self.graph.add_node(LineageNode(event.event_id, NodeType.EVENT, now,
                                            attributes={"channel": event.channel.value,
                                                        "digest": event.event_id}))
            for parent in event.parent_ids:
                self.graph.add_edge(parent, event.event_id)
            result: dict[Sink, Decision] = {}
            for sink in Sink:
                inherited = [self.decisions[parent][sink] for parent in event.parent_ids]
                decision = self.policy.decide(event, sink, inherited)
                result[sink] = decision
                decision_id = stable_digest({"event": event.event_id, "sink": sink.value,
                                             "decision": decision.value, "epoch": self.policy.epoch})
                self.graph.add_node(LineageNode(decision_id, NodeType.DECISION, now,
                                                attributes={"sink": sink.value,
                                                            "decision": decision.value,
                                                            "epoch": self.policy.epoch}))
                self.graph.add_edge(event.event_id, decision_id)
            self.decisions[event.event_id] = result
            if result[Sink.MEMORY] is Decision.ALLOW:
                record_id = stable_digest({"memory": event.event_id, "transform": "identity-v1"})
                self.memory[record_id] = MemoryRecord(record_id, event.payload, (event.event_id,))
                self.graph.add_node(LineageNode(record_id, NodeType.MEMORY, now))
                self.graph.add_edge(event.event_id, record_id)
            elif result[Sink.MEMORY] is Decision.QUARANTINE:
                self.ingress_quarantine.append(event.event_id)
            if result[Sink.TRAIN] is Decision.ALLOW:
                self.eligible.append(event.event_id)
            elif result[Sink.TRAIN] is Decision.QUARANTINE:
                self.training_quarantine.append(event.event_id)
            return dict(result)

    def create_training_example_from_memory(self, record_id: str) -> str:
        """Materialize the paper's explicit memory-to-adapter laundering edge."""
        with self._lock:
            if record_id not in self.memory or not self.memory[record_id].retrievable:
                raise ValueError("memory record is missing or non-retrievable")
            source_ids = self.memory[record_id].source_ids
            if any(item not in self.eligible for item in source_ids):
                raise ValueError("memory closure contains an event denied or quarantined for training")
            example_id = stable_digest({"training_example_from_memory": record_id,
                                        "sources": source_ids, "version": "1"})
            self.graph.add_node(LineageNode(example_id, NodeType.EXAMPLE, self.logical_time,
                                            attributes={"source_ids": list(source_ids)}))
            self.graph.add_edge(record_id, example_id)
            self.training_examples[example_id] = source_ids
            return example_id

    def train_candidate(self, event_ids: Sequence[str] | None = None, step_size: float = 0.1) -> str:
        """Algorithm 1 lines 13-14 and paper Eq. (8)."""
        with self._lock:
            selected = list(event_ids if event_ids is not None else self.eligible)
            if not selected or any(item not in self.eligible and item not in self.training_examples
                                   for item in selected):
                raise ValueError("training window must contain eligible events or training examples")
            source_events: list[str] = []
            for item in selected:
                source_events.extend(self.training_examples.get(item, (item,)))
            source_events = list(dict.fromkeys(source_events))
            now = self._tick()
            window_id = stable_digest({"window": selected, "time": now,
                                       "environment": self.environment.digest})
            self.graph.add_node(LineageNode(window_id, NodeType.WINDOW, now,
                                            attributes={"selected_nodes": selected,
                                                        "event_ids": source_events}))
            for selected_id in selected:
                self.graph.add_edge(selected_id, window_id)
            candidate_params = self.trainer.train(self.parameters,
                                                   [self.events[item] for item in source_events], step_size)
            candidate_id = stable_digest({"parent": self.active_checkpoint_id, "window": window_id,
                                          "parameters": candidate_params.tolist()})
            self.graph.add_node(LineageNode(candidate_id, NodeType.CANDIDATE, now,
                                            attributes={"environment": self.environment.digest}))
            self.graph.add_edge(window_id, candidate_id)
            self.graph.add_edge(self.active_checkpoint_id, candidate_id)
            self.candidates[candidate_id] = {
                "parameters": candidate_params, "window_id": window_id,
                "event_ids": source_events, "selected_nodes": selected,
                "parent": self.active_checkpoint_id,
                "epoch": self.policy.epoch, "step_size": step_size, "logical_time": now,
            }
            return candidate_id

    def audit_and_promote(self, candidate_id: str, probes: np.ndarray,
                          thresholds: AuditThresholds | None = None) -> AuditReport:
        """Algorithm 1 lines 15-20: three-signal audit and atomic promotion."""
        with self._lock:
            thresholds = thresholds or AuditThresholds()
            candidate = self.candidates[candidate_id]
            lineage_complete = self.graph.validate_parent_completeness(
                candidate["window_id"], candidate["selected_nodes"])
            denied = [item for item in candidate["event_ids"]
                      if self.decisions[item][Sink.TRAIN] is Decision.DENY]
            lineage_complete = lineage_complete and not denied
            behavior, update_norm = audit_signals(self.parameters, candidate["parameters"], probes)
            reasons: list[str] = []
            if not lineage_complete:
                reasons.append("lineage_incomplete_or_denied_parent")
            if behavior > thresholds.max_behavior_score:
                reasons.append("behavior_threshold")
            if update_norm > thresholds.max_update_norm:
                reasons.append("update_norm_threshold")
            if candidate["epoch"] != self.policy.epoch:
                reasons.append("stale_policy_epoch")
            if candidate["parent"] != self.active_checkpoint_id:
                reasons.append("stale_active_head")
            passed = not reasons
            audit_id = stable_digest({"candidate": candidate_id, "behavior": behavior,
                                      "norm": update_norm, "passed": passed})
            report = AuditReport(audit_id, candidate_id, lineage_complete, behavior,
                                 update_norm, passed, tuple(reasons))
            self.graph.add_node(LineageNode(audit_id, NodeType.AUDIT, self.logical_time,
                                            attributes=asdict(report)))
            self.graph.add_edge(candidate_id, audit_id)
            if passed:
                self._promote(candidate_id, audit_id)
            return report

    def _promote(self, candidate_id: str, audit_id: str) -> None:
        candidate = self.candidates[candidate_id]
        self.parameters = candidate["parameters"].copy()
        sources = tuple(sorted(set(self.checkpoints[self.active_checkpoint_id].source_ids)
                               | set(candidate["event_ids"])))
        checkpoint_id = stable_digest({"candidate": candidate_id, "audit": audit_id,
                                       "parent": self.active_checkpoint_id})
        checkpoint = Checkpoint(checkpoint_id, self.active_checkpoint_id, self.logical_time,
                                self.parameters.tolist(), sources, self.environment.digest)
        self.graph.add_node(LineageNode(checkpoint_id, NodeType.CHECKPOINT, self.logical_time,
                                        attributes={"environment": self.environment.digest}))
        self.graph.add_edge(candidate_id, checkpoint_id)
        self.graph.add_edge(audit_id, checkpoint_id)
        self.graph.add_edge(self.active_checkpoint_id, checkpoint_id)
        self.checkpoints[checkpoint_id] = checkpoint
        self.active_checkpoint_id = checkpoint_id
        self.training_log.append({"logical_time": self.logical_time,
                                  "event_ids": list(candidate["event_ids"]),
                                  "step_size": candidate["step_size"], "promoted": True})
        self._save_snapshot(checkpoint_id)

    def revoke_and_recover(self, roots: Sequence[str], probe_digest: str = "none") -> RecoveryCertificate:
        """Run Algorithm 2 through the public rollback module."""
        from .rollback import rollback_and_replay
        return rollback_and_replay(self, roots, probe_digest)

    def state_digest(self) -> str:
        return stable_digest({"active": self.active_checkpoint_id,
                              "parameters": self.parameters.tolist(),
                              "memory": sorted((k, v.text, v.retrievable) for k, v in self.memory.items())})
