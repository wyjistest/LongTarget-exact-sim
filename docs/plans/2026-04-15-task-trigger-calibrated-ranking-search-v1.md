# Task Trigger Calibrated Ranking Search V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `minimal_v3` baseline 增加 oracle-free task trigger calibrated ranking search v1，先做 offline ranking search，不做 runtime 变更。

**Architecture:** 扩展 `analyze_two_stage_task_ambiguity.py` 输出更丰富的 deployable task-level features；新增 `search_two_stage_task_trigger_rankings.py`，在 leave-anchor-out 设定下评估 rule-based 与 lightweight learned ranking，并复用现有 task-level rerun replay 口径输出质量/代价/overlap 指标。最后用真实 panel 生成 offline calibration 结论，并只在通过 promotion gate 时考虑后续 runtime confirm。

**Tech Stack:** Python 3, stdlib, `numpy`, `pandas`, `scikit-learn`, shell checks, Makefile targets

### Task 1: 扩展 analyze 输出字段

**Files:**
- Modify: `scripts/analyze_two_stage_task_ambiguity.py`
- Modify: `scripts/check_analyze_two_stage_task_ambiguity.sh`

**Step 1: 写 failing check**

让 check 断言以下新字段存在并正确：
- `rejected_score_sum`
- `rejected_score_mean`
- `rejected_score_top3_sum`
- `rejected_score_x_bp_sum`
- `rejected_score_x_support_sum`
- `reject_reason_bp_totals`
- `rule_strand_object_count`
- `rule_strand_entropy`
- `tile_rank_by_best_rejected_score`
- `tile_rank_by_rejected_score_x_bp_sum`

**Step 2: 跑 check 确认失败**

Run: `bash ./scripts/check_analyze_two_stage_task_ambiguity.sh`

**Step 3: 最小实现**

在 task-level deployable features 中补齐 task 内聚合字段，并在 tile 级别回填 rank 字段。

**Step 4: 跑 check 确认通过**

Run: `make check-analyze-two-stage-task-ambiguity`

### Task 2: 新增 calibrated ranking search 脚本

**Files:**
- Create: `scripts/search_two_stage_task_trigger_rankings.py`
- Create: `scripts/check_search_two_stage_task_trigger_rankings.sh`
- Modify: `Makefile`

**Step 1: 写 failing check**

新增 check，覆盖：
- rule candidates: `rule_score_mass_gap_v2`, `rule_support_reason_pressure_v2`
- learned candidates: `lr_budget16_rank_v1`, `hgb_budget16_rank_v1`
- leave-anchor-out learned scoring
- replay-style aggregate metrics 与 promotion gate 字段

**Step 2: 跑 check 确认失败**

Run: `bash ./scripts/check_search_two_stage_task_trigger_rankings.sh`

**Step 3: 最小实现**

实现：
- feature matrix 构建
- rule-based candidate scoring
- learned ranking（leave-anchor-out）
- replay-compatible budget evaluation
- markdown/json summary 输出

**Step 4: 跑 check 确认通过**

Run: `make check-search-two-stage-task-trigger-rankings`

### Task 3: 真实离线搜索与文档同步

**Files:**
- Modify: `README.md`
- Modify: `EXACT_SIM_PROGRESS.md`

**Step 1: 跑本地 checks**

Run:
- `make check-analyze-two-stage-task-ambiguity`
- `make check-search-two-stage-task-trigger-rankings`
- `make check-replay-two-stage-task-level-rerun`

**Step 2: 跑真实 offline calibration**

基于当前固定 panel 的 deployable analysis summary 执行 search，记录各 candidate 在 budget 8/16 的：
- `delta_top_hit_retention`
- `delta_top10_retention`
- `delta_score_weighted_recall`
- `delta_refine_total_bp_total`
- `oracle_overlap`

**Step 3: 更新文档**

把 candidate library、promotion gate、真实结果与 recommended next step 写入 README 与进展文档。

**Step 4: 收尾**

Run:
- `git diff --check`
- 清理 `scripts/__pycache__/`

### Task 4: 验证与交接

**Files:**
- Review: 以上所有修改文件

**Step 1: 全量验证**

Run all relevant checks and capture output.

**Step 2: 风险评估**

确认 learned ranking 仍然只依赖 deployable features，且没有把 oracle-only 信号泄漏到推理特征里。

**Step 3: 交接**

记录：
- 哪个 candidate 最接近 oracle
- 是否达到 promotion gate
- 是否应继续 runtime confirm
