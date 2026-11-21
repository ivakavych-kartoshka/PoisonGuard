# External attack and baseline provenance

All repositories below were manually cloned on 2026-11-21. The runner never downloads
anything. Each clone is clean at the pinned commit; the Python wrappers verify commit,
clean tree, and remote before any command is allowed to run.

| Component | Repository | Pinned commit | Local root | License | Documented entrypoint (not yet a pinned command) |
|---|---|---|---|---|---|
| AgentPoison | `https://github.com/AI-secure/AgentPoison` | `7b02e28f5e477052bd16c778fef7c1f78f7c9d7c` | `D:/NCKH/MobileSYS/attack_baselines/AgentPoison` | MIT | `python algo/trigger_optimization.py ...`, `python ReAct/run_strategyqa_gpt3.5.py ...` |
| MINJA | `https://github.com/dsh3n77/MINJA` | `a3ec8da0f7740b3fe629f6706e1c14296ee6861d` | `D:/NCKH/MobileSYS/attack_baselines/MINJA` | MIT | `EHR/`, `QA/`, `rap/` experiment directories |
| MemoryGraft | `https://github.com/Jacobhhy/MemoryGraft` | `823662058d1e0fe49306d1820d7947297ef3c252` | `D:/NCKH/MobileSYS/attack_baselines/MemoryGraft` | MIT | `python -m memorygraft.experiment --run-agent` |
| A-MemGuard (defense baseline) | `https://github.com/TangciuYueng/AMemGuard` | `dd92f7ff21b9a904a703141be3d5b80170e57228` | `D:/NCKH/MobileSYS/attack_baselines/AMemGuard` | MIT | `python ReAct/consistency.py --backend hf --model ...`, `python algo/trigger_optimization.py ...` |
| NPO / approximate unlearning (baseline) | `https://github.com/OPTML-Group/Unlearn-Simple` | `3083017cb317753725f35cc404c2d5aede1242ef` | `D:/NCKH/MobileSYS/attack_baselines/Unlearn-Simple` | MIT | `TOFU/`, `MUSE/`, `WMDP/`, `synthetic/` experiment directories |
| MemGhost | no public implementation | — | — | — | CSA research note `https://labs.cloudsecurityalliance.org/research/csa-research-note-memghost-ai-agent-memory-injection-2026072`; must be reported as not reproducible |

## What is pinned and what is not

- Pinned: repository URL, commit, local root, clean-tree check, remote check.
- Not pinned: executable `command` for each wrapper. The config keeps `command: []`
  on purpose, so any attempt to run an attack/baseline fails loudly with
  `ExternalDependencyUnavailable` instead of emulating a published method.
- No adapter converts these repositories' native outputs into PoisonGuard's
  measured-result schema yet. Therefore no ASR/FQR/utility/rollback number may be
  attributed to them.
- `expected_archive_sha256` left unset because the directory digest includes
  `.git` internals and would be unstable across ordinary git operations. Commit
  pin plus clean-tree check is the integrity gate.

## Execution prerequisites still missing

- AgentPoison: DPR/ctx encoder checkpoint and GPU for trigger optimization; GPT-3.5 or equivalent API for end-to-end StrategyQA/ReAct ASR. No API key configured.
- MINJA: LLM backend for query-only injection (GPT-4o-mini or local equivalent). No API key configured.
- MemoryGraft: `pip install -e ".[rag]"` plus an LLM agent/judge backend. No API key configured.
- A-MemGuard: vLLM not installed; documented backend uses Llama-3.1-8B-Instruct. Available GPU is RTX 4060 Laptop 8 GB.
- Unlearn-Simple: TOFU/MUSE/WMDP model and dataset snapshots not provisioned; 8 GB GPU insufficient for the larger unlearning settings.
- No repo has a bridge that converts its native output into PoisonGuard's measured-result schema, so `command: []` stays intentional.

## Clone caveats

- MINJA carries a `post-checkout` git-lfs hook. Clone checkout was retried with
  the hook disabled; working tree is complete and clean. Hook not executed.
- Unlearn-Simple initially failed checkout on Windows path-length limits;
  fixed with `core.longpaths=true` and `git reset --hard HEAD`. Working tree
  is complete and clean at pinned commit.
