#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/phase7_gasal2_long_query_integrated"}"
RUNNER="${RUNNER:-"$ROOT/scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh"}"
COMPARATOR="${COMPARATOR:-"$ROOT/scripts/compare_fasim_gasal2_long_query_integrated.py"}"
SUMMARIZER="${SUMMARIZER:-"$ROOT/scripts/summarize_fasim_gasal2_long_query_integrated.py"}"
KCNQ1OT1_FASTA="${KCNQ1OT1_FASTA:-"$ROOT/.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa"}"
H19_FASTA="${H19_FASTA:-"$ROOT/H19.fa"}"
SMALL_TARGET="${SMALL_TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
FULL_TARGET="${FULL_TARGET:-"$ROOT/.tmp/gasal2_hg38_archive_first_run/shards/chr22.fa"}"
SEGMENT_LEN="${SEGMENT_LEN:-2048}"
SEGMENT_OVERLAP="${SEGMENT_OVERLAP:-512}"
GRID_SHIFTS="${GRID_SHIFTS:-0 256}"
MAX8_REPEATS="${MAX8_REPEATS:-2}"
RUN_SMALL="${RUN_SMALL:-1}"
RUN_MAX4="${RUN_MAX4:-1}"
RUN_MAX8="${RUN_MAX8:-1}"
RUN_H19_SHORT="${RUN_H19_SHORT:-1}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

for boolean_name in RUN_SMALL RUN_MAX4 RUN_MAX8 RUN_H19_SHORT; do
  value="${!boolean_name}"
  if [[ "$value" != "0" && "$value" != "1" ]]; then
    echo "$boolean_name must be 0 or 1" >&2
    exit 1
  fi
done
if (( MAX8_REPEATS < 2 )); then
  echo "MAX8_REPEATS must be at least 2 for the full-run gate" >&2
  exit 1
fi
for path in \
  "$BIN" "$RUNNER" "$COMPARATOR" "$SUMMARIZER" \
  "$KCNQ1OT1_FASTA" "$H19_FASTA" "$SMALL_TARGET" "$FULL_TARGET"; do
  if [[ ! -e "$path" ]]; then
    echo "missing Phase 7 dependency: $path" >&2
    exit 1
  fi
done

mkdir -p "$WORK/runs" "$WORK/pairs"

run_mode() {
  local workload="$1"
  local repeat="$2"
  local mode="$3"
  local target="$4"
  local query="$5"
  local segment_len="$6"
  local segment_overlap="$7"
  local max_segments="$8"
  local exact=0
  if [[ "$mode" == "candidate" ]]; then
    exact=1
  elif [[ "$mode" != "baseline" ]]; then
    echo "unknown integrated mode: $mode" >&2
    return 1
  fi
  local run_root="$WORK/runs/${workload}/repeat_${repeat}/${mode}"
  mkdir -p "$run_root"
  env \
    CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    BIN="$BIN" \
    WORK="$run_root" \
    TARGET="$target" \
    RNA="$query" \
    KCNQ1OT1_FASTA="$query" \
    SEGMENT_LEN="$segment_len" \
    SEGMENT_OVERLAP="$segment_overlap" \
    GRID_SHIFTS="$GRID_SHIFTS" \
    MAX_SEGMENTS="$max_segments" \
    RESUME=1 \
    EXACT_SCOREINFO_PRUNED="$exact" \
    FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=0 \
    MERGE_DEDUP_BACKEND=sqlite \
    CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE=0 \
    bash "$RUNNER" \
    >"$run_root/runner.stdout.log" \
    2>"$run_root/runner.stderr.log"
}

compare_pair() {
  local workload="$1"
  local repeat="$2"
  local pair_root="$WORK/pairs/${workload}/repeat_${repeat}"
  mkdir -p "$pair_root"
  python3 "$COMPARATOR" \
    --workload "$workload" \
    --repeat "$repeat" \
    --baseline-root "$WORK/runs/${workload}/repeat_${repeat}/baseline" \
    --candidate-root "$WORK/runs/${workload}/repeat_${repeat}/candidate" \
    --work-dir "$pair_root/contracts" \
    --output "$pair_root/pair.tsv" \
    >"$pair_root/compare.stdout.log" \
    2>"$pair_root/compare.stderr.log"
}

run_pair() {
  local workload="$1"
  local repeat="$2"
  local target="$3"
  local query="$4"
  local segment_len="$5"
  local segment_overlap="$6"
  local max_segments="$7"
  if (( repeat % 2 == 1 )); then
    run_mode "$workload" "$repeat" baseline "$target" "$query" \
      "$segment_len" "$segment_overlap" "$max_segments"
    run_mode "$workload" "$repeat" candidate "$target" "$query" \
      "$segment_len" "$segment_overlap" "$max_segments"
  else
    run_mode "$workload" "$repeat" candidate "$target" "$query" \
      "$segment_len" "$segment_overlap" "$max_segments"
    run_mode "$workload" "$repeat" baseline "$target" "$query" \
      "$segment_len" "$segment_overlap" "$max_segments"
  fi
  compare_pair "$workload" "$repeat"
}

rebuild_pair_matrix() {
  local first=1
  local matrix="$WORK/pairs.tsv"
  local pair
  : >"$matrix"
  while IFS= read -r pair; do
    if (( first )); then
      cat "$pair" >>"$matrix"
      first=0
    else
      tail -n +2 "$pair" >>"$matrix"
    fi
  done < <(find "$WORK/pairs" -type f -name pair.tsv | sort)
  if (( first )); then
    echo "no integrated pair receipts found" >&2
    return 1
  fi
}

if [[ "$RUN_SMALL" == "1" ]]; then
  run_pair small 1 "$SMALL_TARGET" "$KCNQ1OT1_FASTA" \
    "$SEGMENT_LEN" "$SEGMENT_OVERLAP" 2
fi

if [[ "$RUN_H19_SHORT" == "1" ]]; then
  run_pair h19_short 1 "$SMALL_TARGET" "$H19_FASTA" 2812 512 0
fi

if [[ "$RUN_MAX4" == "1" ]]; then
  run_pair max4 1 "$FULL_TARGET" "$KCNQ1OT1_FASTA" \
    "$SEGMENT_LEN" "$SEGMENT_OVERLAP" 4
fi

if [[ "$RUN_MAX8" == "1" ]]; then
  for repeat in $(seq 1 "$MAX8_REPEATS"); do
    run_pair max8 "$repeat" "$FULL_TARGET" "$KCNQ1OT1_FASTA" \
      "$SEGMENT_LEN" "$SEGMENT_OVERLAP" 8
  done
fi

rebuild_pair_matrix
python3 "$SUMMARIZER" \
  --pairs "$WORK/pairs.tsv" \
  --details "$WORK/bounded-benchmark.tsv" \
  --summary "$WORK/bounded-summary.txt" \
  >"$WORK/summarize.stdout.log" \
  2>"$WORK/summarize.stderr.log"

cat "$WORK/bounded-summary.txt"
