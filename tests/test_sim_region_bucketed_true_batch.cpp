#include <cstdint>
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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
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

static bool expect_equal_uint64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_candidate_states_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                          const std::vector<SimScanCudaCandidateState> &expected,
                                          const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected "
                  << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < actual.size(); ++i)
    {
        if (std::memcmp(&actual[i], &expected[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static void initialize_score_matrix(int scoreMatrix[128][128])
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

static bool plan_bucketed_groups(const std::vector<SimScanCudaRegionBucketedTrueBatchShape> &shapes,
                                 std::vector<SimScanCudaRegionBucketedTrueBatchGroup> *groups,
                                 SimScanCudaRegionBucketedTrueBatchStats *stats)
{
    std::string error;
    if (!sim_scan_cuda_plan_region_bucketed_true_batches_for_test(shapes,
                                                                  groups,
                                                                  stats,
                                                                  &error))
    {
        std::cerr << "planner failed: " << error << "\n";
        return false;
    }
    return true;
}

static bool test_planner_accepts_low_padding_bucket()
{
    std::vector<SimScanCudaRegionBucketedTrueBatchShape> shapes;
    shapes.push_back(SimScanCudaRegionBucketedTrueBatchShape(63, 250));
    shapes.push_back(SimScanCudaRegionBucketedTrueBatchShape(64, 256));

    std::vector<SimScanCudaRegionBucketedTrueBatchGroup> groups;
    SimScanCudaRegionBucketedTrueBatchStats stats;
    if (!plan_bucketed_groups(shapes, &groups, &stats))
    {
        return false;
    }

    bool ok = true;
    ok = expect_equal_size(groups.size(), 1, "low padding group count") && ok;
    if (!groups.empty())
    {
        ok = expect_true(groups[0].bucketed, "low padding group bucketed") && ok;
        ok = expect_equal_size(groups[0].requestBegin, 0, "low padding requestBegin") && ok;
        ok = expect_equal_size(groups[0].requestCount, 2, "low padding requestCount") && ok;
        ok = expect_equal_int(groups[0].bucketRows, 64, "low padding bucketRows") && ok;
        ok = expect_equal_int(groups[0].bucketCols, 256, "low padding bucketCols") && ok;
        ok = expect_equal_uint64(groups[0].actualCells, 32134, "low padding actualCells") && ok;
        ok = expect_equal_uint64(groups[0].paddedCells, 32768, "low padding paddedCells") && ok;
    }
    ok = expect_equal_uint64(stats.batches, 1, "low padding batches") && ok;
    ok = expect_equal_uint64(stats.requests, 2, "low padding requests") && ok;
    ok = expect_equal_uint64(stats.fusedRequests, 2, "low padding fusedRequests") && ok;
    ok = expect_equal_uint64(stats.actualCells, 32134, "low padding stats actualCells") && ok;
    ok = expect_equal_uint64(stats.paddedCells, 32768, "low padding stats paddedCells") && ok;
    ok = expect_equal_uint64(stats.paddingCells, 634, "low padding paddingCells") && ok;
    ok = expect_equal_uint64(stats.rejectedPadding, 0, "low padding rejectedPadding") && ok;
    return ok;
}

static bool test_planner_rejects_high_padding_bucket()
{
    std::vector<SimScanCudaRegionBucketedTrueBatchShape> shapes;
    shapes.push_back(SimScanCudaRegionBucketedTrueBatchShape(33, 200));
    shapes.push_back(SimScanCudaRegionBucketedTrueBatchShape(64, 256));

    std::vector<SimScanCudaRegionBucketedTrueBatchGroup> groups;
    SimScanCudaRegionBucketedTrueBatchStats stats;
    if (!plan_bucketed_groups(shapes, &groups, &stats))
    {
        return false;
    }

    bool ok = true;
    ok = expect_equal_size(groups.size(), 2, "high padding group count") && ok;
    for (size_t i = 0; i < groups.size(); ++i)
    {
        ok = expect_false(groups[i].bucketed, "high padding group not bucketed") && ok;
        ok = expect_equal_size(groups[i].requestCount, 1, "high padding requestCount") && ok;
        ok = expect_equal_uint64(groups[i].actualCells,
                                 static_cast<uint64_t>(shapes[i].rowCount) *
                                   static_cast<uint64_t>(shapes[i].colCount),
                                 "high padding actualCells") && ok;
        ok = expect_equal_uint64(groups[i].paddedCells,
                                 static_cast<uint64_t>(shapes[i].rowCount) *
                                   static_cast<uint64_t>(shapes[i].colCount),
                                 "high padding paddedCells") && ok;
    }
    ok = expect_equal_uint64(stats.batches, 0, "high padding bucketed batches") && ok;
    ok = expect_equal_uint64(stats.fusedRequests, 0, "high padding fusedRequests") && ok;
    ok = expect_equal_uint64(stats.rejectedPadding, 9784, "high padding rejectedPadding") && ok;
    return ok;
}

static bool test_planner_caps_bucket_size_at_32()
{
    std::vector<SimScanCudaRegionBucketedTrueBatchShape> shapes;
    for (int i = 0; i < 33; ++i)
    {
        shapes.push_back(SimScanCudaRegionBucketedTrueBatchShape(64, 256));
    }

    std::vector<SimScanCudaRegionBucketedTrueBatchGroup> groups;
    SimScanCudaRegionBucketedTrueBatchStats stats;
    if (!plan_bucketed_groups(shapes, &groups, &stats))
    {
        return false;
    }

    bool ok = true;
    ok = expect_equal_size(groups.size(), 2, "max batch group count") && ok;
    if (groups.size() == 2)
    {
        ok = expect_true(groups[0].bucketed, "max batch first bucketed") && ok;
        ok = expect_equal_size(groups[0].requestCount, 32, "max batch first requestCount") && ok;
        ok = expect_false(groups[1].bucketed, "max batch tail not bucketed") && ok;
        ok = expect_equal_size(groups[1].requestBegin, 32, "max batch tail requestBegin") && ok;
        ok = expect_equal_size(groups[1].requestCount, 1, "max batch tail requestCount") && ok;
    }
    ok = expect_equal_uint64(stats.batches, 1, "max batch bucketed batches") && ok;
    ok = expect_equal_uint64(stats.requests, 33, "max batch requests") && ok;
    ok = expect_equal_uint64(stats.fusedRequests, 32, "max batch fusedRequests") && ok;
    return ok;
}

static bool run_region_aggregated(const std::vector<SimScanCudaRequest> &requests,
                                  SimScanCudaRegionAggregationResult *result,
                                  SimScanCudaBatchResult *batchResult)
{
    std::string error;
    if (!sim_scan_cuda_enumerate_region_candidate_states_aggregated(requests,
                                                                    result,
                                                                    batchResult,
                                                                    &error))
    {
        std::cerr << "region aggregation failed: " << error << "\n";
        return false;
    }
    return true;
}

static bool test_bucketed_region_path_matches_unbucketed_aggregation()
{
    std::string error;
    if (!sim_scan_cuda_init(0, &error))
    {
        std::cerr << "sim_scan_cuda_init failed: " << error << "\n";
        return false;
    }

    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query(80, 'A');
    const std::string target(300, 'A');
    const int gapOpen = 16;
    const int gapExtend = 4;
    const int eventScoreFloor = 5;

    SimScanCudaRequest request0;
    request0.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    request0.A = query.c_str();
    request0.B = target.c_str();
    request0.queryLength = static_cast<int>(query.size());
    request0.targetLength = static_cast<int>(target.size());
    request0.rowStart = 1;
    request0.rowEnd = 63;
    request0.colStart = 1;
    request0.colEnd = 250;
    request0.gapOpen = gapOpen;
    request0.gapExtend = gapExtend;
    request0.scoreMatrix = scoreMatrix;
    request0.eventScoreFloor = eventScoreFloor;
    request0.reduceCandidates = false;
    request0.reduceAllCandidateStates = true;
    request0.filterStartCoords = NULL;
    request0.filterStartCoordCount = 0;
    request0.seedCandidates = NULL;
    request0.seedCandidateCount = 0;
    request0.seedRunningMin = 0;

    SimScanCudaRequest request1 = request0;
    request1.rowEnd = 64;
    request1.colEnd = 256;

    std::vector<SimScanCudaRequest> requests;
    requests.push_back(request0);
    requests.push_back(request1);

    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH_SHADOW");
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(requests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH", "1", 1);
    unsetenv("LONGTARGET_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH_SHADOW");
    SimScanCudaRegionAggregationResult bucketedResult;
    SimScanCudaBatchResult bucketedBatchResult;
    if (!run_region_aggregated(requests, &bucketedResult, &bucketedBatchResult))
    {
        return false;
    }
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH");

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH_SHADOW", "1", 1);
    SimScanCudaRegionAggregationResult shadowResult;
    SimScanCudaBatchResult shadowBatchResult;
    if (!run_region_aggregated(requests, &shadowResult, &shadowBatchResult))
    {
        return false;
    }
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH_SHADOW");

    bool ok = true;
    ok = expect_equal_uint64(bucketedResult.eventCount,
                             baselineResult.eventCount,
                             "bucketed eventCount") && ok;
    ok = expect_equal_uint64(bucketedResult.runSummaryCount,
                             baselineResult.runSummaryCount,
                             "bucketed runSummaryCount") && ok;
    ok = expect_equal_uint64(bucketedResult.preAggregateCandidateStateCount,
                             baselineResult.preAggregateCandidateStateCount,
                             "bucketed preAggregateCandidateStateCount") && ok;
    ok = expect_equal_uint64(bucketedResult.postAggregateCandidateStateCount,
                             baselineResult.postAggregateCandidateStateCount,
                             "bucketed postAggregateCandidateStateCount") && ok;
    ok = expect_candidate_states_equal(bucketedResult.candidateStates,
                                       baselineResult.candidateStates,
                                       "bucketed candidateStates") && ok;
    ok = expect_true(bucketedBatchResult.usedRegionBucketedTrueBatchPath,
                     "bucketed path used") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchBatches,
                             1,
                             "bucketed batches") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchRequests,
                             2,
                             "bucketed requests") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchFusedRequests,
                             2,
                             "bucketed fused requests") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchActualCells,
                             32134,
                             "bucketed actual cells") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchPaddedCells,
                             32768,
                             "bucketed padded cells") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchPaddingCells,
                             634,
                             "bucketed padding cells") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchRejectedPadding,
                             0,
                             "bucketed rejected padding") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionBucketedTrueBatchShadowMismatches,
                             0,
                             "bucketed shadow mismatches") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationNoFilterReservedCopySkips,
                             bucketedResult.preAggregateCandidateStateCount,
                             "bucketed no-filter reserved copy skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationNoFilterCandidateCountD2HSkips,
                             1,
                             "bucketed no-filter candidate count D2H skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationNoFilterCandidateCountScalarH2DSkips,
                             2,
                             "bucketed no-filter candidate count scalar H2D skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationSliceTempOutputBufferEnsureSkips,
                             2,
                             "bucketed slice temp output buffer ensure skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationCandidateCountClearSkips,
                             1,
                             "bucketed candidate count clear skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationSummaryTotalsClearSkips,
                             1,
                             "bucketed summary totals clear skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationNoFilterInitialCandidateCountBufferEnsureSkips,
                             1,
                             "bucketed no-filter initial candidate count buffer ensure skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.regionPackedAggregationInitialEventBufferEnsureSkips,
                             1,
                             "bucketed initial event buffer ensure skips") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.taskCount,
                             1,
                             "bucketed taskCount") && ok;
    ok = expect_equal_uint64(bucketedBatchResult.launchCount,
                             1,
                             "bucketed launchCount") && ok;
    ok = expect_equal_uint64(shadowResult.eventCount,
                             baselineResult.eventCount,
                             "shadow eventCount") && ok;
    ok = expect_equal_uint64(shadowResult.runSummaryCount,
                             baselineResult.runSummaryCount,
                             "shadow runSummaryCount") && ok;
    ok = expect_candidate_states_equal(shadowResult.candidateStates,
                                       baselineResult.candidateStates,
                                       "shadow candidateStates") && ok;
    ok = expect_true(shadowBatchResult.usedRegionBucketedTrueBatchPath,
                     "shadow bucketed path used") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionBucketedTrueBatchShadowMismatches,
                             0,
                             "shadow mismatches") && ok;
    return ok;
}

}

int main()
{
    bool ok = true;
    ok = test_planner_accepts_low_padding_bucket() && ok;
    ok = test_planner_rejects_high_padding_bucket() && ok;
    ok = test_planner_caps_bucket_size_at_32() && ok;
    ok = test_bucketed_region_path_matches_unbucketed_aggregation() && ok;
    return ok ? 0 : 1;
}
