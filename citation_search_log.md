# Citation Search Log

## Scope and dates

Search performed 2026-10-03 for the locked topic: poisoning and remediation in single-device, multi-channel, mixed memory-plus-LoRA personalization. The search prioritized official arXiv pages, official NeurIPS/ICLR proceedings, ACL Anthology, and DBLP for cross-checking. Semantic Scholar/Hugging Face pages were used only as discovery aids when an official record was subsequently opened.

## Queries and direct record checks

- `site:arxiv.org/abs/2503.03704 MINJA memory injection attack agent`
- `site:proceedings.neurips.cc AgentPoison NeurIPS 2024`
- `site:arxiv.org/abs/2403.00108 LoRATK`
- `site:openreview.net "Machine Unlearning Fails to Remove Data Poisoning"`
- `"LoRATK" 2403.00108`
- `"Machine Unlearning Fails to Remove Data Poisoning" ICLR 2025`
- `site:arxiv.org/abs/2407.01031 PocketLLM`
- `site:arxiv.org "MobileFineTuner" 2512.08211`
- Direct official arXiv opens for every arXiv identifier retained in `references_verified.bib`.
- `Krum Byzantine tolerant machine learning arxiv Blanchard 2017`
- `site:arxiv.org on-device large language model fine-tuning mobile phone personalization`
- `site:aclanthology.org "This Email Could Save Your Life"`

## Inclusion criteria

1. Official metadata record resolves title, author order, year, and stable identifier.
2. Abstract or full text supports the precise scoped statement made in the manuscript.
3. Work belongs to a locked cluster: persistent agent memory, memory/RAG poisoning, LoRA/backdoors, on-device personalization, machine unlearning/rollback, experiments/datasets, or federated robustness used strictly as contrast.
4. Duplicate conference/arXiv versions are represented once, preferring the proceedings version where verified.
5. Recent preprints are labelled and cited only for abstract-supported claims.

## Exclusion criteria

- Identifier resolves to an unrelated title.
- Title or author metadata could not be resolved from an official source.
- Work shares keywords but does not support the cited claim.
- Blog, repository, or aggregator is the only available source.
- Work would shift the paper toward federated aggregation, privacy, or generic prompt injection.
- Dataset licensing/release identity is not yet pinned.

## Seed resolution

- “MINJA” resolved to *Memory Injection Attacks on LLM Agents via Query-Only Interaction*, arXiv:2503.03704.
- AgentPoison resolved to the NeurIPS 2024 proceedings record and DOI 10.52202/079017-4136.
- LoRATK resolved to arXiv:2403.00108.
- *Machine Unlearning Fails to Remove Data Poisoning Attacks* resolved to ICLR 2025 and arXiv:2406.17216; the proceedings version is cited.
- PocketLLM resolved to arXiv:2407.01031.
- MobileFineTuner resolved to the current official title at arXiv:2512.08211, which differs slightly from the concept document shorthand.
- MemGhost, Zombie Agents, MemoryGraft, SkillJack, GhostWriter, token-level LoRA backdoors, GAP, federated instruction-tuning poisoning, A-MemGuard, AgentSys, and DASGuard were resolved by direct arXiv identifier.

## Literature clusters

1. Persistent memory and cross-session attacks.
2. Memory/RAG and prompt-injection defenses.
3. LoRA security and textual backdoors.
4. On-device fine-tuning and personalization workloads.
5. Machine unlearning and exact-retraining alternatives.
6. Federated Byzantine robustness as an inapplicable contrast.

## Verification levels

The claim map conservatively marks retained works `abstract-only verified`, even when a proceedings PDF was available, unless a claim was checked against a deeper location. Manuscript claims are correspondingly limited to what the abstract or official metadata supports. No citation is used to prove a PoisonGuard theorem.

## Counts

- Candidate pool examined: 75 records/identifiers.
- Final verified bibliography: 66 entries.
- Rejected or deferred: 9 items documented in `references_rejected.md`.
- Directly relevant references: 64 of 66 (97%); two are foundational/peripheral context.
