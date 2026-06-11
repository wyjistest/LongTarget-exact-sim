#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_cpu_authority_candidate_coverage"}"
BUILD_BIN="${BUILD_BIN:-1}"
NEAT1_RECORD_LIMITS="${NEAT1_RECORD_LIMITS:-1 64}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-4}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

case "$REPLAY_PROBE_MAX_TASKS" in
  ''|*[!0-9]*)
    echo "REPLAY_PROBE_MAX_TASKS must be a non-negative integer, got: $REPLAY_PROBE_MAX_TASKS" >&2
    exit 1
    ;;
esac
if [[ "$REPLAY_PROBE_MAX_TASKS" -le 0 ]]; then
  echo "REPLAY_PROBE_MAX_TASKS must be > 0 for bounded characterization" >&2
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
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
report="$WORK/coverage_report.json"
printf '%s\n' \
  "workload	record_limit	replay_probe_max_tasks	digest_match	baseline_digest	candidate_digest	total_tasks	state_machine_tasks	scoreinfos	attempts	candidate_attempts	selected	covered	false_negative_scoreinfos	candidate_align_attempts	candidate_coverage_reference_align_attempts	same_scope_cpu_align_reduction	same_scope_cpu_align_reduction_ratio	candidate_align_seconds	candidate_coverage_reference_align_seconds	realpath_extend_align_attempts	realpath_extend_align_seconds	state_machine_total_seconds	realpath_extend_seconds	triplex_mismatches	baseline_wall_seconds	candidate_wall_seconds	candidate_vs_baseline	decision" \
  >"$summary"

first_records() {
  local input="$1"
  local limit="$2"
  local output="$3"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$input" >"$output"
  if [[ ! -s "$output" ]]; then
    echo "empty sample generated from $input limit=$limit" >&2
    exit 1
  fi
}

run_fasim() {
  local sample="$1"
  local out_dir="$2"
  shift 2
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

metric() {
  local stderr="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1
}

wall_seconds() {
  local out_dir="$1"
  local wall
  wall="$(metric "$out_dir/stderr.log" benchmark.total_wall_seconds)"
  if [[ -z "$wall" ]]; then
    wall="$(sed -n 's/^Running time is //p' "$out_dir/stdout.log" | tail -n 1)"
  fi
  if [[ -z "$wall" ]]; then
    echo "missing wall seconds for $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$wall"
}

run_case() {
  local limit="$1"
  case "$limit" in
    ''|*[!0-9]*)
      echo "record limit must be a positive integer, got: $limit" >&2
      exit 1
      ;;
  esac
  if [[ "$limit" -le 0 ]]; then
    echo "record limit must be a positive integer, got: $limit" >&2
    exit 1
  fi

  local run_dir="$WORK/neat1_first${limit}_probe${REPLAY_PROBE_MAX_TASKS}"
  mkdir -p "$run_dir/inputs"
  local sample="$run_dir/inputs/neat1_first${limit}.fa"
  first_records "$DNA_INPUT" "$limit" "$sample"

  echo "running NEAT1 first${limit} CPU-authority candidate coverage probe=${REPLAY_PROBE_MAX_TASKS}" >&2
  run_fasim "$sample" "$run_dir/baseline"
  run_fasim "$sample" "$run_dir/candidate" \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$REPLAY_PROBE_MAX_TASKS" \
    FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1 \
    FASIM_GASAL2_CPU_AUTHORITY_CANDIDATE_COVERAGE_SHADOW=1 \
    FASIM_ALIGN_GASAL2=1

  local baseline_digest candidate_digest digest_match stderr
  baseline_digest="$(digest_for_dir "$run_dir/baseline")"
  candidate_digest="$(digest_for_dir "$run_dir/candidate")"
  digest_match=0
  if [[ "$baseline_digest" == "$candidate_digest" ]]; then
    digest_match=1
  fi
  stderr="$run_dir/candidate/stderr.log"

  python3 - "$summary" "$stderr" "$limit" "$REPLAY_PROBE_MAX_TASKS" \
    "$baseline_digest" "$candidate_digest" "$digest_match" \
    "$(wall_seconds "$run_dir/baseline")" "$(wall_seconds "$run_dir/candidate")" <<'PY'
import sys
from pathlib import Path

summary = Path(sys.argv[1])
stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
limit = int(sys.argv[3])
probe = int(sys.argv[4])
baseline_digest = sys.argv[5]
candidate_digest = sys.argv[6]
digest_match = int(sys.argv[7])
baseline_wall = float(sys.argv[8])
candidate_wall = float(sys.argv[9])

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key] = value

p = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_"

def metric(name: str) -> str:
    key = p + name
    if key not in bench:
        raise SystemExit(f"missing benchmark metric: {key}")
    return bench[key]

def i(name: str) -> int:
    return int(float(metric(name)))

def f(name: str) -> float:
    return float(metric(name))

total_tasks = i("tasks")
state_machine_tasks = i("score_prepass_state_machine_shadow_tasks")
scoreinfos = i("score_prepass_state_machine_shadow_candidate_coverage_scoreinfos")
attempts = i("score_prepass_state_machine_shadow_candidate_coverage_attempts")
candidate_attempts = i("score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts")
selected = i("score_prepass_state_machine_shadow_candidate_coverage_selected")
covered = i("score_prepass_state_machine_shadow_candidate_coverage_covered")
false_negative = i("score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos")
candidate_align_attempts = i("score_prepass_state_machine_shadow_candidate_coverage_candidate_align_attempts")
reference_align_attempts = i("score_prepass_state_machine_shadow_candidate_coverage_reference_align_attempts")
realpath_align_attempts = i("realpath_extend_align_attempts")
candidate_align_seconds = f("score_prepass_state_machine_shadow_candidate_coverage_candidate_align_seconds")
reference_align_seconds = f("score_prepass_state_machine_shadow_candidate_coverage_reference_align_seconds")
realpath_align_seconds = f("realpath_extend_align_seconds")
state_machine_total = f("score_prepass_state_machine_shadow_total_seconds")
realpath_extend_seconds = f("realpath_extend_seconds")
triplex_mismatches = i("score_prepass_state_machine_shadow_triplex_mismatches")
scoreinfo_mismatches = i("scoreinfo_mismatches")
realpath_fallbacks = i("realpath_fallbacks")
state_machine_fallbacks = i("score_prepass_state_machine_shadow_fallbacks")

same_scope_reduction = reference_align_attempts - candidate_align_attempts
same_scope_ratio = (candidate_align_attempts / reference_align_attempts) if reference_align_attempts else 0.0
candidate_vs_baseline = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0

decision = "coverage_candidate_go"
if (
    digest_match != 1 or
    scoreinfo_mismatches != 0 or
    realpath_fallbacks != 0 or
    state_machine_fallbacks != 0 or
    triplex_mismatches != 0 or
    false_negative != 0 or
    covered != selected or
    same_scope_reduction <= 0
):
    decision = "coverage_candidate_no_go"

fields = [
    "neat1",
    str(limit),
    str(probe),
    str(digest_match),
    baseline_digest,
    candidate_digest,
    str(total_tasks),
    str(state_machine_tasks),
    str(scoreinfos),
    str(attempts),
    str(candidate_attempts),
    str(selected),
    str(covered),
    str(false_negative),
    str(candidate_align_attempts),
    str(reference_align_attempts),
    str(same_scope_reduction),
    f"{same_scope_ratio:.6f}",
    f"{candidate_align_seconds:.6f}",
    f"{reference_align_seconds:.6f}",
    str(realpath_align_attempts),
    f"{realpath_align_seconds:.6f}",
    f"{state_machine_total:.6f}",
    f"{realpath_extend_seconds:.6f}",
    str(triplex_mismatches),
    f"{baseline_wall:.6f}",
    f"{candidate_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    decision,
]
summary.open("a", encoding="utf-8").write("\t".join(fields) + "\n")
PY
}

for limit in $NEAT1_RECORD_LIMITS; do
  run_case "$limit"
done

python3 - "$summary" "$report" <<'PY'
import csv
import json
import sys
from pathlib import Path

summary = Path(sys.argv[1])
report = Path(sys.argv[2])
rows = list(csv.DictReader(summary.open(encoding="utf-8"), delimiter="\t"))
if not rows:
    raise SystemExit("empty candidate coverage characterization summary")

decisions = {row["decision"] for row in rows}
false_negatives = sum(int(row["false_negative_scoreinfos"]) for row in rows)
covered = sum(int(row["covered"]) for row in rows)
selected = sum(int(row["selected"]) for row in rows)
candidate_align = sum(int(row["candidate_align_attempts"]) for row in rows)
reference_align = sum(int(row["candidate_coverage_reference_align_attempts"]) for row in rows)
realpath_align = sum(int(row["realpath_extend_align_attempts"]) for row in rows)
payload = {
    "decision": "coverage_candidate_go" if decisions == {"coverage_candidate_go"} else "coverage_candidate_no_go",
    "rows": rows,
    "row_count": len(rows),
    "false_negative_scoreinfos": false_negatives,
    "candidate_coverage_covered": covered,
    "candidate_coverage_selected": selected,
    "candidate_coverage_exact": false_negatives == 0 and covered == selected,
    "candidate_align_attempts": candidate_align,
    "candidate_coverage_reference_align_attempts": reference_align,
    "realpath_extend_align_attempts": realpath_align,
    "same_scope_cpu_align_reduction": reference_align - candidate_align,
    "same_scope_cpu_align_reduction_ratio": (candidate_align / reference_align) if reference_align else 0.0,
}
report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("report=" + str(report))
print("decision=" + payload["decision"])
print("false_negative_scoreinfos=" + str(false_negatives))
print("candidate_coverage_covered=" + str(covered))
print("candidate_coverage_selected=" + str(selected))
print("candidate_align_attempts=" + str(candidate_align))
print("candidate_coverage_reference_align_attempts=" + str(reference_align))
print("realpath_extend_align_attempts=" + str(realpath_align))
print("same_scope_cpu_align_reduction_ratio=" + f"{payload['same_scope_cpu_align_reduction_ratio']:.6f}")
PY

cat "$summary"
