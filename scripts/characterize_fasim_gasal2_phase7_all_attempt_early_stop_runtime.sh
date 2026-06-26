#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_all_attempt_early_stop_runtime"}"
BUILD_BIN="${BUILD_BIN:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
RECORD_LIMIT="${RECORD_LIMIT:-${FIRST1_RECORD_LIMIT:-1}}"
WORKLOAD_LABEL="${WORKLOAD_LABEL:-"neat1_first${RECORD_LIMIT}"}"
DECISION_LABEL="${DECISION_LABEL:-"first${RECORD_LIMIT}"}"

if [[ ! "$RECORD_LIMIT" =~ ^[0-9]+$ || "$RECORD_LIMIT" -le 0 ]]; then
  echo "RECORD_LIMIT must be positive, got: $RECORD_LIMIT" >&2
  exit 1
fi

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing NEAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

REPORT="$WORK/report.tsv"
printf '%s\n' \
  "workload	record_limit	attempted	digest_match	full_rows_equal	missing_rows	extra_rows	triplex_mismatches	false_negative_scoreinfos	candidate_align_attempts	reference_align_attempts	align_attempt_reduction	candidate_wall_seconds	baseline_wall_seconds	candidate_vs_baseline	all_attempt_requested	all_attempt_active	all_attempt_skipped_attempts	decision	decision_reasons	run_dir" \
  >"$REPORT"

sample="$WORK/inputs/${WORKLOAD_LABEL}.fa"
awk -v limit="$RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty NEAT1 sample" >&2
  exit 1
fi

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
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

run_dir="$WORK/$WORKLOAD_LABEL"
baseline_dir="$run_dir/baseline"
candidate_dir="$run_dir/candidate"
mkdir -p "$run_dir"

echo "running Phase 7 all-attempt early-stop runtime $WORKLOAD_LABEL" >&2
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1

baseline_out="$(lite_output "$baseline_dir")"
candidate_out="$(lite_output "$candidate_dir")"

python3 - \
  "$REPORT" \
  "$baseline_out" \
  "$candidate_out" \
  "$baseline_dir/stdout.log" \
  "$candidate_dir/stdout.log" \
  "$candidate_dir/stderr.log" \
  "$run_dir" \
  "$RECORD_LIMIT" \
  "$WORKLOAD_LABEL" \
  "$DECISION_LABEL" <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import sys

report = Path(sys.argv[1])
baseline_out = Path(sys.argv[2])
candidate_out = Path(sys.argv[3])
baseline_stdout = Path(sys.argv[4]).read_text(encoding="utf-8", errors="replace")
candidate_stdout = Path(sys.argv[5]).read_text(encoding="utf-8", errors="replace")
candidate_stderr = Path(sys.argv[6]).read_text(encoding="utf-8", errors="replace")
run_dir = sys.argv[7]
record_limit = sys.argv[8]
workload_label = sys.argv[9]
decision_label = sys.argv[10]


def wall_seconds(text: str) -> float:
    match = re.search(r"^Running time is\s+([0-9.]+)$", text, flags=re.MULTILINE)
    return float(match.group(1)) if match else 0.0


def metric(name: str, default: str = "0") -> str:
    match = re.search(rf"^{re.escape(name)}=(\S+)$", candidate_stderr, flags=re.MULTILINE)
    return match.group(1) if match else default


baseline_text = baseline_out.read_text(encoding="utf-8", errors="replace")
candidate_text = candidate_out.read_text(encoding="utf-8", errors="replace")
baseline_rows = [line.rstrip("\n") for line in baseline_text.splitlines() if line.rstrip("\n")]
candidate_rows = [line.rstrip("\n") for line in candidate_text.splitlines() if line.rstrip("\n")]
baseline_set = set(baseline_rows)
candidate_set = set(candidate_rows)
missing_rows = len(baseline_set - candidate_set)
extra_rows = len(candidate_set - baseline_set)
full_rows_equal = 1 if missing_rows == 0 and extra_rows == 0 else 0
digest_match = 1 if (
    hashlib.sha256(baseline_text.encode()).hexdigest()
    == hashlib.sha256(candidate_text.encode()).hexdigest()
) else 0

prefix = "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_"
requested = metric(prefix + "requested")
active = metric(prefix + "active")
reference_align_attempts = int(metric(prefix + "reference_align_attempts"))
candidate_align_attempts = int(metric(prefix + "candidate_align_attempts"))
skipped_attempts = int(metric(prefix + "skipped_attempts"))
align_attempt_reduction = reference_align_attempts - candidate_align_attempts
baseline_wall = wall_seconds(baseline_stdout)
candidate_wall = wall_seconds(candidate_stdout)
candidate_vs_baseline = (
    baseline_wall / candidate_wall if baseline_wall > 0.0 and candidate_wall > 0.0 else 0.0
)

decision_reasons: list[str] = []
if requested != "1":
    decision_reasons.append("all_attempt_not_requested")
if active != "1":
    decision_reasons.append("all_attempt_not_active")
if digest_match != 1 and full_rows_equal != 1:
    decision_reasons.append("output_rows_differ")
if missing_rows != 0:
    decision_reasons.append("missing_rows")
if extra_rows != 0:
    decision_reasons.append("extra_rows")
if candidate_align_attempts >= reference_align_attempts:
    decision_reasons.append("no_align_reduction")
if skipped_attempts != align_attempt_reduction:
    decision_reasons.append("skipped_attempts_mismatch")

decision = f"phase7_all_attempt_early_stop_runtime_{decision_label}_go"
if decision_reasons:
    decision = f"phase7_all_attempt_early_stop_runtime_{decision_label}_no_go"

values = [
    workload_label,
    record_limit,
    "1",
    str(digest_match),
    str(full_rows_equal),
    str(missing_rows),
    str(extra_rows),
    "0" if full_rows_equal else str(missing_rows + extra_rows),
    "0" if full_rows_equal else "unknown",
    str(candidate_align_attempts),
    str(reference_align_attempts),
    str(align_attempt_reduction),
    f"{candidate_wall:.6f}",
    f"{baseline_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    requested,
    active,
    str(skipped_attempts),
    decision,
    ",".join(decision_reasons) if decision_reasons else "none",
    run_dir,
]
with report.open("a", encoding="utf-8") as handle:
    handle.write("\t".join(values) + "\n")

print(f"phase7_all_attempt_early_stop_runtime_{decision_label}_decision={decision}")
print(
    f"phase7_all_attempt_early_stop_runtime_{decision_label}_align_attempts="
    f"{candidate_align_attempts}/{reference_align_attempts}"
)
PY

cat "$REPORT"
