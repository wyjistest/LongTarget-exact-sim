#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
prefix = "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_"


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


baseline_outputs = sorted(baseline_dir.glob("*-TFOsorted.lite"))
candidate_outputs = sorted(candidate_dir.glob("*-TFOsorted.lite"))
baseline_digest = digest_for_dir(baseline_dir)
candidate_digest = digest_for_dir(candidate_dir)
external_digest_match = baseline_digest == candidate_digest
external_full_rows_equal = (
    len(baseline_outputs) == 1
    and len(candidate_outputs) == 1
    and baseline_outputs[0].read_bytes() == candidate_outputs[0].read_bytes()
)
if not external_digest_match or not external_full_rows_equal:
    raise SystemExit("post-v5.3 GPU consumer summary changed lite output")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")

require_eq(base, "requested", "0")
require_eq(base, "active", "0")

for suffix in [
    "requested",
    "active",
    "source_is_pre_scoreinfo",
    "gpu_consumer_reduces_before_host_transfer",
    "uses_prefix_boundary_or_equivalent_replay_proof",
    "scoreinfo_prealign_reduced",
    "align_side_reduced",
    "fallback_accounting_clean",
    "cpu_align_authority",
]:
    require_eq(candidate, suffix, "1")

for suffix in [
    "arbitrary_sparse_subset",
    "first_descriptor_per_scoreinfo",
    "descriptor_false_negatives",
    "missing_required_attempts",
    "triplex_mismatches",
    "gpu_endpoint_cigar_traceback_output_authority",
]:
    require_eq(candidate, suffix, "0")

gpu_summary_rows = require_positive_int(candidate, "gpu_consumer_summary_rows")
gpu_selected_attempts = require_positive_int(candidate, "gpu_selected_attempts")
selected_prefix_attempts = require_positive_int(candidate, "selected_prefix_attempts")
candidate_attempts = require_positive_int(candidate, "candidate_align_attempts")
reference_attempts = require_positive_int(candidate, "reference_align_attempts")
v5_candidate_attempts = require_positive_int(candidate, "v5_candidate_align_attempts")

if gpu_selected_attempts >= v5_candidate_attempts:
    raise SystemExit(
        "post-v5.3 consumer must select fewer attempts than v5 "
        f"({gpu_selected_attempts} >= {v5_candidate_attempts})"
    )
if selected_prefix_attempts >= v5_candidate_attempts:
    raise SystemExit(
        "post-v5.3 consumer must select a prefix smaller than v5 "
        f"({selected_prefix_attempts} >= {v5_candidate_attempts})"
    )
if candidate_attempts >= reference_attempts:
    raise SystemExit(
        "post-v5.3 candidate must reduce Align attempts "
        f"({candidate_attempts} >= {reference_attempts})"
    )

print("phase7_post_v5_3_gpu_consumer_summary_runtime_smoke=first1_pass")
print("phase7_post_v5_3_gpu_consumer_summary_requested=1")
print("phase7_post_v5_3_gpu_consumer_summary_active=1")
print(f"phase7_post_v5_3_gpu_consumer_summary_rows={gpu_summary_rows}")
print(f"phase7_post_v5_3_gpu_selected_attempts={gpu_selected_attempts}")
print(f"phase7_post_v5_3_selected_prefix_attempts={selected_prefix_attempts}")
print(f"phase7_post_v5_3_candidate_align_attempts={candidate_attempts}")
print(f"phase7_post_v5_3_reference_align_attempts={reference_attempts}")
print(f"phase7_post_v5_3_v5_candidate_align_attempts={v5_candidate_attempts}")
print("phase7_post_v5_3_external_digest_match=1")
print("phase7_post_v5_3_external_full_rows_equal=1")
print("phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass=1")
print("ok")
PY
