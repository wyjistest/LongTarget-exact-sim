#ifndef FASIM_GASAL2_ALIGN_BRIDGE_H
#define FASIM_GASAL2_ALIGN_BRIDGE_H

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>

#include "ssw_cpp.h"

struct FasimGasal2Stats
{
	FasimGasal2Stats() :
		enabled(false),
		built(false),
		requests(0),
		batches(0),
		fallbacks(0),
		score_requests(0),
		score_batches(0),
		traceback_requests(0),
		traceback_batches(0),
		target_view_requests(0),
		score_query_reuse_batches(0),
		score_query_reuse_saved_bytes(0),
		score_query_bytes(0),
		score_target_bytes(0),
		traceback_query_bytes(0),
		traceback_target_bytes(0),
		traceback_query_reuse_saved_bytes(0),
		traceback_query_reuse_potential_saved_bytes(0),
		score_selected_attempts(0),
		score_prepass_select_threshold(0),
		score_prepass_select_best_fallback(0),
		score_prepass_select_last(0),
		score_prepass_select_none(0),
		score_prepass_threshold_rank1(0),
		score_prepass_threshold_rank2(0),
		score_prepass_threshold_rank3(0),
		score_prepass_threshold_rank4plus(0),
		staged_score_prepass_enabled(false),
		staged_score_prepass_first_requests(0),
		staged_score_prepass_remaining_requests(0),
		staged_score_prepass_first_threshold(0),
		staged_score_prepass_pruned_zero_groups(0),
		staged_score_prepass_pruned_best_fallback_groups(0),
		staged_score_prepass_pruned_remaining_requests(0),
		nt_sum_span_prune_enabled(false),
		nt_sum_span_pruned_attempts(0),
		nt_sum_span_pruned_groups(0),
		traceback_certificate_shadow_requested(false),
		traceback_certificate_shadow_active(false),
		traceback_certificate_real_skip_enabled(false),
		traceback_certificate_pre_drop_proof_available(false),
		traceback_certificate_candidates_considered(0),
		traceback_certificate_certified_skips(0),
		traceback_certificate_uncertified_candidates(0),
		traceback_certificate_exact_descriptor_duplicate_skips(0),
		traceback_certificate_static_span_skips(0),
		traceback_certificate_score_endpoint_span_skips(0),
		traceback_certificate_shadow_false_rejects(0),
		traceback_certificate_score_frontier_skips(0),
		traceback_certificate_stability_frontier_skips(0),
		traceback_certificate_nt_frontier_skips(0),
		traceback_certificate_tie_rescues(0),
		traceback_certificate_rank_aware_supported(false),
		traceback_certificate_probe_requests(0),
		traceback_certificate_probe_seconds(0.0),
		traceback_certificate_fallbacks(0),
		limited_traceback_enabled(false),
		limited_traceback_max_scoreinfos(0),
		limited_traceback_min_prealign_score(0),
		limited_traceback_guard_min_prealign_score(0),
		limited_traceback_guard_max_prealign_score(0),
		limited_traceback_guard_max_target_size(0),
		limited_traceback_before(0),
		limited_traceback_after(0),
		limited_traceback_skipped(0),
		limited_traceback_min_prealign_score_skipped(0),
		limited_traceback_guard_kept(0),
		limited_traceback_attempt_export_rows(0),
		cpu_traceback_replay_attempts(0),
		cpu_traceback_selected_attempts(0),
		cpu_traceback_align_calls(0),
		cpu_traceback_skipped_after_emit(0),
		cpu_traceback_rank_cutoff_skipped(0),
		cpu_traceback_emit_threshold(0),
		cpu_traceback_emit_best_fallback(0),
		cpu_traceback_emit_last(0),
		cpu_traceback_candidate_threshold(0),
		cpu_traceback_candidate_fallback(0),
		cpu_traceback_candidate_last(0),
		cpu_traceback_emit_rank1(0),
		cpu_traceback_emit_rank2(0),
		cpu_traceback_emit_rank3(0),
		cpu_traceback_emit_rank4plus(0),
		attempt_consumer_shadow_requested(0),
		attempt_consumer_shadow_active(0),
		attempt_consumer_shadow_decision("not_requested"),
		attempt_consumer_shadow_tasks(0),
		attempt_consumer_shadow_scoreinfos(0),
		attempt_consumer_shadow_attempts(0),
		attempt_consumer_shadow_score_seconds(0.0),
		attempt_consumer_shadow_select_seconds(0.0),
		attempt_consumer_shadow_selected_attempts(0),
		attempt_consumer_shadow_cpu_align_attempts(0),
		attempt_consumer_shadow_cpu_align_seconds(0.0),
		attempt_consumer_shadow_convert_seconds(0.0),
		attempt_consumer_shadow_total_seconds(0.0),
		attempt_consumer_shadow_triplex_mismatches(0),
		attempt_consumer_shadow_missing_triplexes(0),
		attempt_consumer_shadow_extra_triplexes(0),
		attempt_consumer_shadow_first_mismatch("none"),
		attempt_consumer_shadow_fallbacks(0),
		attempt_consumer_shadow_digest_match(0),
		attempt_consumer_shadow_full_rows_equal(0),
		emission_only_consumer_shadow_requested(0),
		emission_only_consumer_shadow_active(0),
		emission_only_consumer_shadow_decision("not_requested"),
		emission_only_consumer_shadow_tasks(0),
		emission_only_consumer_shadow_scoreinfos(0),
		emission_only_consumer_shadow_scored_attempts(0),
		emission_only_consumer_shadow_threshold_emits(0),
		emission_only_consumer_shadow_terminal_emits(0),
		emission_only_consumer_shadow_last_emits(0),
		emission_only_consumer_shadow_empty_emits(0),
		emission_only_consumer_shadow_cpu_align_attempts(0),
		emission_only_consumer_shadow_realpath_reference_align_attempts(0),
		emission_only_consumer_shadow_align_attempt_reduction(0),
		emission_only_consumer_shadow_score_seconds(0.0),
		emission_only_consumer_shadow_select_seconds(0.0),
		emission_only_consumer_shadow_cpu_align_seconds(0.0),
		emission_only_consumer_shadow_convert_seconds(0.0),
		emission_only_consumer_shadow_total_seconds(0.0),
		emission_only_consumer_shadow_triplex_mismatches(0),
		emission_only_consumer_shadow_missing_triplexes(0),
		emission_only_consumer_shadow_extra_triplexes(0),
		emission_only_consumer_shadow_first_mismatch("none"),
		emission_only_consumer_shadow_fallbacks(0),
		emission_only_consumer_shadow_digest_match(0),
		emission_only_consumer_shadow_full_rows_equal(0),
		phase7_next_reducer_requested(0),
		phase7_next_reducer_active(0),
		phase7_next_reducer_tasks(0),
		phase7_next_reducer_scoreinfos(0),
		phase7_next_reducer_reference_attempts(0),
		phase7_next_reducer_candidate_attempts(0),
		phase7_next_reducer_candidate_align_attempts(0),
		phase7_next_reducer_reference_align_attempts(0),
		phase7_next_reducer_false_negative_scoreinfos(0),
		phase7_next_reducer_triplex_mismatches(0),
		phase7_next_reducer_missing_triplexes(0),
		phase7_next_reducer_extra_triplexes(0),
		phase7_next_reducer_digest_match(0),
		phase7_next_reducer_full_rows_equal(0),
		phase7_next_reducer_baseline_wall_seconds(0.0),
		phase7_next_reducer_candidate_wall_seconds(0.0),
		phase7_next_reducer_candidate_vs_baseline(0.0),
		phase7_frontier_log_requested(0),
		phase7_frontier_log_active(0),
		phase7_frontier_log_tasks(0),
		phase7_frontier_log_scoreinfos(0),
		phase7_frontier_log_align_attempts(0),
		phase7_frontier_log_triplexes(0),
		phase7_frontier_log_path(""),
		phase7_frontier_log_digest(""),
		phase7_frontier_early_stop_requested(0),
		phase7_frontier_early_stop_active(0),
		phase7_frontier_early_stop_tasks(0),
		phase7_frontier_early_stop_scoreinfos(0),
		phase7_frontier_early_stop_reference_align_attempts(0),
		phase7_frontier_early_stop_candidate_align_attempts(0),
		phase7_frontier_early_stop_skipped_attempts(0),
		phase7_frontier_early_stop_emitted_groups(0),
		phase7_frontier_early_stop_fallback_groups(0),
		phase7_all_attempt_early_stop_requested(0),
		phase7_all_attempt_early_stop_active(0),
		phase7_all_attempt_early_stop_tasks(0),
		phase7_all_attempt_early_stop_scoreinfos(0),
		phase7_all_attempt_early_stop_reference_align_attempts(0),
		phase7_all_attempt_early_stop_candidate_align_attempts(0),
		phase7_all_attempt_early_stop_skipped_attempts(0),
		phase7_all_attempt_early_stop_emitted_groups(0),
		phase7_all_attempt_early_stop_fallback_groups(0),
		phase7_gate_c_requested(0),
		phase7_gate_c_active(0),
		phase7_gate_c_tasks(0),
		phase7_gate_c_oracle_scoreinfos(0),
		phase7_gate_c_oracle_attempts(0),
		phase7_gate_c_gpu_candidate_scoreinfos(0),
		phase7_gate_c_gpu_candidate_attempts(0),
		phase7_gate_c_false_negative_scoreinfos(0),
		phase7_gate_c_missing_required_attempts(0),
		phase7_gate_c_extra_candidate_attempts(0),
		phase7_gate_c_candidate_align_attempts(0),
		phase7_gate_c_gate_b_candidate_align_attempts(0),
		phase7_gate_c_scoreinfo_cpu_seconds(0.0),
		phase7_gate_c_gpu_candidate_seconds(0.0),
		phase7_gate_c_cpu_replay_seconds(0.0),
		phase7_gate_c_total_seconds(0.0),
		phase7_gate_c_digest_match(0),
		phase7_gate_c_full_rows_equal(0),
		phase7_v3_descriptor_source_requested(0),
		phase7_v3_descriptor_source_active(0),
		phase7_v3_descriptor_source_tasks(0),
		phase7_v3_descriptor_source_reference_scoreinfos(0),
		phase7_v3_descriptor_source_reference_attempts(0),
		phase7_v3_descriptor_source_candidate_scoreinfos(0),
		phase7_v3_descriptor_source_candidate_attempts(0),
		phase7_v3_descriptor_source_candidate_min_cover_positions(0),
		phase7_v3_descriptor_source_cpu_scoreinfo_calls(0),
		phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls(0),
		phase7_v3_descriptor_source_cpu_scoreinfo_reduced(0),
		phase7_v3_descriptor_source_candidate_certificate_checked(0),
		phase7_v3_descriptor_source_candidate_certificate_false_negatives(0),
		phase7_v3_descriptor_source_missing_required_attempts(0),
		phase7_v3_descriptor_source_pre_scoreinfo_source(0),
		phase7_v3_descriptor_source_after_cpu_scoreinfo_source(0),
		phase7_v5_fused_scoreinfo_consumer_requested(0),
		phase7_v5_fused_scoreinfo_consumer_active(0),
		phase7_v5_fused_scoreinfo_consumer_tasks(0),
		phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos(0),
		phase7_v5_fused_scoreinfo_consumer_reference_attempts(0),
		phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos(0),
		phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts(0),
		phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives(0),
		phase7_v5_fused_scoreinfo_consumer_missing_required_attempts(0),
		phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts(0),
		phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced(0),
		phase7_v5_fused_scoreinfo_consumer_cpu_align_authority(0),
		phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_requested(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_active(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_tasks(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_reference_scoreinfos(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_reference_attempts(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass(0),
		phase7_v5_cpu_authority_replay_requested(0),
		phase7_v5_cpu_authority_replay_active(0),
		phase7_v5_cpu_authority_replay_tasks(0),
		phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos(0),
		phase7_v5_cpu_authority_replay_gpu_descriptor_attempts(0),
		phase7_v5_cpu_authority_replay_reference_align_attempts(0),
		phase7_v5_cpu_authority_replay_candidate_align_attempts(0),
		phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo(0),
		phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced(0),
		phase7_v5_cpu_authority_replay_descriptor_false_negatives(0),
		phase7_v5_cpu_authority_replay_missing_required_attempts(0),
		phase7_v5_cpu_authority_replay_cpu_align_authority(0),
		phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_v5_cpu_authority_replay_full_rows_equal(0),
		phase7_v5_cpu_authority_replay_digest_match(0),
		phase7_v5_cpu_authority_replay_missing_rows(0),
		phase7_v5_cpu_authority_replay_extra_rows(0),
		phase7_v5_cpu_authority_replay_triplex_mismatches(0),
		phase7_v5_cpu_authority_replay_gate_v5_2_pass(0),
		phase7_post_v5_3_gpu_consumer_summary_requested(0),
		phase7_post_v5_3_gpu_consumer_summary_active(0),
		phase7_post_v5_3_gpu_consumer_summary_tasks(0),
		phase7_post_v5_3_gpu_consumer_summary_source_is_pre_scoreinfo(0),
		phase7_post_v5_3_gpu_consumer_summary_rows(0),
		phase7_post_v5_3_gpu_consumer_reduces_before_host_transfer(0),
		phase7_post_v5_3_uses_prefix_boundary_or_equivalent_replay_proof(0),
		phase7_post_v5_3_arbitrary_sparse_subset(0),
		phase7_post_v5_3_first_descriptor_per_scoreinfo(0),
		phase7_post_v5_3_gpu_selected_attempts(0),
		phase7_post_v5_3_selected_prefix_attempts(0),
		phase7_post_v5_3_reference_align_attempts(0),
		phase7_post_v5_3_candidate_align_attempts(0),
		phase7_post_v5_3_v5_candidate_align_attempts(0),
		phase7_post_v5_3_scoreinfo_prealign_reduced(0),
		phase7_post_v5_3_align_side_reduced(0),
		phase7_post_v5_3_descriptor_false_negatives(0),
		phase7_post_v5_3_missing_required_attempts(0),
		phase7_post_v5_3_fallback_accounting_clean(0),
		phase7_post_v5_3_cpu_align_authority(0),
		phase7_post_v5_3_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_digest_match(0),
		phase7_post_v5_3_full_rows_equal(0),
		phase7_post_v5_3_missing_rows(0),
		phase7_post_v5_3_extra_rows(0),
		phase7_post_v5_3_triplex_mismatches(0),
		phase7_post_v5_3_gate_first1_pass(0),
		phase7_post_v5_3_task_frontier_certificate_requested(0),
		phase7_post_v5_3_task_frontier_certificate_active(0),
		phase7_post_v5_3_task_frontier_certificate_tasks(0),
		phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo(0),
		phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda(0),
		phase7_post_v5_3_task_frontier_certificate_gasal2_score_only_long_query_dependency(0),
		phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate(0),
		phase7_post_v5_3_task_frontier_certificate_uses_prefix_boundary_only(0),
		phase7_post_v5_3_task_frontier_certificate_arbitrary_sparse_subset(0),
		phase7_post_v5_3_task_frontier_certificate_first_descriptor_per_scoreinfo(0),
		phase7_post_v5_3_task_frontier_certificate_fixed_prefix_per_scoreinfo(0),
		phase7_post_v5_3_task_frontier_certificate_gpu_consumer_reduces_before_host_transfer(0),
		phase7_post_v5_3_task_frontier_certificate_rows(0),
		phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts(0),
		phase7_post_v5_3_task_frontier_certificate_reference_align_attempts(0),
		phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts(0),
		phase7_post_v5_3_task_frontier_certificate_v5_candidate_align_attempts(0),
		phase7_post_v5_3_task_frontier_certificate_descriptor_false_negatives(0),
		phase7_post_v5_3_task_frontier_certificate_missing_required_attempts(0),
		phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean(0),
		phase7_post_v5_3_task_frontier_certificate_cpu_align_authority(0),
		phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_task_frontier_certificate_digest_match(0),
		phase7_post_v5_3_task_frontier_certificate_full_rows_equal(0),
		phase7_post_v5_3_task_frontier_certificate_missing_rows(0),
		phase7_post_v5_3_task_frontier_certificate_extra_rows(0),
		phase7_post_v5_3_task_frontier_certificate_triplex_mismatches(0),
		phase7_post_v5_3_task_frontier_certificate_gate_first1_pass(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_requested(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_active(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_tasks(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_host_assisted(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_source_is_v5_descriptors(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_consumer_reduces_before_host_transfer(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_host_selected_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_prefix_descriptor_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_reference_align_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_v5_candidate_align_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts_less_than_v5(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_descriptor_false_negatives(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_missing_required_attempts(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_fallback_accounting_clean(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_cpu_align_authority(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_digest_match(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_full_rows_equal(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_missing_rows(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_extra_rows(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_triplex_mismatches(0),
		phase7_post_v5_3_host_assisted_consumer_feasibility_gate_first1_pass(0),
		phase7_post_v5_3_pre_d2h_proof_search_requested(0),
		phase7_post_v5_3_pre_d2h_proof_search_active(0),
		phase7_post_v5_3_pre_d2h_proof_search_source_is_pre_scoreinfo(0),
		phase7_post_v5_3_pre_d2h_proof_search_source_is_legacy_byte_cuda(0),
		phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority(0),
		phase7_post_v5_3_pre_d2h_proof_search_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_pre_d2h_proof_search_gpu_output_authority(0),
		phase7_post_v5_3_pre_d2h_proof_search_runtime_reduction_enabled(0),
		phase7_post_v5_3_pre_d2h_proof_search_proof_search_rows(0),
		phase7_post_v5_3_pre_d2h_proof_search_task_count(0),
		phase7_post_v5_3_pre_d2h_proof_search_scoreinfo_count(0),
		phase7_post_v5_3_pre_d2h_proof_search_attempt_count(0),
		phase7_post_v5_3_pre_d2h_proof_search_label_source_cpu_authority_external_output(0),
		phase7_post_v5_3_pre_d2h_proof_search_gate_first1_export_pass(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_requested(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_active(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_scoreinfo_tasks(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_candidate_groups(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_replay_attempts(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_groups(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_attempts(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_replay_attempts(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_baseline_cpu_attempts(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_false_negatives(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_required_attempts(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match(0),
		phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_rows(0),
			phase7_post_v5_3_new_gpu_engine_first1_shadow_extra_rows(0),
			phase7_post_v5_3_new_gpu_engine_first1_shadow_triplex_mismatches(0),
			phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_tasks(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_candidate_groups(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_replay_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_selected_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_groups(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_replay_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_cpu_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_certificate_false_negatives(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_required_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_full_rows_equal(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_digest_match(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_rows(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_extra_rows(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_triplex_mismatches(0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_candidate_wall_seconds(0.0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_wall_seconds(0.0),
			phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_work_drop_path(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_final_cpu_output_membership_required(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_task_count(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_scoreinfo_count(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_attempt_count(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_scoreinfo_count(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_attempt_count(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_certificate_false_negatives(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_required_attempts(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority(0),
			phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority(0),
				phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_full_rows_equal(0),
				phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_digest_match(0),
				phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass(0),
				phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_work_drop_path(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_final_cpu_output_membership_required(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_task_count(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_scoreinfo_count(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_attempt_count(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_scoreinfo_count(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_attempt_count(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_false_negatives(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_missing_required_attempts(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass(0),
				phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_cert_engine_first1_shadow(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_work_drop(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_d2h(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_reduction_enabled(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_work_drop_enabled(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_to_full_cpu_replay(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_scoreinfo_groups(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_attempt_frontier_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_selected_replay_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_scoreinfo_groups(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_replay_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_baseline_cpu_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_false_negatives(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_required_attempts(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_prealign_reduced(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_align_side_reduced(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_accounting_clean(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_full_rows_equal(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_digest_match(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_rows(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_extra_rows(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_triplex_mismatches(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_shadow_pass(0),
				phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_pass(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_requested(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_states(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_attempt_frontier_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_replay_frontier_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_scoreinfo_groups(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_replay_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_baseline_cpu_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_produced_before_work_drop(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_consumed_before_cpu_replay_selection(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_false_negatives(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_required_attempts(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_to_full_cpu_replay(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_accounting_clean(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scoreinfo_prealign_reduced(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_align_side_reduced(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_full_rows_equal(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_digest_match(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_rows(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_extra_rows(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_triplex_mismatches(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass(0),
				phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_pass(0),
				phase7_full_align_verifier_first1_shadow_requested(0),
				phase7_full_align_verifier_first1_shadow_active(0),
				phase7_full_align_verifier_first1_shadow_descriptors(0),
				phase7_full_align_verifier_first1_shadow_proposals(0),
				phase7_full_align_verifier_first1_shadow_proposal_failures(0),
				phase7_full_align_verifier_first1_shadow_verifier_pass(0),
				phase7_full_align_verifier_first1_shadow_verifier_fail(0),
				phase7_full_align_verifier_first1_shadow_cpu_align_fallbacks(0),
				phase7_full_align_verifier_first1_shadow_score_mismatches(0),
				phase7_full_align_verifier_first1_shadow_endpoint_mismatches(0),
				phase7_full_align_verifier_first1_shadow_cigar_mismatches(0),
				phase7_full_align_verifier_first1_shadow_full_row_mismatches(0),
				phase7_full_align_verifier_first1_shadow_digest_mismatches(0),
				phase7_full_align_verifier_first1_shadow_full_rows_equal(0),
				phase7_full_align_verifier_first1_shadow_digest_match(0),
				phase7_full_align_verifier_first1_shadow_missing_rows(0),
				phase7_full_align_verifier_first1_shadow_extra_rows(0),
				phase7_full_align_verifier_first1_shadow_triplex_mismatches(0),
				phase7_full_align_verifier_first1_shadow_runtime_reduction_enabled(0),
				phase7_full_align_verifier_first1_shadow_runtime_work_drop_enabled(0),
				phase7_full_align_verifier_first1_shadow_gpu_endpoint_cigar_traceback_output_authority(0),
				phase7_full_align_verifier_first1_shadow_gpu_output_digest_authority(0),
					phase7_full_align_verifier_first1_shadow_cpu_align_authority(0),
					phase7_full_align_verifier_first1_shadow_fallback_to_full_cpu_replay(0),
					phase7_full_align_verifier_first1_shadow_gate_first1_shadow_pass(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_requested(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_active(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_native_scoreinfo_tiles(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_forward_endpoint_witnesses(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_witnesses(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_traceback_cigar_witnesses(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_certificates(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_certificate_false_negatives(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_missing_required_attempts(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_byte_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_endpoint_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_cigar_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_full_row_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_mismatches(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_full_rows_equal(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_match(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_fallbacks(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_reduction_enabled(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_work_drop_enabled(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_prealign_reduced(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_align_side_reduced(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_accounting_clean(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_score_authority(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_endpoint_authority(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_cigar_traceback_output_authority(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_output_digest_authority(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_to_full_cpu_replay(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_shadow_pass(0),
					phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_pass(0),
					phase7_gpu_upper_bound_reject_first1_shadow_requested(0),
					phase7_gpu_upper_bound_reject_first1_shadow_active(0),
					phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_descriptors(0),
					phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_certificates(0),
					phase7_gpu_upper_bound_reject_first1_shadow_reject_candidates_shadow(0),
					phase7_gpu_upper_bound_reject_first1_shadow_would_reject_scoreinfo_groups(0),
					phase7_gpu_upper_bound_reject_first1_shadow_would_reject_align_attempts(0),
					phase7_gpu_upper_bound_reject_first1_shadow_certificate_false_negatives(0),
					phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_groups(0),
					phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_attempts(0),
					phase7_gpu_upper_bound_reject_first1_shadow_unsupported_descriptors(0),
					phase7_gpu_upper_bound_reject_first1_shadow_fallback_to_full_cpu_replay(0),
					phase7_gpu_upper_bound_reject_first1_shadow_scoreinfo_prealign_reduced(0),
					phase7_gpu_upper_bound_reject_first1_shadow_align_side_reduced(0),
					phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal(0),
					phase7_gpu_upper_bound_reject_first1_shadow_digest_match(0),
					phase7_gpu_upper_bound_reject_first1_shadow_runtime_reduction_enabled(0),
					phase7_gpu_upper_bound_reject_first1_shadow_runtime_work_drop_enabled(0),
					phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gpu_score_authority(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gpu_endpoint_authority(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gpu_cigar_traceback_output_authority(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gpu_output_digest_authority(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_shadow_pass(0),
					phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_pass(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_requested(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_active(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_unique_keys(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_duplicate_units(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_align_unique_keys(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_align_duplicate_attempts(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_key_collisions(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_key_validation_mismatches(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_unsupported_key_descriptors(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_fallback_to_full_cpu_replay(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_prealign_reduced(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_align_side_reduced(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_reduction_enabled(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_work_drop_enabled(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_score_authority(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_endpoint_authority(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_cigar_traceback_output_authority(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_output_digest_authority(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_shadow_pass(0),
					phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_pass(0),
					phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_groups(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempts(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_conservative_fallback_groups(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_cpu_align_authority(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gpu_endpoint_cigar_traceback_output_authority(0),
		phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass(0),
		phase7_v3_oracle_min_cover_replay_requested(0),
		phase7_v3_oracle_min_cover_replay_active(0),
		phase7_v3_oracle_min_cover_replay_tasks(0),
		phase7_v3_oracle_min_cover_replay_reference_align_attempts(0),
		phase7_v3_oracle_min_cover_replay_candidate_align_attempts(0),
		phase7_v3_oracle_min_cover_replay_candidate_min_cover_positions(0),
		phase7_v3_oracle_min_cover_replay_skipped_attempts(0),
		longtarget_task_batches(0),
		longtarget_task_batch_tasks(0),
			longtarget_task_batch_scoreinfos(0),
			length_guard_fallbacks(0),
			length_guard_last_query_len(0),
			length_guard_max_query_len(0),
			length_guard_last_target_len(0),
			length_guard_max_target_len(0),
			effective_streams(0),
			effective_batch_size(0),
			score_prepass_enabled(false),
		load_seconds(0.0),
		init_seconds(0.0),
		fill_seconds(0.0),
		score_fill_seconds(0.0),
		traceback_fill_seconds(0.0),
		submit_seconds(0.0),
		score_submit_seconds(0.0),
		traceback_submit_seconds(0.0),
		wait_seconds(0.0),
			total_seconds(0.0),
			score_wait_seconds(0.0),
			traceback_wait_seconds(0.0),
			score_poll_wait_seconds(0.0),
			traceback_poll_wait_seconds(0.0),
			score_result_copy_seconds(0.0),
			traceback_result_copy_seconds(0.0),
		traceback_cigar_vector_seconds(0.0),
		traceback_cigar_string_seconds(0.0),
		traceback_cigar_raw_ops(0),
		traceback_cigar_merged_ops(0),
		longtarget_attempt_build_seconds(0.0),
		longtarget_score_select_seconds(0.0),
		cpu_traceback_replay_seconds(0.0),
		cpu_traceback_substr_seconds(0.0),
		cpu_traceback_align_seconds(0.0),
		cpu_traceback_convert_seconds(0.0)
	{
	}

	bool enabled;
	bool built;
	uint64_t requests;
	uint64_t batches;
	uint64_t fallbacks;
	uint64_t score_requests;
	uint64_t score_batches;
	uint64_t traceback_requests;
	uint64_t traceback_batches;
	uint64_t target_view_requests;
	uint64_t score_query_reuse_batches;
	uint64_t score_query_reuse_saved_bytes;
	uint64_t score_query_bytes;
	uint64_t score_target_bytes;
	uint64_t traceback_query_bytes;
	uint64_t traceback_target_bytes;
	uint64_t traceback_query_reuse_saved_bytes;
	uint64_t traceback_query_reuse_potential_saved_bytes;
	uint64_t score_selected_attempts;
	uint64_t score_prepass_select_threshold;
	uint64_t score_prepass_select_best_fallback;
	uint64_t score_prepass_select_last;
	uint64_t score_prepass_select_none;
	uint64_t score_prepass_threshold_rank1;
	uint64_t score_prepass_threshold_rank2;
	uint64_t score_prepass_threshold_rank3;
	uint64_t score_prepass_threshold_rank4plus;
	bool staged_score_prepass_enabled;
	uint64_t staged_score_prepass_first_requests;
	uint64_t staged_score_prepass_remaining_requests;
	uint64_t staged_score_prepass_first_threshold;
	uint64_t staged_score_prepass_pruned_zero_groups;
	uint64_t staged_score_prepass_pruned_best_fallback_groups;
	uint64_t staged_score_prepass_pruned_remaining_requests;
	bool nt_sum_span_prune_enabled;
	uint64_t nt_sum_span_pruned_attempts;
	uint64_t nt_sum_span_pruned_groups;
	bool traceback_certificate_shadow_requested;
	bool traceback_certificate_shadow_active;
	bool traceback_certificate_real_skip_enabled;
	bool traceback_certificate_pre_drop_proof_available;
	uint64_t traceback_certificate_candidates_considered;
	uint64_t traceback_certificate_certified_skips;
	uint64_t traceback_certificate_uncertified_candidates;
	uint64_t traceback_certificate_exact_descriptor_duplicate_skips;
	uint64_t traceback_certificate_static_span_skips;
	uint64_t traceback_certificate_score_endpoint_span_skips;
	uint64_t traceback_certificate_shadow_false_rejects;
	uint64_t traceback_certificate_score_frontier_skips;
	uint64_t traceback_certificate_stability_frontier_skips;
	uint64_t traceback_certificate_nt_frontier_skips;
	uint64_t traceback_certificate_tie_rescues;
	bool traceback_certificate_rank_aware_supported;
	uint64_t traceback_certificate_probe_requests;
	double traceback_certificate_probe_seconds;
	uint64_t traceback_certificate_fallbacks;
	bool limited_traceback_enabled;
	uint64_t limited_traceback_max_scoreinfos;
	uint64_t limited_traceback_min_prealign_score;
	uint64_t limited_traceback_guard_min_prealign_score;
	uint64_t limited_traceback_guard_max_prealign_score;
	uint64_t limited_traceback_guard_max_target_size;
	uint64_t limited_traceback_before;
	uint64_t limited_traceback_after;
	uint64_t limited_traceback_skipped;
	uint64_t limited_traceback_min_prealign_score_skipped;
	uint64_t limited_traceback_guard_kept;
	uint64_t limited_traceback_attempt_export_rows;
	uint64_t cpu_traceback_replay_attempts;
	uint64_t cpu_traceback_selected_attempts;
	uint64_t cpu_traceback_align_calls;
	uint64_t cpu_traceback_skipped_after_emit;
	uint64_t cpu_traceback_rank_cutoff_skipped;
	uint64_t cpu_traceback_emit_threshold;
	uint64_t cpu_traceback_emit_best_fallback;
	uint64_t cpu_traceback_emit_last;
	uint64_t cpu_traceback_candidate_threshold;
	uint64_t cpu_traceback_candidate_fallback;
	uint64_t cpu_traceback_candidate_last;
	uint64_t cpu_traceback_emit_rank1;
	uint64_t cpu_traceback_emit_rank2;
	uint64_t cpu_traceback_emit_rank3;
	uint64_t cpu_traceback_emit_rank4plus;
	uint64_t attempt_consumer_shadow_requested;
	uint64_t attempt_consumer_shadow_active;
	std::string attempt_consumer_shadow_decision;
	uint64_t attempt_consumer_shadow_tasks;
	uint64_t attempt_consumer_shadow_scoreinfos;
	uint64_t attempt_consumer_shadow_attempts;
	double attempt_consumer_shadow_score_seconds;
	double attempt_consumer_shadow_select_seconds;
	uint64_t attempt_consumer_shadow_selected_attempts;
	uint64_t attempt_consumer_shadow_cpu_align_attempts;
	double attempt_consumer_shadow_cpu_align_seconds;
	double attempt_consumer_shadow_convert_seconds;
	double attempt_consumer_shadow_total_seconds;
	uint64_t attempt_consumer_shadow_triplex_mismatches;
	uint64_t attempt_consumer_shadow_missing_triplexes;
	uint64_t attempt_consumer_shadow_extra_triplexes;
	std::string attempt_consumer_shadow_first_mismatch;
	uint64_t attempt_consumer_shadow_fallbacks;
	uint64_t attempt_consumer_shadow_digest_match;
	uint64_t attempt_consumer_shadow_full_rows_equal;
	uint64_t emission_only_consumer_shadow_requested;
	uint64_t emission_only_consumer_shadow_active;
	std::string emission_only_consumer_shadow_decision;
	uint64_t emission_only_consumer_shadow_tasks;
	uint64_t emission_only_consumer_shadow_scoreinfos;
	uint64_t emission_only_consumer_shadow_scored_attempts;
	uint64_t emission_only_consumer_shadow_threshold_emits;
	uint64_t emission_only_consumer_shadow_terminal_emits;
	uint64_t emission_only_consumer_shadow_last_emits;
	uint64_t emission_only_consumer_shadow_empty_emits;
	uint64_t emission_only_consumer_shadow_cpu_align_attempts;
	uint64_t emission_only_consumer_shadow_realpath_reference_align_attempts;
	int64_t emission_only_consumer_shadow_align_attempt_reduction;
	double emission_only_consumer_shadow_score_seconds;
	double emission_only_consumer_shadow_select_seconds;
	double emission_only_consumer_shadow_cpu_align_seconds;
	double emission_only_consumer_shadow_convert_seconds;
	double emission_only_consumer_shadow_total_seconds;
	uint64_t emission_only_consumer_shadow_triplex_mismatches;
	uint64_t emission_only_consumer_shadow_missing_triplexes;
	uint64_t emission_only_consumer_shadow_extra_triplexes;
	std::string emission_only_consumer_shadow_first_mismatch;
	uint64_t emission_only_consumer_shadow_fallbacks;
	uint64_t emission_only_consumer_shadow_digest_match;
	uint64_t emission_only_consumer_shadow_full_rows_equal;
	uint64_t phase7_next_reducer_requested;
	uint64_t phase7_next_reducer_active;
	uint64_t phase7_next_reducer_tasks;
	uint64_t phase7_next_reducer_scoreinfos;
	uint64_t phase7_next_reducer_reference_attempts;
	uint64_t phase7_next_reducer_candidate_attempts;
	uint64_t phase7_next_reducer_candidate_align_attempts;
	uint64_t phase7_next_reducer_reference_align_attempts;
	uint64_t phase7_next_reducer_false_negative_scoreinfos;
	uint64_t phase7_next_reducer_triplex_mismatches;
	uint64_t phase7_next_reducer_missing_triplexes;
	uint64_t phase7_next_reducer_extra_triplexes;
	uint64_t phase7_next_reducer_digest_match;
	uint64_t phase7_next_reducer_full_rows_equal;
	double phase7_next_reducer_baseline_wall_seconds;
	double phase7_next_reducer_candidate_wall_seconds;
	double phase7_next_reducer_candidate_vs_baseline;
	uint64_t phase7_frontier_log_requested;
	uint64_t phase7_frontier_log_active;
	uint64_t phase7_frontier_log_tasks;
	uint64_t phase7_frontier_log_scoreinfos;
	uint64_t phase7_frontier_log_align_attempts;
	uint64_t phase7_frontier_log_triplexes;
	std::string phase7_frontier_log_path;
	std::string phase7_frontier_log_digest;
	uint64_t phase7_frontier_early_stop_requested;
	uint64_t phase7_frontier_early_stop_active;
	uint64_t phase7_frontier_early_stop_tasks;
	uint64_t phase7_frontier_early_stop_scoreinfos;
	uint64_t phase7_frontier_early_stop_reference_align_attempts;
	uint64_t phase7_frontier_early_stop_candidate_align_attempts;
	uint64_t phase7_frontier_early_stop_skipped_attempts;
	uint64_t phase7_frontier_early_stop_emitted_groups;
	uint64_t phase7_frontier_early_stop_fallback_groups;
	uint64_t phase7_all_attempt_early_stop_requested;
	uint64_t phase7_all_attempt_early_stop_active;
	uint64_t phase7_all_attempt_early_stop_tasks;
	uint64_t phase7_all_attempt_early_stop_scoreinfos;
	uint64_t phase7_all_attempt_early_stop_reference_align_attempts;
	uint64_t phase7_all_attempt_early_stop_candidate_align_attempts;
	uint64_t phase7_all_attempt_early_stop_skipped_attempts;
	uint64_t phase7_all_attempt_early_stop_emitted_groups;
	uint64_t phase7_all_attempt_early_stop_fallback_groups;
	uint64_t phase7_gate_c_requested;
	uint64_t phase7_gate_c_active;
	uint64_t phase7_gate_c_tasks;
	uint64_t phase7_gate_c_oracle_scoreinfos;
	uint64_t phase7_gate_c_oracle_attempts;
	uint64_t phase7_gate_c_gpu_candidate_scoreinfos;
	uint64_t phase7_gate_c_gpu_candidate_attempts;
	uint64_t phase7_gate_c_false_negative_scoreinfos;
	uint64_t phase7_gate_c_missing_required_attempts;
	uint64_t phase7_gate_c_extra_candidate_attempts;
	uint64_t phase7_gate_c_candidate_align_attempts;
	uint64_t phase7_gate_c_gate_b_candidate_align_attempts;
	double phase7_gate_c_scoreinfo_cpu_seconds;
	double phase7_gate_c_gpu_candidate_seconds;
	double phase7_gate_c_cpu_replay_seconds;
	double phase7_gate_c_total_seconds;
	uint64_t phase7_gate_c_digest_match;
	uint64_t phase7_gate_c_full_rows_equal;
	uint64_t phase7_v3_descriptor_source_requested;
	uint64_t phase7_v3_descriptor_source_active;
	uint64_t phase7_v3_descriptor_source_tasks;
	uint64_t phase7_v3_descriptor_source_reference_scoreinfos;
	uint64_t phase7_v3_descriptor_source_reference_attempts;
	uint64_t phase7_v3_descriptor_source_candidate_scoreinfos;
	uint64_t phase7_v3_descriptor_source_candidate_attempts;
	uint64_t phase7_v3_descriptor_source_candidate_min_cover_positions;
	uint64_t phase7_v3_descriptor_source_cpu_scoreinfo_calls;
	uint64_t phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls;
	uint64_t phase7_v3_descriptor_source_cpu_scoreinfo_reduced;
	uint64_t phase7_v3_descriptor_source_candidate_certificate_checked;
	uint64_t phase7_v3_descriptor_source_candidate_certificate_false_negatives;
	uint64_t phase7_v3_descriptor_source_missing_required_attempts;
	uint64_t phase7_v3_descriptor_source_pre_scoreinfo_source;
	uint64_t phase7_v3_descriptor_source_after_cpu_scoreinfo_source;
	uint64_t phase7_v5_fused_scoreinfo_consumer_requested;
	uint64_t phase7_v5_fused_scoreinfo_consumer_active;
	uint64_t phase7_v5_fused_scoreinfo_consumer_tasks;
	uint64_t phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos;
	uint64_t phase7_v5_fused_scoreinfo_consumer_reference_attempts;
	uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos;
	uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts;
	uint64_t phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives;
	uint64_t phase7_v5_fused_scoreinfo_consumer_missing_required_attempts;
	uint64_t phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts;
	uint64_t phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced;
	uint64_t phase7_v5_fused_scoreinfo_consumer_cpu_align_authority;
	uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_requested;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_active;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_tasks;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_reference_scoreinfos;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_reference_attempts;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass;
	uint64_t phase7_v5_cpu_authority_replay_requested;
	uint64_t phase7_v5_cpu_authority_replay_active;
	uint64_t phase7_v5_cpu_authority_replay_tasks;
	uint64_t phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos;
	uint64_t phase7_v5_cpu_authority_replay_gpu_descriptor_attempts;
	uint64_t phase7_v5_cpu_authority_replay_reference_align_attempts;
	uint64_t phase7_v5_cpu_authority_replay_candidate_align_attempts;
	uint64_t phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo;
	uint64_t phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced;
	uint64_t phase7_v5_cpu_authority_replay_descriptor_false_negatives;
	uint64_t phase7_v5_cpu_authority_replay_missing_required_attempts;
	uint64_t phase7_v5_cpu_authority_replay_cpu_align_authority;
	uint64_t phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_v5_cpu_authority_replay_full_rows_equal;
	uint64_t phase7_v5_cpu_authority_replay_digest_match;
	uint64_t phase7_v5_cpu_authority_replay_missing_rows;
	uint64_t phase7_v5_cpu_authority_replay_extra_rows;
	uint64_t phase7_v5_cpu_authority_replay_triplex_mismatches;
	uint64_t phase7_v5_cpu_authority_replay_gate_v5_2_pass;
	uint64_t phase7_post_v5_3_gpu_consumer_summary_requested;
	uint64_t phase7_post_v5_3_gpu_consumer_summary_active;
	uint64_t phase7_post_v5_3_gpu_consumer_summary_tasks;
	uint64_t phase7_post_v5_3_gpu_consumer_summary_source_is_pre_scoreinfo;
	uint64_t phase7_post_v5_3_gpu_consumer_summary_rows;
	uint64_t phase7_post_v5_3_gpu_consumer_reduces_before_host_transfer;
	uint64_t phase7_post_v5_3_uses_prefix_boundary_or_equivalent_replay_proof;
	uint64_t phase7_post_v5_3_arbitrary_sparse_subset;
	uint64_t phase7_post_v5_3_first_descriptor_per_scoreinfo;
	uint64_t phase7_post_v5_3_gpu_selected_attempts;
	uint64_t phase7_post_v5_3_selected_prefix_attempts;
	uint64_t phase7_post_v5_3_reference_align_attempts;
	uint64_t phase7_post_v5_3_candidate_align_attempts;
	uint64_t phase7_post_v5_3_v5_candidate_align_attempts;
	uint64_t phase7_post_v5_3_scoreinfo_prealign_reduced;
	uint64_t phase7_post_v5_3_align_side_reduced;
	uint64_t phase7_post_v5_3_descriptor_false_negatives;
	uint64_t phase7_post_v5_3_missing_required_attempts;
	uint64_t phase7_post_v5_3_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_cpu_align_authority;
	uint64_t phase7_post_v5_3_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_digest_match;
	uint64_t phase7_post_v5_3_full_rows_equal;
	uint64_t phase7_post_v5_3_missing_rows;
	uint64_t phase7_post_v5_3_extra_rows;
	uint64_t phase7_post_v5_3_triplex_mismatches;
	uint64_t phase7_post_v5_3_gate_first1_pass;
	uint64_t phase7_post_v5_3_task_frontier_certificate_requested;
	uint64_t phase7_post_v5_3_task_frontier_certificate_active;
	uint64_t phase7_post_v5_3_task_frontier_certificate_tasks;
	uint64_t phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo;
	uint64_t phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda;
	uint64_t phase7_post_v5_3_task_frontier_certificate_gasal2_score_only_long_query_dependency;
	uint64_t phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate;
	uint64_t phase7_post_v5_3_task_frontier_certificate_uses_prefix_boundary_only;
	uint64_t phase7_post_v5_3_task_frontier_certificate_arbitrary_sparse_subset;
	uint64_t phase7_post_v5_3_task_frontier_certificate_first_descriptor_per_scoreinfo;
	uint64_t phase7_post_v5_3_task_frontier_certificate_fixed_prefix_per_scoreinfo;
	uint64_t phase7_post_v5_3_task_frontier_certificate_gpu_consumer_reduces_before_host_transfer;
	uint64_t phase7_post_v5_3_task_frontier_certificate_rows;
	uint64_t phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts;
	uint64_t phase7_post_v5_3_task_frontier_certificate_reference_align_attempts;
	uint64_t phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts;
	uint64_t phase7_post_v5_3_task_frontier_certificate_v5_candidate_align_attempts;
	uint64_t phase7_post_v5_3_task_frontier_certificate_descriptor_false_negatives;
	uint64_t phase7_post_v5_3_task_frontier_certificate_missing_required_attempts;
	uint64_t phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_task_frontier_certificate_cpu_align_authority;
	uint64_t phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_task_frontier_certificate_digest_match;
	uint64_t phase7_post_v5_3_task_frontier_certificate_full_rows_equal;
	uint64_t phase7_post_v5_3_task_frontier_certificate_missing_rows;
	uint64_t phase7_post_v5_3_task_frontier_certificate_extra_rows;
	uint64_t phase7_post_v5_3_task_frontier_certificate_triplex_mismatches;
	uint64_t phase7_post_v5_3_task_frontier_certificate_gate_first1_pass;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_requested;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_active;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_tasks;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_host_assisted;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_source_is_v5_descriptors;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_consumer_reduces_before_host_transfer;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_host_selected_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_prefix_descriptor_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_reference_align_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_v5_candidate_align_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts_less_than_v5;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_descriptor_false_negatives;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_missing_required_attempts;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_cpu_align_authority;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_digest_match;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_full_rows_equal;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_missing_rows;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_extra_rows;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_triplex_mismatches;
	uint64_t phase7_post_v5_3_host_assisted_consumer_feasibility_gate_first1_pass;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_requested;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_active;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_source_is_pre_scoreinfo;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_source_is_legacy_byte_cuda;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_gpu_output_authority;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_runtime_reduction_enabled;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_proof_search_rows;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_task_count;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_scoreinfo_count;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_attempt_count;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_label_source_cpu_authority_external_output;
	uint64_t phase7_post_v5_3_pre_d2h_proof_search_gate_first1_export_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_requested;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_scoreinfo_tasks;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_candidate_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_replay_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_replay_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_baseline_cpu_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_false_negatives;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_required_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_rows;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_extra_rows;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_triplex_mismatches;
	uint64_t phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_tasks;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_candidate_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_replay_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_selected_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_replay_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_cpu_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_certificate_false_negatives;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_required_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_full_rows_equal;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_digest_match;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_rows;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_extra_rows;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_triplex_mismatches;
	double phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_candidate_wall_seconds;
	double phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_wall_seconds;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_work_drop_path;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_final_cpu_output_membership_required;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_task_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_scoreinfo_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_attempt_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_scoreinfo_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_attempt_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_certificate_false_negatives;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_required_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_full_rows_equal;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_digest_match;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_work_drop_path;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_final_cpu_output_membership_required;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_task_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_scoreinfo_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_attempt_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_scoreinfo_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_attempt_count;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_false_negatives;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_missing_required_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_cert_engine_first1_shadow;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_work_drop;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_d2h;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_scoreinfo_groups;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_attempt_frontier_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_selected_replay_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_scoreinfo_groups;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_replay_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_baseline_cpu_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_false_negatives;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_required_attempts;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_align_side_reduced;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_full_rows_equal;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_digest_match;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_rows;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_extra_rows;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_triplex_mismatches;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_pass;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_requested;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_states;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_attempt_frontier_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_replay_frontier_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_scoreinfo_groups;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_replay_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_baseline_cpu_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_produced_before_work_drop;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_consumed_before_cpu_replay_selection;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_false_negatives;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_required_attempts;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_align_side_reduced;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_full_rows_equal;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_digest_match;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_rows;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_extra_rows;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_triplex_mismatches;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_pass;
	uint64_t phase7_full_align_verifier_first1_shadow_requested;
	uint64_t phase7_full_align_verifier_first1_shadow_active;
	uint64_t phase7_full_align_verifier_first1_shadow_descriptors;
	uint64_t phase7_full_align_verifier_first1_shadow_proposals;
	uint64_t phase7_full_align_verifier_first1_shadow_proposal_failures;
	uint64_t phase7_full_align_verifier_first1_shadow_verifier_pass;
	uint64_t phase7_full_align_verifier_first1_shadow_verifier_fail;
	uint64_t phase7_full_align_verifier_first1_shadow_cpu_align_fallbacks;
	uint64_t phase7_full_align_verifier_first1_shadow_score_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_endpoint_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_cigar_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_full_row_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_digest_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_full_rows_equal;
	uint64_t phase7_full_align_verifier_first1_shadow_digest_match;
	uint64_t phase7_full_align_verifier_first1_shadow_missing_rows;
	uint64_t phase7_full_align_verifier_first1_shadow_extra_rows;
	uint64_t phase7_full_align_verifier_first1_shadow_triplex_mismatches;
	uint64_t phase7_full_align_verifier_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_full_align_verifier_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_full_align_verifier_first1_shadow_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_full_align_verifier_first1_shadow_gpu_output_digest_authority;
	uint64_t phase7_full_align_verifier_first1_shadow_cpu_align_authority;
	uint64_t phase7_full_align_verifier_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_full_align_verifier_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_requested;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_active;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_native_scoreinfo_tiles;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_forward_endpoint_witnesses;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_witnesses;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_traceback_cigar_witnesses;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_certificates;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_certificate_false_negatives;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_missing_required_attempts;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_byte_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_endpoint_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_cigar_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_full_row_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_mismatches;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_full_rows_equal;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_match;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_fallbacks;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_align_side_reduced;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_accounting_clean;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_score_authority;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_endpoint_authority;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_cigar_traceback_output_authority;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_output_digest_authority;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_pass;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_requested;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_active;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_descriptors;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_certificates;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_reject_candidates_shadow;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_would_reject_scoreinfo_groups;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_would_reject_align_attempts;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_certificate_false_negatives;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_groups;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_attempts;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_unsupported_descriptors;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_align_side_reduced;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_digest_match;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gpu_score_authority;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gpu_endpoint_authority;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gpu_cigar_traceback_output_authority;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gpu_output_digest_authority;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_pass;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_requested;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_active;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_unique_keys;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_duplicate_units;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_align_unique_keys;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_align_duplicate_attempts;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_key_collisions;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_key_validation_mismatches;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_unsupported_key_descriptors;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_fallback_to_full_cpu_replay;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_prealign_reduced;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_align_side_reduced;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_reduction_enabled;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_work_drop_enabled;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_score_authority;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_endpoint_authority;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_cigar_traceback_output_authority;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_output_digest_authority;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_shadow_pass;
	uint64_t phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_pass;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_conservative_fallback_groups;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_cpu_align_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gpu_endpoint_cigar_traceback_output_authority;
	uint64_t phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass;
	uint64_t phase7_v3_oracle_min_cover_replay_requested;
	uint64_t phase7_v3_oracle_min_cover_replay_active;
	uint64_t phase7_v3_oracle_min_cover_replay_tasks;
	uint64_t phase7_v3_oracle_min_cover_replay_reference_align_attempts;
	uint64_t phase7_v3_oracle_min_cover_replay_candidate_align_attempts;
	uint64_t phase7_v3_oracle_min_cover_replay_candidate_min_cover_positions;
	uint64_t phase7_v3_oracle_min_cover_replay_skipped_attempts;
	uint64_t longtarget_task_batches;
	uint64_t longtarget_task_batch_tasks;
	uint64_t longtarget_task_batch_scoreinfos;
	uint64_t length_guard_fallbacks;
	uint64_t length_guard_last_query_len;
	uint64_t length_guard_max_query_len;
	uint64_t length_guard_last_target_len;
	uint64_t length_guard_max_target_len;
	int effective_streams;
	int effective_batch_size;
	bool score_prepass_enabled;
	double load_seconds;
	double init_seconds;
	double fill_seconds;
	double score_fill_seconds;
	double traceback_fill_seconds;
	double submit_seconds;
	double score_submit_seconds;
	double traceback_submit_seconds;
	double wait_seconds;
	double total_seconds;
	double score_wait_seconds;
	double traceback_wait_seconds;
	double score_poll_wait_seconds;
	double traceback_poll_wait_seconds;
	double score_result_copy_seconds;
	double traceback_result_copy_seconds;
	double traceback_cigar_vector_seconds;
	double traceback_cigar_string_seconds;
	uint64_t traceback_cigar_raw_ops;
	uint64_t traceback_cigar_merged_ops;
	double longtarget_attempt_build_seconds;
	double longtarget_score_select_seconds;
	double cpu_traceback_replay_seconds;
	double cpu_traceback_substr_seconds;
	double cpu_traceback_align_seconds;
	double cpu_traceback_convert_seconds;
};

struct FasimFastsimExtendScoreInfoTiming
{
	FasimFastsimExtendScoreInfoTiming() :
		scoreinfo_groups(0),
		align_attempts(0),
		attempt_probe_requested(0),
		attempt_probe_active(0),
		attempt_probe_calls(0),
		attempt_probe_attempts(0),
		attempt_probe_selected_attempts(0),
		attempt_probe_fallbacks(0),
		segmented_attempt_probe_requested(0),
		segmented_attempt_probe_active(0),
		segmented_attempt_probe_segments(0),
		segmented_attempt_probe_calls(0),
		segmented_attempt_probe_attempts(0),
		segmented_attempt_probe_selected_attempts(0),
		segmented_attempt_probe_fallbacks(0),
		phase3_cigar_nt_prefilter_active(0),
		phase3_cigar_nt_alignments_seen(0),
		phase3_cigar_nt_cigar_lt_ntmin(0),
		phase3_cigar_nt_legacy_nt_lt_ntmin(0),
		phase3_cigar_nt_agree_lt_ntmin(0),
		phase3_cigar_nt_disagree_lt_ntmin(0),
		phase3_cigar_nt_candidate_false_negative_rows(0),
		substr_seconds(0.0),
		align_seconds(0.0),
		convert_seconds(0.0),
		phase3_cigar_nt_convert_seconds_projected_saved(0.0),
		sort_seconds(0.0),
		filter_seconds(0.0),
		attempt_probe_seconds(0.0),
		segmented_attempt_probe_seconds(0.0),
		attempt_probe_error("none")
	{
	}

	uint64_t scoreinfo_groups;
	uint64_t align_attempts;
	uint64_t attempt_probe_requested;
	uint64_t attempt_probe_active;
	uint64_t attempt_probe_calls;
	uint64_t attempt_probe_attempts;
	uint64_t attempt_probe_selected_attempts;
	uint64_t attempt_probe_fallbacks;
	uint64_t segmented_attempt_probe_requested;
	uint64_t segmented_attempt_probe_active;
	uint64_t segmented_attempt_probe_segments;
	uint64_t segmented_attempt_probe_calls;
	uint64_t segmented_attempt_probe_attempts;
	uint64_t segmented_attempt_probe_selected_attempts;
	uint64_t segmented_attempt_probe_fallbacks;
	uint64_t phase3_cigar_nt_prefilter_active;
	uint64_t phase3_cigar_nt_alignments_seen;
	uint64_t phase3_cigar_nt_cigar_lt_ntmin;
	uint64_t phase3_cigar_nt_legacy_nt_lt_ntmin;
	uint64_t phase3_cigar_nt_agree_lt_ntmin;
	uint64_t phase3_cigar_nt_disagree_lt_ntmin;
	uint64_t phase3_cigar_nt_candidate_false_negative_rows;
	double substr_seconds;
	double align_seconds;
	double convert_seconds;
	double phase3_cigar_nt_convert_seconds_projected_saved;
	double sort_seconds;
	double filter_seconds;
	double attempt_probe_seconds;
	double segmented_attempt_probe_seconds;
	std::string attempt_probe_error;
};

struct FasimGasal2Attempt
{
	FasimGasal2Attempt() :
		scoreinfo_index(0),
		cutlength(0),
		start(0),
		prealign_score(0),
		target_end_required_for_fallback(0),
		nt_min_length(0),
		target_global_start(-1),
		output_global_start(-1),
		output_global_end(-1),
		task_strand(-1),
		task_para(-1),
		task_rule(-1),
		target_source(NULL),
		target_offset(0),
		target_length(0)
	{
	}

	int scoreinfo_index;
	int cutlength;
	int start;
	int prealign_score;
	int target_end_required_for_fallback;
	int nt_min_length;
	int64_t target_global_start;
	int64_t output_global_start;
	int64_t output_global_end;
	int task_strand;
	int task_para;
	int task_rule;
	const std::string *target_source;
	size_t target_offset;
	size_t target_length;
	std::string target;

	void set_target_view(const std::string *source, size_t offset, size_t length)
	{
		target_source = source;
		target_offset = offset;
		target_length = length;
		target.clear();
	}

	const char *target_data() const
	{
		return target_source != NULL ? target_source->data() + target_offset : target.data();
	}

	size_t target_size() const
	{
		return target_source != NULL ? target_length : target.size();
	}

	bool uses_target_view() const
	{
		return target_source != NULL;
	}
};

struct FasimGasal2SelectedAlignment
{
	FasimGasal2SelectedAlignment() :
		scoreinfo_index(0),
		cutlength(0),
		start(0),
		score_prepass_score(0),
		score_prepass_query_end(-1),
		score_prepass_ref_end(-1),
		score_prepass_threshold_candidate(false),
		score_prepass_fallback_candidate(false),
		selected(false)
	{
	}

	int scoreinfo_index;
	int cutlength;
	int start;
	int score_prepass_score;
	int score_prepass_query_end;
	int score_prepass_ref_end;
	bool score_prepass_threshold_candidate;
	bool score_prepass_fallback_candidate;
	bool selected;
	StripedSmithWaterman::Alignment alignment;
};

struct FasimGasal2ScoreOnlyAlignment
{
	FasimGasal2ScoreOnlyAlignment() :
		scoreinfo_index(0),
		cutlength(0),
		start(0),
		prealign_score(0),
		score(0),
		query_end(-1),
		ref_end(-1)
	{
	}

	int scoreinfo_index;
	int cutlength;
	int start;
	int prealign_score;
	int score;
	int query_end;
	int ref_end;
};

struct FasimGasal2LongQuerySegment
{
	FasimGasal2LongQuerySegment() :
		global_query_start(0),
		global_query_end(0),
		query_segment()
	{
	}

	size_t global_query_start;
	size_t global_query_end;
	std::string query_segment;
};

struct FasimGasal2LongQueryShadowStats
{
	FasimGasal2LongQueryShadowStats() :
		requested(0),
		active(0),
		query_len(0),
		tile_len(0),
		tile_overlap(0),
		segments(0),
		gasal2_requests(0),
		traceback_requests(0),
		fallbacks(0),
		scoreinfo_max_per_task(0),
		scoreinfo_input_groups(0),
		scoreinfo_kept_groups(0),
		scoreinfo_pruned_groups(0),
		total_seconds(0.0)
	{
	}

	uint64_t requested;
	uint64_t active;
	uint64_t query_len;
	uint64_t tile_len;
	uint64_t tile_overlap;
	uint64_t segments;
	uint64_t gasal2_requests;
	uint64_t traceback_requests;
	uint64_t fallbacks;
	uint64_t scoreinfo_max_per_task;
	uint64_t scoreinfo_input_groups;
	uint64_t scoreinfo_kept_groups;
	uint64_t scoreinfo_pruned_groups;
	double total_seconds;
};

struct FasimGasal2LongQueryExactTileShadowStats
{
	FasimGasal2LongQueryExactTileShadowStats() :
		requested(0),
		active(0),
		query_len(0),
		tile_len(0),
		tile_overlap(0),
		tiles(0),
		tile_descriptors(0),
		tile_max_query_len(0),
		tile_descriptor_digest(0),
		cpu_oracle_candidates(0),
		tile_candidates(0),
		candidate_missing(0),
		candidate_extra(0),
		position_missing(0),
		position_extra(0),
		position_score_mismatches(0),
		fallback(0),
		total_seconds(0.0)
	{
	}

	uint64_t requested;
	uint64_t active;
	uint64_t query_len;
	uint64_t tile_len;
	uint64_t tile_overlap;
	uint64_t tiles;
	uint64_t tile_descriptors;
	uint64_t tile_max_query_len;
	uint64_t tile_descriptor_digest;
	uint64_t cpu_oracle_candidates;
	uint64_t tile_candidates;
	uint64_t candidate_missing;
	uint64_t candidate_extra;
	uint64_t position_missing;
	uint64_t position_extra;
	uint64_t position_score_mismatches;
	uint64_t fallback;
	double total_seconds;
};

struct FasimLongQueryExactColumnScoreInfoShadowStats
{
	FasimLongQueryExactColumnScoreInfoShadowStats() :
		requested(0),
		active(0),
		query_len(0),
		tasks(0),
		cells(0),
		gpu_batches(0),
		gpu_tasks(0),
		overflow_batches(0),
		fallback_batches(0),
		scoreinfo_mismatches(0),
		gpu_scoreinfo_groups(0),
		cpu_scoreinfo_groups(0),
		max_per_task(0),
		required_smem_bytes(0),
		default_smem_limit_bytes(0),
		optin_smem_limit_bytes(0),
		resource_fit(0),
		smem_optin_requested(0),
		smem_optin_active(0),
		total_seconds(0.0),
		kernel_seconds(0.0),
		h2d_seconds(0.0),
		d2h_seconds(0.0),
		error("none")
	{
	}

	uint64_t requested;
	uint64_t active;
	uint64_t query_len;
	uint64_t tasks;
	uint64_t cells;
	uint64_t gpu_batches;
	uint64_t gpu_tasks;
	uint64_t overflow_batches;
	uint64_t fallback_batches;
	uint64_t scoreinfo_mismatches;
	uint64_t gpu_scoreinfo_groups;
	uint64_t cpu_scoreinfo_groups;
	uint64_t max_per_task;
	uint64_t required_smem_bytes;
	uint64_t default_smem_limit_bytes;
	uint64_t optin_smem_limit_bytes;
	uint64_t resource_fit;
	uint64_t smem_optin_requested;
	uint64_t smem_optin_active;
	double total_seconds;
	double kernel_seconds;
	double h2d_seconds;
	double d2h_seconds;
	std::string error;
};

struct FasimLongQueryStreamingScoreInfoShadowStats
{
	FasimLongQueryStreamingScoreInfoShadowStats() :
		requested(0),
		active(0),
		query_len(0),
		stripe_len(0),
		stripes(0),
		tasks(0),
		cells(0),
		unsupported(0),
		gpu_batches(0),
		gpu_tasks(0),
			overflow_batches(0),
			fallback_batches(0),
			boundary_state_bytes(0),
			legacy_byte_shared(0),
			legacy_byte_shared_required_smem_bytes(0),
			legacy_byte_shared_default_smem_limit_bytes(0),
			legacy_byte_shared_optin_smem_limit_bytes(0),
			gpu_minscore_requested(0),
		gpu_minscore_active(0),
		gpu_minscore_hot(0),
		gpu_minscore_used(0),
		gpu_minscore_fallbacks(0),
		gpu_minscore_score_mismatches(0),
		gpu_minscore_min_score_mismatches(0),
		gpu_minscore_wall_seconds(0.0),
		gpu_minscore_kernel_seconds(0.0),
		gpu_minscore_h2d_seconds(0.0),
		gpu_minscore_d2h_seconds(0.0),
		fused_minscore_requested(0),
		fused_minscore_active(0),
		fused_minscore_used(0),
		fused_minscore_fallbacks(0),
		fused_minscore_score_mismatches(0),
		fused_minscore_min_score_mismatches(0),
		fused_minscore_kernel_seconds(0.0),
		fused_minscore_total_seconds(0.0),
		two_contract_requested(0),
		two_contract_active(0),
		two_contract_used(0),
		two_contract_fallbacks(0),
		two_contract_score_mismatches(0),
		two_contract_min_score_mismatches(0),
		two_contract_scoreinfo_mismatches(0),
		two_contract_total_seconds(0.0),
		two_contract_h2d_seconds(0.0),
		two_contract_kernel_seconds(0.0),
		two_contract_d2h_seconds(0.0),
			gpu_scoreinfo_groups(0),
		cpu_scoreinfo_groups(0),
		scoreinfo_mismatches(0),
		candidate_missing(0),
		candidate_extra(0),
		first_mismatch_task_index(-1),
		first_mismatch_global_task(-1),
		first_mismatch_diff_index(-1),
		first_mismatch_cpu_count(-1),
		first_mismatch_gpu_count(-1),
		first_mismatch_cpu_score(-1),
		first_mismatch_cpu_position(-1),
		first_mismatch_gpu_score(-1),
		first_mismatch_gpu_position(-1),
		first_mismatch_rule(-1),
		first_mismatch_strand(-1),
		first_mismatch_para(-1),
		first_mismatch_dna_start_pos(-1),
		first_mismatch_target_len(-1),
		first_mismatch_min_score(-1),
		first_mismatch_kind("none"),
		first_mismatch_column_window_start(-1),
		first_mismatch_cpu_column_window(""),
		first_mismatch_gpu_column_window(""),
		first_mismatch_scalar_column_window(""),
		pack_seconds(0.0),
		h2d_seconds(0.0),
		kernel_seconds(0.0),
		d2h_seconds(0.0),
		total_seconds(0.0),
		minscore_cache_hits(0),
		minscore_cache_misses(0),
		minscore_seconds(0.0),
		gpu_call_seconds(0.0),
		validation_seconds(0.0),
		validation_minscore_seconds(0.0),
		cpu_prealign_seconds(0.0),
		compare_seconds(0.0),
		realpath_requested(0),
		realpath_trust(0),
		realpath_used(0),
			realpath_fallbacks(0),
			realpath_extend_calls(0),
			realpath_extend_seconds(0.0),
			realpath_extend_scoreinfo_groups(0),
			realpath_extend_align_attempts(0),
			realpath_extend_attempt_probe_requested(0),
			realpath_extend_attempt_probe_active(0),
			realpath_extend_attempt_probe_calls(0),
			realpath_extend_attempt_probe_attempts(0),
			realpath_extend_attempt_probe_selected_attempts(0),
			realpath_extend_attempt_probe_fallbacks(0),
			realpath_extend_segmented_attempt_probe_requested(0),
			realpath_extend_segmented_attempt_probe_active(0),
			realpath_extend_segmented_attempt_probe_segments(0),
			realpath_extend_segmented_attempt_probe_calls(0),
		realpath_extend_segmented_attempt_probe_attempts(0),
		realpath_extend_segmented_attempt_probe_selected_attempts(0),
		realpath_extend_segmented_attempt_probe_fallbacks(0),
		realpath_extend_flush_segmented_attempt_probe_requested(0),
		realpath_extend_flush_segmented_attempt_probe_active(0),
		realpath_extend_flush_segmented_attempt_probe_flushes(0),
		realpath_extend_flush_segmented_attempt_probe_segments(0),
		realpath_extend_flush_segmented_attempt_probe_calls(0),
		realpath_extend_flush_segmented_attempt_probe_attempts(0),
		realpath_extend_flush_segmented_attempt_probe_selected_attempts(0),
		realpath_extend_flush_segmented_attempt_probe_fallbacks(0),
		realpath_extend_flush_segmented_replay_probe_requested(0),
		realpath_extend_flush_segmented_replay_probe_active(0),
		realpath_extend_flush_segmented_replay_probe_tasks(0),
		realpath_extend_flush_segmented_replay_probe_selected_attempts(0),
		realpath_extend_flush_segmented_replay_probe_align_attempts(0),
		realpath_extend_flush_segmented_replay_probe_triplex_mismatches(0),
		realpath_extend_flush_segmented_replay_probe_fallbacks(0),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_task(-1),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index(-1),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count(-1),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count(-1),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key("none"),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key("none"),
		realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance("none"),
		realpath_extend_flush_segmented_selected_only_replay_probe_requested(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_active(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_tasks(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff(0),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task(-1),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind("none"),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index(-1),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count(-1),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count(-1),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key("none"),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key("none"),
		realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance("none"),
			realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes(0),
			realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo(0),
			realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks(0),
			realpath_extend_flush_segmented_selected_only_replay_probe_seconds(0.0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_requested(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_active(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task(-1),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind("none"),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index(-1),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count(-1),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count(-1),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key("none"),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key("none"),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance("none"),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance("none"),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks(0),
			realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds(0.0),
			realpath_extend_flush_full_replay_probe_requested(0),
		realpath_extend_flush_full_replay_probe_active(0),
		realpath_extend_flush_full_replay_probe_tasks(0),
		realpath_extend_flush_full_replay_probe_align_attempts(0),
		realpath_extend_flush_full_replay_probe_triplex_mismatches(0),
		realpath_extend_flush_full_replay_probe_fallbacks(0),
		realpath_extend_flush_full_replay_probe_seconds(0.0),
		realpath_extend_flush_oracle_replay_probe_requested(0),
		realpath_extend_flush_oracle_replay_probe_active(0),
		realpath_extend_flush_oracle_replay_probe_tasks(0),
		realpath_extend_flush_oracle_replay_probe_triplex_mismatches(0),
		realpath_extend_flush_oracle_replay_probe_seconds(0.0),
		score_prepass_state_machine_shadow_requested(0),
		score_prepass_state_machine_shadow_active(0),
		score_prepass_state_machine_shadow_tasks(0),
		score_prepass_state_machine_shadow_scoreinfos(0),
			score_prepass_state_machine_shadow_attempts(0),
			score_prepass_state_machine_shadow_selected_attempts(0),
			score_prepass_state_machine_shadow_cpu_align_attempts(0),
			score_prepass_state_machine_shadow_cpu_align_cache_requested(0),
			score_prepass_state_machine_shadow_cpu_align_cache_lookups(0),
			score_prepass_state_machine_shadow_cpu_align_cache_hits(0),
			score_prepass_state_machine_shadow_cpu_align_cache_misses(0),
			score_prepass_state_machine_shadow_cpu_align_cache_unique_keys(0),
			score_prepass_state_machine_shadow_gasal2_traceback_requested(0),
			score_prepass_state_machine_shadow_gasal2_traceback_attempts(0),
			score_prepass_state_machine_shadow_gasal2_traceback_selected(0),
			score_prepass_state_machine_shadow_gasal2_traceback_fallbacks(0),
			score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches(0),
			score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches(0),
			score_prepass_state_machine_shadow_gasal2_traceback_seconds(0.0),
			score_prepass_state_machine_shadow_segment_traceback_requested(0),
			score_prepass_state_machine_shadow_segment_traceback_attempts(0),
			score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches(0),
			score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches(0),
			score_prepass_state_machine_shadow_segment_traceback_missing_segment(0),
			score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment(0),
			score_prepass_state_machine_shadow_segment_traceback_score_mismatches(0),
			score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches(0),
			score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches(0),
			score_prepass_state_machine_shadow_segment_traceback_seconds(0.0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_requested(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_attempts(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches(0),
			score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len(0),
		score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit(0),
		score_prepass_state_machine_shadow_expanded_segment_traceback_seconds(0.0),
		score_prepass_state_machine_shadow_triplex_mismatches(0),
			score_prepass_state_machine_shadow_candidate_coverage_requested(0),
			score_prepass_state_machine_shadow_candidate_coverage_active(0),
			score_prepass_state_machine_shadow_candidate_coverage_scoreinfos(0),
			score_prepass_state_machine_shadow_candidate_coverage_attempts(0),
			score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts(0),
			score_prepass_state_machine_shadow_candidate_coverage_selected(0),
			score_prepass_state_machine_shadow_candidate_coverage_covered(0),
			score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos(0),
			score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task(-1),
			score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo(-1),
			score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason("none"),
			score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts(0),
			score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds(0.0),
			score_prepass_state_machine_shadow_first_mismatch_task(-1),
		score_prepass_state_machine_shadow_first_mismatch_source("none"),
		score_prepass_state_machine_shadow_first_mismatch_kind("none"),
		score_prepass_state_machine_shadow_score_seconds(0.0),
		score_prepass_state_machine_shadow_select_seconds(0.0),
		score_prepass_state_machine_shadow_cpu_align_seconds(0.0),
		score_prepass_state_machine_shadow_convert_seconds(0.0),
		score_prepass_state_machine_shadow_total_seconds(0.0),
		score_prepass_state_machine_shadow_fallbacks(0),
		realpath_extend_substr_seconds(0.0),
		realpath_extend_align_seconds(0.0),
		realpath_extend_convert_seconds(0.0),
		realpath_extend_sort_seconds(0.0),
			realpath_extend_filter_seconds(0.0),
		realpath_extend_attempt_probe_seconds(0.0),
		realpath_extend_segmented_attempt_probe_seconds(0.0),
		realpath_extend_flush_segmented_attempt_probe_seconds(0.0),
		realpath_extend_flush_segmented_replay_probe_seconds(0.0),
		realpath_extend_attempt_probe_error("none"),
			realpath_digest_authority("cpu_validated"),
			decision("streaming_scoreinfo_shadow_not_requested"),
		fused_minscore_error("none"),
		two_contract_error("none"),
		gpu_minscore_error("none"),
		error("none")
	{
	}

	uint64_t requested;
	uint64_t active;
	uint64_t query_len;
	uint64_t stripe_len;
	uint64_t stripes;
	uint64_t tasks;
	uint64_t cells;
	uint64_t unsupported;
	uint64_t gpu_batches;
	uint64_t gpu_tasks;
		uint64_t overflow_batches;
		uint64_t fallback_batches;
			uint64_t boundary_state_bytes;
			uint64_t legacy_byte_shared;
			uint64_t legacy_byte_shared_required_smem_bytes;
			uint64_t legacy_byte_shared_default_smem_limit_bytes;
			uint64_t legacy_byte_shared_optin_smem_limit_bytes;
			uint64_t gpu_minscore_requested;
		uint64_t gpu_minscore_active;
		uint64_t gpu_minscore_hot;
		uint64_t gpu_minscore_used;
		uint64_t gpu_minscore_fallbacks;
		uint64_t gpu_minscore_score_mismatches;
		uint64_t gpu_minscore_min_score_mismatches;
		double gpu_minscore_wall_seconds;
		double gpu_minscore_kernel_seconds;
		double gpu_minscore_h2d_seconds;
		double gpu_minscore_d2h_seconds;
		uint64_t fused_minscore_requested;
		uint64_t fused_minscore_active;
		uint64_t fused_minscore_used;
		uint64_t fused_minscore_fallbacks;
		uint64_t fused_minscore_score_mismatches;
		uint64_t fused_minscore_min_score_mismatches;
		double fused_minscore_kernel_seconds;
		double fused_minscore_total_seconds;
		uint64_t two_contract_requested;
		uint64_t two_contract_active;
		uint64_t two_contract_used;
		uint64_t two_contract_fallbacks;
		uint64_t two_contract_score_mismatches;
		uint64_t two_contract_min_score_mismatches;
		uint64_t two_contract_scoreinfo_mismatches;
		double two_contract_total_seconds;
		double two_contract_h2d_seconds;
		double two_contract_kernel_seconds;
		double two_contract_d2h_seconds;
		uint64_t gpu_scoreinfo_groups;
	uint64_t cpu_scoreinfo_groups;
	uint64_t scoreinfo_mismatches;
	uint64_t candidate_missing;
	uint64_t candidate_extra;
	int64_t first_mismatch_task_index;
	int64_t first_mismatch_global_task;
	int64_t first_mismatch_diff_index;
	int64_t first_mismatch_cpu_count;
	int64_t first_mismatch_gpu_count;
	int64_t first_mismatch_cpu_score;
	int64_t first_mismatch_cpu_position;
	int64_t first_mismatch_gpu_score;
	int64_t first_mismatch_gpu_position;
	int64_t first_mismatch_rule;
	int64_t first_mismatch_strand;
	int64_t first_mismatch_para;
	int64_t first_mismatch_dna_start_pos;
	int64_t first_mismatch_target_len;
	int64_t first_mismatch_min_score;
	std::string first_mismatch_kind;
	int64_t first_mismatch_column_window_start;
	std::string first_mismatch_cpu_column_window;
	std::string first_mismatch_gpu_column_window;
	std::string first_mismatch_scalar_column_window;
	double pack_seconds;
	double h2d_seconds;
	double kernel_seconds;
	double d2h_seconds;
	double total_seconds;
	uint64_t minscore_cache_hits;
	uint64_t minscore_cache_misses;
	double minscore_seconds;
	double gpu_call_seconds;
	double validation_seconds;
	double validation_minscore_seconds;
	double cpu_prealign_seconds;
	double compare_seconds;
	uint64_t realpath_requested;
	uint64_t realpath_trust;
	uint64_t realpath_used;
	uint64_t realpath_fallbacks;
	uint64_t realpath_extend_calls;
	double realpath_extend_seconds;
	uint64_t realpath_extend_scoreinfo_groups;
	uint64_t realpath_extend_align_attempts;
	uint64_t realpath_extend_attempt_probe_requested;
	uint64_t realpath_extend_attempt_probe_active;
	uint64_t realpath_extend_attempt_probe_calls;
	uint64_t realpath_extend_attempt_probe_attempts;
	uint64_t realpath_extend_attempt_probe_selected_attempts;
	uint64_t realpath_extend_attempt_probe_fallbacks;
	uint64_t realpath_extend_segmented_attempt_probe_requested;
	uint64_t realpath_extend_segmented_attempt_probe_active;
	uint64_t realpath_extend_segmented_attempt_probe_segments;
	uint64_t realpath_extend_segmented_attempt_probe_calls;
	uint64_t realpath_extend_segmented_attempt_probe_attempts;
	uint64_t realpath_extend_segmented_attempt_probe_selected_attempts;
	uint64_t realpath_extend_segmented_attempt_probe_fallbacks;
	uint64_t realpath_extend_flush_segmented_attempt_probe_requested;
	uint64_t realpath_extend_flush_segmented_attempt_probe_active;
	uint64_t realpath_extend_flush_segmented_attempt_probe_flushes;
	uint64_t realpath_extend_flush_segmented_attempt_probe_segments;
	uint64_t realpath_extend_flush_segmented_attempt_probe_calls;
	uint64_t realpath_extend_flush_segmented_attempt_probe_attempts;
	uint64_t realpath_extend_flush_segmented_attempt_probe_selected_attempts;
	uint64_t realpath_extend_flush_segmented_attempt_probe_fallbacks;
	uint64_t realpath_extend_flush_segmented_replay_probe_requested;
	uint64_t realpath_extend_flush_segmented_replay_probe_active;
	uint64_t realpath_extend_flush_segmented_replay_probe_tasks;
	uint64_t realpath_extend_flush_segmented_replay_probe_selected_attempts;
	uint64_t realpath_extend_flush_segmented_replay_probe_align_attempts;
	uint64_t realpath_extend_flush_segmented_replay_probe_triplex_mismatches;
	uint64_t realpath_extend_flush_segmented_replay_probe_fallbacks;
	int64_t realpath_extend_flush_segmented_replay_probe_first_mismatch_task;
	int64_t realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index;
	int64_t realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count;
	int64_t realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count;
	std::string realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key;
	std::string realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key;
	std::string realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_requested;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_active;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_tasks;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff;
	int64_t realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task;
	std::string realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind;
	int64_t realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index;
	int64_t realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count;
	int64_t realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count;
	std::string realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key;
	std::string realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key;
	std::string realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes;
	uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo;
		uint64_t realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks;
		double realpath_extend_flush_segmented_selected_only_replay_probe_seconds;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_requested;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_active;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff;
		int64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task;
		std::string realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind;
		int64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index;
		int64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count;
		int64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count;
		std::string realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key;
		std::string realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key;
		std::string realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance;
		std::string realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance;
		uint64_t realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks;
		double realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds;
		uint64_t realpath_extend_flush_full_replay_probe_requested;
	uint64_t realpath_extend_flush_full_replay_probe_active;
	uint64_t realpath_extend_flush_full_replay_probe_tasks;
	uint64_t realpath_extend_flush_full_replay_probe_align_attempts;
	uint64_t realpath_extend_flush_full_replay_probe_triplex_mismatches;
	uint64_t realpath_extend_flush_full_replay_probe_fallbacks;
	double realpath_extend_flush_full_replay_probe_seconds;
	uint64_t realpath_extend_flush_oracle_replay_probe_requested;
	uint64_t realpath_extend_flush_oracle_replay_probe_active;
	uint64_t realpath_extend_flush_oracle_replay_probe_tasks;
	uint64_t realpath_extend_flush_oracle_replay_probe_triplex_mismatches;
	double realpath_extend_flush_oracle_replay_probe_seconds;
	uint64_t score_prepass_state_machine_shadow_requested;
	uint64_t score_prepass_state_machine_shadow_active;
	uint64_t score_prepass_state_machine_shadow_tasks;
	uint64_t score_prepass_state_machine_shadow_scoreinfos;
		uint64_t score_prepass_state_machine_shadow_attempts;
		uint64_t score_prepass_state_machine_shadow_selected_attempts;
		uint64_t score_prepass_state_machine_shadow_cpu_align_attempts;
		uint64_t score_prepass_state_machine_shadow_cpu_align_cache_requested;
		uint64_t score_prepass_state_machine_shadow_cpu_align_cache_lookups;
		uint64_t score_prepass_state_machine_shadow_cpu_align_cache_hits;
		uint64_t score_prepass_state_machine_shadow_cpu_align_cache_misses;
		uint64_t score_prepass_state_machine_shadow_cpu_align_cache_unique_keys;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_requested;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_attempts;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_selected;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_fallbacks;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches;
		uint64_t score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches;
		double score_prepass_state_machine_shadow_gasal2_traceback_seconds;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_requested;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_attempts;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_missing_segment;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_score_mismatches;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches;
		uint64_t score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches;
		double score_prepass_state_machine_shadow_segment_traceback_seconds;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_requested;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_attempts;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len;
		uint64_t score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit;
		double score_prepass_state_machine_shadow_expanded_segment_traceback_seconds;
		uint64_t score_prepass_state_machine_shadow_triplex_mismatches;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_requested;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_active;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_scoreinfos;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_attempts;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_selected;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_covered;
			uint64_t score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos;
		int64_t score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task;
		int64_t score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo;
		std::string score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason;
		uint64_t score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts;
		double score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds;
		int64_t score_prepass_state_machine_shadow_first_mismatch_task;
	std::string score_prepass_state_machine_shadow_first_mismatch_source;
	std::string score_prepass_state_machine_shadow_first_mismatch_kind;
	double score_prepass_state_machine_shadow_score_seconds;
	double score_prepass_state_machine_shadow_select_seconds;
	double score_prepass_state_machine_shadow_cpu_align_seconds;
	double score_prepass_state_machine_shadow_convert_seconds;
	double score_prepass_state_machine_shadow_total_seconds;
	uint64_t score_prepass_state_machine_shadow_fallbacks;
	double realpath_extend_substr_seconds;
	double realpath_extend_align_seconds;
	double realpath_extend_convert_seconds;
	double realpath_extend_sort_seconds;
	double realpath_extend_filter_seconds;
	double realpath_extend_attempt_probe_seconds;
	double realpath_extend_segmented_attempt_probe_seconds;
	double realpath_extend_flush_segmented_attempt_probe_seconds;
	double realpath_extend_flush_segmented_replay_probe_seconds;
	std::string realpath_extend_attempt_probe_error;
	std::string realpath_digest_authority;
	std::string decision;
	std::string fused_minscore_error;
	std::string two_contract_error;
	std::string gpu_minscore_error;
	std::string error;
};

bool fasim_gasal2_is_built();
bool fasim_gasal2_enabled();
bool fasim_gasal2_longtarget_bridge_enabled();
FasimGasal2Stats fasim_gasal2_snapshot_stats();
void fasim_gasal2_print_stats();
std::vector<FasimGasal2LongQuerySegment>
fasim_build_gasal2_long_query_segments(const std::string &query,
                                       size_t tile_len,
                                       size_t overlap,
                                       size_t max_segments);
void fasim_gasal2_record_longtarget_task_batch(uint64_t tasks,
                                               uint64_t scoreInfos);
void fasim_gasal2_record_cpu_traceback_replay(uint64_t replayAttempts,
                                              uint64_t selectedAttempts);
void fasim_gasal2_record_cpu_traceback_aligns(uint64_t alignCalls,
                                              uint64_t skippedAfterEmit,
                                              uint64_t rankCutoffSkipped);
void fasim_gasal2_record_cpu_traceback_outcomes(uint64_t thresholdEmits,
                                                uint64_t bestFallbackEmits,
                                                uint64_t lastEmits,
                                                uint64_t thresholdCandidates,
                                                uint64_t fallbackCandidates,
                                                uint64_t lastCandidates,
                                                uint64_t rank1Emits,
                                                uint64_t rank2Emits,
                                                uint64_t rank3Emits,
                                                uint64_t rank4PlusEmits);
void fasim_gasal2_record_longtarget_bridge_timing(double attemptBuildSeconds,
                                                  double scoreSelectSeconds,
                                                  double cpuReplaySeconds,
                                                  double cpuSubstrSeconds,
                                                  double cpuAlignSeconds,
                                                  double cpuConvertSeconds);

bool fasim_gasal2_align_attempts(const std::string &query,
                                 const std::vector<FasimGasal2Attempt> &attempts,
                                 std::vector<FasimGasal2SelectedAlignment> *selected,
                                 std::string *errorOut);

bool fasim_gasal2_select_attempts(const std::string &query,
                                  const std::vector<FasimGasal2Attempt> &attempts,
                                  std::vector<FasimGasal2SelectedAlignment> *selected,
                                  std::string *errorOut);

bool fasim_gasal2_select_attempt_indexes_from_scores(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<size_t> *selectedAttemptIndexes,
	std::string *errorOut);

bool fasim_gasal2_score_attempts(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<FasimGasal2ScoreOnlyAlignment> *scores,
	std::string *errorOut);

void fasim_gasal2_record_attempt_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t attempts,
	const char *decision);
void fasim_gasal2_record_attempt_consumer_shadow_replay(
	uint64_t selectedAttempts,
	uint64_t cpuAlignAttempts,
	double cpuAlignSeconds,
	double convertSeconds,
	double totalSeconds,
	bool active,
	const char *decision);
void fasim_gasal2_record_attempt_consumer_shadow_comparison(
	uint64_t mismatches,
	uint64_t missing,
	uint64_t extra,
	const char *firstMismatch,
	bool digestMatch,
	bool fullRowsEqual,
	const char *decision);

void fasim_gasal2_record_emission_only_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t scoredAttempts,
	const char *decision);
void fasim_gasal2_record_emission_only_consumer_shadow_result(
	uint64_t thresholdEmits,
	uint64_t terminalEmits,
	uint64_t lastEmits,
	uint64_t emptyEmits,
	uint64_t cpuAlignAttempts,
	uint64_t realpathReferenceAlignAttempts,
	double scoreSeconds,
	double selectSeconds,
	double cpuAlignSeconds,
	double convertSeconds,
	double totalSeconds,
	bool active,
	const char *decision);
void fasim_gasal2_record_emission_only_consumer_shadow_comparison(
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes,
	const char *firstMismatch,
	bool digestMatch,
	bool fullRowsEqual,
	const char *decision);

void fasim_gasal2_record_phase7_next_reducer_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t candidateAttempts,
	bool active);
void fasim_gasal2_record_phase7_next_reducer_result(
	uint64_t candidateAlignAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t falseNegativeScoreInfos,
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes);

void fasim_gasal2_record_phase7_frontier_log_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t alignAttempts,
	uint64_t triplexes,
	bool active,
	const char *path,
	const char *digest);

void fasim_gasal2_record_phase7_frontier_early_stop(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t skippedAttempts,
	uint64_t emittedGroups,
	uint64_t fallbackGroups,
	bool active);

void fasim_gasal2_record_phase7_all_attempt_early_stop(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t skippedAttempts,
	uint64_t emittedGroups,
	uint64_t fallbackGroups,
	bool active);

void fasim_gasal2_record_phase7_gate_c(
	uint64_t tasks,
	uint64_t oracleScoreInfos,
	uint64_t oracleAttempts,
	uint64_t gpuCandidateScoreInfos,
	uint64_t gpuCandidateAttempts,
	uint64_t falseNegativeScoreInfos,
	uint64_t missingRequiredAttempts,
	uint64_t extraCandidateAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t gateBCandidateAlignAttempts,
	double scoreInfoCpuSeconds,
	double gpuCandidateSeconds,
	double cpuReplaySeconds,
	double totalSeconds,
	uint64_t digestMatch,
	uint64_t fullRowsEqual,
	bool active);

void fasim_gasal2_record_phase7_v3_descriptor_source(
	uint64_t tasks,
	uint64_t referenceScoreInfos,
	uint64_t referenceAttempts,
	uint64_t candidateScoreInfos,
	uint64_t candidateAttempts,
	uint64_t candidateMinCoverPositions,
	uint64_t cpuScoreInfoCalls,
	uint64_t baselineCpuScoreInfoCalls,
	bool cpuScoreInfoReduced,
	bool candidateCertificateChecked,
	uint64_t candidateCertificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool preScoreInfoSource,
	bool afterCpuScoreInfoSource,
	bool active);
void fasim_gasal2_record_phase7_v3_oracle_min_cover_replay(
	uint64_t tasks,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t candidateMinCoverPositions,
	bool active);

bool fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime();
bool fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_runtime();
bool fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_runtime();
bool fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_runtime();
bool fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime();
bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_runtime();
bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime();
bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime();
bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime();
bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime();
bool fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime();
bool fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime();
bool fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime();
bool fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime();
bool fasim_gasal2_phase7_gpu_upper_bound_reject_first1_shadow_runtime();
bool fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime();
void fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer(
	uint64_t tasks,
	uint64_t referenceScoreInfos,
	uint64_t referenceAttempts,
	uint64_t gpuDescriptorScoreInfos,
	uint64_t gpuDescriptorAttempts,
	uint64_t falseNegatives,
	uint64_t missingRequiredAttempts,
	uint64_t extraDescriptorAttempts,
	bool scoreInfoPrealignReduced,
	bool cpuAlignAuthority,
	bool gateV51Pass);
bool fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime();
bool fasim_gasal2_phase7_v5_cpu_authority_replay_runtime();
void fasim_gasal2_record_phase7_v5_true_pre_scoreinfo_descriptor_source(
	uint64_t tasks,
	uint64_t referenceScoreInfos,
	uint64_t referenceAttempts,
	uint64_t gpuDescriptorScoreInfos,
	uint64_t gpuDescriptorAttempts,
	bool sourceIsPreScoreInfo,
	bool scoreInfoPrealignReduced,
	uint64_t falseNegatives,
	uint64_t missingRequiredAttempts,
	bool candidateAttemptsBelowAllColumnReplayScale,
	bool cpuAlignAuthority,
	bool gateV51Pass);
void fasim_gasal2_record_phase7_v5_cpu_authority_replay(
	uint64_t tasks,
	uint64_t gpuDescriptorScoreInfos,
	uint64_t gpuDescriptorAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	bool sourceIsPreScoreInfo,
	bool scoreInfoPrealignReduced,
	uint64_t falseNegatives,
	uint64_t missingRequiredAttempts,
	bool cpuAlignAuthority,
	bool fullRowsEqual,
	bool digestMatch,
	uint64_t missingRows,
	uint64_t extraRows,
	uint64_t triplexMismatches,
	bool gateV52Pass);
void fasim_gasal2_record_phase7_post_v5_3_gpu_consumer_summary(
	uint64_t tasks,
	bool sourceIsPreScoreInfo,
	uint64_t gpuConsumerSummaryRows,
	bool gpuConsumerReducesBeforeHostTransfer,
	bool usesPrefixBoundaryOrEquivalentReplayProof,
	bool arbitrarySparseSubset,
	bool firstDescriptorPerScoreInfo,
	uint64_t gpuSelectedAttempts,
	uint64_t selectedPrefixAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t v5CandidateAlignAttempts,
	bool scoreInfoPrealignReduced,
	bool alignSideReduced,
	uint64_t descriptorFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool fallbackAccountingClean,
	bool cpuAlignAuthority,
	bool digestMatch,
	bool fullRowsEqual,
	uint64_t missingRows,
	uint64_t extraRows,
	uint64_t triplexMismatches,
	bool gateFirst1Pass);
void fasim_gasal2_record_phase7_post_v5_3_task_frontier_certificate_requested();
void fasim_gasal2_record_phase7_post_v5_3_task_frontier_certificate(
	uint64_t tasks,
	bool active,
	bool sourceIsPreScoreInfo,
	bool sourceIsLegacyByteCuda,
	bool gasal2ScoreOnlyLongQueryDependency,
	bool usesTaskFrontierCertificate,
	bool usesPrefixBoundaryOnly,
	bool arbitrarySparseSubset,
	bool firstDescriptorPerScoreInfo,
	bool fixedPrefixPerScoreInfo,
	bool gpuConsumerReducesBeforeHostTransfer,
	uint64_t taskFrontierCertificateRows,
	uint64_t gpuSelectedAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t v5CandidateAlignAttempts,
	uint64_t descriptorFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool fallbackAccountingClean,
	bool cpuAlignAuthority,
	bool digestMatch,
	bool fullRowsEqual,
	uint64_t missingRows,
	uint64_t extraRows,
	uint64_t triplexMismatches,
	bool gateFirst1Pass);
void fasim_gasal2_record_phase7_post_v5_3_pre_d2h_proof_search_requested();
void fasim_gasal2_record_phase7_post_v5_3_pre_d2h_proof_search(
	uint64_t tasks,
	bool active,
	bool sourceIsPreScoreInfo,
	bool sourceIsLegacyByteCuda,
	uint64_t proofSearchRows,
	uint64_t scoreInfoCount,
	uint64_t attemptCount,
	bool cpuAlignAuthority,
	bool labelSourceCpuAuthorityExternalOutput,
	bool gateFirst1ExportPass);
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested();
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested();
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source(
	uint64_t sourceTaskCount,
	uint64_t sourceScoreInfoCount,
	uint64_t sourceAttemptCount,
	uint64_t referenceScoreInfoCount,
	uint64_t referenceAttemptCount,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool realCertificateSource,
	bool sourceIsPreDrop,
	bool sourceIsLegacyByteCuda,
	bool fallbackAccountingClean,
	bool cpuAlignAuthority,
	bool gateFirst1SourcePass);
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested();
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow(
	uint64_t sourceTaskCount,
	uint64_t sourceScoreInfoCount,
	uint64_t sourceAttemptCount,
	uint64_t referenceScoreInfoCount,
	uint64_t referenceAttemptCount,
	uint64_t candidateProofFalseNegatives,
	uint64_t candidateProofMissingRequiredAttempts,
	bool realCertificateSource,
	bool proofMustNotUseTop5OnlyContract,
	bool proofMustCoverCompleteRowSet,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested();
void fasim_gasal2_record_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow(
	uint64_t gpuScoreInfoGroups,
	uint64_t gpuAttemptFrontierAttempts,
	uint64_t gpuSelectedReplayAttempts,
	uint64_t cpuReplayAttempts,
	uint64_t baselineCpuAttempts,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool realCertificateSource,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested();
void fasim_gasal2_record_phase7_gpu_owned_scoreinfo_consumer_first1_shadow(
	uint64_t gpuOwnedScoreInfoStates,
	uint64_t gpuOwnedAttemptFrontierAttempts,
	uint64_t gpuOwnedReplayFrontierAttempts,
	uint64_t cpuReplayAttempts,
	uint64_t baselineCpuAttempts,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool active,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_full_align_verifier_first1_shadow_requested();
void fasim_gasal2_record_phase7_full_align_verifier_first1_shadow(
	uint64_t descriptors,
	uint64_t proposals,
	uint64_t proposalFailures,
	uint64_t verifierPass,
	uint64_t verifierFail,
	uint64_t cpuAlignFallbacks,
	uint64_t scoreMismatches,
	uint64_t endpointMismatches,
	uint64_t cigarMismatches,
	uint64_t fullRowMismatches,
	uint64_t digestMismatches,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_native_cuda_fasim_dp_engine_first1_shadow_requested();
void fasim_gasal2_record_phase7_native_cuda_fasim_dp_engine_first1_shadow(
	uint64_t nativeScoreInfoTiles,
	uint64_t forwardEndpointWitnesses,
	uint64_t reverseStartWitnesses,
	uint64_t tracebackCigarWitnesses,
	uint64_t certificates,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	uint64_t cpuAlignFallbacks,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_gpu_upper_bound_reject_first1_shadow_requested();
void fasim_gasal2_record_phase7_gpu_upper_bound_reject_first1_shadow(
	uint64_t upperBoundDescriptors,
	uint64_t upperBoundCertificates,
	uint64_t rejectCandidatesShadow,
	uint64_t wouldRejectScoreInfoGroups,
	uint64_t wouldRejectAlignAttempts,
	uint64_t certificateFalseNegatives,
	uint64_t baselineRowsInRejectedGroups,
	uint64_t baselineRowsInRejectedAttempts,
	uint64_t unsupportedDescriptors,
	bool fullRowsEqual,
	bool digestMatch,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow_requested();
void fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow(
	uint64_t scoreInfoKeyDescriptors,
	uint64_t scoreInfoUniqueKeys,
	uint64_t scoreInfoDuplicateUnits,
	uint64_t alignKeyDescriptors,
	uint64_t alignUniqueKeys,
	uint64_t alignDuplicateAttempts,
	uint64_t keyCollisions,
	uint64_t cpuKeyValidationMismatches,
	uint64_t unsupportedKeyDescriptors,
	bool fullRowsEqual,
	bool digestMatch,
	bool cpuAlignAuthority);
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow(
	uint64_t gpuScoreInfoTasks,
	uint64_t gpuCandidateGroups,
	uint64_t gpuReplayAttempts,
	uint64_t gpuSkippedGroups,
	uint64_t gpuSkippedAttempts,
	uint64_t cpuReplayAttempts,
	uint64_t baselineCpuAttempts,
	bool missingCertificateProducer,
	bool certificateValidBeforeD2h,
	bool finalCpuOutputMembershipRequiredForCertificate,
	bool fallbackOnMissingBound,
	bool fallbackToFullCpuReplay,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool scoreInfoPrealignReduced,
	bool alignSideReduced,
	bool fallbackAccountingClean,
	bool cpuAlignAuthority,
	bool fullRowsEqual,
	bool digestMatch,
	uint64_t missingRows,
	uint64_t extraRows,
	uint64_t triplexMismatches,
	bool gateFirst1Pass);
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested();
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested();
void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_producer_first1_pass(
	uint64_t skippedGroups,
	uint64_t skippedAttempts,
	uint64_t conservativeFallbackGroups,
	uint64_t skippedScoreInfoUpperBoundScore,
	uint64_t skippedAttemptUpperBoundScore,
	uint64_t skippedAttemptUpperBoundNt,
	uint64_t skippedAttemptUpperBoundIdentity,
	uint64_t skippedAttemptUpperBoundStability,
	uint64_t taskOutputCapacityExhausted,
	uint64_t scoreInfoLocalBreakState);
void fasim_gasal2_record_phase7_post_v5_3_host_assisted_consumer_feasibility(
	uint64_t tasks,
	bool active,
	bool hostAssisted,
	bool sourceIsV5Descriptors,
	bool gpuConsumerReducesBeforeHostTransfer,
	uint64_t hostSelectedAttempts,
	uint64_t prefixDescriptorAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t v5CandidateAlignAttempts,
	bool candidateAlignAttemptsLessThanV5,
	uint64_t descriptorFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool fallbackAccountingClean,
	bool cpuAlignAuthority,
	bool digestMatch,
	bool fullRowsEqual,
	uint64_t missingRows,
	uint64_t extraRows,
	uint64_t triplexMismatches,
	bool gateFirst1Pass);

bool fasim_gasal2_select_attempts_strict(const std::string &query,
                                         const std::vector<FasimGasal2Attempt> &attempts,
                                         std::vector<FasimGasal2SelectedAlignment> *selected,
                                         std::string *errorOut);

#endif
