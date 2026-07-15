# GASAL2-LongTarget 论文写作前准备执行目标

> 用途：将本文件放到 `wyjistest/LongTarget-exact-sim` 仓库根目录，替换已经完成的上一版 `goal.md`，交给 Codex 按 phase 完成论文开稿前的证据、统计、图表和复现准备。
>
> 起点：长 query 架构探索已经在 commit `0d11aa2d61b7ccda59b462ab8e0750dad17ee18f` 收口，最终结论为 `long_query_architecture_no_go_with_complete_evidence`。本文件不得重新打开已经关闭的架构 phase，也不得把继续优化长 query 设为开稿前提。
>
> 本文件不是论文正文。Codex 的任务是形成一个可审计、可重建、可以直接交给作者写作的 **paper-ready evidence package**。

---

## 0. Agent 指令

从 `active_phase` 指向的 phase 开始。每次只完成一个 phase；完成实现、运行、检查和证据文档后，更新本文件状态，再进入下一 phase。

必须遵守：

1. 先读取当前 checkout、`Makefile`、现有 benchmark/check 脚本和相关文档，再新增文件。不要根据本文件中的历史路径假设仓库未变化。
2. 复用现有 runner、comparator、digest、fallback、GPU memory、archive restore 和 phase checks；不要复制第二套运行时或正确性逻辑。
3. 本轮默认不修改 `fasim/`、CUDA kernel、GASAL2 bridge 或生产运行时算法。只允许修复会影响测量正确性、可复现性或数据解析的 bug。
4. 如果任何 C/C++/CUDA/运行时行为发生变化，必须增加 `paper_runtime_epoch`，冻结新的 runtime commit，并重新运行所有受影响 benchmark；不得混用旧结果和新 binary。
5. 不得为了跨过 `1.10x`、获得更好图形或改善摘要数字而继续调 stream、batch、threshold、pruning 或 long-query 架构。
6. 不得运行完整 121-segment KCNQ1OT1 × chr22、完整 KCNQ1OT1 × hg38 或其它数小时全量任务。本轮 long-query 上限是已有的 bounded max8 dual-grid workload。
7. 所有性能比较必须完成同一个输出合同。不得把 fast top-K 与完整 TFOsorted 的 wall time直接当作同工作量 speedup。
8. 所有正确性判断必须分别记录 score、stability、Nt 三种 clustered TFO1–5；不得只报告一个 rank 或一个 overlap 数。
9. 不得隐藏 mismatch、fallback、guard、OOM、timeout 或失败运行。所有预注册 workload 都必须出现在最终 source data 中。
10. 不得运行后再修改 generalization panel 以删除表现不好的 query、位置或 target。manifest 必须先提交或至少先写入不可变 digest，再开始运行。
11. 原始日志和运行 artifact 一经纳入数据冻结，不得原地修改。解析修复必须生成新的 derived dataset，并保留旧 artifact digest。
12. 不得手工把论文数字复制到图表。表格和图必须从机器可读 source-data 文件生成。
13. 最终论文图不得使用生成式图片作为数据图或方法图。方法示意图必须由可版本控制的矢量脚本生成。
14. 不得编造作者、单位、基金、期刊格式、DOI、PMID、软件版本或硬件信息；未知项写入 gap register。
15. 每个 phase 形成一个可审查 diff。环境支持时一个 phase 一个 commit；不支持提交时记录建议 commit message。
16. 不要 reset、覆盖或清理用户已有改动。只删除当前 phase 自己创建的临时目录。
17. 不要自动 push、创建公开 release、上传 Zenodo 或提交论文。最终只生成 release/tag 清单和建议命令，除非用户另有明确授权。

### 状态值

只允许：

```text
pending
in_progress
pass
no_go
blocked
```

含义：

- `pass`：phase 的实现、运行和所有硬 gate 完成。
- `no_go`：该实验线完整执行，但预注册 claim gate 不成立；负结果已保留，phase 算完成。
- `blocked`：缺硬件、输入、权限或不可恢复 artifact；不算完成，必须列出解除阻塞所需条件。

注意：某一科学 claim 可以得到 `no_go`，但论文准备仍可继续，只要最终文章范围相应缩小且证据完整。核心数据完整性 phase 不允许用 `no_go` 代替缺失工作。

---

## 1. 执行状态

Codex 每完成一个 phase，必须更新此块；不得提前把后续 phase 标为 `pass`。

```text
paper_baseline_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
data_freeze_id = unset

active_phase = 2

phase_0_status = pass
phase_1_status = pass
phase_2_status = pending
phase_3_status = pending
phase_4_status = pending
phase_5_status = pending
phase_6_status = pending
phase_7_status = pending
phase_8_status = pending
phase_9_status = pending

last_completed_phase = 1
last_decision = paper_benchmark_protocol_and_manifest_frozen
last_evidence_doc = paper/benchmark_protocol.md
last_test_command = make check-fasim-gasal2-paper-phase1
last_commit = bench: preregister paper workloads and add digest-aware harness
```

### Phase 依赖

```text
Phase 0  scope / claim / evidence freeze
  -> Phase 1  benchmark protocol and harness
  -> Phase 2  core repeated benchmarks
  -> Phase 3  preregistered generalization panel
  -> Phase 4  ablation, resource and archive characterization
  -> Phase 5  statistics and source-data freeze
  -> Phase 6  figures, tables and captions
  -> Phase 7  reproducibility package
  -> Phase 8  manuscript source kit and citation inventory
  -> Phase 9  final audit and paper-preparation decision
```

### 有效最终结果

Phase 9 只能选择：

```text
paper_preparation_ready
paper_preparation_ready_with_declared_limitations
paper_preparation_blocked_with_complete_gap_report
```

解释：

- `paper_preparation_ready`：核心 claim 有重复实验、完整正确性、统计、source data、图表和复现包。
- `paper_preparation_ready_with_declared_limitations`：所有硬数据 gate 完成，但第二 GPU 平台、某些昂贵 descriptive workload 或外部归档未完成；限制已明确，不影响当前 scoped 文章开稿。
- `paper_preparation_blocked_with_complete_gap_report`：核心 claim 的输入、重复、正确性或原始 artifact 缺失，尚不能安全开稿。

不得使用“基本完成”“大致 ready”“数字够用了”等模糊结论。

---

## 2. 总目标与非目标

### 2.1 总目标

建立以下完整链条：

```text
frozen claims
-> preregistered workloads
-> immutable raw artifacts
-> paired repeated benchmarks
-> explicit correctness contracts
-> statistical summaries
-> machine-readable source data
-> reproducible vector figures and tables
-> reproduction package
-> manuscript outline / methods notes / limitations / citations
-> final paper-ready audit
```

最终输出应允许作者不再回到散落的 `.tmp` 目录查数字，也不需要人工猜测某个 speedup 属于 top-K、完整输出、fallback 还是 long-query boundary。

### 2.2 当前建议文章定位

工作定位固定为：

```text
A contract-aware GPU acceleration path for short-query top-K prediction in
Fasim-LongTarget, with a systematic characterization of its operating envelope.
```

中文工作表述：

```text
面向 Fasim-LongTarget 短 query top-K 工作负载的合同感知 GPU 加速路径，
以及其正确性、资源边界和长 query 架构限制的系统刻画。
```

### 2.3 非目标

本轮不做：

- 通用 full-output GASAL2 replacement。
- MALAT1、NEAT1、KCNQ1OT1 全长产品加速。
- 新的 persistent target engine。
- multi-segment microbatch 重设计。
- 固定 traceback threshold 或 rank-unsafe pruning。
- 为了图表好看而改变 runtime preset。
- 生物学准确率优于所有 triplex 工具的声明，除非另有独立 biological benchmark。
- 正式论文正文、投稿系统、作者排序或 journal-specific 排版。

---

## 3. 论文 claim ledger

Phase 0 必须把下列 claim ID 写入 `paper/claim_evidence.tsv`。后续数字可以更新，但 claim 边界不得悄悄扩大。

### C1 — 短 query fast top-K 加速

允许表述：

```text
在已验证的短 query、normal-triplex、fast top-K 合同和指定硬件范围内，
GASAL2 路径显著减少 wall time，同时保持三种 clustered TFO1–5 一致。
```

当前起点证据：`chr21+chr22` 特定 2-GPU scope 约 `40.119x`。

必须同时报告：

```text
query length
input target scope
GPU count
worker density
baseline output contract
candidate output contract
score/stability/Nt top5 equality
fallback counters
paired repeat count
median paired speedup and interval
```

禁止表述：

```text
40x faster for LongTarget in general
full-output replacement
all lncRNAs are accelerated
```

### C2 — 非 H19 泛化

允许表述：

```text
实现没有 H19 序列特调；在预注册的多个非 H19 短 query 工作负载中，
一部分或多数 contract-clean workload 获得加速。
```

必须保留所有 mismatch rows。禁止写成“所有短 query 均保证 clean”。

### C3 — 合同感知正确性和 fail-closed 行为

必须覆盖：

```text
score-ranked clustered TFO1-5
stability-ranked clustered TFO1-5
Nt-ranked clustered TFO1-5
boundary ties
fallback / guard / overflow / OOM counters
```

仅在完整输出 workload 上才允许声明 row-set equality；top-K equality 不等于完整 TFOsorted equality。

### C4 — two-slot overlap

允许表述：

```text
在一张 GPU 一个 worker 的支持密度下，two-slot CPU/GPU overlap 可进一步降低 wall time。
```

必须与相同 preset 的 synchronous baseline 成对比较。不得外推到一张 24 GB GPU 多 worker。

### C5 — archive-first 存储和 merge 内存

允许表述：

```text
archive-first 对 segmented 输出提供无损恢复、显著存储缩减和 bounded-memory exact merge。
```

必须分开报告 storage ratio、merge RSS 和完整 run+merge wall。不得把存储缩减记为 compute speedup。

### C6 — exact-column 组件级优化

允许表述：

```text
legacy-minScore + GPU pruned scoreInfo 可降低 exact-column stage 时间，
但 stage speedup 不等于同幅度端到端 speedup。
```

必须报告 stage share、stage timing、end-to-end timing 和未变化的 request/task/cell 数。

### C7 — operating envelope 与长 query 限制

允许表述：

```text
强收益集中在短 query top-K；完整输出接近 parity，当前 segmented long-query
架构在 bounded max8 上仅约 1.089x，未达到 promotion gate。
```

必须明确：

```text
full 121-segment candidate = not run
full hg38 = not run
persistent target / ownership / traceback certificate = no-go under current contract
```

负结果是文章的一部分，不得在图表或摘要素材中删除。

---

## 4. 全局实验与数据合同

### 4.1 Runtime 冻结

默认论文 runtime：

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
```

允许新增：

- benchmark wrappers；
- environment capture；
- log parsers；
- source-data generators；
- figure/table scripts；
- check scripts；
- 仅影响 telemetry 且经过验证的 instrumentation。

如果修改会改变 candidate、timing path、allocation、synchronization、sort、dedup、cluster、fallback 或输出：

1. 停止当前 phase；
2. 增加 `paper_runtime_epoch`；
3. 记录新 runtime commit；
4. 在 `paper/runtime_epoch_log.tsv` 解释变化；
5. 重新运行所有受影响 workload；
6. 禁止把不同 epoch 的运行合并成同一统计样本。

### 4.2 输出合同

每个 workload 必须声明以下一种：

```text
full_tfosorted_rowset
fast_topk_score_stability_nt
shifted_grid_bounded_full_rows
archive_restore_only
preflight_guard_only
```

性能比较的 baseline/candidate contract 必须相同。若 Fasim baseline 生成完整输出后再提取 top-K，必须把 baseline 的工作量定义和计时边界写清楚；不得称其为通用 full-output speedup。

### 4.3 正确性 gate

fast top-K clean run：

```text
score_top5_equal = 1
stability_top5_equal = 1
nt_top5_equal = 1
fallbacks = 0
length_guard_fallbacks = 0
runtime_batch_fallbacks = 0, when applicable
overflow_fallbacks = 0, when applicable
OOM = 0
```

完整输出 clean run：

```text
missing_rows = 0
extra_rows = 0
row_count_equal = 1
byte_equal = 1, only when deterministic byte equality is the declared contract
```

任何一项不满足都必须作为 mismatch/fallback row 保留，不能作为 clean GPU replicate 合并。

### 4.4 重复与运行顺序

主性能 claim 使用 **paired repeats**。每个 pair 在同一 machine state、input、binary、affinity 和 preset 下执行 baseline/candidate。

默认：

```text
short core claim:       >= 5 valid pairs
short generalization:   >= 3 valid pairs for preregistered core rows
long max8 bounded:      >= 3 valid pairs total
component ablation:     >= 3 valid pairs
expensive descriptive:  >= 1 valid run per mode; no inferential CI claim
```

运行顺序使用固定 seed 的平衡随机或 ABBA 设计，不能先跑完全部 baseline 再跑全部 candidate。每种 binary/mode 至少一次不计时 warm-up。

### 4.5 排除规则

只有以下预先声明的技术失败可从性能统计中排除：

```text
binary/input/config digest mismatch
machine reboot or driver reset during run
external process consumed configured GPU/CPU resource
runner timeout caused by infrastructure failure
corrupted or incomplete log
correctness comparator could not execute
```

以下情况不能静默排除：

```text
slow run
fallback
mismatch
OOM caused by tested preset
unexpectedly low speedup
```

所有排除写入 `paper/source_data/exclusions.tsv`，包括 run ID、原因、证据路径和是否重跑。

### 4.6 统计合同

主效应量：

```text
paired_speedup_i = baseline_wall_i / candidate_wall_i
primary summary = median(paired_speedup_i)
```

同时报告：

```text
n valid pairs
median baseline wall
median candidate wall
median paired speedup
IQR
min/max
bootstrap 95% CI of median paired speedup, when n >= 3
```

固定 bootstrap seed，默认 `20260715`，至少 `10000` 次重采样。不得把 segment、CUDA batch 或 chromosome window 当作独立生物/系统 replicate。

不要求 p-value。若新增显著性检验，必须在运行前写入 protocol，不能看完结果后选择检验。

### 4.7 Artifact 合同

大 raw artifacts 默认保存在未跟踪目录：

```text
.paper-artifacts/<data_freeze_id>/
```

Git 中只提交：

```text
artifact manifest
relative or external location
size
sha256
producer command
runtime commit
input digests
config digest
created_at
source classification
```

source classification 只允许：

```text
reproduced_current_epoch
reused_digest_verified
committed_historical_artifact
user_provided_external_result
unavailable
```

### 4.8 资源和时间上限

- 一张 24 GB GPU 默认一个 GASAL2 worker。
- 不为论文准备主动复现已知会 OOM 的多 worker 配置；可以复用已有证据。
- short workload 单次 hard timeout 由 Phase 1 manifest 明确，默认不超过 30 分钟。
- max8 单 mode hard timeout 默认不超过 45 分钟。
- 禁止完整 121-segment 和 full hg38 long-query run。
- 超过上限的 descriptive workload 使用已有 digest-verified artifact，或标记为限制；不能无限延长本轮准备。

---

## 5. 目录和机器可读文件约定

Phase 0 建立：

```text
paper/
  README.md
  scope_and_claims.md
  claim_evidence.tsv
  artifact_inventory.tsv
  gap_register.tsv
  runtime_epoch_log.tsv
  benchmark_protocol.md
  workload_manifest.tsv
  source_data/
  figures/
  tables/
  supplementary/
  captions.md
  outline.md
  methods_notes.md
  results_claims.md
  limitations.md
  related_work_inventory.tsv
  references.bib
  PAPER_PREP_STATUS.md

reproduce/
  README.md
  environment.md
  input_manifest.tsv
  expected_checksums.tsv
  benchmark_commands.sh
  collect_results.py
  analyze_results.py
  render_figures.py
  check_reproduction.sh
```

如果仓库已有等价目录或命名，优先复用；在 `paper/README.md` 记录映射，不创建重复体系。

TSV 要求：

- UTF-8；
- 首行 header；
- 无合并单元格；
- 数值字段不带单位字符串，单位写入列名；
- 缺失写空值或 `NA`，不能用 `0` 代替 unavailable；
- stable sort；
- 生成脚本可重复执行并产生相同内容。

---

# Phase 0 — 论文范围、claim 和证据库存冻结

## 目标

把已完成的工程结果转换为论文可审计的 claim/evidence ledger。本 phase 不运行重型 benchmark，不修改 runtime。

## 必做

1. 核对 checkout：

```bash
git rev-parse HEAD
git branch --show-current
git status --short
git merge-base --is-ancestor 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f HEAD
```

2. 运行现有最终 gate：

```bash
make check-fasim-gasal2-long-query-final
```

3. 阅读并纳入 inventory：

```text
docs/fasim_gasal2_long_query_final_decision.md
docs/fasim_gasal2_long_query_architecture_baseline.md
docs/fasim_gasal2_workload_matrix.tsv
docs/fasim_gasal2_short_query_generalization_panel.md
docs/fasim_gasal2_top5_recommended_runtime.md
docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md
docs/fasim_gasal2_segmented_archive_first.md
```

如路径变化，记录实际替代文件。

4. 创建 `paper/scope_and_claims.md`：

- 固定文章定位；
- 列出 C1–C7；
- 对每项写允许表述、禁止表述和输出合同；
- 明确当前 runtime 支持范围与 long-query no-go；
- 不写摘要式夸张结论。

5. 创建 `paper/claim_evidence.tsv`，至少包含：

```text
claim_id
claim_text_short
contract
workload_ids
required_repeats
correctness_gate
primary_metric
current_evidence_path
current_source_class
current_n
current_value
gap
status
```

6. 创建 `paper/artifact_inventory.tsv`：扫描现有 docs 中引用的 artifact、summary、TSV、JSON、binary/input digest。不得假设 `.tmp` 路径仍存在。

7. 创建 `paper/gap_register.tsv`，至少列出：

```text
core repeat gaps
generalization target-diversity gap
raw artifact availability
input FASTA provenance
second GPU platform availability
citation metadata gaps
container/reproduction gaps
```

8. 创建 Phase 0 checker，例如：

```text
scripts/check_fasim_gasal2_paper_phase0.sh
make check-fasim-gasal2-paper-phase0
```

checker 必须验证 ledger schema、C1–C7 均有行、baseline commit、final no-go 文档存在、没有把 long-query 写成 promoted。

## 硬 gate

```text
baseline commit is ancestor = 1
existing final check passes = 1
C1-C7 present in claim ledger = 1
every current number has evidence path and source class = 1
unsupported universal claim count = 0
long-query no-go preserved = 1
runtime code changes = 0
```

## blocked 条件

- `0d11aa2...` 不是当前历史祖先且无法解释分支来源；
- 现有 final check 失败；
- 核心 40.119x、12.57x、1.089x 等数字找不到任何 artifact 或文档 provenance。

## 完成产物

```text
paper/README.md
paper/scope_and_claims.md
paper/claim_evidence.tsv
paper/artifact_inventory.tsv
paper/gap_register.tsv
paper/runtime_epoch_log.tsv
phase 0 checker / Make target
goal.md status update
```

建议 commit：

```text
docs: freeze GASAL2-LongTarget paper scope and evidence ledger
```

---

# Phase 1 — Benchmark protocol、预注册 manifest 和运行 harness

## 目标

在补任何数据前冻结 workload、重复数、计时边界、正确性 gate、排除规则和运行顺序，并建立可断点续跑、digest-aware 的统一 harness。

## 必做

### 1. Protocol

创建 `paper/benchmark_protocol.md`，至少记录：

```text
runtime commit / epoch
build commands
compiler and CUDA/GASAL2 configuration
machine capture commands
CPU/GPU affinity
warm-up policy
paired ordering policy and seed
wall-time boundary
stage telemetry fields
correctness comparators
fallback rules
repeat counts
exclusion rules
timeouts
raw artifact location
data freeze procedure
```

### 2. Workload manifest

创建 `paper/workload_manifest.tsv`，每行至少包含：

```text
workload_id
claim_id
family
role                       # core | generalization_core | breadth | negative_control | descriptive
query_id
query_path
query_sha256
query_start_nt
query_end_nt
query_length_nt
fragment_position          # full | 5p | mid | 3p
target_id
target_path
target_sha256
target_region
rule
baseline_mode
candidate_mode
output_contract
required_pairs
requires_gpu_count
max_wall_seconds
preset_id
preregistered
```

### 3. 预注册 generalization 设计

在运行前固定：

```text
supported rows >= 12
lncRNA identities >= 4
non-H19 identities >= 3
query lengths include 1024, 2048 and 2812 where source length permits
fragment positions include 5p, mid and 3p
target regions >= 3
chromosomes >= 3 when inputs are available; otherwise >= 2 plus declared limitation
one fixed GASAL2 preset for all supported rows
```

设计分两层：

- `generalization_core`：至少 9 个预注册 supported rows，每行 3 paired repeats；
- `breadth`：其余预注册 rows 至少 1 paired run，作为 descriptive breadth，不计算 bootstrap CI；
- full MALAT1、NEAT1、KCNQ1OT1：只做 preflight guard negative controls，不执行已知 CPU fallback 重跑。

选择 query/target 的算法或规则写入 protocol。不得依据结果更换 5p/mid/3p 片段或 target region。

### 4. Harness

新增或复用统一 runner，建议：

```text
scripts/run_fasim_gasal2_paper_benchmarks.sh
scripts/capture_fasim_gasal2_paper_environment.py
scripts/collect_fasim_gasal2_paper_run.py
```

要求：

- 支持 `--dry-run`；
- 支持 `--workload-id`、`--pair-id`、`--mode`；
- 每次运行记录 input/binary/config digest；
- 原子写 receipt；
- config drift fail closed；
- resume 只复用 digest 完全一致的完成运行；
- 保存 stdout/stderr、summary、correctness report、`/usr/bin/time -v`、GPU memory sample；
- 记录 run order 和 warm-up；
- 不在解析失败时返回成功；
- 不覆盖已有 run ID。

推荐 run ID：

```text
<workload_id>__pairNN__<baseline|candidate>__<runtime_epoch>
```

### 5. Harness tests

至少包含：

- dry-run manifest expansion；
- duplicate run ID fail；
- digest mismatch fail；
- incomplete receipt 不可 resume；
- parser 对缺失字段 fail；
- paired order 可由 seed 重建；
- GPU 不可用时给出明确 blocked reason，不伪造零值。

### 6. Phase checker

新增：

```text
make check-fasim-gasal2-paper-phase1
```

## 硬 gate

```text
protocol frozen before real runs = 1
all manifest rows preregistered = 1
core and breadth roles explicit = 1
all output contracts explicit = 1
paired order reproducible = 1
receipts digest-aware and atomic = 1
resume fails closed = 1
dry-run covers every workload = 1
runtime behavior change = 0
```

## blocked 条件

- 核心 query 或 target FASTA 缺失且无合法来源；
- 无法确定历史 benchmark 的 binary/input/config digest；
- runner 不能区分 baseline/candidate 计时边界。

## 完成产物

```text
paper/benchmark_protocol.md
paper/workload_manifest.tsv
paper/input provenance entries
benchmark harness and tests
phase 1 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: preregister paper workloads and add digest-aware harness
```

---

# Phase 2 — 核心重复 benchmark

## 目标

为主性能 claim 补齐 paired repeats、完整正确性和机器状态记录。优先复用 digest-compatible 的已有 raw runs；只补缺失 pair。

## 必做 workload

### 2.1 C1：H19 / chr21+chr22 fast top-K

```text
valid paired repeats >= 5
same top-K contract for baseline and candidate
score/stability/Nt top5 clean for every candidate run
fallbacks = 0
GPU count and worker placement recorded
```

历史 `40.119x` 仅作为起点。论文数字必须由本 phase 数据重新计算；若新 median 不同，使用新冻结值并解释 historical difference。

### 2.2 C4：two-slot overlap

至少：

```text
chr21: synchronous vs two-slot, valid pairs >= 5
chr22: synchronous vs two-slot, valid pairs >= 5
one worker per GPU
same binary/preset/output contract
```

每个 pair 同时记录 wall、stage timings、peak GPU memory、fallback 和 top-K correctness。

### 2.3 C7：KCNQ1OT1 bounded max8

```text
baseline vs safe candidate
valid pairs >= 3 total
existing two repeats may count only when digests and runtime epoch match
full merged output byte/row equality per declared shifted-grid contract
three top5 contracts clean
fallback/OOM = 0
```

只补到 3 pairs，不扩展到 full 121 segments。

### 2.4 Expensive descriptive operating-envelope rows

至少保留或核实：

```text
chr22 full output
chr1 full output
MALAT1 experimental/broad path
NEAT1 guarded boundary
H19 short integrated control
```

这些 workload 如果单 mode 超过 protocol 的成本上限，可使用 `committed_historical_artifact` 或 `reused_digest_verified`，但必须报告 `n` 和 source class；不得为它们声称新 bootstrap CI。

## 运行要求

- 每个 pair 前执行 protocol 定义的 warm-up；
- baseline/candidate 顺序平衡；
- 每次运行后立即执行 correctness comparator；
- mismatch/fallback 不得自动重跑直到 clean；若重跑，旧 run 保留并进入 exclusions/mismatch 表；
- 采集 GPU 温度、功耗/时钟（可用时）、device memory、host RSS、CPU governor；不可用写 `NA`；
- 不手工抄 timing。

## 证据文档

创建：

```text
paper/core_benchmark_report.md
```

内容只引用机器可读 run table，并明确：

```text
valid pairs
invalid/excluded runs
median/IQR/range
correctness status
fallback status
runtime epoch
artifact root and digest manifest
```

此 phase 可以先给 descriptive summary；最终 bootstrap CI 在 Phase 5 统一生成。

## 硬 gate

```text
C1 valid pairs >= 5
chr21 two-slot valid pairs >= 5
chr22 two-slot valid pairs >= 5
max8 valid pairs >= 3
all clean runs satisfy declared correctness contract = 1
all raw runs have receipts and digests = 1
all failures remain in run inventory = 1
full 121-segment run count = 0
runtime epoch mixing = 0
```

## blocked 条件

- 少于要求 GPU 数且无法复现 C1 的原始硬件 scope；
- max8 输入不可用且历史 repeats 无 digest；
- 硬件不稳定导致无法形成最少 valid pairs。

## 完成产物

```text
immutable raw run tree
updated artifact inventory
paper/core_benchmark_report.md
phase 2 run manifest and receipts
phase 2 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: collect paired paper benchmarks for core GASAL2 claims
```

---

# Phase 3 — 预注册 short-query 泛化与 negative controls

## 目标

验证加速路径不是 H19 特调，并把 clean、mismatch、guard 和 fallback 都纳入统一结果，而不是只展示成功点。

## 必做

1. 严格使用 Phase 1 已冻结 manifest；不得删除、替换或新增结果导向的 workload。
2. `generalization_core` 每行至少 3 valid pairs。
3. `breadth` 每行至少 1 valid pair。
4. 所有 supported rows 使用同一个 preset；任何 per-query 特调都必须导致 phase fail。
5. full MALAT1、NEAT1、KCNQ1OT1 运行 preflight guard，确认：

```text
supported = 0
reason = query_length_contract
GPU fast path not executed
```

6. 对每一行记录：

```text
query identity
fragment position
query length
target region
baseline/candidate wall
paired speedup
score/stability/Nt equality
fallback/guard
request counts
peak device memory
status = clean | mismatch | fallback | guarded | failed
```

7. 任何 mismatch 必须保存最小 diff artifact，至少含 top5 keys、rank、cluster/representative 信息和 comparator 输出。
8. 生成：

```text
paper/generalization_report.md
paper/source_data/generalization_runs_pre_freeze.tsv
```

## 预注册 claim decision

实验完成后只能选择：

```text
generalization_supported
generalization_scoped_with_mismatches
generalization_no_go
```

推荐判据：

### `generalization_supported`

```text
>= 75% preregistered supported rows are clean
at least one clean non-H19 row for each included non-H19 identity
at least one clean row in every target region
no query-specific preset
```

### `generalization_scoped_with_mismatches`

存在多个非 H19 clean rows，但未满足上面 breadth gate。文章必须明确 eligibility 需逐 workload 检查。

### `generalization_no_go`

没有足够非 H19 clean evidence。保留 C1 H19 scoped 文章路线，不得包装成泛化成功。

phase 是否完成取决于数据是否完整，而不是 decision 是否 positive。

## 硬 gate

```text
all preregistered rows appear in output = 1
no post-result workload deletion = 1
all core rows meet repeat count = 1
all breadth rows have at least one run = 1
all negative controls recorded = 1
all mismatch artifacts preserved = 1
one preset across supported rows = 1
```

## blocked 条件

- 非 H19 query 输入来源或 digest 无法确认；
- 目标基因组切片无法从合法输入重建；
- manifest 在运行前未冻结且无法证明没有结果导向修改。

## 完成产物

```text
paper/generalization_report.md
generalization raw receipts and mismatch artifacts
machine-readable pre-freeze table
claim decision recorded in claim_evidence.tsv
phase 3 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: complete preregistered short-query generalization panel
```

---

# Phase 4 — 消融、资源和 archive-first characterization

## 目标

说明 speedup 来自哪些组件，并把 wall、stage、显存、RSS、request、fallback 和存储收益分开报告。

## 重要限制

- 只测试仓库已经存在、可由文档和 check 支持的开关组合。
- 不为了消融构造未验证的新 runtime 组合。
- 不重新启用固定 traceback threshold、unsafe rank pruning 或 multi-worker/GPU。

## 必做实验

### 4.1 Fast top-K 路径消融

在至少一个代表性 H19 short workload 上比较：

```text
A. Fasim authority baseline
B. checked GASAL2 fast top-K preset, synchronous
C. checked GASAL2 fast top-K preset, two-slot
```

如仓库有独立、已验证的 staged-prune / scoreInfo toggle，可增加 D/E；不存在安全 toggle 时，不得发明伪消融。

每个可比较配置至少 3 valid paired runs，并运行三种 top5 gate。

### 4.2 Exact-column 组件

在现有 Phase 5 safe scope 上比较：

```text
legacy exact-column baseline
legacy-minScore + GPU pruned scoreInfo candidate
```

报告：

```text
exact-stage median wall
stage reduction
end-to-end wall
stage share
exact tasks
exact cells
GASAL2 requests
traceback requests
fallback/overflow
```

至少 3 compatible pairs；已有 max8 pairs 可复用。

### 4.3 Archive-first

比较 legacy text 与 archive-first：

```text
restored/merged correctness
archive bytes
legacy text bytes
storage reduction ratio
merge wall
restore wall
peak host RSS
dedup DB bytes
run + merge wall
```

- 小 fixture 要求 byte-identical；
- 代表性大 synthetic 或 real subset 至少 3 merge repetitions用于 timing/RSS；
- storage ratio 是确定性描述，不需要伪造统计显著性；
- 不把 archive reduction 计入 GPU compute speedup。

### 4.4 Resource boundary

至少记录：

```text
single-worker peak device memory
reserved headroom
host RSS
pinned memory, when measurable
one-worker-per-GPU recommendation
existing multi-worker OOM evidence path
```

不要为了论文主动重跑已知 OOM stress。复用已有 artifact并标记 source class。

## 证据文档

```text
paper/ablation_resource_report.md
```

## 硬 gate

```text
all compared configurations have same declared output contract = 1
all candidate runs correctness-clean or explicitly labeled mismatch = 1
stage and end-to-end timing both reported = 1
archive restore exactness reported = 1
storage benefit not counted as compute speedup = 1
resource numbers include measurement method = 1
unsafe runtime flags enabled = 0
```

## no_go 条件

- 某个预注册 ablation toggle 不存在安全、可比较的实现：记录为 `not_available_under_checked_contract`，不构造新 runtime；该子项 `no_go`，phase 可继续。
- two-slot 或 exact-column 在重复实验中无稳定收益：保留结果并缩小 claim。

## 完成产物

```text
paper/ablation_resource_report.md
ablation/resource/archive raw artifacts and receipts
updated claim ledger
phase 4 checker / Make target
goal.md status update
```

建议 commit：

```text
bench: add paper ablation, resource and archive characterization
```

---

# Phase 5 — 统计分析和 source-data 冻结

## 目标

把 Phase 2–4 的 raw artifacts 转换为唯一、可重建、机器可读的论文 source data；冻结所有主数字。

## 必做

### 5.1 Collector

新增或完善：

```text
reproduce/collect_results.py
```

它必须从 receipts、summaries、comparators 和 manifests 读取，不允许把文档中的数字当 source of truth。

生成至少：

```text
paper/source_data/benchmark_runs.tsv
paper/source_data/paired_speedups.tsv
paper/source_data/correctness.tsv
paper/source_data/generalization.tsv
paper/source_data/ablation.tsv
paper/source_data/resources.tsv
paper/source_data/archive_first.tsv
paper/source_data/operating_envelope.tsv
paper/source_data/exclusions.tsv
paper/source_data/source_data_manifest.tsv
```

### 5.2 必要字段

`benchmark_runs.tsv` 至少包含：

```text
data_freeze_id
runtime_epoch
runtime_commit
machine_id
workload_id
claim_id
pair_id
run_id
mode
role
output_contract
wall_seconds
stage_seconds fields
peak_gpu_memory_bytes
peak_rss_kb
gasal2_requests
traceback_requests
fallback counters
correctness booleans
status
excluded
exclusion_reason
artifact_sha256
```

### 5.3 Analyzer

新增：

```text
reproduce/analyze_results.py
```

要求：

- 从 pair ID 计算 paired speedup；
- 校验 baseline/candidate 的 workload、epoch、input、preset 和 contract 一致；
- 生成 median、IQR、range、bootstrap 95% CI；
- 固定 seed 和 resample count；
- 对 `n < 3` 不生成误导性 CI；
- 同时输出 TSV 和 JSON；
- 任何手工 override 必须 fail；
- 检查重复 run ID、重复 pair、单位错误、负时间、speedup 算术错误。

### 5.4 Data freeze

生成：

```text
paper/source_data/DATA_FREEZE.md
```

并设置：

```text
data_freeze_id = paper-data-v1-<short_commit>-<YYYYMMDD>
```

`DATA_FREEZE.md` 包含：

```text
runtime commit/epoch
artifact manifest digest
workload manifest digest
collector version/commit
analysis seed
all source-data file digests
known limitations
```

冻结后修改 raw inclusion、runtime 或 workload manifest 必须生成新的 freeze ID，不能覆盖 v1。

### 5.5 Claim ledger 回填

C1–C7 每项写入最终：

```text
n
point estimate
interval or descriptive range
correctness status
source-data row/filter
allowed manuscript wording
```

## 硬 gate

```text
all figures/tables can use source_data only = 1
manual numeric constants in analysis = 0
all paired comparisons contract-compatible = 1
all exclusions explicit = 1
all source-data rows trace to artifact digest = 1
bootstrap reproducible = 1
speedup arithmetic independently checked = 1
data_freeze_id set = 1
```

## blocked 条件

- 主 claim 的 raw artifact 或 receipt 缺失，无法从文档数字重建；
- pair 无法正确匹配；
- runtime epoch 混用且无法拆分。

## 完成产物

```text
frozen paper/source_data/*
collector and analyzer with tests
DATA_FREEZE.md
updated claim_evidence.tsv
data_freeze_id in goal.md
phase 5 checker / Make target
goal.md status update
```

建议 commit：

```text
analysis: freeze GASAL2-LongTarget paper source data
```

---

# Phase 6 — 论文图、表和 captions

## 目标

从冻结 source data 生成出版级矢量图、600 DPI PNG、机器可读表和准确图注。不得人工编辑数字或用低分辨率位图放大冒充矢量输出。

## 通用视觉合同

- 白色背景、无渐变、无阴影、无 3D GPU 图标；
- 色盲友好配色；
- Fasim 使用橙色系，GASAL2 使用蓝色系，共享路径灰色；
- 颜色之外同时使用形状/线型编码；
- 主文最小文字建议不低于 7.5 pt；
- 输出 SVG、PDF、PNG；
- PNG 必须从矢量或原始绘图脚本直接导出，600 DPI metadata 正确；
- 不得把 1536×1024 位图简单上采样作为最终论文图；
- 所有 panel label、轴、单位和 legend 可由脚本重建；
- 每个 figure 有 source-data mapping 和生成命令。

## Figure 1 — 方法与 fast top-K 计算差异

必须程序化重绘，布局固定：

```text
A  全宽：shared LongTarget task construction and downstream semantics
B1 左：Fasim-LongTarget peak-guided candidate reduction + CPU alignment
B2 右：GASAL2-LongTarget fast top-K only
C  左：conceptual computational pattern
D  右：measured fast top-K speedup only
```

版式要求：

- A 独占第一行；
- B1 与 B2 同高、同宽；
- C 与 D 同高、同宽；
- B1 的左右边界与 C 完全对齐；
- B2 的左右边界与 D 完全对齐；
- B2 不画 equivalence bridge，只画 fast top-K；
- D 只放 fast top-K 数据，不混入 full-output 或 long-query broad-path 点；
- 文字显著少于旧草图，以关键词和图形为主；
- 方法图不得使用生成式图像。

推荐文件：

```text
paper/figures/fig1_method_fast_topk.svg
paper/figures/fig1_method_fast_topk.pdf
paper/figures/fig1_method_fast_topk_600dpi.png
```

## Figure 2 — 核心性能和泛化

至少包含：

- C1 paired speedup distribution / points；
- non-H19 generalization core 的 paired speedup；
- clean、mismatch、guard 使用不同符号；
- 每个 workload 显示 `n`；
- 不只画 median bar；优先显示原始 paired points + interval。

## Figure 3 — 消融和资源

至少包含：

- synchronous vs two-slot；
- exact-column stage 与 end-to-end；
- peak GPU memory / host RSS；
- request/traceback 数量在 relevant ablation 中是否变化。

## Figure 4 或 Supplementary Figure — Operating envelope

包含：

```text
fast top-K
full output
long-query boundary/experimental
bounded KCNQ1OT1 max8
```

必须通过形状和注释区分 output contracts。`1x` parity line 明确；negative/no-go 点保留。

## Archive-first supplementary figure

展示：

```text
text vs archive bytes
peak RSS
restore/merge correctness
run+merge wall
```

## Tables

至少生成：

```text
Table 1: workload, contract, hardware and repeat scope
Table 2: primary performance statistics
Table 3: correctness/generalization outcomes
Table 4: ablation, memory and storage
Supplementary table: operating-envelope and no-go evidence
```

表格源必须是 TSV；Markdown/LaTeX 由脚本生成。

## Captions

创建 `paper/captions.md`。每个 caption 必须说明：

```text
what is compared
output contract
n and summary statistic
error interval meaning
hardware scope
fallback/mismatch encoding
source-data file
```

禁止在 caption 中写未由 source data 支持的 universal claim。

## 生成和检查

新增：

```text
reproduce/render_figures.py
make paper-figures
make check-fasim-gasal2-paper-phase6
```

checker 至少验证：

- SVG/PDF/PNG 均存在；
- PNG pixel size 和 600 DPI metadata；
- 图中引用的 workload ID 均存在于 source data；
- 无 NaN/inf；
- 表中 speedup 与 analyzer 一致；
- Figure 1 panel bounding boxes 对齐；
- B2 标题/内容只包含 fast top-K；
- D 数据过滤为 fast top-K contract；
- render 两次 checksum 一致，或只允许明确记录的 metadata 差异。

## 硬 gate

```text
all main figures generated from scripts = 1
all numeric panels generated from frozen source data = 1
vector outputs exist = 1
600 DPI direct exports exist = 1
Figure 1 panel alignment checks pass = 1
no generated raster schematic = 1
captions include contract and n = 1
manual post-edit required = 0
```

## 完成产物

```text
paper/figures/*
paper/tables/*
paper/supplementary/*
paper/captions.md
render scripts and tests
phase 6 checker / Make target
goal.md status update
```

建议 commit：

```text
figures: generate paper-ready GASAL2-LongTarget figures and tables
```

---

# Phase 7 — 复现包和 clean-checkout 验证

## 目标

让第三方能够从固定 commit、输入 manifest 和 source data 重建检查、统计、表格和图；GPU 原始 benchmark 的成本和外部输入限制必须诚实记录。

## 必做

### 7.1 Environment

创建 `reproduce/environment.md`，记录：

```text
OS/kernel
CPU
RAM
GPU model/count/memory
NVIDIA driver
CUDA toolkit/runtime
compiler
Python
GASAL2 compile constants
CPU governor/affinity
GPU persistence/clocks when controlled
```

机器自动采集输出存入 manifest；手工说明与自动输出分开。

### 7.2 Input manifest

`reproduce/input_manifest.tsv` 至少包含：

```text
input_id
kind
source/license
path convention
size
sha256
required_for
tracked_or_external
reconstruction command
```

不得把无法公开分发的 FASTA 悄悄加入仓库。可公开下载的输入记录权威 URL 和 checksum；不可自动下载的输入写清准备步骤。

### 7.3 Reproduction commands

至少提供：

```text
reproduce/benchmark_commands.sh
reproduce/collect_results.py
reproduce/analyze_results.py
reproduce/render_figures.py
reproduce/check_reproduction.sh
```

分层命令：

```text
quick checks           # no expensive GPU benchmark
source-data rebuild    # from available raw artifacts
figure/table rebuild   # from frozen source data
core GPU reproduction # explicit hardware and time requirements
max8 reproduction      # explicit bounded long-query command
```

### 7.4 Build/container definition

优先提供一个可审查的 Dockerfile 或 Apptainer definition，固定 user-space dependency；明确 NVIDIA driver 仍由 host 提供。若许可证或 CUDA base image限制无法完成，写入 gap register，不得伪造可运行 container。

### 7.5 Make targets

新增或复用：

```text
make paper-source-data
make paper-figures
make check-fasim-gasal2-paper-reproduction
make check-fasim-gasal2-paper-prep
```

最终 aggregate target 在 Phase 9 完成；此 phase 先串联 0–7。

### 7.6 Clean checkout test

使用临时 clone/worktree 或干净目录验证：

1. quick checks；
2. source-data checksum；
3. figure/table regeneration；
4. `git diff --check`；
5. 不依赖未记录的 `$HOME`、绝对路径或旧 `.tmp` 文件。

GPU benchmark 可以不在 clean-checkout test 中重跑，但其 raw artifact manifest 和命令必须完整。

### 7.7 Release checklist

创建：

```text
paper/RELEASE_CHECKLIST.md
```

包括建议 tag：

```text
gasal2-longtarget-paper-v0.1
```

但不要自动创建或 push tag。列出 GitHub release、永久归档、source-data、许可证和 citation metadata 所需步骤。

## 硬 gate

```text
quick reproduction from clean checkout passes = 1
source-data checksums reproduce = 1
figures/tables regenerate = 1
all external inputs have provenance = 1
absolute undocumented paths = 0
raw artifact manifest complete = 1
public release not automatically performed = 1
```

## blocked 条件

- 核心 source data 依赖无法访问且未归档的 `.tmp` 文件；
- 输入许可证不允许分发且无法给出合法重建流程；
- 干净 checkout 不能重建表图。

## 完成产物

```text
reproduce/*
paper/RELEASE_CHECKLIST.md
clean-checkout validation log
phase 7 checker / Make target
goal.md status update
```

建议 commit：

```text
repro: add clean-checkout paper reproduction package
```

---

# Phase 8 — Manuscript source kit、限制和文献库存

## 目标

生成作者可以直接据此写正文的结构化素材，但不代替作者完成正式论文。

## 必做

### 8.1 Outline

创建 `paper/outline.md`，建议结构：

```text
Introduction
Methods
  Fasim-LongTarget baseline
  GASAL2 fast top-K path
  output/correctness contracts
  two-slot scheduling
  archive-first merge
  benchmark and statistics
Results
  contract correctness
  short-query speedup
  non-H19 generalization
  ablation and resources
  archive-first
  operating envelope and long-query limits
Discussion
  why top-K benefits
  why full output / long query do not
  limitations
  future execution-contract redesign
Availability and reproducibility
```

每节只列 claim ID、figure/table ID 和 source-data link，不写未经作者审阅的完整叙事。

### 8.2 Methods notes

创建 `paper/methods_notes.md`，包含足够精确的信息：

```text
software commits
build flags
hardware
inputs and preprocessing
output contracts
runner configuration
paired design
correctness comparators
statistics
archive merge semantics
fallback behavior
```

不得从代码猜测未验证的默认值；每个配置引用 manifest 或 command。

### 8.3 Results claims

创建 `paper/results_claims.md`，每项使用模板：

```text
claim_id
one-sentence result
scope
n
point estimate and interval
correctness result
figure/table
source-data filter
allowed wording
forbidden extrapolation
```

所有数字必须由 Phase 5 analyzer 自动插入或验证。

### 8.4 Limitations

创建 `paper/limitations.md`，至少覆盖：

```text
single primary GPU generation, if applicable
short-query <= checked implementation boundary
fast top-K is not full-output replacement
mismatch rows in generalization
full-output near parity
bounded max8 only
full KCNQ1OT1/hg38 not run
one worker per 24 GB GPU
traceback/materialization bottleneck
no biological superiority claim
```

### 8.5 Related work inventory

创建：

```text
paper/related_work_inventory.tsv
paper/references.bib
```

至少核实：

```text
LongTarget
Fasim-LongTarget
GASAL2
3plex or closely related triplex prediction tools
recent GPU pairwise-alignment libraries relevant to score-only/one-to-many execution
```

每条至少记录：

```text
title
authors
year
venue
DOI or PMID
primary source checked
relevance
claim supported
```

只从论文、DOI/Crossref、PubMed、出版社或官方项目页核实；不得凭记忆生成 BibTeX。若网络不可用，使用仓库内 PDF/已知 DOI并把未核实项写 gap register。

### 8.6 Reporting and authorship placeholders

创建：

```text
paper/reporting_checklist.md
paper/authorship_metadata_needed.md
```

- reporting checklist 覆盖软件版本、硬件、重复、随机顺序、correctness、fallback、raw data 和代码可用性；
- 不猜作者、单位、基金和贡献；只列待作者填写字段。

### 8.7 Title candidates

可提供 3 个基于 frozen scope 的标题候选，但不得写 universal acceleration。不要生成未经作者审核的完整 abstract。

## 硬 gate

```text
outline maps every result section to claim and figure/table = 1
methods notes contain no unverified defaults = 1
all results numbers trace to source data = 1
limitations include long-query no-go = 1
all bibliography entries have verified primary metadata = 1
invented author/funding metadata = 0
full manuscript prose generated = 0
```

## blocked 条件

- 关键引用无法确认 DOI/题录；
- 核心 Methods 配置无法从 manifest/代码核实；
- source data 与 claims 文档数字不一致。

## 完成产物

```text
paper/outline.md
paper/methods_notes.md
paper/results_claims.md
paper/limitations.md
paper/related_work_inventory.tsv
paper/references.bib
paper/reporting_checklist.md
paper/authorship_metadata_needed.md
phase 8 checker / Make target
goal.md status update
```

建议 commit：

```text
docs: assemble GASAL2-LongTarget manuscript source kit
```

---

# Phase 9 — 最终 paper-preparation audit

## 目标

从干净状态验证 claim、数据、统计、图表和复现包闭环，并给出唯一的 paper-preparation decision。

## 必做

### 9.1 Aggregate checker

新增：

```text
scripts/check_fasim_gasal2_paper_prep.sh
make check-fasim-gasal2-paper-prep
```

必须串联 Phase 0–8 的轻量 checks，并额外验证：

```text
paper_runtime_epoch and commit consistent
data_freeze_id set
claim C1-C7 complete
all main claims have required repeats or explicitly descriptive role
all clean runs pass exact contract
all mismatch/fallback rows visible
all figure/table values trace to source data
all source-data rows trace to artifact digests
all figures regenerate
all 600 DPI metadata valid
all bibliography metadata verified
no full 121-segment/full hg38 run was added
long-query no-go not overwritten
no unsafe pruning recommendation
no multi-worker/24GB recommendation
no untracked small source-data files
no large raw artifact accidentally tracked
git diff --check passes
```

### 9.2 Independent arithmetic audit

增加一个独立 checker，不调用主 analyzer 的 speedup summary 函数，重新计算：

```text
paired speedups
medians
archive ratio
wall reduction
exact-stage reduction
```

与冻结表格逐项比较，防止同一代码路径自证。

### 9.3 Claim-language audit

扫描 `paper/*.md` 和 captions，禁止未经限定的模式：

```text
universally accelerates
40x faster than LongTarget
full replacement
all short queries
long-query acceleration supported
GPU traceback authority
```

允许在“forbidden wording”或引用上下文中出现，但 checker 必须可区分或使用 allowlist。

### 9.4 最终状态文档

创建 `paper/PAPER_PREP_STATUS.md`，包含：

```text
final decision
runtime commit/epoch
data freeze ID
aggregate check command
primary claims and final numbers
correctness summary
figure/table inventory
reproduction status
known limitations
remaining author-only tasks
release/tag status
```

### 9.5 最终 decision

#### `paper_preparation_ready`

要求：

```text
C1 core repeats complete
C2 generalization experiment complete
C3 correctness complete
C4 two-slot repeats complete
C5/C6 component evidence complete
C7 operating envelope complete
source data frozen
figures/tables/captions complete
clean-checkout reproduction passes
citation inventory verified
```

#### `paper_preparation_ready_with_declared_limitations`

允许缺少：

```text
second GPU architecture
public Zenodo/GitHub release
expensive descriptive reruns beyond current verified artifacts
journal-specific formatting
```

不允许缺少：

```text
C1 core repeated data
correctness gates
source-data provenance
main figures/tables
reproduction commands
long-query limitation statement
```

#### `paper_preparation_blocked_with_complete_gap_report`

用于核心 raw data、输入 provenance、repeat 或正确性缺失。必须在 `PAPER_PREP_STATUS.md` 精确列出：

```text
missing item
why it blocks
minimum command/input/hardware to unblock
which claim/figure is affected
what can still be written safely
```

### 9.6 更新状态

最终更新本文件：

```text
active_phase = complete
phase_0_status ... phase_9_status
last_completed_phase = 9
last_decision = <one valid final result>
last_evidence_doc = paper/PAPER_PREP_STATUS.md
last_test_command = make check-fasim-gasal2-paper-prep
last_commit = <actual commit subject or suggested subject>
```

## 硬 gate

```text
aggregate checker passes = 1
independent arithmetic audit passes = 1
claim-language audit passes = 1
clean checkout/source data/figures reproduce = 1
PAPER_PREP_STATUS.md complete = 1
valid final decision selected = 1
```

## 完成产物

```text
scripts/check_fasim_gasal2_paper_prep.sh
aggregate Make target
paper/PAPER_PREP_STATUS.md
final goal.md status update
clean working tree or explicit remaining diff list
```

建议 commit：

```text
docs: close GASAL2-LongTarget paper preparation
```

---

## 10. 最终 paper-ready 文件清单

Codex 在 Phase 9 必须逐项核对：

```text
[ ] paper scope and claims frozen
[ ] runtime commit/epoch frozen
[ ] workload manifest preregistered
[ ] core paired repeats complete
[ ] generalization panel complete, including mismatches
[ ] negative controls recorded
[ ] ablation/resource/archive evidence complete
[ ] raw artifacts immutable and digested
[ ] exclusions explicit
[ ] source data frozen
[ ] statistics reproducible
[ ] vector figures generated
[ ] 600 DPI PNG directly exported
[ ] tables generated from source data
[ ] captions include scope, n and contracts
[ ] reproduction package passes from clean checkout
[ ] methods notes complete
[ ] results claim map complete
[ ] limitations complete
[ ] bibliography metadata verified
[ ] author/funding placeholders not invented
[ ] long-query no-go preserved
[ ] full 121-segment and hg38 runs not performed
[ ] final aggregate check passes
[ ] PAPER_PREP_STATUS.md written
```

---

## 11. Codex 开始执行时的第一条动作

不要继续写计划。直接执行：

```text
1. 将 active_phase 改为 0 / in_progress。
2. 核对当前 HEAD 和 0d11aa2 的祖先关系。
3. 运行 make check-fasim-gasal2-long-query-final。
4. 创建 paper/claim_evidence.tsv 和 paper/artifact_inventory.tsv。
5. 完成 Phase 0 checker。
6. 通过后提交 Phase 0，并把 active_phase 更新为 1。
```

在 Phase 1 manifest 和 protocol 冻结前，禁止开始新的 benchmark。
