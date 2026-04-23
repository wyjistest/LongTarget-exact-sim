#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-host-merge-reference-profile-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/context_apply.tsv" <<'EOF'
case_id	logical_event_count	context_candidate_count_after_context_apply	running_min_after_context_apply	context_apply_seconds	context_apply_lookup_seconds	context_apply_lookup_hit_seconds	context_apply_lookup_miss_seconds	context_apply_lookup_miss_open_slot_seconds	context_apply_lookup_miss_candidate_set_full_probe_seconds	context_apply_lookup_miss_eviction_select_seconds	context_apply_lookup_miss_reuse_writeback_seconds	context_apply_mutate_seconds	context_apply_finalize_seconds	context_apply_attempted_count	context_apply_modified_count	context_apply_noop_count	context_apply_lookup_hit_count	context_apply_lookup_miss_count	context_apply_lookup_probe_steps_total	context_apply_lookup_probe_steps_max	context_apply_lookup_miss_open_slot_count	context_apply_lookup_miss_candidate_set_full_count	context_apply_eviction_selected_count	context_apply_reused_slot_count	verify_ok
case-00000417	100	50	50	1.30	1.20	0.01	1.19	0	0.11	0.05	1.03	0.10	0.00	10	10	0	1	9	90	8	1	8	8	8	1
case-00000077	100	50	50	1.60	1.48	0.01	1.47	0	0.12	0.06	1.29	0.12	0.00	10	10	0	1	9	95	8	1	8	8	8	1
case-00000039	100	50	50	1.50	1.39	0.01	1.38	0	0.12	0.06	1.20	0.11	0.00	10	10	0	1	9	94	8	1	8	8	8	1
case-00000028	100	50	50	1.40	1.29	0.01	1.28	0	0.11	0.05	1.12	0.11	0.00	10	10	0	1	9	93	8	1	8	8	8	1
case-00000040	100	50	50	1.35	1.24	0.01	1.23	0	0.10	0.05	1.08	0.11	0.00	10	10	0	1	9	92	8	1	8	8	8	1
case-00000022	100	50	50	1.25	1.15	0.01	1.14	0	0.10	0.04	1.00	0.10	0.00	10	10	0	1	9	91	8	1	8	8	8	1
case-00000159	100	50	50	0.90	0.82	0.01	0.81	0	0.07	0.03	0.71	0.08	0.00	10	10	0	1	9	70	6	1	8	8	8	1
EOF

cat >"$WORK/reference_aggregate.tsv" <<'EOF'
case_id	backend	warmup_iterations	iterations	post_fill_event_count	full_set_miss_count	total_mean_seconds	total_p50_seconds	total_p95_seconds	full_set_miss_mean_seconds	full_set_miss_p50_seconds	full_set_miss_p95_seconds	verify_ok
case-00000417	reference	1	5	100	90	0.30	0.30	0.31	0.16	0.16	0.17	1
case-00000077	reference	1	5	100	90	0.38	0.38	0.39	0.19	0.19	0.20	1
case-00000039	reference	1	5	100	90	0.34	0.34	0.35	0.17	0.17	0.18	1
case-00000028	reference	1	5	100	90	0.31	0.31	0.32	0.15	0.15	0.16	1
case-00000040	reference	1	5	100	90	0.29	0.29	0.30	0.14	0.14	0.15	1
case-00000022	reference	1	5	100	90	0.25	0.25	0.26	0.12	0.12	0.13	1
case-00000159	reference	1	5	100	90	0.20	0.20	0.21	0.10	0.10	0.11	1
EOF

mkdir -p "$WORK/gprof"

for case_id in case-00000417 case-00000077 case-00000039 case-00000028 case-00000040 case-00000022; do
  cat >"$WORK/gprof/${case_id}.run1.gprof.txt" <<EOF
Flat profile:

Each sample counts as 0.01 seconds.
  %   cumulative   self              self     total
 time   seconds   seconds    calls  ms/call  ms/call  name
  5.00      0.05     0.05       10     0.00     0.00  probeSimCandidateIndexSlot(SimCandidateStartIndex const&, long, long)
 14.00      0.19     0.14       10     0.00     0.00  std::chrono::duration<long, std::ratio<1l, 1000000000l> >::zero()
 13.00      0.32     0.13       10     0.00     0.00  simElapsedNanoseconds(std::chrono::time_point<std::chrono::_V2::steady_clock, std::chrono::duration<long, std::ratio<1l, 1000000000l> > > const&)
  4.00      0.18     0.04       10     0.00     0.00  ensureSimCandidateIndexForRun(SimKernelContext&, long, long, long, long, long, bool*, bool*, SimCandidateIndexLookupTrace*)
  3.00      0.12     0.03       10     0.00     0.00  std::_Hashtable<unsigned long, std::pair<unsigned long const, unsigned long>, std::allocator<std::pair<unsigned long const, unsigned long> >, std::__detail::_Select1st, std::equal_to<unsigned long>, std::hash<unsigned long>, std::__detail::_Mod_range_hashing, std::__detail::_Default_ranged_hash, std::__detail::_Prime_rehash_policy, std::__detail::_Hashtable_traits<false, false, true> >::_M_find_before_node(unsigned long, unsigned long const&, unsigned long) const
  2.00      0.14     0.02       10     0.00     0.00  std::pair<std::__detail::_Node_iterator<std::pair<unsigned long const, unsigned long>, false, false>, bool> std::_Hashtable<unsigned long, std::pair<unsigned long const, unsigned long>, std::allocator<std::pair<unsigned long const, unsigned long> >, std::__detail::_Select1st, std::equal_to<unsigned long>, std::hash<unsigned long>, std::__detail::_Mod_range_hashing, std::__detail::_Default_ranged_hash, std::__detail::_Prime_rehash_policy, std::__detail::_Hashtable_traits<false, false, true> >::_M_emplace<unsigned long const&, unsigned long>(std::integral_constant<bool, true>, unsigned long const&, unsigned long&&)
  1.00      0.15     0.01       10     0.00     0.00  updateSimCandidateMinHeapIndex(SimKernelContext&, int)
EOF
done

python3 ./scripts/analyze_sim_initial_host_merge_reference_profile.py   --context-apply-tsv "$WORK/context_apply.tsv"   --reference-aggregate-tsv "$WORK/reference_aggregate.tsv"   --gprof-report case-00000417="$WORK/gprof/case-00000417.run1.gprof.txt"   --gprof-report case-00000077="$WORK/gprof/case-00000077.run1.gprof.txt"   --gprof-report case-00000039="$WORK/gprof/case-00000039.run1.gprof.txt"   --gprof-report case-00000028="$WORK/gprof/case-00000028.run1.gprof.txt"   --gprof-report case-00000040="$WORK/gprof/case-00000040.run1.gprof.txt"   --gprof-report case-00000022="$WORK/gprof/case-00000022.run1.gprof.txt"   --anchor-case case-00000417   --heavy-case-count 5   --output-dir "$WORK/out"

python3 - "$WORK/out/summary.json" <<'PY2'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert summary["anchor_case_id"] == "case-00000417", summary
assert summary["selected_case_ids"] == [
    "case-00000417",
    "case-00000077",
    "case-00000039",
    "case-00000028",
    "case-00000040",
    "case-00000022",
], summary
assert summary["dominant_hotspot_family"] == "candidate_index_map_path", summary
assert summary["recommended_next_step"] == "optimize_candidate_index_map_path", summary
assert summary["selected_case_count"] == 6, summary
assert summary["top_hotspot_family_case_count"] >= 4, summary
assert Path(summary["summary_markdown"]).name == "summary.md", summary
assert Path(summary["selected_cases_tsv"]).name == "selected_cases.tsv", summary
assert summary["family_self_seconds"]["candidate_index_map_path"] > summary["family_self_seconds"]["heap_maintenance_path"], summary
PY2

grep -q "Host-Merge Reference Profile Summary" "$WORK/out/summary.md"
grep -q "candidate_index_map_path" "$WORK/out/summary.md"
