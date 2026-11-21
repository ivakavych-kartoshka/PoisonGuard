# Topic Alignment Check

| Axis | Idea PDF | Final manuscript | Status |
|---|---|---|---|
| Title | PoisonGuard; provenance-carried selection; lineage rollback; on-device SLM personalization | All four concepts appear verbatim, plus poison-resilient qualifier | Pass |
| Keywords | on-device personalization, poisoning, provenance, memory, adapters, rollback | Same objects appear in keywords and abstract | Pass |
| Problem | mixed-trust mobile channels can poison memory and locally trained adapters | Formalizes cross-sink laundering and post-deletion persistence | Pass |
| Algorithm | provenance tagger/policy, quarantine-promote, shared lineage, rollback-replay | Algorithms 1 and 2 implement exactly this lifecycle | Pass |
| Theorem directions | implied non-laundering, rollback, cost | Conditional non-laundering, restoration, influence, storage/replay, concurrency | Pass |
| Experiments | Pixel/OnePlus-class phones, compact Qwen/Gemma, LaMP/dialogue/email, six channels, memory/LoRA attacks, costs | Same family; unsupported Enron/SMS citations deferred | Pass |
| Baselines | no defense, memory sanitization, A-MemGuard, unlearning; FL only as contrast | Same; FL methods explicitly excluded from head-to-head single-device claims | Pass |
| Seed literature | MINJA, AgentPoison, LoRATK, PocketLLM, MobileFineTuner, unlearning and recent agent-memory work | Resolved exact titles/metadata and cited in centered related work | Pass |
| Forbidden drift | no federated/incentive/privacy takeover | Federated learning occupies one boundary subsection only; no mechanism design or DP agenda | Pass |

All major sections contain the required topic objects or support their analysis. No section requires revision for topic drift.
