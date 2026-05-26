#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_sharded_runner_telemetry"

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_multicontig.fa" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = src.read_text(encoding="utf-8").splitlines()
header = lines[0]
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
mid = len(sequence) // 2
dst.write_text(
    f"{header.replace('chr11', 'chr11_left')}\n{sequence[:mid]}\n"
    f"{header.replace('chr11', 'chr11_right')}\n{sequence[mid:]}\n",
    encoding="utf-8",
)
PY

env -u FASIM_CUDA_DEVICES \
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/run" \
  --manifest "$WORK/run/run_manifest.json" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --gpu-ids 0,1 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=2 \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/run/report.json" "$WORK/run/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
required = {
    "fasim_prealign_cuda_requested",
    "fasim_prealign_cuda_active",
    "fasim_prealign_cuda_tasks",
    "fasim_prealign_cuda_batches",
    "fasim_prealign_cuda_kernel_seconds",
    "fasim_prealign_cuda_total_seconds",
    "fasim_extend_threads",
    "fasim_extend_seconds",
    "fasim_extend_candidates",
    "fasim_extend_cutlength_attempts",
    "fasim_extend_align_calls",
    "fasim_extend_align_cells",
    "fasim_extend_align_seconds",
    "fasim_extend_convert_calls",
    "fasim_extend_convert_seconds",
    "fasim_extend_sort_unique_seconds",
    "fasim_extend_records_before_filter",
    "fasim_extend_records_emitted",
    "fasim_extend_empty_scoreinfo",
    "fasim_align_query_translate_seconds",
    "fasim_align_ref_translate_seconds",
    "fasim_align_profile_seconds",
    "fasim_align_ssw_total_seconds",
    "fasim_align_forward_score_end_seconds",
    "fasim_align_reverse_start_seconds",
    "fasim_align_traceback_seconds",
    "fasim_align_forward_score_gpu_shadow_enabled",
    "fasim_align_forward_score_gpu_requests",
    "fasim_align_forward_score_gpu_cells",
    "fasim_align_forward_score_gpu_cpu_seconds",
    "fasim_align_forward_score_gpu_pack_seconds",
    "fasim_align_forward_score_gpu_h2d_seconds",
    "fasim_align_forward_score_gpu_kernel_seconds",
    "fasim_align_forward_score_gpu_d2h_seconds",
    "fasim_align_forward_score_gpu_unpack_seconds",
    "fasim_align_forward_score_gpu_total_seconds",
    "fasim_align_forward_score_gpu_score_mismatches",
    "fasim_align_forward_score_gpu_endpoint_mismatches",
    "fasim_align_forward_score_gpu_unsupported_requests",
    "fasim_align_convert_seconds",
    "fasim_align_cleanup_seconds",
    "fasim_align_calls",
    "fasim_align_byte_forward_calls",
    "fasim_align_word_forward_calls",
    "fasim_align_reverse_calls",
    "fasim_align_traceback_calls",
    "fasim_align_null_results",
    "fasim_align_profile_reuse_shadow_enabled",
    "fasim_align_profile_build_calls",
    "fasim_align_profile_unique_keys",
    "fasim_align_profile_reusable_calls",
    "fasim_align_profile_build_seconds",
    "fasim_align_profile_est_saved_seconds",
    "fasim_align_query_unique_keys",
    "fasim_align_query_reusable_calls",
    "fasim_align_profile_cache_requested",
    "fasim_align_profile_cache_active",
    "fasim_align_profile_cache_validate",
    "fasim_align_profile_cache_calls",
    "fasim_align_profile_cache_hits",
    "fasim_align_profile_cache_misses",
    "fasim_align_profile_cache_unique_keys",
    "fasim_align_profile_cache_build_seconds",
    "fasim_align_profile_cache_saved_seconds",
    "fasim_align_profile_cache_validate_seconds",
    "fasim_align_profile_cache_score_mismatches",
    "fasim_align_profile_cache_endpoint_mismatches",
    "fasim_align_profile_cache_cigar_mismatches",
    "fasim_align_profile_cache_digest_mismatches",
    "fasim_align_profile_cache_fallbacks",
    "fasim_output_seconds",
}

assert report["single_vs_sharded_digest_match"] is True, report
assert report["sharded_telemetry"]["fasim_prealign_cuda_requested"] == 1, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_prealign_cuda_tasks"] > 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_extend_candidates"] >= 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_extend_align_calls"] >= 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_extend_align_cells"] >= 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_calls"] >= 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_end_seconds"] >= 0.0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_shadow_enabled"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_requests"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_cells"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_score_mismatches"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_endpoint_mismatches"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_forward_score_gpu_unsupported_requests"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_profile_reuse_shadow_enabled"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_profile_build_calls"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_profile_cache_requested"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_profile_cache_active"] == 0, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_align_profile_cache_calls"] == 0, report["sharded_telemetry"]
assert report["single_run"]["telemetry"]["fasim_prealign_cuda_requested"] == 1, report["single_run"]
assert report["single_run"]["telemetry"]["fasim_align_forward_score_gpu_shadow_enabled"] == 0, report["single_run"]
assert report["single_run"]["telemetry"]["fasim_align_profile_reuse_shadow_enabled"] == 0, report["single_run"]
assert report["single_run"]["telemetry"]["fasim_align_profile_cache_requested"] == 0, report["single_run"]

for shard in report["per_shard"]:
    telemetry = shard["run"]["telemetry"]
    assert required.issubset(telemetry), telemetry
    assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry
    assert telemetry["fasim_align_forward_score_gpu_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_forward_score_gpu_requests"] == 0, telemetry
    assert telemetry["fasim_align_profile_reuse_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_profile_cache_requested"] == 0, telemetry

for worker in report["per_worker"]:
    telemetry = worker["telemetry"]
    assert required.issubset(telemetry), telemetry
    assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry
    assert telemetry["fasim_align_forward_score_gpu_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_forward_score_gpu_requests"] == 0, telemetry
    assert telemetry["fasim_align_profile_reuse_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_profile_cache_requested"] == 0, telemetry

for entry in manifest["per_shard"]:
    telemetry = entry["telemetry"]
    assert required.issubset(telemetry), telemetry
    assert telemetry["fasim_align_forward_score_gpu_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_forward_score_gpu_requests"] == 0, telemetry
    assert telemetry["fasim_align_profile_reuse_shadow_enabled"] == 0, telemetry
    assert telemetry["fasim_align_profile_cache_requested"] == 0, telemetry
PY

echo "ok"
