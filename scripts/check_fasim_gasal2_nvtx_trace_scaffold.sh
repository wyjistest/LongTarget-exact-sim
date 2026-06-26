#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
SUMMARY="$ROOT/scripts/summarize_fasim_gasal2_nvtx_overlap.py"
DOC="$ROOT/docs/fasim_gasal2_nvtx_ground_truth_scaffold.md"

grep -q '#include <nvToolsExt.h>' "$CPP"
grep -q 'FASIM_WITH_NVTX' "$CPP"
grep -q 'FASIM_GASAL2_NVTX_TRACE' "$CPP"
grep -q 'struct FasimNvtxRange' "$CPP"
grep -q 'fasim_nvtx_async_range_start' "$CPP"
grep -q 'fasim_nvtx_async_range_end' "$CPP"
grep -q 'fasim_gasal2_nvtx_trace_runtime' "$CPP"
grep -q 'benchmark.fasim_gasal2_nvtx_trace_requested=' "$CPP"
grep -q 'benchmark.fasim_gasal2_nvtx_trace_active=' "$CPP"
grep -q 'benchmark.fasim_gasal2_nvtx_trace_ranges=' "$CPP"

for range in \
  fasim.gasal2.flush \
  fasim.gasal2.pack \
  fasim.gasal2.score_traceback \
  fasim.gasal2.convert \
  fasim.gasal2.archive_write \
  fasim.gasal2.two_slot.submit_result \
  fasim.gasal2.two_slot.cpu_finalizer \
  fasim.gasal2.two_slot.ordered_commit \
  fasim.gasal2.two_slot.slot_lifetime \
  fasim.gasal2.two_slot.drain
do
  grep -q "$range" "$CPP"
done

for doc_text in \
  "fasim.gasal2.two_slot.cpu_finalizer" \
  "FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1" \
  "host_scheduling_overlap_seconds" \
  "summarize_fasim_gasal2_nvtx_overlap.py" \
  "cpu_finalizer/GPU activity overlap = 4.8569 s"
do
  grep -q "$doc_text" "$DOC"
done

grep -q 'CUPTI_ACTIVITY_KIND_KERNEL' "$SUMMARY"
grep -q 'CUPTI_ACTIVITY_KIND_MEMCPY' "$SUMMARY"
grep -q 'two_slot_cpu_finalizer' "$SUMMARY"
grep -q 'gpu_activity_overlap_seconds' "$SUMMARY"

grep -q 'build-fasim-gasal2-nvtx:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-nvtx-trace-scaffold:' "$MAKEFILE"

echo "check_fasim_gasal2_nvtx_trace_scaffold: ok"
