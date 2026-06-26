#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v3_certificate_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_v3_certificate_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_v3_certificate_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

run_case() {
  local out_dir="$1"
  shift
  env \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$WORK/inputs/target.fa" \
    -f2 "$WORK/inputs/query.fa" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_GASAL2_PHASE7_V3_PRE_SCOREINFO_DESCRIPTOR_SOURCE=1 \
  FASIM_GASAL2_PHASE7_V3_CERTIFICATE_CHECK=1

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
    raise SystemExit("v3 certificate path must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v3 certificate path was not requested")
if value(candidate, "active") != "1":
    raise SystemExit("v3 certificate path did not become active")
if value(candidate, "pre_scoreinfo_source") != "1":
    raise SystemExit("v3 certificate path must remain pre-scoreInfo")
if value(candidate, "after_cpu_scoreinfo_source") != "0":
    raise SystemExit("v3 certificate path must not be after CPU scoreInfo")
if int(value(candidate, "candidate_scoreinfos")) <= 0:
    raise SystemExit("v3 certificate path must keep descriptor groups")
if int(value(candidate, "candidate_attempts")) <= 0:
    raise SystemExit("v3 certificate path must keep descriptor attempts")
if value(candidate, "candidate_certificate_checked") != "1":
    raise SystemExit("v3 certificate path must mark certificate checked")
if int(value(candidate, "candidate_certificate_false_negatives")) != 0:
    raise SystemExit("v3 certificate path must have zero certificate false negatives")
if int(value(candidate, "missing_required_attempts")) != 0:
    raise SystemExit("v3 certificate path must have zero missing required attempts")
if value(candidate, "cpu_scoreinfo_reduced") != "0":
    raise SystemExit("certificate smoke must not claim CPU scoreInfo reduction")
if int(value(candidate, "cpu_scoreinfo_calls")) <= 0:
    raise SystemExit("certificate smoke must account unchanged CPU scoreInfo calls")
if value(candidate, "cpu_scoreinfo_calls") != value(candidate, "baseline_cpu_scoreinfo_calls"):
    raise SystemExit("certificate smoke must still show no CPU scoreInfo reduction")

print("phase7_v3_certificate_runtime_smoke=certificate_checked_no_scoreinfo_reduction")
print("phase7_v3_descriptor_source_active=1")
print("phase7_v3_descriptor_source_pre_scoreinfo_source=1")
print("phase7_v3_descriptor_source_candidate_attempts_gt_zero=1")
print("phase7_v3_descriptor_source_candidate_certificate_checked=1")
print("phase7_v3_descriptor_source_candidate_certificate_false_negatives=0")
print("phase7_v3_descriptor_source_missing_required_attempts=0")
print("phase7_v3_descriptor_source_cpu_scoreinfo_reduced=0")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("ok")
PY
