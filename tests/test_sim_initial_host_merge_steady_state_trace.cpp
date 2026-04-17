#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../sim.h"

namespace
{

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static std::string make_temp_dir()
{
    char buffer[] = "/tmp/longtarget-steady-state-trace-XXXXXX";
    char *created = mkdtemp(buffer);
    if (created == NULL)
    {
        return std::string();
    }
    return std::string(created);
}

static SimScanCudaInitialRunSummary make_summary(int score,
                                                 long startI,
                                                 long startJ,
                                                 uint32_t endI,
                                                 uint32_t minEndJ,
                                                 uint32_t maxEndJ,
                                                 uint32_t scoreEndJ)
{
    SimScanCudaInitialRunSummary summary;
    summary.score = score;
    summary.startCoord = packSimCoord(startI, startJ);
    summary.endI = endI;
    summary.minEndJ = minEndJ;
    summary.maxEndJ = maxEndJ;
    summary.scoreEndJ = scoreEndJ;
    return summary;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(
    const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs,
                                               const SimScanCudaCandidateState &rhs) {
        const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
        const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
        if (lhsStart != rhsStart) return lhsStart < rhsStart;
        if (lhs.score != rhs.score) return lhs.score < rhs.score;
        if (lhs.endI != rhs.endI) return lhs.endI < rhs.endI;
        if (lhs.endJ != rhs.endJ) return lhs.endJ < rhs.endJ;
        if (lhs.top != rhs.top) return lhs.top < rhs.top;
        if (lhs.bot != rhs.bot) return lhs.bot < rhs.bot;
        if (lhs.left != rhs.left) return lhs.left < rhs.left;
        return lhs.right < rhs.right;
    });
    return sorted;
}

static bool expect_candidate_states_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                         const std::vector<SimScanCudaCandidateState> &expected,
                                         const char *label)
{
    const std::vector<SimScanCudaCandidateState> lhs = sorted_candidate_states(actual);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_candidate_states(expected);
    if (lhs.size() != rhs.size())
    {
        std::cerr << label << ": size mismatch expected " << rhs.size() << ", got " << lhs.size() << "\n";
        return false;
    }
    for (size_t index = 0; index < lhs.size(); ++index)
    {
        if (memcmp(&lhs[index], &rhs[index], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": mismatch at index " << index << "\n";
            return false;
        }
    }
    return true;
}

} // namespace

int main()
{
    bool ok = true;

    std::vector<SimScanCudaInitialRunSummary> summaries;
    summaries.reserve(static_cast<size_t>(K) + 3);
    for (int candidateIndex = 0; candidateIndex < K; ++candidateIndex)
    {
        summaries.push_back(make_summary(100 + candidateIndex,
                                         1000 + candidateIndex,
                                         2000 + candidateIndex,
                                         static_cast<uint32_t>(10 + candidateIndex),
                                         static_cast<uint32_t>(20 + candidateIndex),
                                         static_cast<uint32_t>(20 + candidateIndex),
                                         static_cast<uint32_t>(20 + candidateIndex)));
    }
    summaries.push_back(make_summary(250, 1010, 2010, 1000, 400, 420, 415));
    summaries.push_back(make_summary(200, 1010, 2010, 500, 405, 410, 408));
    summaries.push_back(make_summary(300, 9000, 9001, 800, 100, 160, 140));

    SimInitialHostMergeCorpusCase corpus;
    corpus.caseId = "case-00000417";
    corpus.queryLength = 4096;
    corpus.targetLength = 8192;
    corpus.parmM = 1.0f;
    corpus.parmI = -1.0f;
    corpus.parmO = 1.0f;
    corpus.parmE = 1.0f;
    corpus.logicalEventCount = static_cast<uint64_t>(summaries.size());
    corpus.gpuMirrorRequested = false;
    corpus.summaries = summaries;

    SimInitialHostMergeSteadyStateTraceCase trace;
    std::string error;
    ok = expect_true(captureSimInitialHostMergeSteadyStateTraceCase(corpus, trace, &error),
                     error.empty() ? "captureSimInitialHostMergeSteadyStateTraceCase" : error.c_str()) &&
         ok;

    ok = expect_equal_int(trace.seedRunningMin, 100, "seedRunningMin") && ok;
    ok = expect_equal_int(trace.expectedFinalRunningMin, 101, "expectedFinalRunningMin") && ok;
    ok = expect_equal_size(trace.seedContextCandidates.size(), static_cast<size_t>(K),
                           "seedContextCandidates size") &&
         ok;
    ok = expect_equal_size(trace.expectedFinalContextCandidates.size(), static_cast<size_t>(K),
                           "expectedFinalContextCandidates size") &&
         ok;
    ok = expect_equal_size(trace.events.size(), 3, "post-fill event count") && ok;
    ok = expect_equal_u64(trace.postFillFullSetMissCount, 1, "postFillFullSetMissCount") && ok;

    if (trace.events.size() == 3)
    {
        ok = expect_equal_int(static_cast<int>(trace.events[0].referenceEventKind),
                              static_cast<int>(SIM_INITIAL_HOST_MERGE_STEADY_STATE_TRACE_EVENT_HIT_UPDATE),
                              "event[0] kind") &&
             ok;
        ok = expect_equal_int(static_cast<int>(trace.events[1].referenceEventKind),
                              static_cast<int>(SIM_INITIAL_HOST_MERGE_STEADY_STATE_TRACE_EVENT_HIT_NOOP),
                              "event[1] kind") &&
             ok;
        ok = expect_equal_int(static_cast<int>(trace.events[2].referenceEventKind),
                              static_cast<int>(SIM_INITIAL_HOST_MERGE_STEADY_STATE_TRACE_EVENT_FULL_SET_MISS),
                              "event[2] kind") &&
             ok;
        ok = expect_equal_int(trace.events[2].victimCandidateIndexBefore,
                              0,
                              "full-set miss victimCandidateIndexBefore") &&
             ok;
        ok = expect_equal_u64(trace.events[2].victimStartCoordBefore,
                              packSimCoord(1000, 2000),
                              "full-set miss victimStartCoordBefore") &&
             ok;
        ok = expect_equal_int(trace.events[2].victimScoreBefore,
                              100,
                              "full-set miss victimScoreBefore") &&
             ok;
    }

    const std::string rootDir = make_temp_dir();
    ok = expect_true(!rootDir.empty(), "temporary trace root created") && ok;
    ok = expect_true(writeSimInitialHostMergeSteadyStateTraceCase(rootDir, trace, &error),
                     error.empty() ? "writeSimInitialHostMergeSteadyStateTraceCase" : error.c_str()) &&
         ok;

    SimInitialHostMergeSteadyStateTraceCase loaded;
    ok = expect_true(loadSimInitialHostMergeSteadyStateTraceCase(rootDir + "/" + trace.caseId, loaded, &error),
                     error.empty() ? "loadSimInitialHostMergeSteadyStateTraceCase" : error.c_str()) &&
         ok;
    ok = expect_equal_int(loaded.seedRunningMin, trace.seedRunningMin, "loaded seedRunningMin") && ok;
    ok = expect_equal_int(loaded.expectedFinalRunningMin,
                          trace.expectedFinalRunningMin,
                          "loaded expectedFinalRunningMin") &&
         ok;
    ok = expect_equal_size(loaded.events.size(), trace.events.size(), "loaded event count") && ok;
    ok = expect_candidate_states_equal(loaded.seedContextCandidates,
                                       trace.seedContextCandidates,
                                       "loaded seedContextCandidates") &&
         ok;
    ok = expect_candidate_states_equal(loaded.expectedFinalContextCandidates,
                                       trace.expectedFinalContextCandidates,
                                       "loaded expectedFinalContextCandidates") &&
         ok;

    SimInitialHostMergeSteadyStateReplayResult referenceReplay;
    ok = expect_true(replaySimInitialHostMergeSteadyStateTraceCase(
                         loaded,
                         SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_REFERENCE,
                         referenceReplay,
                         &error),
                     error.empty() ? "reference steady-state replay" : error.c_str()) &&
         ok;
    ok = expect_true(verifySimInitialHostMergeSteadyStateTraceReplay(loaded, referenceReplay, &error),
                     error.empty() ? "verify reference steady-state replay" : error.c_str()) &&
         ok;
    ok = expect_equal_size(referenceReplay.fullSetMissCount, 1, "reference fullSetMissCount") && ok;
    ok = expect_equal_size(referenceReplay.hitUpdateCount, 1, "reference hitUpdateCount") && ok;
    ok = expect_equal_size(referenceReplay.hitNoopCount, 1, "reference hitNoopCount") && ok;

    SimInitialHostMergeSteadyStateReplayResult specializedReplay;
    ok = expect_true(replaySimInitialHostMergeSteadyStateTraceCase(
                         loaded,
                         SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_SPECIALIZED,
                         specializedReplay,
                         &error),
                     error.empty() ? "specialized steady-state replay" : error.c_str()) &&
         ok;
    ok = expect_true(verifySimInitialHostMergeSteadyStateTraceReplay(loaded, specializedReplay, &error),
                     error.empty() ? "verify specialized steady-state replay" : error.c_str()) &&
         ok;
    ok = expect_equal_size(specializedReplay.fullSetMissCount, 1, "specialized fullSetMissCount") && ok;
    ok = expect_equal_size(specializedReplay.hitUpdateCount, 1, "specialized hitUpdateCount") && ok;
    ok = expect_equal_size(specializedReplay.hitNoopCount, 1, "specialized hitNoopCount") && ok;
    ok = expect_candidate_states_equal(specializedReplay.finalContextCandidates,
                                       referenceReplay.finalContextCandidates,
                                       "specialized finalContextCandidates") &&
         ok;
    ok = expect_equal_int(specializedReplay.finalRunningMin,
                          referenceReplay.finalRunningMin,
                          "specialized finalRunningMin") &&
         ok;

    if (!ok)
    {
        return 1;
    }
    return 0;
}
