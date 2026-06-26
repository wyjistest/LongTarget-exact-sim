#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_env_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE=1

python3 - "$WORK/baseline/stderr.log" "$WORK/candidate/stderr.log" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_"


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("v5 true pre-scoreInfo source must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v5 true pre-scoreInfo source request was not observed")
if value(candidate, "active") != "0":
    raise SystemExit("env scaffold must fail closed until a true source exists")
if value(candidate, "source_is_pre_scoreinfo") != "0":
    raise SystemExit("env scaffold must not claim a pre-scoreInfo source")
if value(candidate, "scoreinfo_prealign_reduced") != "0":
    raise SystemExit("env scaffold must not claim scoreInfo/preAlign reduction")
if int(value(candidate, "gpu_descriptor_attempts")) != 0:
    raise SystemExit("env scaffold must not emit descriptor attempts")
if value(candidate, "cpu_align_authority") != "1":
    raise SystemExit("env scaffold must preserve CPU Align authority")
if value(candidate, "gpu_endpoint_cigar_traceback_output_authority") != "0":
    raise SystemExit("env scaffold must not grant GPU output authority")
if value(candidate, "gate_v5_1_pass") != "0":
    raise SystemExit("env scaffold must not pass Gate v5.1")

print("phase7_v5_true_pre_scoreinfo_descriptor_source_env_runtime_smoke=fail_closed_no_source")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_requested=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_active=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass=0")
print("ok")
PY
