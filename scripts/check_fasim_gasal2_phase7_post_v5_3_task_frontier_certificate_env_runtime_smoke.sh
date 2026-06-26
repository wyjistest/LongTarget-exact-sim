#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_env_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_"


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


if digest_for_dir(baseline_dir) != digest_for_dir(candidate_dir):
    raise SystemExit("task-frontier certificate env scaffold changed lite output digest")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")
require_eq(base, "gate_first1_pass", "0")

require_eq(candidate, "requested", "1")
require_eq(candidate, "active", "0")
require_eq(candidate, "source_is_pre_scoreinfo", "0")
require_eq(candidate, "source_is_legacy_byte_cuda", "0")
require_eq(candidate, "gasal2_score_only_long_query_dependency", "0")
require_eq(candidate, "uses_task_frontier_certificate", "0")
require_eq(candidate, "uses_prefix_boundary_only", "0")
require_eq(candidate, "arbitrary_sparse_subset", "0")
require_eq(candidate, "first_descriptor_per_scoreinfo", "0")
require_eq(candidate, "fixed_prefix_per_scoreinfo", "0")
require_eq(candidate, "task_frontier_certificate_rows", "0")
require_eq(candidate, "gpu_selected_attempts", "0")
require_eq(candidate, "candidate_align_attempts", "0")
require_eq(candidate, "v5_candidate_align_attempts", "0")
require_eq(candidate, "fallback_accounting_clean", "0")
require_eq(candidate, "cpu_align_authority", "1")
require_eq(candidate, "gpu_endpoint_cigar_traceback_output_authority", "0")
require_eq(candidate, "digest_match", "0")
require_eq(candidate, "full_rows_equal", "0")
require_eq(candidate, "gate_first1_pass", "0")

print("phase7_post_v5_3_task_frontier_certificate_env_runtime_smoke=fail_closed_no_source")
print("phase7_post_v5_3_task_frontier_certificate_requested=1")
print("phase7_post_v5_3_task_frontier_certificate_active=0")
print("phase7_post_v5_3_task_frontier_certificate_gate_first1_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
