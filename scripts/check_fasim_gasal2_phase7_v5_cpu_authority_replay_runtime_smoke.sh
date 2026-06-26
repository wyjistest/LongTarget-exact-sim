#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v5_cpu_authority_replay_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY=1

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


def value(text: str, prefix: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


baseline_digest = digest_for_dir(baseline_dir)
candidate_digest = digest_for_dir(candidate_dir)
if baseline_digest != candidate_digest:
    raise SystemExit("v5 CPU-authority replay changed lite output digest")

base = (baseline_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
candidate = (candidate_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_"

if value(base, prefix, "requested") != "0":
    raise SystemExit("v5 CPU-authority replay must be default-off")
if value(base, prefix, "active") != "0":
    raise SystemExit("v5 CPU-authority replay must not run by default")

required_ones = [
    "requested",
    "active",
    "source_is_pre_scoreinfo",
    "scoreinfo_prealign_reduced",
    "cpu_align_authority",
    "full_rows_equal",
    "digest_match",
    "gate_v5_2_pass",
]
for suffix in required_ones:
    if value(candidate, prefix, suffix) != "1":
        raise SystemExit(f"expected {suffix}=1")

required_zeros = [
    "gpu_endpoint_cigar_traceback_output_authority",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "descriptor_false_negatives",
    "missing_required_attempts",
]
for suffix in required_zeros:
    if value(candidate, prefix, suffix) != "0":
        raise SystemExit(f"expected {suffix}=0")

candidate_attempts = int(value(candidate, prefix, "candidate_align_attempts"))
reference_attempts = int(value(candidate, prefix, "reference_align_attempts"))
descriptor_attempts = int(value(candidate, prefix, "gpu_descriptor_attempts"))
descriptor_scoreinfos = int(value(candidate, prefix, "gpu_descriptor_scoreinfos"))
if candidate_attempts <= 0:
    raise SystemExit("v5 CPU-authority replay must execute CPU Align attempts")
if reference_attempts <= 0:
    raise SystemExit("v5 CPU-authority replay must report reference Align attempts")
if candidate_attempts >= reference_attempts:
    raise SystemExit(
        "v5 CPU-authority replay must reduce CPU Align attempts "
        f"({candidate_attempts} >= {reference_attempts})"
    )
if descriptor_attempts <= 0 or descriptor_scoreinfos <= 0:
    raise SystemExit("v5 CPU-authority replay must use non-empty GPU descriptors")

print("phase7_v5_cpu_authority_replay_runtime_smoke=gate_v5_2_pass_first1")
print("phase7_v5_cpu_authority_replay_requested=1")
print("phase7_v5_cpu_authority_replay_active=1")
print("phase7_v5_cpu_authority_replay_digest_match=1")
print("phase7_v5_cpu_authority_replay_full_rows_equal=1")
print("phase7_v5_cpu_authority_replay_missing_rows=0")
print("phase7_v5_cpu_authority_replay_extra_rows=0")
print("phase7_v5_cpu_authority_replay_triplex_mismatches=0")
print(f"phase7_v5_cpu_authority_replay_candidate_align_attempts={candidate_attempts}")
print(f"phase7_v5_cpu_authority_replay_reference_align_attempts={reference_attempts}")
print("phase7_v5_cpu_authority_replay_gate_v5_2_pass=1")
print("ok")
PY
