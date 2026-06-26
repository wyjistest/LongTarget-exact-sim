#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v3_oracle_min_cover_replay_runtime_smoke"}"
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
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY=1

python3 - \
  "$WORK/baseline/stderr.log" \
  "$WORK/candidate/stderr.log" \
  "$(lite_output "$WORK/baseline")" \
  "$(lite_output "$WORK/candidate")" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

base_stderr = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate_stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
baseline_out = Path(sys.argv[3])
candidate_out = Path(sys.argv[4])
prefix = "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_"


def value(text: str, name: str) -> str:
    needle = name + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


if value(base_stderr, prefix + "requested") != "0":
    raise SystemExit("oracle min-cover replay must be default-off")
if value(candidate_stderr, prefix + "requested") != "1":
    raise SystemExit("oracle min-cover replay was not requested")
if value(candidate_stderr, prefix + "active") != "1":
    raise SystemExit("oracle min-cover replay was not active")

reference = int(value(candidate_stderr, prefix + "reference_align_attempts"))
candidate = int(value(candidate_stderr, prefix + "candidate_align_attempts"))
min_cover = int(value(candidate_stderr, prefix + "candidate_min_cover_positions"))
if reference != 2872:
    raise SystemExit(f"unexpected reference attempts: {reference}")
if min_cover != 463:
    raise SystemExit(f"unexpected min-cover positions: {min_cover}")
if candidate <= 0 or candidate >= reference:
    raise SystemExit(f"oracle min-cover replay must reduce Align attempts: {candidate}/{reference}")

baseline_text = baseline_out.read_text(encoding="utf-8", errors="replace")
candidate_text = candidate_out.read_text(encoding="utf-8", errors="replace")
baseline_rows = {line.rstrip("\n") for line in baseline_text.splitlines() if line.rstrip("\n")}
candidate_rows = {line.rstrip("\n") for line in candidate_text.splitlines() if line.rstrip("\n")}
missing_rows = len(baseline_rows - candidate_rows)
extra_rows = len(candidate_rows - baseline_rows)
digest_match = int(
    hashlib.sha256(baseline_text.encode()).hexdigest()
    == hashlib.sha256(candidate_text.encode()).hexdigest()
)
full_rows_equal = int(missing_rows == 0 and extra_rows == 0)

if digest_match != 0 or full_rows_equal != 0:
    raise SystemExit("oracle min-cover replay unexpectedly preserved full output")
if missing_rows != 11 or extra_rows != 9:
    raise SystemExit(
        "unexpected oracle min-cover replay row drift: "
        f"missing={missing_rows} extra={extra_rows}"
    )

print("phase7_v3_oracle_min_cover_replay_runtime_smoke=output_no_go")
print("phase7_v3_oracle_min_cover_replay_active=1")
print("phase7_v3_oracle_min_cover_replay_candidate_align_attempts_lt_reference=1")
print("phase7_v3_oracle_min_cover_replay_digest_match=" + str(digest_match))
print("phase7_v3_oracle_min_cover_replay_full_rows_equal=" + str(full_rows_equal))
print("phase7_v3_oracle_min_cover_replay_missing_rows=" + str(missing_rows))
print("phase7_v3_oracle_min_cover_replay_extra_rows=" + str(extra_rows))
print("phase7_broad_restart_v3_gate_v3_2_shape_probe_pass=0")
print("phase7_broad_restart_v3_broad_gate_pass=0")
print("ok")
PY
