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
		substr_seconds(0.0),
		align_seconds(0.0),
		convert_seconds(0.0),
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
	double substr_seconds;
	double align_seconds;
	double convert_seconds;
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

bool fasim_gasal2_select_attempts_strict(const std::string &query,
                                         const std::vector<FasimGasal2Attempt> &attempts,
                                         std::vector<FasimGasal2SelectedAlignment> *selected,
                                         std::string *errorOut);

#endif
