#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-mixed-hazard-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

create_audit_dir() {
  local root="$1"
  local case_id="$2"
  local decision_status="$3"
  local schema_version="$4"
  local locality_status="$5"
  local hazard_status="$6"
  local runtime_prototype="$7"
  local miss_count="$8"
  local incoming_reuse_share="$9"
  local floor_change_count="${10}"
  local victim_reappear_count="${11}"
  local create_timeline="${12}"

  python3 - "$root" "$case_id" "$decision_status" "$schema_version" "$locality_status" "$hazard_status" "$runtime_prototype" "$miss_count" "$incoming_reuse_share" "$floor_change_count" "$victim_reappear_count" "$create_timeline" <<'PY_INNER'
import csv
import gzip
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
case_id = sys.argv[2]
decision_status = sys.argv[3]
schema_version = int(sys.argv[4])
locality_status = sys.argv[5]
hazard_status = sys.argv[6]
runtime_prototype = sys.argv[7]
miss_count = int(sys.argv[8])
incoming_reuse_share = float(sys.argv[9])
floor_change_count = int(sys.argv[10])
victim_reappear_count = int(sys.argv[11])
create_timeline = sys.argv[12] == "1"

root.mkdir(parents=True, exist_ok=True)

floor_share = 0.0 if miss_count <= 0 else float(floor_change_count) / float(miss_count)
victim_reappear_share = 0.0 if miss_count <= 0 else float(victim_reappear_count) / float(miss_count)

summary = {
    "decision_status": decision_status,
    "schema_version": schema_version,
    "locality_status": locality_status,
    "exactness_hazard_status": hazard_status,
    "recommended_runtime_prototype": runtime_prototype,
    "total_full_set_miss_count": miss_count,
    "trace_root": f"/trace/{case_id}",
    "aggregate_metrics": {
        "incoming_key_reuse_before_eviction_share": incoming_reuse_share,
        "victim_key_reappears_after_eviction_share": victim_reappear_share,
        "floor_change_per_full_set_miss": floor_share,
        "min_slot_change_per_full_set_miss": floor_share,
    },
    "errors": [],
}

decision = {
    "decision_status": decision_status,
    "locality_status": locality_status,
    "exactness_hazard_status": hazard_status,
    "recommended_runtime_prototype": runtime_prototype,
    "blocked_runtime_prototypes": [
        "incoming_key_coalescing",
        "unordered_key_summary",
        "event_reorder_by_slot",
    ],
    "trace_root": f"/trace/{case_id}",
    "errors": [],
}

hazard = {
    "trace_root": f"/trace/{case_id}",
    "aggregate": {
        "locality_status": locality_status,
        "exactness_hazard_status": hazard_status,
        "recommended_runtime_prototype": runtime_prototype,
        "incoming_key_reuse_before_eviction_share": incoming_reuse_share,
        "victim_key_reappears_after_eviction_share": victim_reappear_share,
        "floor_change_per_full_set_miss": floor_share,
        "min_slot_change_per_full_set_miss": floor_share,
    },
    "cases": [
        {
            "case_id": case_id,
            "observed_full_set_miss_count": miss_count,
            "locality_status": locality_status,
            "exactness_hazard_status": hazard_status,
            "recommended_runtime_prototype": runtime_prototype,
            "metrics": {
                "incoming_key_reuse_before_eviction_share": incoming_reuse_share,
                "victim_key_reappears_after_eviction_share": victim_reappear_share,
                "floor_change_per_full_set_miss": floor_share,
                "min_slot_change_per_full_set_miss": floor_share,
            },
        }
    ],
    "errors": [],
}

(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
(root / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
(root / "hazard_summary.json").write_text(json.dumps(hazard, indent=2) + "\n", encoding="utf-8")

if not create_timeline:
    raise SystemExit(0)

timeline_path = root / "victim_slot_timeline.tsv.gz"
fieldnames = [
    "case_id",
    "event_ordinal",
    "summary_ordinal",
    "victim_slot",
    "observed_candidate_index_before",
    "victim_key_before",
    "incoming_key",
    "incoming_score",
    "victim_score_before",
    "running_min_before",
    "running_min_after",
    "running_min_slot_before",
    "running_min_slot_after",
    "floor_changed",
    "min_slot_changed",
    "incoming_key_next_seen_distance",
    "victim_key_next_seen_distance",
]

running_min = 100
running_min_slot = 0
with gzip.open(timeline_path, "wt", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    for event_ordinal in range(miss_count):
        floor_changed = event_ordinal < floor_change_count
        if floor_changed:
            new_running_min = running_min + 1
            new_running_min_slot = (running_min_slot + 1) % 4
        else:
            new_running_min = running_min
            new_running_min_slot = running_min_slot

        writer.writerow(
            {
                "case_id": case_id,
                "event_ordinal": event_ordinal,
                "summary_ordinal": 100 + event_ordinal,
                "victim_slot": event_ordinal % 2,
                "observed_candidate_index_before": event_ordinal % 2,
                "victim_key_before": 1000 + event_ordinal,
                "incoming_key": 2000 + event_ordinal,
                "incoming_score": 50 + event_ordinal,
                "victim_score_before": 40 + event_ordinal,
                "running_min_before": running_min,
                "running_min_after": new_running_min,
                "running_min_slot_before": running_min_slot,
                "running_min_slot_after": new_running_min_slot,
                "floor_changed": "true" if floor_changed else "false",
                "min_slot_changed": "true" if floor_changed else "false",
                "incoming_key_next_seen_distance": -1,
                "victim_key_next_seen_distance": 1 if event_ordinal < victim_reappear_count else -1,
            }
        )
        running_min = new_running_min
        running_min_slot = new_running_min_slot
PY_INNER
}

run_and_assert() {
  local output_dir="$1"
  shift
  python3 ./scripts/analyze_sim_initial_host_merge_mixed_hazard_modes.py "$@" --output-dir "$output_dir"
}

assert_ready_case() {
  local output_dir="$1"
  local expected_mode="$2"
  local expected_action="$3"
  local expected_candidates_json="$4"
  python3 - "$output_dir" "$expected_mode" "$expected_action" "$expected_candidates_json" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_mode = sys.argv[2]
expected_action = sys.argv[3]
expected_candidates = json.loads(sys.argv[4])
decision = json.loads((output_dir / "mixed_hazard_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "mixed_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["mixed_hazard_mode"] == expected_mode, decision
assert decision["recommended_next_action"] == expected_action, decision
assert decision["candidate_runtime_prototypes"] == expected_candidates, decision
assert summary["aggregate"]["mixed_hazard_mode"] == expected_mode, summary
assert "running_min_delta_signed_p50" in summary["cases"][0], summary
assert "running_min_delta_abs_p50" in summary["cases"][0], summary
assert "victim_key_reappears_before_next_full_set_miss_floor_change_share" in summary["cases"][0], summary
assert "victim_key_reappears_after_next_full_set_miss_floor_change_share" in summary["cases"][0], summary
PY_INNER
}

assert_not_ready() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
decision = json.loads((output_dir / "mixed_hazard_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "mixed_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "not_ready", decision
assert decision["recommended_next_action"] == "fix_audit_inputs", decision
assert summary["aggregate"] == {}, summary
PY_INNER
}

assert_heavy_like() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
decision = json.loads((output_dir / "mixed_hazard_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "mixed_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["case_count"] == 5, decision
assert decision["schema_version_all"] == 2, decision
assert decision["mixed_hazard_mode"] == "floor_and_victim_reappear", decision
assert decision["recommended_next_action"] == "profile_floor_min_maintenance", decision
assert decision["candidate_runtime_prototypes"] == [
    "stable_min_maintenance",
    "eager_index_erase_handle",
], decision
assert decision["stopped_runtime_prototypes"] == [
    "lazy_generation_index",
    "incoming_key_coalescing",
    "victim_slot_event_reorder",
    "full_set_miss_batch_collapse",
], decision
assert summary["aggregate"]["floor_changed_share"] >= 0.79, summary
assert summary["aggregate"]["victim_key_reappears_after_eviction_share"] >= 0.89, summary
assert summary["aggregate"]["incoming_key_reuse_before_eviction_share"] <= 0.02, summary
assert summary["aggregate"]["running_min_delta_signed_p50"] >= 1, summary
assert summary["aggregate"]["running_min_delta_abs_p50"] >= 1, summary
assert summary["aggregate"]["victim_key_reappears_after_next_full_set_miss_floor_change_share"] >= 0.80, summary
assert summary["aggregate"]["victim_key_reappears_before_next_full_set_miss_floor_change_share"] <= 0.20, summary
PY_INNER
}

# floor_only
FLOOR_ONLY="$WORK/floor_only"
create_audit_dir "$FLOOR_ONLY/audit" "case-floor-only" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "8" "0" "1"
run_and_assert "$FLOOR_ONLY/out" --audit-dir "$FLOOR_ONLY/audit"
assert_ready_case "$FLOOR_ONLY/out" "floor_only" "profile_floor_min_maintenance" '["stable_min_maintenance"]'

# victim_reappear_only
VICTIM_ONLY="$WORK/victim_only"
create_audit_dir "$VICTIM_ONLY/audit" "case-victim-only" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "0" "9" "1"
run_and_assert "$VICTIM_ONLY/out" --audit-dir "$VICTIM_ONLY/audit"
assert_ready_case "$VICTIM_ONLY/out" "victim_reappear_only" "profile_candidate_index_lifecycle" '["eager_index_erase_handle"]'

# floor_and_victim_reappear
FLOOR_VICTIM="$WORK/floor_victim"
create_audit_dir "$FLOOR_VICTIM/audit" "case-floor-victim" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "8" "9" "1"
run_and_assert "$FLOOR_VICTIM/out" --audit-dir "$FLOOR_VICTIM/audit"
assert_ready_case "$FLOOR_VICTIM/out" "floor_and_victim_reappear" "profile_floor_min_maintenance" '["stable_min_maintenance","eager_index_erase_handle"]'

# key_reuse_only
KEY_REUSE="$WORK/key_reuse_only"
create_audit_dir "$KEY_REUSE/audit" "case-key-reuse" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.20" "0" "0" "1"
run_and_assert "$KEY_REUSE/out" --audit-dir "$KEY_REUSE/audit"
assert_ready_case "$KEY_REUSE/out" "key_reuse_only" "inspect_key_reuse" '[]'

# all_blockers
ALL_BLOCKERS="$WORK/all_blockers"
create_audit_dir "$ALL_BLOCKERS/audit" "case-all-blockers" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.20" "8" "9" "1"
run_and_assert "$ALL_BLOCKERS/out" --audit-dir "$ALL_BLOCKERS/audit"
assert_ready_case "$ALL_BLOCKERS/out" "all_blockers" "profile_floor_min_maintenance" '["stable_min_maintenance","eager_index_erase_handle"]'

# none
NONE_CASE="$WORK/none"
create_audit_dir "$NONE_CASE/audit" "case-none" "ready" "2" "victim_strong_key_weak" "low" "lazy_generation_index" "10" "0.00" "0" "0" "1"
run_and_assert "$NONE_CASE/out" --audit-dir "$NONE_CASE/audit"
assert_ready_case "$NONE_CASE/out" "none" "no_actionable_mixed_hazard" '[]'

# missing_timeline
MISSING_TIMELINE="$WORK/missing_timeline"
create_audit_dir "$MISSING_TIMELINE/audit" "case-missing-timeline" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "8" "9" "0"
run_and_assert "$MISSING_TIMELINE/out" --audit-dir "$MISSING_TIMELINE/audit"
assert_not_ready "$MISSING_TIMELINE/out"

# schema_mismatch
SCHEMA_MISMATCH="$WORK/schema_mismatch"
create_audit_dir "$SCHEMA_MISMATCH/audit" "case-schema-mismatch" "ready" "1" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "8" "9" "1"
run_and_assert "$SCHEMA_MISMATCH/out" --audit-dir "$SCHEMA_MISMATCH/audit"
assert_not_ready "$SCHEMA_MISMATCH/out"

# not_ready_case
NOT_READY="$WORK/not_ready_case"
create_audit_dir "$NOT_READY/audit" "case-not-ready" "invalid_trace_input" "2" "unknown" "unknown" "none" "10" "0.01" "8" "9" "1"
run_and_assert "$NOT_READY/out" --audit-dir "$NOT_READY/audit"
assert_not_ready "$NOT_READY/out"

# heavy_like campaign
HEAVY_LIKE="$WORK/heavy_like"
for idx in 1 2 3 4 5; do
  create_audit_dir "$HEAVY_LIKE/case-$idx" "case-heavy-$idx" "ready" "2" "victim_strong_key_mixed" "mixed" "none" "10" "0.01" "8" "9" "1"
done
run_and_assert "$HEAVY_LIKE/out" \
  --audit-dir "$HEAVY_LIKE/case-1" \
  --audit-dir "$HEAVY_LIKE/case-2" \
  --audit-dir "$HEAVY_LIKE/case-3" \
  --audit-dir "$HEAVY_LIKE/case-4" \
  --audit-dir "$HEAVY_LIKE/case-5"
assert_heavy_like "$HEAVY_LIKE/out"

echo "check_analyze_sim_initial_host_merge_mixed_hazard_modes: PASS"
