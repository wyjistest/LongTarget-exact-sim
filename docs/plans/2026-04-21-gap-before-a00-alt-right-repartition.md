# Gap Before A00 Alt Right Repartition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new low-overhead `alt_right_repart` boundary for `gap_before_a00_span_0_alt_right` so near-tie child splits can be replaced by a more discriminative continuous-source partition, while keeping runtime prototypes disabled.

**Architecture:** Reuse existing sampled low-overhead spans instead of adding fresh per-event timers. Derive a new continuous parent region by extending the current `alt_right` neighborhood through the adjacent `A00` erase span, then split it into `repart_left` and `repart_right` at a natural pre-erase vs erase boundary. Export the derived fields through the profile harness and teach the A/B summarizer to gate on `alt_right_repart` closure, margin, and dominance stability.

**Tech Stack:** C++, Python, shell regression scripts

# Plan: Gap Before A00 Alt Right Repartition

🎯 任务概述
当前 `gap_before_a00_span_0_alt_right` 的 overhead、coverage 和 sampled trust 都已闭合，但 `child_0/child_1` 只是连续取 timestamp 的缝隙，真实结果也落在 `near_tie`。这轮不再继续拆旧 child，而是重新定义这个源码邻域的边界：用已有 `alt_right` 与紧邻的 `A00` 擦除段派生一个新的 `alt_right_repart` parent，并只在 summarizer 允许时继续拆 `repart_left` 或 `repart_right`。

📋 执行计划
1. 在 `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh` 增加 `alt_right_repart` RED 场景：`stable_left`、`stable_right`、`near_tie`、`coverage_open`。
2. 运行该检查脚本，确认当前实现还不支持 `alt_right_repart_*` 字段与新的决策分支，得到 RED。
3. 修改 `tests/sim_initial_host_merge_context_apply_profile.cpp`，基于已有 `alt_right` + `A00` 指标派生：
   - `terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds`
   - `...repart_left_seconds`
   - `...repart_right_seconds`
   - `...repart_child_known_seconds`
   - `...repart_unexplained_seconds`
   - `...repart_*sampled_event_count`
   - `dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child`
4. 更新 raw/aggregate TSV 与 summary JSON 导出，让 `alt_right_repart` 字段在 artifact 中可见。
5. 修改 `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py`，聚合 `alt_right_repart` 的 closure、dominance 和 gate：
   - `coverage open` -> `inspect_gap_before_a00_span_0_alt_right_repart_timer_scope`
   - `near_tie` / low-margin conflict -> `repartition_gap_before_a00_span_0_alt_right_boundary`
   - stable dominant -> `split_gap_before_a00_span_0_alt_right_repart_left|right`
6. 重新运行 RED 脚本，确认新场景转绿。
7. 运行现有回归：
   - `bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
   - `bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

⚠️ 风险与注意事项
- 这轮仍然是 profiler-only；`runtime_prototype_allowed` 必须保持 `false`。
- `alt_right_repart` 必须优先派生，不能回到 full per-event lexical timers。
- 新 parent 是对当前 `alt_right` 邻域的重切，不应再复用旧 `child_0/child_1` dominance 直接下钻。
- 当前 worktree 已有大量未提交修改，只能增量编辑相关文件，不能回退他人改动。

📎 参考
- `sim.h:9142`
- `tests/sim_initial_host_merge_context_apply_profile.cpp:393`
- `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py:2375`
- `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh:1140`
