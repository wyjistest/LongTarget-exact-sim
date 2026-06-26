#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_runtime_smoke"}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

awk '
  /^>/ { ++records }
  records <= 1 { print }
' "$DNA_INPUT" >"$WORK/inputs/neat1_first1.fa"

run_case() {
  local out_dir="$1"
  shift
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$WORK/inputs/neat1_first1.fa" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_"


def digest_for_dir(path: Path) -> str:
    outputs = sorted(path.glob("*-TFOsorted.lite"))
    if not outputs:
        raise SystemExit(f"missing lite output in {path}")
    return hashlib.sha256(outputs[0].read_bytes()).hexdigest()


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


def require_eq(text: str, suffix: str, expected: str) -> None:
    observed = value(text, suffix)
    if observed != expected:
        raise SystemExit(f"{suffix}: expected {expected}, observed {observed}")


def require_positive_int(text: str, suffix: str) -> int:
    observed = value(text, suffix)
    try:
        number = int(observed)
    except ValueError as exc:
        raise SystemExit(f"{suffix}: expected integer, observed {observed!r}") from exc
    if number <= 0:
        raise SystemExit(f"{suffix}: expected > 0, observed {number}")
    return number


baseline_digest = digest_for_dir(baseline_dir)
candidate_digest = digest_for_dir(candidate_dir)
if baseline_digest == candidate_digest:
    raise SystemExit("host-assisted consumer feasibility unexpectedly matched lite output digest")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")

for suffix in [
    "requested",
    "host_assisted",
    "source_is_v5_descriptors",
    "cpu_align_authority",
]:
    require_eq(candidate, suffix, "1")

for suffix in [
    "active",
    "gpu_consumer_reduces_before_host_transfer",
    "host_selected_attempts",
    "prefix_descriptor_attempts",
    "candidate_align_attempts",
    "candidate_align_attempts_less_than_v5",
    "descriptor_false_negatives",
    "missing_required_attempts",
    "fallback_accounting_clean",
    "digest_match",
    "full_rows_equal",
    "extra_rows",
    "triplex_mismatches",
    "gpu_endpoint_cigar_traceback_output_authority",
    "gate_first1_pass",
]:
    require_eq(candidate, suffix, "0")

reference_attempts = require_positive_int(candidate, "reference_align_attempts")
v5_candidate_attempts = require_positive_int(candidate, "v5_candidate_align_attempts")
missing_rows = require_positive_int(candidate, "missing_rows")

length_guard_prefix = "benchmark.fasim_gasal2_length_guard_"
if f"{length_guard_prefix}fallbacks=1" not in candidate:
    raise SystemExit("expected GASAL2 length guard fallback for long NEAT1 query")
if f"{length_guard_prefix}last_query_len=22767" not in candidate:
    raise SystemExit("expected NEAT1 query length guard evidence")
if f"{length_guard_prefix}max_query_len=2812" not in candidate:
    raise SystemExit("expected GASAL2 max query length guard evidence")

print("phase7_post_v5_3_host_assisted_consumer_feasibility_runtime_smoke=no_go_long_query_length_guard")
print("phase7_post_v5_3_host_assisted_consumer_feasibility_requested=1")
print("phase7_post_v5_3_host_assisted_consumer_feasibility_active=0")
print("phase7_post_v5_3_host_assisted_host_selected_attempts=0")
print("phase7_post_v5_3_host_assisted_prefix_descriptor_attempts=0")
print("phase7_post_v5_3_host_assisted_candidate_align_attempts=0")
print(f"phase7_post_v5_3_host_assisted_reference_align_attempts={reference_attempts}")
print(f"phase7_post_v5_3_host_assisted_v5_candidate_align_attempts={v5_candidate_attempts}")
print(f"phase7_post_v5_3_host_assisted_missing_rows={missing_rows}")
print("phase7_post_v5_3_host_assisted_consumer_feasibility_not_strict_phase5=1")
print("phase7_post_v5_3_host_assisted_consumer_feasibility_gate_first1_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
