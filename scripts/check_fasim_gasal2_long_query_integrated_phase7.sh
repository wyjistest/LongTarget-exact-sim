#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_integrated_phase7"}"
DOC="$ROOT/docs/fasim_gasal2_long_query_integrated_result.md"
BENCHMARK="$ROOT/docs/fasim_gasal2_long_query_integrated_benchmark.tsv"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
GOAL="$ROOT/goal.md"
LOCAL_RESULT="$ROOT/.tmp/phase7_gasal2_long_query_integrated"

for path in "$DOC" "$BENCHMARK" "$MATRIX" "$GOAL"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 7 result dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py" \
  >"$WORK/runner-tests.log" 2>&1
python3 "$ROOT/tests/check_compare_fasim_gasal2_long_query_integrated.py" \
  >"$WORK/comparator-tests.log" 2>&1
python3 "$ROOT/tests/check_summarize_fasim_gasal2_long_query_integrated.py" \
  >"$WORK/summarizer-tests.log" 2>&1

python3 - "$BENCHMARK" "$DOC" "$MATRIX" "$GOAL" \
  "$ROOT/scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh" \
  "$ROOT/scripts/compare_fasim_gasal2_long_query_integrated.py" \
  "$ROOT/scripts/summarize_fasim_gasal2_long_query_integrated.py" \
  "$ROOT/scripts/characterize_fasim_gasal2_long_query_integrated_phase7.sh" \
  "$ROOT/Makefile" "$LOCAL_RESULT" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


benchmark_path = Path(sys.argv[1])
doc = Path(sys.argv[2]).read_text(encoding="utf-8")
matrix = Path(sys.argv[3]).read_text(encoding="utf-8")
goal = Path(sys.argv[4]).read_text(encoding="utf-8")
runner = Path(sys.argv[5]).read_text(encoding="utf-8")
comparator = Path(sys.argv[6]).read_text(encoding="utf-8")
summarizer = Path(sys.argv[7]).read_text(encoding="utf-8")
driver = Path(sys.argv[8]).read_text(encoding="utf-8")
makefile = Path(sys.argv[9]).read_text(encoding="utf-8")
local_result = Path(sys.argv[10])

with benchmark_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
by_name = {row["workload"]: row for row in rows}
if set(by_name) != {"small", "h19_short", "max4", "max8"}:
    raise SystemExit(f"unexpected Phase 7 benchmark workload set: {sorted(by_name)}")


def number(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"invalid {row.get('workload')} {key}") from exc
    if not math.isfinite(value) or value < 0:
        raise SystemExit(f"invalid non-negative {row.get('workload')} {key}={value}")
    return value


for workload, row in by_name.items():
    if row["contracts_clean"] != "1" or row["direction_stable"] != "1":
        raise SystemExit(f"{workload}: integrated contract/direction is not clean")
    if number(row, "candidate_wall_median") >= number(row, "baseline_wall_median"):
        raise SystemExit(f"{workload}: candidate did not improve")

max8 = by_name["max8"]
if max8["repeats"] != "2":
    raise SystemExit("max8 must retain two interleaved repeats")
if not math.isclose(number(max8, "speedup"), 1.089028, abs_tol=1e-6):
    raise SystemExit("max8 speedup receipt drifted")
if not math.isclose(
    number(max8, "wall_reduction_percent"), 8.175018, abs_tol=1e-6
):
    raise SystemExit("max8 wall-reduction receipt drifted")
if number(max8, "speedup") >= 1.10:
    raise SystemExit("max8 unexpectedly crossed the Phase 7 runtime gate")
if number(max8, "exact_stage_reduction_percent") < 25.0:
    raise SystemExit("max8 exact-stage benefit drifted below the measured range")
if number(by_name["h19_short"], "candidate_wall_median") > (
    number(by_name["h19_short"], "baseline_wall_median") * 1.03
):
    raise SystemExit("short-query regression gate failed")

required_doc = (
    "Phase 7 is an evidence-complete `no_go`",
    "max8 median speedup=1.089028x",
    "max8 median wall reduction=8.175018%",
    "max8_full_run_allowed=0",
    "archive/text reduction=6.377893x",
    "peak compute-process device memory=14976 MiB",
    "full segmented KCNQ1OT1 x chr22 candidate=not run",
    "not a claim that every segment was independently sampled",
)
for phrase in required_doc:
    if phrase not in doc:
        raise SystemExit(f"Phase 7 doc missing required phrase: {phrase}")
for forbidden in (
    "full KCNQ1OT1 equivalence validated",
    "grid stability proves full equivalence",
    "GPU traceback authority=true",
):
    if forbidden in doc:
        raise SystemExit(f"Phase 7 doc contains forbidden claim: {forbidden}")

if "kcnq1ot1_max8_integrated\tsegmented_archive_first_exact_scoreinfo_v1\tbounded_dual_grid\tno_go\ttrue\ttrue\t1.089028" not in matrix:
    raise SystemExit("workload matrix is missing the scoped max8 no-go row")

state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if (
    (state.get("active_phase") != "complete" and int(state.get("active_phase", "0")) < 8)
    or state.get("phase_7_status") != "no_go"
    or int(state.get("last_completed_phase", "0")) < 7
):
    raise SystemExit(f"Phase 7 goal state is inconsistent: {state}")

for phrase in (
    'RESUME="${RESUME:-0}"',
    "run-config.json",
    "segment-complete.json",
    "run-complete.json",
    '"merged_outputs"',
    "os.replace(temporary, receipt)",
    "FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=0",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=0",
):
    if phrase not in runner:
        raise SystemExit(f"integrated runner missing contract: {phrase}")
for phrase in (
    "full output byte mismatch",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_offline_cluster_equal",
):
    if phrase not in comparator:
        raise SystemExit(f"integrated comparator missing contract: {phrase}")
for phrase in (
    "max8_repeats >= 2",
    "max8_reduction >= 10.0",
    '"max8_full_run_allowed"',
):
    if phrase not in summarizer:
        raise SystemExit(f"integrated summarizer missing gate: {phrase}")
for phrase in ("run_pair max4", "run_pair max8", "RESUME=1", "EXACT_SCOREINFO_PRUNED"):
    if phrase not in driver:
        raise SystemExit(f"integrated driver missing ladder contract: {phrase}")
if "check-fasim-gasal2-long-query-integrated-phase7:" not in makefile:
    raise SystemExit("Makefile is missing the Phase 7 aggregate target")

if local_result.is_dir():
    summary_path = local_result / "bounded-summary.txt"
    pairs_path = local_result / "pairs.tsv"
    resource_time = local_result / "resource_probe" / "time.txt"
    resource_gpu = local_result / "resource_probe" / "gpu-memory.csv"
    for path in (summary_path, pairs_path, resource_time, resource_gpu):
        if not path.is_file():
            raise SystemExit(f"incomplete local Phase 7 artifact: {path}")
    local_summary = dict(
        line.split("=", 1)
        for line in summary_path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    if local_summary.get("max8_full_run_allowed") != "0":
        raise SystemExit("local max8 artifact unexpectedly allows full run")
    if local_summary.get("all_pair_contracts_clean") != "1":
        raise SystemExit("local pair contracts are not clean")
    if (local_result / "runs" / "full").exists():
        raise SystemExit("full candidate was run despite the denied max8 gate")

print("ok")
PY

echo "GASAL2 integrated long-query Phase 7 evidence complete: no_go"
