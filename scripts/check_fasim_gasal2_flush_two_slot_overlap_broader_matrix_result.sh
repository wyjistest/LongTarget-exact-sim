#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix_v2"}"
MIN_STRONG_GO_WORKLOADS="${MIN_STRONG_GO_WORKLOADS:-2}"
MIN_WORKLOAD_IMPROVEMENT="${MIN_WORKLOAD_IMPROVEMENT:-0.05}"
ALLOW_SCOPED_GO="${ALLOW_SCOPED_GO:-0}"
MIN_WORKLOADS="${MIN_WORKLOADS:-2}"

for path in "$WORK/runs.tsv" "$WORK/topk_compare.tsv" "$WORK/nsight.tsv" "$WORK/summary.txt" "$WORK/report.txt"; do
  if [[ ! -s "$path" ]]; then
    echo "missing broader matrix artifact: $path" >&2
    exit 1
  fi
done

python3 - "$WORK" "$MIN_STRONG_GO_WORKLOADS" "$MIN_WORKLOAD_IMPROVEMENT" "$ALLOW_SCOPED_GO" "$MIN_WORKLOADS" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

work = Path(sys.argv[1])
min_strong_go = int(float(sys.argv[2]))
min_improvement = float(sys.argv[3])
allow_scoped_go = sys.argv[4] == "1"
min_workloads = int(float(sys.argv[5]))

runs = list(csv.DictReader((work / "runs.tsv").open(), delimiter="\t"))
topk = list(csv.DictReader((work / "topk_compare.tsv").open(), delimiter="\t"))
nsight = list(csv.DictReader((work / "nsight.tsv").open(), delimiter="\t"))

def read_summary(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value
    return data

summary = read_summary(work / "summary.txt")
errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(float(row.get(key, "0") or "0"))
    except ValueError:
        fail(f"{row.get('workload')} {row.get('mode')} run {row.get('repeat')}: bad integer {key}={row.get(key)}")
        return 0

def as_float(value: str | None, key: str) -> float:
    try:
        return float(value or "0")
    except ValueError:
        fail(f"bad float {key}={value}")
        return math.nan

workloads = sorted({row["workload"] for row in runs})
if len(workloads) < min_workloads:
    fail(f"expected at least {min_workloads} workloads, got {workloads}")

for row in runs:
    workload = row["workload"]
    mode = row["mode"]
    repeat = row["repeat"]
    if row.get("schema_version") != "2":
        fail(f"{workload} {mode} run {repeat}: schema_version={row.get('schema_version')}")
    if as_int(row, "gasal2_fallbacks") != 0:
        fail(f"{workload} {mode} run {repeat}: gasal2 fallback nonzero")
    if as_int(row, "gasal2_length_guard_fallbacks") != 0:
        fail(f"{workload} {mode} run {repeat}: length guard fallback nonzero")
    if as_int(row, "phase_flushes") <= 0:
        fail(f"{workload} {mode} run {repeat}: no flushes recorded")

    if mode == "extracted":
        if row.get("extracted_requested") != "1" or row.get("extracted_active") != "1":
            fail(f"{workload} extracted run {repeat}: extracted inactive")
        if row.get("extracted_decision") != "real_extracted_active_clean_no_fallback":
            fail(f"{workload} extracted run {repeat}: decision={row.get('extracted_decision')}")
        if as_int(row, "extracted_legacy_fallback_flushes") != 0:
            fail(f"{workload} extracted run {repeat}: legacy fallback nonzero")
    elif mode in {"two_slot", "two_slot_serialized"}:
        if row.get("two_slot_requested") != "1" or row.get("two_slot_active") != "1":
            fail(f"{workload} {mode} run {repeat}: two-slot inactive")
        submitted = as_int(row, "two_slot_gpu_submitted")
        finalized = as_int(row, "two_slot_finalized")
        committed = as_int(row, "two_slot_committed")
        if not (submitted == finalized == committed == as_int(row, "phase_flushes")):
            fail(f"{workload} {mode} run {repeat}: bad lifecycle submitted={submitted} finalized={finalized} committed={committed} phase={row.get('phase_flushes')}")
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
                fail(f"{workload} {mode} run {repeat}: expected {key}=0, got {row.get(key)}")
        if row.get("two_slot_gpu_cpu_overlap_measurement_supported") != "0":
            fail(f"{workload} {mode} run {repeat}: runtime device-overlap support marker changed")
        if row.get("two_slot_gpu_cpu_overlap_seconds") != "unavailable":
            fail(f"{workload} {mode} run {repeat}: gpu_cpu_overlap_seconds={row.get('two_slot_gpu_cpu_overlap_seconds')}")
        if as_int(row, "two_slot_slot0_submit_count") <= 0 or as_int(row, "two_slot_slot1_submit_count") <= 0:
            fail(f"{workload} {mode} run {repeat}: both slots were not used")
        if as_int(row, "two_slot_host_peak_bytes") <= 0:
            fail(f"{workload} {mode} run {repeat}: host peak bytes not recorded")
        if mode == "two_slot":
            if row.get("two_slot_decision") != "two_slot_active_clean_no_fallback":
                fail(f"{workload} two_slot run {repeat}: decision={row.get('two_slot_decision')}")
            if as_float(row.get("two_slot_host_scheduling_overlap_seconds"), "host_scheduling_overlap") <= 0:
                fail(f"{workload} two_slot run {repeat}: no host scheduling overlap")
        else:
            if row.get("two_slot_decision") != "two_slot_serialized_control_clean_no_fallback":
                fail(f"{workload} serialized run {repeat}: decision={row.get('two_slot_decision')}")
            if abs(as_float(row.get("two_slot_host_scheduling_overlap_seconds"), "serialized_host_overlap")) > 1e-9:
                fail(f"{workload} serialized run {repeat}: host overlap={row.get('two_slot_host_scheduling_overlap_seconds')}")
    elif mode == "two_slot_validate":
        if row.get("two_slot_validate_requested") != "1" or row.get("two_slot_validate_active") != "1":
            fail(f"{workload} validate run {repeat}: validate inactive")
        if row.get("two_slot_decision") != "validate_mode_synchronous_audit":
            fail(f"{workload} validate run {repeat}: decision={row.get('two_slot_decision')}")

for row in topk:
    if row.get("schema_version") != "2":
        fail(f"topk {row.get('workload')} {row.get('mode')}: schema_version={row.get('schema_version')}")
    if row["mode"] not in {"two_slot", "two_slot_serialized", "two_slot_validate"}:
        continue
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            fail(f"{row['workload']} {row['mode']} run {row['repeat']}: {key}={row.get(key)}")

for row in nsight:
    if row.get("schema_version") != "2":
        fail(f"nsight {row.get('workload')}: schema_version={row.get('schema_version')}")
    if as_float(row.get("host_scheduling_overlap_seconds"), "nsight_host_overlap") <= 0:
        fail(f"nsight {row.get('workload')}: no host scheduling overlap")
    if as_float(row.get("cpu_finalizer_gpu_activity_overlap_seconds"), "device_overlap") <= 0:
        fail(f"nsight {row.get('workload')}: no device activity overlap")
    kernel = as_float(row.get("cpu_finalizer_kernel_overlap_seconds"), "kernel_overlap")
    memcpy = as_float(row.get("cpu_finalizer_memcpy_overlap_seconds"), "memcpy_overlap")
    total = as_float(row.get("cpu_finalizer_gpu_activity_overlap_seconds"), "total_overlap")
    if kernel + memcpy + 1e-3 < total:
        fail(f"nsight {row.get('workload')}: kernel+memcpy less than total")

if summary.get("schema_version") != "2":
    fail(f"summary schema_version={summary.get('schema_version')}")
if summary.get("runtime_device_overlap_supported") != "false":
    fail(f"runtime_device_overlap_supported={summary.get('runtime_device_overlap_supported')}")
if summary.get("host_scheduling_overlap_available") != "true":
    fail(f"host_scheduling_overlap_available={summary.get('host_scheduling_overlap_available')}")

strong_go_workloads = int(float(summary.get("strong_go_workloads", "0") or "0"))
if strong_go_workloads < min_strong_go and not allow_scoped_go:
    fail(f"strong_go_workloads={strong_go_workloads} below required {min_strong_go}")

for workload in workloads:
    improvement = as_float(
        summary.get(f"{workload}_two_slot_wall_improvement_fraction_vs_extracted"),
        f"{workload}_two_slot_wall_improvement_fraction_vs_extracted",
    )
    if improvement < -0.02:
        fail(f"{workload}: two-slot regression {improvement:.6f}")
    if improvement < min_improvement and not allow_scoped_go:
        fail(f"{workload}: improvement {improvement:.6f} below {min_improvement:.6f}")

if errors:
    for message in errors:
        print(message, file=sys.stderr)
    raise SystemExit(1)

print("check_fasim_gasal2_flush_two_slot_overlap_broader_matrix_result: ok")
print(f"workloads={','.join(workloads)}")
print(f"strong_go_workloads={strong_go_workloads}")
for workload in workloads:
    print(f"{workload}_improvement={summary.get(f'{workload}_two_slot_wall_improvement_fraction_vs_extracted', 'unknown')}")
    print(f"{workload}_host_overlap={summary.get(f'{workload}_two_slot_host_scheduling_overlap_seconds_median', 'unknown')}")
    if f"{workload}_nsight_cpu_finalizer_gpu_activity_overlap_seconds" in summary:
        print(f"{workload}_device_overlap={summary.get(f'{workload}_nsight_cpu_finalizer_gpu_activity_overlap_seconds')}")
PY
