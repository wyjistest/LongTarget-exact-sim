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

static bool expect_equal_uint64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
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

static bool expect_candidates_equal(const SimKernelContext &actual,
                                    const SimKernelContext &expected,
                                    const char *label)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        std::cerr << label << ": candidateCount mismatch expected "
                  << expected.candidateCount << ", got " << actual.candidateCount << "\n";
        return false;
    }

    const std::vector<SimCandidate> lhs = sorted_candidates(actual);
    const std::vector<SimCandidate> rhs = sorted_candidates(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (std::memcmp(&lhs[i], &rhs[i], sizeof(SimCandidate)) != 0)
        {
            std::cerr << label << ": candidate mismatch at sorted index " << i
                      << " expected(score=" << rhs[i].SCORE
                      << ", start=" << rhs[i].STARI << "," << rhs[i].STARJ
                      << ", end=" << rhs[i].ENDI << "," << rhs[i].ENDJ
                      << ", box=" << rhs[i].TOP << "," << rhs[i].BOT
                      << "," << rhs[i].LEFT << "," << rhs[i].RIGHT
                      << ") got(score=" << lhs[i].SCORE
                      << ", start=" << lhs[i].STARI << "," << lhs[i].STARJ
                      << ", end=" << lhs[i].ENDI << "," << lhs[i].ENDJ
                      << ", box=" << lhs[i].TOP << "," << lhs[i].BOT
                      << "," << lhs[i].LEFT << "," << lhs[i].RIGHT << ")\n";
            return false;
        }
    }
    return true;
}

static bool run_case(const char *label,
                     const std::vector<SimScanCudaInitialRunSummary> &summaries,
                     int chunkSize,
                     uint64_t expectedChunks,
                     uint64_t expectedSkippedChunks,
                     uint64_t expectedReplayedChunks,
                     uint64_t expectedSkippedSummaries,
                     uint64_t expectedReplayedSummaries)
{
    SimKernelContext baseline(4096, 4096);
    SimKernelContext chunkSkipped(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baseline);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, chunkSkipped);

    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    baseline);
    SimInitialContextApplyChunkSkipStats stats;
    mergeSimCudaInitialRunSummariesWithContextApplyChunkSkip(
        summaries,
        static_cast<uint64_t>(summaries.size()),
        chunkSkipped,
        chunkSize,
        &stats);

    bool ok = true;
    ok = expect_candidates_equal(chunkSkipped, baseline, label) && ok;
    ok = expect_equal_uint64(stats.chunkCount, expectedChunks, "chunk count") && ok;
    ok = expect_equal_uint64(stats.chunkSkippedCount, expectedSkippedChunks, "skipped chunks") && ok;
    ok = expect_equal_uint64(stats.chunkReplayedCount, expectedReplayedChunks, "replayed chunks") && ok;
    ok = expect_equal_uint64(stats.summarySkippedCount, expectedSkippedSummaries, "skipped summaries") && ok;
    ok = expect_equal_uint64(stats.summaryReplayedCount, expectedReplayedSummaries, "replayed summaries") && ok;
    return ok;
}

static std::vector<SimScanCudaInitialRunSummary> make_full_frontier_with_revisit()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int offset = 0; offset < K; ++offset)
    {
        summaries.push_back(SimScanCudaInitialRunSummary{
            1000 + offset,
            packSimCoord(100, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(100 + offset),
            static_cast<uint32_t>(100 + offset),
            static_cast<uint32_t>(100 + offset)});
    }
    summaries.push_back(SimScanCudaInitialRunSummary{1, packSimCoord(200, 1), 2, 500, 500, 500});
    summaries.push_back(SimScanCudaInitialRunSummary{2000, packSimCoord(100, 1), 3, 600, 600, 600});
    return summaries;
}

} // namespace

int main()
{
    bool ok = true;

    ok = run_case("existing candidate bounds-covered no-op",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(1, 1), 5, 10, 12, 10},
                      SimScanCudaInitialRunSummary{50, packSimCoord(1, 1), 5, 10, 12, 10}},
                  1,
                  2,
                  1,
                  1,
                  1,
                  1) &&
         ok;

    ok = run_case("same-score tie must replay",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(2, 1), 5, 10, 12, 10},
                      SimScanCudaInitialRunSummary{100, packSimCoord(2, 1), 5, 10, 12, 10}},
                  1,
                  2,
                  0,
                  2,
                  0,
                  2) &&
         ok;

    ok = run_case("same-start lower-score bounds update must replay",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(3, 1), 5, 10, 10, 10},
                      SimScanCudaInitialRunSummary{90, packSimCoord(3, 1), 6, 8, 12, 8}},
                  1,
                  2,
                  0,
                  2,
                  0,
                  2) &&
         ok;

    ok = run_case("row-order top expansion must replay",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(4, 1), 5, 10, 10, 10},
                      SimScanCudaInitialRunSummary{90, packSimCoord(4, 1), 4, 10, 10, 10}},
                  1,
                  2,
                  0,
                  2,
                  0,
                  2) &&
         ok;

    ok = run_case("block-split chunk of covered no-ops can skip",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(5, 1), 5, 10, 10, 10},
                      SimScanCudaInitialRunSummary{101, packSimCoord(5, 2), 5, 20, 20, 20},
                      SimScanCudaInitialRunSummary{20, packSimCoord(5, 1), 5, 10, 10, 10},
                      SimScanCudaInitialRunSummary{21, packSimCoord(5, 2), 5, 20, 20, 20}},
                  2,
                  2,
                  1,
                  1,
                  2,
                  2) &&
         ok;

    ok = run_case("missing candidate lower-score must replay",
                  std::vector<SimScanCudaInitialRunSummary>{
                      SimScanCudaInitialRunSummary{100, packSimCoord(6, 1), 5, 10, 10, 10},
                      SimScanCudaInitialRunSummary{1, packSimCoord(6, 2), 6, 20, 20, 20}},
                  1,
                  2,
                  0,
                  2,
                  0,
                  2) &&
         ok;

    ok = run_case("production-K eviction and repeated hit after eviction must replay",
                  make_full_frontier_with_revisit(),
                  K,
                  2,
                  0,
                  2,
                  0,
                  static_cast<uint64_t>(K + 2)) &&
         ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_CONTEXT_APPLY_CHUNK_SKIP", "1", 1);
    ok = expect_true(simCudaInitialContextApplyChunkSkipEnabledRuntime(),
                     "chunk skip runtime opt-in enabled") &&
         ok;

    uint64_t chunksBefore = 0;
    uint64_t skippedChunksBefore = 0;
    uint64_t replayedChunksBefore = 0;
    uint64_t skippedSummariesBefore = 0;
    uint64_t replayedSummariesBefore = 0;
    getSimInitialContextApplyChunkSkipStats(chunksBefore,
                                            skippedChunksBefore,
                                            replayedChunksBefore,
                                            skippedSummariesBefore,
                                            replayedSummariesBefore);

    SimKernelContext telemetryContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, telemetryContext);
    std::vector<SimScanCudaInitialRunSummary> telemetrySummaries;
    for (int i = 0; i < 256; ++i)
    {
        const uint32_t startJ = static_cast<uint32_t>(1 + i % K);
        telemetrySummaries.push_back(SimScanCudaInitialRunSummary{
            100 + (i % K),
            packSimCoord(7, startJ),
            5,
            static_cast<uint32_t>(10 + i % K),
            static_cast<uint32_t>(10 + i % K),
            static_cast<uint32_t>(10 + i % K)});
    }
    for (int i = 0; i < 256; ++i)
    {
        const uint32_t startJ = static_cast<uint32_t>(1 + i % K);
        telemetrySummaries.push_back(SimScanCudaInitialRunSummary{
            1,
            packSimCoord(7, startJ),
            5,
            static_cast<uint32_t>(10 + i % K),
            static_cast<uint32_t>(10 + i % K),
            static_cast<uint32_t>(10 + i % K)});
    }
    applySimCudaInitialRunSummariesToContext(telemetrySummaries,
                                             static_cast<uint64_t>(telemetrySummaries.size()),
                                             telemetryContext,
                                             true);

    uint64_t chunksAfter = 0;
    uint64_t skippedChunksAfter = 0;
    uint64_t replayedChunksAfter = 0;
    uint64_t skippedSummariesAfter = 0;
    uint64_t replayedSummariesAfter = 0;
    getSimInitialContextApplyChunkSkipStats(chunksAfter,
                                            skippedChunksAfter,
                                            replayedChunksAfter,
                                            skippedSummariesAfter,
                                            replayedSummariesAfter);
    ok = expect_true(chunksAfter > chunksBefore, "telemetry records chunk count") && ok;
    ok = expect_true(skippedChunksAfter > skippedChunksBefore, "telemetry records skipped chunks") && ok;
    ok = expect_true(replayedChunksAfter > replayedChunksBefore, "telemetry records replayed chunks") && ok;
    ok = expect_true(skippedSummariesAfter > skippedSummariesBefore, "telemetry records skipped summaries") && ok;
    ok = expect_true(replayedSummariesAfter > replayedSummariesBefore, "telemetry records replayed summaries") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CONTEXT_APPLY_CHUNK_SKIP");

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
