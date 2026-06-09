#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_sharded_characterization_env"}"

rm -rf "$WORK"
mkdir -p "$WORK"

if TOPK=3 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  WORK="$WORK/topk_not_5" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/topk_not_5.stdout.log" \
  2>"$WORK/topk_not_5.stderr.log"; then
  echo "expected TOPK!=5 scoreInfo-prune characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires TOPK=5' \
  "$WORK/topk_not_5.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=0 \
  IN_PROCESS_TOPK=1 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  WORK="$WORK/no_summary_only" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/no_summary_only.stdout.log" \
  2>"$WORK/no_summary_only.stderr.log"; then
  echo "expected missing TOPK_SUMMARY_ONLY scoreInfo-prune characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires TOPK_SUMMARY_ONLY=1' \
  "$WORK/no_summary_only.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=0 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  WORK="$WORK/no_inprocess_topk" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/no_inprocess_topk.stdout.log" \
  2>"$WORK/no_inprocess_topk.stderr.log"; then
  echo "expected missing IN_PROCESS_TOPK scoreInfo-prune characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK requires IN_PROCESS_TOPK=1' \
  "$WORK/no_inprocess_topk.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
  PREALIGN_CUDA_MAX_TASKS=16384 \
  DRY_RUN=1 \
  WORK="$WORK/preset_with_prealign_max_tasks" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/preset_with_prealign_max_tasks.stdout.log" \
  2>"$WORK/preset_with_prealign_max_tasks.stderr.log"; then
  echo "expected formal preset plus PREALIGN_CUDA_MAX_TASKS characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with PREALIGN_CUDA_MAX_TASKS' \
  "$WORK/preset_with_prealign_max_tasks.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
  GASAL2_NT_SUM_SPAN_PRUNE=1 \
  DRY_RUN=1 \
  WORK="$WORK/preset_with_nt_sum_span_prune" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/preset_with_nt_sum_span_prune.stdout.log" \
  2>"$WORK/preset_with_nt_sum_span_prune.stderr.log"; then
  echo "expected formal preset plus GASAL2_NT_SUM_SPAN_PRUNE characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with GASAL2_NT_SUM_SPAN_PRUNE' \
  "$WORK/preset_with_nt_sum_span_prune.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
  GASAL2_SCOREINFO_EMIT_RANK_OBSERVE=1 \
  GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1 \
  DRY_RUN=1 \
  WORK="$WORK/column_pruned_preset" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/column_pruned_preset.stdout.log" \
  2>"$WORK/column_pruned_preset.stderr.log"; then
  :
else
  echo "expected column-pruned preset dry-run characterization to succeed" >&2
  cat "$WORK/column_pruned_preset.stderr.log" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo' "$WORK/column_pruned_preset.stdout.log"
grep -q -- '--shard-output-topk-lite 5' "$WORK/column_pruned_preset.stdout.log"
grep -q -- 'FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE=1' "$WORK/column_pruned_preset.stdout.log"
grep -q -- 'FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1' "$WORK/column_pruned_preset.stdout.log"
if grep -q -- 'FASIM_PREALIGN_CUDA_MAX_TASKS=' "$WORK/column_pruned_preset.stdout.log"; then
  echo "expected formal preset helper not to emit PREALIGN_CUDA_MAX_TASKS" >&2
  exit 1
fi
if grep -q -- '--gasal2-top5-scoreinfo-prune-max-per-task' "$WORK/column_pruned_preset.stdout.log"; then
  echo "expected column-pruned preset helper to use the formal preset flag" >&2
  exit 1
fi

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  DRY_RUN=1 \
  WORK="$WORK/preset_with_manual_prune" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/preset_with_manual_prune.stdout.log" \
  2>"$WORK/preset_with_manual_prune.stderr.log"; then
  echo "expected formal preset plus manual prune characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK' \
  "$WORK/preset_with_manual_prune.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
  EXACT_COLUMN_SCOREINFO_GPU=1 \
  DRY_RUN=1 \
  WORK="$WORK/preset_with_manual_exact" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/preset_with_manual_exact.stdout.log" \
  2>"$WORK/preset_with_manual_exact.stderr.log"; then
  echo "expected formal preset plus manual exact characterization to fail" >&2
  exit 1
fi
grep -q 'GASAL2_TOP5_COLUMN_PRUNED_PRESET cannot be combined with manual exact-column scoreInfo settings' \
  "$WORK/preset_with_manual_exact.stderr.log"

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  EXACT_COLUMN_SCOREINFO_GPU=1 \
  EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512 \
  EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
  DRY_RUN=1 \
  WORK="$WORK/runner_exact_option" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/runner_exact_option.stdout.log" \
  2>"$WORK/runner_exact_option.stderr.log"; then
  :
else
  echo "expected dry-run characterization to succeed" >&2
  cat "$WORK/runner_exact_option.stderr.log" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-scoreinfo-prune-max-per-task' "$WORK/runner_exact_option.stdout.log"
grep -q -- '--exact-scoreinfo-gpu-max-per-task' "$WORK/runner_exact_option.stdout.log"
grep -q -- '--exact-scoreinfo-gpu-pruned-output' "$WORK/runner_exact_option.stdout.log"
if grep -q -- 'FASIM_EXACT_COLUMN_SCOREINFO_GPU=1' "$WORK/runner_exact_option.stdout.log"; then
  echo "expected prune exact scoreInfo helper to use runner option, not raw env" >&2
  exit 1
fi
if grep -q -- 'FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1' "$WORK/runner_exact_option.stdout.log"; then
  echo "expected pruned exact scoreInfo helper to use runner option, not raw env" >&2
  exit 1
fi

if TOPK=5 \
  TOPK_SUMMARY_ONLY=1 \
  IN_PROCESS_TOPK=1 \
  GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
  EXACT_COLUMN_SCOREINFO_GPU=0 \
  EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
  DRY_RUN=1 \
  WORK="$WORK/pruned_without_exact" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
  >"$WORK/pruned_without_exact.stdout.log" \
  2>"$WORK/pruned_without_exact.stderr.log"; then
  echo "expected scoreInfo pruned output without exact GPU to fail" >&2
  exit 1
fi
grep -q 'EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT requires EXACT_COLUMN_SCOREINFO_GPU=1' \
  "$WORK/pruned_without_exact.stderr.log"

echo "ok"
