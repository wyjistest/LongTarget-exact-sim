#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_multi_segment_context_phase3"}"
PROFILE_ROOT="${PROFILE_ROOT:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full/grids/shift_0"}"
DOC="$ROOT/docs/fasim_gasal2_multi_segment_target_reuse.md"
RECEIPT="$ROOT/docs/fasim_gasal2_multi_segment_setup_profile.tsv"
GOAL="$ROOT/goal.md"

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_analyze_fasim_gasal2_multi_segment_setup.py" \
  >"$WORK/analyzer_tests.log" 2>&1

local_profile_available=0
local_profile_consistent=0
if compgen -G "$PROFILE_ROOT/run_*/stderr.log" >/dev/null; then
  local_profile_available=1
  python3 "$ROOT/scripts/analyze_fasim_gasal2_multi_segment_setup.py" \
    --run-root "$PROFILE_ROOT" \
    --details "$WORK/local_profile.tsv" \
    --summary "$WORK/local_profile.txt"
  if cmp -s "$RECEIPT" "$WORK/local_profile.tsv"; then
    local_profile_consistent=1
  fi
fi

python3 - "$ROOT" "$DOC" "$RECEIPT" "$GOAL" "$local_profile_available" "$local_profile_consistent" <<'PY' \
  >"$WORK/summary.txt"
from __future__ import annotations

import csv
import sys
from pathlib import Path


root = Path(sys.argv[1])
doc_path = Path(sys.argv[2])
receipt_path = Path(sys.argv[3])
goal_path = Path(sys.argv[4])
local_available = int(sys.argv[5])
local_consistent = int(sys.argv[6])

source = (root / "fasim/Fasim-LongTarget.cpp").read_text(encoding="utf-8")
bridge = (root / "fasim/gasal2_align_bridge.cpp").read_text(encoding="utf-8")
doc = doc_path.read_text(encoding="utf-8")
goal = goal_path.read_text(encoding="utf-8")
makefile = (root / "Makefile").read_text(encoding="utf-8")

with receipt_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 4:
    raise SystemExit(f"expected four tracked profile rows, found {len(rows)}")

def total(name: str) -> float:
    return sum(float(row[name]) for row in rows)

def total_int(name: str) -> int:
    return sum(int(row[name]) for row in rows)

wall = total("wall_seconds")
flush = total("flush_total_seconds")
host_setup = sum(
    total(name)
    for name in (
        "fasta_read_seconds",
        "cut_sequence_seconds",
        "transfer_string_seconds",
        "src_transform_seconds",
        "encode_seconds",
        "cuda_query_init_seconds",
    )
)
target_bytes = total_int("score_target_bytes") + total_int("traceback_target_bytes")
score_requests = [int(row["score_requests"]) for row in rows]
traceback_requests = [int(row["traceback_requests"]) for row in rows]

expected = {
    "wall": (wall, 334.641191),
    "flush": (flush, 312.530900),
    "host_setup": (host_setup, 17.684555),
}
for name, (actual, wanted) in expected.items():
    if abs(actual - wanted) > 1e-6:
        raise SystemExit(f"tracked Phase 3 {name} mismatch: {actual} != {wanted}")
if target_bytes != 4_987_491_329:
    raise SystemExit(f"tracked target-byte mismatch: {target_bytes}")
if len(set(score_requests)) <= 1 or len(set(traceback_requests)) <= 1:
    raise SystemExit("tracked target request sets are not query dependent")
if total_int("fallbacks") != 0:
    raise SystemExit("tracked Phase 3 profile has fallbacks")

source_audit = int(
    source.count("lncSeq = readRna(paraList.file2path, lncName);") == 1
    and "tmpRNA = tmpRNA + tmpStr;" in source
    and "while (getline(rnaFile, tmpStr))" in source
)
bridge_state_reusable = int(
    "BridgeState g_score_state;" in bridge
    and "BridgeState g_traceback_state;" in bridge
    and "paddedQuery <= state->max_query_len" in bridge
    and "paddedTarget <= state->max_target_len" in bridge
)
target_repacked = int(bridge.count("gasal_host_batch_fill(storage,") >= 4 and bridge.count("TARGET);") >= 2)
no_runtime_scaffold = int(
    "FASIM_GASAL2_MULTI_SEGMENT_CONTEXT" not in source
    and "FASIM_GASAL2_MULTI_SEGMENT_BATCH" not in source
)

required_doc = [
    "Phase 3 is an evidence-complete `no_go`",
    "Phase 4 is",
    "dependency `no_go`",
    "nonflush_wall_percent=6.61",
    "host_setup_observed_percent=5.28",
    "gasal2_target_batch_bytes=4987491329",
    "target_h2d_copy_count=unavailable",
    "target_batches_query_dependent=1",
    "next_active_phase=5",
]
doc_consistent = int(all(phrase in doc for phrase in required_doc))

state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
goal_consistent = int(
    (state.get("active_phase") == "complete" or int(state.get("active_phase", "0")) >= 5)
    and state.get("phase_3_status") == "no_go"
    and state.get("phase_4_status") == "no_go"
    and int(state.get("last_completed_phase", "0")) >= 3
)
make_target_present = int("check-fasim-gasal2-multi-segment-context-phase3:" in makefile)
local_gate = int(not local_available or local_consistent)
phase3_gate = "no_go" if all(
    (
        source_audit,
        bridge_state_reusable,
        target_repacked,
        no_runtime_scaffold,
        doc_consistent,
        goal_consistent,
        make_target_present,
        local_gate,
    )
) else "fail"

print("segments=4")
print("processes=4")
print("target_read_passes=4")
print(f"wall_seconds={wall:.6f}")
print(f"flush_total_seconds={flush:.6f}")
print(f"nonflush_wall_seconds={wall - flush:.6f}")
print(f"host_setup_observed_seconds={host_setup:.6f}")
print(f"gasal2_target_batch_bytes={target_bytes}")
print("target_batches_query_dependent=1")
print("target_h2d_copy_count=unavailable")
print("device_alloc_count=unavailable")
print("device_alloc_bytes=unavailable")
print("workspace_initializations=unavailable")
print(f"source_single_query_audit={source_audit}")
print(f"bridge_state_capacity_reuse_present={bridge_state_reusable}")
print(f"target_batch_repack_present={target_repacked}")
print(f"runtime_scaffold_absent={no_runtime_scaffold}")
print(f"local_profile_available={local_available}")
print(f"local_profile_consistent={local_consistent}")
print(f"doc_consistent={doc_consistent}")
print(f"goal_consistent={goal_consistent}")
print(f"make_target_present={make_target_present}")
print("phase4_status=no_go")
print(f"phase3_gate={phase3_gate}")
if phase3_gate != "no_go":
    raise SystemExit("Phase 3 persistent target/context evidence gate failed")
PY

cat "$WORK/summary.txt"
echo "Fasim GASAL2 multi-segment context Phase 3 evidence complete: no_go"
