from __future__ import annotations

from typing import Any
import numpy as np

from poisonguard.baselines.simple import MemoryOnlyPolicy, NoDefensePolicy, ProvenanceOnlyPolicy
from poisonguard.data.schemas import Decision, Sink
from poisonguard.data.synthetic import generate_synthetic_events
from poisonguard.methods.core import PoisonGuardEngine
from poisonguard.methods.policy import DefaultPolicy
from poisonguard.metrics.metrics import false_admission_rate, false_quarantine_rate, parameter_distance
from poisonguard.models.adapters import DeterministicAdapterTrainer
from poisonguard.models.audits import AuditThresholds
from .common import LABEL, environment_from_config


def _run_method(name: str, policy: DefaultPolicy, config: dict[str, Any], recover: bool) -> dict[str, Any]:
    events, poison_ids = generate_synthetic_events(
        int(config.get("seed", 7)), int(config["synthetic"]["benign_count"]),
        int(config["synthetic"]["poison_count"]))
    trainer = DeterministicAdapterTrainer(int(config["model"]["dimension"]),
                                          float(config["model"]["clip_norm"]))
    engine = PoisonGuardEngine(environment_from_config(config), policy, trainer)
    for event in events:
        engine.ingest(event)
    if engine.eligible:
        candidate = engine.train_candidate(step_size=float(config["training"]["step_size"]))
        probes = np.eye(trainer.dimension)
        report = engine.audit_and_promote(candidate, probes, AuditThresholds(
            float(config["audit"]["max_behavior_score"]),
            float(config["audit"]["max_update_norm"])))
    else:
        report = None
    before = engine.parameters.copy()
    certificate = None
    if recover:
        for poison_id in poison_ids:
            if poison_id in engine.graph.nodes:
                certificate = engine.revoke_and_recover([poison_id], "synthetic-probes")
    benign_decisions = [engine.decisions[e.event_id][Sink.TRAIN] for e in events
                        if e.event_id not in poison_ids]
    malicious_decisions = [engine.decisions[item][Sink.TRAIN] for item in poison_ids]
    return {"method": name,
            "false_quarantine_rate": false_quarantine_rate(benign_decisions),
            "false_admission_rate": false_admission_rate(malicious_decisions),
            "candidate_promoted": bool(report and report.passed),
            "parameter_norm_before_deletion": float(np.linalg.norm(before)),
            "parameter_norm_after_remediation": float(np.linalg.norm(engine.parameters)),
            "remediation_parameter_change": parameter_distance(before, engine.parameters),
            "exact_recovery_certificate": bool(certificate and certificate.exact)}


def run_evaluation(config: dict[str, Any]) -> dict[str, Any]:
    methods = [
        _run_method("no_defense", NoDefensePolicy(), config, False),
        _run_method("memory_only", MemoryOnlyPolicy(), config, False),
        _run_method("provenance_without_lineage_recovery", ProvenanceOnlyPolicy(), config, False),
        _run_method("poisonguard", DefaultPolicy(), config, True),
    ]
    return {"label": LABEL, "real_experiment": False, "methods": methods,
            "note": "Numerical values describe the deterministic synthetic vector harness only."}
