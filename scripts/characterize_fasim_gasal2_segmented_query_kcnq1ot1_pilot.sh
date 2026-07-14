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
MERGE_DEDUP_BACKEND="${MERGE_DEDUP_BACKEND:-sqlite}"
KEEP_DEDUP_DB="${KEEP_DEDUP_DB:-0}"
CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE="${CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE:-0}"
FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW="${FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW:-0}"
RESUME="${RESUME:-0}"
EXACT_SCOREINFO_PRUNED="${EXACT_SCOREINFO_PRUNED:-0}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
DEVICE_MEMORY_BUDGET_BYTES="${DEVICE_MEMORY_BUDGET_BYTES:-23622320128}"
WORKER_COUNT="${WORKER_COUNT:-1}"
SEGMENT_BATCH_SIZE="${SEGMENT_BATCH_SIZE:-1}"
TRACEBACK_CERTIFICATE_MODE="disabled"

MERGE_SCRIPT="$ROOT/scripts/merge_fasim_segmented_tfosorted.py"
CLUSTER_COMPARE="$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py"
OWNERSHIP_SCRIPT="$ROOT/scripts/fasim_segment_ownership.py"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$MERGE_SCRIPT" "$CLUSTER_COMPARE" "$OWNERSHIP_SCRIPT"; do
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
if [[ "$MERGE_DEDUP_BACKEND" != "memory" && "$MERGE_DEDUP_BACKEND" != "sqlite" ]]; then
  echo "MERGE_DEDUP_BACKEND must be memory or sqlite" >&2
  exit 1
fi
if [[ "$KEEP_DEDUP_DB" != "0" && "$KEEP_DEDUP_DB" != "1" ]]; then
  echo "KEEP_DEDUP_DB must be 0 or 1" >&2
  exit 1
fi
if [[ "$CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE" != "0" && "$CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE" != "1" ]]; then
  echo "CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE must be 0 or 1" >&2
  exit 1
fi
if [[ "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW" != "0" && "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW" != "1" ]]; then
  echo "FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW must be 0 or 1" >&2
  exit 1
fi
if [[ "$RESUME" != "0" && "$RESUME" != "1" ]]; then
  echo "RESUME must be 0 or 1" >&2
  exit 1
fi
if [[ "$EXACT_SCOREINFO_PRUNED" != "0" && "$EXACT_SCOREINFO_PRUNED" != "1" ]]; then
  echo "EXACT_SCOREINFO_PRUNED must be 0 or 1" >&2
  exit 1
fi
if (( EXACT_SCOREINFO_GPU_MAX_PER_TASK <= 0 )); then
  echo "EXACT_SCOREINFO_GPU_MAX_PER_TASK must be positive" >&2
  exit 1
fi
if (( DEVICE_MEMORY_BUDGET_BYTES <= 0 )); then
  echo "DEVICE_MEMORY_BUDGET_BYTES must be positive" >&2
  exit 1
fi
if (( WORKER_COUNT != 1 || SEGMENT_BATCH_SIZE != 1 )); then
  echo "the current segmented runner supports WORKER_COUNT=1 and SEGMENT_BATCH_SIZE=1" >&2
  exit 1
fi

if [[ "$RESUME" == "0" ]]; then
  rm -rf "$WORK"
fi
mkdir -p "$WORK/grids"

binary_sha256="$(sha256sum "$BIN" | awk '{print $1}')"
query_sha256="$(sha256sum "$RNA" | awk '{print $1}')"
target_sha256="$(sha256sum "$TARGET" | awk '{print $1}')"
commit="$(git -C "$ROOT" rev-parse HEAD)"
config_candidate="$WORK/.run-config.candidate.json"
python3 - "$config_candidate" "$commit" "$BIN" "$binary_sha256" "$RNA" \
  "$query_sha256" "$TARGET" "$target_sha256" "$RULE" "$SEGMENT_LEN" \
  "$SEGMENT_OVERLAP" "$GRID_SHIFTS" "$MAX_SEGMENTS" "$PRUNE_MAX_PER_TASK" \
  "$GASAL2_STREAMS" "$GASAL2_BATCH" "$MERGE_DEDUP_BACKEND" \
  "$KEEP_DEDUP_DB" "$CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE" \
  "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW" "$EXACT_SCOREINFO_PRUNED" \
  "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" "$DEVICE_MEMORY_BUDGET_BYTES" \
  "$WORKER_COUNT" "$SEGMENT_BATCH_SIZE" "${CUDA_VISIBLE_DEVICES:-inherit}" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


(
    output,
    commit,
    binary,
    binary_sha256,
    query,
    query_sha256,
    target,
    target_sha256,
    rule,
    segment_len,
    segment_overlap,
    grid_shifts,
    max_segments,
    prune_max_per_task,
    streams,
    batch,
    dedup_backend,
    keep_dedup_db,
    clean_segment_archives,
    ownership_shadow,
    exact_scoreinfo_pruned,
    exact_max_per_task,
    memory_budget,
    worker_count,
    segment_batch_size,
    gpu_ids,
) = sys.argv[1:]
shifts = [int(value) for value in grid_shifts.split()]
payload = {
    "schema_version": 1,
    "commit": commit,
    "binary": str(Path(binary).resolve()),
    "binary_sha256": binary_sha256,
    "query": str(Path(query).resolve()),
    "query_sha256": query_sha256,
    "target": str(Path(target).resolve()),
    "target_sha256": target_sha256,
    "rule": int(rule),
    "segment_len": int(segment_len),
    "segment_overlap": int(segment_overlap),
    "grid_shifts": shifts,
    "grid_mode": "dual_grid" if len(shifts) > 1 else "canonical_grid",
    "max_segments": int(max_segments),
    "archive_first": True,
    "persistent_context": False,
    "segment_batch_size": int(segment_batch_size),
    "device_memory_budget_bytes": int(memory_budget),
    "ownership_mode": "shadow" if ownership_shadow == "1" else "disabled",
    "exact_column_variant": (
        "gpu_pruned_scoreinfo_v1"
        if exact_scoreinfo_pruned == "1"
        else "legacy_authority_scoreinfo"
    ),
    "exact_scoreinfo_gpu_max_per_task": int(exact_max_per_task),
    "traceback_certificate_mode": "disabled",
    "streams": int(streams),
    "gasal2_batch": int(batch),
    "prune_max_per_task": int(prune_max_per_task),
    "gpu_ids": gpu_ids,
    "worker_count": int(worker_count),
    "merge_dedup_backend": dedup_backend,
    "keep_dedup_db": keep_dedup_db == "1",
    "clean_segment_archives_after_merge": clean_segment_archives == "1",
    "output_mode": "tfosorted",
}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
payload["config_digest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
path = Path(output)
temporary = path.with_name(path.name + ".tmp")
temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, path)
PY

if [[ -f "$WORK/run-config.json" ]]; then
  if ! cmp -s "$WORK/run-config.json" "$config_candidate"; then
    echo "run config digest mismatch for resumable work directory: $WORK" >&2
    rm -f "$config_candidate"
    exit 1
  fi
  rm -f "$config_candidate"
else
  mv "$config_candidate" "$WORK/run-config.json"
fi
config_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["config_digest_sha256"])' "$WORK/run-config.json")"

if [[ "$RESUME" == "1" && -f "$WORK/run-complete.json" ]]; then
  if python3 - "$WORK/run-complete.json" "$WORK/summary.txt" "$config_digest" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

receipt_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
expected_digest = sys.argv[3]
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
if receipt.get("config_digest_sha256") != expected_digest:
    raise SystemExit("completed run config digest mismatch")
if not summary_path.is_file():
    raise SystemExit("completed run is missing summary.txt")
actual_summary = hashlib.sha256(summary_path.read_bytes()).hexdigest()
if receipt.get("summary_sha256") != actual_summary:
    raise SystemExit("completed run summary digest mismatch")
outputs = receipt.get("merged_outputs")
if not isinstance(outputs, list) or not outputs:
    raise SystemExit("completed run is missing merged output digests")
for output in outputs:
    path = Path(output.get("path", ""))
    if not path.is_file():
        raise SystemExit(f"completed run is missing merged output: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if output.get("sha256") != actual:
        raise SystemExit(f"completed run merged output digest mismatch: {path}")
PY
  then
    cat "$WORK/summary.txt"
    printf 'resume_complete=1\n'
    exit 0
  fi
  rm -f "$WORK/run-complete.json"
fi
pipeline_start="$(date +%s.%N)"

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

find_unique_archive_output() {
  local dir="$1"
  local -a archives=()
  mapfile -t archives < <(find "$dir" -maxdepth 1 -type f -name '*.archive-first.tfoa' | sort)
  if (( ${#archives[@]} != 1 )); then
    echo "expected exactly one segment archive-first artifact in $dir; found ${#archives[@]}" >&2
    return 1
  fi
  printf '%s\n' "${archives[0]}"
}

reject_full_tfosorted_output() {
  local dir="$1"
  local -a outputs=()
  mapfile -t outputs < <(find "$dir" -maxdepth 1 -type f -name '*-TFOsorted' | sort)
  if (( ${#outputs[@]} != 0 )); then
    echo "archive-first run emitted full segment TFOsorted in $dir: ${outputs[*]}" >&2
    return 1
  fi
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

required_stderr_metric() {
  local file="$1"
  local key="$2"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file")" || {
    echo "missing required runtime metric $key in $file" >&2
    return 1
  }
  printf '%s\n' "$value"
}

segment_receipt_valid() {
  local receipt="$1"
  local segment_id="$2"
  local global_start="$3"
  local global_end="$4"
  local query_fasta="$5"
  local archive="$6"
  python3 - "$receipt" "$config_digest" "$segment_id" "$global_start" \
    "$global_end" "$query_fasta" "$TARGET" "$archive" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt_path = Path(sys.argv[1])
expected = {
    "config_digest_sha256": sys.argv[2],
    "segment_id": int(sys.argv[3]),
    "global_start": int(sys.argv[4]),
    "global_end": int(sys.argv[5]),
}
query = Path(sys.argv[6])
target = Path(sys.argv[7])
archive = Path(sys.argv[8])
if not receipt_path.is_file() or not query.is_file() or not target.is_file() or not archive.is_file():
    raise SystemExit(1)
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
if receipt.get("status") != "complete":
    raise SystemExit(1)
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(1)
checks = {
    "query_fasta_sha256": digest(query),
    "target_fasta_sha256": digest(target),
    "archive_sha256": digest(archive),
}
if any(receipt.get(key) != value for key, value in checks.items()):
    raise SystemExit(1)
if Path(receipt.get("archive_path", "")).resolve() != archive.resolve():
    raise SystemExit(1)
PY
}

write_segment_receipt() {
  local receipt="$1"
  local segment_id="$2"
  local global_start="$3"
  local global_end="$4"
  local query_fasta="$5"
  local archive="$6"
  local wall_seconds="$7"
  python3 - "$receipt" "$config_digest" "$segment_id" "$global_start" \
    "$global_end" "$query_fasta" "$TARGET" "$archive" "$wall_seconds" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = Path(sys.argv[1])
query = Path(sys.argv[6])
target = Path(sys.argv[7])
archive = Path(sys.argv[8])
payload = {
    "schema_version": 1,
    "status": "complete",
    "config_digest_sha256": sys.argv[2],
    "segment_id": int(sys.argv[3]),
    "global_start": int(sys.argv[4]),
    "global_end": int(sys.argv[5]),
    "query_fasta": str(query.resolve()),
    "query_fasta_sha256": digest(query),
    "target_fasta": str(target.resolve()),
    "target_fasta_sha256": digest(target),
    "archive_path": str(archive.resolve()),
    "archive_sha256": digest(archive),
    "wall_seconds": float(sys.argv[9]),
}
temporary = receipt.with_name(receipt.name + ".tmp")
temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, receipt)
PY
}

run_gasal2_tfosorted() {
  local query="$1"
  local out_dir="$2"
  local -a exact_env=(
    FASIM_EXACT_COLUMN_SCOREINFO_GPU=0
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK"
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=0
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=0
  )
  if [[ "$EXACT_SCOREINFO_PRUNED" == "1" ]]; then
    exact_env=(
      FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
      FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK"
      FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
      FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=0
    )
  fi
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
    FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=0 \
    "${exact_env[@]}" \
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
        writer.writerow(["segment_id", "global_start", "global_end", "query_len", "fasta"])
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
            writer.writerow([idx, start, end, len(seq), fasta])
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
query_length="$(awk -F= '$1=="query_len"{print $2}' "$WORK/window_summary.txt")"
merged_outputs=()
all_stderr_files=()
all_archive_files=()
merge_summary_files=()
ownership_summary_files=()
target_sha256="$(sha256_file "$TARGET")"
per_segment_full_text_emitted=0

for shift in "${grid_shifts[@]}"; do
  grid_dir="$WORK/grids/shift_${shift}"
  segments_manifest="$grid_dir/segments.tsv"
  outputs_manifest="$grid_dir/segment_outputs.tsv"
  {
    IFS=$'\t' read -r header_segment_id header_start header_end header_len header_fasta
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "segment_id" "global_start" "global_end" "artifact_kind" "artifact_path" \
      "query_fasta" "query_fasta_sha256" "target_fasta" "target_fasta_sha256"
    while IFS=$'\t' read -r segment_id global_start global_end query_len fasta; do
      out_dir="$grid_dir/run_${segment_id}"
      receipt="$out_dir/segment-complete.json"
      archive=""
      segment_reused=0
      if [[ "$RESUME" == "1" && -f "$receipt" ]]; then
        if archive="$(find_unique_archive_output "$out_dir" 2>/dev/null)" && \
           segment_receipt_valid "$receipt" "$segment_id" "$global_start" \
             "$global_end" "$fasta" "$archive"; then
          segment_reused=1
        fi
      fi
      if [[ "$segment_reused" == "0" ]]; then
        rm -rf "$out_dir"
        mkdir -p "$out_dir"
        segment_start="$(now_seconds)"
        run_gasal2_tfosorted "$fasta" "$out_dir"
        segment_end="$(now_seconds)"
        elapsed_seconds "$segment_start" "$segment_end" >"$out_dir/wall_seconds.txt"
        archive="$(find_unique_archive_output "$out_dir")"
      fi
      if [[ ! -s "$archive" ]]; then
        echo "empty segment archive-first artifact for shift $shift segment $segment_id: $archive" >&2
        exit 1
      fi
      reject_full_tfosorted_output "$out_dir"
      archive_requested="$(required_stderr_metric "$out_dir/stderr.log" benchmark.fasim_gasal2_archive_first_output_requested)"
      archive_active="$(required_stderr_metric "$out_dir/stderr.log" benchmark.fasim_gasal2_archive_first_output_active)"
      archive_decision="$(required_stderr_metric "$out_dir/stderr.log" benchmark.fasim_gasal2_archive_first_output_decision)"
      if [[ "$archive_requested" != "1" || "$archive_active" != "1" || "$archive_decision" != "active" ]]; then
        echo "archive-first runtime inactive for shift $shift segment $segment_id: requested=$archive_requested active=$archive_active decision=$archive_decision" >&2
        exit 1
      fi
      if [[ "$segment_reused" == "0" ]]; then
        write_segment_receipt "$receipt" "$segment_id" "$global_start" \
          "$global_end" "$fasta" "$archive" "$(<"$out_dir/wall_seconds.txt")"
      fi
      query_sha256="$(sha256_file "$fasta")"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$segment_id" "$global_start" "$global_end" "archive_first_tfoa" "$archive" \
        "$fasta" "$query_sha256" "$TARGET" "$target_sha256"
      all_stderr_files+=("$out_dir/stderr.log")
      all_archive_files+=("$archive")
    done
  } <"$segments_manifest" >"$outputs_manifest"

  merged="$grid_dir/merged-common-TFOsorted"
  merge_command=(
    python3 "$MERGE_SCRIPT"
    --segments "$outputs_manifest" \
    --query-min "$common_query_start" \
    --query-max "$common_query_end" \
    --output "$merged"
    --dedup-backend "$MERGE_DEDUP_BACKEND"
  )
  if [[ "$MERGE_DEDUP_BACKEND" == "sqlite" ]]; then
    merge_command+=(--dedup-db "$grid_dir/merge-dedup.sqlite")
    if [[ "$KEEP_DEDUP_DB" == "1" ]]; then
      merge_command+=(--keep-dedup-db)
    fi
  fi
  "${merge_command[@]}" >"$grid_dir/merge_summary.txt"
  merged_outputs+=("$merged")
  merge_summary_files+=("$grid_dir/merge_summary.txt")

  if [[ "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW" == "1" ]]; then
    python3 "$OWNERSHIP_SCRIPT" derive \
      --segments "$outputs_manifest" \
      --grid-shift "$shift" \
      --query-length "$query_length" \
      --output "$grid_dir/ownership-descriptors.tsv"
    python3 "$OWNERSHIP_SCRIPT" shadow \
      --segments "$outputs_manifest" \
      --descriptors "$grid_dir/ownership-descriptors.tsv" \
      --output "$grid_dir/ownership-shadow-TFOsorted" \
      --db "$grid_dir/ownership-shadow.sqlite" \
      --summary "$grid_dir/ownership-shadow-summary.txt" \
      >"$grid_dir/ownership-shadow-stdout.txt"
    ownership_summary_files+=("$grid_dir/ownership-shadow-summary.txt")
  fi
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

if [[ "$CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE" == "1" ]]; then
  for archive in "${all_archive_files[@]}"; do
    rm -f -- "$archive"
  done
fi

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

sum_stderr_decimal_metric() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key && $2 ~ /^[0-9]+([.][0-9]+)?$/ {sum += $2; found=1}
    END {if (found) printf "%.6f", sum; else print "unavailable"}
  ' "$@"
}

max_stderr_metric() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key && $2 ~ /^[0-9]+$/ {if (!found || $2 > max) max=$2; found=1}
    END {if (found) printf "%.0f", max; else print "unavailable"}
  ' "$@"
}

sum_summary_metric() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key && $2 ~ /^[0-9]+([.][0-9]+)?$/ {sum += $2; found=1}
    END {if (found) printf "%.6f", sum; else print "unavailable"}
  ' "$@"
}

sum_summary_integer() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key && $2 ~ /^[0-9]+$/ {sum += $2; found=1}
    END {if (found) printf "%.0f", sum; else print "unavailable"}
  ' "$@"
}

max_summary_integer() {
  local key="$1"
  shift
  awk -F= -v key="$key" '
    $1 == key && $2 ~ /^[0-9]+$/ {if (!found || $2 > max) max=$2; found=1}
    END {if (found) printf "%.0f", max; else print "unavailable"}
  ' "$@"
}

gasal2_requests="$(sum_stderr_metric benchmark.fasim_gasal2_requests "${all_stderr_files[@]}")"
gasal2_traceback_requests="$(sum_stderr_metric benchmark.fasim_gasal2_traceback_requests "${all_stderr_files[@]}")"
gasal2_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_fallbacks "${all_stderr_files[@]}")"
length_guard_fallbacks="$(sum_stderr_metric benchmark.fasim_gasal2_length_guard_fallbacks "${all_stderr_files[@]}")"
exact_column_tasks="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_column_tasks "${all_stderr_files[@]}")"
exact_scoreinfo_tasks="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks "${all_stderr_files[@]}")"
exact_column_cells="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_column_cells "${all_stderr_files[@]}")"
exact_scoreinfo_cells="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells "${all_stderr_files[@]}")"
read -r exact_work_tasks exact_work_cells < <(python3 - \
  "$exact_column_tasks" "$exact_scoreinfo_tasks" \
  "$exact_column_cells" "$exact_scoreinfo_cells" <<'PY'
import sys

column_tasks, scoreinfo_tasks, column_cells, scoreinfo_cells = map(int, sys.argv[1:])
if column_tasks and scoreinfo_tasks and column_tasks != scoreinfo_tasks:
    raise SystemExit(
        f"exact task accounting mismatch: {column_tasks} != {scoreinfo_tasks}"
    )
if column_cells and scoreinfo_cells and column_cells != scoreinfo_cells:
    raise SystemExit(
        f"exact cell accounting mismatch: {column_cells} != {scoreinfo_cells}"
    )
print(max(column_tasks, scoreinfo_tasks), max(column_cells, scoreinfo_cells))
PY
)
exact_column_wall_seconds="$(sum_stderr_decimal_metric benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds "${all_stderr_files[@]}")"
exact_scoreinfo_wall_seconds="$(sum_stderr_decimal_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds "${all_stderr_files[@]}")"
exact_stage_seconds="$(python3 - "$exact_column_wall_seconds" "$exact_scoreinfo_wall_seconds" <<'PY'
import sys

if "unavailable" in sys.argv[1:]:
    print("unavailable")
else:
    print(f"{sum(map(float, sys.argv[1:])):.6f}")
PY
)"
exact_scoreinfo_gpu_pruned_output_enabled="$(max_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled "${all_stderr_files[@]}")"
exact_scoreinfo_gpu_column_pruned_output_enabled="$(max_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled "${all_stderr_files[@]}")"
exact_scoreinfo_gpu_overflow_batches="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches "${all_stderr_files[@]}")"
exact_scoreinfo_gpu_fallback_batches="$(sum_stderr_metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches "${all_stderr_files[@]}")"
traceback_fill_seconds="$(sum_stderr_decimal_metric benchmark.fasim_gasal2_traceback_fill_seconds "${all_stderr_files[@]}")"
traceback_submit_seconds="$(sum_stderr_decimal_metric benchmark.fasim_gasal2_traceback_submit_seconds "${all_stderr_files[@]}")"
traceback_wait_seconds="$(sum_stderr_decimal_metric benchmark.fasim_gasal2_traceback_wait_seconds "${all_stderr_files[@]}")"
traceback_convert_seconds="$(sum_stderr_decimal_metric benchmark.fasim_gasal2_cpu_traceback_convert_seconds "${all_stderr_files[@]}")"
traceback_host_observed_stage_seconds="$(python3 - \
  "$traceback_fill_seconds" "$traceback_submit_seconds" \
  "$traceback_wait_seconds" "$traceback_convert_seconds" <<'PY'
import sys

if "unavailable" in sys.argv[1:]:
    print("unavailable")
else:
    print(f"{sum(map(float, sys.argv[1:])):.6f}")
PY
)"
cluster_equal="$(metric_or_default "$WORK/offline_cluster_grid_compare.txt" top5_offline_cluster_equal false)"
cluster_overlap="$(metric_or_default "$WORK/offline_cluster_grid_compare.txt" top5_offline_cluster_overlap 0)"
segment_run_wall_seconds="$(awk '{sum += $1} END {printf "%.6f", sum}' "$WORK"/grids/shift_*/run_*/wall_seconds.txt)"
archive_input_bytes="$(sum_summary_integer archive_input_bytes "${merge_summary_files[@]}")"
segment_archives_retained=0
for archive in "${all_archive_files[@]}"; do
  if [[ -f "$archive" ]]; then
    segment_archives_retained=$((segment_archives_retained + 1))
  fi
done
bounded_memory_backend_active=0
if [[ "$MERGE_DEDUP_BACKEND" == "sqlite" ]]; then
  bounded_memory_backend_active=1
fi
segment_ownership_shadow_active=0
segment_ownership_rows_total="unavailable"
segment_ownership_rows_owned="unavailable"
segment_ownership_rows_non_owner_duplicate="unavailable"
segment_ownership_rows_no_owner="unavailable"
segment_ownership_rows_multi_owner_before_tiebreak="unavailable"
segment_ownership_rows_owner_mismatch_vs_authority="unavailable"
if [[ "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW" == "1" ]]; then
  if (( ${#ownership_summary_files[@]} != ${#grid_shifts[@]} )); then
    echo "ownership shadow summary count does not match grid count" >&2
    exit 1
  fi
  segment_ownership_shadow_active=1
  segment_ownership_rows_total="$(sum_summary_integer rows_total "${ownership_summary_files[@]}")"
  segment_ownership_rows_owned="$(sum_summary_integer rows_owned "${ownership_summary_files[@]}")"
  segment_ownership_rows_non_owner_duplicate="$(sum_summary_integer rows_non_owner_duplicate "${ownership_summary_files[@]}")"
  segment_ownership_rows_no_owner="$(sum_summary_integer rows_no_owner "${ownership_summary_files[@]}")"
  segment_ownership_rows_multi_owner_before_tiebreak="$(sum_summary_integer rows_multi_owner_before_tiebreak "${ownership_summary_files[@]}")"
  segment_ownership_rows_owner_mismatch_vs_authority="$(sum_summary_integer rows_owner_mismatch_vs_authority "${ownership_summary_files[@]}")"
fi
pipeline_end="$(now_seconds)"
pipeline_wall_seconds="$(elapsed_seconds "$pipeline_start" "$pipeline_end")"
exact_column_variant="legacy_authority_scoreinfo"
if [[ "$EXACT_SCOREINFO_PRUNED" == "1" ]]; then
  exact_column_variant="gpu_pruned_scoreinfo_v1"
fi
segment_receipts_complete="$(find "$WORK/grids" -path '*/run_*/segment-complete.json' -type f | wc -l)"

decision="segmented_query_kcnq1ot1_pilot_incomplete"
if [[ "$cluster_equal" == "true" && "$gasal2_fallbacks" == "0" && "$length_guard_fallbacks" == "0" ]]; then
  decision="segmented_query_kcnq1ot1_pilot_grid_stable"
fi

{
  printf 'run_config=%s\n' "$WORK/run-config.json"
  printf 'config_digest_sha256=%s\n' "$config_digest"
  printf 'resume_enabled=%s\n' "$RESUME"
  printf 'exact_column_variant=%s\n' "$exact_column_variant"
  printf 'traceback_certificate_mode=%s\n' "$TRACEBACK_CERTIFICATE_MODE"
  printf 'persistent_context_active=0\n'
  printf 'worker_count=%s\n' "$WORKER_COUNT"
  printf 'segment_batch_size=%s\n' "$SEGMENT_BATCH_SIZE"
  printf 'device_memory_budget_bytes=%s\n' "$DEVICE_MEMORY_BUDGET_BYTES"
  cat "$WORK/window_summary.txt"
  for shift in "${grid_shifts[@]}"; do
    sed "s/^/shift_${shift}_/" "$WORK/grids/shift_${shift}/merge_summary.txt"
  done
  printf 'artifact_kind_counts=archive_first_tfoa:%s\n' "${#all_archive_files[@]}"
  printf 'archive_input_bytes=%s\n' "$archive_input_bytes"
  printf 'text_input_bytes=0\n'
  printf 'input_rows=%s\n' "$(sum_summary_integer input_rows "${merge_summary_files[@]}")"
  printf 'output_rows=%s\n' "$(sum_summary_integer output_rows "${merge_summary_files[@]}")"
  printf 'duplicate_rows=%s\n' "$(sum_summary_integer duplicate_rows "${merge_summary_files[@]}")"
  printf 'filtered_rows=%s\n' "$(sum_summary_integer filtered_rows "${merge_summary_files[@]}")"
  printf 'dedup_backend=%s\n' "$MERGE_DEDUP_BACKEND"
  printf 'dedup_db_bytes=%s\n' "$(sum_summary_integer dedup_db_bytes "${merge_summary_files[@]}")"
  printf 'merge_wall_seconds=%s\n' "$(sum_summary_metric merge_wall_seconds "${merge_summary_files[@]}")"
  printf 'restore_wall_seconds=%s\n' "$(sum_summary_metric restore_wall_seconds "${merge_summary_files[@]}")"
  printf 'dedup_wall_seconds=%s\n' "$(sum_summary_metric dedup_wall_seconds "${merge_summary_files[@]}")"
  printf 'write_wall_seconds=%s\n' "$(sum_summary_metric write_wall_seconds "${merge_summary_files[@]}")"
  printf 'peak_rss_kb=%s\n' "$(max_summary_integer peak_rss_kb "${merge_summary_files[@]}")"
  printf 'segment_run_wall_seconds=%s\n' "$segment_run_wall_seconds"
  printf 'pipeline_wall_seconds=%s\n' "$pipeline_wall_seconds"
  printf 'segment_receipts_complete=%s\n' "$segment_receipts_complete"
  printf 'per_segment_full_text_emitted=%s\n' "$per_segment_full_text_emitted"
  printf 'bounded_memory_backend_active=%s\n' "$bounded_memory_backend_active"
  printf 'segment_archives_retained=%s\n' "$segment_archives_retained"
  printf 'segment_ownership_shadow_requested=%s\n' "$FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW"
  printf 'segment_ownership_shadow_active=%s\n' "$segment_ownership_shadow_active"
  printf 'segment_ownership_rows_total=%s\n' "$segment_ownership_rows_total"
  printf 'segment_ownership_rows_owned=%s\n' "$segment_ownership_rows_owned"
  printf 'segment_ownership_rows_non_owner_duplicate=%s\n' "$segment_ownership_rows_non_owner_duplicate"
  printf 'segment_ownership_rows_no_owner=%s\n' "$segment_ownership_rows_no_owner"
  printf 'segment_ownership_rows_multi_owner_before_tiebreak=%s\n' "$segment_ownership_rows_multi_owner_before_tiebreak"
  printf 'segment_ownership_rows_owner_mismatch_vs_authority=%s\n' "$segment_ownership_rows_owner_mismatch_vs_authority"
  printf 'segment_ownership_potential_exact_tasks_removed=unavailable\n'
  printf 'segment_ownership_potential_tracebacks_removed=unavailable\n'
  printf 'segment_ownership_runtime_work_dropped=0\n'
  printf 'gasal2_requests=%s\n' "$gasal2_requests"
  printf 'gasal2_traceback_requests=%s\n' "$gasal2_traceback_requests"
  printf 'exact_column_tasks=%s\n' "$exact_column_tasks"
  printf 'exact_scoreinfo_gpu_tasks=%s\n' "$exact_scoreinfo_tasks"
  printf 'exact_work_tasks=%s\n' "$exact_work_tasks"
  printf 'exact_column_cells=%s\n' "$exact_column_cells"
  printf 'exact_scoreinfo_gpu_cells=%s\n' "$exact_scoreinfo_cells"
  printf 'exact_work_cells=%s\n' "$exact_work_cells"
  printf 'exact_column_wall_seconds=%s\n' "$exact_column_wall_seconds"
  printf 'exact_scoreinfo_gpu_wall_seconds=%s\n' "$exact_scoreinfo_wall_seconds"
  printf 'exact_stage_seconds=%s\n' "$exact_stage_seconds"
  printf 'exact_scoreinfo_gpu_pruned_output_enabled=%s\n' "$exact_scoreinfo_gpu_pruned_output_enabled"
  printf 'exact_scoreinfo_gpu_column_pruned_output_enabled=%s\n' "$exact_scoreinfo_gpu_column_pruned_output_enabled"
  printf 'exact_scoreinfo_gpu_overflow_batches=%s\n' "$exact_scoreinfo_gpu_overflow_batches"
  printf 'exact_scoreinfo_gpu_fallback_batches=%s\n' "$exact_scoreinfo_gpu_fallback_batches"
  printf 'traceback_host_observed_stage_seconds=%s\n' "$traceback_host_observed_stage_seconds"
  printf 'gasal2_fallbacks=%s\n' "$gasal2_fallbacks"
  printf 'length_guard_fallbacks=%s\n' "$length_guard_fallbacks"
  printf 'top5_offline_cluster_equal=%s\n' "$cluster_equal"
  printf 'top5_offline_cluster_overlap=%s\n' "$cluster_overlap"
  printf 'decision=%s\n' "$decision"
} >"$WORK/summary.txt"

python3 - "$WORK/run-complete.json" "$WORK/summary.txt" "$config_digest" \
  "$WORK/grids" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

receipt = Path(sys.argv[1])
summary = Path(sys.argv[2])
merged_outputs = sorted(Path(sys.argv[4]).glob("shift_*/merged-common-TFOsorted"))
if not merged_outputs:
    raise SystemExit("cannot complete run without merged outputs")
payload = {
    "schema_version": 1,
    "status": "complete",
    "config_digest_sha256": sys.argv[3],
    "summary_sha256": hashlib.sha256(summary.read_bytes()).hexdigest(),
    "merged_outputs": [
        {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in merged_outputs
    ],
}
temporary = receipt.with_name(receipt.name + ".tmp")
temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, receipt)
PY

cat "$WORK/summary.txt"
