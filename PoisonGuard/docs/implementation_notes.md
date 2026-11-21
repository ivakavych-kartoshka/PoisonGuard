# Implementation Notes

The PDF was translated as a state machine, not as an unreported model experiment. `Event` implements the provenance tuple; `DefaultPolicy` implements per-sink decisions and least-trust inheritance; `LineageGraph` is the shared DAG; and `PoisonGuardEngine` groups Algorithm 1 transitions behind a lock. Candidate parameters are invisible until a passing audit and a current epoch/head check.

Algorithm 2 computes the inclusive descendant closure, marks affected objects invalid, walks active checkpoint ancestry, verifies the recorded environment, restores a retained snapshot, and replays surviving events/windows. The recovery certificate records exactness, roots, invalidated counts, replay IDs, hashes, and probe digest. The in-memory lock demonstrates visibility semantics only; production crash consistency requires a WAL-backed transaction layer.

The numerical trainer deliberately models only deterministic update flow. It lets tests establish lineage, promotion, counterfactual replay, and the paper's algebra without misrepresenting a synthetic vector as Qwen/Gemma. `apply_lora` separately implements the exact low-rank matrix equation. Real tokenization, batching, optimizers, probe inference, and phone kernels belong in a version-pinned external trainer.

The paper's audit policy is under-specified numerically because its experimental section is a protocol. Configurable thresholds and empirical benign-quantile calibration are therefore provided as engineering hooks; no conformal, optimality, or detector guarantee is claimed.
