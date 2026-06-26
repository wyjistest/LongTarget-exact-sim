#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v3_strong_seed_runtime_smoke"}"
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
  FASIM_GASAL2_PHASE7_V3_STRONG_SEED_CERTIFICATE_SOURCE=1

python3 - "$WORK/baseline/stderr.log" "$WORK/candidate/stderr.log" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_v3_descriptor_source_"


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("v3 strong-seed certificate must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v3 strong-seed certificate was not requested")
if value(candidate, "active") != "1":
    raise SystemExit("v3 strong-seed certificate did not become active")
if value(candidate, "pre_scoreinfo_source") != "1":
    raise SystemExit("v3 strong-seed certificate must be pre-scoreInfo")
if value(candidate, "after_cpu_scoreinfo_source") != "0":
    raise SystemExit("v3 strong-seed certificate must not run after CPU scoreInfo")

candidate_scoreinfos = int(value(candidate, "candidate_scoreinfos"))
candidate_attempts = int(value(candidate, "candidate_attempts"))
baseline_scoreinfos = int(value(candidate, "baseline_cpu_scoreinfo_calls"))
if baseline_scoreinfos <= 0:
    raise SystemExit("v3 strong-seed certificate must report a positive CPU baseline")
if candidate_scoreinfos < baseline_scoreinfos:
    raise SystemExit("v3 strong-seed certificate must cover every baseline scoreInfo task")
if candidate_attempts <= 0:
    raise SystemExit("v3 strong-seed certificate must emit candidate attempts")
if candidate_attempts >= 168_730_848:
    raise SystemExit("v3 strong-seed certificate must stay below all-column replay scale")

if value(candidate, "candidate_certificate_checked") != "1":
    raise SystemExit("v3 strong-seed certificate must mark certificate checked")
if int(value(candidate, "candidate_certificate_false_negatives")) != 0:
    raise SystemExit("v3 strong-seed certificate must have zero task-level false negatives")
if int(value(candidate, "missing_required_attempts")) <= 0:
    raise SystemExit("v3 strong-seed certificate must still fail closed on attempt coverage")
if value(candidate, "cpu_scoreinfo_reduced") != "1":
    raise SystemExit("v3 strong-seed certificate must reduce CPU scoreInfo calls")
if int(value(candidate, "cpu_scoreinfo_calls")) != 0:
    raise SystemExit("v3 strong-seed certificate candidate path must not call CPU scoreInfo")

print("phase7_v3_strong_seed_runtime_smoke=task_coverage_clean_attempt_coverage_missing")
print("phase7_v3_descriptor_source_active=1")
print("phase7_v3_descriptor_source_pre_scoreinfo_source=1")
print("phase7_v3_descriptor_source_candidate_scoreinfos_ge_baseline=1")
print("phase7_v3_descriptor_source_candidate_attempts_gt_zero=1")
print("phase7_v3_descriptor_source_candidate_attempts_lt_all_column=1")
print("phase7_v3_descriptor_source_candidate_certificate_checked=1")
print("phase7_v3_descriptor_source_candidate_certificate_false_negatives=0")
print("phase7_v3_descriptor_source_missing_required_attempts_gt_zero=1")
print("phase7_v3_descriptor_source_cpu_scoreinfo_calls=0")
print("phase7_v3_descriptor_source_cpu_scoreinfo_reduced=1")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_broad_gate_pass=0")
print("ok")
PY
