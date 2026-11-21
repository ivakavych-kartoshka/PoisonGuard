# Data Format

Real datasets are never downloaded. Each manually provisioned dataset root must contain `poisonguard_events.jsonl`, one event object per line.

Required fields are `event_id`, `payload`, `capture_time`, `app_id`, `channel`, `sender`, `user_authored`, `parent_ids`, `schema_version`, and `metadata`. `channel` is one of `typed`, `sms`, `notification`, `calendar`, `share`, `clipboard`, `screenshot`, or `derived`. `user_authored` is `true`, `false`, or `null`. Parent IDs must precede derived events and identify every direct dependency. The event ID must be generated from the canonical envelope; production adapters must verify rather than trust supplied IDs.

Recommended metadata fields are `dataset`, `source_split`, `user_id`, `conversation_id`, `task`, `label`, `synthetic`, `license_record`, and `payload_retention_class`. Split at user/conversation level and provide separate clean history, poison-bearing history, trigger-free evaluation, trigger evaluation, and post-deletion manifests.

Expected manual roots:

```text
/data/lamp/poisonguard_events.jsonl
/data/personachat/poisonguard_events.jsonl
/data/aeslc/poisonguard_events.jsonl
/data/licensed_sms/poisonguard_events.jsonl
```

LaMP, PersonaChat, and AESLC must preserve their official task/split metadata during normalization. Any Enron/SMS source requires the exact release, license, citation, and acquisition record; the manuscript has not fixed one. Risk/attack annotations must identify family, trigger-set ID, target predicate, poison budget, channel, and whether retyping was induced. Do not store secrets or raw private phone content in result manifests.
