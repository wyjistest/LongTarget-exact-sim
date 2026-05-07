#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_scan_cuda.h"

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
                                                                bool hostCopyElision,
                                                                bool reduceCandidates,
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
    if (hostCopyElision)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_SUMMARY_HOST_COPY_ELISION", "1", 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_SUMMARY_HOST_COPY_ELISION");
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
                                                          reduceCandidates,
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

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_summaries(
    bool packedD2H,
    bool hostCopyElision,
    bool reduceCandidates,
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
    if (hostCopyElision)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_SUMMARY_HOST_COPY_ELISION", "1", 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_SUMMARY_HOST_COPY_ELISION");
    }

    int scoreMatrix[128][128] = {};
    fill_score_matrix(scoreMatrix);

    const char *query = "ACGTACGT";
    const char *target0 = "ACGTACGT";
    const char *target1 = "ACGGACGT";
    const int queryLength = 8;
    const int targetLength = 8;
    const int gapOpen = 16;
    const int gapExtend = 4;
    const int eventScoreFloor = 5;

    SimScanCudaInitialBatchRequest request0;
    request0.A = query;
    request0.B = target0;
    request0.queryLength = queryLength;
    request0.targetLength = targetLength;
    request0.gapOpen = gapOpen;
    request0.gapExtend = gapExtend;
    request0.scoreMatrix = scoreMatrix;
    request0.eventScoreFloor = eventScoreFloor;
    request0.reduceCandidates = reduceCandidates;

    SimScanCudaInitialBatchRequest request1 = request0;
    request1.B = target1;

    std::vector<SimScanCudaInitialBatchRequest> requests;
    requests.push_back(request0);
    requests.push_back(request1);

    std::vector<SimScanCudaInitialBatchResult> results;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &results,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "true-batch initial summary run failed: " << error << "\n";
        std::exit(2);
    }
    return results;
}

} // namespace

int main()
{
    std::string initError;
    if (!sim_scan_cuda_init(0, &initError))
    {
        std::cerr << "sim_scan_cuda_init failed: " << initError << "\n";
        return 2;
    }

    bool ok = true;
    SimScanCudaBatchResult defaultBatchResult;
    const std::vector<SimScanCudaInitialRunSummary> defaultSummaries =
        run_summaries(false, false, false, defaultBatchResult);
    SimScanCudaBatchResult directBatchResult;
    const std::vector<SimScanCudaInitialRunSummary> directSummaries =
        run_summaries(false, true, false, directBatchResult);
    SimScanCudaBatchResult packedDirectBatchResult;
    const std::vector<SimScanCudaInitialRunSummary> packedDirectSummaries =
        run_summaries(true, true, false, packedDirectBatchResult);
    SimScanCudaBatchResult reduceBatchResult;
    (void)run_summaries(false, true, true, reduceBatchResult);
    SimScanCudaBatchResult defaultTrueBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> defaultTrueBatchSummaries =
        run_true_batch_summaries(false, false, false, defaultTrueBatchResult);
    SimScanCudaBatchResult directTrueBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> directTrueBatchSummaries =
        run_true_batch_summaries(false, true, false, directTrueBatchResult);
    SimScanCudaBatchResult packedDirectTrueBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> packedDirectTrueBatchSummaries =
        run_true_batch_summaries(true, true, false, packedDirectTrueBatchResult);
    SimScanCudaBatchResult reduceTrueBatchResult;
    (void)run_true_batch_summaries(false, true, true, reduceTrueBatchResult);

    const uint64_t expectedElidedBytes =
        static_cast<uint64_t>(defaultSummaries.size()) *
        static_cast<uint64_t>(sizeof(SimScanCudaInitialRunSummary));
    uint64_t expectedTrueBatchElidedBytes = 0;
    for (size_t batchIndex = 0; batchIndex < defaultTrueBatchSummaries.size(); ++batchIndex)
    {
        expectedTrueBatchElidedBytes +=
            static_cast<uint64_t>(defaultTrueBatchSummaries[batchIndex].initialRunSummaries.size()) *
            static_cast<uint64_t>(sizeof(SimScanCudaInitialRunSummary));
    }

    ok = expect_true(!defaultSummaries.empty(), "default summaries non-empty") && ok;
    ok = expect_equal_summaries(directSummaries, defaultSummaries, "direct elision exact summaries") && ok;
    ok = expect_equal_summaries(packedDirectSummaries, defaultSummaries, "packed direct elision exact summaries") && ok;
    ok = expect_false(defaultBatchResult.usedInitialSummaryHostCopyElision,
                      "default host-copy elision disabled") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialSummaryHostCopyElidedBytes,
                             0,
                             "default elided bytes zero") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestPrefixSkips,
                             2,
                             "default single-request batch prefix skips") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestInputPackSkips,
                             2,
                             "default single-request input pack skips") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             1,
                             "default single-request target buffer skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             1,
                             "default single-request matrix buffer skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             1,
                             "default single-request diag buffer skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             1,
                             "default single-request metadata buffer skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             1,
                             "default single-request event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             2,
                             "default single-request count copy skips") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "default event-base materialize skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "default event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "default single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(defaultBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "default single-request run-base buffer ensure skip") && ok;
    ok = expect_true(directBatchResult.usedInitialSummaryHostCopyElision,
                     "direct host-copy elision used") && ok;
    ok = expect_equal_uint64(directBatchResult.initialSummaryHostCopyElidedBytes,
                             expectedElidedBytes,
                             "direct elided bytes") && ok;
    ok = expect_equal_uint64(directBatchResult.initialSummaryHostCopyElisionRunCountCopySkips,
                             1,
                             "direct run-count copy skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialSummaryHostCopyElisionEventCountCopySkips,
                             1,
                             "direct event-count copy skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestPrefixSkips,
                             2,
                             "direct single-request batch prefix skips") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestInputPackSkips,
                             2,
                             "direct single-request input pack skips") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             1,
                             "direct single-request target buffer skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             1,
                             "direct single-request matrix buffer skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             1,
                             "direct single-request diag buffer skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             1,
                             "direct single-request metadata buffer skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             1,
                             "direct single-request event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             2,
                             "direct single-request count copy skips") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "direct event-base materialize skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "direct event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "direct single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(directBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "direct single-request run-base buffer ensure skip") && ok;
    ok = expect_true(packedDirectBatchResult.usedInitialPackedSummaryD2H,
                     "packed direct still uses packed D2H") && ok;
    ok = expect_true(packedDirectBatchResult.usedInitialSummaryHostCopyElision,
                     "packed direct host-copy elision used") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialSummaryHostCopyElidedBytes,
                             expectedElidedBytes,
                             "packed direct elided bytes") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialSummaryHostCopyElisionRunCountCopySkips,
                             1,
                             "packed direct run-count copy skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialSummaryHostCopyElisionEventCountCopySkips,
                             1,
                             "packed direct event-count copy skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestPrefixSkips,
                             2,
                             "packed direct single-request batch prefix skips") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestInputPackSkips,
                             2,
                             "packed direct single-request input pack skips") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             1,
                             "packed direct single-request target buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             1,
                             "packed direct single-request matrix buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             1,
                             "packed direct single-request diag buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             1,
                             "packed direct single-request metadata buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             1,
                             "packed direct single-request event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             2,
                             "packed direct single-request count copy skips") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "packed direct event-base materialize skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "packed direct event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "packed direct single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(packedDirectBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "packed direct single-request run-base buffer ensure skip") && ok;
    ok = expect_false(reduceBatchResult.usedInitialSummaryHostCopyElision,
                      "reduce path does not use summary host-copy elision") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             0,
                             "reduce single-request no true-batch event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             0,
                             "reduce single-request no true-batch target buffer skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             0,
                             "reduce single-request no true-batch matrix buffer skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             0,
                             "reduce single-request no true-batch diag buffer skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             0,
                             "reduce single-request no true-batch metadata buffer skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             0,
                             "reduce single-request no run-base materialize skip") && ok;
    ok = expect_equal_uint64(reduceBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             0,
                             "reduce single-request no run-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(defaultTrueBatchSummaries.size()),
                             2,
                             "default true-batch result count") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(directTrueBatchSummaries.size()),
                             2,
                             "direct true-batch result count") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(packedDirectTrueBatchSummaries.size()),
                             2,
                             "packed direct true-batch result count") && ok;
    if (defaultTrueBatchSummaries.size() == 2 && directTrueBatchSummaries.size() == 2)
    {
        ok = expect_equal_summaries(directTrueBatchSummaries[0].initialRunSummaries,
                                    defaultTrueBatchSummaries[0].initialRunSummaries,
                                    "direct true-batch result 0 summaries") && ok;
        ok = expect_equal_summaries(directTrueBatchSummaries[1].initialRunSummaries,
                                    defaultTrueBatchSummaries[1].initialRunSummaries,
                                    "direct true-batch result 1 summaries") && ok;
    }
    if (defaultTrueBatchSummaries.size() == 2 && packedDirectTrueBatchSummaries.size() == 2)
    {
        ok = expect_equal_summaries(packedDirectTrueBatchSummaries[0].initialRunSummaries,
                                    defaultTrueBatchSummaries[0].initialRunSummaries,
                                    "packed direct true-batch result 0 summaries") && ok;
        ok = expect_equal_summaries(packedDirectTrueBatchSummaries[1].initialRunSummaries,
                                    defaultTrueBatchSummaries[1].initialRunSummaries,
                                    "packed direct true-batch result 1 summaries") && ok;
    }
    ok = expect_false(defaultTrueBatchResult.usedInitialSummaryHostCopyElision,
                      "default true-batch host-copy elision disabled") && ok;
    ok = expect_equal_uint64(defaultTrueBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "default true-batch event-base materialize skip") && ok;
    ok = expect_equal_uint64(defaultTrueBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "default true-batch event-base buffer ensure skip") && ok;
    ok = expect_true(directTrueBatchResult.usedInitialSummaryHostCopyElision,
                     "direct true-batch host-copy elision used") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialSummaryHostCopyElidedBytes,
                             expectedTrueBatchElidedBytes,
                             "direct true-batch elided bytes") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialSummaryHostCopyElisionCountCopyReuses,
                             1,
                             "direct true-batch count-copy reuse") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialSummaryHostCopyElisionBaseCopyReuses,
                             1,
                             "direct true-batch base-copy reuse") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestPrefixSkips,
                             0,
                             "direct true-batch no single-request prefix skips") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestInputPackSkips,
                             0,
                             "direct true-batch no single-request input pack skips") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             0,
                             "direct true-batch no single-request target buffer skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             0,
                             "direct true-batch no single-request matrix buffer skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             0,
                             "direct true-batch no single-request diag buffer skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             0,
                             "direct true-batch no single-request metadata buffer skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             0,
                             "direct true-batch no single-request event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             0,
                             "direct true-batch no single-request count copy skips") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "direct true-batch event-base materialize skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "direct true-batch event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             0,
                             "direct true-batch no single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(directTrueBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             0,
                             "direct true-batch no single-request run-base buffer ensure skip") && ok;
    ok = expect_true(packedDirectTrueBatchResult.usedInitialPackedSummaryD2H,
                     "packed direct true-batch still uses packed D2H") && ok;
    ok = expect_true(packedDirectTrueBatchResult.usedInitialSummaryHostCopyElision,
                     "packed direct true-batch host-copy elision used") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialSummaryHostCopyElidedBytes,
                             expectedTrueBatchElidedBytes,
                             "packed direct true-batch elided bytes") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialSummaryHostCopyElisionCountCopyReuses,
                             1,
                             "packed direct true-batch count-copy reuse") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialSummaryHostCopyElisionBaseCopyReuses,
                             1,
                             "packed direct true-batch base-copy reuse") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestPrefixSkips,
                             0,
                             "packed direct true-batch no single-request prefix skips") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestInputPackSkips,
                             0,
                             "packed direct true-batch no single-request input pack skips") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestTargetBufferSkips,
                             0,
                             "packed direct true-batch no single-request target buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestMatrixBufferSkips,
                             0,
                             "packed direct true-batch no single-request matrix buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestDiagBufferSkips,
                             0,
                             "packed direct true-batch no single-request diag buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestMetadataBufferSkips,
                             0,
                             "packed direct true-batch no single-request metadata buffer skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestEventScoreFloorUploadSkips,
                             0,
                             "packed direct true-batch no single-request event-score-floor upload skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             0,
                             "packed direct true-batch no single-request count copy skips") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "packed direct true-batch event-base materialize skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "packed direct true-batch event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             0,
                             "packed direct true-batch no single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(packedDirectTrueBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             0,
                             "packed direct true-batch no single-request run-base buffer ensure skip") && ok;
    ok = expect_false(reduceTrueBatchResult.usedInitialSummaryHostCopyElision,
                      "reduce true-batch does not use summary host-copy elision") && ok;
    ok = expect_equal_uint64(reduceTrueBatchResult.initialTrueBatchSingleRequestCountCopySkips,
                             0,
                             "reduce true-batch no single-request count copy skips") && ok;
    ok = expect_equal_uint64(reduceTrueBatchResult.initialTrueBatchEventBaseMaterializeSkips,
                             1,
                             "reduce true-batch event-base materialize skip") && ok;
    ok = expect_equal_uint64(reduceTrueBatchResult.initialTrueBatchEventBaseBufferEnsureSkips,
                             1,
                             "reduce true-batch event-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(reduceTrueBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             0,
                             "reduce true-batch no single-request run-base materialize skip") && ok;
    ok = expect_equal_uint64(reduceTrueBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             0,
                             "reduce true-batch no single-request run-base buffer ensure skip") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PACKED_SUMMARY_D2H");
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_SUMMARY_HOST_COPY_ELISION");
    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
