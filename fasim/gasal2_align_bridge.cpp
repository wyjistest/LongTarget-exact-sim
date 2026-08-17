#include "gasal2_align_bridge.h"
#include "gasal2_traceback_certificate.h"

#include "gasal_header.h"
#include "ssw.h"
#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <set>
#include <sstream>

namespace
{

const int kDefaultStreams = 2;
const int kMaxStreams = 16;
const int kDefaultMaxQueryLen = 2812;

enum class GasalMode
{
	ScoreOnly,
	Traceback
};

int streamed_attempt_cuda_device();

struct BridgeState
{
	BridgeState() :
		initialized(false),
		max_query_len(0),
		max_target_len(0),
		max_alns(0)
	{
	}

	Parameters *params = NULL;
	gasal_gpu_storage_v storage;
	bool initialized;
	int max_query_len;
	int max_target_len;
	int max_alns;
};

struct StreamedAttemptQueryCache
{
	StreamedAttemptQueryCache() :
		device(-1),
		seg_len(0),
		query(),
		profile(),
		handle()
	{
	}

	~StreamedAttemptQueryCache()
	{
		prealign_cuda_release_query(&handle);
	}

	bool prepare(const std::string &queryValue, std::string *errorOut)
	{
		const int requestedDevice = streamed_attempt_cuda_device();
		if (device == requestedDevice && query == queryValue &&
		    handle.profileDevice != 0)
		{
			return true;
		}

		prealign_cuda_release_query(&handle);
		device = requestedDevice;
		seg_len = 0;
		query.clear();
		profile.clear();
		if (!prealign_cuda_init(device, errorOut))
		{
			return false;
		}
		prealign_shared_build_query_profile(
			queryValue, 5, 4, profile, seg_len);
		if (!prealign_cuda_prepare_query(
			&handle,
			profile.data(),
			5,
			seg_len,
			static_cast<int>(queryValue.size()),
			errorOut))
		{
			prealign_cuda_release_query(&handle);
			return false;
		}
		query = queryValue;
		return true;
	}

	int device;
	int seg_len;
	std::string query;
	std::vector<int16_t> profile;
	PreAlignCudaQueryHandle handle;
};

std::mutex g_mutex;
FasimGasal2Stats g_stats;
BridgeState g_score_state;
BridgeState g_traceback_state;
StreamedAttemptQueryCache g_streamed_attempt_query_cache;
uint64_t g_limited_traceback_export_batch_id = 0;

double seconds_since(const std::chrono::steady_clock::time_point &start)
{
	return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

int env_int_or_default(const char *name, int defaultValue)
{
	const char *env = std::getenv(name);
	if (env == NULL || env[0] == '\0')
	{
		return defaultValue;
	}
	const int value = std::atoi(env);
	return value > 0 ? value : defaultValue;
}

int env_int_or_zero(const char *name)
{
	const char *env = std::getenv(name);
	if (env == NULL || env[0] == '\0')
	{
		return 0;
	}
	const int value = std::atoi(env);
	return value > 0 ? value : 0;
}

int env_int_or_unlimited(const char *name)
{
	const char *env = std::getenv(name);
	if (env == NULL || env[0] == '\0')
	{
		return 0;
	}
	const int value = std::atoi(env);
	return value > 0 ? value : 0;
}

int streamed_attempt_cuda_device()
{
	const char *env = std::getenv("FASIM_CUDA_DEVICE");
	if (env == NULL || env[0] == '\0')
	{
		env = std::getenv("LONGTARGET_CUDA_DEVICE");
	}
	if (env == NULL || env[0] == '\0')
	{
		return 0;
	}
	const int value = std::atoi(env);
	return value >= 0 ? value : 0;
}

int streamed_attempt_batch_size()
{
	const int configured = env_int_or_default(
		"FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH", 4096);
	return std::max(1, std::min(configured, 32768));
}

bool streamed_attempt_runtime_preflight(
	uint64_t queryLength,
	uint64_t maximumTargetSubviewLength,
	bool maximumTargetSubviewLengthKnown,
	const FasimLongQueryScoringContract &scoringContract,
	FasimLongQueryRuntimeDescriptor *descriptorOut,
	std::string *errorOut)
{
	FasimLongQueryRuntimeGuardRequest request;
	request.query_length = queryLength;
	request.maximum_target_subview_length = maximumTargetSubviewLength;
	request.maximum_target_subview_length_known =
		maximumTargetSubviewLengthKnown;
	request.scoring = scoringContract;
	const char *deviceValue = std::getenv("FASIM_CUDA_DEVICE");
	if (deviceValue == NULL || deviceValue[0] == '\0')
	{
		deviceValue = std::getenv("LONGTARGET_CUDA_DEVICE");
	}
	const bool deviceSelectorValid =
		fasim_long_query_runtime_parse_device_index(
			deviceValue, &request.device_index);
	request.cuda_built = prealign_cuda_is_built();
	std::string resourceError;
	if (deviceSelectorValid && request.cuda_built && request.query_length > 0 &&
		request.query_length <= fasim_long_query_runtime_query_length_limit())
	{
		PreAlignCudaQueryHandle resourceProbe;
		resourceProbe.device = request.device_index;
		resourceProbe.queryLength = static_cast<int>(request.query_length);
		resourceProbe.segLen = static_cast<int>(
			(request.query_length + 31u) / 32u);
		PreAlignCudaResourceLimits limits;
		if (prealign_cuda_query_resource_limits(
				resourceProbe, &limits, &resourceError))
		{
			request.device_supported = true;
			request.resource_limits_available = true;
			request.default_dynamic_smem_limit_bytes =
				static_cast<uint64_t>(limits.defaultDynamicSmemLimitBytes);
			request.optin_dynamic_smem_limit_bytes =
				static_cast<uint64_t>(limits.optinDynamicSmemLimitBytes);
		}
	}
	return fasim_long_query_runtime_preflight(
		request, descriptorOut, errorOut);
}

bool env_enabled(const char *name)
{
	const char *env = std::getenv(name);
	return env != NULL && env[0] != '\0' && env[0] != '0';
}

bool env_present(const char *name)
{
	const char *env = std::getenv(name);
	return env != NULL && env[0] != '\0';
}

bool gasal2_cigar_string_enabled_for_mode()
{
	if (env_present("FASIM_ALIGN_GASAL2_CIGAR_STRING"))
	{
		return env_enabled("FASIM_ALIGN_GASAL2_CIGAR_STRING");
	}
	return !env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
}

int gasal2_batch_size_default()
{
	const int top5Default = env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO") ? 30000 : 5000;
	return env_int_or_default("FASIM_ALIGN_GASAL2_BATCH", top5Default);
}

int gasal2_stream_count()
{
	int streams = env_int_or_default("FASIM_ALIGN_GASAL2_STREAMS", kDefaultStreams);
	if (streams < 1)
	{
		streams = 1;
	}
	if (streams > kMaxStreams)
	{
		streams = kMaxStreams;
	}
	return streams;
}

bool check_length_guard(const char *stage,
                        size_t queryLen,
                        size_t observedMaxTargetLen,
                        std::string *errorOut)
{
	const int maxQueryLen = env_int_or_default("FASIM_ALIGN_GASAL2_MAX_QUERY_LEN",
	                                           kDefaultMaxQueryLen);
	const int maxTargetLenGuard = env_int_or_unlimited("FASIM_ALIGN_GASAL2_MAX_TARGET_LEN");
	const bool queryTooLong =
		maxQueryLen > 0 && queryLen > static_cast<size_t>(maxQueryLen);
	const bool targetTooLong =
		maxTargetLenGuard > 0 &&
		observedMaxTargetLen > static_cast<size_t>(maxTargetLenGuard);
	if (!queryTooLong && !targetTooLong)
	{
		return true;
	}
	++g_stats.length_guard_fallbacks;
	g_stats.length_guard_last_query_len = static_cast<uint64_t>(queryLen);
	g_stats.length_guard_max_query_len = static_cast<uint64_t>(maxQueryLen);
	g_stats.length_guard_last_target_len = static_cast<uint64_t>(observedMaxTargetLen);
	g_stats.length_guard_max_target_len = static_cast<uint64_t>(maxTargetLenGuard);
	if (errorOut != NULL)
	{
		std::ostringstream error;
		error << "GASAL2 " << stage << " length guard";
		if (queryTooLong)
		{
			error << ": query_len=" << queryLen << " > max_query_len=" << maxQueryLen;
		}
		if (targetTooLong)
		{
			error << ": max_target_len=" << observedMaxTargetLen
			      << " > guard_max_target_len=" << maxTargetLenGuard;
		}
		*errorOut = error.str();
	}
	return false;
}

void record_effective_batch_size(int batchSize)
{
	if (g_stats.effective_batch_size == 0)
	{
		g_stats.effective_batch_size = batchSize;
	}
}

void record_effective_streams(int streams)
{
	if (g_stats.effective_streams == 0)
	{
		g_stats.effective_streams = streams;
	}
}

bool score_prepass_enabled_for_mode(bool longtargetBridge, bool top5Preset)
{
	if (env_enabled("FASIM_ALIGN_GASAL2_ALL_TRACEBACK"))
	{
		return false;
	}
	if (env_present("FASIM_ALIGN_GASAL2_SCORE_PREPASS"))
	{
		return env_enabled("FASIM_ALIGN_GASAL2_SCORE_PREPASS");
	}
	if (top5Preset)
	{
		return true;
	}
	return longtargetBridge;
}

bool staged_score_prepass_enabled_for_mode(bool top5Preset)
{
	if (env_present("FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS"))
	{
		return env_enabled("FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS");
	}
	return top5Preset;
}

bool staged_first_prune_enabled_for_mode(bool top5Preset)
{
	if (env_present("FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE"))
	{
		return env_enabled("FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE");
	}
	return top5Preset;
}

bool traceback_query_reuse_enabled_for_mode(bool top5Preset)
{
	if (env_present("FASIM_ALIGN_GASAL2_TRACEBACK_QUERY_REUSE"))
	{
		return env_enabled("FASIM_ALIGN_GASAL2_TRACEBACK_QUERY_REUSE");
	}
	return top5Preset;
}

bool nt_sum_span_prune_enabled()
{
	return env_enabled("FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE");
}

bool traceback_certificate_shadow_enabled()
{
	return env_enabled("FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW");
}

int limited_traceback_max_scoreinfos()
{
	return env_int_or_zero("FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS");
}

int limited_traceback_min_prealign_score()
{
	return env_int_or_zero("FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE");
}

int limited_traceback_guard_min_prealign_score()
{
	return env_int_or_zero("FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MIN_PREALIGN_SCORE");
}

int limited_traceback_guard_max_prealign_score()
{
	return env_int_or_zero("FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_PREALIGN_SCORE");
}

int limited_traceback_guard_max_target_size()
{
	return env_int_or_zero("FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_TARGET_SIZE");
}

std::string limited_traceback_mode()
{
	const char *env = std::getenv("FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE");
	if (env == NULL || env[0] == '\0')
	{
		return "score";
	}
	return std::string(env);
}

std::string limited_traceback_attempt_export_path()
{
	const char *env = std::getenv("FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_ATTEMPT_EXPORT");
	if (env == NULL || env[0] == '\0')
	{
		return "";
	}
	return std::string(env);
}

bool file_exists(const std::string &path)
{
	std::ifstream input(path.c_str());
	return input.good();
}

size_t attempt_target_size(const FasimGasal2Attempt &attempt)
{
	return attempt.target_size();
}

const char *attempt_target_data(const FasimGasal2Attempt &attempt)
{
	return attempt.target_data();
}

uint32_t gasal_padded_bytes(size_t size)
{
	return static_cast<uint32_t>(size + ((8 - (size % 8)) % 8));
}

struct ScoreOnlyResult;

bool run_score_only(BridgeState *state,
                    const std::string &query,
                    const std::vector<FasimGasal2Attempt> &attempts,
                    int batchSize,
                    std::vector<ScoreOnlyResult> *results,
                    std::string *errorOut);

void ensure_params(BridgeState *state, GasalMode mode)
{
	if (state->params != NULL)
	{
		return;
	}
	if (mode == GasalMode::Traceback)
	{
		const char *argv[] = {
			"fasim_gasal2",
			"-t",
			"-a", "5",
			"-b", "4",
			"-q", "12",
			"-r", "4",
			"-y", "local",
			"unused_query.fa",
			"unused_target.fa",
		};
		state->params = new Parameters(static_cast<int>(sizeof(argv) / sizeof(argv[0])),
		                               const_cast<char **>(argv));
		state->params->start_pos = WITH_TB;
	}
	else
	{
		const char *argv[] = {
			"fasim_gasal2",
			"-a", "5",
			"-b", "4",
			"-q", "12",
			"-r", "4",
			"-y", "local",
			"unused_query.fa",
			"unused_target.fa",
		};
		state->params = new Parameters(static_cast<int>(sizeof(argv) / sizeof(argv[0])),
		                               const_cast<char **>(argv));
		state->params->start_pos = WITHOUT_START;
	}
	state->params->print_out = 0;
	state->params->n_threads = 1;
	state->params->sa = 5;
	state->params->sb = 4;
	state->params->gapo = env_int_or_default("FASIM_ALIGN_GASAL2_GAP_OPEN", 12);
	state->params->gape = env_int_or_default("FASIM_ALIGN_GASAL2_GAP_EXTEND", 4);
	state->params->algo = LOCAL;
	state->params->secondBest = FALSE;
	state->params->isPacked = false;
	state->params->isReverseComplement = false;
}

bool ensure_state(BridgeState *state,
                  GasalMode mode,
                  int queryLen,
                  int maxTargetLen,
                  int maxAlns,
                  std::string *errorOut)
{
	ensure_params(state, mode);
	if (queryLen <= 0 || maxTargetLen <= 0 || maxAlns <= 0)
	{
		if (errorOut != NULL)
		{
			*errorOut = "invalid GASAL2 batch dimensions";
		}
		return false;
	}

	const int paddedQuery = queryLen + 7;
	const int paddedTarget = maxTargetLen + 7;
	if (state->initialized &&
	    paddedQuery <= state->max_query_len &&
	    paddedTarget <= state->max_target_len &&
	    maxAlns <= state->max_alns)
	{
		return true;
	}

	const auto initStart = std::chrono::steady_clock::now();
	if (state->initialized)
	{
		gasal_destroy_streams(&state->storage, state->params);
		gasal_destroy_gpu_storage_v(&state->storage);
		state->initialized = false;
	}

	gasal_subst_scores subScores;
	subScores.match = state->params->sa;
	subScores.mismatch = state->params->sb;
	subScores.gap_open = state->params->gapo;
	subScores.gap_extend = state->params->gape;
	gasal_copy_subst_scores(&subScores);

	const int streamCount = gasal2_stream_count();
	record_effective_streams(streamCount);
	state->storage = gasal_init_gpu_storage_v(streamCount);
	gasal_init_streams(&state->storage, paddedQuery, paddedTarget, maxAlns, state->params);
	for (int i = 0; i < state->storage.n; ++i)
	{
		// GASAL2 uses unpacked_query_batch for traceback CIGAR output. The
		// device result struct leaves cigar uninitialized, but its destroy path
		// still tries to cudaFree it when storage is resized.
		if (state->storage.a[i].device_cpy != NULL)
		{
			state->storage.a[i].device_cpy->cigar = NULL;
			state->storage.a[i].device_cpy->n_cigar_ops = NULL;
		}
		if (mode == GasalMode::ScoreOnly && state->storage.a[i].host_res != NULL)
		{
			state->storage.a[i].host_res->cigar = NULL;
			state->storage.a[i].host_res->n_cigar_ops = NULL;
		}
	}
	state->initialized = true;
	state->max_query_len = paddedQuery;
	state->max_target_len = paddedTarget;
	state->max_alns = maxAlns;
	g_stats.init_seconds += seconds_since(initStart);
	return true;
}

uint32_t op_to_bam(char op)
{
	switch (op)
	{
	case 'M': return 0;
	case 'I': return 1;
	case 'D': return 2;
	case 'S': return 4;
	case 'X': return 8;
	default: return 0;
	}
}

void decode_gasal_cigar(const gasal_gpu_storage_t &storage,
                        uint32_t alnIndex,
                        uint32_t cigarOffset,
                        bool materializeCigarString,
                        StripedSmithWaterman::Alignment &alignment)
{
	alignment.cigar.clear();
	alignment.cigar_string.clear();
	const uint32_t nOps = storage.host_res->n_cigar_ops[alnIndex];
	if (nOps == 0)
	{
		return;
	}

	const auto vectorStart = std::chrono::steady_clock::now();
	alignment.cigar.reserve(nOps);
	int lastOp = storage.host_res->cigar[cigarOffset + nOps - 1] & 3;
	int count = storage.host_res->cigar[cigarOffset + nOps - 1] >> 2;
	for (int u = static_cast<int>(nOps) - 2; u >= 0; --u)
	{
		const int currOp = storage.host_res->cigar[cigarOffset + static_cast<uint32_t>(u)] & 3;
		const int currCount = storage.host_res->cigar[cigarOffset + static_cast<uint32_t>(u)] >> 2;
		if (currOp == lastOp)
		{
			count += currCount;
		}
		else
		{
			const char op = lastOp == 0 ? 'M' : (lastOp == 1 ? 'X' : (lastOp == 2 ? 'D' : 'I'));
			alignment.cigar.push_back((static_cast<uint32_t>(count) << BAM_CIGAR_SHIFT) | op_to_bam(op));
			count = currCount;
		}
		lastOp = currOp;
	}
	const char op = lastOp == 0 ? 'M' : (lastOp == 1 ? 'X' : (lastOp == 2 ? 'D' : 'I'));
	alignment.cigar.push_back((static_cast<uint32_t>(count) << BAM_CIGAR_SHIFT) | op_to_bam(op));
	g_stats.traceback_cigar_vector_seconds += seconds_since(vectorStart);
	g_stats.traceback_cigar_raw_ops += nOps;
	g_stats.traceback_cigar_merged_ops += alignment.cigar.size();
	if (materializeCigarString)
	{
		const auto stringStart = std::chrono::steady_clock::now();
		std::ostringstream cigar;
		for (size_t i = 0; i < alignment.cigar.size(); ++i)
		{
			cigar << cigar_int_to_len(alignment.cigar[i]) << cigar_int_to_op(alignment.cigar[i]);
		}
		alignment.cigar_string = cigar.str();
		g_stats.traceback_cigar_string_seconds += seconds_since(stringStart);
	}
}

void copy_alignment(const gasal_gpu_storage_t &storage,
                    uint32_t alnIndex,
                    const FasimGasal2Attempt &attempt,
                    bool materializeCigarString,
                    StripedSmithWaterman::Alignment &alignment)
{
	alignment.Clear();
	alignment.sw_score = static_cast<uint16_t>(std::max(0, storage.host_res->aln_score[alnIndex]));
	alignment.sw_score_next_best = 0;
	alignment.query_begin = storage.host_res->query_batch_start[alnIndex];
	alignment.query_end = storage.host_res->query_batch_end[alnIndex];
	alignment.ref_begin = storage.host_res->target_batch_start[alnIndex];
	alignment.ref_end = storage.host_res->target_batch_end[alnIndex];
	alignment.ref_end_next_best = 0;
	alignment.mismatches = 0;
	decode_gasal_cigar(storage,
	                   alnIndex,
	                   storage.use_cigar_offsets && storage.host_cigar_offsets != NULL ?
	                       storage.host_cigar_offsets[alnIndex] :
	                       storage.host_query_batch_offsets[alnIndex],
	                   materializeCigarString,
	                   alignment);
	alignment.ref_begin += attempt.start;
	alignment.ref_end += attempt.start;
}

struct ScoreOnlyResult
{
	ScoreOnlyResult() :
		sw_score(0),
		query_end(0),
		ref_end(0)
	{
	}

	int sw_score;
	int query_end;
	int ref_end;
};

bool attempt_pruned_by_nt_sum_span(const FasimGasal2Attempt &attempt,
                                   const ScoreOnlyResult &result)
{
	if (attempt.nt_min_length <= 0)
	{
		return false;
	}
	const int querySpan = result.query_end + 1;
	const int refSpan = result.ref_end - attempt.start + 1;
	return querySpan + refSpan < attempt.nt_min_length;
}

void copy_score_result(const gasal_gpu_storage_t &storage,
                       uint32_t alnIndex,
                       const FasimGasal2Attempt &attempt,
                       ScoreOnlyResult &result)
{
	result.sw_score = std::max(0, storage.host_res->aln_score[alnIndex]);
	result.query_end = storage.host_res->query_batch_end[alnIndex];
	result.ref_end = storage.host_res->target_batch_end[alnIndex] + attempt.start;
}

bool wait_for_all_traceback(BridgeState *state,
                            std::vector<uint32_t> &streamCounts,
	                  std::vector<size_t> &streamStarts,
	                  const std::vector<FasimGasal2Attempt> &attempts,
	                  std::vector<StripedSmithWaterman::Alignment> &alignments,
                  std::string *errorOut)
{
	bool anyBusy = true;
	const bool materializeCigarString = gasal2_cigar_string_enabled_for_mode();
	while (anyBusy)
	{
		anyBusy = false;
		for (int s = 0; s < state->storage.n; ++s)
		{
			gasal_gpu_storage_t *storage = &state->storage.a[s];
			const int done = gasal_is_aln_async_done(storage);
			if (done == -1)
			{
				anyBusy = true;
				continue;
			}
			if (done == 0)
			{
				const auto copyStart = std::chrono::steady_clock::now();
				const size_t begin = streamStarts[static_cast<size_t>(s)];
				const uint32_t count = streamCounts[static_cast<size_t>(s)];
				for (uint32_t i = 0; i < count; ++i)
				{
					copy_alignment(*storage,
					               i,
					               attempts[begin + i],
					               materializeCigarString,
					               alignments[begin + i]);
				}
				g_stats.traceback_result_copy_seconds += seconds_since(copyStart);
				streamCounts[static_cast<size_t>(s)] = 0;
			}
		}
	}
	(void)errorOut;
	return true;
}

bool wait_for_all_score(BridgeState *state,
                        std::vector<uint32_t> &streamCounts,
                        std::vector<size_t> &streamStarts,
                        const std::vector<FasimGasal2Attempt> &attempts,
                        std::vector<ScoreOnlyResult> &results,
                        std::string *errorOut)
{
	bool anyBusy = true;
	while (anyBusy)
	{
		anyBusy = false;
		for (int s = 0; s < state->storage.n; ++s)
		{
			gasal_gpu_storage_t *storage = &state->storage.a[s];
			const int done = gasal_is_aln_async_done(storage);
			if (done == -1)
			{
				anyBusy = true;
				continue;
			}
			if (done == 0)
			{
				const auto copyStart = std::chrono::steady_clock::now();
				const size_t begin = streamStarts[static_cast<size_t>(s)];
				const uint32_t count = streamCounts[static_cast<size_t>(s)];
				for (uint32_t i = 0; i < count; ++i)
				{
					copy_score_result(*storage,
					                  i,
					                  attempts[begin + i],
					                  results[begin + i]);
				}
				g_stats.score_result_copy_seconds += seconds_since(copyStart);
				streamCounts[static_cast<size_t>(s)] = 0;
			}
		}
	}
	(void)errorOut;
	return true;
}

void select_alignments(const std::vector<FasimGasal2Attempt> &attempts,
                       const std::vector<StripedSmithWaterman::Alignment> &alignments,
                       std::vector<FasimGasal2SelectedAlignment> *selected)
{
	selected->clear();
	int currentScoreInfo = -1;
	StripedSmithWaterman::Alignment best;
	FasimGasal2Attempt bestAttempt;
	bool haveBest = false;
	StripedSmithWaterman::Alignment last;
	FasimGasal2Attempt lastAttempt;
	bool haveLast = false;
	bool emitted = false;

	auto flush = [&]()
	{
		if (currentScoreInfo >= 0 && haveBest && !emitted)
		{
			FasimGasal2SelectedAlignment out;
			out.scoreinfo_index = currentScoreInfo;
			out.cutlength = bestAttempt.cutlength;
			out.start = bestAttempt.start;
			out.selected = true;
			out.alignment = best;
			selected->push_back(out);
		}
		else if (currentScoreInfo >= 0 && haveLast && !emitted && last.sw_score != 0)
		{
			FasimGasal2SelectedAlignment out;
			out.scoreinfo_index = currentScoreInfo;
			out.cutlength = lastAttempt.cutlength;
			out.start = lastAttempt.start;
			out.selected = true;
			out.alignment = last;
			selected->push_back(out);
		}
		haveBest = false;
		haveLast = false;
		emitted = false;
		best.Clear();
		last.Clear();
		bestAttempt = FasimGasal2Attempt();
		lastAttempt = FasimGasal2Attempt();
	};

	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const StripedSmithWaterman::Alignment &alignment = alignments[i];
		if (attempt.scoreinfo_index != currentScoreInfo)
		{
			flush();
			currentScoreInfo = attempt.scoreinfo_index;
		}
		if (!emitted)
		{
			last = alignment;
			lastAttempt = attempt;
			haveLast = true;
		}
		if (!emitted && alignment.sw_score >= attempt.prealign_score)
		{
			FasimGasal2SelectedAlignment out;
			out.scoreinfo_index = attempt.scoreinfo_index;
			out.cutlength = attempt.cutlength;
			out.start = attempt.start;
			out.selected = true;
			out.alignment = alignment;
			selected->push_back(out);
			emitted = true;
			continue;
		}
		if (!emitted &&
		    alignment.sw_score > best.sw_score &&
		    alignment.ref_end == attempt.target_end_required_for_fallback + attempt.start)
		{
			best = alignment;
			bestAttempt = attempt;
			haveBest = true;
		}
	}
	flush();
}

void select_attempts_from_scores(const std::vector<FasimGasal2Attempt> &attempts,
                                 const std::vector<ScoreOnlyResult> &results,
                                 std::vector<size_t> *selectedAttemptIndexes,
                                 std::vector<std::string> *selectionReasons = NULL)
{
	selectedAttemptIndexes->clear();
	if (selectionReasons != NULL)
	{
		selectionReasons->assign(attempts.size(), "not_selected_lower_score");
	}
	const bool ntSumSpanPrune = nt_sum_span_prune_enabled();
	g_stats.nt_sum_span_prune_enabled =
		g_stats.nt_sum_span_prune_enabled || ntSumSpanPrune;
	int currentScoreInfo = -1;
	size_t bestIndex = 0;
	int bestScore = 0;
	bool haveBest = false;
	size_t lastIndex = 0;
	int lastScore = 0;
	bool haveLast = false;
	bool emitted = false;
	bool prunedCurrentGroup = false;
	size_t rankInGroup = 0;

	auto flush = [&]()
	{
		if (currentScoreInfo >= 0 && haveBest && !emitted)
		{
			selectedAttemptIndexes->push_back(bestIndex);
			if (selectionReasons != NULL)
			{
				(*selectionReasons)[bestIndex] = "best_fallback";
			}
			++g_stats.score_prepass_select_best_fallback;
		}
		else if (currentScoreInfo >= 0 && haveLast && !emitted && lastScore != 0)
		{
			selectedAttemptIndexes->push_back(lastIndex);
			if (selectionReasons != NULL)
			{
				(*selectionReasons)[lastIndex] = "last";
			}
			++g_stats.score_prepass_select_last;
		}
		else if (currentScoreInfo >= 0 && !emitted)
		{
			++g_stats.score_prepass_select_none;
		}
		bestIndex = 0;
		bestScore = 0;
		lastIndex = 0;
		lastScore = 0;
		haveBest = false;
		haveLast = false;
		emitted = false;
		if (prunedCurrentGroup)
		{
			++g_stats.nt_sum_span_pruned_groups;
		}
		prunedCurrentGroup = false;
		rankInGroup = 0;
	};

	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const ScoreOnlyResult &result = results[i];
		if (attempt.scoreinfo_index != currentScoreInfo)
		{
			flush();
			currentScoreInfo = attempt.scoreinfo_index;
		}
		++rankInGroup;
		if (ntSumSpanPrune)
		{
			if (attempt_pruned_by_nt_sum_span(attempt, result))
			{
				if (selectionReasons != NULL)
				{
					(*selectionReasons)[i] = "pruned_nt_sum_span";
				}
				++g_stats.nt_sum_span_pruned_attempts;
				prunedCurrentGroup = true;
				continue;
			}
		}
		if (emitted)
		{
			if (selectionReasons != NULL)
			{
				(*selectionReasons)[i] = "not_selected_after_threshold";
			}
			continue;
		}
		if (!emitted)
		{
			lastIndex = i;
			lastScore = result.sw_score;
			haveLast = true;
		}
		if (!emitted && result.sw_score >= attempt.prealign_score)
		{
			selectedAttemptIndexes->push_back(i);
			if (selectionReasons != NULL)
			{
				(*selectionReasons)[i] = "threshold";
			}
			++g_stats.score_prepass_select_threshold;
			if (rankInGroup <= 1)
			{
				++g_stats.score_prepass_threshold_rank1;
			}
			else if (rankInGroup == 2)
			{
				++g_stats.score_prepass_threshold_rank2;
			}
			else if (rankInGroup == 3)
			{
				++g_stats.score_prepass_threshold_rank3;
			}
			else
			{
				++g_stats.score_prepass_threshold_rank4plus;
			}
			emitted = true;
			continue;
		}
		if (!emitted &&
		    result.sw_score > bestScore &&
		    result.ref_end == attempt.target_end_required_for_fallback + attempt.start)
		{
			bestIndex = i;
			bestScore = result.sw_score;
			haveBest = true;
		}
	}
	flush();
	if (selectionReasons != NULL)
	{
		for (size_t i = 0; i < results.size(); ++i)
		{
			if ((*selectionReasons)[i] == "not_selected_lower_score" &&
			    results[i].sw_score == 0)
			{
				(*selectionReasons)[i] = "not_selected_zero_score";
			}
		}
	}
}

bool select_attempts_with_staged_scores(BridgeState *state,
                                        const std::string &query,
                                        const std::vector<FasimGasal2Attempt> &attempts,
                                        int batchSize,
                                        std::vector<size_t> *selectedAttemptIndexes,
                                        std::string *errorOut)
{
	selectedAttemptIndexes->clear();
	const bool ntSumSpanPrune = nt_sum_span_prune_enabled();
	g_stats.nt_sum_span_prune_enabled =
		g_stats.nt_sum_span_prune_enabled || ntSumSpanPrune;
	std::vector<FasimGasal2Attempt> firstAttempts;
	std::vector<size_t> firstMap;
	firstAttempts.reserve(attempts.size() / 4 + 1);
	firstMap.reserve(attempts.size() / 4 + 1);
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (i == 0 || attempts[i].scoreinfo_index != attempts[i - 1].scoreinfo_index)
		{
			firstAttempts.push_back(attempts[i]);
			firstMap.push_back(i);
		}
	}

	std::vector<ScoreOnlyResult> firstResults;
	if (!run_score_only(state, query, firstAttempts, batchSize, &firstResults, errorOut))
	{
		return false;
	}
	g_stats.staged_score_prepass_enabled = true;
	g_stats.staged_score_prepass_first_requests += firstAttempts.size();

	std::vector<size_t> selectedByFirst(firstAttempts.size(), static_cast<size_t>(-1));
	std::vector<FasimGasal2Attempt> remainingAttempts;
	std::vector<size_t> remainingMap;
	std::vector<size_t> unresolvedFirstPositions;
	std::vector<FasimGasal2Attempt> unresolvedFirstAttempts;
	std::vector<ScoreOnlyResult> unresolvedFirstResults;
	std::vector<size_t> unresolvedFirstMap;
	const bool stagedFirstPrune =
		staged_first_prune_enabled_for_mode(env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO"));
	remainingAttempts.reserve(attempts.size() - firstAttempts.size());
	remainingMap.reserve(attempts.size() - firstAttempts.size());
	unresolvedFirstPositions.reserve(firstAttempts.size());
	unresolvedFirstAttempts.reserve(firstAttempts.size());
	unresolvedFirstResults.reserve(firstAttempts.size());
	unresolvedFirstMap.reserve(firstAttempts.size());
	for (size_t first = 0; first < firstAttempts.size(); ++first)
	{
		const FasimGasal2Attempt &attempt = firstAttempts[first];
		const ScoreOnlyResult &result = firstResults[first];
		const size_t originalIndex = firstMap[first];
		size_t next = originalIndex + 1;
		while (next < attempts.size() &&
		       attempts[next].scoreinfo_index == attempt.scoreinfo_index)
		{
			++next;
		}
		const uint64_t skippedRemaining =
			static_cast<uint64_t>(next - originalIndex - 1);
		if (ntSumSpanPrune &&
		    attempt_pruned_by_nt_sum_span(attempt, result))
		{
			++g_stats.nt_sum_span_pruned_attempts;
			++g_stats.nt_sum_span_pruned_groups;
			g_stats.staged_score_prepass_pruned_remaining_requests += skippedRemaining;
			continue;
		}
		if (result.sw_score >= attempt.prealign_score)
		{
			selectedByFirst[first] = originalIndex;
			++g_stats.score_prepass_select_threshold;
			++g_stats.score_prepass_threshold_rank1;
			++g_stats.staged_score_prepass_first_threshold;
			continue;
		}
		if (stagedFirstPrune && result.sw_score == 0)
		{
			++g_stats.score_prepass_select_none;
			++g_stats.staged_score_prepass_pruned_zero_groups;
			g_stats.staged_score_prepass_pruned_remaining_requests += skippedRemaining;
			continue;
		}
		if (stagedFirstPrune &&
		    result.ref_end == attempt.target_end_required_for_fallback + attempt.start)
		{
			selectedByFirst[first] = originalIndex;
			++g_stats.score_prepass_select_best_fallback;
			++g_stats.staged_score_prepass_pruned_best_fallback_groups;
			g_stats.staged_score_prepass_pruned_remaining_requests += skippedRemaining;
			continue;
		}

		unresolvedFirstPositions.push_back(first);
		unresolvedFirstAttempts.push_back(attempt);
		unresolvedFirstResults.push_back(result);
		unresolvedFirstMap.push_back(originalIndex);
		for (size_t remaining = originalIndex + 1; remaining < next; ++remaining)
		{
			remainingAttempts.push_back(attempts[remaining]);
			remainingMap.push_back(remaining);
		}
	}

	if (!remainingAttempts.empty())
	{
		std::vector<ScoreOnlyResult> remainingResults;
		if (!run_score_only(state, query, remainingAttempts, batchSize, &remainingResults, errorOut))
		{
			return false;
		}
		g_stats.staged_score_prepass_remaining_requests += remainingAttempts.size();

		std::vector<FasimGasal2Attempt> fallbackAttempts;
		std::vector<ScoreOnlyResult> fallbackResults;
		std::vector<size_t> fallbackMap;
		fallbackAttempts.reserve(unresolvedFirstAttempts.size() + remainingAttempts.size());
		fallbackResults.reserve(unresolvedFirstResults.size() + remainingResults.size());
		fallbackMap.reserve(unresolvedFirstMap.size() + remainingMap.size());
		size_t remainingIndex = 0;
		for (size_t first = 0; first < unresolvedFirstAttempts.size(); ++first)
		{
			fallbackAttempts.push_back(unresolvedFirstAttempts[first]);
			fallbackResults.push_back(unresolvedFirstResults[first]);
			fallbackMap.push_back(unresolvedFirstMap[first]);
			const int scoreInfoIndex = unresolvedFirstAttempts[first].scoreinfo_index;
			while (remainingIndex < remainingAttempts.size() &&
			       remainingAttempts[remainingIndex].scoreinfo_index == scoreInfoIndex)
			{
				fallbackAttempts.push_back(remainingAttempts[remainingIndex]);
				fallbackResults.push_back(remainingResults[remainingIndex]);
				fallbackMap.push_back(remainingMap[remainingIndex]);
				++remainingIndex;
			}
		}

		std::vector<size_t> fallbackSelected;
		select_attempts_from_scores(fallbackAttempts, fallbackResults, &fallbackSelected);
		size_t unresolvedCursor = 0;
		for (size_t i = 0; i < fallbackSelected.size(); ++i)
		{
			const size_t selectedOriginal = fallbackMap[fallbackSelected[i]];
			const int scoreInfoIndex = attempts[selectedOriginal].scoreinfo_index;
			while (unresolvedCursor < unresolvedFirstPositions.size() &&
			       firstAttempts[unresolvedFirstPositions[unresolvedCursor]].scoreinfo_index < scoreInfoIndex)
			{
				++unresolvedCursor;
			}
			if (unresolvedCursor < unresolvedFirstPositions.size() &&
			    firstAttempts[unresolvedFirstPositions[unresolvedCursor]].scoreinfo_index == scoreInfoIndex)
			{
				selectedByFirst[unresolvedFirstPositions[unresolvedCursor]] = selectedOriginal;
				++unresolvedCursor;
			}
		}
	}
	for (size_t i = 0; i < selectedByFirst.size(); ++i)
	{
		if (selectedByFirst[i] != static_cast<size_t>(-1))
		{
			selectedAttemptIndexes->push_back(selectedByFirst[i]);
		}
	}
	return true;
}

void select_cpu_traceback_candidates_from_scores(const std::vector<FasimGasal2Attempt> &attempts,
                                                 const std::vector<ScoreOnlyResult> &results,
                                                 int scoreMargin,
                                                 bool includeLast,
                                                 bool includeFallback,
                                                 std::vector<size_t> *selectedAttemptIndexes)
{
	selectedAttemptIndexes->clear();
	int currentScoreInfo = -1;
	size_t lastIndex = 0;
	int lastScore = 0;
	bool haveLast = false;
	uint64_t thresholdCandidateCount = 0;
	uint64_t fallbackCandidateCount = 0;
	uint64_t lastCandidateCount = 0;

	auto flush = [&]()
	{
		if (includeLast && currentScoreInfo >= 0 && haveLast && lastScore != 0)
		{
			if (selectedAttemptIndexes->empty() || selectedAttemptIndexes->back() != lastIndex)
			{
				selectedAttemptIndexes->push_back(lastIndex);
				++lastCandidateCount;
			}
		}
		lastIndex = 0;
		lastScore = 0;
		haveLast = false;
	};

	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const ScoreOnlyResult &result = results[i];
		if (attempt.scoreinfo_index != currentScoreInfo)
		{
			flush();
			currentScoreInfo = attempt.scoreinfo_index;
		}

		const bool thresholdCandidate = result.sw_score + scoreMargin >= attempt.prealign_score;
		const bool fallbackCandidate = result.sw_score != 0 &&
		                               result.ref_end == attempt.target_end_required_for_fallback + attempt.start;
		if (thresholdCandidate || (includeFallback && fallbackCandidate))
		{
			selectedAttemptIndexes->push_back(i);
			if (thresholdCandidate)
			{
				++thresholdCandidateCount;
			}
			if (includeFallback && fallbackCandidate)
			{
				++fallbackCandidateCount;
			}
		}

		lastIndex = i;
		lastScore = result.sw_score;
		haveLast = true;
	}
	flush();
	g_stats.cpu_traceback_candidate_threshold += thresholdCandidateCount;
	g_stats.cpu_traceback_candidate_fallback += fallbackCandidateCount;
	g_stats.cpu_traceback_candidate_last += lastCandidateCount;
}

void export_limited_traceback_attempts(const std::vector<FasimGasal2Attempt> &attempts,
                                       const std::vector<size_t> &selectedAttemptIndexes,
                                       const std::vector<unsigned char> &keep)
{
	const std::string path = limited_traceback_attempt_export_path();
	if (path.empty())
	{
		return;
	}
	const bool needsHeader = !file_exists(path);
	std::ofstream output(path.c_str(), std::ios::out | std::ios::app);
	if (!output)
	{
		return;
	}
	if (needsHeader)
	{
		output
			<< "batch_id\tposition\tattempt_index\tdecision\tprealign_score\t"
			<< "scoreinfo_index\tstart\tcutlength\ttarget_size\tnt_min_length\t"
			<< "target_end_required_for_fallback\ttarget_offset\ttarget_length\t"
			<< "target_global_start\ttarget_global_end\t"
			<< "output_global_start\toutput_global_end\t"
			<< "task_strand\ttask_para\ttask_rule\n";
	}
	const uint64_t batchId = g_limited_traceback_export_batch_id++;
	for (size_t position = 0; position < selectedAttemptIndexes.size(); ++position)
	{
		const size_t attemptIndex = selectedAttemptIndexes[position];
		if (attemptIndex >= attempts.size())
		{
			continue;
		}
		const FasimGasal2Attempt &attempt = attempts[attemptIndex];
		output
			<< batchId << "\t"
			<< position << "\t"
			<< attemptIndex << "\t"
			<< (position < keep.size() && keep[position] != 0 ? "keep" : "skip") << "\t"
			<< attempt.prealign_score << "\t"
			<< attempt.scoreinfo_index << "\t"
			<< attempt.start << "\t"
			<< attempt.cutlength << "\t"
			<< attempt.target_size() << "\t"
			<< attempt.nt_min_length << "\t"
			<< attempt.target_end_required_for_fallback << "\t"
			<< attempt.target_offset << "\t"
			<< attempt.target_length << "\t"
			<< attempt.target_global_start << "\t"
			<< (attempt.target_global_start >= 0 ?
				    attempt.target_global_start + static_cast<int64_t>(attempt.target_size()) :
				    static_cast<int64_t>(-1)) << "\t"
			<< attempt.output_global_start << "\t"
			<< attempt.output_global_end << "\t"
			<< attempt.task_strand << "\t"
			<< attempt.task_para << "\t"
			<< attempt.task_rule << "\n";
		++g_stats.limited_traceback_attempt_export_rows;
	}
}

void apply_limited_traceback_scoreinfo_cap(const std::vector<FasimGasal2Attempt> &attempts,
                                           int maxScoreInfos,
                                           std::vector<size_t> *selectedAttemptIndexes)
{
	const int minPrealignScore = limited_traceback_min_prealign_score();
	const int guardMinPrealignScore = limited_traceback_guard_min_prealign_score();
	const int guardMaxPrealignScore = limited_traceback_guard_max_prealign_score();
	const int guardMaxTargetSize = limited_traceback_guard_max_target_size();
	if (selectedAttemptIndexes == NULL || (maxScoreInfos <= 0 && minPrealignScore <= 0))
	{
		return;
	}
	g_stats.limited_traceback_enabled = true;
	g_stats.limited_traceback_max_scoreinfos =
		maxScoreInfos > 0 ? static_cast<uint64_t>(maxScoreInfos) : 0;
	g_stats.limited_traceback_min_prealign_score =
		minPrealignScore > 0 ? static_cast<uint64_t>(minPrealignScore) : 0;
	g_stats.limited_traceback_guard_min_prealign_score =
		guardMinPrealignScore > 0 ? static_cast<uint64_t>(guardMinPrealignScore) : 0;
	g_stats.limited_traceback_guard_max_prealign_score =
		guardMaxPrealignScore > 0 ? static_cast<uint64_t>(guardMaxPrealignScore) : 0;
	g_stats.limited_traceback_guard_max_target_size =
		guardMaxTargetSize > 0 ? static_cast<uint64_t>(guardMaxTargetSize) : 0;
	const size_t before = selectedAttemptIndexes->size();
	g_stats.limited_traceback_before += static_cast<uint64_t>(before);
	std::vector<unsigned char> keep(before, 1);

	if (maxScoreInfos > 0 && before > static_cast<size_t>(maxScoreInfos))
	{
		const std::string mode = limited_traceback_mode();
		std::vector<size_t> order(before);
		for (size_t i = 0; i < before; ++i)
		{
			order[i] = i;
		}
		std::sort(order.begin(),
		          order.end(),
		          [&](size_t lhs, size_t rhs)
		          {
			          const size_t lhsAttemptIndex = (*selectedAttemptIndexes)[lhs];
			          const size_t rhsAttemptIndex = (*selectedAttemptIndexes)[rhs];
			          const FasimGasal2Attempt &a = attempts[lhsAttemptIndex];
			          const FasimGasal2Attempt &b = attempts[rhsAttemptIndex];
			          if (a.prealign_score != b.prealign_score)
			          {
				          return a.prealign_score > b.prealign_score;
			          }
			          if (a.scoreinfo_index != b.scoreinfo_index)
			          {
				          return a.scoreinfo_index < b.scoreinfo_index;
			          }
			          if (a.start != b.start)
			          {
				          return a.start < b.start;
			          }
			          return a.cutlength < b.cutlength;
		          });

		const size_t limit = static_cast<size_t>(maxScoreInfos);
		if (mode == "score_spread")
		{
			std::vector<unsigned char> selected(before, 0);
			std::vector<size_t> selectedOrder;
			selectedOrder.reserve(limit);
			auto add_position = [&](size_t position)
			{
				if (position >= before || selected[position] != 0 || selectedOrder.size() >= limit)
				{
					return false;
				}
				selected[position] = 1;
				selectedOrder.push_back(position);
				return true;
			};

			const size_t scoreQuota = std::max<size_t>(1, limit / 2);
			for (size_t i = 0; i < order.size() && i < scoreQuota; ++i)
			{
				add_position(order[i]);
			}
			const size_t spreadSlots = limit - selectedOrder.size();
			if (spreadSlots > 0)
			{
				for (size_t slot = 0; slot < spreadSlots && selectedOrder.size() < limit; ++slot)
				{
					const size_t denom = spreadSlots > 1 ? spreadSlots - 1 : 1;
					const size_t target =
						spreadSlots > 1 ?
							(slot * (before - 1) + denom / 2) / denom :
							before / 2;
					for (size_t radius = 0; radius < before; ++radius)
					{
						bool added = false;
						if (target >= radius)
						{
							added = add_position(target - radius);
						}
						if (!added && target + radius < before)
						{
							added = add_position(target + radius);
						}
						if (added)
						{
							break;
						}
					}
				}
			}
			for (size_t i = 0; i < order.size() && selectedOrder.size() < limit; ++i)
			{
				add_position(order[i]);
			}
			order.swap(selectedOrder);
		}
		else
		{
			order.resize(limit);
		}
		std::sort(order.begin(), order.end());

		std::fill(keep.begin(), keep.end(), 0);
		for (size_t i = 0; i < order.size(); ++i)
		{
			if (order[i] < keep.size())
			{
				keep[order[i]] = 1;
			}
		}
	}

	uint64_t minPrealignScoreSkipped = 0;
	uint64_t guardKept = 0;
	if (minPrealignScore > 0)
	{
		for (size_t position = 0; position < selectedAttemptIndexes->size(); ++position)
		{
			const size_t attemptIndex = (*selectedAttemptIndexes)[position];
			if (position < keep.size() && keep[position] != 0 &&
			    attemptIndex < attempts.size() &&
			    attempts[attemptIndex].prealign_score < minPrealignScore)
			{
				const FasimGasal2Attempt &attempt = attempts[attemptIndex];
				const bool guarded =
					guardMinPrealignScore > 0 &&
					guardMaxTargetSize > 0 &&
					attempt.prealign_score >= guardMinPrealignScore &&
					(guardMaxPrealignScore <= 0 ||
					 attempt.prealign_score <= guardMaxPrealignScore) &&
					attempt.target_size() <= static_cast<size_t>(guardMaxTargetSize);
				if (guarded)
				{
					++guardKept;
				}
				else
				{
					keep[position] = 0;
					++minPrealignScoreSkipped;
				}
			}
		}
	}
	g_stats.limited_traceback_min_prealign_score_skipped += minPrealignScoreSkipped;
	g_stats.limited_traceback_guard_kept += guardKept;
	export_limited_traceback_attempts(attempts, *selectedAttemptIndexes, keep);

	std::vector<size_t> limited;
	limited.reserve(before);
	for (size_t position = 0; position < selectedAttemptIndexes->size(); ++position)
	{
		if (position < keep.size() && keep[position] != 0)
		{
			limited.push_back((*selectedAttemptIndexes)[position]);
		}
	}
	selectedAttemptIndexes->swap(limited);
	g_stats.limited_traceback_after += static_cast<uint64_t>(selectedAttemptIndexes->size());
	g_stats.limited_traceback_skipped +=
		static_cast<uint64_t>(before - selectedAttemptIndexes->size());
}

bool run_score_only(BridgeState *state,
                    const std::string &query,
                    const std::vector<FasimGasal2Attempt> &attempts,
                    int batchSize,
                    std::vector<ScoreOnlyResult> *results,
                    std::string *errorOut)
{
	int maxTargetLen = 0;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		maxTargetLen = std::max(maxTargetLen, static_cast<int>(attempt_target_size(attempts[i])));
	}
	if (!check_length_guard("score", query.size(), static_cast<size_t>(maxTargetLen), errorOut))
	{
		return false;
	}
	const int allocAlns = std::max(batchSize, static_cast<int>(attempts.size() < static_cast<size_t>(batchSize) ? attempts.size() : static_cast<size_t>(batchSize)));
	if (!ensure_state(state,
	                  GasalMode::ScoreOnly,
	                  static_cast<int>(query.size()),
	                  maxTargetLen,
	                  allocAlns,
	                  errorOut))
	{
		return false;
	}

	results->assign(attempts.size(), ScoreOnlyResult());
	std::vector<uint32_t> streamCounts(static_cast<size_t>(state->storage.n), 0);
	std::vector<size_t> streamStarts(static_cast<size_t>(state->storage.n), 0);
	std::vector<uint8_t> zeroOps(static_cast<size_t>(batchSize), 0);

	size_t next = 0;
	while (next < attempts.size())
	{
		bool launchedThisRound = false;
		for (int s = 0; s < state->storage.n && next < attempts.size(); ++s)
		{
			gasal_gpu_storage_t *storage = &state->storage.a[s];
			if (storage->is_free != 1)
			{
				continue;
			}
			const auto fillStart = std::chrono::steady_clock::now();
			uint32_t queryOffset = 0;
			uint32_t targetOffset = 0;
			uint64_t filledQueryBytes = 0;
			uint64_t filledTargetBytes = 0;
			uint32_t j = 0;
			const size_t batchStart = next;
			const bool reuseQuery = fasim_gasal2_longtarget_bridge_enabled();
			storage->use_cigar_offsets = 0;
			if (reuseQuery)
			{
				queryOffset = gasal_host_batch_fill(storage,
				                                    0,
				                                    query.c_str(),
				                                    static_cast<uint32_t>(query.size()),
				                                    QUERY);
				filledQueryBytes += query.size();
			}
			storage->current_n_alns = 0;
			while (next < attempts.size() && j < static_cast<uint32_t>(batchSize))
			{
				const size_t targetSize = attempt_target_size(attempts[next]);
				storage->host_query_batch_offsets[j] = reuseQuery ? 0 : queryOffset;
				storage->host_target_batch_offsets[j] = targetOffset;
				storage->host_query_batch_lens[j] = static_cast<uint32_t>(query.size());
				storage->host_target_batch_lens[j] = static_cast<uint32_t>(targetSize);
				if (!reuseQuery)
				{
					queryOffset = gasal_host_batch_fill(storage,
					                                    queryOffset,
					                                    query.c_str(),
					                                    static_cast<uint32_t>(query.size()),
					                                    QUERY);
					filledQueryBytes += query.size();
				}
				targetOffset = gasal_host_batch_fill(storage,
				                                     targetOffset,
				                                     attempt_target_data(attempts[next]),
				                                     static_cast<uint32_t>(targetSize),
				                                     TARGET);
				filledTargetBytes += targetSize;
				++storage->current_n_alns;
				++j;
				++next;
			}
			if (reuseQuery && j > 0)
			{
				++g_stats.score_query_reuse_batches;
				g_stats.score_query_reuse_saved_bytes += static_cast<uint64_t>(j - 1) * query.size();
			}
			g_stats.score_query_bytes += filledQueryBytes;
			g_stats.score_target_bytes += filledTargetBytes;
			gasal_op_fill(storage, zeroOps.data(), j, QUERY);
			gasal_op_fill(storage, zeroOps.data(), j, TARGET);
			const double fillSeconds = seconds_since(fillStart);
			g_stats.fill_seconds += fillSeconds;
			g_stats.score_fill_seconds += fillSeconds;

			const auto submitStart = std::chrono::steady_clock::now();
			gasal_aln_async(storage, queryOffset, targetOffset, j, state->params);
			const double submitSeconds = seconds_since(submitStart);
			g_stats.submit_seconds += submitSeconds;
			g_stats.score_submit_seconds += submitSeconds;
			streamCounts[static_cast<size_t>(s)] = j;
			streamStarts[static_cast<size_t>(s)] = batchStart;
			++g_stats.batches;
			++g_stats.score_batches;
			g_stats.requests += j;
			g_stats.score_requests += j;
			launchedThisRound = true;
		}
		if (!launchedThisRound)
		{
			const double copyBefore = g_stats.score_result_copy_seconds;
			const auto waitStart = std::chrono::steady_clock::now();
			wait_for_all_score(state, streamCounts, streamStarts, attempts, *results, errorOut);
			const double waited = seconds_since(waitStart);
			g_stats.wait_seconds += waited;
			g_stats.score_wait_seconds += waited;
			const double copyDelta = g_stats.score_result_copy_seconds - copyBefore;
			if (waited > copyDelta)
			{
				g_stats.score_poll_wait_seconds += waited - copyDelta;
			}
		}
	}
	const double copyBefore = g_stats.score_result_copy_seconds;
	const auto waitStart = std::chrono::steady_clock::now();
	wait_for_all_score(state, streamCounts, streamStarts, attempts, *results, errorOut);
	const double waited = seconds_since(waitStart);
	g_stats.wait_seconds += waited;
	g_stats.score_wait_seconds += waited;
	const double copyDelta = g_stats.score_result_copy_seconds - copyBefore;
	if (waited > copyDelta)
	{
		g_stats.score_poll_wait_seconds += waited - copyDelta;
	}
	return true;
}

bool run_traceback(BridgeState *state,
                   const std::string &query,
                   const std::vector<FasimGasal2Attempt> &attempts,
                   int batchSize,
                   std::vector<StripedSmithWaterman::Alignment> *alignments,
                   std::string *errorOut)
{
	int maxTargetLen = 0;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		maxTargetLen = std::max(maxTargetLen, static_cast<int>(attempt_target_size(attempts[i])));
	}
	if (!check_length_guard("traceback", query.size(), static_cast<size_t>(maxTargetLen), errorOut))
	{
		return false;
	}
	const int allocAlns = std::max(batchSize, static_cast<int>(attempts.size() < static_cast<size_t>(batchSize) ? attempts.size() : static_cast<size_t>(batchSize)));
	if (!ensure_state(state,
	                  GasalMode::Traceback,
	                  static_cast<int>(query.size()),
	                  maxTargetLen,
	                  allocAlns,
	                  errorOut))
	{
		return false;
	}

	alignments->assign(attempts.size(), StripedSmithWaterman::Alignment());
	std::vector<uint32_t> streamCounts(static_cast<size_t>(state->storage.n), 0);
	std::vector<size_t> streamStarts(static_cast<size_t>(state->storage.n), 0);
	std::vector<uint8_t> zeroOps(static_cast<size_t>(batchSize), 0);

	size_t next = 0;
	while (next < attempts.size())
	{
		bool launchedThisRound = false;
		for (int s = 0; s < state->storage.n && next < attempts.size(); ++s)
		{
			gasal_gpu_storage_t *storage = &state->storage.a[s];
			if (storage->is_free != 1)
			{
				continue;
			}
			const auto fillStart = std::chrono::steady_clock::now();
			uint32_t queryOffset = 0;
			uint32_t targetOffset = 0;
			uint32_t cigarOffset = 0;
			const uint32_t cigarStride = gasal_padded_bytes(query.size());
			uint64_t filledQueryBytes = 0;
			uint64_t filledTargetBytes = 0;
			uint32_t j = 0;
			const size_t batchStart = next;
			const bool reuseQuery = traceback_query_reuse_enabled_for_mode(
				env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO"));
			storage->use_cigar_offsets = reuseQuery ? 1 : 0;
			if (reuseQuery)
			{
				queryOffset = gasal_host_batch_fill(storage,
				                                    0,
				                                    query.c_str(),
				                                    static_cast<uint32_t>(query.size()),
				                                    QUERY);
				filledQueryBytes += query.size();
			}
			storage->current_n_alns = 0;
			while (next < attempts.size() && j < static_cast<uint32_t>(batchSize))
			{
					const size_t targetSize = attempt_target_size(attempts[next]);
					storage->host_query_batch_offsets[j] = reuseQuery ? 0 : queryOffset;
					storage->host_target_batch_offsets[j] = targetOffset;
					storage->host_cigar_offsets[j] = cigarOffset;
					storage->host_query_batch_lens[j] = static_cast<uint32_t>(query.size());
					storage->host_target_batch_lens[j] = static_cast<uint32_t>(targetSize);
					if (!reuseQuery)
					{
						queryOffset = gasal_host_batch_fill(storage,
						                                    queryOffset,
						                                    query.c_str(),
						                                    static_cast<uint32_t>(query.size()),
						                                    QUERY);
						filledQueryBytes += query.size();
					}
					cigarOffset += cigarStride;
					targetOffset = gasal_host_batch_fill(storage,
					                                     targetOffset,
					                                     attempt_target_data(attempts[next]),
					                                     static_cast<uint32_t>(targetSize),
					                                     TARGET);
					filledTargetBytes += targetSize;
				++storage->current_n_alns;
				++j;
				++next;
			}
			g_stats.traceback_query_bytes += filledQueryBytes;
			g_stats.traceback_target_bytes += filledTargetBytes;
			if (j > 0)
			{
				const uint64_t savedBytes = static_cast<uint64_t>(j - 1) * query.size();
				g_stats.traceback_query_reuse_potential_saved_bytes += savedBytes;
				if (reuseQuery)
				{
					g_stats.traceback_query_reuse_saved_bytes += savedBytes;
				}
			}
			gasal_op_fill(storage, zeroOps.data(), j, QUERY);
			gasal_op_fill(storage, zeroOps.data(), j, TARGET);
			const double fillSeconds = seconds_since(fillStart);
			g_stats.fill_seconds += fillSeconds;
			g_stats.traceback_fill_seconds += fillSeconds;

			const auto submitStart = std::chrono::steady_clock::now();
			gasal_aln_async(storage, queryOffset, targetOffset, j, state->params);
			const double submitSeconds = seconds_since(submitStart);
			g_stats.submit_seconds += submitSeconds;
			g_stats.traceback_submit_seconds += submitSeconds;
			streamCounts[static_cast<size_t>(s)] = j;
			streamStarts[static_cast<size_t>(s)] = batchStart;
			++g_stats.batches;
			++g_stats.traceback_batches;
			g_stats.requests += j;
			g_stats.traceback_requests += j;
			launchedThisRound = true;
		}
		if (!launchedThisRound)
		{
			const double copyBefore = g_stats.traceback_result_copy_seconds;
			const auto waitStart = std::chrono::steady_clock::now();
			wait_for_all_traceback(state, streamCounts, streamStarts, attempts, *alignments, errorOut);
			const double waited = seconds_since(waitStart);
			g_stats.wait_seconds += waited;
			g_stats.traceback_wait_seconds += waited;
			const double copyDelta =
				g_stats.traceback_result_copy_seconds - copyBefore;
			if (waited > copyDelta)
			{
				g_stats.traceback_poll_wait_seconds += waited - copyDelta;
			}
		}
	}
	const double copyBefore = g_stats.traceback_result_copy_seconds;
	const auto waitStart = std::chrono::steady_clock::now();
	wait_for_all_traceback(state, streamCounts, streamStarts, attempts, *alignments, errorOut);
	const double waited = seconds_since(waitStart);
	g_stats.wait_seconds += waited;
	g_stats.traceback_wait_seconds += waited;
	const double copyDelta =
		g_stats.traceback_result_copy_seconds - copyBefore;
	if (waited > copyDelta)
	{
		g_stats.traceback_poll_wait_seconds += waited - copyDelta;
	}
	return true;
}

}  // namespace

bool fasim_gasal2_is_built()
{
	return true;
}

bool fasim_gasal2_enabled()
{
	return env_enabled("FASIM_ALIGN_GASAL2") ||
	       env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO") ||
	       env_enabled("FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW") ||
	       env_enabled("FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_V1") ||
	       env_enabled("FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE") ||
	       env_enabled("FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
}

bool fasim_gasal2_longtarget_bridge_enabled()
{
	return env_enabled("FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE") ||
	       env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO") ||
	       env_enabled("FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_V1") ||
	       env_enabled("FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE") ||
	       env_enabled("FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW") ||
	       env_enabled("FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER");
}

bool fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE");
}

bool fasim_gasal2_phase7_v5_cpu_authority_replay_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY");
}

bool fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY");
}

bool fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY");
}

bool fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE");
}

bool fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_CERTIFICATE_CUDA_API");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE");
}

bool fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime()
{
	return env_enabled(
		"FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime()
{
	return env_enabled(
		"FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_upper_bound_reject_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW");
}

bool fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW");
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
	std::lock_guard<std::mutex> lock(g_mutex);
	FasimGasal2Stats stats = g_stats;
	stats.enabled = fasim_gasal2_enabled();
	stats.built = true;
	return stats;
}

void fasim_gasal2_print_stats()
{
	const FasimGasal2Stats stats = fasim_gasal2_snapshot_stats();
	const bool top5Preset = env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
	std::cerr << "benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested=" << (top5Preset ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active=" << (top5Preset && stats.built ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_enabled=" << (stats.enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_built=1\n";
	std::cerr << "benchmark.fasim_gasal2_requests=" << stats.requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_batches=" << stats.batches << "\n";
	std::cerr << "benchmark.fasim_gasal2_fallbacks=" << stats.fallbacks << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_requests=" << stats.score_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_batches=" << stats.score_batches << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_requests=" << stats.traceback_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_batches=" << stats.traceback_batches << "\n";
	std::cerr << "benchmark.fasim_gasal2_target_view_requests=" << stats.target_view_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_query_reuse_batches=" << stats.score_query_reuse_batches << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_query_reuse_saved_bytes=" << stats.score_query_reuse_saved_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_query_bytes=" << stats.score_query_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_target_bytes=" << stats.score_target_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_query_bytes=" << stats.traceback_query_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_target_bytes=" << stats.traceback_target_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_query_reuse_saved_bytes=" << stats.traceback_query_reuse_saved_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_query_reuse_potential_saved_bytes=" << stats.traceback_query_reuse_potential_saved_bytes << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_selected_attempts=" << stats.score_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_threshold=" << stats.score_prepass_select_threshold << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_best_fallback=" << stats.score_prepass_select_best_fallback << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_last=" << stats.score_prepass_select_last << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_select_none=" << stats.score_prepass_select_none << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank1=" << stats.score_prepass_threshold_rank1 << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank2=" << stats.score_prepass_threshold_rank2 << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank3=" << stats.score_prepass_threshold_rank3 << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_threshold_rank4plus=" << stats.score_prepass_threshold_rank4plus << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_enabled=" << (stats.staged_score_prepass_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_first_requests=" << stats.staged_score_prepass_first_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_remaining_requests=" << stats.staged_score_prepass_remaining_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_first_threshold=" << stats.staged_score_prepass_first_threshold << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_pruned_zero_groups=" << stats.staged_score_prepass_pruned_zero_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_pruned_best_fallback_groups=" << stats.staged_score_prepass_pruned_best_fallback_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_staged_score_prepass_pruned_remaining_requests=" << stats.staged_score_prepass_pruned_remaining_requests << "\n";
	std::cerr << "benchmark.fasim_gasal2_nt_sum_span_prune_enabled=" << (stats.nt_sum_span_prune_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_nt_sum_span_pruned_attempts=" << stats.nt_sum_span_pruned_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_nt_sum_span_pruned_groups=" << stats.nt_sum_span_pruned_groups << "\n";
	const char *certificatePrefix =
		"benchmark.fasim_gasal2_traceback_certificate_shadow_";
	std::cerr << certificatePrefix << "requested="
	          << (stats.traceback_certificate_shadow_requested ? 1 : 0) << "\n";
	std::cerr << certificatePrefix << "active="
	          << (stats.traceback_certificate_shadow_active ? 1 : 0) << "\n";
	std::cerr << certificatePrefix << "real_skip_enabled="
	          << (stats.traceback_certificate_real_skip_enabled ? 1 : 0) << "\n";
	std::cerr << certificatePrefix << "pre_drop_proof_available="
	          << (stats.traceback_certificate_pre_drop_proof_available ? 1 : 0)
	          << "\n";
	std::cerr << certificatePrefix << "proof_version=phase6_exact_v1\n";
	std::cerr << certificatePrefix << "candidates_considered="
	          << stats.traceback_certificate_candidates_considered << "\n";
	std::cerr << certificatePrefix << "certified_skips="
	          << stats.traceback_certificate_certified_skips << "\n";
	std::cerr << certificatePrefix << "uncertified_candidates="
	          << stats.traceback_certificate_uncertified_candidates << "\n";
	std::cerr << certificatePrefix << "exact_descriptor_duplicate_skips="
	          << stats.traceback_certificate_exact_descriptor_duplicate_skips
	          << "\n";
	std::cerr << certificatePrefix << "static_span_skips="
	          << stats.traceback_certificate_static_span_skips << "\n";
	std::cerr << certificatePrefix << "score_endpoint_span_skips="
	          << stats.traceback_certificate_score_endpoint_span_skips << "\n";
	std::cerr << certificatePrefix << "shadow_false_rejects="
	          << stats.traceback_certificate_shadow_false_rejects << "\n";
	std::cerr << certificatePrefix << "score_frontier_skips="
	          << stats.traceback_certificate_score_frontier_skips << "\n";
	std::cerr << certificatePrefix << "stability_frontier_skips="
	          << stats.traceback_certificate_stability_frontier_skips << "\n";
	std::cerr << certificatePrefix << "nt_frontier_skips="
	          << stats.traceback_certificate_nt_frontier_skips << "\n";
	std::cerr << certificatePrefix << "tie_rescues="
	          << stats.traceback_certificate_tie_rescues << "\n";
	std::cerr << certificatePrefix << "rank_aware_supported="
	          << (stats.traceback_certificate_rank_aware_supported ? 1 : 0) << "\n";
	std::cerr << certificatePrefix << "probe_requests="
	          << stats.traceback_certificate_probe_requests << "\n";
	std::cerr << certificatePrefix << "probe_seconds="
	          << stats.traceback_certificate_probe_seconds << "\n";
	std::cerr << certificatePrefix << "fallbacks="
	          << stats.traceback_certificate_fallbacks << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_enabled=" << (stats.limited_traceback_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_max_scoreinfos=" << stats.limited_traceback_max_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_min_prealign_score=" << stats.limited_traceback_min_prealign_score << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_guard_min_prealign_score=" << stats.limited_traceback_guard_min_prealign_score << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_guard_max_prealign_score=" << stats.limited_traceback_guard_max_prealign_score << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_guard_max_target_size=" << stats.limited_traceback_guard_max_target_size << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_mode=" << limited_traceback_mode() << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_before=" << stats.limited_traceback_before << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_after=" << stats.limited_traceback_after << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_skipped=" << stats.limited_traceback_skipped << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_min_prealign_score_skipped=" << stats.limited_traceback_min_prealign_score_skipped << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_guard_kept=" << stats.limited_traceback_guard_kept << "\n";
	std::cerr << "benchmark.fasim_gasal2_limited_traceback_attempt_export_rows=" << stats.limited_traceback_attempt_export_rows << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_replay_attempts=" << stats.cpu_traceback_replay_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_selected_attempts=" << stats.cpu_traceback_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_align_calls=" << stats.cpu_traceback_align_calls << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_skipped_after_emit=" << stats.cpu_traceback_skipped_after_emit << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_rank_cutoff_skipped=" << stats.cpu_traceback_rank_cutoff_skipped << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_threshold=" << stats.cpu_traceback_emit_threshold << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_best_fallback=" << stats.cpu_traceback_emit_best_fallback << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_last=" << stats.cpu_traceback_emit_last << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_threshold=" << stats.cpu_traceback_candidate_threshold << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_fallback=" << stats.cpu_traceback_candidate_fallback << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_candidate_last=" << stats.cpu_traceback_candidate_last << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank1=" << stats.cpu_traceback_emit_rank1 << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank2=" << stats.cpu_traceback_emit_rank2 << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank3=" << stats.cpu_traceback_emit_rank3 << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_emit_rank4plus=" << stats.cpu_traceback_emit_rank4plus << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=" << stats.attempt_consumer_shadow_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_active=" << stats.attempt_consumer_shadow_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_decision=" << stats.attempt_consumer_shadow_decision << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_tasks=" << stats.attempt_consumer_shadow_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_scoreinfos=" << stats.attempt_consumer_shadow_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_attempts=" << stats.attempt_consumer_shadow_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_score_seconds=" << stats.attempt_consumer_shadow_score_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_select_seconds=" << stats.attempt_consumer_shadow_select_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts=" << stats.attempt_consumer_shadow_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts=" << stats.attempt_consumer_shadow_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_seconds=" << stats.attempt_consumer_shadow_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_convert_seconds=" << stats.attempt_consumer_shadow_convert_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_total_seconds=" << stats.attempt_consumer_shadow_total_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_triplex_mismatches=" << stats.attempt_consumer_shadow_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_missing_triplexes=" << stats.attempt_consumer_shadow_missing_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_extra_triplexes=" << stats.attempt_consumer_shadow_extra_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_first_mismatch=" << stats.attempt_consumer_shadow_first_mismatch << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_fallbacks=" << stats.attempt_consumer_shadow_fallbacks << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_digest_match=" << stats.attempt_consumer_shadow_digest_match << "\n";
	std::cerr << "benchmark.fasim_gasal2_attempt_consumer_shadow_full_rows_equal=" << stats.attempt_consumer_shadow_full_rows_equal << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_requested=" << stats.emission_only_consumer_shadow_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_active=" << stats.emission_only_consumer_shadow_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_decision=" << stats.emission_only_consumer_shadow_decision << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_tasks=" << stats.emission_only_consumer_shadow_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_scoreinfos=" << stats.emission_only_consumer_shadow_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_scored_attempts=" << stats.emission_only_consumer_shadow_scored_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_threshold_emits=" << stats.emission_only_consumer_shadow_threshold_emits << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_terminal_emits=" << stats.emission_only_consumer_shadow_terminal_emits << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_last_emits=" << stats.emission_only_consumer_shadow_last_emits << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_empty_emits=" << stats.emission_only_consumer_shadow_empty_emits << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_attempts=" << stats.emission_only_consumer_shadow_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_realpath_reference_align_attempts=" << stats.emission_only_consumer_shadow_realpath_reference_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_align_attempt_reduction=" << stats.emission_only_consumer_shadow_align_attempt_reduction << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_score_seconds=" << stats.emission_only_consumer_shadow_score_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_select_seconds=" << stats.emission_only_consumer_shadow_select_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_seconds=" << stats.emission_only_consumer_shadow_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_convert_seconds=" << stats.emission_only_consumer_shadow_convert_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_total_seconds=" << stats.emission_only_consumer_shadow_total_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_triplex_mismatches=" << stats.emission_only_consumer_shadow_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_missing_triplexes=" << stats.emission_only_consumer_shadow_missing_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_extra_triplexes=" << stats.emission_only_consumer_shadow_extra_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_first_mismatch=" << stats.emission_only_consumer_shadow_first_mismatch << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_fallbacks=" << stats.emission_only_consumer_shadow_fallbacks << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_digest_match=" << stats.emission_only_consumer_shadow_digest_match << "\n";
	std::cerr << "benchmark.fasim_gasal2_emission_only_consumer_shadow_full_rows_equal=" << stats.emission_only_consumer_shadow_full_rows_equal << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_requested=" << stats.phase7_next_reducer_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_active=" << stats.phase7_next_reducer_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_tasks=" << stats.phase7_next_reducer_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_scoreinfos=" << stats.phase7_next_reducer_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_reference_attempts=" << stats.phase7_next_reducer_reference_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_attempts=" << stats.phase7_next_reducer_candidate_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_align_attempts=" << stats.phase7_next_reducer_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_reference_align_attempts=" << stats.phase7_next_reducer_reference_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_false_negative_scoreinfos=" << stats.phase7_next_reducer_false_negative_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_triplex_mismatches=" << stats.phase7_next_reducer_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_missing_triplexes=" << stats.phase7_next_reducer_missing_triplexes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_extra_triplexes=" << stats.phase7_next_reducer_extra_triplexes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_digest_match=" << stats.phase7_next_reducer_digest_match << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_full_rows_equal=" << stats.phase7_next_reducer_full_rows_equal << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_baseline_wall_seconds=" << stats.phase7_next_reducer_baseline_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_wall_seconds=" << stats.phase7_next_reducer_candidate_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_candidate_vs_baseline=" << stats.phase7_next_reducer_candidate_vs_baseline << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_requested=" << stats.phase7_frontier_log_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_active=" << stats.phase7_frontier_log_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_tasks=" << stats.phase7_frontier_log_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_scoreinfos=" << stats.phase7_frontier_log_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_align_attempts=" << stats.phase7_frontier_log_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_triplexes=" << stats.phase7_frontier_log_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_path=" << stats.phase7_frontier_log_path << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_log_digest=" << stats.phase7_frontier_log_digest << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_requested=" << stats.phase7_frontier_early_stop_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_active=" << stats.phase7_frontier_early_stop_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_tasks=" << stats.phase7_frontier_early_stop_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_scoreinfos=" << stats.phase7_frontier_early_stop_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_reference_align_attempts=" << stats.phase7_frontier_early_stop_reference_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_candidate_align_attempts=" << stats.phase7_frontier_early_stop_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_skipped_attempts=" << stats.phase7_frontier_early_stop_skipped_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_emitted_groups=" << stats.phase7_frontier_early_stop_emitted_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_frontier_early_stop_fallback_groups=" << stats.phase7_frontier_early_stop_fallback_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_requested=" << stats.phase7_all_attempt_early_stop_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_active=" << stats.phase7_all_attempt_early_stop_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_tasks=" << stats.phase7_all_attempt_early_stop_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_scoreinfos=" << stats.phase7_all_attempt_early_stop_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_reference_align_attempts=" << stats.phase7_all_attempt_early_stop_reference_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_candidate_align_attempts=" << stats.phase7_all_attempt_early_stop_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_skipped_attempts=" << stats.phase7_all_attempt_early_stop_skipped_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_emitted_groups=" << stats.phase7_all_attempt_early_stop_emitted_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_all_attempt_early_stop_fallback_groups=" << stats.phase7_all_attempt_early_stop_fallback_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_requested=" << stats.phase7_gate_c_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_active=" << stats.phase7_gate_c_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_tasks=" << stats.phase7_gate_c_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_scoreinfos=" << stats.phase7_gate_c_oracle_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_attempts=" << stats.phase7_gate_c_oracle_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_scoreinfos=" << stats.phase7_gate_c_gpu_candidate_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_attempts=" << stats.phase7_gate_c_gpu_candidate_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_false_negative_scoreinfos=" << stats.phase7_gate_c_false_negative_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_missing_required_attempts=" << stats.phase7_gate_c_missing_required_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_extra_candidate_attempts=" << stats.phase7_gate_c_extra_candidate_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_candidate_align_attempts=" << stats.phase7_gate_c_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gate_b_candidate_align_attempts=" << stats.phase7_gate_c_gate_b_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_scoreinfo_cpu_seconds=" << stats.phase7_gate_c_scoreinfo_cpu_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_seconds=" << stats.phase7_gate_c_gpu_candidate_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_cpu_replay_seconds=" << stats.phase7_gate_c_cpu_replay_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_total_seconds=" << stats.phase7_gate_c_total_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_digest_match=" << stats.phase7_gate_c_digest_match << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_full_rows_equal=" << stats.phase7_gate_c_full_rows_equal << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_requested=" << stats.phase7_v3_descriptor_source_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_active=" << stats.phase7_v3_descriptor_source_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_tasks=" << stats.phase7_v3_descriptor_source_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_reference_scoreinfos=" << stats.phase7_v3_descriptor_source_reference_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_reference_attempts=" << stats.phase7_v3_descriptor_source_reference_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_scoreinfos=" << stats.phase7_v3_descriptor_source_candidate_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_attempts=" << stats.phase7_v3_descriptor_source_candidate_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_min_cover_positions=" << stats.phase7_v3_descriptor_source_candidate_min_cover_positions << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_cpu_scoreinfo_calls=" << stats.phase7_v3_descriptor_source_cpu_scoreinfo_calls << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls=" << stats.phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_cpu_scoreinfo_reduced=" << stats.phase7_v3_descriptor_source_cpu_scoreinfo_reduced << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_certificate_checked=" << stats.phase7_v3_descriptor_source_candidate_certificate_checked << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_candidate_certificate_false_negatives=" << stats.phase7_v3_descriptor_source_candidate_certificate_false_negatives << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_missing_required_attempts=" << stats.phase7_v3_descriptor_source_missing_required_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_pre_scoreinfo_source=" << stats.phase7_v3_descriptor_source_pre_scoreinfo_source << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_descriptor_source_after_cpu_scoreinfo_source=" << stats.phase7_v3_descriptor_source_after_cpu_scoreinfo_source << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_requested=" << stats.phase7_v3_oracle_min_cover_replay_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_active=" << stats.phase7_v3_oracle_min_cover_replay_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_tasks=" << stats.phase7_v3_oracle_min_cover_replay_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_reference_align_attempts=" << stats.phase7_v3_oracle_min_cover_replay_reference_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_candidate_align_attempts=" << stats.phase7_v3_oracle_min_cover_replay_candidate_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_candidate_min_cover_positions=" << stats.phase7_v3_oracle_min_cover_replay_candidate_min_cover_positions << "\n";
	std::cerr << "benchmark.fasim_gasal2_phase7_v3_oracle_min_cover_replay_skipped_attempts=" << stats.phase7_v3_oracle_min_cover_replay_skipped_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batches=" << stats.longtarget_task_batches << "\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batch_tasks=" << stats.longtarget_task_batch_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_task_batch_scoreinfos=" << stats.longtarget_task_batch_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_fallbacks=" << stats.length_guard_fallbacks << "\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_last_query_len=" << stats.length_guard_last_query_len << "\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_max_query_len=" << stats.length_guard_max_query_len << "\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_last_target_len=" << stats.length_guard_last_target_len << "\n";
	std::cerr << "benchmark.fasim_gasal2_length_guard_max_target_len=" << stats.length_guard_max_target_len << "\n";
	std::cerr << "benchmark.fasim_gasal2_effective_streams=" << stats.effective_streams << "\n";
	std::cerr << "benchmark.fasim_gasal2_effective_batch_size=" << stats.effective_batch_size << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_prepass_enabled=" << (stats.score_prepass_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_gasal2_init_seconds=" << stats.init_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_fill_seconds=" << stats.fill_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_fill_seconds=" << stats.score_fill_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_fill_seconds=" << stats.traceback_fill_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_submit_seconds=" << stats.submit_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_submit_seconds=" << stats.score_submit_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_submit_seconds=" << stats.traceback_submit_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_wait_seconds=" << stats.wait_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_wait_seconds=" << stats.score_wait_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_wait_seconds=" << stats.traceback_wait_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_poll_wait_seconds=" << stats.score_poll_wait_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_poll_wait_seconds=" << stats.traceback_poll_wait_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_score_result_copy_seconds=" << stats.score_result_copy_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_result_copy_seconds=" << stats.traceback_result_copy_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_cigar_vector_seconds=" << stats.traceback_cigar_vector_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_cigar_string_seconds=" << stats.traceback_cigar_string_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_cigar_raw_ops=" << stats.traceback_cigar_raw_ops << "\n";
	std::cerr << "benchmark.fasim_gasal2_traceback_cigar_merged_ops=" << stats.traceback_cigar_merged_ops << "\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_attempt_build_seconds=" << stats.longtarget_attempt_build_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_longtarget_score_select_seconds=" << stats.longtarget_score_select_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_replay_seconds=" << stats.cpu_traceback_replay_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_substr_seconds=" << stats.cpu_traceback_substr_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_align_seconds=" << stats.cpu_traceback_align_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_convert_seconds=" << stats.cpu_traceback_convert_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_total_seconds=" << stats.total_seconds << "\n";
}

void fasim_gasal2_record_longtarget_task_batch(uint64_t tasks,
                                               uint64_t scoreInfos)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	++g_stats.longtarget_task_batches;
	g_stats.longtarget_task_batch_tasks += tasks;
	g_stats.longtarget_task_batch_scoreinfos += scoreInfos;
}

bool fasim_gasal2_align_attempts(const std::string &query,
                                 const std::vector<FasimGasal2Attempt> &attempts,
                                 std::vector<FasimGasal2SelectedAlignment> *selected,
                                 std::string *errorOut)
{
	if (selected != NULL)
	{
		selected->clear();
	}
	if (!fasim_gasal2_enabled())
	{
		if (errorOut != NULL)
		{
			*errorOut = "FASIM_ALIGN_GASAL2 is not enabled";
		}
		return false;
	}
	if (query.empty() || attempts.empty() || selected == NULL)
	{
		return true;
	}

	std::lock_guard<std::mutex> lock(g_mutex);
	const auto totalStart = std::chrono::steady_clock::now();
	const int batchSize = gasal2_batch_size_default();
	record_effective_batch_size(batchSize);
	const bool longtargetBridge = fasim_gasal2_longtarget_bridge_enabled();
	const bool top5Preset = env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
	const bool scorePrepass = score_prepass_enabled_for_mode(longtargetBridge, top5Preset);
	const bool certificateShadow = traceback_certificate_shadow_enabled();
	g_stats.traceback_certificate_shadow_requested =
		g_stats.traceback_certificate_shadow_requested || certificateShadow;
	g_stats.score_prepass_enabled = g_stats.score_prepass_enabled || scorePrepass;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (attempts[i].uses_target_view())
		{
			++g_stats.target_view_requests;
		}
	}

	if (!scorePrepass)
	{
		std::vector<StripedSmithWaterman::Alignment> alignments;
		if (!run_traceback(&g_traceback_state, query, attempts, batchSize, &alignments, errorOut))
		{
			++g_stats.fallbacks;
			return false;
		}

		select_alignments(attempts, alignments, selected);
		g_stats.total_seconds += seconds_since(totalStart);
		return true;
	}

	std::vector<size_t> selectedAttemptIndexes;
	if (staged_score_prepass_enabled_for_mode(top5Preset))
	{
		if (!select_attempts_with_staged_scores(&g_score_state,
		                                        query,
		                                        attempts,
		                                        batchSize,
		                                        &selectedAttemptIndexes,
		                                        errorOut))
		{
			++g_stats.fallbacks;
			return false;
		}
	}
	else
	{
		std::vector<ScoreOnlyResult> scoreResults;
		if (!run_score_only(&g_score_state, query, attempts, batchSize, &scoreResults, errorOut))
		{
			++g_stats.fallbacks;
			return false;
		}

		select_attempts_from_scores(attempts, scoreResults, &selectedAttemptIndexes);
	}
	apply_limited_traceback_scoreinfo_cap(attempts,
	                                      limited_traceback_max_scoreinfos(),
	                                      &selectedAttemptIndexes);
	if (selectedAttemptIndexes.empty())
	{
		g_stats.total_seconds += seconds_since(totalStart);
		return true;
	}

	std::vector<FasimGasal2Attempt> tracebackAttempts;
	tracebackAttempts.reserve(selectedAttemptIndexes.size());
	for (size_t i = 0; i < selectedAttemptIndexes.size(); ++i)
	{
		tracebackAttempts.push_back(attempts[selectedAttemptIndexes[i]]);
	}
	std::vector<FasimGasal2TracebackCertificateKind> certificateKinds(
		tracebackAttempts.size(),
		FasimGasal2TracebackCertificateKind::None);
	if (certificateShadow)
	{
		std::vector<ScoreOnlyResult> certificateScores;
		std::string certificateError;
		const auto certificateStart = std::chrono::steady_clock::now();
		const bool certificateScoreOk =
			run_score_only(&g_score_state,
			               query,
			               tracebackAttempts,
			               batchSize,
			               &certificateScores,
			               &certificateError);
		g_stats.traceback_certificate_probe_seconds +=
			seconds_since(certificateStart);
		if (!certificateScoreOk ||
		    certificateScores.size() != tracebackAttempts.size())
		{
			++g_stats.traceback_certificate_fallbacks;
		}
		else
		{
			g_stats.traceback_certificate_shadow_active = true;
			g_stats.traceback_certificate_pre_drop_proof_available = true;
			g_stats.traceback_certificate_probe_requests +=
				static_cast<uint64_t>(tracebackAttempts.size());
			g_stats.traceback_certificate_candidates_considered +=
				static_cast<uint64_t>(tracebackAttempts.size());
			std::set<size_t> seenAttemptIndexes;
			for (size_t i = 0; i < tracebackAttempts.size(); ++i)
			{
				FasimGasal2TracebackCertificateInput input;
				input.query_length = query.size();
				input.target_length = tracebackAttempts[i].target_size();
				input.nt_min_length = tracebackAttempts[i].nt_min_length;
				input.target_start = tracebackAttempts[i].start;
				input.score_query_end = certificateScores[i].query_end;
				input.score_ref_end = certificateScores[i].ref_end;
				input.exact_descriptor_duplicate =
					!seenAttemptIndexes.insert(selectedAttemptIndexes[i]).second;
				certificateKinds[i] =
					fasim_gasal2_traceback_certificate_kind(input);
				switch (certificateKinds[i])
				{
				case FasimGasal2TracebackCertificateKind::ExactDescriptorDuplicate:
					++g_stats
						.traceback_certificate_exact_descriptor_duplicate_skips;
					break;
				case FasimGasal2TracebackCertificateKind::StaticSpan:
					++g_stats.traceback_certificate_static_span_skips;
					break;
				case FasimGasal2TracebackCertificateKind::ScoreEndpointSpan:
					++g_stats.traceback_certificate_score_endpoint_span_skips;
					break;
				case FasimGasal2TracebackCertificateKind::None:
					++g_stats.traceback_certificate_uncertified_candidates;
					break;
				}
				if (certificateKinds[i] !=
				    FasimGasal2TracebackCertificateKind::None)
				{
					++g_stats.traceback_certificate_certified_skips;
				}
			}
		}
	}

	std::vector<StripedSmithWaterman::Alignment> tracebackAlignments;
	if (!run_traceback(&g_traceback_state, query, tracebackAttempts, batchSize, &tracebackAlignments, errorOut))
	{
		++g_stats.fallbacks;
		return false;
	}
	if (certificateShadow && g_stats.traceback_certificate_shadow_active)
	{
		for (size_t i = 0; i < tracebackAttempts.size(); ++i)
		{
			if (certificateKinds[i] != FasimGasal2TracebackCertificateKind::StaticSpan &&
			    certificateKinds[i] !=
			        FasimGasal2TracebackCertificateKind::ScoreEndpointSpan)
			{
				continue;
			}
			const StripedSmithWaterman::Alignment &alignment = tracebackAlignments[i];
			if (!fasim_gasal2_traceback_actual_span_is_invalid(
			        alignment.query_begin,
			        alignment.query_end,
			        alignment.ref_begin,
			        alignment.ref_end,
			        tracebackAttempts[i].nt_min_length))
			{
				++g_stats.traceback_certificate_shadow_false_rejects;
			}
		}
	}

	selected->clear();
	for (size_t i = 0; i < tracebackAttempts.size(); ++i)
	{
		FasimGasal2SelectedAlignment out;
		out.scoreinfo_index = tracebackAttempts[i].scoreinfo_index;
		out.cutlength = tracebackAttempts[i].cutlength;
		out.start = tracebackAttempts[i].start;
		out.selected = true;
		out.alignment = tracebackAlignments[i];
		selected->push_back(out);
	}
	g_stats.total_seconds += seconds_since(totalStart);
	return true;
}

bool fasim_gasal2_select_attempt_indexes_from_scores(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<size_t> *selectedAttemptIndexes,
	std::string *errorOut)
{
	if (selectedAttemptIndexes != NULL)
	{
		selectedAttemptIndexes->clear();
	}
	if (!fasim_gasal2_enabled())
	{
		if (errorOut != NULL)
		{
			*errorOut = "gasal2_disabled";
		}
		return false;
	}
	if (query.empty() || attempts.empty() || selectedAttemptIndexes == NULL)
	{
		if (errorOut != NULL)
		{
			*errorOut = attempts.empty() ? "empty_attempts" : "invalid_input";
		}
		return false;
	}

	std::lock_guard<std::mutex> lock(g_mutex);
	const int batchSize = gasal2_batch_size_default();
	record_effective_batch_size(batchSize);
	g_stats.score_prepass_enabled = true;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (attempts[i].uses_target_view())
		{
			++g_stats.target_view_requests;
		}
	}

	std::vector<ScoreOnlyResult> scoreResults;
	const std::chrono::steady_clock::time_point scoreStart =
		std::chrono::steady_clock::now();
	if (!run_score_only(&g_score_state,
	                    query,
	                    attempts,
	                    batchSize,
	                    &scoreResults,
	                    errorOut))
	{
		++g_stats.fallbacks;
		++g_stats.attempt_consumer_shadow_fallbacks;
		return false;
	}
	g_stats.attempt_consumer_shadow_score_seconds += seconds_since(scoreStart);

	const std::chrono::steady_clock::time_point selectStart =
		std::chrono::steady_clock::now();
	select_attempts_from_scores(attempts, scoreResults, selectedAttemptIndexes);
	g_stats.attempt_consumer_shadow_select_seconds += seconds_since(selectStart);
	return true;
}

bool fasim_gasal2_score_attempts(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<FasimGasal2ScoreOnlyAlignment> *scores,
	std::string *errorOut)
{
	if (scores != NULL)
	{
		scores->clear();
	}
	if (!fasim_gasal2_enabled())
	{
		if (errorOut != NULL)
		{
			*errorOut = "gasal2_disabled";
		}
		return false;
	}
	if (query.empty() || attempts.empty() || scores == NULL)
	{
		if (errorOut != NULL)
		{
			*errorOut = attempts.empty() ? "empty_attempts" : "invalid_input";
		}
		return false;
	}

	std::lock_guard<std::mutex> lock(g_mutex);
	const int batchSize = gasal2_batch_size_default();
	record_effective_batch_size(batchSize);
	g_stats.score_prepass_enabled = true;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (attempts[i].uses_target_view())
		{
			++g_stats.target_view_requests;
		}
	}

	std::vector<ScoreOnlyResult> scoreResults;
	const std::chrono::steady_clock::time_point scoreStart =
		std::chrono::steady_clock::now();
	if (!run_score_only(&g_score_state,
	                    query,
	                    attempts,
	                    batchSize,
	                    &scoreResults,
	                    errorOut))
	{
		++g_stats.fallbacks;
		++g_stats.emission_only_consumer_shadow_fallbacks;
		return false;
	}
	(void)scoreStart;

	scores->clear();
	scores->reserve(attempts.size());
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		FasimGasal2ScoreOnlyAlignment out;
		out.scoreinfo_index = attempts[i].scoreinfo_index;
		out.cutlength = attempts[i].cutlength;
		out.start = attempts[i].start;
		out.prealign_score = attempts[i].prealign_score;
		out.score = scoreResults[i].sw_score;
		out.query_end = scoreResults[i].query_end;
		out.ref_end = scoreResults[i].ref_end;
		scores->push_back(out);
	}
	return true;
}

bool fasim_gasal2_long_query_runtime_query_preflight_v1(
	size_t queryLength,
	const FasimLongQueryScoringContract &scoringContract,
	FasimLongQueryRuntimeDescriptor *descriptorOut,
	std::string *errorOut)
{
	return streamed_attempt_runtime_preflight(
		static_cast<uint64_t>(queryLength), 0, false, scoringContract,
		descriptorOut, errorOut);
}

bool fasim_gasal2_streamed_attempt_score_v1(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	const FasimLongQueryScoringContract &scoringContract,
	std::vector<FasimGasal2StreamedAttemptScore> *scores,
	FasimGasal2StreamedAttemptScoreTelemetry *telemetry,
	std::string *errorOut)
{
	const std::chrono::steady_clock::time_point totalStart =
		std::chrono::steady_clock::now();
	if (scores != NULL)
	{
		scores->clear();
	}
	if (telemetry != NULL)
	{
		*telemetry = FasimGasal2StreamedAttemptScoreTelemetry();
		telemetry->requests = static_cast<uint64_t>(attempts.size());
	}
	if (errorOut != NULL)
	{
		errorOut->clear();
	}
	if (query.empty() || attempts.empty() || scores == NULL)
	{
		const std::string error = attempts.empty() ? "empty_attempts" : "invalid_input";
		if (errorOut != NULL) *errorOut = error;
		if (telemetry != NULL) telemetry->error = error;
		return false;
	}

	size_t maximumTargetLength = 0;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const size_t targetLength = attempt.target_size();
		if (!attempt.target_view_valid() || targetLength == 0 ||
			targetLength > static_cast<size_t>(
				fasim_long_query_runtime_target_subview_length_limit()))
		{
			const std::string error = "invalid_target_subview";
			if (errorOut != NULL) *errorOut = error;
			if (telemetry != NULL)
			{
				telemetry->error = error;
				telemetry->total_seconds = seconds_since(totalStart);
			}
			return false;
		}
		maximumTargetLength = std::max(maximumTargetLength, targetLength);
	}

	FasimLongQueryRuntimeDescriptor runtimeDescriptor;
	std::string guardError;
	if (!streamed_attempt_runtime_preflight(
			static_cast<uint64_t>(query.size()),
			static_cast<uint64_t>(maximumTargetLength), true,
			scoringContract, &runtimeDescriptor, &guardError))
	{
		const std::string error = guardError.empty() ?
			"long_query_runtime_preflight_failed" : guardError;
		if (errorOut != NULL) *errorOut = error;
		if (telemetry != NULL)
		{
			telemetry->runtime_descriptor = runtimeDescriptor;
			telemetry->error = error;
			telemetry->total_seconds = seconds_since(totalStart);
		}
		return false;
	}
	if (telemetry != NULL)
	{
		telemetry->runtime_descriptor = runtimeDescriptor;
	}

	std::lock_guard<std::mutex> lock(g_mutex);
	std::string bridgeError;
	if (!g_streamed_attempt_query_cache.prepare(query, &bridgeError))
	{
		if (errorOut != NULL) *errorOut = bridgeError.empty() ? "query_prepare_failed" : bridgeError;
		if (telemetry != NULL)
		{
			telemetry->error = bridgeError.empty() ? "query_prepare_failed" : bridgeError;
			telemetry->total_seconds = seconds_since(totalStart);
		}
		return false;
	}

	scores->assign(attempts.size(), FasimGasal2StreamedAttemptScore());
	const int maxBatch = streamed_attempt_batch_size();
	for (size_t batchBegin = 0; batchBegin < attempts.size();
	     batchBegin += static_cast<size_t>(maxBatch))
	{
		const size_t batchEnd = std::min(
			attempts.size(), batchBegin + static_cast<size_t>(maxBatch));
		const int taskCount = static_cast<int>(batchEnd - batchBegin);
		size_t paddedTargetLength = 0;
		for (size_t i = batchBegin; i < batchEnd; ++i)
		{
			paddedTargetLength = std::max(
				paddedTargetLength, attempts[i].target_size());
		}
		if (paddedTargetLength == 0 ||
			paddedTargetLength > maximumTargetLength)
		{
			const std::string error = "invalid_padded_target_length";
			if (errorOut != NULL) *errorOut = error;
			if (telemetry != NULL)
			{
				telemetry->error = error;
				telemetry->total_seconds = seconds_since(totalStart);
			}
			return false;
		}

		// N has a negative substitution score for every query base. Padding can
		// only preserve or decrease an existing path, while the endpoint kernel
		// updates its winner on a strict score increase. The real subview winner
		// is therefore unchanged and remains relative to the unpadded attempt.
		std::vector<uint8_t> encoded(
			static_cast<size_t>(taskCount) * paddedTargetLength,
			static_cast<uint8_t>(4));
		for (size_t i = batchBegin; i < batchEnd; ++i)
		{
			const FasimGasal2Attempt &attempt = attempts[i];
			const char *target = attempt.target_data();
			uint8_t *destination = encoded.data() +
				((i - batchBegin) * paddedTargetLength);
			for (size_t base = 0; base < attempt.target_size(); ++base)
			{
				destination[base] = prealign_shared_encode_base(
					static_cast<unsigned char>(target[base]));
			}
		}

		std::vector<PreAlignCudaAttemptEndpoint> endpointRows;
		PreAlignCudaBatchResult batchResult;
		if (!prealign_cuda_find_max_endpoints_batch(
				g_streamed_attempt_query_cache.handle,
				encoded.data(),
				taskCount,
				static_cast<int>(paddedTargetLength),
				&endpointRows,
				&batchResult,
				&bridgeError))
		{
			const std::string error = bridgeError.empty() ?
				"streamed_attempt_score_failed" : bridgeError;
			if (errorOut != NULL) *errorOut = error;
			if (telemetry != NULL)
			{
				telemetry->error = error;
				telemetry->total_seconds = seconds_since(totalStart);
			}
			return false;
		}
		if (endpointRows.size() != static_cast<size_t>(taskCount))
		{
			const std::string error = "streamed_attempt_score_count_mismatch";
			if (errorOut != NULL) *errorOut = error;
			if (telemetry != NULL)
			{
				telemetry->error = error;
				telemetry->total_seconds = seconds_since(totalStart);
			}
			return false;
		}

		if (telemetry != NULL)
		{
			++telemetry->batches;
			telemetry->gpu_scored_requests += static_cast<uint64_t>(taskCount);
			telemetry->gpu_seconds += batchResult.gpuSeconds;
			telemetry->h2d_seconds += batchResult.h2dSeconds;
			telemetry->d2h_seconds += batchResult.d2hSeconds;
		}
		for (size_t i = batchBegin; i < batchEnd; ++i)
		{
			const PreAlignCudaAttemptEndpoint &endpoint =
				endpointRows[i - batchBegin];
			FasimGasal2StreamedAttemptScore &out = (*scores)[i];
			out.score = endpoint.score;
			out.query_end = endpoint.queryEnd;
			out.ref_end_local = endpoint.targetEnd;
			out.ref_end_global = endpoint.targetEnd >= 0 ?
				attempts[i].start + endpoint.targetEnd : -1;
		}
	}
	if (telemetry != NULL)
	{
		telemetry->total_seconds = seconds_since(totalStart);
	}
	return true;
}

bool fasim_gasal2_consumer_spike_select_from_scores(
	const std::vector<FasimGasal2Attempt> &attempts,
	const std::vector<FasimGasal2ScoreOnlyAlignment> &scores,
	std::vector<size_t> *selectedAttemptIndexes,
	std::vector<std::string> *selectionReasons,
	std::string *errorOut)
{
	if (selectedAttemptIndexes == NULL || attempts.size() != scores.size())
	{
		if (errorOut != NULL)
		{
			*errorOut = attempts.size() == scores.size() ?
				"null_selected_indexes" : "attempt_score_count_mismatch";
		}
		return false;
	}
	selectedAttemptIndexes->clear();
	if (selectionReasons != NULL)
	{
		selectionReasons->assign(attempts.size(), "not_selected_lower_score");
	}
	if (attempts.empty())
	{
		return true;
	}

	int currentScoreInfo = -1;
	size_t bestIndex = 0;
	int bestScore = 0;
	bool haveBest = false;
	size_t lastIndex = 0;
	int lastScore = 0;
	bool haveLast = false;
	bool emitted = false;

	auto mark = [&](size_t index, const char *reason)
	{
		if (selectionReasons != NULL && index < selectionReasons->size())
		{
			(*selectionReasons)[index] = reason;
		}
	};
	auto flush = [&]()
	{
		if (currentScoreInfo >= 0 && haveBest && !emitted)
		{
			selectedAttemptIndexes->push_back(bestIndex);
			mark(bestIndex, "best_fallback");
		}
		else if (currentScoreInfo >= 0 && haveLast && !emitted && lastScore != 0)
		{
			selectedAttemptIndexes->push_back(lastIndex);
			mark(lastIndex, "last");
		}
		bestIndex = 0;
		bestScore = 0;
		haveBest = false;
		lastIndex = 0;
		lastScore = 0;
		haveLast = false;
		emitted = false;
	};

	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const FasimGasal2ScoreOnlyAlignment &score = scores[i];
		if (attempt.scoreinfo_index != score.scoreinfo_index)
		{
			if (errorOut != NULL)
			{
				*errorOut = "scoreinfo_identity_mismatch";
			}
			selectedAttemptIndexes->clear();
			return false;
		}
		if (attempt.scoreinfo_index < currentScoreInfo)
		{
			if (errorOut != NULL)
			{
				*errorOut = "scoreinfo_order_not_monotonic";
			}
			selectedAttemptIndexes->clear();
			return false;
		}
		if (attempt.scoreinfo_index != currentScoreInfo)
		{
			flush();
			currentScoreInfo = attempt.scoreinfo_index;
		}
		if (emitted)
		{
			mark(i, "not_selected_after_threshold");
			continue;
		}
		lastIndex = i;
		lastScore = score.score;
		haveLast = true;
		if (score.score >= attempt.prealign_score)
		{
			selectedAttemptIndexes->push_back(i);
			mark(i, "threshold");
			emitted = true;
			continue;
		}
		if (score.score > bestScore &&
			score.ref_end == attempt.start + attempt.cutlength - 1)
		{
			bestIndex = i;
			bestScore = score.score;
			haveBest = true;
		}
	}
	flush();
	return true;
}

void fasim_gasal2_record_attempt_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t attempts,
	const char *decision)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.attempt_consumer_shadow_requested = 1;
	g_stats.attempt_consumer_shadow_tasks += tasks;
	g_stats.attempt_consumer_shadow_scoreinfos += scoreInfos;
	g_stats.attempt_consumer_shadow_attempts += attempts;
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.attempt_consumer_shadow_decision = decision;
	}
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
	std::lock_guard<std::mutex> lock(g_mutex);
	if (active)
	{
		g_stats.attempt_consumer_shadow_active = 1;
	}
	g_stats.attempt_consumer_shadow_selected_attempts += selectedAttempts;
	g_stats.attempt_consumer_shadow_cpu_align_attempts += cpuAlignAttempts;
	g_stats.attempt_consumer_shadow_cpu_align_seconds += cpuAlignSeconds;
	g_stats.attempt_consumer_shadow_convert_seconds += convertSeconds;
	g_stats.attempt_consumer_shadow_total_seconds += totalSeconds;
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.attempt_consumer_shadow_decision = decision;
	}
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.attempt_consumer_shadow_triplex_mismatches += mismatches;
	g_stats.attempt_consumer_shadow_missing_triplexes += missing;
	g_stats.attempt_consumer_shadow_extra_triplexes += extra;
	if (firstMismatch != NULL &&
	    firstMismatch[0] != '\0' &&
	    g_stats.attempt_consumer_shadow_first_mismatch == "none")
	{
		g_stats.attempt_consumer_shadow_first_mismatch = firstMismatch;
	}
	if (digestMatch)
	{
		g_stats.attempt_consumer_shadow_digest_match = 1;
	}
	if (fullRowsEqual)
	{
		g_stats.attempt_consumer_shadow_full_rows_equal = 1;
	}
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.attempt_consumer_shadow_decision = decision;
	}
}

void fasim_gasal2_record_emission_only_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t scoredAttempts,
	const char *decision)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.emission_only_consumer_shadow_requested = 1;
	g_stats.emission_only_consumer_shadow_tasks += tasks;
	g_stats.emission_only_consumer_shadow_scoreinfos += scoreInfos;
	g_stats.emission_only_consumer_shadow_scored_attempts += scoredAttempts;
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.emission_only_consumer_shadow_decision = decision;
	}
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
	std::lock_guard<std::mutex> lock(g_mutex);
	if (active)
	{
		g_stats.emission_only_consumer_shadow_active = 1;
	}
	g_stats.emission_only_consumer_shadow_threshold_emits += thresholdEmits;
	g_stats.emission_only_consumer_shadow_terminal_emits += terminalEmits;
	g_stats.emission_only_consumer_shadow_last_emits += lastEmits;
	g_stats.emission_only_consumer_shadow_empty_emits += emptyEmits;
	g_stats.emission_only_consumer_shadow_cpu_align_attempts += cpuAlignAttempts;
	g_stats.emission_only_consumer_shadow_realpath_reference_align_attempts +=
		realpathReferenceAlignAttempts;
	g_stats.emission_only_consumer_shadow_align_attempt_reduction +=
		static_cast<int64_t>(realpathReferenceAlignAttempts) -
		static_cast<int64_t>(cpuAlignAttempts);
	g_stats.emission_only_consumer_shadow_score_seconds += scoreSeconds;
	g_stats.emission_only_consumer_shadow_select_seconds += selectSeconds;
	g_stats.emission_only_consumer_shadow_cpu_align_seconds += cpuAlignSeconds;
	g_stats.emission_only_consumer_shadow_convert_seconds += convertSeconds;
	g_stats.emission_only_consumer_shadow_total_seconds += totalSeconds;
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.emission_only_consumer_shadow_decision = decision;
	}
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.emission_only_consumer_shadow_triplex_mismatches += triplexMismatches;
	g_stats.emission_only_consumer_shadow_missing_triplexes += missingTriplexes;
	g_stats.emission_only_consumer_shadow_extra_triplexes += extraTriplexes;
	if (firstMismatch != NULL &&
	    firstMismatch[0] != '\0' &&
	    g_stats.emission_only_consumer_shadow_first_mismatch == "none")
	{
		g_stats.emission_only_consumer_shadow_first_mismatch = firstMismatch;
	}
	if (digestMatch)
	{
		g_stats.emission_only_consumer_shadow_digest_match = 1;
	}
	if (fullRowsEqual)
	{
		g_stats.emission_only_consumer_shadow_full_rows_equal = 1;
	}
	if (decision != NULL && decision[0] != '\0')
	{
		g_stats.emission_only_consumer_shadow_decision = decision;
	}
}

void fasim_gasal2_record_phase7_next_reducer_request(
	uint64_t tasks,
	uint64_t scoreInfos,
	uint64_t candidateAttempts,
	bool active)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_next_reducer_requested = 1;
	g_stats.phase7_next_reducer_active = active ? 1 : 0;
	g_stats.phase7_next_reducer_tasks += tasks;
	g_stats.phase7_next_reducer_scoreinfos += scoreInfos;
	g_stats.phase7_next_reducer_candidate_attempts += candidateAttempts;
	g_stats.phase7_next_reducer_reference_attempts += candidateAttempts;
	g_stats.phase7_next_reducer_reference_align_attempts += candidateAttempts;
}

void fasim_gasal2_record_phase7_next_reducer_result(
	uint64_t candidateAlignAttempts,
	uint64_t referenceAlignAttempts,
	uint64_t falseNegativeScoreInfos,
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	if (g_stats.phase7_next_reducer_reference_align_attempts < referenceAlignAttempts)
	{
		g_stats.phase7_next_reducer_reference_align_attempts = referenceAlignAttempts;
	}
	g_stats.phase7_next_reducer_candidate_align_attempts += candidateAlignAttempts;
	g_stats.phase7_next_reducer_false_negative_scoreinfos += falseNegativeScoreInfos;
	g_stats.phase7_next_reducer_triplex_mismatches += triplexMismatches;
	g_stats.phase7_next_reducer_missing_triplexes += missingTriplexes;
	g_stats.phase7_next_reducer_extra_triplexes += extraTriplexes;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_frontier_log_requested = 1;
	g_stats.phase7_frontier_log_active = active ? 1 : 0;
	g_stats.phase7_frontier_log_tasks += tasks;
	g_stats.phase7_frontier_log_scoreinfos += scoreInfos;
	g_stats.phase7_frontier_log_align_attempts += alignAttempts;
	g_stats.phase7_frontier_log_triplexes += triplexes;
	if (path != NULL)
	{
		g_stats.phase7_frontier_log_path = path;
	}
	if (digest != NULL)
	{
		g_stats.phase7_frontier_log_digest = digest;
	}
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_frontier_early_stop_requested = 1;
	g_stats.phase7_frontier_early_stop_active = active ? 1 : 0;
	g_stats.phase7_frontier_early_stop_tasks += tasks;
	g_stats.phase7_frontier_early_stop_scoreinfos += scoreInfos;
	g_stats.phase7_frontier_early_stop_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_frontier_early_stop_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_frontier_early_stop_skipped_attempts += skippedAttempts;
	g_stats.phase7_frontier_early_stop_emitted_groups += emittedGroups;
	g_stats.phase7_frontier_early_stop_fallback_groups += fallbackGroups;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_all_attempt_early_stop_requested = 1;
	g_stats.phase7_all_attempt_early_stop_active = active ? 1 : 0;
	g_stats.phase7_all_attempt_early_stop_tasks += tasks;
	g_stats.phase7_all_attempt_early_stop_scoreinfos += scoreInfos;
	g_stats.phase7_all_attempt_early_stop_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_all_attempt_early_stop_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_all_attempt_early_stop_skipped_attempts += skippedAttempts;
	g_stats.phase7_all_attempt_early_stop_emitted_groups += emittedGroups;
	g_stats.phase7_all_attempt_early_stop_fallback_groups += fallbackGroups;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gate_c_requested = 1;
	g_stats.phase7_gate_c_active = active ? 1 : 0;
	g_stats.phase7_gate_c_tasks += tasks;
	g_stats.phase7_gate_c_oracle_scoreinfos += oracleScoreInfos;
	g_stats.phase7_gate_c_oracle_attempts += oracleAttempts;
	g_stats.phase7_gate_c_gpu_candidate_scoreinfos += gpuCandidateScoreInfos;
	g_stats.phase7_gate_c_gpu_candidate_attempts += gpuCandidateAttempts;
	g_stats.phase7_gate_c_false_negative_scoreinfos += falseNegativeScoreInfos;
	g_stats.phase7_gate_c_missing_required_attempts += missingRequiredAttempts;
	g_stats.phase7_gate_c_extra_candidate_attempts += extraCandidateAttempts;
	g_stats.phase7_gate_c_candidate_align_attempts += candidateAlignAttempts;
	g_stats.phase7_gate_c_gate_b_candidate_align_attempts +=
		gateBCandidateAlignAttempts;
	g_stats.phase7_gate_c_scoreinfo_cpu_seconds += scoreInfoCpuSeconds;
	g_stats.phase7_gate_c_gpu_candidate_seconds += gpuCandidateSeconds;
	g_stats.phase7_gate_c_cpu_replay_seconds += cpuReplaySeconds;
	g_stats.phase7_gate_c_total_seconds += totalSeconds;
	g_stats.phase7_gate_c_digest_match = digestMatch;
	g_stats.phase7_gate_c_full_rows_equal = fullRowsEqual;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_v3_descriptor_source_requested = 1;
	g_stats.phase7_v3_descriptor_source_active =
		(g_stats.phase7_v3_descriptor_source_active || active) ? 1 : 0;
	g_stats.phase7_v3_descriptor_source_tasks += tasks;
	g_stats.phase7_v3_descriptor_source_reference_scoreinfos += referenceScoreInfos;
	g_stats.phase7_v3_descriptor_source_reference_attempts += referenceAttempts;
	g_stats.phase7_v3_descriptor_source_candidate_scoreinfos += candidateScoreInfos;
	g_stats.phase7_v3_descriptor_source_candidate_attempts += candidateAttempts;
	g_stats.phase7_v3_descriptor_source_candidate_min_cover_positions +=
		candidateMinCoverPositions;
	g_stats.phase7_v3_descriptor_source_cpu_scoreinfo_calls += cpuScoreInfoCalls;
	g_stats.phase7_v3_descriptor_source_baseline_cpu_scoreinfo_calls +=
		baselineCpuScoreInfoCalls;
	g_stats.phase7_v3_descriptor_source_cpu_scoreinfo_reduced =
		(g_stats.phase7_v3_descriptor_source_cpu_scoreinfo_reduced ||
		 cpuScoreInfoReduced) ? 1 : 0;
	g_stats.phase7_v3_descriptor_source_candidate_certificate_checked =
		(g_stats.phase7_v3_descriptor_source_candidate_certificate_checked ||
		 candidateCertificateChecked) ? 1 : 0;
	g_stats.phase7_v3_descriptor_source_candidate_certificate_false_negatives +=
		candidateCertificateFalseNegatives;
	g_stats.phase7_v3_descriptor_source_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_v3_descriptor_source_pre_scoreinfo_source =
		(g_stats.phase7_v3_descriptor_source_pre_scoreinfo_source ||
		 preScoreInfoSource) ? 1 : 0;
	g_stats.phase7_v3_descriptor_source_after_cpu_scoreinfo_source =
		(g_stats.phase7_v3_descriptor_source_after_cpu_scoreinfo_source ||
		 afterCpuScoreInfoSource) ? 1 : 0;
}

void fasim_gasal2_record_phase7_v3_oracle_min_cover_replay(
	uint64_t tasks,
	uint64_t referenceAlignAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t candidateMinCoverPositions,
	bool active)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_v3_oracle_min_cover_replay_requested = 1;
	g_stats.phase7_v3_oracle_min_cover_replay_active =
		(g_stats.phase7_v3_oracle_min_cover_replay_active || active) ? 1 : 0;
	g_stats.phase7_v3_oracle_min_cover_replay_tasks += tasks;
	g_stats.phase7_v3_oracle_min_cover_replay_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_v3_oracle_min_cover_replay_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_v3_oracle_min_cover_replay_candidate_min_cover_positions +=
		candidateMinCoverPositions;
	g_stats.phase7_v3_oracle_min_cover_replay_skipped_attempts +=
		referenceAlignAttempts > candidateAlignAttempts ?
			referenceAlignAttempts - candidateAlignAttempts :
			0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_v5_fused_scoreinfo_consumer_requested = 1;
	g_stats.phase7_v5_fused_scoreinfo_consumer_active =
		(g_stats.phase7_v5_fused_scoreinfo_consumer_active ||
		 gpuDescriptorAttempts > 0 || gateV51Pass) ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_tasks += tasks;
	g_stats.phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos +=
		referenceScoreInfos;
	g_stats.phase7_v5_fused_scoreinfo_consumer_reference_attempts +=
		referenceAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos +=
		gpuDescriptorScoreInfos;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts +=
		gpuDescriptorAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives +=
		falseNegatives;
	g_stats.phase7_v5_fused_scoreinfo_consumer_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts +=
		extraDescriptorAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced =
		(g_stats.phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced ||
		 scoreInfoPrealignReduced) ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_cpu_align_authority =
		(g_stats.phase7_v5_fused_scoreinfo_consumer_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass =
		(g_stats.phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass ||
		 gateV51Pass) ? 1 : 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_active =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_active ||
		 gpuDescriptorAttempts > 0 || gateV51Pass) ? 1 : 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_tasks += tasks;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_reference_scoreinfos +=
		referenceScoreInfos;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_reference_attempts +=
		referenceAttempts;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos +=
		gpuDescriptorScoreInfos;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts +=
		gpuDescriptorAttempts;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo ||
		 sourceIsPreScoreInfo) ? 1 : 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced ||
		 scoreInfoPrealignReduced) ? 1 : 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives +=
		falseNegatives;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale ||
		 candidateAttemptsBelowAllColumnReplayScale) ? 1 : 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass =
		(g_stats.phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass ||
		 gateV51Pass) ? 1 : 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_v5_cpu_authority_replay_requested = 1;
	g_stats.phase7_v5_cpu_authority_replay_active =
		(g_stats.phase7_v5_cpu_authority_replay_active ||
		 candidateAlignAttempts > 0 || gateV52Pass) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_tasks += tasks;
	g_stats.phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos +=
		gpuDescriptorScoreInfos;
	g_stats.phase7_v5_cpu_authority_replay_gpu_descriptor_attempts +=
		gpuDescriptorAttempts;
	g_stats.phase7_v5_cpu_authority_replay_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_v5_cpu_authority_replay_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo =
		(g_stats.phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo ||
		 sourceIsPreScoreInfo) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced =
		(g_stats.phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced ||
		 scoreInfoPrealignReduced) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_descriptor_false_negatives +=
		falseNegatives;
	g_stats.phase7_v5_cpu_authority_replay_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_v5_cpu_authority_replay_cpu_align_authority =
		(g_stats.phase7_v5_cpu_authority_replay_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_v5_cpu_authority_replay_full_rows_equal =
		(g_stats.phase7_v5_cpu_authority_replay_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_digest_match =
		(g_stats.phase7_v5_cpu_authority_replay_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_v5_cpu_authority_replay_missing_rows += missingRows;
	g_stats.phase7_v5_cpu_authority_replay_extra_rows += extraRows;
	g_stats.phase7_v5_cpu_authority_replay_triplex_mismatches += triplexMismatches;
	g_stats.phase7_v5_cpu_authority_replay_gate_v5_2_pass =
		(g_stats.phase7_v5_cpu_authority_replay_gate_v5_2_pass ||
		 gateV52Pass) ? 1 : 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_gpu_consumer_summary_requested = 1;
	g_stats.phase7_post_v5_3_gpu_consumer_summary_active =
		(g_stats.phase7_post_v5_3_gpu_consumer_summary_active ||
		 gpuConsumerSummaryRows > 0 || gateFirst1Pass) ? 1 : 0;
	g_stats.phase7_post_v5_3_gpu_consumer_summary_tasks += tasks;
	g_stats.phase7_post_v5_3_gpu_consumer_summary_source_is_pre_scoreinfo =
		(g_stats.phase7_post_v5_3_gpu_consumer_summary_source_is_pre_scoreinfo ||
		 sourceIsPreScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_gpu_consumer_summary_rows +=
		gpuConsumerSummaryRows;
	g_stats.phase7_post_v5_3_gpu_consumer_reduces_before_host_transfer =
		(g_stats.phase7_post_v5_3_gpu_consumer_reduces_before_host_transfer ||
		 gpuConsumerReducesBeforeHostTransfer) ? 1 : 0;
	g_stats.phase7_post_v5_3_uses_prefix_boundary_or_equivalent_replay_proof =
		(g_stats.phase7_post_v5_3_uses_prefix_boundary_or_equivalent_replay_proof ||
		 usesPrefixBoundaryOrEquivalentReplayProof) ? 1 : 0;
	g_stats.phase7_post_v5_3_arbitrary_sparse_subset =
		(g_stats.phase7_post_v5_3_arbitrary_sparse_subset ||
		 arbitrarySparseSubset) ? 1 : 0;
	g_stats.phase7_post_v5_3_first_descriptor_per_scoreinfo =
		(g_stats.phase7_post_v5_3_first_descriptor_per_scoreinfo ||
		 firstDescriptorPerScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_gpu_selected_attempts += gpuSelectedAttempts;
	g_stats.phase7_post_v5_3_selected_prefix_attempts += selectedPrefixAttempts;
	g_stats.phase7_post_v5_3_reference_align_attempts += referenceAlignAttempts;
	g_stats.phase7_post_v5_3_candidate_align_attempts += candidateAlignAttempts;
	g_stats.phase7_post_v5_3_v5_candidate_align_attempts +=
		v5CandidateAlignAttempts;
	g_stats.phase7_post_v5_3_scoreinfo_prealign_reduced =
		(g_stats.phase7_post_v5_3_scoreinfo_prealign_reduced ||
		 scoreInfoPrealignReduced) ? 1 : 0;
	g_stats.phase7_post_v5_3_align_side_reduced =
		(g_stats.phase7_post_v5_3_align_side_reduced ||
		 alignSideReduced) ? 1 : 0;
	g_stats.phase7_post_v5_3_descriptor_false_negatives +=
		descriptorFalseNegatives;
	g_stats.phase7_post_v5_3_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_v5_3_fallback_accounting_clean =
		(g_stats.phase7_post_v5_3_fallback_accounting_clean ||
		 fallbackAccountingClean) ? 1 : 0;
	g_stats.phase7_post_v5_3_cpu_align_authority =
		(g_stats.phase7_post_v5_3_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_digest_match =
		(g_stats.phase7_post_v5_3_digest_match || digestMatch) ? 1 : 0;
	g_stats.phase7_post_v5_3_full_rows_equal =
		(g_stats.phase7_post_v5_3_full_rows_equal || fullRowsEqual) ? 1 : 0;
	g_stats.phase7_post_v5_3_missing_rows += missingRows;
	g_stats.phase7_post_v5_3_extra_rows += extraRows;
	g_stats.phase7_post_v5_3_triplex_mismatches += triplexMismatches;
	g_stats.phase7_post_v5_3_gate_first1_pass =
		(g_stats.phase7_post_v5_3_gate_first1_pass || gateFirst1Pass) ? 1 : 0;
}

void fasim_gasal2_record_phase7_post_v5_3_task_frontier_certificate_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_task_frontier_certificate_requested = 1;
	g_stats.phase7_post_v5_3_task_frontier_certificate_active = 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_task_frontier_certificate_requested = 1;
	g_stats.phase7_post_v5_3_task_frontier_certificate_active =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_active ||
		 active || taskFrontierCertificateRows > 0 || gateFirst1Pass) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_tasks += tasks;
	g_stats.phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo ||
		 sourceIsPreScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda ||
		 sourceIsLegacyByteCuda) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gasal2_score_only_long_query_dependency =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_gasal2_score_only_long_query_dependency ||
		 gasal2ScoreOnlyLongQueryDependency) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate ||
		 usesTaskFrontierCertificate) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_uses_prefix_boundary_only =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_uses_prefix_boundary_only ||
		 usesPrefixBoundaryOnly) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_arbitrary_sparse_subset =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_arbitrary_sparse_subset ||
		 arbitrarySparseSubset) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_first_descriptor_per_scoreinfo =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_first_descriptor_per_scoreinfo ||
		 firstDescriptorPerScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_fixed_prefix_per_scoreinfo =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_fixed_prefix_per_scoreinfo ||
		 fixedPrefixPerScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gpu_consumer_reduces_before_host_transfer =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_gpu_consumer_reduces_before_host_transfer ||
		 gpuConsumerReducesBeforeHostTransfer) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_rows +=
		taskFrontierCertificateRows;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts +=
		gpuSelectedAttempts;
	g_stats.phase7_post_v5_3_task_frontier_certificate_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_post_v5_3_task_frontier_certificate_v5_candidate_align_attempts +=
		v5CandidateAlignAttempts;
	g_stats.phase7_post_v5_3_task_frontier_certificate_descriptor_false_negatives +=
		descriptorFalseNegatives;
	g_stats.phase7_post_v5_3_task_frontier_certificate_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean ||
		 fallbackAccountingClean) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_cpu_align_authority =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_digest_match =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_full_rows_equal =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_post_v5_3_task_frontier_certificate_missing_rows +=
		missingRows;
	g_stats.phase7_post_v5_3_task_frontier_certificate_extra_rows +=
		extraRows;
	g_stats.phase7_post_v5_3_task_frontier_certificate_triplex_mismatches +=
		triplexMismatches;
	g_stats.phase7_post_v5_3_task_frontier_certificate_gate_first1_pass =
		(g_stats.phase7_post_v5_3_task_frontier_certificate_gate_first1_pass ||
		 gateFirst1Pass) ? 1 : 0;
}

void fasim_gasal2_record_phase7_post_v5_3_pre_d2h_proof_search_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_requested = 1;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_active = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_gpu_output_authority = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_runtime_reduction_enabled = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_requested = 1;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_active =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_active ||
		 active || proofSearchRows > 0 || gateFirst1ExportPass) ? 1 : 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_source_is_pre_scoreinfo =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_source_is_pre_scoreinfo ||
		 sourceIsPreScoreInfo) ? 1 : 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_source_is_legacy_byte_cuda =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_source_is_legacy_byte_cuda ||
		 sourceIsLegacyByteCuda) ? 1 : 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_gpu_output_authority = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_proof_search_rows +=
		proofSearchRows;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_task_count += tasks;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_scoreinfo_count +=
		scoreInfoCount;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_attempt_count +=
		attemptCount;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_label_source_cpu_authority_external_output =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_label_source_cpu_authority_external_output ||
		 labelSourceCpuAuthorityExternalOutput) ? 1 : 0;
	g_stats.phase7_post_v5_3_pre_d2h_proof_search_gate_first1_export_pass =
		(g_stats.phase7_post_v5_3_pre_d2h_proof_search_gate_first1_export_pass ||
		 gateFirst1ExportPass) ? 1 : 0;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_active =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_active ||
		 (!missingCertificateProducer && certificateValidBeforeD2h) ||
		 gateFirst1Pass) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_scoreinfo_tasks +=
		gpuScoreInfoTasks;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_candidate_groups +=
		gpuCandidateGroups;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_replay_attempts +=
		gpuReplayAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_groups +=
		gpuSkippedGroups;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_attempts +=
		gpuSkippedAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_replay_attempts +=
		cpuReplayAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_baseline_cpu_attempts +=
		baselineCpuAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer ||
		 missingCertificateProducer) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h ||
		 certificateValidBeforeD2h) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate ||
		 finalCpuOutputMembershipRequiredForCertificate) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound ||
		 fallbackOnMissingBound) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay ||
		 fallbackToFullCpuReplay) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_false_negatives +=
		certificateFalseNegatives;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced ||
		 scoreInfoPrealignReduced) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced ||
		 alignSideReduced) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean ||
		 fallbackAccountingClean) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_rows +=
		missingRows;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_extra_rows +=
		extraRows;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_triplex_mismatches +=
		triplexMismatches;
	g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass =
		(g_stats.phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass ||
		 gateFirst1Pass) ? 1 : 0;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_work_drop_path = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_final_cpu_output_membership_required = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_active ||
		 sourceAttemptCount > 0 || gateFirst1SourcePass) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_certificate_source ||
		 realCertificateSource) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_real_work_drop_path = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_certificate_is_synthetic = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_pre_drop ||
		 sourceIsPreDrop) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_is_legacy_byte_cuda ||
		 sourceIsLegacyByteCuda) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_final_cpu_output_membership_required = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_task_count +=
		sourceTaskCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_scoreinfo_count +=
		sourceScoreInfoCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_source_attempt_count +=
		sourceAttemptCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_scoreinfo_count +=
		referenceScoreInfoCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_reference_attempt_count +=
		referenceAttemptCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_certificate ||
		 !realCertificateSource) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_align_side_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_fallback_accounting_clean ||
		 fallbackAccountingClean) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_certificate_false_negatives +=
		certificateFalseNegatives;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_full_rows_equal = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_digest_match = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass =
		(g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_source_pass ||
		 gateFirst1SourcePass) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_work_drop_path = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_final_cpu_output_membership_required = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active =
		(g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_active ||
		 realCertificateSource || sourceAttemptCount > 0) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source =
		(g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_certificate_source ||
		 realCertificateSource) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_uses_pre_drop_output_inert_proof = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_real_work_drop_path = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_final_cpu_output_membership_required = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract =
		(g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_not_top5_only_contract ||
		 proofMustNotUseTop5OnlyContract) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract =
		(g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_complete_row_set_contract ||
		 proofMustCoverCompleteRowSet) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_task_count +=
		sourceTaskCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_scoreinfo_count +=
		sourceScoreInfoCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_source_attempt_count +=
		sourceAttemptCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_scoreinfo_count +=
		referenceScoreInfoCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_reference_attempt_count +=
		referenceAttemptCount;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_false_negatives +=
		candidateProofFalseNegatives;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_candidate_proof_missing_required_attempts +=
		candidateProofMissingRequiredAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority =
		(g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_digest_match = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_cert_engine_first1_shadow = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_work_drop = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_d2h = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_scoreinfo_groups = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_attempts = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_digest_match = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_rows = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_extra_rows = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_requested = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active =
		(g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_active ||
		 realCertificateSource || gpuAttemptFrontierAttempts > 0) ? 1 : 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_cert_engine_first1_shadow = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source =
		(g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_real_certificate_source ||
		 realCertificateSource) ? 1 : 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_work_drop = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_valid_before_d2h = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_scoreinfo_groups +=
		gpuScoreInfoGroups;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_attempt_frontier_attempts +=
		gpuAttemptFrontierAttempts;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_selected_replay_attempts +=
		gpuSelectedReplayAttempts;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_scoreinfo_groups = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_skipped_attempts = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_replay_attempts +=
		cpuReplayAttempts;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_baseline_cpu_attempts +=
		baselineCpuAttempts;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_certificate_false_negatives +=
		certificateFalseNegatives;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority =
		(g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_digest_match = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_missing_rows = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_extra_rows = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_requested = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_scoreinfo_groups = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_attempts = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_produced_before_work_drop = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_consumed_before_cpu_replay_selection = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_digest_match = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_rows = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_extra_rows = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_requested = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active =
		(g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_active ||
		 active || gpuOwnedAttemptFrontierAttempts > 0) ? 1 : 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_requested = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active =
		(g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_consumer_active ||
		 active || gpuOwnedScoreInfoStates > 0) ? 1 : 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_scoreinfo_states +=
		gpuOwnedScoreInfoStates;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_attempt_frontier_attempts +=
		gpuOwnedAttemptFrontierAttempts;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_replay_frontier_attempts +=
		gpuOwnedReplayFrontierAttempts;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_scoreinfo_groups = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_owned_skipped_attempts = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_replay_attempts +=
		cpuReplayAttempts;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_baseline_cpu_attempts +=
		baselineCpuAttempts;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_produced_before_work_drop = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_consumed_before_cpu_replay_selection = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_certificate_false_negatives +=
		certificateFalseNegatives;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority =
		(g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_digest_match = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_missing_rows = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_extra_rows = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_full_align_verifier_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_full_align_verifier_first1_shadow_requested = 1;
	g_stats.phase7_full_align_verifier_first1_shadow_active = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_descriptors = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_proposals = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_proposal_failures = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_verifier_pass = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_verifier_fail = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_cpu_align_fallbacks = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_score_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_endpoint_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_cigar_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_full_row_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_digest_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_digest_match = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_missing_rows = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_extra_rows = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_full_align_verifier_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_full_align_verifier_first1_shadow_gate_first1_shadow_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_full_align_verifier_first1_shadow_requested = 1;
	g_stats.phase7_full_align_verifier_first1_shadow_active =
		(g_stats.phase7_full_align_verifier_first1_shadow_active ||
		 descriptors > 0 || proposals > 0 || verifierPass > 0 || verifierFail > 0) ? 1 : 0;
	g_stats.phase7_full_align_verifier_first1_shadow_descriptors += descriptors;
	g_stats.phase7_full_align_verifier_first1_shadow_proposals += proposals;
	g_stats.phase7_full_align_verifier_first1_shadow_proposal_failures += proposalFailures;
	g_stats.phase7_full_align_verifier_first1_shadow_verifier_pass += verifierPass;
	g_stats.phase7_full_align_verifier_first1_shadow_verifier_fail += verifierFail;
	g_stats.phase7_full_align_verifier_first1_shadow_cpu_align_fallbacks += cpuAlignFallbacks;
	g_stats.phase7_full_align_verifier_first1_shadow_score_mismatches += scoreMismatches;
	g_stats.phase7_full_align_verifier_first1_shadow_endpoint_mismatches += endpointMismatches;
	g_stats.phase7_full_align_verifier_first1_shadow_cigar_mismatches += cigarMismatches;
	g_stats.phase7_full_align_verifier_first1_shadow_full_row_mismatches += fullRowMismatches;
	g_stats.phase7_full_align_verifier_first1_shadow_digest_mismatches += digestMismatches;
	g_stats.phase7_full_align_verifier_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_digest_match = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_missing_rows = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_extra_rows = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_triplex_mismatches = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_full_align_verifier_first1_shadow_cpu_align_authority =
		(g_stats.phase7_full_align_verifier_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_full_align_verifier_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_full_align_verifier_first1_shadow_gate_first1_shadow_pass = 0;
}

void fasim_gasal2_record_phase7_native_cuda_fasim_dp_engine_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_requested = 1;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_active = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_native_scoreinfo_tiles = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_forward_endpoint_witnesses = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_witnesses = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_traceback_cigar_witnesses = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificates = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificate_false_negatives = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_missing_required_attempts = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_byte_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_endpoint_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cigar_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_row_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_match = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_fallbacks = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_requested = 1;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_active =
		(g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_active ||
		 nativeScoreInfoTiles > 0 || forwardEndpointWitnesses > 0 ||
		 reverseStartWitnesses > 0 || tracebackCigarWitnesses > 0 ||
		 certificates > 0) ? 1 : 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_native_scoreinfo_tiles += nativeScoreInfoTiles;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_forward_endpoint_witnesses += forwardEndpointWitnesses;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_witnesses += reverseStartWitnesses;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_traceback_cigar_witnesses += tracebackCigarWitnesses;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificates += certificates;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_certificate_false_negatives += certificateFalseNegatives;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_missing_required_attempts += missingRequiredAttempts;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_byte_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_endpoint_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_reverse_start_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cigar_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_row_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_mismatches = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_digest_match = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_fallbacks += cpuAlignFallbacks;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_accounting_clean = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority =
		(g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_native_cuda_fasim_dp_engine_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_gpu_upper_bound_reject_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_requested = 1;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_active = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_descriptors = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_certificates = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_reject_candidates_shadow = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_scoreinfo_groups = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_align_attempts = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_certificate_false_negatives = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_groups = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_attempts = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_unsupported_descriptors = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_digest_match = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_requested = 1;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_active =
		(g_stats.phase7_gpu_upper_bound_reject_first1_shadow_active ||
		 upperBoundDescriptors > 0 || upperBoundCertificates > 0) ? 1 : 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_descriptors += upperBoundDescriptors;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_upper_bound_certificates += upperBoundCertificates;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_reject_candidates_shadow += rejectCandidatesShadow;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_scoreinfo_groups += wouldRejectScoreInfoGroups;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_would_reject_align_attempts += wouldRejectAlignAttempts;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_certificate_false_negatives += certificateFalseNegatives;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_groups += baselineRowsInRejectedGroups;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_baseline_rows_in_rejected_attempts += baselineRowsInRejectedAttempts;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_unsupported_descriptors += unsupportedDescriptors;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal =
		(g_stats.phase7_gpu_upper_bound_reject_first1_shadow_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_digest_match =
		(g_stats.phase7_gpu_upper_bound_reject_first1_shadow_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority =
		(g_stats.phase7_gpu_upper_bound_reject_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_shadow_pass =
		upperBoundDescriptors > 0 && upperBoundCertificates > 0 &&
		certificateFalseNegatives == 0 && baselineRowsInRejectedGroups == 0 &&
		baselineRowsInRejectedAttempts == 0 && unsupportedDescriptors == 0 &&
		fullRowsEqual && digestMatch ? 1 : 0;
	g_stats.phase7_gpu_upper_bound_reject_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_requested = 1;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_active = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_unique_keys = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_duplicate_units = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_unique_keys = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_duplicate_attempts = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_key_collisions = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_key_validation_mismatches = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_unsupported_key_descriptors = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority = 1;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_shadow_pass = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_requested = 1;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_active =
		(g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_active ||
		 scoreInfoKeyDescriptors > 0 || alignKeyDescriptors > 0) ? 1 : 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors +=
		scoreInfoKeyDescriptors;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_unique_keys +=
		scoreInfoUniqueKeys;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_duplicate_units +=
		scoreInfoDuplicateUnits;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors +=
		alignKeyDescriptors;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_unique_keys +=
		alignUniqueKeys;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_duplicate_attempts +=
		alignDuplicateAttempts;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_key_collisions +=
		keyCollisions;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_key_validation_mismatches +=
		cpuKeyValidationMismatches;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_unsupported_key_descriptors +=
		unsupportedKeyDescriptors;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_fallback_to_full_cpu_replay = 1;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_prealign_reduced = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_align_side_reduced = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal =
		(g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match =
		(g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_reduction_enabled = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_work_drop_enabled = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority =
		(g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_score_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_endpoint_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_cigar_traceback_output_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gpu_output_digest_authority = 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_shadow_pass =
		scoreInfoKeyDescriptors > 0 && alignKeyDescriptors > 0 &&
		keyCollisions == 0 && cpuKeyValidationMismatches == 0 &&
		unsupportedKeyDescriptors == 0 && fullRowsEqual && digestMatch ? 1 : 0;
	g_stats.phase7_gpu_exact_work_unit_compaction_first1_shadow_gate_first1_pass = 0;
}

void fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested()
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_groups = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempts = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_conservative_fallback_groups = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass = 0;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_groups = skippedGroups;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempts = skippedAttempts;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_conservative_fallback_groups = conservativeFallbackGroups;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score =
		skippedScoreInfoUpperBoundScore;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score =
		skippedAttemptUpperBoundScore;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt =
		skippedAttemptUpperBoundNt;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity =
		skippedAttemptUpperBoundIdentity;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability =
		skippedAttemptUpperBoundStability;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted =
		taskOutputCapacityExhausted;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state =
		scoreInfoLocalBreakState;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_cpu_align_authority = 1;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass = 1;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_requested = 1;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_active =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_active ||
		 active || gateFirst1Pass) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_tasks += tasks;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_host_assisted =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_host_assisted ||
		 hostAssisted) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_source_is_v5_descriptors =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_source_is_v5_descriptors ||
		 sourceIsV5Descriptors) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_consumer_reduces_before_host_transfer =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_consumer_reduces_before_host_transfer ||
		 gpuConsumerReducesBeforeHostTransfer) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_host_selected_attempts +=
		hostSelectedAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_prefix_descriptor_attempts +=
		prefixDescriptorAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_reference_align_attempts +=
		referenceAlignAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts +=
		candidateAlignAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_v5_candidate_align_attempts +=
		v5CandidateAlignAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts_less_than_v5 =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_candidate_align_attempts_less_than_v5 ||
		 candidateAlignAttemptsLessThanV5) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_descriptor_false_negatives +=
		descriptorFalseNegatives;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_missing_required_attempts +=
		missingRequiredAttempts;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_fallback_accounting_clean =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_fallback_accounting_clean ||
		 fallbackAccountingClean) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_cpu_align_authority =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_cpu_align_authority ||
		 cpuAlignAuthority) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_digest_match =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_digest_match ||
		 digestMatch) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_full_rows_equal =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_full_rows_equal ||
		 fullRowsEqual) ? 1 : 0;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_missing_rows +=
		missingRows;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_extra_rows +=
		extraRows;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_triplex_mismatches +=
		triplexMismatches;
	g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_gate_first1_pass =
		(g_stats.phase7_post_v5_3_host_assisted_consumer_feasibility_gate_first1_pass ||
		 gateFirst1Pass) ? 1 : 0;
}

bool select_attempts_impl(const std::string &query,
                          const std::vector<FasimGasal2Attempt> &attempts,
                          bool strict,
                          std::vector<FasimGasal2SelectedAlignment> *selected,
                          std::vector<FasimGasal2AttemptScoreTelemetry> *telemetry,
                          std::string *errorOut)
{
	if (selected != NULL)
	{
		selected->clear();
	}
	if (telemetry != NULL)
	{
		telemetry->clear();
	}
	if (!fasim_gasal2_enabled())
	{
		if (errorOut != NULL)
		{
			*errorOut = "FASIM_ALIGN_GASAL2 is not enabled";
		}
		return false;
	}
	if (query.empty() || attempts.empty() || selected == NULL)
	{
		return true;
	}

	std::lock_guard<std::mutex> lock(g_mutex);
	const auto totalStart = std::chrono::steady_clock::now();
	const int batchSize = gasal2_batch_size_default();
	record_effective_batch_size(batchSize);
	g_stats.score_prepass_enabled = true;
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (attempts[i].uses_target_view())
		{
			++g_stats.target_view_requests;
		}
	}

	std::vector<ScoreOnlyResult> scoreResults;
	if (!run_score_only(&g_score_state, query, attempts, batchSize, &scoreResults, errorOut))
	{
		++g_stats.fallbacks;
		return false;
	}

	std::vector<size_t> selectedAttemptIndexes;
	std::vector<std::string> selectionReasons;
	if (strict || env_enabled("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_STRICT"))
	{
		select_attempts_from_scores(attempts,
		                            scoreResults,
		                            &selectedAttemptIndexes,
		                            telemetry != NULL ? &selectionReasons : NULL);
	}
	if (telemetry != NULL)
	{
		telemetry->reserve(attempts.size());
		for (size_t i = 0; i < attempts.size(); ++i)
		{
			FasimGasal2AttemptScoreTelemetry row;
			row.attempt_index = static_cast<int64_t>(i);
			row.gpu_score = scoreResults[i].sw_score;
			row.gpu_query_end = scoreResults[i].query_end;
			row.gpu_ref_end_global = scoreResults[i].ref_end;
			row.selection_reason = selectionReasons.empty() ?
				"selection_reason_unavailable" : selectionReasons[i];
			row.selected = row.selection_reason == "threshold" ||
			               row.selection_reason == "best_fallback" ||
			               row.selection_reason == "last";
			telemetry->push_back(row);
		}
	}
	else
	{
		const int scoreMargin = env_int_or_zero("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_SCORE_MARGIN");
		const bool includeLast = !env_enabled("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST");
		const bool includeFallback = !env_enabled("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST");
		select_cpu_traceback_candidates_from_scores(attempts,
		                                            scoreResults,
		                                            scoreMargin,
		                                            includeLast,
		                                            includeFallback,
		                                            &selectedAttemptIndexes);
	}
	g_stats.score_selected_attempts += selectedAttemptIndexes.size();
	selected->reserve(selectedAttemptIndexes.size());
	for (size_t i = 0; i < selectedAttemptIndexes.size(); ++i)
	{
		const size_t selectedIndex = selectedAttemptIndexes[i];
		const FasimGasal2Attempt &attempt = attempts[selectedIndex];
		const ScoreOnlyResult &scoreResult = scoreResults[selectedIndex];
		FasimGasal2SelectedAlignment out;
		out.attempt_index = static_cast<int64_t>(selectedIndex);
		out.scoreinfo_index = attempt.scoreinfo_index;
		out.cutlength = attempt.cutlength;
		out.start = attempt.start;
		out.score_prepass_score = scoreResult.sw_score;
		out.score_prepass_query_end = scoreResult.query_end;
		out.score_prepass_ref_end = scoreResult.ref_end;
		const int scoreMargin = env_int_or_zero("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_SCORE_MARGIN");
		out.score_prepass_threshold_candidate =
			scoreResult.sw_score + scoreMargin >= attempt.prealign_score;
		out.score_prepass_fallback_candidate =
			scoreResult.sw_score != 0 &&
			scoreResult.ref_end == attempt.target_end_required_for_fallback + attempt.start;
		out.selected = true;
		selected->push_back(out);
	}
	g_stats.total_seconds += seconds_since(totalStart);
	return true;
}

bool fasim_gasal2_select_attempts(const std::string &query,
                                  const std::vector<FasimGasal2Attempt> &attempts,
                                  std::vector<FasimGasal2SelectedAlignment> *selected,
                                  std::string *errorOut)
{
	return select_attempts_impl(query, attempts, false, selected, NULL, errorOut);
}

bool fasim_gasal2_select_attempts_canonical_hybrid_v2(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<FasimGasal2SelectedAlignment> *selected,
	std::vector<FasimGasal2AttemptScoreTelemetry> *telemetry,
	std::string *errorOut)
{
	return select_attempts_impl(query, attempts, true, selected, telemetry, errorOut);
}

bool fasim_gasal2_select_attempts_strict(const std::string &query,
                                         const std::vector<FasimGasal2Attempt> &attempts,
                                         std::vector<FasimGasal2SelectedAlignment> *selected,
                                         std::string *errorOut)
{
	return select_attempts_impl(query, attempts, true, selected, NULL, errorOut);
}

void fasim_gasal2_record_cpu_traceback_replay(uint64_t replayAttempts,
                                              uint64_t selectedAttempts)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.cpu_traceback_replay_attempts += replayAttempts;
	g_stats.cpu_traceback_selected_attempts += selectedAttempts;
}

void fasim_gasal2_record_cpu_traceback_aligns(uint64_t alignCalls,
                                              uint64_t skippedAfterEmit,
                                              uint64_t rankCutoffSkipped)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.cpu_traceback_align_calls += alignCalls;
	g_stats.cpu_traceback_skipped_after_emit += skippedAfterEmit;
	g_stats.cpu_traceback_rank_cutoff_skipped += rankCutoffSkipped;
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
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.cpu_traceback_emit_threshold += thresholdEmits;
	g_stats.cpu_traceback_emit_best_fallback += bestFallbackEmits;
	g_stats.cpu_traceback_emit_last += lastEmits;
	g_stats.cpu_traceback_candidate_threshold += thresholdCandidates;
	g_stats.cpu_traceback_candidate_fallback += fallbackCandidates;
	g_stats.cpu_traceback_candidate_last += lastCandidates;
	g_stats.cpu_traceback_emit_rank1 += rank1Emits;
	g_stats.cpu_traceback_emit_rank2 += rank2Emits;
	g_stats.cpu_traceback_emit_rank3 += rank3Emits;
	g_stats.cpu_traceback_emit_rank4plus += rank4PlusEmits;
}

void fasim_gasal2_record_longtarget_bridge_timing(double attemptBuildSeconds,
                                                  double scoreSelectSeconds,
                                                  double cpuReplaySeconds,
                                                  double cpuSubstrSeconds,
                                                  double cpuAlignSeconds,
                                                  double cpuConvertSeconds)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.longtarget_attempt_build_seconds += attemptBuildSeconds;
	g_stats.longtarget_score_select_seconds += scoreSelectSeconds;
	g_stats.cpu_traceback_replay_seconds += cpuReplaySeconds;
	g_stats.cpu_traceback_substr_seconds += cpuSubstrSeconds;
	g_stats.cpu_traceback_align_seconds += cpuAlignSeconds;
	g_stats.cpu_traceback_convert_seconds += cpuConvertSeconds;
}
