#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
DNA="${DNA:?DNA must point to a target FASTA}"
RNA="${RNA:?RNA must point to an RNA/query FASTA}"
RULE="${RULE:-0}"
OUT="${OUT:-"$ROOT/.tmp/fasim_gasal2_topk_lite"}"
K="${K:-5}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
AUTO_CPU_CORE_RANGES="${AUTO_CPU_CORE_RANGES:-0}"
CPU_POOL="${CPU_POOL:-}"
CPU_CORES_PER_WORKER="${CPU_CORES_PER_WORKER:-}"
FORCE="${FORCE:-1}"
RESUME="${RESUME:-0}"
DRY_RUN="${DRY_RUN:-0}"
LEGACY_DIRECT="${LEGACY_DIRECT:-0}"
GROUP_TARGET_RECORDS="${GROUP_TARGET_RECORDS:-}"

# Legacy direct Fasim mode is retained only for historical diagnostics.
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-16}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
IN_PROCESS_TOPK="${IN_PROCESS_TOPK:-0}"

if [[ "$K" != "5" ]]; then
  echo "formal GASAL2 topK-lite wrapper requires K=5" >&2
  exit 1
fi
if [[ "$RESUME" == "1" && "$FORCE" == "1" ]]; then
  echo "RESUME=1 cannot be combined with FORCE=1" >&2
  exit 1
fi

print_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

build_binary_if_needed() {
  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi
  if [[ ! -x "$BIN" ]]; then
    (
      cd "$ROOT"
      make build-fasim-gasal2 \
        CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
        CUDA_ARCH="${CUDA_ARCH:-89}" \
        FASIM_GASAL2_TARGET="$BIN"
    )
  fi
}

write_formal_summary() {
  local report="$1"
  python3 - "$report" "$OUT/summary.tsv" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary_path = Path(sys.argv[2])
sums = report.get("fasim_benchmark_sums", {})
columns = [
    "dna",
    "rna",
    "rule",
    "k",
    "contract",
    "topk_lite",
    "topk_lite_records",
    "topk_lite_digest",
    "topk_summary",
    "topk_summary_payload_digest",
    "run_status",
    "shard_count",
    "resumed_shards_count",
    "group_target_records",
    "grouped_shard_count",
    "activation_verified",
    "query_preflight_supported",
    "query_preflight_query_len",
    "query_preflight_max_query_len",
    "gasal2_requests",
    "gasal2_traceback_requests",
    "exact_scoreinfo_gpu_tasks",
    "gasal2_fallbacks",
    "length_guard_fallbacks",
]
values = {
    "dna": report.get("target", ""),
    "rna": report.get("rna", ""),
    "rule": report.get("rule", ""),
    "k": str((report.get("topk_summary") or {}).get("k", "")),
    "contract": report.get("result_contract", ""),
    "topk_lite": report.get("topk_lite_output", ""),
    "topk_lite_records": str(report.get("topk_lite_records", "")),
    "topk_lite_digest": report.get("topk_lite_digest", ""),
    "topk_summary": report.get("topk_summary_output", ""),
    "topk_summary_payload_digest": report.get("topk_summary_payload_digest", ""),
    "run_status": report.get("run_status", ""),
    "shard_count": str(report.get("shard_count") or ""),
    "resumed_shards_count": str(len(report.get("resumed_shards") or [])),
    "group_target_records": str(report.get("group_target_records") or ""),
    "grouped_shard_count": str(report.get("grouped_shard_count") or ""),
    "activation_verified": str(report.get("gasal2_top5_activation_verified", "")).lower(),
    "query_preflight_supported": str(report.get("gasal2_top5_query_preflight_supported", "")).lower(),
    "query_preflight_query_len": str(report.get("gasal2_top5_query_preflight_query_len", "")),
    "query_preflight_max_query_len": str(report.get("gasal2_top5_query_preflight_max_query_len", "")),
    "gasal2_requests": str(int(sums.get("fasim_gasal2_requests", 0))),
    "gasal2_traceback_requests": str(int(sums.get("fasim_gasal2_traceback_requests", 0))),
    "exact_scoreinfo_gpu_tasks": str(int(sums.get("fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks", 0))),
    "gasal2_fallbacks": str(int(sums.get("fasim_gasal2_fallbacks", 0))),
    "length_guard_fallbacks": str(int(sums.get("fasim_gasal2_length_guard_fallbacks", 0))),
}
summary_path.write_text(
    "\t".join(columns) + "\n" + "\t".join(values[column] for column in columns) + "\n",
    encoding="utf-8",
)
print(summary_path.read_text(encoding="utf-8"), end="")
PY
}

run_formal_runner() {
  local runner_cmd=(
    python3 "$ROOT/scripts/fasim_sharded_runner.py"
    --fasim-bin "$BIN"
    --target "$DNA"
    --rna "$RNA"
    --rule "$RULE"
    --work-dir "$OUT"
    --manifest "$OUT/run_manifest.json"
    --output-mode lite
    --gasal2-top5-column-pruned-scoreinfo
    --workers "$WORKERS"
  )
  if [[ -n "$GPU_IDS" ]]; then
    runner_cmd+=(--gpu-ids "$GPU_IDS")
  fi
  if [[ -n "$GROUP_TARGET_RECORDS" ]]; then
    runner_cmd+=(--group-target-records "$GROUP_TARGET_RECORDS")
  fi
  if [[ "$AUTO_CPU_CORE_RANGES" == "1" ]]; then
    runner_cmd+=(--auto-cpu-core-ranges)
  fi
  if [[ -n "$CPU_POOL" ]]; then
    runner_cmd+=(--cpu-pool "$CPU_POOL")
  fi
  if [[ -n "$CPU_CORES_PER_WORKER" ]]; then
    runner_cmd+=(--cpu-cores-per-worker "$CPU_CORES_PER_WORKER")
  fi
  if [[ "$RESUME" == "1" ]]; then
    runner_cmd+=(--resume)
  fi
  if [[ "$FORCE" == "1" ]]; then
    runner_cmd+=(--force)
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    print_cmd "${runner_cmd[@]}"
    return
  fi

  if [[ "$RESUME" != "1" ]]; then
    rm -rf "$OUT"
  fi
  mkdir -p "$OUT"
  "${runner_cmd[@]}" >"$OUT/stdout.log" 2>"$OUT/stderr.log"
  cp "$OUT/topk-TFOsorted.lite" "$OUT/top${K}.lite"
  write_formal_summary "$OUT/report.json"
}

run_legacy_direct() {
  local -a fasim_env=(
    FASIM_OUTPUT_MODE=lite
    FASIM_VERBOSE=0
    FASIM_TOP5_GASAL2_PHASE_TIMING=1
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK"
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS"
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH"
  )

  if [[ "$IN_PROCESS_TOPK" == "1" ]]; then
    fasim_env+=(FASIM_OUTPUT_TOPK_LITE="$K")
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "LEGACY_DIRECT=1"
    print_cmd env "${fasim_env[@]}" "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$OUT/full"
    return
  fi

  rm -rf "$OUT"
  mkdir -p "$OUT/full"

  local start_seconds end_seconds wall_seconds
  start_seconds="$(date +%s.%N)"
  env "${fasim_env[@]}" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$OUT/full" \
    >"$OUT/stdout.log" 2>"$OUT/stderr.log"
  end_seconds="$(date +%s.%N)"
  wall_seconds="$(awk -v start="$start_seconds" -v end="$end_seconds" 'BEGIN {printf "%.6f", end - start}')"
  printf '%s\n' "$wall_seconds" >"$OUT/wall_seconds.txt"

  mapfile -t lite_outputs < <(find "$OUT/full" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort)
  if [[ "${#lite_outputs[@]}" -ne 1 ]]; then
    echo "expected one lite output, found ${#lite_outputs[@]}" >&2
    printf '%s\n' "${lite_outputs[@]}" >&2
    exit 1
  fi

  local full_lite topk_lite postprocess_topk_lite
  full_lite="${lite_outputs[0]}"
  topk_lite="$OUT/top${K}.lite"
  postprocess_topk_lite=""
  if [[ "$IN_PROCESS_TOPK" == "1" ]]; then
    cp "$full_lite" "$topk_lite"
  else
    python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
      --input "$full_lite" \
      --output "$topk_lite" \
      --k "$K" \
      >"$OUT/topk_extract.txt"
    postprocess_topk_lite="$topk_lite"
  fi

  local full_rows topk_rows topk_digest query_preflight_supported
  local query_preflight_query_len query_preflight_max_query_len
  local gasal2_requests length_guard_fallbacks gasal2_total_seconds
  full_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$full_lite")"
  topk_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$topk_lite")"
  topk_digest="$(sha256sum "$topk_lite" | awk '{print $1}')"
  query_preflight_supported="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=/{print $2}' "$OUT/stderr.log")"
  query_preflight_query_len="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len=/{print $2}' "$OUT/stderr.log")"
  query_preflight_max_query_len="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len=/{print $2}' "$OUT/stderr.log")"
  gasal2_requests="$(awk -F= '/^benchmark\.fasim_gasal2_requests=/{print $2}' "$OUT/stderr.log")"
  length_guard_fallbacks="$(awk -F= '/^benchmark\.fasim_gasal2_length_guard_fallbacks=/{print $2}' "$OUT/stderr.log")"
  gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$OUT/stderr.log")"

  cat >"$OUT/summary.tsv" <<EOF
dna	rna	rule	k	in_process_topk	full_lite	topk_lite	postprocess_topk_lite	full_rows	topk_rows	topk_digest	wall_seconds	query_preflight_supported	query_preflight_query_len	query_preflight_max_query_len	gasal2_requests	length_guard_fallbacks	gasal2_total_seconds
$DNA	$RNA	$RULE	$K	$IN_PROCESS_TOPK	$full_lite	$topk_lite	${postprocess_topk_lite:-}	$full_rows	$topk_rows	$topk_digest	$wall_seconds	${query_preflight_supported:-0}	${query_preflight_query_len:-0}	${query_preflight_max_query_len:-0}	${gasal2_requests:-0}	${length_guard_fallbacks:-0}	${gasal2_total_seconds:-0}
EOF

  cat "$OUT/summary.tsv"
}

build_binary_if_needed
if [[ "$LEGACY_DIRECT" == "1" ]]; then
  run_legacy_direct
else
  run_formal_runner
fi
