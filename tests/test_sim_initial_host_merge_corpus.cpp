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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(
    const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs, const SimScanCudaCandidateState &rhs) {
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
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (memcmp(&lhs[i], &rhs[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_summaries_equal(const std::vector<SimScanCudaInitialRunSummary> &actual,
                                   const std::vector<SimScanCudaInitialRunSummary> &expected,
                                   const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected " << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < actual.size(); ++i)
    {
        if (memcmp(&actual[i], &expected[i], sizeof(SimScanCudaInitialRunSummary)) != 0)
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static std::string make_temp_dir()
{
    char buffer[] = "/tmp/longtarget-host-merge-corpus-XXXXXX";
    char *created = mkdtemp(buffer);
    if (created == NULL)
    {
        return std::string();
    }
    return std::string(created);
}

} // namespace

int main()
{
    bool ok = true;

    const std::string captureRootDir = make_temp_dir();
    ok = expect_true(!captureRootDir.empty(), "runtime capture root created") && ok;
    if (!captureRootDir.empty())
    {
        setenv("LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_DIR", captureRootDir.c_str(), 1);
        setenv("LONGTARGET_SIM_CUDA_LOCATE_MODE", "safe_workset", 1);
    }

    std::vector<SimScanCudaInitialRunSummary> summaries;
    summaries.push_back(SimScanCudaInitialRunSummary{17, packSimCoord(1, 1), 3, 2, 4, 4});
    summaries.push_back(SimScanCudaInitialRunSummary{13, packSimCoord(1, 2), 1, 4, 6, 5});
    summaries.push_back(SimScanCudaInitialRunSummary{8, packSimCoord(2, 1), 2, 1, 4, 1});
    summaries.push_back(SimScanCudaInitialRunSummary{16, packSimCoord(3, 3), 3, 3, 3, 3});
    summaries.push_back(SimScanCudaInitialRunSummary{11, packSimCoord(1, 2), 4, 0, 7, 2});

    SimKernelContext contextAfterApply(64, 128);
    SimKernelContext materializedContext(64, 128);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, contextAfterApply);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, materializedContext);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size() * 3),
                                    contextAfterApply);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size() * 3),
                                    materializedContext);

    std::vector<SimScanCudaCandidateState> expectedContextCandidates;
    collectSimContextCandidateStates(contextAfterApply, expectedContextCandidates);
    mergeSimCudaInitialRunSummariesIntoSafeStore(summaries, materializedContext);
    const std::vector<SimScanCudaCandidateState> expectedStoreMaterialized =
        materializedContext.safeCandidateStateStore.states;
    pruneSimSafeCandidateStateStore(materializedContext);
    const std::vector<SimScanCudaCandidateState> expectedStorePruned =
        materializedContext.safeCandidateStateStore.states;

    SimKernelContext runtimeCaptureContext(64, 128);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, runtimeCaptureContext);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size() * 3),
                                             runtimeCaptureContext,
                                             false);
    std::vector<std::string> runtimeCapturedCases;
    std::string error;
    ok = expect_true(listSimInitialHostMergeCorpusCases(captureRootDir, runtimeCapturedCases, &error),
                     error.empty() ? "runtime listSimInitialHostMergeCorpusCases" : error.c_str()) &&
         ok;
    ok = expect_equal_size(runtimeCapturedCases.size(), 1, "runtime captured case count") && ok;
    SimInitialHostMergeCorpusCase runtimeLoaded;
    if (!runtimeCapturedCases.empty())
    {
        ok = expect_true(loadSimInitialHostMergeCorpusCase(captureRootDir + "/" + runtimeCapturedCases[0],
                                                           runtimeLoaded,
                                                           &error),
                         error.empty() ? "runtime loadSimInitialHostMergeCorpusCase" : error.c_str()) &&
             ok;
        ok = expect_candidate_states_equal(runtimeLoaded.expectedContextCandidates,
                                           expectedContextCandidates,
                                           "runtime expected context candidates") &&
             ok;
        ok = expect_candidate_states_equal(runtimeLoaded.expectedStoreMaterialized,
                                           expectedStoreMaterialized,
                                           "runtime expected materialized store") &&
             ok;
        ok = expect_candidate_states_equal(runtimeLoaded.expectedStorePruned,
                                           expectedStorePruned,
                                           "runtime expected pruned store") &&
             ok;
    }

    SimInitialHostMergeCorpusCase corpus;
    corpus.caseId = "case-00000001";
    corpus.queryLength = 64;
    corpus.targetLength = 128;
    corpus.parmM = 1.0f;
    corpus.parmI = -1.0f;
    corpus.parmO = 1.0f;
    corpus.parmE = 1.0f;
    corpus.logicalEventCount = static_cast<uint64_t>(summaries.size() * 3);
    corpus.gpuMirrorRequested = true;
    corpus.runningMinAfterContextApply = static_cast<int>(contextAfterApply.runningMin);
    corpus.summaries = summaries;
    corpus.expectedContextCandidates = expectedContextCandidates;
    corpus.expectedStoreMaterialized = expectedStoreMaterialized;
    corpus.expectedStorePruned = expectedStorePruned;

    const std::string rootDir = make_temp_dir();
    ok = expect_true(!rootDir.empty(), "temporary corpus root created") && ok;

    error.clear();
    ok = expect_true(writeSimInitialHostMergeCorpusCase(rootDir, corpus, &error),
                     error.empty() ? "writeSimInitialHostMergeCorpusCase" : error.c_str()) &&
         ok;

    std::vector<std::string> listedCases;
    ok = expect_true(listSimInitialHostMergeCorpusCases(rootDir, listedCases, &error),
                     error.empty() ? "listSimInitialHostMergeCorpusCases" : error.c_str()) &&
         ok;
    ok = expect_equal_size(listedCases.size(), 1, "listed case count") && ok;

    SimInitialHostMergeCorpusCase loaded;
    ok = expect_true(loadSimInitialHostMergeCorpusCase(rootDir + "/" + corpus.caseId, loaded, &error),
                     error.empty() ? "loadSimInitialHostMergeCorpusCase" : error.c_str()) &&
         ok;
    ok = expect_summaries_equal(loaded.summaries, corpus.summaries, "loaded summaries") && ok;
    ok = expect_candidate_states_equal(loaded.expectedContextCandidates,
                                       corpus.expectedContextCandidates,
                                       "loaded expected context candidates") &&
         ok;
    ok = expect_candidate_states_equal(loaded.expectedStoreMaterialized,
                                       corpus.expectedStoreMaterialized,
                                       "loaded expected materialized store") &&
         ok;
    ok = expect_candidate_states_equal(loaded.expectedStorePruned,
                                       corpus.expectedStorePruned,
                                       "loaded expected pruned store") &&
         ok;

    SimInitialHostMergeReplayResult replay;
    ok = expect_true(replaySimInitialHostMergeCorpusCase(loaded, replay, &error),
                     error.empty() ? "replaySimInitialHostMergeCorpusCase" : error.c_str()) &&
         ok;
    ok = expect_true(verifySimInitialHostMergeReplay(loaded, replay, &error),
                     error.empty() ? "verifySimInitialHostMergeReplay" : error.c_str()) &&
         ok;
    ok = expect_true(replay.contextApplySeconds >= 0.0, "contextApplySeconds recorded") && ok;
    ok = expect_true(replay.storeMaterializeSeconds >= 0.0, "storeMaterializeSeconds recorded") && ok;
    ok = expect_true(replay.storePruneSeconds >= 0.0, "storePruneSeconds recorded") && ok;
    ok = expect_true(replay.fullHostMergeSeconds >= replay.contextApplySeconds,
                     "fullHostMergeSeconds covers contextApply") &&
         ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
