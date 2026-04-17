#include <algorithm>
#include <cmath>
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

static bool expect_near(double actual, double expected, double epsilon, const char *label)
{
    if (std::fabs(actual - expected) <= epsilon)
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
    ok = expect_true(replay.storeMaterializeResetSeconds >= 0.0,
                     "storeMaterializeResetSeconds recorded") &&
         ok;
    ok = expect_true(replay.storeMaterializeInsertSeconds >= 0.0,
                     "storeMaterializeInsertSeconds recorded") &&
         ok;
    ok = expect_true(replay.storeMaterializeUpdateSeconds >= 0.0,
                     "storeMaterializeUpdateSeconds recorded") &&
         ok;
    ok = expect_true(replay.storeMaterializeSnapshotCopySeconds >= 0.0,
                     "storeMaterializeSnapshotCopySeconds recorded") &&
         ok;
    ok = expect_equal_size(replay.storeMaterializeInsertedCount + replay.storeMaterializeUpdatedCount,
                           summaries.size(),
                           "storeMaterialize summary accounting") &&
         ok;
    ok = expect_equal_size(replay.storeMaterializePeakSize,
                           replay.storeMaterialized.size(),
                           "storeMaterializePeakSize matches final store") &&
         ok;
    ok = expect_true(replay.storeMaterializeRehashCount >= 0,
                     "storeMaterializeRehashCount recorded") &&
         ok;
    ok = expect_near(replay.storeMaterializeSeconds,
                     replay.storeMaterializeResetSeconds + replay.storeMaterializeInsertSeconds +
                         replay.storeMaterializeUpdateSeconds,
                     1e-9,
                     "storeMaterializeSeconds subphase total") &&
         ok;
    ok = expect_true(replay.storePruneSeconds >= 0.0, "storePruneSeconds recorded") && ok;
    ok = expect_true(replay.storeOtherMergeSeconds >= 0.0, "storeOtherMergeSeconds recorded") && ok;
    ok = expect_true(replay.fullHostMergeSeconds >= replay.contextApplySeconds,
                     "fullHostMergeSeconds covers contextApply") &&
         ok;
    ok = expect_near(replay.storeOtherMergeSeconds,
                     std::max(replay.fullHostMergeSeconds - replay.storeMaterializeSeconds - replay.storePruneSeconds,
                              0.0),
                     1e-9,
                     "storeOtherMergeSeconds residual") &&
         ok;

    SimInitialHostMergeReplayBenchmarkResult benchmark;
    ok = expect_true(benchmarkSimInitialHostMergeCorpusCase(loaded, 1, 3, benchmark, &error),
                     error.empty() ? "benchmarkSimInitialHostMergeCorpusCase" : error.c_str()) &&
         ok;
    ok = expect_equal_size(benchmark.iterations, 3, "benchmark iterations") && ok;
    ok = expect_true(benchmark.contextApply.meanSeconds >= 0.0, "benchmark contextApply mean recorded") && ok;
    ok = expect_true(benchmark.storeMaterialize.meanSeconds >= 0.0,
                     "benchmark storeMaterialize mean recorded") &&
         ok;
    ok = expect_true(benchmark.storeMaterializeReset.meanSeconds >= 0.0,
                     "benchmark storeMaterializeReset mean recorded") &&
         ok;
    ok = expect_true(benchmark.storeMaterializeInsert.meanSeconds >= 0.0,
                     "benchmark storeMaterializeInsert mean recorded") &&
         ok;
    ok = expect_true(benchmark.storeMaterializeUpdate.meanSeconds >= 0.0,
                     "benchmark storeMaterializeUpdate mean recorded") &&
         ok;
    ok = expect_true(benchmark.storeMaterializeSnapshotCopy.meanSeconds >= 0.0,
                     "benchmark storeMaterializeSnapshotCopy mean recorded") &&
         ok;
    ok = expect_equal_size(benchmark.storeMaterializeInsertedCount,
                           replay.storeMaterializeInsertedCount,
                           "benchmark storeMaterializeInsertedCount") &&
         ok;
    ok = expect_equal_size(benchmark.storeMaterializeUpdatedCount,
                           replay.storeMaterializeUpdatedCount,
                           "benchmark storeMaterializeUpdatedCount") &&
         ok;
    ok = expect_equal_size(benchmark.storeMaterializePeakSize,
                           replay.storeMaterializePeakSize,
                           "benchmark storeMaterializePeakSize") &&
         ok;
    ok = expect_equal_size(benchmark.storeMaterializeRehashCount,
                           replay.storeMaterializeRehashCount,
                           "benchmark storeMaterializeRehashCount") &&
         ok;
    ok = expect_near(benchmark.storeMaterialize.meanSeconds,
                     benchmark.storeMaterializeReset.meanSeconds +
                         benchmark.storeMaterializeInsert.meanSeconds +
                         benchmark.storeMaterializeUpdate.meanSeconds,
                     1e-9,
                     "benchmark storeMaterialize subphase total") &&
         ok;
    ok = expect_true(benchmark.storePrune.meanSeconds >= 0.0, "benchmark storePrune mean recorded") && ok;
    ok = expect_true(benchmark.storeOtherMerge.meanSeconds >= 0.0,
                     "benchmark storeOtherMerge mean recorded") &&
         ok;
    ok = expect_true(benchmark.fullHostMerge.meanSeconds >= benchmark.storeMaterialize.meanSeconds,
                     "benchmark fullHostMerge mean covers materialize") &&
         ok;
    ok = expect_true(benchmark.nsPerLogicalEvent >= 0.0, "benchmark nsPerLogicalEvent recorded") && ok;
    ok = expect_true(benchmark.nsPerMaterializedRecord >= 0.0,
                     "benchmark nsPerMaterializedRecord recorded") &&
         ok;
    ok = expect_true(benchmark.nsPerPrunedRecord >= 0.0, "benchmark nsPerPrunedRecord recorded") && ok;

    SimKernelContext invalidStoreContext(64, 128);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, invalidStoreContext);
    invalidStoreContext.safeCandidateStateStore.valid = false;
    invalidStoreContext.safeCandidateStateStore.states.push_back(expectedStoreMaterialized.front());
    invalidStoreContext.safeCandidateStateStore.startCoordToIndex
        [simScanCudaCandidateStateStartCoord(expectedStoreMaterialized.front())] = 0;
    double invalidResetSeconds = 0.0;
    double invalidInsertSeconds = 0.0;
    double invalidUpdateSeconds = 0.0;
    size_t invalidInsertedCount = 0;
    size_t invalidUpdatedCount = 0;
    size_t invalidPeakSize = 0;
    size_t invalidRehashCount = 0;
    mergeSimCudaInitialRunSummariesIntoSafeStore({},
                                                 invalidStoreContext,
                                                 &invalidResetSeconds,
                                                 &invalidInsertSeconds,
                                                 &invalidUpdateSeconds,
                                                 &invalidInsertedCount,
                                                 &invalidUpdatedCount,
                                                 &invalidPeakSize,
                                                 &invalidRehashCount);
    ok = expect_true(invalidStoreContext.safeCandidateStateStore.valid, "invalid store reset to valid") && ok;
    ok = expect_equal_size(invalidStoreContext.safeCandidateStateStore.states.size(),
                           0,
                           "invalid store reset clears states") &&
         ok;
    ok = expect_equal_size(invalidPeakSize, 0, "invalid store empty merge peak size resets to zero") && ok;
    ok = expect_equal_size(invalidInsertedCount, 0, "invalid store empty merge inserted count") && ok;
    ok = expect_equal_size(invalidUpdatedCount, 0, "invalid store empty merge updated count") && ok;
    ok = expect_true(invalidResetSeconds >= 0.0, "invalid store empty merge reset seconds recorded") && ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
