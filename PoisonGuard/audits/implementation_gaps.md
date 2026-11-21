# Implementation Gaps

## External assets and integrations

- LaMP, PersonaChat, AESLC, and an exact licensed Enron/SMS release are not present; only validation adapters and a normalized schema exist.
- Qwen2.5-0.5B/Gemma-3-1B-class checkpoints, tokenizers, quantization, optimizer, LoRA module selection, and phone-native trainer are not provisioned.
- Android authenticated ingress, package UID evidence, screenshot/clipboard uncertainty, privileged services, durable SQLite/WAL transactions, recovery barrier, CAS pointer, and crash tests require a real harness.
- AgentPoison, MINJA, MemGhost, GhostWriter, MemoryGraft, A-MemGuard, NPO, and other released unlearning methods need pinned external repositories and task-specific adapters.
- Hardware energy, memory, temperature, throttling, scheduling, and job-completion telemetry require devices and, for joules, an external power monitor.
- Human reply evaluation, ethics review, malicious payload release review, and multilingual/accessibility workloads require manual protocols.

## Reference-implementation limits

- The deterministic vector trainer verifies lifecycle semantics; it is not an SLM or attack-effect model.
- In-memory lineage and snapshots are not durable or privacy-preserving. Payload encryption, replay-horizon erasure, indexes, reference-count GC, and storage measurements remain production work.
- Behavioral audit probes and numerical thresholds are synthetic hooks; efficacy and false-quarantine tradeoffs are unmeasured.
- The update audit reports vector norm only. Per-layer spectra, sketches, microbatch influence, and phone cost are not implemented.
- The current generic experiment runner does not activate real adapters even if paths are supplied; this avoids accidental full runs during repository creation.

## Author decisions needed

- Select exact Android devices/builds and real integration versus controlled emulation per channel.
- Select exact model checkpoints/licenses/framework commits and deterministic-equivalence criterion.
- Select an exact Enron/SMS release and citation.
- Pre-register detector thresholds, trigger-success predicates, utility metrics, equivalence margins, pilot-based power, replay horizon, and failure/exclusion rules.

No mathematical inconsistency was detected. Exactness is conditional, not unconditional, and the code surfaces environment/retention failures as guarantee downgrades.
