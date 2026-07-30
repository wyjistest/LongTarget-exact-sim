# GASAL2-LongTarget clustered Top-K TFO candidate-site 验证与投稿强化执行目标

> **文件角色**：本文件必须保存为仓库根目录的 `goal-biological-topk.md`。它是一个新的、独立的研究 epoch，不得覆盖或改写 `goal.md`、`goal-final.md`、`goal-bioinformatics.md`、`goal-ssw.md`。正式执行时，优先将本文件作为仓库外 protocol source 交给 Codex；Codex 必须先在尚未创建任何新文件时记录 clean start check，再把本文件作为 Phase 0 allowlisted change 写入仓库。若仓库中已存在未跟踪的同名文件且没有先前 clean-start receipt，必须停止、恢复 clean tree 后重新开始 Phase 0。
>
> **科学对象修正**：现有 LongTarget/Fasim 聚类是在 **query/TFO 坐标轴**上，以 `int((QueryStart + QueryEnd) / 2)` 为中点，对满足 `Nt(bp) > 50` 的行执行既有聚类；它不是按基因组 target 坐标进行 DNA-locus 聚类。因此，本 epoch 的合同对象固定为：
>
> ```text
> clustered TFO/query-target candidate site
> ```
>
> 不得在合同、软件或稿件中将其简写成“DNA locus preservation”，除非未来另立一个真正按 target genomic coordinates 聚类的独立合同。
>
> **产品状态边界**：在新鲜 CPU-reference concordance、独立实验数据 biological utility、新 epoch 端到端性能全部通过之后，`gpu-screen` 仍必须保持 `experimental`；只有 Phase 8 的产品 artifact、CI、容器、provenance 与 release-candidate checker 全部通过，状态转换已包含在 Phase 8 commit 中，且该 commit 的 post-commit read-only check 通过后，才能升级为 `validated_screening_backend_v1_release_candidate`。Bioinformatics 路线在 Phase 9 最终认证前只能写成 `conditionally_reopened`。
>
> **起草时历史锚点**：`2658a98fea8f34bd295892e6236607060e2f2803`。执行时必须重新读取实际 branch、HEAD、remote 和 working tree。该 SHA 只用于绑定起草时已知历史证据，不是强制 checkout 起点。

---

## 0. 不可改写的历史结论

本 epoch 是研究目标的正式换轨，不是对旧 gate 的事后放宽。以下状态必须在状态机、claim ledger、稿件和 release notes 中并列保留：

```text
strict_canonical_row_v1 = no_go
sequential_verified_v1 = no_go
canonical_hybrid_v2_correctness = pass
canonical_hybrid_v2_performance = no_go
canonical_hybrid_v2_rescue_track = closed
exact_ssw_cuda = closed
exact_ssw_cuda_final_decision = ssw_cuda_forward_or_reverse_checkpoint_only
new_epoch_contract_status = proposed
```

### 0.1 strict canonical-row v1

旧合同要求 score、stability、Nt 三种排序下 clustered TFO1–TFO5 的完整 representative row 一致。已知严格 mismatch 最终定位为可重复的 endpoint/CIGAR traceback 表示分叉；旧结论仍然是：

```text
gpu_traceback_v1_contract = verified_only_contract
```

不得改写为 pass，不得删除 mismatch、traceback replay 或 full-output diagnostic。

### 0.2 sequential verified-v1

旧 verified 路径为：

```text
GPU candidate + complete CPU authority + comparison
```

它结构上不可能快于单独 CPU authority，因此：

```text
sequential_verified_v1_B3 = no_go
```

### 0.3 canonical-hybrid-v2

已冻结事实：

```text
regression clustered Top-5 canonical rows = 36/36
regression full-output diagnostic          = 35/36
fresh holdout                              = 60/60
performance pilot correctness              = 18/18
primary A/H speedup                        = 0.257592x
hybrid slowdown                            = 3.882109x
B3-v2                                      = no_go
rescue track                               = closed
```

不得重复开启同一 rescue track。

### 0.4 exact SSW-CUDA

exact SSW-CUDA 已完成 L1–L3 correctness checkpoint；Phase 7 forward-hybrid 为 no-go，后续未授权。不得在本文件中继续 reverse-start、CPU-compatible CIGAR 或 full-GPU exact SSW 实现。

### 0.5 历史 38.32x 的边界

历史 H19 short-query fast Top-K 约 `38.32x` 只能标记为：

```text
historical_candidate_performance_anchor
```

在本 epoch 新合同、固定输入、独立执行和独立统计完成前，不得称为：

```text
biological_topk_candidate_site_v1 validated speedup
validated biological acceleration
production GPU speedup
```

---

## 1. 新 epoch 状态块

Codex 必须把以下对象作为**真正的 JSON**写入 `paper/biological_topk/PROGRAM_STATE.json`；不得使用 `key = value` 伪 JSON。状态 schema 必须拒绝未知字段、未知状态和非法 phase 转换。

```json
{
  "program_name": "biological_topk_candidate_site_validation",
  "program_schema_version": 5,
  "contract_name": "biological_topk_candidate_site_v1",
  "contract_status": "proposed",
  "scientific_object": "clustered_TFO_query_target_candidate_site",
  "claim_scope": "set_preservation_with_top1_retention",
  "rank_order_claim": "diagnostic_only",
  "score_representation": "pending_phase1",
  "gpu_screen_status": "experimental",
  "bioinformatics_route": "conditionally_reopened",
  "active_phase": 0,
  "phase_status": {
    "0": "pending",
    "1": "pending",
    "2": "pending",
    "3": "pending",
    "4": "pending",
    "5": "pending",
    "6": "pending",
    "7": "pending",
    "8": "pending",
    "9": "pending"
  },
  "last_completed_phase": null,
  "last_decision": "epoch_not_started",
  "previous_phase_commit": null,
  "audit_candidate_commit": null,
  "final_decision_candidate": null,
  "final_decision": null
}
```

### 1.1 合法 phase 状态

```text
pending
active
pass
no_go
blocked_missing_evidence
blocked_insufficient_source_universe
blocked_insufficient_information
blocked_insufficient_experimental_information
blocked_external_data
blocked_fixed_budget
blocked_technical_failure
not_authorized_previous_no_go
```

不得使用 `mostly_pass`、`partial_ready`、`probably_ready` 等模糊状态。`blocked_insufficient_experimental_information` 是正式枚举值，不得临时写入未注册状态。

机器可读枚举统一为：

```text
rank_order_claim = diagnostic_only
ranking_mode = score | stability | nt
score_representation = pending_phase1 | integral_exact | decimal_exact
```

人类可读文字可以写 `Nt`，但 TSV/JSON/schema/CLI 中的 ranking machine value 必须写小写 `nt`。后续所有合同阶段变化必须写入 `PROGRAM_STATE.json.contract_status`；不得另造平行的 `biological_topk_candidate_site_v1 = ...` 状态字段。

`contract_status` 合法值固定为：

```text
proposed
in_validation
fresh_concordance_pass
concordance_no_go
concordance_and_utility_pass
biological_utility_no_go
performance_widening_pass
performance_widening_no_go
validated_within_fixed_operating_envelope
release_or_reproducibility_blocked
```

每次 phase transition 只能使用与该 phase 授权路径一致的值；schema 必须拒绝未知值。


`gpu_screen_status` 合法值固定为：

```text
experimental
validated_screening_backend_v1_release_candidate
```

`bioinformatics_route` 合法值固定为：

```text
conditionally_reopened
closed_for_this_contract
closed_biological_utility_gap
conditionally_reopened_pending_phase8_release_candidate
no_go_retarget_csbj_or_methods
conditionally_reopened_pending_final_audit
release_or_reproducibility_blocked
bioinformatics_application_note_ready_pending_owner_actions
bioinformatics_application_note_ready_for_submission
```

Schema 对这两个字段同样必须拒绝未知值；Phase 4/6/7 的科学通过不得提前产生 validated product status。

`active_phase` 在执行中必须是整数 `0..9`；当 epoch 因 Phase 9 认证完成，或因没有任何后续 phase 获授权的 terminal no-go/block 而结束时，必须设为 JSON `null`。`last_decision` 必须保存导致当前 terminal state 的已注册机器值；`schemas/biological_topk_program_state.schema.json` 与 transition checker 必须同步拒绝未知 decision 值。

后文为可读性使用的 `phase_4_status = pass` 等写法，均是 `PROGRAM_STATE.json` 中 `phase_status["4"] = "pass"` 的 prose shorthand；实现和 checker 只能读写真实 JSON path。

### 1.2 Phase 依赖

```text
Phase 0 pass -> Phase 1
Phase 1 pass -> Phase 2
Phase 2 pass -> Phase 3
Phase 3 pass -> Phase 4
Phase 4 pass -> Phase 5
Phase 5 pass -> Phase 6
Phase 6 pass -> Phase 7
Phase 7 pass -> Phase 8
Phase 8 pass -> Phase 9
```

任一 scientific `no_go` 必须停止所有依赖该结论的后续 phase；不得通过修改阈值、补样或更换主终点继续原 epoch。

---

## 2. Agent 总指令与 Git 执行语义

### 2.1 一次只执行一个 phase

每个 Phase 0–8 必须使用以下顺序；**状态转换必须先于 phase commit，并包含在该 commit 中**：

```text
1. phase-start clean check；
2. start receipt 绑定上一 phase commit（Phase 0 绑定 execution-start HEAD）；
3. implementation / protocol freeze；
4. unit and integration tests；
5. machine-readable evidence；
6. 将 PROGRAM_STATE.json 从 active 转为本 phase最终状态；
7. allowlisted pre-commit diff check；
8. pre-commit checker；
9. phase commit；
10. post-commit read-only check；
11. 下一 phase 的 start receipt 绑定该 phase commit。
```

禁止在 commit 之后再修改状态而不提交。post-commit checker 必须是 read-only：不得生成或修改 tracked/untracked 文件。

### 2.2 Phase 开始、receipt 与提交的正确语义

```text
1. phase 开始时：working tree 必须 clean；
2. phase 执行中：只能存在该 phase allowlist 中的 tracked/untracked changes；
3. pre-commit checker：必须拒绝 allowlist 外变化，并验证最终状态已写入 PROGRAM_STATE.json；
4. phase commit 后：working tree 必须 clean；
5. post-commit read-only checker：验证 HEAD tree、状态和 evidence，但不得写文件；
6. 下一 phase 开始前：再次验证 clean，并把上一 phase commit SHA 写入新的 start receipt。
```

每个 phase 必须生成：

```text
paper/biological_topk/phase_<N>_change_allowlist.txt
paper/biological_topk/phase_<N>_start_receipt.json
paper/biological_topk/phase_<N>_precommit_receipt.json
```

`phase_<N>_precommit_receipt.json` 只能记录：

```text
phase-start parent HEAD
expected changed paths
schema/evidence digests
checker command and result
planned commit message
```

它不得记录尚不存在的本 phase commit SHA。任何文件都不得声称记录其自身所在 commit 的 SHA。

从 Phase 1 开始，`phase_<N>_start_receipt.json` 必须记录：

```text
previous_phase_number
previous_phase_commit
previous_phase_postcommit_check_command
previous_phase_postcommit_check_result
```

因此上一 phase 的 commit 身份由下一 phase start receipt 认证，而不是由自身提交中的自引用 receipt 认证。

### 2.3 Phase 0 protocol bootstrap

Phase 0 的 clean-start 证据必须发生在创建 `goal-biological-topk.md`、receipt 或任何目录之前：

```text
1. 从仓库外读取 protocol source；
2. 执行 git status --porcelain=v1、git rev-parse HEAD、git branch --show-current；
3. 要求 status 输出为空；
4. 在内存中保留 command、stdout、stderr、exit code、execution-start HEAD；
5. 随后创建 phase_0_start_receipt.json，并记录 protocol_source_sha256；
6. 将 goal-biological-topk.md 复制到仓库根目录，作为 Phase 0 allowlisted change；
7. Phase 0 commit 同时提交 goal 文件、start receipt、状态机和其余 Phase 0 证据。
```

若同名文件已作为未跟踪文件存在，且没有可验证的“创建前 clean check”证据，Phase 0 不得把当前状态认证为 clean start；必须移出该文件、恢复 clean tree 后重启。

### 2.4 统一 phase checker 与 aggregate checker

Phase 0 必须建立单一参数化 checker，作为 Phase 0–9 的规范入口：

```text
python scripts/check_biological_topk_phase.py --phase N --mode precommit
python scripts/check_biological_topk_phase.py --phase N --mode postcommit
```

允许提供 `scripts/check_biological_topk_phase<N>.sh` 薄包装，但不得复制或分叉核心规则。Phase 9 额外允许：

```text
--mode audit-candidate
--mode certification
--mode post-certification
```

最终 aggregate checker 必须调用同一个参数化 checker 的所有已授权 phase，并提供：

```text
scripts/check_biological_topk_all.sh
```

要求：

```text
precommit mode 可验证 allowlisted diff，但不得执行未预注册的科学运行；
postcommit / audit / post-certification mode 必须 read-only；
checker 启动前后 git status 必须相同；
所有 mode 的参数、schema 和 exit-code 语义固定；
aggregate checker 不得跳过 no_go/blocked phase 的状态一致性检查。
```

Phase 9 使用两步提交：

```text
A. audit-candidate commit：包含完整 manuscript、claim ledger、tables/figures、
   aggregate-audit inputs，并将 phase_9_status 保持为 active、写入 final_decision_candidate；
B. 在 audit-candidate commit 上运行 read-only aggregate checker；
C. certification commit：只允许修改最终状态、final_decision 和 certification receipt，
   receipt 绑定 audit-candidate commit SHA 与 checker output digest；
D. certification commit 后运行 read-only post-certification checker。
```

certification receipt 不得记录 certification commit 自身 SHA；最终 HEAD 本身就是认证 commit 的身份。

### 2.5 历史活跃文件的绑定方式

`paper/PAPER_PREP_STATUS.md`、`paper/scope_and_claims.md` 等是活跃总览文件，未来可以合法更新。历史 registry 不得声称 live path 永久不可变。

必须绑定：

```text
execution_start_head:path
Git blob SHA-1
blob bytes SHA-256
size_bytes
historical evidence role
```

字段：

```text
path
frozen_at_commit
git_blob_sha1
blob_sha256
size_bytes
evidence_role
live_path_mutable = 1
frozen_blob_mutable = 0
```

历史审计比较的是 frozen blob，不是要求当前工作树中的同名文件永远不变。

### 2.6 开始前必须读取

```text
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -80
git remote -v

Makefile
README.md
goal.md
goal-final.md
goal-bioinformatics.md
goal-ssw.md

paper/PAPER_PREP_STATUS.md
paper/scope_and_claims.md
paper/generalization_report.md
paper/bioinformatics/README.md
paper/bioinformatics/phase2_decision.md
paper/bioinformatics/holdout_mismatch_details.tsv
paper/bioinformatics/canonical_hybrid_v2_regression_decision.md
paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md
paper/bioinformatics/canonical_hybrid_v2_performance_decision.md
paper/bioinformatics/application_selection.json
paper/ssw_cuda/STATUS.md
paper/ssw_cuda/final_decision.json

scripts/compare_fasim_lite_offline_cluster_topk.py
scripts/compare_fasim_segmented_contract.py
scripts/fasim_tfo_archive.py
reproduce/ssw_cuda/freeze_phase0.py
fasim/fastsim.h
fasim/Fasim-LongTarget.cpp
```

### 2.7 禁止事项

```text
不得回写旧 no-go 为 pass
不得删除 mismatch、OOM、timeout、missing output 或失败 attempt
不得根据 A/G 结果调 overlap、K、margin、统计方法或 panel
不得使用 query/gene 名、SHA、cluster ID 白名单
不得把旧 38.32x 当作本合同的新性能结果
不得把 CPU reference 当作 biological truth
不得把 double-empty workload 计为 concordance success
不得把 technical repeats 当独立样本
不得把运行结果中的 Rule/Strand 用于 fresh input selection
不得在 G arm 运行时读取 A arm output
不得在 A/G 全部完成前启动 comparator
不得用 complete-case-only 统计替代失败计入分母的 primary analysis
不得将 `candidate site` 改写成 `DNA locus` 或 `genomic locus` 主张
```

---

## 3. Arms、证据角色与独立执行

### 3.1 Arms

```text
A = CPU Fasim-LongTarget reference arm
G = GASAL2-LongTarget experimental gpu-screen arm
X = external comparator tool, when operationally and semantically comparable
```

A 是历史 reference，不是生物学真值。

### 3.2 A/G 独立执行

A、G、X 必须：

```text
独立进程
独立 artifact root
独立 stdout/stderr
独立 run receipt
不接收其他 arm 的 output path
不读取其他 arm 的 output digest
不读取离线 comparison result
```

Balanced order 只控制启动顺序：

```text
A -> G
G -> A
```

无论顺序如何，comparison 必须在两侧 receipt 都完成、artifact checksum 都冻结之后离线执行。

### 3.3 证据角色

```text
historical_anchor
regression_only
fresh_concordance_promotion
experimental_utility_promotion
performance_promotion
diagnostic_only
```

每个 artifact、表、图和 source-data row 必须有 `evidence_role`。

---

## 4. 科学对象：clustered TFO/query-target candidate site

### 4.1 不再使用“DNA locus”作为合同对象

现有 clustering 代码事实：

```text
row qualifies only when Nt(bp) > 50
legacy midpoint = int((QueryStart + QueryEnd) / 2)
cluster axis = query/TFO coordinate
cluster distance parameter dd = 15
```

因此本合同的对象是：

```text
一个在 query/TFO 坐标轴上形成的 cluster，
以及在指定 ranking mode 下从该 cluster 选出的 query-target representative alignment。
```

正式术语：

```text
clustered TFO candidate site
或
clustered TFO/query-target candidate site
```

禁止正式术语：

```text
DNA locus
DNA-binding locus preservation
pure genomic-locus clustering
```

### 4.2 v1 允许的主张

本 epoch 只验证：

```text
Top-K candidate-site set preservation with Top-1 retention
```

它不自动验证：

```text
第 2–5 名完全相同的顺序
完整 ranking equivalence
endpoint/CIGAR equality
full-output equality
```

Phase 1 必须将 `rank_order_claim = diagnostic_only` 冻结。若未来要声称完整排序保持，必须另立版本化合同和独立 holdout。

### 4.3 Within-arm clustering 必须逐语义复刻现有实现

不得用通用 DBSCAN、简单 midpoint distance grouping 或输出中的数字 `Class/cluster_id` 替代。

必须复刻：

```text
strict Nt(bp) > 50
legacy query midpoint = int((raw QueryStart + raw QueryEnd) / 2)
positive-coordinate Python/C++ truncation semantics
exact dd=15 loop range and weights
exact max-position tie behavior
exact motif assignment order
exact row eligibility and cluster termination behavior
```

Phase 1 必须生成：

```text
docs/biological_topk/legacy_clustering_semantics.md
paper/biological_topk/legacy_clustering_fixtures.tsv
```

并将现有脚本/源代码行与 golden fixtures 绑定。

### 4.4 `minimum_nt_bp` 的边界

合同字段必须写成：

```text
minimum_nt_rule = strict_greater_than
minimum_nt_bp = 50
```

即：

```text
Nt(bp) = 50 -> excluded
Nt(bp) = 51 -> eligible
```

Tests 必须覆盖 49、50、51。

---

## 5. 输入身份：A/G 必须完全相同

### 5.1 Workload identity

在 matcher 或 canonicalizer 读取输出前，preflight 必须证明 A/G 使用完全相同输入和运行合同。

必须全部相等，使用 **AND** 语义：

```text
query_ordinal_namespace
query_source_ordinal
query_sequence_sha256
target_ordinal_namespace
target_source_ordinal
target_sequence_sha256
assembly
target_coordinate_namespace
query_extraction_recipe_id
target_extraction_recipe_id
parameter_bundle_sha256
input_pair_digest
```

以下任何一项不一致：

```text
input_identity_mismatch = technical failure
comparison must not start
all primary metrics for the workload = failure
```

不得使用：

```text
same target digest OR same coordinate namespace
bare source ordinal equality
filename equality
query/target display name equality
```

### 5.2 Namespaced ordinal

Source ordinal identity 必须是二元组：

```text
(namespace, ordinal)
```

例如：

```text
("gencode_v49_representative_lncRNA", 12345)
("phase3_application_role_ordinal", 1)
```

裸整数 `1` 不得跨 namespace 比较。

### 5.3 Pair digest

Pair digest 必须来自 canonical JSON：

```text
schema version
query namespace + ordinal + digest + extracted interval
 target namespace + ordinal + digest + extracted interval
assembly
coordinate namespace
extraction recipe IDs
parameter bundle digest
```

序列化规则：

```text
UTF-8
sorted keys
separators=(",", ":")
no insignificant whitespace
SHA-256
```

---

## 6. 坐标语义与 canonicalization

### 6.1 原始字段必须保留

每行首先保存：

```text
raw_QueryStart
raw_QueryEnd
raw_StartInSeq
raw_EndInSeq
raw_StartInGenome
raw_EndInGenome
raw_Strand
raw_Direction
raw_Chr
```

不得先 `min/max` 后丢失历史语义。

### 6.2 必须建立逐 Strand/Direction 映射表

现有 target 坐标存在不同历史约定；不得统一使用：

```text
start = min(raw_start, raw_end)
end = max(raw_start, raw_end) + 1
```

Phase 1 必须从代码事实建立并冻结：

```text
docs/biological_topk/coordinate_mapping_table.tsv
```

覆盖所有实际支持组合：

```text
ParaPlus  x R/L
ParaMinus x R/L
AntiPlus  x R/L
AntiMinus x R/L
```

每行至少包含：

```text
Strand label
Direction label
internal strand code
raw StartInSeq basis
raw EndInSeq basis
interval closure
orientation relative to target FASTA
forward-target interval formula
genome interval formula
TTS sequence orientation rule
query coordinate formula
source code path and line range
supported/unsupported status
```

若某组合不可达，也必须通过 fixture 证明并标记 `unreachable_by_current_runtime`，不得猜测公式。

### 6.3 Golden coordinate fixtures

至少生成：

```text
one fixture per reachable Strand/Direction combination
boundary fixture at first target base
boundary fixture at last target base
single-base interval
multi-base interval
reverse/complement sequence fixture
known hq10/hq11 fixture
```

每个 fixture 同时验证：

```text
raw fields
normalized 0-based half-open query interval
normalized forward-target 0-based half-open interval
normalized genome interval
reconstructed ungapped TTS
```

### 6.4 Query clustering midpoint

为了逐语义复现现有聚类，必须直接使用原始正整数字段：

```text
legacy_query_midpoint = int((raw_QueryStart + raw_QueryEnd) / 2)
```

实现可在正整数域写为：

```text
(raw_QueryStart + raw_QueryEnd) // 2
```

不得使用：

```text
query_midpoint_twice = normalized_start + normalized_end - 1
```

再反推 midpoint，因为这在奇偶边界和坐标基转换时不能保证复现现有实现。

### 6.5 Score integrality audit、Decimal 与整数解析

源结构中的 `triplex.score` 为浮点类型，因此不能先假设产品 Score 是整数。所有 supported rows 必须先执行：

```text
raw Score string -> decimal.Decimal
```

Phase 1 必须生成：

```text
paper/biological_topk/score_integrality_audit.tsv
paper/biological_topk/score_integrality_decision.json
```

逐来源路径证明：

```text
score_decimal == score_decimal.to_integral_value()
```

不得通过 `int(score)`、四舍五入、容差或字符串截断完成证明。

若所有 supported row/path 均通过：

```text
PROGRAM_STATE.score_representation = integral_exact
canonical/product field score_decimal_string remains required
score_integer = exact derived integer and is required
primary region score may be represented as exact integer
```

若任一 supported row/path 不能证明 integral：

```text
PROGRAM_STATE.score_representation = decimal_exact
score_decimal_string is the normative field
score_integer = null（字段仍必须存在，以保持 schema 稳定）
primary region score uses exact Decimal
```

不得因此关闭整个合同，也不得把 Decimal 值强制截断为整数。

其他字段：

```text
Nt(bp) -> exact integer
MeanStability -> decimal.Decimal from raw string
MeanIdentity(%) -> decimal.Decimal from raw string
```

禁止用 Python `float` 作为合同比较值。

Decimal 规则必须冻结：

```text
ASCII decimal regex
no NaN
no Infinity
no locale comma
preserve raw string
canonical decimal string serializer
numeric comparison through Decimal
no post-parse quantization unless source format requires it
```

### 6.6 Ungapped sequence normalization

对 `TFO sequence`、`TTS sequence`：

```text
strip only line-ending/field-external whitespace
convert ASCII letters to uppercase
remove ASCII '-' gap characters only
validate remaining alphabet against frozen operating envelope
preserve original orientation; do not reverse-complement in generic normalization
compute raw field digest and ungapped digest separately
```

不得删除任意标点、内部空格或未知 gap symbol；遇到未知字符必须 fail closed。

---

## 7. Canonical candidate-site record

每个 within-arm ranked candidate site 至少包含：

```text
workload_id
arm
ranking_mode
rank
query_ordinal_namespace
query_source_ordinal
query_sequence_sha256
target_ordinal_namespace
target_source_ordinal
target_sequence_sha256
assembly
target_coordinate_namespace
input_pair_digest
legacy_cluster_local_index
legacy_cluster_center
legacy_cluster_member_count
legacy_cluster_query_midpoint_min
legacy_cluster_query_midpoint_max
cluster_query_span_start0
cluster_query_span_end0
representative_query_start0
representative_query_end0
representative_target_start0
representative_target_end0
representative_genome_start0
representative_genome_end0
chromosome_or_target_id
direction
strand
rule
score_decimal_string
score_integer
score_representation
nt_integer
mean_stability_decimal
mean_identity_decimal
ungapped_tfo_sha256
ungapped_tts_sha256
technical_valid
strict_row_digest_diagnostic
```

### 7.1 Identity 不得包含

```text
CPU/GPU backend name
implementation numeric cluster ID
gapped TFO/TTS byte identity
CIGAR
full canonical row digest
MeanStability exact equality as an edge requirement
file row order
```

### 7.2 Representative selection

Phase 1 必须从当前实际业务代码冻结 score、stability、Nt 三种 representative/ranking 语义。不得自行设计一个“更合理”的排序。

所有 tie 字段、ascending/descending、原始数值类型和最终 fallback 必须写入：

```text
docs/biological_topk/ranking_semantics.md
```

如果现有实现最终使用 full row 或 row index 解决完全等价 tie：

```text
该 tie 行为可用于 within-arm deterministic reproduction，
但不得进入跨 arm biological identity 或 edge quality。
```

若同一 arm 在移除实现相关字段后无法唯一形成 candidate site：

```text
within_arm_ambiguous_candidate_site = 1
```

该 workload/ranking 按失败计。

---

## 8. 跨 arm 一对一 candidate-site matching

### 8.1 Matcher 前置输入身份 gate

只有 Section 5 的所有 A/G identity 字段完全相等，才允许构图。否则：

```text
matching_started = 0
input_identity_mismatch = 1
technical_failure = 1
```

### 8.2 Edge eligibility

A candidate site 与 G candidate site 只有在以下全部满足时才允许连边：

```text
same input_pair_digest
same chromosome_or_target_id
same direction
same strand
same rule
query representative reciprocal overlap >= frozen threshold
query cluster-span reciprocal overlap >= frozen threshold
target representative reciprocal overlap >= frozen threshold
```

起草默认阈值：

```text
query_representative_reciprocal_overlap_min = 0.90
query_cluster_span_reciprocal_overlap_min = 0.90
target_representative_reciprocal_overlap_min = 0.90
```

Phase 1 可在任何 fresh selection 前，仅依据历史 regression、代码语义和生物学理由确定最终阈值；Phase 1 commit 后不得修改。

Reciprocal overlap 固定定义：

```text
intersection_length / max(length_A, length_G)
```

Eligibility 使用 exact integer cross multiplication：

```text
intersection * denominator_threshold >= numerator_threshold * max_length
```

不得用 binary float 判断边界。

### 8.3 Edge quality：禁止“sum of tuples”模糊语义

每条 eligible edge 计算：

```text
target_overlap = Fraction(intersection_target, max_target_length)
query_rep_overlap = Fraction(intersection_query_rep, max_query_rep_length)
query_cluster_overlap = Fraction(intersection_query_cluster, max_query_cluster_length)
ungapped_tfo_equal = 0|1
ungapped_tts_equal = 0|1
target_endpoint_L1 = abs(startA-startG) + abs(endA-endG)
query_endpoint_L1 = abs(startA-startG) + abs(endA-endG)
cluster_center_distance = abs(centerA-centerG)
```

对一个完整 matching，objective vector 明确定义为：

```text
1. matched_edge_count                                  maximize
2. sum(target_overlap as exact Fraction)              maximize
3. sum(query_rep_overlap as exact Fraction)           maximize
4. sum(query_cluster_overlap as exact Fraction)       maximize
5. sum(ungapped_tfo_equal)                            maximize
6. sum(ungapped_tts_equal)                            maximize
7. sum(target_endpoint_L1)                            minimize
8. sum(query_endpoint_L1)                             minimize
9. sum(cluster_center_distance)                       minimize
```

比较方式：

```text
lexicographic comparison of the aggregate objective vector
```

不得对 Python tuple 做隐式求和，不得使用浮点近似，不得用 score、Nt、stability、cluster ID、row order 或 backend name 打破平局。

### 8.4 Ambiguity

若两个不同 pair sets 的 matching 在上述全部 objective component 上完全相同：

```text
ambiguous_one_to_one_matching = 1
```

影响范围：

```text
该 workload/ranking 的 complete-set success = 0
recall = 0
precision = 0
Top-1 retention = 0
ordered diagnostic = 0
```

不得通过 lexicographic row ID fallback 隐藏 ambiguity。

### 8.5 输出

每个 workload/ranking 输出：

```text
reference_candidate_count
candidate_candidate_count
matched_count
unmatched_reference_count
unmatched_candidate_count
recall
precision
top1_retained
complete_set_preserved
ambiguous_matching
match objective vector
per-pair interval overlaps
per-pair rank displacement
per-pair Score/Nt/Stability deltas
strict-row equality diagnostic
```

---

## 9. 空结果、信息量与二项 gate 分母

### 9.1 Double-empty 是唯一可从 binary denominator 排除的情形

只有同时满足以下全部条件：

```text
A technical status = success
G technical status = success
A/G input identity AND gate = pass
A output schema/checksum = valid
G output schema/checksum = valid
A candidate-site count = 0
G candidate-site count = 0
```

才允许：

```text
double_empty = 1
informative_for_recovery = 0
binary_gate_denominator_eligible = 0
```

它必须单独报告，但：

```text
不得把 recall=1
不得把 precision=1
不得计为 complete-set success
不得进入 exact-binomial 分子或分母
```

### 9.2 所有其他预冻结 primary workloads 都进入 binary denominator

以下情况全部必须：

```text
binary_gate_denominator_eligible = 1
binary_success = 0
```

包括：

```text
A non-empty / G empty
A empty / G non-empty
technical failure
OOM
timeout
non-zero exit
missing output
malformed output
schema mismatch
checksum mismatch
unexpected fallback
unsupported input discovered after execution
coordinate normalization failure
input identity mismatch
within-arm ambiguity
cross-arm ambiguity
arm isolation violation
comparator failure
```

即使 technical failure 使 `informative_for_recovery` 无法判定，也不得从 exact-binomial denominator 中删除。

### 9.3 `informative_for_recovery` 与 binary denominator 是不同字段

```text
informative_for_recovery = 1
```

只表示 A 端存在至少一个可解析 reference candidate site，可用于 recall 和 candidate-count 描述性统计。它不控制技术失败是否进入 binary gate。

默认规则：

```text
A non-empty / G empty -> informative_for_recovery=1, denominator=1, success=0
A empty / G non-empty -> informative_for_recovery=0, denominator=1, success=0
clean double-empty       -> informative_for_recovery=0, denominator=0
technical/malformed      -> informative_for_recovery=null, denominator=1, success=0
```

### 9.4 最低统计与生物信息量

Fresh panel 运行后，promotion 至少要求：

```text
binary_gate_denominator_count >= n_binary_required_from_sample_size_plan
informative_reference_nonempty_workload_count >= 60
total_reference_candidate_sites_across_informative_workloads >= 240
unique primary query count = total frozen primary workload count
unique primary target count = total frozen primary workload count
```

若预冻结 panel 运行后 binary denominator 或 reference-nonempty 信息量不足：

```text
phase_4_status = blocked_insufficient_information
```

不得运行后补样；如需新 panel，必须关闭 epoch 1，建立新 epoch 和新 exclusion registry。

### 9.5 零技术失败仍是独立 hard gate

虽然技术失败已按 `success=0` 进入 denominator，promotion 仍额外要求：

```text
technical_failure_count = 0
missing_output_count = 0
input_identity_mismatch_count = 0
ambiguous_matching_count = 0
unexpected_fallback_count = 0
```

这一附加 gate 防止“样本量很大时仍可容忍少量工程失败”的错误解释。

## 10. CPU-reference concordance 统计计划

### 10.1 主合同措辞

v1 的正式措辞固定为：

```text
Top-K candidate-site set preservation with Top-1 retention
```

不得写：

```text
complete rank-order preservation
ranking equivalence
DNA-locus preservation
```

### 10.2 每 workload binary success

对每种 ranking mode，只有当：

```text
binary_gate_denominator_eligible = 1
technical_failure = 0
ambiguous_matching = 0
reference_candidate_count > 0
matched_count = reference_candidate_count
matched_count = candidate_candidate_count
recall = 1
precision = 1
Top-1 reference site matched to Top-1 candidate site
```

才允许：

```text
binary_success = 1
complete_set_success = 1
```

当 A 只有 `<5` 个 site 时，仍要求：

```text
G candidate count == A candidate count
```

因此额外假阳性不能通过。clean double-empty 的 `binary_success` 必须为 `null`，不能写成 1。

### 10.3 Primary endpoint

主终点：

```text
score-ranked complete-set binary success rate
```

固定顺序 secondary promotion endpoints：

```text
stability-ranked complete-set binary success rate
Nt-ranked complete-set binary success rate
score Top-1 retention binary rate
stability Top-1 retention binary rate
Nt Top-1 retention binary rate
```

所有 rate 的分母均为各 endpoint 对应的 `binary_gate_denominator_eligible=1` workload；不得使用 complete-case denominator。

### 10.4 有限样本有效的主置信下界

所有 binary promotion rates 使用：

```text
one-sided exact Clopper-Pearson 95% lower confidence bound
alpha = 0.05
```

不得用 percentile bootstrap 作为 binary gate；全成功数据的退化 bootstrap 不提供有限样本不确定性。

Tests 必须固定：

```text
60/60  -> one-sided 95% LCB = 0.9512970866899025
59/60  -> one-sided 95% LCB = 0.9233600050654955
89/89  -> allowed failures = 0
100/100 gate -> minimum passing successes = 99, allowed failures = 1
150/150 gate -> minimum passing successes = 148, allowed failures = 2
```

Promotion threshold：

```text
one-sided exact LCB >= 0.95
```

### 10.5 Recall 与 precision 描述性统计

同时报告：

```text
macro Top-K recall
macro Top-K precision
micro matched/reference
micro matched/candidate
all-five-or-all-available set preservation
```

连续/分数指标的 query-level bootstrap仅用于描述性 CI，不得替代 exact binary promotion gate。

### 10.6 Ordered candidate-site diagnostic

为了量化第 2–5 名重排，Phase 1 必须冻结一个 rank-sensitive diagnostic。默认使用：

```text
finite Rank-Biased Overlap at depth K=5
p = 0.90
matching identity = frozen one-to-one candidate-site pairs
```

必须写出精确有限列表公式、不同列表长度处理和 empty 处理。

本 epoch：

```text
ordered metric = key secondary diagnostic
rank-order product claim = diagnostic_only
```

只有未来另立合同并预注册 ordered gate，才能声称 rank-order preservation。

### 10.7 固定顺序与多重性

固定顺序：

```text
score complete-set pass
-> stability complete-set test
-> Nt complete-set test
-> Top-1 tests
```

前一 gate 失败，后续仍报告但不得 promotion。样本量的 80% power 目标默认针对 primary score complete-set gate；所有 secondary gate 必须报告同一 `p_alt` 下的 marginal power。除非 Phase 1 另外冻结相关结构与联合模拟，本 epoch 不宣称 80% joint power；这一严格固定顺序是有意设计，不得在结果后更换 gate。

### 10.8 零失败附加条件

即使 exact LCB 通过，promotion 仍要求：

```text
technical_failure_count = 0
missing_output_count = 0
input_identity_mismatch_count = 0
ambiguous_matching_count = 0
unexpected_fallback_count = 0
```

## 11. Source universe freeze 与 fresh panel feasibility

### 11.1 不得直接复用旧 50x668 panel

旧 application panel：

```text
selected queries = 50
targets = 668
target length = 2501 bp for all targets
```

它无法满足：

```text
>=60 unique fresh queries
>=3 target-scale strata
```

因此 Phase 1 必须建立新的、输入独立的 source universe。

### 11.2 Query source universe

必须从冻结的 annotation/FASTA 重建完整候选 universe，并记录至少：

```text
annotation release
assembly
FASTA/GTF SHA-256
query ordinal namespace
source ordinal
transcript ID
gene ID
biotype
sequence length
sequence SHA-256
GC fraction
repeat/static complexity proxy
primary chromosome status
operating-envelope eligibility
historical exclusion status
```

已知上游 representative query universe 约 27,125 条；Codex 必须重建实际数字，不能硬编码。

### 11.3 Target source universe

必须从冻结 genome/annotation 构建至少 3 个 **输入定义的** target-scale strata。

Phase 1 在任何 prediction 前，通过静态资源模拟冻结：

```text
window recipes
length bins
coordinate extraction
chromosome-boundary handling
strand handling
assembly
ordinal namespace
```

允许的默认候选 recipes（可在 Phase 1 仅依据输入和预算修正）：

```text
short  = promoter-scale window
medium = regulatory-neighborhood window
large  = regional-screening window
```

最终必须满足：

```text
three non-overlapping target length/scale strata
sufficient fresh target digests in each stratum
all within fixed operating envelope and budget
```

不得在看 A/G 输出后改变 window size。

### 11.4 Rule/Strand coverage

`Rule` 与输出 `Strand` 是运行结果，不能用于 input-only selection。

Fresh plan 只能预注册：

```text
observed_rule_coverage = report_only
observed_strand_coverage = report_only
```

不得因运行后某 rule/strand 覆盖不足而补样或替换 workload。

### 11.5 Fresh exclusion registry

字段必须与现有 namespaced registry 结构兼容：

```text
record_type
query_ordinal_namespace
query_source_ordinal
target_ordinal_namespace
target_source_ordinal
query_id
target_id
query_sha256
target_sha256
query_region
target_region
assembly
coordinate_namespace
pair_digest
source_receipt_path
exclusion_reason
```

Fresh selection 与任何历史记录出现以下任一重叠即拒绝：

```text
same query sequence digest
same namespaced query ordinal
same target sequence digest
same namespaced target ordinal
same pair digest
same experimental dataset accession used for development
```

不得提供 override。

### 11.6 Fresh sample-size planning：信息量与 concordance power 双重约束

Phase 1 必须在运行前生成：

```text
paper/biological_topk/fresh_information_feasibility.json
paper/biological_topk/sample_size_plan.json
```

#### A. Exact-binomial concordance power

默认设计参数必须在任何 fresh selection 前冻结：

```text
alpha = 0.05
required one-sided CP LCB = 0.95
alternative complete-set success rate p_alt = 0.99
minimum primary-gate power = 0.80
minimum denominator floor = 60
```

对每个候选 denominator size `n`，脚本必须精确枚举：

```text
k_min(n) = 最小成功数，使 CP_LCB(k_min, n) >= 0.95
power(n) = Pr[K >= k_min(n) | K ~ Binomial(n, p_alt)]
```

并选择满足 floor 与 power 的最小 `n_binary_required`。默认参数的强制 fixture 为：

```text
n = 123: k_min = 122, allowed failures = 1, power = 0.651398441786（约）
n = 124: k_min = 122, allowed failures = 2, power = 0.871553509746（约）
```

因此默认设计下：

```text
n_binary_required = 124
```

这比原来的 60-workload 信息量 floor 更严格，是有意的统计收紧。脚本还必须输出用户评审中的 sanity fixtures：

```text
n=60  -> 0 failures allowed; power at p=.99 ≈ 0.547156642391
n=89  -> 0 failures allowed; power at p=.99 ≈ 0.408820174423
n=100 -> 1 failure allowed;  power at p=.99 ≈ 0.735761978923
n=150 -> 2 failures allowed; power at p=.99 ≈ 0.809481862016
```

#### B. 获得足够 denominator-eligible workloads 的概率

只有 clean double-empty 可从 denominator 排除，因此 planning 参数应命名为：

```text
p_binary_denominator_eligible_planning
```

允许用历史 regression 估计该概率，但只用于 planning，并必须使用保守下界。预冻结总 panel 大小 `N_panel` 必须满足：

```text
Pr[Binomial(N_panel, p_binary_denominator_eligible_planning)
   >= n_binary_required] >= 0.95
```

若没有可信 estimate，默认：

```text
p_binary_denominator_eligible_planning = 0.75
```

在默认 `n_binary_required=124` 下，强制 fixture 为：

```text
N_panel = 178
Pr(eligible_count >= 124) = 0.955969707503（约）
```

#### C. Reference-nonempty、candidate-site 数量与联合前瞻可行性

仅保证 denominator 数量不足以保证最终获得 60 个 reference-nonempty workload 和 240 个 reference candidate sites。Phase 1 必须额外冻结：

```text
p_reference_nonempty_planning
reference_candidate_count_distribution_planning
reference_candidate_count_definition
joint_outer_bootstrap_seed = 20260731
joint_inner_simulation_seed = 20260801
joint_outer_bootstrap_replicates >= 2000
joint_inner_panel_simulations_initial >= 10000
joint_inner_panel_simulations_max >= 100000
joint_inner_mc_halfwidth_max = 0.005
joint_outer_lcb_quantile = 0.05
```

`reference_candidate_count_definition` 固定为：

```text
每个 workload 的 CPU A arm 中，score ranking 下去重后的 canonical candidate-site 数量，
K 上限为 5；不得把 score/stability/nt 三种列表简单相加。
```

Planning 数据只能来自 development/regression evidence，且必须与 fresh panel 使用相同 operating envelope。每条历史 planning row 必须保留联合 tuple：

```text
(target_scale_stratum,
 denominator_eligible_indicator,
 reference_nonempty_indicator,
 reference_candidate_site_count)
```

联合不确定性必须分成两个层级，不能把内层 Monte Carlo 次数当作真实独立证据量：

```text
outer bootstrap development planning rows
    -> 得到一个可能的 development joint distribution
    -> 在该 outer replicate 内模拟完整固定配额 panel
    -> 计算该 replicate 的 joint success probability q_b
```

对每个 outer replicate `b`：

1. 按冻结 target-scale strata 和独立 development planning unit 做有放回 bootstrap；
2. 从 bootstrap 后的每个 stratum 联合 tuple 分布中，按计划配额模拟完整 `N_panel`；
3. 一次 inner panel 只有在以下三项同时满足时记为 success：

```text
eligible_count >= n_binary_required
reference_nonempty_count >= 60
total_reference_candidate_sites >= 240
```

4. 令：

```text
q_b = inner_joint_success_count / inner_panel_simulation_count
```

`joint_information_probability_point` 固定为在**未 bootstrap 的原 development empirical distribution**上计算的 joint success probability。最终 planning 下界固定为 outer `q_b` 分布的单侧 5% empirical quantile：

```text
joint_information_probability_lcb = empirical_quantile_0.05({q_b})
```

quantile 使用预注册的不插值 order-statistic 定义：对升序 `q_(1)...q_(B)`，取：

```text
q_(ceil(0.05 * B))
```

Promotion gate 仍为：

```text
joint_information_probability_lcb >= 0.95
```

内层 simulation 只用于估计每个 `q_b`，不得对内层 success count 计算 Clopper-Pearson 后将其当成 development-distribution uncertainty。每个 outer replicate 从初始 inner 次数开始；若该 `q_b` 的预注册 95% binomial Monte Carlo interval half-width 超过 `0.005`，必须按 2 倍递增 inner simulations，最多到 `joint_inner_panel_simulations_max`。达到上限仍不满足精度时：

```text
phase_1_status = blocked_insufficient_information
reason = joint_information_inner_mc_precision_not_met
```

必须另行报告：

```text
outer q_b point distribution
outer 5% quantile
inner simulation counts per outer replicate
inner Monte Carlo interval/half-width audit
两组独立 inner seeds 对原 empirical distribution 与 5% boundary outer replicates 的复算差异
```

同时报告各单项概率、`p_reference_nonempty_planning`、每个 stratum 的 0–5 candidate-count distribution、联合相关性，以及 outer-bootstrap uncertainty。若 development evidence 无法支持任一计划 stratum 的联合模型，必须：

```text
phase_1_status = blocked_insufficient_information
```

不得使用乐观默认值，也不得在 fresh 运行后补样。

#### D. Phase 4 前瞻资源与固定预算 gate

Phase 1 必须仅使用历史/development timing 建立输入驱动的 A/G 资源模型，禁止运行 fresh panel。至少使用：

```text
query length
target length
query_length * target_length
target-scale stratum
static sequence-complexity proxy
fixed CPU/GPU execution configuration
```

分别建模并冻结：

```text
projected CPU aggregate wall seconds
projected GPU aggregate wall seconds
projected GPU-hours
projected scheduled elapsed wall seconds
projected artifact/storage bytes
one-sided 95% upper resource bound for each primary quantity
```

`paper/biological_topk/fresh_budget_projection_plan.json` 还必须在任何 fresh selection 前冻结：

```text
max_formal_scheduled_wall_seconds = 172800
max_gpu_hours = 72
max_artifact_storage_bytes = <owner-approved positive integer>
```

`max_artifact_storage_bytes` 不得在看到 manifest projection 后上调；若 owner 未提供可审计的固定 quota，Phase 1 不得宣称 resource gate 已冻结。

模型、bootstrap 层级、seed、residual treatment 和 scheduler simulation 必须在 Phase 1 固定；默认至少 10,000 次 stratified bootstrap。Phase 3 在 exact fresh manifest 冻结后必须重新生成 manifest-specific projection，但不得改变模型。

候选 `N_panel` 必须同时满足：

```text
exact-binomial power gate
joint information probability LCB >= 0.95
fresh unique query/target universe capacity
projected elapsed-wall upper bound <= 48 hours
projected GPU-hours upper bound <= 72
```

若最小统计有效 panel 在冻结硬件与调度下超过预算：

```text
phase_3_status = blocked_fixed_budget
Phase 4 not authorized
```

不得降低 `n_binary_required`、60 nonempty、240 sites 或 confidence threshold 来适配预算。

最终 `sample_size_plan.json` 必须同时记录：

```text
primary alternative p
power target
n_binary_required
k_min
allowed failures
achieved power
eligibility probability
p_reference_nonempty_planning
reference_candidate_count_distribution_planning
N_panel
Pr(eligible_count >= n_binary_required)
Pr(reference_nonempty_count >= 60)
Pr(total_reference_candidate_sites >= 240)
joint_information_probability_point
joint_information_probability_lcb
joint_outer_bootstrap_replicates
joint_outer_lcb_quantile
joint_inner_simulations_min/max/actual distribution
joint_inner_mc_halfwidth_max
joint_inner_mc_precision_pass
resource_projection_model_sha256
projected CPU/GPU/elapsed/storage point estimates and upper bounds
secondary marginal powers
joint-power claim = primary_joint_information_model_frozen
```

`N_panel` 必须选择为同时满足统计、联合信息量、source universe 和固定预算的最小整数。技术 repeats 不增加 independent n，也不能弥补 unique query/target 不足。

## 12. Experimental biological utility：决定性定义

### 12.1 CPU concordance 与 experimental utility 完全分离

CPU 只回答：

```text
G 是否保留历史 Fasim 方法的 candidate sites
```

实验数据回答：

```text
G 是否对真实 RNA-DNA occupancy / binding labels 有预测价值
```

任何一个不得替代另一个。

### 12.2 Historical development 数据登记

Phase 0/5 必须将所有曾用于开发、论文、generalization 或参数判断的 lncRNA/dataset 登记为 development，包括已使用的：

```text
MEG3
MALAT1
NEAT1
H19
KCNQ1OT1
及其历史 assay/accession/segment/digest
```

这些数据可用于 pipeline regression 和 power simulation，但不得作为本 epoch primary independent biological evaluation。

### 12.3 合法 query 构造

Primary evaluation query 只能来自：

```text
A. 冻结 annotation 中完整 transcript/isoform，长度在 operating envelope 内；
或
B. 在 prediction 前由独立文献、实验探针设计、功能结构域注释或预先存在的数据库定义的短 domain/isoform。
```

禁止：

```text
根据 GPU/CPU 结果选择 5'/mid/3' segment
任意截断长 lncRNA 以获得更好指标
使用历史 MALAT1/NEAT1 segments 作为 primary independent evaluation
```

完整 MALAT1、NEAT1 等超出 `2812` 的 query 不得直接进入 primary GPU evaluation。若使用独立定义的短结构域，必须冻结：

```text
source citation/accession
full transcript ID
segment coordinates
biological rationale
sequence digest
selection timestamp before predictions
```

### 12.4 Target-region prediction score

Phase 5 必须在读取任何 evaluation prediction 前冻结“每个 target region 如何得到一个标量分数”。默认 primary 定义：

```text
1. 对该 query-target region 运行固定 pipeline；
2. 只保留满足现有有效性规则和 Nt(bp) > 50 的 candidate rows；
3. primary_region_score = maximum exact Score among valid rows；
4. score_representation=integral_exact 时使用 exact integer；
5. score_representation=decimal_exact 时使用 canonical exact Decimal string/value；
6. 无 valid row：使用冻结 scoring lower bound 以下的 deterministic sentinel；
7. 相同 score 的排序不读取 label，以固定 target identity 处理 ties；
8. CPU 与 GPU 使用完全相同的 region-scoring function。
```

Phase 5 必须从 scoring source code证明合法最低分并冻结 sentinel；不得在结果后选择 max stability、candidate count 或其他更有利聚合。

Secondary 可报告：

```text
max Nt
max MeanStability
valid candidate count
candidate density
```

但不得替换 primary。

### 12.5 K 的定义

Primary screening endpoint：

```text
recall@P_d
P_d = dataset d 在冻结过滤后 positive target regions 的数量
```

即每个 dataset 检查 top `P_d` predictions 能恢复多少 positives。

Secondary：

```text
recall@10
recall@50
recall@100
precision@10/50/100
```

若 dataset 总 region 数小于 K，使用 `min(K, N_d)` 并在 manifest 中预先确定。

### 12.6 独立单位、嵌套结构与 pooled estimand

Clopper-Pearson fresh concordance 的 primary workloads必须使用 unique query 与 unique target；实验效用的独立性则以**distinct lncRNA**为 outer unit。

同一 lncRNA 的多个 assay、dataset、replicate 或 peak caller output 均视为嵌套单位，不能作为多个独立 outer units。

每个 dataset 先计算：

```text
AUCPR_d
recall_at_P_d
prevalence_d
fold_enrichment_d = precision_at_P_d / prevalence_d
log_enrichment_d = natural_log(fold_enrichment_d)
GPU_minus_CPU_AUCPR_d
GPU_minus_CPU_recall_d
GPU_AUCPR_minus_prevalence_d
```

若任一 **primary dataset** 的 `precision_at_P_d = 0`，该 dataset 不产生可聚合的有限 `log_enrichment`，并按以下确定性规则处理：

```text
zero_precision = true
log_enrichment = null
endpoint_status = automatic_failure
containing_lncRNA_E4_status = automatic_failure_zero_precision
global_E4_status = fail
biological_utility_intersection_union_gate = fail
```

不得结果后加 pseudocount，不得把 `null` 替换成有限数，不得先忽略该 dataset 后在 lncRNA 内聚合，也不得通过 bootstrap 数值替代。E1–E3 可以继续计算为诊断结果，但本 epoch 的 biological utility 总 gate 已因 E4 自动失败。

只有当某个 lncRNA 的**全部 primary datasets**均具有 `precision_at_P_d > 0` 时，才允许按 Phase 5 冻结的等权规则聚合其有限 `log_enrichment` 为 lncRNA-level E4 estimand；随后在 distinct lncRNAs 之间等权 macro mean。不得把所有 regions、datasets 或 assays 直接拼接，让大数据集或重复 assay 支配结果。

Region-count-weighted、dataset-level 和 assay-level结果只能作为 secondary diagnostics。

### 12.7 Minimum independent information 与 assay availability

Promotion 默认要求：

```text
>= 5 distinct evaluation lncRNAs
每个 lncRNA 至少 1 个合法 primary dataset
outer independent unit count = distinct lncRNA count
```

`assay_type_available` 必须在 Phase 5 inventory freeze 时按 input/data 条件确定，而不是运行后决定。一个 assay type 只有在以下全部满足时才算 available：

```text
存在至少一个未被 development registry 消耗的公开或合法可访问 dataset；
query 构造在 operating envelope 内且在 prediction 前确定；
genome build、positive/negative labels、region universe 可确定重建；
数据和 metadata 足以完成预注册 estimand；
该 dataset 属于一个尚未被另一 primary outer unit复用的 distinct lncRNA。
```

若 inventory 中有至少两个满足以上定义的 assay types，primary panel 必须覆盖至少两个；若只有一个，允许继续，但必须明确：

```text
cross_assay_generality_claim = not_supported
```

### 12.8 Power/feasibility simulation

在下载/运行 primary predictions 前，固定：

```text
plausible prevalence range
regions per dataset
within-dataset correlation/block size
within-lncRNA cross-assay correlation
expected AUCPR range
non-inferiority margins
number of distinct lncRNA outer units
nested dataset/assay counts
bootstrap method
simulation seed
replicates >= 10000
```

输出：

```text
paper/biological_topk/experimental_power_simulation.json
paper/biological_topk/experimental_information_decision.json
```

若 `<5` distinct lncRNAs，或 simulation 显示预注册 margins 下不能提供可识别的 one-sided CI：

```text
phase_5_status = blocked_insufficient_experimental_information
```

不得把同一 lncRNA 的多个 assays 当作增加 outer n 的方式救援。

### 12.9 四个 co-primary 终点与 intersection-union gate

四个 endpoint 必须在运行前全部冻结，并全部通过：

```text
E1 non-inferiority:
LCB[macro_lncRNA(GPU AUCPR - CPU AUCPR)] >= -0.02

E2 non-inferiority:
LCB[macro_lncRNA(GPU recall@P_d - CPU recall@P_d)] >= -0.05

E3 absolute utility:
LCB[macro_lncRNA(GPU AUCPR - prevalence)] > 0

E4 absolute utility:
LCB[macro_lncRNA(log(GPU top-P fold enrichment))] > 0
```

总体 biological-utility gate 是固定的 intersection-union test：

```text
biological_utility_pass = E1 AND E2 AND E3 AND E4
```

每个 component 使用 one-sided alpha `0.05`。因为只有全部 component null 都被拒绝才 promotion，不得在结果后从四个 endpoint 中选择子集，也不得运行后改为更有利的多重性方法。

### 12.10 Paired hierarchical resampling

Phase 5 必须根据 power simulation冻结单一主方法。默认：

```text
outer resampling unit = distinct lncRNA
nested level 1 = dataset/assay within sampled lncRNA
nested level 2 = chromosome or frozen genomic block within dataset
paired A/G values remain paired at every level
replicates = 10000
fixed seed
one-sided percentile or basic interval method frozen before predictions
```

所有四个 co-primary contrast 使用同一 resample index；不得分别寻找更有利 seed 或 interval method。

若 outer lncRNA units 太少导致方法无效，必须 blocked，而不是运行后把 dataset/assay 当作独立 outer units。

## 13. GPU operating envelope

Phase 1 必须冻结：

```text
runtime_mode = normal-triplex fast Top-K
query_length_min
query_length_max = 2812
target scale recipes and length bounds
K = 5
legacy cluster distance = 15
legacy minimum Nt rule = Nt(bp) > 50
supported alphabet
scoring parameters
supported runtime modes
GPU model(s)
CUDA driver/runtime
workers per GPU
number of GPUs
batching policy
memory guard
OOM behavior
unexpected fallback behavior
unsupported-input behavior
```

`2812` 是实现范围，不是所有 short lncRNA 的生物学定义。

若只验证 RTX 4090，论文必须明确单 GPU generation limitation。

---

# Phase 0 — 独立 epoch、历史 blob 与 exclusion registry

## 0A. 目标

建立独立 epoch，绑定历史结论，不修改旧状态。

## 0B. 必须产出

```text
goal-biological-topk.md
paper/biological_topk/STATUS.md
paper/biological_topk/PROGRAM_STATE.json
paper/biological_topk/epoch_receipt.json
paper/biological_topk/historical_blob_registry.tsv
paper/biological_topk/fresh_input_exclusion_registry.tsv
paper/biological_topk/claim_ledger.tsv
paper/biological_topk/phase_0_change_allowlist.txt
schemas/biological_topk_program_state.schema.json
reproduce/biological_topk/build_historical_blob_registry.py
reproduce/biological_topk/build_exclusion_registry.py
scripts/check_biological_topk_phase.py
scripts/check_biological_topk_all.sh
scripts/check_biological_topk_phase0.sh
```

## 0C. Historical blob registry

至少绑定 Section 2.5 所列历史文件。读取方式必须是：

```text
git show execution_start_head:path
```

而不是直接假设 live path 不变。

## 0D. Exclusion registry

从全部历史 correctness、pilot、performance、debug/minimization、generalization、canonical-hybrid-v2、SSW-CUDA 和 experimental development receipts 提取 namespaced identity。

## 0E. Gate

```text
pre-file-creation clean check recorded
protocol_source_sha256 recorded
goal-biological-topk.md is in Phase 0 allowlist
phase start tree clean
actual execution HEAD recorded
old decision strings unchanged in frozen blobs
historical registry rebuilds byte-for-byte
exclusion registry rebuilds byte-for-byte
PROGRAM_STATE validates against schemas/biological_topk_program_state.schema.json
PROGRAM_STATE schema rejects unknown fields, unknown enum values and illegal transitions
no new scientific run started
only phase-0 allowlisted changes before commit
post-commit read-only check specified; next phase start must confirm clean
bioinformatics_route = conditionally_reopened
gpu_screen_status = experimental
```

失败：

```text
missing evidence -> blocked_missing_evidence
registry cannot rebuild -> blocked_missing_evidence
old state altered -> blocked_missing_evidence
```

建议 commit：

```text
docs: freeze biological Top-K candidate-site validation epoch
```

---

# Phase 1 — 冻结科学对象、坐标、匹配、统计、source universe 与实验可行性

## 1A. 目标

在选择任何 fresh pair 或运行任何新 prediction 前，把所有科学规则写死。

## 1B. 必须产出

```text
docs/biological_topk/scientific_object.md
docs/biological_topk/legacy_clustering_semantics.md
docs/biological_topk/coordinate_mapping.md
docs/biological_topk/coordinate_mapping_table.tsv
docs/biological_topk/canonicalization_spec.md
docs/biological_topk/ranking_semantics.md
docs/biological_topk/matching_spec.md
docs/biological_topk/statistical_analysis_plan.md
docs/biological_topk/source_universe_spec.md
docs/biological_topk/experimental_estimand_spec.md
docs/biological_topk/operating_envelope.md
paper/biological_topk/contract_spec.json
paper/biological_topk/legacy_clustering_fixtures.tsv
paper/biological_topk/coordinate_golden_fixtures.tsv
paper/biological_topk/query_source_universe.tsv.gz
paper/biological_topk/target_source_universe.tsv.gz
paper/biological_topk/source_universe_receipt.json
paper/biological_topk/fresh_information_feasibility.json
paper/biological_topk/sample_size_plan.json
paper/biological_topk/concordance_power_plan.json
paper/biological_topk/joint_information_model.json
paper/biological_topk/joint_information_simulation.json
paper/biological_topk/score_integrality_audit.tsv
paper/biological_topk/score_integrality_decision.json
paper/biological_topk/resource_projection_model.json
paper/biological_topk/resource_projection_model_receipt.json
paper/biological_topk/fresh_budget_projection_plan.json
paper/biological_topk/experimental_power_simulation_plan.json
paper/biological_topk/operating_envelope.json
paper/biological_topk/phase_1_change_allowlist.txt
schemas/biological_topk_contract.schema.json
scripts/check_biological_topk_phase1.sh
```

## 1C. Source universe freeze

必须：

```text
rebuild the full representative query universe
build three input-only target-scale strata
apply historical exclusions
record all namespaced ordinals/digests/assembly/recipes
prove >= planned N_panel fresh unique queries and >= planned N_panel fresh unique targets
```

Rule/Strand 不作为 selection strata。

## 1D. Statistical feasibility

Checker 必须验证：

```text
60/60 and 59/60 CP fixtures
123/124 power-boundary fixtures at p_alt=0.99
n_binary_required computed by exact enumeration
planned N_panel satisfies denominator-eligibility probability >=0.95
outer-development-bootstrap joint information probability LCB for eligible/nonempty/240-sites >=0.95
resource-model and fixed-budget projection rules are frozen
at least planned N_panel fresh unique query digests and namespaced ordinals exist
a distinct fresh target digest and namespaced target ordinal exists for every primary workload
three target-scale strata exist after exclusion
secondary marginal powers are recorded
joint-power claim is explicitly not made unless separately simulated
```

## 1E. Tests

至少覆盖：

```text
Nt 49/50/51 boundary
legacy midpoint even/odd boundaries
all reachable Strand/Direction coordinate mappings
target first/last base
input identity AND semantics
namespaced ordinal mismatch
Decimal parsing
Score integrality proof and decimal_exact fallback
ungapped normalization
same candidate site different CIGAR
same candidate site 3-bp target extension
true different query cluster
true different target region
precision failure from extra G site
A/G double empty non-informative
A empty/G nonempty failure
multiple unique matching
multiple equivalent matching ambiguity
CP 60/60 and 59/60
CP power fixtures for n=60/89/100/123/124/150
joint information model uses workload-level eligible/nonempty/site-count tuples
outer bootstrap resamples development distributions before inner panel simulation
inner Monte Carlo count is not treated as independent scientific evidence
joint information outer-quantile LCB is finite and >=0.95
inner Monte Carlo precision audit meets frozen half-width
resource projection uses only input features and historical timing
binary denominator includes technical failure and excludes only clean double-empty
```

## 1F. Rule freeze

Phase 1 commit 后禁止：

```text
scientific-object change
overlap threshold change
K change
minimum Nt boundary change
confidence method change
non-inferiority margin change
region-score function change
K for biological recall change
source-universe recipe change
```

任何变更必须关闭 v1，建立 v2。

## 1G. Gate

```text
all schemas validate
all fixtures pass
source universe frozen before fresh selection
coordinate mapping proven for every reachable mode
sample-size plan passes exact-gate power, denominator-yield, reference-nonempty, 240-site joint feasibility, and fixed-budget feasibility
experimental power plan defined
no fresh pair selected
no new prediction run
phase allowlist valid
post-commit read-only check specified; next phase start must confirm clean
```

最多 mechanism repairs：3。超过：

```text
phase_1_status = no_go
reason = unable_to_define_deterministic_candidate_site_contract
```

建议 commit：

```text
repro: freeze candidate-site contract, source universe, and statistical gates
```

---

# Phase 2 — Comparator 实现与历史 regression

## 2A. 目标

实现 canonicalizer、legacy cluster reproduction、candidate-site matcher 和统计组件。只使用已消费数据，绝不 promotion。

## 2B. 必须实现

```text
reproduce/biological_topk/canonicalize_rows.py
reproduce/biological_topk/recluster_candidate_sites.py
reproduce/biological_topk/match_candidate_sites.py
reproduce/biological_topk/compare_candidate_topk.py
reproduce/biological_topk/exact_binomial_bounds.py
reproduce/biological_topk/rank_diagnostics.py
```

CLI：

```text
--authority
--candidate
--authority-receipt
--candidate-receipt
--contract-spec
--output-json
--details-tsv
--fail-closed
```

默认 fail closed。

## 2C. 已知 mismatch fixtures

必须得到：

```text
hq10_ht02:
  strict-row diagnostic = mismatch
  candidate-site unique match = yes
  set membership = preserved

hq11_ht02:
  strict-row diagnostic = mismatch
  target reciprocal overlap = 62/65
  candidate-site unique match = yes
  set membership = preserved
```

不得识别 workload ID 实现特例。

## 2D. 历史 regression

至少包括：

```text
Phase 2 36 attempts
canonical-hybrid-v2 regression 36 attempts
canonical-hybrid-v2 former fresh holdout 60 attempts, regression-only
historical paper core/generalization panels where artifacts exist
```

输出分类：

```text
representation-only difference
same candidate site endpoint shift
set-preserving rank displacement
true candidate-site substitution
extra candidate site
missing candidate site
ambiguous matching
strict-row diagnostic mismatch
```

不得调整 contract 追求全 pass。

## 2E. Freeze comparator

冻结：

```text
source commit
Python version
contract SHA-256
coordinate mapping SHA-256
comparator SHA-256
fixture SHA-256
expected regression digest
```

## 2F. Gate

```text
known cases classified without special cases
legacy clustering output matches golden fixtures
input mismatch fails before matcher
all regression deterministic
no parser/comparator technical failures
no independent-validation claim
phase allowlist valid
post-commit read-only check specified; next phase start must confirm clean
```

建议 commit：

```text
test: freeze clustered TFO candidate-site comparator regression
```

---

# Phase 3 — Fresh CPU-reference concordance panel 冻结

## 3A. 目标

从 Phase 1 source universe 中，按 input-only 规则选取未参与任何开发或运行的 panel。

## 3B. 选择允许字段

```text
namespaced source ordinal
sequence length
GC fraction
static repeat/complexity proxy
chromosome
transcript biotype
assembly
target scale stratum
hash ordering
```

禁止：

```text
CPU/GPU output
predicted Score/Nt/Stability
number of candidates
Rule/Strand output
known pass/fail
query/gene whitelist
post-run supplementation
```

## 3C. Panel 规模与 independent workload 单位

使用 Phase 1 `sample_size_plan.json` 的冻结数字。Primary workload 必须同时满足：

```text
preselected primary workloads = planned N_panel
每个 primary workload 使用唯一 query sequence digest
每个 primary workload 使用唯一 namespaced query ordinal
每个 primary workload 使用唯一 target sequence digest
每个 primary workload 使用唯一 namespaced target ordinal
同一 query 或 target 不得出现在两个 primary workloads 中
>=3 query-length strata
>=3 target-scale strata
balanced static strata when feasible
fixed technical repeat subset, not counted as independent n
```

unique query 不足、unique target 不足或需要复用任何 primary query/target 时：

```text
phase_3_status = blocked_insufficient_source_universe
```

本 epoch 不在运行后改用 target-cluster/stratified inference；若未来需要复用 target，必须另立合同并预注册相关结构。

## 3D. Exclusion hard gate

逐项检查：

```text
query digest
namespaced query ordinal
target digest
namespaced target ordinal
pair digest
historical dataset accession
debug/minimization identity
```

任何重叠：

```text
exit non-zero
no final manifest
```

## 3E. A/G attempt plan

冻结：

```text
identical A/G input pair digest
identical parameter bundle
balanced execution order
independent artifact roots
GPU mapping
CPU affinity
workers per GPU
timeouts
memory limits
no automatic retries
comparison starts only after both arms complete
exact analysis command
```

## 3F. 必须产出

```text
paper/biological_topk/fresh_holdout_plan.json
paper/biological_topk/fresh_holdout_manifest.tsv
paper/biological_topk/fresh_holdout_attempt_plan.tsv
paper/biological_topk/fresh_holdout_manifest.sha256
paper/biological_topk/fresh_holdout_resource_projection.json
paper/biological_topk/fresh_holdout_resource_decision.json
paper/biological_topk/phase_3_change_allowlist.txt
reproduce/biological_topk/freeze_fresh_holdout.py
reproduce/biological_topk/run_fresh_holdout.py
reproduce/biological_topk/analyze_fresh_holdout.py
scripts/check_biological_topk_phase3.sh
```

## 3G. Gate

```text
input-only selection
planned N_panel met
all primary query digests/ordinals unique
all primary target digests/ordinals unique
zero historical overlap
A/G identity exact AND gate passes
contract/comparator/runtime bound by digest
manifest-specific resource projection uses frozen Phase 1 model
projected CPU aggregate-wall upper bound recorded
projected GPU aggregate-wall upper bound recorded
projected elapsed-wall upper bound <=48 hours
projected GPU-hours upper bound <=72
projected storage upper bound <= frozen Phase 1 quota
resource decision = pass
no scientific output before freeze commit
phase allowlist valid
post-commit read-only check specified; next phase start must confirm clean
```

建议 commit：

```text
repro: freeze fresh clustered TFO candidate-site holdout
```

---

# Phase 4 — Fresh concordance execution 与 decision

## 4A. 执行

严格按 attempt plan 执行一次完整 epoch。不得补样、替换、删除失败或重排主分析。

## 4B. Source data

```text
paper/biological_topk/source_data/fresh_candidate_matches.tsv
paper/biological_topk/source_data/fresh_workload_metrics.tsv
paper/biological_topk/source_data/fresh_empty_workloads.tsv
paper/biological_topk/source_data/fresh_failure_ledger.tsv
paper/biological_topk/source_data/fresh_exact_binomial_bounds.tsv
paper/biological_topk/source_data/fresh_rank_diagnostics.tsv
paper/biological_topk/fresh_holdout_receipt.json
paper/biological_topk/fresh_holdout_decision.json
```

## 4C. Promotion gate

必须同时满足：

```text
binary gate denominator count >= n_binary_required_from_sample_size_plan
informative reference-nonempty workload count >= 60
total reference candidate sites >= 240
all frozen primary query digests and namespaced ordinals unique
all frozen primary target digests and namespaced ordinals unique
score complete-set success one-sided exact 95% LCB >= 0.95
stability complete-set success one-sided exact 95% LCB >= 0.95
Nt complete-set success one-sided exact 95% LCB >= 0.95
score Top-1 retention exact LCB >= 0.95
stability Top-1 retention exact LCB >= 0.95
Nt Top-1 retention exact LCB >= 0.95
technical failures = 0
missing outputs = 0
input identity mismatches = 0
ambiguous matches = 0
unexpected fallbacks = 0
```

只有 clean double-empty 可设置 `binary_gate_denominator_eligible=0`。technical/missing/malformed/ambiguous workload 必须作为 `success=0` 进入 exact-binomial denominator。

Ordered RBO 仅 diagnostic，不决定 v1 promotion，也不得据此写完整 rank-order preservation。

## 4D. 状态转换

Pass：

```text
PROGRAM_STATE.contract_status = "fresh_concordance_pass"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "conditionally_reopened"
```

No-go：

```text
PROGRAM_STATE.contract_status = "concordance_no_go"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "closed_for_this_contract"
PROGRAM_STATE.phase_status["5"] = "not_authorized_previous_no_go"
```

信息量不足：

```text
PROGRAM_STATE.phase_status["4"] = "blocked_insufficient_information"
no supplementation in epoch v1
```

## 4E. 预算

Phase 4 只有在 Phase 3 manifest-specific resource decision 已通过时才可启动：

```text
projected elapsed-wall one-sided 95% upper bound <= 48 hours
projected GPU-hours one-sided 95% upper bound <= 72
max formal wall budget = 48 hours
max GPU-hours = 72
max infrastructure repair epochs = 1
```

实际执行达到任一固定 budget 时必须停止并保留 partial evidence；不得删除已完成/失败 attempts 后缩小 panel。Repair 只能修 runner/infrastructure；新 epoch 必须从全部 attempt 重跑，保留旧失败 receipts。

建议 commit：

```text
bench: freeze fresh candidate-site concordance decision
```

---

# Phase 5 — Independent experimental benchmark 预注册

## 5A. 目标

在任何 primary evaluation prediction 前，冻结 dataset、合法 query、labels、region score、K、estimand、weighting、power 和 external tools。

## 5B. Inventory

```text
paper/biological_topk/experimental_development_registry.tsv
paper/biological_topk/experimental_evaluation_inventory.tsv
```

字段：

```text
dataset_id
outer_lncRNA_id
lncRNA
assay
assay_type_class
assay_type_available
availability_reason
accession
publication
genome_build
query construction type
full transcript/domain coordinates
query length
sequence digest
positive definition
negative definition
license
development_or_evaluation
failure reason
```

### 5C. Minimum information

默认：

```text
>=5 distinct lncRNA outer units
每个 lncRNA 至少 1 个合法 primary dataset
若 Phase 5 inventory 中 >=2 assay types 满足 frozen availability definition，则必须覆盖 >=2 assay types
```

同一 lncRNA 的多个 assays/datasets 只能嵌套在该 lncRNA 内，不能增加 outer n。Phase 5 power simulation必须证明 distinct-lncRNA 信息量能评估 margins。

## 5D. Prediction score and K

必须固定 Section 12.4/12.5 的 primary region score、no-hit sentinel、tie policy 和 `recall@P_d`。

## 5E. Labels

在 prediction 前冻结：

```text
peak source and version
positive threshold
blacklist handling
region/window definition
negative universe
GC/length/chromosome matching
random seed
negative replicates
chromosome/block partition
```

不得用 A/G/X 输出构建 labels。

## 5F. External tools

至少预注册一个可运行外部 triplex predictor attempt；记录版本、license、安装、输入转换、语义和失败处理。

## 5G. 必须产出

```text
docs/biological_topk/experimental_benchmark_spec.md
paper/biological_topk/experimental_power_simulation.json
paper/biological_topk/experimental_information_decision.json
paper/biological_topk/experimental_benchmark_plan.json
paper/biological_topk/experimental_benchmark_manifest.tsv
paper/biological_topk/experimental_attempt_plan.tsv
paper/biological_topk/experimental_manifest.sha256
paper/biological_topk/phase_5_change_allowlist.txt
reproduce/biological_topk/freeze_experimental_benchmark.py
scripts/check_biological_topk_phase5.sh
```

## 5H. Gate

```text
historical datasets marked development
primary query construction independently justified
full queries within operating envelope
power/information gate pass
region score and K frozen
labels and negatives deterministic
external attempt plan frozen
no evaluation prediction run
phase allowlist valid
post-commit read-only check specified; next phase start must confirm clean
```

失败：

```text
<5 distinct lncRNAs or insufficient nested-data power -> blocked_insufficient_experimental_information
unavailable/legal issue -> blocked_external_data
```

建议 commit：

```text
repro: preregister independent biological utility benchmark
```

---

# Phase 6 — Biological utility execution 与 decision

## 6A. Execution isolation

A、G、X 独立执行。Prediction backend 不得读取 experimental labels；labels 只在离线 analysis 使用。

## 6B. Primary analysis

每个 dataset：

```text
GPU AUCPR
CPU AUCPR
GPU-CPU AUCPR difference
GPU recall@P_d
CPU recall@P_d
GPU-CPU recall difference
prevalence
GPU AUCPR - prevalence
GPU top-P fold enrichment
log(GPU top-P fold enrichment)
external metrics when comparable
```

先按冻结规则在同一 lncRNA 内聚合 nested dataset/assay，再对 distinct lncRNAs 等权 macro。

## 6C. Intersection-union gate

以下四项必须同时通过：

```text
E1: LCB[macro_lncRNA GPU AUCPR - CPU AUCPR] >= -0.02
E2: LCB[macro_lncRNA GPU recall@P - CPU recall@P] >= -0.05
E3: LCB[macro_lncRNA GPU AUCPR - prevalence] > 0
E4: LCB[macro_lncRNA log(GPU top-P enrichment)] > 0
```

并且：

```text
>=5 distinct lncRNA outer units
no primary lncRNA/dataset technical failure
no missing primary output
no primary dataset with zero_precision = true
all four contrasts use identical paired resample indices
```

若任一 primary dataset 出现 `zero_precision=true`：

```text
containing lncRNA E4 = automatic_failure_zero_precision
global E4 = fail
biological_utility_pass = false
```

此失败不进入 numeric bootstrap，不得通过 lncRNA 内聚合、pseudocount 或删除 dataset 修复。

总体 gate：

```text
biological_utility_pass = E1 AND E2 AND E3 AND E4
```

不得在结果后选择 endpoint、改变 margin、加入 pseudocount 或选择多重性校正。

## 6D. 状态

Pass：

```text
biological_utility = pass
PROGRAM_STATE.contract_status = "concordance_and_utility_pass"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "conditionally_reopened"
```

此时证据完成，但产品在 Phase 8 commit 之前仍是 experimental。

No-go：

```text
biological_utility = no_go
PROGRAM_STATE.contract_status = "biological_utility_no_go"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "closed_biological_utility_gap"
PROGRAM_STATE.phase_status["7"] = "not_authorized_previous_no_go"
```

## 6E. 预算

```text
max GPU-hours = 96
max CPU wall budget = 96 hours
max infrastructure repair epochs = 1
```

## 6F. 产出

```text
paper/biological_topk/source_data/experimental_region_scores.tsv
paper/biological_topk/source_data/experimental_metrics.tsv
paper/biological_topk/source_data/experimental_failure_ledger.tsv
paper/biological_topk/biological_utility_receipt.json
paper/biological_topk/biological_utility_decision.json
paper/biological_topk/figures/biological_utility.*
paper/biological_topk/tables/biological_utility.tsv
```

建议 commit：

```text
bench: freeze independent biological utility decision
```

---

# Phase 7 — 新 epoch 端到端性能与 widening gate

## 7A. 目标

重新测量已经通过 candidate-site concordance 与 biological utility gate 的实际 G 路径。旧 `38.32x` 只作为 historical anchor。

## 7B. Fresh performance panel 与输出合同复核

必须排除：

```text
旧 H19 core
旧 correctness/holdout/pilot/performance
canonical-hybrid-v2
SSW-CUDA
Phase 4 fresh concordance
Phase 6 biological evaluation
```

使用 input-only metadata/hash 选择。至少包含：

```text
small overhead controls
medium application-shaped workloads
large application-shaped workloads
>=5 paired claim repeats per claim row
balanced A/G order
independent artifact roots
```

A、G 后端独立执行；comparison 只能在两侧全部完成后离线运行。每个用于性能 claim 的 workload/repeat 必须重新通过 frozen candidate-site comparator。

```text
validated_performance_attempt = 1
```

仅在 A/G technical success、input identity pass、candidate-site contract pass 时成立。任何不满足合同的快速运行不得计作 validated speedup。

## 7C. 资源与并发冻结

`performance_plan.json` 必须在运行前冻结：

```text
host model and RAM
OS/kernel
CPU model
CPU physical cores used
CPU process count
CPU threads per process
CPU affinity / NUMA policy
GPU model and count
GPU UUIDs
CUDA driver/runtime
workers per GPU
worker-to-GPU mapping
A/G concurrency policy
background-process policy
power/clock policy when controllable
```

不得在看结果后改变线程数、GPU 数、worker density 或并发调度以获得更好 claim row。

## 7D. Cache、warm-up 与计时边界

默认 freeze：

```text
one unclaimed warm-up per backend/workload/config
每个 claim attempt 使用新进程
filesystem page cache 保持自然 warm，不执行结果驱动 drop_caches
A/G 顺序 balanced AB/BA
GPU context initialization included
process startup included
input parsing included
packing/H2D/kernel/traceback/D2H included
triplex conversion/stability/Nt/clustering/ranking/output included
comparison time excluded from user runtime but comparator gate required
```

若需要 cold-cache claim，必须另立预注册 claim row；不得把 warm 与 cold repeats 混在一个估计量中。

## 7E. Primary performance estimand

对 workload `w`、paired repeat block `r`：

```text
s_wr = wall_seconds_A_wr / wall_seconds_G_wr
```

每个 workload：

```text
S_w = median_r(s_wr)
```

每个冻结 claim row：

```text
S_primary = median_w(S_w)
```

Primary 是 **median of paired speedups**，不是 `median(A)/median(G)`。必须同时报告但不得替换 primary：

```text
ratio_of_medians
ratio_of_total_walls
per-workload S_w
per-repeat s_wr
```

## 7F. Hierarchical paired bootstrap

默认：

```text
replicates = 10000
seed = 20260730
outer resampling = workloads within frozen claim stratum
inner resampling = paired repeat blocks within workload
A/G pairing and AB/BA order block kept intact
one-sided 95% lower confidence bound
```

Bootstrap statistic必须重算 `median_w(median_r(s_wr))`。不得独立重采样 A、G wall times。

## 7G. Failure 与 contract-invalid accounting

以下任一情况：

```text
G technical failure
A technical failure
missing/malformed output
input identity failure
candidate-site comparator failure
unexpected fallback
```

必须：

```text
attempt retained
validated_performance_attempt = 0
speedup contribution = 0 for conservative summaries
claim row cannot pass while any primary attempt is invalid
```

不得删除失败 repeat 后重新计算更高 speedup。

## 7H. Widening branch 必须预先指定

Phase 7 freeze 时必须从以下三项选择一个 `primary_widening_branch`；其余只能 secondary，不得在运行后换 branch。

### Branch S：paired speedup

Primary claim stratum 必须在运行前冻结，并满足：

```text
>= 5 unique primary workloads
>= 5 paired timing repeats per workload
unique query sequence digest across primary workloads
unique namespaced query ordinal across primary workloads
unique target sequence digest across primary workloads
unique namespaced target ordinal across primary workloads
```

一个 workload 的 5 次 repeat 不能替代跨 workload 独立信息；技术 repeat 不增加 outer n。通过条件：

```text
S_primary >= 10.0
and one-sided 95% hierarchical-bootstrap LCB >= 10.0
```

### Branch T：固定真实任务节省时间

对一个预冻结 real-task manifest，至少 5 个 paired repeats：

```text
d_r = wall_seconds_A_r - wall_seconds_G_r
D_primary = median_r(d_r)
```

通过条件：

```text
D_primary >= 28800 seconds
and one-sided 95% paired-bootstrap LCB >= 28800 seconds
```

### Branch C：24-hour validated capacity

对固定 batch 中 `U` 个 input pairs，每个 repeat：

```text
capacity_A_r = 86400 * U / wall_seconds_A_r
capacity_G_r = 86400 * U / wall_seconds_G_r
capacity_ratio_r = capacity_G_r / capacity_A_r
```

报告整数 capacity 时使用 floor，但 gate 使用连续 ratio。通过条件：

```text
median_r(capacity_ratio_r) >= 10.0
and one-sided 95% paired-bootstrap LCB >= 10.0
```

所有 branch 的输入必须通过 candidate-site comparator；`validated` 不指 row equality，但必须指本 epoch contract-valid output。

## 7I. Scale cutoff

允许小 workload 因启动开销无加速，但 claim scale 必须在看结果前由 input-only size 定义并冻结。不得在结果后把慢 workload移出 claim stratum。

## 7J. 状态

Pass：

```text
performance_widening = pass
PROGRAM_STATE.contract_status = "performance_widening_pass"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "conditionally_reopened_pending_phase8_release_candidate"
```

即使 Phase 7 pass，产品仍是 experimental，直到 Phase 8 checker、状态转换和 commit 完成。

No-go：

```text
performance_widening = no_go
PROGRAM_STATE.contract_status = "performance_widening_no_go"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.bioinformatics_route = "no_go_retarget_csbj_or_methods"
```

## 7K. 产出

```text
paper/biological_topk/performance_plan.json
paper/biological_topk/performance_manifest.tsv
paper/biological_topk/performance_attempt_plan.tsv
paper/biological_topk/performance_receipt.json
paper/biological_topk/performance_decision.json
paper/biological_topk/source_data/performance_runs.tsv
paper/biological_topk/source_data/performance_contract_checks.tsv
paper/biological_topk/source_data/performance_statistics.tsv
paper/biological_topk/figures/performance.*
paper/biological_topk/tables/performance.tsv
```

预算：

```text
max GPU-hours = 96
max wall budget = 96 hours
max infrastructure repair epochs = 1
```

建议 commit：

```text
perf: freeze biological Top-K candidate-site widening decision
```

# Phase 8 — `gpu-screen` 产品 artifact、CI 与 release candidate

## 8A. Modes

```text
gpu-screen
cpu-reference
audit
strict-row-diagnostic
```

### gpu-screen

Phase 8 commit 前始终：

```text
status = experimental
contract = biological_topk_candidate_site_v1 proposed/in-validation/evidence-complete
```

即使 Phase 4、6、7 已 pass，也不得提前升级。

### cpu-reference

历史 reference，用于复现和比较，不要求默认完整双跑。

### audit

指定小样本的 A/G 离线 candidate-site comparison；不得在默认 gpu-screen 隐式执行完整 CPU。

### strict-row-diagnostic

开发用途；明确 endpoint/CIGAR 等分路径可能导致 mismatch。

## 8B. 用户可见合同 artifact：`candidate_sites.tsv`

`gpu-screen` 必须稳定输出机器可读：

```text
candidate_sites.tsv
```

现有 `TFOsorted`、`topk_rows`、raw CIGAR 或内部 cluster table只能作为 source/diagnostic artifact，不能自动视为新产品合同。

`candidate_sites.tsv` 采用 long format，每个 workload、ranking mode、rank 一行，至少包含：

```text
schema_version
contract_name
contract_version
product_status
workload_id
ranking_mode = score|stability|nt
rank
k
local_cluster_uid
candidate_site_uid
query_ordinal_namespace
query_source_ordinal
query_sha256
target_ordinal_namespace
target_source_ordinal
target_sha256
assembly
coordinate_namespace
query_cluster_start_raw
query_cluster_end_raw
query_representative_start_raw
query_representative_end_raw
target_interval_start_canonical
target_interval_end_canonical
strand
direction
rule
score_decimal_string
score_integer
score_representation
nt_integer
mean_stability_decimal
representative_row_digest
ungapped_tfo_digest
ungapped_tts_digest
backend
software_commit
parameter_bundle_sha256
```

`score_decimal_string` 始终为必填 exact Decimal 字符串。`score_integer` 在 `score_representation=integral_exact` 时为必填 exact integer；在 `decimal_exact` 时必须为 JSON null / TSV empty，规范分值由 `score_decimal_string` 提供。

`local_cluster_uid` 与 `candidate_site_uid` 是 **arm-local provenance IDs**，不是 CPU/GPU 跨 arm equality key。跨 arm 等价只能由 Phase 1 matcher 的 canonical fields 和 exact matching objective判定，matcher 不得比较这两个 UID。

UID canonical serialization 固定为：

```text
Unicode strings normalized to NFC
JSON keys sorted lexicographically
separators = (",", ":")
UTF-8 encoding
no binary floats
Decimal values serialized as canonical decimal strings
SHA-256 over canonical JSON bytes
```

UID payload 中 `arm` 的机器枚举固定为 `A|G`；下面示例使用合法具体值 `A`。

`local_cluster_uid` payload 精确为：

```json
{
  "uid_schema": "biological_topk_local_cluster_uid_v1",
  "contract_name": "biological_topk_candidate_site_v1",
  "contract_version": "1.0",
  "arm": "A",
  "input_pair_digest": "sha256:...",
  "query_identity": {"namespace": "...", "ordinal": "...", "sha256": "..."},
  "target_identity": {"namespace": "...", "ordinal": "...", "sha256": "..."},
  "legacy_cluster_center": 0,
  "legacy_cluster_query_midpoint_min": 0,
  "legacy_cluster_query_midpoint_max": 0,
  "legacy_cluster_member_count": 0,
  "sorted_member_geometry_sha256": "sha256:..."
}
```

`sorted_member_geometry_sha256` 必须由 cluster members 的冻结几何记录按 canonical order 排序后计算。member geometry 只允许包含 query/target intervals、`chromosome_or_target_id`、direction、strand、rule、ungapped TFO/TTS digests；不得包含 full row digest、CIGAR、backend、software commit、numeric `Class`、文件行号或运行时间。该字段用于避免不同 cluster 恰好具有相同 center/min/max/member-count 时产生 UID collision。

`candidate_site_uid` payload 精确为：

```json
{
  "uid_schema": "biological_topk_candidate_site_uid_v1",
  "contract_name": "biological_topk_candidate_site_v1",
  "contract_version": "1.0",
  "arm": "A",
  "local_cluster_uid": "sha256:...",
  "representative_query_start0": 0,
  "representative_query_end0": 0,
  "representative_target_start0": 0,
  "representative_target_end0": 0,
  "chromosome_or_target_id": "...",
  "direction": "...",
  "strand": "...",
  "rule": "...",
  "ungapped_tfo_sha256": "sha256:...",
  "ungapped_tts_sha256": "sha256:..."
}
```

两个 payload 均不得包含：

```text
numeric Class
row digest
representative_row_digest
backend
software commit
file row order
ranking_mode
rank
wall time
```

同一 arm 中同一 candidate site 出现在多个 ranking mode 时应复用同一 `candidate_site_uid`。三种 machine ranking values 必须全部写成 `score|stability|nt`；缺失 ranking/output 必须 fail closed。

Phase 8 必须冻结：

```text
schemas/candidate_sites.schema.json
docs/biological_topk/candidate_sites_format.md
candidate_sites.tsv golden fixture
round-trip parser and deterministic digest tests
```

## 8C. Provenance

每次运行另生成：

```text
backend
contract/version
product status
software commit
binary SHA-256
query/target pair digest
assembly/coordinate namespace
operating-envelope result
GPU/driver/runtime
worker placement
fallback/guard counters
candidate_sites.tsv digest
diagnostic artifact digests
```

## 8D. Release candidate

```text
semantic version candidate
CHANGELOG
license inventory
CITATION.cff draft
Zenodo metadata draft
quick start
smoke dataset
container/Apptainer
CI
contract docs
coordinate docs
candidate_sites.tsv docs
limitations
unsupported inputs
```

Codex不得实际发布 release/DOI。

## 8E. Gate、状态转换与 commit

Phase 8 pre-commit checker必须验证：

```text
user modes match docs
gpu-screen does not run full CPU authority
unsupported input fails closed
candidate_sites.tsv schema complete and deterministic
all three rankings present
numeric implementation cluster ID absent from product identity
A/G identity/provenance emitted
smoke deterministic
CI passes
container reproduces candidate_sites.tsv digest
release checklist complete except owner actions
PROGRAM_STATE status transition included in diff
```

只有 checker pass 后，Phase 8 commit 中才允许设置：

```text
PROGRAM_STATE.phase_status["8"] = "pass"
PROGRAM_STATE.gpu_screen_status = "validated_screening_backend_v1_release_candidate"
PROGRAM_STATE.contract_status = "validated_within_fixed_operating_envelope"
PROGRAM_STATE.bioinformatics_route = "conditionally_reopened_pending_final_audit"
```

Phase 8 commit 后必须运行 read-only post-commit checker。若 pre-commit checker 在允许的修复次数内无法通过，或 post-commit checker 证明 release/reproducibility gate 不成立，必须通过一个明确的 terminal no-go/corrective commit 设置：

```text
PROGRAM_STATE.phase_status["8"] = "no_go"
PROGRAM_STATE.phase_status["9"] = "not_authorized_previous_no_go"
PROGRAM_STATE.gpu_screen_status = "experimental"
PROGRAM_STATE.contract_status = "release_or_reproducibility_blocked"
PROGRAM_STATE.bioinformatics_route = "release_or_reproducibility_blocked"
PROGRAM_STATE.active_phase = null
PROGRAM_STATE.last_completed_phase = 8
PROGRAM_STATE.last_decision = "release_or_reproducibility_blocked"
PROGRAM_STATE.final_decision_candidate = "release_or_reproducibility_blocked"
PROGRAM_STATE.final_decision = "release_or_reproducibility_blocked"
```

不得保留或口头使用 `validated_screening_backend_v1_release_candidate`。若一个先前 Phase 8 pass commit 的 post-commit check 失败，corrective commit 必须显式撤销 product/status promotion，并由 post-commit read-only checker认证 terminal blocked state。

建议 pass commit：

```text
release: certify candidate-site gpu-screen release candidate
```

# Phase 9 — Manuscript、claim ledger 与最终审计

## 9A. 允许主张

Gate 通过后才允许：

```text
C1: GASAL2-LongTarget preserves Top-K clustered TFO/query-target candidate-site sets with Top-1 retention under biological_topk_candidate_site_v1.
C2: GPU predictions are non-inferior to CPU Fasim on independent experimental biological endpoints and show absolute utility above prevalence.
C3: The validated gpu-screen path provides >=10x end-to-end acceleration or another preregistered widening outcome within the fixed operating envelope.
C4: Endpoint/CIGAR/full-row differences remain diagnostic limitations and are not treated as candidate-site substitutions when the frozen matcher establishes a unique match.
```

### 禁止主张

```text
DNA-locus preservation
complete rank-order preservation
exact CPU replacement
full-output replacement
all lncRNAs
all GPUs
full-length MALAT1/NEAT1/KCNQ1OT1 support
38.32x as new validated estimate
production status before Phase 8
```

## 9B. Title/abstract wording

优先：

```text
GPU-accelerated screening of clustered lncRNA-DNA triplex candidate sites
```

避免：

```text
exact loci
DNA-locus equivalence
identical rankings
```

## 9C. Claim ledger

每项绑定：

```text
claim_id
exact wording
scientific object
contract
population/operating envelope
source data
analysis code
figure/table
limitations
status
```

## 9D. 最终合法决策

```text
bioinformatics_application_note_ready_for_submission
bioinformatics_application_note_ready_pending_owner_actions
candidate_site_concordance_no_go
biological_utility_no_go
performance_widening_no_go_retarget_csbj
release_or_reproducibility_blocked
```

## 9E. Audit-candidate commit

第一步提交必须包含完整 manuscript package、claim ledger、source-data references、figures/tables 与 aggregate-checker inputs，但状态保持：

```text
phase_9_status = active
final_decision = null
final_decision_candidate = <one legal value>
audit_candidate_commit = null
```

该 commit 建议：

```text
docs: assemble clustered candidate-site audit candidate
```

## 9F. Read-only aggregate checker

在 audit-candidate commit 上运行 `make check-biological-topk`，必须：

```text
run all phase checkers
validate historical frozen blobs
rebuild exclusion registry
rebuild source universe
re-run regression comparator
verify zero fresh overlap
verify unique primary query and target identities
verify exact A/G input identity
recompute CP bounds and concordance power
recompute outer-bootstrap joint eligible/nonempty/240-site planning q_b distribution, 5% LCB and inner-MC precision audit
verify Phase 3 manifest-specific resource projection and budget decision
verify Score integrality audit or decimal_exact fallback
verify binary denominator accounting
recompute biological paired contrasts
verify intersection-union gate
recompute performance primary estimand and bootstrap
verify every performance claim row passes candidate-site comparator
rebuild candidate_sites.tsv golden output
verify arm-local UID canonical payloads and golden digests
verify standard-JSON zero-precision serialization and automatic lncRNA/global E4 failure propagation
rebuild figures/tables
scan prohibited wording
verify old no-go unchanged
verify double-empty not counted as success
verify rank-order claim remains diagnostic-only
verify 38.32x historical-only
verify gpu-screen validation occurred only in Phase 8 commit
verify audit-candidate working tree clean
```

Checker 必须 read-only，并生成可捕获的 stdout/stderr digest；不得修改 audit-candidate tree。

## 9G. Certification commit

仅在 aggregate checker pass 后，第二步 certification commit 才允许修改：

```text
paper/biological_topk/PROGRAM_STATE.json
paper/biological_topk/final_decision.json
paper/biological_topk/final_certification_receipt.json
```

`final_certification_receipt.json` 必须绑定：

```text
audit_candidate_commit SHA
aggregate checker command
checker stdout/stderr SHA-256
checker exit code
all phase decision digests
```

不得记录 certification commit 自身 SHA。

certification commit 设置：

```text
PROGRAM_STATE.phase_status["9"] = "pass"
PROGRAM_STATE.active_phase = null
PROGRAM_STATE.last_completed_phase = 9
PROGRAM_STATE.last_decision = PROGRAM_STATE.final_decision_candidate
PROGRAM_STATE.final_decision = PROGRAM_STATE.final_decision_candidate
PROGRAM_STATE.final_decision_candidate remains unchanged as the audited proposed decision
PROGRAM_STATE.audit_candidate_commit = <actual audit candidate SHA>
```

`bioinformatics_route` 必须与 final decision 同步，映射固定为：

```text
bioinformatics_application_note_ready_for_submission
    -> bioinformatics_application_note_ready_for_submission

bioinformatics_application_note_ready_pending_owner_actions
    -> bioinformatics_application_note_ready_pending_owner_actions

release_or_reproducibility_blocked
    -> release_or_reproducibility_blocked

candidate_site_concordance_no_go
    -> closed_for_this_contract

biological_utility_no_go
    -> closed_biological_utility_gap

performance_widening_no_go_retarget_csbj
    -> no_go_retarget_csbj_or_methods
```

Phase 9 完成后的 `active_phase = null` 表示状态机已终止；不得使用 `10`、`complete` 或最后 phase number 伪装 active phase。PROGRAM_STATE schema 必须允许 `active_phase` 为 `0..9` 或 `null`，并验证 final decision、route 与 phase statuses 的一致性。

建议 commit：

```text
docs: certify biological Top-K final decision
```

commit 后运行 read-only post-certification checker并验证 working tree clean。

## 14. Machine-readable schema minimums

### 14.0 PROGRAM_STATE schema

Phase 0 必须创建并版本化：

```text
schemas/biological_topk_program_state.schema.json
```

该 JSON Schema 至少必须：

```text
additionalProperties = false
program_schema_version = 5
active_phase = integer 0..9 or null
phase_status keys exactly "0".."9"
phase_status values restricted to Section 1.1 enum
contract_status/gpu_screen_status/bioinformatics_route restricted to frozen enums
final_decision_candidate/final_decision nullable but otherwise restricted to Section 9D enum
unknown fields rejected
```

除静态 JSON Schema 外，参数化 phase checker 必须实现 transition validation，因为普通 schema 不能独立表达全部跨字段历史约束。至少验证：

```text
Phase 8 validated product status only with phase 8 pass
Phase 8 no_go forces experimental + release_or_reproducibility_blocked + phase 9 not authorized
Phase 9 pass forces active_phase=null and final_decision non-null
final_decision and bioinformatics_route follow the frozen mapping
no later phase becomes active after a prior no_go/blocked terminal state
```

### 14.1 Contract spec

```json
{
  "schema_version": 2,
  "contract_name": "biological_topk_candidate_site_v1",
  "scientific_object": "clustered_TFO_query_target_candidate_site",
  "claim_scope": "set_preservation_with_top1_retention",
  "rank_order_claim": "diagnostic_only",
  "ranking_mode_values": ["score", "stability", "nt"],
  "score_representation": "integral_exact",
  "k": 5,
  "row_eligibility": {"nt_operator": ">", "nt_bp": 50},
  "legacy_midpoint": "int((raw_QueryStart+raw_QueryEnd)/2)",
  "cluster_distance": 15,
  "coordinate_mapping_table_sha256": "...",
  "matching": {
    "input_identity": "all_fields_AND",
    "objective": "lexicographic_aggregate_exact_fraction",
    "equivalent_optima": "failure"
  },
  "primary_endpoint": "score_complete_set_success_rate",
  "confidence_method": "one_sided_exact_clopper_pearson",
  "alpha": 0.05,
  "lcb_min": 0.95,
  "double_empty": "non_informative_not_success",
  "strict_row_equality": "diagnostic_only"
}
```

### 14.2 Attempt receipt

```json
{
  "attempt_id": "...",
  "workload_id": "...",
  "arm": "A",
  "evidence_role": "fresh_concordance_promotion",
  "query_ordinal_namespace": "...",
  "query_source_ordinal": "...",
  "query_sha256": "...",
  "target_ordinal_namespace": "...",
  "target_source_ordinal": "...",
  "target_sha256": "...",
  "assembly": "GRCh38",
  "coordinate_namespace": "...",
  "input_pair_digest": "...",
  "parameter_bundle_sha256": "...",
  "status": "success",
  "command": ["..."],
  "source_commit": "...",
  "binary_sha256": "...",
  "output_sha256": "...",
  "wall_seconds": 0.0,
  "fallback_used": false,
  "comparison_started": false
}
```

### 14.3 Workload metric

```json
{
  "workload_id": "...",
  "ranking_mode": "score",
  "reference_candidate_count": 5,
  "candidate_candidate_count": 5,
  "matched_count": 5,
  "informative_for_recovery": true,
  "binary_gate_denominator_eligible": true,
  "binary_success": true,
  "double_empty": false,
  "recall": "1",
  "precision": "1",
  "top1_retained": true,
  "complete_set_success": true,
  "rbo5_diagnostic": "1",
  "ambiguous_matching": false,
  "technical_failure": false,
  "strict_row_equal": false
}
```

### 14.4 Stable product candidate-site row

```json
{
  "schema_version": 1,
  "contract_name": "biological_topk_candidate_site_v1",
  "contract_version": "1.0",
  "product_status": "experimental",
  "workload_id": "...",
  "ranking_mode": "score",
  "rank": 1,
  "local_cluster_uid": "sha256:...",
  "candidate_site_uid": "sha256:...",
  "query_identity": {"namespace": "...", "ordinal": "...", "sha256": "..."},
  "target_identity": {"namespace": "...", "ordinal": "...", "sha256": "..."},
  "assembly": "GRCh38",
  "coordinate_namespace": "...",
  "score_decimal_string": "0",
  "score_integer": 0,
  "score_representation": "integral_exact",
  "nt_integer": 0,
  "mean_stability_decimal": "0.00000",
  "representative_row_digest": "sha256:...",
  "backend": "gasal2",
  "software_commit": "..."
}
```

当 `score_representation=integral_exact` 时，`score_integer` 必须为 exact derived integer；当 `score_representation=decimal_exact` 时，`score_integer` 必须为 `null`，`score_decimal_string` 是唯一规范值。不得对 `score_decimal_string` 调用 `int()` 生成产品值。

### 14.5 Performance claim row

```json
{
  "claim_row_id": "...",
  "primary_widening_branch": "paired_speedup",
  "performance_estimand": "median_workload_of_median_paired_speedups",
  "bootstrap_seed": 20260730,
  "bootstrap_replicates": 10000,
  "cpu_processes": 1,
  "cpu_threads_per_process": 1,
  "gpu_count": 1,
  "workers_per_gpu": 1,
  "primary_unique_workloads": 5,
  "primary_unique_query_identities": 5,
  "primary_unique_target_identities": 5,
  "cache_policy": "new_process_balanced_order_natural_warm_page_cache",
  "all_primary_attempts_contract_valid": true,
  "point_estimate": "...",
  "one_sided_95_lcb": "..."
}
```

### 14.6 Experimental utility metric row

```json
{
  "lncrna_outer_unit": "...",
  "dataset_id": "...",
  "precision_at_p": "0",
  "prevalence": "0.01",
  "fold_enrichment": "0",
  "zero_precision": true,
  "log_enrichment": null,
  "endpoint_status": "automatic_failure",
  "containing_lncRNA_E4_status": "automatic_failure_zero_precision",
  "global_E4_status": "fail"
}
```

标准 JSON 中禁止 `NaN`、`Infinity` 和 `-Infinity`。非零 precision 时，`log_enrichment` 必须写为 canonical decimal string；零 precision 时只能使用上面的 `null + automatic_failure` 表示。

---

## 15. 必须实现的 tests

### 15.1 Scientific-object tests

```text
Nt=50 excluded
Nt=51 included
legacy midpoint exact for odd/even sums
legacy cluster output independent of numeric input Class field
cluster is query-axis, not target-axis
```

### 15.2 Coordinate tests

```text
every reachable Strand/Direction combination
first/last target base
forward/reverse/complement reconstruction
genome offset mapping
hq10/hq11 coordinates
no generic min/max shortcut
```

### 15.2A Score representation tests

```text
raw Score parsed as Decimal before any integer conversion
integral Score emits exact score_integer and score_decimal_string
non-integral Score selects decimal_exact schema branch
int() truncation and tolerance-based integrality proof rejected
region-score function uses the frozen exact representation
JSON/TSV decimal serialization round-trips byte-for-byte
```

### 15.3 Input identity tests

```text
same digest but different assembly -> fail
same target namespace but different digest -> fail
same bare ordinal but different namespace -> fail
same filenames but different digest -> fail
all fields same -> comparison allowed
```

### 15.4 Matcher tests

```text
row permutation invariant
numeric cluster ID invariant
gapped CIGAR invariant
unique exact optimum
exact-Fraction objective
ambiguous aggregate optimum fails
extra G candidate makes precision/complete-set fail
A count <5 with extra G candidate fails
```

### 15.5 Empty/failure tests

```text
double empty is non-informative, denominator-ineligible, and not success
A nonempty/G empty is denominator-eligible failure
A empty/G nonempty is denominator-eligible failure
technical failure is denominator-eligible failure even when informative=null
missing/malformed output is denominator-eligible failure
```

### 15.6 Statistics tests

```text
60/60 CP LCB = 0.9512970866899025
59/60 CP LCB = 0.9233600050654955
89/89, 99/100, 148/150 pass-threshold fixtures
primary-gate power at p=.99 for n=60/89/100/150
n=123 fails 80% power; n=124 passes 80% power
N_panel=178 gives Pr(eligible>=124)>=0.95 at p_eligible=.75
joint planning simulation accounts for nonempty>=60 and total reference sites>=240
outer-bootstrap q_b distribution uses frozen one-sided 5% order-statistic LCB >=0.95; inner MC is precision-only
resource projection rejects panel whose upper elapsed/GPU-hour bound exceeds budget
all-success bootstrap is not used for binary gate
fixed-sequence testing stops promotion after first failure
technical failure included in binary failure count
```

### 15.7 Source-universe/leakage tests

```text
query digest overlap rejected
namespaced query ordinal overlap rejected
target digest overlap rejected
namespaced target ordinal overlap rejected
pair overlap rejected
old 50x668 panel cannot satisfy new panel by itself
primary query digest and namespaced ordinal unique
primary target digest and namespaced ordinal unique
reused query or target rejected
Rule/Strand result columns prohibited in selector
post-freeze supplementation rejected
```

### 15.8 Experimental estimand tests

```text
no-hit sentinel ranks below valid scores
region score identical function for A/G
recall@P_d exact
outer unit is distinct lncRNA; nested assays do not increase n
macro equal-weight not region-count pooled
assay availability frozen from pre-prediction inventory
AUCPR-prevalence paired contrast exact
log-enrichment contrast exact; any primary zero precision emits null and forces containing-lncRNA/global E4 automatic failure without bootstrap replacement
all four co-primary endpoints use intersection-union AND gate
historical MALAT1/NEAT1 segments marked development
unannotated result-driven segment rejected
```

### 15.9 Runner isolation tests

```text
A cannot read G artifact root
G cannot read A artifact root
comparison only after both arms terminal
AB and BA orders both executable
backend output cannot read labels
performance comparison is offline and excluded from user runtime
```

### 15.10 Performance estimand tests

```text
primary uses median of paired speedups, not ratio of medians
Branch S rejects fewer than 5 unique workloads
Branch S rejects reused primary query or target identity
hierarchical bootstrap keeps A/G repeat pairing
bootstrap seed deterministic
invalid contract output cannot count as validated speedup
failed repeat retained with conservative zero contribution
8-hour branch uses seconds difference and LCB >=28800
24-hour capacity formula uses fixed U and continuous ratio
post-result widening branch switch rejected
```

### 15.11 Product artifact tests

```text
candidate_sites.tsv contains score/stability/nt machine rankings
stable schema and column order
local_cluster_uid independent of numeric Class
candidate_site_uid deterministic under row permutation
UID payload excludes row digest/backend/software commit/Class/ranking/rank
UIDs are arm-local provenance and are not accepted as cross-arm equality keys
missing ranking fails closed
local_cluster_uid canonical JSON golden digest
local_cluster_uid differs when summary fields match but sorted member geometry differs
candidate_site_uid canonical JSON golden digest
standard JSON rejects NaN/Infinity and uses null/status for zero-precision enrichment
TFOsorted/topk_rows not accepted as product artifact
Phase 4/6/7 pass cannot upgrade product status
Phase 8 commit + post-commit check required for validated release-candidate status
```

### 15.12 Git/state tests

```text
PROGRAM_STATE.json is valid JSON and validates against schemas/biological_topk_program_state.schema.json
unknown phase state rejected
blocked_insufficient_experimental_information accepted
final_decision_candidate and final_decision are known nullable schema fields
status transition present before phase commit
precommit receipt does not contain future/self commit SHA
post-commit checker is read-only
next phase start receipt binds previous phase commit
Phase 9 audit candidate and certification commits are distinct
certification receipt binds audit candidate, not itself
```

## 16. Stop-loss 与研究边界

### 16.1 Contract no-go

```text
cannot reproduce legacy clustering
cannot define coordinate mapping for reachable mode
cannot define deterministic candidate-site matching
fresh exact LCB < 0.95
ambiguous match > 0
technical failure > 0
```

不得降低 overlap 或修改 scientific object rescue。

### 16.2 Information no-go

```text
binary denominator count < n_binary_required
<60 reference-nonempty informative workloads
<240 primary score-ranked CPU reference candidate sites
joint pre-run information feasibility LCB <0.95
primary query or target identity reused
```

不得补样；关闭 epoch 或建立新 epoch。

### 16.3 Biological utility no-go

```text
<5 distinct lncRNA outer units
experimental power/information gate fails
AUCPR NI contrast fails
recall@P NI contrast fails
AUCPR-prevalence contrast fails
log-enrichment contrast fails
intersection-union gate fails
primary evaluation technical failure
```

### 16.4 Performance no-go

若 widening gate失败：

```text
保留 concordance/utility evidence
关闭 Bioinformatics widening story
转 CSBJ/methods/software characterization
```

不得用历史 38.32x 替代。

### 16.5 不授权重开

```text
exact SSW-CUDA Phase 8-12
canonical-hybrid-v2 rescue
full CPU verified double run
long-query architecture
full 121-segment KCNQ1OT1
full hg38
```

---

## 17. Owner-only actions

Codex只能准备，不能自行决定：

```text
author list/order
corresponding author
license changes
public data redistribution approval
GitHub release
Zenodo deposition/DOI
journal submission
cover-letter signoff
final scientific approval of non-inferiority margins
```

---

## 18. 立即开始的第一批动作

1. 将 protocol source 保持在仓库外；在创建任何文件前验证 working tree clean，并在内存中保留 clean-check command/result；
2. 创建 Phase 0 start receipt，绑定 execution-start HEAD 和 protocol source SHA-256；
3. 将本文件写入仓库根目录 `goal-biological-topk.md`，并把它列入 Phase 0 allowlist；不得覆盖其他 goal；
4. 读取实际 branch、HEAD、remote 和历史 evidence；
5. 运行现有 Bioinformatics、hybrid-v2、SSW-CUDA checkers；
6. 创建 `paper/biological_topk/`、`docs/biological_topk/`；
7. 用 `git show HEAD:path` 建 historical blob registry；
8. 重建 namespaced exclusion registry；
9. 创建 `schemas/biological_topk_program_state.schema.json`、统一的 `scripts/check_biological_topk_phase.py`、aggregate checker、Phase 0 allowlist 与 precommit receipt；
10. 提交：

```text
docs: freeze biological Top-K candidate-site validation epoch
```

11. Phase 1 先完成 scientific-object correction、legacy clustering semantics、Strand/Direction coordinate table、input identity AND gate、exact matching objective、Clopper-Pearson gate、exact-binomial power plan、outer-bootstrap reference-nonempty/240-site joint feasibility、inner-MC precision audit、fixed-budget resource model、Score integrality/Decimal decision、unique-query/unique-target source universe 和 experimental nested-lncRNA power plan；
12. Phase 1 commit 前不得选择 fresh pair、不得下载 primary evaluation output、不得运行新 A/G prediction；
13. Phase 2 只做历史 regression；
14. 任一 no-go 立即更新状态并停止未授权后续 phase。

---

## 19. 最终原则

本 epoch 不要求：

```text
GPU CIGAR == CPU CIGAR
```

也不声称：

```text
DNA-locus equality
完整第 1–5 名顺序等价
```

它要求在固定 operating envelope 内证明：

```text
1. GASAL2 gpu-screen 在全新输入上，以有限样本有效的精确统计规则，
   保留 CPU Fasim 的 clustered TFO/query-target Top-K candidate-site set，
   并保留 Top-1；primary binary gate 只排除 clean double-empty，其他失败全部进入分母；
2. 技术失败、缺失、额外候选、ambiguity 全部按失败或非信息性规则如实计数；
3. 在至少 5 个 distinct lncRNA outer units 的独立真实实验数据上，GPU 预测通过四项预注册 intersection-union gate：两项非劣与两项绝对效用；
4. 在新的独立端到端性能实验中，所有 claim rows 重新通过 candidate-site comparator，实际交付路径按冻结估计量达到预注册 widening gate；
5. 软件、容器、CI、provenance、限制与历史 no-go 均可复现。
```

只有上述全部成立，Bioinformatics 路线才从：

```text
conditionally_reopened
```

升级为：

```text
bioinformatics_application_note_ready_pending_owner_actions
或
bioinformatics_application_note_ready_for_submission
```

否则必须保留全部证据并按预注册状态转向 CSBJ、方法论文或负结果/边界刻画；不得事后改名、放宽合同或删除失败。

