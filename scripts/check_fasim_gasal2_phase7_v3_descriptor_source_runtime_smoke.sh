#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v3_descriptor_source_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_v3_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_v3_target
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
run_case "$WORK/candidate" FASIM_GASAL2_PHASE7_V3_DESCRIPTOR_SOURCE=1

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
    raise SystemExit("v3 descriptor-source path must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v3 descriptor-source env did not request path")
if value(candidate, "active") != "0":
    raise SystemExit("current v3 smoke must not claim an active descriptor source")
if int(value(candidate, "reference_scoreinfos")) <= 0:
    raise SystemExit("v3 smoke must observe reference scoreInfo groups")
if int(value(candidate, "reference_attempts")) <= 0:
    raise SystemExit("v3 smoke must observe reference attempts")
if int(value(candidate, "candidate_scoreinfos")) != 0:
    raise SystemExit("current v3 smoke must not claim candidate scoreInfos")
if int(value(candidate, "candidate_attempts")) != 0:
    raise SystemExit("current v3 smoke must not claim candidate attempts")
cpu_calls = int(value(candidate, "cpu_scoreinfo_calls"))
baseline_cpu_calls = int(value(candidate, "baseline_cpu_scoreinfo_calls"))
if cpu_calls <= 0 or baseline_cpu_calls <= 0:
    raise SystemExit("v3 smoke must account CPU scoreInfo calls")
if cpu_calls != baseline_cpu_calls:
    raise SystemExit("current v3 smoke should show no CPU scoreInfo reduction")
if int(value(candidate, "candidate_certificate_false_negatives")) != 0:
    raise SystemExit("v3 smoke scaffold must not report certificate false negatives")
if int(value(candidate, "missing_required_attempts")) != 0:
    raise SystemExit("v3 smoke scaffold must not report missing required attempts")
if value(candidate, "pre_scoreinfo_source") != "0":
    raise SystemExit("current v3 smoke must not claim a pre-scoreInfo source")
if value(candidate, "after_cpu_scoreinfo_source") != "1":
    raise SystemExit("current v3 smoke must mark descriptor evidence as after CPU scoreInfo")

print("phase7_v3_descriptor_source_runtime_smoke=current_no_pre_scoreinfo_source")
print("phase7_v3_descriptor_source_requested=1")
print("phase7_v3_descriptor_source_active=0")
print("phase7_v3_descriptor_source_candidate_attempts=0")
print("phase7_v3_descriptor_source_cpu_scoreinfo_reduced=0")
print("ok")
PY
