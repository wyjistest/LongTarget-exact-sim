#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY=1

python3 - "$WORK/baseline" "$WORK/candidate" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

baseline_dir = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])


def digest_for_dir(path: Path) -> str:
    outputs = sorted(path.glob("*-TFOsorted.lite"))
    if not outputs:
        raise SystemExit(f"missing lite output in {path}")
    return hashlib.sha256(outputs[0].read_bytes()).hexdigest()


baseline_digest = digest_for_dir(baseline_dir)
candidate_digest = digest_for_dir(candidate_dir)
if baseline_digest != candidate_digest:
    raise SystemExit("v4 GPU legacy-byte scoreInfo source replay changed lite output digest")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
v4_prefix = "benchmark.fasim_gasal2_phase7_v4_legacy_byte_scoreinfo_shadow_"
stream_prefix = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_"


def value(text: str, prefix: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base, v4_prefix, "source_replay_requested") != "0":
    raise SystemExit("v4 source replay must be default-off")
if value(base, v4_prefix, "source_replay_active") != "0":
    raise SystemExit("v4 source replay must not run by default")

if value(candidate, v4_prefix, "requested") != "1":
    raise SystemExit("v4 GPU legacy-byte source replay did not request v4 scoreInfo shadow")
if value(candidate, v4_prefix, "active") != "1":
    raise SystemExit("v4 GPU legacy-byte source replay did not run v4 scoreInfo shadow")
if value(candidate, v4_prefix, "source") != "gpu_legacy_byte_scoreinfo_source_replay":
    raise SystemExit("v4 source replay must report the GPU legacy-byte source")

for suffix in [
    "scoreinfo_rows_equal",
    "scoreinfo_order_equal",
    "scoreinfo_attempt_windows_equal",
    "host_contract_pass",
    "gate_v4_1_pass",
    "source_replay_requested",
    "source_replay_active",
    "source_replay_streaming_ready",
    "source_replay_cpu_authority",
]:
    if value(candidate, v4_prefix, suffix) != "1":
        raise SystemExit(f"expected {suffix}=1")

for suffix in [
    "scoreinfo_mismatches",
    "scoreinfo_false_negatives",
    "scoreinfo_extra_required_attempts",
    "gpu_endpoint_cigar_traceback_output_authority",
    "source_replay_gpu_endpoint_cigar_traceback_output_authority",
]:
    if value(candidate, v4_prefix, suffix) != "0":
        raise SystemExit(f"expected {suffix}=0")

tasks = int(value(candidate, v4_prefix, "tasks"))
gpu_rows = int(value(candidate, v4_prefix, "gpu_scoreinfo_rows"))
source_rows = int(value(candidate, v4_prefix, "source_replay_scoreinfo_rows"))
if tasks <= 0:
    raise SystemExit("v4 source replay must see at least one task")
if gpu_rows <= 0 or source_rows <= 0:
    raise SystemExit("v4 source replay must use non-empty GPU scoreInfo rows")
if source_rows != gpu_rows:
    raise SystemExit("v4 source replay scoreInfo rows must match GPU rows")

realpath_requested = int(value(candidate, stream_prefix, "realpath_requested"))
realpath_extend_align_attempts = int(value(candidate, stream_prefix, "realpath_extend_align_attempts"))
reference_align_attempts = 2872
if realpath_requested != 1:
    raise SystemExit("v4 source replay must request CPU-authority realpath replay")
if realpath_extend_align_attempts <= 0:
    raise SystemExit("v4 source replay must execute CPU Align attempts through replay")
if realpath_extend_align_attempts >= reference_align_attempts:
    raise SystemExit(
        "v4 source replay first1 must reduce CPU Align attempts "
        f"({realpath_extend_align_attempts} >= {reference_align_attempts})"
    )

if value(candidate, v4_prefix, "gate_v4_2_pass") != "1":
    raise SystemExit("v4 source replay first1 must pass Gate v4.2")

print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke=cpu_authority_replay_first1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_active=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gpu_scoreinfo_rows_gt_zero=1")
print(f"phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts={realpath_extend_align_attempts}")
print(f"phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts={reference_align_attempts}")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction=864")
print("phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gate_v4_2_pass=1")
print("phase7_broad_restart_v4_broad_gate_pass=0")
print("ok")
PY
