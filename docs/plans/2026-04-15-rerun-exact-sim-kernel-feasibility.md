# Rerun Exact SIM Kernel Feasibility

> **Status:** implemented feasibility baseline + frozen corpus / CPU replay + CPU bucket benchmark run (current decision: no CPU executor prototype)
> **Scope:** semantic audit + fixed-panel benchmark corpus/export harness + shape audit + isolated replay driver + CPU bucket executor micro-benchmark
> **Runtime baseline:** `deferred_exact_minimal_v3_task_rerun_budget16`

## Goal

把 two-stage 的下一阶段从“继续选哪些 task rerun”收束为“对已证明有效的 rerun task，评估 exact `SIM` kernel 是否值得重写”。本阶段不实现 GPU kernel 本身，只把后续 prototype 必需的三件基础设施补齐：

1. rerun rescue 语义审计；
2. fixed-panel `budget16` selected-task corpus/export；
3. prototype 可复用的 task-output semantic compare 入口。
4. frozen corpus 上的 task-shape audit 与 isolated CPU replay。

## Semantic Audit

### Audit target

审计对象是 `runExactReferenceSIMTwoStageRescueWithWindows(...)` 触发的 rerun rescue 路径，以及其最终调用的 `SIM(...)`。

### Key findings

1. **当前 rerun 不是“直接对 transformed strings 做一次标准 local-affine alignment”。**
   - `SIM(...)` 的 substitution score 不是普通字符矩阵，而是 `triplex_score(c1, c2, Para)` 的 triplex-specific 评分；
   - 同时 `penaltyT / penaltyC` 会按 traceback 脚本中的字符类别重写 `tri_score` 累积。

2. **当前输出语义不只是单个最优 local alignment。**
   - `SIM(...)` 先维护候选集合，再通过 blocked-diagonal / `updateSimCandidatesAfterTraceback(...)` 做 top-K 候选推进；
   - rerun rescue 外层还会按 rescue windows 迭代，并用 `ExactSimTriplexKey` 做跨 window 去重。

3. **traceback 阶段已经是“SIM-specific candidate proposal + bounded affine traceback”的组合。**
   - 候选定位与 blocked-word 语义来自当前 `SIM` 主体；
   - bounded traceback 可以复用 affine-gap kernel 思路，但它不是完整的 drop-in 语义。

### Audit decision

- **Audit result: fail for direct local-affine equivalence**
- 结论：当前 rerun rescue **不能** 在“输出结果集强等价”的要求下，直接收缩成一个 off-the-shelf local-affine rescue kernel。
- 因此后续 prototype 的默认首选路径应是：
  - **task-level exact `SIM` GPU rewrite**
- `local-affine rescue kernel` 只适合作为探索分支，前提是愿意把等价目标降级为更弱的近似目标，而不是当前要求的 task-output semantic equality。

## Implemented Baseline

### Runtime export surface

新增可选 runtime env：

- `LONGTARGET_TWO_STAGE_TASK_RERUN_TASK_OUTPUT_TSV`

启用 task rerun lane 且设置该 env 时，runtime 会为 **selected + effective** rerun tasks 导出 task-scoped TSV，列格式与现有 `.lite` 输出对齐，并额外带上：

- `task_key`
- `selected`
- `effective`

同时 `benchmark.*` telemetry / `report.json` 新增：

- `two_stage_task_rerun_task_output_tsv`
- rerun profile TSV 也新增 `min_score`，供后续 isolated replay 直接复用

### Fixed-panel feasibility harness

新增脚本：

```bash
python3 ./scripts/benchmark_two_stage_task_rerun_kernel_feasibility.py \
  --panel-summary .tmp/panel_minimal_v3_task_rerun_budget16_runtime_2026-04-14/summary.json \
  --output-dir .tmp/panel_minimal_v3_task_rerun_budget16_feasibility
```

它会固定 selected tiles 与 selected-task TSV，只重跑：

- `deferred_exact_minimal_v3_scoreband_75_79`
- `deferred_exact_minimal_v3_task_rerun_budget16`

并在输出目录下生成：

- `task_rerun_selected_tasks/*.tsv`
- `task_rerun_profiles/*.tsv`
- `task_rerun_task_outputs/*.tsv`
- `task_rerun_window_traces/*.tsv`
- `task_rerun_windows/*.tsv`
- `task_rerun_corpus_manifest.tsv`
- `task_rerun_corpus_manifest.json`
- `summary.json`
- `summary.md`

其中：

- `task_rerun_window_traces/*.tsv` 保留 candidate lane 的原始 window trace；
- `task_rerun_windows/*.tsv` 只保留 selected+effective task 的 replay-ready `before_gate` windows，并把 `min_score` 写回每行；
- `task_rerun_corpus_manifest.tsv|json` 冻结 tile filename、FASTA 输入、task spec、replay window path、gold task-output path，供后续 isolated replay / GPU prototype 直接消费。

### Task-shape audit

新增脚本：

```bash
python3 ./scripts/analyze_two_stage_task_rerun_corpus_shapes.py \
  --corpus-manifest .tmp/panel_minimal_v3_task_rerun_budget16_feasibility/task_rerun_corpus_manifest.tsv \
  --output-dir .tmp/panel_minimal_v3_task_rerun_budget16_feasibility/shape_audit
```

它只读取 frozen manifest，并输出：

- `rerun_bp` / `target_length` / `output_row_count` / `rule|strand` / `seconds_per_kbp` buckets
- dynamic `bp_target_buckets`
- dynamic `rule_strand_bp_buckets`
- `long_tail_coverage`
- `recommended_cpu_buckets`
- `recommended_gpu_buckets`
- top rerun-seconds tasks
- top rerun-bp tasks
- conservative `gpu_batching_candidate`

### Full fixed-panel result

已在完整 fixed panel 上实际跑完：

- selected tiles: `12`
- selected / effective / manifest tasks: `16 / 16 / 16`
- replay windows rows: `71`
- task-output rows: `468`
- rerun added bp total: `8097`
- rerun effective sim seconds total: `19.216958`

shape audit 真实结果：

- `task_count=16`
- `rerun_seconds_total=19.216985`
- `rerun_bp_total=19631`
- `gpu_candidate_seconds_total=10.084305`
- `gpu_batching_candidate=False`

当前 full-panel bucket 结论：

- `rerun_bp`
  - `513-1024`: `4 tasks`, `2.809711s`
  - `1025-2048`: `12 tasks`, `16.407274s`
- `target_length`
  - `4097-8192`: `15/16 tasks`, `18.706718s`
- `output_row_count`
  - `>16`: `12 tasks`, `16.897942s`

这意味着 full-panel rerun corpus 虽然继续证明 exact `SIM` 是主成本，但按当前保守 heuristic，**还不足以直接把下一阶段定成“GPU batching rescue kernel rewrite”**。

### Isolated CPU replay driver

新增 binary：

```bash
./exact_sim_task_rerun_replay \
  --corpus-manifest .tmp/panel_minimal_v3_task_rerun_budget16_feasibility/task_rerun_corpus_manifest.tsv \
  --output-dir .tmp/panel_minimal_v3_task_rerun_replay_cpu
```

实现约束：

- 不走 discovery / gate；
- 直接读取 frozen FASTA、task spec、`min_score` 与 replay windows；
- 每 task 调用 `runExactReferenceSIMTwoStageDeferredWithMinScore(...)`；
- 再复用和 runtime 一致的 post-filter 与 task-output writer；
- 输出 tile filename / TSV schema 与 exported gold 完全对齐。
- `--threads` 现已变成真实的 per-task parallel replay 控制；
- `--task-list-tsv` 可直接消费单列 `task_key` 列表。

### CPU bucket benchmark

新增脚本：

```bash
python3 ./scripts/benchmark_two_stage_task_rerun_cpu_buckets.py \
  --corpus-manifest .tmp/panel_minimal_v3_task_rerun_budget16_feasibility/task_rerun_corpus_manifest.tsv \
  --shape-summary .tmp/panel_minimal_v3_task_rerun_budget16_feasibility/shape_audit/summary.json \
  --replay-bin ./exact_sim_task_rerun_replay \
  --output-dir .tmp/panel_minimal_v3_task_rerun_budget16_cpu_buckets
```

它会只对 `recommended_cpu_buckets` 评估三类执行形态：

- `isolated_serial`
- `bucket_serial`
- `bucket_parallel`

并固定用以下门槛决定是否继续进入 CPU bucketed executor prototype：

- `speedup_vs_isolated_serial >= 1.25`
- `speedup_vs_bucket_serial >= 1.10`

### CPU bucket benchmark result

当前 frozen corpus 上的真实结果已经跑完：

- `shape_audit_v2` 只产出一个 `recommended_cpu_bucket`
  - `bp_target:513-1024|4097-8192`
  - `task_count=3`
  - `rerun_bp_total=2388`
  - `rerun_seconds_total=2.299444`
  - `rerun_seconds_ratio≈0.1197`
- benchmark 输出：
  - `isolated_serial=1.118311s`
  - `bucket_serial=0.898488s`
  - best `bucket_parallel(thread=2)=0.920922s`
- 对应 speedup：
  - `bucket_serial vs isolated_serial = 1.244658x`
  - best `bucket_parallel vs isolated_serial = 1.214338x`
  - best `bucket_parallel vs bucket_serial = 0.975640x`
- **Decision: fail for CPU executor continuation**
  - 没有任何 bucket 同时达到 `1.25x / 1.10x`
  - 当前结论是 `continue_cpu_executor_prototype=False`
  - 因此这一阶段不进入 CPU bucketed executor rewrite

### Prototype compare contract

同一脚本支持可选：

```bash
  --compare-task-output-root <prototype_task_output_root>
```

要求 prototype 目录按 tile filename 对齐导出 task-output TSV。对拍口径是：

- task key 一致；
- strict result-set key 一致；
- per strict key score 一致（`1e-6` tolerance）；
- 不要求原始行顺序一致。

## Verification

本阶段新增/更新的本地验证入口：

```bash
make check-exact-sim-two-stage-threshold
make check-two-stage-task-rerun-runtime
make check-benchmark-two-stage-task-rerun-kernel-feasibility
make check-benchmark-two-stage-task-rerun-cpu-buckets
make check-analyze-two-stage-task-rerun-corpus-shapes
make check-exact-sim-task-rerun-replay
```

## Next Step

如果下一轮要继续推进 kernel feasibility，应直接基于该 baseline 做：

1. 不再重复“先跑 full fixed-panel audit”这一步，当前 full-panel 结果已经表明 `gpu_batching_candidate=False`；
2. 直接基于现有 corpus 运行新的更细 shape audit，先看 `recommended_cpu_buckets` / `recommended_gpu_buckets` 是否稳定；
3. 当前这轮 benchmark 已经表明：没有任何 bucket 过 CPU continuation rule，因此先不进入 executor rewrite；
4. 下一轮只有在新的 shape audit 把更多 wall-time 收敛到更大、更稳定的 batch 形态后，才重新考虑 CPU executor 或 task-level exact `SIM` GPU prototype；
5. 无论后续走 CPU 还是 GPU prototype，都继续沿用同一 corpus 与 task-output semantic compare contract，并按 go/no-go（语义等价 + kernel speedup + integrated wall-time impact）决定是否继续。
