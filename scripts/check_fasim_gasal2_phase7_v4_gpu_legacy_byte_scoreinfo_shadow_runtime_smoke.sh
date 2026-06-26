#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v4_gpu_legacy_byte_scoreinfo_shadow_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SHADOW=1

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


if digest_for_dir(baseline_dir) != digest_for_dir(candidate_dir):
    raise SystemExit("v4 GPU legacy-byte scoreInfo shadow changed lite output digest")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_v4_legacy_byte_scoreinfo_shadow_"


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("v4 GPU legacy-byte scoreInfo shadow must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v4 GPU legacy-byte scoreInfo shadow was not requested")
if value(candidate, "active") != "1":
    raise SystemExit("v4 GPU legacy-byte scoreInfo shadow did not run")

tasks = int(value(candidate, "tasks"))
cpu_rows = int(value(candidate, "cpu_scoreinfo_rows"))
host_rows = int(value(candidate, "host_scoreinfo_rows"))
gpu_rows = int(value(candidate, "gpu_scoreinfo_rows"))
if tasks <= 0:
    raise SystemExit("v4 GPU shadow must see at least one task")
if cpu_rows <= 0 or host_rows <= 0 or gpu_rows <= 0:
    raise SystemExit("v4 GPU shadow must compare non-empty CPU, host, and GPU scoreInfo rows")

for suffix in [
    "scoreinfo_rows_equal",
    "scoreinfo_order_equal",
    "scoreinfo_attempt_windows_equal",
    "host_contract_pass",
    "gate_v4_1_pass",
]:
    if value(candidate, suffix) != "1":
        raise SystemExit(f"expected {suffix}=1")

for suffix in [
    "scoreinfo_mismatches",
    "scoreinfo_false_negatives",
    "scoreinfo_extra_required_attempts",
    "gpu_endpoint_cigar_traceback_output_authority",
]:
    if value(candidate, suffix) != "0":
        raise SystemExit(f"expected {suffix}=0")

source = value(candidate, "source")
if source != "gpu_legacy_byte_scoreinfo":
    raise SystemExit(f"unexpected v4 GPU source: {source}")

print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_runtime_smoke=gpu_contract_clean")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_active=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_host_contract_pass=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows_gt_zero=1")
print("phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gate_v4_1_pass=1")
print("phase7_broad_restart_v4_broad_gate_pass=0")
print("ok")
PY
