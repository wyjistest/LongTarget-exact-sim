#ifndef FASIM_GPU_EXACT_BATCH_H
#define FASIM_GPU_EXACT_BATCH_H

#include "gasal2_align_bridge.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <ostream>
#include <utility>

inline bool fasim_gpu_exact_batch_v1_runtime()
{
	const char *value = std::getenv("FASIM_GPU_EXACT_BATCH_V1");
	return value != NULL && value[0] != '\0' && value[0] != '0';
}

// Shared with the endpoint bridge: changing this limit alone does not enable
// cross-task batching. Keep the historical bridge's default and bounds.
inline size_t fasim_streamed_attempt_batch_limit_v1()
{
	const char *value = std::getenv("FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH");
	const int configured = value == NULL ? 0 : std::atoi(value);
	return static_cast<size_t>(std::min(configured > 0 ? configured : 4096, 32768));
}

// This is the legacy attempt planner, shared by the serial and batched paths.
// In particular, preserve float accumulation (four rounds on this build),
// integer/float conversion order, window clipping, and group/round order.
inline void fasim_gpu_exact_plan_attempts(
	const std::string &target,
	const std::vector<StripedSmithWaterman::scoreInfo> &scoreInfos,
	int ntMin, std::vector<FasimGasal2Attempt> &attempts)
{
	attempts.clear();
	attempts.reserve(scoreInfos.size() * 5);
	for (size_t group = 0; group < scoreInfos.size(); ++group)
	{
		const StripedSmithWaterman::scoreInfo &info = scoreInfos[group];
		float identity = 0.6f;
		int round = 0;
		while (identity <= 1.0f)
		{
			int cutlength = static_cast<int>(info.score + 24) /
				(9 * identity - 4) + 1;
			cutlength = info.position - cutlength + 1 > 0 ?
				cutlength : info.position + 1;
			const int start = info.position - cutlength + 1;
			if (start >= 0 && cutlength > 0 &&
				start + cutlength <= static_cast<int>(target.size()))
			{
				FasimGasal2Attempt attempt;
				attempt.scoreinfo_index = static_cast<int>(group);
				attempt.cutlength = cutlength;
				attempt.start = start;
				attempt.prealign_score = info.score;
				attempt.target_end_required_for_fallback = cutlength - 1;
				attempt.nt_min_length = ntMin;
				attempt.identity_round = round;
				attempt.set_target_view(&target, static_cast<size_t>(start),
					static_cast<size_t>(cutlength));
				attempts.push_back(attempt);
			}
			identity += 0.1f;
			++round;
		}
	}
}

struct FasimGpuExactPreparedTask
{
	const std::string *query = NULL;
	const std::string *target = NULL;
	const std::vector<StripedSmithWaterman::scoreInfo> *score_infos = NULL;
	uint64_t task_index = 0;
	int nt_min = 0;
	bool ready = false;
	double planning_seconds = 0.0;
	std::vector<FasimGasal2Attempt> attempts;
	std::vector<FasimGasal2StreamedAttemptScore> endpoints;
	FasimGasal2StreamedAttemptScoreTelemetry telemetry;

	bool matches(const std::string &q, const std::string &t,
		const std::vector<StripedSmithWaterman::scoreInfo> &infos, int ntMin) const
	{
		return ready && query == &q && target == &t && score_infos == &infos &&
			nt_min == ntMin && endpoints.size() == attempts.size() &&
			telemetry.gpu_scored_requests == attempts.size();
	}
};

// A window holds complete tasks, normally at most batchLimit attempts.
// A single larger task is allowed and uses the existing bridge's splitting.
// Sequence/scoreInfo owners must remain alive and unchanged until consumption.
struct FasimGpuExactAttemptWindow
{
	size_t attempt_count = 0;
	double planning_seconds = 0.0;
	std::vector<FasimGpuExactPreparedTask> tasks;
	FasimGasal2StreamedAttemptScoreTelemetry telemetry;

	bool append(uint64_t taskIndex, const std::string &query,
		const std::string &target,
		const std::vector<StripedSmithWaterman::scoreInfo> &infos,
		int ntMin, size_t batchLimit)
	{
		const auto start = std::chrono::steady_clock::now();
		FasimGpuExactPreparedTask task;
		task.task_index = taskIndex;
		task.query = &query;
		task.target = &target;
		task.score_infos = &infos;
		task.nt_min = ntMin;
		fasim_gpu_exact_plan_attempts(target, infos, ntMin, task.attempts);
		const double elapsed = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - start).count();
		planning_seconds += elapsed;
		if (!tasks.empty() && task.attempts.size() >
			batchLimit - std::min(batchLimit, attempt_count))
		{
			// The one-task lookahead is discarded and replanned next window.
			tasks.front().planning_seconds += elapsed;
			return false;
		}
		task.planning_seconds = elapsed;
		attempt_count += task.attempts.size();
		tasks.push_back(std::move(task));
		return true;
	}

	bool score(std::string *errorOut)
	{
		const auto start = std::chrono::steady_clock::now();
		telemetry = FasimGasal2StreamedAttemptScoreTelemetry();
		if (errorOut != NULL) errorOut->clear();
		if (tasks.empty())
		{
			if (errorOut != NULL) *errorOut = "empty_attempt_window";
			return false;
		}
		std::vector<FasimGasal2Attempt> flat;
		flat.reserve(attempt_count);
		for (FasimGpuExactPreparedTask &task : tasks)
		{
			task.ready = false;
			if (task.query == NULL || task.query != tasks.front().query ||
				task.target == NULL || task.score_infos == NULL ||
				(!task.score_infos->empty() && task.attempts.empty()))
			{
				if (errorOut != NULL) *errorOut = "invalid_attempt_window_task";
				return false;
			}
			flat.insert(flat.end(), task.attempts.begin(), task.attempts.end());
		}
		if (flat.size() != attempt_count)
		{
			if (errorOut != NULL) *errorOut = "attempt_window_count_mismatch";
			return false;
		}
		std::vector<FasimGasal2StreamedAttemptScore> scores;
		if (!flat.empty() && !fasim_gasal2_streamed_attempt_score_v1(
			*tasks.front().query, flat, &scores, &telemetry, errorOut)) return false;
		if (scores.size() != attempt_count ||
			telemetry.gpu_scored_requests != attempt_count)
		{
			if (errorOut != NULL) *errorOut = "attempt_window_endpoint_count_mismatch";
			return false;
		}
		size_t offset = 0;
		for (FasimGpuExactPreparedTask &task : tasks)
		{
			task.endpoints.assign(scores.begin() + offset,
				scores.begin() + offset + task.attempts.size());
			task.telemetry = FasimGasal2StreamedAttemptScoreTelemetry();
			task.telemetry.requests = task.attempts.size();
			task.telemetry.gpu_scored_requests = task.attempts.size();
			task.ready = true;
			offset += task.attempts.size();
		}
		telemetry.total_seconds = std::chrono::duration<double>(
			std::chrono::steady_clock::now() - start).count();
		// Attribute shared batch timing/counts once, to the first nonempty task.
		// Per-task request counts remain local. These times are accounting, not
		// individual task latency; summing the report reproduces window totals.
		for (FasimGpuExactPreparedTask &task : tasks)
			if (!task.attempts.empty())
			{
				task.telemetry.batches = telemetry.batches;
				task.telemetry.gpu_seconds = telemetry.gpu_seconds;
				task.telemetry.h2d_seconds = telemetry.h2d_seconds;
				task.telemetry.d2h_seconds = telemetry.d2h_seconds;
				task.telemetry.total_seconds = telemetry.total_seconds;
				break;
			}
		return true;
	}
};

struct FasimGpuExactBatchStats
{
	uint64_t windows = 0, tasks = 0, attempts = 0, endpoint_batches = 0;
	uint64_t max_window_tasks = 0, max_window_attempts = 0;
	double planning_seconds = 0.0, score_seconds = 0.0;
	double gpu_seconds = 0.0, h2d_seconds = 0.0, d2h_seconds = 0.0;

	void add(const FasimGpuExactAttemptWindow &window)
	{
		++windows;
		tasks += window.tasks.size();
		attempts += window.attempt_count;
		endpoint_batches += window.telemetry.batches;
		max_window_tasks = std::max(max_window_tasks,
			static_cast<uint64_t>(window.tasks.size()));
		max_window_attempts = std::max(max_window_attempts,
			static_cast<uint64_t>(window.attempt_count));
		planning_seconds += window.planning_seconds;
		score_seconds += window.telemetry.total_seconds;
		gpu_seconds += window.telemetry.gpu_seconds;
		h2d_seconds += window.telemetry.h2d_seconds;
		d2h_seconds += window.telemetry.d2h_seconds;
	}

	void report(std::ostream &out) const
	{
		out << "benchmark.fasim_gpu_exact_batch_v1.active=1\n"
			<< "benchmark.fasim_gpu_exact_batch_v1.attempt_limit="
			<< fasim_streamed_attempt_batch_limit_v1() << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.windows=" << windows << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.tasks=" << tasks << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.attempts=" << attempts << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.endpoint_batches=" << endpoint_batches << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.max_window_tasks=" << max_window_tasks << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.max_window_attempts=" << max_window_attempts << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.planning_seconds=" << planning_seconds << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.score_seconds=" << score_seconds << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.gpu_seconds=" << gpu_seconds << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.h2d_seconds=" << h2d_seconds << '\n'
			<< "benchmark.fasim_gpu_exact_batch_v1.d2h_seconds=" << d2h_seconds << '\n';
	}
};

#endif
