# Gap Before A00 Span 0 Alt Boundary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repartition `gap_before_a00_span_0` with a more discriminative sampled lexical boundary (`alt_left/alt_right`) and update A/B summarization so low-margin child conflicts route to boundary repartition instead of deeper child splits.

**Architecture:** Keep the existing low-overhead sampled profiler path and reuse the same parent sampled flag inside the `gap_before_a00` pre-`a00` region. Add an alternate lexical partition (`alt_left/alt_right`) that groups the old unstable `span_0` children into a new, more natural continuous-source boundary, then propagate the new fields through replay/export/summary layers while keeping runtime work disabled.

**Tech Stack:** C++, shell checks, Python summarizer

# Plan: Gap Before A00 Span 0 Alt Boundary

🎯 任务概述
当前 `gap_before_a00` 与 `span_0` 的 sampled overhead/coverage 都已闭合，但 `child_0/child_1` 出现 case-weighted 与 seconds-weighted 冲突，且 `margin_share≈0.0006`，不能再继续沿旧边界下钻。这轮只做 profiler-only 重切边界：为 `gap_before_a00_span_0` 增加 `alt_left/alt_right` sampled split，并在 summarizer 中把下一步 gate 收窄到 `repartition_*`、`split_*_alt_left`、`split_*_alt_right` 或 `inspect_*_alt_timer_scope`。

📋 执行计划
1. 在 `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh` 增加 `alt boundary` 场景：`alt_left stable`、`alt_right stable`、`alt low-margin conflict`。
2. 运行该检查脚本，确认当前实现还不支持 `alt_*` 字段与新决策分支，得到 RED。
3. 修改 `sim.h`，为 `gap_before_a00_span_0` 增加 `alt_parent/alt_left/alt_right` 的 sampled 计时、计数和 coverage mask 闭合。
4. 修改 `tests/sim_initial_host_merge_context_apply_profile.cpp`，把 `alt_*` 字段导出到 raw/aggregate TSV、derived metrics 和 dominant-child summary。
5. 修改 `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py`，聚合 `alt_*` 字段并更新低扰动决策链：
   - low-margin conflict -> `repartition_gap_before_a00_span_0_boundary`
   - stable alt dominant -> `split_gap_before_a00_span_0_alt_left|right`
   - alt coverage/scope open -> `inspect_gap_before_a00_span_0_alt_timer_scope`
6. 重新运行红测脚本，确认新场景转绿。
7. 运行 `make tests/sim_initial_host_merge_context_apply_profile`、`bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`、`bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh` 做回归验证。
8. 如验证全部通过，再按同一 5-case workload 重跑真实低扰动 A/B artifact，确认 real summary 改为 `repartition_gap_before_a00_span_0_boundary` 或稳定的 `split_gap_before_a00_span_0_alt_left|right`。

⚠️ 风险与注意事项
- 只能沿用 sampled 低扰动口径，不能回到 full per-event lexical timers。
- `multi_child_share` 在连续源码区间模型下允许为 1.0，真正的 closure gate 仍然是 `unclassified_share`。
- `alt boundary` 必须复用同一个 parent sampled flag，不能引入新的 sample predicate。
- 当前 worktree 有大量无关改动，不能回退不属于本轮的修改。

📎 参考
- `sim.h:9048`
- `tests/sim_initial_host_merge_context_apply_profile.cpp:132`
- `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py:1090`
- `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh:493`
