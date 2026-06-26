#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v1"}"
MIN_MULTI_WORKER_STRONG_GO="${MIN_MULTI_WORKER_STRONG_GO:-2}"
MIN_IMPROVEMENT="${MIN_IMPROVEMENT:-0.05}"
ALLOW_SCOPED_GO="${ALLOW_SCOPED_GO:-0}"

for path in "$WORK/runs.tsv" "$WORK/topk_compare.tsv" "$WORK/determinism.tsv" "$WORK/failed_runs.tsv" "$WORK/summary.json"; do
  if [[ ! -s "$path" ]]; then
    echo "missing multi-worker two-slot artifact: $path" >&2
    exit 1
  fi
done

python3 - "$WORK" "$MIN_MULTI_WORKER_STRONG_GO" "$MIN_IMPROVEMENT" "$ALLOW_SCOPED_GO" <<'PY'
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

work = Path(sys.argv[1])
min_strong = int(float(sys.argv[2]))
min_improvement = float(sys.argv[3])
allow_scoped = sys.argv[4] == "1"

runs = list(csv.DictReader((work / "runs.tsv").open(), delimiter="\t"))
topk = list(csv.DictReader((work / "topk_compare.tsv").open(), delimiter="\t"))
determinism = list(csv.DictReader((work / "determinism.tsv").open(), delimiter="\t"))
failed_runs = list(csv.DictReader((work / "failed_runs.tsv").open(), delimiter="\t"))
summary = json.loads((work / "summary.json").read_text())
is_smoke = bool(summary.get("smoke"))
errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(float(row.get(key, "0") or "0"))
    except ValueError:
        fail(f"{row.get('mode')} workers={row.get('worker_count')} repeat={row.get('repeat')}: bad int {key}={row.get(key)}")
        return 0

def as_float(value: object, key: str) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        fail(f"bad float {key}={value}")
        return math.nan

worker_counts = sorted({int(row["worker_count"]) for row in runs})
if 1 not in worker_counts:
    fail("worker_counts does not include 1")
if len(worker_counts) < (2 if summary.get("smoke") else 4):
    attempted = set(worker_counts) | {int(row["worker_count"]) for row in failed_runs}
    if len(attempted) < (2 if summary.get("smoke") else 4):
        fail(f"too few worker counts: completed={worker_counts} attempted={sorted(attempted)}")

for row in runs:
    mode = row["mode"]
    worker = row["worker_count"]
    repeat = row["repeat"]
    if row.get("schema_version") != "1":
        fail(f"{mode} workers={worker} repeat={repeat}: schema_version={row.get('schema_version')}")
    if row.get("run_status") != "completed":
        fail(f"{mode} workers={worker} repeat={repeat}: run_status={row.get('run_status')}")
    if as_int(row, "failed_shards") != 0:
        fail(f"{mode} workers={worker} repeat={repeat}: failed shards")
    if as_int(row, "fasim_gasal2_fallbacks") != 0:
        fail(f"{mode} workers={worker} repeat={repeat}: GASAL2 fallback")
    if as_int(row, "fasim_gasal2_length_guard_fallbacks") != 0:
        fail(f"{mode} workers={worker} repeat={repeat}: length guard fallback")
    material = as_int(row, "fasim_top5_gasal2_phase_flushes") > 0
    if not material and not is_smoke:
        fail(f"{mode} workers={worker} repeat={repeat}: no flushes")
    if as_float(row.get("wall_seconds"), "wall_seconds") <= 0:
        fail(f"{mode} workers={worker} repeat={repeat}: non-positive wall")
    assignment = row.get("worker_gpu_assignment", "")
    if "None" in assignment or not assignment:
        fail(f"{mode} workers={worker} repeat={repeat}: bad GPU assignment {assignment}")

    if mode == "extracted":
        if as_int(row, "fasim_gasal2_extracted_finalizer_requested") <= 0:
            fail(f"extracted workers={worker} repeat={repeat}: not requested")
        if as_int(row, "fasim_gasal2_extracted_finalizer_active") <= 0:
            fail(f"extracted workers={worker} repeat={repeat}: not active")
        expected_extracted_decisions = {"real_extracted_active_clean_no_fallback"}
        if is_smoke and not material:
            expected_extracted_decisions.add("needs_material_workload")
        if row.get("fasim_gasal2_extracted_finalizer_decision") not in expected_extracted_decisions:
            fail(f"extracted workers={worker} repeat={repeat}: decision={row.get('fasim_gasal2_extracted_finalizer_decision')}")
        for key in (
            "fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes",
            "fasim_gasal2_extracted_finalizer_legacy_fallback_flushes",
            "fasim_gasal2_extracted_finalizer_missing_rows",
            "fasim_gasal2_extracted_finalizer_extra_rows",
            "fasim_gasal2_extracted_finalizer_order_mismatches",
            "fasim_gasal2_extracted_finalizer_cigar_mismatches",
            "fasim_gasal2_extracted_finalizer_coordinate_mismatches",
            "fasim_gasal2_extracted_finalizer_counter_mismatches",
            "fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches",
        ):
            if as_int(row, key) != 0:
                fail(f"extracted workers={worker} repeat={repeat}: {key}={row.get(key)}")
    elif mode == "two_slot":
        if as_int(row, "fasim_gasal2_flush_two_slot_overlap_requested") <= 0:
            fail(f"two_slot workers={worker} repeat={repeat}: not requested")
        if as_int(row, "fasim_gasal2_flush_two_slot_overlap_active") <= 0:
            fail(f"two_slot workers={worker} repeat={repeat}: not active")
        expected_two_slot_decisions = {"two_slot_active_clean_no_fallback"}
        if is_smoke and not material:
            expected_two_slot_decisions.add("needs_material_workload")
        if row.get("fasim_gasal2_flush_two_slot_overlap_decision") not in expected_two_slot_decisions:
            fail(f"two_slot workers={worker} repeat={repeat}: decision={row.get('fasim_gasal2_flush_two_slot_overlap_decision')}")
        if not material:
            continue
        submitted = as_int(row, "fasim_gasal2_flush_two_slot_overlap_flushes_gpu_submitted")
        finalized = as_int(row, "fasim_gasal2_flush_two_slot_overlap_flushes_finalized")
        committed = as_int(row, "fasim_gasal2_flush_two_slot_overlap_flushes_committed")
        total = as_int(row, "fasim_gasal2_flush_two_slot_overlap_flushes_total")
        if not (submitted == finalized == committed == total):
            fail(f"two_slot workers={worker} repeat={repeat}: lifecycle submitted={submitted} finalized={finalized} committed={committed} total={total}")
        if as_int(row, "fasim_gasal2_flush_two_slot_overlap_slot0_submit_count") <= 0:
            fail(f"two_slot workers={worker} repeat={repeat}: slot0 unused")
        if as_int(row, "fasim_gasal2_flush_two_slot_overlap_slot1_submit_count") <= 0:
            fail(f"two_slot workers={worker} repeat={repeat}: slot1 unused")
        if as_int(row, "fasim_gasal2_flush_two_slot_overlap_max_live_slots") != 2:
            fail(f"two_slot workers={worker} repeat={repeat}: max_live_slots={row.get('fasim_gasal2_flush_two_slot_overlap_max_live_slots')}")
        if as_float(row.get("fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds"), "host overlap") <= 0:
            fail(f"two_slot workers={worker} repeat={repeat}: no host scheduling overlap")
        if row.get("fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported") != "0":
            fail(f"two_slot workers={worker} repeat={repeat}: runtime device-overlap support marker changed")
        if row.get("fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds") != "unavailable":
            fail(f"two_slot workers={worker} repeat={repeat}: gpu_cpu_overlap_seconds={row.get('fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds')}")
        for key in (
            "fasim_gasal2_flush_two_slot_overlap_unsupported_flushes",
            "fasim_gasal2_flush_two_slot_overlap_legacy_fallback_flushes",
            "fasim_gasal2_flush_two_slot_overlap_state_transition_violations",
            "fasim_gasal2_flush_two_slot_overlap_order_violations",
            "fasim_gasal2_flush_two_slot_overlap_allocation_failures",
            "fasim_gasal2_flush_two_slot_overlap_missing_rows",
            "fasim_gasal2_flush_two_slot_overlap_extra_rows",
            "fasim_gasal2_flush_two_slot_overlap_order_mismatches",
            "fasim_gasal2_flush_two_slot_overlap_cigar_mismatches",
            "fasim_gasal2_flush_two_slot_overlap_coordinate_mismatches",
            "fasim_gasal2_flush_two_slot_overlap_counter_mismatches",
            "fasim_gasal2_flush_two_slot_overlap_archive_descriptor_mismatches",
        ):
            if as_int(row, key) != 0:
                fail(f"two_slot workers={worker} repeat={repeat}: {key}={row.get(key)}")

for row in topk:
    worker = row["worker_count"]
    repeat = row["repeat"]
    if row.get("schema_version") != "1":
        fail(f"topk workers={worker} repeat={repeat}: schema_version={row.get('schema_version')}")
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            fail(f"topk workers={worker} repeat={repeat}: {key}={row.get(key)}")

for row in determinism:
    if row.get("schema_version") != "1":
        fail(f"determinism {row.get('mode')} workers={row.get('worker_count')}: schema_version={row.get('schema_version')}")
    for key in ("top5_score_stable", "top5_stability_stable", "top5_nt_score_stable"):
        if row.get(key) != "true":
            fail(f"determinism {row.get('mode')} workers={row.get('worker_count')}: {key}={row.get(key)}")

if summary.get("schema_version") != 1:
    fail(f"summary schema_version={summary.get('schema_version')}")
if summary.get("scope") != "normal-triplex lite":
    fail(f"summary scope={summary.get('scope')}")
if summary.get("default_policy") != "default_off":
    fail(f"summary default_policy={summary.get('default_policy')}")
if summary.get("runtime_device_overlap_supported") is not False:
    fail(f"summary runtime_device_overlap_supported={summary.get('runtime_device_overlap_supported')}")

repeats = int(summary.get("repeats", 0) or 0)
det_by_mode_worker = {
    (row.get("mode"), int(row.get("worker_count", "0") or "0")): row
    for row in determinism
}
if repeats >= 2:
    for worker in worker_counts:
        extracted = det_by_mode_worker.get(("extracted", worker))
        two_slot = det_by_mode_worker.get(("two_slot", worker))
        if not extracted or not two_slot:
            fail(f"workers={worker}: missing determinism rows")
            continue
        for key in (
            "max_pair_set_missing",
            "max_pair_set_extra",
            "max_pair_multiset_missing",
            "max_pair_multiset_extra",
        ):
            if as_int(two_slot, key) > as_int(extracted, key):
                fail(
                    f"workers={worker}: two-slot expanded {key} "
                    f"{two_slot.get(key)} > extracted {extracted.get(key)}"
                )

strong_go = int(summary.get("strong_go_multi_worker_configs", 0))
if strong_go < min_strong and not allow_scoped and not is_smoke:
    fail(f"strong_go_multi_worker_configs={strong_go} below required {min_strong}")

if not is_smoke:
    failed_workers = sorted({int(row["worker_count"]) for row in failed_runs})
    if failed_workers:
        print(
            "multi-worker failed configs recorded: "
            + ",".join(str(value) for value in failed_workers),
            file=sys.stderr,
        )
    for worker in worker_counts:
        if worker <= 1:
            continue
        improvement = as_float(
            summary.get(f"workers_{worker}_two_slot_wall_improvement_fraction_vs_extracted"),
            f"workers_{worker}_improvement",
        )
        if improvement < -0.02:
            fail(f"workers={worker}: regression {improvement:.6f}")
        if improvement < min_improvement and not allow_scoped:
            fail(f"workers={worker}: improvement {improvement:.6f} below {min_improvement:.6f}")

if errors:
    for message in errors:
        print(message, file=sys.stderr)
    raise SystemExit(1)

print("check_fasim_gasal2_flush_two_slot_multi_worker_2gpu_result: ok")
print("worker_counts=" + ",".join(str(v) for v in worker_counts))
print(f"strong_go_multi_worker_configs={strong_go}")
for worker in worker_counts:
    key = f"workers_{worker}_two_slot_wall_improvement_fraction_vs_extracted"
    print(f"workers_{worker}_improvement={summary.get(key, 'unknown')}")
    print(f"workers_{worker}_host_overlap={summary.get(f'workers_{worker}_two_slot_host_scheduling_overlap_seconds_median', 'unknown')}")
PY
