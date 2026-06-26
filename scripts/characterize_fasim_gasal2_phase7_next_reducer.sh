#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer"}"
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

rna_input="$WORK/inputs/phase7_short_query.fa"
dna_input="$WORK/inputs/phase7_short_target.fa"
cat >"$rna_input" <<'EOF'
>phase7_short_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$dna_input" <<'EOF'
>phase7_short_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

run_case() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
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

digest_for_dir() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  sha256sum "$out_file" | awk '{print $1}'
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
  FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW=1

baseline_digest="$(digest_for_dir "$WORK/baseline")"
candidate_digest="$(digest_for_dir "$WORK/candidate")"

python3 - \
  "$WORK/baseline/stdout.log" \
  "$WORK/candidate/stdout.log" \
  "$WORK/candidate/stderr.log" \
  "$baseline_digest" \
  "$candidate_digest" \
  "$WORK/report.tsv" <<'PY'
from pathlib import Path
import re
import sys

baseline_stdout = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate_stdout = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
candidate_stderr = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")
baseline_digest = sys.argv[4]
candidate_digest = sys.argv[5]
report = Path(sys.argv[6])


def metric(text, name, default="0"):
    match = re.search(rf"^{re.escape(name)}=(\S+)$", text, flags=re.MULTILINE)
    return match.group(1) if match else default


def wall_seconds(text):
    match = re.search(r"^Running time is\s+([0-9.]+)$", text, flags=re.MULTILINE)
    return float(match.group(1)) if match else 0.0


baseline_wall = wall_seconds(baseline_stdout)
candidate_wall = wall_seconds(candidate_stdout)
candidate_vs_baseline = (
    baseline_wall / candidate_wall if baseline_wall > 0.0 and candidate_wall > 0.0 else 0.0
)

prefix = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_"
digest_match = 1 if baseline_digest == candidate_digest else 0
false_negative_scoreinfos = int(metric(candidate_stderr, prefix + "false_negative_scoreinfos"))
triplex_mismatches = int(metric(candidate_stderr, prefix + "triplex_mismatches"))
candidate_align_attempts = int(metric(candidate_stderr, prefix + "candidate_align_attempts"))
reference_align_attempts = int(metric(candidate_stderr, prefix + "reference_align_attempts"))

decision = "phase7_next_reducer_no_go"
if (
    digest_match == 1
    and false_negative_scoreinfos == 0
    and triplex_mismatches == 0
    and candidate_align_attempts < reference_align_attempts
):
    decision = "phase7_next_reducer_go"

columns = [
    "workload",
    "record_limit",
    "digest_match",
    "false_negative_scoreinfos",
    "triplex_mismatches",
    "candidate_align_attempts",
    "reference_align_attempts",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "candidate_vs_baseline",
    "decision",
]
values = [
    "phase7_short_query_smoke",
    "1",
    str(digest_match),
    str(false_negative_scoreinfos),
    str(triplex_mismatches),
    str(candidate_align_attempts),
    str(reference_align_attempts),
    f"{candidate_wall:.6f}",
    f"{baseline_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    decision,
]
report.write_text("\t".join(columns) + "\n" + "\t".join(values) + "\n", encoding="utf-8")
print(f"phase7_next_reducer_characterization_report={report}")
print(f"phase7_next_reducer_characterization_decision={decision}")
PY
