#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-steady-state-locality-v2-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

create_case() {
  local scenario_dir="$1"
  local case_id="$2"
  local scenario_name="$3"
  local full_miss_count="$4"
  local schema_version="${5:-2}"
  local meta_miss_count="${6:-$full_miss_count}"

  mkdir -p "$scenario_dir/$case_id"

  python3 - "$scenario_dir/$case_id" "$scenario_name" "$full_miss_count" "$schema_version" "$meta_miss_count" <<'PY_INNER'
import json
import struct
import sys
from pathlib import Path

case_dir = Path(sys.argv[1])
scenario = sys.argv[2]
full_miss_count = int(sys.argv[3])
schema_version = int(sys.argv[4])
meta_miss_count = int(sys.argv[5])

HEADER_STRUCT = struct.Struct("<8sIIQQ")
EVENT_STRUCT_V1 = struct.Struct("<i4xQIIIIiiQi4x")
EVENT_STRUCT_V2 = struct.Struct("<i4xQIIIIQQiiiiiiii")

HIT_UPDATE = 0
HIT_NOOP = 1
FULL_SET_MISS = 2


def pack_coord(i: int, j: int) -> int:
    return ((i & 0xFFFFFFFF) << 32) | (j & 0xFFFFFFFF)


def make_event(summary_score: int,
               incoming_key: int,
               summary_ordinal: int,
               reference_event_kind: int,
               observed_candidate_index_before: int,
               victim_candidate_index_before: int,
               victim_key_before: int,
               victim_score_before: int,
               running_min_before: int,
               running_min_after: int,
               running_min_slot_before: int,
               running_min_slot_after: int):
    return {
        "score": summary_score,
        "start_coord": incoming_key,
        "end_i": 10 + (summary_ordinal % 5),
        "min_end_j": 20 + (summary_ordinal % 7),
        "max_end_j": 23 + (summary_ordinal % 7),
        "score_end_j": 21 + (summary_ordinal % 7),
        "summary_ordinal": summary_ordinal,
        "victim_key_before": victim_key_before,
        "reference_event_kind": reference_event_kind,
        "observed_candidate_index_before": observed_candidate_index_before,
        "victim_candidate_index_before": victim_candidate_index_before,
        "victim_score_before": victim_score_before,
        "running_min_before": running_min_before,
        "running_min_after": running_min_after,
        "running_min_slot_before": running_min_slot_before,
        "running_min_slot_after": running_min_slot_after,
    }


def strong_slot_no_reuse(count: int):
    events = []
    ordinal = 0
    for index in range(count):
        slot = 3
        incoming_key = pack_coord(1000 + index, 2000 + index)
        victim_key = pack_coord(4000 + index, 5000 + index)
        events.append(
            make_event(
                250 - (index % 17),
                incoming_key,
                ordinal,
                FULL_SET_MISS,
                slot,
                slot,
                victim_key,
                100,
                100,
                100,
                slot,
                slot,
            )
        )
        ordinal += 1
        events.append(
            make_event(
                210,
                pack_coord(900000 + index, 910000 + index),
                ordinal,
                HIT_NOOP,
                11,
                -1,
                0,
                0,
                100,
                100,
                slot,
                slot,
            )
        )
        ordinal += 1
    return events


def strong_slot_with_reuse(count: int):
    events = []
    ordinal = 0
    for index in range(count):
        slot = 3
        incoming_key = pack_coord(2000 + index, 3000 + index)
        victim_key = pack_coord(6000 + index, 7000 + index)
        events.append(
            make_event(
                260 - (index % 13),
                incoming_key,
                ordinal,
                FULL_SET_MISS,
                slot,
                slot,
                victim_key,
                100,
                100,
                100,
                slot,
                slot,
            )
        )
        ordinal += 1
        events.append(
            make_event(
                261 - (index % 13),
                incoming_key,
                ordinal,
                HIT_UPDATE,
                slot,
                -1,
                0,
                0,
                100,
                100,
                slot,
                slot,
            )
        )
        ordinal += 1
    return events


def floor_churn(count: int):
    events = []
    ordinal = 0
    for index in range(count):
        slot = 5
        incoming_key = pack_coord(3000 + index, 4000 + index)
        victim_key = pack_coord(8000 + index, 9000 + index)
        before = 100 + (index % 2)
        after = 101 + (index % 2)
        before_slot = 5 if index % 2 == 0 else 6
        after_slot = 6 if index % 2 == 0 else 5
        events.append(
            make_event(
                280 - (index % 11),
                incoming_key,
                ordinal,
                FULL_SET_MISS,
                slot,
                slot,
                victim_key,
                before,
                before,
                after,
                before_slot,
                after_slot,
            )
        )
        ordinal += 1
        events.append(
            make_event(
                200,
                pack_coord(990000 + index, 991000 + index),
                ordinal,
                HIT_NOOP,
                17,
                -1,
                0,
                0,
                after,
                after,
                after_slot,
                after_slot,
            )
        )
        ordinal += 1
    return events


def weak_slot_weak_key(count: int):
    events = []
    ordinal = 0
    for index in range(count):
        slot = index % 50
        incoming_key = pack_coord(50000 + index, 60000 + index)
        victim_key = pack_coord(70000 + index, 80000 + index)
        events.append(
            make_event(
                300 - (index % 19),
                incoming_key,
                ordinal,
                FULL_SET_MISS,
                slot,
                slot,
                victim_key,
                100,
                100,
                100,
                slot,
                slot,
            )
        )
        ordinal += 1
    return events


scenario_builders = {
    "strong_slot_no_reuse": strong_slot_no_reuse,
    "strong_slot_with_reuse": strong_slot_with_reuse,
    "floor_churn": floor_churn,
    "weak_slot_weak_key": weak_slot_weak_key,
    "invalid_meta": strong_slot_no_reuse,
    "needs_schema_v2": strong_slot_no_reuse,
}

events = scenario_builders[scenario](full_miss_count)
event_struct = EVENT_STRUCT_V2 if schema_version == 2 else EVENT_STRUCT_V1

with (case_dir / "events.bin").open("wb") as handle:
    handle.write(
        HEADER_STRUCT.pack(
            b"LTHMSSE1",
            1,
            0,
            len(events),
            event_struct.size,
        )
    )
    for event in events:
        if schema_version == 2:
            handle.write(
                EVENT_STRUCT_V2.pack(
                    event["score"],
                    event["start_coord"],
                    event["end_i"],
                    event["min_end_j"],
                    event["max_end_j"],
                    event["score_end_j"],
                    event["summary_ordinal"],
                    event["victim_key_before"],
                    event["reference_event_kind"],
                    event["observed_candidate_index_before"],
                    event["victim_candidate_index_before"],
                    event["victim_score_before"],
                    event["running_min_before"],
                    event["running_min_after"],
                    event["running_min_slot_before"],
                    event["running_min_slot_after"],
                )
            )
        else:
            handle.write(
                EVENT_STRUCT_V1.pack(
                    event["score"],
                    event["start_coord"],
                    event["end_i"],
                    event["min_end_j"],
                    event["max_end_j"],
                    event["score_end_j"],
                    event["reference_event_kind"],
                    event["victim_candidate_index_before"],
                    event["victim_key_before"],
                    event["victim_score_before"],
                )
            )

meta = {
    "schema_version": schema_version,
    "path_kind": "steady_state_full_set_miss_trace",
    "query_length": 2812,
    "target_length": 5000,
    "parm_M": 5,
    "parm_I": -4,
    "parm_O": -12,
    "parm_E": -4,
    "logical_event_count": len(events),
    "seed_running_min": 100,
    "expected_final_running_min": 100,
    "post_fill_event_count": len(events),
    "post_fill_full_set_miss_count": meta_miss_count,
    "seed_candidate_count": 50,
    "expected_final_candidate_count": 50,
    "gpu_mirror_requested": True,
}
(case_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
PY_INNER
}

assert_ready_outputs() {
  local out_dir="$1"
  local expected_locality="$2"
  local expected_hazard="$3"
  local expected_runtime="$4"

  python3 - "$out_dir" "$expected_locality" "$expected_hazard" "$expected_runtime" <<'PY_INNER'
import csv
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
expected_locality = sys.argv[2]
expected_hazard = sys.argv[3]
expected_runtime = sys.argv[4]

summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
hazard = json.loads((out_dir / "hazard_summary.json").read_text(encoding="utf-8"))
per_case_rows = list(csv.DictReader((out_dir / "per_case.tsv").open(encoding="utf-8"), delimiter="\t"))
timeline_rows = list(csv.DictReader((out_dir / "victim_slot_timeline.tsv").open(encoding="utf-8"), delimiter="\t"))

assert summary["decision_status"] == "ready", summary
assert summary["locality_status"] == expected_locality, summary
assert summary["exactness_hazard_status"] == expected_hazard, summary
assert summary["recommended_runtime_prototype"] == expected_runtime, summary
assert Path(summary["per_case_tsv"]).name == "per_case.tsv", summary
assert Path(summary["victim_slot_timeline_tsv"]).name == "victim_slot_timeline.tsv", summary
assert Path(summary["hazard_summary_json"]).name == "hazard_summary.json", summary
assert Path(summary["decision_json"]).name == "decision.json", summary
assert (out_dir / "summary.md").exists(), summary

assert decision["decision_status"] == "ready", decision
assert decision["locality_status"] == expected_locality, decision
assert decision["exactness_hazard_status"] == expected_hazard, decision
assert decision["recommended_runtime_prototype"] == expected_runtime, decision
assert decision["blocked_runtime_prototypes"] == [
    "incoming_key_coalescing",
    "unordered_key_summary",
    "event_reorder_by_slot",
], decision

assert hazard["aggregate"]["locality_status"] == expected_locality, hazard
assert hazard["aggregate"]["exactness_hazard_status"] == expected_hazard, hazard
assert hazard["aggregate"]["recommended_runtime_prototype"] == expected_runtime, hazard
assert len(hazard["cases"]) == 1, hazard

assert len(per_case_rows) == 1, per_case_rows
row = per_case_rows[0]
assert row["case_id"] == "case-00000001", row
assert row["meta_count_match"] == "true", row
assert row["locality_status"] == expected_locality, row
assert row["exactness_hazard_status"] == expected_hazard, row
assert row["recommended_runtime_prototype"] == expected_runtime, row

assert len(timeline_rows) > 0, timeline_rows
required_timeline_fields = {
    "case_id",
    "event_ordinal",
    "summary_ordinal",
    "victim_slot",
    "victim_key_before",
    "incoming_key",
    "running_min_before",
    "running_min_after",
    "floor_changed",
    "incoming_key_next_seen_distance",
    "victim_key_next_seen_distance",
}
assert required_timeline_fields.issubset(set(timeline_rows[0].keys())), timeline_rows[0]
PY_INNER
}

run_ready_scenario() {
  local scenario="$1"
  local expected_locality="$2"
  local expected_hazard="$3"
  local expected_runtime="$4"
  local miss_count="$5"
  local out_dir="$WORK/$scenario.out"
  local trace_root="$WORK/$scenario.trace"

  mkdir -p "$out_dir" "$trace_root"
  create_case "$trace_root" "case-00000001" "$scenario" "$miss_count"

  python3 ./scripts/analyze_sim_initial_host_merge_steady_state_locality.py \
    --trace-root "$trace_root" \
    --output-dir "$out_dir"

  assert_ready_outputs "$out_dir" "$expected_locality" "$expected_hazard" "$expected_runtime"
}

run_invalid_meta_scenario() {
  local out_dir="$WORK/invalid_meta.out"
  local trace_root="$WORK/invalid_meta.trace"

  mkdir -p "$out_dir" "$trace_root"
  create_case "$trace_root" "case-00000001" "invalid_meta" "16" "2" "15"

  python3 ./scripts/analyze_sim_initial_host_merge_steady_state_locality.py \
    --trace-root "$trace_root" \
    --output-dir "$out_dir"

  python3 - "$out_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
assert summary["decision_status"] == "invalid_trace_input", summary
assert decision["decision_status"] == "invalid_trace_input", decision
assert summary["recommended_runtime_prototype"] == "none", summary
assert any("meta_post_fill_full_set_miss_count" in error for error in summary["errors"]), summary
PY_INNER
}

run_needs_schema_v2_scenario() {
  local out_dir="$WORK/needs_schema_v2.out"
  local trace_root="$WORK/needs_schema_v2.trace"

  mkdir -p "$out_dir" "$trace_root"
  create_case "$trace_root" "case-00000001" "needs_schema_v2" "16" "1" "16"

  python3 ./scripts/analyze_sim_initial_host_merge_steady_state_locality.py \
    --trace-root "$trace_root" \
    --output-dir "$out_dir"

  python3 - "$out_dir" <<'PY_INNER'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
assert summary["decision_status"] == "needs_schema_v2", summary
assert summary["recommended_runtime_prototype"] == "none", summary
assert decision["decision_status"] == "needs_schema_v2", decision
assert any("schema_version" in error for error in summary["errors"]), summary
PY_INNER
}

run_ready_scenario strong_slot_no_reuse victim_strong_key_weak low lazy_generation_index 24
run_ready_scenario strong_slot_with_reuse victim_strong_key_mixed key_reuse none 24
run_ready_scenario floor_churn victim_strong_key_weak floor_churn none 24
run_ready_scenario weak_slot_weak_key no_actionable_locality low none 60
run_invalid_meta_scenario
run_needs_schema_v2_scenario
