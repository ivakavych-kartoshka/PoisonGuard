# Math-to-Code Audit

| Location | Object | Implementation interpretation | Edge cases / consistency |
|---|---|---|---|
| Eq. 1 | Event identity | Stable JSON serialization and SHA-256 over payload, envelope, ordered parents, and schema version | Capture time is explicit; mutation creates a new ID. Consistent. |
| Eq. 2 | LoRA | Validate `A=(r,d_i)`, `B=(d_o,r)`, `W=(d_o,d_i)` before `W + alpha*B@A/r` | Rank must be positive. Consistent. |
| Eq. 3 / policy table | Sink policy | Separate memory/training decisions; mixed-parent derivations take the least permissive decision unless a recorded declassification exists | The table is illustrative, so thresholds/rules remain config. |
| Eqs. 6-8 | Transitions | Event-log state machine with deterministic memory transform and a lightweight vector adapter trainer | The paper does not specify an optimizer; the simulator is not claimed as the real SLM trainer. |
| Descendant/clean set | Revocation | Inclusive descendant closure; denied and invalidated events are excluded | Missing roots are rejected instead of silently ignored. |
| Eq. 10 | ASR / LP | Mean Boolean success; `LP=post_delete_ASR-clean_ASR` | Empty samples return `NaN`, never zero. Consistent. |
| Eq. 11 | FQR | Benign decisions in quarantine or deny divided by benign count | Empty benign set returns `NaN`. Consistent. |
| Eq. 12 | Objective | Pure evaluator over caller-supplied weights/costs | No optimizer is asserted because the paper specifies none. |
| Algorithm 1 | Admission/promotion | Candidate namespace and epoch/head compare-and-swap are explicit | Process lock is a reference, not a distributed/Android transaction. |
| Algorithm 2 / Theorem 2 | Recovery | Choose newest unaffected snapshot, verify environment, replay admissible events in logical order, then atomically swap | Exactness is downgraded if payloads/environment are unavailable; no approximate result is labelled exact. |
| Eq. 13 | Influence bound | `2 * fraction * gradient_bound * sum(step_sizes)` | Validates fraction and nonnegative terms; not an ASR guarantee. Consistent with paper audit. |
| Eq. 14 | Storage bound | Direct byte arithmetic over vertices, bounded degree, checkpoints, indexes, and replay capsules | It is an upper-bound calculator, not measured storage. Consistent. |
| Replay proposition | Work | Report actual replayed event count and invalidated suffix | Checkpoint interval alone does not cap a widely inherited poison. Consistent. |
| Recovery linearizability | Visibility | Recovery barrier queues arrivals; complete state swaps under a lock | Crash durability needs a real WAL/SQLite backend and is therefore documented as external. |

No definition/theorem/algorithm conflict requiring a mathematical correction was found. The only necessary conservative choice is to expose exact-replay prerequisites as validation failures rather than quietly falling back to approximate repair.
