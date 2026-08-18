#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_longtarget_f0_audit}"
TARGET="${TARGET:-/data/wenyujianData/linjieData/promoter_sequences/human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1/shards/shard_0009.fa}"
QUERY="${QUERY:-$ROOT/.tmp/lower-bound-shard-0009/query.fa}"
CACHE="${CACHE:-$ROOT/.tmp/lower-bound-shard-0009/endpoint_cache.bin}"
WORK="${WORK:-$ROOT/.tmp/f0-replay-formal}"
REPEATS="${REPEATS:-3}"
EXPECTED_SHA="${EXPECTED_SHA:-2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075}"

for path in "$BIN" "$TARGET" "$QUERY" "$CACHE"; do
  [[ -s "$path" ]] || { echo "missing artifact: $path" >&2; exit 2; }
done
[[ "$REPEATS" =~ ^[1-9][0-9]*$ ]] || { echo "REPEATS must be positive" >&2; exit 2; }
rm -rf "$WORK"
mkdir -p "$WORK"

for repeat in $(seq 1 "$REPEATS"); do
  out="$WORK/repeat_${repeat}"
  mkdir -p "$out/output"
  /usr/bin/time -f 'wall_seconds=%e\nmax_rss_kb=%M\nexit_status=%x' \
    -o "$out/time.txt" \
    env CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
      FASIM_OUTPUT_MODE=tfosorted \
      FASIM_VERBOSE=0 \
      FASIM_ALIGN_GASAL2=1 \
      FASIM_ENABLE_PREALIGN_CUDA=1 \
      FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
      FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
      FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
      FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE=1 \
      FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1 \
      FASIM_LONG_QUERY_F0_ENDPOINT_CACHE="$CACHE" \
      FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT="$out/consumer.tsv" \
      "$BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 -O "$out/output" \
      >"$out/stdout.log" 2>"$out/stderr.log"
  artifact="$(find "$out/output" -maxdepth 1 -type f -name '*-TFOsorted' -print -quit)"
  [[ -s "$artifact" ]] || { echo "missing F0 output repeat $repeat" >&2; exit 1; }
  digest="$(sha256sum "$artifact" | awk '{print $1}')"
  [[ "$digest" == "$EXPECTED_SHA" ]] || {
    echo "F0 output digest mismatch repeat $repeat: $digest" >&2
    exit 1
  }
done

python3 - "$WORK" "$EXPECTED_SHA" "$REPEATS" <<'PY'
import csv
import json
import statistics
import sys
from pathlib import Path

work = Path(sys.argv[1])
expected = sys.argv[2]
repeats = int(sys.argv[3])
rows_by_repeat = []
wall = []
for index in range(1, repeats + 1):
    root = work / f"repeat_{index}"
    wall_text = (root / "time.txt").read_text()
    wall.append(float(next(line.split("=", 1)[1] for line in wall_text.splitlines() if line.startswith("wall_seconds="))))
    with (root / "consumer.tsv").open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    rows_by_repeat.append(rows)
    if len(rows) == 0 or any(row["ok"] != "1" for row in rows):
        raise SystemExit(f"F0 technical failure in repeat {index}")
    for key in ("cached_endpoint_replay", "error", "cpu_continuation_failures", "cpu_oracle_attempts", "cpu_reference_align_attempts"):
        if key == "cached_endpoint_replay" and any(row[key] != "1" for row in rows):
            raise SystemExit(f"cache not active in repeat {index}")
        if key == "error" and any(row[key] != "none" for row in rows):
            raise SystemExit(f"F0 error in repeat {index}")
        if key != "cached_endpoint_replay" and key != "error" and any(int(row[key]) != 0 for row in rows):
            raise SystemExit(f"unexpected {key} in repeat {index}")
if any(len(rows) != len(rows_by_repeat[0]) for rows in rows_by_repeat):
    raise SystemExit("repeat row count mismatch")
if len(rows_by_repeat[0]) != 48432:
    raise SystemExit(f"unexpected task rows: {len(rows_by_repeat[0])}")
def total(rows, key):
    return sum(float(row[key]) for row in rows)
summary = {
    "schema_version": "long_query_f0_cached_endpoint_replay_v1",
    "physical_floor_experiment": True,
    "repeats": repeats,
    "task_rows": len(rows_by_repeat[0]),
    "wall_seconds": wall,
    "median_wall_seconds": statistics.median(wall),
    "expected_output_sha256": expected,
    "all_repeats_cached": True,
    "all_repeats_exact": True,
    "gpu_kernel_seconds": [total(rows, "gpu_kernel_seconds") for rows in rows_by_repeat],
    "h2d_seconds": [total(rows, "h2d_seconds") for rows in rows_by_repeat],
    "d2h_seconds": [total(rows, "d2h_seconds") for rows in rows_by_repeat],
    "cache_records": [int(total(rows, "cache_records")) for rows in rows_by_repeat],
    "attempts": [int(total(rows, "attempts")) for rows in rows_by_repeat],
    "selected_continuation_calls": [int(total(rows, "cpu_continuation_calls")) for rows in rows_by_repeat],
}
(work / "f0_report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY
