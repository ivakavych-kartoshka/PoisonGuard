# Paper Implementation Specification

Source: `../main.pdf` (48 pages). This repository does not modify the source PDF.

## Identity and task

- **Title:** *PoisonGuard: Provenance-Carried Data Selection and Lineage Rollback for Poison-Resilient On-Device SLM Personalization*.
- **Central task:** protect a single device's memory and LoRA personalization sinks from mixed-trust mobile content, and causally remove identified poison by lineage rollback-and-replay.
- **Method:** PoisonGuard: authenticated provenance capture, sink-specific admission, least-trust inheritance, shared typed lineage, candidate quarantine/audit, atomic promotion, and versioned recovery.

## Implemented paper objects

- Event tuple (Eq. 1): payload, time, app, channel, sender, verified authorship, authenticated digest, and parent IDs.
- Channels: typed, SMS, notification, calendar, share, clipboard, screenshot, and derived.
- Policy (Eq. 3): independent memory/training decisions in `{allow, quarantine, deny}`.
- Typed DAG: event, decision, memory, example, window, candidate, audit, checkpoint, declassification, recovery certificate.
- LoRA equation (Eq. 2): `W' = W + alpha * B @ A / rank`, with dimension validation.
- Versioned transition, memory transform, deterministic candidate update, clean event-set selection, descendant invalidation, and recovery certificate.
- Algorithm 1: Provenance-Aware Admission and Quarantine.
- Algorithm 2: Lineage Rollback-and-Replay.
- Audit layers: lineage, behavioral score, and update norm.

Inputs are event records plus policy/configuration and optional already-provisioned dataset/model paths. Outputs are a lineage graph, mutable synthetic memory/adapter state, decisions, audit records, checkpoints, recovery certificates, metrics, and provenance-bearing result files.

## Equations, bounds, and metrics

The implementation exposes the event digest, LoRA update, policy decision, state transition, descendant closure, clean-event set, ASR, laundering persistence, false-quarantine and false-admission rates, injection/admission and retrieval rates, utility metrics, parameter/output distance, bootstrap intervals, the contaminated-displacement upper bound, storage upper bound, and replay-work accounting. The paper's multi-objective optimization is represented as an evaluator, not an optimizer, because the paper gives deployment weights rather than a solution algorithm.

## Baselines and experiments

Direct implementations: no defense, memory-only sanitization, provenance selection without recovery, shared lineage without quarantine, quarantine without rollback, and full clean replay. External adapter stubs: A-MemGuard, NPO/approximate unlearning, AgentPoison/MINJA-style attacks, MemGhost/GhostWriter/MemoryGraft-style attacks, real LoRA trainers, Android ingress, and power/thermal telemetry. Federated robust aggregation is intentionally out of scope because the paper treats it only as an inapplicable contrast.

Datasets requiring manual provisioning are LaMP, PersonaChat, AESLC, and a precisely licensed Enron/SMS release. The local harness uses only deterministic synthetic channel events. The protocol supports clean and attacked branches, pre/post-deletion measurement, remediation, multiple seeds, bootstrap intervals, ablations, and result plotting. It does not execute paper-level experiments.

## Assumptions and limits

The guarantees require a trusted ingress/policy/lineage/training base, complete mediation, immutable IDs, sound lineage, monotone trust inheritance, atomic promotion, deterministic versioned replay, and retention of required clean events. Origin does not prove intent; socially engineered retyping, unidentified poison, incomplete opaque-transform lineage, TCB compromise, and nondeterministic kernels remain outside the guarantee. Audits are signals, not universal detectors.

The manuscript is explicitly a design/protocol artifact: its result table is empty and its plotted curves are conceptual. No benchmark number is copied or replaced here. Phone services, real SLM training, Android integration, external attacks/baselines, energy measurement, human evaluation, and licensed datasets remain external work.
