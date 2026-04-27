#include "sim_scan_cuda.h"

using namespace std;

bool sim_scan_cuda_is_built()
{
  return false;
}

bool sim_scan_cuda_init(int device,string *errorOut)
{
  (void)device;
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_upload_persistent_safe_candidate_state_store(const SimScanCudaCandidateState *states,
                                                                size_t stateCount,
                                                                SimCudaPersistentSafeStoreHandle *handleOut,
                                                                string *errorOut)
{
  (void)states;
  (void)stateCount;
  if(handleOut != NULL)
  {
    *handleOut = SimCudaPersistentSafeStoreHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_erase_persistent_safe_candidate_state_store_start_coords(const uint64_t *startCoords,
                                                                            size_t startCoordCount,
                                                                            SimCudaPersistentSafeStoreHandle *handle,
                                                                            string *errorOut)
{
  (void)startCoords;
  (void)startCoordCount;
  if(handle != NULL)
  {
    *handle = SimCudaPersistentSafeStoreHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_path_summary(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                int summaryRowStart,
                                                                                const vector<int> &rowMinCols,
                                                                                const vector<int> &rowMaxCols,
                                                                                vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                string *errorOut)
{
  (void)handle;
  (void)summaryRowStart;
  (void)rowMinCols;
  (void)rowMaxCols;
  if(outCandidateStates != NULL)
  {
    outCandidateStates->clear();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                 int queryLength,
                                                                                 int targetLength,
                                                                                 const vector<int> &rowOffsets,
                                                                                 const vector<SimScanCudaColumnInterval> &intervals,
                                                                                 vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                 string *errorOut)
{
  (void)handle;
  (void)queryLength;
  (void)targetLength;
  (void)rowOffsets;
  (void)intervals;
  if(outCandidateStates != NULL)
  {
    outCandidateStates->clear();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_start_coords_by_row_intervals(
  const SimCudaPersistentSafeStoreHandle &handle,
  int queryLength,
  int targetLength,
  const vector<int> &rowOffsets,
  const vector<SimScanCudaColumnInterval> &intervals,
  vector<uint64_t> *outStartCoords,
  string *errorOut)
{
  (void)handle;
  (void)queryLength;
  (void)targetLength;
  (void)rowOffsets;
  (void)intervals;
  if(outStartCoords != NULL)
  {
    outStartCoords->clear();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_select_safe_workset_windows(const SimCudaPersistentSafeStoreHandle &handle,
                                               int queryLength,
                                               int targetLength,
                                               int summaryRowStart,
                                               const vector<int> &rowMinCols,
                                               const vector<int> &rowMaxCols,
                                               SimScanCudaSafeWindowPlannerMode plannerMode,
                                               int maxWindowCount,
                                               SimScanCudaSafeWindowResult *outResult,
                                               string *errorOut)
{
  (void)handle;
  (void)queryLength;
  (void)targetLength;
  (void)summaryRowStart;
  (void)rowMinCols;
  (void)rowMaxCols;
  (void)plannerMode;
  (void)maxWindowCount;
  if(outResult != NULL)
  {
    *outResult = SimScanCudaSafeWindowResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_build_safe_window_execute_plan(const SimCudaPersistentSafeStoreHandle &handle,
                                                  int queryLength,
                                                  int targetLength,
                                                  int summaryRowStart,
                                                  const vector<int> &rowMinCols,
                                                  const vector<int> &rowMaxCols,
                                                  SimScanCudaSafeWindowPlannerMode plannerMode,
                                                  int maxWindowCount,
                                                  SimScanCudaSafeWindowExecutePlanResult *outResult,
                                                  string *errorOut)
{
  (void)handle;
  (void)queryLength;
  (void)targetLength;
  (void)summaryRowStart;
  (void)rowMinCols;
  (void)rowMaxCols;
  (void)plannerMode;
  (void)maxWindowCount;
  if(outResult != NULL)
  {
    *outResult = SimScanCudaSafeWindowExecutePlanResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(const SimCudaPersistentSafeStoreHandle &handle,
                                                                              int maxProposalCount,
                                                                              vector<SimScanCudaCandidateState> *outSelectedStates,
                                                                              string *errorOut,
                                                                              bool *outUsedFrontierCache)
{
  (void)handle;
  (void)maxProposalCount;
  (void)outUsedFrontierCache;
  if(outSelectedStates != NULL)
  {
    outSelectedStates->clear();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_update_persistent_safe_candidate_state_store(const vector<SimScanCudaCandidateState> &updatedStates,
                                                                const vector<SimScanCudaCandidateState> &finalCandidates,
                                                                int runningMin,
                                                                SimCudaPersistentSafeStoreHandle *handle,
                                                                string *errorOut)
{
  (void)updatedStates;
  (void)finalCandidates;
  (void)runningMin;
  if(handle != NULL)
  {
    *handle = SimCudaPersistentSafeStoreHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
  const vector<SimScanCudaInitialRunSummary> &summaries,
  const vector<SimScanCudaCandidateState> &finalCandidates,
  int runningMin,
  SimCudaPersistentSafeStoreHandle *handleOut,
  double *outBuildSeconds,
  double *outPruneSeconds,
  double *outFrontierUploadSeconds,
  string *errorOut)
{
  (void)summaries;
  (void)finalCandidates;
  (void)runningMin;
  if(handleOut != NULL)
  {
    *handleOut = SimCudaPersistentSafeStoreHandle();
  }
  if(outBuildSeconds != NULL)
  {
    *outBuildSeconds = 0.0;
  }
  if(outPruneSeconds != NULL)
  {
    *outPruneSeconds = 0.0;
  }
  if(outFrontierUploadSeconds != NULL)
  {
    *outFrontierUploadSeconds = 0.0;
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_apply_region_candidate_states_residency(const vector<SimScanCudaRequest> &requests,
                                                           const vector<SimScanCudaCandidateState> &seedCandidates,
                                                           int seedRunningMin,
                                                           SimCudaPersistentSafeStoreHandle *handle,
                                                           SimScanCudaRegionResidencyResult *outResult,
                                                           SimScanCudaBatchResult *batchResult,
                                                           string *errorOut,
                                                           bool materializeFrontierStatesToHost)
{
  (void)requests;
  (void)seedCandidates;
  (void)seedRunningMin;
  (void)materializeFrontierStatesToHost;
  if(handle != NULL)
  {
    *handle = SimCudaPersistentSafeStoreHandle();
  }
  if(outResult != NULL)
  {
    *outResult = SimScanCudaRegionResidencyResult();
  }
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

void sim_scan_cuda_release_persistent_safe_candidate_state_store(SimCudaPersistentSafeStoreHandle *handle)
{
  if(handle != NULL)
  {
    *handle = SimCudaPersistentSafeStoreHandle();
  }
}

bool sim_scan_cuda_enumerate_events_row_major_batch(const vector<SimScanCudaRequest> &requests,
                                                    vector<SimScanCudaRequestResult> *outResults,
                                                    SimScanCudaBatchResult *batchResult,
                                                    string *errorOut)
{
  if(outResults == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  outResults->clear();
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(requests.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  for(size_t i = 0; i < requests.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[i];
    SimScanCudaRequestResult requestResult;
    SimScanCudaBatchResult requestBatchResult;
    bool ok = false;
    if(request.kind == SIM_SCAN_CUDA_REQUEST_INITIAL)
    {
      ok = sim_scan_cuda_enumerate_initial_events_row_major(request.A,
                                                            request.B,
                                                            request.queryLength,
                                                            request.targetLength,
                                                            request.gapOpen,
                                                            request.gapExtend,
                                                            request.scoreMatrix,
                                                            request.eventScoreFloor,
                                                            request.reduceCandidates,
                                                            request.proposalCandidates,
                                                            &requestResult.initialRunSummaries,
                                                            &requestResult.candidateStates,
                                                            &requestResult.allCandidateStates,
                                                            &requestResult.allCandidateStateCount,
                                                            &requestResult.runningMin,
                                                            &requestResult.eventCount,
                                                            &requestResult.runSummaryCount,
                                                            &requestBatchResult,
                                                            errorOut);
    }
    else if(request.kind == SIM_SCAN_CUDA_REQUEST_REGION)
    {
      int requestEventCount = 0;
      ok = sim_scan_cuda_enumerate_region_events_row_major(request.A,
                                                           request.B,
                                                           request.queryLength,
                                                           request.targetLength,
                                                           request.rowStart,
                                                           request.rowEnd,
                                                           request.colStart,
                                                           request.colEnd,
                                                           request.gapOpen,
                                                           request.gapExtend,
                                                           request.scoreMatrix,
                                                           request.eventScoreFloor,
                                                           request.blockedWords,
                                                           request.blockedWordStart,
                                                           request.blockedWordCount,
                                                           request.blockedWordStride,
                                                           request.reduceCandidates,
                                                           request.reduceAllCandidateStates,
                                                           request.filterStartCoords,
                                                           request.filterStartCoordCount,
                                                           request.seedCandidates,
                                                           request.seedCandidateCount,
                                                           request.seedRunningMin,
                                                           &requestResult.candidateStates,
                                                           &requestResult.runningMin,
                                                           &requestEventCount,
                                                           &requestResult.runSummaryCount,
                                                           &requestResult.events,
                                                           &requestResult.rowOffsets,
                                                           &requestBatchResult,
                                                           errorOut);
      requestResult.eventCount = static_cast<uint64_t>(requestEventCount);
    }
    else
    {
      if(errorOut != NULL)
      {
        *errorOut = "unknown SIM scan CUDA request kind";
      }
      ok = false;
    }

    if(!ok)
    {
      outResults->clear();
      if(batchResult != NULL)
      {
        *batchResult = SimScanCudaBatchResult();
      }
      return false;
    }

    outResults->push_back(requestResult);
    if(batchResult != NULL)
    {
      batchResult->gpuSeconds += requestBatchResult.gpuSeconds;
      batchResult->d2hSeconds += requestBatchResult.d2hSeconds;
      batchResult->usedCuda = batchResult->usedCuda || requestBatchResult.usedCuda;
      batchResult->taskCount += requestBatchResult.taskCount;
      batchResult->launchCount += requestBatchResult.launchCount;
    }
  }

  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool sim_scan_cuda_enumerate_region_candidate_states_aggregated(const vector<SimScanCudaRequest> &requests,
                                                                SimScanCudaRegionAggregationResult *outResult,
                                                                SimScanCudaBatchResult *batchResult,
                                                                string *errorOut)
{
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  *outResult = SimScanCudaRegionAggregationResult();
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(requests.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_enumerate_initial_events_row_major(const char *A,
                                                      const char *B,
                                                      int queryLength,
                                                      int targetLength,
                                                      int gapOpen,
                                                      int gapExtend,
                                                      const int scoreMatrix[128][128],
                                                      int eventScoreFloor,
                                                      bool reduceCandidates,
                                                      bool proposalCandidates,
                                                      vector<SimScanCudaInitialRunSummary> *outRunSummaries,
                                                      vector<SimScanCudaCandidateState> *outCandidateStates,
                                                      vector<SimScanCudaCandidateState> *outAllCandidateStates,
                                                      uint64_t *outAllCandidateStateCount,
                                                      int *outRunningMin,
                                                      uint64_t *outEventCount,
                                                      uint64_t *outRunSummaryCount,
                                                      SimScanCudaBatchResult *batchResult,
                                                      string *errorOut,
                                                      SimCudaPersistentSafeStoreHandle *outPersistentSafeStoreHandle)
{
  (void)A;
  (void)B;
  (void)queryLength;
  (void)targetLength;
  (void)gapOpen;
  (void)gapExtend;
  (void)scoreMatrix;
  (void)eventScoreFloor;
  (void)reduceCandidates;
  (void)proposalCandidates;
  if(outRunSummaries != NULL)
  {
    outRunSummaries->clear();
  }
  if(outCandidateStates != NULL)
  {
    outCandidateStates->clear();
  }
  if(outAllCandidateStates != NULL)
  {
    outAllCandidateStates->clear();
  }
  if(outRunningMin != NULL)
  {
    *outRunningMin = 0;
  }
  if(outAllCandidateStateCount != NULL)
  {
    *outAllCandidateStateCount = 0;
  }
  if(outEventCount != NULL)
  {
    *outEventCount = 0;
  }
  if(outRunSummaryCount != NULL)
  {
    *outRunSummaryCount = 0;
  }
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(outPersistentSafeStoreHandle != NULL)
  {
    *outPersistentSafeStoreHandle = SimCudaPersistentSafeStoreHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_enumerate_initial_events_row_major_true_batch(const vector<SimScanCudaInitialBatchRequest> &requests,
                                                                 vector<SimScanCudaInitialBatchResult> *outResults,
                                                                 SimScanCudaBatchResult *batchResult,
                                                                 string *errorOut)
{
  if(outResults == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  outResults->clear();
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(requests.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_reduce_initial_run_summaries_for_test(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                         vector<SimScanCudaCandidateState> *outCandidateStates,
                                                         int *outRunningMin,
                                                         SimScanCudaInitialReduceReplayStats *outReplayStats,
                                                         string *errorOut,
                                                         SimScanCudaOrderedMaintenanceReplayDigestStats *outDigestStats)
{
  (void)summaries;
  if(outCandidateStates != NULL)
  {
    outCandidateStates->clear();
  }
  if(outRunningMin != NULL)
  {
    *outRunningMin = 0;
  }
  if(outReplayStats != NULL)
  {
    *outReplayStats = SimScanCudaInitialReduceReplayStats();
  }
  if(outDigestStats != NULL)
  {
    *outDigestStats = SimScanCudaOrderedMaintenanceReplayDigestStats();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_select_top_disjoint_candidate_states(const vector<SimScanCudaCandidateState> &candidateStates,
                                                        int maxProposalCount,
                                                        vector<SimScanCudaCandidateState> *outSelectedStates,
                                                        string *errorOut)
{
  (void)candidateStates;
  (void)maxProposalCount;
  if(outSelectedStates != NULL)
  {
    outSelectedStates->clear();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_scan_cuda_enumerate_region_events_row_major(const char *A,
                                                     const char *B,
                                                     int queryLength,
                                                     int targetLength,
                                                     int rowStart,
                                                     int rowEnd,
                                                     int colStart,
                                                     int colEnd,
                                                     int gapOpen,
                                                     int gapExtend,
                                                     const int scoreMatrix[128][128],
                                                     int eventScoreFloor,
                                                     const uint64_t *blockedWords,
                                                     int blockedWordStart,
                                                     int blockedWordCount,
                                                     int blockedWordStride,
                                                     bool reduceCandidates,
                                                     bool reduceAllCandidateStates,
                                                     const uint64_t *filterStartCoords,
                                                     int filterStartCoordCount,
                                                     const SimScanCudaCandidateState *seedCandidates,
                                                     int seedCandidateCount,
                                                     int seedRunningMin,
                                                     vector<SimScanCudaCandidateState> *outCandidateStates,
                                                     int *outRunningMin,
                                                     int *outEventCount,
                                                     uint64_t *outRunSummaryCount,
                                                     vector<SimScanCudaRowEvent> *outEvents,
                                                     vector<int> *outRowOffsets,
                                                     SimScanCudaBatchResult *batchResult,
                                                     string *errorOut)
{
  (void)A;
  (void)B;
  (void)queryLength;
  (void)targetLength;
  (void)rowStart;
  (void)rowEnd;
  (void)colStart;
  (void)colEnd;
  (void)gapOpen;
  (void)gapExtend;
  (void)scoreMatrix;
  (void)eventScoreFloor;
  (void)blockedWords;
  (void)blockedWordStart;
  (void)blockedWordCount;
  (void)blockedWordStride;
  (void)reduceCandidates;
  (void)reduceAllCandidateStates;
  (void)filterStartCoords;
  (void)filterStartCoordCount;
  (void)seedCandidates;
  (void)seedCandidateCount;
  (void)seedRunningMin;
  if(outCandidateStates != NULL)
  {
    outCandidateStates->clear();
  }
  if(outRunningMin != NULL)
  {
    *outRunningMin = 0;
  }
  if(outEventCount != NULL)
  {
    *outEventCount = 0;
  }
  if(outRunSummaryCount != NULL)
  {
    *outRunSummaryCount = 0;
  }
  if(outEvents != NULL)
  {
    outEvents->clear();
  }
  if(outRowOffsets != NULL)
  {
    outRowOffsets->clear();
  }
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}
