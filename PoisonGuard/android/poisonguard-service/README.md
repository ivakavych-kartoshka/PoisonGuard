# PoisonGuard Android Service Skeleton

This directory is a **skeleton**, not a complete Android app. It shows the intended boundary between PoisonGuard's provenance policy and MobileFineTuner's native trainer.

## Intended flow

1. An Android app/service receives or constructs a `ProvenanceEvent`.
2. `PoisonGuardPolicy` returns `allow`, `quarantine`, or `deny` for memory and training sinks.
3. Only training-eligible events are converted into flattened `inputIds`, `attentionMask`, and `labels`.
4. `MobileFineTunerTrainingService` calls the MobileFineTuner SDK:
   - `MobileFineTuner.open(modelDir, true)`
   - `initLora(...)`
   - `createTrainer(...)`
   - `trainStep(...)`
5. The service hashes the resulting adapter/checkpoint and returns a `TrainingStepResult` with provenance metadata.

## Not implemented here

- Durable lineage storage, crash recovery, CAS promotion, and rollback.
- Real provenance capture from Android channels.
- Dataset normalization and evaluation metrics.
- Production security hardening.

The MobileFineTuner AAR must be published locally before this module can build.
See `MobileFineTuner/docs/ANDROID_SDK.md`.
