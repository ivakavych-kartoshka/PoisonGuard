# Checklist Hoàn Thành Paper — PoisonGuard (MobiSys 2027)

Cập nhật theo trạng thái hiện tại của repo: manuscript thiết kế + chứng minh + code tham chiếu đã có; **chưa có kết quả paper-level nào**. Đã có policy simulation trên event thật và system microbenchmark 3 lần trên Xiaomi 13T, tất cả gắn nhãn "not a paper result". Mọi bảng/đường cong hiện tại vẫn là placeholder hoặc conceptual.

## 0. Trạng thái đã hoàn thành (không cần làm lại)

- [x] Khóa chủ đề/idea: single-device, multi-channel SLM personalization, memory + LoRA adapter, provenance, quarantine, lineage rollback.
- [x] Viết đầy đủ các section: abstract, introduction, related work, preliminaries, system model, problem formulation, methodology, theory, algorithms, experiments (protocol), discussion, limitations, conclusion.
- [x] Formal results + proofs appendix: Lemma 1, Theorem 1/2/3, Corollary 1, Proposition 1/2/3.
- [x] Kiểm tra toán học, dependency graph, notation consistency.
- [x] Figure quality audit (6 figure types, TikZ/PGFPlots).
- [x] Claim strength audit (đã loại bỏ "first/SOTA/optimal/sharp" chưa chứng minh).
- [x] Code tham chiếu `PoisonGuard/`: schema, policy, lineage, core, rollback, metrics, baselines, tests (`53 passed`).
- [x] Synthetic smoke-test demo có nhãn rõ "not paper result".
- [x] Result integrity audit: không có kết quả bị fabricate.
- [x] External attack/baseline wrapper boundary: `PoisonGuard/src/poisonguard/baselines/external_wrappers.py` (validate provenance, fail loud, không emulate).
- [x] Real policy simulation trên normalized events: `PoisonGuard/configs/real_policy_aeslc.yaml`, chỉ policy rate, không ASR/utility.
- [x] Real protocol runner + metric ingestion: `real_runner.py`, `metrics/ingestion.py`, immutable manifest, aggregate chỉ từ measured file.
- [x] CLI stage `poisonguard real --stage assets|probe|policy|run|aggregate`.

---

## 1. Chuyển định dạng sang MobiSys/ACM (bắt buộc trước submission)

- [ ] Xác nhận CFP MobiSys 2027: page limit, format, double-blind, artifact evaluation, deadline.
- [ ] Chuyển `main.tex` từ `elsarticle` (Elsevier preprint) sang ACM conference format (`acmart`, `sigconf` hoặc sigmobile).
- [ ] Cập nhật `\journal{}`/metadata, author block, keywords, CCS concepts theo ACM.
- [ ] Kiểm tra giới hạn trang sau khi chuyển format (thường ~12 trang + references).
- [ ] Điều chỉnh figure/table width, caption style, reference style theo ACM.
- [ ] Kiểm tra overfull boxes sau khi đổi format và thêm tên tác giả.
- [ ] Tạo camera-ready version sau accept (nếu cần).

## 2. Công việc thực nghiệm blocking (core paper)

- [ ] Chạy "killer experiment" cross-sink laundering trên thiết bị thật: nội dung qua channel → vào memory → được chọn train LoRA → hành vi trigger còn lại sau khi xóa source/memory.
- [x] Model asset manifest recorded: `PoisonGuard/models_manifests/qwen2.5-0.5b-instruct.json`.
- [x] Five-step Qwen training pilot recorded on Xiaomi 13T: `PoisonGuard/outputs/pilot_xiaomi13t/qwen_step_measurement.json`.
- [x] Three-run Qwen step-time/RSS/thermal pilot recorded on Xiaomi 13T: `PoisonGuard/outputs/qwen_step_pilot_3seed/qwen_step_pilot.json` (not a paper result; không có energy monitor).
- [x] Real trainer probe recorded on Xiaomi 13T: `PoisonGuard/outputs/real_trainer_probe_xiaomi13t/real_training_probe.json` (MobileFineTuner via ADB, 5 steps, 33.6s, RSS ~2.16GB; not a paper result).
- [x] Real protocol run recorded on Xiaomi 13T: `PoisonGuard/outputs/real_protocol_run2_xiaomi13t/real_run_manifest.json` (100 AESLC events, MobileFineTuner device trainer, 0 attack/baseline pinned; not a paper result).
- [ ] Implement mobile provenance capture + state transitions (Android ingress, UID, channel, sender, user-authored evidence).
- [ ] Implement real trainer interface (Qwen2.5-0.5B / Gemma-3-1B-class) + hashing adapter/checkpoint + deterministic replay validation. Đã có ADB probe wrapper `scripts/run_mobilefinetuner_probe.py` và probe thành công; chưa có training trên normalized data/attack manifests.
- [ ] Chạy toàn bộ direct baselines và ablations với seed độc lập (≥5 training seeds + user-level bootstrap).
- [ ] Đo rollback equality, ASR, clean utility, false quarantine, storage, latency, energy, memory, thermal. Đã có 3-seed device systems measurement (step time median 3919 ms, peak RSS median 2174692 kB) tại `PoisonGuard/outputs/aggregate_systems/real_metrics_aggregate.json`; energy/ASR/utility/rollback vẫn `count: 0`.
- [ ] Hoàn thành adaptive user-retyping/confirmation evaluation.
- [ ] Thay thế mọi cell `--` trong bảng kết quả và 2 đường PGFPlots conceptual bằng dữ liệu thật.
- [ ] Pre-register seeds, pilot/power analysis, thresholds, equivalence margins, attack budgets, exclusion rules, ethics controls.

## 3. Thiết bị, model, framework

- [x] Backend training chính đã chọn: MobileFineTuner (C++ native); build Android ARM64 thành công; smoke test 2/2 pass trên Xiaomi 13T.
- [x] Adapter boundary cho trainer ngoài đã thêm: `PoisonGuard/src/poisonguard/models/external_trainer.py` (failure-loud, hash output).
- [x] Real protocol runner added: `PoisonGuard/src/poisonguard/experiments/real_runner.py` (asset gate, normalized-event input manifest, pinned attack/baseline/trainer invocation, telemetry import, immutable manifests, no fabricated metrics).
- [x] Dataset normalizers added for AESLC, SMS, PersonaChat, and LaMP JSON with tests.
- [x] Normalized manifests created: AESLC (14,436), SMS (5,574), PersonaChat (19,369), LaMP-4 dev (332,466), LaMP-4 train (332,482).
- [x] Pilot config đã thêm: `PoisonGuard/configs/pilot_xiaomi13t.yaml`.
- [x] Android service skeleton đã thêm: `PoisonGuard/android/poisonguard-service/` (Kotlin, MobileFineTuner SDK boundary).
- [x] Exact primary device/build recorded: Xiaomi 13T `2306EPN60G`, `9DBQFE8LEEWWYHYD`, Android 16 `BP2A.250605.031.A3`, `mt6895`, `arm64-v8a` (xem `configs/real_experiment_template.yaml`).
- [ ] Bổ sung RAM, ambient temp, governor state, charging policy controlled. Đã ghi USB charging + battery health/temperature snapshot trong pilot; chưa kiểm soát charging policy.
- [ ] Bao gồm ít nhất 1 thiết bị cũ + 1 thiết bị mới để tránh claim single-phone.
- [ ] Pin Qwen/Gemma checkpoints, tokenizer, quantization, LoRA rank {4,8,16}, optimizer, precision, gradient accumulation, framework commit.
- [ ] Ghi rõ channel nào là real OS integration, channel nào là controlled emulation (SMS/RCS, screenshot index).
- [ ] Implement durable storage: SQLite/WAL, crash recovery, CAS promotion pointer, recovery barrier, concurrency, GC, encryption, retention.
- [ ] Thu thập energy qua external power monitor; Android energy counters chỉ là secondary. Ghi median/IQR/trial count.

## 4. Dữ liệu và workloads

- [x] Normalize LaMP-4 dev/train, PersonaChat, AESLC, SMS theo `docs/data_format.md`; license/citation vẫn ở mục 4 bên dưới.
- [ ] Chọn + cite exact licensed Enron-derived release (hoặc quyết định không dùng).
- [ ] Chọn + cite exact SMS/RCS-like public corpus + license + preprocessing. Đã có `datas/sms+spam+collection/poisonguard_events.jsonl` (5,574), nhưng chưa cite/license/preprocessing record.
- [ ] Split theo user/conversation; cung cấp clean history, poison-bearing history, trigger-free eval, trigger eval, post-deletion manifests.
- [ ] Tạo synthetic calendar/notification/clipboard/screenshot text từ templates + public benign distributions.
- [ ] Ethics/licensing review cho dữ liệu có thông tin cá nhân.
- [ ] Ghi rõ attack annotations: family, trigger-set ID, target predicate, poison budget, channel, retyping induced.

## 5. Attacks và baselines

- [x] Adapter boundary cho AgentPoison, MINJA, MemGhost, MemoryGraft, A-MemGuard, NPO/unlearning đã thêm; chưa pin repo/command nên mọi run sẽ fail loud.
- [ ] Pin + adapt AgentPoison, MINJA, MemGhost, GhostWriter, MemoryGraft (chỉ nếu normalize được vào event schema). AgentPoison `7b02e28f`, MINJA `a3ec8da0`, MemoryGraft `82366205` đã pin URL+commit+clean tree; MemGhost không có code public; GhostWriter chưa pin. Command vẫn để trống nên wrapper fail loud, chưa adapt output schema.
- [ ] Pin A-MemGuard implementation hoặc ghi rõ không reproduce được. Đã pin `TangciuYueng/AMemGuard` @ `dd92f7ff21b9a904a703141be3d5b80170e57228`, MIT.
- [ ] Pin NPO/RMU/unlearning implementation + adaptation cho task/model. Đã pin `OPTML-Group/Unlearn-Simple` @ `3083017cb317753725f35cc404c2d5aede1242ef`, MIT.
- [ ] Implement behavioral probe construction, clean-utility metrics, layer/spectral audit, optional influence approximations.
- [ ] Chạy 4 attack families: memory retrieval, external-content persistence, LoRA data poisoning, adaptive retyping.
- [ ] Ablations: remove provenance, least-trust inheritance, shared vs separate lineage, behavioral audit, update audit, quarantine, checkpoint interval, replay horizon, env pinning.
- [ ] Ghi rõ FL baselines chỉ là inapplicable contrast, không plot head-to-head single-device.

## 6. Metrics và phân tích thống kê

- [x] Metric ingestion/aggregation helpers đã thêm cho ASR before/after, FQR, utility, rollback, telemetry; chỉ đọc measured file và fail loud khi thiếu field bắt buộc.
- [ ] Tính ASR (before/after deletion), clean-trigger false activation, laundering persistence LP từ harness thật.
- [ ] Recovery: hash equality/numerical distance/output-distribution distance/residual ASR/clean utility.
- [ ] Policy: FQR, false admission, user-confirmation burden.
- [ ] Utility: task metric chính thức + bootstrap CI across users/seeds.
- [ ] Systems: wall/active time, peak memory, bytes, battery energy, avg/peak temp, throttling, job completion.
- [ ] So sánh PoisonGuard recovery với clean counterfactual branch, không chỉ với pre-recovery attacked model.
- [ ] Tách audit probe construction khỏi attack evaluation; adaptive attacker chỉ biết family, không biết exact probe.

## 7. Chứng minh và giả thiết

- [ ] Test complete mediation với adversarial bypass attempts.
- [ ] Validate lineage parent completeness cho summarization, embeddings, window construction.
- [ ] Xác định deterministic training có khả dụng bitwise không; nếu không, định nghĩa + biện minh numerical equivalence tolerance.
- [ ] Đo nonexpansive-update assumption thực tế hoặc chuyển Proposition 1 sang appendix qualified.
- [ ] Test linearizability với atomic head-swap/crash recovery trên implementation thật.
- [ ] Giữ claims conditional, không dùng "optimal/sharp/SOTA/universal".

## 8. Trích dẫn và metadata

- [ ] Resolve exact Enron + SMS corpus releases + citations.
- [ ] Add Android API/build, energy monitor, pinned software-release citations.
- [ ] Add page ranges cho 19 conference references BibTeX đang thiếu.
- [ ] Lặp lại literature search ngay trước submission, đặc biệt post-2026 on-device personalization poisoning.
- [ ] Verify metadata all 66 references (title/authors/venue/year/pages).
- [ ] Không dùng deferred references (MobiZO, Crayon, PortLLM, EMG-RAG, generic Enron/SMS) cho claim chính.

## 9. Tác giả và venue metadata

- [ ] Thay anonymous author + placeholder affiliation bằng tên thật/tổ chức.
- [ ] Thêm CRediT authorship, funding, ethics approval, data/code availability statements.
- [ ] Xác nhận licenses của tất cả dataset/model.
- [ ] Double-blind: kiểm tra không lộ tên/affiliation trong manuscript, code, supplementary.
- [ ] Chuẩn bị artifact evaluation package (code, data manifest, scripts, seeds, lineage schemas).

## 10. LaTeX, hình và compile

- [ ] Loại bỏ Tectonic/legacy `algorithm.sty` invalid-byte warning hoặc compile bằng venue toolchain.
- [ ] Thêm page ranges để silence BibTeX warnings.
- [ ] Re-run figure preview audit sau khi real plots thay thế conceptual curves.
- [ ] Recheck overfull boxes sau khi thêm tên tác giả + venue formatting.
- [ ] Đảm bảo abstract/keywords/title chứa required terms.
- [ ] Kiểm tra labels/cross-references không unresolved.

## 11. Release engineering

- [ ] Publish code, manifests, device details, raw traces, analysis scripts, seeds, lineage schemas.
- [ ] Redact private event content nhưng giữ auditable run identifiers.
- [ ] Cung cấp reproducibility README + one-command analysis pipeline.
- [ ] Đảm bảo không commit credentials/dataset/raw private phone content.
- [ ] Ghi failure/excluded runs/manual interventions.
- [ ] Cập nhật `audits/result_integrity_audit.md` với immutable provenance trước khi cite kết quả.

## 12. Kiểm tra cuối trước submission

- [x] Full test suite chạy xanh: `53 passed` (`PYTHONPATH=src python -m pytest -q`). Cần ghi version Python/NumPy khi freeze artifact.
- [ ] Compile manuscript final, kiểm tra page count + không placeholder.
- [ ] Kiểm tra bảng kết quả không còn `--` và caption không còn "conceptual expected trends".
- [ ] Kiểm tra `real_experiment` flag truthful.
- [ ] Peer/self review theo reviewer_audit.md objections.
- [ ] Final diff review: không có fabricated numbers, không overclaim.

---

## Gợi ý thứ tự thực hiện

1. Hoàn thành implementation thực + datasets + devices (mục 2–5).
2. Chạy experiments + thay placeholders (mục 6).
3. Cập nhật citations/metadata (mục 8–9).
4. Chuyển format ACM + compile (mục 1, 10).
5. Release + final audit (mục 11–12).

## 13. AgentPoison attack ASR pilot (hoan thanh, 2026-11-22)

- [x] Pin AgentPoison @ `7b02e28f` (clean tree sau smoke patch restore).
- [x] Bridge script `PoisonGuard/scripts/run_agentpoison_bridge.py` (Windows timestamp patch + restore, PYTHONUTF8, local Ollama qwen2.5:7b-instruct).
- [x] ASR bridge script `PoisonGuard/scripts/run_agentpoison_asr_bridge.py` (benign + adv evaluator, metric aggregation, "not a paper result" label).
- [x] 3 seed trigger artifacts: `outputs/agentpoison_run_seed{1,2,3}_v2/attacks/agentpoison.json`.
- [x] 3 seed measured ASR files: `outputs/measured_agentpoison_seed{1,2,3}.json` (ASR before 1.00/0.95/0.95; clean utility 0.70 all; FQR 0.00 all).
- [x] Aggregate: `outputs/aggregate_agentpoison/real_metrics_aggregate.json` (ASR before median 0.95, IQR 0.025, n=3).
- [x] Code commit updated to `958bfec773d19e01da2d4c303aa8fd57cecebb77` and pushed.
- [ ] Scale (b): full `1000/100` AgentPoison run (20-40h) -- chua chay.
- [ ] Defense numbers: ASR after, rollback, FQR, utility after (can policy pipeline + device).
- [ ] Baselines: A-MemGuard, MINJA, MemoryGraft bridges.
- [ ] Energy: can external power monitor (hien tai n/a).
