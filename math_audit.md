# Mathematical Audit

| Result | Assumptions | Proof status | External theorem/citation | Possible gap | Dimensions/dependencies | Strength decision |
|---|---|---|---|---|---|---|
| Lemma 1, provenance closure | immutable identity; sound lineage | complete | none | opaque transform may omit a parent | graph reachability only | retained as sufficient-condition lemma |
| Theorem 1, non-laundering | trusted TCB; complete mediation; immutable identity; sound lineage; monotone policy | complete | none | fails for bypass or silent relabelling | independent of model dimension | retained; explicitly not a detector guarantee |
| Theorem 2, exact rollback-and-replay | complete mediation; sound lineage; retained ordered events; versioned deterministic execution | complete | none | nondeterministic kernels or erased payloads break premise | equality depends on full version/randomness record | retained with floating-point qualification |
| Corollary 1, post-recovery poison removal | Theorem 2 plus all poison influence entering registered transitions | complete | none | unidentified poison not in revocation set remains | causal, not semantic equality | retained and narrowed to registered causal influence |
| Proposition 1, contaminated displacement | clipped gradients; contamination fraction; coupled batches; nonexpansive clean update | complete | triangle inequality only | Adam/momentum or expansive maps require Lipschitz factors | gradient × step size has parameter units; linear in alpha, G, and sum eta | retained; explicitly not an ASR bound |
| Proposition 2, storage bound | bounded vertex/edge size and degree; K retained LoRA checkpoints | complete | none | indexes and replay capsules implementation-dependent | all additive terms are bytes; O(N)+O(Kp_L) | retained |
| Proposition 3, replay-work bound | checkpoint interval and lineage-complete invalidation | complete | none | poison ancestor can invalidate every later checkpoint | work depends on affected suffix, not merely interval | retained with explicit worst case |
| Theorem 3, recovery linearizability | recovery barrier; immutable heads; atomic compare-and-swap | complete | standard linearization argument, no external theorem invoked | long recovery reduces availability | state visibility rather than numerical claim | retained |

No proof is labelled as a sketch or conjecture. The results verify the specified state machine; empirical detector effectiveness remains an experimental question.
