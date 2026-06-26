#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_v5_cpu_authority_replay_first64"}"
BUILD_BIN="${BUILD_BIN:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
RECORD_LIMIT="${RECORD_LIMIT:-64}"
WORKLOAD_LABEL="${WORKLOAD_LABEL:-neat1_first64}"

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
mkdir -p "$WORK/inputs" "$WORK/$WORKLOAD_LABEL"

REPORT="$WORK/report.tsv"
printf '%s\n' \
  "workload	record_limit	attempted	digest_match	full_rows_equal	missing_rows	extra_rows	triplex_mismatches	candidate_align_attempts	reference_align_attempts	align_attempt_reduction	candidate_wall_seconds	baseline_wall_seconds	candidate_vs_baseline	requested	active	source_is_pre_scoreinfo	scoreinfo_prealign_reduced	gpu_descriptor_scoreinfos	gpu_descriptor_attempts	descriptor_false_negatives	missing_required_attempts	cpu_align_authority	gpu_endpoint_cigar_traceback_output_authority	fallback_accounting_clean	broad_gate_pass	decision	decision_reasons	run_dir" \
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
  local start_seconds end_seconds
  start_seconds="$(date +%s.%N)"
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
  end_seconds="$(date +%s.%N)"
  awk -v start="$start_seconds" -v end="$end_seconds" \
    'BEGIN {printf "%.6f\n", end - start}' >"$out_dir/wall_seconds.txt"
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

echo "running Phase 7 v5 CPU-authority replay first64 baseline" >&2
run_fasim "$baseline_dir"
echo "running Phase 7 v5 CPU-authority replay first64 candidate" >&2
run_fasim "$candidate_dir" \
  FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY=1

python3 - \
  "$REPORT" \
  "$(lite_output "$baseline_dir")" \
  "$(lite_output "$candidate_dir")" \
  "$baseline_dir/wall_seconds.txt" \
  "$candidate_dir/wall_seconds.txt" \
  "$candidate_dir/stderr.log" \
  "$run_dir" \
  "$RECORD_LIMIT" \
  "$WORKLOAD_LABEL" <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import sys

report = Path(sys.argv[1])
baseline_out = Path(sys.argv[2])
candidate_out = Path(sys.argv[3])
baseline_wall = float(Path(sys.argv[4]).read_text().strip())
candidate_wall = float(Path(sys.argv[5]).read_text().strip())
candidate_stderr = Path(sys.argv[6]).read_text(encoding="utf-8", errors="replace")
run_dir = sys.argv[7]
record_limit = sys.argv[8]
workload = sys.argv[9]


def rows(path: Path) -> list[str]:
    return [
        line.rstrip("\n")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.rstrip("\n")
    ]


def metric(suffix: str, default: str = "0") -> str:
    prefix = "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_"
    needle = prefix + suffix + "="
    for line in candidate_stderr.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    return default


baseline_text = baseline_out.read_text(encoding="utf-8", errors="replace")
candidate_text = candidate_out.read_text(encoding="utf-8", errors="replace")
baseline_set = set(rows(baseline_out))
candidate_set = set(rows(candidate_out))
missing_rows = len(baseline_set - candidate_set)
extra_rows = len(candidate_set - baseline_set)
full_rows_equal = 1 if missing_rows == 0 and extra_rows == 0 else 0
digest_match = 1 if (
    hashlib.sha256(baseline_text.encode()).hexdigest()
    == hashlib.sha256(candidate_text.encode()).hexdigest()
) else 0

requested = metric("requested")
active = metric("active")
source_is_pre_scoreinfo = metric("source_is_pre_scoreinfo")
scoreinfo_prealign_reduced = metric("scoreinfo_prealign_reduced")
gpu_descriptor_scoreinfos = int(metric("gpu_descriptor_scoreinfos"))
gpu_descriptor_attempts = int(metric("gpu_descriptor_attempts"))
candidate_align_attempts = int(metric("candidate_align_attempts"))
reference_align_attempts = int(metric("reference_align_attempts"))
descriptor_false_negatives = int(metric("descriptor_false_negatives"))
missing_required_attempts = int(metric("missing_required_attempts"))
cpu_align_authority = metric("cpu_align_authority")
gpu_authority = metric("gpu_endpoint_cigar_traceback_output_authority")
telemetry_full_rows_equal = metric("full_rows_equal")
telemetry_digest_match = metric("digest_match")
telemetry_missing_rows = int(metric("missing_rows"))
telemetry_extra_rows = int(metric("extra_rows"))
telemetry_triplex_mismatches = int(metric("triplex_mismatches"))

align_attempt_reduction = reference_align_attempts - candidate_align_attempts
candidate_vs_baseline = (
    baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
)
fallback_accounting_clean = 1 if (
    requested == "1"
    and active == "1"
    and source_is_pre_scoreinfo == "1"
    and scoreinfo_prealign_reduced == "1"
    and descriptor_false_negatives == 0
    and missing_required_attempts == 0
    and cpu_align_authority == "1"
    and gpu_authority == "0"
) else 0

reasons: list[str] = []
if digest_match != 1 or full_rows_equal != 1:
    reasons.append("output_rows_differ")
if telemetry_full_rows_equal != "1" or telemetry_digest_match != "1":
    reasons.append("telemetry_output_gate_failed")
if telemetry_missing_rows != 0 or telemetry_extra_rows != 0:
    reasons.append("telemetry_row_diff")
if telemetry_triplex_mismatches != 0:
    reasons.append("triplex_mismatches")
if candidate_align_attempts <= 0 or reference_align_attempts <= 0:
    reasons.append("missing_align_attempts")
elif candidate_align_attempts >= reference_align_attempts:
    reasons.append("no_align_reduction")
if scoreinfo_prealign_reduced != "1":
    reasons.append("scoreinfo_prealign_not_reduced")
if fallback_accounting_clean != 1:
    reasons.append("fallback_accounting_not_clean")
if candidate_vs_baseline <= 1.0:
    reasons.append("candidate_vs_baseline_not_above_1")

broad_gate_pass = 0 if reasons else 1
decision = (
    "phase7_v5_cpu_authority_replay_first64_broad_gate_go"
    if broad_gate_pass
    else "phase7_v5_cpu_authority_replay_first64_broad_gate_no_go"
)

values = [
    workload,
    record_limit,
    "1",
    str(digest_match),
    str(full_rows_equal),
    str(missing_rows),
    str(extra_rows),
    str(telemetry_triplex_mismatches),
    str(candidate_align_attempts),
    str(reference_align_attempts),
    str(align_attempt_reduction),
    f"{candidate_wall:.6f}",
    f"{baseline_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    requested,
    active,
    source_is_pre_scoreinfo,
    scoreinfo_prealign_reduced,
    str(gpu_descriptor_scoreinfos),
    str(gpu_descriptor_attempts),
    str(descriptor_false_negatives),
    str(missing_required_attempts),
    cpu_align_authority,
    gpu_authority,
    str(fallback_accounting_clean),
    str(broad_gate_pass),
    decision,
    ",".join(reasons) if reasons else "none",
    run_dir,
]
with report.open("a", encoding="utf-8") as handle:
    handle.write("\t".join(values) + "\n")

print(f"phase7_v5_cpu_authority_replay_first64_decision={decision}")
print(f"phase7_v5_cpu_authority_replay_first64_broad_gate_pass={broad_gate_pass}")
print(f"phase7_v5_cpu_authority_replay_first64_candidate_vs_baseline={candidate_vs_baseline:.6f}")
PY

cat "$REPORT"
