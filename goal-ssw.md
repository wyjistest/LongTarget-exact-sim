# LongTarget exact SSW-CUDA 后端执行目标（修订版）

> **文件角色**：本文件必须保存为仓库根目录的 `goal-ssw.md`。**不得覆盖现有 `goal.md`、`goal-final.md` 或 `goal-bioinformatics.md`**。调用本地 Codex 时应明确指定本文件为当前执行入口。
>
> **目标**：在不改写 CPU authority 语义、不放宽 clustered TFO1–TFO5 严格合同的前提下，逐层开发一个 GPU-native 的 modified-SSW 兼容后端，并用提前冻结的 correctness、Amdahl、futility、holdout 和性能 gate 决定它是否能够：
>
> 1. 逐层复现 CPU `sswNew.cpp` 的可观察结果；
> 2. 在支持范围内不再执行完整 CPU authority；
> 3. 最终提供端到端 safe 加速；
> 4. 若无法达到原 B3 `>=10×` 标准，诚实关闭 Bioinformatics widening 路线，但仍保留方法/系统工程成果。
>
> **评审时已知本地状态**：本文件修订时，用户报告本地 HEAD 为 `9f87aac`，领先远端 20 个提交。执行时必须重新读取实际 HEAD；`9f87aac` 只是证据锚点，不是强制 checkout 起点。

---

## 0. 不可改写的历史证据

### 0.1 旧 GPU traceback v1

以下历史结论必须保留，不能回写为 pass：

```text
old_gpu_traceback_v1_contract = verified_only_contract
old_phase3_sequential_verified_b3 = no_go
old_phase3_decision = stop_after_pilot_futility
```

旧 sequential verified 路径为：

```text
GPU candidate + complete CPU authority + comparison
```

它结构上不能快于单独 CPU authority。旧结论只适用于该架构。

### 0.2 已完成 canonical-hybrid-v2

本轮开始前，仓库已经完成 `canonical-hybrid-v2`，不得把相同科学问题当成尚未验证：

```text
regression clustered Top-5 = 36/36 clean
regression full-output      = 35/36 clean
fresh holdout               = 60/60 clean
performance pilot           = 18/18 correct
A/H paired speedup          = 0.257592x
H relative slowdown         = 3.882109x
B3-v2                       = no_go
canonical-hybrid-v2 track   = closed
```

至少读取并冻结以下证据及其引用的 receipts/manifests：

```text
paper/bioinformatics/canonical_hybrid_v2_regression_decision.md
paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md
paper/bioinformatics/canonical_hybrid_v2_performance_decision.md
paper/bioinformatics/application_pilot_receipt.json
paper/bioinformatics/phase3_postpilot_decision.json
paper/bioinformatics/phase2_decision.md
paper/bioinformatics/holdout_workload_results.tsv
paper/bioinformatics/holdout_mismatch_details.tsv
```

若上述决策文件引用的 machine-readable receipt、manifest、selection receipt 或 source data 路径不存在，Phase 0 必须 `blocked`，不得靠手工转录数字继续。

### 0.3 本轮与 v2 的关系

新的 exact SSW-CUDA 后端是一个**新实现 epoch**，目标是消除 v2 的主要成本来源：

```text
GPU exact pre-align / selection / forward endpoint
+ GPU reverse-start
+ GPU canonical banded traceback
```

Phase 5–10 的结果必须写成：

> new exact SSW-CUDA backend relative to the completed canonical-hybrid-v2 no-go baseline

不得写成第一次验证 GPU prepass + CPU traceback，也不得重开已关闭的 v2 rescue track。

---

## 1. Agent 总指令

### 1.1 执行方式

从状态块的 `active_phase` 开始。一次只完成一个 phase。每个 phase 都必须：

```text
实现
测试
生成 machine-readable evidence
运行 checker
更新状态
提交 commit
```

未通过当前 phase 的硬 gate，不得进入下一 phase。

### 1.2 开始前必须读取

```text
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -40
git remote -v
Makefile
README.md
goal.md
goal-final.md
goal-bioinformatics.md
goal-ssw.md
paper/PAPER_PREP_STATUS.md
paper/bioinformatics/README.md
paper/bioinformatics/phase2_decision.md
paper/bioinformatics/phase3_postpilot_decision.json
paper/bioinformatics/application_protocol.md
paper/bioinformatics/application_pilot_receipt.json
paper/bioinformatics/canonical_hybrid_v2_regression_decision.md
paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md
paper/bioinformatics/canonical_hybrid_v2_performance_decision.md
paper/bioinformatics/holdout_workload_results.tsv
paper/bioinformatics/holdout_mismatch_details.tsv
fasim/sswNew.cpp
fasim/ssw_cpp.cpp
fasim/ssw_cpp.h
fasim/Fasim-LongTarget.cpp
fasim/fastsim.h
fasim/gasal2_align_bridge.cpp
scripts/compare_fasim_segmented_contract.py
所有已有 SSW/GASAL2/CUDA runner、receipt、manifest、schema、测试和 checker
```

文件布局变化时先搜索实际实现。不得因建议路径不存在而新建重复系统。

### 1.3 绝对纪律

1. 不得覆盖、删除或改写历史 Phase 2、Phase 3、canonical-hybrid-v2 evidence。
2. 不得把旧 v2 的 60/60 correctness 当成新 full-GPU 后端的独立 promotion。
3. 不得把旧 38× candidate-only、旧 sequential verified、旧 H2 pilot 或 kernel-only 时间作为新 safe speedup。
4. CPU modified-SSW 是本轮唯一语义 authority。Accelign、G3SA、GASAL2 都只是实现参考。
5. CPU oracle 只能增加默认关闭、经零行为差异验证的 instrumentation；不得边实现 GPU 边静默修改 authority。
6. 若发现 CPU oracle bug，停止当前 phase，写独立 `oracle_change_proposal.md`；未经 owner 决策不得混入本轮。
7. correctness 优先于性能。L1–L7 任一 strict gate 未通过，性能不能使阶段 pass。
8. 禁止 query/gene/target 名称、source ID、digest、已知 case、blacklist、allowlist 或结果驱动特例。
9. 已知 `hq10_ht02`、`hq11_ht02` 只能作为 regression fixtures，生产代码不得识别其身份。
10. 不得删除、覆盖、替换 mismatch、OOM、timeout、fallback、非零退出、partial artifact 或慢结果。
11. 所有昂贵运行前必须先提交代码、manifest、attempt plan、预算和 checker，且工作树 clean。
12. 任何看过结果的数据立即降级为 regression；修复后 promotion 必须使用新的未运行 holdout。
13. 所有 DP/score/tie key 使用精确整数；不得使用 float tolerance、TF32、half 或近似 equality。
14. GPU reduction/compaction 必须确定性；不得依赖 atomic winner、线程完成顺序或未承诺稳定性。
15. 不得把 locus overlap、相同 cluster 或 equal score alternative CIGAR 替代 canonical-row strict equality。
16. `query_len <= 2812` 只能描述工程范围，不能称为所有 lncRNA 或生物学短 RNA 定义。
17. 原 B3 `>=10×`、节省 `>=8 hours`、24h capacity `>=10×` 标准不得降低。
18. Amdahl gate 只决定 B3 理论可达性；即使 B3 关闭，方法/系统工程路线仍可继续。
19. L8 在本轮始终是 diagnostic，**绝不在 Phase 13 看完结果后临时升级为产品合同**。
20. byte/word fresh-holdout 选择只能使用运行前可得的静态代理；不得观察运行路径后补样本。
21. A/H/G 各 arm 必须独立执行，后端不得读取其他 arm 输出；所有 correctness comparison 延后离线完成。
22. 每个研究 phase 有固定 repair 次数和 GPU-hour 上限。超预算必须 `no_go` 或 `blocked`，不能无限搜索。
23. 第三方代码必须 pin commit、记录 license 和 patch。G3SA 默认只借鉴算法结构；复制 GPL 代码前必须完成兼容性审查。
24. 不得自动 push、强推、tag、release、Zenodo、购买云资源或代表作者投稿。
25. 不得 `git reset --hard`、`git clean -fdx`、重写用户 commit 或覆盖未跟踪文件。
26. 长 query、完整 KCNQ1OT1、完整 hg38、rank-unsafe pruning 不属于本轮。
27. 本文件是状态机；DP、CIGAR、telemetry、holdout 和性能细则必须拆到独立规范文件，避免 Phase 13 后再出现技术规范章节。

### 1.4 状态值

```text
pending
in_progress
pass
no_go
blocked
not_available
```

`no_go` 表示预注册证据足以关闭该路线；`blocked` 表示环境/输入/权限不足，尚无科学结论。

---

## 2. 执行状态

Codex 每完成一个 phase 后更新本块，不得提前标记。

```text
reviewed_local_head = 9f87aac
execution_start_head = 9f87aace6d96cf8142e3816299f04defae5710e4
execution_branch = gasal2-kcnq1ot1-focused-review
execution_ahead_remote = 20

historical_gpu_traceback_v1 = verified_only_contract
historical_phase3_v1_b3 = no_go
historical_canonical_hybrid_v2_regression_top5 = 36/36
historical_canonical_hybrid_v2_regression_full_output = 35/36
historical_canonical_hybrid_v2_fresh_holdout = 60/60
historical_canonical_hybrid_v2_performance_correct = 18/18
historical_canonical_hybrid_v2_speedup = 0.257592
historical_canonical_hybrid_v2_slowdown = 3.882109
historical_canonical_hybrid_v2_b3 = no_go
historical_canonical_hybrid_v2_track = closed

ssw_cpu_oracle_epoch = 2
ssw_cuda_program_epoch = 1
ssw_cuda_runtime_commit = UNSET
ssw_cuda_final_holdout_freeze = UNSET
ssw_cuda_release_candidate = UNSET

bioinformatics_b3_track = closed_amdahl
engineering_track = active
l8_contract_status = diagnostic_only

active_phase = 7
phase_0_status = pass
phase_1_status = pass
phase_1_profile_execution_epoch = 2
phase_1_analysis_epoch = 2
phase_1_v1_status = blocked_by_fixed_timeout
phase_1_recovery_status = pass
phase_2_oracle_execution_epoch = 1
phase_2_status = pass
phase_3_status = pass
phase_4_upstream_evidence_epoch = 1
phase_4_architecture = C_mixed_in_tree_checkpoint_recompute
phase_4_accelign_build_attempts = 1
phase_4_g3sa_build_attempts = 3
phase_4_status = pass
phase_5_status = pass
phase_6_status = pass
phase_7_status = in_progress
phase_8_status = pending
phase_9_status = pending
phase_10_status = pending
phase_11_status = pending
phase_12_status = pending
phase_13_status = pending

last_completed_phase = 6
last_decision = phase6_l3_exact_forward_pass
last_evidence_doc = paper/ssw_cuda/forward_endpoint_receipt.json
last_test_command = make check-ssw-cuda-phase6
last_commit = e41f76d
```

### 2.1 Phase 依赖

```text
Phase 0  当前仓库状态、v2 历史证据、排除集合与新 epoch 冻结
Phase 1  CPU authority profiling、Amdahl 上限与早期 futility gate
Phase 2  CPU SSW 可观察语义、零行为差异 instrumentation
Phase 3  differential corpus、分层比较器与 holdout policy
Phase 4  Accelign/G3SA bounded spike 与架构选择
Phase 5  GPU per-column maxima + exact selection（L1/L2）
Phase 6  GPU forward endpoint（L3）
Phase 7  new forward-hybrid checkpoint + 早期性能/止损
Phase 8  GPU reverse-start（L4）
Phase 9  GPU banded traceback/CIGAR（L5/L6）
Phase 10 full-GPU backend 集成与 regression（L1-L7）
Phase 11 全新独立 holdout、确定性与可选跨架构 promotion
Phase 12 正式性能、真实应用、CLI 与 release candidate
Phase 13 最终审计和投稿路线决策
```

Phase 7 不是重开 canonical-hybrid-v2。它只是验证新 L1–L3 实现是否相对已关闭的 H2 基线有工程价值，并估计完成 L4/L5 后的性能余量。

---

## 3. 合同层级与产品边界

### 3.1 唯一 authority

CPU oracle 为 Phase 0 实际 checkout 中冻结的：

```text
fasim/sswNew.cpp
fasim/ssw_cpp.cpp
fasim/ssw_cpp.h
Fasim-LongTarget 实际调用链
```

必须冻结：source commit、compiler、flags、SIMD path、binary digest、CPU、microcode、scoring matrix、gap 参数、mask/filter/flag、byte/word availability。

### 3.2 L0–L8

#### L0 输入与参数

```text
encoded query/ref bytes and lengths
strand/rule/identity round/start/cutlength
substitution matrix
gap open/extend
threshold/filter/maskLen/flag
```

#### L1 per-reference-column maxima

CPU `ssw_pre_align()` 最终 column vector：长度、每列整数、vector digest、max score、word recompute final semantics 全部 exact。

#### L2 attempt selection

```text
selected set
multiplicity
stable order
selection reason
scoreinfo_index
reference column/score
zero false negative
zero unexpected extra descriptor
```

#### L3 forward endpoint

必须显式实现并比较：

```text
score1
ref_end1
read_end1
score2/ref_end2（若当前调用合同可观察）
CPU-defined exact endpoint tie-breaking
```

Phase 5 只有 L1/L2，不得声称已经提供 L3。

#### L4 reverse-start

```text
ref_begin1
read_begin1
reverse score
reverse endpoint/tie key
```

#### L5 canonical CIGAR

```text
cigarLen
packed ops
expanded ops
band history
CIGAR digest
```

必须复现 CPU `banded_sw()` 选择的 canonical path。

#### L6 LongTarget emitted row

坐标、aligned/ungapped TFO/TTS、Score、Nt、MeanIdentity、MeanStability、完整 canonical row digest。

#### L7 本轮产品合同

```text
score-ranked clustered TFO1–TFO5 canonical rows
stability-ranked clustered TFO1–TFO5 canonical rows
Nt-ranked clustered TFO1–TFO5 canonical rows
```

#### L8 full-output diagnostic only

```text
TFOsorted canonical row multiset
row count
sorted digest
```

本轮从 Phase 0 到 Phase 13 始终：

```text
l8_contract_status = diagnostic_only
```

即使 L8 在最终 holdout 全 clean，也只能报告 diagnostic observation，不得升级为产品合同。若未来要 promotion full-output，必须另立目标、另冻全新 holdout。

### 3.3 已知 mismatch 根因

固定表述：

```text
reproducible GASAL2 GPU endpoint/CIGAR traceback divergence,
consistent with an alternative reported-equal-score alignment path
```

`hq10_ht02`：gap placement regression；`hq11_ht02`：forward/reverse endpoint/CIGAR regression。不得声称已经找到具体 DP tie cell，除非新 trace 直接证明。

### 3.4 后端命名

```text
A  = ssw_cpu_oracle_v1
H2 = canonical_hybrid_v2（历史、closed、slow）
P  = ssw_cuda_preselect_v1（L1/L2）
F  = ssw_cuda_forward_hybrid_v1（GPU L1–L3 + CPU L4/L5）
R  = ssw_cuda_reverse_hybrid_v1（GPU L1–L4 + CPU L5）
G  = ssw_cuda_full_v1（GPU L1–L5 + unchanged downstream）
```

不得把这些统称为 GASAL2，也不得复用旧 runtime epoch 名称。

---

## 4. 规范文件与 artifact 结构

### 4.1 本文件只保留状态机

Phase 0–3 必须创建并维护：

```text
docs/ssw_cuda/DP_CONTRACT.md
docs/ssw_cuda/ENDPOINT_CONTRACT.md
docs/ssw_cuda/CIGAR_CONTRACT.md
docs/ssw_cuda/TELEMETRY_SPEC.md
docs/ssw_cuda/HOLDOUT_POLICY.md
docs/ssw_cuda/PERFORMANCE_PROTOCOL.md
paper/ssw_cuda/PROGRAM_STATE.json
paper/ssw_cuda/STATUS.md
```

这些文档是技术规范的唯一来源；不得在本文件尾部追加重复实现细节。

### 4.2 Artifact 根目录

```text
.paper-artifacts/ssw-cuda-v1/
  phase0/
  profiling/
  oracle/
  corpus/
  upstream/
  preselect/
  endpoint/
  forward_hybrid/
  reverse/
  traceback/
  full_backend/
  holdout/
  performance/
```

大 artifact git ignored；仓库提交 manifest、receipt、source data、SHA-256 和重建脚本。

### 4.3 每个 attempt 最小记录

```text
attempt_id
phase
backend
workload_id
query_source_ordinal
target_source_ordinal
query_sha256
target_sha256
pair_digest
command argv
environment digest
source commit
binary digest
GPU/CPU identity
start/end timestamps
return code
status
fallback reason
stdout/stderr paths
artifact manifest digest
```

### 4.4 GPU stage telemetry

```text
packing
H2D
prealign
selection
forward endpoint
reverse-start
traceback
D2H
downstream triplex
clustering/sort
I/O
total wall
peak host/device memory
CPU SSW call counters
```

计时必须可加和；无法归属的 overhead 单列，不得塞进最快阶段。

---

# Phase 0：导入当前证据、冻结新 epoch 和排除集合

## 目标

让状态机从实际 `9f87aac` 或更晚 checkout 出发，完整吸收 canonical-hybrid-v2 已完成证据，并建立所有未来 fresh holdout 的硬排除 registry。

## 必做任务

1. 记录实际 HEAD、分支、远端、领先/落后、工作区。
2. 从 `9f87aac` 到实际 HEAD 有变化时，记录 commit 清单；不得回退。
3. 验证本节 0.2 的 v2 数字能由 machine-readable evidence 重建。
4. 计算并冻结所有历史 evidence digest。
5. 创建：

   ```text
   paper/ssw_cuda/historical_evidence_inventory.tsv
   paper/ssw_cuda/historical_evidence_receipt.json
   ```

6. 建立 `used_input_exclusion_registry.tsv`。至少汇总：
   - 原 Phase 2 correctness holdout；
   - 原 Phase 3 v1 fixed pilot；
   - canonical-hybrid-v2 regression；
   - canonical-hybrid-v2 fresh holdout；
   - canonical-hybrid-v2 performance pilot；
   - 所有开发、debug、replay、fuzz 和已查看 pair。
7. 每个排除项至少使用：

   ```text
   query_source_ordinal
   target_source_ordinal
   query_sha256
   target_sha256
   pair_digest
   source_receipt_path
   exclusion_reason
   ```

8. 决策文件只给摘要时，递归读取其引用的 manifest/receipt。任一引用无法解析则 `blocked`。
9. 冻结 CPU authority binary/source/toolchain/hardware。
10. 创建本轮 epoch：

   ```text
   ssw_cpu_oracle_epoch = 2
   ssw_cuda_program_epoch = 1
   ```

11. 创建独立规范文件骨架，不覆盖现有目标文件。
12. 运行旧检查：至少 Phase 2、Phase 3 pilot、canonical-hybrid-v2 aggregate checks。

## 交付物

```text
paper/ssw_cuda/STATUS.md
paper/ssw_cuda/PROGRAM_STATE.json
paper/ssw_cuda/historical_evidence_inventory.tsv
paper/ssw_cuda/historical_evidence_receipt.json
paper/ssw_cuda/used_input_exclusion_registry.tsv
paper/ssw_cuda/used_input_exclusion_registry.sha256
paper/ssw_cuda/runtime_epochs.json
paper/ssw_cuda/source_inventory.tsv
paper/ssw_cuda/license_inventory.tsv
paper/ssw_cuda/claim_ledger.tsv
docs/ssw_cuda/*.md skeletons
scripts/check_ssw_cuda_phase0.sh
```

## 硬 gate

- v2 结论和数字全部重建一致。
- 所有相关 selection receipts 已解析到 source ordinal + digest；重叠 registry 可机器查询。
- 历史 evidence digest 未被修改。
- 当前 authority 可构建，旧 checks 通过；环境不足则 `blocked`。
- `goal.md` 未被覆盖。

## 状态转换

```text
pass    -> active_phase = 1
blocked -> 保持 phase 0
```

## Commit

```text
docs: import completed hybrid-v2 evidence and freeze SSW-CUDA epoch
```

---

# Phase 1：CPU authority profiling、Amdahl 上限与早期 futility gate

## 目标

在任何大规模 CUDA 实现之前，测量 CPU authority 中 SSW 可加速部分占比，判断端到端 10× 是否在理论上可达。

## 1.1 Profiling stages

使用 mutually exclusive timers，至少拆分：

```text
pre_align
selection
forward_alignment
reverse_alignment
banded_traceback
SSW bridge/orchestration directly replaced by new backend
downstream triplex conversion
stability/identity/Nt
clustering/ranking/sort
serialization/I/O
wrapper/other
```

定义：

```text
p_strict_ssw =
  (pre_align + selection + forward + reverse + traceback) / total

p_backend_addressable =
  (strict SSW + only the bridge/orchestration explicitly replaced) / total
```

不得把 unchanged downstream 计入 p。

## 1.2 Profiling panel

运行前冻结一个只含 regression/development 数据的 panel，不消耗 fresh holdout：

- 小型 overhead case；
- 中等 workload；
- H19 chr21；
- H19 chr22；
- 至少一个 application-like、但已在排除 registry 中的现实 workload；
- 至少 5 次 CPU authority observation/主 workload；
- cold 与 steady-state 分开。

## 1.3 Amdahl 计算

对每个 workload 计算：

```text
maximum_speedup_infinite = 1 / (1 - p_backend_addressable)
```

若目标总加速为 `T = 10` 且 `p > 0.9`，计算所需 backend stage speedup：

```text
required_backend_speedup = p / (1/T - (1-p))
```

必须给出 observation、median、IQR 和 bootstrap CI。不得只给平均值。

## 1.4 B3 理论 gate

```text
若 claim-relevant 大 workload 的 conservative p <= 0.90：
    bioinformatics_b3_track = closed_amdahl
    理由：有限 backend speedup 无法达到端到端 10×

若 10 < maximum_speedup_infinite < 12：
    bioinformatics_b3_track = open_low_headroom
    允许继续工程，但在 Phase 7 前不得启动昂贵优化

若 maximum_speedup_infinite >= 12：
    bioinformatics_b3_track = open_amdahl
```

`p = 0.90` 时 10×只在 backend 成本趋近零的极限达到，实际按不可达处理。

无论 B3 是否关闭：

```text
engineering_track = active
```

除非 profiling 显示 SSW 部分极小到本项目无方法价值，才可由预注册决策关闭整个工程路线。

## 1.5 计时一致性

所有 stage 总和与 outer wall time 差异必须：

```text
<= 2% 或明确归入 wrapper/other
```

instrumentation on/off 的 authority output digest 必须一致；性能 overhead 必须单独量化。

## 交付物

```text
paper/ssw_cuda/cpu_profile_protocol.md
paper/ssw_cuda/cpu_profile_attempt_plan.tsv
paper/ssw_cuda/cpu_profile_source_data.tsv
paper/ssw_cuda/cpu_profile_statistics.json
paper/ssw_cuda/amdahl_decision.json
paper/ssw_cuda/amdahl_decision.md
reproduce/ssw_cuda/run_cpu_profile.py
scripts/check_ssw_cuda_phase1.sh
```

## 硬 gate

- 分解覆盖完整 wall time。
- p 与 Amdahl 数字可从 source data 重建。
- B3 track 状态明确，不降低 10×标准。
- profiling 不使用 fresh holdout。
- authority 输出不变。

## 状态转换

```text
pass -> active_phase = 2
blocked -> 保持 phase 1
```

B3 `closed_amdahl` 不阻止进入 Phase 2，但最终稿件不得再宣称 widening 路线开放。

## Commit

```text
perf: profile CPU SSW authority and freeze Amdahl futility gate
```

---

# Phase 2：冻结 CPU 可观察语义与零行为差异 instrumentation

## 目标

把 L0–L6 变成字段级 oracle；增加默认关闭 trace，不改变 authority 行为。

## 必做任务

1. 从实际 source 写入：

   ```text
   docs/ssw_cuda/DP_CONTRACT.md
   docs/ssw_cuda/ENDPOINT_CONTRACT.md
   docs/ssw_cuda/CIGAR_CONTRACT.md
   docs/ssw_cuda/TELEMETRY_SPEC.md
   ```

2. 明确：
   - recurrence 和 gap penalty 语义；
   - byte-first/word-recompute final semantics；
   - per-column maximum；
   - threshold/best/last selection；
   - forward endpoint scan/tie-breaking；
   - reverse-start scan/tie-breaking；
   - band initial width、扩展、停止；
   - H/E/F/diagonal tie rules；
   - traceback stop 和 CIGAR merge。
3. 增加 opt-in trace：

   ```text
   FASIM_SSW_ORACLE_TRACE=1
   FASIM_SSW_ORACLE_TRACE_DIR=...
   FASIM_SSW_ORACLE_TRACE_FILTER=...
   FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS=0|1
   ```

4. 默认关闭时不创建文件、不改 stdout/stderr、不改 digest。
5. trace 至少输出 L0–L6、attempt key、selection reason、byte/word、band history。
6. 建立 tiny scalar reference 仅用于诊断，不替代 oracle。
7. 对 hq10/hq11 建立逐 call regression trace。
8. instrumentation on/off 至少 5 次输出 digest 一致。

## 交付物

```text
docs/ssw_cuda/DP_CONTRACT.md
docs/ssw_cuda/ENDPOINT_CONTRACT.md
docs/ssw_cuda/CIGAR_CONTRACT.md
docs/ssw_cuda/TELEMETRY_SPEC.md
schemas/ssw_oracle_call.schema.json
fasim/ssw_oracle_trace.*
tests/ssw_cuda/fixtures/hq10_*.json
tests/ssw_cuda/fixtures/hq11_*.json
paper/ssw_cuda/cpu_oracle_binary_receipt.json
scripts/check_ssw_cuda_phase2.sh
```

## 硬 gate

- instrumentation off/on authority outputs byte-identical。
- hq10/hq11 定位到稳定 call/attempt key。
- endpoint/CIGAR tie rules 不是“与 SSW 相同”的空描述。
- schema/tests 全通过。

## Commit

```text
repro: freeze observable modified-SSW oracle semantics
```

---

# Phase 3：differential corpus、比较器与 fresh-holdout policy

## 目标

在写 CUDA kernel 前冻结 regression/fuzz corpus、L0–L8 比较器和不可绕过的 holdout 排除规则。

## 3.1 Corpus

### 历史 regression

- Phase 2 24 workloads / 36 formal attempts；
- hq10/hq11；
- full-output diagnostic difference；
- H19 core；
- canonical-hybrid-v2 regression/holdout/performance inputs全部作为 regression；
- 所有旧 pilot/replay/debug。

### Tiny exhaustive/semiexhaustive

运行前冻结确切 alphabet、长度、组合数量和裁剪规则。覆盖 multiple equal optimum、zero、single match、all mismatch。

### Adversarial

```text
homopolymer
periodic repeats
palindrome/reverse complement
equal forward endpoints
equal reverse starts
equal gap placements
open/extend tie
E/F tie
diagonal/gap tie
byte boundary 253/254/255/256
length boundaries 31/32/33 ... 2811/2812
unsupported alphabet/input fail-closed
```

### Deterministic fuzz

冻结生成器版本、seed、数量、长度/GC/repeat 分布。compact corpus进入常规测试，large corpus进入昂贵 gate。

## 3.2 比较器

逐 attempt 输出：

```text
L0_input_equal
L1_column_equal + first_diff_column
L2_selection_equal + false_negative/extra/order
L3_forward_equal
L4_reverse_equal
L5_cigar_equal + first_diff_op
L6_row_equal
L7_score/stability/Nt_top5_equal
L8_full_output_diagnostic_equal
first_divergent_layer
```

## 3.3 Fresh holdout policy

写入 `docs/ssw_cuda/HOLDOUT_POLICY.md`：

1. 最终 holdout 只能在 full-GPU implementation commit 冻结后选择。
2. selection 必须先加载 `used_input_exclusion_registry.tsv`。
3. query 或 target 任一满足以下任一条件即排除：

   ```text
   source_ordinal overlap
   sequence digest overlap
   pair digest overlap
   referenced by any prior correctness/performance/pilot receipt
   used for debug/minimization/fuzz replay
   ```

4. checker 对任一重叠硬失败；不能靠人工豁免。
5. fresh holdout stratification 只使用运行前静态 metadata：长度、来源、GC、repeat proxy、静态最大评分上界、digest/hash。
6. 不要求 fresh holdout 运行后必须触发 byte/word path。实际覆盖只报告，不补样。
7. byte/word 强制覆盖放在 regression/adversarial corpus。
8. L8 始终 diagnostic。

## 交付物

```text
docs/ssw_cuda/HOLDOUT_POLICY.md
paper/ssw_cuda/corpus_manifest.tsv
paper/ssw_cuda/corpus_manifest.sha256
paper/ssw_cuda/corpus_receipt.json
reproduce/ssw_cuda/build_corpus.py
reproduce/ssw_cuda/compare_layers.py
tests/ssw_cuda/test_layered_comparator.py
scripts/check_ssw_cuda_phase3.sh
```

## 硬 gate

- corpus 在 CUDA 实现前冻结。
- exclusion registry 可重建，所有旧 receipts 已吸收。
- 比较器能正确分类已知 hq10/hq11。
- holdout checker 对 synthetic overlap fixture 硬失败。
- L8 被锁定 diagnostic。

## Commit

```text
test: freeze exact SSW-CUDA differential corpus and holdout policy
```

---

# Phase 4：Accelign/G3SA bounded spike 与架构选择

## 目标

只验证可复用的 GPU 设计，不让第三方语义取代 CPU oracle。

## Accelign spike

- pin exact commit/license/toolchain；
- 运行 local affine score/start/end 示例；
- 比较 API、batching、length binning、wavefront、int precision；
- 记录与 L1 per-column vector、L2 selection、L3 endpoint 的语义缺口；
- 不直接假设其 endpoint 等于 CPU SSW。

## G3SA spike

- pin exact commit/license/toolchain；
- 优先分析 checkpoint/recompute traceback、block boundary storage、CIGAR generation；
- 默认不复制 KSW/minimap2 tie semantics；
- GPL 兼容性未完成时只引用论文/结构。

## Architecture decision

必须在最多三个候选中选择：

```text
A. in-tree dense/reference kernels
B. Accelign-style forward + in-tree SSW semantics
C. mixed design with in-tree checkpoint/recompute traceback
```

决策要明确：L1/L2/L3/L4/L5 哪些完全自研，哪些只借鉴调度。

## 预算

```text
repair/architecture candidates <= 3
GPU time <= 8 hours
wall-clock external build attempts <= 3 per upstream
```

## 交付物

```text
paper/ssw_cuda/upstream_snapshot.tsv
paper/ssw_cuda/upstream_build_receipt.json
paper/ssw_cuda/upstream_semantic_diff.tsv
paper/ssw_cuda/architecture_decision.md
scripts/check_ssw_cuda_phase4.sh
```

## 状态转换

```text
pass    -> active_phase = 5
no_go   -> 选择 in-tree reference design 后仍可 pass；若无可执行设计则 engineering no_go
blocked -> 缺环境但 in-tree 可执行时不阻塞；否则 blocked
```

## Commit

```text
research: select bounded exact SSW-CUDA architecture
```

---

# Phase 5：GPU per-column maxima 与 exact selection（L1/L2）

## 目标

在 GPU 上精确复现 CPU `ssw_pre_align()` final per-column vector，并生成完全相同的 stable retained attempt descriptors。

## 实现

1. `int32` reference kernel；local zero floor、affine E/F、确定性列最大。
2. test/debug path 可导出完整 vector；生产 path 可 GPU-side compact。
3. CPU byte-first/word-recompute 只要求 final observable vector 一致。
4. exact predicates：threshold/best/last、dedup、order、selection reason。
5. stable compaction：flag -> scan -> stable scatter -> deterministic validation。
6. default backend 仍 CPU；无 CUDA stub/fail-closed。

## Correctness 顺序

```text
tiny exhaustive
adversarial byte/word boundaries
compact fuzz
known hq10/hq11 calls
full frozen regression
large fuzz
```

## 预算与停止

```text
mechanism-level repair iterations <= 3
GPU budget <= 24 hours
```

超过预算或三次普适修复后仍有 L1/L2 diff：

```text
phase_5_status = no_go
engineering_track = closed_preselect
不得进入 Phase 6
```

## 交付物

```text
fasim/ssw_cuda/ssw_cuda_api.h
fasim/ssw_cuda/ssw_cuda_pre_align.cu
fasim/ssw_cuda/ssw_cuda_select.cu
fasim/ssw_cuda/ssw_cuda_stub.cpp
paper/ssw_cuda/preselect_design.md
paper/ssw_cuda/preselect_regression.tsv
paper/ssw_cuda/preselect_receipt.json
tests/ssw_cuda/test_preselect.py
scripts/check_ssw_cuda_phase5.sh
```

## 硬 gate

- L1/L2 entire frozen corpus zero mismatch。
- selected false negative = 0；extra/order/reason mismatch = 0。
- 10-repeat digest stable；同型号双 GPU可用时一致。
- unsupported/OOM/capacity fail closed。
- default-off authority不变。

## Commit

```text
feat: add exact GPU modified-SSW prealign and selection
```

---

# Phase 6：GPU forward endpoint（L3）

## 目标

补齐原目标缺失的 GPU forward implementation。GPU 必须实际输出 CPU-compatible forward score/endpoints，而不是把 CPU endpoint 当成 Phase 5 已提供。

## 6.1 Observable outputs

根据 Phase 2 spec，实现并比较：

```text
score1
ref_end1
read_end1
score2/ref_end2 if observable
byte/word final semantics
endpoint ordered key
```

## 6.2 实现顺序

1. CPU L1 vector + GPU endpoint reducer，先验证 tie key；
2. GPU L1 vector + GPU endpoint reducer；
3. batch/grid 合并；
4. selected attempts 上的 full forward alignment output；
5. deterministic multi-run/multi-device。

GPU reduction必须显式组合完整 key，不能只 `atomicMax(score)`。

## 6.3 hq11 与 adversarial

- hq11 forward endpoint 逐字段 exact；
- equal score ref columns；
- equal read coordinates within selected column；
- repeat/homopolymer；
- byte/word boundary；
- lengths at tile/block boundaries。

## 预算与停止

```text
mechanism-level repair iterations <= 3
GPU budget <= 24 hours
```

三次后 L3 仍不 exact：

```text
phase_6_status = no_go
engineering_track = exact_forward_no_go
保留 Phase 5 研究结果
不得进入 Phase 8 reverse-start
```

## 交付物

```text
fasim/ssw_cuda/ssw_cuda_forward.cu
paper/ssw_cuda/forward_endpoint_design.md
paper/ssw_cuda/forward_endpoint_regression.tsv
paper/ssw_cuda/forward_endpoint_receipt.json
tests/ssw_cuda/test_forward_endpoint.py
scripts/check_ssw_cuda_phase6.sh
```

## 硬 gate

- L3 entire frozen corpus zero mismatch。
- hq11 forward fields exact。
- CPU-vector/GPU-reducer 与 full-GPU forward 两种模式结果相同。
- 10-repeat deterministic；supported path无CPU endpoint调用。

## Commit

```text
feat: add CPU-compatible GPU SSW forward endpoints
```

---

# Phase 7：new forward-hybrid checkpoint 与早期性能止损

## 目标

组合 GPU L1–L3 与 CPU L4/L5，验证新 forward backend 相对已关闭 H2 是否有正确性和性能改善；不消耗 fresh holdout，不重开 H2 promotion。

## Arms

```text
A  = CPU authority
H2 = historical canonical-hybrid-v2
F  = GPU exact L1/L2/L3 + selected CPU reverse-start/banded traceback
```

F 不得执行完整 CPU pre-align/selection/forward；只允许 selected attempts 的 CPU L4/L5。

## Correctness

在 frozen regression 上：

```text
L1-L7 zero mismatch
L2 false negative = 0
hq10/hq11 exact
L8 diagnostic reported
CPU call counters prove only L4/L5 remain
```

## 独立执行与离线比较

1. A/H2/F 各自独立进程、独立 artifact root、独立命令。
2. F 不得读取 A/H2 output、digest 或 comparator result。
3. balanced order 只控制执行次序：AF/FA、H2F/FH2 等由 attempt plan 预先冻结。
4. 所有 arms 完成后，另起 offline comparison job。
5. 任何 arm 运行时 comparator fallback 都是硬失败。

## Fixed development pilot

使用已在排除 registry 的 development workloads：

- micro overhead；
- medium；
- H19 chr21/chr22；
- selected-attempt density strata；
- 每个主 workload至少 5 observations。

## 早期性能模型

结合 Phase 1 p，测量：

```text
F end-to-end
GPU L1-L3
authority L4/L5 remaining cost
selected ratio
projected G cost lower/upper bound
```

不得把 projection 当正式 speedup。

## Futility gate

允许结论：

```text
forward_hybrid_checkpoint_pass_continue_full_gpu
forward_hybrid_correct_but_b3_track_closed
forward_hybrid_performance_futility_stop
blocked_by_environment
```

规则：

- F correctness 不通过：phase no_go，停止。
- F correct 且 Phase 1 已 `closed_amdahl`：可继续方法路线，但 B3保持关闭。
- F correct、B3开放，但基于实测 lower/upper bound 即使 L4/L5 成本降为零仍无法达到10×：`forward_hybrid_performance_futility_stop`，关闭 B3；owner未另立方法路线时停止昂贵 full GPU。
- pilot 不能修改 10×标准、输入或合同。

## 预算

```text
runner/measurement repair <= 2
GPU budget <= 12 hours
```

## 交付物

```text
paper/ssw_cuda/forward_hybrid_protocol.md
paper/ssw_cuda/forward_hybrid_attempt_plan.tsv
paper/ssw_cuda/forward_hybrid_source_data.tsv
paper/ssw_cuda/forward_hybrid_decision.json
paper/ssw_cuda/forward_hybrid_projection.json
reproduce/ssw_cuda/run_forward_hybrid.py
scripts/check_ssw_cuda_phase7.sh
```

## Commit

```text
bench: validate exact forward hybrid and freeze full-GPU futility decision
```

---

# Phase 8：GPU reverse-start（L4）

## 目标

在已 exact 的 GPU forward endpoint 上复现 CPU reverse alignment begin。

## 实现阶梯

```text
R8A: CPU forward endpoint -> GPU reverse-start
R8B: GPU forward endpoint -> GPU reverse-start
```

两种模式都使用 CPU banded traceback，以隔离 L4。

## 要求

- CPU source/spec 定义 reverse prefixes、orientation、scan、first-hit/tie key；
- integer deterministic reduction；
- hq11 begin/end exact；
- equal reverse endpoints/adversarial；
- L4 full corpus zero mismatch；
- R8B supported path不调用 CPU reverse；
- L5–L7 由 CPU traceback保持 exact。

## 预算与状态转换

```text
repair iterations <= 3
GPU budget <= 24 hours
```

```text
pass    -> active_phase = 9
no_go   -> full_gpu_track = closed_reverse; retain F; active_phase = 13
blocked -> 保持 phase 8
```

不得在同一 corpus 上放宽 begin equality。

## 交付物

```text
fasim/ssw_cuda/ssw_cuda_reverse.cu
paper/ssw_cuda/reverse_design.md
paper/ssw_cuda/reverse_regression.tsv
paper/ssw_cuda/reverse_receipt.json
tests/ssw_cuda/test_reverse_start.py
scripts/check_ssw_cuda_phase8.sh
```

## Commit

```text
feat: add CPU-compatible GPU SSW reverse-start
```

---

# Phase 9：GPU banded traceback 与 canonical CIGAR（L5/L6）

## 目标

复现 CPU `banded_sw()` 的 band、方向、traceback、CIGAR 和 emitted row。

## 实现阶梯

### T9A reference dense

以 CPU score/begin/end 为输入：

```text
initial band
H/E/F DP
band expansion
exact tie rules
traceback
packed CIGAR
```

### T9B checkpoint/recompute

只有 T9A全 pass 后，才实现 G3SA-style storage/recompute；只借鉴内存结构，不复制 tie semantics。

### T9C full GPU endpoints

GPU L1–L4 + GPU L5，形成 G 的 alignment core。

## 独立 replay validator

从 sequence、begin、CIGAR、scoring重算：end、score、matches、gaps、aligned strings。不得调用被测 GPU 辅助函数。

## 要求

- hq10 gap placement、CIGAR、MeanStability、row exact；
- first divergent cell debug；
- capacity/overflow/OOM不truncate；
- band history exact，除非预注册允许内部不同但可观察/失败语义相同；默认 exact；
- L5/L6 full corpus zero mismatch；
- L7 full regression zero mismatch。

## 预算与状态转换

```text
repair iterations <= 3
GPU budget <= 36 hours
```

```text
pass    -> active_phase = 10
no_go   -> full_gpu_track = closed_traceback; retain F/R; active_phase = 13
blocked -> 保持 phase 9
```

优化 T9B失败可保留 T9A；若 T9A内存/性能不可用于 declared envelope，记录 performance no_go。

## 交付物

```text
fasim/ssw_cuda/ssw_cuda_traceback.cu
fasim/ssw_cuda/ssw_cuda_cigar.cuh
paper/ssw_cuda/traceback_design.md
paper/ssw_cuda/traceback_tie_rules.tsv
paper/ssw_cuda/traceback_regression.tsv
paper/ssw_cuda/traceback_receipt.json
tests/ssw_cuda/test_banded_traceback.py
scripts/check_ssw_cuda_phase9.sh
```

## Commits

```text
feat: add reference CPU-compatible GPU SSW traceback
perf: add bounded checkpoint-recompute GPU traceback
```

---

# Phase 10：full-GPU backend 集成与 regression

## 目标

组合 GPU L1–L5，并保持 unchanged LongTarget downstream，使支持范围内不调用 CPU SSW。

## Backend

```text
G = GPU per-column maxima
  + exact selection
  + exact forward endpoint
  + exact reverse-start
  + exact banded traceback/CIGAR
  + unchanged triplex/stability/clustering
```

## CPU call proof

```text
cpu_ssw_pre_align_calls
cpu_ssw_forward_calls
cpu_ssw_reverse_calls
cpu_banded_sw_calls
cpu_fallback_calls
```

supported G fast path 前四项必须为 0。fallback有明确原因和最终 backend。

## Supported envelope

冻结：GPU arch、CUDA/driver、length、alphabet、scoring matrix/type、gap、mask/filter/flag、batch/temp memory、CIGAR capacity。

## Regression

```text
L1-L7 zero mismatch
L2 false negative = 0
supported CPU SSW calls = 0
unexpected fallback = 0
technical failure = 0
10-repeat deterministic
L8 diagnostic only
```

## Feature flags

```text
FASIM_SSW_BACKEND=cpu
FASIM_SSW_BACKEND=cuda-forward-hybrid
FASIM_SSW_BACKEND=cuda-reverse-hybrid
FASIM_SSW_BACKEND=cuda-full-experimental
```

promotion前 default仍 CPU。

## 预算与状态转换

```text
integration repair iterations <= 3
GPU budget <= 24 hours
```

```text
pass    -> freeze implementation commit; active_phase = 11
no_go   -> full_gpu_track = closed_integration; active_phase = 13
blocked -> 保持 phase 10
```

## 交付物

```text
fasim/ssw_cuda/ssw_cuda_runtime.cu
fasim/ssw_cuda/ssw_cuda_backend.cpp
paper/ssw_cuda/full_backend_envelope.md
paper/ssw_cuda/full_backend_regression.tsv
paper/ssw_cuda/full_backend_receipt.json
schemas/ssw_cuda_run_report.schema.json
tests/ssw_cuda/test_full_backend.py
scripts/check_ssw_cuda_phase10.sh
```

## Commit

```text
feat: integrate exact full-GPU modified-SSW backend
```

---

# Phase 11：全新独立 holdout、确定性与 promotion

## 目标

在 full-GPU implementation commit 冻结后，从未运行输入中选择一个真正独立的 holdout，promotion L1–L7。L8仍 diagnostic。

## 11.1 Freeze 前置条件

- Phase 10 commit 已提交；工作树 clean；
- config、binary、compiler、GPU arch、batch、stream已冻结；
- `used_input_exclusion_registry.tsv`已更新包含 Phase 4–10所有运行/debug输入；
- selection script和overlap checker先提交。

## 11.2 Static selection

最低 72 workloads；三 query-length strata各24；target来源尽可能平衡；16个进入三次重复。

只允许静态字段：

```text
query_source_ordinal
target_source_ordinal
query/ref lengths
GC/repeat proxy
static maximum-score upper bound
source metadata
SHA/hash ordering
```

禁止运行后补 byte/word case。实际 CPU byte/word coverage仅报告。

## 11.3 硬排除

对以下任一重叠 hard fail：

```text
query source_ordinal
query digest
target source_ordinal
target digest
pair digest
any prior correctness/performance/pilot/debug receipt
```

必须直接读取 Phase 0 registry和所有新增 receipts；不能只检查 pair ID。

## 11.4 Promotion gate

```text
L1-L6 zero mismatch
score/stability/Nt clustered Top5 zero mismatch
selected false negative = 0
supported-path CPU SSW calls = 0
unexpected fallback = 0
technical failure = 0
repeat instability = 0
L8 diagnostic report complete
```

任一 L1–L7 mismatch使该 epoch不得 promotion。

## 11.5 Failure policy

- 失败 holdout立即转 regression；
- 默认只允许一个 `ssw_cuda_full_v2` mechanism-level rescue；
- rescue实现冻结后必须选全新 holdout；
- 第二次独立 failure后 full GPU `no_go`。

## 11.6 跨设备

- 两张同型号 GPU可用时，固定 subset逐字节一致；
- 第二架构 optional；无则 `not_available`，不影响主 GPU promotion。

## 预算

```text
primary + repeat GPU budget <= 24 hours
rescue GPU budget <= 16 hours
promotion attempts <= 2 epochs
```

## 交付物

```text
paper/ssw_cuda/full_holdout_protocol.md
paper/ssw_cuda/full_holdout_manifest.tsv
paper/ssw_cuda/full_holdout_manifest.sha256
paper/ssw_cuda/full_holdout_attempt_plan.tsv
paper/ssw_cuda/full_holdout_results.tsv
paper/ssw_cuda/full_holdout_receipt.json
paper/ssw_cuda/full_holdout_decision.json
paper/ssw_cuda/cross_device_results.tsv
reproduce/ssw_cuda/select_full_holdout.py
reproduce/ssw_cuda/run_full_holdout.py
scripts/check_ssw_cuda_phase11.sh
```

## 状态转换

```text
pass    -> full_cuda_contract_promoted; active_phase = 12
no_go   -> full_cuda_contract_not_promoted; active_phase = 13
blocked -> 保持 phase 11
```

## Commits

```text
repro: freeze independent exact SSW-CUDA holdout
analysis: validate exact SSW-CUDA contract on fresh holdout
```

---

# Phase 12：正式性能、真实应用、CLI 与 release candidate

## 目标

只对已 promotion 的 G 测量端到端 safe 性能，决定 B3 和投稿路线。

## 12.1 Arms 与执行解耦

```text
A = CPU authority
G = promoted full-GPU backend
H2 = historical baseline only, not a safe performance contender
F/R = ablation only, if needed
```

正式 A/G：

1. attempt plan预先生成 balanced AG/GA order；
2. A/G独立进程、独立 artifact roots；
3. G运行时不能读取A输出、digest或comparison；
4. A运行时不能读取G输出；
5. 所有 arms 完成后再离线 compare；
6. comparison failure不触发重跑替换。

## 12.2 Performance panel

- micro overhead（不进主 claim）；
- H19 chr21/chr22；
- query length strata；
- selected-density strata；
- preregistered real application pilot；
- 只有 fixed pilot和Amdahl gate均非 futility，才启动50×668 formal application。

每个主 workload至少5 paired observations。正式配置最多3个，必须在 development set选定；holdout不用于调优。

## 12.3 必报

```text
end-to-end wall
median/IQR/bootstrap CI
GPU stage breakdown
packing/H2D/D2H
selected ratio
memory
CPU SSW call counters
fallback/technical failures
L1-L8 results
cold vs steady-state
```

## 12.4 B3 gate

至少满足一项且 correctness仍严格：

```text
median paired safe speedup >= 10x
或同一观测任务 wall-time reduction >= 8 hours
或24-hour safe capacity >= 10x
```

建议内部稳定性标准：95% CI下界超过10×；若只达到点估计，必须按预注册统计规则决定，不能临时包装。

若 Phase 1 已 `closed_amdahl`，Phase 12不得重新开启 B3，除非本轮正式实现明确扩大了 addressable scope并在新的预注册 profiling中重算；不得事后把 downstream 算入p。

## 12.5 CLI

promotion后：

```text
safe:
  supported -> G
  unsupported/technical failure -> CPU authority fail-closed with report
verified:
  optional diagnostic dual-run, not speed claim
fast-experimental:
  unpromoted backends only
cpu-authority:
  A
```

run report记录 backend、contract、promotion evidence、fallback、CPU calls、stage timings、publication source。

## 12.6 Release candidate

build docs、CUDA matrix、smoke data、container/Apptainer或可重建环境、CPU/stub CI、GPU receipt、license inventory、changelog、CITATION/Zenodo metadata draft、archive manifest。

## 预算和停止

```text
formal benchmark GPU budget <= 36 hours
formal application GPU budget <= 24 hours
config count <= 3
no replacement retries
```

## 交付物

```text
docs/ssw_cuda/PERFORMANCE_PROTOCOL.md
paper/ssw_cuda/performance_attempt_plan.tsv
paper/ssw_cuda/performance_source_data.tsv
paper/ssw_cuda/performance_statistics.json
paper/ssw_cuda/performance_decision.json
paper/ssw_cuda/b3_v3_decision.json
paper/ssw_cuda/figures/
paper/ssw_cuda/tables/
docs/ssw_cuda_backend.md
examples/ssw_cuda/
container/ or equivalent
paper/ssw_cuda/release_candidate_receipt.json
scripts/check_ssw_cuda_phase12.sh
```

## 状态转换

```text
correctness promoted + B3 pass -> bioinformatics_b3_track = pass
correctness promoted + B3 fail -> bioinformatics_b3_track = closed_performance
operational failure            -> blocked or performance_no_go per protocol
active_phase = 13
```

## Commits

```text
bench: characterize promoted exact SSW-CUDA backend
feat: integrate promoted exact SSW-CUDA safe execution
repro: assemble exact SSW-CUDA release candidate
```

---

# Phase 13：最终审计、唯一结论与投稿路线

## 目标

核对历史与新证据并存、合同/数字/source data一致，输出唯一 final decision。

## Aggregate checker

```text
make check-ssw-cuda
```

必须核对：

- Phase 0–12状态；
- historical H2 no-go未被改写；
- Amdahl gate；
- CPU oracle未漂移；
- all manifests/SHA；
- used-input exclusion和fresh holdout零重叠；
- L1–L7；
- L8 diagnostic-only措辞；
- CPU SSW counters；
- fallback/failure inventory；
- independent arm execution；
- performance statistics和B3；
- license/release reproducibility；
- clean working tree和final commit。

## 唯一允许的 final decisions

```text
ssw_cuda_full_ready_b3_pass
ssw_cuda_full_ready_b3_no_go
ssw_cuda_full_correctness_not_promoted
ssw_cuda_forward_or_reverse_checkpoint_only
ssw_cuda_research_no_go
ssw_cuda_blocked_by_environment
```

### `ssw_cuda_full_ready_b3_pass`

- G fresh holdout L1–L7 zero mismatch；
- safe end-to-end B3通过；
- Bioinformatics Applications Note路线可重新开启。

### `ssw_cuda_full_ready_b3_no_go`

- correctness promotion成功；
- B3因Amdahl或正式性能失败；
- 适合CSBJ/BMC Bioinformatics/HPC/方法论文，不宣称significantly widens application。

### 其余

- 不发布GPU-only safe claim；
- 保留CPU或历史verified路径；
- 负结果和机制证据完整交接。

## 禁用措辞

除非证据明确支持，不得出现：

```text
all SSW alignments identical
general GPU replacement
all lncRNAs
full-output exact replacement
38x safe speedup
zero mismatch（无合同/holdout范围）
Bioinformatics-ready（B3关闭时）
```

L8永远不能写成full-output replacement。

## 最终交付物

```text
paper/ssw_cuda/FINAL_STATUS.md
paper/ssw_cuda/final_decision.json
paper/ssw_cuda/claim_to_evidence.tsv
paper/ssw_cuda/limitations.md
paper/ssw_cuda/release_checklist.md
paper/ssw_cuda/manuscript_handoff.md
paper/ssw_cuda/completion_audit.tsv
scripts/check_ssw_cuda_all.sh
```

## Commit

```text
docs: certify exact SSW-CUDA completion audit and publication route
```

---

## 5. Make target 与 checker 约定

建议新增：

```text
check-ssw-cuda-phase0
check-ssw-cuda-phase1
check-ssw-cuda-phase2
check-ssw-cuda-phase3
check-ssw-cuda-phase4
check-ssw-cuda-phase5
check-ssw-cuda-phase6
check-ssw-cuda-phase7
check-ssw-cuda-phase8
check-ssw-cuda-phase9
check-ssw-cuda-phase10
check-ssw-cuda-phase11
check-ssw-cuda-phase12
check-ssw-cuda-phase13
check-ssw-cuda
```

Checker必须：不自动联网、不自动跑未冻结昂贵实验、校验receipt/schema/SHA/state/claim、明确区分GPU不可用与receipt无效。

---

## 6. Commit 纪律

推荐顺序：

```text
docs: import completed hybrid-v2 evidence and freeze SSW-CUDA epoch
perf: profile CPU SSW authority and freeze Amdahl futility gate
repro: freeze observable modified-SSW oracle semantics
test: freeze exact SSW-CUDA differential corpus and holdout policy
research: select bounded exact SSW-CUDA architecture
feat: add exact GPU modified-SSW prealign and selection
feat: add CPU-compatible GPU SSW forward endpoints
bench: validate exact forward hybrid and freeze full-GPU futility decision
feat: add CPU-compatible GPU SSW reverse-start
feat: add reference CPU-compatible GPU SSW traceback
perf: add bounded checkpoint-recompute GPU traceback
feat: integrate exact full-GPU modified-SSW backend
repro: freeze independent exact SSW-CUDA holdout
analysis: validate exact SSW-CUDA contract on fresh holdout
bench: characterize promoted exact SSW-CUDA backend
feat: integrate promoted exact SSW-CUDA safe execution
repro: assemble exact SSW-CUDA release candidate
docs: certify exact SSW-CUDA completion audit and publication route
```

每笔commit message必须匹配真实内容；未运行不能写validate/complete。

---

## 7. 立即开始的动作

Codex收到本文件后：

1. 不修改未跟踪的旧 `goal-ssw.md`内容前，先将本修订版保存并计算SHA。
2. 核对实际HEAD；记录从`9f87aac`到实际HEAD的commit。
3. 更新状态：`phase_0_status=in_progress`。
4. 读取三份canonical-hybrid-v2 decision及其全部引用receipts。
5. 重建36/36、35/36、60/60、18/18、0.257592×、3.882109×和B3 no_go。
6. 建立used-input exclusion registry，按source ordinal和digest去重。
7. 运行旧checks和新的Phase 0 checker。
8. Phase 0 pass后提交：

   ```text
   docs: import completed hybrid-v2 evidence and freeze SSW-CUDA epoch
   ```

9. 立即进入Phase 1 CPU profiling/Amdahl gate。
10. **Phase 1完成前不得实现新的CUDA DP kernel。**

---

## 8. Codex 每次汇报格式

```text
Phase:
Status: pass | no_go | blocked
HEAD:
Commits:
Files changed:
Commands executed:
Tests passed/failed:
GPU hours used / phase budget:
Repair iterations used / phase limit:
Scientific/engineering decision:
Bioinformatics B3 track status:
Known mismatches/fallbacks/failures:
Artifacts and line references:
Next active phase:
Working tree clean: yes/no
Ahead/behind remote:
```

不得只写“基本完成”“大致相同”“性能很好”。所有判断必须指向 machine-readable evidence。
