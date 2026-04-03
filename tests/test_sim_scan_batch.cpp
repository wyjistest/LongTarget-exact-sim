#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_cuda_runtime.h"
#include "../cuda/sim_scan_cuda.h"

namespace
{

static bool expect_equal_uint64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_bool(bool actual, bool expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << (expected ? "true" : "false")
              << ", got " << (actual ? "true" : "false") << "\n";
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

} // namespace

int main()
{
    bool ok = true;

    unsetenv("LONGTARGET_CUDA_DEVICE");
    unsetenv("LONGTARGET_SIM_CUDA_WORKERS_PER_DEVICE");
    sim_clear_cuda_device_override();
    sim_clear_cuda_worker_slot_override();

    ok = expect_equal_int(simCudaDeviceRuntime(), -1, "default device runtime") && ok;
    ok = expect_equal_int(simCudaWorkerSlotRuntime(), 0, "default worker slot runtime") && ok;
    ok = expect_equal_int(simCudaWorkersPerDeviceRuntime(), 1, "default workers per device") && ok;

    sim_set_cuda_device_override(7);
    ok = expect_equal_int(simCudaDeviceRuntime(), 7, "device override runtime") && ok;
    sim_clear_cuda_device_override();
    ok = expect_equal_int(simCudaDeviceRuntime(), -1, "device override cleared") && ok;

    sim_set_cuda_worker_slot_override(3);
    ok = expect_equal_int(simCudaWorkerSlotRuntime(), 3, "worker slot override runtime") && ok;
    sim_clear_cuda_worker_slot_override();
    ok = expect_equal_int(simCudaWorkerSlotRuntime(), 0, "worker slot override cleared") && ok;

    std::vector<int> devices;
    devices.push_back(2);
    devices.push_back(5);
    const std::vector<SimCudaWorkerAssignment> assignments =
        simBuildCudaWorkerAssignments(devices, 2);
    ok = expect_equal_uint64(assignments.size(), 4, "worker assignment count") && ok;
    ok = expect_equal_int(assignments[0].device, 2, "assignment[0] device") && ok;
    ok = expect_equal_int(assignments[0].slot, 0, "assignment[0] slot") && ok;
    ok = expect_equal_int(assignments[1].device, 2, "assignment[1] device") && ok;
    ok = expect_equal_int(assignments[1].slot, 1, "assignment[1] slot") && ok;
    ok = expect_equal_int(assignments[2].device, 5, "assignment[2] device") && ok;
    ok = expect_equal_int(assignments[2].slot, 0, "assignment[2] slot") && ok;
    ok = expect_equal_int(assignments[3].device, 5, "assignment[3] device") && ok;
    ok = expect_equal_int(assignments[3].slot, 1, "assignment[3] slot") && ok;

    SimScanCudaBatchResult emptyResult;
    ok = expect_equal_bool(emptyResult.usedCuda, false, "default usedCuda") && ok;
    ok = expect_equal_bool(emptyResult.usedRegionTrueBatchPath,
                           false,
                           "default usedRegionTrueBatchPath") && ok;
    ok = expect_equal_bool(emptyResult.usedInitialHashReducePath,
                           false,
                           "default usedInitialHashReducePath") && ok;
    ok = expect_equal_bool(emptyResult.usedInitialProposalOnlinePath,
                           false,
                           "default usedInitialProposalOnlinePath") && ok;
    ok = expect_equal_bool(emptyResult.usedInitialProposalV2Path,
                           false,
                           "default usedInitialProposalV2Path") && ok;
    ok = expect_equal_bool(emptyResult.usedInitialProposalV2DirectTopKPath,
                           false,
                           "default usedInitialProposalV2DirectTopKPath") && ok;
    ok = expect_equal_bool(emptyResult.usedInitialProposalV3Path,
                           false,
                           "default usedInitialProposalV3Path") && ok;
    ok = expect_equal_bool(emptyResult.initialHashReduceFallback,
                           false,
                           "default initialHashReduceFallback") && ok;
    ok = expect_equal_bool(emptyResult.initialProposalOnlineFallback,
                           false,
                           "default initialProposalOnlineFallback") && ok;
    ok = expect_equal_uint64(emptyResult.regionTrueBatchRequestCount,
                             0,
                             "default regionTrueBatchRequestCount") && ok;
    ok = expect_equal_uint64(emptyResult.initialProposalV2RequestCount,
                             0,
                             "default initialProposalV2RequestCount") && ok;
    ok = expect_equal_uint64(emptyResult.initialProposalV3RequestCount,
                             0,
                             "default initialProposalV3RequestCount") && ok;
    ok = expect_equal_uint64(emptyResult.initialProposalV3SelectedStateCount,
                             0,
                             "default initialProposalV3SelectedStateCount") && ok;
    ok = expect_equal_uint64(emptyResult.initialProposalLogicalCandidateCount,
                             0,
                             "default initialProposalLogicalCandidateCount") && ok;
    ok = expect_equal_uint64(emptyResult.initialProposalMaterializedCandidateCount,
                             0,
                             "default initialProposalMaterializedCandidateCount") && ok;
    ok = expect_equal_bool(emptyResult.initialProposalDirectTopKGpuSeconds == 0.0,
                           true,
                           "default initialProposalDirectTopKGpuSeconds") && ok;
    ok = expect_equal_bool(emptyResult.initialProposalV3GpuSeconds == 0.0,
                           true,
                           "default initialProposalV3GpuSeconds") && ok;
    ok = expect_equal_bool(emptyResult.initialProposalSelectD2HSeconds == 0.0,
                           true,
                           "default initialProposalSelectD2HSeconds") && ok;
    ok = expect_equal_bool(emptyResult.initialScanTailSeconds == 0.0,
                           true,
                           "default initialScanTailSeconds") && ok;
    ok = expect_equal_bool(emptyResult.initialHashReduceSeconds == 0.0,
                           true,
                           "default initialHashReduceSeconds") && ok;
    ok = expect_equal_uint64(emptyResult.taskCount, 0, "default taskCount") && ok;
    ok = expect_equal_uint64(emptyResult.launchCount, 0, "default launchCount") && ok;

    SimScanCudaRequest defaultRequest;
    ok = expect_equal_bool(defaultRequest.reduceCandidates, false, "default reduceCandidates") && ok;
    ok = expect_equal_bool(defaultRequest.reduceAllCandidateStates, false, "default reduceAllCandidateStates") && ok;
    ok = expect_equal_bool(defaultRequest.filterStartCoords == NULL, true, "default filterStartCoords") && ok;
    ok = expect_equal_int(defaultRequest.filterStartCoordCount, 0, "default filterStartCoordCount") && ok;

    std::string error;

    SimScanCudaInitialBatchRequest defaultInitialBatchRequest;
    ok = expect_equal_bool(defaultInitialBatchRequest.A == NULL, true, "default initial batch A") && ok;
    ok = expect_equal_bool(defaultInitialBatchRequest.B == NULL, true, "default initial batch B") && ok;
    ok = expect_equal_int(defaultInitialBatchRequest.queryLength, 0, "default initial batch queryLength") && ok;
    ok = expect_equal_int(defaultInitialBatchRequest.targetLength, 0, "default initial batch targetLength") && ok;
    ok = expect_equal_bool(defaultInitialBatchRequest.reduceCandidates, false, "default initial batch reduceCandidates") && ok;

    SimScanCudaInitialBatchResult defaultInitialBatchResult;
    ok = expect_equal_uint64(defaultInitialBatchResult.eventCount, 0, "default initial batch eventCount") && ok;
    ok = expect_equal_uint64(defaultInitialBatchResult.runSummaryCount, 0, "default initial batch runSummaryCount") && ok;
    ok = expect_equal_bool(defaultInitialBatchResult.initialRunSummaries.empty(), true, "default initial batch summaries empty") && ok;
    ok = expect_equal_bool(defaultInitialBatchResult.candidateStates.empty(), true, "default initial batch candidate states empty") && ok;

    std::vector<SimScanCudaInitialBatchRequest> emptyInitialBatchRequests;
    std::vector<SimScanCudaInitialBatchResult> emptyInitialBatchResults;
    error.clear();
    emptyResult = SimScanCudaBatchResult();
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(emptyInitialBatchRequests,
                                                                     &emptyInitialBatchResults,
                                                                     &emptyResult,
                                                                     &error))
    {
        std::cerr << "empty initial true batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(emptyInitialBatchResults.empty(), true, "empty initial true batch results") && ok;
    ok = expect_equal_bool(error.empty(), true, "empty initial true batch error") && ok;

    std::vector<SimScanCudaRequest> requests;
    std::vector<SimScanCudaRequestResult> results;
    if (!sim_scan_cuda_enumerate_events_row_major_batch(requests, &results, &emptyResult, &error))
    {
        std::cerr << "empty batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(results.empty(), true, "empty results") && ok;
    ok = expect_equal_bool(error.empty(), true, "empty error") && ok;
    ok = expect_equal_uint64(emptyResult.taskCount, 0, "empty taskCount") && ok;
    ok = expect_equal_uint64(emptyResult.launchCount, 0, "empty launchCount") && ok;

    int scoreMatrix[128][128] = {};
    scoreMatrix['A']['A'] = 5;
    scoreMatrix['C']['C'] = 5;
    scoreMatrix['G']['G'] = 5;
    scoreMatrix['T']['T'] = 5;

    SimScanCudaRequest request;
    request.kind = SIM_SCAN_CUDA_REQUEST_INITIAL;
    request.A = "ACGT";
    request.B = "ACGT";
    request.queryLength = 4;
    request.targetLength = 4;
    request.gapOpen = 16;
    request.gapExtend = 4;
    request.scoreMatrix = scoreMatrix;
    request.eventScoreFloor = 5;
    requests.push_back(request);

    SimScanCudaInitialBatchRequest initialBatchRequest;
    initialBatchRequest.A = "ACGT";
    initialBatchRequest.B = "ACGT";
    initialBatchRequest.queryLength = 4;
    initialBatchRequest.targetLength = 4;
    initialBatchRequest.gapOpen = 16;
    initialBatchRequest.gapExtend = 4;
    initialBatchRequest.scoreMatrix = scoreMatrix;
    initialBatchRequest.eventScoreFloor = 5;
    initialBatchRequest.reduceCandidates = true;
    initialBatchRequest.seedRunningMin = 9;

    std::vector<SimScanCudaInitialBatchRequest> initialBatchRequests(2, initialBatchRequest);
    std::vector<SimScanCudaInitialBatchResult> initialBatchResults;
    initialBatchResults.push_back(SimScanCudaInitialBatchResult());
    error.clear();
    emptyResult = SimScanCudaBatchResult();
    if (sim_scan_cuda_enumerate_initial_events_row_major_true_batch(initialBatchRequests,
                                                                    &initialBatchResults,
                                                                    &emptyResult,
                                                                    &error))
    {
        std::cerr << "stub initial true batch should fail when CUDA is unavailable\n";
        return 1;
    }
    ok = expect_equal_bool(initialBatchResults.empty(), true, "failed initial true batch clears results") && ok;
    ok = expect_equal_bool(emptyResult.usedCuda, false, "failed initial true batch usedCuda") && ok;
    ok = expect_equal_bool(emptyResult.usedRegionTrueBatchPath,
                           false,
                           "failed initial true batch usedRegionTrueBatchPath") && ok;
    ok = expect_equal_uint64(emptyResult.regionTrueBatchRequestCount,
                             0,
                             "failed initial true batch regionTrueBatchRequestCount") && ok;
    ok = expect_equal_uint64(emptyResult.taskCount, 0, "failed initial true batch taskCount") && ok;
    ok = expect_equal_uint64(emptyResult.launchCount, 0, "failed initial true batch launchCount") && ok;
    ok = expect_equal_bool(error == "CUDA support not built", true, "stub initial true batch error") && ok;

    std::vector<uint64_t> filterStartCoords;
    filterStartCoords.push_back((static_cast<uint64_t>(1) << 32) | 3u);
    filterStartCoords.push_back((static_cast<uint64_t>(2) << 32) | 4u);
    SimScanCudaRequest regionReduceRequest;
    regionReduceRequest.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    regionReduceRequest.A = "ACGT";
    regionReduceRequest.B = "ACGT";
    regionReduceRequest.queryLength = 4;
    regionReduceRequest.targetLength = 4;
    regionReduceRequest.rowStart = 1;
    regionReduceRequest.rowEnd = 4;
    regionReduceRequest.colStart = 1;
    regionReduceRequest.colEnd = 4;
    regionReduceRequest.gapOpen = 16;
    regionReduceRequest.gapExtend = 4;
    regionReduceRequest.scoreMatrix = scoreMatrix;
    regionReduceRequest.eventScoreFloor = 5;
    regionReduceRequest.reduceAllCandidateStates = true;
    regionReduceRequest.filterStartCoords = filterStartCoords.data();
    regionReduceRequest.filterStartCoordCount = static_cast<int>(filterStartCoords.size());
    ok = expect_equal_bool(regionReduceRequest.reduceCandidates, false, "region reduce keeps top-k reduce disabled") && ok;
    ok = expect_equal_bool(regionReduceRequest.reduceAllCandidateStates, true, "region reduce enables all candidate states") && ok;
    ok = expect_equal_bool(regionReduceRequest.filterStartCoords == filterStartCoords.data(), true, "region reduce filter pointer") && ok;
    ok = expect_equal_int(regionReduceRequest.filterStartCoordCount,
                          static_cast<int>(filterStartCoords.size()),
                          "region reduce filter count") && ok;

    results.push_back(SimScanCudaRequestResult());
    error.clear();
    emptyResult = SimScanCudaBatchResult();
    if (sim_scan_cuda_enumerate_events_row_major_batch(requests, &results, &emptyResult, &error))
    {
        std::cerr << "stub batch should fail when CUDA is unavailable\n";
        return 1;
    }
    ok = expect_equal_bool(results.empty(), true, "failed batch clears results") && ok;
    ok = expect_equal_bool(emptyResult.usedCuda, false, "failed batch usedCuda") && ok;
    ok = expect_equal_bool(emptyResult.usedRegionTrueBatchPath,
                           false,
                           "failed batch usedRegionTrueBatchPath") && ok;
    ok = expect_equal_uint64(emptyResult.regionTrueBatchRequestCount,
                             0,
                             "failed batch regionTrueBatchRequestCount") && ok;
    ok = expect_equal_uint64(emptyResult.taskCount, 0, "failed batch taskCount") && ok;
    ok = expect_equal_uint64(emptyResult.launchCount, 0, "failed batch launchCount") && ok;
    ok = expect_equal_bool(error == "CUDA support not built", true, "stub error") && ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
