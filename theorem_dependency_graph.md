# Theorem Dependency Graph

```text
Trusted TCB + Complete mediation
             |
Immutable IDs + Sound lineage ---> Lemma 1: provenance closure
             |                         |
Monotone policy -----------------------+--> Theorem 1: non-laundering
                                       |
Versioned deterministic replay --------+--> Theorem 2: exact restoration
                                                |
Registered-only poison influence --------------+--> Corollary 1: causal removal

Gradient clipping + contamination fraction + nonexpansive update
    -> Proposition 1: pre-promotion displacement bound

Bounded edge degree + checkpoint retention
    -> Proposition 2: storage bound

Checkpoint interval + affected lineage suffix
    -> Proposition 3: replay-work bound

Recovery barrier + atomic head swap
    -> Theorem 3: linearizable recovery
```

Experimental links: Theorem 2/Corollary 1 motivate clean-counterfactual equality checks; Proposition 1 motivates adapter-distance reporting but not an ASR prediction; Propositions 2 and 3 define storage/replay measurements; Theorem 3 motivates concurrency and crash tests.
