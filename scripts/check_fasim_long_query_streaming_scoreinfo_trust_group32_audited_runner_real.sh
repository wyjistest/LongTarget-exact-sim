#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner_real"}"
BUILD_BIN="${BUILD_BIN:-1}"
RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-1}"
RNA_INPUT="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
DNA_INPUT="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

case "$RECORD_LIMIT" in
  ''|*[!0-9]*)
    echo "MALAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
    exit 1
    ;;
esac
if [[ "$RECORD_LIMIT" -le 0 ]]; then
  echo "MALAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
  exit 1
fi
case "$REPLAY_PROBE_MAX_TASKS" in
  ''|*[!0-9]*)
    echo "REPLAY_PROBE_MAX_TASKS must be a non-negative integer, got: $REPLAY_PROBE_MAX_TASKS" >&2
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
if [[ ! -x "$WRAPPER" ]]; then
  echo "missing audited wrapper: $WRAPPER" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing MALAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"
sample="$WORK/inputs/malat1_first${RECORD_LIMIT}.fa"
awk -v limit="$RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty MALAT1 sample" >&2
  exit 1
fi

"$WRAPPER" \
  --fasim-bin "$BIN" \
  --target "$sample" \
  --rna "$RNA_INPUT" \
  --work-dir "$WORK/audit" \
  --workers 1 \
  --replay-probe-max-tasks "$REPLAY_PROBE_MAX_TASKS" \
  >"$WORK/fresh.json"

"$WRAPPER" \
  --fasim-bin "$BIN" \
  --target "$sample" \
  --rna "$RNA_INPUT" \
  --work-dir "$WORK/audit" \
  --workers 1 \
  --replay-probe-max-tasks "$REPLAY_PROBE_MAX_TASKS" \
  --resume \
  >"$WORK/resume.json"

python3 - "$WORK/fresh.json" "$WORK/resume.json" "$REPLAY_PROBE_MAX_TASKS" <<'PY'
import json
import sys
from pathlib import Path

fresh = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
resume = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
replay_probe_max_tasks = int(sys.argv[3])

for label, payload in (("fresh", fresh), ("resume", resume)):
    if payload["audited_status"] != "accepted":
        raise SystemExit(f"{label}: unexpected audited_status={payload['audited_status']}")
    if payload["baseline_digest"] != payload["candidate_digest"]:
        raise SystemExit(f"{label}: digest mismatch")
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1":
        raise SystemExit(f"{label}: unexpected contract={payload['result_contract']}")
    if payload["trust_profile"] != "malat1_like_group32_experimental_v1":
        raise SystemExit(f"{label}: unexpected trust_profile={payload['trust_profile']}")
    if payload["group_target_records"] != 32:
        raise SystemExit(f"{label}: group_target_records != 32")
    if payload["tasks"] <= 0:
        raise SystemExit(f"{label}: expected positive tasks")
    expected_replay_tasks = (
        payload["tasks"]
        if replay_probe_max_tasks == 0
        else payload["candidate_realpath_extend_flush_segmented_attempt_probe_flushes"]
        * replay_probe_max_tasks
    )
    if payload["candidate_realpath_extend_flush_segmented_replay_probe_tasks"] != expected_replay_tasks:
        raise SystemExit(
            f"{label}: segmented replay tasks != flushes * cap "
            f"({payload['candidate_realpath_extend_flush_segmented_replay_probe_tasks']} != "
            f"{expected_replay_tasks})"
        )
    if payload["candidate_realpath_extend_flush_full_replay_probe_tasks"] != expected_replay_tasks:
        raise SystemExit(
            f"{label}: full replay tasks != flushes * cap "
            f"({payload['candidate_realpath_extend_flush_full_replay_probe_tasks']} != "
            f"{expected_replay_tasks})"
        )
    if payload["candidate_realpath_extend_flush_oracle_replay_probe_tasks"] != expected_replay_tasks:
        raise SystemExit(
            f"{label}: oracle replay tasks != flushes * cap "
            f"({payload['candidate_realpath_extend_flush_oracle_replay_probe_tasks']} != "
            f"{expected_replay_tasks})"
        )
    for key in ("baseline_runner_wall_seconds", "candidate_runner_wall_seconds", "candidate_vs_baseline"):
        if float(payload[key]) <= 0.0:
            raise SystemExit(f"{label}: expected positive {key}, got {payload[key]}")
    for key in (
        "candidate_gpu_scoreinfo_total_seconds",
        "candidate_gpu_scoreinfo_call_seconds",
        "candidate_gpu_scoreinfo_kernel_seconds",
        "candidate_gpu_scoreinfo_wall_fraction",
        "candidate_gpu_scoreinfo_call_fraction",
        "candidate_realpath_extend_seconds",
        "candidate_realpath_extend_calls",
        "candidate_realpath_extend_fraction",
        "candidate_realpath_extend_scoreinfo_groups",
        "candidate_realpath_extend_align_attempts",
        "candidate_realpath_extend_align_seconds",
        "candidate_realpath_extend_align_fraction",
        "candidate_realpath_extend_attempt_probe_requested",
        "candidate_realpath_extend_attempt_probe_calls",
        "candidate_realpath_extend_attempt_probe_attempts",
        "candidate_realpath_extend_attempt_probe_seconds",
        "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
        "candidate_realpath_extend_flush_segmented_attempt_probe_flushes",
        "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
        "candidate_realpath_extend_flush_segmented_attempt_probe_calls",
        "candidate_realpath_extend_flush_segmented_attempt_probe_attempts",
        "candidate_realpath_extend_flush_segmented_attempt_probe_seconds",
        "candidate_realpath_extend_flush_segmented_replay_probe_requested",
        "candidate_realpath_extend_flush_segmented_replay_probe_active",
        "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
        "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
        "candidate_realpath_extend_flush_full_replay_probe_requested",
        "candidate_realpath_extend_flush_full_replay_probe_active",
        "candidate_realpath_extend_flush_full_replay_probe_tasks",
        "candidate_realpath_extend_flush_full_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_full_replay_probe_seconds",
        "candidate_realpath_extend_flush_oracle_replay_probe_requested",
        "candidate_realpath_extend_flush_oracle_replay_probe_active",
        "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
        "candidate_realpath_extend_flush_oracle_replay_probe_seconds",
    ):
        if float(payload[key]) <= 0.0:
            raise SystemExit(f"{label}: expected positive {key}, got {payload[key]}")
    for key in (
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_task",
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index",
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count",
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count",
    ):
        if key not in payload:
            raise SystemExit(f"{label}: missing {key}")
    for key in (
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key",
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key",
        "candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance",
    ):
        if key not in payload or not isinstance(payload[key], str) or not payload[key]:
            raise SystemExit(f"{label}: missing {key}")
    for key in (
        "candidate_realpath_extend_substr_seconds",
        "candidate_realpath_extend_convert_seconds",
        "candidate_realpath_extend_sort_seconds",
        "candidate_realpath_extend_filter_seconds",
        "candidate_realpath_extend_attempt_probe_active",
        "candidate_realpath_extend_attempt_probe_selected_attempts",
        "candidate_realpath_extend_attempt_probe_fallbacks",
        "candidate_realpath_extend_segmented_attempt_probe_active",
        "candidate_realpath_extend_segmented_attempt_probe_requested",
        "candidate_realpath_extend_segmented_attempt_probe_segments",
        "candidate_realpath_extend_segmented_attempt_probe_calls",
        "candidate_realpath_extend_segmented_attempt_probe_attempts",
        "candidate_realpath_extend_segmented_attempt_probe_selected_attempts",
        "candidate_realpath_extend_segmented_attempt_probe_seconds",
        "candidate_realpath_extend_segmented_attempt_probe_fallbacks",
        "candidate_realpath_extend_flush_segmented_attempt_probe_active",
        "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks",
        "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
        "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_full_replay_probe_fallbacks",
        "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches",
    ):
        if float(payload[key]) < 0.0:
            raise SystemExit(f"{label}: expected non-negative {key}, got {payload[key]}")
    if label == "fresh":
        if float(payload["candidate_post_scoreinfo_unattributed_seconds"]) <= 0.0:
            raise SystemExit(
                f"{label}: expected positive candidate_post_scoreinfo_unattributed_seconds, "
                f"got {payload['candidate_post_scoreinfo_unattributed_seconds']}"
            )
        if float(payload["candidate_post_scoreinfo_unattributed_fraction"]) <= 0.0:
            raise SystemExit(
                f"{label}: expected positive candidate_post_scoreinfo_unattributed_fraction, "
                f"got {payload['candidate_post_scoreinfo_unattributed_fraction']}"
            )
    else:
        for key in (
            "candidate_post_scoreinfo_unattributed_seconds",
            "candidate_post_scoreinfo_unattributed_fraction",
        ):
            if float(payload[key]) < 0.0:
                raise SystemExit(f"{label}: expected non-negative {key}, got {payload[key]}")
    if float(payload["candidate_non_gpu_wall_seconds"]) < 0.0:
        raise SystemExit(
            f"{label}: expected non-negative candidate_non_gpu_wall_seconds, "
            f"got {payload['candidate_non_gpu_wall_seconds']}"
        )
    if payload["realpath_used"] != payload["tasks"]:
        raise SystemExit(f"{label}: realpath_used != tasks")
    if payload["gpu_minscore_used"] != payload["tasks"]:
        raise SystemExit(f"{label}: gpu_minscore_used != tasks")
    if payload["realpath_fallbacks"] != 0:
        raise SystemExit(f"{label}: realpath_fallbacks != 0")
    if payload["cpu_scoreinfo_groups"] != 0:
        raise SystemExit(f"{label}: cpu_scoreinfo_groups != 0")
    if payload["cpu_prealign_seconds"] != 0:
        raise SystemExit(f"{label}: cpu_prealign_seconds != 0")
    if payload["compare_seconds"] != 0:
        raise SystemExit(f"{label}: compare_seconds != 0")
    if payload["candidate_realpath_extend_attempt_probe_fallbacks"] > payload["candidate_realpath_extend_attempt_probe_calls"]:
        raise SystemExit(f"{label}: probe fallbacks exceed probe calls")
    if payload["candidate_realpath_extend_segmented_attempt_probe_fallbacks"] > payload["candidate_realpath_extend_segmented_attempt_probe_calls"]:
        raise SystemExit(f"{label}: segmented probe fallbacks exceed probe calls")
    if payload["candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks"] > payload["candidate_realpath_extend_flush_segmented_attempt_probe_calls"]:
        raise SystemExit(f"{label}: flush segmented probe fallbacks exceed probe calls")
    if payload["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"] != 0:
        raise SystemExit(f"{label}: flush segmented replay probe triplex mismatches != 0")
    if payload["candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches"] != 0:
        raise SystemExit(f"{label}: flush full replay probe triplex mismatches != 0")
    if payload["candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches"] != 0:
        raise SystemExit(f"{label}: flush oracle replay probe triplex mismatches != 0")
    if payload["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"] != 0:
        raise SystemExit(f"{label}: flush segmented replay probe fallbacks != 0")
    if payload["candidate_realpath_extend_flush_full_replay_probe_fallbacks"] != 0:
        raise SystemExit(f"{label}: flush full replay probe fallbacks != 0")
    if not Path(payload["accepted_output"]).is_file():
        raise SystemExit(f"{label}: missing accepted output")

if fresh["audited_resume"] is not False:
    raise SystemExit("fresh run should record audited_resume=false")
if fresh["baseline_resumed_shards_count"] != 0:
    raise SystemExit("fresh baseline resumed shards should be 0")
if fresh["candidate_resumed_shards_count"] != 0:
    raise SystemExit("fresh candidate resumed shards should be 0")
if resume["audited_resume"] is not True:
    raise SystemExit("resume run should record audited_resume=true")
if resume["baseline_resumed_shards_count"] != fresh["shard_count"]:
    raise SystemExit(
        "resume baseline_resumed_shards_count mismatch: "
        f"{resume['baseline_resumed_shards_count']} vs {fresh['shard_count']}"
    )
if resume["candidate_resumed_shards_count"] != fresh["shard_count"]:
    raise SystemExit(
        "resume candidate_resumed_shards_count mismatch: "
        f"{resume['candidate_resumed_shards_count']} vs {fresh['shard_count']}"
    )
if resume["baseline_digest"] != fresh["baseline_digest"]:
    raise SystemExit("resume changed baseline digest")
if resume["candidate_digest"] != fresh["candidate_digest"]:
    raise SystemExit("resume changed candidate digest")

print("digest=" + fresh["candidate_digest"])
print("tasks=" + str(fresh["tasks"]))
print("realpath_used=" + str(fresh["realpath_used"]))
print("gpu_scoreinfo_groups=" + str(fresh["gpu_scoreinfo_groups"]))
print("candidate_vs_baseline=" + f"{float(fresh['candidate_vs_baseline']):.6f}x")
print("candidate_gpu_scoreinfo_wall_fraction=" + f"{float(fresh['candidate_gpu_scoreinfo_wall_fraction']):.6f}")
print("candidate_realpath_extend_seconds=" + f"{float(fresh['candidate_realpath_extend_seconds']):.6f}")
print("candidate_realpath_extend_fraction=" + f"{float(fresh['candidate_realpath_extend_fraction']):.6f}")
print("candidate_realpath_extend_scoreinfo_groups=" + str(fresh["candidate_realpath_extend_scoreinfo_groups"]))
print("candidate_realpath_extend_align_attempts=" + str(fresh["candidate_realpath_extend_align_attempts"]))
print("candidate_realpath_extend_align_seconds=" + f"{float(fresh['candidate_realpath_extend_align_seconds']):.6f}")
print("candidate_realpath_extend_align_fraction=" + f"{float(fresh['candidate_realpath_extend_align_fraction']):.6f}")
print("candidate_realpath_extend_attempt_probe_requested=" + str(fresh["candidate_realpath_extend_attempt_probe_requested"]))
print("candidate_realpath_extend_attempt_probe_active=" + str(fresh["candidate_realpath_extend_attempt_probe_active"]))
print("candidate_realpath_extend_attempt_probe_calls=" + str(fresh["candidate_realpath_extend_attempt_probe_calls"]))
print("candidate_realpath_extend_attempt_probe_attempts=" + str(fresh["candidate_realpath_extend_attempt_probe_attempts"]))
print("candidate_realpath_extend_attempt_probe_selected_attempts=" + str(fresh["candidate_realpath_extend_attempt_probe_selected_attempts"]))
print("candidate_realpath_extend_attempt_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_attempt_probe_seconds']):.6f}")
print("candidate_realpath_extend_attempt_probe_fallbacks=" + str(fresh["candidate_realpath_extend_attempt_probe_fallbacks"]))
print("candidate_realpath_extend_segmented_attempt_probe_requested=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_requested"]))
print("candidate_realpath_extend_segmented_attempt_probe_active=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_active"]))
print("candidate_realpath_extend_segmented_attempt_probe_segments=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_segments"]))
print("candidate_realpath_extend_segmented_attempt_probe_calls=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_calls"]))
print("candidate_realpath_extend_segmented_attempt_probe_attempts=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_attempts"]))
print("candidate_realpath_extend_segmented_attempt_probe_selected_attempts=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_selected_attempts"]))
print("candidate_realpath_extend_segmented_attempt_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_segmented_attempt_probe_seconds']):.6f}")
print("candidate_realpath_extend_segmented_attempt_probe_fallbacks=" + str(fresh["candidate_realpath_extend_segmented_attempt_probe_fallbacks"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_requested=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_requested"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_active=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_active"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_flushes=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_flushes"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_segments=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_segments"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_calls=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_calls"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_attempts=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_attempts"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts"]))
print("candidate_realpath_extend_flush_segmented_attempt_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_flush_segmented_attempt_probe_seconds']):.6f}")
print("candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks=" + str(fresh["candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_requested=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_requested"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_active=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_active"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_tasks=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_tasks"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_align_attempts=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_align_attempts"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_flush_segmented_replay_probe_seconds']):.6f}")
print("candidate_realpath_extend_flush_segmented_replay_probe_fallbacks=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_task=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_task"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key"]))
print("candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance"]))
print("candidate_realpath_extend_flush_full_replay_probe_requested=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_requested"]))
print("candidate_realpath_extend_flush_full_replay_probe_active=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_active"]))
print("candidate_realpath_extend_flush_full_replay_probe_tasks=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_tasks"]))
print("candidate_realpath_extend_flush_full_replay_probe_align_attempts=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_align_attempts"]))
print("candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches"]))
print("candidate_realpath_extend_flush_full_replay_probe_fallbacks=" + str(fresh["candidate_realpath_extend_flush_full_replay_probe_fallbacks"]))
print("candidate_realpath_extend_flush_full_replay_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_flush_full_replay_probe_seconds']):.6f}")
print("candidate_realpath_extend_flush_oracle_replay_probe_requested=" + str(fresh["candidate_realpath_extend_flush_oracle_replay_probe_requested"]))
print("candidate_realpath_extend_flush_oracle_replay_probe_active=" + str(fresh["candidate_realpath_extend_flush_oracle_replay_probe_active"]))
print("candidate_realpath_extend_flush_oracle_replay_probe_tasks=" + str(fresh["candidate_realpath_extend_flush_oracle_replay_probe_tasks"]))
print("candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches=" + str(fresh["candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches"]))
print("candidate_realpath_extend_flush_oracle_replay_probe_seconds=" + f"{float(fresh['candidate_realpath_extend_flush_oracle_replay_probe_seconds']):.6f}")
print("candidate_non_gpu_wall_seconds=" + f"{float(fresh['candidate_non_gpu_wall_seconds']):.6f}")
print("candidate_post_scoreinfo_unattributed_seconds=" + f"{float(fresh['candidate_post_scoreinfo_unattributed_seconds']):.6f}")
print("candidate_post_scoreinfo_unattributed_fraction=" + f"{float(fresh['candidate_post_scoreinfo_unattributed_fraction']):.6f}")
print("baseline_resumed_shards_count=" + str(resume["baseline_resumed_shards_count"]))
print("candidate_resumed_shards_count=" + str(resume["candidate_resumed_shards_count"]))
print("ok")
PY
