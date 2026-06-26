#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
KCNQ1OT1_FASTA="${KCNQ1OT1_FASTA:-"$ROOT/.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa"}"
RNA="${RNA:-"$KCNQ1OT1_FASTA"}"
RULE="${RULE:-0}"
SEGMENT_LEN="${SEGMENT_LEN:-2048}"
SEGMENT_OVERLAP="${SEGMENT_OVERLAP:-512}"
GRID_SHIFTS="${GRID_SHIFTS:-0 256}"
MAX_SEGMENTS="${MAX_SEGMENTS:-4}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"

MERGE_SCRIPT="$ROOT/scripts/merge_fasim_segmented_tfosorted.py"
CLUSTER_COMPARE="$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$MERGE_SCRIPT" "$CLUSTER_COMPARE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

if (( SEGMENT_LEN <= 0 )); then
  echo "SEGMENT_LEN must be positive" >&2
  exit 1
fi
if (( SEGMENT_OVERLAP < 0 || SEGMENT_OVERLAP >= SEGMENT_LEN )); then
  echo "SEGMENT_OVERLAP must be >=0 and < SEGMENT_LEN" >&2
  exit 1
fi
if (( SEGMENT_LEN > 2812 )); then
  echo "SEGMENT_LEN exceeds current verified GASAL2 query contract" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/grids"

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

find_tfosorted_output() {
  local dir="$1"
  find "$dir" -maxdepth 1 -type f -name '*-TFOsorted' | sort | head -n 1
}

run_gasal2_tfosorted() {
  local query="$1"
  local out_dir="$2"
  env \
    FASIM_OUTPUT_MODE=tfosorted \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    "$BIN" -f1 "$TARGET" -f2 "$query" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

python3 - "$RNA" "$WORK/grids" "$SEGMENT_LEN" "$SEGMENT_OVERLAP" "$GRID_SHIFTS" "$MAX_SEGMENTS" <<'PY' >"$WORK/window_summary.txt"
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

rna = Path(sys.argv[1])
grids_dir = Path(sys.argv[2])
segment_len = int(sys.argv[3])
segment_overlap = int(sys.argv[4])
grid_shifts = [int(value) for value in sys.argv[5].split() if value]
max_segments = int(sys.argv[6])
step = segment_len - segment_overlap

header = ""
seq_parts: list[str] = []
with rna.open(encoding="utf-8", errors="replace") as handle:
    for raw in handle:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if not header:
                header = line[1:].split()[0]
        else:
            seq_parts.append(line)
sequence = "".join(seq_parts).upper()
query_len = len(sequence)
if query_len == 0:
    raise SystemExit(f"empty query FASTA: {rna}")
if not grid_shifts:
    raise SystemExit("at least one grid shift is required")

def grid_starts(shift: int) -> list[int]:
    max_start = max(query_len - segment_len, 0)
    if max_segments <= 0:
        starts: list[int] = []
        start = min(max(shift, 0), max_start)
        if start != 0:
            starts.append(0)
        while start <= max_start:
            starts.append(start)
            next_start = start + step
            if next_start > max_start and start != max_start:
                starts.append(max_start)
                break
            if next_start <= start:
                break
            start = next_start
        return sorted(set(starts))

    center_start = max(0, min((query_len - segment_len) // 2, max_start))
    anchor = int(round((center_start - shift) / step)) * step + shift
    half_left = max_segments // 2
    starts = [anchor + (idx - half_left) * step for idx in range(max_segments)]
    starts = [max(0, min(start, max_start)) for start in starts]
    return sorted(set(starts))

grid_ranges: list[tuple[int, int]] = []
for shift in grid_shifts:
    starts = grid_starts(shift)
    if not starts:
        raise SystemExit(f"no starts for shift {shift}")
    grid_dir = grids_dir / f"shift_{shift}"
    grid_dir.mkdir(parents=True, exist_ok=True)
    manifest = grid_dir / "segments.tsv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["segment_id", "global_start", "global_end", "query_len", "fasta", "tfosorted"])
        for idx, start in enumerate(starts):
            end = min(start + segment_len, query_len)
            seq = sequence[start:end]
            fasta = grid_dir / f"segment_{idx:03d}.fa"
            with fasta.open("w", encoding="utf-8") as out:
                out.write(
                    f">{header or rna.stem}|segment_id={idx}|grid_shift={shift}|"
                    f"global_query_start={start}|global_query_end={end}\n"
                )
                for pos in range(0, len(seq), 80):
                    out.write(seq[pos:pos + 80] + "\n")
            writer.writerow([idx, start, end, len(seq), fasta, ""])
    grid_ranges.append((min(starts), max(start + segment_len for start in starts)))
    print(f"grid_shift_{shift}_segment_count={len(starts)}")
    print(f"grid_shift_{shift}_range_start={min(starts)}")
    print(f"grid_shift_{shift}_range_end={max(start + segment_len for start in starts)}")
    print(f"grid_shift_{shift}_manifest={manifest}")

common_start = max(start for start, _ in grid_ranges)
common_end = min(end for _, end in grid_ranges)
if common_start >= common_end:
    raise SystemExit(f"empty common grid coverage: {common_start}-{common_end}")

print(f"query_len={query_len}")
print(f"segment_len={segment_len}")
print(f"segment_overlap={segment_overlap}")
print(f"grid_shifts={' '.join(str(value) for value in grid_shifts)}")
print(f"max_segments={max_segments}")
print(f"common_query_start={common_start}")
print(f"common_query_end={common_end}")
PY

mapfile -t grid_shifts < <(printf '%s\n' $GRID_SHIFTS)
common_query_start="$(awk -F= '$1=="common_query_start"{print $2}' "$WORK/window_summary.txt")"
common_query_end="$(awk -F= '$1=="common_query_end"{print $2}' "$WORK/window_summary.txt")"
merged_outputs=()
all_stderr_files=()

for shift in "${grid_shifts[@]}"; do
  grid_dir="$WORK/grids/shift_${shift}"
  segments_manifest="$grid_dir/segments.tsv"
  outputs_manifest="$grid_dir/segment_outputs.tsv"
  {
    IFS=$'\t' read -r header_segment_id header_start header_end header_len header_fasta header_tfosorted
    printf '%s\t%s\t%s\t%s\n' "segment_id" "global_start" "global_end" "tfosorted"
    while IFS=$'\t' read -r segment_id global_start global_end query_len fasta ignored_tfosorted; do
      out_dir="$grid_dir/run_${segment_id}"
      mkdir -p "$out_dir"
      segment_start="$(now_seconds)"
      run_gasal2_tfosorted "$fasta" "$out_dir"
      segment_end="$(now_seconds)"
      elapsed_seconds "$segment_start" "$segment_end" >"$out_dir/wall_seconds.txt"
      tfosorted="$(find_tfosorted_output "$out_dir")"
      if [[ -z "$tfosorted" || ! -s "$tfosorted" ]]; then
        echo "missing segment TFOsorted output for shift $shift segment $segment_id" >&2
        exit 1
      fi
      printf '%s\t%s\t%s\t%s\n' "$segment_id" "$global_start" "$global_end" "$tfosorted"
      all_stderr_files+=("$out_dir/stderr.log")
    done
  } <"$segments_manifest" >"$outputs_manifest"

  merged="$grid_dir/merged-common-TFOsorted"
  python3 "$MERGE_SCRIPT" \
    --segments "$outputs_manifest" \
    --query-min "$common_query_start" \
    --query-max "$common_query_end" \
    --output "$merged" \
    >"$grid_dir/merge_summary.txt"
  merged_outputs+=("$merged")
done

if (( ${#merged_outputs[@]} < 2 )); then
  echo "at least two grid shifts are required for stability comparison" >&2
  exit 1
fi

python3 "$CLUSTER_COMPARE" \
  --baseline "${merged_outputs[0]}" \
  --candidate "${merged_outputs[1]}" \
  --k 5 \
  --details "$WORK/offline_cluster_grid_compare_details.tsv" \
  >"$WORK/offline_cluster_grid_compare.txt" || true

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
}

sum_stderr_metric() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key {sum += $2}
    END {printf "%.0f", sum}
  ' "$@"
}

gasal2_requests="$(sum_stderr_metric benchmark.fasim_gasal2_requests "${all_stderr_files[@]}")"
gasal2_traceback_requests="$(sum_stderr_metric benchmark.fasim_gasal2_traceback_requests "${all_stderr_files[@]}")"
gasal2_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_fallbacks "${all_stderr_files[@]}")"
length_guard_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_length_guard_fallbacks "${all_stderr_files[@]}")"
cluster_equal="$(metric_or_default "$WORK/offline_cluster_grid_compare.txt" top5_offline_cluster_equal false)"
cluster_overlap="$(metric_or_default "$WORK/offline_cluster_grid_compare.txt" top5_offline_cluster_overlap 0)"

decision="segmented_query_kcnq1ot1_pilot_incomplete"
if [[ "$cluster_equal" == "true" && "$gasal2_fallbacks" == "0" && "$length_guard_fallbacks" == "0" ]]; then
  decision="segmented_query_kcnq1ot1_pilot_grid_stable"
fi

{
  cat "$WORK/window_summary.txt"
  for shift in "${grid_shifts[@]}"; do
    sed "s/^/shift_${shift}_/" "$WORK/grids/shift_${shift}/merge_summary.txt"
  done
  printf 'gasal2_requests=%s\n' "$gasal2_requests"
  printf 'gasal2_traceback_requests=%s\n' "$gasal2_traceback_requests"
  printf 'gasal2_fallbacks=%s\n' "$gasal2_fallbacks"
  printf 'length_guard_fallbacks=%s\n' "$length_guard_fallbacks"
  printf 'top5_offline_cluster_equal=%s\n' "$cluster_equal"
  printf 'top5_offline_cluster_overlap=%s\n' "$cluster_overlap"
  printf 'decision=%s\n' "$decision"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
