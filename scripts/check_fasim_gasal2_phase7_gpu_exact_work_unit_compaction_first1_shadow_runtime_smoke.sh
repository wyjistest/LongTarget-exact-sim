#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_"


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


def require_int(text: str, suffix: str) -> int:
    observed = value(text, suffix)
    try:
        return int(observed)
    except ValueError as exc:
        raise SystemExit(f"{suffix}: expected integer, observed {observed!r}") from exc


def require_positive_int(text: str, suffix: str) -> int:
    number = require_int(text, suffix)
    if number <= 0:
        raise SystemExit(f"{suffix}: expected > 0, observed {number}")
    return number


def require_nonnegative_int(text: str, suffix: str) -> int:
    number = require_int(text, suffix)
    if number < 0:
        raise SystemExit(f"{suffix}: expected >= 0, observed {number}")
    return number


baseline_output = output_for_dir(baseline_dir)
candidate_output = output_for_dir(candidate_dir)
if digest_for_file(baseline_output) != digest_for_file(candidate_output):
    raise SystemExit("exact work-unit compaction shadow changed lite output digest")
if baseline_output.read_bytes() != candidate_output.read_bytes():
    raise SystemExit("exact work-unit compaction shadow changed lite output bytes")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

for suffix in [
    "requested",
    "active",
    "scoreinfo_key_descriptors",
    "scoreinfo_unique_keys",
    "scoreinfo_duplicate_units",
    "align_key_descriptors",
    "align_unique_keys",
    "align_duplicate_attempts",
    "key_collisions",
    "cpu_key_validation_mismatches",
    "unsupported_key_descriptors",
    "fallback_to_full_cpu_replay",
    "scoreinfo_prealign_reduced",
    "align_side_reduced",
    "full_rows_equal",
    "digest_match",
    "runtime_reduction_enabled",
    "runtime_work_drop_enabled",
    "cpu_align_authority",
    "gpu_score_authority",
    "gpu_endpoint_authority",
    "gpu_cigar_traceback_output_authority",
    "gpu_output_digest_authority",
    "gate_first1_shadow_pass",
    "gate_first1_pass",
]:
    require_eq(base, suffix, "0")

require_eq(candidate, "requested", "1")
require_eq(candidate, "active", "1")
require_positive_int(candidate, "scoreinfo_key_descriptors")
require_positive_int(candidate, "scoreinfo_unique_keys")
require_nonnegative_int(candidate, "scoreinfo_duplicate_units")
require_positive_int(candidate, "align_key_descriptors")
require_positive_int(candidate, "align_unique_keys")
require_nonnegative_int(candidate, "align_duplicate_attempts")
require_eq(candidate, "key_collisions", "0")
require_eq(candidate, "cpu_key_validation_mismatches", "0")
require_eq(candidate, "unsupported_key_descriptors", "0")
require_eq(candidate, "fallback_to_full_cpu_replay", "1")
require_eq(candidate, "scoreinfo_prealign_reduced", "0")
require_eq(candidate, "align_side_reduced", "0")
require_eq(candidate, "full_rows_equal", "1")
require_eq(candidate, "digest_match", "1")
require_eq(candidate, "runtime_reduction_enabled", "0")
require_eq(candidate, "runtime_work_drop_enabled", "0")
require_eq(candidate, "cpu_align_authority", "1")
require_eq(candidate, "gpu_score_authority", "0")
require_eq(candidate, "gpu_endpoint_authority", "0")
require_eq(candidate, "gpu_cigar_traceback_output_authority", "0")
require_eq(candidate, "gpu_output_digest_authority", "0")
require_eq(candidate, "gate_first1_shadow_pass", "1")
require_eq(candidate, "gate_first1_pass", "0")

print("phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_smoke=pass")
print("phase7_gpu_exact_work_unit_compaction_requested=1")
print("phase7_gpu_exact_work_unit_compaction_active=1")
print("phase7_gpu_exact_work_unit_compaction_scoreinfo_key_descriptors_gt_zero=1")
print("phase7_gpu_exact_work_unit_compaction_align_key_descriptors_gt_zero=1")
print("phase7_gpu_exact_work_unit_compaction_runtime_reduction_enabled=0")
print("phase7_gpu_exact_work_unit_compaction_runtime_work_drop_enabled=0")
print("phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
