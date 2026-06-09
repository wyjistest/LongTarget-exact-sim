#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_sharded_gpu_utilization"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
GPU_IDS="${GPU_IDS:-0,1}"
WORKERS="${WORKERS:-2}"
CPU_POOL="${CPU_POOL:-0-19}"
CPU_CORES_PER_WORKER="${CPU_CORES_PER_WORKER:-3}"
GPU_SAMPLE_INTERVAL_SECONDS="${GPU_SAMPLE_INTERVAL_SECONDS:-1}"
TOPK_SUMMARY_ONLY="${TOPK_SUMMARY_ONLY:-0}"
IN_PROCESS_TOPK="${IN_PROCESS_TOPK:-0}"
TOPK="${TOPK:-5}"
GASAL2_BATCH="${GASAL2_BATCH:-}"
GASAL2_STREAMS="${GASAL2_STREAMS:-}"
GASAL2_NT_SUM_SPAN_PRUNE="${GASAL2_NT_SUM_SPAN_PRUNE:-0}"
GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="${GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK:-}"
GASAL2_SCOREINFO_EMIT_RANK_OBSERVE="${GASAL2_SCOREINFO_EMIT_RANK_OBSERVE:-0}"
GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE="${GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE:-0}"
GASAL2_TOP5_COLUMN_PRUNED_PRESET="${GASAL2_TOP5_COLUMN_PRUNED_PRESET:-0}"
GASAL2_SINGLE_PASS_TOPN="${GASAL2_SINGLE_PASS_TOPN:-0}"
PREALIGN_CUDA_MAX_TASKS="${PREALIGN_CUDA_MAX_TASKS:-}"
EXACT_COLUMN_SCOREINFO_GPU="${EXACT_COLUMN_SCOREINFO_GPU:-0}"
EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK:-}"
EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT="${EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT:-0}"
EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT="${EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT:-0}"
DRY_RUN="${DRY_RUN:-0}"
CHR21="${CHR21:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr21.fa.gz"}"
CHR22="${CHR22:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz"}"
TARGET="${TARGET:-"$WORK/inputs/chr21_chr22.fa"}"

if [[ "$GASAL2_TOP5_COLUMN_PRUNED_PRESET" == "1" ]]; then
  if [[ "$TOPK" != "5" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET requires TOPK=5" >&2
    exit 1
  fi
  if [[ "$TOPK_SUMMARY_ONLY" != "1" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET requires TOPK_SUMMARY_ONLY=1" >&2
    exit 1
  fi
  if [[ "$IN_PROCESS_TOPK" != "1" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET requires IN_PROCESS_TOPK=1" >&2
    exit 1
  fi
  if [[ -n "$GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK" >&2
    exit 1
  fi
  if [[ "$GASAL2_SINGLE_PASS_TOPN" == "1" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with GASAL2_SINGLE_PASS_TOPN=1" >&2
    exit 1
  fi
  if [[ -n "$PREALIGN_CUDA_MAX_TASKS" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with PREALIGN_CUDA_MAX_TASKS" >&2
    exit 1
  fi
  if [[ "$GASAL2_NT_SUM_SPAN_PRUNE" == "1" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with GASAL2_NT_SUM_SPAN_PRUNE" >&2
    exit 1
  fi
  if [[ "$EXACT_COLUMN_SCOREINFO_GPU" == "1" || -n "$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK" || "$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" == "1" || "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
    echo "GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with manual exact-column scoreInfo settings" >&2
    exit 1
  fi
fi

if [[ -n "$GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK" ]]; then
  if [[ "$TOPK" != "5" ]]; then
    echo "GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires TOPK=5" >&2
    exit 1
  fi
  if [[ "$TOPK_SUMMARY_ONLY" != "1" ]]; then
    echo "GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires TOPK_SUMMARY_ONLY=1" >&2
    exit 1
  fi
  if [[ "$IN_PROCESS_TOPK" != "1" ]]; then
    echo "GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires IN_PROCESS_TOPK=1" >&2
    exit 1
  fi
fi

runner_args=()
if [[ "$TOPK_SUMMARY_ONLY" == "1" ]]; then
  runner_args+=(--topk-summary-only)
fi
if [[ "$IN_PROCESS_TOPK" == "1" ]]; then
  runner_args+=(--shard-output-topk-lite "$TOPK")
fi
if [[ -n "$GASAL2_BATCH" ]]; then
  runner_args+=(--env "FASIM_ALIGN_GASAL2_BATCH=$GASAL2_BATCH")
fi
if [[ -n "$GASAL2_STREAMS" ]]; then
  runner_args+=(--env "FASIM_ALIGN_GASAL2_STREAMS=$GASAL2_STREAMS")
fi
if [[ "$GASAL2_NT_SUM_SPAN_PRUNE" == "1" ]]; then
  runner_args+=(--env FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE=1)
fi
if [[ -n "$PREALIGN_CUDA_MAX_TASKS" ]]; then
  runner_args+=(--env "FASIM_PREALIGN_CUDA_MAX_TASKS=$PREALIGN_CUDA_MAX_TASKS")
fi
if [[ "$GASAL2_SCOREINFO_EMIT_RANK_OBSERVE" == "1" ]]; then
  runner_args+=(--env FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE=1)
fi
if [[ "$GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE" == "1" ]]; then
  runner_args+=(--env FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1)
fi
if [[ "$GASAL2_TOP5_COLUMN_PRUNED_PRESET" == "1" ]]; then
  runner_args+=(--gasal2-top5-column-pruned-scoreinfo)
elif [[ -n "$GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK" ]]; then
  runner_args+=(--gasal2-top5-scoreinfo-prune-max-per-task "$GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK")
  if [[ "$GASAL2_SINGLE_PASS_TOPN" == "1" ]]; then
    runner_args+=(--gasal2-single-pass-topn)
  fi
  if [[ "$EXACT_COLUMN_SCOREINFO_GPU" == "1" ]]; then
    runner_args+=(--exact-scoreinfo-gpu-max-per-task "${EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK:-2048}")
    if [[ "$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" == "1" ]]; then
      runner_args+=(--exact-scoreinfo-gpu-pruned-output)
      if [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
        runner_args+=(--exact-scoreinfo-gpu-column-pruned-output)
      fi
    elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
      echo "EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1" >&2
      exit 1
    fi
  elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" == "1" ]]; then
    echo "EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU=1" >&2
    exit 1
  elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
    echo "EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU=1" >&2
    exit 1
  fi
else
  if [[ "$GASAL2_SINGLE_PASS_TOPN" == "1" ]]; then
    echo "GASAL2_SINGLE_PASS_TOPN requires GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK" >&2
    exit 1
  fi
  runner_args+=(
    --env FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
    --env FASIM_TOP5_GASAL2_PHASE_TIMING=1
  )
  if [[ "$EXACT_COLUMN_SCOREINFO_GPU" == "1" ]]; then
    runner_args+=(--env FASIM_EXACT_COLUMN_SCOREINFO_GPU=1)
    if [[ -n "$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK" ]]; then
      runner_args+=(--env "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK")
    fi
    if [[ "$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" == "1" ]]; then
      runner_args+=(--env FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1)
      if [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
        runner_args+=(--env FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1)
      fi
    elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
      echo "EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1" >&2
      exit 1
    fi
  elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" == "1" ]]; then
    echo "EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU=1" >&2
    exit 1
  elif [[ "$EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT" == "1" ]]; then
    echo "EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU=1" >&2
    exit 1
  fi
fi

runner_cmd=(
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/run" \
  --manifest "$WORK/run/run_manifest.json" \
  --output-mode lite \
  --topk-summary "$TOPK" \
  --workers "$WORKERS" \
  --gpu-ids "$GPU_IDS" \
  --auto-cpu-core-ranges \
  --cpu-pool "$CPU_POOL" \
  --cpu-cores-per-worker "$CPU_CORES_PER_WORKER" \
  --env FASIM_VERBOSE=0 \
  "${runner_args[@]}" \
  "$@"
)
if [[ "$DRY_RUN" == "1" ]]; then
  printf '%q ' "${runner_cmd[@]}"
  printf '\n'
  exit 0
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

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"

if [[ "$TARGET" == "$WORK/inputs/chr21_chr22.fa" ]]; then
  gzip -dc "$CHR21" >"$TARGET"
  gzip -dc "$CHR22" >>"$TARGET"
fi

sampler_pid=""
gpu_samples="$WORK/gpu_utilization.csv"
gpu_sampler_stderr="$WORK/gpu_utilization.stderr.log"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi \
    --query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total \
    --format=csv,noheader,nounits \
    -l "$GPU_SAMPLE_INTERVAL_SECONDS" \
    >"$gpu_samples" 2>"$gpu_sampler_stderr" &
  sampler_pid="$!"
fi

cleanup_sampler() {
  if [[ -n "$sampler_pid" ]]; then
    kill "$sampler_pid" >/dev/null 2>&1 || true
    wait "$sampler_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup_sampler EXIT

start_seconds="$(date +%s.%N)"
"${runner_cmd[@]}" >"$WORK/runner.stdout.log" 2>"$WORK/runner.stderr.log"
end_seconds="$(date +%s.%N)"
cleanup_sampler
trap - EXIT

wall_seconds="$(awk -v start="$start_seconds" -v end="$end_seconds" 'BEGIN {printf "%.6f", end - start}')"
printf '%s\n' "$wall_seconds" >"$WORK/wall_seconds.txt"

gpu_rows_tmp="$WORK/gpu_utilization_rows.tmp"
gpu_summary="$WORK/gpu_utilization_summary.csv"
if [[ -s "$gpu_samples" ]]; then
  awk -F, '
    function trim(value) {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      return value
    }
    NF >= 6 {
      idx = trim($2)
      gpu = trim($3) + 0
      mem = trim($4) + 0
      used = trim($5) + 0
      total = trim($6) + 0
      count[idx] += 1
      gpu_sum[idx] += gpu
      mem_sum[idx] += mem
      if (count[idx] == 1 || gpu > gpu_max[idx]) gpu_max[idx] = gpu
      if (count[idx] == 1 || mem > mem_max[idx]) mem_max[idx] = mem
      if (count[idx] == 1 || used > used_max[idx]) used_max[idx] = used
      total_mem[idx] = total
    }
    END {
      for (idx in count) {
        printf "%s,%d,%.6f,%d,%.6f,%d,%d,%d\n",
          idx,
          count[idx],
          gpu_sum[idx] / count[idx],
          gpu_max[idx],
          mem_sum[idx] / count[idx],
          mem_max[idx],
          used_max[idx],
          total_mem[idx]
      }
    }
  ' "$gpu_samples" | sort -t, -k1,1n >"$gpu_rows_tmp"
else
  : >"$gpu_rows_tmp"
fi
{
  echo "gpu_index,samples,gpu_util_avg,gpu_util_max,mem_util_avg,mem_util_max,mem_used_max_mib,mem_total_mib"
  cat "$gpu_rows_tmp"
} >"$gpu_summary"
rm -f "$gpu_rows_tmp"

python3 - "$WORK/run/report.json" "$WORK/shard_benchmark_summary.tsv" <<'PY'
import json
import re
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])

def metric(path: Path, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$")
    try:
        for line in path.read_text(errors="replace").splitlines():
            match = pattern.match(line)
            if match:
                return match.group(1)
    except FileNotFoundError:
        return ""
    return ""

rows = []
for shard in report["per_shard"]:
    stderr = Path(shard["run"]["stderr_path"])
    rows.append(
        {
            "shard_id": shard["shard_id"],
            "worker_id": str(shard["worker_id"]),
            "gpu_id": str(shard["gpu_id"]),
            "wall_seconds": f'{float(shard["run"]["wall_seconds"]):.6f}',
            "records": str(shard["records"]),
            "traceback_requests": metric(stderr, "benchmark.fasim_gasal2_traceback_requests"),
            "scoreinfo_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_groups",
            ),
            "exact_scoreinfo_gpu_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled",
            ),
            "exact_scoreinfo_gpu_batches": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches",
            ),
            "exact_scoreinfo_gpu_tasks": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks",
            ),
            "exact_scoreinfo_gpu_overflow_batches": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
            ),
            "exact_scoreinfo_gpu_fallback_batches": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
            ),
            "exact_scoreinfo_gpu_pruned_output_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled",
            ),
            "exact_scoreinfo_gpu_pruned_output_batches": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_batches",
            ),
            "exact_scoreinfo_gpu_pruned_output_input_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_input_groups",
            ),
            "exact_scoreinfo_gpu_pruned_output_kept_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_kept_groups",
            ),
            "exact_scoreinfo_gpu_pruned_output_pruned_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_pruned_groups",
            ),
            "exact_scoreinfo_gpu_pruned_output_pruned_tasks": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_pruned_tasks",
            ),
            "single_pass_topn_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_single_pass_topn_enabled",
            ),
            "single_pass_topn_batches": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_single_pass_topn_batches",
            ),
            "single_pass_topn_tasks": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_single_pass_topn_tasks",
            ),
            "single_pass_topn_scoreinfo_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_single_pass_topn_scoreinfo_groups",
            ),
            "scoreinfo_prune_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_enabled",
            ),
            "scoreinfo_prune_max_per_task": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task",
            ),
            "scoreinfo_prune_input_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_input_groups",
            ),
            "scoreinfo_prune_kept_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_kept_groups",
            ),
            "scoreinfo_prune_pruned_groups": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_groups",
            ),
            "scoreinfo_prune_pruned_tasks": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_tasks",
            ),
            "scoreinfo_emit_rank_observe_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_enabled",
            ),
            "scoreinfo_emit_rank_observe_alignments": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_alignments",
            ),
            "scoreinfo_emit_rank_observe_max_rank": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_max_rank",
            ),
            "scoreinfo_emit_rank_observe_rank1": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank1",
            ),
            "scoreinfo_emit_rank_observe_rank2_4": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank2_4",
            ),
            "scoreinfo_emit_rank_observe_rank5_8": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank5_8",
            ),
            "scoreinfo_emit_rank_observe_rank9_16": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank9_16",
            ),
            "scoreinfo_emit_rank_observe_rank17_32": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank17_32",
            ),
            "scoreinfo_emit_rank_observe_rank33_plus": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank33_plus",
            ),
            "scoreinfo_topk_lite_rank_observe_enabled": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled",
            ),
            "scoreinfo_topk_lite_rank_observe_rows": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows",
            ),
            "scoreinfo_topk_lite_rank_observe_unknown_rows": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows",
            ),
            "scoreinfo_topk_lite_rank_observe_max_rank": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank",
            ),
            "scoreinfo_topk_lite_rank_observe_rank1": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank1",
            ),
            "scoreinfo_topk_lite_rank_observe_rank2_4": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank2_4",
            ),
            "scoreinfo_topk_lite_rank_observe_rank5_8": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank5_8",
            ),
            "scoreinfo_topk_lite_rank_observe_rank9_16": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank9_16",
            ),
            "scoreinfo_topk_lite_rank_observe_rank17_32": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank17_32",
            ),
            "scoreinfo_topk_lite_rank_observe_rank33_plus": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank33_plus",
            ),
            "selected_alignments": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_selected_alignments",
            ),
            "convert_input_alignments": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_input_alignments",
            ),
            "convert_raw_triplexes": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplexes_raw",
            ),
            "convert_tasks": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_tasks",
            ),
            "convert_tasks_with_input": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_tasks_with_input",
            ),
            "emit_candidates": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_candidates",
            ),
            "emit_filtered_score": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_score",
            ),
            "emit_filtered_identity": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_identity",
            ),
            "emit_filtered_stability": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_stability",
            ),
            "emit_filtered_nt": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_nt",
            ),
            "emit_rows_lite": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_lite",
            ),
            "nt_shadow_query_span_lt_clength": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_query_span_lt_clength",
            ),
            "nt_shadow_ref_span_lt_clength": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_ref_span_lt_clength",
            ),
            "nt_shadow_min_span_lt_clength": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_min_span_lt_clength",
            ),
            "nt_shadow_max_span_lt_clength": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_max_span_lt_clength",
            ),
            "nt_shadow_sum_span_lt_clength": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_sum_span_lt_clength",
            ),
            "nt_shadow_query_span_false_negative": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_query_span_false_negative",
            ),
            "nt_shadow_ref_span_false_negative": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_ref_span_false_negative",
            ),
            "nt_shadow_min_span_false_negative": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_min_span_false_negative",
            ),
            "nt_shadow_max_span_false_negative": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_max_span_false_negative",
            ),
            "nt_shadow_sum_span_false_negative": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_sum_span_false_negative",
            ),
            "nt_sum_span_prune_active": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_nt_sum_span_prune_active",
            ),
            "bridge_nt_sum_span_prune_enabled": metric(
                stderr,
                "benchmark.fasim_gasal2_nt_sum_span_prune_enabled",
            ),
            "bridge_nt_sum_span_pruned_attempts": metric(
                stderr,
                "benchmark.fasim_gasal2_nt_sum_span_pruned_attempts",
            ),
            "bridge_nt_sum_span_pruned_groups": metric(
                stderr,
                "benchmark.fasim_gasal2_nt_sum_span_pruned_groups",
            ),
            "query_preflight_supported": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported",
            ),
            "query_preflight_query_len": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len",
            ),
            "query_preflight_max_query_len": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len",
            ),
            "length_guard_fallbacks": metric(
                stderr,
                "benchmark.fasim_gasal2_length_guard_fallbacks",
            ),
            "length_guard_last_query_len": metric(
                stderr,
                "benchmark.fasim_gasal2_length_guard_last_query_len",
            ),
            "length_guard_max_query_len": metric(
                stderr,
                "benchmark.fasim_gasal2_length_guard_max_query_len",
            ),
            "length_guard_last_target_len": metric(
                stderr,
                "benchmark.fasim_gasal2_length_guard_last_target_len",
            ),
            "length_guard_max_target_len": metric(
                stderr,
                "benchmark.fasim_gasal2_length_guard_max_target_len",
            ),
            "gasal2_total_seconds": metric(stderr, "benchmark.fasim_gasal2_total_seconds"),
            "gasal2_effective_streams": metric(stderr, "benchmark.fasim_gasal2_effective_streams"),
            "gasal2_wait_seconds": metric(stderr, "benchmark.fasim_gasal2_wait_seconds"),
            "gasal2_score_wait_seconds": metric(stderr, "benchmark.fasim_gasal2_score_wait_seconds"),
            "gasal2_traceback_wait_seconds": metric(stderr, "benchmark.fasim_gasal2_traceback_wait_seconds"),
            "gasal2_score_fill_seconds": metric(stderr, "benchmark.fasim_gasal2_score_fill_seconds"),
            "gasal2_traceback_fill_seconds": metric(stderr, "benchmark.fasim_gasal2_traceback_fill_seconds"),
            "gasal2_score_submit_seconds": metric(stderr, "benchmark.fasim_gasal2_score_submit_seconds"),
            "gasal2_traceback_submit_seconds": metric(stderr, "benchmark.fasim_gasal2_traceback_submit_seconds"),
            "gasal2_score_result_copy_seconds": metric(
                stderr,
                "benchmark.fasim_gasal2_score_result_copy_seconds",
            ),
            "gasal2_traceback_result_copy_seconds": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_result_copy_seconds",
            ),
            "gasal2_traceback_cigar_vector_seconds": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_cigar_vector_seconds",
            ),
            "gasal2_traceback_cigar_string_seconds": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_cigar_string_seconds",
            ),
            "gasal2_traceback_cigar_raw_ops": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_cigar_raw_ops",
            ),
            "gasal2_traceback_cigar_merged_ops": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_cigar_merged_ops",
            ),
            "gasal2_convert_alignment_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds",
            ),
            "gasal2_convert_sort_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds",
            ),
            "gasal2_convert_filter_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds",
            ),
            "gasal2_convert_rank_map_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds",
            ),
            "legacy_score_gpu_replacement_enabled": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_replacement_enabled",
            ),
            "legacy_score_gpu_requests": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_requests",
            ),
            "legacy_score_gpu_batches": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_batches",
            ),
            "legacy_score_gpu_cells": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_cells",
            ),
            "legacy_score_gpu_replacement_used": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_replacement_used",
            ),
            "legacy_score_gpu_replacement_fallbacks": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_replacement_fallbacks",
            ),
            "legacy_score_gpu_mismatches": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_mismatches",
            ),
            "legacy_score_gpu_min_score_mismatches": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_min_score_mismatches",
            ),
            "legacy_score_gpu_wall_seconds": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_wall_seconds",
            ),
            "legacy_score_gpu_kernel_seconds": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_kernel_seconds",
            ),
            "legacy_score_gpu_h2d_seconds": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_h2d_seconds",
            ),
            "legacy_score_gpu_d2h_seconds": metric(
                stderr,
                "benchmark.fasim_exact_column_legacy_score_gpu_shadow_d2h_seconds",
            ),
            "exact_scoreinfo_gpu_wall_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds",
            ),
            "exact_scoreinfo_gpu_kernel_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds",
            ),
            "exact_scoreinfo_gpu_h2d_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds",
            ),
            "exact_scoreinfo_gpu_d2h_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds",
            ),
            "exact_column_kernel_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds",
            ),
            "exact_column_wall_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds",
            ),
            "exact_column_h2d_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds",
            ),
            "exact_column_d2h_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds",
            ),
            "transfer_table_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_transfer_table_seconds",
            ),
            "transfer_reverse_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_transfer_reverse_seconds",
            ),
            "src_transform_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_seconds",
            ),
            "transfer_calls": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_transfer_calls",
            ),
            "transfer_bytes": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_transfer_bytes",
            ),
            "transfer_reverse_calls": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_transfer_reverse_calls",
            ),
            "src_transform_calls": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_calls",
            ),
            "src_transform_bytes": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_bytes",
            ),
            "src_transform_orig": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_orig",
            ),
            "src_transform_comp": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_comp",
            ),
            "src_transform_rev": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_rev",
            ),
            "src_transform_revcomp": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_src_transform_revcomp",
            ),
            "encode_dual_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_encode_dual_seconds",
            ),
            "encode_prealign_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_encode_prealign_seconds",
            ),
            "encode_legacy_seconds": metric(
                stderr,
                "benchmark.fasim_top5_gasal2_phase_encode_legacy_seconds",
            ),
            "traceback_query_reuse_saved_bytes": metric(
                stderr,
                "benchmark.fasim_gasal2_traceback_query_reuse_saved_bytes",
            ),
        }
    )

columns = [
    "shard_id",
    "worker_id",
    "gpu_id",
    "wall_seconds",
    "records",
    "traceback_requests",
    "scoreinfo_groups",
    "exact_scoreinfo_gpu_enabled",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_tasks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
    "exact_scoreinfo_gpu_pruned_output_enabled",
    "exact_scoreinfo_gpu_pruned_output_batches",
    "exact_scoreinfo_gpu_pruned_output_input_groups",
    "exact_scoreinfo_gpu_pruned_output_kept_groups",
    "exact_scoreinfo_gpu_pruned_output_pruned_groups",
    "exact_scoreinfo_gpu_pruned_output_pruned_tasks",
    "single_pass_topn_enabled",
    "single_pass_topn_batches",
    "single_pass_topn_tasks",
    "single_pass_topn_scoreinfo_groups",
    "scoreinfo_prune_enabled",
    "scoreinfo_prune_max_per_task",
    "scoreinfo_prune_input_groups",
    "scoreinfo_prune_kept_groups",
    "scoreinfo_prune_pruned_groups",
    "scoreinfo_prune_pruned_tasks",
    "scoreinfo_emit_rank_observe_enabled",
    "scoreinfo_emit_rank_observe_alignments",
    "scoreinfo_emit_rank_observe_max_rank",
    "scoreinfo_emit_rank_observe_rank1",
    "scoreinfo_emit_rank_observe_rank2_4",
    "scoreinfo_emit_rank_observe_rank5_8",
    "scoreinfo_emit_rank_observe_rank9_16",
    "scoreinfo_emit_rank_observe_rank17_32",
    "scoreinfo_emit_rank_observe_rank33_plus",
    "scoreinfo_topk_lite_rank_observe_enabled",
    "scoreinfo_topk_lite_rank_observe_rows",
    "scoreinfo_topk_lite_rank_observe_unknown_rows",
    "scoreinfo_topk_lite_rank_observe_max_rank",
    "scoreinfo_topk_lite_rank_observe_rank1",
    "scoreinfo_topk_lite_rank_observe_rank2_4",
    "scoreinfo_topk_lite_rank_observe_rank5_8",
    "scoreinfo_topk_lite_rank_observe_rank9_16",
    "scoreinfo_topk_lite_rank_observe_rank17_32",
    "scoreinfo_topk_lite_rank_observe_rank33_plus",
    "selected_alignments",
    "convert_input_alignments",
    "convert_raw_triplexes",
    "convert_tasks",
    "convert_tasks_with_input",
    "emit_candidates",
    "emit_filtered_score",
    "emit_filtered_identity",
    "emit_filtered_stability",
    "emit_filtered_nt",
    "emit_rows_lite",
    "nt_shadow_query_span_lt_clength",
    "nt_shadow_ref_span_lt_clength",
    "nt_shadow_min_span_lt_clength",
    "nt_shadow_max_span_lt_clength",
    "nt_shadow_sum_span_lt_clength",
    "nt_shadow_query_span_false_negative",
    "nt_shadow_ref_span_false_negative",
    "nt_shadow_min_span_false_negative",
    "nt_shadow_max_span_false_negative",
    "nt_shadow_sum_span_false_negative",
    "nt_sum_span_prune_active",
    "bridge_nt_sum_span_prune_enabled",
    "bridge_nt_sum_span_pruned_attempts",
    "bridge_nt_sum_span_pruned_groups",
    "query_preflight_supported",
    "query_preflight_query_len",
    "query_preflight_max_query_len",
    "length_guard_fallbacks",
    "length_guard_last_query_len",
    "length_guard_max_query_len",
    "length_guard_last_target_len",
    "length_guard_max_target_len",
    "gasal2_total_seconds",
    "gasal2_effective_streams",
    "gasal2_wait_seconds",
    "gasal2_score_wait_seconds",
    "gasal2_traceback_wait_seconds",
    "gasal2_score_fill_seconds",
    "gasal2_traceback_fill_seconds",
    "gasal2_score_submit_seconds",
    "gasal2_traceback_submit_seconds",
    "gasal2_score_result_copy_seconds",
    "gasal2_traceback_result_copy_seconds",
    "gasal2_traceback_cigar_vector_seconds",
    "gasal2_traceback_cigar_string_seconds",
    "gasal2_traceback_cigar_raw_ops",
    "gasal2_traceback_cigar_merged_ops",
    "gasal2_convert_alignment_seconds",
    "gasal2_convert_sort_seconds",
    "gasal2_convert_filter_seconds",
    "gasal2_convert_rank_map_seconds",
    "legacy_score_gpu_replacement_enabled",
    "legacy_score_gpu_requests",
    "legacy_score_gpu_batches",
    "legacy_score_gpu_cells",
    "legacy_score_gpu_replacement_used",
    "legacy_score_gpu_replacement_fallbacks",
    "legacy_score_gpu_mismatches",
    "legacy_score_gpu_min_score_mismatches",
    "legacy_score_gpu_wall_seconds",
    "legacy_score_gpu_kernel_seconds",
    "legacy_score_gpu_h2d_seconds",
    "legacy_score_gpu_d2h_seconds",
    "exact_scoreinfo_gpu_wall_seconds",
    "exact_scoreinfo_gpu_kernel_seconds",
    "exact_scoreinfo_gpu_h2d_seconds",
    "exact_scoreinfo_gpu_d2h_seconds",
    "exact_column_kernel_seconds",
    "exact_column_wall_seconds",
    "exact_column_h2d_seconds",
    "exact_column_d2h_seconds",
    "transfer_table_seconds",
    "transfer_reverse_seconds",
    "src_transform_seconds",
    "transfer_calls",
    "transfer_bytes",
    "transfer_reverse_calls",
    "src_transform_calls",
    "src_transform_bytes",
    "src_transform_orig",
    "src_transform_comp",
    "src_transform_rev",
    "src_transform_revcomp",
    "encode_dual_seconds",
    "encode_prealign_seconds",
    "encode_legacy_seconds",
    "traceback_query_reuse_saved_bytes",
]
out.write_text(
    "\t".join(columns)
    + "\n"
    + "\n".join("\t".join(row[column] for column in columns) for row in rows)
    + "\n",
    encoding="utf-8",
)
PY

report_json="$WORK/run/report.json"
merged_digest="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["merged_digest"])
PY
)"
merged_records="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["merged_records"])
PY
)"
duplicate_removed="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["duplicate_records_removed"])
PY
)"
topk_summary_only="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["topk_summary_only"])
PY
)"
merge_seconds="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["merge_seconds"])
PY
)"
topk_summary_seconds="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["topk_summary_seconds"])
PY
)"
top5_score_digest="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["topk_summary"]["modes"]["score"]["digest"])
PY
)"
top5_stability_digest="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["topk_summary"]["modes"]["stability"]["digest"])
PY
)"
top5_nt_score_digest="$(python3 - "$report_json" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["topk_summary"]["modes"]["nt_score"]["digest"])
PY
)"
runner_gasal2_top5_scoreinfo_prune_max_per_task="$(python3 - "$report_json" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1]).read()).get("gasal2_top5_scoreinfo_prune_max_per_task")
print("" if value is None else value)
PY
)"
runner_exact_scoreinfo_gpu_max_per_task="$(python3 - "$report_json" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1]).read()).get("exact_scoreinfo_gpu_max_per_task")
print("" if value is None else value)
PY
)"
runner_exact_scoreinfo_gpu_pruned_output="$(python3 - "$report_json" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1]).read()).get("exact_scoreinfo_gpu_pruned_output")
print("1" if value else "0")
PY
)"
runner_exact_scoreinfo_gpu_column_pruned_output="$(python3 - "$report_json" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1]).read()).get("exact_scoreinfo_gpu_column_pruned_output")
print("1" if value else "0")
PY
)"
runner_gasal2_single_pass_topn="$(python3 - "$report_json" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1]).read()).get("gasal2_single_pass_topn")
print("1" if value else "0")
PY
)"
effective_batch_size="$(python3 - "$WORK/shard_benchmark_summary.tsv" <<'PY'
import csv
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("")
    raise SystemExit

stderr_paths = []
report_path = path.parent / "run" / "report.json"
if report_path.exists():
    import json

    report = json.loads(report_path.read_text())
    stderr_paths = [
        shard["run"]["stderr_path"]
        for shard in report.get("per_shard", [])
        if shard.get("run", {}).get("stderr_path")
    ]

pattern = re.compile(r"^benchmark\.fasim_gasal2_effective_batch_size=(.*)$")
for stderr in stderr_paths:
    try:
        for line in Path(stderr).read_text(errors="replace").splitlines():
            match = pattern.match(line)
            if match:
                print(match.group(1))
                raise SystemExit
    except FileNotFoundError:
        pass
print("")
PY
)"
effective_streams="$(python3 - "$WORK/shard_benchmark_summary.tsv" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("")
    raise SystemExit

stderr_paths = []
report_path = path.parent / "run" / "report.json"
if report_path.exists():
    import json

    report = json.loads(report_path.read_text())
    stderr_paths = [
        shard["run"]["stderr_path"]
        for shard in report.get("per_shard", [])
        if shard.get("run", {}).get("stderr_path")
    ]

pattern = re.compile(r"^benchmark\.fasim_gasal2_effective_streams=(.*)$")
for stderr in stderr_paths:
    try:
        for line in Path(stderr).read_text(errors="replace").splitlines():
            match = pattern.match(line)
            if match:
                print(match.group(1))
                raise SystemExit
    except FileNotFoundError:
        pass
print("")
PY
)"

cat >"$WORK/summary.txt" <<EOF
target=$TARGET
rna=$RNA
rule=$RULE
wall_seconds=$wall_seconds
workers=$WORKERS
gpu_ids=$GPU_IDS
cpu_pool=$CPU_POOL
cpu_cores_per_worker=$CPU_CORES_PER_WORKER
gasal2_batch=$GASAL2_BATCH
gasal2_streams=$GASAL2_STREAMS
gasal2_nt_sum_span_prune=$GASAL2_NT_SUM_SPAN_PRUNE
gasal2_scoreinfo_prune_max_per_task=$GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK
gasal2_single_pass_topn=$GASAL2_SINGLE_PASS_TOPN
prealign_cuda_max_tasks=$PREALIGN_CUDA_MAX_TASKS
exact_column_scoreinfo_gpu=$EXACT_COLUMN_SCOREINFO_GPU
exact_column_scoreinfo_gpu_max_per_task=$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK
exact_column_scoreinfo_gpu_pruned_output=$EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT
runner_gasal2_top5_scoreinfo_prune_max_per_task=$runner_gasal2_top5_scoreinfo_prune_max_per_task
runner_exact_scoreinfo_gpu_max_per_task=$runner_exact_scoreinfo_gpu_max_per_task
runner_exact_scoreinfo_gpu_pruned_output=$runner_exact_scoreinfo_gpu_pruned_output
runner_exact_scoreinfo_gpu_column_pruned_output=$runner_exact_scoreinfo_gpu_column_pruned_output
runner_gasal2_single_pass_topn=$runner_gasal2_single_pass_topn
gasal2_effective_streams=$effective_streams
gasal2_effective_batch_size=$effective_batch_size
topk=$TOPK
in_process_topk=$IN_PROCESS_TOPK
topk_summary_only=$topk_summary_only
merged_digest=$merged_digest
merged_records=$merged_records
duplicate_records_removed=$duplicate_removed
merge_seconds=$merge_seconds
topk_summary_seconds=$topk_summary_seconds
top5_score_digest=$top5_score_digest
top5_stability_digest=$top5_stability_digest
top5_nt_score_digest=$top5_nt_score_digest
runner_report=$report_json
gpu_utilization_summary=$gpu_summary
shard_benchmark_summary=$WORK/shard_benchmark_summary.tsv
runner_stdout=$WORK/runner.stdout.log
runner_stderr=$WORK/runner.stderr.log
EOF

cat "$WORK/summary.txt"
echo
cat "$gpu_summary"
echo
cat "$WORK/shard_benchmark_summary.tsv"
