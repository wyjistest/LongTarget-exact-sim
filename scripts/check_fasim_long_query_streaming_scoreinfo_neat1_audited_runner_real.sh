#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_neat1_audited.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real"}"
BUILD_BIN="${BUILD_BIN:-1}"
RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-4}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-0}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

case "$RECORD_LIMIT" in
  ''|*[!0-9]*)
    echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
    exit 1
    ;;
esac
if [[ "$RECORD_LIMIT" -le 0 ]]; then
  echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
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
  echo "missing NEAT1 audited wrapper: $WRAPPER" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing NEAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"
sample="$WORK/inputs/neat1_first${RECORD_LIMIT}.fa"
awk -v limit="$RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty NEAT1 sample" >&2
  exit 1
fi

"$WRAPPER" \
  --fasim-bin "$BIN" \
  --target "$sample" \
  --rna "$RNA_INPUT" \
  --work-dir "$WORK/audit" \
  --replay-probe-max-tasks "$REPLAY_PROBE_MAX_TASKS" \
  >"$WORK/fresh.json"

"$WRAPPER" \
  --fasim-bin "$BIN" \
  --target "$sample" \
  --rna "$RNA_INPUT" \
  --work-dir "$WORK/audit" \
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
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_nonshared_neat1_audit_v1":
        raise SystemExit(f"{label}: unexpected contract={payload['result_contract']}")
    if payload["trust_profile"] != "neat1_like_nonshared_experimental_v1":
        raise SystemExit(f"{label}: unexpected trust_profile={payload['trust_profile']}")
    if payload["tasks"] <= 0:
        raise SystemExit(f"{label}: expected positive tasks")
    if payload["realpath_used"] != payload["tasks"]:
        raise SystemExit(
            f"{label}: realpath_used != tasks: {payload['realpath_used']} vs {payload['tasks']}"
        )
    expected_replay_tasks = (
        payload["tasks"]
        if replay_probe_max_tasks == 0
        else payload["candidate_realpath_extend_flush_segmented_attempt_probe_flushes"]
        * replay_probe_max_tasks
    )
    for key in (
        "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
        "candidate_realpath_extend_flush_full_replay_probe_tasks",
        "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
    ):
        if payload[key] != expected_replay_tasks:
            raise SystemExit(f"{label}: {key}={payload[key]} expected {expected_replay_tasks}")
    for key in (
        "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches",
        "realpath_fallbacks",
    ):
        if payload[key] != 0:
            raise SystemExit(f"{label}: {key}={payload[key]}")
    if payload["legacy_byte_shared"] != 0:
        raise SystemExit(
            f"{label}: expected non-shared legacy-byte mode, got {payload['legacy_byte_shared']}"
        )
    for key in (
        "gpu_scoreinfo_groups",
        "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    ):
        if payload[key] <= 0:
            raise SystemExit(f"{label}: expected positive {key}, got {payload[key]}")

if fresh["audited_resume"] is not False:
    raise SystemExit("fresh run should record audited_resume=false")
if resume["audited_resume"] is not True:
    raise SystemExit("resume run should record audited_resume=true")
for key in (
    "baseline_digest",
    "candidate_digest",
    "tasks",
    "realpath_used",
    "gpu_scoreinfo_groups",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
):
    if fresh[key] != resume[key]:
        raise SystemExit(f"resume changed {key}: {fresh[key]} vs {resume[key]}")

print("digest=" + fresh["candidate_digest"])
print("tasks=" + str(fresh["tasks"]))
print("realpath_used=" + str(fresh["realpath_used"]))
print("gpu_scoreinfo_groups=" + str(fresh["gpu_scoreinfo_groups"]))
print("segmented_replay_tasks=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_tasks"]))
print("segmented_replay_align_attempts=" + str(fresh["candidate_realpath_extend_flush_segmented_replay_probe_align_attempts"]))
print("resume_audited=" + str(resume["audited_resume"]).lower())
print("ok")
PY
