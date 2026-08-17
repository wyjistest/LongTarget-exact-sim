#include "gasal2_align_bridge.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>

bool fasim_gasal2_is_built()
{
	return false;
}

bool fasim_gasal2_enabled()
{
	const char *env = std::getenv("FASIM_ALIGN_GASAL2");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
	return env != NULL && env[0] != '\0' && env[0] != '0';
}

static bool fasim_gasal2_env_enabled(const char *name)
{
	const char *env = std::getenv(name);
	return env != NULL && env[0] != '\0' && env[0] != '0';
}

bool fasim_gasal2_longtarget_bridge_enabled()
{
	const char *env = std::getenv("FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW");
	if (env != NULL && env[0] != '\0' && env[0] != '0')
	{
		return true;
	}
	env = std::getenv("FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
	return env != NULL && env[0] != '\0' && env[0] != '0';
}

std::vector<FasimGasal2LongQuerySegment>
fasim_build_gasal2_long_query_segments(const std::string &query,
                                       size_t tile_len,
                                       size_t overlap,
                                       size_t max_segments)
{
	std::vector<FasimGasal2LongQuerySegment> segments;
	if (query.empty() || tile_len == 0 || overlap >= tile_len)
	{
		return segments;
	}

	const size_t step = tile_len - overlap;
	for (size_t start = 0; start < query.size(); start += step)
	{
		if (max_segments > 0 && segments.size() >= max_segments)
		{
			break;
		}
		const size_t end = std::min(query.size(), start + tile_len);
		FasimGasal2LongQuerySegment segment;
		segment.global_query_start = start;
		segment.global_query_end = end;
		segment.query_segment.assign(query.data() + start, end - start);
		segments.push_back(segment);
		if (end >= query.size())
		{
			break;
		}
	}
	return segments;
}

FasimGasal2Stats fasim_gasal2_snapshot_stats()
{
	FasimGasal2Stats stats;
	stats.enabled = fasim_gasal2_enabled();
	stats.built = false;
	if (fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime())
	{
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime())
	{
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_work_drop_path = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_final_cpu_output_membership_required = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority = 1;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass = 0;
		stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime())
	{
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested = 1;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_work_drop_path = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_final_cpu_output_membership_required = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract = 1;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract = 1;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority = 1;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass = 0;
		stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime())
	{
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested = 1;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_cert_engine_first1_shadow = 1;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_work_drop = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_d2h = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_scoreinfo_groups = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_attempts = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_align_side_reduced = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_accounting_clean = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority = 1;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_full_rows_equal = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_digest_match = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_rows = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_extra_rows = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_triplex_mismatches = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_shadow_pass = 0;
		stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime())
	{
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested = 1;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_requested = 1;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_scoreinfo_groups = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_attempts = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_produced_before_work_drop = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_consumed_before_cpu_replay_selection = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_accounting_clean = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_align_side_reduced = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority = 1;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_full_rows_equal = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_digest_match = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_rows = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_extra_rows = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_triplex_mismatches = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass = 0;
		stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime())
	{
		stats.phase7_full_align_verifier_first1_shadow_requested = 1;
		stats.phase7_full_align_verifier_first1_shadow_active = 0;
		stats.phase7_full_align_verifier_first1_shadow_descriptors = 0;
		stats.phase7_full_align_verifier_first1_shadow_proposals = 0;
		stats.phase7_full_align_verifier_first1_shadow_proposal_failures = 0;
		stats.phase7_full_align_verifier_first1_shadow_verifier_pass = 0;
		stats.phase7_full_align_verifier_first1_shadow_verifier_fail = 0;
		stats.phase7_full_align_verifier_first1_shadow_cpu_align_fallbacks = 0;
		stats.phase7_full_align_verifier_first1_shadow_score_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_endpoint_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_cigar_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_full_row_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_digest_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_full_rows_equal = 0;
		stats.phase7_full_align_verifier_first1_shadow_digest_match = 0;
		stats.phase7_full_align_verifier_first1_shadow_missing_rows = 0;
		stats.phase7_full_align_verifier_first1_shadow_extra_rows = 0;
		stats.phase7_full_align_verifier_first1_shadow_triplex_mismatches = 0;
		stats.phase7_full_align_verifier_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_full_align_verifier_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_full_align_verifier_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
		stats.phase7_full_align_verifier_first1_shadow_gpu_output_digest_authority = 0;
		stats.phase7_full_align_verifier_first1_shadow_cpu_align_authority = 1;
		stats.phase7_full_align_verifier_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_full_align_verifier_first1_shadow_gate_first1_shadow_pass = 0;
	}
	if (fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime())
	{
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_requested = 1;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_active = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_native_scoreinfo_tiles = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_forward_endpoint_witnesses = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_witnesses = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_traceback_cigar_witnesses = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificates = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificate_false_negatives = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_missing_required_attempts = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_byte_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_endpoint_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cigar_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_row_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_mismatches = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_rows_equal = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_match = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_fallbacks = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_align_side_reduced = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_accounting_clean = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority = 1;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_score_authority = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_endpoint_authority = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_cigar_traceback_output_authority = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_output_digest_authority = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_shadow_pass = 0;
		stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_gpu_upper_bound_reject_first1_shadow_runtime())
	{
		stats.phase7_gpu_upper_bound_reject_first1_shadow_requested = 1;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_active = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_descriptors = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_certificates = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_reject_candidates_shadow = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_scoreinfo_groups = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_align_attempts = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_certificate_false_negatives = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_groups = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_attempts = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_unsupported_descriptors = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_align_side_reduced = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_digest_match = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority = 1;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_score_authority = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_endpoint_authority = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_cigar_traceback_output_authority = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_output_digest_authority = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_shadow_pass = 0;
		stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_pass = 0;
	}
	if (fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime())
	{
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_requested = 1;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_active = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_unique_keys = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_duplicate_units = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_unique_keys = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_duplicate_attempts = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_key_collisions = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_key_validation_mismatches = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_unsupported_key_descriptors = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_fallback_to_full_cpu_replay = 1;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_prealign_reduced = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_side_reduced = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_reduction_enabled = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_work_drop_enabled = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority = 1;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_score_authority = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_endpoint_authority = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_cigar_traceback_output_authority = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_output_digest_authority = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_shadow_pass = 0;
		stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_pass = 0;
	}
	return stats;
}

void fasim_gasal2_print_stats()
{
	const FasimGasal2Stats stats = fasim_gasal2_snapshot_stats();
	const char *top5PresetEnv = std::getenv("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
	const bool top5Preset = top5PresetEnv != NULL &&
	                        top5PresetEnv[0] != '\0' &&
	                        top5PresetEnv[0] != '0';
	std::cerr << "benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested=" << (top5Preset ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_enabled=" << (stats.enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_built=0\n";
	std::cerr << "benchmark.fasim_gasal2_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_batches=0\n";
	std::cerr << "benchmark.fasim_gasal2_fallbacks=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_batches=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_batches=0\n";
	std::cerr << "benchmark.fasim_gasal2_target_view_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_query_reuse_batches=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_query_reuse_saved_bytes=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_threshold=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_best_fallback=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_last=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_none=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank1=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank2=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank3=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank4plus=0\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_first_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_remaining_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_first_threshold=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_replay_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_align_calls=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_skipped_after_emit=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_rank_cutoff_skipped=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_threshold=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_best_fallback=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_last=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_threshold=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_fallback=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_last=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank1=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank2=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank3=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank4plus=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_decision=not_requested\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_score_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_select_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_convert_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_total_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_missing_triplexes=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_extra_triplexes=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_first_mismatch=none\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_fallbacks=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_decision=not_requested\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_scored_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_threshold_emits=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_terminal_emits=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_last_emits=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_empty_emits=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_realpath_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_align_attempt_reduction=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_score_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_select_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_convert_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_total_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_missing_triplexes=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_extra_triplexes=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_first_mismatch=none\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_fallbacks=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_requested=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_active=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_tasks=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_reference_attempts=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_attempts=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_false_negative_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_missing_triplexes=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_extra_triplexes=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_digest_match=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_baseline_wall_seconds=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_wall_seconds=0\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_vs_baseline=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_triplexes=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_path=\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_digest=\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_skipped_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_emitted_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_fallback_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_skipped_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_emitted_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_fallback_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_false_negative_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_extra_candidate_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gate_b_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_scoreinfo_cpu_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_cpu_replay_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_total_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_reference_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_reference_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_cpu_scoreinfo_calls=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_cpu_scoreinfo_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_certificate_checked=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_certificate_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_pre_scoreinfo_source=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_after_cpu_scoreinfo_source=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_reference_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_reference_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_gpu_descriptor_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_descriptor_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_missing_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_extra_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v5_cpu_authority_replay_gate_v5_2_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_source_is_pre_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_gpu_consumer_summary_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_gpu_consumer_reduces_before_host_transfer=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_uses_prefix_boundary_or_equivalent_replay_proof=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_arbitrary_sparse_subset=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_descriptor_per_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_gpu_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_selected_prefix_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_v5_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_align_side_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_descriptor_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_missing_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_extra_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_gasal2_score_only_long_query_dependency=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_uses_prefix_boundary_only=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_arbitrary_sparse_subset=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_descriptor_per_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_fixed_prefix_per_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_gpu_consumer_reduces_before_host_transfer=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_task_frontier_certificate_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_reference_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_v5_candidate_align_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_descriptor_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_missing_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_extra_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_gate_first1_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_source_is_pre_scoreinfo=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_source_is_legacy_byte_cuda=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_gpu_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime_reduction_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_proof_search_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_task_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_scoreinfo_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_attempt_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_label_source_cpu_authority_external_output=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_gate_first1_export_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_scoreinfo_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_candidate_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_replay_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_replay_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_baseline_cpu_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_extra_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass=0\n";
	const bool realSourceFirst1ShadowRequested =
		fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime();
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested="
	          << (realSourceFirst1ShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_fasim_runtime_certificate_source=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_fasim_runtime_work_drop_path=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_candidate_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_replay_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_selected_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_skipped_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_replay_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_cpu_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate="
	          << (realSourceFirst1ShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay="
	          << (realSourceFirst1ShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_certificate_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority="
	          << (realSourceFirst1ShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_extra_rows=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_triplex_mismatches=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_candidate_wall_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_baseline_wall_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass=0\n";
	const bool realSourceCertificateSourceRequested =
		fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime();
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested="
	          << (realSourceCertificateSourceRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_fasim_runtime_certificate_source=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_fasim_runtime_work_drop_path=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_candidate_uses_final_cpu_output_as_runtime_proof=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_task_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_scoreinfo_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_attempt_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_scoreinfo_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_attempt_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_certificate_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass=0\n";
	const bool preDropProofFirst1ShadowRequested =
		fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime();
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested="
	          << (preDropProofFirst1ShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_fasim_runtime_certificate_source=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_fasim_runtime_work_drop_path=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_uses_final_cpu_output_as_runtime_proof=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_proof_must_not_use_top5_only_contract=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_proof_must_cover_complete_row_set=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_task_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_scoreinfo_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_attempt_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_scoreinfo_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_attempt_count=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority=1\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_conservative_fallback_groups=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_cpu_align_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gpu_endpoint_cigar_traceback_output_authority=0\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_requested=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_active=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_real_skip_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_pre_drop_proof_available=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_proof_version=phase6_exact_v1\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_candidates_considered=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_certified_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_uncertified_candidates=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_exact_descriptor_duplicate_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_static_span_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_score_endpoint_span_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_shadow_false_rejects=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_score_frontier_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_stability_frontier_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_nt_frontier_skips=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_tie_rescues=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_rank_aware_supported=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_probe_requests=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_probe_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_certificate_shadow_fallbacks=0\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batches=0\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batch_tasks=0\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batch_scoreinfos=0\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_fallbacks=0\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_last_query_len=0\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_max_query_len=0\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_last_target_len=0\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_max_target_len=0\n";
	std::cerr << "benchmark.fasim_gasal2_effective_streams=0\n";
	std::cerr << "benchmark.fasim_gasal2_effective_batch_size=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_enabled=0\n";
	std::cerr << "benchmark.fasim_gasal2_init_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_fill_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_submit_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_wait_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_wait_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_wait_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_poll_wait_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_poll_wait_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_score_result_copy_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_result_copy_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_attempt_build_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_score_select_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_replay_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_substr_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_align_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_convert_seconds=0\n";
	std::cerr << "benchmark.fasim_gasal2_total_seconds=0\n";
}

void fasim_gasal2_record_longtarget_task_batch(uint64_t tasks,
                                               uint64_t scoreInfos)
{
	(void)tasks;
	(void)scoreInfos;
}

bool fasim_gasal2_align_attempts(const std::string &query,
                                 const std::vector<FasimGasal2Attempt> &attempts,
                                 std::vector<FasimGasal2SelectedAlignment> *selected,
                                 std::string *errorOut)
{
	(void)query;
	(void)attempts;
	if (selected != NULL)
	{
		selected->clear();
	}
	if (errorOut != NULL)
	{
		*errorOut = "GASAL2 support not built";
	}
	return false;
}

bool fasim_gasal2_select_attempts(const std::string &query,
                                  const std::vector<FasimGasal2Attempt> &attempts,
                                  std::vector<FasimGasal2SelectedAlignment> *selected,
                                  std::string *errorOut)
{
	return fasim_gasal2_align_attempts(query, attempts, selected, errorOut);
}

bool fasim_gasal2_select_attempts_canonical_hybrid_v2(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<FasimGasal2SelectedAlignment> *selected,
	std::vector<FasimGasal2AttemptScoreTelemetry> *telemetry,
	std::string *errorOut)
{
	if (telemetry != NULL)
	{
		telemetry->clear();
	}
	return fasim_gasal2_align_attempts(query, attempts, selected, errorOut);
}

bool fasim_gasal2_select_attempt_indexes_from_scores(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<size_t> *selectedAttemptIndexes,
	std::string *errorOut)
{
	(void)query;
	(void)attempts;
	if (selectedAttemptIndexes != NULL)
	{
		selectedAttemptIndexes->clear();
	}
	if (errorOut != NULL)
	{
		*errorOut = "gasal2_unavailable";
	}
	return false;
}

bool fasim_gasal2_score_attempts(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<FasimGasal2ScoreOnlyAlignment> *scores,
	std::string *errorOut)
{
	(void)query;
	(void)attempts;
	if (scores != NULL)
	{
		scores->clear();
	}
	if (errorOut != NULL)
	{
		*errorOut = "gasal2_unavailable";
	}
	return false;
}

bool fasim_gasal2_streamed_attempt_score_v1(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	const FasimLongQueryScoringContract &scoringContract,
	std::vector<FasimGasal2StreamedAttemptScore> *scores,
	FasimGasal2StreamedAttemptScoreTelemetry *telemetry,
	std::string *errorOut)
{
	(void)query;
	(void)attempts;
	(void)scoringContract;
	if (scores != NULL)
	{
		scores->clear();
	}
	if (telemetry != NULL)
	{
		telemetry->error = "gasal2_unavailable";
	}
	if (errorOut != NULL)
	{
		*errorOut = "gasal2_unavailable";
	}
	return false;
}

bool fasim_gasal2_long_query_runtime_query_preflight_v1(
	size_t queryLength,
	const FasimLongQueryScoringContract &scoringContract,
	FasimLongQueryRuntimeDescriptor *descriptorOut,
	std::string *errorOut)
{
	if (descriptorOut == NULL)
	{
		if (errorOut != NULL) *errorOut = "missing_runtime_descriptor";
		return false;
	}
	*descriptorOut = FasimLongQueryRuntimeDescriptor();
	descriptorOut->query_length = static_cast<uint64_t>(queryLength);
	descriptorOut->scoring = scoringContract;
	descriptorOut->cuda_built = false;
	descriptorOut->decision = "prealign_cuda_not_built";
	if (errorOut != NULL) *errorOut = descriptorOut->decision;
	return false;
}

bool fasim_gasal2_consumer_spike_select_from_scores(
	const std::vector<FasimGasal2Attempt> &attempts,
	const std::vector<FasimGasal2ScoreOnlyAlignment> &scores,
	std::vector<size_t> *selectedAttemptIndexes,
	std::vector<std::string> *selectionReasons,
	std::string *errorOut)
{
	(void)attempts;
	(void)scores;
	if (selectedAttemptIndexes != NULL)
	{
		selectedAttemptIndexes->clear();
	}
	if (selectionReasons != NULL)
	{
		selectionReasons->clear();
	}
	if (errorOut != NULL)
	{
		*errorOut = "gasal2_unavailable";
	}
	return false;
}

void fasim_gasal2_record_attempt_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t attempts,
	const char *decision)
{
	(void)tasks;
	(void)scoreInfos;
	(void)attempts;
	(void)decision;
}

void fasim_gasal2_record_attempt_consumer_shadow_replay(
	uint64_t selectedAttempts,
	uint64_t cpuAlignAttempts,
	double cpuAlignSeconds,
	double convertSeconds,
	double totalSeconds,
	bool active,
	const char *decision)
{
	(void)selectedAttempts;
	(void)cpuAlignAttempts;
	(void)cpuAlignSeconds;
	(void)convertSeconds;
	(void)totalSeconds;
	(void)active;
	(void)decision;
}

void fasim_gasal2_record_attempt_consumer_shadow_comparison(
	uint64_t mismatches,
	uint64_t missing,
	uint64_t extra,
	const char *firstMismatch,
	bool digestMatch,
	bool fullRowsEqual,
	const char *decision)
{
	(void)mismatches;
	(void)missing;
	(void)extra;
	(void)firstMismatch;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)decision;
}

void fasim_gasal2_record_emission_only_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t scoredAttempts,
	const char *decision)
{
	(void)tasks;
	(void)scoreInfos;
	(void)scoredAttempts;
	(void)decision;
}

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
	const char *decision)
{
	(void)thresholdEmits;
	(void)terminalEmits;
	(void)lastEmits;
	(void)emptyEmits;
	(void)cpuAlignAttempts;
	(void)realpathReferenceAlignAttempts;
	(void)scoreSeconds;
	(void)selectSeconds;
	(void)cpuAlignSeconds;
	(void)convertSeconds;
	(void)totalSeconds;
	(void)active;
	(void)decision;
}

void fasim_gasal2_record_emission_only_consumer_shadow_comparison(
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes,
	const char *firstMismatch,
	bool digestMatch,
	bool fullRowsEqual,
	const char *decision)
{
	(void)triplexMismatches;
	(void)missingTriplexes;
	(void)extraTriplexes;
	(void)firstMismatch;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)decision;
}

void fasim_gasal2_record_phase7_next_reducer_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t candidateAttempts,
	bool active)
{
	(void)tasks;
	(void)scoreInfos;
	(void)candidateAttempts;
	(void)active;
}

void fasim_gasal2_record_phase7_next_reducer_result(
	uint64_t candidateAlignAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t falseNegativeScoreInfos,
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes)
{
	(void)candidateAlignAttempts;
	(void)referenceAlignAttempts;
	(void)falseNegativeScoreInfos;
	(void)triplexMismatches;
	(void)missingTriplexes;
	(void)extraTriplexes;
}

void fasim_gasal2_record_phase7_frontier_log_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t alignAttempts,
	uint64_t triplexes,
	bool active,
	const char *path,
	const char *digest)
{
	(void)tasks;
	(void)scoreInfos;
	(void)alignAttempts;
	(void)triplexes;
	(void)active;
	(void)path;
	(void)digest;
}

void fasim_gasal2_record_phase7_frontier_early_stop(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t skippedAttempts,
	uint64_t emittedGroups,
	uint64_t fallbackGroups,
	bool active)
{
	(void)tasks;
	(void)scoreInfos;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)skippedAttempts;
	(void)emittedGroups;
	(void)fallbackGroups;
	(void)active;
}

void fasim_gasal2_record_phase7_all_attempt_early_stop(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t skippedAttempts,
	uint64_t emittedGroups,
	uint64_t fallbackGroups,
	bool active)
{
	(void)tasks;
	(void)scoreInfos;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)skippedAttempts;
	(void)emittedGroups;
	(void)fallbackGroups;
	(void)active;
}

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
	bool active)
{
	(void)tasks;
	(void)oracleScoreInfos;
	(void)oracleAttempts;
	(void)gpuCandidateScoreInfos;
	(void)gpuCandidateAttempts;
	(void)falseNegativeScoreInfos;
	(void)missingRequiredAttempts;
	(void)extraCandidateAttempts;
	(void)candidateAlignAttempts;
	(void)gateBCandidateAlignAttempts;
	(void)scoreInfoCpuSeconds;
	(void)gpuCandidateSeconds;
	(void)cpuReplaySeconds;
	(void)totalSeconds;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)active;
}

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
	bool active)
{
	(void)tasks;
	(void)referenceScoreInfos;
	(void)referenceAttempts;
	(void)candidateScoreInfos;
	(void)candidateAttempts;
	(void)candidateMinCoverPositions;
	(void)cpuScoreInfoCalls;
	(void)baselineCpuScoreInfoCalls;
	(void)cpuScoreInfoReduced;
	(void)candidateCertificateChecked;
	(void)candidateCertificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)preScoreInfoSource;
	(void)afterCpuScoreInfoSource;
	(void)active;
}

bool fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_v5_cpu_authority_replay_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_runtime()
{
	return false;
}

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
	bool gateV51Pass)
{
	(void)tasks;
	(void)referenceScoreInfos;
	(void)referenceAttempts;
	(void)gpuDescriptorScoreInfos;
	(void)gpuDescriptorAttempts;
	(void)falseNegatives;
	(void)missingRequiredAttempts;
	(void)extraDescriptorAttempts;
	(void)scoreInfoPrealignReduced;
	(void)cpuAlignAuthority;
	(void)gateV51Pass;
}

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
	bool gateV51Pass)
{
	(void)tasks;
	(void)referenceScoreInfos;
	(void)referenceAttempts;
	(void)gpuDescriptorScoreInfos;
	(void)gpuDescriptorAttempts;
	(void)sourceIsPreScoreInfo;
	(void)scoreInfoPrealignReduced;
	(void)falseNegatives;
	(void)missingRequiredAttempts;
	(void)candidateAttemptsBelowAllColumnReplayScale;
	(void)cpuAlignAuthority;
	(void)gateV51Pass;
}

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
	bool gateV52Pass)
{
	(void)tasks;
	(void)gpuDescriptorScoreInfos;
	(void)gpuDescriptorAttempts;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)sourceIsPreScoreInfo;
	(void)scoreInfoPrealignReduced;
	(void)falseNegatives;
	(void)missingRequiredAttempts;
	(void)cpuAlignAuthority;
	(void)fullRowsEqual;
	(void)digestMatch;
	(void)missingRows;
	(void)extraRows;
	(void)triplexMismatches;
	(void)gateV52Pass;
}

void fasim_gasal2_record_phase7_v3_oracle_min_cover_replay(
	uint64_t tasks,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t candidateMinCoverPositions,
	bool active)
{
	(void)tasks;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)candidateMinCoverPositions;
	(void)active;
}

bool fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime()
{
	return false;
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_upper_bound_reject_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime()
{
	return fasim_gasal2_env_enabled(
		"FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
}

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
	bool gateFirst1Pass)
{
	(void)tasks;
	(void)sourceIsPreScoreInfo;
	(void)gpuConsumerSummaryRows;
	(void)gpuConsumerReducesBeforeHostTransfer;
	(void)usesPrefixBoundaryOrEquivalentReplayProof;
	(void)arbitrarySparseSubset;
	(void)firstDescriptorPerScoreInfo;
	(void)gpuSelectedAttempts;
	(void)selectedPrefixAttempts;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)v5CandidateAlignAttempts;
	(void)scoreInfoPrealignReduced;
	(void)alignSideReduced;
	(void)descriptorFalseNegatives;
	(void)missingRequiredAttempts;
	(void)fallbackAccountingClean;
	(void)cpuAlignAuthority;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)missingRows;
	(void)extraRows;
	(void)triplexMismatches;
	(void)gateFirst1Pass;
}

void fasim_gasal2_record_phase7_post_v5_3_task_frontier_certificate_requested()
{
}

void fasim_gasal2_record_phase7_post_v5_3_pre_d2h_proof_search_requested()
{
}

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
	bool gateFirst1Pass)
{
	(void)tasks;
	(void)active;
	(void)sourceIsPreScoreInfo;
	(void)sourceIsLegacyByteCuda;
	(void)gasal2ScoreOnlyLongQueryDependency;
	(void)usesTaskFrontierCertificate;
	(void)usesPrefixBoundaryOnly;
	(void)arbitrarySparseSubset;
	(void)firstDescriptorPerScoreInfo;
	(void)fixedPrefixPerScoreInfo;
	(void)gpuConsumerReducesBeforeHostTransfer;
	(void)taskFrontierCertificateRows;
	(void)gpuSelectedAttempts;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)v5CandidateAlignAttempts;
	(void)descriptorFalseNegatives;
	(void)missingRequiredAttempts;
	(void)fallbackAccountingClean;
	(void)cpuAlignAuthority;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)missingRows;
	(void)extraRows;
	(void)triplexMismatches;
	(void)gateFirst1Pass;
}

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
	bool gateFirst1ExportPass)
{
	(void)tasks;
	(void)active;
	(void)sourceIsPreScoreInfo;
	(void)sourceIsLegacyByteCuda;
	(void)proofSearchRows;
	(void)scoreInfoCount;
	(void)attemptCount;
	(void)cpuAlignAuthority;
	(void)labelSourceCpuAuthorityExternalOutput;
	(void)gateFirst1ExportPass;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested()
{
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_full_align_verifier_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_native_cuda_fasim_dp_engine_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_gpu_upper_bound_reject_first1_shadow_requested()
{
}

void fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow_requested()
{
}

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
	bool gateFirst1SourcePass)
{
	(void)sourceTaskCount;
	(void)sourceScoreInfoCount;
	(void)sourceAttemptCount;
	(void)referenceScoreInfoCount;
	(void)referenceAttemptCount;
	(void)certificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)realCertificateSource;
	(void)sourceIsPreDrop;
	(void)sourceIsLegacyByteCuda;
	(void)fallbackAccountingClean;
	(void)cpuAlignAuthority;
	(void)gateFirst1SourcePass;
}

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
	bool cpuAlignAuthority)
{
	(void)sourceTaskCount;
	(void)sourceScoreInfoCount;
	(void)sourceAttemptCount;
	(void)referenceScoreInfoCount;
	(void)referenceAttemptCount;
	(void)candidateProofFalseNegatives;
	(void)candidateProofMissingRequiredAttempts;
	(void)realCertificateSource;
	(void)proofMustNotUseTop5OnlyContract;
	(void)proofMustCoverCompleteRowSet;
	(void)cpuAlignAuthority;
}

void fasim_gasal2_record_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow(
	uint64_t gpuScoreInfoGroups,
	uint64_t gpuAttemptFrontierAttempts,
	uint64_t gpuSelectedReplayAttempts,
	uint64_t cpuReplayAttempts,
	uint64_t baselineCpuAttempts,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool realCertificateSource,
	bool cpuAlignAuthority)
{
	(void)gpuScoreInfoGroups;
	(void)gpuAttemptFrontierAttempts;
	(void)gpuSelectedReplayAttempts;
	(void)cpuReplayAttempts;
	(void)baselineCpuAttempts;
	(void)certificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)realCertificateSource;
	(void)cpuAlignAuthority;
}

void fasim_gasal2_record_phase7_gpu_owned_scoreinfo_consumer_first1_shadow(
	uint64_t gpuOwnedScoreInfoStates,
	uint64_t gpuOwnedAttemptFrontierAttempts,
	uint64_t gpuOwnedReplayFrontierAttempts,
	uint64_t cpuReplayAttempts,
	uint64_t baselineCpuAttempts,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	bool active,
	bool cpuAlignAuthority)
{
	(void)gpuOwnedScoreInfoStates;
	(void)gpuOwnedAttemptFrontierAttempts;
	(void)gpuOwnedReplayFrontierAttempts;
	(void)cpuReplayAttempts;
	(void)baselineCpuAttempts;
	(void)certificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)active;
	(void)cpuAlignAuthority;
}

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
	bool cpuAlignAuthority)
{
	(void)descriptors;
	(void)proposals;
	(void)proposalFailures;
	(void)verifierPass;
	(void)verifierFail;
	(void)cpuAlignFallbacks;
	(void)scoreMismatches;
	(void)endpointMismatches;
	(void)cigarMismatches;
	(void)fullRowMismatches;
	(void)digestMismatches;
	(void)cpuAlignAuthority;
}

void fasim_gasal2_record_phase7_native_cuda_fasim_dp_engine_first1_shadow(
	uint64_t nativeScoreInfoTiles,
	uint64_t forwardEndpointWitnesses,
	uint64_t reverseStartWitnesses,
	uint64_t tracebackCigarWitnesses,
	uint64_t certificates,
	uint64_t certificateFalseNegatives,
	uint64_t missingRequiredAttempts,
	uint64_t cpuAlignFallbacks,
	bool cpuAlignAuthority)
{
	(void)nativeScoreInfoTiles;
	(void)forwardEndpointWitnesses;
	(void)reverseStartWitnesses;
	(void)tracebackCigarWitnesses;
	(void)certificates;
	(void)certificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)cpuAlignFallbacks;
	(void)cpuAlignAuthority;
}

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
	bool cpuAlignAuthority)
{
	(void)upperBoundDescriptors;
	(void)upperBoundCertificates;
	(void)rejectCandidatesShadow;
	(void)wouldRejectScoreInfoGroups;
	(void)wouldRejectAlignAttempts;
	(void)certificateFalseNegatives;
	(void)baselineRowsInRejectedGroups;
	(void)baselineRowsInRejectedAttempts;
	(void)unsupportedDescriptors;
	(void)fullRowsEqual;
	(void)digestMatch;
	(void)cpuAlignAuthority;
}

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
	bool cpuAlignAuthority)
{
	(void)scoreInfoKeyDescriptors;
	(void)scoreInfoUniqueKeys;
	(void)scoreInfoDuplicateUnits;
	(void)alignKeyDescriptors;
	(void)alignUniqueKeys;
	(void)alignDuplicateAttempts;
	(void)keyCollisions;
	(void)cpuKeyValidationMismatches;
	(void)unsupportedKeyDescriptors;
	(void)fullRowsEqual;
	(void)digestMatch;
	(void)cpuAlignAuthority;
}

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
	bool gateFirst1Pass)
{
	(void)gpuScoreInfoTasks;
	(void)gpuCandidateGroups;
	(void)gpuReplayAttempts;
	(void)gpuSkippedGroups;
	(void)gpuSkippedAttempts;
	(void)cpuReplayAttempts;
	(void)baselineCpuAttempts;
	(void)missingCertificateProducer;
	(void)certificateValidBeforeD2h;
	(void)finalCpuOutputMembershipRequiredForCertificate;
	(void)fallbackOnMissingBound;
	(void)fallbackToFullCpuReplay;
	(void)certificateFalseNegatives;
	(void)missingRequiredAttempts;
	(void)scoreInfoPrealignReduced;
	(void)alignSideReduced;
	(void)fallbackAccountingClean;
	(void)cpuAlignAuthority;
	(void)fullRowsEqual;
	(void)digestMatch;
	(void)missingRows;
	(void)extraRows;
	(void)triplexMismatches;
	(void)gateFirst1Pass;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested()
{
}

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
	uint64_t scoreInfoLocalBreakState)
{
	(void)skippedGroups;
	(void)skippedAttempts;
	(void)conservativeFallbackGroups;
	(void)skippedScoreInfoUpperBoundScore;
	(void)skippedAttemptUpperBoundScore;
	(void)skippedAttemptUpperBoundNt;
	(void)skippedAttemptUpperBoundIdentity;
	(void)skippedAttemptUpperBoundStability;
	(void)taskOutputCapacityExhausted;
	(void)scoreInfoLocalBreakState;
}

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
	bool gateFirst1Pass)
{
	(void)tasks;
	(void)active;
	(void)hostAssisted;
	(void)sourceIsV5Descriptors;
	(void)gpuConsumerReducesBeforeHostTransfer;
	(void)hostSelectedAttempts;
	(void)prefixDescriptorAttempts;
	(void)referenceAlignAttempts;
	(void)candidateAlignAttempts;
	(void)v5CandidateAlignAttempts;
	(void)candidateAlignAttemptsLessThanV5;
	(void)descriptorFalseNegatives;
	(void)missingRequiredAttempts;
	(void)fallbackAccountingClean;
	(void)cpuAlignAuthority;
	(void)digestMatch;
	(void)fullRowsEqual;
	(void)missingRows;
	(void)extraRows;
	(void)triplexMismatches;
	(void)gateFirst1Pass;
}

void fasim_gasal2_record_cpu_traceback_replay(uint64_t replayAttempts,
                                              uint64_t selectedAttempts)
{
	(void)replayAttempts;
	(void)selectedAttempts;
}

void fasim_gasal2_record_cpu_traceback_aligns(uint64_t alignCalls,
                                              uint64_t skippedAfterEmit,
                                              uint64_t rankCutoffSkipped)
{
	(void)alignCalls;
	(void)skippedAfterEmit;
	(void)rankCutoffSkipped;
}

void fasim_gasal2_record_cpu_traceback_outcomes(uint64_t thresholdEmits,
                                                uint64_t bestFallbackEmits,
                                                uint64_t lastEmits,
                                                uint64_t thresholdCandidates,
                                                uint64_t fallbackCandidates,
                                                uint64_t lastCandidates,
                                                uint64_t rank1Emits,
                                                uint64_t rank2Emits,
                                                uint64_t rank3Emits,
                                                uint64_t rank4PlusEmits)
{
	(void)thresholdEmits;
	(void)bestFallbackEmits;
	(void)lastEmits;
	(void)thresholdCandidates;
	(void)fallbackCandidates;
	(void)lastCandidates;
	(void)rank1Emits;
	(void)rank2Emits;
	(void)rank3Emits;
	(void)rank4PlusEmits;
}

void fasim_gasal2_record_longtarget_bridge_timing(double attemptBuildSeconds,
                                                  double scoreSelectSeconds,
                                                  double cpuReplaySeconds,
                                                  double cpuSubstrSeconds,
                                                  double cpuAlignSeconds,
                                                  double cpuConvertSeconds)
{
	(void)attemptBuildSeconds;
	(void)scoreSelectSeconds;
	(void)cpuReplaySeconds;
	(void)cpuSubstrSeconds;
	(void)cpuAlignSeconds;
	(void)cpuConvertSeconds;
}
