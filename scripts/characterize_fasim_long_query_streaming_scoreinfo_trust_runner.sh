#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_trust_runner"}"
BUILD_BIN="${BUILD_BIN:-1}"
WORKERS="${WORKERS:-1}"
GPU_IDS="${GPU_IDS:-}"
GROUP_TARGET_RECORDS="${GROUP_TARGET_RECORDS:-}"
TRUST_PRESET="${TRUST_PRESET:-plain}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-8 16 32 64}"
RNA_INPUT="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
DNA_INPUT="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

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
case "$TRUST_PRESET" in
  plain)
    candidate_trust_args=(--long-query-streaming-scoreinfo-gpu-trust)
    expected_contract="long_query_streaming_scoreinfo_gpu_trust_experimental_v1"
    expected_profile=""
    ;;
  group32)
    if [[ "$GROUP_TARGET_RECORDS" != "32" ]]; then
      echo "TRUST_PRESET=group32 requires GROUP_TARGET_RECORDS=32" >&2
      exit 1
    fi
    candidate_trust_args=(--long-query-streaming-scoreinfo-gpu-trust-group32)
    expected_contract="long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1"
    expected_profile="malat1_like_group32_experimental_v1"
    ;;
  *)
    echo "TRUST_PRESET must be plain or group32, got: $TRUST_PRESET" >&2
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
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing MALAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	record_limit	group_target_records	digest	shard_count	worker_count	merged_records	tasks	realpath_used	realpath_fallbacks	realpath_digest_authority	gpu_scoreinfo_groups	cpu_scoreinfo_groups	gpu_minscore_used	gpu_minscore_fallbacks	gpu_total_seconds	gpu_call_seconds	kernel_seconds	realpath_extend_calls	realpath_extend_seconds	realpath_extend_scoreinfo_groups	realpath_extend_align_attempts	realpath_extend_substr_seconds	realpath_extend_align_seconds	realpath_extend_convert_seconds	realpath_extend_sort_seconds	realpath_extend_filter_seconds	cpu_prealign_seconds	compare_seconds	baseline_runner_wall_seconds	candidate_runner_wall_seconds	candidate_vs_baseline	result_contract	trust_profile	decision" \
  >"$summary"

run_runner() {
  local label="$1"
  local target="$2"
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
    --rna "$RNA_INPUT" \
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

run_limit() {
  local limit="$1"
  case "$limit" in
    ''|*[!0-9]*)
      echo "record limits must contain positive integers, got: $limit" >&2
      exit 1
      ;;
  esac
  if [[ "$limit" -le 0 ]]; then
    echo "record limits must contain positive integers, got: $limit" >&2
    exit 1
  fi

  local run_work="$WORK/malat1_first${limit}"
  local sample="$WORK/inputs/malat1_first${limit}.fa"
  mkdir -p "$run_work"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$DNA_INPUT" >"$sample"
  if [[ ! -s "$sample" ]]; then
    echo "empty MALAT1 sample for record_limit=$limit" >&2
    exit 1
  fi

  echo "running MALAT1 first${limit} trust runner characterization" >&2
  local baseline_wall candidate_wall
  baseline_wall="$(run_runner baseline "$sample" "$run_work/baseline")"
  candidate_wall="$(run_runner candidate "$sample" "$run_work/candidate" "${candidate_trust_args[@]}")"

  python3 - \
    "$run_work/baseline.report.json" \
    "$run_work/candidate.report.json" \
    "$baseline_wall" \
    "$candidate_wall" \
    "$limit" \
    "${GROUP_TARGET_RECORDS:-null}" \
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
record_limit = int(sys.argv[5])
group_target_records = sys.argv[6]
expected_contract = sys.argv[7]
expected_profile = None if sys.argv[8] == "null" else sys.argv[8]

baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

if baseline["merged_digest"] != candidate["merged_digest"]:
    raise SystemExit(
        "trust runner changed merged digest for MALAT1 first"
        f"{record_limit}: baseline={baseline['merged_digest']} "
        f"candidate={candidate['merged_digest']}"
    )
if candidate["result_contract"] != expected_contract:
    raise SystemExit(f"unexpected result_contract: {candidate['result_contract']}")
if candidate["long_query_streaming_scoreinfo_gpu_trust"] is not True:
    raise SystemExit("candidate did not record long-query trust flag")
if candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile") != expected_profile:
    raise SystemExit(
        "candidate trust profile mismatch: "
        f"{candidate.get('long_query_streaming_scoreinfo_gpu_trust_profile')}"
    )
if expected_profile:
    if candidate.get("long_query_streaming_scoreinfo_gpu_trust_group32") is not True:
        raise SystemExit("candidate did not record group32 trust flag")
    if candidate.get("group_target_records") != 32:
        raise SystemExit(
            f"group32 preset candidate did not record group_target_records=32: "
            f"{candidate.get('group_target_records')}"
        )
if candidate["long_query_streaming_scoreinfo_gpu_trust_decision"] != "experimental_external_digest_gate":
    raise SystemExit("candidate did not record external digest gate decision")
if baseline["result_contract"] == candidate["result_contract"]:
    raise SystemExit("baseline and candidate result contracts must differ")

bench = candidate["fasim_benchmark_sums"]
shard_count = candidate["shard_count"]
expected = {
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_requested": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_active": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds": 0,
}
for key, expected_value in expected.items():
    actual = bench.get(key)
    if actual != expected_value:
        raise SystemExit(f"unexpected {key}: {actual} expected {expected_value}")

required_numeric = [
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_calls",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds",
]
missing = [key for key in required_numeric if key not in bench]
if missing:
    raise SystemExit("candidate report missing metrics: " + ", ".join(missing))

tasks = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks"]
realpath_used = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used"]
gpu_minscore_used = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used"]
gpu_groups = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups"]
extend_calls = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_calls"]
extend_groups = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups"]
extend_align_attempts = bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts"]
if not isinstance(tasks, int) or tasks <= 0:
    raise SystemExit(f"expected positive integer tasks, got {tasks}")
if realpath_used != tasks:
    raise SystemExit(f"realpath_used != tasks: {realpath_used} vs {tasks}")
if gpu_minscore_used != tasks:
    raise SystemExit(f"gpu_minscore_used != tasks: {gpu_minscore_used} vs {tasks}")
if not isinstance(gpu_groups, int) or gpu_groups <= 0:
    raise SystemExit(f"expected positive GPU scoreInfo groups, got {gpu_groups}")
if not isinstance(extend_calls, int) or extend_calls <= 0:
    raise SystemExit(f"expected positive realpath extend calls, got {extend_calls}")
if not isinstance(extend_groups, int) or extend_groups <= 0:
    raise SystemExit(f"expected positive realpath extend scoreInfo groups, got {extend_groups}")
if not isinstance(extend_align_attempts, int) or extend_align_attempts <= 0:
    raise SystemExit(f"expected positive realpath extend align attempts, got {extend_align_attempts}")
if bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds"] <= 0:
    raise SystemExit("expected positive realpath extend align seconds")

authorities = set()
decisions = set()
for shard in candidate["per_shard"]:
    stderr_path = Path(shard["run"]["stderr_path"])
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    for line in stderr.splitlines():
        if line.startswith("benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority="):
            authorities.add(line.split("=", 1)[1])
        elif line.startswith("benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision="):
            decisions.add(line.split("=", 1)[1])
if authorities != {"external_digest_gate"}:
    raise SystemExit(f"unexpected realpath digest authority set: {sorted(authorities)}")
if decisions != {"streaming_scoreinfo_shadow_active"}:
    raise SystemExit(f"unexpected decision set: {sorted(decisions)}")

speedup = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
row = [
    f"malat1_first{record_limit}",
    str(record_limit),
    group_target_records,
    str(candidate["merged_digest"]),
    str(shard_count),
    str(candidate["worker_count"]),
    str(candidate["merged_records"]),
    str(tasks),
    str(realpath_used),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks"]),
    "external_digest_gate",
    str(gpu_groups),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups"]),
    str(gpu_minscore_used),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds"]),
    str(extend_calls),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds"]),
    str(extend_groups),
    str(extend_align_attempts),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds"]),
    str(bench["fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds"]),
    f"{baseline_wall:.6f}",
    f"{candidate_wall:.6f}",
    f"{speedup:.6f}x",
    str(candidate["result_contract"]),
    str(candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile") or "null"),
    "streaming_scoreinfo_shadow_active",
]
print("\t".join(row))
PY
}

for limit in $MALAT1_RECORD_LIMITS; do
  run_limit "$limit"
done

cat "$summary"
