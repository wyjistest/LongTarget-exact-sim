#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-profile-mode-ab-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_artifact() {
  local dir="$1"
  local profile_mode="$2"
  local candidate_index_seconds="$3"
  local terminal_parent_seconds="$4"
  local first_half_parent_seconds="$5"
  local first_half_span_a_seconds="$6"
  local first_half_span_b_seconds="$7"
  local sim_seconds="$8"
  local total_seconds="$9"
  local timer_call_count="${10}"
  local terminal_timer_call_count="${11}"
  local lexical_timer_call_count="${12}"
  local workload_id="${13}"
  local dominant_span="${14}"
  local pairing_status="${15:-complete}"
  local benchmark_source="${16:-/tmp/${profile_mode}.stderr.log}"
  local first_half_unexplained_seconds="${17:-0.0}"
  local benchmark_payload="${18:-${profile_mode}-payload}"
  local profile_sample_log2="${19:-}"
  local profile_sample_rate="${20:-}"
  local span_a_parent_seconds="${21:-${first_half_span_a_seconds}}"
  local span_a0_seconds="${22:-0.0}"
  local span_a1_seconds="${23:-0.0}"
  local span_a_unexplained_seconds="${24:-0.0}"
  local dominant_span_a_child="${25:-unknown}"
  local span_a0_parent_seconds="${26:-${span_a0_seconds}}"
  local span_a00_seconds="${27:-0.0}"
  local span_a01_seconds="${28:-0.0}"
  local span_a0_unexplained_seconds="${29:-0.0}"
  local dominant_span_a0_child="${30:-unknown}"
  local span_a0_gap_before_a00_seconds="${31:-0.0}"
  local span_a0_gap_between_a00_a01_seconds="${32:-0.0}"
  local span_a0_gap_after_a01_seconds="${33:-0.0}"
  local span_a0_sampled_event_count="${34:-0}"
  local span_a0_covered_sampled_event_count="${35:-0}"
  local span_a0_gap_before_a00_sampled_event_count="${36:-0}"
  local span_a00_sampled_event_count="${37:-0}"
  local span_a0_gap_between_a00_a01_sampled_event_count="${38:-0}"
  local span_a01_sampled_event_count="${39:-0}"
  local span_a0_gap_after_a01_sampled_event_count="${40:-0}"
  local span_a0_unclassified_sampled_event_count="${41:-0}"
  local span_a0_multi_child_sampled_event_count="${42:-0}"
  local span_a0_overlap_sampled_event_count="${43:-0}"
  local gap_before_a00_parent_seconds="${44:-${span_a0_gap_before_a00_seconds}}"
  local gap_before_a00_span_0_seconds="${45:-0.0}"
  local gap_before_a00_span_1_seconds="${46:-0.0}"
  local gap_before_a00_covered_sampled_event_count="${47:-0}"
  local gap_before_a00_span_0_sampled_event_count="${48:-0}"
  local gap_before_a00_span_1_sampled_event_count="${49:-0}"
  local gap_before_a00_unclassified_sampled_event_count="${50:-0}"
  local gap_before_a00_multi_child_sampled_event_count="${51:-0}"
  local dominant_gap_before_a00_child="${52:-unknown}"
  local gap_before_a00_span_0_parent_seconds="${53:-${gap_before_a00_span_0_seconds}}"
  local gap_before_a00_span_0_child_0_seconds="${54:-0.0}"
  local gap_before_a00_span_0_child_1_seconds="${55:-0.0}"
  local gap_before_a00_span_0_covered_sampled_event_count="${56:-0}"
  local gap_before_a00_span_0_child_0_sampled_event_count="${57:-0}"
  local gap_before_a00_span_0_child_1_sampled_event_count="${58:-0}"
  local gap_before_a00_span_0_unclassified_sampled_event_count="${59:-0}"
  local gap_before_a00_span_0_multi_child_sampled_event_count="${60:-0}"
  local dominant_gap_before_a00_span_0_child="${61:-unknown}"
  local gap_before_a00_span_0_alt_parent_seconds="${62:-${gap_before_a00_span_0_parent_seconds}}"
  local gap_before_a00_span_0_alt_left_seconds="${63:-0.0}"
  local gap_before_a00_span_0_alt_right_seconds="${64:-0.0}"
  local gap_before_a00_span_0_alt_sampled_event_count="${65:-0}"
  local gap_before_a00_span_0_alt_covered_sampled_event_count="${66:-0}"
  local gap_before_a00_span_0_alt_left_sampled_event_count="${67:-0}"
  local gap_before_a00_span_0_alt_right_sampled_event_count="${68:-0}"
  local gap_before_a00_span_0_alt_unclassified_sampled_event_count="${69:-0}"
  local gap_before_a00_span_0_alt_multi_child_sampled_event_count="${70:-0}"
  local dominant_gap_before_a00_span_0_alt_child="${71:-unknown}"
  local span_a_child_known_seconds
  span_a_child_known_seconds=$(python3 - <<PY
print(float("${span_a0_seconds}") + float("${span_a1_seconds}"))
PY
)
  local span_a0_child_known_seconds
  span_a0_child_known_seconds=$(python3 - <<PY
print(
    float("${span_a0_gap_before_a00_seconds}") +
    float("${span_a00_seconds}") +
    float("${span_a0_gap_between_a00_a01_seconds}") +
    float("${span_a01_seconds}") +
    float("${span_a0_gap_after_a01_seconds}")
)
PY
)
  local gap_before_a00_child_known_seconds
  gap_before_a00_child_known_seconds=$(python3 - <<PY
print(float("${gap_before_a00_span_0_seconds}") + float("${gap_before_a00_span_1_seconds}"))
PY
)
  local gap_before_a00_unexplained_seconds
  gap_before_a00_unexplained_seconds=$(python3 - <<PY
parent = float("${gap_before_a00_parent_seconds}")
child = float("${gap_before_a00_child_known_seconds}")
print(parent - child if parent > child else 0.0)
PY
)
  local gap_before_a00_span_0_child_known_seconds
  gap_before_a00_span_0_child_known_seconds=$(python3 - <<PY
print(float("${gap_before_a00_span_0_child_0_seconds}") + float("${gap_before_a00_span_0_child_1_seconds}"))
PY
  )
  local gap_before_a00_span_0_unexplained_seconds
  gap_before_a00_span_0_unexplained_seconds=$(python3 - <<PY
parent = float("${gap_before_a00_span_0_parent_seconds}")
child = float("${gap_before_a00_span_0_child_known_seconds}")
print(parent - child if parent > child else 0.0)
PY
  )
  local gap_before_a00_span_0_alt_child_known_seconds
  gap_before_a00_span_0_alt_child_known_seconds=$(python3 - <<PY
print(float("${gap_before_a00_span_0_alt_left_seconds}") + float("${gap_before_a00_span_0_alt_right_seconds}"))
PY
  )
  local gap_before_a00_span_0_alt_unexplained_seconds
  gap_before_a00_span_0_alt_unexplained_seconds=$(python3 - <<PY
parent = float("${gap_before_a00_span_0_alt_parent_seconds}")
child = float("${gap_before_a00_span_0_alt_child_known_seconds}")
print(parent - child if parent > child else 0.0)
PY
  )

  mkdir -p "$dir"
  mkdir -p "$(dirname "$benchmark_source")"
  cat >"$benchmark_source" <<EOF
benchmark.sim_initial_scan_seconds=1.0
benchmark.sim_initial_scan_cpu_merge_seconds=2.0
benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=2.0
benchmark.sim_seconds=${sim_seconds}
benchmark.total_seconds=${total_seconds}
payload=${benchmark_payload}
EOF
  local aggregate_path="$dir/${profile_mode}.aggregate.tsv"
  cat >"$aggregate_path" <<EOF
case_id	aggregate_tsv	workload_id	benchmark_source	profile_mode	profile_sample_log2	profile_sample_rate	candidate_index_mean_seconds	sim_seconds_mean_seconds	total_seconds_mean_seconds	terminal_path_parent_seconds	terminal_first_half_parent_seconds	terminal_first_half_span_a_seconds	terminal_first_half_span_b_seconds	terminal_first_half_unexplained_seconds	terminal_first_half_span_a_parent_seconds	terminal_first_half_span_a0_seconds	terminal_first_half_span_a1_seconds	terminal_first_half_span_a_child_known_seconds	terminal_first_half_span_a_unexplained_seconds	terminal_first_half_span_a0_parent_seconds	terminal_first_half_span_a0_gap_before_a00_seconds	terminal_first_half_span_a00_seconds	terminal_first_half_span_a0_gap_between_a00_a01_seconds	terminal_first_half_span_a01_seconds	terminal_first_half_span_a0_gap_after_a01_seconds	terminal_first_half_span_a0_child_known_seconds	terminal_first_half_span_a0_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_seconds	terminal_first_half_span_a0_gap_before_a00_span_1_seconds	terminal_first_half_span_a0_gap_before_a00_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds	dominant_terminal_first_half_span_a_child	dominant_terminal_first_half_span_a0_child	dominant_terminal_first_half_span_a0_gap_before_a00_child	dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child	dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child	terminal_first_half_span_a0_sampled_event_count	terminal_first_half_span_a0_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_1_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count	terminal_first_half_span_a00_sampled_event_count	terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count	terminal_first_half_span_a01_sampled_event_count	terminal_first_half_span_a0_gap_after_a01_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count	terminal_first_half_span_a0_unclassified_sampled_event_count	terminal_first_half_span_a0_multi_child_sampled_event_count	terminal_first_half_span_a0_overlap_sampled_event_count	timer_call_count	benchmark_source_original_path	benchmark_source_copied_path	benchmark_source_sha256	benchmark_source_size_bytes	benchmark_identity_basis
case-00000028	$aggregate_path	${workload_id}	${benchmark_source}	${profile_mode}	${profile_sample_log2}	${profile_sample_rate}	${candidate_index_seconds}	${sim_seconds}	${total_seconds}	${terminal_parent_seconds}	${first_half_parent_seconds}	${first_half_span_a_seconds}	${first_half_span_b_seconds}	${first_half_unexplained_seconds}	${span_a_parent_seconds}	${span_a0_seconds}	${span_a1_seconds}	${span_a_child_known_seconds}	${span_a_unexplained_seconds}	${span_a0_parent_seconds}	${span_a0_gap_before_a00_seconds}	${span_a00_seconds}	${span_a0_gap_between_a00_a01_seconds}	${span_a01_seconds}	${span_a0_gap_after_a01_seconds}	${span_a0_child_known_seconds}	${span_a0_unexplained_seconds}	${gap_before_a00_parent_seconds}	${gap_before_a00_span_0_seconds}	${gap_before_a00_span_1_seconds}	${gap_before_a00_child_known_seconds}	${gap_before_a00_unexplained_seconds}	${gap_before_a00_span_0_parent_seconds}	${gap_before_a00_span_0_child_0_seconds}	${gap_before_a00_span_0_child_1_seconds}	${gap_before_a00_span_0_child_known_seconds}	${gap_before_a00_span_0_unexplained_seconds}	${gap_before_a00_span_0_alt_parent_seconds}	${gap_before_a00_span_0_alt_left_seconds}	${gap_before_a00_span_0_alt_right_seconds}	${gap_before_a00_span_0_alt_child_known_seconds}	${gap_before_a00_span_0_alt_unexplained_seconds}	${dominant_span_a_child}	${dominant_span_a0_child}	${dominant_gap_before_a00_child}	${dominant_gap_before_a00_span_0_child}	${dominant_gap_before_a00_span_0_alt_child}	${span_a0_sampled_event_count}	${span_a0_covered_sampled_event_count}	${span_a0_gap_before_a00_sampled_event_count}	${gap_before_a00_covered_sampled_event_count}	${gap_before_a00_span_0_sampled_event_count}	${gap_before_a00_span_1_sampled_event_count}	${gap_before_a00_span_0_covered_sampled_event_count}	${gap_before_a00_span_0_child_0_sampled_event_count}	${gap_before_a00_span_0_child_1_sampled_event_count}	${gap_before_a00_span_0_alt_sampled_event_count}	${gap_before_a00_span_0_alt_covered_sampled_event_count}	${gap_before_a00_span_0_alt_left_sampled_event_count}	${gap_before_a00_span_0_alt_right_sampled_event_count}	${span_a00_sampled_event_count}	${span_a0_gap_between_a00_a01_sampled_event_count}	${span_a01_sampled_event_count}	${span_a0_gap_after_a01_sampled_event_count}	${gap_before_a00_unclassified_sampled_event_count}	${gap_before_a00_multi_child_sampled_event_count}	${gap_before_a00_span_0_unclassified_sampled_event_count}	${gap_before_a00_span_0_multi_child_sampled_event_count}	${gap_before_a00_span_0_alt_unclassified_sampled_event_count}	${gap_before_a00_span_0_alt_multi_child_sampled_event_count}	${span_a0_unclassified_sampled_event_count}	${span_a0_multi_child_sampled_event_count}	${span_a0_overlap_sampled_event_count}	${timer_call_count}	${benchmark_source}	${benchmark_source}	$(sha256sum "$benchmark_source" | awk '{print $1}')	$(wc -c <"$benchmark_source" | tr -d '[:space:]')	content_sha256
EOF
  cat >"$dir/candidate_index_lifecycle_cases.tsv" <<EOF
case_id	aggregate_tsv	workload_id	benchmark_source	profile_mode	candidate_index_mean_seconds	candidate_index_share_of_initial_cpu_merge	candidate_index_share_of_sim_seconds	candidate_index_share_of_total_seconds	sim_seconds_mean_seconds	total_seconds_mean_seconds	terminal_path_parent_seconds	terminal_first_half_parent_seconds	terminal_first_half_span_a_seconds	terminal_first_half_span_b_seconds	terminal_first_half_child_known_seconds	terminal_first_half_unexplained_seconds	terminal_first_half_span_a_parent_seconds	terminal_first_half_span_a0_seconds	terminal_first_half_span_a1_seconds	terminal_first_half_span_a_child_known_seconds	terminal_first_half_span_a_unexplained_seconds	terminal_first_half_span_a0_parent_seconds	terminal_first_half_span_a0_gap_before_a00_seconds	terminal_first_half_span_a00_seconds	terminal_first_half_span_a0_gap_between_a00_a01_seconds	terminal_first_half_span_a01_seconds	terminal_first_half_span_a0_gap_after_a01_seconds	terminal_first_half_span_a0_child_known_seconds	terminal_first_half_span_a0_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_seconds	terminal_first_half_span_a0_gap_before_a00_span_1_seconds	terminal_first_half_span_a0_gap_before_a00_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_seconds	terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds	dominant_terminal_first_half_span_a_child	dominant_terminal_first_half_span_a0_child	dominant_terminal_first_half_span_a0_gap_before_a00_child	dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child	dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child	terminal_first_half_span_a0_sampled_event_count	terminal_first_half_span_a0_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_1_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count	terminal_first_half_span_a00_sampled_event_count	terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count	terminal_first_half_span_a01_sampled_event_count	terminal_first_half_span_a0_gap_after_a01_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count	terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count	terminal_first_half_span_a0_unclassified_sampled_event_count	terminal_first_half_span_a0_multi_child_sampled_event_count	terminal_first_half_span_a0_overlap_sampled_event_count	terminal_path_dominant_child	dominant_terminal_span	dominant_terminal_first_half_span	timer_call_count	terminal_timer_call_count	lexical_timer_call_count	recommended_next_action	materiality_status
case-00000028	${aggregate_path}	${workload_id}	${benchmark_source}	${profile_mode}	${candidate_index_seconds}	0.96	0.64	0.63	${sim_seconds}	${total_seconds}	${terminal_parent_seconds}	${first_half_parent_seconds}	${first_half_span_a_seconds}	${first_half_span_b_seconds}	$(python3 - <<PY
print(float("${first_half_span_a_seconds}") + float("${first_half_span_b_seconds}"))
PY
)	${first_half_unexplained_seconds}	${span_a_parent_seconds}	${span_a0_seconds}	${span_a1_seconds}	${span_a_child_known_seconds}	${span_a_unexplained_seconds}	${span_a0_parent_seconds}	${span_a0_gap_before_a00_seconds}	${span_a00_seconds}	${span_a0_gap_between_a00_a01_seconds}	${span_a01_seconds}	${span_a0_gap_after_a01_seconds}	${span_a0_child_known_seconds}	${span_a0_unexplained_seconds}	${gap_before_a00_parent_seconds}	${gap_before_a00_span_0_seconds}	${gap_before_a00_span_1_seconds}	${gap_before_a00_child_known_seconds}	${gap_before_a00_unexplained_seconds}	${gap_before_a00_span_0_parent_seconds}	${gap_before_a00_span_0_child_0_seconds}	${gap_before_a00_span_0_child_1_seconds}	${gap_before_a00_span_0_child_known_seconds}	${gap_before_a00_span_0_unexplained_seconds}	${gap_before_a00_span_0_alt_parent_seconds}	${gap_before_a00_span_0_alt_left_seconds}	${gap_before_a00_span_0_alt_right_seconds}	${gap_before_a00_span_0_alt_child_known_seconds}	${gap_before_a00_span_0_alt_unexplained_seconds}	${dominant_span_a_child}	${dominant_span_a0_child}	${dominant_gap_before_a00_child}	${dominant_gap_before_a00_span_0_child}	${dominant_gap_before_a00_span_0_alt_child}	${span_a0_sampled_event_count}	${span_a0_covered_sampled_event_count}	${span_a0_gap_before_a00_sampled_event_count}	${gap_before_a00_covered_sampled_event_count}	${gap_before_a00_span_0_sampled_event_count}	${gap_before_a00_span_1_sampled_event_count}	${gap_before_a00_span_0_covered_sampled_event_count}	${gap_before_a00_span_0_child_0_sampled_event_count}	${gap_before_a00_span_0_child_1_sampled_event_count}	${gap_before_a00_span_0_alt_sampled_event_count}	${gap_before_a00_span_0_alt_covered_sampled_event_count}	${gap_before_a00_span_0_alt_left_sampled_event_count}	${gap_before_a00_span_0_alt_right_sampled_event_count}	${span_a00_sampled_event_count}	${span_a0_gap_between_a00_a01_sampled_event_count}	${span_a01_sampled_event_count}	${span_a0_gap_after_a01_sampled_event_count}	${gap_before_a00_unclassified_sampled_event_count}	${gap_before_a00_multi_child_sampled_event_count}	${gap_before_a00_span_0_unclassified_sampled_event_count}	${gap_before_a00_span_0_multi_child_sampled_event_count}	${gap_before_a00_span_0_alt_unclassified_sampled_event_count}	${gap_before_a00_span_0_alt_multi_child_sampled_event_count}	${span_a0_unclassified_sampled_event_count}	${span_a0_multi_child_sampled_event_count}	${span_a0_overlap_sampled_event_count}	residual	first_half	${dominant_span}	${timer_call_count}	${terminal_timer_call_count}	${lexical_timer_call_count}	run_profile_mode_ab	known
EOF

  cat >"$dir/candidate_index_lifecycle_summary.json" <<EOF
{
  "decision_status": "ready",
  "materiality_pairing_status": "${pairing_status}",
  "candidate_index_materiality_status": "material",
  "runtime_prototype_allowed": false,
  "candidate_index": {
    "seconds": ${candidate_index_seconds},
    "share_of_sim_seconds": 0.64,
    "share_of_total_seconds": 0.63,
    "terminal_path_parent_seconds": ${terminal_parent_seconds},
    "terminal_path_dominant_child": "residual",
    "terminal_first_half_parent_seconds": ${first_half_parent_seconds},
    "terminal_first_half_span_a_seconds": ${first_half_span_a_seconds},
    "terminal_first_half_span_b_seconds": ${first_half_span_b_seconds},
    "terminal_first_half_span_a_parent_seconds": ${span_a_parent_seconds},
    "terminal_first_half_span_a0_seconds": ${span_a0_seconds},
    "terminal_first_half_span_a1_seconds": ${span_a1_seconds},
    "terminal_first_half_span_a_child_known_seconds": ${span_a_child_known_seconds},
    "terminal_first_half_span_a_unexplained_seconds": ${span_a_unexplained_seconds},
    "terminal_first_half_span_a0_parent_seconds": ${span_a0_parent_seconds},
    "terminal_first_half_span_a0_gap_before_a00_seconds": ${span_a0_gap_before_a00_seconds},
    "terminal_first_half_span_a0_gap_before_a00_parent_seconds": ${gap_before_a00_parent_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_seconds": ${gap_before_a00_span_0_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_1_seconds": ${gap_before_a00_span_1_seconds},
    "terminal_first_half_span_a0_gap_before_a00_child_known_seconds": ${gap_before_a00_child_known_seconds},
    "terminal_first_half_span_a0_gap_before_a00_unexplained_seconds": ${gap_before_a00_unexplained_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds": ${gap_before_a00_span_0_parent_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds": ${gap_before_a00_span_0_child_0_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds": ${gap_before_a00_span_0_child_1_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds": ${gap_before_a00_span_0_child_known_seconds},
    "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds": ${gap_before_a00_span_0_unexplained_seconds},
    "terminal_first_half_span_a00_seconds": ${span_a00_seconds},
    "terminal_first_half_span_a0_gap_between_a00_a01_seconds": ${span_a0_gap_between_a00_a01_seconds},
    "terminal_first_half_span_a01_seconds": ${span_a01_seconds},
    "terminal_first_half_span_a0_gap_after_a01_seconds": ${span_a0_gap_after_a01_seconds},
    "terminal_first_half_span_a0_child_known_seconds": ${span_a0_child_known_seconds},
    "terminal_first_half_span_a0_unexplained_seconds": ${span_a0_unexplained_seconds},
    "dominant_terminal_span": "first_half",
    "dominant_terminal_first_half_span": "${dominant_span}",
    "dominant_terminal_first_half_span_a_child": "${dominant_span_a_child}",
    "dominant_terminal_first_half_span_a0_child": "${dominant_span_a0_child}",
    "dominant_terminal_first_half_span_a0_gap_before_a00_child": "${dominant_gap_before_a00_child}",
    "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child": "${dominant_gap_before_a00_span_0_child}",
    "terminal_first_half_span_a0_sampled_event_count": ${span_a0_sampled_event_count},
    "terminal_first_half_span_a0_covered_sampled_event_count": ${span_a0_covered_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_sampled_event_count": ${span_a0_gap_before_a00_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count": ${gap_before_a00_covered_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count": ${gap_before_a00_span_0_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_1_sampled_event_count": ${gap_before_a00_span_1_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count": ${gap_before_a00_span_0_covered_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count": ${gap_before_a00_span_0_child_0_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count": ${gap_before_a00_span_0_child_1_sampled_event_count},
    "terminal_first_half_span_a00_sampled_event_count": ${span_a00_sampled_event_count},
    "terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count": ${span_a0_gap_between_a00_a01_sampled_event_count},
    "terminal_first_half_span_a01_sampled_event_count": ${span_a01_sampled_event_count},
    "terminal_first_half_span_a0_gap_after_a01_sampled_event_count": ${span_a0_gap_after_a01_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count": ${gap_before_a00_unclassified_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count": ${gap_before_a00_multi_child_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count": ${gap_before_a00_span_0_unclassified_sampled_event_count},
    "terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count": ${gap_before_a00_span_0_multi_child_sampled_event_count},
    "terminal_first_half_span_a0_unclassified_sampled_event_count": ${span_a0_unclassified_sampled_event_count},
    "terminal_first_half_span_a0_multi_child_sampled_event_count": ${span_a0_multi_child_sampled_event_count},
    "terminal_first_half_span_a0_overlap_sampled_event_count": ${span_a0_overlap_sampled_event_count},
    "timer_call_count": ${timer_call_count},
    "terminal_timer_call_count": ${terminal_timer_call_count},
    "lexical_timer_call_count": ${lexical_timer_call_count}
  }
}
EOF
}

run_and_assert() {
  local output_dir="$1"
  local coarse_dir="$2"
  local terminal_dir="$3"
  local lexical_dir="$4"
  python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
    --coarse-dir "$coarse_dir" \
    --terminal-dir "$terminal_dir" \
    --lexical-first-half-dir "$lexical_dir" \
    --output-dir "$output_dir"
}

assert_decision() {
  local output_dir="$1"
  local expected_status="$2"
  local expected_action="$3"
  local expected_overhead="$4"
  local expected_scope="$5"
  python3 - "$output_dir" "$expected_status" "$expected_action" "$expected_overhead" "$expected_scope" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_status = sys.argv[2]
expected_action = sys.argv[3]
expected_overhead = sys.argv[4]
expected_scope = sys.argv[5]
summary = json.loads((output_dir / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
decision = json.loads((output_dir / "profile_mode_ab_decision.json").read_text(encoding="utf-8"))
assert summary["decision_status"] == expected_status, summary
assert decision["decision_status"] == expected_status, decision
assert summary["recommended_next_action"] == expected_action, summary
assert decision["recommended_next_action"] == expected_action, decision
assert summary["profile_mode_overhead_status"] == expected_overhead, summary
assert decision["profile_mode_overhead_status"] == expected_overhead, decision
assert summary["benchmark_scope"] == expected_scope, summary
assert decision["benchmark_scope"] == expected_scope, decision
assert summary["runtime_prototype_allowed"] is False, summary
assert decision["runtime_prototype_allowed"] is False, decision
PY
}

assert_null_first_half_ratio() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
assert summary["terminal_first_half_parent_seconds_ratio_lexical_vs_terminal"] is None, summary
PY
}

assert_low_overhead_decision() {
  local output_dir="$1"
  local expected_action="$2"
  local expected_overhead="$3"
  local expected_trusted="$4"
  python3 - "$output_dir" "$expected_action" "$expected_overhead" "$expected_trusted" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
decision = json.loads((Path(sys.argv[1]) / "profile_mode_ab_decision.json").read_text(encoding="utf-8"))
expected_action = sys.argv[2]
expected_overhead = sys.argv[3]
expected_trusted = (sys.argv[4] == "true")
assert summary["recommended_next_action"] == expected_action, summary
assert decision["recommended_next_action"] == expected_action, decision
assert summary["profile_mode_overhead_status"] == expected_overhead, summary
assert decision["profile_mode_overhead_status"] == expected_overhead, decision
assert summary["trusted_span_timing"] is expected_trusted, summary
assert decision["trusted_span_timing"] is expected_trusted, decision
assert "sampled_count_closure_status" in summary, summary
assert "sampled_count_closure_status" in decision, decision
PY
}

assert_materiality_mirror() {
  local output_dir="$1"
  local expected_status="${2:-material}"
  local expected_match="${3:-true}"
  python3 - "$output_dir" "$expected_status" "$expected_match" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
decision = json.loads((Path(sys.argv[1]) / "profile_mode_ab_decision.json").read_text(encoding="utf-8"))
expected_status = sys.argv[2]
expected_match = (sys.argv[3] == "true")
assert summary["candidate_index_materiality_status"] == expected_status, summary
assert decision["candidate_index_materiality_status"] == expected_status, decision
assert summary["materiality_status_all_modes_match"] is expected_match, summary
assert decision["materiality_status_all_modes_match"] is expected_match, decision
PY
}

assert_case_field_populated() {
  local output_dir="$1"
  local field="$2"
  python3 - "$output_dir" "$field" <<'PY'
import csv
import sys
from pathlib import Path

cases_path = Path(sys.argv[1]) / "profile_mode_ab_cases.tsv"
field = sys.argv[2]
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = reader.fieldnames or []
    rows = list(reader)
if field not in fieldnames:
    raise SystemExit(f"{cases_path}: missing field {field}")
if not rows:
    raise SystemExit(f"{cases_path}: no rows")
for row in rows:
    if row.get(field, "") == "":
        raise SystemExit(f"{cases_path}: empty field {field} for case {row.get('case_id')}")
PY
}

assert_sampled_count_closure_status() {
  local output_dir="$1"
  local expected_status="$2"
  python3 - "$output_dir" "$expected_status" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
decision = json.loads((Path(sys.argv[1]) / "profile_mode_ab_decision.json").read_text(encoding="utf-8"))
expected_status = sys.argv[2]
assert summary["sampled_count_closure_status"] == expected_status, summary
assert decision["sampled_count_closure_status"] == expected_status, decision
PY
}

assert_summary_decision_field() {
  local output_dir="$1"
  local field="$2"
  local expected_value="$3"
  python3 - "$output_dir" "$field" "$expected_value" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "profile_mode_ab_summary.json").read_text(encoding="utf-8"))
decision = json.loads((Path(sys.argv[1]) / "profile_mode_ab_decision.json").read_text(encoding="utf-8"))
field = sys.argv[2]
expected = sys.argv[3]

summary_value = summary.get(field, None)
decision_value = decision.get(field, None)
assert summary_value is not None, (field, summary)
assert decision_value is not None, (field, decision)
assert str(summary_value) == expected, (field, summary_value, expected)
assert str(decision_value) == expected, (field, decision_value, expected)
PY
}

duplicate_artifact_cases() {
  local dir="$1"
  shift
  python3 - "$dir" "$@" <<'PY'
import csv
import sys
from pathlib import Path

dir_path = Path(sys.argv[1])
case_ids = sys.argv[2:]
cases_path = dir_path / "candidate_index_lifecycle_cases.tsv"
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = reader.fieldnames
    rows = list(reader)
if not rows:
    raise SystemExit(f"no template rows in {cases_path}")
base_row = rows[0]
aggregate_path = Path(base_row["aggregate_tsv"])
with aggregate_path.open(newline="", encoding="utf-8") as handle:
    aggregate_reader = csv.DictReader(handle, delimiter="\t")
    aggregate_fieldnames = aggregate_reader.fieldnames
    aggregate_rows = list(aggregate_reader)
if not aggregate_rows:
    raise SystemExit(f"no template aggregate row in {aggregate_path}")
base_aggregate = aggregate_rows[0]

new_rows = []
for case_id in case_ids:
    aggregate_copy_path = dir_path / f"{case_id}.{aggregate_path.name}"
    aggregate_copy = dict(base_aggregate)
    aggregate_copy["case_id"] = case_id
    aggregate_copy["aggregate_tsv"] = str(aggregate_copy_path)
    with aggregate_copy_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow(aggregate_copy)
    row = dict(base_row)
    row["case_id"] = case_id
    row["aggregate_tsv"] = str(aggregate_copy_path)
    new_rows.append(row)

with cases_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(new_rows)
PY
}

rewrite_sampled_span0_conflict_cases() {
  local dir="$1"
  local variant="${2:-low_margin}"
  python3 - "$dir" "$variant" <<'PY'
import csv
import sys
from pathlib import Path

dir_path = Path(sys.argv[1])
variant = sys.argv[2]
cases_path = dir_path / "candidate_index_lifecycle_cases.tsv"
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = reader.fieldnames
    rows = list(reader)
if len(rows) != 3:
    raise SystemExit(f"expected 3 rows in {cases_path}, found {len(rows)}")

if variant == "low_margin":
    specs = {
        "case-00000028": ("child_0", 0.10, 0.0506, 0.0494),
        "case-00000039": ("child_0", 0.10, 0.0506, 0.0494),
        "case-00000040": ("child_1", 0.10, 0.0485, 0.0515),
    }
elif variant == "wide_margin":
    specs = {
        "case-00000028": ("child_0", 0.10, 0.0700, 0.0300),
        "case-00000039": ("child_0", 0.10, 0.0700, 0.0300),
        "case-00000040": ("child_1", 0.14, 0.0200, 0.1200),
    }
else:
    raise SystemExit(f"unknown conflict variant: {variant}")

for row in rows:
    dominant, parent, child_0, child_1 = specs[row["case_id"]]
    row["terminal_first_half_span_a0_gap_before_a00_span_0_seconds"] = f"{parent:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds"] = f"{parent:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds"] = f"{child_0:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds"] = f"{child_1:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds"] = f"{child_0 + child_1:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds"] = "0.0"
    row["dominant_terminal_first_half_span_a0_gap_before_a00_child"] = "span_0"
    row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child"] = dominant
    row["terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count"] = "0"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count"] = "100"

    aggregate_path = Path(row["aggregate_tsv"])
    with aggregate_path.open(newline="", encoding="utf-8") as handle:
        aggregate_reader = csv.DictReader(handle, delimiter="\t")
        aggregate_fieldnames = aggregate_reader.fieldnames
        aggregate_rows = list(aggregate_reader)
    if len(aggregate_rows) != 1:
        raise SystemExit(f"expected 1 aggregate row in {aggregate_path}, found {len(aggregate_rows)}")
    aggregate_row = aggregate_rows[0]
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_seconds"] = f"{parent:.6f}"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds"] = f"{parent:.6f}"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds"] = f"{child_0:.6f}"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds"] = f"{child_1:.6f}"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds"] = f"{child_0 + child_1:.6f}"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds"] = "0.0"
    aggregate_row["dominant_terminal_first_half_span_a0_gap_before_a00_child"] = "span_0"
    aggregate_row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child"] = dominant
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count"] = "0"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count"] = "100"
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(aggregate_rows)

with cases_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
PY
}

rewrite_sampled_span0_alt_cases() {
  local dir="$1"
  local variant="${2:-stable_left}"
  python3 - "$dir" "$variant" <<'PY'
import csv
import sys
from pathlib import Path

dir_path = Path(sys.argv[1])
variant = sys.argv[2]
cases_path = dir_path / "candidate_index_lifecycle_cases.tsv"
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = reader.fieldnames
    rows = list(reader)
if len(rows) != 3:
    raise SystemExit(f"expected 3 rows in {cases_path}, found {len(rows)}")

if variant == "stable_left":
    specs = {
        "case-00000028": ("alt_left", 0.10, 0.072, 0.028),
        "case-00000039": ("alt_left", 0.10, 0.071, 0.029),
        "case-00000040": ("alt_left", 0.10, 0.073, 0.027),
    }
elif variant == "stable_right":
    specs = {
        "case-00000028": ("alt_right", 0.10, 0.028, 0.072),
        "case-00000039": ("alt_right", 0.10, 0.029, 0.071),
        "case-00000040": ("alt_right", 0.10, 0.027, 0.073),
    }
elif variant == "low_margin_conflict":
    specs = {
        "case-00000028": ("alt_left", 0.10, 0.0506, 0.0494),
        "case-00000039": ("alt_left", 0.10, 0.0506, 0.0494),
        "case-00000040": ("alt_right", 0.10, 0.0494, 0.0506),
    }
else:
    raise SystemExit(f"unknown alt variant: {variant}")

for row in rows:
    dominant, parent, alt_left, alt_right = specs[row["case_id"]]
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds"] = f"{parent:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds"] = f"{alt_left:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds"] = f"{alt_right:.6f}"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_seconds"] = (
        f"{alt_left + alt_right:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds"] = "0.0"
    row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child"] = dominant
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count"] = "0"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count"] = "100"

    aggregate_path = Path(row["aggregate_tsv"])
    with aggregate_path.open(newline="", encoding="utf-8") as handle:
        aggregate_reader = csv.DictReader(handle, delimiter="\t")
        aggregate_fieldnames = aggregate_reader.fieldnames
        aggregate_rows = list(aggregate_reader)
    if len(aggregate_rows) != 1:
        raise SystemExit(f"expected 1 aggregate row in {aggregate_path}, found {len(aggregate_rows)}")
    aggregate_row = aggregate_rows[0]
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds"] = (
        f"{parent:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds"] = (
        f"{alt_left:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds"] = (
        f"{alt_right:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_seconds"] = (
        f"{alt_left + alt_right:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds"] = "0.0"
    aggregate_row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child"] = dominant
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count"] = "0"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count"] = "100"
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(aggregate_rows)

with cases_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
PY
}

rewrite_sampled_span0_alt_right_cases() {
  local dir="$1"
  local variant="${2:-stable_child_0}"
  python3 - "$dir" "$variant" <<'PY'
import csv
import sys
from pathlib import Path

dir_path = Path(sys.argv[1])
variant = sys.argv[2]
cases_path = dir_path / "candidate_index_lifecycle_cases.tsv"
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
if len(rows) != 3:
    raise SystemExit(f"expected 3 rows in {cases_path}, found {len(rows)}")

new_fields = [
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_seconds",
    "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
]
for field in new_fields:
    if field not in fieldnames:
        fieldnames.append(field)

if variant == "stable_child_0":
    specs = {
        "case-00000028": ("child_0", 0.072, 0.046, 0.026),
        "case-00000039": ("child_0", 0.071, 0.045, 0.026),
        "case-00000040": ("child_0", 0.073, 0.047, 0.026),
    }
elif variant == "stable_child_1":
    specs = {
        "case-00000028": ("child_1", 0.072, 0.026, 0.046),
        "case-00000039": ("child_1", 0.071, 0.026, 0.045),
        "case-00000040": ("child_1", 0.073, 0.026, 0.047),
    }
elif variant == "low_margin_conflict":
    specs = {
        "case-00000028": ("child_0", 0.072, 0.0363, 0.0357),
        "case-00000039": ("child_0", 0.071, 0.0358, 0.0352),
        "case-00000040": ("child_1", 0.073, 0.0361, 0.0369),
    }
elif variant == "near_tie":
    specs = {
        "case-00000028": ("child_0", 0.072, 0.0365, 0.0355),
        "case-00000039": ("child_0", 0.071, 0.0360, 0.0350),
        "case-00000040": ("child_0", 0.073, 0.0370, 0.0360),
    }
elif variant == "stale_label_seconds_favor_child_0":
    specs = {
        "case-00000028": ("child_1", 0.072, 0.0460, 0.0260),
        "case-00000039": ("child_1", 0.071, 0.0450, 0.0260),
        "case-00000040": ("child_1", 0.073, 0.0470, 0.0260),
    }
else:
    raise SystemExit(f"unknown alt_right variant: {variant}")

for row in rows:
    dominant, parent, child_0, child_1 = specs[row["case_id"]]
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds"] = (
        f"{parent:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds"] = (
        f"{child_0:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds"] = (
        f"{child_1:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_seconds"] = (
        f"{child_0 + child_1:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_seconds"] = "0.0"
    row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child"] = dominant
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count"] = "100"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count"] = "0"
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count"] = "100"

    aggregate_path = Path(row["aggregate_tsv"])
    with aggregate_path.open(newline="", encoding="utf-8") as handle:
        aggregate_reader = csv.DictReader(handle, delimiter="\t")
        aggregate_fieldnames = list(aggregate_reader.fieldnames or [])
        aggregate_rows = list(aggregate_reader)
    if len(aggregate_rows) != 1:
        raise SystemExit(f"expected 1 aggregate row in {aggregate_path}, found {len(aggregate_rows)}")
    for field in new_fields:
        if field not in aggregate_fieldnames:
            aggregate_fieldnames.append(field)
    aggregate_row = aggregate_rows[0]
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds"] = (
        f"{parent:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds"] = (
        f"{child_0:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds"] = (
        f"{child_1:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_seconds"] = (
        f"{child_0 + child_1:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_seconds"] = "0.0"
    aggregate_row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child"] = dominant
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count"] = "100"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count"] = "0"
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count"] = "100"
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(aggregate_rows)

with cases_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
PY
}

rewrite_sampled_span0_alt_right_repart_cases() {
  local dir="$1"
  local variant="${2:-stable_left}"
  python3 - "$dir" "$variant" <<'PY'
import csv
import sys
from pathlib import Path

dir_path = Path(sys.argv[1])
variant = sys.argv[2]
cases_path = dir_path / "candidate_index_lifecycle_cases.tsv"
with cases_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
if len(rows) != 3:
    raise SystemExit(f"expected 3 rows in {cases_path}, found {len(rows)}")

new_fields = [
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_seconds",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds",
    "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
]
for field in new_fields:
    if field not in fieldnames:
        fieldnames.append(field)

if variant == "stable_left":
    specs = {
        "case-00000028": ("repart_left", 0.090, 0.061, 0.029, "100", "100", "100", "100", "0", "100"),
        "case-00000039": ("repart_left", 0.089, 0.060, 0.029, "100", "100", "100", "100", "0", "100"),
        "case-00000040": ("repart_left", 0.091, 0.062, 0.029, "100", "100", "100", "100", "0", "100"),
    }
elif variant == "stable_right":
    specs = {
        "case-00000028": ("repart_right", 0.090, 0.028, 0.062, "100", "100", "100", "100", "0", "100"),
        "case-00000039": ("repart_right", 0.089, 0.028, 0.061, "100", "100", "100", "100", "0", "100"),
        "case-00000040": ("repart_right", 0.091, 0.029, 0.062, "100", "100", "100", "100", "0", "100"),
    }
elif variant == "near_tie":
    specs = {
        "case-00000028": ("repart_right", 0.090, 0.0448, 0.0452, "100", "100", "100", "100", "0", "100"),
        "case-00000039": ("repart_right", 0.089, 0.0444, 0.0446, "100", "100", "100", "100", "0", "100"),
        "case-00000040": ("repart_right", 0.091, 0.0453, 0.0457, "100", "100", "100", "100", "0", "100"),
    }
elif variant == "coverage_open":
    specs = {
        "case-00000028": ("repart_right", 0.090, 0.028, 0.062, "100", "0", "100", "100", "100", "0"),
        "case-00000039": ("repart_right", 0.089, 0.028, 0.061, "100", "0", "100", "100", "100", "0"),
        "case-00000040": ("repart_right", 0.091, 0.029, 0.062, "100", "0", "100", "100", "100", "0"),
    }
else:
    raise SystemExit(f"unknown alt_right_repart variant: {variant}")

for row in rows:
    (
        dominant,
        parent,
        left_seconds,
        right_seconds,
        parent_count,
        covered_count,
        left_count,
        right_count,
        unclassified_count,
        multi_child_count,
    ) = specs[row["case_id"]]
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds"] = (
        f"{parent:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds"] = (
        f"{left_seconds:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds"] = (
        f"{right_seconds:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_seconds"] = (
        f"{left_seconds + right_seconds:.6f}"
    )
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds"] = "0.0"
    row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child"] = dominant
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count"] = parent_count
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count"] = covered_count
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count"] = left_count
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count"] = right_count
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count"] = unclassified_count
    row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count"] = multi_child_count

    aggregate_path = Path(row["aggregate_tsv"])
    with aggregate_path.open(newline="", encoding="utf-8") as handle:
        aggregate_reader = csv.DictReader(handle, delimiter="\t")
        aggregate_fieldnames = list(aggregate_reader.fieldnames or [])
        aggregate_rows = list(aggregate_reader)
    if len(aggregate_rows) != 1:
        raise SystemExit(f"expected 1 aggregate row in {aggregate_path}, found {len(aggregate_rows)}")
    for field in new_fields:
        if field not in aggregate_fieldnames:
            aggregate_fieldnames.append(field)
    aggregate_row = aggregate_rows[0]
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds"] = (
        f"{parent:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds"] = (
        f"{left_seconds:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds"] = (
        f"{right_seconds:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_seconds"] = (
        f"{left_seconds + right_seconds:.6f}"
    )
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds"] = "0.0"
    aggregate_row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child"] = dominant
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count"] = parent_count
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count"] = covered_count
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count"] = left_count
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count"] = right_count
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count"] = unclassified_count
    aggregate_row["terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count"] = multi_child_count
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(aggregate_rows)

with cases_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
PY
}

COARSE="$WORK/coarse"
TERMINAL="$WORK/terminal"
LEXICAL_A="$WORK/lexical-a"
write_artifact "$COARSE" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-shared" "unknown" "complete" "/tmp/shared.stderr.log" "0.0" "shared-benchmark"
write_artifact "$TERMINAL" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-shared" "unknown" "complete" "/tmp/shared.stderr.log" "0.0" "shared-benchmark"
write_artifact "$LEXICAL_A" "lexical_first_half" "6.3" "4.0" "1.9" "1.2" "0.5" "9.0" "10.0" "560" "420" "140" "wl-shared" "span_a" "complete" "/tmp/shared.stderr.log" "0.0" "shared-benchmark"
run_and_assert "$WORK/out-a" "$COARSE" "$TERMINAL" "$LEXICAL_A"
assert_decision "$WORK/out-a" "ready" "split_terminal_first_half_span_a" "ok" "shared_workload"
assert_null_first_half_ratio "$WORK/out-a"

LEXICAL_B="$WORK/lexical-b"
write_artifact "$LEXICAL_B" "lexical_first_half" "6.3" "4.0" "1.9" "0.5" "1.2" "9.0" "10.0" "560" "420" "140" "wl-shared" "span_b" "complete" "/tmp/shared.stderr.log" "0.0" "shared-benchmark"
run_and_assert "$WORK/out-b" "$COARSE" "$TERMINAL" "$LEXICAL_B"
assert_decision "$WORK/out-b" "ready" "split_terminal_first_half_span_b" "ok" "shared_workload"

LEXICAL_SCOPE="$WORK/lexical-scope"
write_artifact "$LEXICAL_SCOPE" "lexical_first_half" "6.3" "4.0" "1.9" "1.0" "0.4" "9.0" "10.0" "560" "420" "140" "wl-shared" "span_a" "complete" "/tmp/shared.stderr.log" "0.5" "shared-benchmark"
run_and_assert "$WORK/out-scope" "$COARSE" "$TERMINAL" "$LEXICAL_SCOPE"
assert_decision "$WORK/out-scope" "ready" "inspect_first_half_timer_scope" "ok" "shared_workload"

COARSE_COPY="$WORK/coarse-copy"
TERMINAL_COPY="$WORK/terminal-copy"
LEXICAL_COPY="$WORK/lexical-copy"
write_artifact "$COARSE_COPY" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-shared-copy" "unknown" "complete" "$WORK/bench/coarse-copy.stderr.log" "0.0" "shared-copy-benchmark"
write_artifact "$TERMINAL_COPY" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-shared-copy" "unknown" "complete" "$WORK/bench/terminal-copy.stderr.log" "0.0" "shared-copy-benchmark"
write_artifact "$LEXICAL_COPY" "lexical_first_half" "6.3" "4.0" "1.9" "1.2" "0.5" "9.0" "10.0" "560" "420" "140" "wl-shared-copy" "span_a" "complete" "$WORK/bench/lexical-copy.stderr.log" "0.0" "shared-copy-benchmark"
run_and_assert "$WORK/out-copy-shared" "$COARSE_COPY" "$TERMINAL_COPY" "$LEXICAL_COPY"
assert_decision "$WORK/out-copy-shared" "ready" "split_terminal_first_half_span_a" "ok" "shared_workload"
assert_null_first_half_ratio "$WORK/out-copy-shared"

COARSE_PER="$WORK/coarse-per"
TERMINAL_PER="$WORK/terminal-per"
write_artifact "$COARSE_PER" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-shared" "unknown" "complete" "$WORK/bench/coarse.stderr.log" "0.0" "coarse-benchmark"
write_artifact "$TERMINAL_PER" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.1" "10.1" "420" "420" "0" "wl-shared" "unknown" "complete" "$WORK/bench/terminal.stderr.log" "0.0" "terminal-benchmark"

LEXICAL_SUSPECT="$WORK/lexical-suspect"
write_artifact "$LEXICAL_SUSPECT" "lexical_first_half" "7.2" "4.6" "2.3" "1.4" "0.7" "9.7" "10.7" "860" "520" "340" "wl-shared" "span_a" "complete" "$WORK/bench/lexical.stderr.log" "0.0" "lexical-benchmark"
run_and_assert "$WORK/out-suspect" "$COARSE_PER" "$TERMINAL_PER" "$LEXICAL_SUSPECT"
assert_decision "$WORK/out-suspect" "ready" "reduce_profiler_timer_overhead" "suspect" "per_profile_mode"

MISMATCH="$WORK/lexical-mismatch"
write_artifact "$MISMATCH" "lexical_first_half" "6.3" "4.0" "1.9" "1.2" "0.5" "9.0" "10.0" "560" "420" "140" "wl-other" "span_a"
run_and_assert "$WORK/out-mismatch" "$COARSE_PER" "$TERMINAL_PER" "$MISMATCH"
assert_decision "$WORK/out-mismatch" "not_ready" "fix_profile_mode_ab_inputs" "unknown" "unknown"

LOW_COARSE="$WORK/low-coarse"
LOW_TERMINAL="$WORK/low-terminal"
LOW_COUNT_ONLY="$WORK/low-count-only"
LOW_SAMPLED="$WORK/low-sampled"
write_artifact "$LOW_COARSE" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low" "unknown" "complete" "$WORK/bench/low-coarse.stderr.log" "0.0" "low-shared-benchmark"
write_artifact "$LOW_TERMINAL" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low" "unknown" "complete" "$WORK/bench/low-terminal.stderr.log" "0.0" "low-shared-benchmark"
write_artifact "$LOW_COUNT_ONLY" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low" "span_a" "complete" "$WORK/bench/low-count.stderr.log" "0.0" "low-shared-benchmark"
write_artifact "$LOW_SAMPLED" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low" "span_a" "complete" "$WORK/bench/low-sampled.stderr.log" "0.05" "low-shared-benchmark" "6" "0.015625" "0.70" "0.41" "0.22" "0.07" "span_a0"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE" \
  --terminal-dir "$LOW_TERMINAL" \
  --count-only-dir "$LOW_COUNT_ONLY" \
  --sampled-dir "$LOW_SAMPLED" \
  --output-dir "$WORK/out-low-ok"
assert_low_overhead_decision "$WORK/out-low-ok" "split_terminal_first_half_span_a0" "ok" "true"

LOW_SAMPLED_B="$WORK/low-sampled-b"
write_artifact "$LOW_SAMPLED_B" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-b" "span_a" "complete" "$WORK/bench/low-sampled-b.stderr.log" "0.05" "low-shared-benchmark-b" "6" "0.015625" "0.70" "0.18" "0.45" "0.07" "span_a1"
write_artifact "$LOW_COARSE-sampled-b" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-b" "unknown" "complete" "$WORK/bench/low-coarse-b.stderr.log" "0.0" "low-shared-benchmark-b"
write_artifact "$LOW_TERMINAL-sampled-b" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-b" "unknown" "complete" "$WORK/bench/low-terminal-b.stderr.log" "0.0" "low-shared-benchmark-b"
write_artifact "$LOW_COUNT_ONLY-sampled-b" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-b" "span_a" "complete" "$WORK/bench/low-count-b.stderr.log" "0.0" "low-shared-benchmark-b"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-sampled-b" \
  --terminal-dir "$LOW_TERMINAL-sampled-b" \
  --count-only-dir "$LOW_COUNT_ONLY-sampled-b" \
  --sampled-dir "$LOW_SAMPLED_B" \
  --output-dir "$WORK/out-low-span-a1"
assert_low_overhead_decision "$WORK/out-low-span-a1" "split_terminal_first_half_span_a1" "ok" "true"

LOW_SAMPLED_SCOPE="$WORK/low-sampled-scope"
write_artifact "$LOW_SAMPLED_SCOPE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-scope" "span_a" "complete" "$WORK/bench/low-sampled-scope.stderr.log" "0.05" "low-shared-benchmark-scope" "6" "0.015625" "0.70" "0.26" "0.23" "0.21" "span_a0"
write_artifact "$LOW_COARSE-scope" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-scope" "unknown" "complete" "$WORK/bench/low-coarse-scope.stderr.log" "0.0" "low-shared-benchmark-scope"
write_artifact "$LOW_TERMINAL-scope" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-scope" "unknown" "complete" "$WORK/bench/low-terminal-scope.stderr.log" "0.0" "low-shared-benchmark-scope"
write_artifact "$LOW_COUNT_ONLY-scope" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-scope" "span_a" "complete" "$WORK/bench/low-count-scope.stderr.log" "0.0" "low-shared-benchmark-scope"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-scope" \
  --terminal-dir "$LOW_TERMINAL-scope" \
  --count-only-dir "$LOW_COUNT_ONLY-scope" \
  --sampled-dir "$LOW_SAMPLED_SCOPE" \
  --output-dir "$WORK/out-low-scope"
assert_low_overhead_decision "$WORK/out-low-scope" "inspect_terminal_first_half_span_a_timer_scope" "ok" "true"

LOW_SAMPLED_A0="$WORK/low-sampled-a0"
write_artifact "$LOW_SAMPLED_A0" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0" "span_a" "complete" "$WORK/bench/low-sampled-a0.stderr.log" "0.05" "low-shared-benchmark-a0" "6" "0.015625" "0.70" "0.41" "0.22" "0.07" "span_a0" "0.41" "0.26" "0.11" "0.04" "span_a00" "0.00" "0.00" "0.00" "5" "5" "5" "5" "5" "5" "5" "0" "5" "0"
write_artifact "$LOW_COARSE-a0" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0" "unknown" "complete" "$WORK/bench/low-coarse-a0.stderr.log" "0.0" "low-shared-benchmark-a0"
write_artifact "$LOW_TERMINAL-a0" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0" "unknown" "complete" "$WORK/bench/low-terminal-a0.stderr.log" "0.0" "low-shared-benchmark-a0"
write_artifact "$LOW_COUNT_ONLY-a0" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0" "span_a" "complete" "$WORK/bench/low-count-a0.stderr.log" "0.0" "low-shared-benchmark-a0"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0" \
  --terminal-dir "$LOW_TERMINAL-a0" \
  --count-only-dir "$LOW_COUNT_ONLY-a0" \
  --sampled-dir "$LOW_SAMPLED_A0" \
  --output-dir "$WORK/out-low-span-a00"
assert_low_overhead_decision "$WORK/out-low-span-a00" "split_terminal_first_half_span_a00" "ok" "true"

LOW_SAMPLED_A0_B="$WORK/low-sampled-a0-b"
write_artifact "$LOW_SAMPLED_A0_B" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-b" "span_a" "complete" "$WORK/bench/low-sampled-a0-b.stderr.log" "0.05" "low-shared-benchmark-a0-b" "6" "0.015625" "0.70" "0.41" "0.22" "0.07" "span_a0" "0.41" "0.11" "0.26" "0.04" "span_a01" "0.00" "0.00" "0.00" "5" "5" "5" "5" "5" "5" "5" "0" "5" "0"
write_artifact "$LOW_COARSE-a0-b" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-b" "unknown" "complete" "$WORK/bench/low-coarse-a0-b.stderr.log" "0.0" "low-shared-benchmark-a0-b"
write_artifact "$LOW_TERMINAL-a0-b" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-b" "unknown" "complete" "$WORK/bench/low-terminal-a0-b.stderr.log" "0.0" "low-shared-benchmark-a0-b"
write_artifact "$LOW_COUNT_ONLY-a0-b" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-b" "span_a" "complete" "$WORK/bench/low-count-a0-b.stderr.log" "0.0" "low-shared-benchmark-a0-b"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-b" \
  --terminal-dir "$LOW_TERMINAL-a0-b" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-b" \
  --sampled-dir "$LOW_SAMPLED_A0_B" \
  --output-dir "$WORK/out-low-span-a01"
assert_low_overhead_decision "$WORK/out-low-span-a01" "split_terminal_first_half_span_a01" "ok" "true"

LOW_SAMPLED_A0_SCOPE="$WORK/low-sampled-a0-scope"
write_artifact "$LOW_SAMPLED_A0_SCOPE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-scope" "span_a" "complete" "$WORK/bench/low-sampled-a0-scope.stderr.log" "0.05" "low-shared-benchmark-a0-scope" "6" "0.015625" "0.70" "0.41" "0.12" "0.11" "span_a0" "0.41" "0.00" "0.00" "0.21" "span_a00" "0.00" "0.00" "0.00" "5" "5" "5" "5" "5" "5" "5" "0" "5" "0"
write_artifact "$LOW_COARSE-a0-scope" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-scope" "unknown" "complete" "$WORK/bench/low-coarse-a0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-scope"
write_artifact "$LOW_TERMINAL-a0-scope" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-scope" "unknown" "complete" "$WORK/bench/low-terminal-a0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-scope"
write_artifact "$LOW_COUNT_ONLY-a0-scope" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-scope" "span_a" "complete" "$WORK/bench/low-count-a0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-scope"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-scope" \
  --terminal-dir "$LOW_TERMINAL-a0-scope" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-scope" \
  --sampled-dir "$LOW_SAMPLED_A0_SCOPE" \
  --output-dir "$WORK/out-low-a0-scope"
assert_low_overhead_decision "$WORK/out-low-a0-scope" "inspect_terminal_first_half_span_a0_timer_scope" "ok" "true"

LOW_SAMPLED_A0_GAP="$WORK/low-sampled-a0-gap"
write_artifact "$LOW_SAMPLED_A0_GAP" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap.stderr.log" "0.05" "low-shared-benchmark-a0-gap" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "5" "5" "5" "5" "5" "5" "5" "0" "5" "0"
write_artifact "$LOW_COARSE-a0-gap" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap.stderr.log" "0.0" "low-shared-benchmark-a0-gap"
write_artifact "$LOW_TERMINAL-a0-gap" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap.stderr.log" "0.0" "low-shared-benchmark-a0-gap"
write_artifact "$LOW_COUNT_ONLY-a0-gap" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap" "span_a" "complete" "$WORK/bench/low-count-a0-gap.stderr.log" "0.0" "low-shared-benchmark-a0-gap"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap" \
  --terminal-dir "$LOW_TERMINAL-a0-gap" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP" \
  --output-dir "$WORK/out-low-a0-gap"
assert_low_overhead_decision "$WORK/out-low-a0-gap" "split_terminal_first_half_span_a0_gap_before_a00" "ok" "true"

LOW_SAMPLED_A0_MULTI_CHILD="$WORK/low-sampled-a0-multi-child"
write_artifact "$LOW_SAMPLED_A0_MULTI_CHILD" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-multi-child" "span_a" "complete" "$WORK/bench/low-sampled-a0-multi-child.stderr.log" "0.05" "low-shared-benchmark-a0-multi-child" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0"
write_artifact "$LOW_COARSE-a0-multi-child" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-multi-child" "unknown" "complete" "$WORK/bench/low-coarse-a0-multi-child.stderr.log" "0.0" "low-shared-benchmark-a0-multi-child"
write_artifact "$LOW_TERMINAL-a0-multi-child" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-multi-child" "unknown" "complete" "$WORK/bench/low-terminal-a0-multi-child.stderr.log" "0.0" "low-shared-benchmark-a0-multi-child"
write_artifact "$LOW_COUNT_ONLY-a0-multi-child" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-multi-child" "span_a" "complete" "$WORK/bench/low-count-a0-multi-child.stderr.log" "0.0" "low-shared-benchmark-a0-multi-child"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-multi-child" \
  --terminal-dir "$LOW_TERMINAL-a0-multi-child" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-multi-child" \
  --sampled-dir "$LOW_SAMPLED_A0_MULTI_CHILD" \
  --output-dir "$WORK/out-low-a0-multi-child"
assert_low_overhead_decision "$WORK/out-low-a0-multi-child" "split_terminal_first_half_span_a0_gap_before_a00" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-multi-child" "closed"

LOW_SAMPLED_A0_COVERAGE_OPEN="$WORK/low-sampled-a0-coverage-open"
write_artifact "$LOW_SAMPLED_A0_COVERAGE_OPEN" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-coverage-open" "span_a" "complete" "$WORK/bench/low-sampled-a0-coverage-open.stderr.log" "0.05" "low-shared-benchmark-a0-coverage-open" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "0" "100" "100" "100" "100" "100" "100" "0" "0"
write_artifact "$LOW_COARSE-a0-coverage-open" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-coverage-open" "unknown" "complete" "$WORK/bench/low-coarse-a0-coverage-open.stderr.log" "0.0" "low-shared-benchmark-a0-coverage-open"
write_artifact "$LOW_TERMINAL-a0-coverage-open" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-coverage-open" "unknown" "complete" "$WORK/bench/low-terminal-a0-coverage-open.stderr.log" "0.0" "low-shared-benchmark-a0-coverage-open"
write_artifact "$LOW_COUNT_ONLY-a0-coverage-open" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-coverage-open" "span_a" "complete" "$WORK/bench/low-count-a0-coverage-open.stderr.log" "0.0" "low-shared-benchmark-a0-coverage-open"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-coverage-open" \
  --terminal-dir "$LOW_TERMINAL-a0-coverage-open" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-coverage-open" \
  --sampled-dir "$LOW_SAMPLED_A0_COVERAGE_OPEN" \
  --output-dir "$WORK/out-low-a0-coverage-open"
assert_low_overhead_decision "$WORK/out-low-a0-coverage-open" "inspect_terminal_first_half_span_a0_timer_scope" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-coverage-open" "open"
assert_materiality_mirror "$WORK/out-low-a0-coverage-open" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0="$WORK/low-sampled-a0-gap-span0"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "span_0"
write_artifact "$LOW_COARSE-a0-gap-span0" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0"
write_artifact "$LOW_TERMINAL-a0-gap-span0" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0" \
  --output-dir "$WORK/out-low-a0-gap-span0"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0" "split_terminal_first_half_span_a0_gap_before_a00_span_0" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0" "material" "true"

LOW_SAMPLED_A0_GAP_SCOPE="$WORK/low-sampled-a0-gap-scope"
write_artifact "$LOW_SAMPLED_A0_GAP_SCOPE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-scope" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-scope.stderr.log" "0.05" "low-shared-benchmark-a0-gap-scope" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.05" "0.04" "100" "100" "100" "0" "100" "span_0"
write_artifact "$LOW_COARSE-a0-gap-scope" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-scope" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-scope"
write_artifact "$LOW_TERMINAL-a0-gap-scope" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-scope" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-scope"
write_artifact "$LOW_COUNT_ONLY-a0-gap-scope" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-scope" "span_a" "complete" "$WORK/bench/low-count-a0-gap-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-scope"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-scope" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-scope" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-scope" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SCOPE" \
  --output-dir "$WORK/out-low-a0-gap-scope"
assert_low_overhead_decision "$WORK/out-low-a0-gap-scope" "inspect_terminal_first_half_span_a0_gap_before_a00_timer_scope" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-scope" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-scope" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_CHILD0="$WORK/low-sampled-a0-gap-span0-child0"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_CHILD0" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-child0" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-child0.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-child0" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "span_0" "0.11" "0.07" "0.03" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-child0" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-child0" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child0"
write_artifact "$LOW_TERMINAL-a0-gap-span0-child0" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-child0" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child0"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-child0" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-child0" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child0"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-child0" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-child0" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-child0" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_CHILD0" \
  --output-dir "$WORK/out-low-a0-gap-span0-child0"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-child0" "split_terminal_first_half_span_a0_gap_before_a00_span_0_child_0" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-child0" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-child0" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_CHILD1="$WORK/low-sampled-a0-gap-span0-child1"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_CHILD1" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-child1" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-child1.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-child1" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "span_0" "0.11" "0.03" "0.07" "100" "100" "100" "0" "100" "child_1"
write_artifact "$LOW_COARSE-a0-gap-span0-child1" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-child1" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child1"
write_artifact "$LOW_TERMINAL-a0-gap-span0-child1" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-child1" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child1"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-child1" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-child1" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-child1"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-child1" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-child1" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-child1" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_CHILD1" \
  --output-dir "$WORK/out-low-a0-gap-span0-child1"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-child1" "split_terminal_first_half_span_a0_gap_before_a00_span_0_child_1" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-child1" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-child1" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_SCOPE="$WORK/low-sampled-a0-gap-span0-scope"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_SCOPE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-scope" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-scope.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-scope" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "span_0" "0.11" "0.03" "0.02" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-scope" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-scope" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-scope"
write_artifact "$LOW_TERMINAL-a0-gap-span0-scope" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-scope" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-scope"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-scope" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-scope" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-scope.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-scope"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-scope" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-scope" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-scope" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_SCOPE" \
  --output-dir "$WORK/out-low-a0-gap-span0-scope"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-scope" "inspect_gap_before_a00_span_0_timer_scope" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-scope" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-scope" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT="$WORK/low-sampled-a0-gap-span0-conflict"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-conflict" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-conflict.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-conflict" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-conflict" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-conflict" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict"
write_artifact "$LOW_TERMINAL-a0-gap-span0-conflict" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-conflict" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-conflict" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-conflict" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-conflict" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-conflict" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-conflict" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-conflict" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT" \
  --output-dir "$WORK/out-low-a0-gap-span0-conflict"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-conflict" "repartition_gap_before_a00_span_0_boundary" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-conflict" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-conflict" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT_PARALLEL="$WORK/low-sampled-a0-gap-span0-conflict-parallel"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT_PARALLEL" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-conflict-parallel" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-conflict-parallel.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-conflict-parallel" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-conflict-parallel" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-conflict-parallel" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-conflict-parallel.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict-parallel"
write_artifact "$LOW_TERMINAL-a0-gap-span0-conflict-parallel" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-conflict-parallel" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-conflict-parallel.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict-parallel"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-conflict-parallel" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-conflict-parallel" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-conflict-parallel.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-conflict-parallel"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT_PARALLEL" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-conflict-parallel" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-conflict-parallel" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-conflict-parallel" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT_PARALLEL" wide_margin
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-conflict-parallel" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-conflict-parallel" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-conflict-parallel" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_CONFLICT_PARALLEL" \
  --output-dir "$WORK/out-low-a0-gap-span0-conflict-parallel"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-conflict-parallel" "split_gap_before_a00_span_0_children_in_parallel" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-conflict-parallel" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-conflict-parallel" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT="$WORK/low-sampled-a0-gap-span0-alt-left"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-left" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-left.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-left" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-left" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-left" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-left"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-left" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-left" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-left"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-left" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-left" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-left"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-left" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-left" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-left" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT" stable_left
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-left" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-left" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-left" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_LEFT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-left"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-left" "split_gap_before_a00_span_0_alt_left" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-left" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-alt-left" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT="$WORK/low-sampled-a0-gap-span0-alt-right"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT" stable_right
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right" "split_gap_before_a00_span_0_alt_right" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-alt-right" "material" "true"
assert_case_field_populated "$WORK/out-low-a0-gap-span0-alt-right" "gap_before_a00_span_0_alt_left_share"
assert_case_field_populated "$WORK/out-low-a0-gap-span0-alt-right" "gap_before_a00_span_0_alt_right_share"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT="$WORK/low-sampled-a0-gap-span0-alt-conflict"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-conflict" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-conflict.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-conflict" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-conflict" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-conflict" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-conflict"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-conflict" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-conflict" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-conflict"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-conflict" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-conflict" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-conflict"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-conflict" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT" low_margin_conflict
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-conflict" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-conflict" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-conflict" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_CONFLICT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-conflict"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-conflict" "repartition_gap_before_a00_span_0_boundary" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-conflict" "closed"
assert_materiality_mirror "$WORK/out-low-a0-gap-span0-alt-conflict" "material" "true"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0="$WORK/low-sampled-a0-gap-span0-alt-right-child0"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-child0" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-child0.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-child0" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-child0" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-child0" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child0"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-child0" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-child0" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child0"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child0" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-child0" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-child0.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child0"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-child0" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-child0" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child0" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0" stable_child_0
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-child0" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-child0" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child0" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD0" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-child0"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-child0" "split_gap_before_a00_span_0_alt_right_child_0" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-child0" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1="$WORK/low-sampled-a0-gap-span0-alt-right-child1"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-child1" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-child1.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-child1" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-child1" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-child1" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child1"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-child1" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-child1" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child1"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child1" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-child1" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-child1.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-child1"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-child1" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-child1" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child1" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1" stable_child_1
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-child1" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-child1" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-child1" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CHILD1" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-child1"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-child1" "split_gap_before_a00_span_0_alt_right_child_1" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-child1" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE="$WORK/low-sampled-a0-gap-span0-alt-right-stale"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-stale" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-stale.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-stale" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-stale" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-stale" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-stale.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-stale"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-stale" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-stale" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-stale.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-stale"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-stale" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-stale" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-stale.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-stale"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-stale" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-stale" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-stale" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE" stale_label_seconds_favor_child_0
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-stale" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-stale" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-stale" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_STALE" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-stale"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-stale" "split_gap_before_a00_span_0_alt_right_child_0" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-stale" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT="$WORK/low-sampled-a0-gap-span0-alt-right-conflict"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-conflict" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-conflict.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-conflict" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-conflict" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-conflict" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-conflict"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-conflict" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-conflict" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-conflict"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-conflict" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-conflict" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-conflict.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-conflict"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-conflict" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-conflict" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT" low_margin_conflict
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-conflict" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-conflict" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-conflict" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_CONFLICT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-conflict"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-conflict" "repartition_gap_before_a00_span_0_alt_right_boundary" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-conflict" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT="$WORK/low-sampled-a0-gap-span0-alt-right-repart-left"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-repart-left" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-repart-left.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-repart-left" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-repart-left" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-repart-left" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-repart-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-left"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-left" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-repart-left" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-repart-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-left"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-left" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-repart-left" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-repart-left.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-left"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-repart-left" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-left" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-left" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" low_margin_conflict
rewrite_sampled_span0_alt_right_repart_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" stable_left
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-repart-left" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-left" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-left" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_LEFT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-repart-left"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-repart-left" "split_gap_before_a00_span_0_alt_right_repart_left" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-repart-left" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT="$WORK/low-sampled-a0-gap-span0-alt-right-repart-right"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-repart-right" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-repart-right.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-repart-right" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-repart-right" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-repart-right" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-repart-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-right"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-right" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-repart-right" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-repart-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-right"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-right" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-repart-right" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-repart-right.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-right"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-repart-right" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-right" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-right" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" low_margin_conflict
rewrite_sampled_span0_alt_right_repart_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" stable_right
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-repart-right" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-right" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-right" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_RIGHT" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-repart-right"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-repart-right" "split_gap_before_a00_span_0_alt_right_repart_right" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-repart-right" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE="$WORK/low-sampled-a0-gap-span0-alt-right-repart-tie"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-repart-tie" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-repart-tie.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-repart-tie" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-repart-tie" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-repart-tie" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-repart-tie.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-tie"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-tie" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-repart-tie" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-repart-tie.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-tie"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-tie" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-repart-tie" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-repart-tie.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-tie"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-repart-tie" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-tie" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-tie" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" low_margin_conflict
rewrite_sampled_span0_alt_right_repart_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" near_tie
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-repart-tie" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-tie" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-tie" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_TIE" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-repart-tie"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-repart-tie" "repartition_gap_before_a00_span_0_alt_right_boundary" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-repart-tie" "closed"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP="$WORK/low-sampled-a0-gap-span0-alt-right-repart-stop"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-repart-stop" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-repart-stop.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-repart-stop" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-repart-stop" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-repart-stop" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-repart-stop.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-stop"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-stop" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-repart-stop" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-repart-stop.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-stop"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-stop" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-repart-stop" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-repart-stop.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-stop"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-repart-stop" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-stop" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-stop" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" near_tie
rewrite_sampled_span0_alt_right_repart_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" near_tie
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-repart-stop" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-stop" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-stop" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_STOP" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-repart-stop"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-repart-stop" "mark_gap_before_a00_span_0_alt_right_as_distributed_overhead" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-repart-stop" "closed"
assert_summary_decision_field "$WORK/out-low-a0-gap-span0-alt-right-repart-stop" "gap_before_a00_span_0_alt_right_repartition_attempt_count" "2"
assert_summary_decision_field "$WORK/out-low-a0-gap-span0-alt-right-repart-stop" "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count" "2"
assert_summary_decision_field "$WORK/out-low-a0-gap-span0-alt-right-repart-stop" "gap_before_a00_span_0_alt_right_subtree_status" "distributed_overhead_no_stable_leaf"

LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN="$WORK/low-sampled-a0-gap-span0-alt-right-repart-open"
write_artifact "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-a0-gap-span0-alt-right-repart-open" "span_a" "complete" "$WORK/bench/low-sampled-a0-gap-span0-alt-right-repart-open.stderr.log" "0.05" "low-shared-benchmark-a0-gap-span0-alt-right-repart-open" "6" "0.015625" "0.70" "0.41" "0.10" "0.08" "span_a0" "0.41" "0.18" "0.02" "0.03" "gap_before_a00" "0.18" "0.02" "0.03" "100" "100" "100" "100" "100" "100" "100" "0" "100" "0" "0.18" "0.11" "0.05" "100" "100" "100" "0" "100" "child_0"
write_artifact "$LOW_COARSE-a0-gap-span0-alt-right-repart-open" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-a0-gap-span0-alt-right-repart-open" "unknown" "complete" "$WORK/bench/low-coarse-a0-gap-span0-alt-right-repart-open.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-open"
write_artifact "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-open" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-a0-gap-span0-alt-right-repart-open" "unknown" "complete" "$WORK/bench/low-terminal-a0-gap-span0-alt-right-repart-open.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-open"
write_artifact "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-open" "lexical_first_half_count_only" "6.1" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-a0-gap-span0-alt-right-repart-open" "span_a" "complete" "$WORK/bench/low-count-a0-gap-span0-alt-right-repart-open.stderr.log" "0.0" "low-shared-benchmark-a0-gap-span0-alt-right-repart-open"
duplicate_artifact_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COARSE-a0-gap-span0-alt-right-repart-open" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-open" case-00000028 case-00000039 case-00000040
duplicate_artifact_cases "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-open" case-00000028 case-00000039 case-00000040
rewrite_sampled_span0_conflict_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN"
rewrite_sampled_span0_alt_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" stable_right
rewrite_sampled_span0_alt_right_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" low_margin_conflict
rewrite_sampled_span0_alt_right_repart_cases "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" coverage_open
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE-a0-gap-span0-alt-right-repart-open" \
  --terminal-dir "$LOW_TERMINAL-a0-gap-span0-alt-right-repart-open" \
  --count-only-dir "$LOW_COUNT_ONLY-a0-gap-span0-alt-right-repart-open" \
  --sampled-dir "$LOW_SAMPLED_A0_GAP_SPAN0_ALT_RIGHT_REPART_OPEN" \
  --output-dir "$WORK/out-low-a0-gap-span0-alt-right-repart-open"
assert_low_overhead_decision "$WORK/out-low-a0-gap-span0-alt-right-repart-open" "inspect_gap_before_a00_span_0_alt_right_repart_timer_scope" "ok" "true"
assert_sampled_count_closure_status "$WORK/out-low-a0-gap-span0-alt-right-repart-open" "closed"

LOW_COUNT_SUSPECT="$WORK/low-count-suspect"
write_artifact "$LOW_COUNT_SUSPECT" "lexical_first_half_count_only" "6.9" "0.0" "0.0" "0.0" "0.0" "9.0" "10.0" "0" "0" "0" "wl-low-suspect" "span_a" "complete" "$WORK/bench/low-count-suspect.stderr.log" "0.0" "low-shared-benchmark-2"
LOW_TERMINAL_SUSPECT="$WORK/low-terminal-suspect"
LOW_COARSE_SUSPECT="$WORK/low-coarse-suspect"
LOW_SAMPLED_SUSPECT="$WORK/low-sampled-suspect"
write_artifact "$LOW_COARSE_SUSPECT" "coarse" "6.0" "4.0" "0.0" "0.0" "0.0" "9.0" "10.0" "300" "300" "0" "wl-low-suspect" "unknown" "complete" "$WORK/bench/low-coarse-suspect.stderr.log" "0.0" "low-shared-benchmark-2"
write_artifact "$LOW_TERMINAL_SUSPECT" "terminal" "6.2" "4.1" "0.0" "0.0" "0.0" "9.0" "10.0" "420" "420" "0" "wl-low-suspect" "unknown" "complete" "$WORK/bench/low-terminal-suspect.stderr.log" "0.0" "low-shared-benchmark-2"
write_artifact "$LOW_SAMPLED_SUSPECT" "lexical_first_half_sampled" "6.3" "4.2" "1.0" "0.7" "0.2" "9.0" "10.0" "450" "420" "30" "wl-low-suspect" "span_a" "complete" "$WORK/bench/low-sampled-suspect.stderr.log" "0.05" "low-shared-benchmark-2" "6" "0.015625"
python3 ./scripts/summarize_sim_initial_host_merge_profile_mode_ab.py \
  --coarse-dir "$LOW_COARSE_SUSPECT" \
  --terminal-dir "$LOW_TERMINAL_SUSPECT" \
  --count-only-dir "$LOW_COUNT_SUSPECT" \
  --sampled-dir "$LOW_SAMPLED_SUSPECT" \
  --output-dir "$WORK/out-low-count-suspect"
assert_low_overhead_decision "$WORK/out-low-count-suspect" "reduce_profiler_timer_overhead" "suspect_count_bookkeeping" "false"

echo "check_summarize_sim_initial_host_merge_profile_mode_ab: PASS"
