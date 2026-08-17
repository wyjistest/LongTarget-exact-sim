#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_exact_column_long_query_exact_pruned"}"
TARGET="${TARGET:-"$ROOT/.tmp/gasal2_hg38_archive_first_run/shards/chr22.fa"}"
KCNQ1OT1_FASTA="${KCNQ1OT1_FASTA:-"$ROOT/.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa"}"
QUERY_FASTA="${QUERY_FASTA:-}"
REPEATS="${REPEATS:-3}"
RULE="${RULE:-0}"
SEGMENT_LEN="${SEGMENT_LEN:-2048}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
BUILD_BIN="${BUILD_BIN:-1}"

if (( REPEATS < 1 )); then
  echo "REPEATS must be >= 1" >&2
  exit 1
fi
if (( SEGMENT_LEN <= 0 || SEGMENT_LEN > 2812 )); then
  echo "SEGMENT_LEN must be in 1..2812" >&2
  exit 1
fi
query_source="$KCNQ1OT1_FASTA"
if [[ -n "$QUERY_FASTA" ]]; then
  query_source="$QUERY_FASTA"
fi
for path in "$TARGET" "$query_source"; do
  if [[ ! -s "$path" ]]; then
    echo "missing benchmark dependency: $path" >&2
    exit 1
  fi
done
if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2 binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

RNA="$WORK/inputs/kcnq1ot1_segment_000.fa"
if [[ -n "$QUERY_FASTA" ]]; then
  RNA="$QUERY_FASTA"
else
python3 - "$KCNQ1OT1_FASTA" "$RNA" "$SEGMENT_LEN" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1])
output = Path(sys.argv[2])
segment_len = int(sys.argv[3])
header = ""
parts: list[str] = []
for raw in source.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line:
        continue
    if line.startswith(">"):
        if not header:
            header = line[1:].split()[0]
    else:
        parts.append(line)
sequence = "".join(parts).upper()
if len(sequence) < segment_len:
    raise SystemExit(f"query has {len(sequence)} bp; need {segment_len}")
segment = sequence[:segment_len]
with output.open("w", encoding="utf-8") as handle:
    handle.write(
        f">{header or source.stem}|segment_id=0|grid_shift=0|"
        f"global_query_start=0|global_query_end={segment_len}\n"
    )
    for start in range(0, len(segment), 80):
        handle.write(segment[start : start + 80] + "\n")
PY
fi

query_len="$(awk '!/^>/ {gsub(/[[:space:]]/, ""); n += length($0)} END {print n + 0}' "$RNA")"
if (( query_len <= 0 || query_len > 2812 )); then
  echo "benchmark query length must be in 1..2812; got $query_len" >&2
  exit 1
fi
effective_segment_len="$SEGMENT_LEN"
query_mode="segmented"
if [[ -n "$QUERY_FASTA" ]]; then
  effective_segment_len="$query_len"
  query_mode="provided_full_query"
fi

run_one() {
  local mode="$1"
  local repeat="$2"
  local out_dir="$WORK/$mode/run_$repeat"
  local candidate_env=()
  if [[ "$mode" == "candidate" ]]; then
    candidate_env+=(
      FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
      FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK"
      FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
    )
  fi
  mkdir -p "$out_dir"
  /usr/bin/time -f '%e' -o "$out_dir/wall_seconds.txt" \
    env \
      FASIM_OUTPUT_MODE=tfosorted \
      FASIM_VERBOSE=0 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
      FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
      FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1 \
      "${candidate_env[@]}" \
      "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"

  local -a archives=()
  mapfile -t archives < <(find "$out_dir" -maxdepth 1 -type f -name '*.archive-first.tfoa' | sort)
  if (( ${#archives[@]} != 1 )); then
    echo "expected one archive-first output in $out_dir; found ${#archives[@]}" >&2
    exit 1
  fi
  sha256sum "${archives[0]}" | awk '{print $1}' >"$out_dir/output.sha256"
}

for repeat in $(seq 1 "$REPEATS"); do
  if (( repeat % 2 == 1 )); then
    run_one baseline "$repeat"
    run_one candidate "$repeat"
  else
    run_one candidate "$repeat"
    run_one baseline "$repeat"
  fi
done

python3 "$ROOT/scripts/summarize_fasim_gasal2_exact_column_benchmark.py" \
  --baseline-root "$WORK/baseline" \
  --candidate-root "$WORK/candidate" \
  --details "$WORK/details.tsv" \
  --summary "$WORK/summary.txt"

{
  printf 'target=%s\n' "$TARGET"
  printf 'target_sha256=%s\n' "$(sha256sum "$TARGET" | awk '{print $1}')"
  printf 'query_source=%s\n' "$query_source"
  printf 'query_source_sha256=%s\n' "$(sha256sum "$query_source" | awk '{print $1}')"
  printf 'query_segment=%s\n' "$RNA"
  printf 'query_segment_sha256=%s\n' "$(sha256sum "$RNA" | awk '{print $1}')"
  printf 'query_mode=%s\n' "$query_mode"
  printf 'query_len=%s\n' "$query_len"
  printf 'segment_len=%s\n' "$effective_segment_len"
  printf 'rule=%s\n' "$RULE"
  printf 'repeats=%s\n' "$REPEATS"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  printf 'exact_scoreinfo_gpu_max_per_task=%s\n' "$EXACT_SCOREINFO_GPU_MAX_PER_TASK"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'baseline_kernel_variant=column_maxima_cpu_scoreinfo\n'
  printf 'candidate_kernel_variant=legacy_minscore_gpu_pruned_scoreinfo\n'
} >"$WORK/manifest.txt"

cat "$WORK/manifest.txt"
cat "$WORK/summary.txt"
