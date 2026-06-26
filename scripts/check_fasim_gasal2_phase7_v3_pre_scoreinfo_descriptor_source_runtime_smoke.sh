#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v3_pre_scoreinfo_descriptor_source_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_v3_pre_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_v3_pre_target
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
  FASIM_GASAL2_PHASE7_V3_PRE_SCOREINFO_DESCRIPTOR_SOURCE=1

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
    raise SystemExit("v3 pre-scoreInfo descriptor source must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v3 pre-scoreInfo descriptor source was not requested")
if value(candidate, "active") != "1":
    raise SystemExit("v3 pre-scoreInfo descriptor source did not become active")
if int(value(candidate, "candidate_scoreinfos")) <= 0:
    raise SystemExit("v3 pre-scoreInfo descriptor source must produce descriptor groups")
if int(value(candidate, "candidate_attempts")) <= 0:
    raise SystemExit("v3 pre-scoreInfo descriptor source must produce descriptor attempts")
if value(candidate, "pre_scoreinfo_source") != "1":
    raise SystemExit("v3 pre-scoreInfo descriptor source must be marked pre-scoreInfo")
if value(candidate, "after_cpu_scoreinfo_source") != "0":
    raise SystemExit("v3 pre-scoreInfo descriptor source must not be marked after CPU scoreInfo")
if value(candidate, "cpu_scoreinfo_reduced") != "0":
    raise SystemExit("current smoke must not claim CPU scoreInfo reduction")
if value(candidate, "candidate_certificate_checked") != "0":
    raise SystemExit("current smoke must not claim certificate checking")
if int(value(candidate, "cpu_scoreinfo_calls")) <= 0:
    raise SystemExit("current smoke must account unchanged CPU scoreInfo calls")
if value(candidate, "cpu_scoreinfo_calls") != value(candidate, "baseline_cpu_scoreinfo_calls"):
    raise SystemExit("current smoke should show no CPU scoreInfo reduction")
if int(value(candidate, "candidate_certificate_false_negatives")) != 0:
    raise SystemExit("current smoke must not report certificate false negatives")
if int(value(candidate, "missing_required_attempts")) != 0:
    raise SystemExit("current smoke must not report missing required attempts")

print("phase7_v3_pre_scoreinfo_descriptor_source_runtime_smoke=pre_scoreinfo_descriptors_no_reduction")
print("phase7_v3_descriptor_source_requested=1")
print("phase7_v3_descriptor_source_active=1")
print("phase7_v3_descriptor_source_pre_scoreinfo_source=1")
print("phase7_v3_descriptor_source_candidate_attempts_gt_zero=1")
print("phase7_v3_descriptor_source_cpu_scoreinfo_reduced=0")
print("phase7_v3_descriptor_source_candidate_certificate_checked=0")
print("ok")
PY
