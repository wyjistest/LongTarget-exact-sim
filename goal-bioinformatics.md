# GASAL2-LongTarget Bioinformatics Applications Note 投稿强化执行目标

> 用途：将本文件放到 `wyjistest/LongTarget-exact-sim` 仓库根目录，作为新一轮本地 Codex 的唯一执行入口，替换已完成的旧 `goal.md`，但保留 `goal-final.md` 作为历史 paper-evidence 状态机。
>
> 当前仓库起点：分支 `gasal2-kcnq1ot1-focused-review` 在 2026-07-16 的已知完成 commit 为 `a98d80d44d4418cdb8a67dc8d83ee41b8e599023`，其 paper runtime authority 为 `0d11aa2d61b7ccda59b462ab8e0750dad17ee18f`，数据冻结为 `paper-data-v1-dccfd49-20260716`。执行前必须核对实际 HEAD，不得假设仓库仍停留在该 commit。
>
> 已完成状态：`paper_preparation_ready_with_declared_limitations`。本轮不是继续做普通论文证据整理，也不是重新打开长 query 架构探索；本轮目标是把现有研究包强化成更适合 **Bioinformatics Application Note** 的用户软件、真实应用、外部比较、发布候选和期刊稿件包。
>
> 期刊目标的当前约束基线（执行时必须再次核对 Bioinformatics 官方 Author Guidelines、Scope Guidelines 和 Submission Online 页面，并记录核对日期）：Application Note 通常不超过 4 页，约 2,600 词，或约 2,000 词加一幅主图；Availability and Implementation 必须明确；速度改进只有在能够证明显著扩大方法应用范围时才有说服力；新方法应在真实生物数据上与现有 state-of-the-art 方法比较。

---

## 0. Agent 总指令

从 `active_phase` 指向的 phase 开始。不要再生成一份新的总计划；直接实现、运行、验证、记录证据并更新本文件状态。一次只完成一个 phase，达到该 phase 的硬 gate 后再进入下一 phase。

### 0.1 必须遵守

1. 先读取当前 checkout、`git status`、`Makefile`、`README.md`、`goal-final.md`、`paper/PAPER_PREP_STATUS.md`、`paper/scope_and_claims.md`、`paper/results_claims.md`、`paper/limitations.md`、`paper/RELEASE_CHECKLIST.md`、现有 runner、comparator、manifest、source-data 和 check 脚本，再新增或修改文件。
2. 不要根据本文件中的推荐路径或 Make target 名称假设仓库未变化。先搜索现有实现；能复用就复用，不能复用时才新增。
3. 不得 reset、rebase、clean、覆盖或删除用户已有改动。只删除本 phase 自己创建且已确认不再需要的临时目录。
4. 不得自动 push、创建 GitHub release、上传 Zenodo、创建 DOI、签 tag、购买云资源、运行付费服务或提交稿件。上述动作必须保留给仓库 owner，除非用户另有明确授权。
5. 不得重新打开 persistent target、multi-segment microbatch、完整 KCNQ1OT1、完整 hg38、固定 traceback threshold、rank-unsafe pruning 或其它已经在 `goal.md` / `goal-final.md` 中关闭的长 query 主线。
6. 不得为了让图更好看或跨过某个 speedup 数字而继续调 stream、batch、threshold、worker density、GPU clocks、pruning 或运行时 preset。
7. 旧 paper runtime commit 和旧数据冻结必须保持可复现。除非本轮确实修改了 `fasim/`、CUDA、GASAL2 bridge、排序/聚类/输出合同或生产二进制行为，否则不得改变 `paper_runtime_epoch`，也不得重写旧 source data。
8. 用户界面 wrapper、输入校验、容器、文档和独立 orchestration 层可以形成新的 `submission_software_epoch`，但必须明确区分“历史 benchmark runtime”和“投稿软件 release candidate”。
9. 如果任何 C/C++/CUDA 或核心 Fasim 运行时发生变化：
   - 增加 `paper_runtime_epoch`；
   - 冻结新的 runtime commit；
   - 标记所有受影响的旧 benchmark 为历史证据；
   - 重新运行所有受影响的正确性和性能数据；
   - 不得把新 binary 与旧 benchmark 混在同一主张中。
10. 所有新 biological input、annotation、reference、known-pair label、外部工具、container base 和 dependency 必须记录来源、版本、license/redistribution note、下载命令、大小和 SHA-256。
11. 所有新实验必须先冻结 manifest 和 selection rule，再运行。不得运行后删除失败 query、mismatch、OOM、timeout、fallback 或表现不佳的工具。
12. 所有性能比较必须是同输入、同输出合同、同重复协议。不得把 fast top-K、完整 TFOsorted、外部工具原生输出或 verified 双跑模式直接当作同工作量 speedup。
13. 所有正确性仍需分别记录 score、stability、Nt 三种 clustered TFO1-TFO5。若主产品合同最终只承诺其中一种，另外两种仍须完整保留在 source data 和 Supplementary 中。
14. 不得把 `query_len <= 2812` 写成生物学上的“短 lncRNA”定义；只能写成当前实现和验证的工程边界。
15. 不得使用 query 名称、基因名、固定 SHA allowlist 或手工黑名单伪装成通用安全判定。任何安全 guard 必须来自输入/运行时可计算的机制条件，并在独立留出数据上验证。
16. 不得声称 biological superiority、novel biological discovery、genome-wide generality、full-output replacement、所有 lncRNA 均被加速或所有 rank 均严格等价，除非新增证据逐项支持。
17. 不得手工复制数字到图表、表格或摘要。所有数字必须从冻结的 machine-readable source data 生成，并有独立算术审计。
18. 每个 phase 形成一个可审查 diff；环境允许时一个 phase 一个 commit。若不能提交，记录建议 commit subject 和未提交 diff 清单。
19. 对耗时任务先做 plan-only、输入计数、资源估算和一个不进入主结果的 pilot。不得直接启动不可控的数小时或数天任务。
20. 遇到缺网络、缺 GPU、缺 license、缺 author metadata 或外部工具安装失败时，不得伪造成功。写入 gap register，并按本文件定义选择 `blocked`、`not_available` 或最终 no-go。

### 0.2 状态值

只允许：

```text
pending
in_progress
pass
no_go
blocked
not_available
```

含义：

- `pass`：实现、运行、证据和所有硬 gate 完成。
- `no_go`：实验完整执行，但预注册 promotion 条件不成立；负结果已保留，phase 科学上完成。
- `blocked`：缺输入、权限、依赖、网络、硬件或不可恢复 artifact，尚未完成。
- `not_available`：仅允许用于明确标为 optional 的 Phase 6 第二 GPU；不会单独阻止最终 Bioinformatics 决策，但必须保留 limitation。

---

## 1. 执行状态

Codex 每完成一个 phase 后更新此块。不得提前标记后续 phase。

```text
historical_paper_branch = gasal2-kcnq1ot1-focused-review
historical_paper_completion_commit = a98d80d44d4418cdb8a67dc8d83ee41b8e599023
historical_paper_runtime_epoch = 0
historical_paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
historical_paper_data_freeze = paper-data-v1-dccfd49-20260716

submission_software_epoch = 1
submission_baseline_commit = a98d80d44d4418cdb8a67dc8d83ee41b8e599023
submission_release_candidate_commit = UNSET
submission_data_freeze = UNSET

active_phase = 3
phase_0_status = pass
phase_1_status = pass
phase_2_status = pass
phase_3_status = pending
phase_4_status = pending
phase_5_status = pending
phase_6_status = pending
phase_7_status = pending
phase_8_status = pending

last_completed_phase = 2
last_decision = verified_only_contract
last_evidence_doc = paper/bioinformatics/phase2_decision.md
last_test_command = make check-bioinformatics-phase2
last_commit = analysis: validate a promotable GASAL2-LongTarget output contract
```

### Phase 依赖

```text
Phase 0  Bioinformatics target, claims and gap freeze
  -> Phase 1  user-facing contract-aware CLI and fail-closed execution
  -> Phase 2  mismatch analysis, promotable contract and independent holdout
  -> Phase 3  real biological batch application and widening evidence
  -> Phase 4  external state-of-the-art comparison
  -> Phase 5  installation, container, CI and release-candidate package
  -> Phase 6  optional second-GPU portability study
  -> Phase 7  Bioinformatics Application Note manuscript package
  -> Phase 8  final submission-readiness audit and journal decision
```

Phase 6 是 optional；若没有第二种 GPU，可以为 `not_available` 后继续 Phase 7–8。Phase 1–5 中任何核心科学或软件 gate 缺失，不得用“以后补”替代。

---

## 2. 最终目标与有效决策

### 2.1 总目标

建立以下完整链条：

```text
existing audited evidence
-> user-facing safe execution contract
-> independent holdout validation
-> real biological batch use case
-> external-tool positioning
-> installable release candidate
-> public-archive-ready payload
-> Bioinformatics-sized manuscript and one main figure
-> final submission audit
```

目标不是继续增加内部工程实验，而是回答编辑和用户最关心的四个问题：

1. 用户用哪个命令运行，输入不合同时软件会怎样 fail closed？
2. 哪一种结果合同经过独立验证，哪些输出仍属 experimental？
3. 相比现有 Fasim-LongTarget 和当前 triplex 工具，这个软件让真实任务扩大了多少？
4. 审稿人能否从干净环境安装、运行示例、重建主图和核对数字？

### 2.2 有效最终决策

Phase 8 只能选择以下一种：

```text
bioinformatics_application_note_ready_for_submission
bioinformatics_application_note_ready_pending_owner_actions
bioinformatics_application_note_blocked_by_scientific_gap
bioinformatics_application_note_no_go_retarget_csbj
```

解释：

- `bioinformatics_application_note_ready_for_submission`：所有科学、软件、稿件和公开 availability 条件完成；正式 release/tag/DOI 已由 owner 执行并被本地 audit 核对。
- `bioinformatics_application_note_ready_pending_owner_actions`：所有 Codex 可完成的科学、软件和稿件 gate 完成，只剩作者顺序、单位、基金、license 最终批准、GitHub/Zenodo 发布、DOI 回填和投稿系统操作。
- `bioinformatics_application_note_blocked_by_scientific_gap`：关键真实应用、独立合同验证或外部比较尚未运行/不可获得；仍可能补齐，但目前不能安全投稿。
- `bioinformatics_application_note_no_go_retarget_csbj`：上述研究完整执行，但无法形成有意义的安全 fast contract、真实应用扩大证据或外部定位；不得继续包装，转而生成 CSBJ Short Communication handoff。

不得使用“基本 ready”“差不多可以投”“只差润色”等模糊状态。

### 2.3 本轮明确非目标

- 通用 full-output GPU replacement。
- 全长 MALAT1、NEAT1、KCNQ1OT1 产品化。
- 完整 KCNQ1OT1 × chr22、完整 KCNQ1OT1 × hg38 或完整 hg38 新 benchmark。
- 重新优化 long-query kernel、persistent target 或 traceback 架构。
- 通过 query ID allowlist 隐藏 mismatch。
- 为 Bioinformatics 强行制造 biological discovery。
- 自动发布 release、Zenodo 或提交稿件。

---

## 3. 全局软件与科学合同

### 3.1 历史证据不可变合同

以下为旧论文证据包的 authority：

```text
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
paper_data_freeze = paper-data-v1-dccfd49-20260716
historical_completion_commit = a98d80d44d4418cdb8a67dc8d83ee41b8e599023
historical_aggregate_check = make check-fasim-gasal2-paper-prep
```

本轮新增文件不得修改旧 frozen source-data 的内容或 digest。需要重新解释旧结果时，生成新 derived table，并保留旧表。

### 3.2 用户执行模式合同

最终用户入口必须至少提供以下四种明确模式；实际参数名称可以根据仓库风格调整，但语义不得混淆：

```text
safe             default; only runs a promoted fast contract when all guards pass,
                 otherwise falls back before producing user-visible output
verified         runs candidate and authority for the same declared contract,
                 compares, and publishes only a contract-safe result
fast-experimental GPU fast path without authority verification; explicit opt-in,
                 prominent warning and machine-readable experimental status
cpu-authority    existing authority implementation
```

要求：

- `safe` 不等于“query_len 合规就肯定正确”。长度、normal-triplex、GPU memory 等只是 eligibility guard，不是正确性证明。
- 若 Phase 2 没有得到可 promotion 的 fast contract，`safe` 必须选择 CPU authority 或 verified path；不得静默进入 GPU-only。
- `verified` 模式发生 mismatch 时必须原子地发布 authority 结果，记录 `cpu_fallback_after_mismatch`，不得混合 candidate 与 authority 文件。
- `fast-experimental` 必须输出 warning、运行报告和限制，不得成为 README 首个默认示例。
- 所有模式必须支持 `--dry-run` 或等价预检，不写最终输出。

### 3.3 可 promotion 的结果合同

候选合同按以下优先级评估：

```text
P1  score-ranked clustered TFO1-TFO5
P2  score + stability + Nt clustered TFO1-TFO5
P3  full TFOsorted row-set equality
```

规则：

- P3 当前不作为本轮目标。
- 若 P1 在旧冻结数据和独立 holdout 上全部 clean，可以把用户默认产品输出收窄为 `score_top5_v1`，但必须把 stability/Nt 的 mismatch 如实放在 Supplementary。
- 若要 promotion P2，三种 gate 均必须在旧冻结数据和独立 holdout 上零 mismatch。
- 任一合同的 promotion 都要求：无 query ID allowlist、guard 可在运行前或运行时机械计算、unsupported 输入 fail closed、独立 holdout 无 false-safe。
- 若只有 full verification 才能保证结果，必须称为 `verified`，不能称为“自动安全 GPU fast path”。

### 3.4 安全 guard 合同

允许的 guard 包括但不限于：

- 输入 FASTA 和序列字符合法性；
- query length 与编译常量；
- normal-triplex / rule / output-mode / top-K preset；
- GPU compute capability、显存预算、worker density；
- 已证明与 mismatch 机制相关的 deterministic tie/candidate-boundary/runtime certificate；
- runtime fallback、overflow、allocation 和 comparator 状态。

禁止：

- query/gene name 黑名单；
- sequence SHA allowlist；
- “在当前 13 个 workload 中没错”直接当作 guard；
- 只看一个 rank 的 clean 就输出另外两个 rank 的保证；
- 在 mismatch 后仍保留 candidate 结果为最终结果。

### 3.5 性能合同

- 同输入、同声明合同、同 build、同设备映射、同 worker density。
- 至少记录 wall time、CPU time（可得时）、peak RSS、peak GPU memory、fallback、output digest 和输出记录数。
- 短/中等 workload 至少 5 个 paired repeats，AB/BA 顺序平衡；大 batch application 可使用一个完整 paired run加一个至少 5 次的代表性重复子集，但必须预注册。
- 任何 warm-up、异常、timeout 和 exclusion 必须 machine-readable。
- `verified` 模式的双跑总 wall time不得与 GPU candidate 单跑混为一个 speedup。
- 外部工具的输出定义若不同，只报告 tool-native runtime/coverage/output，不声称结果等价。

### 3.6 真实数据合同

- 数据选择必须由 annotation 字段、长度、字符合法性、染色体范围和固定 seed/hash 决定。
- 不得依据运行速度、mismatch、候选数量或已知生物结果筛除样本。
- holdout、application 和开发集之间按 gene ID 与 sequence digest 去重。
- 所有 reference coordinates 必须记录 assembly 和 annotation release。
- 只在有独立、可引用的实验标签时报告 known-pair recall；否则明确写“computational prioritization only”。

### 3.7 外部工具公平性合同

- 至少比较 Fasim-LongTarget authority baseline 和一个当前可运行的外部 triplex tool。
- 优先从现有 `paper/related_work_inventory.tsv` 中选择 PATO、Triplexator、3plex/Threeplex 等；最终选择由 license、可安装性和输入兼容性决定。
- 固定版本/commit/container digest、线程数、硬件、命令和输出语义。
- GPU 与 CPU 工具硬件不同必须透明报告；不得把硬件差异包装成纯算法 superiority。
- 工具无法运行时保留失败日志；不能只留下成功工具。

### 3.8 Owner-only 合同

Codex 不得编造或自行批准：

```text
author order
affiliations
ORCIDs
funding
CRediT roles
corresponding author
third-party redistribution approval
final software version number
public DOI
signed release tag
submission-system answers
```

Codex 可以生成模板、校验器、payload 和 owner 命令，但必须保留明确 placeholder 和阻塞状态。

---

## 4. Bioinformatics claim ledger

Phase 0 必须创建 `paper/bioinformatics/claim_evidence.tsv`，至少包含以下 claim ID、允许措辞、禁用措辞、数据源、gate 和状态。

### B1 — 用户可运行的软件

允许：

> GASAL2-LongTarget provides a documented, contract-aware command-line workflow for short-query lncRNA–DNA triplex top-K screening, with explicit authority, verified and experimental execution modes.

必须证明：

- 单一用户入口；
- 默认 fail-closed；
- `--help`、`--version`、example、machine-readable report；
- 干净环境安装与 smoke test；
- unsupported 输入不会静默进入 GPU fast path。

禁止：

```text
turn-key acceleration for all LongTarget analyses
full replacement for Fasim-LongTarget
safe for all lncRNAs
```

### B2 — 可声明的正确性合同

允许措辞由 Phase 2 结果决定。例如只有 P1 promotion 时：

> Under the declared short-query `score_top5_v1` contract and checked guards, the promoted fast path preserved score-ranked clustered TFO1–TFO5 on all frozen development and independent holdout workloads.

必须同时报告：

- 旧冻结数据 n；
- 新 holdout n；
- score/stability/Nt 分别的 clean/mismatch；
- guard coverage；
- fallback；
- ties/boundary evidence；
- 非 promotion 输出的限制。

禁止：

```text
exact results in general
all ranked outputs are identical
full-output equivalence
```

### B3 — 显著扩大真实应用

目标措辞：

> The software completed a preregistered multi-lncRNA, multi-promoter screening task in substantially less wall time than the authority implementation while preserving the declared final-output contract.

必须证明：

- 真实 lncRNA 和真实 regulatory target 数据；
- 至少 30 个独立 lncRNA query；
- 至少 300 个真实 promoter/target records；
- 总 query-target pair 数和总 bp；
- authority 与 safe pipeline 的 wall time；
- fixed-budget scale gain；
- final-output contract clean；
- fast-path coverage/fallback。

Bioinformatics editorial-strength gate：以下至少满足一项，且 safe pipeline 最终输出正确：

```text
median or full-batch wall speedup >= 10x
OR observed wall-time reduction >= 8 hours
OR fixed 24-hour compute budget supports >= 10x more query-target pairs
```

若未满足，B3 为 `no_go`，不能靠核心 H19 的 38x 替代真实应用扩大证据。

### B4 — 外部方法定位

允许：

> GASAL2-LongTarget was positioned against the Fasim-LongTarget authority implementation and at least one current triplex-prediction tool on the same real biological input panel, with tool-native output semantics reported separately.

必须证明：

- 至少一个外部工具成功执行；
- version、license、install、command、threads、hardware；
- runtime、peak RSS、input coverage、output count；
- 若有共同 biological labels，报告共同评价；否则不伪造等价性。

### B5 — Availability and reproducibility

允许：

> Source code, container/build instructions, example inputs, frozen source data and a checksum-verified release payload are available from the stated repository/archive.

必须证明：

- clean-checkout CPU smoke；
- CUDA build/运行说明；
- container 或等价可复现环境；
- CI；
- release payload manifest 和 checksums；
- owner release/DOI 状态明确。

### B6 — 第二 GPU portability（optional）

只有实际运行后允许：

> The declared contract was also validated on a second GPU architecture.

没有第二 GPU 时必须保留 limitation，不影响 B1–B5，但不能写跨架构 generality。

---

# Phase 0 — Bioinformatics 目标、需求和 gap freeze

## 目标

确认实际 HEAD、旧 evidence package 完整性、Bioinformatics 当前要求、B1–B6 claim 边界和所有缺口。本 phase 不修改运行时，不开始新 benchmark。

## 必做

1. 记录：

```bash
git rev-parse HEAD
git branch --show-current
git status --short
git log -1 --format='%H%n%cs%n%s'
git merge-base --is-ancestor a98d80d44d4418cdb8a67dc8d83ee41b8e599023 HEAD
```

2. 将实际 HEAD 写入 `submission_baseline_commit`。若当前 HEAD 不包含历史 completion commit，标记 `blocked`，不要自行 cherry-pick。
3. 运行历史 aggregate check：

```text
make check-fasim-gasal2-paper-prep
```

若真实 target 名称变化，先搜索并记录替代 target；不得跳过。
4. 创建：

```text
paper/bioinformatics/README.md
paper/bioinformatics/journal_requirements.md
paper/bioinformatics/claim_evidence.tsv
paper/bioinformatics/gap_register.tsv
paper/bioinformatics/owner_metadata_needed.md
paper/bioinformatics/submission_manifest.tsv
```

5. `journal_requirements.md` 必须记录：
   - 核对日期；
   - 官方页面名称；
   - article type；
   - page/word/figure guidance；
   - software availability 要求；
   - scope 中 speed improvement 与 real-data/SOTA comparison 要求；
   - figure resolution、initial-submission 和 supplement 要点；
   - 任何与本文件不一致的新要求。
6. 审计仓库是否已有以下能力并记录真实路径：
   - 用户级 wrapper/CLI；
   - input guard；
   - authority/candidate comparator；
   - JSON run report；
   - container/environment lock；
   - CI；
   - external-tool wrapper；
   - public release metadata；
   - manuscript template。
7. 建立新数据和新软件 epoch 规则：

```text
historical source data stays immutable
submission software changes tracked separately
new holdout and application data receive new freeze ID
```

8. 增加轻量 checker 和 Make target，推荐：

```text
scripts/check_bioinformatics_phase0.sh
make check-bioinformatics-phase0
```

若仓库已有统一 check framework，复用其命名和实现。

## 硬 gate

```text
historical aggregate check passes = 1
HEAD ancestry recorded = 1
journal requirements rechecked = 1
B1-B6 ledger complete = 1
all current gaps classified = 1
runtime behavior change = 0
new benchmark started = 0
```

## 完成产物

```text
paper/bioinformatics/journal_requirements.md
paper/bioinformatics/claim_evidence.tsv
paper/bioinformatics/gap_register.tsv
paper/bioinformatics/owner_metadata_needed.md
paper/bioinformatics/submission_manifest.tsv
phase 0 checker / Make target
goal.md status update
```

建议 commit：

```text
docs: freeze Bioinformatics Application Note submission scope
```

---

# Phase 1 — 用户级 contract-aware CLI 与 fail-closed 执行

## 目标

把当前研究型环境变量和 benchmark runner 收敛成一个普通用户能理解、能审计、默认安全的命令行入口。此 phase 优先使用外部 wrapper/orchestrator，不修改核心 Fasim/CUDA 算法。

## 设计要求

最终入口名称遵循仓库风格；推荐二选一：

```text
bin/gasal2-longtarget
scripts/gasal2_longtarget.py
```

不要同时维护两个独立实现。一个可以是另一个的薄 wrapper。

### 必需命令语义

```text
--mode safe|verified|fast-experimental|cpu-authority
--contract auto|score-top5|all-ranked-top5|full-output
--query <FASTA>
--target <FASTA>
--output <DIR>
--report <JSON>
--dry-run
--version
```

参数名可以调整，但 README、测试和运行报告必须使用同一语义。

## 必做

### 1. 输入与环境预检

预检至少覆盖：

```text
files exist and are readable
FASTA parse succeeds
record counts explicit
sequence characters valid
query lengths measured
query_len <= checked boundary when GPU requested
rule / normal-triplex preset explicit
requested output contract supported
CUDA binary exists when requested
GPU visible and compute capability recorded
GPU memory and worker density checked
output directory writable
no accidental overwrite without explicit flag
```

预检结果写入 report；unsupported 输入 fail closed。

### 2. 模式执行

#### `cpu-authority`

- 调用现有 authority runner；
- 生成最终输出和 report；
- 不改变旧 binary 默认行为。

#### `fast-experimental`

- 调用现有 fast top-K GPU path；
- 要求显式 opt-in；
- stderr 显示限制；
- report 写入 `result_status=experimental_unverified`；
- 不允许生成“safe”字样。

#### `verified`

- candidate 与 authority 使用独立临时目录；
- 同输入、同 contract；
- 运行现有 comparator；
- score/stability/Nt 分别记录；
- clean 时原子发布一个明确来源的最终结果；
- mismatch、candidate failure、OOM、unknown comparator state 时发布 authority 结果；
- 最终 report 记录 `candidate_clean` 或 `cpu_fallback_after_mismatch`；
- 临时目录只在完整 report 写入后按配置清理。

#### `safe`

- 初始实现不得假设存在可 promotion 的 fast contract；
- Phase 2 之前，默认行为应为：通过静态 eligibility 仍不能证明正确时，选择 `verified` 或 `cpu-authority`；
- Phase 2 只有在 promotion decision 写入 machine-readable contract registry 后，才允许 safe 模式直接走 promoted fast path；
- contract registry 必须带版本、data freeze、guard 和验证范围。

### 3. Machine-readable run report

推荐 schema 文件：

```text
schemas/gasal2_longtarget_run_report.schema.json
```

report 至少包含：

```text
schema_version
software_version
wrapper_commit
paper_runtime_commit
mode
requested_contract
resolved_contract
result_status
authority_backend
candidate_backend
input paths and SHA-256
record counts
query length min/max/distribution
target total bp
assembly/annotation metadata when available
GPU model/count/memory/driver/CUDA
CPU model and thread count
command and relevant environment
start/end timestamps
wall seconds by backend
peak RSS and peak GPU memory when available
score/stability/Nt comparator results
fallback/guard/OOM/timeout counters
published output paths and SHA-256
warnings
```

未知值写 `null`/`unavailable`，不能写 0。

### 4. 原子输出与退出码

定义并测试稳定退出码，例如：

```text
0 success with declared contract
2 invalid input or unsupported contract
3 environment/GPU unavailable
4 authority failure
5 candidate failure with no safe fallback
6 comparator failure
7 internal/report schema error
```

发生失败时不得留下看似成功的最终输出目录。

### 5. 测试

至少覆盖：

1. CPU authority small fixture。
2. Candidate 与 authority clean fixture。
3. 人工构造 comparator mismatch，确认 authority 发布。
4. query length guard。
5. malformed FASTA。
6. unsupported contract。
7. output directory collision。
8. candidate OOM/failure injection。
9. report schema validation。
10. paths 含空格和 shell metacharacter，确认无命令注入。
11. interrupt/partial output 不会被当作成功。
12. `--dry-run` 不执行 benchmark。

### 6. 文档

创建或更新：

```text
docs/gasal2_longtarget_cli.md
README.md quick start
examples/ or reproduce/ small example
```

README 首个 GPU 示例必须使用 `safe`，不得使用一串未解释环境变量作为普通用户入口。

## 硬 gate

```text
single documented user entrypoint = 1
default mode fail-closed = 1
verified mismatch publishes authority = 1
fast-experimental explicit opt-in = 1
run report validates against schema = 1
atomic output tests pass = 1
historical aggregate check still passes = 1
core runtime behavior change = 0, unless epoch protocol executed
```

## 完成产物

```text
user CLI/wrapper
run-report schema
CLI tests and fixtures
docs/gasal2_longtarget_cli.md
README quick start
phase 1 checker / Make target
goal.md status update
```

建议 commit：

```text
feat: add contract-aware GASAL2-LongTarget user workflow
```

---

# Phase 2 — mismatch 机制、可 promotion 合同和独立 holdout

## 目标

决定当前 GPU fast path 能否形成一个用户可声明的安全合同。不得把旧 10/13 clean 结果直接包装成 universal guarantee。

## 2.1 旧冻结数据重新分解

从旧 frozen source data 生成：

```text
paper/bioinformatics/frozen_contract_matrix.tsv
paper/bioinformatics/mismatch_feature_matrix.tsv
paper/bioinformatics/mismatch_analysis.md
```

至少按以下维度分解：

```text
workload/query/target
query length and composition
rank = score|stability|Nt
which TFO positions differ
tie/boundary condition
candidate count and top-K boundary margin
fallback/overflow/allocation state
runtime telemetry available from artifact
repeat consistency
```

必须明确回答：

1. score-ranked gate 是否在旧 13 个 supported-query workload 中全部 clean？
2. 三个 mismatch 是否只影响 stability/Nt，还是也影响 score？
3. mismatch 是否能由 deterministic、query-name-independent 条件提前或运行时检测？
4. 检测条件是否来自机制证据，而不是对 13 个样本过拟合？

## 2.2 Contract registry

创建：

```text
config/gasal2_longtarget_contracts.json
schemas/gasal2_longtarget_contracts.schema.json
```

每个 contract 至少包含：

```text
contract_id
status = experimental|promoted|retired
output definition
required preset
input guards
runtime guards
authority definition
validation datasets and freeze IDs
clean/mismatch counts
known limitations
```

初始全部为 `experimental`。只有 Phase 2 最终 promotion gate 通过后才能标记 `promoted`。

## 2.3 独立 holdout manifest

若没有 author 提供的更合适 panel，使用以下默认 protocol；允许根据实际 annotation 字段调整，但不得降低最低规模：

- 来源：一个公开、可重建的 human lncRNA annotation release，assembly 固定为 GRCh38 或仓库当前 authority assembly；
- 至少 12 个非 H19、非旧 generalization panel 的 lncRNA query；
- gene ID 与 sequence digest 均不与开发集重叠；
- 只保留 canonical A/C/G/T、长度 `<=2812` 的 transcript；
- 至少覆盖三个长度层：`<=800`、`801–1600`、`1601–2812`，每层至少 4 个；
- 每个 gene 只选一个 transcript，选择规则固定；
- 使用固定 seed/hash 进行确定性选择；
- target 使用至少两个真实、已记录来源的 target scopes，且不允许全部是 H19 原核心 scope；
- manifest、输入 SHA 和 selection script 先提交/冻结，再运行。

创建：

```text
reproduce/bioinformatics/fetch_holdout_inputs.sh
reproduce/bioinformatics/build_holdout_panel.py
paper/bioinformatics/holdout_manifest.tsv
paper/bioinformatics/holdout_manifest.sha256
paper/bioinformatics/holdout_protocol.md
```

若网络不可用，脚本和 manifest 可以先完成，但 Phase 2 状态必须为 `blocked`，不能假装 holdout 已完成。

## 2.4 Holdout 运行

- authority、candidate 与 CLI verified 模式均运行；
- 每个 workload 至少一组完整正确性比较；
- 代表性子集至少 3 次，确认 mismatch 不是随机波动；
- score/stability/Nt 三种 gate 分别记录；
- 所有 mismatch、fallback、guard、OOM、timeout 保留。

## 2.5 Guard promotion

任何 proposed guard 必须满足：

```text
uses no query name/gene ID/sequence digest allowlist
computable from input or runtime certificate
zero false-safe on all frozen development rows
zero false-safe on all independent holdout rows
all promoted-path outputs pass the declared contract
unsupported/uncertain rows fail closed
```

可接受 guard 对 clean 样本有保守 fallback；必须报告 coverage 和 fallback cost。

## 2.6 Phase 2 决策

只能选择：

```text
safe_fast_contract_promoted
verified_only_contract
no_user_safe_gpu_contract
```

### `safe_fast_contract_promoted`

要求：

- 至少 P1 `score_top5_v1` 在旧冻结 + holdout 全部 clean；
- guard 无 false-safe；
- `safe` CLI 仅在该 contract 下直接进入 GPU fast path；
- stability/Nt 若未 promotion，CLI 不得声称保证。

### `verified_only_contract`

- 静态/运行时 guard 不能保证 GPU candidate；
- verified 模式可保证最终结果；
- safe 模式不得直接 GPU-only；
- 后续 Phase 3 必须测量包含验证/回退后的真实总 wall time。

### `no_user_safe_gpu_contract`

- 连 verified/authority fallback 流程也无法稳定提供声明合同，或无任何有意义的 top-K 合同；
- 保留证据；
- Phase 3–5 可以继续完成软件和应用评估，但 Phase 8 很可能选择 CSBJ no-go。

## 硬 gate

```text
old mismatch rows fully decomposed = 1
score/stability/Nt old counts explicit = 1
independent holdout preregistered before run = 1
holdout query count >= 12 = 1
holdout has no development overlap = 1
all holdout rows represented = 1
promotion uses no ID/digest allowlist = 1
contract registry machine-readable = 1
one valid Phase 2 decision selected = 1
```

## 完成产物

```text
frozen_contract_matrix.tsv
mismatch_feature_matrix.tsv
mismatch_analysis.md
contract registry and schema
holdout fetch/build scripts
holdout manifest/protocol/source data
promotion decision document
phase 2 checker / Make target
goal.md status update
```

建议 commit：

```text
analysis: validate a promotable GASAL2-LongTarget output contract
```

---

# Phase 3 — 真实 biological batch application 与应用范围扩大证据

## 目标

构建一个编辑和普通生物信息学用户都能理解的真实批量 screening 任务，证明软件不仅在 H19 chr21/chr22 benchmark 上快，而是能在固定计算预算内处理显著更多 lncRNA–target pairs。

## 3.1 默认 application design

若作者没有提供更有生物意义、可公开且已批准的数据集，采用以下默认设计：

### Query panel

- 同一公开 human lncRNA annotation release；
- 至少 50 个 lncRNA gene，每个 gene 一个 transcript；
- 长度 500–2812 nt；
- canonical A/C/G/T；
- 排除 H19、旧 generalization panel、Phase 2 holdout；
- 按 gene ID 排序后使用固定 seed/hash 确定性选取；
- 不依据结果、速度或 known biology 挑选。

### Target panel

- 同一 assembly/annotation release；
- 至少 300 个真实 protein-coding gene promoter records；
- 默认使用 chr21+chr22 上所有满足规则的 protein-coding genes；若不足 300，按染色体顺序扩展到 chr20；
- 每个 gene 选择一个确定性的代表 TSS；
- promoter window 默认 `TSS-2000` 到 `TSS+500`，剪裁到染色体边界；
- 记录 strand、gene ID、coordinates、assembly；
- 不因候选数量或运行表现改变窗口。

最低规模：

```text
lncRNA queries >= 30
target records >= 300
query-target pairs >= 9000
```

推荐规模：

```text
lncRNA queries = 50
all eligible chr21+chr22 promoters
```

如果本机资源不足，允许在运行前通过一个明确排除在主结果外的 pilot 选择“推荐规模”或“最低规模”；选择规则只能基于预声明的计算预算和输入规模，不能基于 speedup/correctness 结果。

## 3.2 输入构建与冻结

创建：

```text
reproduce/bioinformatics/fetch_application_inputs.sh
reproduce/bioinformatics/build_application_panel.py
paper/bioinformatics/application_manifest.tsv
paper/bioinformatics/application_manifest.sha256
paper/bioinformatics/application_protocol.md
paper/bioinformatics/application_input_summary.tsv
```

manifest 至少包含：

```text
record_id
record_role = query|target
source release
assembly
original ID
selection rule
sequence length
coordinates where applicable
SHA-256
license note
split = application|positive_control
```

## 3.3 Positive control / biological illustration

- 可以加入一个或少量独立、文献支持的 lncRNA-target positive control；
- 必须由 primary source 或现有公开 benchmark 明确支持；
- 不得从 application 输出中事后挑选“看起来合理”的案例；
- 若没有可靠 label，跳过 known-pair recall，并在稿件中写 `computational prioritization only`；
- 不得因此阻止性能 application 完成。

## 3.4 运行模式

必须比较：

```text
A  cpu-authority
B  candidate fast path under the declared contract
C  user-facing safe pipeline
```

若 Phase 2 为 `safe_fast_contract_promoted`，B 与 C 可能相同，但仍分别记录 mode/report。

若 Phase 2 为 `verified_only_contract`：

- C 必须包含 authority verification/fallback 的真实总 wall time；
- 不能用 B 的单跑 speedup 代表用户安全 pipeline；
- 稿件可以分别报告 candidate capability 与 safe end-to-end cost，但主要用户 claim 使用 C。

## 3.5 重复协议

- 一个完整 application paired run，保留所有 raw artifacts；
- 若完整 run 每个 arm 在可接受预算内，再完成至少 3 个 paired repeats；
- 否则冻结一个代表性子集，完成至少 5 个 AB/BA paired repeats；
- 完整 run 仍作为 descriptive application result；
- 所有 run 使用同输入 manifest、同 contract、同 worker density。

## 3.6 必须报告

```text
query count
target count
query-target pair count
query total bp and target total bp
authority wall seconds
candidate wall seconds
safe pipeline wall seconds
paired speedups where valid
fixed 24-hour capacity estimate based on observed throughput
peak RSS
peak GPU memory
fast-path coverage
fallback counts and reasons
score/stability/Nt contract results
published output count/digest
candidate prioritization summary
```

fixed-budget scale gain 必须由 observed throughput 计算，不得仅用理论请求数。

## 3.7 应用扩大 promotion gate

B3 要成为 Bioinformatics 主结果，必须：

```text
real biological panel complete = 1
minimum scale reached = 1
final safe output contract clean = 1
all fallbacks visible = 1
and at least one editorial-strength widening criterion passes
```

widening criterion：

```text
safe pipeline speedup >= 10x
OR observed wall reduction >= 8 hours
OR 24-hour pair capacity gain >= 10x
```

若 candidate B 很快但 safe C 不满足，上述主 claim 为 `no_go`；不得只报 B。

## 3.8 Source data 和图表

创建：

```text
paper/bioinformatics/source_data/application_runs.tsv
paper/bioinformatics/source_data/application_summary.tsv
paper/bioinformatics/source_data/application_correctness.tsv
paper/bioinformatics/application_report.md
paper/bioinformatics/figures/application_panel.svg
paper/bioinformatics/figures/application_panel.pdf
```

图从 source data 生成，不手工改数字。

## 硬 gate

```text
query selection preregistered = 1
target selection preregistered = 1
query count >= 30 = 1
target records >= 300 = 1
pairs >= 9000 = 1
authority and safe pipeline both run = 1
final contract clean or fail-closed authority result = 1
all failure rows retained = 1
application source data frozen = 1
B3 promotion decision explicit = 1
```

## 完成产物

```text
application fetch/build scripts
application manifest/protocol/input summary
raw artifact manifest
application source data and report
reproducible application figure
phase 3 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: add preregistered real-world lncRNA promoter screening application
```

---

# Phase 4 — 当前外部 triplex 工具比较

## 目标

满足 Bioinformatics 对 real-data state-of-the-art positioning 的要求，并清楚说明 GASAL2-LongTarget 是同算法加速、输出合同不同或应用场景不同，而不是借不公平硬件比较宣称全面 superiority。

## 4.1 工具选择

强制：

```text
Fasim-LongTarget authority baseline
```

外部工具至少成功运行一个，优先顺序：

```text
PATO
Triplexator
3plex / Threeplex
other current tool already verified in related_work_inventory
```

选择前检查：

```text
source/release available
license permits local benchmark
installation reproducible
input semantics compatible enough for the application panel
command-line or batch interface available
```

不要同时投入多个无法安装的工具；先完成最相关的一个，再将第二个作为加分项。

## 4.2 可复现环境

为每个工具创建：

```text
reproduce/external_tools/<tool>/README.md
reproduce/external_tools/<tool>/install.sh or container definition
reproduce/external_tools/<tool>/run_application.sh
reproduce/external_tools/<tool>/VERSION.txt
reproduce/external_tools/<tool>/LICENSE_NOTE.md
```

固定：

```text
version/commit/container digest
threads
CPU/GPU assignment
input conversion
native parameters
output parser
```

## 4.3 公平比较

- 使用 Phase 3 的同一 query/target panel；若工具不能支持全部输入，预先定义兼容子集并报告 coverage。
- 每个工具使用文档推荐参数；任何参数改变均记录。
- 记录 wall time、peak RSS、成功输入比例、output count、失败原因。
- 不把工具原生输出与 LongTarget top-K 当作逐行等价。
- 若存在独立 positive-control labels，使用一个共同、预注册的评价，如 recall@K；否则只报告 runtime/coverage/output characteristics。
- 外部工具运行在 CPU 而 GASAL2 在 GPU 时，表头和 caption 必须明确硬件，不写“algorithm X times faster”而不限定硬件与合同。

## 4.4 失败保留

所有尝试写入：

```text
paper/bioinformatics/external_tool_attempts.tsv
```

字段至少：

```text
tool
version
attempt_status
install_status
run_status
input_coverage
failure_stage
failure_message
log_path
included_in_main_comparison
```

## 4.5 Source data 与定位表

创建：

```text
paper/bioinformatics/source_data/external_comparison.tsv
paper/bioinformatics/external_comparison.md
paper/bioinformatics/tables/tool_positioning.tsv
paper/bioinformatics/tables/tool_positioning.md
```

定位表至少包括：

```text
tool
algorithm/application focus
output semantics
hardware
version
input coverage
wall time
peak RSS/GPU memory
availability/license
biological evaluation metric, if any
```

## 硬 gate

```text
Fasim authority included = 1
at least one external current tool successfully run = 1
same real input panel or explicit compatible subset = 1
versions/licenses/commands frozen = 1
hardware and output semantics explicit = 1
failed attempts retained = 1
no false row-equivalence claim = 1
```

若没有任何外部工具可成功执行，Phase 4 为 `blocked`，Bioinformatics final decision 不得为 ready；可以生成 CSBJ handoff。

## 完成产物

```text
external tool reproducibility wrappers
external_tool_attempts.tsv
external comparison source data/report/table
phase 4 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: position GASAL2-LongTarget against current triplex tools
```

---

# Phase 5 — 安装、容器、CI 和 release-candidate package

## 目标

把研究仓库转成审稿人和用户能够安装、运行示例、检查版本和重建论文材料的软件 release candidate。Codex 只准备和验证 payload，不公开发布。

## 5.1 版本和目录

根据仓库现有风格建立：

```text
VERSION or equivalent generated version source
CHANGELOG.md
release/README.md
release/OWNER_ACTIONS.md
release/release_manifest.tsv
release/SHA256SUMS
```

版本号不得自行定为最终正式版本。可以使用：

```text
0.1.0-rc1+<shortsha>
```

或仓库现有规范，最终由 owner 批准。

`--version` 至少输出：

```text
software version
wrapper commit
paper runtime commit
contract registry version
```

## 5.2 安装与环境

至少提供一种可实际验证的 CUDA 可复现环境，以及一个 CPU-only smoke 路径。推荐：

```text
containers/Dockerfile.cuda
containers/Apptainer.def
```

可以只完成其中一个 GPU container，但必须实际 build 或给出明确 blocked 原因。另提供：

```text
environment/README.md
environment/toolchain_versions.tsv
```

固定并记录：

```text
base image tag and digest
OS
compiler
CUDA toolkit
Python packages
GASAL2 source commit
build flags
```

不得依赖未记录的 host-local library。

## 5.3 一条命令 quick start

从干净 checkout，用户应能执行类似：

```text
make release-smoke
```

或等价入口，完成：

```text
build or locate binary
run bundled small example through safe mode
validate run report
validate expected output digest/contract
```

真实 target 名称由 Codex 检查后确定。

## 5.4 CI

新增 CPU-only GitHub Actions 或仓库现有 CI 等价物，至少：

```text
build CPU authority/wrapper
lint Python/shell where existing tools permit
run unit tests
run small safe/verified smoke without GPU
validate schemas
run historical lightweight paper checks
```

GPU CI 非强制；不得用 mock GPU 伪装真实 CUDA success。GPU smoke 在 release checklist 中作为本地 owner-run gate。

## 5.5 文档

README 和 docs 至少包含：

```text
what the software does
supported contract
unsupported/full-output limitations
hardware requirements
installation
safe-mode quick start
verified-mode example
fast-experimental warning
input/output formats
run-report interpretation
troubleshooting
citation placeholder
license
```

环境变量细节移到 advanced docs，普通用户入口不应要求理解所有内部开关。

## 5.6 Third-party license inventory

创建或更新：

```text
THIRD_PARTY_LICENSES.md
release/redistribution_inventory.tsv
```

覆盖：

```text
LongTarget/Fasim code
GASAL2
annotation/reference inputs
external comparison tools
container base
paper raw artifacts
```

不确定项写 `owner_review_required`。

## 5.7 Citation 和 archive metadata 模板

在 author metadata 未批准前生成模板而不是伪造最终文件：

```text
release/CITATION.cff.in
release/.zenodo.json.in
release/RELEASE_NOTES.md.in
```

checker 必须确保最终 release candidate 若使用正式 `CITATION.cff` / `.zenodo.json`，其中不含 placeholder。

## 5.8 Artifact archive payload

把以下内容打包到 Git 外的 staging directory：

```text
source-data
tables
main/supplementary figures
manifests
checksums
reproduction scripts
Phase 2–4 raw artifact manifests
允许公开的 raw artifacts
```

创建：

```text
release/archive_payload_manifest.tsv
release/archive_payload_SHA256SUMS
release/archive_payload_validation.log
```

不得把数 GB raw artifacts直接提交到 Git。

## 5.9 Release candidate audit

从 clean checkout / container 执行：

```text
historical aggregate check
Phase 1–5 checks
release smoke
quick reproduction
application source-data rebuild
main figure/table rebuild
archive payload checksum validation
```

## 硬 gate

```text
single release version source = 1
CPU smoke from clean checkout = 1
GPU environment/build instructions validated or exact block recorded = 1
safe example passes = 1
run report validates = 1
CPU CI configuration passes locally where possible = 1
third-party inventory complete = 1
release payload manifest/checksums complete = 1
no large raw artifacts accidentally tracked = 1
no invented citation metadata = 1
```

## 完成产物

```text
version/changelog
container/environment files
release smoke
CI workflow
user documentation
third-party inventory
citation/archive metadata templates
archive payload and checksum manifests
phase 5 checker / Make target
goal.md status update
```

建议 commit：

```text
release: prepare GASAL2-LongTarget Application Note candidate
```

---

# Phase 6 — 第二 GPU 架构 portability（optional）

## 目标

若本地或已获授权的机器存在非 RTX 4090 的第二种 NVIDIA GPU 架构，验证同一 contract 和 preset 的正确性与可迁移性。不得为此购买或租用资源。

## 6.1 可用性检查

记录：

```text
nvidia-smi -L
model
compute capability
memory
driver
CUDA
machine ownership/authorization
```

若只有当前 RTX 4090，或没有授权的第二平台：

- 设置 `phase_6_status = not_available`；
- 创建 `paper/bioinformatics/second_gpu_runbook.md`；
- 保留单架构 limitation；
- 继续 Phase 7。

## 6.2 运行协议

若可用：

- 不改变 contract、batch、stream、threshold、worker density 或算法；
- 运行 Phase 2 的代表性 correctness subset；
- 运行 Phase 3 application 的固定代表性 subset；
- 每个 performance pair 至少 3 次；
- 报告绝对 wall、speedup、peak memory、fallback、correctness；
- 不要求与 4090 达到同一 speedup，只要求合同不被破坏。

## 6.3 决策

```text
pass   contract clean and evidence complete
no_go  actual second GPU run completed but contract/portability failed
not_available no authorized second architecture
```

## 完成产物

```text
paper/bioinformatics/second_gpu_report.md
paper/bioinformatics/source_data/second_gpu.tsv
or paper/bioinformatics/second_gpu_runbook.md
phase 6 checker / Make target when applicable
goal.md status update
```

建议 commit：

```text
bench: characterize GASAL2-LongTarget on a second GPU architecture
```

---

# Phase 7 — Bioinformatics Application Note 稿件包

## 目标

从 B1–B6 和新冻结 source data 生成一套符合当前 Bioinformatics Application Note 要求的短稿、单幅主图、Supplementary、cover letter 和 submission checklist。作者信息保持 placeholder。

## 7.1 稿件定位

推荐标题起点：

```text
GASAL2-LongTarget: contract-aware GPU acceleration for lncRNA–DNA triplex screening
```

标题根据 Phase 2 合同调整：

- 若只 promotion score top-K，不得在标题或摘要暗示 all-ranked/full-output exactness。
- 若 B3 no-go，不得继续写“enables large-scale screening”；Phase 8 应考虑 CSBJ。

## 7.2 主稿结构

执行时按最新官方模板核对。建议内容：

```text
Title
Abstract / required structured fields
1 Introduction or Motivation
2 Implementation
3 Results / Application
4 Availability and implementation
Data availability
Funding placeholder
Conflict of interest placeholder
References
```

正文目标：

```text
2000–2300 words plus one main composite figure
hard maximum according to current official guidance
```

不把 Supplementary、references 和 figure caption 的计数规则想当然；记录实际统计方法。

## 7.3 一幅主图

创建一个可缩放的 composite figure，推荐四个 panel：

```text
A  user workflow: safe / verified / experimental / authority
B  frozen + holdout correctness and fast-path coverage
C  real batch application wall time / fixed-budget scale gain
D  external-tool positioning or application candidate summary
```

要求：

- 从 source data 生成；
- vector PDF/EPS/SVG 之一；
- 另导出符合当前期刊分辨率要求的 raster；
- 字体在单栏/双栏缩放后可读；
- caption 明确 n、合同、硬件、fallback 和输出语义；
- 不用生成式图片作为方法或数据图。

## 7.4 Supplementary

把当前 evidence package 中不适合 4 页正文的内容移入 Supplementary：

```text
complete correctness matrix
all mismatch rows
holdout selection protocol
application manifest details
external tool commands/failures
two-slot/exact-column/archive ablations
long-query no-go
resource limits
second GPU or portability runbook
reproduction instructions
```

保持旧 C1–C7 证据可追踪，不在正文塞入所有内部优化细节。

## 7.5 Cover letter

`paper/bioinformatics/cover_letter.md` 必须直接回答：

1. 相比 Fasim-LongTarget，新软件让用户完成了什么以前明显更昂贵的任务？
2. 为什么这不只是把已有代码接到 GASAL2？
3. 软件如何处理 unsupported、uncertain 和 mismatch 情况？
4. 与至少一个当前 triplex 工具的关系是什么？
5. 本稿没有声称什么？

不得写无法支持的“first”“universal”“exact replacement”。

## 7.6 Availability

主稿必须明确：

```text
repository
release candidate or final tag
license
container/build instructions
example
source-data/archive
DOI status
supported hardware and contract
```

如果 DOI 尚未由 owner 创建，使用显式 placeholder，并使 Phase 8 最终状态为 `ready_pending_owner_actions`，不能写虚构 DOI。

## 7.7 稿件产物

创建：

```text
paper/bioinformatics/manuscript.md
paper/bioinformatics/manuscript.tex or current official template source
paper/bioinformatics/manuscript.pdf
paper/bioinformatics/supplementary.md
paper/bioinformatics/supplementary.pdf
paper/bioinformatics/main_figure.*
paper/bioinformatics/cover_letter.md
paper/bioinformatics/submission_checklist.md
paper/bioinformatics/data_availability.md
paper/bioinformatics/availability_and_implementation.md
paper/bioinformatics/author_placeholders.tsv
```

## 7.8 Claim-language audit

扫描正文、摘要、caption、cover letter，禁止未经限定的模式：

```text
38x faster than LongTarget
universally accelerates
exact replacement
all lncRNAs
all top-K rankings identical
full-output equivalence
genome-wide acceleration
biologically superior
state of the art accuracy
```

允许在引用或明确否定上下文中出现；checker 需支持 allowlist/context。

## 7.9 数字审计

所有主稿数字必须映射到：

```text
claim ID
source-data file
row/filter
analysis script
figure/table panel
```

创建：

```text
paper/bioinformatics/manuscript_number_map.tsv
```

独立 checker 重新计算所有 speedup、capacity gain、clean counts 和 coverage，不调用主绘图脚本的 summary 函数。

## 硬 gate

```text
current journal requirements followed = 1
word/page guidance met = 1
one main figure only, unless current rules differ = 1
B1-B5 each represented or explicitly no-go = 1
all numbers trace to source data = 1
all limitations retained = 1
availability statement complete = 1
no invented author/funding/DOI = 1
cover letter answers novelty/safety/application = 1
claim-language audit passes = 1
```

## 完成产物

```text
Bioinformatics manuscript source/PDF
one main composite figure
Supplementary source/PDF
cover letter
availability/data statements
submission checklist
manuscript number map and audit
phase 7 checker / Make target
goal.md status update
```

建议 commit：

```text
paper: assemble Bioinformatics Application Note submission package
```

---

# Phase 8 — 最终 submission-readiness audit 与 journal decision

## 目标

从 clean checkout 验证历史证据、新合同、真实应用、外部比较、release candidate 和 Bioinformatics 稿件闭环，并给出唯一决策。

## 8.1 新数据冻结

冻结：

```text
submission_data_freeze = bioinformatics-data-v1-<commit>-<YYYYMMDD>
```

包含：

```text
holdout inputs and results
application inputs and results
external comparison
second GPU if available
manuscript source data
all manifests/checksums
```

旧 `paper-data-v1-dccfd49-20260716` 保持不变。

## 8.2 Aggregate checker

新增：

```text
scripts/check_bioinformatics_application_note_ready.sh
make check-bioinformatics-application-note-ready
```

必须串联：

```text
historical paper aggregate check
Phase 0–7 checks
contract registry validation
CLI safe/verified smoke
holdout completeness
application scale/correctness
external comparison
release smoke
container/environment validation
source-data/figure/table rebuild
manuscript word/figure/checklist audit
claim-language audit
owner-action status
```

## 8.3 Clean-checkout reproduction

从无未跟踪依赖的 clean checkout 验证：

```text
CPU smoke
schema tests
quick source-data reproduction
main figure rebuild
manuscript PDF build
release payload checksum validation
```

GPU 和外部工具昂贵运行可以使用 frozen artifacts，但必须有完整 rerun command 和 input digest。

## 8.4 Submission readiness 文档

创建：

```text
paper/bioinformatics/SUBMISSION_READINESS.md
paper/bioinformatics/OWNER_ACTIONS.md
paper/bioinformatics/completion_audit.tsv
```

`SUBMISSION_READINESS.md` 至少包含：

```text
final decision
actual HEAD and release candidate commit
historical runtime/data freeze
new submission data freeze
promoted contract or verified-only status
holdout counts
application task and widening result
external comparator result
software/install/container/CI status
second GPU status
manuscript word count and figure inventory
known limitations
remaining owner-only actions
recommended journal and fallback
```

## 8.5 Bioinformatics hard gates

最终 ready 要求：

```text
B1 user-facing software passes = 1
at least one meaningful contract is safe for final user output = 1
independent holdout complete = 1
B3 real application scale complete = 1
B3 widening criterion passes = 1
at least one external current tool comparison complete = 1
release candidate/install/smoke complete = 1
manuscript package complete = 1
all main numbers reproducible = 1
no hidden mismatch/fallback/failure = 1
```

第二 GPU 不属于 hard gate。

### 特殊判断：verified-only

若 Phase 2 为 `verified_only_contract`，只有在 Phase 3 的完整 **safe pipeline** 仍满足 B3 widening criterion，且最终输出零错误时，才允许 Bioinformatics ready。不得用 candidate-only speedup 代替。

## 8.6 CSBJ handoff

若最终为 `bioinformatics_application_note_no_go_retarget_csbj`，创建：

```text
paper/csbj/HANDOFF.md
paper/csbj/outline.md
paper/csbj/claim_map.tsv
```

内容应把 operating envelope、mismatch、negative results、long-query no-go、archive/exact-column/two-slot 证据恢复为正文主线。不得丢弃本轮失败证据。

## 8.7 Owner actions

Owner-only 最少包括：

```text
approve authors/affiliations/ORCIDs/CRediT/funding
approve third-party redistribution
fill final CITATION.cff and Zenodo metadata
publish GitHub release
publish permanent archive and obtain DOI
verify DOI payload checksum
create signed tag
replace manuscript placeholders
perform final coauthor review
submit through journal system
```

若只剩这些，选择 `bioinformatics_application_note_ready_pending_owner_actions`。

## 硬 gate

```text
aggregate checker passes = 1
historical data freeze unchanged = 1
new submission data freeze complete = 1
independent arithmetic audit passes = 1
clean-checkout reproduction passes = 1
completion audit has no unknown/missing core rows = 1
one valid final decision selected = 1
SUBMISSION_READINESS.md complete = 1
```

## 完成产物

```text
submission data freeze
aggregate checker / Make target
SUBMISSION_READINESS.md
OWNER_ACTIONS.md
completion_audit.tsv
optional CSBJ handoff
final goal.md status update
clean working tree or explicit diff list
```

建议 commit：

```text
docs: certify Bioinformatics Application Note submission readiness
```

---

## 9. 最终文件清单

Phase 8 必须逐项核对并更新为 `[x]`、`[no-go]`、`[not-available]` 或 `[blocked]`，不得提前勾选。

```text
[ ] historical paper aggregate still passes
[ ] historical paper data freeze unchanged
[ ] Bioinformatics requirements rechecked
[ ] B1-B6 claim ledger complete
[ ] single user-facing CLI exists
[ ] safe mode fail-closed
[ ] verified mismatch publishes authority
[ ] fast-experimental is explicit opt-in
[ ] run report schema and tests pass
[ ] old mismatch mechanism analyzed
[ ] independent holdout preregistered
[ ] independent holdout complete
[ ] contract registry frozen
[ ] valid contract promotion decision selected
[ ] real application manifest preregistered
[ ] real application minimum scale reached
[ ] authority/candidate/safe application runs complete
[ ] safe application correctness complete
[ ] application widening decision explicit
[ ] at least one external current tool run
[ ] external tool failures retained
[ ] fair hardware/output semantics documented
[ ] clean installation path documented
[ ] container or equivalent environment validated
[ ] CPU CI/smoke passes
[ ] release payload and checksums complete
[ ] third-party redistribution inventory complete
[ ] second GPU pass/no-go/not-available recorded
[ ] one-main-figure Bioinformatics manuscript complete
[ ] Supplementary complete
[ ] cover letter complete
[ ] availability/data statements complete
[ ] author/funding/DOI not invented
[ ] all manuscript numbers trace to source data
[ ] independent arithmetic audit passes
[ ] claim-language audit passes
[ ] new submission data freeze complete
[ ] final aggregate check passes
[ ] SUBMISSION_READINESS.md written
[ ] one valid final decision selected
```

---

## 10. Codex 开始执行时的第一条动作

不要继续写新的 planning 文档。直接执行：

1. 将本文件 `active_phase` 保持/改为 `0`，`phase_0_status` 改为 `in_progress`。
2. 读取 `goal-final.md` 和 `paper/PAPER_PREP_STATUS.md`，确认旧状态为完成。
3. 记录实际 HEAD、branch、working tree 和 `a98d80d44d4418cdb8a67dc8d83ee41b8e599023` 的祖先关系。
4. 运行 `make check-fasim-gasal2-paper-prep`；若 target 改名，搜索真实 target 并记录。
5. 创建 `paper/bioinformatics/` 的 Phase 0 六个基础文件。
6. 重新核对 Bioinformatics 官方 requirements，并写入核对日期和差异。
7. 完成 Phase 0 checker；通过后形成 Phase 0 commit/diff，再把 `active_phase` 更新为 1。
8. 在 Phase 2 holdout manifest 和 Phase 3 application manifest 冻结前，禁止开始对应 benchmark。
