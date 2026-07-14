#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_certificate_phase6"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
DOC="$ROOT/docs/fasim_gasal2_traceback_certificate_long_query.md"
TIMING="$ROOT/docs/fasim_gasal2_traceback_long_query_timing.tsv"
MATRIX="$ROOT/docs/fasim_gasal2_traceback_certificate_long_query.tsv"
GOAL="$ROOT/goal.md"

for path in "$DOC" "$TIMING" "$MATRIX" "$GOAL"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 6 result dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_analyze_fasim_gasal2_traceback_long_query.py" \
  >"$WORK/analyzer_tests.log" 2>&1
python3 "$ROOT/tests/check_summarize_fasim_gasal2_traceback_certificate.py" \
  >"$WORK/summarizer_tests.log" 2>&1
WORK="$WORK/certificate_unit_work" \
  bash "$ROOT/scripts/check_fasim_gasal2_traceback_certificate_unit.sh" \
  >"$WORK/certificate_unit.log" 2>&1

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN" \
  >"$WORK/build.log" 2>&1
BUILD_BIN=0 BIN="$BIN" WORK="$WORK/shadow_smoke" \
  bash "$ROOT/scripts/check_fasim_gasal2_traceback_certificate_shadow_smoke.sh" \
  >"$WORK/shadow_smoke.log" 2>&1

for log in \
  analyzer_tests.log \
  summarizer_tests.log \
  certificate_unit.log \
  build.log \
  shadow_smoke.log; do
  if [[ ! -s "$WORK/$log" ]]; then
    echo "missing Phase 6 audit log: $WORK/$log" >&2
    exit 1
  fi
done

python3 - "$TIMING" "$MATRIX" "$DOC" "$GOAL" \
  "$ROOT/fasim/gasal2_align_bridge.cpp" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


timing_path = Path(sys.argv[1])
matrix_path = Path(sys.argv[2])
doc = Path(sys.argv[3]).read_text(encoding="utf-8")
goal = Path(sys.argv[4]).read_text(encoding="utf-8")
bridge = Path(sys.argv[5]).read_text(encoding="utf-8")

with timing_path.open(newline="", encoding="utf-8") as handle:
    timing_rows = list(csv.DictReader(handle, delimiter="\t"))
if len(timing_rows) != 1:
    raise SystemExit(f"expected one timing row, found {len(timing_rows)}")
timing = timing_rows[0]
if timing["runs"] != "121" or timing["grid_shifts"] != "0,256":
    raise SystemExit(f"unexpected full-query timing scope: {timing}")
if timing["traceback_requests"] != "918240875":
    raise SystemExit("full-query traceback request count drifted")
if timing["timing_closure"] != "clean":
    raise SystemExit("traceback timing closure is not clean")
if timing["device_timing_supported"] != "0":
    raise SystemExit("runtime must not claim device traceback timing support")
for name in ("traceback_h2d_seconds", "traceback_kernel_seconds", "traceback_d2h_seconds"):
    if timing[name] != "unavailable":
        raise SystemExit(f"{name} must remain unavailable")


def number(row: dict[str, str], name: str) -> float:
    value = float(row[name])
    if not math.isfinite(value) or value < 0:
        raise SystemExit(f"invalid {name}={row[name]!r}")
    return value


wait = number(timing, "traceback_host_wait_seconds")
poll = number(timing, "traceback_host_poll_wait_seconds")
copy = number(timing, "traceback_result_copy_seconds")
if not math.isclose(wait, poll + copy, rel_tol=1e-6, abs_tol=1e-5):
    raise SystemExit("traceback wait components do not close")
host_stage = (
    number(timing, "traceback_pack_seconds")
    + number(timing, "traceback_submit_seconds")
    + wait
    + number(timing, "traceback_convert_seconds")
)
if not math.isclose(
    host_stage,
    number(timing, "traceback_host_observed_stage_seconds"),
    rel_tol=1e-8,
    abs_tol=1e-5,
):
    raise SystemExit("host-observed traceback stage does not close")
if number(timing, "traceback_cigar_materialize_seconds") > copy:
    raise SystemExit("CIGAR materialization must be nested inside result copy")
if number(timing, "traceback_filter_dedup_cluster_seconds") > number(
    timing, "traceback_convert_seconds"
):
    raise SystemExit("filter/sort must be nested inside convert")
if timing["fallbacks"] != "0" or timing["length_guard_fallbacks"] != "0":
    raise SystemExit("full-query timing fallback accounting is not clean")

with matrix_path.open(newline="", encoding="utf-8") as handle:
    matrix = list(csv.DictReader(handle, delimiter="\t"))
required_workloads = {
    "h19_chr22_2mb",
    "kcnq1ot1_fragment_chr22_2mb",
    "h19_chr21_chr22_full",
    "kcnq1ot1_max4_chr22_full",
    "kcnq1ot1_max8_chr22_full",
}
by_name = {row["workload"]: row for row in matrix}
if set(by_name) != required_workloads:
    raise SystemExit(f"unexpected certificate workload set: {sorted(by_name)}")
for name, row in by_name.items():
    if row["status"] != "complete":
        raise SystemExit(f"{name}: incomplete result")
    if row["decision"] != "no_go_below_request_reduction_gate":
        raise SystemExit(f"{name}: unexpected decision={row['decision']}")
    considered = int(row["candidates_considered"])
    certified = int(row["certified_skips"])
    uncertified = int(row["uncertified_candidates"])
    reasons = sum(
        int(row[key])
        for key in (
            "exact_descriptor_duplicate_skips",
            "static_span_skips",
            "score_endpoint_span_skips",
        )
    )
    if considered <= 0 or certified + uncertified != considered:
        raise SystemExit(f"{name}: candidate accounting does not close")
    if reasons != certified:
        raise SystemExit(f"{name}: reason accounting does not close")
    if int(row["authority_traceback_requests"]) != considered:
        raise SystemExit(f"{name}: authority requests do not match considered")
    fraction = float(row["certified_fraction"])
    if not (0.0 <= fraction < 0.20):
        raise SystemExit(f"{name}: fraction does not support Phase 6 no-go: {fraction}")
    for key in (
        "shadow_false_rejects",
        "exact_descriptor_duplicate_skips",
        "static_span_skips",
        "score_frontier_skips",
        "stability_frontier_skips",
        "nt_frontier_skips",
        "tie_rescues",
        "rank_aware_supported",
        "real_skip_enabled",
        "certificate_fallbacks",
        "authority_fallbacks",
        "length_guard_fallbacks",
    ):
        if int(row[key]) != 0:
            raise SystemExit(f"{name}: expected {key}=0, got {row[key]}")
    if row["pre_drop_proof_available"] != "1":
        raise SystemExit(f"{name}: missing pre-drop proof")
    if row["proof_version"] != "phase6_exact_v1":
        raise SystemExit(f"{name}: unexpected proof version")

if by_name["kcnq1ot1_max8_chr22_full"]["certified_skips"] != "64990":
    raise SystemExit("max8 certified count drifted")
if float(by_name["kcnq1ot1_max8_chr22_full"]["certified_fraction"]) >= 0.001:
    raise SystemExit("max8 certificate unexpectedly reached 0.1%")
if by_name["h19_chr22_2mb"]["output_contract"] != "byte_equal":
    raise SystemExit("H19 smoke must retain byte-equal contract")
if by_name["kcnq1ot1_fragment_chr22_2mb"]["output_contract"] != "byte_equal":
    raise SystemExit("non-H19 smoke must retain byte-equal contract")

required_doc_phrases = (
    "Phase 6 is an evidence-complete `no_go`",
    "real_skip_enabled=0",
    "traceback_h2d_seconds",
    "0.0508%",
    "score_certificate_supported=true",
    "stability_certificate_supported=false",
    "nt_score_certificate_supported=false",
    "not unsegmented full-length equivalence",
)
for phrase in required_doc_phrases:
    if phrase not in doc:
        raise SystemExit(f"result doc missing required phrase: {phrase}")
for forbidden in (
    "FASIM_GASAL2_TRACEBACK_CERTIFICATE_REAL_SKIP",
    "fixed traceback score threshold is safe",
    "full KCNQ1OT1 equivalence validated",
):
    if forbidden in doc or forbidden in bridge:
        raise SystemExit(f"Phase 6 contains forbidden claim/path: {forbidden}")

state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if (
    (state.get("active_phase") != "complete" and int(state.get("active_phase", "0")) < 7)
    or state.get("phase_6_status") != "no_go"
    or int(state.get("last_completed_phase", "0")) < 6
):
    raise SystemExit(f"Phase 6 goal state is inconsistent: {state}")

print("ok")
PY

echo "GASAL2 traceback certificate Phase 6 OK"
