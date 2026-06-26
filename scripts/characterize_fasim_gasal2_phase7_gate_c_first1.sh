#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_gate_c_first1"}"
BUILD_BIN="${BUILD_BIN:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
GATE_B_CANDIDATE_ALIGN_ATTEMPTS="${GATE_B_CANDIDATE_ALIGN_ATTEMPTS:-2008}"

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
if [[ ! "$GATE_B_CANDIDATE_ALIGN_ATTEMPTS" =~ ^[0-9]+$ || "$GATE_B_CANDIDATE_ALIGN_ATTEMPTS" -le 0 ]]; then
  echo "GATE_B_CANDIDATE_ALIGN_ATTEMPTS must be positive" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

REPORT="$WORK/report.tsv"
printf '%s\n' \
  "workload	record_limit	attempted	digest_match	full_rows_equal	missing_rows	extra_rows	triplex_mismatches	false_negative_scoreinfos	candidate_align_attempts	gate_b_candidate_align_attempts	scoreinfo_reduced	oracle_scoreinfos	oracle_attempts	gpu_candidate_scoreinfos	gpu_candidate_attempts	missing_required_attempts	extra_candidate_attempts	gate_c_requested	gate_c_active	candidate_wall_seconds	baseline_wall_seconds	candidate_vs_baseline	decision	decision_reasons	run_dir" \
  >"$REPORT"

sample="$WORK/inputs/neat1_first1.fa"
awk '
  /^>/ { ++records }
  records <= 1 { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty NEAT1 first1 sample" >&2
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

run_dir="$WORK/neat1_first1"
baseline_dir="$run_dir/baseline"
candidate_dir="$run_dir/candidate"
mkdir -p "$run_dir"

echo "running Phase 7 Gate C first1 characterization" >&2
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1 \
  FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1

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
  "$GATE_B_CANDIDATE_ALIGN_ATTEMPTS" <<'PY'
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
gate_b_candidate_align_attempts = int(sys.argv[8])


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

prefix = "benchmark.fasim_gasal2_phase7_gate_c_"
requested = metric(prefix + "requested")
active = metric(prefix + "active")
oracle_scoreinfos = int(metric(prefix + "oracle_scoreinfos"))
oracle_attempts = int(metric(prefix + "oracle_attempts"))
gpu_candidate_scoreinfos = int(metric(prefix + "gpu_candidate_scoreinfos"))
gpu_candidate_attempts = int(metric(prefix + "gpu_candidate_attempts"))
false_negative_scoreinfos = int(metric(prefix + "false_negative_scoreinfos"))
missing_required_attempts = int(metric(prefix + "missing_required_attempts"))
extra_candidate_attempts = int(metric(prefix + "extra_candidate_attempts"))
candidate_align_attempts = int(metric(prefix + "candidate_align_attempts"))
scoreinfo_reduced = 1 if gpu_candidate_scoreinfos > 0 and gpu_candidate_attempts > 0 else 0

baseline_wall = wall_seconds(baseline_stdout)
candidate_wall = wall_seconds(candidate_stdout)
candidate_vs_baseline = (
    baseline_wall / candidate_wall if baseline_wall > 0.0 and candidate_wall > 0.0 else 0.0
)

decision_reasons: list[str] = []
if requested != "1":
    decision_reasons.append("gate_c_not_requested")
if active != "1":
    decision_reasons.append("gate_c_not_active")
if digest_match != 1 and full_rows_equal != 1:
    decision_reasons.append("output_rows_differ")
if missing_rows != 0:
    decision_reasons.append("missing_rows")
if extra_rows != 0:
    decision_reasons.append("extra_rows")
if false_negative_scoreinfos != 0:
    decision_reasons.append("false_negative_scoreinfos")
if missing_required_attempts != 0:
    decision_reasons.append("missing_required_attempts")
if candidate_align_attempts > gate_b_candidate_align_attempts:
    decision_reasons.append("more_align_attempts_than_gate_b")
if gpu_candidate_attempts == 0:
    decision_reasons.append("no_gpu_candidate_descriptors")
if scoreinfo_reduced != 1:
    decision_reasons.append("scoreinfo_not_reduced")

decision = "phase7_gate_c_first1_go"
if decision_reasons:
    decision = "phase7_gate_c_first1_no_go"

values = [
    "neat1_first1",
    "1",
    "1",
    str(digest_match),
    str(full_rows_equal),
    str(missing_rows),
    str(extra_rows),
    "0" if full_rows_equal else str(missing_rows + extra_rows),
    str(false_negative_scoreinfos),
    str(candidate_align_attempts),
    str(gate_b_candidate_align_attempts),
    str(scoreinfo_reduced),
    str(oracle_scoreinfos),
    str(oracle_attempts),
    str(gpu_candidate_scoreinfos),
    str(gpu_candidate_attempts),
    str(missing_required_attempts),
    str(extra_candidate_attempts),
    requested,
    active,
    f"{candidate_wall:.6f}",
    f"{baseline_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    decision,
    ",".join(decision_reasons) if decision_reasons else "none",
    run_dir,
]
with report.open("a", encoding="utf-8") as handle:
    handle.write("\t".join(values) + "\n")

print("phase7_gate_c_first1_decision=" + decision)
print(f"phase7_gate_c_first1_candidate_align_attempts={candidate_align_attempts}")
print(f"phase7_gate_c_first1_gpu_candidate_attempts={gpu_candidate_attempts}")
PY

cat "$REPORT"
