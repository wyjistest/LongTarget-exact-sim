#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

#include "../sim.h"

namespace
{

static std::vector<SimCandidate> sorted_candidates(const SimKernelContext &context)
{
    std::vector<SimCandidate> candidates(static_cast<size_t>(context.candidateCount));
    for (long i = 0; i < context.candidateCount; ++i)
    {
        candidates[static_cast<size_t>(i)] = context.candidates[static_cast<size_t>(i)];
    }
    std::sort(candidates.begin(), candidates.end(), [](const SimCandidate &lhs, const SimCandidate &rhs) {
        if (lhs.SCORE != rhs.SCORE) return lhs.SCORE < rhs.SCORE;
        if (lhs.STARI != rhs.STARI) return lhs.STARI < rhs.STARI;
        if (lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
        if (lhs.ENDI != rhs.ENDI) return lhs.ENDI < rhs.ENDI;
        if (lhs.ENDJ != rhs.ENDJ) return lhs.ENDJ < rhs.ENDJ;
        if (lhs.TOP != rhs.TOP) return lhs.TOP < rhs.TOP;
        if (lhs.BOT != rhs.BOT) return lhs.BOT < rhs.BOT;
        if (lhs.LEFT != rhs.LEFT) return lhs.LEFT < rhs.LEFT;
        return lhs.RIGHT < rhs.RIGHT;
    });
    return candidates;
}

static std::vector<SimScanCudaCandidateState> sorted_states(std::vector<SimScanCudaCandidateState> states)
{
    std::sort(states.begin(), states.end(), [](const SimScanCudaCandidateState &lhs,
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
    return states;
}

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static bool expect_false(bool value, const char *label)
{
    if (!value)
    {
        return true;
    }
    std::cerr << label << ": expected false, got true\n";
    return false;
}

static bool expect_equal_uint64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
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

static bool expect_equal_string(const char *actual, const char *expected, const char *label)
{
    if (std::strcmp(actual, expected) == 0)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_candidates_equal(const SimKernelContext &actual,
                                    const SimKernelContext &expected,
                                    const char *label)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        std::cerr << label << ": candidateCount expected "
                  << expected.candidateCount << ", got " << actual.candidateCount << "\n";
        return false;
    }
    const std::vector<SimCandidate> lhs = sorted_candidates(actual);
    const std::vector<SimCandidate> rhs = sorted_candidates(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (std::memcmp(&lhs[i], &rhs[i], sizeof(SimCandidate)) != 0)
        {
            std::cerr << label << ": candidate mismatch at " << i << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_safe_store_equal(const SimCandidateStateStore &actual,
                                    const SimCandidateStateStore &expected,
                                    const char *label)
{
    if (actual.valid != expected.valid)
    {
        std::cerr << label << ": valid expected " << expected.valid
                  << ", got " << actual.valid << "\n";
        return false;
    }
    const std::vector<SimScanCudaCandidateState> lhs = sorted_states(actual.states);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_states(expected.states);
    if (lhs.size() != rhs.size())
    {
        std::cerr << label << ": state count expected " << rhs.size()
                  << ", got " << lhs.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (std::memcmp(&lhs[i], &rhs[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": state mismatch at " << i << "\n";
            return false;
        }
    }
    return true;
}

static std::vector<SimScanCudaInitialRunSummary> make_handoff_case()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int i = 0; i < K; ++i)
    {
        summaries.push_back(SimScanCudaInitialRunSummary{
            500 + i,
            packSimCoord(10, static_cast<uint32_t>(i + 1)),
            static_cast<uint32_t>(1 + i),
            static_cast<uint32_t>(20 + i),
            static_cast<uint32_t>(20 + i),
            static_cast<uint32_t>(20 + i)});
    }
    summaries.push_back(SimScanCudaInitialRunSummary{10, packSimCoord(99, 1), 60, 70, 72, 71});
    summaries.push_back(SimScanCudaInitialRunSummary{300, packSimCoord(10, 1), 61, 18, 80, 80});
    summaries.push_back(SimScanCudaInitialRunSummary{1000, packSimCoord(77, 3), 62, 90, 90, 90});
    summaries.push_back(SimScanCudaInitialRunSummary{250, packSimCoord(77, 3), 63, 88, 95, 88});
    return summaries;
}

} // namespace

int main()
{
    bool ok = true;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF");
    ok = expect_false(simCudaInitialChunkedHandoffEnabledRuntime(),
                      "chunked handoff default disabled") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffChunkRowsRuntime(), 256,
                          "chunked handoff default rows") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffRingSlotsRuntime(), 3,
                          "chunked handoff default ring slots") && ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK", "2", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS", "4", 1);
    ok = expect_true(simCudaInitialChunkedHandoffEnabledRuntime(),
                     "chunked handoff opt-in enabled") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffChunkRowsRuntime(), 2,
                          "chunked handoff env rows") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffRingSlotsRuntime(), 4,
                          "chunked handoff env ring slots") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime(),
                             "canonical_env",
                             "chunked handoff canonical rows source") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime(),
                             "canonical_env",
                             "chunked handoff canonical ring source") && ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNK_ROWS", "64", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK", "128", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_RING_SLOTS", "2", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS", "5", 1);
    ok = expect_equal_int(simCudaInitialChunkedHandoffChunkRowsRuntime(), 128,
                          "chunked handoff canonical rows wins conflict") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime(),
                             "canonical_env",
                             "chunked handoff conflict rows source") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffRingSlotsRuntime(), 5,
                          "chunked handoff canonical ring wins conflict") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime(),
                             "canonical_env",
                             "chunked handoff conflict ring source") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS");
    ok = expect_equal_int(simCudaInitialChunkedHandoffChunkRowsRuntime(), 64,
                          "chunked handoff short rows alias") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime(),
                             "short_env",
                             "chunked handoff short rows source") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffRingSlotsRuntime(), 2,
                          "chunked handoff short ring alias") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime(),
                             "short_env",
                             "chunked handoff short ring source") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNK_ROWS");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_RING_SLOTS");
    setenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_CHUNK_ROWS", "7", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_RING_SLOTS", "6", 1);
    ok = expect_equal_int(simCudaInitialChunkedHandoffChunkRowsRuntime(), 7,
                          "chunked handoff compat rows alias") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime(),
                             "compat_env",
                             "chunked handoff compat rows source") && ok;
    ok = expect_equal_int(simCudaInitialChunkedHandoffRingSlotsRuntime(), 6,
                          "chunked handoff compat ring alias") && ok;
    ok = expect_equal_string(simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime(),
                             "compat_env",
                             "chunked handoff compat ring source") && ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK", "2", 1);
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS", "4", 1);

    const std::vector<SimScanCudaInitialRunSummary> summaries = make_handoff_case();
    SimKernelContext baseline(4096, 4096);
    SimKernelContext streaming(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baseline);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, streaming);

    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    baseline);
    mergeSimCudaInitialRunSummariesIntoSafeStore(summaries, baseline);
    pruneSimSafeCandidateStateStore(baseline);

    SimInitialChunkedHandoffStats stats;
    applySimCudaInitialRunSummariesChunkedHandoffForTest(
        summaries,
        static_cast<uint64_t>(summaries.size()),
        streaming,
        true,
        &stats);

    ok = expect_candidates_equal(streaming, baseline, "streaming chunk candidates") && ok;
    ok = expect_equal_int(static_cast<int>(streaming.runningMin),
                          static_cast<int>(baseline.runningMin),
                          "streaming chunk runningMin") && ok;
    ok = expect_safe_store_equal(streaming.safeCandidateStateStore,
                                 baseline.safeCandidateStateStore,
                                 "streaming chunk safe-store") && ok;
    ok = expect_equal_uint64(stats.chunkCount,
                             (static_cast<uint64_t>(summaries.size()) + 1u) / 2u,
                             "streaming chunk count") && ok;
    ok = expect_equal_uint64(stats.rowsPerChunk, 2, "streaming rows per chunk") && ok;
    ok = expect_equal_uint64(stats.ringSlots, 4, "streaming ring slots") && ok;
    ok = expect_equal_uint64(stats.pinnedAllocationFailures, 0,
                             "streaming pinned allocation failures") && ok;
    ok = expect_equal_uint64(stats.pageableFallbacks, 0,
                             "streaming pageable fallbacks") && ok;
    ok = expect_equal_uint64(stats.syncCopies, 0, "streaming sync copies") && ok;
    ok = expect_equal_uint64(stats.fallbackCount, 0, "streaming fallback count") && ok;
    ok = expect_equal_int(static_cast<int>(stats.fallbackReason),
                          static_cast<int>(SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_NONE),
                          "streaming fallback reason") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_CHUNK_ROWS");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_RING_SLOTS");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNK_ROWS");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_RING_SLOTS");

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
