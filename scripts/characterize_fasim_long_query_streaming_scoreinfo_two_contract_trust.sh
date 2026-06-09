#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_two_contract_trust"}"
BUILD_BIN="${BUILD_BIN:-1}"
WORKERS="${WORKERS:-1}"
GPU_IDS="${GPU_IDS:-}"
GROUP_TARGET_RECORDS="${GROUP_TARGET_RECORDS:-}"
TWO_CONTRACT_CASES="${TWO_CONTRACT_CASES:-MALAT1:8}"
TWO_CONTRACT_TRUST_PRESET="${TWO_CONTRACT_TRUST_PRESET:-plain}"

MALAT1_RNA="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
MALAT1_DNA="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"
NEAT1_RNA="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
NEAT1_DNA="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

case "$WORKERS" in
  ''|*[!0-9]*)
    echo "WORKERS must be a positive integer, got: $WORKERS" >&2
    exit 1
    ;;
esac
if [[ "$WORKERS" -le 0 ]]; then
  echo "WORKERS must be a positive integer, got: $WORKERS" >&2
  exit 1
fi
if [[ -n "$GROUP_TARGET_RECORDS" ]]; then
  case "$GROUP_TARGET_RECORDS" in
    *[!0-9]*)
      echo "GROUP_TARGET_RECORDS must be a positive integer when set, got: $GROUP_TARGET_RECORDS" >&2
      exit 1
      ;;
  esac
  if [[ "$GROUP_TARGET_RECORDS" -le 0 ]]; then
    echo "GROUP_TARGET_RECORDS must be a positive integer when set, got: $GROUP_TARGET_RECORDS" >&2
    exit 1
  fi
fi
case "$TWO_CONTRACT_TRUST_PRESET" in
  plain)
    candidate_trust_args=(--long-query-streaming-scoreinfo-gpu-two-contract-trust)
    expected_contract="long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1"
    expected_profile=""
    ;;
  group32)
    if [[ "$GROUP_TARGET_RECORDS" != "32" ]]; then
      echo "TWO_CONTRACT_TRUST_PRESET=group32 requires GROUP_TARGET_RECORDS=32" >&2
      exit 1
    fi
    candidate_trust_args=(--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32)
    expected_contract="long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1"
    expected_profile="malat1_like_two_contract_group32_experimental_v1"
    ;;
  *)
    echo "TWO_CONTRACT_TRUST_PRESET must be plain or group32, got: $TWO_CONTRACT_TRUST_PRESET" >&2
    exit 1
    ;;
esac

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	workload	record_limit	group_target_records	shard_count	worker_count	digest	merged_records	tasks	two_contract_used	two_contract_fallbacks	two_contract_score_mismatches	two_contract_min_score_mismatches	two_contract_scoreinfo_mismatches	realpath_used	realpath_fallbacks	gpu_scoreinfo_groups	cpu_scoreinfo_groups	cpu_prealign_seconds	compare_seconds	gpu_minscore_hot	minscore_seconds	two_contract_total_seconds	two_contract_h2d_seconds	two_contract_kernel_seconds	two_contract_d2h_seconds	gpu_call_seconds	kernel_seconds	baseline_runner_wall_seconds	candidate_runner_wall_seconds	candidate_vs_baseline	result_contract	decision" \
  >"$summary"

sample_records() {
  local source="$1"
  local limit="$2"
  local output="$3"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$source" >"$output"
  if [[ ! -s "$output" ]]; then
    echo "empty sample created from $source limit=$limit" >&2
    exit 1
  fi
}

run_runner() {
  local target="$1"
  local rna="$2"
  local out_dir="$3"
  shift 3
  local report="$out_dir.report.json"
  local stderr="$out_dir.runner.stderr"
  local start end
  local gpu_args=()
  local group_args=()
  if [[ -n "$GPU_IDS" ]]; then
    gpu_args=(--gpu-ids "$GPU_IDS")
  fi
  if [[ -n "$GROUP_TARGET_RECORDS" ]]; then
    group_args=(--group-target-records "$GROUP_TARGET_RECORDS")
  fi

  start="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
  python3 "$RUNNER" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$rna" \
    --rule 0 \
    --work-dir "$out_dir" \
    --manifest "$out_dir/run_manifest.json" \
    --workers "$WORKERS" \
    "${gpu_args[@]}" \
    "${group_args[@]}" \
    "$@" \
    >"$report" 2>"$stderr"
  end="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
  python3 - "$start" "$end" <<'PY'
import sys
start = float(sys.argv[1])
end = float(sys.argv[2])
print(f"{end - start:.6f}")
PY
}

run_case() {
  local case_spec="$1"
  local workload="${case_spec%%:*}"
  local limit="${case_spec#*:}"
  if [[ "$workload" == "$limit" || -z "$workload" || -z "$limit" ]]; then
    echo "case must use WORKLOAD:RECORD_LIMIT syntax, got: $case_spec" >&2
    exit 1
  fi
  workload="${workload^^}"
  case "$limit" in
    ''|*[!0-9]*)
      echo "record limit must be a positive integer, got: $case_spec" >&2
      exit 1
      ;;
  esac
  if [[ "$limit" -le 0 ]]; then
    echo "record limit must be a positive integer, got: $case_spec" >&2
    exit 1
  fi

  local rna_input dna_input label expected_query_len
  case "$workload" in
    MALAT1)
      rna_input="$MALAT1_RNA"
      dna_input="$MALAT1_DNA"
      expected_query_len=8708
      ;;
    NEAT1)
      rna_input="$NEAT1_RNA"
      dna_input="$NEAT1_DNA"
      expected_query_len=22767
      ;;
    *)
      echo "unsupported workload in case $case_spec; expected MALAT1 or NEAT1" >&2
      exit 1
      ;;
  esac
  if [[ ! -s "$rna_input" || ! -s "$dna_input" ]]; then
    echo "missing $workload inputs: rna=$rna_input dna=$dna_input" >&2
    exit 1
  fi

  label="${workload,,}_first${limit}"
  local run_work="$WORK/$label"
  local sample="$WORK/inputs/$label.fa"
  mkdir -p "$run_work"
  sample_records "$dna_input" "$limit" "$sample"

  echo "running $workload first${limit} two-contract trust characterization" >&2
  local baseline_wall candidate_wall
  baseline_wall="$(run_runner "$sample" "$rna_input" "$run_work/baseline")"
  candidate_wall="$(run_runner "$sample" "$rna_input" "$run_work/candidate" \
    "${candidate_trust_args[@]}")"

  python3 - \
    "$run_work/baseline.report.json" \
    "$run_work/candidate.report.json" \
    "$baseline_wall" \
    "$candidate_wall" \
    "$label" \
    "$workload" \
    "$limit" \
    "${GROUP_TARGET_RECORDS:-null}" \
    "$expected_query_len" \
    "$expected_contract" \
    "${expected_profile:-null}" \
    >>"$summary" <<'PY'
import json
import sys
from pathlib import Path

baseline_path = Path(sys.argv[1])
candidate_path = Path(sys.argv[2])
baseline_wall = float(sys.argv[3])
candidate_wall = float(sys.argv[4])
label = sys.argv[5]
workload = sys.argv[6]
record_limit = int(sys.argv[7])
group_target_records = sys.argv[8]
expected_query_len = int(sys.argv[9])
expected_contract = sys.argv[10]
expected_profile = None if sys.argv[11] == "null" else sys.argv[11]

baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
if baseline["merged_digest"] != candidate["merged_digest"]:
    raise SystemExit(
        f"{label} two-contract trust changed merged digest: "
        f"baseline={baseline['merged_digest']} candidate={candidate['merged_digest']}"
    )
if candidate["result_contract"] != expected_contract:
    raise SystemExit(f"{label} unexpected result_contract={candidate['result_contract']}")
if candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust") is not True:
    raise SystemExit(f"{label} did not record two-contract trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile") != expected_profile:
    raise SystemExit(
        f"{label} unexpected trust_profile="
        f"{candidate.get('long_query_streaming_scoreinfo_gpu_trust_profile')}"
    )
if expected_profile:
    if candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust_group32") is not True:
        raise SystemExit(f"{label} did not record two-contract group32 flag")
    if candidate.get("group_target_records") != 32:
        raise SystemExit(
            f"{label} group32 preset did not record group_target_records=32: "
            f"{candidate.get('group_target_records')}"
        )
if candidate.get("long_query_streaming_scoreinfo_gpu_trust") is not False:
    raise SystemExit(f"{label} unexpectedly recorded legacy trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_decision") != "experimental_external_digest_gate":
    raise SystemExit(f"{label} missing external digest gate decision")
if baseline["result_contract"] == candidate["result_contract"]:
    raise SystemExit(f"{label} baseline and candidate contracts must differ")

bench = candidate.get("fasim_benchmark_sums", {})
shard_count = candidate["shard_count"]

def value(key):
    if key not in bench:
        raise SystemExit(f"{label} missing benchmark metric: {key}")
    return bench[key]

requested = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested")
active = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active")
tasks = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks")
query_len_sum = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_query_len")
two_used = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used")
two_fallbacks = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks")
two_score_mismatches = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches")
two_min_score_mismatches = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches")
two_scoreinfo_mismatches = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches")
realpath_used = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used")
realpath_fallbacks = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks")
realpath_trust = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust")
realpath_authority = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority")
gpu_groups = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups")
cpu_groups = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups")
cpu_prealign = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds")
compare_seconds = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds")
candidate_missing = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing")
candidate_extra = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra")
legacy_byte_shared = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared")
gpu_minscore_hot = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot")
minscore_seconds = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds")
two_total = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds")
two_h2d = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds")
two_kernel = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds")
two_d2h = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds")
gpu_call = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds")
kernel = value("fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds")

if requested != shard_count:
    raise SystemExit(
        f"{label} expected two-contract requested to equal shard_count={shard_count}, "
        f"got requested={requested}"
    )
if query_len_sum != expected_query_len * shard_count:
    raise SystemExit(
        f"{label} expected query_len sum {expected_query_len * shard_count}, "
        f"got {query_len_sum}"
    )
if not isinstance(tasks, int) or tasks <= 0:
    raise SystemExit(f"{label} expected positive task count, got {tasks}")
if realpath_trust != shard_count or realpath_authority != "external_digest_gate":
    raise SystemExit(
        f"{label} expected external digest trust on all shards, "
        f"got trust={realpath_trust} authority={realpath_authority}"
    )
if legacy_byte_shared != shard_count:
    raise SystemExit(
        f"{label} expected legacy_byte_shared on all shards, "
        f"got {legacy_byte_shared} shard_count={shard_count}"
    )

decisions = set()
for shard in candidate["per_shard"]:
    run = shard.get("run") or {}
    stderr_path = run.get("stderr_path")
    if not stderr_path:
        continue
    stderr = Path(stderr_path).read_text(encoding="utf-8", errors="replace")
    for line in stderr.splitlines():
        if line.startswith("benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision="):
            decisions.add(line.split("=", 1)[1])

clean_active = (
    active == shard_count
    and two_used == tasks
    and realpath_used == tasks
    and two_fallbacks == 0
    and two_score_mismatches == 0
    and two_min_score_mismatches == 0
    and two_scoreinfo_mismatches == 0
    and realpath_fallbacks == 0
    and cpu_groups == 0
    and cpu_prealign == 0
    and compare_seconds == 0
    and gpu_minscore_hot == shard_count
    and candidate_missing == 0
    and candidate_extra == 0
    and isinstance(gpu_groups, int)
    and gpu_groups > 0
    and decisions == {"two_contract_bridge_trust_active"}
)
launch_failed = (
    active == 0
    and two_fallbacks == shard_count
    and realpath_fallbacks == shard_count
    and realpath_used == 0
    and cpu_groups == 0
    and cpu_prealign == 0
    and compare_seconds == 0
    and candidate_missing == 0
    and candidate_extra == 0
    and decisions == {"two_contract_bridge_shadow_launch_failed"}
)
if not clean_active and not launch_failed:
    raise SystemExit(
        f"{label} expected clean active row or clean launch-failed fallback row, got "
        f"active={active} shard_count={shard_count} two_used={two_used} tasks={tasks} "
        f"fallbacks={two_fallbacks}/{realpath_fallbacks} realpath_used={realpath_used} "
        f"score={two_score_mismatches} min_score={two_min_score_mismatches} "
        f"scoreinfo={two_scoreinfo_mismatches} cpu_groups={cpu_groups} "
        f"cpu_prealign={cpu_prealign} compare={compare_seconds} "
        f"missing={candidate_missing} extra={candidate_extra} "
        f"gpu_groups={gpu_groups} decisions={sorted(decisions)}"
    )
if clean_active:
    for timing_name, timing_value in (
        ("two_contract_total_seconds", two_total),
        ("two_contract_kernel_seconds", two_kernel),
        ("gpu_call_seconds", gpu_call),
        ("kernel_seconds", kernel),
    ):
        if float(timing_value) <= 0.0:
            raise SystemExit(f"{label} expected positive {timing_name}, got {timing_value}")
decision = "two_contract_bridge_trust_active" if clean_active else "two_contract_bridge_launch_failed"

speedup = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
row = [
    label,
    workload,
    str(record_limit),
    group_target_records,
    str(shard_count),
    str(candidate["worker_count"]),
    str(candidate["merged_digest"]),
    str(candidate["merged_records"]),
    str(tasks),
    str(two_used),
    str(two_fallbacks),
    str(two_score_mismatches),
    str(two_min_score_mismatches),
    str(two_scoreinfo_mismatches),
    str(realpath_used),
    str(realpath_fallbacks),
    str(gpu_groups),
    str(cpu_groups),
    str(cpu_prealign),
    str(compare_seconds),
    str(gpu_minscore_hot),
    str(minscore_seconds),
    str(two_total),
    str(two_h2d),
    str(two_kernel),
    str(two_d2h),
    str(gpu_call),
    str(kernel),
    f"{baseline_wall:.6f}",
    f"{candidate_wall:.6f}",
    f"{speedup:.6f}x",
    str(candidate["result_contract"]),
    decision,
]
print("\t".join(row))
PY
}

for case_spec in $TWO_CONTRACT_CASES; do
  run_case "$case_spec"
done

cat "$summary"
