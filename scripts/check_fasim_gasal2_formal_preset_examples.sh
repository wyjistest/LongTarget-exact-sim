#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_formal_preset_examples"}"
K="${K:-5}"
WORKERS="${WORKERS:-1}"
GPU_IDS="${GPU_IDS:-0}"
MEG3_RECORDS="${MEG3_RECORDS:-32}"
SOURCE_TARGET="${SOURCE_TARGET:-"$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa"}"
TARGET="${TARGET:-}"
RNA="${RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa"}"
RULE="${RULE:-0}"

if [[ "$K" != "5" ]]; then
  echo "formal preset examples gate requires K=5" >&2
  exit 1
fi
if [[ "$MEG3_RECORDS" -lt 1 ]]; then
  echo "MEG3_RECORDS must be >= 1" >&2
  exit 1
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

if [[ -z "$TARGET" && ! -s "$SOURCE_TARGET" ]]; then
  echo "missing MEG3 source target: $SOURCE_TARGET" >&2
  exit 1
fi
if [[ -n "$TARGET" && ! -s "$TARGET" ]]; then
  echo "missing target: $TARGET" >&2
  exit 1
fi
if [[ ! -s "$RNA" ]]; then
  echo "missing MEG3 RNA: $RNA" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

first_records_fasta() {
  local input="$1"
  local output="$2"
  local count="$3"
  awk -v limit="$count" '
    /^>/ {
      ++records
    }
    records <= limit {
      print
    }
  ' "$input" >"$output"
}

if [[ -z "$TARGET" ]]; then
  TARGET="$WORK/inputs/meg3_first${MEG3_RECORDS}.fa"
  first_records_fasta "$SOURCE_TARGET" "$TARGET" "$MEG3_RECORDS"
fi

runner_gpu_args=()
if [[ -n "$GPU_IDS" ]]; then
  runner_gpu_args+=(--gpu-ids "$GPU_IDS")
fi

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/cpu_summary" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/cpu_summary.stdout.log" \
  2>"$WORK/cpu_summary.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/formal_preset" \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/formal_preset.stdout.log" \
  2>"$WORK/formal_preset.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/cap32_no_go" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite "$K" \
  --gasal2-top5-scoreinfo-prune-max-per-task 32 \
  --exact-scoreinfo-gpu-max-per-task 512 \
  --exact-scoreinfo-gpu-pruned-output \
  --exact-scoreinfo-gpu-column-pruned-output \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/cap32_no_go.stdout.log" \
  2>"$WORK/cap32_no_go.stderr.log"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/cpu_summary/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/formal_preset/report.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/cpu_summary/report.json"
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/cap32_no_go/report.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  >"$WORK/cap32_no_go.check.stdout.log" \
  2>"$WORK/cap32_no_go.check.stderr.log"; then
  echo "expected cap32 MEG3 first32 artifact mismatch" >&2
  exit 1
fi
grep -q -- "topK payload digest mismatch" "$WORK/cap32_no_go.check.stderr.log"

python3 - "$WORK/cpu_summary/report.json" "$WORK/formal_preset/report.json" "$WORK/cap32_no_go/report.json" "$K" "$WORKERS" "$MEG3_RECORDS" <<'PY'
import json
import sys
from pathlib import Path

cpu = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
preset = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
cap32 = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
k = int(sys.argv[4])
workers = int(sys.argv[5])
meg3_records = int(sys.argv[6])

assert cpu["run_status"] == "completed", cpu
assert preset["run_status"] == "completed", preset
assert cap32["run_status"] == "completed", cap32
assert cpu["gasal2_top5_activation_verified"] is None, cpu
assert cpu["gasal2_top5_activation_error"] is None, cpu
assert preset["gasal2_top5_activation_verified"] is True, preset
assert preset["gasal2_top5_activation_error"] is None, preset
assert cpu["result_contract"] == "topk_summary_artifact_v1", cpu
assert preset["result_contract"] == "gasal2_top5_column_pruned_scoreinfo_artifact_v1", preset
assert cpu["topk_summary_only"] is True, cpu
assert preset["topk_summary_only"] is True, preset
assert cpu["shard_output_topk_lite"] is None, cpu
assert preset["shard_output_topk_lite"] == k, preset
assert preset["gasal2_top5_column_pruned_scoreinfo"] is True, preset
assert cpu["shard_count"] == preset["shard_count"] == meg3_records, (cpu, preset)
assert preset["gasal2_top5_scoreinfo_prune_max_per_task"] == 64, preset
assert cap32["gasal2_top5_scoreinfo_prune_max_per_task"] == 32, cap32
assert preset["exact_scoreinfo_gpu_max_per_task"] == 512, preset
assert preset["exact_scoreinfo_gpu_pruned_output"] is True, preset
assert preset["exact_scoreinfo_gpu_column_pruned_output"] is True, preset
assert cpu["worker_count"] == workers, cpu
assert preset["worker_count"] == workers, preset
assert preset["fasim_benchmark_shards"] == preset["shard_count"], preset

for mode in ("score", "stability", "nt_score"):
    cpu_mode = cpu["topk_summary"]["modes"][mode]
    preset_mode = preset["topk_summary"]["modes"][mode]
    assert preset_mode == cpu_mode, (mode, cpu_mode, preset_mode)
    print(f"{mode}_digest={preset_mode['digest']}")

assert cap32["topk_summary"]["modes"]["score"] == cpu["topk_summary"]["modes"]["score"], cap32
assert cap32["topk_summary"]["modes"]["stability"] == cpu["topk_summary"]["modes"]["stability"], cap32
assert cap32["topk_summary"]["modes"]["nt_score"] != cpu["topk_summary"]["modes"]["nt_score"], cap32
assert preset["topk_rows_payload_digest"] == cpu["topk_rows_payload_digest"], (cpu, preset)
assert preset["topk_lite_digest"] == cpu["topk_lite_digest"], (cpu, preset)
assert preset["topk_lite_records"] == cpu["topk_lite_records"], (cpu, preset)

sums = preset["fasim_benchmark_sums"]
assert sums["fasim_top5_gasal2_gpu_scoreinfo_requested"] == preset["shard_count"], sums
assert sums["fasim_top5_gasal2_gpu_scoreinfo_active"] == preset["shard_count"], sums
assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled"] == preset["shard_count"], sums
assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled"] == preset["shard_count"], sums
assert sums["fasim_gasal2_requests"] > 0, sums
assert sums["fasim_gasal2_score_requests"] > 0, sums
assert sums["fasim_gasal2_traceback_requests"] > 0, sums
assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks"] > 0, sums
assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches"] == 0, sums
assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches"] == 0, sums
assert sums["fasim_gasal2_fallbacks"] == 0, sums
assert sums["fasim_gasal2_length_guard_fallbacks"] == 0, sums

cpu_wall = sum(float(worker["wall_seconds"]) for worker in cpu["per_worker"])
preset_wall = sum(float(worker["wall_seconds"]) for worker in preset["per_worker"])
speedup = cpu_wall / preset_wall if preset_wall > 0 else float("nan")
print(f"formal_preset_example=meg3_first{meg3_records}")
print("formal_preset_topk_artifact_match=true")
print("cap32_nt_score_artifact_match=false")
print(f"formal_preset_gasal2_requests={int(sums['fasim_gasal2_requests'])}")
print(f"formal_preset_exact_scoreinfo_gpu_tasks={int(sums['fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks'])}")
print(f"formal_preset_speedup_vs_cpu_worker_wall_sum={speedup:.6f}")
PY

echo "ok"
