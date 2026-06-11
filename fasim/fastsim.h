#include <iostream>
#include <string.h>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include <utility>
#include <chrono>
#include "ssw_cpp.h"
#include "ssw.h"
#include "sim.h"
#include "gasal2_align_bridge.h"
#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"
#define N 50
using std::string;
using std::cout;
using std::endl;
using std::ifstream;

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
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
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
	bool materializeAlignmentStrings);

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

void fastSIM(string& strA, string& strB, string& strSrc,
	long dnaStartPos, long min_score, float parm_M,
	float parm_I, float parm_O, float parm_E,
	vector<struct triplex>& triplex_list,
	long strand, long Para, long rule,
	int ntMin, int ntMax, int penaltyT,
	int penaltyC, struct para paraList,
	bool materializeAlignmentStrings = true)
{
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
	    !fasim_gasal2_attempt_consumer_shadow_enabled_runtime())
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
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
			myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
			myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
			std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
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
			StripedSmithWaterman::Alignment bestalignment;
			bestalignment.sw_score = 0;
			while (Iden <= 1)
			{
				cutlength = (int)(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
				cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
				const std::chrono::steady_clock::time_point substrStart =
					std::chrono::steady_clock::now();
				smallSeq = strB.substr(finalScoreInfo[i].position - cutlength + 1, cutlength);
				if (timing != NULL)
				{
					timing->substr_seconds +=
						std::chrono::duration<double>(
							std::chrono::steady_clock::now() - substrStart).count();
				}
				const std::chrono::steady_clock::time_point alignStart =
					std::chrono::steady_clock::now();
				aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &alignment, maskLen);
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
				myflag = 2;
			}
			Iden += 0.1;
		}
		if (myflag == 2)
		{
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
			bestalignment.Clear();
			if (alignment.sw_score != 0)
			{
				alignment.ref_begin = alignment.ref_begin + finalScoreInfo[i].position - cutlength + 1;
				alignment.ref_end = alignment.ref_end + finalScoreInfo[i].position - cutlength + 1;
				const std::chrono::steady_clock::time_point convertStart =
					std::chrono::steady_clock::now();
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
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
		myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
		std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
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

	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
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

	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
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
	bool materializeAlignmentStrings)
{
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
	if (materializeAlignmentStrings)
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
	struct triplex fullTriplex;
	fullTriplex = triplex(alignment.query_begin + 1, alignment.query_end + 1,
	                      refStart + dnaStartPos, refEnd + dnaStartPos,
	                      strand, Para, rule, nt, score, identity, tri_score,
	                      read_align, ref_align_src, 0, 0, 0, 0, 0, 0, "");
	if (fasim_tfosorted_cigar_archive_probe_enabled_runtime() ||
	    fasim_tfosorted_compact_archive_probe_enabled_runtime() ||
	    fasim_tfosorted_column_archive_probe_enabled_runtime())
	{
		fullTriplex.cigar_probe = fasim_cigar_probe_string(alignment.cigar);
	}
	if (nt >= ntMin)
	{
		triplex_list.push_back(fullTriplex);
	}
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
