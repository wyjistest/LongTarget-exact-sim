#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-min-maintenance-profile-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_profile_tsv() {
  local path="$1"
  local case_id="$2"
  local context_apply_mean="$3"
  local full_set_miss_mean="$4"
  local refresh_min_mean="$5"
  local candidate_index_mean="$6"
  local candidate_index_erase_mean="$7"
  local candidate_index_insert_mean="$8"
  local full_set_miss_count="$9"
  local refresh_min_calls="${10}"
  local refresh_min_slots_scanned="${11}"
  local candidate_lookup_count="${12}"
  local candidate_hit_count="${13}"
  local candidate_miss_count="${14}"
  local candidate_erase_count="${15}"
  local candidate_insert_count="${16}"
  local floor_changed_count="${17}"
  local floor_changed_share="${18}"
  local running_min_slot_changed_count="${19}"
  local running_min_slot_changed_share="${20}"
  local victim_was_running_min_count="${21}"
  local victim_was_running_min_share="${22}"
  local sim_initial_scan_cpu_merge_mean="${23}"
  local sim_initial_scan_mean="${24}"
  local sim_seconds_mean="${25}"
  local total_seconds_mean="${26}"
  local workload_id="${27:-}"
  local benchmark_source="${28:-}"

  cat >"$path" <<EOF
case_id	candidate_index_backend	warmup_iterations	iterations	logical_event_count	context_candidate_count_after_context_apply	context_apply_attempted_count	context_apply_modified_count	context_apply_noop_count	context_apply_lookup_hit_count	context_apply_lookup_miss_count	context_apply_lookup_probe_steps_total	context_apply_lookup_probe_steps_max	context_apply_lookup_miss_open_slot_count	context_apply_lookup_miss_candidate_set_full_count	context_apply_eviction_selected_count	context_apply_reused_slot_count	context_apply_full_set_miss_count	context_apply_floor_changed_count	context_apply_floor_changed_share	context_apply_running_min_slot_changed_count	context_apply_running_min_slot_changed_share	context_apply_victim_was_running_min_count	context_apply_victim_was_running_min_share	context_apply_refresh_min_calls	context_apply_refresh_min_slots_scanned	context_apply_refresh_min_slots_scanned_per_call	context_apply_candidate_index_lookup_count	context_apply_candidate_index_hit_count	context_apply_candidate_index_miss_count	context_apply_candidate_index_erase_count	context_apply_candidate_index_insert_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	context_apply_full_set_miss_mean_seconds	context_apply_full_set_miss_p50_seconds	context_apply_full_set_miss_p95_seconds	context_apply_refresh_min_mean_seconds	context_apply_refresh_min_p50_seconds	context_apply_refresh_min_p95_seconds	context_apply_candidate_index_mean_seconds	context_apply_candidate_index_p50_seconds	context_apply_candidate_index_p95_seconds	context_apply_candidate_index_erase_mean_seconds	context_apply_candidate_index_erase_p50_seconds	context_apply_candidate_index_erase_p95_seconds	context_apply_candidate_index_insert_mean_seconds	context_apply_candidate_index_insert_p50_seconds	context_apply_candidate_index_insert_p95_seconds	verify_ok	sim_initial_scan_cpu_merge_seconds_mean_seconds	sim_initial_scan_seconds_mean_seconds	sim_seconds_mean_seconds	total_seconds_mean_seconds	workload_id	benchmark_source
${case_id}	tombstone	1	5	1000	64	1000	1000	0	${candidate_hit_count}	${candidate_miss_count}	4096	17	8	${full_set_miss_count}	${full_set_miss_count}	${full_set_miss_count}	${full_set_miss_count}	${floor_changed_count}	${floor_changed_share}	${running_min_slot_changed_count}	${running_min_slot_changed_share}	${victim_was_running_min_count}	${victim_was_running_min_share}	${refresh_min_calls}	${refresh_min_slots_scanned}	8.0	${candidate_lookup_count}	${candidate_hit_count}	${candidate_miss_count}	${candidate_erase_count}	${candidate_insert_count}	${context_apply_mean}	${context_apply_mean}	${context_apply_mean}	${full_set_miss_mean}	${full_set_miss_mean}	${full_set_miss_mean}	${refresh_min_mean}	${refresh_min_mean}	${refresh_min_mean}	${candidate_index_mean}	${candidate_index_mean}	${candidate_index_mean}	${candidate_index_erase_mean}	${candidate_index_erase_mean}	${candidate_index_erase_mean}	${candidate_index_insert_mean}	${candidate_index_insert_mean}	${candidate_index_insert_mean}	1	${sim_initial_scan_cpu_merge_mean}	${sim_initial_scan_mean}	${sim_seconds_mean}	${total_seconds_mean}	${workload_id}	${benchmark_source}
EOF
}

run_and_assert() {
  local output_dir="$1"
  shift
  python3 ./scripts/summarize_sim_initial_host_merge_min_maintenance_profile.py "$@" --output-dir "$output_dir"
}

assert_decision() {
  local output_dir="$1"
  local expected_status="$2"
  local expected_action="$3"
  local expected_case_count="$4"
  local expected_materiality="$5"
  local expected_initial_cpu_merge_share_of_sim="$6"
  local expected_pairing="$7"
  python3 - "$output_dir" "$expected_status" "$expected_action" "$expected_case_count" "$expected_materiality" "$expected_initial_cpu_merge_share_of_sim" "$expected_pairing" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_status = sys.argv[2]
expected_action = sys.argv[3]
expected_case_count = int(sys.argv[4])
expected_materiality = sys.argv[5]
expected_initial_cpu_merge_share_of_sim = sys.argv[6]
expected_pairing = sys.argv[7]
summary = json.loads((output_dir / "min_maintenance_profile_summary.json").read_text(encoding="utf-8"))
decision = json.loads((output_dir / "min_maintenance_profile_decision.json").read_text(encoding="utf-8"))
assert decision["decision_status"] == expected_status, decision
assert decision["recommended_next_action"] == expected_action, decision
assert decision["case_count"] == expected_case_count, decision
assert summary["decision_status"] == expected_status, summary
assert summary["case_count"] == expected_case_count, summary
assert "cost_shares" in summary, summary
assert summary["materiality_status"] == expected_materiality, summary
assert summary["materiality_pairing_status"] == expected_pairing, summary
assert decision["materiality_pairing_status"] == expected_pairing, decision
if expected_initial_cpu_merge_share_of_sim == "none":
    assert summary["cost_shares"]["initial_cpu_merge_share_of_sim_seconds"] is None, summary
else:
    assert abs(
        summary["cost_shares"]["initial_cpu_merge_share_of_sim_seconds"]
        - float(expected_initial_cpu_merge_share_of_sim)
    ) < 1e-9, summary
assert Path(summary["cases_tsv"]).name == "min_maintenance_profile_cases.tsv", summary
assert Path(summary["summary_markdown"]).name == "min_maintenance_profile_summary.md", summary
PY
}

assert_not_ready() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
summary = json.loads((output_dir / "min_maintenance_profile_summary.json").read_text(encoding="utf-8"))
decision = json.loads((output_dir / "min_maintenance_profile_decision.json").read_text(encoding="utf-8"))
assert summary["decision_status"] == "not_ready", summary
assert decision["decision_status"] == "not_ready", decision
assert decision["recommended_next_action"] == "fix_profile_inputs", decision
PY
}

REFRESH="$WORK/refresh.tsv"
write_profile_tsv "$REFRESH" "case-refresh" "1.00" "0.40" "0.25" "0.05" "0.01" "0.02" "400" "400" "3200" "1000" "600" "400" "100" "400" "320" "0.80" "300" "0.75" "240" "0.60" "0.50" "2.00" "2.50" "5.00" "wl-refresh" "/tmp/wl-refresh.stderr.log"
run_and_assert "$WORK/out-refresh" --aggregate-tsv "$REFRESH"
assert_decision "$WORK/out-refresh" "ready" "prototype_stable_min_maintenance" "1" "known" "0.2" "complete"

CANDIDATE="$WORK/candidate.tsv"
write_profile_tsv "$CANDIDATE" "case-candidate" "1.00" "0.20" "0.05" "0.30" "0.04" "0.03" "200" "200" "1600" "1000" "700" "300" "40" "300" "160" "0.80" "150" "0.75" "120" "0.60" "0.50" "2.00" "2.50" "5.00" "wl-candidate" "/tmp/wl-candidate.stderr.log"
run_and_assert "$WORK/out-candidate" --aggregate-tsv "$CANDIDATE"
assert_decision "$WORK/out-candidate" "ready" "profile_candidate_index_lifecycle" "1" "known" "0.2" "complete"

ERASE="$WORK/erase.tsv"
write_profile_tsv "$ERASE" "case-erase" "1.00" "0.18" "0.04" "0.30" "0.18" "0.03" "180" "180" "1440" "1000" "760" "240" "180" "240" "144" "0.80" "120" "0.67" "96" "0.53" "0.50" "2.00" "2.50" "5.00" "wl-erase" "/tmp/wl-erase.stderr.log"
run_and_assert "$WORK/out-erase" --aggregate-tsv "$ERASE"
assert_decision "$WORK/out-erase" "ready" "prototype_eager_index_erase_handle" "1" "known" "0.2" "complete"

LOW="$WORK/low.tsv"
write_profile_tsv "$LOW" "case-low" "1.00" "0.08" "0.05" "0.07" "0.01" "0.02" "80" "80" "640" "1000" "800" "200" "10" "200" "48" "0.60" "32" "0.40" "24" "0.30" "0.50" "2.00" "2.50" "5.00" "wl-low" "/tmp/wl-low.stderr.log"
run_and_assert "$WORK/out-low" --aggregate-tsv "$LOW"
assert_decision "$WORK/out-low" "ready" "return_to_initial_run_summary_kernel" "1" "known" "0.2" "complete"

IMMATERIAL="$WORK/immaterial.tsv"
write_profile_tsv "$IMMATERIAL" "case-immaterial" "0.02" "0.01" "0.008" "0.006" "0.002" "0.001" "10" "10" "80" "100" "80" "20" "2" "20" "8" "0.80" "8" "0.80" "7" "0.70" "0.02" "0.30" "2.00" "4.00" "wl-immaterial" "/tmp/wl-immaterial.stderr.log"
run_and_assert "$WORK/out-immaterial" --aggregate-tsv "$IMMATERIAL"
assert_decision "$WORK/out-immaterial" "ready" "no_host_merge_runtime_work" "1" "known" "0.01" "complete"

UNKNOWN="$WORK/unknown.tsv"
cat >"$UNKNOWN" <<'EOF'
case_id	candidate_index_backend	warmup_iterations	iterations	logical_event_count	context_candidate_count_after_context_apply	context_apply_attempted_count	context_apply_modified_count	context_apply_noop_count	context_apply_lookup_hit_count	context_apply_lookup_miss_count	context_apply_lookup_probe_steps_total	context_apply_lookup_probe_steps_max	context_apply_lookup_miss_open_slot_count	context_apply_lookup_miss_candidate_set_full_count	context_apply_eviction_selected_count	context_apply_reused_slot_count	context_apply_full_set_miss_count	context_apply_floor_changed_count	context_apply_floor_changed_share	context_apply_running_min_slot_changed_count	context_apply_running_min_slot_changed_share	context_apply_victim_was_running_min_count	context_apply_victim_was_running_min_share	context_apply_refresh_min_calls	context_apply_refresh_min_slots_scanned	context_apply_refresh_min_slots_scanned_per_call	context_apply_candidate_index_lookup_count	context_apply_candidate_index_hit_count	context_apply_candidate_index_miss_count	context_apply_candidate_index_erase_count	context_apply_candidate_index_insert_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	context_apply_full_set_miss_mean_seconds	context_apply_full_set_miss_p50_seconds	context_apply_full_set_miss_p95_seconds	context_apply_refresh_min_mean_seconds	context_apply_refresh_min_p50_seconds	context_apply_refresh_min_p95_seconds	context_apply_candidate_index_mean_seconds	context_apply_candidate_index_p50_seconds	context_apply_candidate_index_p95_seconds	context_apply_candidate_index_erase_mean_seconds	context_apply_candidate_index_erase_p50_seconds	context_apply_candidate_index_erase_p95_seconds	context_apply_candidate_index_insert_mean_seconds	context_apply_candidate_index_insert_p50_seconds	context_apply_candidate_index_insert_p95_seconds	verify_ok
case-unknown	tombstone	1	5	1000	64	1000	1000	0	700	300	4096	17	8	300	300	300	300	240	0.80	210	0.70	180	0.60	300	2400	8.0	1000	700	300	40	300	0.95	0.95	0.95	0.18	0.18	0.18	0.05	0.05	0.05	0.28	0.28	0.28	0.05	0.05	0.05	0.04	0.04	0.04	1
EOF
run_and_assert "$WORK/out-unknown" --aggregate-tsv "$UNKNOWN"
assert_decision "$WORK/out-unknown" "ready_but_materiality_unknown" "profile_candidate_index_lifecycle" "1" "unknown" "none" "missing"

MISSING="$WORK/missing.tsv"
cat >"$MISSING" <<'EOF'
case_id	context_apply_mean_seconds
case-missing	1.0
EOF
run_and_assert "$WORK/out-missing" --aggregate-tsv "$MISSING"
assert_not_ready "$WORK/out-missing"

ZERO="$WORK/zero.tsv"
write_profile_tsv "$ZERO" "case-zero" "1.00" "0.20" "0.05" "0.30" "0.04" "0.03" "200" "200" "1600" "1000" "700" "300" "40" "300" "160" "0.80" "150" "0.75" "120" "0.60" "0.50" "0.00" "2.50" "5.00" "wl-zero" "/tmp/wl-zero.stderr.log"
run_and_assert "$WORK/out-zero" --aggregate-tsv "$ZERO"
assert_not_ready "$WORK/out-zero"

MISMATCH="$WORK/mismatch.tsv"
cat >"$MISMATCH" <<'EOF'
case_id	candidate_index_backend	warmup_iterations	iterations	logical_event_count	context_candidate_count_after_context_apply	context_apply_attempted_count	context_apply_modified_count	context_apply_noop_count	context_apply_lookup_hit_count	context_apply_lookup_miss_count	context_apply_lookup_probe_steps_total	context_apply_lookup_probe_steps_max	context_apply_lookup_miss_open_slot_count	context_apply_lookup_miss_candidate_set_full_count	context_apply_eviction_selected_count	context_apply_reused_slot_count	context_apply_full_set_miss_count	context_apply_floor_changed_count	context_apply_floor_changed_share	context_apply_running_min_slot_changed_count	context_apply_running_min_slot_changed_share	context_apply_victim_was_running_min_count	context_apply_victim_was_running_min_share	context_apply_refresh_min_calls	context_apply_refresh_min_slots_scanned	context_apply_refresh_min_slots_scanned_per_call	context_apply_candidate_index_lookup_count	context_apply_candidate_index_hit_count	context_apply_candidate_index_miss_count	context_apply_candidate_index_erase_count	context_apply_candidate_index_insert_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	context_apply_full_set_miss_mean_seconds	context_apply_full_set_miss_p50_seconds	context_apply_full_set_miss_p95_seconds	context_apply_refresh_min_mean_seconds	context_apply_refresh_min_p50_seconds	context_apply_refresh_min_p95_seconds	context_apply_candidate_index_mean_seconds	context_apply_candidate_index_p50_seconds	context_apply_candidate_index_p95_seconds	context_apply_candidate_index_erase_mean_seconds	context_apply_candidate_index_erase_p50_seconds	context_apply_candidate_index_erase_p95_seconds	context_apply_candidate_index_insert_mean_seconds	context_apply_candidate_index_insert_p50_seconds	context_apply_candidate_index_insert_p95_seconds	verify_ok	sim_initial_scan_cpu_merge_seconds_mean_seconds	sim_initial_scan_seconds_mean_seconds	sim_seconds_mean_seconds	total_seconds_mean_seconds	workload_id	benchmark_source
case-a	tombstone	1	5	1000	64	1000	1000	0	600	400	4096	17	8	400	400	400	400	320	0.80	300	0.75	240	0.60	400	3200	8.0	1000	600	400	100	400	1.00	1.00	1.00	0.40	0.40	0.40	0.28	0.28	0.28	0.08	0.08	0.08	0.03	0.03	0.03	0.03	0.03	0.03	1	2.00	2.50	10.00	20.00	wl-shared	/tmp/wl-a.stderr.log
case-b	tombstone	1	5	1000	64	1000	1000	0	700	300	4096	17	8	300	300	300	300	240	0.80	210	0.70	180	0.60	300	2400	8.0	1000	700	300	40	300	0.95	0.95	0.95	0.18	0.18	0.18	0.05	0.05	0.05	0.28	0.28	0.28	0.05	0.05	0.05	0.04	0.04	0.04	1	2.00	2.50	10.00	20.00	wl-shared	/tmp/wl-b.stderr.log
EOF
run_and_assert "$WORK/out-mismatch" --aggregate-tsv "$MISMATCH"
assert_decision "$WORK/out-mismatch" "ready_but_materiality_unknown" "prototype_stable_min_maintenance" "2" "unknown" "none" "mismatched"

COMBINED="$WORK/combined.tsv"
cat >"$COMBINED" <<'EOF'
case_id	candidate_index_backend	warmup_iterations	iterations	logical_event_count	context_candidate_count_after_context_apply	context_apply_attempted_count	context_apply_modified_count	context_apply_noop_count	context_apply_lookup_hit_count	context_apply_lookup_miss_count	context_apply_lookup_probe_steps_total	context_apply_lookup_probe_steps_max	context_apply_lookup_miss_open_slot_count	context_apply_lookup_miss_candidate_set_full_count	context_apply_eviction_selected_count	context_apply_reused_slot_count	context_apply_full_set_miss_count	context_apply_floor_changed_count	context_apply_floor_changed_share	context_apply_running_min_slot_changed_count	context_apply_running_min_slot_changed_share	context_apply_victim_was_running_min_count	context_apply_victim_was_running_min_share	context_apply_refresh_min_calls	context_apply_refresh_min_slots_scanned	context_apply_refresh_min_slots_scanned_per_call	context_apply_candidate_index_lookup_count	context_apply_candidate_index_hit_count	context_apply_candidate_index_miss_count	context_apply_candidate_index_erase_count	context_apply_candidate_index_insert_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	context_apply_full_set_miss_mean_seconds	context_apply_full_set_miss_p50_seconds	context_apply_full_set_miss_p95_seconds	context_apply_refresh_min_mean_seconds	context_apply_refresh_min_p50_seconds	context_apply_refresh_min_p95_seconds	context_apply_candidate_index_mean_seconds	context_apply_candidate_index_p50_seconds	context_apply_candidate_index_p95_seconds	context_apply_candidate_index_erase_mean_seconds	context_apply_candidate_index_erase_p50_seconds	context_apply_candidate_index_erase_p95_seconds	context_apply_candidate_index_insert_mean_seconds	context_apply_candidate_index_insert_p50_seconds	context_apply_candidate_index_insert_p95_seconds	verify_ok	sim_initial_scan_cpu_merge_seconds_mean_seconds	sim_initial_scan_seconds_mean_seconds	sim_seconds_mean_seconds	total_seconds_mean_seconds	workload_id	benchmark_source
case-a	tombstone	1	5	1000	64	1000	1000	0	600	400	4096	17	8	400	400	400	400	320	0.80	300	0.75	240	0.60	400	3200	8.0	1000	600	400	100	400	1.00	1.00	1.00	0.40	0.40	0.40	0.28	0.28	0.28	0.08	0.08	0.08	0.03	0.03	0.03	0.03	0.03	0.03	1	2.00	2.50	10.00	20.00	wl-dup	/tmp/wl-dup.stderr.log
case-b	tombstone	1	5	1000	64	1000	1000	0	700	300	4096	17	8	300	300	300	300	240	0.80	210	0.70	180	0.60	300	2400	8.0	1000	700	300	40	300	0.95	0.95	0.95	0.18	0.18	0.18	0.05	0.05	0.05	0.28	0.28	0.28	0.05	0.05	0.05	0.04	0.04	0.04	1	2.00	2.50	10.00	20.00	wl-dup	/tmp/wl-dup.stderr.log
EOF
run_and_assert "$WORK/out-combined" --aggregate-tsv "$COMBINED"
assert_decision "$WORK/out-combined" "ready" "prototype_stable_min_maintenance" "2" "known" "0.2" "duplicate_grouped"

echo "check_summarize_sim_initial_host_merge_min_maintenance_profile: PASS"
