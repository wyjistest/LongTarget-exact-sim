#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = (
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_"
    "real_source_first1_shadow_"
)


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


baseline_output = output_for_dir(baseline_dir)
candidate_output = output_for_dir(candidate_dir)
if digest_for_file(baseline_output) != digest_for_file(candidate_output):
    raise SystemExit("real-source first1 shadow scaffold changed lite output digest")
if baseline_output.read_bytes() != candidate_output.read_bytes():
    raise SystemExit("real-source first1 shadow scaffold changed lite output bytes")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")
require_eq(base, "gate_first1_pass", "0")

require_eq(candidate, "requested", "1")
require_eq(candidate, "active", "0")
require_eq(candidate, "real_fasim_runtime_certificate_source", "0")
require_eq(candidate, "real_fasim_runtime_work_drop_path", "0")
require_eq(candidate, "runtime_certificate_is_synthetic", "0")
require_eq(candidate, "gpu_tasks", "0")
require_eq(candidate, "gpu_candidate_groups", "0")
require_eq(candidate, "gpu_replay_attempts", "0")
require_eq(candidate, "gpu_selected_attempts", "0")
require_eq(candidate, "gpu_skipped_groups", "0")
require_eq(candidate, "gpu_skipped_attempts", "0")
require_eq(candidate, "cpu_replay_attempts", "0")
require_eq(candidate, "baseline_cpu_attempts", "0")
require_eq(candidate, "missing_certificate", "1")
require_eq(candidate, "fallback_to_full_cpu_replay", "1")
require_eq(candidate, "scoreinfo_prealign_reduced", "0")
require_eq(candidate, "align_side_reduced", "0")
require_eq(candidate, "fallback_accounting_clean", "0")
require_eq(candidate, "certificate_false_negatives", "0")
require_eq(candidate, "missing_required_attempts", "0")
require_eq(candidate, "cpu_align_authority", "1")
require_eq(candidate, "gpu_endpoint_cigar_traceback_output_authority", "0")
require_eq(candidate, "full_rows_equal", "0")
require_eq(candidate, "digest_match", "0")
require_eq(candidate, "missing_rows", "0")
require_eq(candidate, "extra_rows", "0")
require_eq(candidate, "triplex_mismatches", "0")
require_eq(candidate, "candidate_wall_seconds", "0")
require_eq(candidate, "baseline_wall_seconds", "0")
require_eq(candidate, "gate_first1_pass", "0")

print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_smoke=fail_closed_no_real_source")
print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested=1")
print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active=0")
print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
