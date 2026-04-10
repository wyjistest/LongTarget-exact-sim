# Panel Coverage Attribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate panel-level coverage attribution for the `minimal_v2` shortlist lane so representative heavy micro-anchor tiles can be summarized into a single `inside_rejected_window` vs `near_kept` vs `far_outside` decision artifact.

**Architecture:** Reuse the existing single-tile threshold benchmark runner and single-tile coverage attribution analyzer. Add one narrow panel orchestration script that reads heavy micro-anchor `summary.json`, reruns only the candidate lane with debug-window TSVs for selected representative tiles, then aggregates per-tile attribution JSON into panel-level JSON/Markdown summaries.

**Tech Stack:** Python 3 CLI tooling, bash check scripts, JSON/Markdown reports

### Task 1: Lock the panel report contract in a failing check

**Files:**
- Create: `/data/wenyujianData/LongTarget-exact-sim/scripts/check_two_stage_coverage_attribution_panel.sh`

**Step 1: Write the failing check**

Require a new panel attribution script to:
- read an existing heavy-panel `summary.json`
- select representative tiles from `strongest_shrink` and `medium_shrink`
- emit `summary.json` and `summary.md`
- include panel aggregate counts/shares for `inside_kept_window`, `inside_rejected_window`, `outside_kept_but_near_kept`, and `far_outside_all_kept`

**Step 2: Run check to verify it fails**

Run: `bash ./scripts/check_two_stage_coverage_attribution_panel.sh`
Expected: FAIL because the panel automation script does not exist yet.

### Task 2: Implement the minimal panel attribution automation

**Files:**
- Create: `/data/wenyujianData/LongTarget-exact-sim/scripts/analyze_two_stage_coverage_attribution_panel.py`
- Modify if needed: `/data/wenyujianData/LongTarget-exact-sim/scripts/analyze_two_stage_coverage_attribution.py`
- Modify if needed: `/data/wenyujianData/LongTarget-exact-sim/scripts/benchmark_two_stage_threshold_modes.py`

**Step 1: Keep the scope narrow**

Implement only:
- panel summary ingestion
- representative tile selection
- candidate-only rerun with `--debug-window-run-label`
- single-tile attribution invocation
- panel aggregate JSON/Markdown rendering

Do not add fallback logic, new gate rules, or broader sweep behavior here.

**Step 2: Keep outputs directly decision-friendly**

Write:
- per-tile attribution JSONs under the panel work directory
- panel `summary.json`
- panel `summary.md`

Include aggregate views for:
- overall missing
- top5 missing
- top10 missing
- score-weighted missing

### Task 3: Verify with targeted checks and one real panel run

**Files:**
- No required file changes beyond Task 1/2 unless verification exposes a small fix

**Step 1: Run targeted validation**

Run:
- `python3 -m py_compile scripts/analyze_two_stage_coverage_attribution_panel.py scripts/analyze_two_stage_coverage_attribution.py scripts/benchmark_two_stage_threshold_modes.py`
- `bash ./scripts/check_two_stage_coverage_attribution.sh`
- `bash ./scripts/check_two_stage_threshold_modes.sh`
- `bash ./scripts/check_two_stage_coverage_attribution_panel.sh`

**Step 2: Run one real panel summary**

Run the new panel script against:
- `/data/wenyujianData/LongTarget-exact-sim/.tmp/panel_minimal_v2_2026-04-10_chr22_3anchor/summary.json`

Confirm the output is enough to decide whether misses are still dominated by `inside_rejected_window`.

**Step 3: Commit**

```bash
git add docs/plans/2026-04-10-panel-coverage-attribution.md scripts/check_two_stage_coverage_attribution_panel.sh scripts/analyze_two_stage_coverage_attribution_panel.py
git commit -m "Add panel coverage attribution automation"
```

### Risks and Notes

- Re-running representative tiles with debug windows is materially cheaper than a full broader sweep, but still shells out to LongTarget; keep the selector narrow.
- The panel summary schema must stay tolerant of existing heavy-panel outputs, because this is post-hoc analysis over already-generated panel results.
- The goal is attribution, not gate tuning; any signal that points toward selective fallback should be left to the next change.
