#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_extracted_finalizer_chr22"}"
MAX_EXTRACTED_OVERHEAD="${MAX_EXTRACTED_OVERHEAD:-0.02}"

for path in "$WORK/runs.tsv" "$WORK/topk_compare.tsv" "$WORK/summary.txt"; do
  if [[ ! -s "$path" ]]; then
    echo "missing characterization artifact: $path" >&2
    exit 1
  fi
done

python3 - "$WORK" "$MAX_EXTRACTED_OVERHEAD" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

work = Path(sys.argv[1])
max_overhead = float(sys.argv[2])
runs = list(csv.DictReader((work / "runs.tsv").open(), delimiter="\t"))
topk = list(csv.DictReader((work / "topk_compare.tsv").open(), delimiter="\t"))
summary: dict[str, str] = {}
for line in (work / "summary.txt").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        summary[key] = value

errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(float(row.get(key, "0") or "0"))
    except ValueError:
        fail(f"{row.get('case')} run {row.get('repeat')}: bad integer {key}={row.get(key)}")
        return 0

def as_float_value(value: str, key: str) -> float:
    try:
        return float(value)
    except ValueError:
        fail(f"bad float {key}={value}")
        return math.nan

def all_zero(row: dict[str, str], keys: list[str]) -> None:
    for key in keys:
        if as_int(row, key) != 0:
            fail(f"{row['case']} run {row['repeat']}: expected {key}=0, got {row.get(key)}")

cases = {row["case"] for row in runs}
for required in ("legacy", "extracted", "extracted_validate"):
    if required not in cases:
        fail(f"missing case: {required}")

mismatch_keys = [
    "extracted_missing_rows",
    "extracted_extra_rows",
    "extracted_order_mismatches",
    "extracted_cigar_mismatches",
    "extracted_coordinate_mismatches",
    "extracted_counter_mismatches",
    "extracted_archive_descriptor_mismatches",
]

for row in runs:
    case = row["case"]
    repeat = row["repeat"]
    if case == "legacy":
        continue
    ready = as_int(row, "extracted_ready_flushes")
    observed = as_int(row, "extracted_observed_flushes")
    eligible = as_int(row, "extracted_eligible_flushes")
    committed = as_int(row, "extracted_committed_flushes")
    unsupported = as_int(row, "extracted_unsupported_flushes")
    fallback = as_int(row, "extracted_legacy_fallback_flushes")
    active_flushes = as_int(row, "extracted_extracted_active_flushes")
    extracted_exec = as_int(row, "extracted_extracted_finalizer_executed")
    legacy_exec = as_int(row, "extracted_legacy_finalizer_executed")
    comparison = as_int(row, "extracted_comparison_performed")
    decision = row.get("extracted_decision", "")

    if row.get("extracted_requested") != "1" or row.get("extracted_active") != "1":
        fail(f"{case} run {repeat}: extracted finalizer not requested/active")
    if ready < 1:
        fail(f"{case} run {repeat}: no ready flushes")
    if not (observed == ready == eligible == committed == active_flushes):
        fail(
            f"{case} run {repeat}: bad flush accounting "
            f"observed={observed} ready={ready} eligible={eligible} committed={committed} "
            f"active={active_flushes}"
        )
    if unsupported != 0 or fallback != 0:
        fail(f"{case} run {repeat}: unsupported={unsupported} fallback={fallback}")
    all_zero(row, mismatch_keys)
    if decision != "real_extracted_active_clean_no_fallback":
        fail(f"{case} run {repeat}: decision={decision}")
    if as_int(row, "ordered_order_violations") != 0:
        fail(f"{case} run {repeat}: ordered commit violation")
    if as_int(row, "ordered_result_bytes_includes_traceback") != 1:
        fail(f"{case} run {repeat}: missing ordered result_bytes_includes_traceback marker")
    if as_int(row, "result_boundary_result_bytes_includes_traceback") != 1:
        fail(f"{case} run {repeat}: missing result boundary result_bytes_includes_traceback marker")

    if case == "extracted":
        if row.get("extracted_validate_active") != "0":
            fail(f"{case} run {repeat}: validate should be inactive")
        if legacy_exec != 0 or comparison != 0:
            fail(f"{case} run {repeat}: legacy_exec={legacy_exec} comparison={comparison}")
        if extracted_exec != ready:
            fail(f"{case} run {repeat}: extracted_exec={extracted_exec} ready={ready}")
    elif case == "extracted_validate":
        if row.get("extracted_validate_active") != "1":
            fail(f"{case} run {repeat}: validate should be active")
        if legacy_exec != ready or extracted_exec != ready or comparison != ready:
            fail(
                f"{case} run {repeat}: bad validate accounting "
                f"legacy_exec={legacy_exec} extracted_exec={extracted_exec} comparison={comparison} ready={ready}"
            )
        if as_int(row, "extracted_legacy_rows") != as_int(row, "extracted_extracted_rows"):
            fail(
                f"{case} run {repeat}: legacy/extracted rows differ "
                f"{row.get('extracted_legacy_rows')} vs {row.get('extracted_extracted_rows')}"
            )

for row in topk:
    case = row["case"]
    if case not in {"extracted", "extracted_validate"}:
        continue
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            fail(f"{case} run {row['repeat']}: {key}={row.get(key)}")

overhead_text = summary.get("extracted_wall_overhead_fraction_vs_legacy")
if overhead_text is None:
    fail("summary missing extracted_wall_overhead_fraction_vs_legacy")
else:
    overhead = as_float_value(overhead_text, "extracted_wall_overhead_fraction_vs_legacy")
    if not math.isnan(overhead) and overhead > max_overhead:
        fail(
            f"extracted overhead {overhead:.6f} exceeds MAX_EXTRACTED_OVERHEAD={max_overhead:.6f}"
        )

if errors:
    for message in errors:
        print(message, file=sys.stderr)
    raise SystemExit(1)

print("check_fasim_gasal2_flush_extracted_finalizer_chr22_result: ok")
print(f"runs={len(runs)}")
print(f"extracted_wall_overhead_fraction_vs_legacy={summary.get('extracted_wall_overhead_fraction_vs_legacy', 'unknown')}")
PY
