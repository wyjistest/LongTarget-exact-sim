#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_chr22"}"
MIN_TWO_SLOT_IMPROVEMENT="${MIN_TWO_SLOT_IMPROVEMENT:-0.05}"
MAX_VARIABILITY_EXPANSION="${MAX_VARIABILITY_EXPANSION:-0}"

for path in "$WORK/runs.tsv" "$WORK/topk_compare.tsv" "$WORK/summary.txt" "$WORK/report.txt" "$WORK/extracted_determinism_summary.txt" "$WORK/two_slot_serialized_determinism_summary.txt" "$WORK/two_slot_determinism_summary.txt"; do
  if [[ ! -s "$path" ]]; then
    echo "missing characterization artifact: $path" >&2
    exit 1
  fi
done

python3 - "$WORK" "$MIN_TWO_SLOT_IMPROVEMENT" "$MAX_VARIABILITY_EXPANSION" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

work = Path(sys.argv[1])
min_improvement = float(sys.argv[2])
max_variability_expansion = int(float(sys.argv[3]))
runs = list(csv.DictReader((work / "runs.tsv").open(), delimiter="\t"))
topk = list(csv.DictReader((work / "topk_compare.tsv").open(), delimiter="\t"))

def read_summary(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value
    return data

summary = read_summary(work / "summary.txt")
extracted_det = read_summary(work / "extracted_determinism_summary.txt")
serialized_det = read_summary(work / "two_slot_serialized_determinism_summary.txt")
two_slot_det = read_summary(work / "two_slot_determinism_summary.txt")
errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(float(row.get(key, "0") or "0"))
    except ValueError:
        fail(f"{row.get('case')} run {row.get('repeat')}: bad integer {key}={row.get(key)}")
        return 0

def as_float_text(value: str | None, key: str) -> float:
    try:
        return float(value or "0")
    except ValueError:
        fail(f"bad float {key}={value}")
        return math.nan

cases = {row["case"] for row in runs}
for required in ("legacy", "extracted", "two_slot_serialized", "two_slot", "extracted_validate"):
    if required not in cases:
        fail(f"missing case: {required}")

for row in runs:
    case = row["case"]
    repeat = row["repeat"]
    phase_flushes = as_int(row, "phase_flushes")
    if phase_flushes != 94:
        fail(f"{case} run {repeat}: expected phase_flushes=94, got {phase_flushes}")
    if as_int(row, "gasal2_fallbacks") != 0:
        fail(f"{case} run {repeat}: gasal2 fallback nonzero")
    if as_int(row, "gasal2_length_guard_fallbacks") != 0:
        fail(f"{case} run {repeat}: length guard fallback nonzero")

    if case in {"two_slot", "two_slot_serialized"}:
        if row.get("two_slot_requested") != "1" or row.get("two_slot_active") != "1":
            fail(f"{case} run {repeat}: not requested/active")
        submitted = as_int(row, "two_slot_gpu_submitted")
        finalized = as_int(row, "two_slot_finalized")
        committed = as_int(row, "two_slot_committed")
        if not (submitted == finalized == committed == 94):
            fail(
                f"{case} run {repeat}: bad flush accounting "
                f"submitted={submitted} finalized={finalized} committed={committed}"
            )
        for key in (
            "two_slot_unsupported",
            "two_slot_legacy_fallback",
            "two_slot_state_transition_violations",
            "two_slot_order_violations",
            "two_slot_allocation_failures",
            "two_slot_missing_rows",
            "two_slot_extra_rows",
            "two_slot_order_mismatches",
            "two_slot_cigar_mismatches",
            "two_slot_coordinate_mismatches",
            "two_slot_counter_mismatches",
            "two_slot_archive_descriptor_mismatches",
        ):
            if as_int(row, key) != 0:
                fail(f"{case} run {repeat}: expected {key}=0, got {row.get(key)}")
        if case == "two_slot":
            if row.get("two_slot_decision") != "two_slot_active_clean_no_fallback":
                fail(f"two_slot run {repeat}: decision={row.get('two_slot_decision')}")
            if row.get("two_slot_gpu_cpu_overlap_measurement_supported") != "0":
                fail(f"two_slot run {repeat}: unexpected GPU/CPU overlap support marker")
            if row.get("two_slot_gpu_cpu_overlap_seconds") != "unavailable":
                fail(f"two_slot run {repeat}: gpu_cpu_overlap_seconds={row.get('two_slot_gpu_cpu_overlap_seconds')}")
            for key in (
                "two_slot_slot0_submit_count",
                "two_slot_slot1_submit_count",
                "two_slot_slot0_finalize_count",
                "two_slot_slot1_finalize_count",
                "two_slot_slot0_commit_count",
                "two_slot_slot1_commit_count",
            ):
                if as_int(row, key) <= 0:
                    fail(f"two_slot run {repeat}: expected {key}>0, got {row.get(key)}")
            if as_float_text(row.get("two_slot_host_scheduling_overlap_seconds"), "two_slot_host_scheduling_overlap_seconds") <= 0:
                fail(f"two_slot run {repeat}: no host scheduling overlap")
            if as_int(row, "two_slot_slot0_peak_live_bytes") <= 0 or as_int(row, "two_slot_slot1_peak_live_bytes") <= 0:
                fail(f"two_slot run {repeat}: slot live bytes not recorded")
        else:
            if row.get("two_slot_decision") != "two_slot_serialized_control_clean_no_fallback":
                fail(f"serialized run {repeat}: decision={row.get('two_slot_decision')}")
            if row.get("two_slot_serialized_control_requested") != "1" or row.get("two_slot_serialized_control_active") != "1":
                fail(f"serialized run {repeat}: control not active")
            if as_int(row, "two_slot_max_live_slots") > 1:
                fail(f"serialized run {repeat}: max_live_slots={row.get('two_slot_max_live_slots')}")
            if abs(as_float_text(row.get("two_slot_time_with_2_live_slots_seconds"), "serialized_time_with_2_live_slots_seconds")) > 1e-9:
                fail(f"serialized run {repeat}: time_with_2_live_slots_seconds={row.get('two_slot_time_with_2_live_slots_seconds')}")
            if abs(as_float_text(row.get("two_slot_host_scheduling_overlap_seconds"), "serialized_host_scheduling_overlap_seconds")) > 1e-9:
                fail(f"serialized run {repeat}: host overlap={row.get('two_slot_host_scheduling_overlap_seconds')}")
        if as_int(row, "two_slot_host_peak_bytes") <= 0:
            fail(f"{case} run {repeat}: host peak bytes not recorded")
    elif case == "extracted":
        if row.get("extracted_requested") != "1" or row.get("extracted_active") != "1":
            fail(f"extracted run {repeat}: not requested/active")
        if row.get("extracted_decision") != "real_extracted_active_clean_no_fallback":
            fail(f"extracted run {repeat}: decision={row.get('extracted_decision')}")
        if as_int(row, "extracted_legacy_fallback_flushes") != 0:
            fail(f"extracted run {repeat}: legacy fallback nonzero")
    elif case == "extracted_validate":
        if row.get("extracted_validate_active") != "1":
            fail(f"validate run {repeat}: validate inactive")
        ready = as_int(row, "extracted_ready_flushes")
        if ready != 94:
            fail(f"validate run {repeat}: ready={ready}")
        if as_int(row, "extracted_comparison_performed") != ready:
            fail(f"validate run {repeat}: comparison count mismatch")

for row in topk:
    if row["case"] not in {"extracted", "two_slot_serialized", "two_slot", "extracted_validate"}:
        continue
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            fail(f"{row['case']} run {row['repeat']}: {key}={row.get(key)}")

improvement = as_float_text(
    summary.get("two_slot_wall_improvement_fraction_vs_extracted"),
    "two_slot_wall_improvement_fraction_vs_extracted",
)
if not math.isnan(improvement) and improvement < min_improvement:
    fail(
        f"two-slot median wall improvement {improvement:.6f} below MIN_TWO_SLOT_IMPROVEMENT={min_improvement:.6f}"
    )

def det_int(data: dict[str, str], key: str) -> int:
    try:
        return int(float(data.get(key, "0") or "0"))
    except ValueError:
        fail(f"bad determinism integer {key}={data.get(key)}")
        return 0

for key in ("max_pair_set_missing", "max_pair_set_extra", "max_pair_multiset_missing", "max_pair_multiset_extra"):
    extracted_value = det_int(extracted_det, key)
    two_slot_value = det_int(two_slot_det, key)
    if two_slot_value > extracted_value + max_variability_expansion:
        fail(
            f"two-slot variability expanded for {key}: two_slot={two_slot_value} extracted={extracted_value}"
        )

for key in ("top5_score_stable", "top5_stability_stable", "top5_nt_score_stable"):
    if serialized_det.get(key) != "true":
        fail(f"serialized determinism {key}={serialized_det.get(key)}")
    if two_slot_det.get(key) != "true":
        fail(f"two-slot determinism {key}={two_slot_det.get(key)}")

if errors:
    for message in errors:
        print(message, file=sys.stderr)
    raise SystemExit(1)

print("check_fasim_gasal2_flush_two_slot_overlap_chr22_result: ok")
print(f"runs={len(runs)}")
print(f"two_slot_wall_improvement_fraction_vs_extracted={summary.get('two_slot_wall_improvement_fraction_vs_extracted', 'unknown')}")
print(f"two_slot_wall_saving_seconds_vs_extracted={summary.get('two_slot_wall_saving_seconds_vs_extracted', 'unknown')}")
print(f"two_slot_wall_improvement_fraction_vs_serialized={summary.get('two_slot_wall_improvement_fraction_vs_serialized', 'unknown')}")
print(f"two_slot_wall_saving_seconds_vs_serialized={summary.get('two_slot_wall_saving_seconds_vs_serialized', 'unknown')}")
print(f"two_slot_gpu_cpu_overlap_measurement_supported={summary.get('two_slot_gpu_cpu_overlap_measurement_supported', '0')}")
print(f"two_slot_gpu_cpu_overlap_seconds_median={summary.get('two_slot_gpu_cpu_overlap_seconds_median', 'unavailable')}")
print(f"two_slot_host_scheduling_overlap_seconds_median={summary.get('two_slot_host_scheduling_overlap_seconds_median', 'unknown')}")
print(f"two_slot_host_peak_bytes_median={summary.get('two_slot_host_peak_bytes_median', 'unknown')}")
PY
