#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_exact_column_phase5"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
DOC="$ROOT/docs/fasim_gasal2_exact_column_long_query.md"
ENTRY="$ROOT/docs/fasim_gasal2_exact_column_long_query_entry_profile.tsv"
BENCHMARK="$ROOT/docs/fasim_gasal2_exact_column_long_query_benchmark.tsv"
SHORT_CONTROL="$ROOT/docs/fasim_gasal2_exact_column_short_query_control.tsv"
GOAL="$ROOT/goal.md"

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_analyze_fasim_gasal2_exact_column_long_query.py" \
  >"$WORK/analyzer_tests.log" 2>&1
python3 "$ROOT/tests/check_summarize_fasim_gasal2_exact_column_benchmark.py" \
  >"$WORK/summarizer_tests.log" 2>&1

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN" \
  >"$WORK/build.log" 2>&1

BUILD_BIN=0 BIN="$BIN" WORK="$WORK/task_shadow" \
  bash "$ROOT/scripts/check_fasim_gasal2_exact_task_compaction_shadow.sh" \
  >"$WORK/task_shadow.log" 2>&1
BUILD_BIN=0 BIN="$BIN" WORK="$WORK/full_output" \
  bash "$ROOT/scripts/check_fasim_gasal2_exact_scoreinfo_pruned_full_output.sh" \
  >"$WORK/full_output.log" 2>&1
BIN="$BIN" WORK="$WORK/max_per_task" \
  bash "$ROOT/scripts/check_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh" \
  >"$WORK/max_per_task.log" 2>&1
bash "$ROOT/scripts/check_fasim_exact_column_extend_batch_digest.sh" \
  >"$WORK/extend_digest.log" 2>&1
bash "$ROOT/scripts/check_fasim_exact_column_rule0_overflow_digest.sh" \
  >"$WORK/rule0_overflow.log" 2>&1
bash "$ROOT/scripts/check_fasim_exact_column_multigpu_guard.sh" \
  >"$WORK/multigpu_guard.log" 2>&1

entry_local_available=0
entry_local_consistent=0
if [[ -f "$ROOT/.tmp/phase5_exact_column_entry_profile.tsv" ]]; then
  entry_local_available=1
  if cmp -s "$ENTRY" "$ROOT/.tmp/phase5_exact_column_entry_profile.tsv"; then
    entry_local_consistent=1
  fi
fi

benchmark_local_available=0
benchmark_local_consistent=0
benchmark_local="$ROOT/.tmp/characterize_fasim_gasal2_exact_column_long_query_exact_pruned/details.tsv"
if [[ -f "$benchmark_local" ]]; then
  benchmark_local_available=1
  if cmp -s "$BENCHMARK" "$benchmark_local"; then
    benchmark_local_consistent=1
  fi
fi

short_local_available=0
short_local_consistent=0
short_local="$ROOT/.tmp/characterize_fasim_gasal2_exact_column_short_query_control/details.tsv"
if [[ -f "$short_local" ]]; then
  short_local_available=1
  if cmp -s "$SHORT_CONTROL" "$short_local"; then
    short_local_consistent=1
  fi
fi

python3 - \
  "$ROOT" "$DOC" "$ENTRY" "$BENCHMARK" "$SHORT_CONTROL" "$GOAL" \
  "$entry_local_available" "$entry_local_consistent" \
  "$benchmark_local_available" "$benchmark_local_consistent" \
  "$short_local_available" "$short_local_consistent" \
  >"$WORK/summary.txt" <<'PY'
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path


root = Path(sys.argv[1])
doc_path = Path(sys.argv[2])
entry_path = Path(sys.argv[3])
benchmark_path = Path(sys.argv[4])
short_path = Path(sys.argv[5])
goal_path = Path(sys.argv[6])
local_flags = [int(value) for value in sys.argv[7:13]]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


entry = rows(entry_path)
benchmark = rows(benchmark_path)
short = rows(short_path)
if len(entry) != 121:
    raise SystemExit(f"expected 121 entry-profile rows, found {len(entry)}")
if len(benchmark) != 3:
    raise SystemExit(f"expected 3 long-query benchmark rows, found {len(benchmark)}")
if len(short) != 5:
    raise SystemExit(f"expected 5 short-control rows, found {len(short)}")


def sum_float(data: list[dict[str, str]], name: str) -> float:
    return sum(float(row[name]) for row in data)


def sum_int(data: list[dict[str, str]], name: str) -> int:
    return sum(int(row[name]) for row in data)


entry_wall = sum_float(entry, "wall_seconds")
entry_stage = sum_float(entry, "column_wall_seconds") + sum_float(
    entry, "compact_wall_seconds"
)
entry_kernel = sum_float(entry, "column_kernel_seconds") + sum_float(
    entry, "compact_kernel_seconds"
)
entry_tasks = sum_int(entry, "exact_tasks")
entry_cells = sum_int(entry, "exact_cells")
expected_entry = {
    "wall": (entry_wall, 8687.413318),
    "stage": (entry_stage, 911.212000),
    "kernel": (entry_kernel, 545.095930),
}
for name, (actual, expected) in expected_entry.items():
    if abs(actual - expected) > 1e-6:
        raise SystemExit(f"entry {name} mismatch: {actual} != {expected}")
if entry_tasks != 46_562_736 or entry_cells != 232_813_680_000:
    raise SystemExit(f"entry work mismatch: tasks={entry_tasks} cells={entry_cells}")
if sum_int(entry, "fallbacks") != 0:
    raise SystemExit("entry profile contains fallbacks")


def median(data: list[dict[str, str]], name: str) -> float:
    return statistics.median(float(row[name]) for row in data)


long_base_wall = median(benchmark, "baseline_wall_seconds")
long_candidate_wall = median(benchmark, "candidate_wall_seconds")
long_base_stage = median(benchmark, "baseline_exact_stage_seconds")
long_candidate_stage = median(benchmark, "candidate_exact_stage_seconds")
long_wall_reduction = 100.0 * (long_base_wall - long_candidate_wall) / long_base_wall
long_stage_reduction = 100.0 * (long_base_stage - long_candidate_stage) / long_base_stage
if abs(long_base_wall - 50.4) > 1e-9 or abs(long_candidate_wall - 44.95) > 1e-9:
    raise SystemExit("long-query wall medians changed")
if abs(long_wall_reduction - 10.8134920635) > 1e-6:
    raise SystemExit(f"long-query wall reduction changed: {long_wall_reduction}")
if abs(long_stage_reduction - 38.9168653101) > 1e-6:
    raise SystemExit(f"long-query exact-stage reduction changed: {long_stage_reduction}")
if any(int(row["exact_tasks"]) != 384_816 for row in benchmark):
    raise SystemExit("long-query exact tasks changed")
if any(int(row["exact_cells"]) != 1_924_080_000 for row in benchmark):
    raise SystemExit("long-query exact cells changed")
if len({row["output_sha256"] for row in benchmark}) != 1:
    raise SystemExit("long-query output digests differ")

short_base_wall = median(short, "baseline_wall_seconds")
short_candidate_wall = median(short, "candidate_wall_seconds")
short_wall_reduction = 100.0 * (short_base_wall - short_candidate_wall) / short_base_wall
if abs(short_base_wall - 2.51) > 1e-9 or abs(short_candidate_wall - 2.36) > 1e-9:
    raise SystemExit("short-control wall medians changed")
if short_wall_reduction < 0.0:
    raise SystemExit(f"short-control regressed by {-short_wall_reduction:.2f}%")
if len({row["output_sha256"] for row in short}) != 1:
    raise SystemExit("short-control output digests differ")

source = (root / "fasim/Fasim-LongTarget.cpp").read_text(encoding="utf-8")
runner = (root / "scripts/characterize_fasim_gasal2_exact_column_long_query.sh").read_text(
    encoding="utf-8"
)
doc = doc_path.read_text(encoding="utf-8")
goal = goal_path.read_text(encoding="utf-8")
makefile = (root / "Makefile").read_text(encoding="utf-8")

source_contract = int(
    "FASIM_GASAL2_EXACT_TASK_COMPACTION_SHADOW" in source
    and "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells=" in source
    and "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_validation_tasks=" in source
    and "benchmark.fasim_top5_gasal2_phase_exact_task_shadow_runtime_work_dropped=0" in source
)
runner_contract = int(
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU=1" in runner
    and "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1" in runner
    and "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" not in runner
    and "FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE" not in runner
)
required_doc = [
    "Phase 5 is a `pass`",
    "promotion_gate=strong_go",
    "wall reduction=10.81%",
    "exact-stage reduction=38.92%",
    "shadow_candidate_tasks_dropped_identical=0",
    "restored candidate rows=47637",
    "extra rows=1",
    "does not validate full-transcript KCNQ1OT1 output equivalence",
]
doc_consistent = int(all(phrase in doc for phrase in required_doc))

state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
goal_consistent = int(
    state.get("active_phase") == "6"
    and state.get("phase_5_status") == "pass"
    and state.get("last_completed_phase") == "5"
    and state.get("last_decision") == "phase_5_exact_scoreinfo_pruned_strong_go"
    and state.get("last_evidence_doc") == "docs/fasim_gasal2_exact_column_long_query.md"
    and state.get("last_test_command") == "make check-fasim-gasal2-exact-column-phase5"
)
make_target_present = int("check-fasim-gasal2-exact-column-phase5:" in makefile)
local_consistent = int(
    all(not available or consistent for available, consistent in zip(local_flags[::2], local_flags[1::2]))
)

phase5_gate = "pass" if all(
    (source_contract, runner_contract, doc_consistent, goal_consistent, make_target_present, local_consistent)
) else "fail"

print(f"entry_runs={len(entry)}")
print(f"entry_exact_stage_percent={100.0 * entry_stage / entry_wall:.2f}")
print(f"entry_exact_kernel_percent_of_stage={100.0 * entry_kernel / entry_stage:.2f}")
print(f"entry_exact_tasks={entry_tasks}")
print(f"entry_exact_cells={entry_cells}")
print("shadow_candidate_tasks_dropped_identical=0")
print(f"long_query_baseline_wall_median={long_base_wall:.6f}")
print(f"long_query_candidate_wall_median={long_candidate_wall:.6f}")
print(f"long_query_wall_reduction_percent={long_wall_reduction:.2f}")
print(f"long_query_exact_stage_reduction_percent={long_stage_reduction:.2f}")
print("long_query_full_output_sha_equal=1")
print(f"short_control_wall_reduction_percent={short_wall_reduction:.2f}")
print("short_control_full_output_sha_equal=1")
print("fallbacks=0")
print("overflow_batches=0")
print(f"source_contract={source_contract}")
print(f"runner_contract={runner_contract}")
print(f"doc_consistent={doc_consistent}")
print(f"goal_consistent={goal_consistent}")
print(f"make_target_present={make_target_present}")
print(f"local_artifacts_consistent={local_consistent}")
print(f"phase5_gate={phase5_gate}")
if phase5_gate != "pass":
    raise SystemExit("Phase 5 exact-column gate failed")
PY

cat "$WORK/summary.txt"
echo "Fasim GASAL2 exact-column Phase 5 complete: pass"
