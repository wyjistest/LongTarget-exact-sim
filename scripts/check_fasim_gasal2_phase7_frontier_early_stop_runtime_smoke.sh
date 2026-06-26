#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_frontier_early_stop_runtime_smoke"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

rna_input="$WORK/inputs/phase7_early_stop_query.fa"
dna_input="$WORK/inputs/phase7_early_stop_target.fa"
cat >"$rna_input" <<'EOF'
>phase7_early_stop_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$dna_input" <<'EOF'
>phase7_early_stop_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

run_case() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
    FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$dna_input" \
    -f2 "$rna_input" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

lite_output() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$out_file"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1

baseline_out="$(lite_output "$WORK/baseline")"
candidate_out="$(lite_output "$WORK/candidate")"

python3 - \
  "$WORK/baseline/stderr.log" \
  "$WORK/candidate/stderr.log" \
  "$baseline_out" \
  "$candidate_out" <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import sys

baseline_stderr = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate_stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
baseline_out = Path(sys.argv[3]).read_bytes()
candidate_out = Path(sys.argv[4]).read_bytes()


def metrics(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    prefix = "benchmark.fasim_gasal2_phase7_frontier_early_stop_"
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        key, sep, value = line.partition("=")
        if sep:
            out[key] = value
    return out


base = metrics(baseline_stderr)
candidate = metrics(candidate_stderr)
prefix = "benchmark.fasim_gasal2_phase7_frontier_early_stop_"

for suffix in [
    "requested",
    "active",
    "scoreinfos",
    "reference_align_attempts",
    "candidate_align_attempts",
    "skipped_attempts",
]:
    key = prefix + suffix
    if key not in base:
        raise SystemExit(f"default run missing metric: {key}")
    if key not in candidate:
        raise SystemExit(f"candidate run missing metric: {key}")

if base[prefix + "requested"] != "0" or base[prefix + "active"] != "0":
    raise SystemExit("early-stop must be default-off")
if candidate[prefix + "requested"] != "1" or candidate[prefix + "active"] != "1":
    raise SystemExit("early-stop env did not activate runtime telemetry")

reference = int(candidate[prefix + "reference_align_attempts"])
candidate_attempts = int(candidate[prefix + "candidate_align_attempts"])
skipped = int(candidate[prefix + "skipped_attempts"])
scoreinfos = int(candidate[prefix + "scoreinfos"])
if scoreinfos <= 0:
    raise SystemExit("early-stop scoreinfo count must be positive")
if reference <= 0 or candidate_attempts <= 0:
    raise SystemExit("early-stop attempt counts must be positive")
if candidate_attempts > reference:
    raise SystemExit(
        f"candidate attempts exceed reference attempts: {candidate_attempts}>{reference}"
    )
if skipped != reference - candidate_attempts:
    raise SystemExit(
        f"skipped attempts mismatch: skipped={skipped} reference={reference} candidate={candidate_attempts}"
    )

baseline_digest = hashlib.sha256(baseline_out).hexdigest()
candidate_digest = hashlib.sha256(candidate_out).hexdigest()
if baseline_digest != candidate_digest:
    raise SystemExit(
        f"early-stop changed lite output digest: {baseline_digest} != {candidate_digest}"
    )

print("phase7_frontier_early_stop_runtime_smoke=pass")
print(f"phase7_frontier_early_stop_reference_align_attempts={reference}")
print(f"phase7_frontier_early_stop_candidate_align_attempts={candidate_attempts}")
print(f"phase7_frontier_early_stop_skipped_attempts={skipped}")
PY
