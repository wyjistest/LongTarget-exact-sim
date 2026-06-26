#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md"
BROADER_DOC="$ROOT/docs/fasim_gasal2_flush_two_slot_overlap_broader_matrix.md"
MULTI_DOC="$ROOT/docs/fasim_gasal2_flush_two_slot_multi_worker_2gpu.md"
RUNNER_DOC="$ROOT/docs/fasim_sharded_runner.md"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
NVTX_SUMMARY="$ROOT/scripts/summarize_fasim_gasal2_nvtx_overlap.py"
GUARD_CHECK="$ROOT/scripts/check_fasim_gasal2_two_slot_low_density_guard.sh"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$DOC" \
  "$BROADER_DOC" \
  "$MULTI_DOC" \
  "$RUNNER_DOC" \
  "$RUNNER" \
  "$NVTX_SUMMARY" \
  "$GUARD_CHECK" \
  "$MAKEFILE"
do
  if [[ ! -s "$path" ]]; then
    echo "missing readiness dependency: $path" >&2
    exit 1
  fi
done

grep -q 'decision = default-off recommended candidate' "$DOC"
grep -q 'scope    = normal-triplex lite' "$DOC"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1' "$DOC"
grep -q 'single worker or one worker per GPU' "$DOC"
grep -q 'unsupported_worker_density_for_current_gasal2_memory_budget' "$DOC"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING=1' "$DOC"
grep -q 'direct-lite finalizer shape' "$DOC"
grep -q 'archive-first finalizer shape' "$DOC"
grep -q 'traceback / exact-column kernel optimization' "$DOC"

grep -q 'chr21_full:' "$BROADER_DOC"
grep -q 'reduction vs extracted   = 8.1194 s / 12.9986%' "$BROADER_DOC"
grep -q 'chr22_full:' "$BROADER_DOC"
grep -q 'reduction vs extracted   = 8.0168 s / 12.9868%' "$BROADER_DOC"
grep -q 'CPU finalizer / CUDA activity overlap = 4.8484 s' "$BROADER_DOC"
grep -q 'strong_go_workloads = 2' "$BROADER_DOC"
grep -q 'device_overlap_measurement=nsight' "$BROADER_DOC"

grep -q 'two-slot multi-worker resource behavior = scoped-go' "$MULTI_DOC"
grep -q 'workers=2, GPUs=0,1:' "$MULTI_DOC"
grep -q 'reduction           = 3.72 s / 10.71%' "$MULTI_DOC"
grep -q 'workers=4: GASAL2 CUDA OOM' "$MULTI_DOC"
grep -q 'workers=6: GASAL2 CUDA OOM' "$MULTI_DOC"
grep -q 'make check-fasim-gasal2-two-slot-low-density-guard' "$MULTI_DOC"

grep -q 'two_slot_low_density_guard' "$RUNNER"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING' "$RUNNER"
grep -q 'unsupported_worker_density_for_current_gasal2_memory_budget' "$RUNNER"
grep -q 'single_worker_or_one_worker_per_gpu' "$RUNNER"
grep -q 'two_slot_low_density_guard' "$RUNNER_DOC"
grep -q 'run_config_digest' "$RUNNER_DOC"

grep -q 'NVTX' "$NVTX_SUMMARY"
grep -q 'two_slot_cpu_finalizer' "$NVTX_SUMMARY"
grep -q 'gpu_activity_overlap_seconds' "$NVTX_SUMMARY"

grep -q 'check-fasim-gasal2-two-slot-low-density-guard:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-two-slot-recommended-runtime-readiness:' "$MAKEFILE"
grep -q 'check_fasim_gasal2_two_slot_recommended_runtime_readiness.sh' "$MAKEFILE"

echo "check_fasim_gasal2_two_slot_recommended_runtime_readiness: ok"
