#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"

usage() {
  cat >&2 <<'EOF'
usage: run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh \
  --fasim-bin BIN --target TARGET.fa --rna RNA.fa --work-dir DIR [options]

Runs a CPU-authority baseline and a default-off MALAT1-like group32 GASAL2
scoreInfo candidate. The candidate is accepted only when the merged digest and
scoreInfo coverage gates pass.

Options:
  --rule N
  --output-mode MODE
  --workers N
  --gpu-ids IDS
  --cpu-core-ranges RANGES
  --cpu-pool RANGE
  --cpu-cores-per-worker N
  --auto-cpu-core-ranges
  --replay-probe-max-tasks N  (default 1; 0 = all tasks per flush)
  --resume
  --force
EOF
}

fasim_bin=""
target=""
rna=""
work_dir=""
rule="0"
output_mode="lite"
workers=""
gpu_ids=""
cpu_core_ranges=""
cpu_pool=""
cpu_cores_per_worker=""
auto_cpu_core_ranges=0
replay_probe_max_tasks="1"
resume=0
force=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --fasim-bin)
      fasim_bin="$2"
      shift 2
      ;;
    --target)
      target="$2"
      shift 2
      ;;
    --rna)
      rna="$2"
      shift 2
      ;;
    --work-dir)
      work_dir="$2"
      shift 2
      ;;
    --rule)
      rule="$2"
      shift 2
      ;;
    --output-mode)
      output_mode="$2"
      shift 2
      ;;
    --workers)
      workers="$2"
      shift 2
      ;;
    --gpu-ids)
      gpu_ids="$2"
      shift 2
      ;;
    --cpu-core-ranges)
      cpu_core_ranges="$2"
      shift 2
      ;;
    --cpu-pool)
      cpu_pool="$2"
      shift 2
      ;;
    --cpu-cores-per-worker)
      cpu_cores_per_worker="$2"
      shift 2
      ;;
    --auto-cpu-core-ranges)
      auto_cpu_core_ranges=1
      shift
      ;;
    --replay-probe-max-tasks)
      replay_probe_max_tasks="$2"
      shift 2
      ;;
    --resume)
      resume=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$fasim_bin" || -z "$target" || -z "$rna" || -z "$work_dir" ]]; then
  usage
  exit 2
fi
if [[ ! -x "$fasim_bin" ]]; then
  echo "missing executable --fasim-bin: $fasim_bin" >&2
  exit 1
fi
if [[ ! -s "$target" ]]; then
  echo "missing --target FASTA: $target" >&2
  exit 1
fi
if [[ ! -s "$rna" ]]; then
  echo "missing --rna FASTA: $rna" >&2
  exit 1
fi
if [[ "$resume" == "1" && "$force" == "1" ]]; then
  echo "--resume and --force cannot be used together" >&2
  exit 1
fi
if ! [[ "$replay_probe_max_tasks" =~ ^[0-9]+$ ]]; then
  echo "--replay-probe-max-tasks must be >= 0" >&2
  exit 1
fi
if [[ "$force" == "1" ]]; then
  rm -rf "$work_dir"
fi
mkdir -p "$work_dir"

baseline_dir="$work_dir/baseline"
candidate_dir="$work_dir/candidate"
accepted_dir="$work_dir/accepted"
summary="$work_dir/audit_summary.json"
baseline_report="$work_dir/baseline.report.json"
candidate_report="$work_dir/candidate.report.json"
if [[ "$resume" == "1" ]]; then
  if [[ ! -s "$summary" ]]; then
    echo "--resume requires an accepted audit summary: $summary" >&2
    exit 1
  fi
  python3 - "$summary" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if summary.get("audited_status") != "accepted":
    raise SystemExit("--resume requires an accepted audit summary")
PY
fi

common_args=(
  --fasim-bin "$fasim_bin"
  --target "$target"
  --rna "$rna"
  --rule "$rule"
  --output-mode "$output_mode"
  --group-target-records 32
)
if [[ -n "$workers" ]]; then
  common_args+=(--workers "$workers")
fi
if [[ -n "$gpu_ids" ]]; then
  common_args+=(--gpu-ids "$gpu_ids")
fi
if [[ -n "$cpu_core_ranges" ]]; then
  common_args+=(--cpu-core-ranges "$cpu_core_ranges")
fi
if [[ -n "$cpu_pool" ]]; then
  common_args+=(--cpu-pool "$cpu_pool")
fi
if [[ -n "$cpu_cores_per_worker" ]]; then
  common_args+=(--cpu-cores-per-worker "$cpu_cores_per_worker")
fi
if [[ "$auto_cpu_core_ranges" == "1" ]]; then
  common_args+=(--auto-cpu-core-ranges)
fi
resume_args=()
if [[ "$resume" == "1" ]]; then
  resume_args+=(--resume)
fi

baseline_start="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
python3 "$RUNNER" \
  "${common_args[@]}" \
  "${resume_args[@]}" \
  --work-dir "$baseline_dir" \
  --manifest "$baseline_dir/run_manifest.json" \
  >"$baseline_report"
baseline_end="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
baseline_runner_wall_seconds="$(python3 - "$baseline_start" "$baseline_end" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

candidate_start="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
python3 "$RUNNER" \
  "${common_args[@]}" \
  "${resume_args[@]}" \
  --work-dir "$candidate_dir" \
  --manifest "$candidate_dir/run_manifest.json" \
  --long-query-streaming-scoreinfo-gpu-trust-group32 \
  --long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks "$replay_probe_max_tasks" \
  >"$candidate_report"
candidate_end="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
candidate_runner_wall_seconds="$(python3 - "$candidate_start" "$candidate_end" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

python3 - \
  "$baseline_report" \
  "$candidate_report" \
  "$summary" \
  "$accepted_dir" \
  "$resume" \
  "$baseline_runner_wall_seconds" \
  "$candidate_runner_wall_seconds" <<'PY'
import json
import shutil
import sys
from pathlib import Path

baseline_path = Path(sys.argv[1])
candidate_path = Path(sys.argv[2])
summary_path = Path(sys.argv[3])
accepted_dir = Path(sys.argv[4])
audited_resume = sys.argv[5] == "1"
baseline_runner_wall_seconds = float(sys.argv[6])
candidate_runner_wall_seconds = float(sys.argv[7])

baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
bench = candidate.get("fasim_benchmark_sums", {})

def fail(message: str) -> None:
    raise SystemExit(message)

if baseline.get("run_status") != "completed":
    fail(f"baseline did not complete: {baseline.get('run_status')}")
if candidate.get("run_status") != "completed":
    fail(f"candidate did not complete: {candidate.get('run_status')}")
if baseline.get("merged_digest") != candidate.get("merged_digest"):
    fail(
        "digest gate failed: "
        f"baseline={baseline.get('merged_digest')} "
        f"candidate={candidate.get('merged_digest')}"
    )
if candidate.get("result_contract") != "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1":
    fail(f"unexpected result_contract: {candidate.get('result_contract')}")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile") != "malat1_like_group32_experimental_v1":
    fail(
        "unexpected trust profile: "
        f"{candidate.get('long_query_streaming_scoreinfo_gpu_trust_profile')}"
    )
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_group32") is not True:
    fail("candidate did not record group32 trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_decision") != "experimental_external_digest_gate":
    fail("candidate did not record external digest gate decision")
if candidate.get("group_target_records") != 32:
    fail(f"candidate did not record group_target_records=32: {candidate.get('group_target_records')}")
if baseline.get("group_target_records") != 32:
    fail(f"baseline did not record group_target_records=32: {baseline.get('group_target_records')}")

tasks = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks", 0)
realpath_used = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used", 0)
gpu_minscore_used = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used", 0)
gpu_groups = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups", 0)
realpath_fallbacks = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks", 0)
cpu_groups = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups", 0)
cpu_prealign_seconds = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds", 0)
compare_seconds = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds", 0)
gpu_total_seconds = float(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds", 0.0)
)
gpu_call_seconds = float(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds", 0.0)
)
gpu_kernel_seconds = float(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds", 0.0)
)
realpath_extend_calls = int(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_calls", 0)
)
realpath_extend_seconds = float(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds", 0.0)
)
realpath_extend_scoreinfo_groups = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups",
        0,
    )
)
realpath_extend_align_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts",
        0,
    )
)
realpath_extend_attempt_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_requested",
        0,
    )
)
realpath_extend_attempt_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_active",
        0,
    )
)
realpath_extend_attempt_probe_calls = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_calls",
        0,
    )
)
realpath_extend_attempt_probe_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_attempts",
        0,
    )
)
realpath_extend_attempt_probe_selected_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_selected_attempts",
        0,
    )
)
realpath_extend_attempt_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_seconds",
        0.0,
    )
)
realpath_extend_attempt_probe_fallbacks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_fallbacks",
        0,
    )
)
realpath_extend_segmented_attempt_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_requested",
        0,
    )
)
realpath_extend_segmented_attempt_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_active",
        0,
    )
)
realpath_extend_segmented_attempt_probe_segments = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_segments",
        0,
    )
)
realpath_extend_segmented_attempt_probe_calls = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_calls",
        0,
    )
)
realpath_extend_segmented_attempt_probe_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_attempts",
        0,
    )
)
realpath_extend_segmented_attempt_probe_selected_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_selected_attempts",
        0,
    )
)
realpath_extend_segmented_attempt_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_seconds",
        0.0,
    )
)
realpath_extend_segmented_attempt_probe_fallbacks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_fallbacks",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_requested",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_active",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_flushes = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_flushes",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_segments = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_segments",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_calls = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_calls",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_attempts",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_selected_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_selected_attempts",
        0,
    )
)
realpath_extend_flush_segmented_attempt_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_seconds",
        0.0,
    )
)
realpath_extend_flush_segmented_attempt_probe_fallbacks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_fallbacks",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_tasks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_selected_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_align_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_triplex_mismatches = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds",
        0.0,
    )
)
realpath_extend_flush_segmented_replay_probe_fallbacks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks",
        0,
    )
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_task = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_task",
        -1,
    )
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index",
        -1,
    )
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count",
        -1,
    )
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count",
        -1,
    )
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key = bench.get(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key",
    "none",
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key = bench.get(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key",
    "none",
)
realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance = bench.get(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance",
    "none",
)
realpath_extend_flush_full_replay_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_requested",
        0,
    )
)
realpath_extend_flush_full_replay_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_active",
        0,
    )
)
realpath_extend_flush_full_replay_probe_tasks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_tasks",
        0,
    )
)
realpath_extend_flush_full_replay_probe_align_attempts = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_align_attempts",
        0,
    )
)
realpath_extend_flush_full_replay_probe_triplex_mismatches = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_triplex_mismatches",
        0,
    )
)
realpath_extend_flush_full_replay_probe_fallbacks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_fallbacks",
        0,
    )
)
realpath_extend_flush_full_replay_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_seconds",
        0.0,
    )
)
realpath_extend_flush_oracle_replay_probe_requested = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_requested",
        0,
    )
)
realpath_extend_flush_oracle_replay_probe_active = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_active",
        0,
    )
)
realpath_extend_flush_oracle_replay_probe_tasks = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_tasks",
        0,
    )
)
realpath_extend_flush_oracle_replay_probe_triplex_mismatches = int(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_triplex_mismatches",
        0,
    )
)
realpath_extend_flush_oracle_replay_probe_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_seconds",
        0.0,
    )
)
realpath_extend_substr_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds",
        0.0,
    )
)
realpath_extend_align_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds",
        0.0,
    )
)
realpath_extend_convert_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds",
        0.0,
    )
)
realpath_extend_sort_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds",
        0.0,
    )
)
realpath_extend_filter_seconds = float(
    bench.get(
        "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds",
        0.0,
    )
)

if not isinstance(tasks, int) or tasks <= 0:
    fail(f"expected positive tasks, got {tasks}")
if realpath_used != tasks:
    fail(f"realpath_used != tasks: {realpath_used} vs {tasks}")
if gpu_minscore_used != tasks:
    fail(f"gpu_minscore_used != tasks: {gpu_minscore_used} vs {tasks}")
if not isinstance(gpu_groups, int) or gpu_groups <= 0:
    fail(f"expected positive gpu_scoreinfo_groups, got {gpu_groups}")
if realpath_fallbacks != 0:
    fail(f"expected realpath_fallbacks=0, got {realpath_fallbacks}")
if cpu_groups != 0:
    fail(f"expected cpu_scoreinfo_groups=0, got {cpu_groups}")
if cpu_prealign_seconds != 0:
    fail(f"expected cpu_prealign_seconds=0, got {cpu_prealign_seconds}")
if compare_seconds != 0:
    fail(f"expected compare_seconds=0, got {compare_seconds}")
if baseline_runner_wall_seconds <= 0.0:
    fail(f"expected positive baseline_runner_wall_seconds, got {baseline_runner_wall_seconds}")
if candidate_runner_wall_seconds <= 0.0:
    fail(f"expected positive candidate_runner_wall_seconds, got {candidate_runner_wall_seconds}")
if gpu_total_seconds <= 0.0:
    fail(f"expected positive candidate GPU scoreInfo total seconds, got {gpu_total_seconds}")
if gpu_call_seconds <= 0.0:
    fail(f"expected positive candidate GPU scoreInfo call seconds, got {gpu_call_seconds}")
if gpu_kernel_seconds <= 0.0:
    fail(f"expected positive candidate GPU scoreInfo kernel seconds, got {gpu_kernel_seconds}")
if realpath_extend_calls <= 0:
    fail(f"expected positive candidate realpath extend calls, got {realpath_extend_calls}")
if realpath_extend_seconds <= 0.0:
    fail(f"expected positive candidate realpath extend seconds, got {realpath_extend_seconds}")
if realpath_extend_scoreinfo_groups <= 0:
    fail(
        "expected positive candidate realpath extend scoreInfo groups, "
        f"got {realpath_extend_scoreinfo_groups}"
    )
if realpath_extend_align_attempts <= 0:
    fail(
        "expected positive candidate realpath extend align attempts, "
        f"got {realpath_extend_align_attempts}"
    )
if realpath_extend_align_seconds <= 0.0:
    fail(
        "expected positive candidate realpath extend align seconds, "
        f"got {realpath_extend_align_seconds}"
    )
if realpath_extend_attempt_probe_requested <= 0:
    fail(
        "expected positive candidate realpath extend attempt probe requested, "
        f"got {realpath_extend_attempt_probe_requested}"
    )
if realpath_extend_attempt_probe_calls <= 0:
    fail(
        "expected positive candidate realpath extend attempt probe calls, "
        f"got {realpath_extend_attempt_probe_calls}"
    )
if realpath_extend_attempt_probe_attempts <= 0:
    fail(
        "expected positive candidate realpath extend attempt probe attempts, "
        f"got {realpath_extend_attempt_probe_attempts}"
    )
if realpath_extend_attempt_probe_selected_attempts < 0:
    fail(
        "expected non-negative candidate realpath extend attempt probe selected attempts, "
        f"got {realpath_extend_attempt_probe_selected_attempts}"
    )
if realpath_extend_attempt_probe_seconds <= 0.0:
    fail(
        "expected positive candidate realpath extend attempt probe seconds, "
        f"got {realpath_extend_attempt_probe_seconds}"
    )
if realpath_extend_attempt_probe_fallbacks < 0:
    fail(
        "expected non-negative candidate realpath extend attempt probe fallbacks, "
        f"got {realpath_extend_attempt_probe_fallbacks}"
    )
for key, value in (
    ("realpath_extend_segmented_attempt_probe_requested", realpath_extend_segmented_attempt_probe_requested),
    ("realpath_extend_segmented_attempt_probe_segments", realpath_extend_segmented_attempt_probe_segments),
    ("realpath_extend_segmented_attempt_probe_calls", realpath_extend_segmented_attempt_probe_calls),
    ("realpath_extend_segmented_attempt_probe_attempts", realpath_extend_segmented_attempt_probe_attempts),
):
    if value < 0:
        fail(f"expected non-negative candidate {key}, got {value}")
if realpath_extend_segmented_attempt_probe_selected_attempts < 0:
    fail(
        "expected non-negative candidate realpath extend segmented attempt probe selected attempts, "
        f"got {realpath_extend_segmented_attempt_probe_selected_attempts}"
    )
if realpath_extend_segmented_attempt_probe_seconds < 0.0:
    fail(
        "expected non-negative candidate realpath extend segmented attempt probe seconds, "
        f"got {realpath_extend_segmented_attempt_probe_seconds}"
    )
if realpath_extend_segmented_attempt_probe_fallbacks < 0:
    fail(
        "expected non-negative candidate realpath extend segmented attempt probe fallbacks, "
        f"got {realpath_extend_segmented_attempt_probe_fallbacks}"
    )
if realpath_extend_flush_segmented_attempt_probe_requested <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe requested, "
        f"got {realpath_extend_flush_segmented_attempt_probe_requested}"
    )
if realpath_extend_flush_segmented_attempt_probe_flushes <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe flushes, "
        f"got {realpath_extend_flush_segmented_attempt_probe_flushes}"
    )
if realpath_extend_flush_segmented_attempt_probe_segments <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe segments, "
        f"got {realpath_extend_flush_segmented_attempt_probe_segments}"
    )
if realpath_extend_flush_segmented_attempt_probe_calls <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe calls, "
        f"got {realpath_extend_flush_segmented_attempt_probe_calls}"
    )
if realpath_extend_flush_segmented_attempt_probe_attempts <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe attempts, "
        f"got {realpath_extend_flush_segmented_attempt_probe_attempts}"
    )
if realpath_extend_flush_segmented_attempt_probe_selected_attempts < 0:
    fail(
        "expected non-negative candidate realpath extend flush segmented attempt probe selected attempts, "
        f"got {realpath_extend_flush_segmented_attempt_probe_selected_attempts}"
    )
if realpath_extend_flush_segmented_attempt_probe_seconds <= 0.0:
    fail(
        "expected positive candidate realpath extend flush segmented attempt probe seconds, "
        f"got {realpath_extend_flush_segmented_attempt_probe_seconds}"
    )
if realpath_extend_flush_segmented_attempt_probe_fallbacks < 0:
    fail(
        "expected non-negative candidate realpath extend flush segmented attempt probe fallbacks, "
        f"got {realpath_extend_flush_segmented_attempt_probe_fallbacks}"
    )
if realpath_extend_flush_segmented_replay_probe_requested <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe requested, "
        f"got {realpath_extend_flush_segmented_replay_probe_requested}"
    )
if realpath_extend_flush_segmented_replay_probe_active <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe active, "
        f"got {realpath_extend_flush_segmented_replay_probe_active}"
    )
if realpath_extend_flush_segmented_replay_probe_tasks <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe tasks, "
        f"got {realpath_extend_flush_segmented_replay_probe_tasks}"
    )
if realpath_extend_flush_segmented_replay_probe_selected_attempts <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe selected attempts, "
        f"got {realpath_extend_flush_segmented_replay_probe_selected_attempts}"
    )
if realpath_extend_flush_segmented_replay_probe_align_attempts <= 0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe align attempts, "
        f"got {realpath_extend_flush_segmented_replay_probe_align_attempts}"
    )
if realpath_extend_flush_segmented_replay_probe_triplex_mismatches < 0:
    fail(
        "expected non-negative candidate realpath extend flush segmented replay probe triplex mismatches, "
        f"got {realpath_extend_flush_segmented_replay_probe_triplex_mismatches}"
    )
if realpath_extend_flush_segmented_replay_probe_seconds <= 0.0:
    fail(
        "expected positive candidate realpath extend flush segmented replay probe seconds, "
        f"got {realpath_extend_flush_segmented_replay_probe_seconds}"
    )
if realpath_extend_flush_segmented_replay_probe_fallbacks < 0:
    fail(
        "expected non-negative candidate realpath extend flush segmented replay probe fallbacks, "
        f"got {realpath_extend_flush_segmented_replay_probe_fallbacks}"
    )
for key, value in (
    ("realpath_extend_substr_seconds", realpath_extend_substr_seconds),
    ("realpath_extend_convert_seconds", realpath_extend_convert_seconds),
    ("realpath_extend_sort_seconds", realpath_extend_sort_seconds),
    ("realpath_extend_filter_seconds", realpath_extend_filter_seconds),
):
    if value < 0.0:
        fail(f"expected non-negative candidate {key}, got {value}")
candidate_vs_baseline = (
    baseline_runner_wall_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)
candidate_post_scoreinfo_unattributed_seconds = max(
    0.0, candidate_runner_wall_seconds - gpu_total_seconds
)
candidate_gpu_scoreinfo_wall_fraction = (
    gpu_total_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)
candidate_gpu_scoreinfo_call_fraction = (
    gpu_call_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)
candidate_realpath_extend_fraction = (
    realpath_extend_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)
candidate_realpath_extend_align_fraction = (
    realpath_extend_align_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)
candidate_post_scoreinfo_unattributed_fraction = (
    candidate_post_scoreinfo_unattributed_seconds / candidate_runner_wall_seconds
    if candidate_runner_wall_seconds > 0.0
    else 0.0
)

accepted_dir.mkdir(parents=True, exist_ok=True)
candidate_output = Path(candidate["merged_output"])
accepted_output = accepted_dir / candidate_output.name
shutil.copy2(candidate_output, accepted_output)

summary = {
    "audited_status": "accepted",
    "audited_resume": audited_resume,
    "baseline_report": str(baseline_path),
    "candidate_report": str(candidate_path),
    "accepted_output": str(accepted_output),
    "baseline_runner_wall_seconds": baseline_runner_wall_seconds,
    "candidate_runner_wall_seconds": candidate_runner_wall_seconds,
    "candidate_vs_baseline": candidate_vs_baseline,
    "candidate_gpu_scoreinfo_total_seconds": gpu_total_seconds,
    "candidate_gpu_scoreinfo_call_seconds": gpu_call_seconds,
    "candidate_gpu_scoreinfo_kernel_seconds": gpu_kernel_seconds,
    "candidate_non_gpu_wall_seconds": candidate_post_scoreinfo_unattributed_seconds,
    "candidate_gpu_scoreinfo_wall_fraction": candidate_gpu_scoreinfo_wall_fraction,
    "candidate_gpu_scoreinfo_call_fraction": candidate_gpu_scoreinfo_call_fraction,
    "candidate_realpath_extend_seconds": realpath_extend_seconds,
    "candidate_realpath_extend_calls": realpath_extend_calls,
    "candidate_realpath_extend_fraction": candidate_realpath_extend_fraction,
    "candidate_realpath_extend_scoreinfo_groups": realpath_extend_scoreinfo_groups,
    "candidate_realpath_extend_align_attempts": realpath_extend_align_attempts,
    "candidate_realpath_extend_attempt_probe_requested": realpath_extend_attempt_probe_requested,
    "candidate_realpath_extend_attempt_probe_active": realpath_extend_attempt_probe_active,
    "candidate_realpath_extend_attempt_probe_calls": realpath_extend_attempt_probe_calls,
    "candidate_realpath_extend_attempt_probe_attempts": realpath_extend_attempt_probe_attempts,
    "candidate_realpath_extend_attempt_probe_selected_attempts": realpath_extend_attempt_probe_selected_attempts,
    "candidate_realpath_extend_attempt_probe_seconds": realpath_extend_attempt_probe_seconds,
    "candidate_realpath_extend_attempt_probe_fallbacks": realpath_extend_attempt_probe_fallbacks,
    "candidate_realpath_extend_segmented_attempt_probe_requested": realpath_extend_segmented_attempt_probe_requested,
    "candidate_realpath_extend_segmented_attempt_probe_active": realpath_extend_segmented_attempt_probe_active,
    "candidate_realpath_extend_segmented_attempt_probe_segments": realpath_extend_segmented_attempt_probe_segments,
    "candidate_realpath_extend_segmented_attempt_probe_calls": realpath_extend_segmented_attempt_probe_calls,
    "candidate_realpath_extend_segmented_attempt_probe_attempts": realpath_extend_segmented_attempt_probe_attempts,
    "candidate_realpath_extend_segmented_attempt_probe_selected_attempts": realpath_extend_segmented_attempt_probe_selected_attempts,
    "candidate_realpath_extend_segmented_attempt_probe_seconds": realpath_extend_segmented_attempt_probe_seconds,
    "candidate_realpath_extend_segmented_attempt_probe_fallbacks": realpath_extend_segmented_attempt_probe_fallbacks,
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested": realpath_extend_flush_segmented_attempt_probe_requested,
    "candidate_realpath_extend_flush_segmented_attempt_probe_active": realpath_extend_flush_segmented_attempt_probe_active,
    "candidate_realpath_extend_flush_segmented_attempt_probe_flushes": realpath_extend_flush_segmented_attempt_probe_flushes,
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments": realpath_extend_flush_segmented_attempt_probe_segments,
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls": realpath_extend_flush_segmented_attempt_probe_calls,
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts": realpath_extend_flush_segmented_attempt_probe_attempts,
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts": realpath_extend_flush_segmented_attempt_probe_selected_attempts,
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds": realpath_extend_flush_segmented_attempt_probe_seconds,
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks": realpath_extend_flush_segmented_attempt_probe_fallbacks,
    "candidate_realpath_extend_flush_segmented_replay_probe_requested": realpath_extend_flush_segmented_replay_probe_requested,
    "candidate_realpath_extend_flush_segmented_replay_probe_active": realpath_extend_flush_segmented_replay_probe_active,
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks": realpath_extend_flush_segmented_replay_probe_tasks,
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts": realpath_extend_flush_segmented_replay_probe_selected_attempts,
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts": realpath_extend_flush_segmented_replay_probe_align_attempts,
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches": realpath_extend_flush_segmented_replay_probe_triplex_mismatches,
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds": realpath_extend_flush_segmented_replay_probe_seconds,
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks": realpath_extend_flush_segmented_replay_probe_fallbacks,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_task": realpath_extend_flush_segmented_replay_probe_first_mismatch_task,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index": realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count": realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count": realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key": realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key": realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key,
    "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance": realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance,
    "candidate_realpath_extend_flush_full_replay_probe_requested": realpath_extend_flush_full_replay_probe_requested,
    "candidate_realpath_extend_flush_full_replay_probe_active": realpath_extend_flush_full_replay_probe_active,
    "candidate_realpath_extend_flush_full_replay_probe_tasks": realpath_extend_flush_full_replay_probe_tasks,
    "candidate_realpath_extend_flush_full_replay_probe_align_attempts": realpath_extend_flush_full_replay_probe_align_attempts,
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches": realpath_extend_flush_full_replay_probe_triplex_mismatches,
    "candidate_realpath_extend_flush_full_replay_probe_fallbacks": realpath_extend_flush_full_replay_probe_fallbacks,
    "candidate_realpath_extend_flush_full_replay_probe_seconds": realpath_extend_flush_full_replay_probe_seconds,
    "candidate_realpath_extend_flush_oracle_replay_probe_requested": realpath_extend_flush_oracle_replay_probe_requested,
    "candidate_realpath_extend_flush_oracle_replay_probe_active": realpath_extend_flush_oracle_replay_probe_active,
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks": realpath_extend_flush_oracle_replay_probe_tasks,
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches": realpath_extend_flush_oracle_replay_probe_triplex_mismatches,
    "candidate_realpath_extend_flush_oracle_replay_probe_seconds": realpath_extend_flush_oracle_replay_probe_seconds,
    "candidate_realpath_extend_substr_seconds": realpath_extend_substr_seconds,
    "candidate_realpath_extend_align_seconds": realpath_extend_align_seconds,
    "candidate_realpath_extend_align_fraction": candidate_realpath_extend_align_fraction,
    "candidate_realpath_extend_convert_seconds": realpath_extend_convert_seconds,
    "candidate_realpath_extend_sort_seconds": realpath_extend_sort_seconds,
    "candidate_realpath_extend_filter_seconds": realpath_extend_filter_seconds,
    "candidate_post_scoreinfo_unattributed_seconds": candidate_post_scoreinfo_unattributed_seconds,
    "candidate_post_scoreinfo_unattributed_fraction": candidate_post_scoreinfo_unattributed_fraction,
    "baseline_digest": baseline["merged_digest"],
    "candidate_digest": candidate["merged_digest"],
    "merged_records": candidate["merged_records"],
    "result_contract": candidate["result_contract"],
    "trust_profile": candidate["long_query_streaming_scoreinfo_gpu_trust_profile"],
    "group_target_records": candidate["group_target_records"],
    "shard_count": candidate["shard_count"],
    "worker_count": candidate["worker_count"],
    "baseline_resumed_shards": baseline.get("resumed_shards", []),
    "baseline_resumed_shards_count": len(baseline.get("resumed_shards", [])),
    "candidate_resumed_shards": candidate.get("resumed_shards", []),
    "candidate_resumed_shards_count": len(candidate.get("resumed_shards", [])),
    "tasks": tasks,
    "realpath_used": realpath_used,
    "realpath_fallbacks": realpath_fallbacks,
    "gpu_scoreinfo_groups": gpu_groups,
    "gpu_minscore_used": gpu_minscore_used,
    "cpu_scoreinfo_groups": cpu_groups,
    "cpu_prealign_seconds": cpu_prealign_seconds,
    "compare_seconds": compare_seconds,
    "decision": "accepted_by_external_digest_gate",
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
PY
