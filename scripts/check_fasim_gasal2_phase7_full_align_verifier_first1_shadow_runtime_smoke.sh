#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_full_align_verifier_"


def output_for_dir(path: Path) -> Path:
    outputs = sorted(path.glob("*-TFOsorted.lite"))
    if len(outputs) != 1:
        raise SystemExit(f"expected one lite output in {path}, observed {len(outputs)}")
    return outputs[0]


def digest_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def require_same_int(text: str, left: str, right: str) -> None:
    left_value = value(text, left)
    right_value = value(text, right)
    if left_value != right_value:
        raise SystemExit(f"{left} != {right}: observed {left_value} vs {right_value}")


baseline_output = output_for_dir(baseline_dir)
candidate_output = output_for_dir(candidate_dir)
if digest_for_file(baseline_output) != digest_for_file(candidate_output):
    raise SystemExit("full-align verifier shadow changed lite output digest")
if baseline_output.read_bytes() != candidate_output.read_bytes():
    raise SystemExit("full-align verifier shadow changed lite output bytes")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")
require_eq(base, "runtime_reduction_enabled", "0")
require_eq(base, "runtime_work_drop_enabled", "0")
require_eq(base, "gpu_endpoint_cigar_traceback_output_authority", "0")
require_eq(base, "gpu_output_digest_authority", "0")
require_eq(base, "gate_first1_shadow_pass", "0")

require_eq(candidate, "requested", "1")
require_eq(candidate, "active", "1")
descriptors = require_positive_int(candidate, "descriptors")
require_eq(candidate, "proposals", "0")
require_same_int(candidate, "proposal_failures", "descriptors")
require_eq(candidate, "verifier_pass", "0")
require_eq(candidate, "verifier_fail", "0")
require_same_int(candidate, "cpu_align_fallbacks", "descriptors")
require_eq(candidate, "score_mismatches", "0")
require_eq(candidate, "endpoint_mismatches", "0")
require_eq(candidate, "cigar_mismatches", "0")
require_eq(candidate, "full_row_mismatches", "0")
require_eq(candidate, "digest_mismatches", "0")
require_eq(candidate, "full_rows_equal", "0")
require_eq(candidate, "digest_match", "0")
require_eq(candidate, "missing_rows", "0")
require_eq(candidate, "extra_rows", "0")
require_eq(candidate, "triplex_mismatches", "0")
require_eq(candidate, "runtime_reduction_enabled", "0")
require_eq(candidate, "runtime_work_drop_enabled", "0")
require_eq(candidate, "gpu_endpoint_cigar_traceback_output_authority", "0")
require_eq(candidate, "gpu_output_digest_authority", "0")
require_eq(candidate, "cpu_align_authority", "1")
require_eq(candidate, "fallback_to_full_cpu_replay", "1")
require_eq(candidate, "gate_first1_shadow_pass", "0")
if descriptors == 0:
    raise SystemExit("descriptors unexpectedly zero")

print("phase7_full_align_verifier_first1_shadow_runtime_smoke=fail_closed")
print("phase7_full_align_verifier_requested=1")
print("phase7_full_align_verifier_active=1")
print("phase7_full_align_verifier_descriptors_gt_zero=1")
print("phase7_full_align_verifier_proposals=0")
print("phase7_full_align_verifier_runtime_reduction_enabled=0")
print("phase7_full_align_verifier_runtime_work_drop_enabled=0")
print("phase7_full_align_verifier_gate_first1_shadow_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
