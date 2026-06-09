#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"

usage() {
  cat >&2 <<'EOF'
usage: run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh \
  --fasim-bin BIN --target TARGET.fa --rna RNA.fa --work-dir DIR [options]

Runs a CPU-authority group32 baseline and a default-off MALAT1-like group32
two-contract GASAL2 scoreInfo candidate. The candidate is accepted only when
the merged digest and two-contract scoreInfo coverage gates pass.

Options:
  --rule N
  --output-mode MODE
  --workers N
  --gpu-ids IDS
  --cpu-core-ranges RANGES
  --cpu-pool RANGE
  --cpu-cores-per-worker N
  --auto-cpu-core-ranges
  --replay-probe-max-tasks N
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
case "$replay_probe_max_tasks" in
  ''|*[!0-9]*)
    echo "--replay-probe-max-tasks must be a non-negative integer: $replay_probe_max_tasks" >&2
    exit 2
    ;;
esac
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
  --long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 \
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

def number(key: str, default: int | float = 0) -> int | float:
    return bench.get(key, default)

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
if candidate.get("result_contract") != "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1":
    fail(f"unexpected result_contract: {candidate.get('result_contract')}")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile") != "malat1_like_two_contract_group32_experimental_v1":
    fail(
        "unexpected trust profile: "
        f"{candidate.get('long_query_streaming_scoreinfo_gpu_trust_profile')}"
    )
if candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust") is not True:
    fail("candidate did not record two-contract trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust_group32") is not True:
    fail("candidate did not record two-contract group32 flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust") is not False:
    fail("candidate unexpectedly recorded legacy trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_group32") is not False:
    fail("candidate unexpectedly recorded legacy group32 trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_decision") != "experimental_external_digest_gate":
    fail("candidate did not record external digest gate decision")
if candidate.get("group_target_records") != 32:
    fail(f"candidate did not record group_target_records=32: {candidate.get('group_target_records')}")
if baseline.get("group_target_records") != 32:
    fail(f"baseline did not record group_target_records=32: {baseline.get('group_target_records')}")

tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks", 0))
two_contract_used = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used", 0))
two_contract_fallbacks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks", 0))
two_contract_score_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches", 0))
two_contract_min_score_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches", 0))
two_contract_scoreinfo_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches", 0))
realpath_used = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used", 0))
realpath_fallbacks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks", 0))
gpu_groups = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups", 0))
cpu_groups = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups", 0))
cpu_prealign_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds", 0.0))
compare_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds", 0.0))
gpu_minscore_hot = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot", 0))
minscore_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds", 0.0))
two_contract_total_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds", 0.0))
two_contract_h2d_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds", 0.0))
two_contract_kernel_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds", 0.0))
two_contract_d2h_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds", 0.0))
gpu_call_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds", 0.0))
kernel_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds", 0.0))
replay_requested = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested", 0))
replay_active = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active", 0))
replay_tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks", 0))
replay_selected_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts", 0))
replay_align_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts", 0))
replay_triplex_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches", 0))
replay_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds", 0.0))
replay_fallbacks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks", 0))
selected_only_replay_requested = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_requested", 0))
selected_only_replay_active = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_active", 0))
selected_only_replay_tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks", 0))
selected_only_replay_selected_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts", 0))
selected_only_replay_align_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts", 0))
selected_only_replay_selected_scoreinfos = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos", 0))
selected_only_replay_tasks_with_selected = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected", 0))
selected_only_replay_tasks_with_triplex = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex", 0))
selected_only_replay_zero_triplex_tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks", 0))
selected_only_replay_triplex_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches", 0))
selected_only_replay_mismatch_selected_empty = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty", 0))
selected_only_replay_mismatch_legacy_empty = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty", 0))
selected_only_replay_mismatch_selected_less = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less", 0))
selected_only_replay_mismatch_selected_more = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more", 0))
selected_only_replay_mismatch_same_count_diff = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff", 0))
selected_only_replay_first_mismatch_task = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task", -1))
selected_only_replay_first_mismatch_kind = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind", "none"))
selected_only_replay_first_mismatch_diff_index = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index", -1))
selected_only_replay_first_mismatch_selected_count = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count", -1))
selected_only_replay_first_mismatch_legacy_count = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count", -1))
selected_only_replay_first_mismatch_selected_key = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key", "none"))
selected_only_replay_first_mismatch_legacy_key = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key", "none"))
selected_only_replay_first_mismatch_selected_provenance = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance", "none"))
selected_only_replay_scoreinfos_with_multiple_triplexes = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes", 0))
selected_only_replay_extra_triplexes_from_repeated_scoreinfo = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo", 0))
selected_only_replay_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_seconds", 0.0))
selected_only_replay_fallbacks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks", 0))
grouped_selected_replay_requested = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested", 0))
grouped_selected_replay_active = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_active", 0))
grouped_selected_replay_tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks", 0))
grouped_selected_replay_selected_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts", 0))
grouped_selected_replay_align_attempts = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts", 0))
grouped_selected_replay_selected_scoreinfos = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos", 0))
grouped_selected_replay_tasks_with_selected = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected", 0))
grouped_selected_replay_tasks_with_triplex = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex", 0))
grouped_selected_replay_zero_triplex_tasks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks", 0))
grouped_selected_replay_triplex_mismatches = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches", 0))
grouped_selected_replay_mismatch_selected_empty = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty", 0))
grouped_selected_replay_mismatch_legacy_empty = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty", 0))
grouped_selected_replay_mismatch_selected_less = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less", 0))
grouped_selected_replay_mismatch_selected_more = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more", 0))
grouped_selected_replay_mismatch_same_count_diff = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff", 0))
grouped_selected_replay_first_mismatch_task = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task", -1))
grouped_selected_replay_first_mismatch_kind = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind", "none"))
grouped_selected_replay_first_mismatch_diff_index = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index", -1))
grouped_selected_replay_first_mismatch_selected_count = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count", -1))
grouped_selected_replay_first_mismatch_legacy_count = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count", -1))
grouped_selected_replay_first_mismatch_selected_key = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key", "none"))
grouped_selected_replay_first_mismatch_legacy_key = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key", "none"))
grouped_selected_replay_first_mismatch_selected_provenance = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance", "none"))
grouped_selected_replay_first_mismatch_legacy_provenance = str(bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance", "none"))
grouped_selected_replay_seconds = float(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds", 0.0))
grouped_selected_replay_fallbacks = int(number("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks", 0))

if tasks <= 0:
    fail(f"expected positive tasks, got {tasks}")
if two_contract_used != tasks:
    fail(f"two_contract_used != tasks: {two_contract_used} vs {tasks}")
if realpath_used != tasks:
    fail(f"realpath_used != tasks: {realpath_used} vs {tasks}")
if two_contract_fallbacks != 0:
    fail(f"expected two_contract_fallbacks=0, got {two_contract_fallbacks}")
if two_contract_score_mismatches != 0:
    fail(f"expected two_contract_score_mismatches=0, got {two_contract_score_mismatches}")
if two_contract_min_score_mismatches != 0:
    fail(
        "expected two_contract_min_score_mismatches=0, "
        f"got {two_contract_min_score_mismatches}"
    )
if two_contract_scoreinfo_mismatches != 0:
    fail(
        "expected two_contract_scoreinfo_mismatches=0, "
        f"got {two_contract_scoreinfo_mismatches}"
    )
if realpath_fallbacks != 0:
    fail(f"expected realpath_fallbacks=0, got {realpath_fallbacks}")
if gpu_groups <= 0:
    fail(f"expected positive gpu_scoreinfo_groups, got {gpu_groups}")
if cpu_groups != 0:
    fail(f"expected cpu_scoreinfo_groups=0, got {cpu_groups}")
if cpu_prealign_seconds != 0:
    fail(f"expected cpu_prealign_seconds=0, got {cpu_prealign_seconds}")
if compare_seconds != 0:
    fail(f"expected compare_seconds=0, got {compare_seconds}")
if gpu_minscore_hot <= 0:
    fail(f"expected positive gpu_minscore_hot, got {gpu_minscore_hot}")
if replay_requested > 0:
    if replay_active <= 0:
        fail("flush segmented replay probe requested but not active")
    if replay_tasks <= 0:
        fail(f"expected positive replay tasks, got {replay_tasks}")
    if replay_selected_attempts <= 0:
        fail(
            "expected positive flush segmented replay selected attempts, "
            f"got {replay_selected_attempts}"
        )
    if replay_align_attempts <= 0:
        fail(f"expected positive replay align attempts, got {replay_align_attempts}")
    if replay_triplex_mismatches != 0:
        fail(
            "expected zero flush segmented replay triplex mismatches, "
            f"got {replay_triplex_mismatches}"
        )
    if replay_seconds <= 0.0:
        fail(f"expected positive replay seconds, got {replay_seconds}")
    if replay_fallbacks != 0:
        fail(f"expected zero replay fallbacks, got {replay_fallbacks}")
if selected_only_replay_requested > 0:
    if selected_only_replay_active <= 0:
        fail("selected-only replay probe requested but not active")
    if selected_only_replay_tasks <= 0:
        fail(f"expected positive selected-only replay tasks, got {selected_only_replay_tasks}")
    if selected_only_replay_selected_attempts <= 0:
        fail(
            "expected positive selected-only replay selected attempts, "
            f"got {selected_only_replay_selected_attempts}"
        )
    if selected_only_replay_align_attempts <= 0:
        fail(
            "expected positive selected-only replay align attempts, "
            f"got {selected_only_replay_align_attempts}"
        )
    if selected_only_replay_selected_scoreinfos <= 0:
        fail(
            "expected positive selected-only replay selected scoreInfos, "
            f"got {selected_only_replay_selected_scoreinfos}"
        )
    if selected_only_replay_tasks_with_selected <= 0:
        fail(
            "expected positive selected-only replay tasks with selected attempts, "
            f"got {selected_only_replay_tasks_with_selected}"
        )
    selected_only_mismatch_class_total = (
        selected_only_replay_mismatch_selected_empty
        + selected_only_replay_mismatch_legacy_empty
        + selected_only_replay_mismatch_selected_less
        + selected_only_replay_mismatch_selected_more
        + selected_only_replay_mismatch_same_count_diff
    )
    if selected_only_mismatch_class_total != selected_only_replay_triplex_mismatches:
        fail(
            "selected-only mismatch classification does not sum to mismatches: "
            f"{selected_only_mismatch_class_total} vs {selected_only_replay_triplex_mismatches}"
        )
    if selected_only_replay_triplex_mismatches > 0:
        if selected_only_replay_first_mismatch_task < 0:
            fail("expected selected-only first mismatch task when mismatches are present")
        if selected_only_replay_first_mismatch_kind == "none":
            fail("expected selected-only first mismatch kind when mismatches are present")
    if selected_only_replay_seconds <= 0.0:
        fail(f"expected positive selected-only replay seconds, got {selected_only_replay_seconds}")
    if selected_only_replay_fallbacks != 0:
        fail(f"expected zero selected-only replay fallbacks, got {selected_only_replay_fallbacks}")
if grouped_selected_replay_requested > 0:
    if grouped_selected_replay_active <= 0:
        fail("grouped-selected replay probe requested but not active")
    if grouped_selected_replay_tasks <= 0:
        fail(f"expected positive grouped-selected replay tasks, got {grouped_selected_replay_tasks}")
    if grouped_selected_replay_selected_attempts <= 0:
        fail(
            "expected positive grouped-selected replay selected attempts, "
            f"got {grouped_selected_replay_selected_attempts}"
        )
    if grouped_selected_replay_align_attempts <= 0:
        fail(
            "expected positive grouped-selected replay align attempts, "
            f"got {grouped_selected_replay_align_attempts}"
        )
    if grouped_selected_replay_selected_scoreinfos <= 0:
        fail(
            "expected positive grouped-selected replay selected scoreInfos, "
            f"got {grouped_selected_replay_selected_scoreinfos}"
        )
    if grouped_selected_replay_tasks_with_selected <= 0:
        fail(
            "expected positive grouped-selected replay tasks with selected attempts, "
            f"got {grouped_selected_replay_tasks_with_selected}"
        )
    grouped_selected_mismatch_class_total = (
        grouped_selected_replay_mismatch_selected_empty
        + grouped_selected_replay_mismatch_legacy_empty
        + grouped_selected_replay_mismatch_selected_less
        + grouped_selected_replay_mismatch_selected_more
        + grouped_selected_replay_mismatch_same_count_diff
    )
    if grouped_selected_mismatch_class_total != grouped_selected_replay_triplex_mismatches:
        fail(
            "grouped-selected mismatch classification does not sum to mismatches: "
            f"{grouped_selected_mismatch_class_total} vs {grouped_selected_replay_triplex_mismatches}"
        )
    if grouped_selected_replay_triplex_mismatches > 0:
        if grouped_selected_replay_first_mismatch_task < 0:
            fail("expected grouped-selected first mismatch task when mismatches are present")
        if grouped_selected_replay_first_mismatch_kind == "none":
            fail("expected grouped-selected first mismatch kind when mismatches are present")
    if grouped_selected_replay_seconds <= 0.0:
        fail(f"expected positive grouped-selected replay seconds, got {grouped_selected_replay_seconds}")
    if grouped_selected_replay_fallbacks != 0:
        fail(f"expected zero grouped-selected replay fallbacks, got {grouped_selected_replay_fallbacks}")
for name, value in (
    ("baseline_runner_wall_seconds", baseline_runner_wall_seconds),
    ("candidate_runner_wall_seconds", candidate_runner_wall_seconds),
    ("candidate_two_contract_total_seconds", two_contract_total_seconds),
    ("candidate_two_contract_h2d_seconds", two_contract_h2d_seconds),
    ("candidate_two_contract_kernel_seconds", two_contract_kernel_seconds),
    ("candidate_two_contract_d2h_seconds", two_contract_d2h_seconds),
    ("candidate_gpu_call_seconds", gpu_call_seconds),
    ("candidate_kernel_seconds", kernel_seconds),
):
    if value <= 0.0:
        fail(f"expected positive {name}, got {value}")

candidate_vs_baseline = (
    baseline_runner_wall_seconds / candidate_runner_wall_seconds
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
    "two_contract_used": two_contract_used,
    "two_contract_fallbacks": two_contract_fallbacks,
    "two_contract_score_mismatches": two_contract_score_mismatches,
    "two_contract_min_score_mismatches": two_contract_min_score_mismatches,
    "two_contract_scoreinfo_mismatches": two_contract_scoreinfo_mismatches,
    "realpath_used": realpath_used,
    "realpath_fallbacks": realpath_fallbacks,
    "gpu_scoreinfo_groups": gpu_groups,
    "gpu_minscore_hot": gpu_minscore_hot,
    "minscore_seconds": minscore_seconds,
    "cpu_scoreinfo_groups": cpu_groups,
    "cpu_prealign_seconds": cpu_prealign_seconds,
    "compare_seconds": compare_seconds,
    "candidate_two_contract_total_seconds": two_contract_total_seconds,
    "candidate_two_contract_h2d_seconds": two_contract_h2d_seconds,
    "candidate_two_contract_kernel_seconds": two_contract_kernel_seconds,
    "candidate_two_contract_d2h_seconds": two_contract_d2h_seconds,
    "candidate_gpu_call_seconds": gpu_call_seconds,
    "candidate_kernel_seconds": kernel_seconds,
    "candidate_realpath_extend_flush_segmented_replay_probe_requested": replay_requested,
    "candidate_realpath_extend_flush_segmented_replay_probe_active": replay_active,
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks": replay_tasks,
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts": replay_selected_attempts,
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts": replay_align_attempts,
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches": replay_triplex_mismatches,
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds": replay_seconds,
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks": replay_fallbacks,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_requested": selected_only_replay_requested,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_active": selected_only_replay_active,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks": selected_only_replay_tasks,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts": selected_only_replay_selected_attempts,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts": selected_only_replay_align_attempts,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos": selected_only_replay_selected_scoreinfos,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected": selected_only_replay_tasks_with_selected,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex": selected_only_replay_tasks_with_triplex,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks": selected_only_replay_zero_triplex_tasks,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches": selected_only_replay_triplex_mismatches,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty": selected_only_replay_mismatch_selected_empty,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty": selected_only_replay_mismatch_legacy_empty,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less": selected_only_replay_mismatch_selected_less,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more": selected_only_replay_mismatch_selected_more,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff": selected_only_replay_mismatch_same_count_diff,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task": selected_only_replay_first_mismatch_task,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind": selected_only_replay_first_mismatch_kind,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index": selected_only_replay_first_mismatch_diff_index,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count": selected_only_replay_first_mismatch_selected_count,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count": selected_only_replay_first_mismatch_legacy_count,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key": selected_only_replay_first_mismatch_selected_key,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key": selected_only_replay_first_mismatch_legacy_key,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance": selected_only_replay_first_mismatch_selected_provenance,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes": selected_only_replay_scoreinfos_with_multiple_triplexes,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo": selected_only_replay_extra_triplexes_from_repeated_scoreinfo,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_seconds": selected_only_replay_seconds,
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks": selected_only_replay_fallbacks,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested": grouped_selected_replay_requested,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_active": grouped_selected_replay_active,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks": grouped_selected_replay_tasks,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts": grouped_selected_replay_selected_attempts,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts": grouped_selected_replay_align_attempts,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos": grouped_selected_replay_selected_scoreinfos,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected": grouped_selected_replay_tasks_with_selected,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex": grouped_selected_replay_tasks_with_triplex,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks": grouped_selected_replay_zero_triplex_tasks,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches": grouped_selected_replay_triplex_mismatches,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty": grouped_selected_replay_mismatch_selected_empty,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty": grouped_selected_replay_mismatch_legacy_empty,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less": grouped_selected_replay_mismatch_selected_less,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more": grouped_selected_replay_mismatch_selected_more,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff": grouped_selected_replay_mismatch_same_count_diff,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task": grouped_selected_replay_first_mismatch_task,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind": grouped_selected_replay_first_mismatch_kind,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index": grouped_selected_replay_first_mismatch_diff_index,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count": grouped_selected_replay_first_mismatch_selected_count,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count": grouped_selected_replay_first_mismatch_legacy_count,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key": grouped_selected_replay_first_mismatch_selected_key,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key": grouped_selected_replay_first_mismatch_legacy_key,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance": grouped_selected_replay_first_mismatch_selected_provenance,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance": grouped_selected_replay_first_mismatch_legacy_provenance,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds": grouped_selected_replay_seconds,
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks": grouped_selected_replay_fallbacks,
    "decision": "accepted_by_external_digest_gate",
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
PY
