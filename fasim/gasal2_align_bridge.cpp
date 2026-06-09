#include "gasal2_align_bridge.h"

#include "../.tmp/GASAL2/include/gasal_header.h"
#include "ssw.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
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

std::mutex g_mutex;
FasimGasal2Stats g_stats;
BridgeState g_score_state;
BridgeState g_traceback_state;

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
	state->params->gapo = 12;
	state->params->gape = 4;
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
                                 std::vector<size_t> *selectedAttemptIndexes)
{
	selectedAttemptIndexes->clear();
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
			++g_stats.score_prepass_select_best_fallback;
		}
		else if (currentScoreInfo >= 0 && haveLast && !emitted && lastScore != 0)
		{
			selectedAttemptIndexes->push_back(lastIndex);
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
				++g_stats.nt_sum_span_pruned_attempts;
				prunedCurrentGroup = true;
				continue;
			}
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
			const auto waitStart = std::chrono::steady_clock::now();
			wait_for_all_score(state, streamCounts, streamStarts, attempts, *results, errorOut);
			const double waited = seconds_since(waitStart);
			g_stats.wait_seconds += waited;
			g_stats.score_wait_seconds += waited;
		}
	}
	const auto waitStart = std::chrono::steady_clock::now();
	wait_for_all_score(state, streamCounts, streamStarts, attempts, *results, errorOut);
	const double waited = seconds_since(waitStart);
	g_stats.wait_seconds += waited;
	g_stats.score_wait_seconds += waited;
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
			const auto waitStart = std::chrono::steady_clock::now();
			wait_for_all_traceback(state, streamCounts, streamStarts, attempts, *alignments, errorOut);
			const double waited = seconds_since(waitStart);
			g_stats.wait_seconds += waited;
			g_stats.traceback_wait_seconds += waited;
		}
	}
	const auto waitStart = std::chrono::steady_clock::now();
	wait_for_all_traceback(state, streamCounts, streamStarts, attempts, *alignments, errorOut);
	const double waited = seconds_since(waitStart);
	g_stats.wait_seconds += waited;
	g_stats.traceback_wait_seconds += waited;
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
	       env_enabled("FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW");
}

bool fasim_gasal2_longtarget_bridge_enabled()
{
	return env_enabled("FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE") ||
	       env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO") ||
	       env_enabled("FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW");
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
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_replay_attempts=" << stats.cpu_traceback_replay_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_selected_attempts=" << stats.cpu_traceback_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_align_calls=" << stats.cpu_traceback_align_calls << "\n";
	std::cerr << "benchmark.fasim_gasal2_cpu_traceback_skipped_after_emit=" << stats.cpu_traceback_skipped_after_emit << "\n";
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

	std::vector<StripedSmithWaterman::Alignment> tracebackAlignments;
	if (!run_traceback(&g_traceback_state, query, tracebackAttempts, batchSize, &tracebackAlignments, errorOut))
	{
		++g_stats.fallbacks;
		return false;
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

bool select_attempts_impl(const std::string &query,
                          const std::vector<FasimGasal2Attempt> &attempts,
                          bool strict,
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
	if (strict || env_enabled("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_STRICT"))
	{
		select_attempts_from_scores(attempts, scoreResults, &selectedAttemptIndexes);
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
	return select_attempts_impl(query, attempts, false, selected, errorOut);
}

bool fasim_gasal2_select_attempts_strict(const std::string &query,
                                         const std::vector<FasimGasal2Attempt> &attempts,
                                         std::vector<FasimGasal2SelectedAlignment> *selected,
                                         std::string *errorOut)
{
	return select_attempts_impl(query, attempts, true, selected, errorOut);
}

void fasim_gasal2_record_cpu_traceback_replay(uint64_t replayAttempts,
                                              uint64_t selectedAttempts)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.cpu_traceback_replay_attempts += replayAttempts;
	g_stats.cpu_traceback_selected_attempts += selectedAttempts;
}

void fasim_gasal2_record_cpu_traceback_aligns(uint64_t alignCalls,
                                              uint64_t skippedAfterEmit)
{
	std::lock_guard<std::mutex> lock(g_mutex);
	g_stats.cpu_traceback_align_calls += alignCalls;
	g_stats.cpu_traceback_skipped_after_emit += skippedAfterEmit;
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
