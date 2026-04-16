#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-host-merge-phase-shares-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

run_scenario() {
  local scenario="$1"
  local expected_status="$2"
  local expected_next="$3"
  local expected_phase="$4"
  local manifest="$WORK/$scenario.manifest.tsv"
  local selected="$WORK/$scenario.selected.tsv"
  local aggregate="$WORK/$scenario.aggregate.tsv"
  local out_dir="$WORK/$scenario.out"
  mkdir -p "$out_dir"

  case "$scenario" in
    materialize)
      cat >"$manifest" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-a	1	64	128	400	40	5	400	120	0.3	true
case-b	2	64	128	600	60	5	600	480	0.8	true
EOF
      cat >"$selected" <<'EOF'
case_id	bucket_key	summary_bin	materialized_bin	prune_bin	logical_event_count	summary_count	store_materialized_count	store_pruned_count	prune_ratio	selection_rank	selection_reason
case-a	s1|m1|p0	1	1	0	400	40	400	120	0.3	1	bucket_representative
case-b	s2|m2|p2	2	2	2	600	60	600	480	0.8	2	bucket_representative
EOF
      cat >"$aggregate" <<'EOF'
case_id	warmup_iterations	iterations	logical_event_count	store_materialized_count	store_pruned_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	store_materialize_mean_seconds	store_materialize_p50_seconds	store_materialize_p95_seconds	store_prune_mean_seconds	store_prune_p50_seconds	store_prune_p95_seconds	store_other_merge_mean_seconds	store_other_merge_p50_seconds	store_other_merge_p95_seconds	full_host_merge_mean_seconds	full_host_merge_p50_seconds	full_host_merge_p95_seconds	ns_per_logical_event	ns_per_materialized_record	ns_per_pruned_record
case-a	1	3	400	400	120	0.05	0.05	0.05	2.0	2.0	2.0	0.4	0.4	0.4	0.1	0.1	0.1	2.5	2.5	2.5	0	0	0
case-b	1	3	600	600	480	0.05	0.05	0.05	3.0	3.0	3.0	0.9	0.9	0.9	0.1	0.1	0.1	4.0	4.0	4.0	0	0	0
EOF
      ;;
    prune)
      cat >"$manifest" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-a	1	64	128	300	30	5	300	270	0.9	true
case-b	2	64	128	500	50	5	500	450	0.9	true
EOF
      cat >"$selected" <<'EOF'
case_id	bucket_key	summary_bin	materialized_bin	prune_bin	logical_event_count	summary_count	store_materialized_count	store_pruned_count	prune_ratio	selection_rank	selection_reason
case-a	s0|m0|p2	0	0	2	300	30	300	270	0.9	1	bucket_representative
case-b	s2|m2|p2	2	2	2	500	50	500	450	0.9	2	bucket_representative
EOF
      cat >"$aggregate" <<'EOF'
case_id	warmup_iterations	iterations	logical_event_count	store_materialized_count	store_pruned_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	store_materialize_mean_seconds	store_materialize_p50_seconds	store_materialize_p95_seconds	store_prune_mean_seconds	store_prune_p50_seconds	store_prune_p95_seconds	store_other_merge_mean_seconds	store_other_merge_p50_seconds	store_other_merge_p95_seconds	full_host_merge_mean_seconds	full_host_merge_p50_seconds	full_host_merge_p95_seconds	ns_per_logical_event	ns_per_materialized_record	ns_per_pruned_record
case-a	1	3	300	300	270	0.05	0.05	0.05	0.3	0.3	0.3	1.2	1.2	1.2	0.1	0.1	0.1	1.6	1.6	1.6	0	0	0
case-b	1	3	500	500	450	0.05	0.05	0.05	0.5	0.5	0.5	2.5	2.5	2.5	0.2	0.2	0.2	3.2	3.2	3.2	0	0	0
EOF
      ;;
    split)
      cat >"$manifest" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-a	1	64	128	400	40	5	400	280	0.7	true
case-b	2	64	128	400	40	5	400	280	0.7	true
EOF
      cat >"$selected" <<'EOF'
case_id	bucket_key	summary_bin	materialized_bin	prune_bin	logical_event_count	summary_count	store_materialized_count	store_pruned_count	prune_ratio	selection_rank	selection_reason
case-a	s1|m1|p2	1	1	2	400	40	400	280	0.7	1	bucket_representative
case-b	s2|m2|p2	2	2	2	400	40	400	280	0.7	2	bucket_representative
EOF
      cat >"$aggregate" <<'EOF'
case_id	warmup_iterations	iterations	logical_event_count	store_materialized_count	store_pruned_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	store_materialize_mean_seconds	store_materialize_p50_seconds	store_materialize_p95_seconds	store_prune_mean_seconds	store_prune_p50_seconds	store_prune_p95_seconds	store_other_merge_mean_seconds	store_other_merge_p50_seconds	store_other_merge_p95_seconds	full_host_merge_mean_seconds	full_host_merge_p50_seconds	full_host_merge_p95_seconds	ns_per_logical_event	ns_per_materialized_record	ns_per_pruned_record
case-a	1	3	400	400	280	0.05	0.05	0.05	1.0	1.0	1.0	0.9	0.9	0.9	0.2	0.2	0.2	2.1	2.1	2.1	0	0	0
case-b	1	3	400	400	280	0.05	0.05	0.05	1.1	1.1	1.1	1.0	1.0	1.0	0.2	0.2	0.2	2.3	2.3	2.3	0	0	0
EOF
      ;;
    insufficient)
      cat >"$manifest" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-a	1	64	128	200	20	5	200	60	0.3	true
case-b	2	64	128	300	30	5	300	90	0.3	true
case-c	3	64	128	700	70	5	700	560	0.8	true
EOF
      cat >"$selected" <<'EOF'
case_id	bucket_key	summary_bin	materialized_bin	prune_bin	logical_event_count	summary_count	store_materialized_count	store_pruned_count	prune_ratio	selection_rank	selection_reason
case-a	s0|m0|p0	0	0	0	200	20	200	60	0.3	1	bucket_representative
EOF
      cat >"$aggregate" <<'EOF'
case_id	warmup_iterations	iterations	logical_event_count	store_materialized_count	store_pruned_count	context_apply_mean_seconds	context_apply_p50_seconds	context_apply_p95_seconds	store_materialize_mean_seconds	store_materialize_p50_seconds	store_materialize_p95_seconds	store_prune_mean_seconds	store_prune_p50_seconds	store_prune_p95_seconds	store_other_merge_mean_seconds	store_other_merge_p50_seconds	store_other_merge_p95_seconds	full_host_merge_mean_seconds	full_host_merge_p50_seconds	full_host_merge_p95_seconds	ns_per_logical_event	ns_per_materialized_record	ns_per_pruned_record
case-a	1	3	200	200	60	0.05	0.05	0.05	1.2	1.2	1.2	0.2	0.2	0.2	0.1	0.1	0.1	1.5	1.5	1.5	0	0	0
EOF
      ;;
    *)
      echo "unknown scenario: $scenario" >&2
      return 1
      ;;
  esac

  python3 ./scripts/analyze_sim_initial_host_merge_phase_shares.py \
    --manifest "$manifest" \
    --selected "$selected" \
    --aggregate "$aggregate" \
    --output-dir "$out_dir"

  python3 - "$out_dir/summary.json" "$expected_status" "$expected_next" "$expected_phase" <<'PY'
import json
import math
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_status = sys.argv[2]
expected_next = sys.argv[3]
expected_phase = sys.argv[4]

assert summary["decision_status"] == expected_status, summary
assert summary["next_action"] == expected_next, summary
assert summary["dominant_phase"] == expected_phase, summary
assert "covered_logical_event_share" in summary
assert "covered_store_materialized_share" in summary
assert set(summary["phase_seconds"].keys()) == {"store_materialize", "store_prune", "store_other_merge"}
assert set(summary["phase_shares"].keys()) == {"store_materialize", "store_prune", "store_other_merge"}
assert Path(summary["selected_joined_tsv"]).name == "selected_joined.tsv"
assert Path(summary["bucket_rollup_tsv"]).name == "bucket_rollup.tsv"
assert Path(summary["summary_markdown"]).name == "summary.md"
if expected_status != "insufficient_coverage":
    assert summary["covered_logical_event_share"] >= 0.8, summary
    assert summary["covered_store_materialized_share"] >= 0.8, summary
else:
    assert summary["covered_logical_event_share"] < 0.8 or summary["covered_store_materialized_share"] < 0.8, summary
PY
}

run_scenario materialize ready optimize_store_materialize store_materialize
run_scenario prune ready optimize_store_prune store_prune
run_scenario split ready split_materialize_and_prune split
run_scenario insufficient insufficient_coverage expand_corpus store_materialize
