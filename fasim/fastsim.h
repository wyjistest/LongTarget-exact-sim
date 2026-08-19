#include <iostream>
#include <string.h>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include <utility>
#include <numeric>
#include <chrono>
#include "ssw_cpp.h"
#include "ssw.h"
#include "ssw_oracle_trace.h"
#include "sim.h"
#include "gasal2_align_bridge.h"
#ifdef FASIM_WITH_SSW_CUDA_FORWARD_HYBRID
#include "ssw_cuda/ssw_cuda_forward_hybrid.h"
#endif
#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"
#define N 50
using std::string;
using std::cout;
using std::endl;
using std::ifstream;

class FasimAuthorityProfileScope
{
public:
	explicit FasimAuthorityProfileScope(fasim_authority_profile_stage stageValue) :
		stage(stageValue), active(fasim_authority_profile_enabled() != 0)
	{
		if (active)
		{
			fasim_authority_profile_enter(static_cast<uint8_t>(stage));
		}
	}

	~FasimAuthorityProfileScope()
	{
		if (active)
		{
			fasim_authority_profile_leave(static_cast<uint8_t>(stage));
		}
	}

private:
	fasim_authority_profile_stage stage;
	bool active;
};

inline bool fasim_prealign_cuda_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ENABLE_PREALIGN_CUDA");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_identity_rounds_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGN_GASAL2_IDENTITY_ROUNDS");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_tfosorted_cigar_archive_probe_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_TFOSORTED_CIGAR_ARCHIVE_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_tfosorted_compact_archive_probe_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_TFOSORTED_COMPACT_ARCHIVE_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_tfosorted_column_archive_probe_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE");
		const char* archiveFirstEnv = getenv("FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT");
		if ((env == NULL || env[0] == '\0') &&
		    (archiveFirstEnv == NULL || archiveFirstEnv[0] == '\0'))
		{
			return false;
		}
		return (env != NULL && env[0] != '\0' && env[0] != '0') ||
		       (archiveFirstEnv != NULL && archiveFirstEnv[0] != '\0' &&
		        archiveFirstEnv[0] != '0');
	}();
	return enabled;
}

inline int fasim_gasal2_min_attempts_runtime()
{
	static const int minAttempts = []()
	{
		const char* env = getenv("FASIM_ALIGN_GASAL2_MIN_ATTEMPTS");
		if (env == NULL || env[0] == '\0')
		{
			return 0;
		}
		const int value = atoi(env);
		return value > 0 ? value : 0;
	}();
	return minAttempts;
}

inline bool fasim_gasal2_cpu_traceback_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGN_GASAL2_CPU_TRACEBACK");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_cpu_traceback_all_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_ALL");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline int fasim_gasal2_fastsim_max_query_len_runtime()
{
	static const int maxQueryLen = []()
	{
		const char* env = getenv("FASIM_ALIGN_GASAL2_MAX_QUERY_LEN");
		if (env == NULL || env[0] == '\0')
		{
			return 2812;
		}
		const int value = atoi(env);
		return value > 0 ? value : 0;
	}();
	return maxQueryLen;
}

inline bool fasim_gasal2_fastsim_query_length_supported_runtime(size_t queryLen)
{
	const int maxQueryLen = fasim_gasal2_fastsim_max_query_len_runtime();
	return maxQueryLen <= 0 || queryLen <= static_cast<size_t>(maxQueryLen);
}

inline bool fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_cpu_authority_candidate_coverage_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_CPU_AUTHORITY_CANDIDATE_COVERAGE_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_cpu_authority_selected_only_coverage_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_CPU_AUTHORITY_SELECTED_ONLY_COVERAGE_SHADOW");
		if (env == NULL || env[0] == '\0') return false;
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_phase7_next_reducer_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_align_cache_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_gasal2_traceback_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_segment_traceback_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_score_prepass_state_machine_expanded_segment_traceback_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_attempt_consumer_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_spike_v1_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_V1");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_f1_scheduler_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_f1_continuation_profile_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv(
			"FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_PROFILE");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_f1_profile_reuse_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv(
			"FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_f1_host_profile_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv(
			"FASIM_LONG_QUERY_GPU_CONSUMER_F1_HOST_PROFILE");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

class FasimLongQueryGpuConsumerF1ContinuationProfileScope
{
public:
	explicit FasimLongQueryGpuConsumerF1ContinuationProfileScope(bool enabled) :
		active(enabled),
		priorContinuationProfile(
			StripedSmithWaterman::ForwardContinuationProfileEnabled()),
		priorInternalProfile(ssw_align_internal_stats_enabled())
	{
		if (active)
		{
			StripedSmithWaterman::ForwardContinuationProfileSetEnabled(true);
			ssw_align_internal_stats_set_enabled(1);
		}
	}

	~FasimLongQueryGpuConsumerF1ContinuationProfileScope()
	{
		if (active)
		{
			StripedSmithWaterman::ForwardContinuationProfileSetEnabled(
				priorContinuationProfile);
			ssw_align_internal_stats_set_enabled(priorInternalProfile);
		}
	}

private:
	bool active;
	bool priorContinuationProfile;
	uint8_t priorInternalProfile;
};

// Inputs for the global F1 round scheduler.  The pointers are borrowed for
// the duration of one call; the caller owns all strings and scoreInfo vectors.
struct FasimLongQueryGpuConsumerF1TaskInput
{
	FasimLongQueryGpuConsumerF1TaskInput() :
		target(NULL), source(NULL), dnaStartPos(0), strand(0), Para(0), rule(0),
		scoreInfo(NULL)
	{
	}
	const string *target;
	const string *source;
	long dnaStartPos;
	long strand;
	long Para;
	long rule;
	const std::vector<struct StripedSmithWaterman::scoreInfo> *scoreInfo;
};

inline bool fasim_long_query_gpu_consumer_cpu_continuation_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv(
			"FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_gpu_consumer_lazy_reverse_shadow_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv(
			"FASIM_LONG_QUERY_GPU_CONSUMER_LAZY_REVERSE_SHADOW");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_emission_only_consumer_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_emission_only_consumer_shadow_debug_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline size_t fasim_gasal2_emission_only_consumer_shadow_debug_limit_runtime()
{
	const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_LIMIT");
	if (env == NULL || env[0] == '\0' || env[0] == '-')
	{
		return 8;
	}
	const size_t limit = static_cast<size_t>(strtoul(env, NULL, 10));
	return limit > 128 ? static_cast<size_t>(128) : limit;
}

inline long fasim_gasal2_emission_only_consumer_shadow_debug_task_runtime()
{
	const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_TASK");
	if (env == NULL || env[0] == '\0')
	{
		return -1;
	}
	return strtol(env, NULL, 10);
}

inline long fasim_gasal2_emission_only_consumer_shadow_debug_scoreinfo_runtime()
{
	const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_SCOREINFO");
	if (env == NULL || env[0] == '\0')
	{
		return -1;
	}
	return strtol(env, NULL, 10);
}

inline bool fasim_gasal2_emission_only_consumer_shadow_no_gpu_terminal_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_NO_GPU_TERMINAL");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gasal2_emission_only_consumer_shadow_verify_terminal_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_VERIFY_TERMINAL");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_extend_attempt_probe_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_EXTEND_ATTEMPT_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_segmented_extend_attempt_probe_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_flush_segmented_extend_attempt_probe_runtime()
{
	static const bool enabled = []()
	{
		if (fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime())
		{
			return true;
		}
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_runtime()
{
	static const bool enabled = []()
	{
		if (fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime())
		{
			return true;
		}
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_flush_segmented_selected_only_replay_probe_runtime()
{
	static const bool enabled = []()
	{
		if (fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime())
		{
			return true;
		}
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_SELECTED_ONLY_REPLAY_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_flush_segmented_grouped_selected_replay_probe_runtime()
{
	static const bool enabled = []()
	{
		if (fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime())
		{
			return true;
		}
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_GROUPED_SELECTED_REPLAY_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_long_query_streaming_scoreinfo_flush_full_replay_probe_runtime()
{
	static const bool enabled = []()
	{
		if (fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime())
		{
			return true;
		}
		const char* env = getenv(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_FULL_REPLAY_PROBE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline size_t fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime()
{
	const char* env = getenv(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS");
	if (env == NULL || env[0] == '\0' || env[0] == '-')
	{
		return 0;
	}
	return static_cast<size_t>(strtoul(env, NULL, 10));
}

inline size_t fasim_long_query_streaming_scoreinfo_segmented_probe_tile_len_runtime()
{
	const char* env = getenv(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN");
	if (env == NULL || env[0] == '\0')
	{
		return 2812;
	}
	const unsigned long value = strtoul(env, NULL, 10);
	return value > 0 ? static_cast<size_t>(value) : static_cast<size_t>(2812);
}

inline size_t fasim_long_query_streaming_scoreinfo_segmented_probe_tile_overlap_runtime()
{
	const char* env = getenv(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP");
	if (env == NULL || env[0] == '\0' || env[0] == '-')
	{
		return 512;
	}
	return static_cast<size_t>(strtoul(env, NULL, 10));
}

inline size_t fasim_long_query_streaming_scoreinfo_segmented_probe_max_segments_runtime()
{
	const char* env = getenv(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS");
	if (env == NULL || env[0] == '\0' || env[0] == '-')
	{
		return 0;
	}
	return static_cast<size_t>(strtoul(env, NULL, 10));
}

inline void fasim_probe_gasal2_extend_attempts_from_scoreinfo(
	const std::string &query,
	const std::string &target,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	int ntMin,
	FasimFastsimExtendScoreInfoTiming *timing)
{
	if (timing == NULL ||
	    !fasim_long_query_streaming_scoreinfo_extend_attempt_probe_runtime())
	{
		return;
	}
	timing->attempt_probe_requested = 1;
	std::vector<FasimGasal2Attempt> attempts;
	attempts.reserve(finalScoreInfo.size() * 5);
	for (int i = 0; i < finalScoreInfo.size(); ++i)
	{
		float Iden = 0.6;
		while (Iden <= 1)
		{
			int cutlength =
				static_cast<int>(finalScoreInfo[i].score + 24) /
				(9 * Iden - 4) + 1;
			cutlength =
				finalScoreInfo[i].position - cutlength + 1 > 0 ?
				cutlength : finalScoreInfo[i].position + 1;
			const int start = finalScoreInfo[i].position - cutlength + 1;
			if (start >= 0 && cutlength > 0)
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = i;
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = finalScoreInfo[i].score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.set_target_view(&target,
				                        static_cast<size_t>(start),
				                        static_cast<size_t>(cutlength));
				attempts.push_back(attempt);
			}
			Iden += 0.1;
		}
	}
	timing->attempt_probe_attempts += static_cast<uint64_t>(attempts.size());
	if (attempts.empty())
	{
		timing->attempt_probe_error = "empty_attempts";
		return;
	}

	std::vector<FasimGasal2SelectedAlignment> selected;
	std::string error;
	const std::chrono::steady_clock::time_point probeStart =
		std::chrono::steady_clock::now();
	const bool ok = fasim_gasal2_select_attempts(query, attempts, &selected, &error);
	timing->attempt_probe_seconds +=
		std::chrono::duration<double>(
			std::chrono::steady_clock::now() - probeStart).count();
	++timing->attempt_probe_calls;
	if (ok)
	{
		timing->attempt_probe_active = 1;
		timing->attempt_probe_selected_attempts +=
			static_cast<uint64_t>(selected.size());
		timing->attempt_probe_error = "none";
	}
	else
	{
		++timing->attempt_probe_fallbacks;
		timing->attempt_probe_error = error.empty() ? "unknown" : error;
	}

	if (!fasim_long_query_streaming_scoreinfo_segmented_extend_attempt_probe_runtime())
	{
		return;
	}
	timing->segmented_attempt_probe_requested = 1;
	size_t tileLen =
		fasim_long_query_streaming_scoreinfo_segmented_probe_tile_len_runtime();
	size_t tileOverlap =
		fasim_long_query_streaming_scoreinfo_segmented_probe_tile_overlap_runtime();
	if (tileLen == 0)
	{
		tileLen = 2812;
	}
	if (tileOverlap >= tileLen)
	{
		tileOverlap = 0;
	}
	const std::vector<FasimGasal2LongQuerySegment> segments =
		fasim_build_gasal2_long_query_segments(
			query,
			tileLen,
			tileOverlap,
			fasim_long_query_streaming_scoreinfo_segmented_probe_max_segments_runtime());
	timing->segmented_attempt_probe_segments +=
		static_cast<uint64_t>(segments.size());
	if (segments.empty())
	{
		++timing->segmented_attempt_probe_fallbacks;
		return;
	}
	for (size_t segIndex = 0; segIndex < segments.size(); ++segIndex)
	{
		std::vector<FasimGasal2SelectedAlignment> segmentedSelected;
		std::string segmentedError;
		const std::chrono::steady_clock::time_point segmentedProbeStart =
			std::chrono::steady_clock::now();
		const bool segmentedOk =
			fasim_gasal2_select_attempts(segments[segIndex].query_segment,
			                            attempts,
			                            &segmentedSelected,
			                            &segmentedError);
		timing->segmented_attempt_probe_seconds +=
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - segmentedProbeStart).count();
		++timing->segmented_attempt_probe_calls;
		timing->segmented_attempt_probe_attempts +=
			static_cast<uint64_t>(attempts.size());
		if (segmentedOk)
		{
			timing->segmented_attempt_probe_active = 1;
			timing->segmented_attempt_probe_selected_attempts +=
				static_cast<uint64_t>(segmentedSelected.size());
		}
		else
		{
			++timing->segmented_attempt_probe_fallbacks;
		}
	}
}

inline int fasim_cuda_device_runtime()
{
	const char* env = getenv("FASIM_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	env = getenv("LONGTARGET_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	return -1;
}

inline int fasim_prealign_peak_suppress_bp_runtime()
{
	static const int suppressBp = []()
	{
		const char* env = getenv("FASIM_PREALIGN_PEAK_SUPPRESS_BP");
		if (env == NULL || env[0] == '\0')
		{
			return 5;
		}
		const int value = atoi(env);
		if (value <= 0)
		{
			return 5;
		}
		if (value > 1024)
		{
			return 1024;
		}
		return value;
	}();
	return suppressBp;
}

inline int fasim_prealign_cuda_topk_runtime()
{
	static const int topK = []()
	{
		const char* env = getenv("FASIM_PREALIGN_CUDA_TOPK");
		if (env == NULL || env[0] == '\0')
		{
			return 64;
		}
		int value = atoi(env);
		if (value <= 0)
		{
			return 64;
		}
		if (value > 256)
		{
			return 256;
		}
		return value;
	}();
	return topK;
}

inline uint8_t fasim_encode_base(unsigned char c)
{
	return prealign_shared_encode_base(c);
}

inline void fasim_build_query_profile(const string& query, int matchScore, int mismatchPenalty, std::vector<int16_t>& profile, int& segLenOut)
{
	prealign_shared_build_query_profile(query, matchScore, mismatchPenalty, profile, segLenOut);
}

struct mycutregion
{
	mycutregion() {};
	mycutregion(int ei, int ej) :start(ei), end(ej) {};
	int start;
	int end;
};

struct para
{
	string file1path;
	string file2path;
	string outpath;
	int corenum;
	int rule;
	int cutLength;
	int strand;
	int overlapLength;
	int minScore;
	bool detailOutput;
	bool doFastSim;
	int ntMin;
	int ntMax;
	float scoreMin;
	float minIdentity;
	float minStability;
	int penaltyT;
	int penaltyC;
	int cDistance;
	int cLength;
	// 2021-09-25 22:21:08: use this parameter to determine do fastSIM or not.
};

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src);

inline string fasim_cigar_probe_string(const std::vector<uint32_t> &cigar)
{
	std::ostringstream out;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		out << cigar_int_to_len(cigar[i]) << cigar_int_to_op(cigar[i]);
	}
	return out.str();
}

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut);

struct FasimConvertMaterializationPolicy
{
	FasimConvertMaterializationPolicy() :
		materialize_alignment_strings(true),
		materialize_cigar_probe_string(false),
		materialize_typed_cigar(false),
		materialize_gap_masks(false)
	{
	}

	bool materialize_alignment_strings;
	bool materialize_cigar_probe_string;
	bool materialize_typed_cigar;
	bool materialize_gap_masks;
};

struct FasimConvertedTriplexRecord
{
	FasimConvertedTriplexRecord() :
		stari(0),
		endi(0),
		starj(0),
		endj(0),
		strand(0),
		reverse(0),
		rule(0),
		score(0.0f),
		nt(0),
		identity(0.0f),
		tri_score(0.0f),
		genomestart(0),
		genomeend(0),
		motif(0),
		middle(0),
		center(0),
		neartriplex(0)
	{
	}

	int stari;
	int endi;
	int starj;
	int endj;
	int strand;
	int reverse;
	int rule;
	float score;
	int nt;
	float identity;
	float tri_score;
	string chr;
	long genomestart;
	long genomeend;
	int motif;
	int middle;
	int center;
	int neartriplex;
	string stri_align;
	string strj_align;
	string cigar_probe;
	std::vector<uint32_t> typed_cigar;
	string query_gap_mask;
	string target_gap_mask;
};

bool buildConvertedTriplexRecord(const StripedSmithWaterman::Alignment &alignment,
	FasimConvertedTriplexRecord &record,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	const FasimConvertMaterializationPolicy &policy);

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings,
	bool materializeCigarProbe = true);

inline uint64_t fasim_phase3_cigar_nt_aligned_len(
	const std::vector<uint32_t> &cigar)
{
	uint64_t alignedLen = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar_int_to_op(cigar[i]);
		if (op == 'M' || op == '=' || op == 'X' || op == 'I' || op == 'D')
		{
			alignedLen += cigar_int_to_len(cigar[i]);
		}
	}
	return alignedLen;
}

inline void fasim_phase3_observe_cigar_nt_prefilter(
	const StripedSmithWaterman::Alignment &alignment,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	FasimFastsimExtendScoreInfoTiming *timing)
{
	if (timing == NULL || timing->phase3_cigar_nt_prefilter_active == 0)
	{
		return;
	}
	const std::chrono::steady_clock::time_point convertStart =
		std::chrono::steady_clock::now();
	FasimConvertMaterializationPolicy policy;
	policy.materialize_alignment_strings = false;
	policy.materialize_cigar_probe_string = false;
	policy.materialize_typed_cigar = false;
	FasimConvertedTriplexRecord converted;
	buildConvertedTriplexRecord(alignment,
	                            converted,
	                            read_seq,
	                            ref_seq,
	                            ref_seq_src,
	                            table,
	                            dnaStartPos,
	                            rule,
	                            strand,
	                            Para,
	                            penaltyT,
	                            penaltyC,
	                            ntMin,
	                            ntMax,
	                            policy);
	const double convertSeconds = std::chrono::duration<double>(
		std::chrono::steady_clock::now() - convertStart).count();
	const bool cigarLtNtMin =
		fasim_phase3_cigar_nt_aligned_len(alignment.cigar) <
		static_cast<uint64_t>(ntMin);
	const bool legacyNtLtNtMin = converted.nt < ntMin;
	++timing->phase3_cigar_nt_alignments_seen;
	if (cigarLtNtMin)
	{
		++timing->phase3_cigar_nt_cigar_lt_ntmin;
		timing->phase3_cigar_nt_convert_seconds_projected_saved +=
			convertSeconds;
		if (!legacyNtLtNtMin)
		{
			++timing->phase3_cigar_nt_candidate_false_negative_rows;
		}
	}
	if (legacyNtLtNtMin)
	{
		++timing->phase3_cigar_nt_legacy_nt_lt_ntmin;
	}
	if (cigarLtNtMin == legacyNtLtNtMin)
	{
		++timing->phase3_cigar_nt_agree_lt_ntmin;
	}
	else
	{
		++timing->phase3_cigar_nt_disagree_lt_ntmin;
	}
}

void cutSequence(string& seq, vector<string>& seqsVec, vector<int>& seqsStartPos,
	int cutLength, int overlapLength, int &cut_num)
{
	unsigned int pos = 0;
	int tmpa = 0;
	int tmpb = 0;
	seqsVec.clear();
	seqsStartPos.clear();
	string cutSeq;
	while (pos < seq.size())
	{
		cutSeq = seq.substr(pos, cutLength);
		seqsVec.push_back(cutSeq);
		seqsStartPos.push_back(pos);
		pos += cutLength;
		pos -= overlapLength;
		tmpa++;
	}
	cut_num = tmpa;
}

bool compMyTriplexSingle(const triplex &a, const triplex &b)
{
	return a.score > b.score;
}

bool compMyTriplexMultiple(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.stari == b.stari)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj > b.starj;
		}
	}
	else
	{
		return a.starj > b.starj;
	}

}

bool compMyTriplexMultiple2(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.endi == b.endi)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj < b.starj;
		}
	}
	else
	{
		return a.starj < b.starj;
	}

}

bool sameMyTriplex(const triplex &a, const triplex &b)
{
	if (a.stari == b.stari && a.starj == b.starj && a.endi == b.endi &&
		a.endj == b.endj && a.score == b.score)
	{
		return true;
	}
	else if (b.stari >= a.stari && b.starj >= a.starj && b.endi <= a.endi &&
		b.endj <= a.endj && b.score < a.score)
	{
		return true;
	}
	else
	{
		return false;
	}

}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
	                                         int penaltyC,
	                                         const struct para &paraList,
	                                         bool materializeAlignmentStrings = true,
	                                         FasimFastsimExtendScoreInfoTiming *timing = NULL);

inline void fastSIM_extend_from_attempt_descriptors(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	StripedSmithWaterman::Alignment &alignment,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<PreAlignCudaAttemptDescriptor> &descriptors,
	vector<struct triplex> &triplex_list,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings = true,
	FasimFastsimExtendScoreInfoTiming *timing = NULL);

void fastSIM(string& strA, string& strB, string& strSrc,
	long dnaStartPos, long min_score, float parm_M,
	float parm_I, float parm_O, float parm_E,
	vector<struct triplex>& triplex_list,
	long strand, long Para, long rule,
	int ntMin, int ntMax, int penaltyT,
	int penaltyC, struct para paraList,
	bool materializeAlignmentStrings = true)
{
	fasim_ssw_oracle::begin_workload(strA, strB, dnaStartPos, rule, strand);
	FasimAuthorityProfileScope authoritySelectionScope(
		FASIM_AUTHORITY_STAGE_SELECTION);
	int32_t maskLen = 15;
	StripedSmithWaterman::Aligner aligner;
	StripedSmithWaterman::Filter filter;
	StripedSmithWaterman::Alignment alignment;
	std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
		bool prealigned = false;
		if (fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built())
		{
			static thread_local bool cudaInitDone = false;
			static thread_local bool cudaInitOk = false;
			static thread_local PrealignSharedQueryCache queryCache;

			if (!cudaInitDone)
			{
			cudaInitDone = true;
			string cudaError;
			cudaInitOk = prealign_cuda_init(fasim_cuda_device_runtime(), &cudaError);
		}

			if (cudaInitOk)
			{
				string cudaError;
				if (!queryCache.prepare(fasim_cuda_device_runtime(), strA, 5, 5, 4, &cudaError))
				{
					cudaInitOk = false;
				}

				if (cudaInitOk && queryCache.query_handle().profileDevice != 0)
				{
					static std::vector<uint8_t> encodedTarget;
					prealign_shared_encode_sequence(strB, encodedTarget);

						std::vector<PreAlignCudaPeak> peaks;
						PreAlignCudaBatchResult batchResult;
						string cudaError;
						const int topK = fasim_prealign_cuda_topk_runtime();
						if (prealign_cuda_find_topk_column_maxima(queryCache.query_handle(),
						                                          encodedTarget.data(),
						                                          1,
						                                          static_cast<int>(encodedTarget.size()),
				                                          topK,
				                                          &peaks,
				                                          &batchResult,
				                                          &cudaError))
				{
					finalScoreInfo.clear();
					const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
					for (int k = 0; k < topK; ++k)
					{
						const PreAlignCudaPeak& p = peaks[static_cast<size_t>(k)];
						if (p.score <= min_score || p.position < 0)
						{
							continue;
						}
						bool suppressed = false;
						for (size_t s = 0; s < finalScoreInfo.size(); ++s)
						{
							if (abs(finalScoreInfo[s].position - p.position) < suppressBp)
							{
								suppressed = true;
								break;
							}
						}
						if (!suppressed)
						{
							finalScoreInfo.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
						}
					}
					prealigned = true;
				}
			}
		}
	}

	if (!prealigned)
	{
		aligner.preAlign(strA.c_str(), strB.c_str(), strB.size(), filter, &alignment, maskLen, min_score, finalScoreInfo, parm_M, parm_I);
	}
	fastSIM_extend_from_scoreinfo(aligner,
	                              filter,
	                              alignment,
	                              maskLen,
	                              strA,
	                              strB,
	                              strSrc,
	                              dnaStartPos,
	                              finalScoreInfo,
	                              triplex_list,
	                              strand,
	                              Para,
	                              rule,
	                              ntMin,
	                              ntMax,
	                              penaltyT,
	                              penaltyC,
	                              paraList,
	                              materializeAlignmentStrings);
	fasim_ssw_oracle::end_workload();
}

inline void fastSIM_extend_from_attempt_descriptors(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	StripedSmithWaterman::Alignment &alignment,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<PreAlignCudaAttemptDescriptor> &descriptors,
	vector<struct triplex> &triplex_list,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	FasimFastsimExtendScoreInfoTiming *timing)
{
	vector<struct triplex> myTriplexList;
	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	string smallSeq;
	int currentScoreInfoOrder = -1;
	int currentScoreInfoScore = 0;
	FasimGasal2Attempt bestAttempt;
	FasimGasal2Attempt lastAttempt;
	StripedSmithWaterman::Alignment bestAlignment;
	StripedSmithWaterman::Alignment lastAlignment;
	bool haveBest = false;
	bool haveLast = false;
	bool emitted = false;

	auto emit_alignment = [&](const FasimGasal2Attempt &attempt,
	                          const StripedSmithWaterman::Alignment &localAlignment)
	{
		if (localAlignment.sw_score == 0)
		{
			return;
		}
		StripedSmithWaterman::Alignment emitAlignment = localAlignment;
		emitAlignment.ref_begin += attempt.start;
		emitAlignment.ref_end += attempt.start;
		fasim_phase3_observe_cigar_nt_prefilter(
			emitAlignment,
			strA,
			strB,
			strSrc,
			nt_table,
			dnaStartPos,
			rule,
			strand,
			Para,
			penaltyT,
			penaltyC,
			ntMin,
			ntMax,
			timing);
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(emitAlignment,
		                 myTriplexList,
		                 strA,
		                 strB,
		                 strSrc,
		                 nt_table,
		                 dnaStartPos,
		                 rule,
		                 strand,
		                 Para,
		                 penaltyT,
		                 penaltyC,
		                 ntMin,
		                 ntMax,
		                 materializeAlignmentStrings);
		if (timing != NULL)
		{
			timing->convert_seconds +=
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - convertStart).count();
		}
	};

	auto flush_scoreinfo = [&]()
	{
		if (currentScoreInfoOrder >= 0 && !emitted)
		{
			if (haveBest)
			{
				emit_alignment(bestAttempt, bestAlignment);
			}
			else if (haveLast && lastAlignment.sw_score != 0)
			{
				emit_alignment(lastAttempt, lastAlignment);
			}
		}
		haveBest = false;
		haveLast = false;
		emitted = false;
		bestAlignment.Clear();
		lastAlignment.Clear();
		bestAttempt = FasimGasal2Attempt();
		lastAttempt = FasimGasal2Attempt();
	};

	for (size_t i = 0; i < descriptors.size(); ++i)
	{
		const PreAlignCudaAttemptDescriptor &descriptor = descriptors[i];
		if (descriptor.scoreInfoOrder != currentScoreInfoOrder)
		{
			flush_scoreinfo();
			currentScoreInfoOrder = descriptor.scoreInfoOrder;
			currentScoreInfoScore = descriptor.scoreInfoScore;
			if (timing != NULL)
			{
				++timing->scoreinfo_groups;
			}
		}
		if (emitted)
		{
			continue;
		}
		if (descriptor.targetStart < 0 ||
		    descriptor.cutlength <= 0 ||
		    descriptor.targetStart + descriptor.cutlength >
			    static_cast<int>(strB.size()))
		{
			continue;
		}
		FasimGasal2Attempt attempt;
		attempt.scoreinfo_index = descriptor.scoreInfoOrder;
		attempt.cutlength = descriptor.cutlength;
		attempt.start = descriptor.targetStart;
		attempt.prealign_score = descriptor.scoreInfoScore;
		attempt.target_end_required_for_fallback =
			descriptor.targetEndRequiredForFallback;
		attempt.nt_min_length = ntMin;
		const std::chrono::steady_clock::time_point substrStart =
			std::chrono::steady_clock::now();
		smallSeq = strB.substr(static_cast<size_t>(attempt.start),
		                       static_cast<size_t>(attempt.cutlength));
		if (timing != NULL)
		{
			timing->substr_seconds +=
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - substrStart).count();
		}
		const std::chrono::steady_clock::time_point alignStart =
			std::chrono::steady_clock::now();
		StripedSmithWaterman::Alignment localAlignment;
		aligner.Align(strA.c_str(),
		              smallSeq.c_str(),
		              smallSeq.size(),
		              filter,
		              &localAlignment,
		              maskLen);
		if (timing != NULL)
		{
			++timing->align_attempts;
			timing->align_seconds +=
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - alignStart).count();
		}
		lastAttempt = attempt;
		lastAlignment = localAlignment;
		haveLast = true;
		if (localAlignment.sw_score >= currentScoreInfoScore)
		{
			emit_alignment(attempt, localAlignment);
			emitted = true;
			continue;
		}
		if (localAlignment.sw_score > bestAlignment.sw_score &&
		    localAlignment.ref_end == attempt.cutlength - 1)
		{
			bestAttempt = attempt;
			bestAlignment = localAlignment;
			haveBest = true;
		}
	}
	flush_scoreinfo();

	const std::chrono::steady_clock::time_point sortStart =
		std::chrono::steady_clock::now();
	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	}
	if (timing != NULL)
	{
		timing->sort_seconds +=
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - sortStart).count();
	}
	const std::chrono::steady_clock::time_point filterStart =
		std::chrono::steady_clock::now();
	for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
	{
		triplex atr = myTriplexList[i];
		if (atr.identity >= paraList.minIdentity &&
		    atr.tri_score >= paraList.minStability &&
		    atr.nt >= ntMin)
		{
			triplex_list.push_back(atr);
		}
	}
	if (timing != NULL)
	{
		timing->filter_seconds +=
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - filterStart).count();
	}
}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
	                                         int penaltyC,
	                                         const struct para &paraList,
	                                         bool materializeAlignmentStrings,
	                                         FasimFastsimExtendScoreInfoTiming *timing)
{
	vector<struct triplex> myTriplexList;

	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	string smallSeq;
	if (fasim_gasal2_enabled() &&
	    fasim_gasal2_is_built() &&
	    fasim_gasal2_fastsim_query_length_supported_runtime(strA.size()) &&
	    !fasim_gasal2_attempt_consumer_shadow_enabled_runtime() &&
	    !fasim_long_query_gpu_consumer_spike_v1_enabled_runtime())
	{
		std::vector<FasimGasal2Attempt> gasalAttempts;
		std::vector<FasimGasal2SelectedAlignment> gasalSelected;
		std::string gasalError;
		const bool useTargetViews = fasim_gasal2_longtarget_bridge_enabled();
		const bool useCpuTraceback = fasim_gasal2_cpu_traceback_enabled_runtime();
		const bool useCpuTracebackAll = fasim_gasal2_cpu_traceback_all_enabled_runtime();

		if (!useCpuTraceback && fasim_gasal2_identity_rounds_enabled_runtime())
		{
			std::vector<bool> scoreInfoSelected(finalScoreInfo.size(), false);
			std::vector<bool> scoreInfoHaveBest(finalScoreInfo.size(), false);
			std::vector<FasimGasal2SelectedAlignment> scoreInfoBest(finalScoreInfo.size());
			float Iden = 0.6;
			while (Iden <= 1)
				{
					gasalAttempts.clear();
					gasalAttempts.reserve(finalScoreInfo.size());
					for (int i = 0; i < finalScoreInfo.size(); i++)
				{
					if (scoreInfoSelected[static_cast<size_t>(i)])
					{
						continue;
					}
					int cutlength = static_cast<int>(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
					cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
					const int start = finalScoreInfo[i].position - cutlength + 1;
					if (start < 0 || cutlength <= 0)
					{
						continue;
					}
					FasimGasal2Attempt attempt;
					attempt.scoreinfo_index = i;
					attempt.cutlength = cutlength;
						attempt.start = start;
						attempt.prealign_score = finalScoreInfo[i].score;
						attempt.target_end_required_for_fallback = cutlength - 1;
						attempt.nt_min_length = paraList.cLength;
						if (useTargetViews)
					{
						attempt.set_target_view(&strB, static_cast<size_t>(start), static_cast<size_t>(cutlength));
					}
					else
					{
						attempt.target = strB.substr(start, cutlength);
					}
					gasalAttempts.push_back(std::move(attempt));
				}
					if (gasalAttempts.empty())
					{
						Iden += 0.1;
						continue;
					}
				std::vector<FasimGasal2SelectedAlignment> roundSelected;
				const bool gasalOk = useCpuTraceback ?
					fasim_gasal2_select_attempts(strA, gasalAttempts, &roundSelected, &gasalError) :
					fasim_gasal2_align_attempts(strA, gasalAttempts, &roundSelected, &gasalError);
				if (!gasalOk)
				{
					gasalSelected.clear();
					break;
				}
				for (size_t gi = 0; gi < roundSelected.size(); ++gi)
				{
					const int scoreInfoIndex = roundSelected[gi].scoreinfo_index;
					if (scoreInfoIndex >= 0 && static_cast<size_t>(scoreInfoIndex) < scoreInfoSelected.size())
					{
						const size_t scoreInfoOffset = static_cast<size_t>(scoreInfoIndex);
						if (roundSelected[gi].alignment.sw_score >= finalScoreInfo[scoreInfoOffset].score)
						{
							scoreInfoSelected[scoreInfoOffset] = true;
							gasalSelected.push_back(roundSelected[gi]);
						}
						else if (!scoreInfoHaveBest[scoreInfoOffset] ||
						         roundSelected[gi].alignment.sw_score > scoreInfoBest[scoreInfoOffset].alignment.sw_score)
						{
							scoreInfoHaveBest[scoreInfoOffset] = true;
							scoreInfoBest[scoreInfoOffset] = roundSelected[gi];
						}
					}
				}
				Iden += 0.1;
			}
			for (size_t i = 0; i < scoreInfoHaveBest.size(); ++i)
			{
				if (!scoreInfoSelected[i] && scoreInfoHaveBest[i])
				{
					gasalSelected.push_back(scoreInfoBest[i]);
				}
			}
		}
		else
		{
			gasalAttempts.reserve(finalScoreInfo.size() * 5);
			for (int i = 0; i < finalScoreInfo.size(); i++)
			{
				float Iden = 0.6;
				while (Iden <= 1)
				{
					int cutlength = static_cast<int>(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
					cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
					const int start = finalScoreInfo[i].position - cutlength + 1;
					if (start < 0 || cutlength <= 0)
					{
						Iden += 0.1;
						continue;
					}
					FasimGasal2Attempt attempt;
					attempt.scoreinfo_index = i;
					attempt.cutlength = cutlength;
						attempt.start = start;
						attempt.prealign_score = finalScoreInfo[i].score;
						attempt.target_end_required_for_fallback = cutlength - 1;
						attempt.nt_min_length = ntMin;
						if (useTargetViews)
					{
						attempt.set_target_view(&strB, static_cast<size_t>(start), static_cast<size_t>(cutlength));
					}
					else
					{
						attempt.target = strB.substr(start, cutlength);
					}
					gasalAttempts.push_back(std::move(attempt));
					Iden += 0.1;
				}
			}
			const int gasalMinAttempts = fasim_gasal2_min_attempts_runtime();
			if (gasalMinAttempts <= 0 || gasalAttempts.size() >= static_cast<size_t>(gasalMinAttempts))
			{
				if (useCpuTraceback && useCpuTracebackAll)
				{
					std::vector<FasimGasal2SelectedAlignment> scoreProbeSelected;
					fasim_gasal2_select_attempts(strA, gasalAttempts, &scoreProbeSelected, &gasalError);
					gasalSelected.clear();
					gasalSelected.reserve(gasalAttempts.size());
					for (size_t ai = 0; ai < gasalAttempts.size(); ++ai)
					{
						FasimGasal2SelectedAlignment selectedAttempt;
						selectedAttempt.scoreinfo_index = gasalAttempts[ai].scoreinfo_index;
						selectedAttempt.cutlength = gasalAttempts[ai].cutlength;
						selectedAttempt.start = gasalAttempts[ai].start;
						selectedAttempt.selected = true;
						gasalSelected.push_back(selectedAttempt);
					}
				}
				else if (useCpuTraceback)
				{
					fasim_gasal2_select_attempts(strA, gasalAttempts, &gasalSelected, &gasalError);
				}
				else
				{
					fasim_gasal2_align_attempts(strA, gasalAttempts, &gasalSelected, &gasalError);
				}
			}
		}

		if (!gasalSelected.empty())
		{
			std::vector<FasimGasal2SelectedAlignment> gasalReplaySelected;
			const std::vector<FasimGasal2SelectedAlignment> *selectedForTriplex = &gasalSelected;
			if (useCpuTraceback)
			{
				gasalReplaySelected.clear();
				int currentScoreInfo = -1;
				FasimGasal2SelectedAlignment bestSelected;
				FasimGasal2SelectedAlignment lastSelected;
				StripedSmithWaterman::Alignment bestAlignment;
				StripedSmithWaterman::Alignment lastAlignment;
				bool haveBest = false;
				bool haveLast = false;
				bool emitted = false;

				auto flushCpuReplay = [&]()
				{
					if (currentScoreInfo >= 0 && !emitted)
					{
						if (haveBest)
						{
							bestSelected.alignment = bestAlignment;
							gasalReplaySelected.push_back(bestSelected);
						}
						else if (haveLast)
						{
							lastSelected.alignment = lastAlignment;
							if (lastSelected.alignment.sw_score != 0)
							{
								gasalReplaySelected.push_back(lastSelected);
							}
						}
					}
					haveBest = false;
					haveLast = false;
					emitted = false;
					bestSelected = FasimGasal2SelectedAlignment();
					lastSelected = FasimGasal2SelectedAlignment();
					bestAlignment.Clear();
					lastAlignment.Clear();
				};

				for (size_t gi = 0; gi < gasalSelected.size(); ++gi)
				{
					FasimGasal2SelectedAlignment candidate = gasalSelected[gi];
					if (candidate.scoreinfo_index != currentScoreInfo)
					{
						flushCpuReplay();
						currentScoreInfo = candidate.scoreinfo_index;
					}
					if (emitted)
					{
						continue;
					}
					const int scoreInfoIndex = candidate.scoreinfo_index;
					if (scoreInfoIndex < 0 || static_cast<size_t>(scoreInfoIndex) >= finalScoreInfo.size())
					{
						continue;
					}
					const int start = candidate.start;
					const int cutlength = candidate.cutlength;
					if (start < 0 || cutlength <= 0)
					{
						continue;
					}
					smallSeq = strB.substr(start, cutlength);
					StripedSmithWaterman::Alignment cpuCandidateAlignment;
					aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &cpuCandidateAlignment, maskLen);
					if (!emitted)
					{
						lastSelected = candidate;
						lastAlignment = cpuCandidateAlignment;
						haveLast = true;
					}
					if (!emitted && cpuCandidateAlignment.sw_score >= finalScoreInfo[static_cast<size_t>(scoreInfoIndex)].score)
					{
						candidate.alignment = cpuCandidateAlignment;
						gasalReplaySelected.push_back(candidate);
						emitted = true;
						continue;
					}
					if (!emitted &&
					    cpuCandidateAlignment.sw_score > bestAlignment.sw_score &&
					    cpuCandidateAlignment.ref_end == cutlength - 1)
					{
						bestSelected = candidate;
						bestAlignment = cpuCandidateAlignment;
						haveBest = true;
					}
				}
				flushCpuReplay();
				fasim_gasal2_record_cpu_traceback_replay(gasalSelected.size(),
				                                         gasalReplaySelected.size());
				selectedForTriplex = &gasalReplaySelected;
			}

			for (size_t gi = 0; gi < selectedForTriplex->size(); ++gi)
			{
				FasimGasal2SelectedAlignment selectedAlignment = (*selectedForTriplex)[gi];
				StripedSmithWaterman::Alignment gasalAlignment = selectedAlignment.alignment;
				if (useCpuTraceback && selectedAlignment.selected)
				{
					gasalAlignment.ref_begin += selectedAlignment.start;
					gasalAlignment.ref_end += selectedAlignment.start;
				}
				if (selectedAlignment.selected && gasalAlignment.sw_score != 0)
				{
					fasim_phase3_observe_cigar_nt_prefilter(
						gasalAlignment,
						strA,
						strB,
						strSrc,
						nt_table,
						dnaStartPos,
						rule,
						strand,
						Para,
						penaltyT,
						penaltyC,
						ntMin,
						ntMax,
						timing);
					convertMyTriplex(gasalAlignment,
					                 myTriplexList,
					                 strA,
					                 strB,
					                 strSrc,
					                 nt_table,
					                 dnaStartPos,
					                 rule,
					                 strand,
					                 Para,
					                 penaltyT,
					                 penaltyC,
					                 ntMin,
					                 ntMax,
					                 materializeAlignmentStrings);
				}
			}
			{
				FasimAuthorityProfileScope authoritySortScope(
					FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
				myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
				myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
			}
			for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
			{
				triplex atr = myTriplexList[i];
				if (atr.identity >= paraList.minIdentity && atr.tri_score >= paraList.minStability && atr.nt >= ntMin)
				{
					triplex_list.push_back(atr);
				}
			}
			return;
		}
		}

		fasim_probe_gasal2_extend_attempts_from_scoreinfo(strA,
		                                                  strB,
		                                                  finalScoreInfo,
		                                                  ntMin,
		                                                  timing);

		for (int i = 0; i < finalScoreInfo.size(); i++)
		{
			if (timing != NULL)
			{
				++timing->scoreinfo_groups;
			}
			float Iden = 0.6;
			int cutlength, bestcutregion;
			int myflag = 0;
			int identityRound = 0;
			std::string bestTraceAttempt;
			std::string lastTraceAttempt;
			std::string selectedTraceAttempt;
			const char* traceSelectionReason = "none";
			StripedSmithWaterman::Alignment bestalignment;
			bestalignment.sw_score = 0;
			while (Iden <= 1)
			{
				cutlength = (int)(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
				cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
				const std::chrono::steady_clock::time_point substrStart =
					std::chrono::steady_clock::now();
				const int traceTargetStart = finalScoreInfo[i].position - cutlength + 1;
				smallSeq = strB.substr(traceTargetStart, cutlength);
				if (timing != NULL)
				{
					timing->substr_seconds +=
						std::chrono::duration<double>(
							std::chrono::steady_clock::now() - substrStart).count();
				}
				const std::chrono::steady_clock::time_point alignStart =
					std::chrono::steady_clock::now();
				const std::string traceAttempt = fasim_ssw_oracle::begin_attempt(
					i, finalScoreInfo[i].score, identityRound, Iden,
					traceTargetStart, cutlength);
				aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &alignment, maskLen);
				lastTraceAttempt = traceAttempt;
				if (timing != NULL &&
				    fasim_long_query_gpu_consumer_spike_v1_enabled_runtime())
				{
					FasimConsumerAttemptTraceRow traceRow;
					traceRow.scoreinfo_index = i;
					traceRow.identity_round = identityRound;
					traceRow.start = traceTargetStart;
					traceRow.cutlength = cutlength;
					traceRow.score = alignment.sw_score;
					traceRow.query_end = alignment.query_end;
					traceRow.ref_end_local = alignment.ref_end;
					timing->consumer_attempt_trace.push_back(traceRow);
				}
				if (timing != NULL)
				{
					++timing->align_attempts;
					timing->align_seconds +=
						std::chrono::duration<double>(
							std::chrono::steady_clock::now() - alignStart).count();
				}
				if (alignment.sw_score >= finalScoreInfo[i].score)
				{
					myflag = 1;
					selectedTraceAttempt = traceAttempt;
					traceSelectionReason = "threshold";
				break;
			}
			if (alignment.sw_score > bestalignment.sw_score && alignment.ref_end == cutlength - 1)
			{
				bestalignment.sw_score = alignment.sw_score;
				bestalignment.sw_score_next_best = alignment.sw_score_next_best;
				bestalignment.ref_begin = alignment.ref_begin;
				bestalignment.ref_end = alignment.ref_end;
				bestalignment.query_begin = alignment.query_begin;
				bestalignment.query_end = alignment.query_end;
				bestalignment.ref_end_next_best = alignment.ref_end_next_best;
				bestalignment.mismatches = alignment.mismatches;
				bestalignment.cigar_string = alignment.cigar_string;
				bestalignment.cigar = alignment.cigar;
				bestcutregion = cutlength;
				bestTraceAttempt = traceAttempt;
				myflag = 2;
			}
			Iden += 0.1;
			++identityRound;
		}
		if (myflag == 2)
		{
			selectedTraceAttempt = bestTraceAttempt;
			traceSelectionReason = "best_fallback";
			alignment.sw_score = bestalignment.sw_score;
			alignment.sw_score_next_best = bestalignment.sw_score_next_best;
			alignment.ref_begin = bestalignment.ref_begin;
			alignment.ref_end = bestalignment.ref_end;
			alignment.query_begin = bestalignment.query_begin;
			alignment.query_end = bestalignment.query_end;
			alignment.ref_end_next_best = bestalignment.ref_end_next_best;
			alignment.mismatches = bestalignment.mismatches;
			alignment.cigar_string = bestalignment.cigar_string;
			alignment.cigar = bestalignment.cigar;
			cutlength = bestcutregion;
		}
		else if (myflag == 0 && alignment.sw_score != 0)
		{
			selectedTraceAttempt = lastTraceAttempt;
			traceSelectionReason = "last";
		}
		fasim_ssw_oracle::finish_scoreinfo_group(
			i, selectedTraceAttempt, traceSelectionReason);
			bestalignment.Clear();
			if (alignment.sw_score != 0)
			{
				alignment.ref_begin = alignment.ref_begin + finalScoreInfo[i].position - cutlength + 1;
				alignment.ref_end = alignment.ref_end + finalScoreInfo[i].position - cutlength + 1;
				fasim_phase3_observe_cigar_nt_prefilter(
					alignment,
					strA,
					strB,
					strSrc,
					nt_table,
					dnaStartPos,
					rule,
					strand,
					Para,
					penaltyT,
					penaltyC,
					ntMin,
					ntMax,
					timing);
				const std::chrono::steady_clock::time_point convertStart =
					std::chrono::steady_clock::now();
				const size_t convertedRowBegin = myTriplexList.size();
				convertMyTriplex(alignment,
				                 myTriplexList,
				                 strA,
			                 strB,
			                 strSrc,
			                 nt_table,
			                 dnaStartPos,
			                 rule,
			                 strand,
			                 Para,
			                 penaltyT,
			                 penaltyC,
				                 ntMin,
				                 ntMax,
				                 materializeAlignmentStrings);
				for (size_t rowIndex = convertedRowBegin;
					rowIndex < myTriplexList.size(); ++rowIndex)
				{
					myTriplexList[rowIndex].ssw_oracle_attempt_key =
						selectedTraceAttempt;
				}
				if (timing != NULL)
				{
					timing->convert_seconds +=
						std::chrono::duration<double>(
							std::chrono::steady_clock::now() - convertStart).count();
				}
			}
		}
		const std::chrono::steady_clock::time_point sortStart =
			std::chrono::steady_clock::now();
		{
			FasimAuthorityProfileScope authoritySortScope(
				FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
			myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
			myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
		}
		if (timing != NULL)
		{
			timing->sort_seconds +=
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - sortStart).count();
		}
		const std::chrono::steady_clock::time_point filterStart =
			std::chrono::steady_clock::now();
		for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
		{
			triplex atr = myTriplexList[i];
			if (atr.identity >= paraList.minIdentity && atr.tri_score >= paraList.minStability && atr.nt >= ntMin)
			{
				fasim_ssw_oracle::record_emitted_row(
					atr.ssw_oracle_attempt_key,
					atr.stari,
					atr.endi,
					atr.starj,
					atr.endj,
					atr.strand,
					atr.reverse,
					atr.rule,
					atr.nt,
					atr.score,
					atr.identity,
					atr.tri_score,
					atr.stri_align,
					atr.strj_align);
				triplex_list.push_back(atr);
			}
		}
		fasim_ssw_oracle::publish_workload_records();
		if (timing != NULL)
		{
			timing->filter_seconds +=
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - filterStart).count();
		}
	}

#ifdef FASIM_WITH_SSW_CUDA_FORWARD_HYBRID
inline bool fastSIM_extend_from_forward_hybrid_selected(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<fasim_ssw_cuda::ForwardHybridSelectedAttempt> &selected,
	vector<struct triplex> &triplex_list,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	FasimFastsimExtendScoreInfoTiming *timing,
	fasim_ssw_cuda::ForwardHybridCpuTelemetry *cpuTelemetry,
	std::string *error)
{
	if (error != NULL) error->clear();
	if (cpuTelemetry == NULL)
	{
		if (error != NULL) *error = "forward-hybrid CPU telemetry is null";
		return false;
	}
	vector<struct triplex> myTriplexList;
	const int8_t nt_table[128] = {
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4
	};

	for (size_t index = 0; index < selected.size(); ++index)
	{
		const fasim_ssw_cuda::ForwardHybridSelectedAttempt &attempt = selected[index];
		if (attempt.start < 0 || attempt.cutlength <= 0 ||
			static_cast<size_t>(attempt.start + attempt.cutlength) > strB.size() ||
			attempt.endpoint.score1 <= 0)
		{
			++cpuTelemetry->failures;
			if (error != NULL) *error = "invalid selected forward-hybrid attempt";
			return false;
		}
		const std::chrono::steady_clock::time_point substringStart =
			std::chrono::steady_clock::now();
		const string smallSeq = strB.substr(static_cast<size_t>(attempt.start),
			static_cast<size_t>(attempt.cutlength));
		const double substringSeconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - substringStart).count();
		cpuTelemetry->substring_seconds += substringSeconds;
		if (timing != NULL) timing->substr_seconds += substringSeconds;

		StripedSmithWaterman::ForwardEndpoint endpoint;
		endpoint.score1 = attempt.endpoint.score1;
		endpoint.score2 = attempt.endpoint.score2;
		endpoint.ref_end1 = attempt.endpoint.ref_end1;
		endpoint.query_end1 = attempt.endpoint.read_end1;
		endpoint.ref_end2 = attempt.endpoint.ref_end2;
		endpoint.numeric_path = attempt.endpoint.numeric_path;
		const ssw_align_internal_stats before = ssw_align_internal_stats_snapshot();
		const uint8_t priorStats = ssw_align_internal_stats_enabled();
		ssw_align_internal_stats_set_enabled(1);
		const std::chrono::steady_clock::time_point continuationStart =
			std::chrono::steady_clock::now();
		StripedSmithWaterman::Alignment alignment;
		const bool continuationOk = aligner.AlignFromForward(
			strA.c_str(), smallSeq.c_str(), static_cast<int>(smallSeq.size()),
			filter, endpoint, &alignment, maskLen);
		const double continuationSeconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - continuationStart).count();
		ssw_align_internal_stats_set_enabled(priorStats);
		const ssw_align_internal_stats after = ssw_align_internal_stats_snapshot();
		if (after.forward_calls < before.forward_calls ||
			after.reverse_calls < before.reverse_calls ||
			after.banded_sw_calls < before.banded_sw_calls ||
			after.reverse_start_nanoseconds < before.reverse_start_nanoseconds ||
			after.banded_sw_nanoseconds < before.banded_sw_nanoseconds ||
			after.cigar_nanoseconds < before.cigar_nanoseconds)
		{
			++cpuTelemetry->failures;
			if (error != NULL) *error = "forward-hybrid CPU counter moved backwards";
			return false;
		}
		const uint64_t forwardCalls = after.forward_calls - before.forward_calls;
		const uint64_t reverseCalls = after.reverse_calls - before.reverse_calls;
		const uint64_t bandedCalls = after.banded_sw_calls - before.banded_sw_calls;
		++cpuTelemetry->continuation_calls;
		cpuTelemetry->cpu_forward_calls += forwardCalls;
		cpuTelemetry->cpu_reverse_calls += reverseCalls;
		cpuTelemetry->cpu_banded_sw_calls += bandedCalls;
		cpuTelemetry->continuation_seconds += continuationSeconds;
		cpuTelemetry->reverse_start_seconds += static_cast<double>(
			after.reverse_start_nanoseconds - before.reverse_start_nanoseconds) /
			1000000000.0;
		cpuTelemetry->banded_traceback_seconds += static_cast<double>(
			after.banded_sw_nanoseconds - before.banded_sw_nanoseconds) /
			1000000000.0;
		cpuTelemetry->cigar_seconds += static_cast<double>(
			after.cigar_nanoseconds - before.cigar_nanoseconds) /
			1000000000.0;
		if (timing != NULL)
		{
			++timing->align_attempts;
			timing->align_seconds += continuationSeconds;
		}
		if (!continuationOk || forwardCalls != 0 || reverseCalls != 1 ||
			bandedCalls != 1 || alignment.sw_score != attempt.endpoint.score1 ||
			alignment.sw_score_next_best != attempt.endpoint.score2 ||
			alignment.ref_end != attempt.endpoint.ref_end1 ||
			alignment.query_end != attempt.endpoint.read_end1 ||
			alignment.ref_end_next_best != attempt.endpoint.ref_end2)
		{
			++cpuTelemetry->failures;
			if (error != NULL) *error = "forward-hybrid continuation contract mismatch";
			return false;
		}

		alignment.ref_begin += attempt.start;
		alignment.ref_end += attempt.start;
		fasim_phase3_observe_cigar_nt_prefilter(
			alignment, strA, strB, strSrc, nt_table, dnaStartPos, rule,
			strand, Para, penaltyT, penaltyC, ntMin, ntMax, timing);
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(alignment, myTriplexList, strA, strB, strSrc,
			nt_table, dnaStartPos, rule, strand, Para, penaltyT, penaltyC,
			ntMin, ntMax, materializeAlignmentStrings);
		const double convertSeconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - convertStart).count();
		cpuTelemetry->conversion_seconds += convertSeconds;
		if (timing != NULL) timing->convert_seconds += convertSeconds;
	}

	const std::chrono::steady_clock::time_point sortStart =
		std::chrono::steady_clock::now();
	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(),
			sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(),
			sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	}
	if (timing != NULL)
		timing->sort_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - sortStart).count();
	cpuTelemetry->sort_seconds += std::chrono::duration<double>(
		std::chrono::steady_clock::now() - sortStart).count();
	const std::chrono::steady_clock::time_point filterStart =
		std::chrono::steady_clock::now();
	for (int index = 0;
		index < static_cast<int>(myTriplexList.size() > N ? N : myTriplexList.size());
		++index)
	{
		const triplex &item = myTriplexList[static_cast<size_t>(index)];
		if (item.identity >= paraList.minIdentity &&
			item.tri_score >= paraList.minStability && item.nt >= ntMin)
			triplex_list.push_back(item);
	}
	if (timing != NULL)
		timing->filter_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - filterStart).count();
	cpuTelemetry->filter_seconds += std::chrono::duration<double>(
		std::chrono::steady_clock::now() - filterStart).count();
	return true;
}
#endif

inline bool fasim_shadow_attempt_consumer_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	vector<struct triplex> &shadowTriplexList,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	std::string *errorOut)
{
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();
	if (errorOut != NULL)
	{
		errorOut->clear();
	}
	shadowTriplexList.clear();
	if (finalScoreInfo.empty())
	{
		fasim_gasal2_record_attempt_consumer_shadow_request(
			1, 0, 0, "empty_scoreinfo");
		return true;
	}

	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	std::vector<FasimGasal2Attempt> attempts;
	attempts.reserve(finalScoreInfo.size() * 5);
	for (size_t scoreInfoIndex = 0;
	     scoreInfoIndex < finalScoreInfo.size();
	     ++scoreInfoIndex)
	{
		const StripedSmithWaterman::scoreInfo &scoreInfo =
			finalScoreInfo[scoreInfoIndex];
		float Iden = 0.6f;
		while (Iden <= 1)
		{
			int cutlength =
				static_cast<int>(scoreInfo.score + 24) /
				(9 * Iden - 4) + 1;
			cutlength =
				scoreInfo.position - cutlength + 1 > 0 ?
				cutlength : scoreInfo.position + 1;
			const int start = scoreInfo.position - cutlength + 1;
			if (start >= 0 &&
			    cutlength > 0 &&
			    start + cutlength <= static_cast<int>(strB.size()))
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(scoreInfoIndex);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = scoreInfo.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.set_target_view(&strB,
				                        static_cast<size_t>(start),
				                        static_cast<size_t>(cutlength));
				attempts.push_back(attempt);
			}
			Iden += 0.1f;
		}
	}
	fasim_gasal2_record_attempt_consumer_shadow_request(
		1,
		static_cast<uint64_t>(finalScoreInfo.size()),
		static_cast<uint64_t>(attempts.size()),
		"attempt_consumer_shadow_requested");
	if (attempts.empty())
	{
		if (errorOut != NULL)
		{
			*errorOut = "empty_attempts";
		}
		fasim_gasal2_record_attempt_consumer_shadow_replay(
			0, 0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			"empty_attempts");
		return false;
	}

	std::vector<size_t> selectedAttemptIndexes;
	std::string selectError;
	bool selectOk = false;
	if (fasim_gasal2_fastsim_query_length_supported_runtime(strA.size()))
	{
		selectOk = fasim_gasal2_select_attempt_indexes_from_scores(
			strA, attempts, &selectedAttemptIndexes, &selectError);
	}
	else
	{
		size_t tileLen =
			fasim_long_query_streaming_scoreinfo_segmented_probe_tile_len_runtime();
		size_t tileOverlap =
			fasim_long_query_streaming_scoreinfo_segmented_probe_tile_overlap_runtime();
		if (tileLen == 0)
		{
			tileLen = 2812;
		}
		if (tileOverlap >= tileLen)
		{
			tileOverlap = 0;
		}
		const std::vector<FasimGasal2LongQuerySegment> segments =
			fasim_build_gasal2_long_query_segments(
				strA,
				tileLen,
				tileOverlap,
				fasim_long_query_streaming_scoreinfo_segmented_probe_max_segments_runtime());
		if (segments.empty())
		{
			selectError = "empty_query_segments";
		}
		std::vector<unsigned char> selectedMask(
			attempts.size(),
			static_cast<unsigned char>(0));
		for (size_t segmentIndex = 0;
		     segmentIndex < segments.size();
		     ++segmentIndex)
		{
			std::vector<size_t> segmentSelected;
			std::string segmentError;
			if (!fasim_gasal2_select_attempt_indexes_from_scores(
				    segments[segmentIndex].query_segment,
				    attempts,
				    &segmentSelected,
				    &segmentError))
			{
				selectError = segmentError.empty() ?
					"gasal2_segment_select_failed" : segmentError;
				continue;
			}
			selectOk = true;
			for (size_t i = 0; i < segmentSelected.size(); ++i)
			{
				const size_t selectedIndex = segmentSelected[i];
				if (selectedIndex < selectedMask.size())
				{
					selectedMask[selectedIndex] = static_cast<unsigned char>(1);
				}
			}
		}
		if (selectOk)
		{
			for (size_t i = 0; i < selectedMask.size(); ++i)
			{
				if (selectedMask[i] != 0)
				{
					selectedAttemptIndexes.push_back(i);
				}
			}
		}
	}
	if (!selectOk)
	{
		if (errorOut != NULL)
		{
			*errorOut = selectError.empty() ? "gasal2_select_failed" : selectError;
		}
		fasim_gasal2_record_attempt_consumer_shadow_replay(
			0, 0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			selectError.empty() ? "gasal2_select_failed" : selectError.c_str());
		return false;
	}
	if (selectedAttemptIndexes.empty())
	{
		if (errorOut != NULL)
		{
			*errorOut = "empty_selected_attempts";
		}
		fasim_gasal2_record_attempt_consumer_shadow_replay(
			0, 0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			"empty_selected_attempts");
		return false;
	}

	std::sort(selectedAttemptIndexes.begin(), selectedAttemptIndexes.end());
	selectedAttemptIndexes.erase(
		std::unique(selectedAttemptIndexes.begin(), selectedAttemptIndexes.end()),
		selectedAttemptIndexes.end());
	std::vector<size_t> replayAttemptIndexes;
	replayAttemptIndexes.reserve(selectedAttemptIndexes.size() * 5);
	std::vector<unsigned char> replaySelected(
		attempts.size(),
		static_cast<unsigned char>(0));
	for (size_t i = 0; i < selectedAttemptIndexes.size(); ++i)
	{
		const size_t selectedIndex = selectedAttemptIndexes[i];
		if (selectedIndex >= attempts.size())
		{
			continue;
		}
		const int selectedScoreInfo = attempts[selectedIndex].scoreinfo_index;
		size_t groupBegin = selectedIndex;
		while (groupBegin > 0 &&
		       attempts[groupBegin - 1].scoreinfo_index == selectedScoreInfo)
		{
			--groupBegin;
		}
		size_t groupEnd = selectedIndex + 1;
		while (groupEnd < attempts.size() &&
		       attempts[groupEnd].scoreinfo_index == selectedScoreInfo)
		{
			++groupEnd;
		}
		for (size_t attemptIndex = groupBegin; attemptIndex < groupEnd; ++attemptIndex)
		{
			if (replaySelected[attemptIndex] == 0)
			{
				replaySelected[attemptIndex] = static_cast<unsigned char>(1);
				replayAttemptIndexes.push_back(attemptIndex);
			}
		}
	}
	std::sort(replayAttemptIndexes.begin(), replayAttemptIndexes.end());
	const char *unselectedPrefixEnv =
		getenv("FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW_UNSELECTED_PREFIX");
	int unselectedPrefix = unselectedPrefixEnv == NULL ||
	                        unselectedPrefixEnv[0] == '\0' ?
		1 : atoi(unselectedPrefixEnv);
	if (unselectedPrefix < 0)
	{
		unselectedPrefix = 0;
	}
	if (unselectedPrefix > 5)
	{
		unselectedPrefix = 5;
	}
	if (unselectedPrefix > 0)
	{
		std::vector<unsigned char> scoreInfoSelected(
			finalScoreInfo.size(),
			static_cast<unsigned char>(0));
		for (size_t i = 0; i < replayAttemptIndexes.size(); ++i)
		{
			const size_t attemptIndex = replayAttemptIndexes[i];
			if (attemptIndex < attempts.size() &&
			    attempts[attemptIndex].scoreinfo_index >= 0 &&
			    static_cast<size_t>(attempts[attemptIndex].scoreinfo_index) <
				    scoreInfoSelected.size())
			{
				scoreInfoSelected[
					static_cast<size_t>(
						attempts[attemptIndex].scoreinfo_index)] =
					static_cast<unsigned char>(1);
			}
		}
		for (size_t attemptIndex = 0; attemptIndex < attempts.size();)
		{
			const int scoreInfoIndex = attempts[attemptIndex].scoreinfo_index;
			size_t groupEnd = attemptIndex + 1;
			while (groupEnd < attempts.size() &&
			       attempts[groupEnd].scoreinfo_index == scoreInfoIndex)
			{
				++groupEnd;
			}
			const bool scoreInfoCovered =
				scoreInfoIndex >= 0 &&
				static_cast<size_t>(scoreInfoIndex) < scoreInfoSelected.size() &&
				scoreInfoSelected[static_cast<size_t>(scoreInfoIndex)] != 0;
			if (!scoreInfoCovered)
			{
				size_t added = 0;
				for (size_t addIndex = attemptIndex;
				     addIndex < groupEnd &&
				     added < static_cast<size_t>(unselectedPrefix);
				     ++addIndex, ++added)
				{
					if (replaySelected[addIndex] == 0)
					{
						replaySelected[addIndex] = static_cast<unsigned char>(1);
						replayAttemptIndexes.push_back(addIndex);
					}
				}
			}
			attemptIndex = groupEnd;
		}
		std::sort(replayAttemptIndexes.begin(), replayAttemptIndexes.end());
	}
	const char *forceAllEnv =
		getenv("FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW_FORCE_ALL");
	if (forceAllEnv != NULL && forceAllEnv[0] != '\0' && forceAllEnv[0] != '0')
	{
		replayAttemptIndexes.clear();
		replayAttemptIndexes.reserve(attempts.size());
		for (size_t attemptIndex = 0; attemptIndex < attempts.size(); ++attemptIndex)
		{
			replayAttemptIndexes.push_back(attemptIndex);
		}
	}
	selectedAttemptIndexes.swap(replayAttemptIndexes);

	vector<struct triplex> myTriplexList;
	std::string smallSeq;
	uint64_t cpuAlignAttempts = 0;
	double cpuAlignSeconds = 0.0;
	double convertSeconds = 0.0;
	int currentScoreInfo = -1;
	FasimGasal2Attempt bestAttempt;
	FasimGasal2Attempt lastAttempt;
	StripedSmithWaterman::Alignment bestAlignment;
	StripedSmithWaterman::Alignment lastAlignment;
	bool haveBest = false;
	bool haveLast = false;
	bool emitted = false;

	auto emit_alignment = [&](const FasimGasal2Attempt &attempt,
	                          const StripedSmithWaterman::Alignment &localAlignment)
	{
		if (localAlignment.sw_score == 0)
		{
			return;
		}
		StripedSmithWaterman::Alignment emitAlignment = localAlignment;
		emitAlignment.ref_begin += attempt.start;
		emitAlignment.ref_end += attempt.start;
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(emitAlignment,
		                 myTriplexList,
		                 strA,
		                 strB,
		                 strSrc,
		                 nt_table,
		                 dnaStartPos,
		                 rule,
		                 strand,
		                 Para,
		                 penaltyT,
		                 penaltyC,
		                 ntMin,
		                 ntMax,
		                 materializeAlignmentStrings);
		convertSeconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - convertStart).count();
	};

	auto flush_scoreinfo = [&]()
	{
		if (currentScoreInfo >= 0 && !emitted)
		{
			if (haveBest)
			{
				emit_alignment(bestAttempt, bestAlignment);
			}
			else if (haveLast && lastAlignment.sw_score != 0)
			{
				emit_alignment(lastAttempt, lastAlignment);
			}
		}
		haveBest = false;
		haveLast = false;
		emitted = false;
		bestAlignment.Clear();
		lastAlignment.Clear();
		bestAttempt = FasimGasal2Attempt();
		lastAttempt = FasimGasal2Attempt();
	};

	for (size_t i = 0; i < selectedAttemptIndexes.size(); ++i)
	{
		const size_t attemptIndex = selectedAttemptIndexes[i];
		if (attemptIndex >= attempts.size())
		{
			if (errorOut != NULL)
			{
				*errorOut = "selected_attempt_index_out_of_range";
			}
			fasim_gasal2_record_attempt_consumer_shadow_replay(
				0, cpuAlignAttempts, cpuAlignSeconds, convertSeconds,
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - totalStart).count(),
				false,
				"selected_attempt_index_out_of_range");
			return false;
		}
		const FasimGasal2Attempt &attempt = attempts[attemptIndex];
		if (attempt.scoreinfo_index != currentScoreInfo)
		{
			flush_scoreinfo();
			currentScoreInfo = attempt.scoreinfo_index;
		}
		if (emitted)
		{
			continue;
		}
		if (attempt.scoreinfo_index < 0 ||
		    static_cast<size_t>(attempt.scoreinfo_index) >= finalScoreInfo.size())
		{
			continue;
		}
		smallSeq = strB.substr(static_cast<size_t>(attempt.start),
		                       static_cast<size_t>(attempt.cutlength));
		StripedSmithWaterman::Alignment localAlignment;
		const std::chrono::steady_clock::time_point alignStart =
			std::chrono::steady_clock::now();
		aligner.Align(strA.c_str(),
		              smallSeq.c_str(),
		              smallSeq.size(),
		              filter,
		              &localAlignment,
		              maskLen);
		cpuAlignSeconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - alignStart).count();
		++cpuAlignAttempts;
		lastAttempt = attempt;
		lastAlignment = localAlignment;
		haveLast = true;
		if (localAlignment.sw_score >=
		    finalScoreInfo[static_cast<size_t>(attempt.scoreinfo_index)].score)
		{
			emit_alignment(attempt, localAlignment);
			emitted = true;
			continue;
		}
		if (localAlignment.sw_score > bestAlignment.sw_score &&
		    localAlignment.ref_end == attempt.cutlength - 1)
		{
			bestAttempt = attempt;
			bestAlignment = localAlignment;
			haveBest = true;
		}
	}
	flush_scoreinfo();

	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	}
	for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
	{
		triplex atr = myTriplexList[i];
		if (atr.identity >= paraList.minIdentity &&
		    atr.tri_score >= paraList.minStability &&
		    atr.nt >= ntMin)
		{
			shadowTriplexList.push_back(atr);
		}
	}
	fasim_gasal2_record_attempt_consumer_shadow_replay(
		cpuAlignAttempts,
		cpuAlignAttempts,
		cpuAlignSeconds,
		convertSeconds,
		std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count(),
		true,
		"attempt_consumer_shadow_active");
	return true;
}

// Isolated v1 feasibility probe.  The GPU owns the score-only pass; this
// first spike intentionally keeps the ordered consumer and canonical
// traceback on the host so that correctness and cost can be measured without
// changing the production result path.
inline bool fasim_long_query_gpu_consumer_spike_v1_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	const std::vector<FasimConsumerAttemptTraceRow> &cpuReferenceAttempts,
	bool validateAgainstCpu,
	vector<struct triplex> &shadowTriplexList,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	FasimLongQueryGpuConsumerSpikeResult *result,
	std::string *errorOut,
	std::ostream *attemptTraceOut = NULL,
	uint64_t attemptTraceTaskId = std::numeric_limits<uint64_t>::max())
{
	FasimLongQueryGpuConsumerSpikeResult localResult;
	if (result == NULL)
	{
		result = &localResult;
	}
	*result = FasimLongQueryGpuConsumerSpikeResult();
	result->validation_enabled = validateAgainstCpu;
	result->lazy_reverse_shadow_requested =
		fasim_long_query_gpu_consumer_lazy_reverse_shadow_runtime();
	shadowTriplexList.clear();
	if (errorOut != NULL)
	{
		errorOut->clear();
	}
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();

	if (finalScoreInfo.empty())
	{
		if (result->lazy_reverse_shadow_requested)
		{
			result->lazy_reverse_shadow_active = true;
			result->lazy_reverse_selection_equal = true;
			result->lazy_reverse_reasons_equal = true;
		}
		result->ok = true;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return true;
	}
	const int8_t nt_table[128] = {
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4
	};

	std::vector<FasimGasal2Attempt> attempts;
	attempts.reserve(finalScoreInfo.size() * 5);
	for (size_t scoreInfoIndex = 0;
	     scoreInfoIndex < finalScoreInfo.size();
	     ++scoreInfoIndex)
	{
		const StripedSmithWaterman::scoreInfo &scoreInfo =
			finalScoreInfo[scoreInfoIndex];
		float identity = 0.6f;
		int identityRound = 0;
		while (identity <= 1.0f)
		{
			int cutlength = static_cast<int>(scoreInfo.score + 24) /
				(9 * identity - 4) + 1;
			cutlength = scoreInfo.position - cutlength + 1 > 0 ?
				cutlength : scoreInfo.position + 1;
			const int start = scoreInfo.position - cutlength + 1;
			if (start >= 0 && cutlength > 0 &&
				start + cutlength <= static_cast<int>(strB.size()))
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(scoreInfoIndex);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = scoreInfo.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.identity_round = identityRound;
				attempt.set_target_view(&strB,
				                        static_cast<size_t>(start),
				                        static_cast<size_t>(cutlength));
				attempts.push_back(attempt);
			}
			identity += 0.1f;
			++identityRound;
		}
	}
	result->scoreinfo_groups = static_cast<uint64_t>(finalScoreInfo.size());
	result->attempts = static_cast<uint64_t>(attempts.size());
	if (attempts.empty())
	{
		result->error = "empty_attempts";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}

	std::vector<FasimGasal2StreamedAttemptScore> endpointScores;
	FasimGasal2StreamedAttemptScoreTelemetry endpointTelemetry;
	std::string bridgeError;
	const std::chrono::steady_clock::time_point scoreStart =
		std::chrono::steady_clock::now();
	if (!fasim_gasal2_streamed_attempt_score_v1(
			strA, attempts, &endpointScores, &endpointTelemetry, &bridgeError,
			attemptTraceTaskId))
	{
		result->error = bridgeError.empty() ?
			"streamed_attempt_score_failed" : bridgeError;
		if (errorOut != NULL) *errorOut = result->error;
		result->score_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - scoreStart).count();
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
	result->score_seconds = std::chrono::duration<double>(
		std::chrono::steady_clock::now() - scoreStart).count();
	result->gpu_scored_attempts = endpointTelemetry.gpu_scored_requests;
	result->exact_forward_only = endpointTelemetry.exact_forward_only;
	result->cached_endpoint_replay = endpointTelemetry.cached_endpoint_replay;
	result->cache_records = endpointTelemetry.cache_records;
	result->cache_load_seconds = endpointTelemetry.cache_load_seconds;
	result->cache_lookup_seconds = endpointTelemetry.cache_lookup_seconds;
	result->endpoint_batches = endpointTelemetry.batches;
	result->gpu_kernel_seconds = endpointTelemetry.gpu_seconds;
	result->h2d_seconds = endpointTelemetry.h2d_seconds;
	result->d2h_seconds = endpointTelemetry.d2h_seconds;
	if (endpointScores.size() != attempts.size() ||
		endpointTelemetry.gpu_scored_requests != attempts.size())
	{
		result->error = "gpu_score_count_mismatch";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
	if (result->exact_forward_only && result->lazy_reverse_shadow_requested)
	{
		result->error =
			"forward_only_timing_incompatible_with_lazy_reverse_shadow";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}

	std::vector<FasimGasal2ScoreOnlyAlignment> scores(attempts.size());
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const FasimGasal2StreamedAttemptScore &gpu = endpointScores[i];
		FasimGasal2ScoreOnlyAlignment &gpuRow = scores[i];
		gpuRow.scoreinfo_index = attempt.scoreinfo_index;
		gpuRow.cutlength = attempt.cutlength;
		gpuRow.start = attempt.start;
		gpuRow.prealign_score = attempt.prealign_score;
		gpuRow.score = gpu.score;
		gpuRow.forward_score = gpu.forward_score;
		gpuRow.reverse_score = gpu.reverse_score;
		gpuRow.query_end = gpu.query_end;
		gpuRow.ref_end = gpu.ref_end_global;
		gpuRow.numeric_path = gpu.numeric_path;
	}

	// Optional development trace.  It is emitted from the endpoint array before
	// ordered selection or continuation can discard any attempt.  The trace is
	// deliberately diagnostic and has no effect when the stream is absent.
	if (attemptTraceOut != NULL && *attemptTraceOut)
	{
		for (size_t i = 0; i < attempts.size(); ++i)
		{
			const FasimGasal2Attempt &attempt = attempts[i];
			const FasimGasal2StreamedAttemptScore &gpu = endpointScores[i];
			const int refEndLocal = gpu.ref_end_local;
			const bool terminal = refEndLocal == attempt.cutlength - 1;
			const uint64_t padded = gpu.padded_target_length > 0 ?
				static_cast<uint64_t>(gpu.padded_target_length) :
				static_cast<uint64_t>(attempt.cutlength);
			const uint64_t queryLength = static_cast<uint64_t>(strA.size());
			const uint64_t cells = queryLength > 0 && padded > 0 &&
				queryLength <= std::numeric_limits<uint64_t>::max() / padded ?
				queryLength * padded : std::numeric_limits<uint64_t>::max();
			int scoreInfoPosition = -1;
			int scoreInfoScore = attempt.prealign_score;
			if (attempt.scoreinfo_index >= 0 &&
				static_cast<size_t>(attempt.scoreinfo_index) < finalScoreInfo.size())
			{
				scoreInfoPosition = finalScoreInfo[
					static_cast<size_t>(attempt.scoreinfo_index)].position;
				scoreInfoScore = finalScoreInfo[
					static_cast<size_t>(attempt.scoreinfo_index)].score;
			}
			*attemptTraceOut
				<< attemptTraceTaskId << '\t'
				<< attempt.scoreinfo_index << '\t'
				<< scoreInfoPosition << '\t'
				<< scoreInfoScore << '\t'
				<< i << '\t'
				<< attempt.identity_round << '\t'
				<< attempt.start << '\t'
				<< attempt.cutlength << '\t'
				<< attempt.prealign_score << '\t'
				<< gpu.forward_score << '\t'
				<< gpu.reverse_score << '\t'
				<< gpu.score << '\t'
				<< gpu.query_end << '\t'
				<< refEndLocal << '\t'
				<< gpu.ref_end_global << '\t'
				<< (terminal ? 1 : 0) << '\t'
				<< gpu.numeric_path << '\t'
				<< padded << '\t'
				<< queryLength << '\t'
				<< cells << '\t'
				<< cells << '\n';
		}
		attemptTraceOut->flush();
	}

	std::vector<FasimGasal2ScoreOnlyAlignment> cpuScores;
	if (validateAgainstCpu)
	{
		cpuScores.resize(attempts.size());
		const std::chrono::steady_clock::time_point oracleStart =
			std::chrono::steady_clock::now();
		for (size_t i = 0; i < attempts.size(); ++i)
		{
			const FasimGasal2Attempt &attempt = attempts[i];
			const FasimGasal2StreamedAttemptScore &gpu = endpointScores[i];
			const std::string small(attempt.target_data(), attempt.target_size());
			StripedSmithWaterman::Alignment cpuAlignment;
			aligner.Align(strA.c_str(), small.c_str(), small.size(),
			              filter, &cpuAlignment, maskLen);
			++result->cpu_oracle_attempts;
			FasimGasal2ScoreOnlyAlignment &cpuRow = cpuScores[i];
			cpuRow.scoreinfo_index = attempt.scoreinfo_index;
			cpuRow.cutlength = attempt.cutlength;
			cpuRow.start = attempt.start;
			cpuRow.prealign_score = attempt.prealign_score;
			cpuRow.score = cpuAlignment.sw_score;
			cpuRow.query_end = cpuAlignment.query_end;
			cpuRow.ref_end = attempt.start + cpuAlignment.ref_end;

			const bool scoreMismatch = gpu.score != cpuAlignment.sw_score;
			const bool queryEndMismatch = gpu.query_end != cpuAlignment.query_end;
			const bool refEndMismatch =
				gpu.ref_end_local != cpuAlignment.ref_end;
			const bool gpuTerminal =
				gpu.ref_end_local == attempt.cutlength - 1;
			const bool cpuTerminal =
				cpuAlignment.ref_end == attempt.cutlength - 1;
			const bool terminalMismatch = gpuTerminal != cpuTerminal;
			result->score_mismatches += scoreMismatch ? 1ULL : 0ULL;
			result->query_end_mismatches += queryEndMismatch ? 1ULL : 0ULL;
			result->ref_end_local_mismatches += refEndMismatch ? 1ULL : 0ULL;
			result->terminal_mismatches += terminalMismatch ? 1ULL : 0ULL;
			if (scoreMismatch || queryEndMismatch || refEndMismatch || terminalMismatch)
			{
				++result->attempt_mismatch_rows;
				if (result->first_attempt_mismatch == "none")
				{
					std::ostringstream mismatch;
					mismatch << "attempt=" << i
					         << ":group=" << attempt.scoreinfo_index
					         << ":round=" << attempt.identity_round
					         << ":gpu=" << gpu.score << ',' << gpu.query_end
					         << ',' << gpu.ref_end_local << ',' << (gpuTerminal ? 1 : 0)
					         << ":cpu=" << cpuAlignment.sw_score << ','
					         << cpuAlignment.query_end << ',' << cpuAlignment.ref_end
					         << ',' << (cpuTerminal ? 1 : 0);
					result->first_attempt_mismatch = mismatch.str();
				}
			}
		}
		result->cpu_oracle_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - oracleStart).count();
		if (result->attempt_mismatch_rows != 0)
		{
			result->error = "attempt_l3_mismatch";
			if (errorOut != NULL) *errorOut = result->error;
			result->total_seconds = std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count();
			return false;
		}
	}

	std::vector<size_t> selected;
	std::vector<size_t> cpuSelected;
	std::vector<std::string> reasons;
	std::vector<std::string> cpuReasons;
	const std::chrono::steady_clock::time_point selectStart =
		std::chrono::steady_clock::now();
	if (!fasim_gasal2_consumer_spike_select_from_scores(
			attempts, scores, &selected, &reasons, &bridgeError))
	{
		result->error = bridgeError.empty() ? "consumer_selection_failed" : bridgeError;
		if (errorOut != NULL) *errorOut = result->error;
		result->select_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - selectStart).count();
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
	if (validateAgainstCpu &&
		!fasim_gasal2_consumer_spike_select_from_scores(
			attempts, cpuScores, &cpuSelected, &cpuReasons, &bridgeError))
	{
		result->error = bridgeError.empty() ?
			"cpu_consumer_selection_failed" : bridgeError;
		if (errorOut != NULL) *errorOut = result->error;
		result->select_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - selectStart).count();
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
	result->select_seconds = std::chrono::duration<double>(
		std::chrono::steady_clock::now() - selectStart).count();
	result->control_selected_attempts = static_cast<uint64_t>(selected.size());
	result->cpu_control_selected_attempts =
		static_cast<uint64_t>(cpuSelected.size());
	result->consumer_selection_equal =
		!validateAgainstCpu || selected == cpuSelected;
	if (validateAgainstCpu && !result->consumer_selection_equal)
	{
		result->error = "consumer_selection_mismatch";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}

	if (result->lazy_reverse_shadow_requested)
	{
		const std::chrono::steady_clock::time_point lazyStart =
			std::chrono::steady_clock::now();
		FasimGasal2LazyReverseShadowResult lazy;
		std::string lazyError;
		if (!fasim_gasal2_lazy_reverse_shadow_select(
				attempts, scores, &lazy, &lazyError))
		{
			result->error = lazyError.empty() ?
				"lazy_reverse_shadow_failed" : lazyError;
			if (errorOut != NULL) *errorOut = result->error;
			result->lazy_reverse_shadow_seconds =
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - lazyStart).count();
			result->total_seconds = std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count();
			return false;
		}
		result->lazy_reverse_shadow_active = true;
		result->lazy_reverse_full_attempts = lazy.full_reverse_attempts;
		result->lazy_reverse_attempts = lazy.lazy_reverse_attempts;
		result->lazy_reverse_threshold_attempts =
			lazy.lazy_reverse_threshold_attempts;
		result->lazy_reverse_best_attempts = lazy.lazy_reverse_best_attempts;
		result->lazy_reverse_last_attempts = lazy.lazy_reverse_last_attempts;
		result->lazy_reverse_reused_for_best = lazy.lazy_reverse_reused_for_best;
		result->lazy_reverse_reused_for_last = lazy.lazy_reverse_reused_for_last;
		result->lazy_reverse_full_envelope_cells =
			lazy.full_reverse_envelope_cells;
		result->lazy_reverse_envelope_cells = lazy.lazy_reverse_envelope_cells;
		result->lazy_reverse_threshold_envelope_cells =
			lazy.lazy_reverse_threshold_envelope_cells;
		result->lazy_reverse_best_envelope_cells =
			lazy.lazy_reverse_best_envelope_cells;
		result->lazy_reverse_last_envelope_cells =
			lazy.lazy_reverse_last_envelope_cells;
		result->lazy_reverse_selection_equal =
			selected == lazy.selected_attempt_indexes;
		result->lazy_reverse_reasons_equal = reasons == lazy.selection_reasons;
		result->lazy_reverse_shadow_seconds =
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - lazyStart).count();
		if (!result->lazy_reverse_selection_equal ||
			!result->lazy_reverse_reasons_equal)
		{
			size_t mismatch = 0;
			const size_t sharedSelected = std::min(
				selected.size(), lazy.selected_attempt_indexes.size());
			while (mismatch < sharedSelected &&
				selected[mismatch] == lazy.selected_attempt_indexes[mismatch])
			{
				++mismatch;
			}
			std::ostringstream detail;
			detail << "selected_position=" << mismatch
			       << ":full_count=" << selected.size()
			       << ":lazy_count=" << lazy.selected_attempt_indexes.size();
			if (mismatch < selected.size())
			{
				detail << ":full_index=" << selected[mismatch];
			}
			if (mismatch < lazy.selected_attempt_indexes.size())
			{
				detail << ":lazy_index=" << lazy.selected_attempt_indexes[mismatch];
			}
			if (result->lazy_reverse_selection_equal)
			{
				mismatch = 0;
				const size_t sharedReasons = std::min(
					reasons.size(), lazy.selection_reasons.size());
				while (mismatch < sharedReasons &&
					reasons[mismatch] == lazy.selection_reasons[mismatch])
				{
					++mismatch;
				}
				detail.str("");
				detail.clear();
				detail << "reason_attempt=" << mismatch;
				if (mismatch < reasons.size())
				{
					detail << ":full_reason=" << reasons[mismatch];
				}
				if (mismatch < lazy.selection_reasons.size())
				{
					detail << ":lazy_reason=" << lazy.selection_reasons[mismatch];
				}
			}
			result->first_lazy_reverse_mismatch = detail.str();
			result->error = "lazy_reverse_shadow_selection_mismatch";
			if (errorOut != NULL) *errorOut = result->error;
			result->total_seconds = std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count();
			return false;
		}
	}

	// A selected winner is insufficient to reproduce the ordered state machine.
	// Threshold winners stop at that attempt. Best-fallback and last winners are
	// known only after every attempt in their scoreInfo group has executed.
	std::vector<unsigned char> replayMask(attempts.size(), 0);
	std::vector<size_t> replay;
	for (size_t selectedIndex : selected)
	{
		if (selectedIndex >= attempts.size())
		{
			result->error = "selected_index_out_of_range";
			if (errorOut != NULL) *errorOut = result->error;
			result->total_seconds = std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count();
			return false;
		}
		const int group = attempts[selectedIndex].scoreinfo_index;
		size_t begin = selectedIndex;
		while (begin > 0 && attempts[begin - 1].scoreinfo_index == group)
		{
			--begin;
		}
		size_t end = selectedIndex;
		if (selectedIndex >= reasons.size() ||
			reasons[selectedIndex] != "threshold")
		{
			while (end + 1 < attempts.size() &&
			       attempts[end + 1].scoreinfo_index == group)
			{
				++end;
			}
		}
		for (size_t i = begin; i <= end; ++i)
		{
			if (replayMask[i] == 0)
			{
				replayMask[i] = 1;
				replay.push_back(i);
			}
		}
	}
	std::sort(replay.begin(), replay.end());
	result->replay_attempts = static_cast<uint64_t>(replay.size());
	result->cpu_reference_align_attempts =
		static_cast<uint64_t>(cpuReferenceAttempts.size());
	result->consumer_attempt_prefix_equal = true;
	const size_t sharedPrefix = std::min(replay.size(), cpuReferenceAttempts.size());
	for (size_t i = 0; validateAgainstCpu && i < sharedPrefix; ++i)
	{
		const size_t attemptIndex = replay[i];
		const FasimGasal2Attempt &candidate = attempts[attemptIndex];
		const FasimGasal2ScoreOnlyAlignment &candidateScore =
			scores[attemptIndex];
		const FasimConsumerAttemptTraceRow &authority =
			cpuReferenceAttempts[i];
		const bool equal =
			candidate.scoreinfo_index == authority.scoreinfo_index &&
			candidate.identity_round == authority.identity_round &&
			candidate.start == authority.start &&
			candidate.cutlength == authority.cutlength &&
			candidateScore.score == authority.score &&
			candidateScore.query_end == authority.query_end &&
			candidateScore.ref_end - candidate.start == authority.ref_end_local;
		if (!equal)
		{
			result->consumer_attempt_prefix_equal = false;
			std::ostringstream mismatch;
			mismatch << "prefix=" << i
			         << ":gpu=" << candidate.scoreinfo_index << ','
			         << candidate.identity_round << ',' << candidate.start << ','
			         << candidate.cutlength << ',' << candidateScore.score << ','
			         << candidateScore.query_end << ','
			         << (candidateScore.ref_end - candidate.start)
			         << ":cpu=" << authority.scoreinfo_index << ','
			         << authority.identity_round << ',' << authority.start << ','
			         << authority.cutlength << ',' << authority.score << ','
			         << authority.query_end << ',' << authority.ref_end_local;
			result->first_consumer_mismatch = mismatch.str();
			break;
		}
	}
	if (validateAgainstCpu && result->consumer_attempt_prefix_equal &&
		replay.size() != cpuReferenceAttempts.size())
	{
		result->consumer_attempt_prefix_equal = false;
		std::ostringstream mismatch;
		mismatch << "prefix=" << sharedPrefix;
		if (sharedPrefix < replay.size())
		{
			const size_t attemptIndex = replay[sharedPrefix];
			const FasimGasal2Attempt &candidate = attempts[attemptIndex];
			const FasimGasal2ScoreOnlyAlignment &candidateScore =
				scores[attemptIndex];
			mismatch << ":gpu=" << candidate.scoreinfo_index << ','
			         << candidate.identity_round << ',' << candidate.start << ','
			         << candidate.cutlength << ',' << candidateScore.score << ','
			         << candidateScore.query_end << ','
			         << (candidateScore.ref_end - candidate.start);
		}
		else
		{
			mismatch << ":gpu=eof";
		}
		if (sharedPrefix < cpuReferenceAttempts.size())
		{
			const FasimConsumerAttemptTraceRow &authority =
				cpuReferenceAttempts[sharedPrefix];
			mismatch << ":cpu=" << authority.scoreinfo_index << ','
			         << authority.identity_round << ',' << authority.start << ','
			         << authority.cutlength << ',' << authority.score << ','
			         << authority.query_end << ',' << authority.ref_end_local;
		}
		else
		{
			mismatch << ":cpu=eof";
		}
		result->first_consumer_mismatch = mismatch.str();
	}
	if (validateAgainstCpu && !result->consumer_attempt_prefix_equal)
	{
		result->error = "consumer_attempt_prefix_mismatch";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
	if (replay.empty())
	{
		result->error = "empty_replay_prefix";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}

	vector<struct triplex> convertedRows;
	result->cpu_continuation_requested =
		fasim_long_query_gpu_consumer_cpu_continuation_runtime();
#if !defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) && \
	!defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
	if (result->cpu_continuation_requested)
	{
		result->error = "cpu_continuation_not_built";
		if (errorOut != NULL) *errorOut = result->error;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	}
#endif
	int currentGroup = -1;
	FasimGasal2Attempt bestAttempt;
	FasimGasal2Attempt lastAttempt;
	StripedSmithWaterman::Alignment bestAlignment;
	StripedSmithWaterman::Alignment lastAlignment;
	bool haveBest = false;
	bool haveLast = false;
	bool emitted = false;
	const std::chrono::steady_clock::time_point tracebackStart =
		std::chrono::steady_clock::now();
	auto emit = [&](const FasimGasal2Attempt &attempt,
	                const StripedSmithWaterman::Alignment &local)
	{
		if (local.sw_score == 0)
		{
			return;
		}
		StripedSmithWaterman::Alignment global = local;
		global.ref_begin += attempt.start;
		global.ref_end += attempt.start;
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(global, convertedRows, strA, strB, strSrc,
		                 nt_table, dnaStartPos, rule, strand, Para,
		                 penaltyT, penaltyC, ntMin, ntMax,
		                 materializeAlignmentStrings);
		result->convert_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - convertStart).count();
	};
#if defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) || \
	defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
	if (result->cpu_continuation_requested)
	{
		result->cpu_continuation_active = true;
		for (size_t selectedIndex : selected)
		{
			if (selectedIndex >= attempts.size() || selectedIndex >= scores.size() ||
				selectedIndex >= reasons.size())
			{
				++result->cpu_continuation_failures;
				result->error = "cpu_continuation_selected_index_out_of_range";
				if (errorOut != NULL) *errorOut = result->error;
				result->total_seconds = std::chrono::duration<double>(
					std::chrono::steady_clock::now() - totalStart).count();
				return false;
			}
			const FasimGasal2Attempt &attempt = attempts[selectedIndex];
			const FasimGasal2ScoreOnlyAlignment &score = scores[selectedIndex];
			const std::string small = strB.substr(
				static_cast<size_t>(attempt.start),
				static_cast<size_t>(attempt.cutlength));
			StripedSmithWaterman::ForwardEndpoint endpoint;
			endpoint.score1 = score.forward_score;
			endpoint.score2 = 0;
			endpoint.ref_end1 = score.ref_end - attempt.start;
			endpoint.query_end1 = score.query_end;
			endpoint.ref_end2 = -1;
			endpoint.numeric_path = score.numeric_path;
			StripedSmithWaterman::Alignment local;
			const std::chrono::steady_clock::time_point continuationStart =
				std::chrono::steady_clock::now();
			const bool continuationOk = aligner.AlignFromForward(
				strA.c_str(), small.c_str(), static_cast<int>(small.size()),
				filter, endpoint, &local, maskLen);
			result->traceback_seconds += std::chrono::duration<double>(
				std::chrono::steady_clock::now() - continuationStart).count();
			++result->cpu_continuation_calls;
			++result->cpu_align_attempts;
			if (!continuationOk || local.sw_score != score.score ||
				local.ref_end != endpoint.ref_end1 ||
				local.query_end != endpoint.query_end1)
			{
				++result->cpu_continuation_failures;
				std::ostringstream detail;
				detail << "cpu_continuation_contract_mismatch"
				       << ":attempt=" << selectedIndex
				       << ":expected=" << score.score << ','
				       << endpoint.ref_end1 << ',' << endpoint.query_end1
				       << ":observed=" << local.sw_score << ','
				       << local.ref_end << ',' << local.query_end
				       << ":ok=" << (continuationOk ? 1 : 0);
				result->error = detail.str();
				if (errorOut != NULL) *errorOut = result->error;
				result->total_seconds = std::chrono::duration<double>(
					std::chrono::steady_clock::now() - totalStart).count();
				return false;
			}
			emit(attempt, local);
			if (reasons[selectedIndex] == "threshold")
			{
				++result->threshold_groups;
			}
			else if (reasons[selectedIndex] == "best_fallback")
			{
				++result->best_fallback_groups;
			}
			else if (reasons[selectedIndex] == "last")
			{
				++result->last_groups;
			}
		}
		result->empty_groups = result->scoreinfo_groups >= selected.size() ?
			result->scoreinfo_groups - selected.size() : 0;
	}
	else
#endif
	{
	auto flush = [&]()
	{
		if (currentGroup >= 0 && !emitted)
		{
			if (haveBest)
			{
				emit(bestAttempt, bestAlignment);
				++result->best_fallback_groups;
			}
			else if (haveLast && lastAlignment.sw_score != 0)
			{
				emit(lastAttempt, lastAlignment);
				++result->last_groups;
			}
			else
			{
				++result->empty_groups;
			}
		}
		haveBest = false;
		haveLast = false;
		emitted = false;
		bestAlignment.Clear();
		lastAlignment.Clear();
		bestAttempt = FasimGasal2Attempt();
		lastAttempt = FasimGasal2Attempt();
	};

	for (size_t attemptIndex : replay)
	{
		const FasimGasal2Attempt &attempt = attempts[attemptIndex];
		if (attempt.scoreinfo_index != currentGroup)
		{
			flush();
			currentGroup = attempt.scoreinfo_index;
		}
		if (emitted)
		{
			continue;
		}
		const std::string small = strB.substr(
			static_cast<size_t>(attempt.start),
			static_cast<size_t>(attempt.cutlength));
		StripedSmithWaterman::Alignment local;
		const std::chrono::steady_clock::time_point alignStart =
			std::chrono::steady_clock::now();
		aligner.Align(strA.c_str(), small.c_str(), small.size(),
		              filter, &local, maskLen);
		result->traceback_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - alignStart).count();
		++result->cpu_align_attempts;
		lastAttempt = attempt;
		lastAlignment = local;
		haveLast = true;
		if (local.sw_score >= finalScoreInfo[
				static_cast<size_t>(attempt.scoreinfo_index)].score)
		{
			emit(attempt, local);
			emitted = true;
			++result->threshold_groups;
			continue;
		}
		if (local.sw_score > bestAlignment.sw_score &&
			local.ref_end == attempt.cutlength - 1)
		{
			bestAttempt = attempt;
			bestAlignment = local;
			haveBest = true;
		}
	}
	flush();
	}

	const std::chrono::steady_clock::time_point sortStart =
		std::chrono::steady_clock::now();
	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple);
		convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
		                                sameMyTriplex), convertedRows.end());
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple2);
		convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
		                                sameMyTriplex), convertedRows.end());
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexSingle);
	}
	(void)sortStart;
	const size_t topLimit = std::min(convertedRows.size(), static_cast<size_t>(N));
	for (size_t i = 0; i < topLimit; ++i)
	{
		const triplex &row = convertedRows[i];
		if (row.identity >= paraList.minIdentity &&
			row.tri_score >= paraList.minStability && row.nt >= ntMin)
		{
			shadowTriplexList.push_back(row);
		}
	}
	result->ok = true;
	result->total_seconds = std::chrono::duration<double>(
		std::chrono::steady_clock::now() - totalStart).count();
	return true;
}

// Global development-only F1 scheduler.  All task descriptors for a given
// identity round are submitted in one global stage call.  This declaration is
// kept next to the single-task implementation below so both paths share the
// same continuation contract.
inline bool fasim_long_query_gpu_consumer_f1_batch_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &query,
	const std::vector<FasimLongQueryGpuConsumerF1TaskInput> &taskInputs,
	std::vector<std::vector<struct triplex> > &taskTriplexLists,
	std::vector<FasimLongQueryGpuConsumerF1Result> &taskResults,
	long ntMin,
	long ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	std::string *errorOut);

// Development-only per-task F1 scheduler.  It keeps the scientific consumer on the
// host, but submits only the ordered forward prefix and the reverse requests
// proven necessary by the forward-score upper bound.  The default path never
// calls this function.
inline bool fasim_long_query_gpu_consumer_f1_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	vector<struct triplex> &shadowTriplexList,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	FasimLongQueryGpuConsumerF1Result *result,
	std::string *errorOut)
{
	FasimLongQueryGpuConsumerF1Result localResult;
	if (result == NULL) result = &localResult;
	*result = FasimLongQueryGpuConsumerF1Result();
	shadowTriplexList.clear();
	if (errorOut != NULL) errorOut->clear();
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();

	if (!fasim_long_query_gpu_consumer_f1_scheduler_runtime())
	{
		result->error = "f1_scheduler_not_requested";
		if (errorOut != NULL) *errorOut = result->error;
		return false;
	}
	if (!fasim_long_query_gpu_consumer_cpu_continuation_runtime())
	{
		result->error = "f1_requires_cpu_continuation_flag";
		if (errorOut != NULL) *errorOut = result->error;
		return false;
	}
#if !defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) && \
	!defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
	result->error = "f1_cpu_continuation_not_built";
	if (errorOut != NULL) *errorOut = result->error;
	return false;
#endif
	if (finalScoreInfo.empty())
	{
		result->ok = true;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return true;
	}

	struct F1GroupState
	{
		F1GroupState() :
			active(true), emitted(false), haveBest(false), bestScore(0),
			bestIndex(0), haveLast(false), lastIndex(0), selectedIndex(0),
			haveSelected(false), reason("empty")
		{
		}
		std::vector<size_t> indexes;
		bool active;
		bool emitted;
		bool haveBest;
		int bestScore;
		size_t bestIndex;
		bool haveLast;
		size_t lastIndex;
		size_t selectedIndex;
		bool haveSelected;
		std::string reason;
	};

	std::vector<FasimGasal2Attempt> attempts;
	std::vector<F1GroupState> groups(finalScoreInfo.size());
	attempts.reserve(finalScoreInfo.size() * 4);
	const int8_t nt_table[128] = {
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,0,4,1,4,4,4,2,4,4,4,4,4,4,4,4,
		4,4,4,4,3,0,4,4,4,4,4,4,4,4,4,4,
		4,0,4,1,4,4,4,2,4,4,4,4,4,4,4,4,
		4,4,4,4,3,0,4,4,4,4,4,4,4,4,4,4
	};
	for (size_t groupIndex = 0; groupIndex < finalScoreInfo.size(); ++groupIndex)
	{
		const StripedSmithWaterman::scoreInfo &info = finalScoreInfo[groupIndex];
		float identity = 0.6f;
		int identityRound = 0;
		while (identity <= 1.0f)
		{
			int cutlength = static_cast<int>(info.score + 24) /
				(9 * identity - 4) + 1;
			cutlength = info.position - cutlength + 1 > 0 ?
				cutlength : info.position + 1;
			const int start = info.position - cutlength + 1;
			if (start >= 0 && cutlength > 0 &&
				start + cutlength <= static_cast<int>(strB.size()))
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(groupIndex);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = info.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.identity_round = identityRound;
				attempt.set_target_view(&strB, static_cast<size_t>(start),
				                       static_cast<size_t>(cutlength));
				groups[groupIndex].indexes.push_back(attempts.size());
				attempts.push_back(attempt);
			}
			identity += 0.1f;
			++identityRound;
		}
		if (groups[groupIndex].indexes.empty())
		{
			result->error = "f1_empty_scoreinfo_group";
			if (errorOut != NULL) *errorOut = result->error;
			return false;
		}
	}
	result->scoreinfo_groups = static_cast<uint64_t>(groups.size());
	result->attempts = static_cast<uint64_t>(attempts.size());
	std::vector<FasimGasal2StreamedAttemptScore> forwardScores(attempts.size());
	std::vector<FasimGasal2StreamedAttemptScore> canonicalScores(attempts.size());
	std::vector<unsigned char> canonicalKnown(attempts.size(), 0);
	std::vector<unsigned char> reverseRequested(attempts.size(), 0);

	auto addTelemetry = [&](const FasimGasal2StreamedAttemptScoreTelemetry &telemetry,
	                        bool reverse)
	{
		if (reverse) result->reverse_seconds += telemetry.total_seconds;
		else result->forward_seconds += telemetry.total_seconds;
		result->gpu_kernel_seconds += telemetry.gpu_seconds;
		result->h2d_seconds += telemetry.h2d_seconds;
		result->d2h_seconds += telemetry.d2h_seconds;
	};
	auto fail = [&](const std::string &message) -> bool
	{
		result->error = message;
		if (errorOut != NULL) *errorOut = message;
		result->total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count();
		return false;
	};

	const size_t maxRounds = [&]() {
		size_t maximum = 0;
		for (size_t i = 0; i < groups.size(); ++i)
			maximum = std::max(maximum, groups[i].indexes.size());
		return maximum;
	}();
	for (size_t round = 0; round < maxRounds; ++round)
	{
		std::vector<size_t> roundIndexes;
		std::vector<FasimGasal2Attempt> roundAttempts;
		uint64_t activeGroups = 0;
		for (size_t groupIndex = 0; groupIndex < groups.size(); ++groupIndex)
		{
			F1GroupState &group = groups[groupIndex];
			if (!group.active || round >= group.indexes.size()) continue;
			++activeGroups;
			roundIndexes.push_back(group.indexes[round]);
			roundAttempts.push_back(attempts[group.indexes[round]]);
		}
		result->round_active_groups.push_back(activeGroups);
		result->round_forward_attempts.push_back(
			static_cast<uint64_t>(roundAttempts.size()));
		if (roundAttempts.empty())
		{
			result->round_reverse_requests.push_back(0);
			continue;
		}
		FasimGasal2StreamedAttemptScoreTelemetry forwardTelemetry;
		std::string stageError;
		std::vector<FasimGasal2StreamedAttemptScore> roundForward;
		if (!fasim_gasal2_streamed_attempt_forward_score_v1(
				strA, roundAttempts, &roundForward, &forwardTelemetry,
				&stageError))
		{
			return fail(stageError.empty() ? "f1_forward_stage_failed" : stageError);
		}
		addTelemetry(forwardTelemetry, false);
		result->forward_attempts += static_cast<uint64_t>(roundIndexes.size());
		for (size_t i = 0; i < roundIndexes.size(); ++i)
			forwardScores[roundIndexes[i]] = roundForward[i];

		std::vector<size_t> reverseIndexes;
		std::vector<FasimGasal2Attempt> reverseAttempts;
		std::vector<FasimGasal2StreamedAttemptScore> reverseForward;
		for (size_t i = 0; i < roundIndexes.size(); ++i)
		{
			const size_t globalIndex = roundIndexes[i];
			const FasimGasal2Attempt &attempt = attempts[globalIndex];
			const FasimGasal2StreamedAttemptScore &score = roundForward[i];
			F1GroupState &group = groups[static_cast<size_t>(attempt.scoreinfo_index)];
			group.haveLast = true;
			group.lastIndex = globalIndex;
			const bool terminal = score.ref_end_local == attempt.cutlength - 1;
			const bool needsThresholdCheck = score.forward_score >= attempt.prealign_score;
			const bool needsBestCheck = terminal &&
				score.forward_score > group.bestScore;
			if ((needsThresholdCheck || needsBestCheck) &&
				reverseRequested[globalIndex] == 0)
			{
				reverseRequested[globalIndex] = 1;
				reverseIndexes.push_back(globalIndex);
				reverseAttempts.push_back(attempt);
				reverseForward.push_back(score);
			}
		}
		result->round_reverse_requests.push_back(
			static_cast<uint64_t>(reverseIndexes.size()));
		result->reverse_requests += static_cast<uint64_t>(reverseIndexes.size());
		if (!reverseIndexes.empty())
		{
			FasimGasal2StreamedAttemptScoreTelemetry reverseTelemetry;
			std::vector<FasimGasal2StreamedAttemptScore> reverseScores;
			if (!fasim_gasal2_streamed_attempt_reverse_score_v1(
					strA, reverseAttempts, reverseForward, &reverseScores,
					&reverseTelemetry, &stageError))
			{
				return fail(stageError.empty() ? "f1_reverse_stage_failed" : stageError);
			}
			addTelemetry(reverseTelemetry, true);
			result->reverse_scored_attempts +=
				static_cast<uint64_t>(reverseIndexes.size());
			for (size_t i = 0; i < reverseIndexes.size(); ++i)
			{
				const size_t globalIndex = reverseIndexes[i];
				canonicalScores[globalIndex] = reverseScores[i];
				canonicalKnown[globalIndex] = 1;
				const FasimGasal2Attempt &attempt = attempts[globalIndex];
				F1GroupState &group = groups[
					static_cast<size_t>(attempt.scoreinfo_index)];
				const int canonical = reverseScores[i].score;
				if (!group.emitted && canonical >= attempt.prealign_score)
				{
					group.emitted = true;
					group.active = false;
					group.haveSelected = true;
					group.selectedIndex = globalIndex;
					group.reason = "threshold";
				}
				else if (!group.emitted &&
					canonical > group.bestScore &&
					reverseScores[i].ref_end_local == attempt.cutlength - 1)
				{
					group.bestScore = canonical;
					group.bestIndex = globalIndex;
					group.haveBest = true;
				}
			}
		}

		// A group whose final attempt was just consumed can retire via best or
		// defer the last fallback until its canonical reverse is available.
		for (size_t groupIndex = 0; groupIndex < groups.size(); ++groupIndex)
		{
			F1GroupState &group = groups[groupIndex];
			if (!group.active || round + 1 < group.indexes.size()) continue;
			if (group.haveBest)
			{
				group.active = false;
				group.emitted = true;
				group.haveSelected = true;
				group.selectedIndex = group.bestIndex;
				group.reason = "best_fallback";
			}
			else if (group.haveLast && canonicalKnown[group.lastIndex])
			{
				group.active = false;
				group.emitted = true;
				if (canonicalScores[group.lastIndex].score != 0)
				{
					group.haveSelected = true;
					group.selectedIndex = group.lastIndex;
					group.reason = "last";
				}
				else
				{
					group.reason = "empty";
				}
			}
		}
	}

	// Last fallback is the only decision that may require a deferred reverse.
	std::vector<size_t> deferredIndexes;
	std::vector<FasimGasal2Attempt> deferredAttempts;
	std::vector<FasimGasal2StreamedAttemptScore> deferredForward;
	for (size_t groupIndex = 0; groupIndex < groups.size(); ++groupIndex)
	{
		F1GroupState &group = groups[groupIndex];
		if (!group.active || !group.haveLast || canonicalKnown[group.lastIndex]) continue;
		const size_t globalIndex = group.lastIndex;
		if (reverseRequested[globalIndex] == 0)
		{
			reverseRequested[globalIndex] = 1;
			deferredIndexes.push_back(globalIndex);
			deferredAttempts.push_back(attempts[globalIndex]);
			deferredForward.push_back(forwardScores[globalIndex]);
		}
	}
	if (!deferredIndexes.empty())
	{
		result->round_active_groups.push_back(0);
		result->round_forward_attempts.push_back(0);
		result->round_reverse_requests.push_back(
			static_cast<uint64_t>(deferredIndexes.size()));
		result->reverse_requests += static_cast<uint64_t>(deferredIndexes.size());
		FasimGasal2StreamedAttemptScoreTelemetry reverseTelemetry;
		std::vector<FasimGasal2StreamedAttemptScore> reverseScores;
		std::string stageError;
		if (!fasim_gasal2_streamed_attempt_reverse_score_v1(
				strA, deferredAttempts, deferredForward, &reverseScores,
				&reverseTelemetry, &stageError))
		{
			return fail(stageError.empty() ? "f1_deferred_reverse_failed" : stageError);
		}
		addTelemetry(reverseTelemetry, true);
		result->reverse_scored_attempts +=
			static_cast<uint64_t>(deferredIndexes.size());
		for (size_t i = 0; i < deferredIndexes.size(); ++i)
		{
			const size_t globalIndex = deferredIndexes[i];
			canonicalScores[globalIndex] = reverseScores[i];
			canonicalKnown[globalIndex] = 1;
			F1GroupState &group = groups[
				static_cast<size_t>(attempts[globalIndex].scoreinfo_index)];
			group.active = false;
			group.emitted = true;
			if (reverseScores[i].score != 0)
			{
				group.haveSelected = true;
				group.selectedIndex = globalIndex;
				group.reason = "last";
			}
			else
			{
				group.reason = "empty";
			}
		}
	}

	std::vector<size_t> selected;
	for (size_t groupIndex = 0; groupIndex < groups.size(); ++groupIndex)
	{
		F1GroupState &group = groups[groupIndex];
		if (group.haveSelected)
		{
			selected.push_back(group.selectedIndex);
			if (group.reason == "threshold") ++result->threshold_groups;
			else if (group.reason == "best_fallback") ++result->best_fallback_groups;
			else if (group.reason == "last") ++result->last_groups;
		}
		else
		{
			++result->empty_groups;
		}
	}
	result->selected_attempts = static_cast<uint64_t>(selected.size());

	std::vector<triplex> convertedRows;
	for (size_t selectedPosition = 0; selectedPosition < selected.size();
		 ++selectedPosition)
	{
		const size_t index = selected[selectedPosition];
		if (index >= attempts.size() || index >= forwardScores.size() ||
			index >= canonicalScores.size() || !canonicalKnown[index])
			return fail("f1_selected_endpoint_missing");
		const FasimGasal2Attempt &attempt = attempts[index];
		const FasimGasal2StreamedAttemptScore &forward = forwardScores[index];
		const FasimGasal2StreamedAttemptScore &canonical = canonicalScores[index];
		const std::string small = strB.substr(
			static_cast<size_t>(attempt.start),
			static_cast<size_t>(attempt.cutlength));
		StripedSmithWaterman::Alignment local;
		bool continuationOk = false;
		const std::chrono::steady_clock::time_point continuationStart =
			std::chrono::steady_clock::now();
#if defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) || \
	defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
		StripedSmithWaterman::ForwardEndpoint endpoint;
		endpoint.score1 = forward.forward_score;
		endpoint.score2 = 0;
		endpoint.ref_end1 = forward.ref_end_local;
		endpoint.query_end1 = forward.query_end;
		endpoint.ref_end2 = -1;
		endpoint.numeric_path = forward.numeric_path;
		continuationOk = aligner.AlignFromForward(
			strA.c_str(), small.c_str(), static_cast<int>(small.size()),
			filter, endpoint, &local, maskLen);
#else
		aligner.Align(strA.c_str(), small.c_str(), small.size(), filter,
		              &local, maskLen);
		continuationOk = true;
#endif
		result->traceback_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - continuationStart).count();
		++result->cpu_continuation_calls;
		if (!continuationOk || local.sw_score != canonical.score ||
			local.ref_end != forward.ref_end_local ||
			local.query_end != forward.query_end)
		{
			++result->cpu_continuation_failures;
			std::ostringstream detail;
			detail << "f1_continuation_contract_mismatch:attempt=" << index
			       << ":expected=" << canonical.score << ','
			       << forward.ref_end_local << ',' << forward.query_end
			       << ":observed=" << local.sw_score
			       << ',' << local.ref_end << ',' << local.query_end;
			return fail(detail.str());
		}
		StripedSmithWaterman::Alignment global = local;
		global.ref_begin += attempt.start;
		global.ref_end += attempt.start;
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(global, convertedRows, strA, strB, strSrc, nt_table,
		                 dnaStartPos, rule, strand, Para, penaltyT, penaltyC,
		                 ntMin, ntMax, materializeAlignmentStrings);
		result->convert_seconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - convertStart).count();
	}

	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple);
		convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
		                                sameMyTriplex), convertedRows.end());
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple2);
		convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
		                                sameMyTriplex), convertedRows.end());
		std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexSingle);
	}
	const size_t topLimit = std::min(convertedRows.size(), static_cast<size_t>(N));
	for (size_t i = 0; i < topLimit; ++i)
	{
		const triplex &row = convertedRows[i];
		if (row.identity >= paraList.minIdentity &&
			row.tri_score >= paraList.minStability && row.nt >= ntMin)
			shadowTriplexList.push_back(row);
	}
	result->ok = result->cpu_continuation_failures == 0;
	result->total_seconds = std::chrono::duration<double>(
		std::chrono::steady_clock::now() - totalStart).count();
	return result->ok;
}

inline bool fasim_long_query_gpu_consumer_f1_batch_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &query,
	const std::vector<FasimLongQueryGpuConsumerF1TaskInput> &taskInputs,
	std::vector<std::vector<struct triplex> > &taskTriplexLists,
	std::vector<FasimLongQueryGpuConsumerF1Result> &taskResults,
	long ntMin,
	long ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	std::string *errorOut)
{
	taskTriplexLists.assign(taskInputs.size(), std::vector<struct triplex>());
	taskResults.assign(taskInputs.size(), FasimLongQueryGpuConsumerF1Result());
	if (errorOut != NULL) errorOut->clear();
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();
	const bool hostProfileActive =
		fasim_long_query_gpu_consumer_f1_host_profile_runtime();
	auto hostElapsed = [&](const std::chrono::steady_clock::time_point &start)
		-> double
	{
		return hostProfileActive ? std::chrono::duration<double>(
			std::chrono::steady_clock::now() - start).count() : 0.0;
	};
	double hostValidationSeconds = 0.0;
	double hostAttemptBuildSeconds = 0.0;
	double hostScoreBufferAllocSeconds = 0.0;
	double hostRoundDescriptorSeconds = 0.0;
	double hostForwardStageSeconds = 0.0;
	double hostForwardApplySeconds = 0.0;
	double hostReverseCompactSeconds = 0.0;
	double hostReverseStageSeconds = 0.0;
	double hostReverseApplySeconds = 0.0;
	double hostRoundRetireSeconds = 0.0;
	double hostDeferredCompactSeconds = 0.0;
	double hostDeferredStageSeconds = 0.0;
	double hostDeferredApplySeconds = 0.0;
	double hostSelectionSeconds = 0.0;
	double hostAccountingSeconds = 0.0;
	double hostContinuationOuterSeconds = 0.0;

	auto fail = [&](const std::string &message) -> bool
	{
		if (errorOut != NULL) *errorOut = message;
		for (size_t i = 0; i < taskResults.size(); ++i)
		{
			taskResults[i].ok = false;
			taskResults[i].error = message;
			taskResults[i].total_seconds = std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count();
		}
		return false;
	};

	if (!fasim_long_query_gpu_consumer_f1_scheduler_runtime())
		return fail("f1_scheduler_not_requested");
	if (!fasim_long_query_gpu_consumer_cpu_continuation_runtime())
		return fail("f1_requires_cpu_continuation_flag");
#if !defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) && \
	!defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
	return fail("f1_cpu_continuation_not_built");
#endif
	if (query.empty()) return fail("f1_empty_query");
	if (taskInputs.empty()) return true;
	hostValidationSeconds = hostElapsed(totalStart);
	std::chrono::steady_clock::time_point hostAttemptBuildStart;
	if (hostProfileActive) hostAttemptBuildStart = std::chrono::steady_clock::now();

	struct BatchGroupState
	{
		BatchGroupState() :
			active(true), emitted(false), haveBest(false), bestScore(0),
			bestIndex(0), haveLast(false), lastIndex(0), selectedIndex(0),
			haveSelected(false), reason("empty")
		{
		}
		std::vector<size_t> indexes;
		bool active;
		bool emitted;
		bool haveBest;
		int bestScore;
		size_t bestIndex;
		bool haveLast;
		size_t lastIndex;
		size_t selectedIndex;
		bool haveSelected;
		std::string reason;
	};

	std::vector<std::vector<BatchGroupState> > groups(taskInputs.size());
	std::vector<FasimGasal2Attempt> attempts;
	std::vector<size_t> attemptTasks;
	const size_t reserveGroups = taskInputs.size() * 16;
	attempts.reserve(reserveGroups);
	attemptTasks.reserve(reserveGroups);

	for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
	{
		const FasimLongQueryGpuConsumerF1TaskInput &input = taskInputs[taskIndex];
		if (input.target == NULL || input.source == NULL || input.scoreInfo == NULL)
			return fail("f1_missing_task_input");
		const std::vector<struct StripedSmithWaterman::scoreInfo> &scoreInfos =
			*input.scoreInfo;
		groups[taskIndex].resize(scoreInfos.size());
		taskResults[taskIndex].scoreinfo_groups =
			static_cast<uint64_t>(scoreInfos.size());
		if (scoreInfos.empty())
		{
			taskResults[taskIndex].ok = true;
			continue;
		}
		float identity = 0.6f;
		int identityRound = 0;
		while (identity <= 1.0f)
		{
			for (size_t groupIndex = 0; groupIndex < scoreInfos.size(); ++groupIndex)
			{
				const struct StripedSmithWaterman::scoreInfo &info =
					scoreInfos[groupIndex];
				int cutlength = static_cast<int>(info.score + 24) /
					(9 * identity - 4) + 1;
				cutlength = info.position - cutlength + 1 > 0 ?
					cutlength : info.position + 1;
				const int start = info.position - cutlength + 1;
				if (start < 0 || cutlength <= 0 ||
					start + cutlength > static_cast<int>(input.target->size()))
					continue;
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(groupIndex);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = info.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = static_cast<int>(ntMin);
				attempt.identity_round = identityRound;
				attempt.set_target_view(input.target,
					static_cast<size_t>(start), static_cast<size_t>(cutlength));
				groups[taskIndex][groupIndex].indexes.push_back(attempts.size());
				attempts.push_back(attempt);
				attemptTasks.push_back(taskIndex);
			}
			identity += 0.1f;
			++identityRound;
		}
		for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
		{
			if (groups[taskIndex][groupIndex].indexes.empty())
				return fail("f1_empty_scoreinfo_group");
		}
		taskResults[taskIndex].attempts = static_cast<uint64_t>(
			std::accumulate(groups[taskIndex].begin(), groups[taskIndex].end(),
				static_cast<size_t>(0),
				[](size_t total, const BatchGroupState &group)
				{
					return total + group.indexes.size();
				}));
	}
	// Empty scoreInfo tasks have no attempt rows; non-empty tasks were counted
	// above.  Keep this assignment explicit so the report cannot drift if the
	// attempt-generation loop changes its round count.
	for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
	{
		if (!taskInputs[taskIndex].scoreInfo->empty() &&
			taskResults[taskIndex].attempts == 0)
			return fail("f1_attempt_generation_empty");
	}
	hostAttemptBuildSeconds = hostElapsed(hostAttemptBuildStart);
	std::chrono::steady_clock::time_point hostScoreBufferAllocStart;
	if (hostProfileActive)
		hostScoreBufferAllocStart = std::chrono::steady_clock::now();

	std::vector<FasimGasal2StreamedAttemptScore> forwardScores(attempts.size());
	std::vector<FasimGasal2StreamedAttemptScore> canonicalScores(attempts.size());
	std::vector<unsigned char> canonicalKnown(attempts.size(), 0);
	std::vector<unsigned char> reverseRequested(attempts.size(), 0);

	auto distributeTelemetry = [&](const FasimGasal2StreamedAttemptScoreTelemetry &telemetry,
									bool reverse,
									const std::vector<uint64_t> &taskCounts)
	{
		uint64_t totalCount = 0;
			for (size_t i = 0; i < taskCounts.size(); ++i) totalCount += taskCounts[i];
			if (totalCount == 0) return;
			for (size_t i = 0; i < taskCounts.size(); ++i)
			{
				const double fraction = static_cast<double>(taskCounts[i]) /
					static_cast<double>(totalCount);
				if (reverse) taskResults[i].reverse_seconds +=
					telemetry.total_seconds * fraction;
				else taskResults[i].forward_seconds +=
					telemetry.total_seconds * fraction;
				taskResults[i].gpu_kernel_seconds += telemetry.gpu_seconds * fraction;
				taskResults[i].h2d_seconds += telemetry.h2d_seconds * fraction;
				taskResults[i].d2h_seconds += telemetry.d2h_seconds * fraction;
			}
	};

	size_t maxRounds = 0;
	for (size_t taskIndex = 0; taskIndex < groups.size(); ++taskIndex)
		for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
			maxRounds = std::max(maxRounds, groups[taskIndex][groupIndex].indexes.size());
	hostScoreBufferAllocSeconds = hostElapsed(hostScoreBufferAllocStart);

	for (size_t round = 0; round < maxRounds; ++round)
	{
		std::chrono::steady_clock::time_point hostRoundDescriptorStart;
		if (hostProfileActive)
			hostRoundDescriptorStart = std::chrono::steady_clock::now();
		std::vector<size_t> roundIndexes;
		std::vector<FasimGasal2Attempt> roundAttempts;
		std::vector<uint64_t> taskRoundCounts(taskInputs.size(), 0);
		for (size_t taskIndex = 0; taskIndex < groups.size(); ++taskIndex)
		{
			uint64_t activeGroups = 0;
			for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
			{
				BatchGroupState &group = groups[taskIndex][groupIndex];
				if (!group.active || round >= group.indexes.size()) continue;
				++activeGroups;
				taskRoundCounts[taskIndex]++;
				roundIndexes.push_back(group.indexes[round]);
				roundAttempts.push_back(attempts[group.indexes[round]]);
			}
			taskResults[taskIndex].round_active_groups.push_back(activeGroups);
			taskResults[taskIndex].round_forward_attempts.push_back(activeGroups);
			taskResults[taskIndex].round_reverse_requests.push_back(0);
		}
		hostRoundDescriptorSeconds += hostElapsed(hostRoundDescriptorStart);
		if (roundAttempts.empty()) continue;

		FasimGasal2StreamedAttemptScoreTelemetry forwardTelemetry;
		std::vector<FasimGasal2StreamedAttemptScore> roundForward;
		std::string stageError;
		std::chrono::steady_clock::time_point hostForwardStageStart;
		if (hostProfileActive)
			hostForwardStageStart = std::chrono::steady_clock::now();
		if (!fasim_gasal2_streamed_attempt_forward_score_v1(
				query, roundAttempts, &roundForward, &forwardTelemetry, &stageError))
			return fail(stageError.empty() ? "f1_global_forward_stage_failed" : stageError);
		hostForwardStageSeconds += hostElapsed(hostForwardStageStart);
		std::chrono::steady_clock::time_point hostForwardApplyStart;
		if (hostProfileActive)
			hostForwardApplyStart = std::chrono::steady_clock::now();
		distributeTelemetry(forwardTelemetry, false, taskRoundCounts);
		for (size_t i = 0; i < roundIndexes.size(); ++i)
		{
			const size_t globalIndex = roundIndexes[i];
			forwardScores[globalIndex] = roundForward[i];
			++taskResults[attemptTasks[globalIndex]].forward_attempts;
		}
		hostForwardApplySeconds += hostElapsed(hostForwardApplyStart);

		std::chrono::steady_clock::time_point hostReverseCompactStart;
		if (hostProfileActive)
			hostReverseCompactStart = std::chrono::steady_clock::now();
		std::vector<size_t> reverseIndexes;
		std::vector<FasimGasal2Attempt> reverseAttempts;
		std::vector<FasimGasal2StreamedAttemptScore> reverseForward;
		std::vector<uint64_t> taskReverseCounts(taskInputs.size(), 0);
		for (size_t i = 0; i < roundIndexes.size(); ++i)
		{
			const size_t globalIndex = roundIndexes[i];
			const FasimGasal2Attempt &attempt = attempts[globalIndex];
			const FasimGasal2StreamedAttemptScore &score = roundForward[i];
			const size_t taskIndex = attemptTasks[globalIndex];
			BatchGroupState &group = groups[taskIndex][
				static_cast<size_t>(attempt.scoreinfo_index)];
			group.haveLast = true;
			group.lastIndex = globalIndex;
			const bool terminal = score.ref_end_local == attempt.cutlength - 1;
			const bool needsThresholdCheck = score.forward_score >= attempt.prealign_score;
			const bool needsBestCheck = terminal && score.forward_score > group.bestScore;
			if ((needsThresholdCheck || needsBestCheck) &&
				reverseRequested[globalIndex] == 0)
			{
				reverseRequested[globalIndex] = 1;
				reverseIndexes.push_back(globalIndex);
				reverseAttempts.push_back(attempt);
				reverseForward.push_back(score);
				++taskReverseCounts[taskIndex];
			}
		}
		for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
			taskResults[taskIndex].round_reverse_requests.back() = taskReverseCounts[taskIndex];
		for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
			taskResults[taskIndex].reverse_requests += taskReverseCounts[taskIndex];
		hostReverseCompactSeconds += hostElapsed(hostReverseCompactStart);
		if (!reverseIndexes.empty())
		{
			FasimGasal2StreamedAttemptScoreTelemetry reverseTelemetry;
			std::vector<FasimGasal2StreamedAttemptScore> reverseScores;
			std::chrono::steady_clock::time_point hostReverseStageStart;
			if (hostProfileActive)
				hostReverseStageStart = std::chrono::steady_clock::now();
			if (!fasim_gasal2_streamed_attempt_reverse_score_v1(
					query, reverseAttempts, reverseForward, &reverseScores,
					&reverseTelemetry, &stageError))
				return fail(stageError.empty() ? "f1_global_reverse_stage_failed" : stageError);
			hostReverseStageSeconds += hostElapsed(hostReverseStageStart);
			std::chrono::steady_clock::time_point hostReverseApplyStart;
			if (hostProfileActive)
				hostReverseApplyStart = std::chrono::steady_clock::now();
			distributeTelemetry(reverseTelemetry, true, taskReverseCounts);
			for (size_t i = 0; i < reverseIndexes.size(); ++i)
			{
				const size_t globalIndex = reverseIndexes[i];
				const size_t taskIndex = attemptTasks[globalIndex];
				const FasimGasal2Attempt &attempt = attempts[globalIndex];
				const int canonical = reverseScores[i].score;
				canonicalScores[globalIndex] = reverseScores[i];
				canonicalKnown[globalIndex] = 1;
				++taskResults[taskIndex].reverse_scored_attempts;
				BatchGroupState &group = groups[taskIndex][
					static_cast<size_t>(attempt.scoreinfo_index)];
				if (!group.emitted && canonical >= attempt.prealign_score)
				{
					group.emitted = true;
					group.active = false;
					group.haveSelected = true;
					group.selectedIndex = globalIndex;
					group.reason = "threshold";
				}
				else if (!group.emitted && canonical > group.bestScore &&
					reverseScores[i].ref_end_local == attempt.cutlength - 1)
				{
					group.bestScore = canonical;
					group.bestIndex = globalIndex;
					group.haveBest = true;
				}
			}
			hostReverseApplySeconds += hostElapsed(hostReverseApplyStart);
		}

		std::chrono::steady_clock::time_point hostRoundRetireStart;
		if (hostProfileActive)
			hostRoundRetireStart = std::chrono::steady_clock::now();
		for (size_t taskIndex = 0; taskIndex < groups.size(); ++taskIndex)
		{
			for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
			{
				BatchGroupState &group = groups[taskIndex][groupIndex];
				if (!group.active || round + 1 < group.indexes.size()) continue;
				if (group.haveBest)
				{
					group.active = false;
					group.emitted = true;
					group.haveSelected = true;
					group.selectedIndex = group.bestIndex;
					group.reason = "best_fallback";
				}
				else if (group.haveLast && canonicalKnown[group.lastIndex])
				{
					group.active = false;
					group.emitted = true;
					if (canonicalScores[group.lastIndex].score != 0)
					{
						group.haveSelected = true;
						group.selectedIndex = group.lastIndex;
						group.reason = "last";
					}
					else group.reason = "empty";
				}
			}
		}
		hostRoundRetireSeconds += hostElapsed(hostRoundRetireStart);
	}

	std::chrono::steady_clock::time_point hostDeferredCompactStart;
	if (hostProfileActive)
		hostDeferredCompactStart = std::chrono::steady_clock::now();
	std::vector<size_t> deferredIndexes;
	std::vector<FasimGasal2Attempt> deferredAttempts;
	std::vector<FasimGasal2StreamedAttemptScore> deferredForward;
	std::vector<uint64_t> deferredTaskCounts(taskInputs.size(), 0);
	for (size_t taskIndex = 0; taskIndex < groups.size(); ++taskIndex)
	{
		for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
		{
			BatchGroupState &group = groups[taskIndex][groupIndex];
			if (!group.active || !group.haveLast || canonicalKnown[group.lastIndex]) continue;
			const size_t globalIndex = group.lastIndex;
			if (reverseRequested[globalIndex] == 0)
			{
				reverseRequested[globalIndex] = 1;
				deferredIndexes.push_back(globalIndex);
				deferredAttempts.push_back(attempts[globalIndex]);
				deferredForward.push_back(forwardScores[globalIndex]);
				++deferredTaskCounts[taskIndex];
			}
		}
	}
	hostDeferredCompactSeconds = hostElapsed(hostDeferredCompactStart);
	if (!deferredIndexes.empty())
	{
		for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
		{
			// Keep the deferred stage visible for every task, including tasks
			// that contribute no last fallback. This makes the per-task report
			// a rectangular view of the same global barrier.
			taskResults[taskIndex].round_active_groups.push_back(0);
			taskResults[taskIndex].round_forward_attempts.push_back(0);
			taskResults[taskIndex].round_reverse_requests.push_back(
				deferredTaskCounts[taskIndex]);
			if (deferredTaskCounts[taskIndex] != 0)
				taskResults[taskIndex].reverse_requests += deferredTaskCounts[taskIndex];
		}
		FasimGasal2StreamedAttemptScoreTelemetry reverseTelemetry;
		std::vector<FasimGasal2StreamedAttemptScore> reverseScores;
		std::string stageError;
		std::chrono::steady_clock::time_point hostDeferredStageStart;
		if (hostProfileActive)
			hostDeferredStageStart = std::chrono::steady_clock::now();
		if (!fasim_gasal2_streamed_attempt_reverse_score_v1(
				query, deferredAttempts, deferredForward, &reverseScores,
				&reverseTelemetry, &stageError))
			return fail(stageError.empty() ? "f1_global_deferred_reverse_failed" : stageError);
		hostDeferredStageSeconds = hostElapsed(hostDeferredStageStart);
		std::chrono::steady_clock::time_point hostDeferredApplyStart;
		if (hostProfileActive)
			hostDeferredApplyStart = std::chrono::steady_clock::now();
		distributeTelemetry(reverseTelemetry, true, deferredTaskCounts);
		for (size_t i = 0; i < deferredIndexes.size(); ++i)
		{
			const size_t globalIndex = deferredIndexes[i];
			const size_t taskIndex = attemptTasks[globalIndex];
			canonicalScores[globalIndex] = reverseScores[i];
			canonicalKnown[globalIndex] = 1;
			++taskResults[taskIndex].reverse_scored_attempts;
			BatchGroupState &group = groups[taskIndex][
				static_cast<size_t>(attempts[globalIndex].scoreinfo_index)];
			group.active = false;
			group.emitted = true;
			if (reverseScores[i].score != 0)
			{
				group.haveSelected = true;
				group.selectedIndex = globalIndex;
				group.reason = "last";
			}
			else group.reason = "empty";
		}
		hostDeferredApplySeconds = hostElapsed(hostDeferredApplyStart);
	}

	std::chrono::steady_clock::time_point hostSelectionStart;
	if (hostProfileActive) hostSelectionStart = std::chrono::steady_clock::now();
	std::vector<std::vector<size_t> > selected(taskInputs.size());
	const int8_t nt_table[128] = {
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
		4,0,4,1,4,4,4,2,4,4,4,4,4,4,4,4,
		4,4,4,4,3,0,4,4,4,4,4,4,4,4,4,4,
		4,0,4,1,4,4,4,2,4,4,4,4,4,4,4,4,
		4,4,4,4,3,0,4,4,4,4,4,4,4,4,4,4
	};
	for (size_t taskIndex = 0; taskIndex < groups.size(); ++taskIndex)
	{
		for (size_t groupIndex = 0; groupIndex < groups[taskIndex].size(); ++groupIndex)
		{
			BatchGroupState &group = groups[taskIndex][groupIndex];
			if (group.haveSelected)
			{
				selected[taskIndex].push_back(group.selectedIndex);
				if (group.reason == "threshold") ++taskResults[taskIndex].threshold_groups;
				else if (group.reason == "best_fallback") ++taskResults[taskIndex].best_fallback_groups;
				else if (group.reason == "last") ++taskResults[taskIndex].last_groups;
			}
			else if (!taskInputs[taskIndex].scoreInfo->empty())
				++taskResults[taskIndex].empty_groups;
		}
		taskResults[taskIndex].selected_attempts =
			static_cast<uint64_t>(selected[taskIndex].size());
	}
	hostSelectionSeconds = hostElapsed(hostSelectionStart);

	// The F1 report is also a runtime contract. Reject accounting drift before
	// materializing output, rather than allowing a partial result to be
	// mistaken for an exact scheduler run.
	std::chrono::steady_clock::time_point hostAccountingStart;
	if (hostProfileActive) hostAccountingStart = std::chrono::steady_clock::now();
	for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
	{
		const FasimLongQueryGpuConsumerF1Result &taskResult =
			taskResults[taskIndex];
		const bool emptyScoreInfo = taskInputs[taskIndex].scoreInfo->empty();
		const uint64_t reasonGroups = taskResult.threshold_groups +
			taskResult.best_fallback_groups + taskResult.last_groups +
			taskResult.empty_groups;
		uint64_t roundForwardTotal = 0;
		uint64_t roundReverseTotal = 0;
		const bool rectangularRounds =
			taskResult.round_active_groups.size() ==
				taskResult.round_forward_attempts.size() &&
			taskResult.round_active_groups.size() ==
				taskResult.round_reverse_requests.size();
		if (rectangularRounds)
		{
			for (size_t round = 0;
			     round < taskResult.round_active_groups.size(); ++round)
			{
				roundForwardTotal += taskResult.round_forward_attempts[round];
				roundReverseTotal += taskResult.round_reverse_requests[round];
			}
		}
		const bool accountingOk =
			(emptyScoreInfo ?
				(taskResult.attempts == 0 && taskResult.forward_attempts == 0 &&
				 taskResult.reverse_requests == 0 &&
				 taskResult.reverse_scored_attempts == 0 &&
				 taskResult.selected_attempts == 0 &&
				 taskResult.cpu_continuation_calls == 0 &&
				 taskResult.threshold_groups == 0 &&
				 taskResult.best_fallback_groups == 0 &&
				 taskResult.last_groups == 0 && taskResult.empty_groups == 0) :
				(taskResult.attempts > 0 && taskResult.forward_attempts > 0 &&
				 taskResult.forward_attempts <= taskResult.attempts &&
				 taskResult.reverse_requests <= taskResult.forward_attempts &&
				 taskResult.reverse_scored_attempts == taskResult.reverse_requests &&
				 taskResult.selected_attempts <= taskResult.scoreinfo_groups &&
				 reasonGroups == taskResult.scoreinfo_groups &&
				 taskResult.selected_attempts + taskResult.empty_groups ==
					taskResult.scoreinfo_groups)) &&
			rectangularRounds &&
			roundForwardTotal == taskResult.forward_attempts &&
			roundReverseTotal == taskResult.reverse_requests;
		if (!accountingOk)
			return fail("f1_global_accounting_contract_mismatch");
	}
	hostAccountingSeconds = hostElapsed(hostAccountingStart);

	std::chrono::steady_clock::time_point hostContinuationOuterStart;
	if (hostProfileActive)
		hostContinuationOuterStart = std::chrono::steady_clock::now();
	const bool continuationProfileActive =
		fasim_long_query_gpu_consumer_f1_continuation_profile_runtime();
	FasimLongQueryGpuConsumerF1ContinuationProfileScope continuationProfileScope(
		continuationProfileActive);
	const bool continuationProfileReuseRequested =
		fasim_long_query_gpu_consumer_f1_profile_reuse_runtime();
	bool continuationProfileReuseActive = false;
	double continuationProfilePrepareSeconds = 0.0;
#if defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) || \
	defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
	StripedSmithWaterman::ForwardContinuationQuery preparedContinuationQuery;
	if (continuationProfileReuseRequested)
	{
		const std::chrono::steady_clock::time_point prepareStart =
			std::chrono::steady_clock::now();
		continuationProfileReuseActive = aligner.PrepareForwardContinuationQuery(
			query.c_str(), &preparedContinuationQuery);
		continuationProfilePrepareSeconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - prepareStart).count();
		if (!continuationProfileReuseActive)
			return fail("f1_global_continuation_profile_prepare_failed");
	}
#else
	if (continuationProfileReuseRequested)
		return fail("f1_global_continuation_profile_reuse_not_built");
#endif
	for (size_t taskIndex = 0; taskIndex < taskInputs.size(); ++taskIndex)
	{
		const FasimLongQueryGpuConsumerF1TaskInput &input = taskInputs[taskIndex];
		std::vector<triplex> &convertedRows = taskTriplexLists[taskIndex];
		taskResults[taskIndex].continuation_profile_reuse_requested =
			continuationProfileReuseRequested;
		taskResults[taskIndex].continuation_profile_reuse_active =
			continuationProfileReuseActive;
		if (taskIndex == 0)
			taskResults[taskIndex].continuation_profile_prepare_seconds =
				continuationProfilePrepareSeconds;
		StripedSmithWaterman::ForwardContinuationProfileStats profileBefore;
		ssw_align_internal_stats internalBefore = {};
		if (continuationProfileActive)
		{
			profileBefore =
				StripedSmithWaterman::ForwardContinuationProfileSnapshot();
			internalBefore = ssw_align_internal_stats_snapshot();
		}
		const std::chrono::steady_clock::time_point taskStart =
			std::chrono::steady_clock::now();
		for (size_t position = 0; position < selected[taskIndex].size(); ++position)
		{
			const size_t globalIndex = selected[taskIndex][position];
			if (globalIndex >= attempts.size() || attemptTasks[globalIndex] != taskIndex ||
				!canonicalKnown[globalIndex])
				return fail("f1_global_selected_endpoint_missing");
			const FasimGasal2Attempt &attempt = attempts[globalIndex];
			const FasimGasal2StreamedAttemptScore &forward = forwardScores[globalIndex];
			const FasimGasal2StreamedAttemptScore &canonical = canonicalScores[globalIndex];
			std::chrono::steady_clock::time_point substringStart;
			if (continuationProfileActive)
				substringStart = std::chrono::steady_clock::now();
			const std::string small = input.target->substr(
				static_cast<size_t>(attempt.start), static_cast<size_t>(attempt.cutlength));
			if (continuationProfileActive)
				taskResults[taskIndex].continuation_substring_seconds +=
					std::chrono::duration<double>(
						std::chrono::steady_clock::now() - substringStart).count();
			StripedSmithWaterman::Alignment local;
			const std::chrono::steady_clock::time_point continuationStart =
				std::chrono::steady_clock::now();
			bool continuationOk = false;
#if defined(FASIM_WITH_SSW_FORWARD_CONTINUATION) || \
	defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID)
			StripedSmithWaterman::ForwardEndpoint endpoint;
			endpoint.score1 = forward.forward_score;
			endpoint.score2 = 0;
			endpoint.ref_end1 = forward.ref_end_local;
			endpoint.query_end1 = forward.query_end;
			endpoint.ref_end2 = -1;
			endpoint.numeric_path = forward.numeric_path;
			if (continuationProfileReuseActive)
				continuationOk = aligner.AlignFromForward(
					preparedContinuationQuery, small.c_str(),
					static_cast<int>(small.size()), filter, endpoint, &local,
					maskLen);
			else
				continuationOk = aligner.AlignFromForward(
					query.c_str(), small.c_str(), static_cast<int>(small.size()),
					filter, endpoint, &local, maskLen);
#else
			aligner.Align(query.c_str(), small.c_str(), small.size(), filter, &local, maskLen);
			continuationOk = true;
#endif
			taskResults[taskIndex].traceback_seconds += std::chrono::duration<double>(
				std::chrono::steady_clock::now() - continuationStart).count();
			++taskResults[taskIndex].cpu_continuation_calls;
			if (!continuationOk || local.sw_score != canonical.score ||
				local.ref_end != forward.ref_end_local || local.query_end != forward.query_end)
			{
				++taskResults[taskIndex].cpu_continuation_failures;
				std::ostringstream detail;
				detail << "f1_global_continuation_contract_mismatch:task=" << taskIndex
				       << ":attempt=" << globalIndex;
				return fail(detail.str());
			}
			StripedSmithWaterman::Alignment global = local;
			global.ref_begin += attempt.start;
			global.ref_end += attempt.start;
			const std::chrono::steady_clock::time_point convertStart =
				std::chrono::steady_clock::now();
			convertMyTriplex(global, convertedRows, query, *input.target, *input.source,
				nt_table, input.dnaStartPos, input.rule, input.strand, input.Para,
				penaltyT, penaltyC, static_cast<int>(ntMin), static_cast<int>(ntMax),
				materializeAlignmentStrings);
			taskResults[taskIndex].convert_seconds += std::chrono::duration<double>(
				std::chrono::steady_clock::now() - convertStart).count();
		}
		{
			FasimAuthorityProfileScope authoritySortScope(
				FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
			std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple);
			convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
									sameMyTriplex), convertedRows.end());
			std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexMultiple2);
			convertedRows.erase(std::unique(convertedRows.begin(), convertedRows.end(),
									sameMyTriplex), convertedRows.end());
			std::sort(convertedRows.begin(), convertedRows.end(), compMyTriplexSingle);
		}
		const size_t topLimit = std::min(convertedRows.size(), static_cast<size_t>(N));
		std::vector<triplex> filtered;
		for (size_t i = 0; i < topLimit; ++i)
		{
			const triplex &row = convertedRows[i];
			if (row.identity >= paraList.minIdentity &&
				row.tri_score >= paraList.minStability && row.nt >= ntMin)
				filtered.push_back(row);
		}
		convertedRows.swap(filtered);
		if (continuationProfileActive)
		{
			const StripedSmithWaterman::ForwardContinuationProfileStats profileAfter =
				StripedSmithWaterman::ForwardContinuationProfileSnapshot();
			const ssw_align_internal_stats internalAfter =
				ssw_align_internal_stats_snapshot();
			auto delta = [](uint64_t after, uint64_t before) -> uint64_t
			{
				return after >= before ? after - before : 0;
			};
			const double secondsPerNanosecond = 1.0e-9;
			FasimLongQueryGpuConsumerF1Result &profileResult = taskResults[taskIndex];
			profileResult.continuation_profile_active = true;
			profileResult.continuation_profile_calls =
				delta(profileAfter.calls, profileBefore.calls);
			profileResult.continuation_query_bytes =
				delta(profileAfter.query_bytes, profileBefore.query_bytes);
			profileResult.continuation_ref_bytes =
				delta(profileAfter.ref_bytes, profileBefore.ref_bytes);
			profileResult.continuation_profile_cache_calls =
				delta(profileAfter.profile_cache_calls, profileBefore.profile_cache_calls);
			profileResult.continuation_profile_cache_hits =
				delta(profileAfter.profile_cache_hits, profileBefore.profile_cache_hits);
			profileResult.continuation_profile_cache_misses =
				delta(profileAfter.profile_cache_misses, profileBefore.profile_cache_misses);
			profileResult.continuation_reverse_calls =
				delta(internalAfter.reverse_calls, internalBefore.reverse_calls);
			profileResult.continuation_banded_sw_calls =
				delta(internalAfter.banded_sw_calls, internalBefore.banded_sw_calls);
			profileResult.continuation_query_strlen_seconds = secondsPerNanosecond *
				delta(profileAfter.query_strlen_nanoseconds,
					profileBefore.query_strlen_nanoseconds);
			profileResult.continuation_query_alloc_seconds = secondsPerNanosecond *
				delta(profileAfter.query_alloc_nanoseconds,
					profileBefore.query_alloc_nanoseconds);
			profileResult.continuation_query_translate_seconds = secondsPerNanosecond *
				delta(profileAfter.query_translate_nanoseconds,
					profileBefore.query_translate_nanoseconds);
			profileResult.continuation_ref_alloc_seconds = secondsPerNanosecond *
				delta(profileAfter.ref_alloc_nanoseconds,
					profileBefore.ref_alloc_nanoseconds);
			profileResult.continuation_ref_translate_seconds = secondsPerNanosecond *
				delta(profileAfter.ref_translate_nanoseconds,
					profileBefore.ref_translate_nanoseconds);
			profileResult.continuation_profile_lookup_seconds = secondsPerNanosecond *
				delta(profileAfter.profile_lookup_nanoseconds,
					profileBefore.profile_lookup_nanoseconds);
			profileResult.continuation_profile_build_seconds = secondsPerNanosecond *
				delta(profileAfter.profile_build_nanoseconds,
					profileBefore.profile_build_nanoseconds);
			profileResult.continuation_ssw_seconds = secondsPerNanosecond *
				delta(profileAfter.ssw_nanoseconds, profileBefore.ssw_nanoseconds);
			profileResult.continuation_reverse_start_seconds = secondsPerNanosecond *
				delta(internalAfter.reverse_start_nanoseconds,
					internalBefore.reverse_start_nanoseconds);
			profileResult.continuation_banded_sw_seconds = secondsPerNanosecond *
				delta(internalAfter.banded_sw_nanoseconds,
					internalBefore.banded_sw_nanoseconds);
			profileResult.continuation_cigar_seconds = secondsPerNanosecond *
				delta(internalAfter.cigar_nanoseconds,
					internalBefore.cigar_nanoseconds);
			profileResult.continuation_alignment_convert_seconds = secondsPerNanosecond *
				delta(profileAfter.alignment_convert_nanoseconds,
					profileBefore.alignment_convert_nanoseconds);
			profileResult.continuation_cleanup_seconds = secondsPerNanosecond *
				delta(profileAfter.cleanup_nanoseconds,
					profileBefore.cleanup_nanoseconds);
			if (profileResult.continuation_profile_calls !=
				profileResult.cpu_continuation_calls)
				return fail("f1_global_continuation_profile_accounting_mismatch");
		}
		taskResults[taskIndex].ok = taskResults[taskIndex].cpu_continuation_failures == 0;
		if (taskResults[taskIndex].cpu_continuation_calls !=
			taskResults[taskIndex].selected_attempts)
			return fail("f1_global_continuation_accounting_mismatch");
		taskResults[taskIndex].total_seconds =
			std::chrono::duration<double>(std::chrono::steady_clock::now() - taskStart).count() +
			taskResults[taskIndex].forward_seconds + taskResults[taskIndex].reverse_seconds;
	}
	hostContinuationOuterSeconds = hostElapsed(hostContinuationOuterStart);
	if (hostProfileActive && !taskResults.empty())
	{
		FasimLongQueryGpuConsumerF1Result &hostResult = taskResults[0];
		hostResult.host_profile_active = true;
		hostResult.host_validation_seconds = hostValidationSeconds;
		hostResult.host_attempt_build_seconds = hostAttemptBuildSeconds;
		hostResult.host_score_buffer_alloc_seconds = hostScoreBufferAllocSeconds;
		hostResult.host_round_descriptor_seconds = hostRoundDescriptorSeconds;
		hostResult.host_forward_stage_seconds = hostForwardStageSeconds;
		hostResult.host_forward_apply_seconds = hostForwardApplySeconds;
		hostResult.host_reverse_compact_seconds = hostReverseCompactSeconds;
		hostResult.host_reverse_stage_seconds = hostReverseStageSeconds;
		hostResult.host_reverse_apply_seconds = hostReverseApplySeconds;
		hostResult.host_round_retire_seconds = hostRoundRetireSeconds;
		hostResult.host_deferred_compact_seconds = hostDeferredCompactSeconds;
		hostResult.host_deferred_stage_seconds = hostDeferredStageSeconds;
		hostResult.host_deferred_apply_seconds = hostDeferredApplySeconds;
		hostResult.host_selection_seconds = hostSelectionSeconds;
		hostResult.host_accounting_seconds = hostAccountingSeconds;
		hostResult.host_continuation_outer_seconds = hostContinuationOuterSeconds;
		hostResult.host_inner_elapsed_seconds = hostElapsed(totalStart);
		hostResult.host_accounted_seconds =
			hostValidationSeconds + hostAttemptBuildSeconds +
			hostScoreBufferAllocSeconds + hostRoundDescriptorSeconds +
			hostForwardStageSeconds + hostForwardApplySeconds +
			hostReverseCompactSeconds + hostReverseStageSeconds +
			hostReverseApplySeconds + hostRoundRetireSeconds +
			hostDeferredCompactSeconds + hostDeferredStageSeconds +
			hostDeferredApplySeconds + hostSelectionSeconds +
			hostAccountingSeconds + hostContinuationOuterSeconds;
		hostResult.host_inner_unaccounted_seconds = std::max(0.0,
			hostResult.host_inner_elapsed_seconds -
			hostResult.host_accounted_seconds);
	}
	return true;
}

inline bool fasim_shadow_emission_only_consumer_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	uint64_t realpathReferenceAlignAttempts,
	long debugTaskKey,
	vector<struct triplex> &shadowTriplexList,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	std::string *errorOut)
{
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();
	if (errorOut != NULL)
	{
		errorOut->clear();
	}
	shadowTriplexList.clear();
	if (finalScoreInfo.empty())
	{
		fasim_gasal2_record_emission_only_consumer_shadow_request(
			1, 0, 0, "empty_scoreinfo");
		fasim_gasal2_record_emission_only_consumer_shadow_result(
			0, 0, 0, 0, 0, realpathReferenceAlignAttempts,
			0.0, 0.0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			true,
			"emission_only_consumer_shadow_active");
		return true;
	}

	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	std::vector<FasimGasal2Attempt> attempts;
	attempts.reserve(finalScoreInfo.size() * 5);
	for (size_t scoreInfoIndex = 0;
	     scoreInfoIndex < finalScoreInfo.size();
	     ++scoreInfoIndex)
	{
		const StripedSmithWaterman::scoreInfo &scoreInfo =
			finalScoreInfo[scoreInfoIndex];
		float Iden = 0.6f;
		while (Iden <= 1)
		{
			int cutlength =
				static_cast<int>(scoreInfo.score + 24) /
				(9 * Iden - 4) + 1;
			cutlength =
				scoreInfo.position - cutlength + 1 > 0 ?
				cutlength : scoreInfo.position + 1;
			const int start = scoreInfo.position - cutlength + 1;
			if (start >= 0 &&
			    cutlength > 0 &&
			    start + cutlength <= static_cast<int>(strB.size()))
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(scoreInfoIndex);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = scoreInfo.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.set_target_view(&strB,
				                        static_cast<size_t>(start),
				                        static_cast<size_t>(cutlength));
				attempts.push_back(attempt);
			}
			Iden += 0.1f;
		}
	}
	fasim_gasal2_record_emission_only_consumer_shadow_request(
		1,
		static_cast<uint64_t>(finalScoreInfo.size()),
		static_cast<uint64_t>(attempts.size()),
		"emission_only_consumer_shadow_requested");
	if (attempts.empty())
	{
		if (errorOut != NULL)
		{
			*errorOut = "empty_attempts";
		}
		fasim_gasal2_record_emission_only_consumer_shadow_result(
			0, 0, 0, 0, 0, realpathReferenceAlignAttempts,
			0.0, 0.0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			"empty_attempts");
		return false;
	}

	std::vector<FasimGasal2ScoreOnlyAlignment> scoredAttempts;
	std::string scoreError;
	const std::chrono::steady_clock::time_point scoreStart =
		std::chrono::steady_clock::now();
	auto score_attempts_for_query = [&](const string &query,
	                                    std::vector<FasimGasal2ScoreOnlyAlignment> *scores,
	                                    std::string *error) -> bool
	{
		return fasim_gasal2_score_attempts(query, attempts, scores, error);
	};
	bool scoreOk = false;
	if (fasim_gasal2_fastsim_query_length_supported_runtime(strA.size()))
	{
		scoreOk = score_attempts_for_query(strA, &scoredAttempts, &scoreError);
	}
	else
	{
		size_t tileLen =
			fasim_long_query_streaming_scoreinfo_segmented_probe_tile_len_runtime();
		size_t tileOverlap =
			fasim_long_query_streaming_scoreinfo_segmented_probe_tile_overlap_runtime();
		if (tileLen == 0)
		{
			tileLen = 2812;
		}
		if (tileOverlap >= tileLen)
		{
			tileOverlap = 0;
		}
		const std::vector<FasimGasal2LongQuerySegment> segments =
			fasim_build_gasal2_long_query_segments(
				strA,
				tileLen,
				tileOverlap,
				fasim_long_query_streaming_scoreinfo_segmented_probe_max_segments_runtime());
		if (segments.empty())
		{
			scoreError = "empty_query_segments";
		}
		else
		{
			scoredAttempts.assign(attempts.size(), FasimGasal2ScoreOnlyAlignment());
			for (size_t i = 0; i < attempts.size(); ++i)
			{
				scoredAttempts[i].scoreinfo_index = attempts[i].scoreinfo_index;
				scoredAttempts[i].cutlength = attempts[i].cutlength;
				scoredAttempts[i].start = attempts[i].start;
				scoredAttempts[i].prealign_score = attempts[i].prealign_score;
			}
			scoreOk = true;
			for (size_t segmentIndex = 0;
			     segmentIndex < segments.size();
			     ++segmentIndex)
			{
				std::vector<FasimGasal2ScoreOnlyAlignment> segmentScores;
				std::string segmentError;
				if (!score_attempts_for_query(segments[segmentIndex].query_segment,
				                              &segmentScores,
				                              &segmentError))
				{
					scoreOk = false;
					scoreError = segmentError.empty() ?
						"gasal2_segment_score_failed" : segmentError;
					break;
				}
				if (segmentScores.size() != attempts.size())
				{
					scoreOk = false;
					scoreError = "segment_score_result_count_mismatch";
					break;
				}
				for (size_t i = 0; i < segmentScores.size(); ++i)
				{
					const FasimGasal2ScoreOnlyAlignment &candidate =
						segmentScores[i];
					if (candidate.score > scoredAttempts[i].score)
					{
						scoredAttempts[i].score = candidate.score;
						scoredAttempts[i].query_end =
							candidate.query_end < 0 ?
							candidate.query_end :
							candidate.query_end +
								static_cast<int>(segments[segmentIndex].global_query_start);
						scoredAttempts[i].ref_end = candidate.ref_end;
					}
				}
			}
		}
	}
	if (!scoreOk)
	{
		if (errorOut != NULL)
		{
			*errorOut = scoreError.empty() ? "gasal2_score_failed" : scoreError;
		}
		fasim_gasal2_record_emission_only_consumer_shadow_result(
			0, 0, 0, 0, 0, realpathReferenceAlignAttempts,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - scoreStart).count(),
			0.0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			scoreError.empty() ? "gasal2_score_failed" : scoreError.c_str());
		return false;
	}
	const double scoreSeconds =
		std::chrono::duration<double>(
			std::chrono::steady_clock::now() - scoreStart).count();
	if (scoredAttempts.size() != attempts.size())
	{
		if (errorOut != NULL)
		{
			*errorOut = "score_result_count_mismatch";
		}
		fasim_gasal2_record_emission_only_consumer_shadow_result(
			0, 0, 0, 0, 0, realpathReferenceAlignAttempts,
			scoreSeconds, 0.0, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			"score_result_count_mismatch");
		return false;
	}

	std::vector<size_t> emittedAttemptIndexes;
	emittedAttemptIndexes.reserve(finalScoreInfo.size());
	uint64_t thresholdEmits = 0;
	uint64_t terminalEmits = 0;
	uint64_t lastEmits = 0;
	uint64_t emptyEmits = 0;
	const std::chrono::steady_clock::time_point selectStart =
		std::chrono::steady_clock::now();
	struct FasimEmissionOnlyDebugDecision
	{
		FasimEmissionOnlyDebugDecision() :
			legacy_have(false),
			legacy_index(0),
			legacy_score(0),
			legacy_ref_end(-1),
			legacy_query_end(-1),
			legacy_emit_reason("none"),
			shadow_have(false),
			shadow_index(0),
			shadow_score(0),
			shadow_ref_end(-1),
			shadow_query_end(-1),
			shadow_emit_reason("none")
		{
		}

		bool legacy_have;
		size_t legacy_index;
		int legacy_score;
		int legacy_ref_end;
		int legacy_query_end;
		const char *legacy_emit_reason;
		bool shadow_have;
		size_t shadow_index;
		int shadow_score;
		int shadow_ref_end;
		int shadow_query_end;
		const char *shadow_emit_reason;
	};
	std::vector<FasimEmissionOnlyDebugDecision> debugDecisions;
	const bool debugEnabled =
		fasim_gasal2_emission_only_consumer_shadow_debug_runtime();
	const bool noGpuTerminal =
		fasim_gasal2_emission_only_consumer_shadow_no_gpu_terminal_runtime();
	const bool verifyGpuTerminal =
		fasim_gasal2_emission_only_consumer_shadow_verify_terminal_runtime();
	if (debugEnabled)
	{
		debugDecisions.assign(finalScoreInfo.size(),
		                      FasimEmissionOnlyDebugDecision());
	}
	for (size_t begin = 0; begin < scoredAttempts.size();)
	{
		const int scoreInfoIndex = scoredAttempts[begin].scoreinfo_index;
		if (scoreInfoIndex < 0 ||
		    static_cast<size_t>(scoreInfoIndex) >= finalScoreInfo.size())
		{
			if (errorOut != NULL)
			{
				*errorOut = "scoreinfo_index_out_of_range";
			}
			fasim_gasal2_record_emission_only_consumer_shadow_result(
				thresholdEmits, terminalEmits, lastEmits, emptyEmits, 0,
				realpathReferenceAlignAttempts,
				scoreSeconds, 0.0, 0.0, 0.0,
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - totalStart).count(),
				false,
				"scoreinfo_index_out_of_range");
			return false;
		}
		size_t end = begin + 1;
		while (end < scoredAttempts.size() &&
		       scoredAttempts[end].scoreinfo_index == scoreInfoIndex)
		{
			++end;
		}

		bool emitted = false;
		bool haveTerminal = false;
		size_t terminalBestIndex = begin;
		int terminalBestScore = 0;
		bool haveVerifiedTerminal = false;
		size_t verifiedTerminalBestIndex = begin;
		int verifiedTerminalBestScore = 0;
		bool haveLast = false;
		size_t lastIndex = begin;
		int lastScore = 0;
		for (size_t i = begin; i < end; ++i)
		{
			const FasimGasal2ScoreOnlyAlignment &score = scoredAttempts[i];
			const FasimGasal2Attempt &attempt = attempts[i];
			if (!emitted)
			{
				haveLast = true;
				lastIndex = i;
				lastScore = score.score;
			}
			if (score.score >= finalScoreInfo[
			        static_cast<size_t>(scoreInfoIndex)].score)
			{
				emittedAttemptIndexes.push_back(i);
				if (debugEnabled)
				{
					FasimEmissionOnlyDebugDecision &decision =
						debugDecisions[static_cast<size_t>(scoreInfoIndex)];
					decision.shadow_have = true;
					decision.shadow_index = i;
					decision.shadow_score = score.score;
					decision.shadow_ref_end = score.ref_end;
					decision.shadow_query_end = score.query_end;
					decision.shadow_emit_reason = "threshold";
				}
				++thresholdEmits;
				emitted = true;
				break;
			}
			if (!noGpuTerminal &&
			    score.ref_end == attempt.start + attempt.cutlength - 1)
			{
				if (verifyGpuTerminal)
				{
					if (attempt.start < 0 ||
					    attempt.cutlength <= 0 ||
					    attempt.start + attempt.cutlength >
						    static_cast<int>(strB.size()))
					{
						continue;
					}
					std::string verifySmallSeq(
						strB.data() + attempt.start,
						static_cast<size_t>(attempt.cutlength));
					StripedSmithWaterman::Alignment verifyAlignment;
					aligner.Align(strA.c_str(),
					              verifySmallSeq.c_str(),
					              verifySmallSeq.size(),
					              filter,
					              &verifyAlignment,
					              maskLen);
					if (verifyAlignment.ref_end == attempt.cutlength - 1 &&
					    (!haveVerifiedTerminal ||
					     verifyAlignment.sw_score > verifiedTerminalBestScore))
					{
						haveVerifiedTerminal = true;
						verifiedTerminalBestIndex = i;
						verifiedTerminalBestScore = verifyAlignment.sw_score;
					}
				}
				else if (!haveTerminal || score.score > terminalBestScore)
				{
					haveTerminal = true;
					terminalBestIndex = i;
					terminalBestScore = score.score;
				}
			}
		}
		if (!emitted && verifyGpuTerminal && haveVerifiedTerminal)
		{
			emittedAttemptIndexes.push_back(verifiedTerminalBestIndex);
			if (debugEnabled)
			{
				const FasimGasal2ScoreOnlyAlignment &score =
					scoredAttempts[verifiedTerminalBestIndex];
				FasimEmissionOnlyDebugDecision &decision =
					debugDecisions[static_cast<size_t>(scoreInfoIndex)];
				decision.shadow_have = true;
				decision.shadow_index = verifiedTerminalBestIndex;
				decision.shadow_score = verifiedTerminalBestScore;
				decision.shadow_ref_end = score.ref_end;
				decision.shadow_query_end = score.query_end;
				decision.shadow_emit_reason = "verified_terminal";
			}
			++terminalEmits;
		}
		else if (!emitted && haveTerminal)
		{
			emittedAttemptIndexes.push_back(terminalBestIndex);
			if (debugEnabled)
			{
				const FasimGasal2ScoreOnlyAlignment &score =
					scoredAttempts[terminalBestIndex];
				FasimEmissionOnlyDebugDecision &decision =
					debugDecisions[static_cast<size_t>(scoreInfoIndex)];
				decision.shadow_have = true;
				decision.shadow_index = terminalBestIndex;
				decision.shadow_score = score.score;
				decision.shadow_ref_end = score.ref_end;
				decision.shadow_query_end = score.query_end;
				decision.shadow_emit_reason = "terminal";
			}
			++terminalEmits;
		}
		else if (!emitted && debugEnabled && haveLast && lastScore != 0)
		{
			const FasimGasal2ScoreOnlyAlignment &score = scoredAttempts[lastIndex];
			FasimEmissionOnlyDebugDecision &decision =
				debugDecisions[static_cast<size_t>(scoreInfoIndex)];
			emittedAttemptIndexes.push_back(lastIndex);
			decision.shadow_have = true;
			decision.shadow_index = lastIndex;
			decision.shadow_score = score.score;
			decision.shadow_ref_end = score.ref_end;
			decision.shadow_query_end = score.query_end;
			decision.shadow_emit_reason = "last_nonzero";
			++lastEmits;
		}
		else if (!emitted && !debugEnabled && haveLast && lastScore != 0)
		{
			emittedAttemptIndexes.push_back(lastIndex);
			++lastEmits;
		}
		else if (!emitted)
		{
			if (debugEnabled)
			{
				FasimEmissionOnlyDebugDecision &decision =
					debugDecisions[static_cast<size_t>(scoreInfoIndex)];
				decision.shadow_emit_reason = "empty";
			}
			++emptyEmits;
		}
		begin = end;
	}
	const double selectSeconds =
		std::chrono::duration<double>(
			std::chrono::steady_clock::now() - selectStart).count();

	if (debugEnabled)
	{
		const long debugTaskFilter =
			fasim_gasal2_emission_only_consumer_shadow_debug_task_runtime();
		const long debugScoreInfoFilter =
			fasim_gasal2_emission_only_consumer_shadow_debug_scoreinfo_runtime();
		const bool debugTaskMatches =
			debugTaskFilter < 0 || debugTaskFilter == debugTaskKey;
		if (debugTaskMatches)
		{
			for (size_t begin = 0; begin < attempts.size();)
			{
				const int scoreInfoIndex = attempts[begin].scoreinfo_index;
				size_t end = begin + 1;
				while (end < attempts.size() &&
				       attempts[end].scoreinfo_index == scoreInfoIndex)
				{
					++end;
				}
				if (scoreInfoIndex < 0 ||
				    static_cast<size_t>(scoreInfoIndex) >= debugDecisions.size())
				{
					begin = end;
					continue;
				}
				if (debugScoreInfoFilter >= 0 &&
				    debugScoreInfoFilter != scoreInfoIndex)
				{
					begin = end;
					continue;
				}
				FasimEmissionOnlyDebugDecision &decision =
					debugDecisions[static_cast<size_t>(scoreInfoIndex)];
				bool haveBest = false;
				size_t bestIndex = begin;
				StripedSmithWaterman::Alignment bestAlignment;
				bestAlignment.Clear();
				bool haveLast = false;
				size_t lastIndex = begin;
				StripedSmithWaterman::Alignment lastAlignment;
				bool emittedLegacy = false;
				for (size_t i = begin; i < end; ++i)
				{
					const FasimGasal2Attempt &attempt = attempts[i];
					const FasimGasal2ScoreOnlyAlignment &shadowScore =
						scoredAttempts[i];
					if (attempt.start < 0 ||
					    attempt.cutlength <= 0 ||
					    attempt.start + attempt.cutlength >
						    static_cast<int>(strB.size()))
					{
						continue;
					}
					std::string debugSmallSeq(
						strB.data() + attempt.start,
						static_cast<size_t>(attempt.cutlength));
					StripedSmithWaterman::Alignment localAlignment;
					aligner.Align(strA.c_str(),
					              debugSmallSeq.c_str(),
					              debugSmallSeq.size(),
					              filter,
					              &localAlignment,
					              maskLen);
					std::cerr
						<< "debug.fasim_gasal2_emission_only_consumer_shadow_attempt"
						<< " task_key=" << debugTaskKey
						<< " scoreinfo_index=" << scoreInfoIndex
						<< " attempt_index=" << i
						<< " prealign_score="
						<< finalScoreInfo[static_cast<size_t>(scoreInfoIndex)].score
						<< " position="
						<< finalScoreInfo[static_cast<size_t>(scoreInfoIndex)].position
						<< " attempt_start=" << attempt.start
						<< " attempt_cutlength=" << attempt.cutlength
						<< " cpu_score=" << localAlignment.sw_score
						<< " cpu_ref_end=" << localAlignment.ref_end + attempt.start
						<< " cpu_query_end=" << localAlignment.query_end
						<< " cpu_terminal="
						<< (localAlignment.ref_end == attempt.cutlength - 1 ? 1 : 0)
						<< " shadow_score=" << shadowScore.score
						<< " shadow_ref_end=" << shadowScore.ref_end
						<< " shadow_query_end=" << shadowScore.query_end
						<< " shadow_terminal="
						<< (shadowScore.ref_end ==
						    attempt.start + attempt.cutlength - 1 ? 1 : 0)
						<< "\n";
					if (!emittedLegacy)
					{
						haveLast = true;
						lastIndex = i;
						lastAlignment = localAlignment;
					}
					if (!emittedLegacy &&
					    localAlignment.sw_score >= finalScoreInfo[
						    static_cast<size_t>(scoreInfoIndex)].score)
					{
						decision.legacy_have = true;
						decision.legacy_index = i;
						decision.legacy_score = localAlignment.sw_score;
						decision.legacy_ref_end =
							localAlignment.ref_end + attempt.start;
						decision.legacy_query_end = localAlignment.query_end;
						decision.legacy_emit_reason = "threshold";
						emittedLegacy = true;
						break;
					}
					if (!emittedLegacy &&
					    localAlignment.sw_score > bestAlignment.sw_score &&
					    localAlignment.ref_end == attempt.cutlength - 1)
					{
						haveBest = true;
						bestIndex = i;
						bestAlignment = localAlignment;
					}
				}
				if (!emittedLegacy && haveBest)
				{
					const FasimGasal2Attempt &attempt = attempts[bestIndex];
					decision.legacy_have = true;
					decision.legacy_index = bestIndex;
					decision.legacy_score = bestAlignment.sw_score;
					decision.legacy_ref_end = bestAlignment.ref_end + attempt.start;
					decision.legacy_query_end = bestAlignment.query_end;
					decision.legacy_emit_reason = "terminal";
				}
				else if (!emittedLegacy && haveLast && lastAlignment.sw_score != 0)
				{
					const FasimGasal2Attempt &attempt = attempts[lastIndex];
					decision.legacy_have = true;
					decision.legacy_index = lastIndex;
					decision.legacy_score = lastAlignment.sw_score;
					decision.legacy_ref_end = lastAlignment.ref_end + attempt.start;
					decision.legacy_query_end = lastAlignment.query_end;
					decision.legacy_emit_reason = "last_nonzero";
				}
				begin = end;
			}
		}

		size_t printed = 0;
		const size_t limit =
			fasim_gasal2_emission_only_consumer_shadow_debug_limit_runtime();
		for (size_t i = 0; i < debugDecisions.size() && printed < limit; ++i)
		{
			if (!debugTaskMatches ||
			    (debugScoreInfoFilter >= 0 &&
			     debugScoreInfoFilter != static_cast<long>(i)))
			{
				continue;
			}
			const FasimEmissionOnlyDebugDecision &decision = debugDecisions[i];
			const bool same =
				decision.legacy_have == decision.shadow_have &&
				(!decision.legacy_have ||
				 decision.legacy_index == decision.shadow_index);
			if (same)
			{
				continue;
			}
			const size_t legacyIndex =
				decision.legacy_index < attempts.size() ?
				decision.legacy_index : static_cast<size_t>(0);
			const size_t shadowIndex =
				decision.shadow_index < attempts.size() ?
				decision.shadow_index : static_cast<size_t>(0);
			std::cerr
				<< "debug.fasim_gasal2_emission_only_consumer_shadow"
				<< " task_key=" << debugTaskKey
				<< " scoreinfo_index=" << i
				<< " prealign_score=" << finalScoreInfo[i].score
				<< " position=" << finalScoreInfo[i].position
				<< " legacy_have=" << (decision.legacy_have ? 1 : 0)
				<< " legacy_emit_reason=" << decision.legacy_emit_reason
				<< " legacy_attempt_index=" << legacyIndex
				<< " legacy_attempt_start=" << attempts[legacyIndex].start
				<< " legacy_attempt_cutlength=" << attempts[legacyIndex].cutlength
				<< " legacy_align_score=" << decision.legacy_score
				<< " legacy_ref_end=" << decision.legacy_ref_end
				<< " legacy_query_end=" << decision.legacy_query_end
				<< " shadow_have=" << (decision.shadow_have ? 1 : 0)
				<< " shadow_emit_reason=" << decision.shadow_emit_reason
				<< " shadow_attempt_index=" << shadowIndex
				<< " shadow_attempt_start=" << attempts[shadowIndex].start
				<< " shadow_attempt_cutlength=" << attempts[shadowIndex].cutlength
				<< " shadow_score=" << decision.shadow_score
				<< " shadow_ref_end=" << decision.shadow_ref_end
				<< " shadow_query_end=" << decision.shadow_query_end
				<< "\n";
			++printed;
		}
	}
	if (emittedAttemptIndexes.empty())
	{
		if (errorOut != NULL)
		{
			*errorOut = "empty_emitted_attempts";
		}
		fasim_gasal2_record_emission_only_consumer_shadow_result(
			thresholdEmits, terminalEmits, lastEmits, emptyEmits, 0,
			realpathReferenceAlignAttempts,
			scoreSeconds, selectSeconds, 0.0, 0.0,
			std::chrono::duration<double>(
				std::chrono::steady_clock::now() - totalStart).count(),
			false,
			"empty_emitted_attempts");
		return false;
	}

	vector<struct triplex> myTriplexList;
	std::string smallSeq;
	uint64_t cpuAlignAttempts = 0;
	double cpuAlignSeconds = 0.0;
	double convertSeconds = 0.0;

	for (size_t i = 0; i < emittedAttemptIndexes.size(); ++i)
	{
		const size_t attemptIndex = emittedAttemptIndexes[i];
		if (attemptIndex >= attempts.size())
		{
			if (errorOut != NULL)
			{
				*errorOut = "emitted_attempt_index_out_of_range";
			}
			fasim_gasal2_record_emission_only_consumer_shadow_result(
				thresholdEmits, terminalEmits, lastEmits, emptyEmits,
				cpuAlignAttempts, realpathReferenceAlignAttempts,
				scoreSeconds, selectSeconds, cpuAlignSeconds, convertSeconds,
				std::chrono::duration<double>(
					std::chrono::steady_clock::now() - totalStart).count(),
				false,
				"emitted_attempt_index_out_of_range");
			return false;
		}
		const FasimGasal2Attempt &attempt = attempts[attemptIndex];
		if (attempt.start < 0 ||
		    attempt.cutlength <= 0 ||
		    attempt.start + attempt.cutlength > static_cast<int>(strB.size()))
		{
			continue;
		}
		smallSeq.assign(strB.data() + attempt.start,
		                static_cast<size_t>(attempt.cutlength));
		StripedSmithWaterman::Alignment localAlignment;
		const std::chrono::steady_clock::time_point alignStart =
			std::chrono::steady_clock::now();
		aligner.Align(strA.c_str(),
		              smallSeq.c_str(),
		              smallSeq.size(),
		              filter,
		              &localAlignment,
		              maskLen);
		cpuAlignSeconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - alignStart).count();
		++cpuAlignAttempts;
		if (localAlignment.sw_score == 0)
		{
			continue;
		}
		localAlignment.ref_begin += attempt.start;
		localAlignment.ref_end += attempt.start;
		const std::chrono::steady_clock::time_point convertStart =
			std::chrono::steady_clock::now();
		convertMyTriplex(localAlignment,
		                 myTriplexList,
		                 strA,
		                 strB,
		                 strSrc,
		                 nt_table,
		                 dnaStartPos,
		                 rule,
		                 strand,
		                 Para,
		                 penaltyT,
		                 penaltyC,
		                 ntMin,
		                 ntMax,
		                 materializeAlignmentStrings);
		convertSeconds += std::chrono::duration<double>(
			std::chrono::steady_clock::now() - convertStart).count();
	}

	{
		FasimAuthorityProfileScope authoritySortScope(
			FASIM_AUTHORITY_STAGE_CLUSTER_RANK_SORT);
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	}
	for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
	{
		triplex atr = myTriplexList[i];
		if (atr.identity >= paraList.minIdentity &&
		    atr.tri_score >= paraList.minStability &&
		    atr.nt >= ntMin)
		{
			shadowTriplexList.push_back(atr);
		}
	}
	fasim_gasal2_record_emission_only_consumer_shadow_result(
		thresholdEmits,
		terminalEmits,
		lastEmits,
		emptyEmits,
		cpuAlignAttempts,
		realpathReferenceAlignAttempts,
		scoreSeconds,
		selectSeconds,
		cpuAlignSeconds,
		convertSeconds,
		std::chrono::duration<double>(
			std::chrono::steady_clock::now() - totalStart).count(),
		true,
		"emission_only_consumer_shadow_active");
	return true;
}

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut)
{
	FasimAuthorityProfileScope authorityStabilityScope(
		FASIM_AUTHORITY_STAGE_STABILITY_IDENTITY_NT);
	int match = 0;
	int mis_match = 0;
	int nt = 0;

	float tri_score = 0.0f;
	float hashvalue = 0.0f;
	float prescore = 0.0f;
	char prechar = 0;
	char curchar = 0;

	int32_t q = alignment.ref_begin;
	int32_t p = alignment.query_begin;

	for (size_t cLoop = 0; cLoop < alignment.cigar.size(); ++cLoop)
	{
		const uint32_t cigarInt = alignment.cigar[cLoop];
		const char letter = cigar_int_to_op(cigarInt);
		const uint32_t length = cigar_int_to_len(cigarInt);
		for (uint32_t i = 0; i < length; ++i)
		{
			char refc = 0;
			char refc_src = 0;
			char readc = 0;
			bool ref_gap = false;

			if (letter == 'I')
			{
				refc = '-';
				refc_src = '-';
				readc = read_seq[static_cast<size_t>(p)];
				++p;
				ref_gap = true;
			}
			else if (letter == 'D')
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = '-';
			}
			else
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = read_seq[static_cast<size_t>(p)];
				++p;
			}

			++nt;
			if (refc == readc)
			{
				++match;
			}
			else
			{
				++mis_match;
			}

			curchar = (refc == '-') ? '-' : refc_src;
			hashvalue = triplex_score(curchar, readc, static_cast<int>(Para));

			if ((curchar == prechar) && curchar == 'T')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyT);
				hashvalue = static_cast<float>(penaltyT);
			}
			if ((curchar == prechar) && curchar == 'C')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyC);
				hashvalue = static_cast<float>(penaltyC);
			}
			prescore = hashvalue;
			if (!ref_gap)
			{
				prechar = curchar;
			}
			tri_score += hashvalue;
		}
	}

	ntOut = nt;
	identityOut = (match + mis_match) ? (static_cast<float>(100 * match) / static_cast<float>(match + mis_match)) : 0.0f;
	if (nt > 0 && nt >= ntMin && nt <= ntMax)
	{
		triScoreOut = tri_score / static_cast<float>(nt);
	}
	else
	{
		triScoreOut = 0.0f;
	}
}

bool buildConvertedTriplexRecord(const StripedSmithWaterman::Alignment &alignment,
	FasimConvertedTriplexRecord &record,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	const FasimConvertMaterializationPolicy &policy)
{
	FasimAuthorityProfileScope authorityConversionScope(
		FASIM_AUTHORITY_STAGE_TRIPLEX_CONVERSION);
	int nt = 0;
	float identity = 0.0f;
	float tri_score = 0.0f;
	fasim_calc_identity_and_triscore_from_cigar(alignment,
	                                            ref_seq,
	                                            read_seq,
	                                            ref_seq_src,
	                                            Para,
	                                            penaltyT,
	                                            penaltyC,
	                                            ntMin,
	                                            ntMax,
	                                            identity,
	                                            tri_score,
	                                            nt);

	string read_align;
	string ref_align_src;
	if (policy.materialize_alignment_strings)
	{
		string ref_align;
		getAlignment(alignment, ref_seq, read_seq, ref_seq_src, table, ref_align, read_align, ref_align_src);
	}

	int refStart;
	int refEnd;
	if ((Para > 0 && strand == 1) || (Para < 0 && strand == 0))
	{
		refStart = static_cast<int>(ref_seq.size()) - alignment.ref_end - 1;
		refEnd = static_cast<int>(ref_seq.size()) - alignment.ref_begin - 1;
	}
	else
	{
		refStart = alignment.ref_begin + 1;
		refEnd = alignment.ref_end + 1;
	}

	const float score = static_cast<float>(alignment.sw_score);
	record = FasimConvertedTriplexRecord();
	record.stari = alignment.query_begin + 1;
	record.endi = alignment.query_end + 1;
	record.starj = refStart + dnaStartPos;
	record.endj = refEnd + dnaStartPos;
	record.strand = static_cast<int>(strand);
	record.reverse = static_cast<int>(Para);
	record.rule = static_cast<int>(rule);
	record.nt = nt;
	record.score = score;
	record.identity = identity;
	record.tri_score = tri_score;
	record.stri_align = read_align;
	record.strj_align = ref_align_src;
	record.middle = static_cast<int>((record.stari + record.endi) / 2);
	record.center = record.middle;
	if (policy.materialize_cigar_probe_string &&
	    (fasim_tfosorted_cigar_archive_probe_enabled_runtime() ||
	     fasim_tfosorted_compact_archive_probe_enabled_runtime() ||
	     fasim_tfosorted_column_archive_probe_enabled_runtime()))
	{
		record.cigar_probe = fasim_cigar_probe_string(alignment.cigar);
	}
	if (policy.materialize_typed_cigar)
	{
		record.typed_cigar = alignment.cigar;
	}
	if (nt >= ntMin)
	{
		return true;
	}
	return false;
}

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings,
	bool materializeCigarProbe)
{
	FasimConvertMaterializationPolicy policy;
	policy.materialize_alignment_strings = materializeAlignmentStrings;
	policy.materialize_cigar_probe_string = materializeCigarProbe;
	FasimConvertedTriplexRecord converted;
	if (!buildConvertedTriplexRecord(alignment,
	                                 converted,
	                                 read_seq,
	                                 ref_seq,
	                                 ref_seq_src,
	                                 table,
	                                 dnaStartPos,
	                                 rule,
	                                 strand,
	                                 Para,
	                                 penaltyT,
	                                 penaltyC,
	                                 ntMin,
	                                 ntMax,
	                                 policy))
	{
		return;
	}
	struct triplex fullTriplex;
	fullTriplex = triplex(converted.stari, converted.endi,
	                      converted.starj, converted.endj,
	                      converted.strand, converted.reverse,
	                      converted.rule, converted.nt, converted.score,
	                      converted.identity, converted.tri_score,
	                      converted.stri_align, converted.strj_align,
	                      0, 0, 0, 0, 0, 0, "");
	fullTriplex.cigar_probe = converted.cigar_probe;
	fullTriplex.typed_cigar = converted.typed_cigar;
	triplex_list.push_back(fullTriplex);
}

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src)
{
	// Use this function to get alignment of two sequences.
	int cLoop;
	std::vector<uint32_t> tmpCigar;
	for (cLoop = 0; cLoop < alignment.cigar.size(); cLoop++)
	{
		tmpCigar.push_back(alignment.cigar[cLoop]);
	}
	if (tmpCigar.size() > 0)
	{
		// begin to generate alignment.
		int32_t c = 0, left = 0, e = 0, qb = alignment.ref_begin, pb = alignment.query_begin;//need to CHECK
		uint32_t i;
		uint32_t j;
		while (e < tmpCigar.size() || left > 0)
		{
			int32_t count = 0;
			int32_t q = qb;
			int32_t p = pb;
			//fprintf(stdout, "Target: %8d		", q + 1);
			// DEBUG.
			//e = y + 1;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'I')
					{
						//fprintf(stdout, "-");
						ref_align = ref_align + "-";
						ref_align_src = ref_align_src + '-';
					}
					else
					{
						//fprintf(stdout, "%c", ref_seq[q]);
						ref_align = ref_align + ref_seq[q];
						ref_align_src = ref_align_src + ref_seq_src[q];
						++q;
					}
					++count;
					if (count == 60) goto step2;
				}
			}//for c = e.

		step2:
			//fprintf(stdout, "		%d\n										", q);
			q = qb;
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'M')
						//if (letter == '=')
					{
						if (table[(int)ref_seq[q]] == table[(int)read_seq[p]])
						{
							//fprintf(stdout, "|");
						}
						else
						{
							//fprintf(stdout, "*");
						}
						++q;
						++p;
					}
					else
					{
						//fprintf(stdout, "*");
						if (letter == 'I')
						{
							++p;
						}
						else
						{
							++q;
						}
					}
					++count;
					if (count == 60)
					{
						qb = q;
						goto step3;
					}
				}
			}// for c = e.
		step3:
			p = pb;
			//fprintf(stdout, "\nQuery:	%8d		", p + 1);
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; i++)
				{
					if (letter == 'D')
					{
						//fprintf(stdout, "-");
						read_align = read_align + "-";
					}
					else
					{
						//fprintf(stdout, "%c", read_seq[p]);
						read_align = read_align + read_seq[p];
						++p;
					}
					++count;
					if (count == 60)
					{
						pb = p;
						left = l - i - 1;
						e = (left == 0) ? (c + 1) : c;
						goto end;

					}
				}
			}// for c = e.
			e = c;
			left = 0;
		end:
			//fprintf(stdout, "		%d\n\n", p);
			j = 0;
				//2021-09-16 23:04:55: we don't need to print alignment, we
			// just need to get alignment sequence.
			//cout << ref_align << " is ref_align" << endl;
			//cout << read_align << " is read_align" << endl;
		}
	}
}
