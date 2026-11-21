# Baseline Adapters

Direct baselines are implemented as explicit policy/lifecycle variants, never as aliases for external research code. No defense admits both sinks. Memory-only sanitization quarantines remote memory while leaving training admission open. Provenance-only applies origin rules but omits lineage recovery. Shared-lineage/no-quarantine and quarantine/no-rollback separate the two lifecycle controls. Full clean replay is represented by the same deterministic replay engine used for the clean counterfactual.

`ExternalBaseline.run(input_manifest, output_dir, config)` defines the boundary for A-MemGuard and approximate unlearning. `build_baseline_adapter` and `build_attack_adapter` construct wrappers from explicit YAML specs; `repository_provenance` records path, git commit, dirty state, remote, and optional archive digest. Until a repository commit/hash, model/task adaptation, environment, input conversion, command, and output parser are pinned and validated, these adapters raise `ExternalDependencyUnavailable`. The attack adapter follows the same rule for AgentPoison/MINJA, MemGhost/GhostWriter/MemoryGraft, and LoRA backdoor implementations. Dummy/synthetic logic is never labelled as one of these published methods.

An external implementation must write a result manifest containing method/version/commit, input-manifest digest, model/base/adapter hashes, seed, start/end time, excluded failures, metric files, and environment versions. A wrapper test should compare a tiny fixture with that implementation's documented expected output before any benchmark run.

Federated robust aggregation methods are not baselines for this single-device state machine. Adding a synthetic multi-source reinterpretation would require a separate exploratory protocol and label.
