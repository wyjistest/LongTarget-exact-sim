# LongTarget GASAL2 长 Query 架构优化执行目标

> 用途：把本文件放到 `wyjistest/LongTarget-exact-sim` 仓库根目录，交给 Codex 逐 phase 执行。
>
> 本文件是执行入口和状态机，不是结果声明。Codex 必须实现、测试、记录证据，而不是继续生成更多计划文档。

---

## 0. Agent 指令

从 `active_phase` 指向的 phase 开始工作。每次只完成一个 phase；当前 phase 达到 `pass` 或有充分证据的 `no_go` 后，更新本文件状态，再进入下一 phase。

必须遵守：

1. 先读代码、现有测试、Makefile 和相关文档，再改代码。不要依据本文件中的行号假设源码未变化。
2. 不要只写设计或 TODO。除非 phase 明确是 telemetry/shadow gate，否则必须提交可运行实现和自动化检查。
3. 不要跳过正确性 gate 去追求 benchmark 数字。
4. 不要把 shifted-grid 一致、top5 一致或 archive 可恢复，误写成完整输出等价。
5. 不要把 `no_go` 包装成成功。达到停止条件时，保留最小安全代码、记录证据，然后进入下一条独立优化线。
6. 不要清理、覆盖或 reset 用户已有改动。只删除本 phase 自己创建的临时目录。
7. 不要默认运行耗时数小时的全量 KCNQ1OT1；只有 phase 明确允许且前置 gate 全部通过时才运行。
8. 不要自动改变现有默认运行策略。所有新路径先 `default-off`，通过最终 promotion gate 后才讨论推荐配置。
9. 每个 phase 形成一个可审查的 diff。不要把多个 phase 混在同一个大改动中。
10. 如环境支持提交，使用一个 phase 一个 commit；如不支持提交，至少保持 phase 级 diff 边界并记录建议 commit message。

### 状态值

只允许：

```text
pending
in_progress
pass
no_go
blocked
```

其中：

- `pass`：实现与所有硬 gate 通过。
- `no_go`：实现/原型和必要测量已完成，但 promotion 条件不成立；证据完整，算该 phase 已完成。
- `blocked`：缺数据、缺硬件、缺依赖或无法重现；不算完成，不得直接跳到最终成功声明。

---

## 1. 执行状态

Codex 每完成一个 phase，必须更新此块；不得提前把后续 phase 标为 `pass`。

```text
active_phase = complete

phase_0_status = pass
phase_1_status = pass
phase_2_status = no_go
phase_3_status = no_go
phase_4_status = no_go
phase_5_status = pass
phase_6_status = no_go
phase_7_status = no_go
phase_8_status = pass

last_completed_phase = 8
last_decision = long_query_architecture_no_go_with_complete_evidence
last_evidence_doc = docs/fasim_gasal2_long_query_final_decision.md
last_test_command = make check-fasim-gasal2-long-query-final
last_commit = docs: close the scoped GASAL2 long-query architecture decision
```

### Phase 依赖

```text
Phase 0
  -> Phase 1
  -> Phase 2
  -> Phase 3
  -> Phase 4
  -> Phase 5
  -> Phase 6
  -> Phase 7
  -> Phase 8
```

说明：Phase 2、4、5、6 可以得到 `no_go`，但仍可继续后续独立优化线。Phase 3 的 B=1 persistent context 是 Phase 4 的硬前置；Phase 7 的全量运行是前面所有安全 gate 的集成验证。

---

## 2. 总目标

在不破坏现有短 query 产品路径和输出合同的前提下，完成长 query / segmented-query 的下一代优化：

```text
segmented archive-first
-> segmentation completeness / ownership
-> persistent target context
-> multi-segment target reuse + memory co-design
-> exact-column task/kernel reduction
-> traceback safe certificate
-> integrated KCNQ1OT1 validation
```

最终目标不是继续微调 `stream` / `batch`，而是：

1. 避免每个 RNA segment 重复读取、转换、传输和分配同一 target。
2. 降低 overlap、exact-column 和 traceback 的重复工作量。
3. 把 segmented 输出改成 archive-first、流式恢复、精确去重，控制磁盘和 host RSS。
4. 把单 worker GPU 峰值显存压到可预测预算内，为 microbatch 提供空间。
5. 保持完整 row-set、三类 clustered top5、ties、fallback 和默认行为合同。

### 有效最终结果

Phase 8 只能选择以下一种：

```text
long_query_architecture_strong_go
long_query_architecture_scoped_go
long_query_architecture_no_go_with_complete_evidence
```

不得使用含糊的“基本完成”“看起来更快”或“目标完成”替代上述结论。

---

## 3. 当前证据与问题陈述

Phase 0 必须从当前 checkout 和可用 benchmark artifact 中重新核实；以下是起始线索，不是可以跳过复现的权威结果。

```text
短 query top5, chr21+chr22, 特定 2-GPU scope:
  speedup ~= 40.119x
  top5 clean

非 H19 short-query panel:
  clean rows median speedup ~= 12.57x

Two-slot overlap:
  chr21/chr22 single-worker wall reduction ~= 13%
  supported density = one worker per GPU

完整 TFOsorted:
  chr22 ~= 0.993x
  chr1  ~= 1.094x

长 query:
  MALAT1 ~= 1.01-1.04x
  NEAT1  ~= 0.705x

KCNQ1OT1 segmented x chr22，用户提供的较新结果:
  wall ~= 2.413 h
  GASAL2 requests ~= 2.19B
  traceback requests ~= 918M
  shifted-grid top5 overlap = 5/5
  fallback = 0
```

如果较新 KCNQ1OT1 数字未提交到仓库：

```text
source = user_provided_external_result
verified_in_current_checkout = 0
```

不得悄悄用旧的 extrapolation 替代实测，也不得把外部结果写成当前 commit 已复现。

### 已知主要问题

- `scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh` 当前按 segment 单独启动 Fasim，并查找文本 `*-TFOsorted`。
- 当前 runner 没有在 segmented 路径显式启用 `FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1`。
- `scripts/merge_fasim_segmented_tfosorted.py` 当前 manifest 依赖 `tfosorted` 字段，并把全部 `output_rows` 与 `seen` 留在内存。
- 两套 shifted grids 证明的是 bounded grid stability，不是 unsegmented full-length equivalence。
- naïve multi-segment batching 只复用固定开销，不会自动减少 GASAL2 request 或 DP cell 数。
- 当前单 worker 约占 20 GB / 24 GB，显存预算必须和 microbatch 一起设计。
- 固定 traceback threshold 已被证明会破坏部分染色体的 clustered TFO1-5 等价，不得重新启用。

---

## 4. 全局正确性与工程合同

这些合同适用于所有 phase，除非后续独立证明明确修改合同。

### 4.1 Authority 合同

```text
CPU / existing exact path authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```

任何 GPU 结果都必须由现有 authority 或等价比较器验证。不得把 GPU 自己的输出同时当 candidate 和 oracle。

### 4.2 输出合同必须分开报告

#### Contract A：完整输出

对声称完整等价的 workload，要求：

```text
missing_rows = 0
extra_rows = 0
row_count_equal = 1
```

小 fixture 在已有 deterministic 条件下还要求：

```text
byte_identical = 1
```

大 workload 如已有顺序不确定性，允许 canonical sorted row-set equality，但必须明确：

```text
compare_mode = set_or_canonical_sort
byte_identity_claimed = 0
```

#### Contract B：clustered top5

必须运行仓库现有的全部 top5 合同，不得只检查其中一个排序：

```text
score-ranked clustered TFO1-5
stability-ranked clustered TFO1-5
Nt-ranked clustered TFO1-5
```

必须保留边界 ties、cluster 语义和最终排序。只报告 overlap 数不足以替代 equality。

#### Contract C：shifted-grid stability

```text
grid_0_vs_grid_256_equal = useful evidence
unsegmented_equivalence = not implied
```

#### Contract D：archive-first

```text
archive restores claimed TFOsorted exactly
archive schema/version recorded
no full per-segment TFOsorted text emitted in archive-first fast path
```

### 4.3 Fallback 合同

任何“clean GASAL2 fast path”声明必须满足：

```text
gasal2_fallbacks = 0
length_guard_fallbacks = 0
runtime_batch_fallbacks = 0, when applicable
OOM = 0
```

如 fallback 非零，必须单独报告 fallback work 和 authority work；不得把总结果写成纯 GPU 加速。

### 4.4 性能合同

- wall time 使用相同输入、相同输出合同、相同 GPU/CPU affinity、相同 build 和相同环境变量。
- 短 benchmark 至少 3 次，报告 median；长 benchmark 可 1 次，但必须保留完整日志和分阶段 telemetry。
- 不得把 kernel microbenchmark 加速直接写成 end-to-end 加速。
- 不得把 request 数下降直接写成 wall time 下降。
- promotion 必须比较当前 phase 的直接 baseline，而不是挑选较慢历史结果。

### 4.5 资源合同

24 GB GPU 的推荐 promotion 边界：

```text
peak_device_memory <= 22 GiB
reserved_headroom >= 2 GiB
one_worker_per_gpu = default supported density
```

如果测试机器不是 24 GB，必须同时报告绝对峰值和占总显存比例，不得伪造 22 GiB gate。

Host 侧：

- 不允许把全量 merged rows 保存在 Python list。
- 不允许使用无上限的 in-memory dedup set 作为 KCNQ1OT1 production merge 唯一路径。
- 所有 queue、batch、spool、trace 和 export 必须有明确上限。

### 4.6 禁止事项

- 继续盲调 stream/batch 作为独立主线。
- 重启固定 traceback score threshold pruning。
- 用最终 CPU 输出成员身份作为 pre-traceback skip 证明。
- 只因两个 shifted grids 相同就删除第二 grid 或声称分段完备。
- 一张 24 GB GPU 默认启动两个 GASAL2 worker。
- 为了 telemetry 添加新的全局 `cudaDeviceSynchronize()`。
- 在没有 row-set gate 的情况下改变 dedup、sort、cluster、tie 或 representative-row 语义。
- 把短 query H19 top5 的 scoped 结果外推到 MALAT1、NEAT1、KCNQ1OT1 或完整输出。
- 每次实验新建一份重复 phase-plan 文档。每个 phase 最多一份主证据文档，优先更新现有文档。

---

# Phase 0 — Reproducibility、合同冻结和 baseline ledger

## 目标

建立当前 checkout 的权威起点，确认已有 gate、artifact、硬件和 workload scope。此 phase 不做运行时优化。

## 必做

1. 记录：

```bash
git rev-parse HEAD
git branch --show-current
git status --short
```

2. 记录 build/runtime 环境：

```text
compiler
CUDA version
GPU model and memory
SM arch
GASAL2_MAX_QUERY_LEN
GASAL2_N_CODE
CPU model
worker/GPU binding
```

3. 检查这些路径是否存在；如名称已变化，记录实际替代路径：

```text
scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh
scripts/merge_fasim_segmented_tfosorted.py
scripts/compare_fasim_lite_offline_cluster_topk.py
docs/fasim_gasal2_archive_first_output.md
docs/fasim_gasal2_workload_matrix.tsv
docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md
```

4. 搜索并复用现有 archive restore、row-set comparator、top5 comparator、GPU memory telemetry 和 Makefile check；不要复制实现。

5. 建立：

```text
docs/fasim_gasal2_long_query_architecture_baseline.md
```

至少包含：

```text
commit
build command
runtime env
input paths and digests
baseline artifact paths
output contract for each workload
wall / stage timings
GASAL2 requests
traceback requests
exact-column tasks/cells/kernel seconds
peak GPU memory
peak host RSS
archive/text bytes
fallback counters
source = reproduced | committed_artifact | user_provided_external_result
```

6. 对小 fixture 运行现有 smoke/exactness checks。通过 `grep`/`make help` 找到真实 target，不得凭空发明 Make target。

7. 为后续 phase 增加一个轻量总入口；命名遵循仓库现有风格，例如：

```text
make check-fasim-gasal2-long-query-phase0
```

如仓库已有等价 target，直接复用并在文档中记录，不重复新增。

## 硬 gate

```text
clean checkout build reproducible = 1
small fixture exactness clean = 1
archive-first existing smoke clean = 1
baseline inputs have digests = 1
all claims have explicit contract = 1
external/unverified metrics labeled = 1
runtime behavior change = 0
```

## 停止条件

以下任一成立则标记 `blocked`：

- 当前 checkout 无法构建既有 GASAL2/Fasim 路径。
- benchmark 依赖未跟踪的本地源码或未知 binary。
- 找不到 authority output，且无法重新生成小 fixture oracle。

## 完成产物

```text
docs/fasim_gasal2_long_query_architecture_baseline.md
phase 0 check target or reused-check manifest
goal.md status update
```

建议 commit：

```text
docs/test: freeze long-query GASAL2 architecture baseline
```

---

# Phase 1 — Segmented archive-first 与 bounded-memory merge

## 目标

让每个 RNA segment 直接生成 `.archive-first.tfoa`，merge 过程流式恢复 global query 坐标、精确过滤和去重，不生成全量 per-segment 临时文本，也不把所有 rows 留在内存。

## 设计边界

- 只改变显式 opt-in 的 segmented runner 和 merge pipeline。
- 不改变 scoring、traceback、candidate、sort、unique、filter、cluster 或默认输出语义。
- 保持 legacy text manifest 可读，以便回归和兼容。
- archive-first 原始 artifact 默认保留；清理必须是显式 opt-in 且只在 merge 成功后执行。

## 必做

### 1. Runner

修改：

```text
scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh
```

要求：

- 在 archive 路径显式设置：

```text
FASIM_OUTPUT_MODE=tfosorted
FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1
```

- 不再只用 `find '*-TFOsorted'` 判断成功。
- 检测唯一 `.archive-first.tfoa`；零个或多个都 fail closed。
- 确认 archive-first run 没有写完整 segment `TFOsorted` 文本。
- manifest 使用 typed artifact 字段。推荐：

```text
segment_id
global_start
global_end
artifact_kind        # tfosorted | archive_first_tfoa
artifact_path
```

- 兼容旧 manifest 的 `tfosorted` 字段，至少保留一个 release cycle 的读取能力。

### 2. Typed row iterator

重构：

```text
scripts/merge_fasim_segmented_tfosorted.py
```

或把通用实现放到一个可 import module，再保留原 CLI wrapper。

要求：

- `iter_text_tfosorted_rows(path)`：逐行读文本。
- `iter_archive_first_rows(path)`：复用仓库现有 archive restore schema/decoder，逐行或逐 block 产出 typed rows。
- 不要复制第二套 archive schema。
- 对 archive schema/version、reference digest 和列集合 fail closed。
- global offset 恢复至少覆盖现有：

```text
QueryStart
QueryEnd
MidPoint
Center
```

- 对缺列、非整数坐标、越界 query 范围给出可诊断错误。

### 3. Bounded-memory exact dedup

替换当前：

```text
output_rows: list[...]
seen: set[...]
```

production archive merge 必须使用精确、磁盘支持的 dedup backend，并保持“first seen row wins”的现有顺序语义。可用 SQLite/临时 KV store；不得使用有碰撞风险的短 hash 作为唯一判据。

推荐接口：

```text
--dedup-backend memory|sqlite
--dedup-db /path/to/temp.sqlite
--keep-dedup-db
```

规则：

- 小测试可以使用 `memory`。
- segmented archive runner 默认使用 `sqlite` 或等价 bounded backend。
- 输出文件边读边写，不保留完整 output list。
- SQLite/KV 事务分块提交，临时文件写在 phase workdir。
- 异常时保留可诊断状态；成功后按配置清理。

### 4. Telemetry

summary 至少增加：

```text
artifact_kind_counts
archive_input_bytes
text_input_bytes
input_rows
output_rows
duplicate_rows
filtered_rows
dedup_backend
dedup_db_bytes
merge_wall_seconds
restore_wall_seconds
dedup_wall_seconds
write_wall_seconds
peak_rss_kb
```

“不可测”必须写 unavailable，不能写 0。

### 5. Tests

增加或复用自动化检查：

1. 小 synthetic：text 与 archive 两种 manifest merge byte-identical。
2. duplicate 跨 segment，确认 first-seen 顺序不变。
3. query-min/query-max 边界测试。
4. malformed archive/schema/digest fail closed。
5. archive-first run 不产生完整 per-segment text。
6. 现有 archive-first small fixture：restored/merged 等于 legacy。
7. 至少一个较大 synthetic 流式测试，确认没有 `output_rows` 全量积累，peak RSS 受控。

## 硬 gate

```text
legacy_text_vs_archive_merged_equal = 1
missing_rows = 0
extra_rows = 0
small_fixture_byte_identical = 1
per_segment_full_text_emitted = 0
bounded_memory_backend_active = 1
fallbacks = 0
existing_default_path_unchanged = 1
```

## Promotion gate

Phase 1 是存储/内存优化，不要求显著 compute speedup。至少满足：

```text
archive_bytes < legacy_text_bytes
peak_host_rss materially below legacy in large synthetic or real subset
```

不得把 restore 时间单独忽略；报告 run + merge/restore 的完整 wall。

## no_go 条件

- 现有 archive decoder 无法安全流式复用，且第一版只能恢复全量临时文本：允许实现兼容桥，但 phase 只能标 `no_go` 或 `blocked`，不得声称 bounded streaming 已完成。
- disk-backed exact dedup 比 legacy 慢到不可用：保留正确实现和数据，标 `no_go`，Phase 2/3 仍可继续。

## 完成产物

```text
updated segmented runner
updated typed/bounded merge
parser + smoke tests
Makefile check target
docs/fasim_gasal2_segmented_archive_first.md
goal.md status update
```

建议 commit：

```text
fasim: add archive-first streaming merge for segmented queries
```

---

# Phase 2 — Segmentation completeness、core/halo ownership 与 single-grid gate

## 目标

把“两个 shifted grids 的 top5 相同”提升为可验证的分段合同；证明或否定一个 canonical grid + core/halo ownership 是否能在不丢 row 的情况下减少 overlap 重复工作。

## 重要限制

此 phase 先做 oracle 和 shadow ownership。没有证明前，不允许在 runtime 丢弃任何候选、exact task 或 traceback request。

## 必做

### 1. 明确定义 segment descriptor

manifest 增加或派生：

```text
segment_id
grid_shift
segment_start
segment_end
core_start
core_end
left_halo
right_halo
query_length
is_first_segment
is_last_segment
```

默认参数仍从当前已验证配置开始：

```text
segment_len = 2048
segment_overlap = 512
stride = 1536
```

但不得先假设 512 halo 足以覆盖所有有效 alignment；必须由测试/规则上界证明。

### 2. 建立 unsegmented authority ladder

选择当前 GASAL2 query-length 合同内、能够直接跑 unsegmented authority 的 query，并人工切成与 KCNQ1OT1 相同的 segment/overlap/shift 形状。

fixture 必须覆盖：

- alignment 完全位于 core。
- alignment 左右跨 segment 边界。
- alignment 起止正好等于 core/halo 边界。
- query 首段和尾段。
- forward/reverse strand。
- 同 score / stability / Nt 的 ties。
- 重复 cluster 和 representative-row 冲突。
- 当前允许的最大 Nt/query span 附近。
- 多个 grid shifts，不只 0/256。

### 3. 定义 ownership

ownership 必须是确定性的、可从最终 row 或安全的 pre-traceback descriptor 推导，并满足：

```text
every retained authority row has at least one eligible segment
every retained row has exactly one canonical owner after tie-break
owner decision independent of processing order
first/last segment cover query edges
```

不要凭直觉硬编码 midpoint owner。候选规则必须附证明或 exhaustive fixture 证据；如 row span 超过 halo 或描述不充分，必须回退 legacy multi-owner 路径。

### 4. Shadow only

增加 default-off shadow：

```text
FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=1
```

shadow 只记录：

```text
rows_total
rows_owned
rows_non_owner_duplicate
rows_no_owner
rows_multi_owner_before_tiebreak
rows_owner_mismatch_vs_authority
potential_exact_tasks_removed
potential_tracebacks_removed
```

不得实际 drop work。

### 5. 比较合同

至少比较：

```text
unsegmented authority vs dual-grid merged
unsegmented authority vs canonical-grid merged
unsegmented authority vs canonical-grid ownership-filtered shadow
```

每组都检查：

```text
full row-set
score top5
stability top5
Nt top5
boundary ties
```

### 6. KCNQ1OT1 bounded shadow

在 max4/max8 或等价 bounded KCNQ1OT1 workload 上运行 shadow，报告潜在工作量下降；此 workload 仍不能证明 full transcript equivalence。

## 硬 gate

runtime ownership 只有在以下全部成立时才允许进入后续 phase：

```text
short_oracle_missing_rows = 0
short_oracle_extra_rows = 0
rows_no_owner = 0
owner_is_unique = 1
all_three_top5_equal = 1
boundary_ties_equal = 1
multiple_shift_matrix_clean = 1
```

## Promotion gate

允许 production canonical-grid/ownership 的最低证据：

```text
potential_duplicate_or_work_reduction >= 20%
```

并且不能增加 fallback 或破坏输出。

## no_go 路径

若无法证明 single-grid 或 ownership：

- 标记 Phase 2 `no_go`。
- 保留 dual-grid 语义和 shadow telemetry。
- Phase 3/4 仍处理多个 segment，但不得利用 ownership drop work。
- 文档明确：`grid_stable != unsegmented_equivalent`。

## 完成产物

```text
segment descriptor/core-halo implementation
short-query segmentation oracle fixtures
ownership shadow and comparator
Makefile checks
docs/fasim_gasal2_segment_ownership.md
goal.md status update
```

建议 commit：

```text
fasim: prove segmented query ownership before work reduction
```

---

# Phase 3 — Persistent target context，B=1 等价 scaffold

## 目标

把“每个 segment 启动一个完整 process/上下文”改成一个 persistent execution context。先保持 active segment batch `B=1`，只消除重复 target setup、context creation 和 device allocation；不改变 request 集合。

## 必做

### 1. 找到真实重复边界

profile 并记录每 segment 的：

```text
target FASTA read/parse
target transform/encoding
transfer table build
target H2D bytes and time
GASAL2 context create/destroy
cudaMalloc/cudaFree count and bytes
workspace initialization
query parse/encode
```

不得在未测量的情况下声称 target setup 是主要 wall。

### 2. Persistent context

实现一个生命周期清晰的 context，至少包含：

```text
immutable target representation
host transfer tables
device-resident target buffers
GASAL2 scoring/traceback context
reusable exact-column workspace or pool
reusable host/device staging buffers
memory accounting
```

要求：

- target digest 绑定 context；输入变更必须重建。
- context 不跨 GPU 混用。
- error/fallback 后可安全销毁，不留下 stale device state。
- 不使用全局可变 singleton 破坏多进程/多 GPU 隔离。

### 3. 输入方式

优先复用仓库已有 multi-record query/manifest 能力。若现有 CLI 只能处理一个 query：

- 增加显式、可测试的 segment manifest/batch entry point。
- 不要悄悄改变 `-f2` 的既有语义。
- 保持 legacy per-process runner 作为 oracle/fallback。

### 4. Default-off scaffold

建议 env 名称；如仓库已有同义开关，复用真实名称：

```text
FASIM_GASAL2_MULTI_SEGMENT_CONTEXT=1
FASIM_GASAL2_MULTI_SEGMENT_BATCH=1
```

`B=1` 时每次只执行一个 segment，但 target/context 不重建。

### 5. Telemetry

至少增加：

```text
multi_segment_context_requested
multi_segment_context_active
segments_processed
target_reads
target_transforms
target_h2d_copies
target_h2d_bytes
context_creations
context_reuses
device_alloc_count
device_alloc_bytes
workspace_reuses
peak_device_memory_bytes
peak_host_rss_kb
per_segment_wall_seconds
total_wall_seconds
```

### 6. Tests

- 1 segment：persistent B=1 与 legacy byte/set equal。
- 2、4、8 segments：逐段输出和 merged 输出等价。
- context reuse 计数正确：N segments 只允许 1 次 target transform/context creation，除非有明确 fallback。
- 输入 digest 变化会重建 context。
- GPU error/fallback 后资源释放测试。
- 两个不同 GPU/process 不共享错误状态。

## 硬 gate

```text
full row-set equal = 1
all three top5 equal = 1
fallbacks = 0
N_segments_target_reads = 1
N_segments_target_transforms = 1
N_segments_context_creations = 1
device_memory_leak = 0
default path unchanged = 1
```

## Promotion gate

B=1 scaffold 可合并的条件是正确性和真实 reuse；不要求大幅 wall 改善。但必须满足：

```text
persistent_B1_wall <= legacy_process_per_segment_wall * 1.03
```

若 setup 占比很小且 wall 基本不变，明确记录，不夸大收益。

## no_go 条件

- B=1 仍为每段重建 target/context，说明抽象边界不成立。
- wall 回归超过 3%，且无法由新增 telemetry 开销解释。
- 生命周期导致输出漂移或 fallback。

Phase 3 `no_go` 会阻塞 Phase 4；此时直接进入 Phase 5 的独立 exact-column 优化，并在状态中记录 Phase 4 `blocked`。

## 完成产物

```text
persistent target/context implementation
B=1 runner path
resource/reuse telemetry
tests and Makefile target
docs/fasim_gasal2_multi_segment_target_reuse.md
goal.md status update
```

建议 commit：

```text
fasim: reuse target and GASAL2 context across query segments
```

---

# Phase 4 — Multi-segment microbatch 与 GPU memory co-design

## 目标

在 Phase 3 persistent context 上，让多个 RNA segments 共享同一个 target tile/representation 和 bounded buffer pool。按 `B=2`、再 `B=4` 逐级验证；显存预算和 batching 必须同一 phase 完成。

## 关键认识

```text
persistent/microbatch reuse != automatic request reduction
```

如果每个 segment 仍计算相同 target-window × query work，GASAL2 requests 和 DP cells 可能不变。必须分开报告：

```text
setup/transfer/allocation reduction
memory-traffic or launch amortization
ownership-driven work reduction, only if Phase 2 passed
```

## 必做

### 1. Memory inventory

把峰值显存按类别拆分：

```text
immutable target
score buffers
traceback buffers
exact-column workspace
query/segment descriptors
host-pinned staging
output/CIGAR staging
allocator fragmentation or reserved pool
```

### 2. Buffer pool

- 共享 immutable target。
- 可复用但不能安全并发共享的 workspace 必须有明确 slot ownership。
- traceback buffer 按 active frontier 或有界最大值分配，不按所有未来 segment 无上限预分配。
- 移除 hot loop 中重复 `cudaMalloc/free`；使用 context-owned pool。
- 记录 requested、reserved、active、peak bytes。

### 3. B=2 gate

新增显式开关；名称按现有风格调整：

```text
FASIM_GASAL2_MULTI_SEGMENT_BATCH=2
FASIM_GASAL2_MULTI_SEGMENT_MEMORY_LIMIT_MB=N
```

B=2 必须先通过完整合同，再运行性能测试。

### 4. B=4 gate

只有 B=2 同时满足正确性、无 OOM、无 fallback 且出现有效 reuse 后才允许实现/运行 B=4。

### 5. Scheduling

- 保持一 worker 一 GPU。
- segment 输出 commit 顺序必须确定。
- 一个 segment 失败时，不允许半提交其他 segment 造成不可恢复 manifest。
- partial batch 可在尾部执行。
- 当 memory estimate 不安全时 fail closed 到较小 B 或 legacy，不得 OOM 后静默重跑并掩盖计数。

### 6. 与 Phase 2 集成

- Phase 2 `pass`：允许在 shadow 验证后按 owner 过滤重复 work，并单独统计减少量。
- Phase 2 `no_go`：microbatch 必须处理 legacy dual-grid 全部 work，不得私自过滤。

### 7. Telemetry

```text
segment_batch_size_requested
segment_batch_size_active
segment_batches
partial_batches
batch_memory_estimate_bytes
batch_peak_device_memory_bytes
memory_limit_fallbacks
OOM_count
target_tiles_loaded
target_tile_reuses
launches
GASAL2_requests
DP_cells
traceback_requests
ownership_work_dropped
batch_wall_seconds
```

## 测试梯度

```text
1 segment
2 segments
4 segments
KCNQ1OT1 max4
KCNQ1OT1 max8
short-query H19 control
non-H19 short-query control
```

每级先 correctness，后 benchmark。

## 硬 gate

```text
full row-set equal = 1
all three top5 equal = 1
ties equal = 1
fallbacks = 0
OOM = 0
one_worker_per_gpu = 1
peak memory within measured budget = 1
output commit deterministic = 1
```

## Promotion gate

B=2 或 B=4 作为推荐 candidate 至少满足：

```text
max8 median wall reduction vs persistent B1 >= 10%
short-query control regression <= 3%
request count does not increase
peak device memory leaves required headroom
```

`strong_go` 参考：

```text
max8 median wall reduction >= 20%
```

如果只有 target setup 计数下降但 wall 收益 <5%，标记 `scaffold_useful_but_runtime_no_go`，不要扩大 B。

## no_go 条件

- B=2 即超过安全显存预算。
- B=2 正确但 wall 改善 <5%，且 profile 显示无可摊薄部分。
- batching 增加 request、traceback 或 fallback。
- B=4 只增加内存而不减少 wall。

允许保留 Phase 3 的 B=1 persistent context 和 buffer pool，即使 Phase 4 标 `no_go`。

## 完成产物

```text
bounded multi-segment microbatch
memory pool and accounting
B=2/B=4 gates
benchmark artifacts
docs/fasim_gasal2_multi_segment_microbatch.md
goal.md status update
```

建议 commit：

```text
fasim: batch query segments within a bounded GASAL2 memory budget
```

---

# Phase 5 — Exact-column task reduction、fusion 与 kernel 优化

## 目标

基于 Phase 3/4 后的新 profile，先减少进入 exact-column 的工作和中间流量，再优化 kernel tile/launch shape。不得只做 microbenchmark。

## Entry gate

先确认 exact-column 仍是 material hotspot。记录：

```text
exact_stage_seconds / end_to_end_seconds
exact_kernel_seconds / exact_stage_seconds
exact_tasks
exact_cells
H2D/D2H seconds
launch count
occupancy/register/shared-memory metrics, when available
```

若 exact stage 已低于 end-to-end 的 10%，可直接标 `no_go_low_ceiling`，避免无价值重写。

## 必做

### 1. Shadow task compaction

寻找不改变语义的 exact task 减少方式，例如：

- Phase 2 ownership 已证明的重复 task。
- 完全相同 task 的精确去重。
- 已有规则能证明不会改变 minScore/column maxima 的 task 合并。
- 上游已有安全 filter 的提前应用。

新增 shadow 统计 candidate task set 与 authority task set；没有 proof 不得 drop。

### 2. Fusion

评估并原型：

```text
minScore calculation
column maxima
prune metadata
exact-column result packing
```

目标是减少中间 global-memory roundtrip 和 launch；fusion 后结果必须逐 task 等价。

### 3. Kernel variants

在 default-off 下测试：

```text
tile dimensions
block/warp mapping
launch shape
vectorized/coalesced loads
register pressure
shared-memory use
persistent or grouped launch, only if justified
```

不得默认运行时 autotune；选择必须可复现并按 GPU arch fail closed。

### 4. Overflow 和规则矩阵

必须覆盖：

```text
rule=0
现有 overflow fixtures
最大已验证 query length
不同 target tile sizes
多 GPU guard
```

### 5. Telemetry

```text
exact_tasks_before
exact_tasks_after
exact_tasks_dropped_by_reason
exact_cells_before
exact_cells_after
exact_launches
exact_kernel_seconds
exact_h2d_seconds
exact_d2h_seconds
exact_stage_seconds
end_to_end_seconds
kernel_variant
```

## 硬 gate

```text
per-task exact outputs equal = 1
full row-set equal = 1
all three top5 equal = 1
overflow fixtures clean = 1
fallbacks = 0
```

## Promotion gate

至少满足以下之一，并且 end-to-end 不回归：

```text
exact_stage median reduction >= 20%
end_to_end median reduction >= 5%
```

`strong_go`：

```text
end_to_end median reduction >= 10%
```

短 query control 回归必须 <=3%。

## no_go 条件

- kernel 快但 end-to-end 改善 <2%，且 exact stage ceiling 已低。
- task compaction 无法证明 exact-safe。
- shared-memory/tile 只对特定 query 长度有效并导致其他长度 fallback 或输出漂移。

## 完成产物

```text
exact task shadow/compaction if safe
kernel/fusion candidate if material
automated exactness gates
profile and benchmark artifacts
docs/fasim_gasal2_exact_column_long_query.md
goal.md status update
```

建议 commit：

```text
fasim: reduce and optimize exact-column work for segmented queries
```

---

# Phase 6 — Traceback timing 与 safe candidate certificate

## 目标

降低 traceback requests，但只允许使用 pre-traceback、tie-complete、全局合同安全的 certificate。此 phase 是高收益、高风险线；零 skip 或不加速是合法 `no_go`。

## 禁止重启的旧方案

```text
fixed traceback score threshold
chromosome-specific hardcoded threshold
只覆盖 score top5 的 early stop
用最终 CPU retained rows 反推 runtime skip
```

## 必做

### 1. 先拆 timing

至少分开：

```text
traceback_score_prepass_seconds
traceback_pack_seconds
traceback_H2D_seconds
traceback_kernel_seconds
traceback_D2H_seconds
traceback_convert_seconds
traceback_filter_dedup_cluster_seconds
```

如果当前架构不能无同步测量 GPU 区间，保留 host wait timing 并标 unavailable；不得添加全局同步只为计时。

### 2. Rank-independent certificate 优先

先实现/验证不依赖最终排名的安全拒绝：

- Phase 2 已证明的 non-owner duplicate。
- 可证明无效的 query/target span。
- 可证明不能通过最终长度/坐标合同的候选。
- 完全重复 descriptor 的 exact dedup。

每个 drop reason 必须有独立 counter 和 fail-closed fallback。

### 3. Rank-aware certificate 仅从 shadow 开始

若继续全局 top5 certificate，必须同时覆盖：

```text
score upper bound
stability upper bound
Nt upper bound
boundary ties
filter/dedup/cluster 后的 retained unique top5
```

停止条件必须基于全局、多 segment 的最终合同，不能只看 segment-local top5。

### 4. Pre-drop proof

实际 skip 前必须存在可验证 proof record：

```text
candidate_id
segment_id
certificate_kind
upper_bounds
current_global_frontier
boundary_tie_state
proof_version
```

proof 必须在 drop 之前产生。无法证明的候选走完整 traceback。

### 5. Shadow matrix

至少运行：

```text
synthetic tie fixtures
short-query H19
non-H19 short-query panel subset
chr21/chr22 control
KCNQ1OT1 max4/max8
```

统计：

```text
candidates_considered
certified_skips
uncertified_candidates
shadow_false_rejects
score_frontier_skips
stability_frontier_skips
Nt_frontier_skips
tie_rescues
fallbacks
```

### 6. Runtime gate

只有 shadow：

```text
shadow_false_rejects = 0
```

并且所有合同 clean 后，才允许 default-off real skip。

## 硬 gate

```text
pre_drop_proof = 1
shadow_false_rejects = 0
full row-set equal = 1, for full-output claim
all three top5 equal = 1
ties equal = 1
fallback accounting clean = 1
```

## Promotion gate

实际 runtime candidate 至少满足：

```text
traceback_requests reduction >= 20%
traceback stage wall reduction >= 15%
end_to_end wall reduction >= 8%
```

`strong_go`：

```text
traceback_requests reduction >= 35%
end_to_end wall reduction >= 15%
```

## no_go 条件

- certificate union 后 `certified_skips = 0`。
- 只有 score bound，没有 stability/Nt 安全上界。
- proof 依赖最终 CPU output membership。
- request 数下降但 convert/cluster 或 proof overhead 抵消全部 wall 收益。
- 任一 tie、row-set 或 top5 mismatch。

no_go 时：

- 关闭真实 skip。
- 可保留低开销 timing 和有用的 shadow telemetry。
- 文档记录该 certificate family 停止，不继续通过调阈值“抢”收益。

## 完成产物

```text
traceback stage timing
rank-independent certificate if safe
rank-aware shadow/runtime candidate or measured no-go
automated tie/row/top5 gates
docs/fasim_gasal2_traceback_certificate_long_query.md
goal.md status update
```

建议 commit：

```text
fasim: gate traceback reduction with pre-drop exact certificates
```

---

# Phase 7 — 集成 benchmark 与 full KCNQ1OT1 × chr22 gate

## 目标

把已通过的 Phase 1-6 组件组合起来，先 bounded workload，再决定是否运行完整 KCNQ1OT1 × chr22。此 phase 不再引入新架构，只修集成 bug 和做测量。

## Entry gate

以下必须成立：

```text
Phase 0 = pass
Phase 1 = pass or documented no_go with safe fallback
Phase 3 = pass, unless Phase 4 is blocked and only Phase 5/6 are tested
all enabled runtime reductions have clean correctness gates
archive-first available for long run
peak memory estimate within budget
```

任一真实 work-drop 路径未通过 full contract，禁止全量运行。

## 集成配置

建立一份机器可读 config manifest，至少包括：

```text
commit
binary digest
input digests
segment_len/overlap/shifts
canonical vs dual grid
archive-first
persistent context
segment batch size
memory limit
ownership mode
exact-column variant
traceback certificate mode
streams/batch
GPU IDs
worker count
```

run config 必须进入 digest，避免不同配置 artifact 混用。

## Benchmark ladder

按顺序执行；前一级失败不得进入下一级：

### 7.1 Small integration

- synthetic + small chr22 slice。
- 完整 row-set、byte/set、三 top5、archive restore、fallback、memory 全 clean。

### 7.2 KCNQ1OT1 max4

- 与 Phase 0/current legacy max4 直接比较。
- 记录完整 stage timing、requests、tracebacks、memory、archive bytes。

### 7.3 KCNQ1OT1 max8

promotion 前至少 3 次，报告 median；如单次成本过高，允许 2 次，但必须解释。

### 7.4 完整 KCNQ1OT1 × chr22

只有 max8 满足：

```text
correctness clean
fallbacks = 0
OOM = 0
wall improvement >= 10%
performance direction stable across repeats
```

才允许运行。

full run 要求：

- archive-first；不产生每段全量文本。
- 失败可 resume，不能从头丢失全部进度。
- 每 segment/batch manifest 原子提交。
- 保留 stderr、summary、config、digests、top5 details。
- 如 Phase 2 未证明 single-grid，必须继续 dual-grid；不得为了省一半计算私自切 single-grid。

## 对照 workload

集成候选还必须检查：

```text
short-query H19 chr21/chr22 top5
non-H19 short-query panel subset
完整 TFOsorted chr22 control
至少一个 MALAT1/NEAT1 representative control, if inputs are available
```

不得只在 KCNQ1OT1 上赢而破坏已有短 query 产品。

## 结果表

至少输出 baseline/candidate：

```text
outer wall
sum segment wall
speedup
segment count
grid count
GASAL2 requests
DP cells
exact tasks
exact kernel/stage seconds
traceback requests
traceback stage seconds
convert/merge/restore seconds
input/output rows
duplicates removed
archive bytes
temporary text bytes
peak GPU memory
peak host RSS
fallbacks
all output contract results
```

## 集成 gate

```text
missing_rows = 0, where authority exists
extra_rows = 0, where authority exists
all three top5 equal = 1
grid contract respected = 1
archive restore clean = 1
fallbacks = 0
OOM = 0
short-query regression <= 3%
```

## 运行时判定

相对 Phase 0 的可比 KCNQ1OT1 baseline：

```text
speedup >= 1.50x -> strong_go candidate
speedup >= 1.25x -> scoped_go candidate
speedup < 1.10x  -> runtime no_go
1.10x <= speedup < 1.25x -> useful but not product promotion; final decision must justify
```

存储目标单独报告：

```text
per-segment full text bytes = 0
archive/text reduction >= 4x preferred
```

不得把存储压缩写成计算 speedup。

## 完成产物

```text
resumable integrated runner/config manifest
bounded and optional full benchmark artifacts
docs/fasim_gasal2_long_query_integrated_result.md
updated docs/fasim_gasal2_workload_matrix.tsv
goal.md status update
```

建议 commit：

```text
bench: validate integrated GASAL2 long-query architecture
```

---

# Phase 8 — 关闭决策、推荐配置与清理

## 目标

根据 Phase 7 证据给出唯一、严格 scoped 的最终决定。此 phase 不新增性能功能。

## 必做

1. 新建或更新：

```text
docs/fasim_gasal2_long_query_final_decision.md
```

2. 列出：

```text
what passed
what was no-go
what remains default-off
supported workloads
unsupported workloads
correctness contract
memory/resource boundary
recommended invocation
fallback behavior
artifact and restore procedure
known limitations
next valid research question
```

3. 更新 README/advanced runtime notes，只加入已经通过 promotion 的配置。

4. 更新 Makefile 总检查，运行所有新增 parser/smoke/static checks。

5. 删除 phase 内明显 dead code 和未使用 env；不得删除用于 authority/fallback 的 legacy 路径。

6. 检查文档没有以下错误声明：

```text
grid stability == full equivalence
top5 clean == full output clean
archive restore == aligner replacement
KCNQ1OT1 result == universal long-query result
kernel speedup == end-to-end speedup
fallback-heavy == clean GPU fast path
```

## 最终决策规则

### `long_query_architecture_strong_go`

必须满足：

```text
Phase 7 integrated correctness clean
KCNQ1OT1 comparable speedup >= 1.50x
short-query regression <= 3%
peak memory within supported budget
fallbacks = 0
archive-first storage gate clean
```

### `long_query_architecture_scoped_go`

必须满足：

```text
Phase 7 integrated correctness clean
KCNQ1OT1 comparable speedup >= 1.25x
scope explicitly limited to tested segmented workload/config
short-query regression <= 3%
resource boundary documented
```

### `long_query_architecture_no_go_with_complete_evidence`

适用：

- 所有安全架构线已按 phase 实现/测量。
- 关键候选无 material speedup、OOM、或无法建立安全 proof。
- 默认路径未受损。
- no-go family 和证据完整记录。

no-go 不是失败隐藏；它是合法关闭结果，但不得写成产品优化完成。

## 最终硬 gate

```text
all phases are pass/no_go, none blocked
final decision is one allowed value
claims match workload matrix
recommended invocation is reproducible
all enabled paths have tests
legacy/default behavior remains available
```

## 完成产物

```text
docs/fasim_gasal2_long_query_final_decision.md
README/advanced runtime updates
final Makefile check target
updated goal.md with active_phase = complete
```

完成时状态块应类似：

```text
active_phase = complete
last_completed_phase = 8
last_decision = long_query_architecture_scoped_go
last_evidence_doc = docs/fasim_gasal2_long_query_final_decision.md
last_test_command = make check-fasim-gasal2-long-query-final
last_commit = <commit-or-uncommitted>
```

建议 commit：

```text
docs: close the scoped GASAL2 long-query architecture decision
```

---

## 5. 每个 Phase 的标准执行模板

Codex 在每个 phase 都按以下顺序执行：

### A. Inspect

```text
read current source and tests
locate existing helpers/env/telemetry
record current behavior
confirm authority and comparator
```

### B. Baseline

```text
run smallest representative baseline
save command, env, logs, digests, wall, counters
```

### C. Implement

```text
smallest default-off implementation
fail closed
bounded resources
no unrelated refactor
```

### D. Correctness first

```text
parser/unit/synthetic
small fixture
row-set
three top5 contracts
ties
fallbacks
```

### E. Performance second

```text
profile direct baseline vs candidate
repeat short runs
report median and stage attribution
```

### F. Decide

```text
pass | no_go | blocked
```

### G. Record

更新：

```text
one phase evidence doc
Makefile/check target
goal.md status block
workload matrix when claim scope changes
```

### H. Diff hygiene

结束前输出并检查：

```bash
git status --short
git diff --stat
git diff --check
```

列出实际运行过的测试；不得写未运行的测试已通过。

---

## 6. Benchmark artifact 规范

每个长 benchmark workdir 至少包含：

```text
run_config.env or run_config.json
commit.txt
binary.sha256
inputs.sha256
stdout.log
stderr.log
summary.txt
phase_timing.tsv or equivalent
memory_summary.txt
output_contract_summary.txt
fallback_summary.txt
artifacts manifest
```

禁止只在文档手抄最终数字而丢失原始日志。

对于 resumable segmented run：

```text
segment/batch state = pending | running | complete | failed
complete state written atomically
artifact digest recorded before complete
config digest mismatch -> refuse resume
```

---

## 7. 预期总检查入口

最终应有一个真实、可运行的总入口；名称可按仓库风格调整：

```text
make check-fasim-gasal2-long-query-final
```

它只运行合理时长的 static/parser/synthetic/small-fixture checks，不默认运行数小时 benchmark。

长 benchmark 必须由显式开关触发，例如：

```text
RUN_LONG=1
RUN_KCNQ1OT1_FULL=1
```

总检查至少验证：

```text
archive-first segmented parser/restore
bounded merge
segment ownership oracle/shadow
persistent B=1 context
microbatch small fixture
exact-column equality fixtures
traceback tie/certificate fixtures
final docs/workload-matrix consistency
```

---

## 8. 最终提醒

这项工作真正的空间是架构复用和工作量削减，不是继续调参。Codex 必须始终保持以下判断：

```text
短 query top5 的低风险优化基本成熟。
完整输出与长 query 仍未优化到头。
下一步价值来自：
  archive-first + bounded merge
  target/context reuse
  segmentation ownership proof
  memory-bounded multi-segment execution
  exact task/kernel reduction
  pre-drop safe traceback certificates
```

任何不能证明正确、不能减少真实 end-to-end wall、或只能依赖特定 H19/染色体阈值的方案，都应及时记录为 `no_go`，而不是继续堆叠复杂度。
