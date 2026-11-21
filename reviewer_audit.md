# Reviewer-Style Self-Audit

## Locked topic and fit

The manuscript matches the idea PDF: it studies persistent poisoning in single-device, multi-channel SLM personalization with both memory and LoRA state, and proposes provenance-through-selection, candidate quarantine, shared lineage, and rollback-and-replay. The systems framing fits mobile/edge and security venues; the final target should be chosen after device measurements determine whether systems cost or attack analysis is stronger.

## Contributions and evidence

1. Cross-sink laundering definition: supported formally; empirical existence remains to be demonstrated.
2. Provenance-carried selection: complete architecture and policy state machine; prototype pending.
3. Quarantine and shared lineage: algorithms and complexity specified; prototype pending.
4. Conditional guarantees: all results have complete proofs in the appendix; assumptions are strong and visible.
5. Evaluation protocol: detailed and reproducible, but contains no results.

## Novelty boundary

The closest verified work is SkillJack, which shows transformation of poisoned experiences into persistent skills, and recent persistent-memory attacks/defenses. The manuscript does not claim these papers studied local LoRA laundering. The novelty claim is limited to the proposed combination and problem formulation pending a refreshed pre-submission search.

## Citation status

Sixty-six verified references are in the bibliography; claim support is mapped in `citation_claim_map.csv`. Metadata-page and abstract checks support the current claims. Nineteen proceedings entries lack page ranges and should be completed. Enron/SMS and implementation-specific sources remain TODOs.

## Mathematical risks

- Complete mediation and sound lineage are architectural assumptions that require instrumentation evidence.
- Exact restoration depends on deterministic/versioned replay and retained data.
- Proposition 1 needs nonexpansiveness and does not predict ASR.
- Linearizability needs a real atomic head-swap/crash-recovery implementation.

## Experimental gaps

All core experimental claims are unmeasured. Required work includes the killer laundering experiment, device integration, adaptive retyping, baseline reproduction, power/thermal instrumentation, statistical analysis, and real plot/table replacement.

## Likely reviewer objections

- Phones may not yet fine-tune continuously in production.
- A conservative typed-only policy may capture most benefit.
- OS support makes deployment nontrivial.
- Provenance is not semantic trust and can burden users.
- Exact replay may conflict with privacy deletion and storage budgets.
- Public datasets may not represent multilingual private phone streams.

The manuscript acknowledges each objection and makes it testable, but acceptance readiness depends on measurements.

## Figures and compilation

Six figure types are present: architecture, method pipeline, threat boundary, theory dependency, experimental setup, and two-panel PGFPlots conceptual trends. Pure TikZ icons are used. The project compiles with Tectonic to a 48-page Elsevier preprint. Final page-by-page visual status is recorded in `figure_quality_audit.md`.

## Overall verdict

Strong design manuscript and experiment plan; not submission-ready as an empirical systems/security paper until all placeholders, metadata warnings, and device experiments are resolved.
