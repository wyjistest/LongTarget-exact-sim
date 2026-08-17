#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_h19_control"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
SEGMENT_LEN="${SEGMENT_LEN:-2048}"
SEGMENT_OVERLAP="${SEGMENT_OVERLAP:-auto}"
OVERLAP_GUARD="${OVERLAP_GUARD:-32}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"

MERGE_SCRIPT="$ROOT/scripts/merge_fasim_segmented_tfosorted.py"
CLUSTER_COMPARE="$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py"
TFO_COMPARE="$ROOT/scripts/compare_fasim_tfosorted_tfo_contract.py"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$MERGE_SCRIPT" "$CLUSTER_COMPARE" "$TFO_COMPARE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

if (( SEGMENT_LEN <= 0 )); then
  echo "SEGMENT_LEN must be positive" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/unsegmented" "$WORK/segments" "$WORK/merged"

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

unseg_start="$(now_seconds)"
run_gasal2_tfosorted "$RNA" "$WORK/unsegmented"
unseg_end="$(now_seconds)"
unsegmented_wall_seconds="$(elapsed_seconds "$unseg_start" "$unseg_end")"
unsegmented_tfosorted="$(find_tfosorted_output "$WORK/unsegmented")"
if [[ -z "$unsegmented_tfosorted" || ! -s "$unsegmented_tfosorted" ]]; then
  echo "missing unsegmented TFOsorted output" >&2
  exit 1
fi

python3 - "$RNA" "$unsegmented_tfosorted" "$WORK/segments" "$SEGMENT_LEN" "$SEGMENT_OVERLAP" "$OVERLAP_GUARD" <<'PY' >"$WORK/window_summary.txt"
from __future__ import annotations

import csv
import sys
from pathlib import Path

rna = Path(sys.argv[1])
unsegmented = Path(sys.argv[2])
segments_dir = Path(sys.argv[3])
segment_len = int(sys.argv[4])
segment_overlap_arg = sys.argv[5]
overlap_guard = int(sys.argv[6])

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

max_query_span = 0
with unsegmented.open(newline="", encoding="utf-8", errors="replace") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        try:
            span = int(row["QueryEnd"]) - int(row["QueryStart"]) + 1
        except (KeyError, ValueError):
            continue
        max_query_span = max(max_query_span, span)

if segment_overlap_arg == "auto":
    segment_overlap = max(max_query_span - 1 + overlap_guard, 0)
else:
    segment_overlap = int(segment_overlap_arg)
if segment_overlap >= segment_len:
    raise SystemExit(
        f"segment overlap must be smaller than segment length: {segment_overlap} >= {segment_len}"
    )

starts: list[int] = []
if query_len <= segment_len:
    starts = [0]
else:
    step = segment_len - segment_overlap
    start = 0
    while True:
        starts.append(start)
        if start + segment_len >= query_len:
            break
        next_start = start + step
        if next_start + segment_len >= query_len:
            next_start = max(query_len - segment_len, 0)
        if next_start <= start:
            break
        start = next_start

segments_dir.mkdir(parents=True, exist_ok=True)
manifest_path = segments_dir / "segments.tsv"
with manifest_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(["segment_id", "global_start", "global_end", "query_len", "fasta", "tfosorted"])
    for idx, start in enumerate(starts):
        end = min(start + segment_len, query_len)
        segment_seq = sequence[start:end]
        fasta = segments_dir / f"segment_{idx:03d}.fa"
        with fasta.open("w", encoding="utf-8") as out:
            out.write(
                f">{header or rna.stem}|segment_id={idx}|global_query_start={start}|"
                f"global_query_end={end}\n"
            )
            for pos in range(0, len(segment_seq), 80):
                out.write(segment_seq[pos:pos + 80] + "\n")
        writer.writerow([idx, start, end, len(segment_seq), fasta, ""])

actual_overlaps = []
for left, right in zip(starts, starts[1:]):
    actual_overlaps.append(max(0, left + segment_len - right))

print(f"query_len={query_len}")
print(f"segment_len={segment_len}")
print(f"max_query_span={max_query_span}")
print(f"overlap_guard={overlap_guard}")
print(f"segment_overlap={segment_overlap}")
print(f"segment_count={len(starts)}")
print(f"actual_overlap_min={min(actual_overlaps) if actual_overlaps else 0}")
print(f"actual_overlap_max={max(actual_overlaps) if actual_overlaps else 0}")
print(f"manifest={manifest_path}")
PY

segments_manifest="$WORK/segments/segments.tsv"
segment_outputs_manifest="$WORK/segments/segment_outputs.tsv"
{
  IFS=$'\t' read -r header_segment_id header_start header_end header_len header_fasta header_tfosorted
  printf '%s\t%s\t%s\t%s\n' "segment_id" "global_start" "global_end" "tfosorted"
  while IFS=$'\t' read -r segment_id global_start global_end query_len fasta ignored_tfosorted; do
    out_dir="$WORK/segments/run_${segment_id}"
    mkdir -p "$out_dir"
    segment_start="$(now_seconds)"
    run_gasal2_tfosorted "$fasta" "$out_dir"
    segment_end="$(now_seconds)"
    elapsed_seconds "$segment_start" "$segment_end" >"$out_dir/wall_seconds.txt"
    tfosorted="$(find_tfosorted_output "$out_dir")"
    if [[ -z "$tfosorted" || ! -s "$tfosorted" ]]; then
      echo "missing segment TFOsorted output for segment $segment_id" >&2
      exit 1
    fi
    printf '%s\t%s\t%s\t%s\n' "$segment_id" "$global_start" "$global_end" "$tfosorted"
  done
} <"$segments_manifest" >"$segment_outputs_manifest"

python3 "$MERGE_SCRIPT" \
  --segments "$segment_outputs_manifest" \
  --output "$WORK/merged/segmented-global-TFOsorted" \
  >"$WORK/merge_summary.txt"

python3 "$CLUSTER_COMPARE" \
  --baseline "$unsegmented_tfosorted" \
  --candidate "$WORK/merged/segmented-global-TFOsorted" \
  --k 5 \
  --details "$WORK/offline_cluster_top5_details.tsv" \
  >"$WORK/offline_cluster_compare.txt" || true

python3 "$TFO_COMPARE" \
  --baseline "$unsegmented_tfosorted" \
  --candidate "$WORK/merged/segmented-global-TFOsorted" \
  >"$WORK/tfo_contract_compare.txt"

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

segment_stderr_files=("$WORK"/segments/run_*/stderr.log)
gasal2_requests="$(sum_stderr_metric benchmark.fasim_gasal2_requests "$WORK/unsegmented/stderr.log" "${segment_stderr_files[@]}")"
gasal2_traceback_requests="$(sum_stderr_metric benchmark.fasim_gasal2_traceback_requests "$WORK/unsegmented/stderr.log" "${segment_stderr_files[@]}")"
gasal2_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_fallbacks "$WORK/unsegmented/stderr.log" "${segment_stderr_files[@]}")"
length_guard_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_length_guard_fallbacks "$WORK/unsegmented/stderr.log" "${segment_stderr_files[@]}")"

cluster_equal="$(metric_or_default "$WORK/offline_cluster_compare.txt" top5_offline_cluster_equal false)"
cluster_overlap="$(metric_or_default "$WORK/offline_cluster_compare.txt" top5_offline_cluster_overlap 0)"

decision="segmented_query_h19_control_incomplete"
if [[ "$cluster_equal" == "true" && "$gasal2_fallbacks" == "0" && "$length_guard_fallbacks" == "0" ]]; then
  decision="segmented_query_h19_control_clean"
fi

{
  cat "$WORK/window_summary.txt"
  printf 'unsegmented_wall_seconds=%s\n' "$unsegmented_wall_seconds"
  printf 'unsegmented_tfosorted=%s\n' "$unsegmented_tfosorted"
  printf 'merged_tfosorted=%s\n' "$WORK/merged/segmented-global-TFOsorted"
  cat "$WORK/merge_summary.txt"
  printf 'gasal2_requests=%s\n' "$gasal2_requests"
  printf 'gasal2_traceback_requests=%s\n' "$gasal2_traceback_requests"
  printf 'gasal2_fallbacks=%s\n' "$gasal2_fallbacks"
  printf 'length_guard_fallbacks=%s\n' "$length_guard_fallbacks"
  printf 'top5_offline_cluster_equal=%s\n' "$cluster_equal"
  printf 'top5_offline_cluster_overlap=%s\n' "$cluster_overlap"
  printf 'top5_tfo_score_equal=%s\n' "$(metric_or_default "$WORK/tfo_contract_compare.txt" top5_tfo_score_equal false)"
  printf 'top5_tfo_stability_equal=%s\n' "$(metric_or_default "$WORK/tfo_contract_compare.txt" top5_tfo_stability_equal false)"
  printf 'top5_tfo_nt_score_equal=%s\n' "$(metric_or_default "$WORK/tfo_contract_compare.txt" top5_tfo_nt_score_equal false)"
  printf 'full_missing_rows=%s\n' "$(metric_or_default "$WORK/tfo_contract_compare.txt" full_missing_rows 0)"
  printf 'full_extra_rows=%s\n' "$(metric_or_default "$WORK/tfo_contract_compare.txt" full_extra_rows 0)"
  printf 'decision=%s\n' "$decision"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
