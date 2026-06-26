#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_"


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


baseline_output = output_for_dir(baseline_dir)
candidate_output = output_for_dir(candidate_dir)
external_digest_match = digest_for_file(baseline_output) == digest_for_file(candidate_output)
external_full_rows_equal = baseline_output.read_bytes() == candidate_output.read_bytes()
if not external_digest_match or not external_full_rows_equal:
    raise SystemExit("pre-D2H proof-search export changed lite output")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")
require_eq(base, "runtime_reduction_enabled", "0")

for suffix in [
    "requested",
    "active",
    "source_is_pre_scoreinfo",
    "source_is_legacy_byte_cuda",
    "cpu_align_authority",
    "label_source_cpu_authority_external_output",
    "gate_first1_export_pass",
]:
    require_eq(candidate, suffix, "1")

for suffix in [
    "gpu_endpoint_cigar_traceback_output_authority",
    "gpu_output_authority",
    "runtime_reduction_enabled",
]:
    require_eq(candidate, suffix, "0")

proof_search_rows = require_positive_int(candidate, "proof_search_rows")
task_count = require_positive_int(candidate, "task_count")
scoreinfo_count = require_positive_int(candidate, "scoreinfo_count")
attempt_count = require_positive_int(candidate, "attempt_count")

print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_runtime_smoke=first1_export_pass")
print("phase7_post_v5_3_pre_d2h_proof_search_requested=1")
print("phase7_post_v5_3_pre_d2h_proof_search_active=1")
print(f"phase7_post_v5_3_pre_d2h_proof_search_rows={proof_search_rows}")
print(f"phase7_post_v5_3_pre_d2h_proof_search_task_count={task_count}")
print(f"phase7_post_v5_3_pre_d2h_proof_search_scoreinfo_count={scoreinfo_count}")
print(f"phase7_post_v5_3_pre_d2h_proof_search_attempt_count={attempt_count}")
print("phase7_post_v5_3_pre_d2h_proof_search_external_digest_match=1")
print("phase7_post_v5_3_pre_d2h_proof_search_external_full_rows_equal=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
