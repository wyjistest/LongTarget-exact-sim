#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real"}"
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
  echo "missing two-contract group32 audited wrapper: $WRAPPER" >&2
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

python3 - "$WORK/fresh.json" "$WORK/resume.json" <<'PY'
import json
import sys
from pathlib import Path

fresh = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
resume = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

for label, payload in (("fresh", fresh), ("resume", resume)):
    if payload["audited_status"] != "accepted":
        raise SystemExit(f"{label}: unexpected audited_status={payload['audited_status']}")
    if payload["baseline_digest"] != payload["candidate_digest"]:
        raise SystemExit(f"{label}: digest mismatch")
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1":
        raise SystemExit(f"{label}: unexpected contract={payload['result_contract']}")
    if payload["trust_profile"] != "malat1_like_two_contract_group32_experimental_v1":
        raise SystemExit(f"{label}: unexpected trust_profile={payload['trust_profile']}")
    if payload["group_target_records"] != 32:
        raise SystemExit(f"{label}: group_target_records != 32")
    if payload["tasks"] <= 0:
        raise SystemExit(f"{label}: expected positive tasks")
    if payload["two_contract_used"] != payload["tasks"]:
        raise SystemExit(
            f"{label}: two_contract_used != tasks: "
            f"{payload['two_contract_used']} vs {payload['tasks']}"
        )
    if payload["realpath_used"] != payload["tasks"]:
        raise SystemExit(
            f"{label}: realpath_used != tasks: "
            f"{payload['realpath_used']} vs {payload['tasks']}"
        )
    for key in (
        "two_contract_fallbacks",
        "two_contract_score_mismatches",
        "two_contract_min_score_mismatches",
        "two_contract_scoreinfo_mismatches",
        "realpath_fallbacks",
        "cpu_scoreinfo_groups",
        "cpu_prealign_seconds",
        "compare_seconds",
    ):
        if payload[key] != 0:
            raise SystemExit(f"{label}: expected {key}=0, got {payload[key]}")
    for key in (
        "gpu_scoreinfo_groups",
        "gpu_minscore_hot",
        "candidate_two_contract_total_seconds",
        "candidate_two_contract_h2d_seconds",
        "candidate_two_contract_kernel_seconds",
        "candidate_two_contract_d2h_seconds",
        "candidate_gpu_call_seconds",
        "candidate_kernel_seconds",
        "baseline_runner_wall_seconds",
        "candidate_runner_wall_seconds",
        "candidate_vs_baseline",
    ):
        if float(payload[key]) <= 0.0:
            raise SystemExit(f"{label}: expected positive {key}, got {payload[key]}")
    for key in (
        "candidate_realpath_extend_flush_segmented_replay_probe_requested",
        "candidate_realpath_extend_flush_segmented_replay_probe_active",
        "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
        "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_requested",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_active",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_seconds",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_active",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds",
    ):
        if float(payload[key]) <= 0.0:
            raise SystemExit(f"{label}: expected positive {key}, got {payload[key]}")
    if "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks" not in payload:
        raise SystemExit(f"{label}: missing selected-only zero-triplex task counter")
    if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks"] < 0:
        raise SystemExit(
            f"{label}: negative selected-only zero-triplex task counter: "
            f"{payload['candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks']}"
        )
    selected_only_mismatch_keys = (
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff",
    )
    for key in selected_only_mismatch_keys:
        if key not in payload:
            raise SystemExit(f"{label}: missing {key}")
        if payload[key] < 0:
            raise SystemExit(f"{label}: negative {key}: {payload[key]}")
    for key in (
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo",
    ):
        if key not in payload:
            raise SystemExit(f"{label}: missing {key}")
        if payload[key] < 0:
            raise SystemExit(f"{label}: negative {key}: {payload[key]}")
    selected_only_mismatch_class_total = sum(payload[key] for key in selected_only_mismatch_keys)
    if (
        selected_only_mismatch_class_total
        != payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches"]
    ):
        raise SystemExit(
            f"{label}: selected-only mismatch classes do not sum to mismatch count: "
            f"{selected_only_mismatch_class_total} vs "
            f"{payload['candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches']}"
        )
    if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches"] > 0:
        if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task"] < 0:
            raise SystemExit(f"{label}: missing selected-only first mismatch task")
        if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind"] == "none":
            raise SystemExit(f"{label}: missing selected-only first mismatch kind")
        if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key"] != "none":
            if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance"] == "none":
                raise SystemExit(f"{label}: missing selected-only first mismatch provenance")
    grouped_selected_mismatch_keys = (
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more",
        "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff",
    )
    for key in grouped_selected_mismatch_keys:
        if key not in payload:
            raise SystemExit(f"{label}: missing {key}")
        if payload[key] < 0:
            raise SystemExit(f"{label}: negative {key}: {payload[key]}")
    grouped_selected_mismatch_class_total = sum(
        payload[key] for key in grouped_selected_mismatch_keys
    )
    if (
        grouped_selected_mismatch_class_total
        != payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches"]
    ):
        raise SystemExit(
            f"{label}: grouped-selected mismatch classes do not sum to mismatch count: "
            f"{grouped_selected_mismatch_class_total} vs "
            f"{payload['candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches']}"
        )
    if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches"] > 0:
        if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task"] < 0:
            raise SystemExit(f"{label}: missing grouped-selected first mismatch task")
        if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind"] == "none":
            raise SystemExit(f"{label}: missing grouped-selected first mismatch kind")
    if payload["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"] != 0:
        raise SystemExit(
            f"{label}: replay triplex mismatches: "
            f"{payload['candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches']}"
        )
    if payload["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"] != 0:
        raise SystemExit(
            f"{label}: replay fallbacks: "
            f"{payload['candidate_realpath_extend_flush_segmented_replay_probe_fallbacks']}"
        )
    if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks"] != 0:
        raise SystemExit(
            f"{label}: selected-only replay fallbacks: "
            f"{payload['candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks']}"
        )
    if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks"] != 0:
        raise SystemExit(
            f"{label}: grouped-selected replay fallbacks: "
            f"{payload['candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks']}"
        )

if fresh["audited_resume"] is not False:
    raise SystemExit("fresh run should record audited_resume=false")
if resume["audited_resume"] is not True:
    raise SystemExit("resume run should record audited_resume=true")
for key in (
    "baseline_digest",
    "candidate_digest",
    "tasks",
    "two_contract_used",
    "realpath_used",
    "gpu_scoreinfo_groups",
):
    if fresh[key] != resume[key]:
        raise SystemExit(f"resume changed {key}: {fresh[key]} vs {resume[key]}")

print("digest=" + fresh["candidate_digest"])
print("tasks=" + str(fresh["tasks"]))
print("two_contract_used=" + str(fresh["two_contract_used"]))
print("realpath_used=" + str(fresh["realpath_used"]))
print("gpu_scoreinfo_groups=" + str(fresh["gpu_scoreinfo_groups"]))
print(
    "replay_probe_tasks="
    + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_tasks"])
)
print(
    "replay_probe_selected_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts"])
)
print(
    "replay_probe_align_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_align_attempts"])
)
print(
    "replay_probe_triplex_mismatches="
    + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"])
)
print(
    "replay_probe_fallbacks="
    + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"])
)
print(
    "selected_only_replay_probe_tasks="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks"])
)
print(
    "selected_only_replay_probe_selected_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts"])
)
print(
    "selected_only_replay_probe_align_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts"])
)
print(
    "selected_only_replay_probe_selected_scoreinfos="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos"])
)
print(
    "selected_only_replay_probe_tasks_with_selected="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected"])
)
print(
    "selected_only_replay_probe_tasks_with_triplex="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex"])
)
print(
    "selected_only_replay_probe_zero_triplex_tasks="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks"])
)
print(
    "selected_only_replay_probe_mismatch_selected_empty="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty"])
)
print(
    "selected_only_replay_probe_mismatch_legacy_empty="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty"])
)
print(
    "selected_only_replay_probe_mismatch_selected_less="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less"])
)
print(
    "selected_only_replay_probe_mismatch_selected_more="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more"])
)
print(
    "selected_only_replay_probe_mismatch_same_count_diff="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff"])
)
print(
    "selected_only_replay_probe_first_mismatch_task="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task"])
)
print(
    "selected_only_replay_probe_first_mismatch_kind="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind"])
)
print(
    "selected_only_replay_probe_first_mismatch_diff_index="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index"])
)
print(
    "selected_only_replay_probe_first_mismatch_selected_count="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count"])
)
print(
    "selected_only_replay_probe_first_mismatch_legacy_count="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count"])
)
print(
    "selected_only_replay_probe_first_mismatch_selected_key="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key"])
)
print(
    "selected_only_replay_probe_first_mismatch_legacy_key="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key"])
)
print(
    "selected_only_replay_probe_first_mismatch_selected_provenance="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance"])
)
print(
    "selected_only_replay_probe_scoreinfos_with_multiple_triplexes="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes"])
)
print(
    "selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo"])
)
print(
    "selected_only_replay_probe_triplex_mismatches="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches"])
)
print(
    "selected_only_replay_probe_fallbacks="
    + str(fresh["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks"])
)
print(
    "grouped_selected_replay_probe_tasks="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks"])
)
print(
    "grouped_selected_replay_probe_selected_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts"])
)
print(
    "grouped_selected_replay_probe_align_attempts="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts"])
)
print(
    "grouped_selected_replay_probe_selected_scoreinfos="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos"])
)
print(
    "grouped_selected_replay_probe_tasks_with_selected="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected"])
)
print(
    "grouped_selected_replay_probe_tasks_with_triplex="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex"])
)
print(
    "grouped_selected_replay_probe_zero_triplex_tasks="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks"])
)
print(
    "grouped_selected_replay_probe_mismatch_selected_empty="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty"])
)
print(
    "grouped_selected_replay_probe_mismatch_legacy_empty="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty"])
)
print(
    "grouped_selected_replay_probe_mismatch_selected_less="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less"])
)
print(
    "grouped_selected_replay_probe_mismatch_selected_more="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more"])
)
print(
    "grouped_selected_replay_probe_mismatch_same_count_diff="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_task="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_kind="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_diff_index="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_selected_count="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_legacy_count="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_selected_key="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_legacy_key="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_selected_provenance="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance"])
)
print(
    "grouped_selected_replay_probe_first_mismatch_legacy_provenance="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance"])
)
print(
    "grouped_selected_replay_probe_triplex_mismatches="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches"])
)
print(
    "grouped_selected_replay_probe_fallbacks="
    + str(fresh["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks"])
)
print("candidate_vs_baseline=" + str(fresh["candidate_vs_baseline"]))
print("resume_audited=" + str(resume["audited_resume"]).lower())
print("ok")
PY
