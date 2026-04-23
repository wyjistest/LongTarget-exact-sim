#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-hazard-campaign-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

create_audit_dir() {
  local root="$1"
  local case_id="$2"
  local decision_status="$3"
  local locality_status="$4"
  local hazard_status="$5"
  local runtime_prototype="$6"
  local miss_count="$7"
  local summary_extra="${8:-}"

  mkdir -p "$root"

  python3 - "$root" "$case_id" "$decision_status" "$locality_status" "$hazard_status" "$runtime_prototype" "$miss_count" "$summary_extra" <<'PY_INNER'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
case_id = sys.argv[2]
decision_status = sys.argv[3]
locality_status = sys.argv[4]
hazard_status = sys.argv[5]
runtime_prototype = sys.argv[6]
miss_count = int(sys.argv[7])
summary_extra = sys.argv[8]

summary = {
    "decision_status": decision_status,
    "locality_status": locality_status,
    "exactness_hazard_status": hazard_status,
    "recommended_runtime_prototype": runtime_prototype,
    "total_full_set_miss_count": miss_count,
    "trace_root": f"/trace/{case_id}",
    "errors": [],
}
if summary_extra:
    summary.update(json.loads(summary_extra))

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
    },
    "cases": [
        {
            "case_id": case_id,
            "observed_full_set_miss_count": miss_count,
            "locality_status": locality_status,
            "exactness_hazard_status": hazard_status,
            "recommended_runtime_prototype": runtime_prototype,
        }
    ],
    "errors": [],
}

(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
(root / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
(root / "hazard_summary.json").write_text(json.dumps(hazard, indent=2) + "\n", encoding="utf-8")
PY_INNER
}

run_and_assert() {
  local output_dir="$1"
  shift
  python3 ./scripts/summarize_sim_initial_host_merge_hazard_campaign.py "$@" --output-dir "$output_dir"
}

assert_ready_lazy() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
decision = json.loads((output_dir / "campaign_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "campaign_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["recommended_runtime_prototype"] == "lazy_generation_index", decision
assert decision["next_action"] == "prototype_lazy_generation_index", decision
assert decision["schema_version_all"] == 2, decision
assert decision["ready_case_count"] == 5, decision
assert decision["event_weighted"]["low_hazard_event_share"] >= 0.8, decision
assert decision["event_weighted"]["victim_strong_key_weak_event_share"] >= 0.7, decision
assert summary["aggregate"]["recommended_runtime_prototype"] == "lazy_generation_index", summary
PY_INNER
}

assert_ready_none_with_action() {
  local output_dir="$1"
  local expected_action="$2"
  python3 - "$output_dir" "$expected_action" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_action = sys.argv[2]
decision = json.loads((output_dir / "campaign_decision.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["recommended_runtime_prototype"] == "none", decision
assert decision["next_action"] == expected_action, decision
assert decision["blocking_reasons"], decision
PY_INNER
}

assert_not_ready() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
decision = json.loads((output_dir / "campaign_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "campaign_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "not_ready", decision
assert decision["recommended_runtime_prototype"] == "none", decision
assert decision["next_action"] == "fix_audit_inputs", decision
assert summary["aggregate"] == {}, summary
PY_INNER
}

assert_ready_split_mixed() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
decision = json.loads((output_dir / "campaign_decision.json").read_text(encoding="utf-8"))
summary = json.loads((output_dir / "campaign_hazard_summary.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["recommended_runtime_prototype"] == "none", decision
assert decision["next_action"] == "split_mixed_floor_reappearance_hazard", decision
assert decision["dominant_blockers"] == [
    "victim_key_reappears_after_eviction",
    "floor_churn",
], decision
assert decision["blocked_runtime_prototypes"] == [
    "lazy_generation_index",
    "incoming_key_coalescing",
    "victim_slot_event_reorder",
    "full_set_miss_batch_collapse",
], decision
assert summary["aggregate"]["next_action"] == "split_mixed_floor_reappearance_hazard", summary
PY_INNER
}

# all_low_hazard -> lazy_generation_index
LOW_WORK="$WORK/all_low_hazard"
for idx in 1 2 3 4 5; do
  create_audit_dir "$LOW_WORK/case-$idx" "case-00000$idx" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
done
run_and_assert "$LOW_WORK/out" \
  --audit-dir "$LOW_WORK/case-1" \
  --audit-dir "$LOW_WORK/case-2" \
  --audit-dir "$LOW_WORK/case-3" \
  --audit-dir "$LOW_WORK/case-4" \
  --audit-dir "$LOW_WORK/case-5"
assert_ready_lazy "$LOW_WORK/out"

# one_mixed_small_event_share -> still lazy_generation_index
MIXED_SMALL="$WORK/one_mixed_small"
create_audit_dir "$MIXED_SMALL/case-1" "case-00000001" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "4000"
create_audit_dir "$MIXED_SMALL/case-2" "case-00000002" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "4000"
create_audit_dir "$MIXED_SMALL/case-3" "case-00000003" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "4000"
create_audit_dir "$MIXED_SMALL/case-4" "case-00000004" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "4000"
create_audit_dir "$MIXED_SMALL/case-5" "case-00000005" "ready" "victim_strong_key_mixed" "mixed" "none" "200"
run_and_assert "$MIXED_SMALL/out" \
  --audit-dir "$MIXED_SMALL/case-1" \
  --audit-dir "$MIXED_SMALL/case-2" \
  --audit-dir "$MIXED_SMALL/case-3" \
  --audit-dir "$MIXED_SMALL/case-4" \
  --audit-dir "$MIXED_SMALL/case-5"
assert_ready_lazy "$MIXED_SMALL/out"

# one_key_reuse_dominant -> none / inspect_key_reuse
KEY_REUSE="$WORK/key_reuse_dominant"
create_audit_dir "$KEY_REUSE/case-1" "case-00000001" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$KEY_REUSE/case-2" "case-00000002" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$KEY_REUSE/case-3" "case-00000003" "ready" "victim_strong_key_mixed" "key_reuse" "none" "6000"
create_audit_dir "$KEY_REUSE/case-4" "case-00000004" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$KEY_REUSE/case-5" "case-00000005" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
run_and_assert "$KEY_REUSE/out" \
  --audit-dir "$KEY_REUSE/case-1" \
  --audit-dir "$KEY_REUSE/case-2" \
  --audit-dir "$KEY_REUSE/case-3" \
  --audit-dir "$KEY_REUSE/case-4" \
  --audit-dir "$KEY_REUSE/case-5"
assert_ready_none_with_action "$KEY_REUSE/out" "inspect_key_reuse"

# one_floor_churn_dominant -> none / inspect_floor_churn
FLOOR="$WORK/floor_churn_dominant"
create_audit_dir "$FLOOR/case-1" "case-00000001" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$FLOOR/case-2" "case-00000002" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$FLOOR/case-3" "case-00000003" "ready" "victim_strong_key_weak" "floor_churn" "none" "6000"
create_audit_dir "$FLOOR/case-4" "case-00000004" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$FLOOR/case-5" "case-00000005" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
run_and_assert "$FLOOR/out" \
  --audit-dir "$FLOOR/case-1" \
  --audit-dir "$FLOOR/case-2" \
  --audit-dir "$FLOOR/case-3" \
  --audit-dir "$FLOOR/case-4" \
  --audit-dir "$FLOOR/case-5"
assert_ready_none_with_action "$FLOOR/out" "inspect_floor_churn"

# homogeneous_mixed_floor_reappear_5_heavy -> split_mixed_floor_reappearance_hazard
MIXED_HEAVY="$WORK/mixed_floor_reappear"
MIXED_EXTRA='{"aggregate_metrics":{"victim_key_reappears_after_eviction_share":0.88,"floor_change_per_full_set_miss":0.78}}'
for idx in 1 2 3 4 5; do
  create_audit_dir "$MIXED_HEAVY/case-$idx" "case-0000000$idx" "ready" "victim_strong_key_mixed" "mixed" "none" "4000" "$MIXED_EXTRA"
done
run_and_assert "$MIXED_HEAVY/out" \
  --audit-dir "$MIXED_HEAVY/case-1" \
  --audit-dir "$MIXED_HEAVY/case-2" \
  --audit-dir "$MIXED_HEAVY/case-3" \
  --audit-dir "$MIXED_HEAVY/case-4" \
  --audit-dir "$MIXED_HEAVY/case-5"
assert_ready_split_mixed "$MIXED_HEAVY/out"

# schema_mismatch -> not_ready
SCHEMA="$WORK/schema_mismatch"
create_audit_dir "$SCHEMA/case-1" "case-00000001" "needs_schema_v2" "unknown" "unknown" "none" "0"
create_audit_dir "$SCHEMA/case-2" "case-00000002" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
run_and_assert "$SCHEMA/out" \
  --audit-dir "$SCHEMA/case-1" \
  --audit-dir "$SCHEMA/case-2"
assert_not_ready "$SCHEMA/out"

# missing_decision_json -> not_ready
MISSING="$WORK/missing_decision"
create_audit_dir "$MISSING/case-1" "case-00000001" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
create_audit_dir "$MISSING/case-2" "case-00000002" "ready" "victim_strong_key_weak" "low" "lazy_generation_index" "1000"
rm "$MISSING/case-2/decision.json"
run_and_assert "$MISSING/out" \
  --audit-dir "$MISSING/case-1" \
  --audit-dir "$MISSING/case-2"
assert_not_ready "$MISSING/out"
