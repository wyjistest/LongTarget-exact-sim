# Rerun Exact SIM Kernel Feasibility

> **Status:** implemented feasibility baseline  
> **Scope:** semantic audit + fixed-panel benchmark corpus/export harness  
> **Runtime baseline:** `deferred_exact_minimal_v3_task_rerun_budget16`

## Goal

把 two-stage 的下一阶段从“继续选哪些 task rerun”收束为“对已证明有效的 rerun task，评估 exact `SIM` kernel 是否值得重写”。本阶段不实现 GPU kernel 本身，只把后续 prototype 必需的三件基础设施补齐：

1. rerun rescue 语义审计；
2. fixed-panel `budget16` selected-task corpus/export；
3. prototype 可复用的 task-output semantic compare 入口。

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
- `summary.json`
- `summary.md`

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
```

## Next Step

如果下一轮要继续推进 kernel feasibility，应直接基于该 baseline 做：

1. fixed-panel `budget16` selected tasks 的 CPU gold export；
2. task-level exact `SIM` GPU rewrite prototype；
3. prototype task-output semantic compare；
4. micro-benchmark go/no-go（语义等价 + kernel speedup + integrated wall-time impact）。
