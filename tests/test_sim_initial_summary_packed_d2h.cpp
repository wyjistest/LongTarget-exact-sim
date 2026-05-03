#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_scan_cuda.h"

namespace
{

static uint64_t pack_coord(uint32_t i, uint32_t j)
{
    return (static_cast<uint64_t>(i) << 32) | static_cast<uint64_t>(j);
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

static bool expect_equal_summary(const SimScanCudaInitialRunSummary &actual,
                                 const SimScanCudaInitialRunSummary &expected,
                                 const char *label)
{
    if (actual.score == expected.score &&
        actual.startCoord == expected.startCoord &&
        actual.endI == expected.endI &&
        actual.minEndJ == expected.minEndJ &&
        actual.maxEndJ == expected.maxEndJ &&
        actual.scoreEndJ == expected.scoreEndJ)
    {
        return true;
    }
    std::cerr << label << ": summary mismatch\n";
    return false;
}

static bool expect_equal_summaries(const std::vector<SimScanCudaInitialRunSummary> &actual,
                                   const std::vector<SimScanCudaInitialRunSummary> &expected,
                                   const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected " << expected.size()
                  << ", got " << actual.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < actual.size(); ++i)
    {
        if (!expect_equal_summary(actual[i], expected[i], label))
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static void fill_score_matrix(int scoreMatrix[128][128])
{
    for (int i = 0; i < 128; ++i)
    {
        for (int j = 0; j < 128; ++j)
        {
            scoreMatrix[i][j] = -4;
        }
    }
    scoreMatrix['A']['A'] = 5;
    scoreMatrix['C']['C'] = 5;
    scoreMatrix['G']['G'] = 5;
    scoreMatrix['T']['T'] = 5;
}

static std::vector<SimScanCudaInitialRunSummary> run_summaries(bool packedD2H,
                                                                SimScanCudaBatchResult &batchResult)
{
    if (packedD2H)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PACKED_SUMMARY_D2H", "1", 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PACKED_SUMMARY_D2H");
    }

    int scoreMatrix[128][128] = {};
    fill_score_matrix(scoreMatrix);

    const char *query = "ACGTACGT";
    const char *target = "ACGGACGT";
    const int queryLength = 8;
    const int targetLength = 8;
    const int gapOpen = 16;
    const int gapExtend = 4;
    const int eventScoreFloor = 5;

    std::vector<SimScanCudaInitialRunSummary> summaries;
    std::vector<SimScanCudaCandidateState> candidateStates;
    std::vector<SimScanCudaCandidateState> allCandidateStates;
    int runningMin = 0;
    uint64_t eventCount = 0;
    uint64_t runSummaryCount = 0;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(query,
                                                          target,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          false,
                                                          false,
                                                          &summaries,
                                                          &candidateStates,
                                                          &allCandidateStates,
                                                          NULL,
                                                          &runningMin,
                                                          &eventCount,
                                                          &runSummaryCount,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "initial summary run failed: " << error << "\n";
        std::exit(2);
    }
    return summaries;
}

} // namespace

int main()
{
    bool ok = true;

    ok = expect_equal_uint64(sizeof(SimScanCudaPackedInitialRunSummary16),
                             16,
                             "packed initial summary wire size") && ok;

    const SimScanCudaInitialRunSummary boundarySummary{
        -123,
        pack_coord(65535u, 65534u),
        65535u,
        0u,
        65535u,
        65534u};
    SimScanCudaPackedInitialRunSummary16 packedBoundary;
    SimScanCudaInitialRunSummary unpackedBoundary;
    ok = expect_true(simScanCudaInitialRunSummaryFitsPacked16(boundarySummary),
                     "boundary summary fits packed16") && ok;
    ok = expect_true(packSimScanCudaInitialRunSummary16(boundarySummary, packedBoundary),
                     "boundary summary packs") && ok;
    unpackSimScanCudaInitialRunSummary16(packedBoundary, unpackedBoundary);
    ok = expect_equal_summary(unpackedBoundary, boundarySummary, "boundary summary roundtrip") && ok;

    const SimScanCudaInitialRunSummary startIOverflow{1, pack_coord(65536u, 1u), 1u, 1u, 1u, 1u};
    const SimScanCudaInitialRunSummary startJOverflow{1, pack_coord(1u, 65536u), 1u, 1u, 1u, 1u};
    const SimScanCudaInitialRunSummary endIOverflow{1, pack_coord(1u, 1u), 65536u, 1u, 1u, 1u};
    const SimScanCudaInitialRunSummary minEndJOverflow{1, pack_coord(1u, 1u), 1u, 65536u, 1u, 1u};
    const SimScanCudaInitialRunSummary maxEndJOverflow{1, pack_coord(1u, 1u), 1u, 1u, 65536u, 1u};
    const SimScanCudaInitialRunSummary scoreEndJOverflow{1, pack_coord(1u, 1u), 1u, 1u, 1u, 65536u};
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(startIOverflow),
                      "startI overflow rejected") && ok;
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(startJOverflow),
                      "startJ overflow rejected") && ok;
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(endIOverflow),
                      "endI overflow rejected") && ok;
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(minEndJOverflow),
                      "minEndJ overflow rejected") && ok;
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(maxEndJOverflow),
                      "maxEndJ overflow rejected") && ok;
    ok = expect_false(simScanCudaInitialRunSummaryFitsPacked16(scoreEndJOverflow),
                      "scoreEndJ overflow rejected") && ok;

    std::string initError;
    if (!sim_scan_cuda_init(0, &initError))
    {
        std::cerr << "sim_scan_cuda_init failed: " << initError << "\n";
        return 2;
    }

    SimScanCudaBatchResult defaultBatchResult;
    const std::vector<SimScanCudaInitialRunSummary> defaultSummaries =
        run_summaries(false, defaultBatchResult);
    SimScanCudaBatchResult packedBatchResult;
    const std::vector<SimScanCudaInitialRunSummary> packedSummaries =
        run_summaries(true, packedBatchResult);

    ok = expect_true(!defaultSummaries.empty(), "default summaries non-empty") && ok;
    ok = expect_equal_summaries(packedSummaries, defaultSummaries, "packed D2H exact summaries") && ok;
    ok = expect_false(defaultBatchResult.usedInitialPackedSummaryD2H,
                      "default packed summary D2H disabled") && ok;
    ok = expect_true(packedBatchResult.usedInitialPackedSummaryD2H,
                     "opt-in packed summary D2H used") && ok;
    ok = expect_equal_uint64(packedBatchResult.initialSummaryPackedBytesD2H,
                             static_cast<uint64_t>(packedSummaries.size()) *
                                 static_cast<uint64_t>(sizeof(SimScanCudaPackedInitialRunSummary16)),
                             "packed summary actual D2H bytes") && ok;
    ok = expect_equal_uint64(packedBatchResult.initialSummaryUnpackedEquivalentBytesD2H,
                             static_cast<uint64_t>(packedSummaries.size()) *
                                 static_cast<uint64_t>(sizeof(SimScanCudaInitialRunSummary)),
                             "packed summary equivalent unpacked D2H bytes") && ok;
    ok = expect_equal_uint64(packedBatchResult.initialSummaryPackedD2HFallbacks,
                             0,
                             "packed summary D2H fallbacks") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PACKED_SUMMARY_D2H");
    if (!ok)
    {
        return 1;
    }
    return 0;
}
