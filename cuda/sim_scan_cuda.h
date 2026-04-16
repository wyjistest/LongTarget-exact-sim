#ifndef LONGTARGET_SIM_SCAN_CUDA_H
#define LONGTARGET_SIM_SCAN_CUDA_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#if defined(__CUDACC__)
#define LONGTARGET_SIM_SCAN_HOST_DEVICE __host__ __device__ __forceinline__
#else
#define LONGTARGET_SIM_SCAN_HOST_DEVICE inline
#endif

struct SimScanCudaRowEvent
{
  int score;
  uint64_t startCoord;
  uint32_t endI;
  uint32_t endJ;
};

struct SimScanCudaInitialRunSummary
{
  int score;
  uint64_t startCoord;
  uint32_t endI;
  uint32_t minEndJ;
  uint32_t maxEndJ;
  uint32_t scoreEndJ;
};

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaInitialRunStartsAt(const SimScanCudaRowEvent *events,
                                                                   int rowStartIndex,
                                                                   int eventIndex)
{
  return eventIndex == rowStartIndex ||
         events[eventIndex].startCoord != events[eventIndex - 1].startCoord;
}

inline bool simScanCudaInitialRunStartsAt(const std::vector<SimScanCudaRowEvent> &events,
                                          int rowStartIndex,
                                          int eventIndex)
{
  return rowStartIndex >= 0 &&
         eventIndex >= rowStartIndex &&
         static_cast<size_t>(eventIndex) < events.size() &&
         simScanCudaInitialRunStartsAt(events.data(), rowStartIndex, eventIndex);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE int simScanCudaInitialRunEndExclusive(const SimScanCudaRowEvent *events,
                                                                      int rowEndIndex,
                                                                      int runStartIndex)
{
  const uint64_t startCoord = events[runStartIndex].startCoord;
  int eventIndex = runStartIndex + 1;
  while(eventIndex < rowEndIndex && events[eventIndex].startCoord == startCoord)
  {
    ++eventIndex;
  }
  return eventIndex;
}

inline int simScanCudaInitialRunEndExclusive(const std::vector<SimScanCudaRowEvent> &events,
                                             int rowEndIndex,
                                             int runStartIndex)
{
  if(runStartIndex < 0 ||
     rowEndIndex < runStartIndex ||
     static_cast<size_t>(runStartIndex) >= events.size())
  {
    return runStartIndex;
  }
  const int clampedRowEndIndex =
    rowEndIndex < static_cast<int>(events.size()) ?
    rowEndIndex :
    static_cast<int>(events.size());
  return simScanCudaInitialRunEndExclusive(events.data(),
                                           clampedRowEndIndex,
                                           runStartIndex);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaInitialMatrixRunStartsAt(int score,
                                                                         uint64_t startCoord,
                                                                         int prevScore,
                                                                         uint64_t prevStartCoord,
                                                                         uint32_t endJ,
                                                                         int eventScoreFloor)
{
  return score > eventScoreFloor &&
         (endJ == 1 || prevScore <= eventScoreFloor || startCoord != prevStartCoord);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void initSimCudaInitialRunSummaryFromCell(int score,
                                                                          uint64_t startCoord,
                                                                          uint32_t endI,
                                                                          uint32_t endJ,
                                                                          SimScanCudaInitialRunSummary &summary)
{
  summary.score = score;
  summary.startCoord = startCoord;
  summary.endI = endI;
  summary.minEndJ = endJ;
  summary.maxEndJ = endJ;
  summary.scoreEndJ = endJ;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void updateSimCudaInitialRunSummaryFromCell(int score,
                                                                            uint32_t endJ,
                                                                            SimScanCudaInitialRunSummary &summary)
{
  if(endJ < summary.minEndJ) summary.minEndJ = endJ;
  if(endJ > summary.maxEndJ) summary.maxEndJ = endJ;
  if(score > summary.score)
  {
    summary.score = score;
    summary.scoreEndJ = endJ;
  }
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void initSimCudaInitialRunSummary(const SimScanCudaRowEvent &event,
                                                                  SimScanCudaInitialRunSummary &summary)
{
  initSimCudaInitialRunSummaryFromCell(event.score,event.startCoord,event.endI,event.endJ,summary);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void updateSimCudaInitialRunSummary(const SimScanCudaRowEvent &event,
                                                                    SimScanCudaInitialRunSummary &summary)
{
  updateSimCudaInitialRunSummaryFromCell(event.score,event.endJ,summary);
}

struct SimScanCudaProposalRowSummaryState
{
  int hasSummary;
  SimScanCudaInitialRunSummary summary;
};

LONGTARGET_SIM_SCAN_HOST_DEVICE void resetSimScanCudaProposalRowSummaryState(SimScanCudaProposalRowSummaryState &state)
{
  state.hasSummary = 0;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaProposalRowSummaryFlush(SimScanCudaProposalRowSummaryState &state,
                                                                        SimScanCudaInitialRunSummary *flushedSummary)
{
  if(state.hasSummary == 0)
  {
    return false;
  }
  if(flushedSummary != NULL)
  {
    *flushedSummary = state.summary;
  }
  state.hasSummary = 0;
  return true;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaProposalRowSummaryPushEvent(const SimScanCudaRowEvent &event,
                                                                            SimScanCudaProposalRowSummaryState &state,
                                                                            SimScanCudaInitialRunSummary *flushedSummary)
{
  if(state.hasSummary == 0)
  {
    initSimCudaInitialRunSummary(event,state.summary);
    state.hasSummary = 1;
    return false;
  }
  if(state.summary.startCoord == event.startCoord)
  {
    updateSimCudaInitialRunSummary(event,state.summary);
    return false;
  }
  if(flushedSummary != NULL)
  {
    *flushedSummary = state.summary;
  }
  initSimCudaInitialRunSummary(event,state.summary);
  state.hasSummary = 1;
  return true;
}

struct SimScanCudaCandidateState
{
  int score;
  int startI;
  int startJ;
  int endI;
  int endJ;
  int top;
  int bot;
  int left;
  int right;
};

LONGTARGET_SIM_SCAN_HOST_DEVICE uint64_t simScanCudaCandidateStateStartCoord(const SimScanCudaCandidateState &candidate)
{
  return (static_cast<uint64_t>(static_cast<uint32_t>(candidate.startI)) << 32) |
         static_cast<uint64_t>(static_cast<uint32_t>(candidate.startJ));
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaCandidateStateMatchesStartCoord(const SimScanCudaCandidateState &candidate,
                                                                                uint64_t startCoord)
{
  return simScanCudaCandidateStateStartCoord(candidate) == startCoord;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaCandidateStateBoxesOverlap(const SimScanCudaCandidateState &lhs,
                                                                           const SimScanCudaCandidateState &rhs)
{
  return lhs.top <= rhs.bot &&
         rhs.top <= lhs.bot &&
         lhs.left <= rhs.right &&
         rhs.left <= lhs.right;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void initSimScanCudaCandidateStateFromInitialRunSummary(const SimScanCudaInitialRunSummary &summary,
                                                                                         SimScanCudaCandidateState &candidate)
{
  candidate.score = summary.score;
  candidate.startI = static_cast<int>(summary.startCoord >> 32);
  candidate.startJ = static_cast<int>(summary.startCoord & 0xffffffffu);
  candidate.endI = static_cast<int>(summary.endI);
  candidate.endJ = static_cast<int>(summary.scoreEndJ);
  candidate.top = static_cast<int>(summary.endI);
  candidate.bot = static_cast<int>(summary.endI);
  candidate.left = static_cast<int>(summary.minEndJ);
  candidate.right = static_cast<int>(summary.maxEndJ);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool updateSimScanCudaCandidateStateFromInitialRunSummary(const SimScanCudaInitialRunSummary &summary,
                                                                                           SimScanCudaCandidateState &candidate)
{
  const bool improved = candidate.score < summary.score;
  if(improved)
  {
    candidate.score = summary.score;
    candidate.endI = static_cast<int>(summary.endI);
    candidate.endJ = static_cast<int>(summary.scoreEndJ);
  }
  if(candidate.top > static_cast<int>(summary.endI)) candidate.top = static_cast<int>(summary.endI);
  if(candidate.bot < static_cast<int>(summary.endI)) candidate.bot = static_cast<int>(summary.endI);
  if(candidate.left > static_cast<int>(summary.minEndJ)) candidate.left = static_cast<int>(summary.minEndJ);
  if(candidate.right < static_cast<int>(summary.maxEndJ)) candidate.right = static_cast<int>(summary.maxEndJ);
  return improved;
}

struct SimScanCudaInitialReduceReplayStats
{
  SimScanCudaInitialReduceReplayStats():
    chunkCount(0),
    chunkReplayedCount(0),
    chunkSkippedCount(0),
    summaryReplayCount(0)
  {
  }

  uint64_t chunkCount;
  uint64_t chunkReplayedCount;
  uint64_t chunkSkippedCount;
  uint64_t summaryReplayCount;
};

struct SimCudaPersistentSafeStoreHandle
{
  SimCudaPersistentSafeStoreHandle():
    valid(false),
    device(0),
    slot(0),
    stateCount(0),
    statesDevice(0),
    frontierValid(false),
    frontierRunningMin(0),
    frontierCapacity(0),
    frontierCount(0),
    frontierStatesDevice(0)
  {
  }

  bool valid;
  int device;
  int slot;
  size_t stateCount;
  uintptr_t statesDevice;
  bool frontierValid;
  int frontierRunningMin;
  size_t frontierCapacity;
  size_t frontierCount;
  uintptr_t frontierStatesDevice;
};

struct SimScanCudaColumnInterval
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE SimScanCudaColumnInterval():
    colStart(0),
    colEnd(0)
  {
  }

  LONGTARGET_SIM_SCAN_HOST_DEVICE SimScanCudaColumnInterval(int startValue,int endValue):
    colStart(startValue),
    colEnd(endValue)
  {
  }

  int colStart;
  int colEnd;
};

struct SimScanCudaSafeWindow
{
  SimScanCudaSafeWindow():
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0)
  {
  }

  SimScanCudaSafeWindow(int rowStartValue,
                        int rowEndValue,
                        int colStartValue,
                        int colEndValue):
    rowStart(rowStartValue),
    rowEnd(rowEndValue),
    colStart(colStartValue),
    colEnd(colEndValue)
  {
  }

  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
};

enum SimScanCudaSafeWindowPlannerMode
{
  SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE = 0,
  SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1 = 1
};

enum SimScanCudaRequestKind
{
  SIM_SCAN_CUDA_REQUEST_INITIAL = 0,
  SIM_SCAN_CUDA_REQUEST_REGION = 1
};

struct SimScanCudaRequest
{
  SimScanCudaRequest():
    kind(SIM_SCAN_CUDA_REQUEST_INITIAL),
    A(NULL),
    B(NULL),
    queryLength(0),
    targetLength(0),
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0),
    gapOpen(0),
    gapExtend(0),
    scoreMatrix(NULL),
    eventScoreFloor(0),
    blockedWords(NULL),
    blockedWordStart(0),
    blockedWordCount(0),
    blockedWordStride(0),
    reduceCandidates(false),
    proposalCandidates(false),
    persistAllCandidateStatesOnDevice(false),
    reduceAllCandidateStates(false),
    filterStartCoords(NULL),
    filterStartCoordCount(0),
    seedCandidates(NULL),
    seedCandidateCount(0),
    seedRunningMin(0)
  {
  }

  SimScanCudaRequestKind kind;
  const char *A;
  const char *B;
  int queryLength;
  int targetLength;
  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
  int gapOpen;
  int gapExtend;
  const int (*scoreMatrix)[128];
  int eventScoreFloor;
  const uint64_t *blockedWords;
  int blockedWordStart;
  int blockedWordCount;
  int blockedWordStride;
  bool reduceCandidates;
  bool proposalCandidates;
  bool persistAllCandidateStatesOnDevice;
  bool reduceAllCandidateStates;
  const uint64_t *filterStartCoords;
  int filterStartCoordCount;
  const SimScanCudaCandidateState *seedCandidates;
  int seedCandidateCount;
  int seedRunningMin;
};

struct SimScanCudaRequestResult
{
  std::vector<SimScanCudaRowEvent> events;
  std::vector<int> rowOffsets;
  std::vector<SimScanCudaInitialRunSummary> initialRunSummaries;
  std::vector<SimScanCudaCandidateState> candidateStates;
  std::vector<SimScanCudaCandidateState> allCandidateStates;
  SimCudaPersistentSafeStoreHandle persistentSafeStoreHandle;
  uint64_t allCandidateStateCount;
  int runningMin;
  uint64_t eventCount;
  uint64_t runSummaryCount;

  SimScanCudaRequestResult():allCandidateStateCount(0),runningMin(0),eventCount(0),runSummaryCount(0) {}
};

struct SimScanCudaRegionAggregationResult
{
  std::vector<SimScanCudaCandidateState> candidateStates;
  uint64_t eventCount;
  uint64_t runSummaryCount;
  uint64_t preAggregateCandidateStateCount;
  uint64_t postAggregateCandidateStateCount;
  uint64_t affectedStartCount;
  int runningMin;

  SimScanCudaRegionAggregationResult():
    eventCount(0),
    runSummaryCount(0),
    preAggregateCandidateStateCount(0),
    postAggregateCandidateStateCount(0),
    affectedStartCount(0),
    runningMin(0)
  {
  }
};

struct SimScanCudaRegionResidencyResult
{
  std::vector<SimScanCudaCandidateState> frontierStates;
  uint64_t frontierStateCount;
  int runningMin;
  uint64_t eventCount;
  uint64_t runSummaryCount;
  uint64_t updatedStateCount;

  SimScanCudaRegionResidencyResult():
    frontierStateCount(0),
    runningMin(0),
    eventCount(0),
    runSummaryCount(0),
    updatedStateCount(0)
  {
  }
};

struct SimScanCudaInitialBatchRequest
{
  SimScanCudaInitialBatchRequest():
    A(NULL),
    B(NULL),
    queryLength(0),
    targetLength(0),
    gapOpen(0),
    gapExtend(0),
    scoreMatrix(NULL),
    eventScoreFloor(0),
    reduceCandidates(false),
    proposalCandidates(false),
    persistAllCandidateStatesOnDevice(false),
    seedCandidates(NULL),
    seedCandidateCount(0),
    seedRunningMin(0)
  {
  }

  const char *A;
  const char *B;
  int queryLength;
  int targetLength;
  int gapOpen;
  int gapExtend;
  const int (*scoreMatrix)[128];
  int eventScoreFloor;
  bool reduceCandidates;
  bool proposalCandidates;
  bool persistAllCandidateStatesOnDevice;
  const SimScanCudaCandidateState *seedCandidates;
  int seedCandidateCount;
  int seedRunningMin;
};

struct SimScanCudaInitialBatchResult
{
  std::vector<SimScanCudaInitialRunSummary> initialRunSummaries;
  std::vector<SimScanCudaCandidateState> candidateStates;
  std::vector<SimScanCudaCandidateState> allCandidateStates;
  SimCudaPersistentSafeStoreHandle persistentSafeStoreHandle;
  uint64_t allCandidateStateCount;
  int runningMin;
  uint64_t eventCount;
  uint64_t runSummaryCount;

  SimScanCudaInitialBatchResult():allCandidateStateCount(0),runningMin(0),eventCount(0),runSummaryCount(0) {}
};

struct SimScanCudaBatchResult
{
  SimScanCudaBatchResult():
    gpuSeconds(0.0),
    d2hSeconds(0.0),
    proposalSelectGpuSeconds(0.0),
    initialDiagSeconds(0.0),
    initialOnlineReduceSeconds(0.0),
    initialWaitSeconds(0.0),
    initialCountCopySeconds(0.0),
    initialBaseUploadSeconds(0.0),
    initialProposalDirectTopKGpuSeconds(0.0),
    initialProposalV3GpuSeconds(0.0),
    initialProposalSelectD2HSeconds(0.0),
    initialSyncWaitSeconds(0.0),
    initialScanTailSeconds(0.0),
    initialHashReduceSeconds(0.0),
    initialSegmentedReduceSeconds(0.0),
    initialSegmentedCompactSeconds(0.0),
    initialOrderedReplaySeconds(0.0),
    initialTopKSeconds(0.0),
    usedCuda(false),
    usedRegionTrueBatchPath(false),
    usedRegionPackedAggregationPath(false),
    usedInitialDirectSummaryPath(false),
    usedInitialHashReducePath(false),
    usedInitialSegmentedReducePath(false),
    usedInitialDeviceResidencyPath(false),
    usedInitialProposalOnlinePath(false),
    usedInitialProposalV2Path(false),
    usedInitialProposalV2DirectTopKPath(false),
    usedInitialProposalV3Path(false),
    initialHashReduceFallback(false),
    initialSegmentedFallback(false),
    initialProposalOnlineFallback(false),
    regionTrueBatchRequestCount(0),
    regionPackedAggregationRequestCount(0),
    initialDeviceResidencyRequestCount(0),
    initialProposalV2RequestCount(0),
    initialProposalV3RequestCount(0),
    initialProposalV3SelectedStateCount(0),
    initialProposalLogicalCandidateCount(0),
    initialProposalMaterializedCandidateCount(0),
    initialSegmentedTileStateCount(0),
    initialSegmentedGroupedStateCount(0),
    taskCount(0),
    launchCount(0),
    initialReduceReplayStats()
  {}

  double gpuSeconds;
  double d2hSeconds;
  double proposalSelectGpuSeconds;
  double initialDiagSeconds;
  double initialOnlineReduceSeconds;
  double initialWaitSeconds;
  double initialCountCopySeconds;
  double initialBaseUploadSeconds;
  double initialProposalDirectTopKGpuSeconds;
  double initialProposalV3GpuSeconds;
  double initialProposalSelectD2HSeconds;
  double initialSyncWaitSeconds;
  double initialScanTailSeconds;
  double initialHashReduceSeconds;
  double initialSegmentedReduceSeconds;
  double initialSegmentedCompactSeconds;
  double initialOrderedReplaySeconds;
  double initialTopKSeconds;
  bool usedCuda;
  bool usedRegionTrueBatchPath;
  bool usedRegionPackedAggregationPath;
  bool usedInitialDirectSummaryPath;
  bool usedInitialHashReducePath;
  bool usedInitialSegmentedReducePath;
  bool usedInitialDeviceResidencyPath;
  bool usedInitialProposalOnlinePath;
  bool usedInitialProposalV2Path;
  bool usedInitialProposalV2DirectTopKPath;
  bool usedInitialProposalV3Path;
  bool initialHashReduceFallback;
  bool initialSegmentedFallback;
  bool initialProposalOnlineFallback;
  uint64_t regionTrueBatchRequestCount;
  uint64_t regionPackedAggregationRequestCount;
  uint64_t initialDeviceResidencyRequestCount;
  uint64_t initialProposalV2RequestCount;
  uint64_t initialProposalV3RequestCount;
  uint64_t initialProposalV3SelectedStateCount;
  uint64_t initialProposalLogicalCandidateCount;
  uint64_t initialProposalMaterializedCandidateCount;
  uint64_t initialSegmentedTileStateCount;
  uint64_t initialSegmentedGroupedStateCount;
  uint64_t taskCount;
  uint64_t launchCount;
  SimScanCudaInitialReduceReplayStats initialReduceReplayStats;
};

struct SimScanCudaSafeWindowResult
{
  SimScanCudaSafeWindowResult():
    affectedCandidateCount(0),
    overflowFallback(false),
    coordBytesD2H(0),
    gpuSeconds(0.0),
    d2hSeconds(0.0)
  {
  }

  std::vector<SimScanCudaSafeWindow> windows;
  std::vector<uint64_t> affectedStartCoords;
  uint64_t affectedCandidateCount;
  bool overflowFallback;
  uint64_t coordBytesD2H;
  double gpuSeconds;
  double d2hSeconds;
};

struct SimScanCudaSafeWindowExecutePlanResult
{
  SimScanCudaSafeWindowExecutePlanResult():
    windowCount(0),
    affectedStartCount(0),
    execBandCount(0),
    execCellCount(0),
    overflowFallback(false),
    emptyPlan(true),
    coordBytesD2H(0),
    gpuSeconds(0.0),
    d2hSeconds(0.0)
  {
  }

  std::vector<SimScanCudaSafeWindow> execWindows;
  std::vector<uint64_t> uniqueAffectedStartCoords;
  uint64_t windowCount;
  uint64_t affectedStartCount;
  uint64_t execBandCount;
  uint64_t execCellCount;
  bool overflowFallback;
  bool emptyPlan;
  uint64_t coordBytesD2H;
  double gpuSeconds;
  double d2hSeconds;
};

bool sim_scan_cuda_is_built();
bool sim_scan_cuda_init(int device,std::string *errorOut);

bool sim_scan_cuda_upload_persistent_safe_candidate_state_store(const SimScanCudaCandidateState *states,
                                                                size_t stateCount,
                                                                SimCudaPersistentSafeStoreHandle *handleOut,
                                                                std::string *errorOut);

bool sim_scan_cuda_erase_persistent_safe_candidate_state_store_start_coords(const uint64_t *startCoords,
                                                                            size_t startCoordCount,
                                                                            SimCudaPersistentSafeStoreHandle *handle,
                                                                            std::string *errorOut);

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_path_summary(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                int summaryRowStart,
                                                                                const std::vector<int> &rowMinCols,
                                                                                const std::vector<int> &rowMaxCols,
                                                                                std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                std::string *errorOut);

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                 int queryLength,
                                                                                 int targetLength,
                                                                                 const std::vector<int> &rowOffsets,
                                                                                 const std::vector<SimScanCudaColumnInterval> &intervals,
                                                                                 std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                 std::string *errorOut);

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_start_coords_by_row_intervals(
  const SimCudaPersistentSafeStoreHandle &handle,
  int queryLength,
  int targetLength,
  const std::vector<int> &rowOffsets,
  const std::vector<SimScanCudaColumnInterval> &intervals,
  std::vector<uint64_t> *outStartCoords,
  std::string *errorOut);

bool sim_scan_cuda_select_safe_workset_windows(const SimCudaPersistentSafeStoreHandle &handle,
                                               int queryLength,
                                               int targetLength,
                                               int summaryRowStart,
                                               const std::vector<int> &rowMinCols,
                                               const std::vector<int> &rowMaxCols,
                                               SimScanCudaSafeWindowPlannerMode plannerMode,
                                               int maxWindowCount,
                                               SimScanCudaSafeWindowResult *outResult,
                                               std::string *errorOut);

bool sim_scan_cuda_build_safe_window_execute_plan(const SimCudaPersistentSafeStoreHandle &handle,
                                                  int queryLength,
                                                  int targetLength,
                                                  int summaryRowStart,
                                                  const std::vector<int> &rowMinCols,
                                                  const std::vector<int> &rowMaxCols,
                                                  SimScanCudaSafeWindowPlannerMode plannerMode,
                                                  int maxWindowCount,
                                                  SimScanCudaSafeWindowExecutePlanResult *outResult,
                                                  std::string *errorOut);

bool sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(const SimCudaPersistentSafeStoreHandle &handle,
                                                                              int maxProposalCount,
                                                                              std::vector<SimScanCudaCandidateState> *outSelectedStates,
                                                                              std::string *errorOut,
                                                                              bool *outUsedFrontierCache = NULL);

bool sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
  const std::vector<SimScanCudaInitialRunSummary> &summaries,
  const std::vector<SimScanCudaCandidateState> &finalCandidates,
  int runningMin,
  SimCudaPersistentSafeStoreHandle *handleOut,
  double *outBuildSeconds,
  double *outPruneSeconds,
  double *outFrontierUploadSeconds,
  std::string *errorOut);

bool sim_scan_cuda_update_persistent_safe_candidate_state_store(const std::vector<SimScanCudaCandidateState> &updatedStates,
                                                                const std::vector<SimScanCudaCandidateState> &finalCandidates,
                                                                int runningMin,
                                                                SimCudaPersistentSafeStoreHandle *handle,
                                                                std::string *errorOut);

void sim_scan_cuda_release_persistent_safe_candidate_state_store(SimCudaPersistentSafeStoreHandle *handle);

bool sim_scan_cuda_enumerate_events_row_major_batch(const std::vector<SimScanCudaRequest> &requests,
                                                    std::vector<SimScanCudaRequestResult> *outResults,
                                                    SimScanCudaBatchResult *batchResult,
                                                    std::string *errorOut);

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
                                                      std::vector<SimScanCudaInitialRunSummary> *outRunSummaries,
                                                      std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                      std::vector<SimScanCudaCandidateState> *outAllCandidateStates,
                                                      uint64_t *outAllCandidateStateCount,
                                                      int *outRunningMin,
                                                      uint64_t *outEventCount,
                                                      uint64_t *outRunSummaryCount,
                                                      SimScanCudaBatchResult *batchResult,
                                                      std::string *errorOut,
                                                      SimCudaPersistentSafeStoreHandle *outPersistentSafeStoreHandle = NULL);

bool sim_scan_cuda_enumerate_initial_events_row_major_true_batch(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                 std::vector<SimScanCudaInitialBatchResult> *outResults,
                                                                 SimScanCudaBatchResult *batchResult,
                                                                 std::string *errorOut);

bool sim_scan_cuda_reduce_initial_run_summaries_for_test(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                                         std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                         int *outRunningMin,
                                                         SimScanCudaInitialReduceReplayStats *outReplayStats,
                                                         std::string *errorOut);

bool sim_scan_cuda_select_top_disjoint_candidate_states(const std::vector<SimScanCudaCandidateState> &candidateStates,
                                                        int maxProposalCount,
                                                        std::vector<SimScanCudaCandidateState> *outSelectedStates,
                                                        std::string *errorOut);

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
                                                     std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                     int *outRunningMin,
                                                     int *outEventCount,
                                                     uint64_t *outRunSummaryCount,
                                                     std::vector<SimScanCudaRowEvent> *outEvents,
                                                     std::vector<int> *outRowOffsets,
                                                     SimScanCudaBatchResult *batchResult,
                                                     std::string *errorOut);

bool sim_scan_cuda_enumerate_region_candidate_states_aggregated(const std::vector<SimScanCudaRequest> &requests,
                                                                SimScanCudaRegionAggregationResult *outResult,
                                                                SimScanCudaBatchResult *batchResult,
                                                                std::string *errorOut);

bool sim_scan_cuda_apply_region_candidate_states_residency(
  const std::vector<SimScanCudaRequest> &requests,
  const std::vector<SimScanCudaCandidateState> &seedCandidates,
  int seedRunningMin,
  SimCudaPersistentSafeStoreHandle *handle,
  SimScanCudaRegionResidencyResult *outResult,
  SimScanCudaBatchResult *batchResult,
  std::string *errorOut,
  bool materializeFrontierStatesToHost = true);

#endif
