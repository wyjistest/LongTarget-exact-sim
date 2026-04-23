#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage: scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir DIR \
  [--case CASE_ID ... | --case-list PATH] \
  --workload-id ID \
  --benchmark-stderr PATH \
  --output-dir DIR \
  [--profile-binary PATH] \
  [--profile-mode coarse|terminal|lexical_first_half|lexical_first_half_count_only|lexical_first_half_sampled|lexical_first_half_sampled_no_terminal_telemetry|lexical_first_half_sampled_no_state_update_bookkeeping] \
  [--terminal-telemetry-overhead auto|on|off] \
  [--profile-sample-log2 N] \
  [--warmup-iterations N] \
  [--iterations N] \
  [--verify]
EOF
}

die() {
  echo "$*" >&2
  exit 1
}

PROFILE_BINARY="tests/sim_initial_host_merge_context_apply_profile"
CORPUS_DIR=""
WORKLOAD_ID=""
BENCHMARK_STDERR=""
OUTPUT_DIR=""
WARMUP_ITERATIONS="1"
ITERATIONS="3"
VERIFY=0
PROFILE_MODE=""
PROFILE_SAMPLE_LOG2=""
TERMINAL_TELEMETRY_OVERHEAD_MODE=""

declare -a CASE_IDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --corpus-dir)
      CORPUS_DIR="$2"
      shift 2
      ;;
    --case)
      CASE_IDS+=("$2")
      shift 2
      ;;
    --case-list)
      while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
        [[ -z "$line" ]] && continue
        CASE_IDS+=("$line")
      done <"$2"
      shift 2
      ;;
    --workload-id)
      WORKLOAD_ID="$2"
      shift 2
      ;;
    --benchmark-stderr)
      BENCHMARK_STDERR="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --profile-binary)
      PROFILE_BINARY="$2"
      shift 2
      ;;
    --profile-mode)
      PROFILE_MODE="$2"
      shift 2
      ;;
    --profile-sample-log2)
      PROFILE_SAMPLE_LOG2="$2"
      shift 2
      ;;
    --terminal-telemetry-overhead)
      TERMINAL_TELEMETRY_OVERHEAD_MODE="$2"
      shift 2
      ;;
    --warmup-iterations)
      WARMUP_ITERATIONS="$2"
      shift 2
      ;;
    --iterations)
      ITERATIONS="$2"
      shift 2
      ;;
    --verify)
      VERIFY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$CORPUS_DIR" ]] || { usage >&2; die "--corpus-dir is required"; }
[[ -n "$WORKLOAD_ID" ]] || { usage >&2; die "--workload-id is required"; }
[[ -n "$BENCHMARK_STDERR" ]] || { usage >&2; die "--benchmark-stderr is required"; }
[[ -n "$OUTPUT_DIR" ]] || { usage >&2; die "--output-dir is required"; }
[[ ${#CASE_IDS[@]} -gt 0 ]] || { usage >&2; die "at least one --case or --case-list entry is required"; }

[[ -d "$CORPUS_DIR" ]] || die "corpus dir not found: $CORPUS_DIR"
[[ -x "$PROFILE_BINARY" ]] || die "profile binary not found or not executable: $PROFILE_BINARY"
[[ -f "$BENCHMARK_STDERR" ]] || die "benchmark stderr not found: $BENCHMARK_STDERR"
[[ -s "$BENCHMARK_STDERR" ]] || die "benchmark stderr is empty: $BENCHMARK_STDERR"

for required_line in \
  'benchmark.sim_initial_scan_seconds=' \
  'benchmark.sim_initial_scan_cpu_merge_seconds=' \
  'benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=' \
  'benchmark.sim_seconds=' \
  'benchmark.total_seconds='
do
  grep -q "$required_line" "$BENCHMARK_STDERR" || die "benchmark stderr missing required metric '$required_line': $BENCHMARK_STDERR"
done

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd)
CASES_DIR="$OUTPUT_DIR/cases"
mkdir -p "$CASES_DIR"

COPIED_BENCHMARK="$OUTPUT_DIR/full_run.stderr.log"
SOURCE_BENCHMARK_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$BENCHMARK_STDERR")
COPIED_BENCHMARK_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$COPIED_BENCHMARK")
if [[ "$SOURCE_BENCHMARK_REAL" != "$COPIED_BENCHMARK_REAL" ]]; then
  cp "$BENCHMARK_STDERR" "$COPIED_BENCHMARK"
fi
[[ -s "$COPIED_BENCHMARK" ]] || die "copied benchmark stderr is empty: $COPIED_BENCHMARK"
BENCHMARK_SOURCE_SHA256=$(sha256sum "$COPIED_BENCHMARK" | awk '{print $1}')
BENCHMARK_SOURCE_SIZE_BYTES=$(wc -c <"$COPIED_BENCHMARK" | tr -d '[:space:]')
BENCHMARK_IDENTITY_BASIS="content_sha256"

SELECTED_CASE_IDS="$OUTPUT_DIR/selected_case_ids.txt"
printf '%s\n' "${CASE_IDS[@]}" >"$SELECTED_CASE_IDS"

validate_aggregate() {
  local aggregate_tsv="$1"
  local expected_case_id="$2"
  python3 - "$aggregate_tsv" "$expected_case_id" "$WORKLOAD_ID" "$COPIED_BENCHMARK" "$SOURCE_BENCHMARK_REAL" "$BENCHMARK_SOURCE_SHA256" "$BENCHMARK_SOURCE_SIZE_BYTES" "$BENCHMARK_IDENTITY_BASIS" <<'PY'
import csv
import sys
from pathlib import Path

aggregate_tsv = Path(sys.argv[1])
expected_case_id = sys.argv[2]
expected_workload_id = sys.argv[3]
expected_benchmark_source = sys.argv[4]
expected_original_source = sys.argv[5]
expected_benchmark_sha256 = sys.argv[6]
expected_benchmark_size_bytes = sys.argv[7]
expected_benchmark_identity_basis = sys.argv[8]

if not aggregate_tsv.is_file():
    raise SystemExit(f"missing aggregate TSV: {aggregate_tsv}")

with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

if len(rows) != 1:
    raise SystemExit(f"{aggregate_tsv}: expected exactly one row, found {len(rows)}")

row = rows[0]
required_fields = [
    "case_id",
    "workload_id",
    "benchmark_source",
    "benchmark_source_original_path",
    "benchmark_source_copied_path",
    "benchmark_source_sha256",
    "benchmark_source_size_bytes",
    "benchmark_identity_basis",
    "sim_initial_scan_seconds_mean_seconds",
    "sim_initial_scan_cpu_merge_seconds_mean_seconds",
    "sim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
]
for field in required_fields:
    if field not in row:
        raise SystemExit(f"{aggregate_tsv}: missing field {field}")
    if row[field] == "":
        raise SystemExit(f"{aggregate_tsv}: empty field {field}")

if row["case_id"] != expected_case_id:
    raise SystemExit(f"{aggregate_tsv}: expected case_id={expected_case_id}, got {row['case_id']}")
if row["workload_id"] != expected_workload_id:
    raise SystemExit(f"{aggregate_tsv}: expected workload_id={expected_workload_id}, got {row['workload_id']}")
if row["benchmark_source"] != expected_benchmark_source:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_source={expected_benchmark_source}, got {row['benchmark_source']}"
    )
if row["benchmark_source_original_path"] != expected_original_source:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_source_original_path={expected_original_source}, got {row['benchmark_source_original_path']}"
    )
if row["benchmark_source_copied_path"] != expected_benchmark_source:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_source_copied_path={expected_benchmark_source}, got {row['benchmark_source_copied_path']}"
    )
if row["benchmark_source_sha256"] != expected_benchmark_sha256:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_source_sha256={expected_benchmark_sha256}, got {row['benchmark_source_sha256']}"
    )
if row["benchmark_source_size_bytes"] != expected_benchmark_size_bytes:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_source_size_bytes={expected_benchmark_size_bytes}, got {row['benchmark_source_size_bytes']}"
    )
if row["benchmark_identity_basis"] != expected_benchmark_identity_basis:
    raise SystemExit(
        f"{aggregate_tsv}: expected benchmark_identity_basis={expected_benchmark_identity_basis}, got {row['benchmark_identity_basis']}"
    )

for field in [
    "sim_initial_scan_seconds_mean_seconds",
    "sim_initial_scan_cpu_merge_seconds_mean_seconds",
    "sim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
]:
    value = float(row[field])
    if value <= 0:
        raise SystemExit(f"{aggregate_tsv}: non-positive benchmark metric {field}={value}")
PY
}

declare -a AGGREGATE_ARGS=()

for case_id in "${CASE_IDS[@]}"; do
  aggregate_tsv="$CASES_DIR/${case_id}.aggregate.tsv"
  context_tsv="$CASES_DIR/${case_id}.context.tsv"
  cmd=(
    "$PROFILE_BINARY"
    --corpus-dir "$CORPUS_DIR"
    --case "$case_id"
    --output-tsv "$context_tsv"
    --aggregate-tsv "$aggregate_tsv"
    --benchmark-stderr "$COPIED_BENCHMARK"
    --workload-id "$WORKLOAD_ID"
    --warmup-iterations "$WARMUP_ITERATIONS"
    --iterations "$ITERATIONS"
  )
  if [[ "$VERIFY" == "1" ]]; then
    cmd+=(--verify)
  fi
  if [[ -n "$PROFILE_MODE" ]]; then
    cmd+=(--profile-mode "$PROFILE_MODE")
  fi
  if [[ -n "$PROFILE_SAMPLE_LOG2" ]]; then
    cmd+=(--profile-sample-log2 "$PROFILE_SAMPLE_LOG2")
  fi
  if [[ -n "$TERMINAL_TELEMETRY_OVERHEAD_MODE" ]]; then
    cmd+=(--terminal-telemetry-overhead "$TERMINAL_TELEMETRY_OVERHEAD_MODE")
  fi
  cmd+=(
    --benchmark-source-original-path "$SOURCE_BENCHMARK_REAL"
    --benchmark-source-copied-path "$COPIED_BENCHMARK"
    --benchmark-source-sha256 "$BENCHMARK_SOURCE_SHA256"
    --benchmark-source-size-bytes "$BENCHMARK_SOURCE_SIZE_BYTES"
    --benchmark-identity-basis "$BENCHMARK_IDENTITY_BASIS"
  )
  "${cmd[@]}"
  validate_aggregate "$aggregate_tsv" "$case_id"
  AGGREGATE_ARGS+=(--aggregate-tsv "$aggregate_tsv")
done

MIN_DIR="$OUTPUT_DIR/min_maintenance_profile"
CANDIDATE_DIR="$OUTPUT_DIR/candidate_index_lifecycle"

python3 scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py \
  "${AGGREGATE_ARGS[@]}" \
  --output-dir "$MIN_DIR"

python3 scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py \
  "${AGGREGATE_ARGS[@]}" \
  --output-dir "$CANDIDATE_DIR"
