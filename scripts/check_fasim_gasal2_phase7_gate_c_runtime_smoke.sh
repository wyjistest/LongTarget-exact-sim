#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_gate_c_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_gate_c_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_gate_c_target
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
run_case "$WORK/candidate" FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1

python3 - "$WORK/baseline/stderr.log" "$WORK/candidate/stderr.log" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_gate_c_"


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("Gate C must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("Gate C env did not request path")
if int(value(candidate, "oracle_attempts")) <= 0:
    raise SystemExit("Gate C smoke must record oracle attempts")

print("phase7_gate_c_runtime_smoke=pass")
print("ok")
PY
