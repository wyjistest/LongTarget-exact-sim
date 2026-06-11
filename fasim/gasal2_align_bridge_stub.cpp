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
