#ifndef LONGTARGET_SIM_SCAN_CUDA_H
#define LONGTARGET_SIM_SCAN_CUDA_H

#include <cstddef>
#include <cstdint>
#include <functional>
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

struct SimScanCudaPackedInitialRunSummary16
{
  int32_t score;
  uint16_t startI;
  uint16_t startJ;
  uint16_t endI;
  uint16_t minEndJ;
  uint16_t maxEndJ;
  uint16_t scoreEndJ;
};

static_assert(sizeof(SimScanCudaPackedInitialRunSummary16) == 16,
              "packed initial run summary must stay 16 bytes");

LONGTARGET_SIM_SCAN_HOST_DEVICE uint32_t simScanCudaInitialRunSummaryStartI(
  const SimScanCudaInitialRunSummary &summary)
{
  return static_cast<uint32_t>(summary.startCoord >> 32);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE uint32_t simScanCudaInitialRunSummaryStartJ(
  const SimScanCudaInitialRunSummary &summary)
{
  return static_cast<uint32_t>(summary.startCoord & 0xffffffffu);
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool simScanCudaInitialRunSummaryFitsPacked16(
  const SimScanCudaInitialRunSummary &summary)
{
  const uint32_t startI = simScanCudaInitialRunSummaryStartI(summary);
  const uint32_t startJ = simScanCudaInitialRunSummaryStartJ(summary);
  return startI <= 65535u &&
         startJ <= 65535u &&
         summary.endI <= 65535u &&
         summary.minEndJ <= 65535u &&
         summary.maxEndJ <= 65535u &&
         summary.scoreEndJ <= 65535u;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool packSimScanCudaInitialRunSummary16(
  const SimScanCudaInitialRunSummary &summary,
  SimScanCudaPackedInitialRunSummary16 &packed)
{
  if(!simScanCudaInitialRunSummaryFitsPacked16(summary))
  {
    return false;
  }
  packed.score = static_cast<int32_t>(summary.score);
  packed.startI = static_cast<uint16_t>(simScanCudaInitialRunSummaryStartI(summary));
  packed.startJ = static_cast<uint16_t>(simScanCudaInitialRunSummaryStartJ(summary));
  packed.endI = static_cast<uint16_t>(summary.endI);
  packed.minEndJ = static_cast<uint16_t>(summary.minEndJ);
  packed.maxEndJ = static_cast<uint16_t>(summary.maxEndJ);
  packed.scoreEndJ = static_cast<uint16_t>(summary.scoreEndJ);
  return true;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void unpackSimScanCudaInitialRunSummary16(
  const SimScanCudaPackedInitialRunSummary16 &packed,
  SimScanCudaInitialRunSummary &summary)
{
  summary.score = static_cast<int>(packed.score);
  summary.startCoord = (static_cast<uint64_t>(packed.startI) << 32) |
                       static_cast<uint64_t>(packed.startJ);
  summary.endI = static_cast<uint32_t>(packed.endI);
  summary.minEndJ = static_cast<uint32_t>(packed.minEndJ);
  summary.maxEndJ = static_cast<uint32_t>(packed.maxEndJ);
  summary.scoreEndJ = static_cast<uint32_t>(packed.scoreEndJ);
}

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

struct SimScanCudaInitialSummaryChunk
{
  SimScanCudaInitialSummaryChunk():
    batchIndex(0),
    chunkIndex(0),
    summaryBase(0),
    summaryCount(0),
    summaries(NULL)
  {
  }

  int batchIndex;
  uint64_t chunkIndex;
  uint64_t summaryBase;
  uint64_t summaryCount;
  const SimScanCudaInitialRunSummary *summaries;
};

typedef std::function<void(const SimScanCudaInitialSummaryChunk &)>
  SimScanCudaInitialSummaryChunkConsumer;

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

struct SimScanCudaFrontierDigest
{
  int candidateCount;
  int runningMin;
  uint64_t slotOrderHash;
  uint64_t candidateIdentityHash;
  uint64_t scoreHash;
  uint64_t boundsHash;
};

struct SimScanCudaFrontierTransducerShadowStats
{
  uint64_t summaryReplayCount;
  uint64_t insertCount;
  uint64_t evictionCount;
  uint64_t revisitCount;
  uint64_t sameStartUpdateCount;
  uint64_t kBoundaryReplacementCount;
};

LONGTARGET_SIM_SCAN_HOST_DEVICE uint64_t simScanCudaFrontierDigestMix(uint64_t hash,
                                                                      uint64_t value)
{
  hash ^= value + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
  hash *= 0xbf58476d1ce4e5b9ULL;
  hash ^= hash >> 31;
  return hash;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE uint64_t simScanCudaFrontierDigestInt(int value)
{
  return static_cast<uint64_t>(static_cast<uint32_t>(value));
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void resetSimScanCudaFrontierDigest(
  SimScanCudaFrontierDigest &digest,
  int candidateCount,
  int runningMin)
{
  digest.candidateCount = candidateCount;
  digest.runningMin = runningMin;
  digest.slotOrderHash = 0xcbf29ce484222325ULL;
  digest.candidateIdentityHash = 0x84222325cbf29ce4ULL;
  digest.scoreHash = 0x9e3779b97f4a7c15ULL;
  digest.boundsHash = 0xbf58476d1ce4e5b9ULL;
  digest.slotOrderHash = simScanCudaFrontierDigestMix(digest.slotOrderHash,
                                                      simScanCudaFrontierDigestInt(candidateCount));
  digest.slotOrderHash = simScanCudaFrontierDigestMix(digest.slotOrderHash,
                                                      simScanCudaFrontierDigestInt(runningMin));
  digest.candidateIdentityHash =
    simScanCudaFrontierDigestMix(digest.candidateIdentityHash,
                                 simScanCudaFrontierDigestInt(candidateCount));
  digest.scoreHash = simScanCudaFrontierDigestMix(digest.scoreHash,
                                                  simScanCudaFrontierDigestInt(runningMin));
  digest.boundsHash = simScanCudaFrontierDigestMix(digest.boundsHash,
                                                   simScanCudaFrontierDigestInt(candidateCount));
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void updateSimScanCudaFrontierDigest(
  SimScanCudaFrontierDigest &digest,
  const SimScanCudaCandidateState &state,
  int slot)
{
  const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
  digest.slotOrderHash = simScanCudaFrontierDigestMix(digest.slotOrderHash,
                                                      simScanCudaFrontierDigestInt(slot));
  digest.slotOrderHash = simScanCudaFrontierDigestMix(digest.slotOrderHash,startCoord);
  digest.candidateIdentityHash =
    simScanCudaFrontierDigestMix(digest.candidateIdentityHash,startCoord);
  digest.candidateIdentityHash =
    simScanCudaFrontierDigestMix(digest.candidateIdentityHash,
                                 simScanCudaFrontierDigestInt(state.endI));
  digest.candidateIdentityHash =
    simScanCudaFrontierDigestMix(digest.candidateIdentityHash,
                                 simScanCudaFrontierDigestInt(state.endJ));
  digest.scoreHash = simScanCudaFrontierDigestMix(digest.scoreHash,
                                                  simScanCudaFrontierDigestInt(state.score));
  digest.scoreHash = simScanCudaFrontierDigestMix(digest.scoreHash,
                                                  simScanCudaFrontierDigestInt(slot));
  digest.boundsHash = simScanCudaFrontierDigestMix(digest.boundsHash,
                                                   simScanCudaFrontierDigestInt(state.top));
  digest.boundsHash = simScanCudaFrontierDigestMix(digest.boundsHash,
                                                   simScanCudaFrontierDigestInt(state.bot));
  digest.boundsHash = simScanCudaFrontierDigestMix(digest.boundsHash,
                                                   simScanCudaFrontierDigestInt(state.left));
  digest.boundsHash = simScanCudaFrontierDigestMix(digest.boundsHash,
                                                   simScanCudaFrontierDigestInt(state.right));
}

struct SimScanCudaFrontierTransducerSegmentedShadowResult
{
  SimScanCudaFrontierTransducerSegmentedShadowResult():
    runningMin(0)
  {
    resetSimScanCudaFrontierDigest(digest,0,0);
    stats.summaryReplayCount = 0;
    stats.insertCount = 0;
    stats.evictionCount = 0;
    stats.revisitCount = 0;
    stats.sameStartUpdateCount = 0;
    stats.kBoundaryReplacementCount = 0;
  }

  std::vector<SimScanCudaCandidateState> candidateStates;
  int runningMin;
  SimScanCudaFrontierDigest digest;
  SimScanCudaFrontierTransducerShadowStats stats;
};

struct SimCudaPersistentSafeStoreHandle
{
  SimCudaPersistentSafeStoreHandle():
    valid(false),
	    device(0),
	    slot(0),
	    stateCount(0),
	    telemetryEpoch(0),
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
	  uint64_t telemetryEpoch;
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
  SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1 = 1,
  SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2 = 2
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
    seedRunningMin(0),
    initialSummaryChunkConsumer()
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
  SimScanCudaInitialSummaryChunkConsumer initialSummaryChunkConsumer;
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
    seedRunningMin(0),
    initialSummaryChunkConsumer()
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
  SimScanCudaInitialSummaryChunkConsumer initialSummaryChunkConsumer;
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

enum SimScanCudaInitialPinnedAsyncDisabledReason
{
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED = 0,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NONE = 1,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_CHUNKED_HANDOFF_OFF = 2,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_UNSUPPORTED_PATH = 3,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NO_SUMMARIES = 4,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_PACKED_SUMMARY_D2H = 5,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_HOST_COPY_ELISION = 6,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NO_CHUNKS = 7
};

enum SimScanCudaInitialPinnedAsyncSourceReadyMode
{
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE = 0,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_GLOBAL_STOP_EVENT = 1
};

enum SimScanCudaInitialPinnedAsyncCpuPipelineDisabledReason
{
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED = 0,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NONE = 1,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_PINNED_ASYNC_OFF = 2,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_CHUNKED_HANDOFF_OFF = 3,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_UNSUPPORTED_PATH = 4,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NO_SUMMARIES = 5,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NO_CHUNKS = 6,
  SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_PINNED_ASYNC_FALLBACK = 7
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
    initialSummaryPackSeconds(0.0),
    initialSummaryD2HCopySeconds(0.0),
    initialSummaryUnpackSeconds(0.0),
    initialSummaryResultMaterializeSeconds(0.0),
    initialHandoffAsyncD2HSeconds(0.0),
    initialHandoffD2HWaitSeconds(0.0),
    initialHandoffCpuApplySeconds(0.0),
    initialHandoffCpuD2HOverlapSeconds(0.0),
    initialHandoffDpD2HOverlapSeconds(0.0),
    initialHandoffCriticalPathSeconds(0.0),
    regionSingleRequestDirectReduceGpuSeconds(0.0),
    regionSingleRequestDirectReduceDpGpuSeconds(0.0),
    regionSingleRequestDirectReduceFilterReduceGpuSeconds(0.0),
    regionSingleRequestDirectReduceCompactGpuSeconds(0.0),
    regionSingleRequestDirectReduceCountD2HSeconds(0.0),
    regionSingleRequestDirectReduceCandidateCountD2HSeconds(0.0),
    regionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds(0.0),
    regionSingleRequestDirectReduceFusedDpGpuSeconds(0.0),
    regionSingleRequestDirectReduceFusedOracleDpGpuSecondsShadow(0.0),
    regionSingleRequestDirectReduceFusedTotalGpuSeconds(0.0),
    regionSingleRequestDirectReduceCoopDpGpuSeconds(0.0),
    regionSingleRequestDirectReduceCoopOracleDpGpuSecondsShadow(0.0),
    regionSingleRequestDirectReduceCoopTotalGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineMetadataH2DSeconds(0.0),
    regionSingleRequestDirectReducePipelineDiagGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineEventCountGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineEventCountD2HSeconds(0.0),
    regionSingleRequestDirectReducePipelineEventPrefixGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineRunCountGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineRunCountD2HSeconds(0.0),
    regionSingleRequestDirectReducePipelineRunPrefixGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineRunCompactGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineCandidatePrefixGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineCandidateCompactGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineCountSnapshotD2HSeconds(0.0),
    regionSingleRequestDirectReducePipelineAccountedGpuSeconds(0.0),
    regionSingleRequestDirectReducePipelineUnaccountedGpuSeconds(0.0),
    usedCuda(false),
    usedRegionTrueBatchPath(false),
    usedRegionBucketedTrueBatchPath(false),
    usedRegionPackedAggregationPath(false),
    usedRegionSingleRequestDirectReducePath(false),
    usedRegionSingleRequestDirectReduceDeferredCounts(false),
    usedInitialDirectSummaryPath(false),
    usedInitialPackedSummaryD2H(false),
    usedInitialSummaryHostCopyElision(false),
    usedInitialPinnedAsyncHandoff(false),
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
    regionBucketedTrueBatchBatches(0),
    regionBucketedTrueBatchRequests(0),
    regionBucketedTrueBatchFusedRequests(0),
    regionBucketedTrueBatchActualCells(0),
    regionBucketedTrueBatchPaddedCells(0),
    regionBucketedTrueBatchPaddingCells(0),
    regionBucketedTrueBatchRejectedPadding(0),
    regionBucketedTrueBatchShadowMismatches(0),
    regionPackedAggregationRequestCount(0),
    regionPackedAggregationZeroRunCandidateBufferEnsureSkips(0),
    regionPackedAggregationZeroRunCandidateCountD2HSkips(0),
    regionPackedAggregationNoFilterCandidateCountD2HSkips(0),
    regionPackedAggregationNoFilterCandidateCountScalarH2DSkips(0),
    regionPackedAggregationSliceTempOutputBufferEnsureSkips(0),
    regionPackedAggregationCandidateCountClearSkips(0),
    regionPackedAggregationSummaryTotalsClearSkips(0),
    regionPackedAggregationInitialSummaryTotalsBufferEnsureSkips(0),
    regionPackedAggregationInitialRunSummaryBufferEnsureSkips(0),
    regionPackedAggregationNoFilterInitialCandidateCountBufferEnsureSkips(0),
    regionPackedAggregationInitialEventBufferEnsureSkips(0),
    regionPackedAggregationFinalCompactBaseBufferEnsureSkips(0),
    regionPackedAggregationZeroRunTrueBatchRunCompactSkips(0),
    regionPackedAggregationNoFilterReservedCopySkips(0),
    regionPackedAggregationFilterReservedCopySkips(0),
    regionPackedAggregationSingleCandidateFinalReduceSkips(0),
    regionPackedAggregationSingleRequestFinalReduceSkips(0),
    regionSingleRequestDirectReduceAttempts(0),
    regionSingleRequestDirectReduceSuccesses(0),
    regionSingleRequestDirectReduceFallbacks(0),
    regionSingleRequestDirectReduceOverflows(0),
    regionSingleRequestDirectReduceShadowMismatches(0),
    regionSingleRequestDirectReduceHashCapacity(0),
    regionSingleRequestDirectReduceZeroCandidateCompactBufferEnsureSkips(0),
    regionSingleRequestDirectReduceCandidateCount(0),
    regionSingleRequestDirectReduceEventCount(0),
    regionSingleRequestDirectReduceRunSummaryCount(0),
    regionSingleRequestDirectReduceAffectedStartCount(0),
    regionSingleRequestDirectReduceReduceWorkItems(0),
    regionSingleRequestDirectReduceFusedDpAttempts(0),
    regionSingleRequestDirectReduceFusedDpEligible(0),
    regionSingleRequestDirectReduceFusedDpSuccesses(0),
    regionSingleRequestDirectReduceFusedDpFallbacks(0),
    regionSingleRequestDirectReduceFusedDpShadowMismatches(0),
    regionSingleRequestDirectReduceFusedDpRejectedByCells(0),
    regionSingleRequestDirectReduceFusedDpRejectedByDiagLen(0),
    regionSingleRequestDirectReduceFusedDpCells(0),
    regionSingleRequestDirectReduceFusedDpRequests(0),
    regionSingleRequestDirectReduceFusedDpDiagLaunchesReplaced(0),
    regionSingleRequestDirectReduceCoopDpSupported(0),
    regionSingleRequestDirectReduceCoopDpAttempts(0),
    regionSingleRequestDirectReduceCoopDpEligible(0),
    regionSingleRequestDirectReduceCoopDpSuccesses(0),
    regionSingleRequestDirectReduceCoopDpFallbacks(0),
    regionSingleRequestDirectReduceCoopDpShadowMismatches(0),
    regionSingleRequestDirectReduceCoopDpRejectedByUnsupported(0),
    regionSingleRequestDirectReduceCoopDpRejectedByCells(0),
    regionSingleRequestDirectReduceCoopDpRejectedByDiagLen(0),
    regionSingleRequestDirectReduceCoopDpRejectedByResidency(0),
    regionSingleRequestDirectReduceCoopDpCells(0),
    regionSingleRequestDirectReduceCoopDpRequests(0),
    regionSingleRequestDirectReduceCoopDpDiagLaunchesReplaced(0),
    regionSingleRequestDirectReducePipelineRequestCount(0),
    regionSingleRequestDirectReducePipelineRowCountTotal(0),
    regionSingleRequestDirectReducePipelineRowCountMax(0),
    regionSingleRequestDirectReducePipelineColCountTotal(0),
    regionSingleRequestDirectReducePipelineColCountMax(0),
    regionSingleRequestDirectReducePipelineCellCountTotal(0),
    regionSingleRequestDirectReducePipelineCellCountMax(0),
    regionSingleRequestDirectReducePipelineDiagCountTotal(0),
    regionSingleRequestDirectReducePipelineDiagCountMax(0),
    regionSingleRequestDirectReducePipelineFilterStartCountTotal(0),
    regionSingleRequestDirectReducePipelineFilterStartCountMax(0),
    regionSingleRequestDirectReducePipelineDiagLaunchCount(0),
    regionSingleRequestDirectReducePipelineEventCountLaunchCount(0),
    regionSingleRequestDirectReducePipelineEventPrefixLaunchCount(0),
    regionSingleRequestDirectReducePipelineRunCountLaunchCount(0),
    regionSingleRequestDirectReducePipelineRunPrefixLaunchCount(0),
    regionSingleRequestDirectReducePipelineRunCompactLaunchCount(0),
    regionSingleRequestDirectReducePipelineFilterReduceLaunchCount(0),
    regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount(0),
    regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount(0),
    regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount(0),
    regionSingleRequestDirectReducePipelineDpLt1msCount(0),
    regionSingleRequestDirectReducePipelineDp1To5msCount(0),
    regionSingleRequestDirectReducePipelineDp5To10msCount(0),
    regionSingleRequestDirectReducePipelineDp10To50msCount(0),
    regionSingleRequestDirectReducePipelineDpGte50msCount(0),
    regionSingleRequestDirectReducePipelineDpMaxNanoseconds(0),
    initialDeviceResidencyRequestCount(0),
    initialProposalV2RequestCount(0),
    initialProposalDirectTopKCountClearSkips(0),
    initialProposalDirectTopKSingleStateSkips(0),
    initialHashReduceSingleRequestBaseBufferEnsureSkips(0),
    initialHashReduceSingleRequestBaseUploadSkips(0),
    initialHashReduceSingleRequestCountKernelSkips(0),
    initialProposalV3RequestCount(0),
    initialProposalV3SelectedStateCount(0),
    initialProposalV3SelectedCountClearSkips(0),
    initialProposalV3SingleStateSelectorSkips(0),
    initialProposalLogicalCandidateCount(0),
    initialProposalMaterializedCandidateCount(0),
    initialSummaryPackedBytesD2H(0),
    initialSummaryUnpackedEquivalentBytesD2H(0),
    initialSummaryPackedD2HFallbacks(0),
    initialSummaryHostCopyElidedBytes(0),
    initialSummaryHostCopyElisionCountCopyReuses(0),
    initialSummaryHostCopyElisionBaseCopyReuses(0),
    initialSummaryHostCopyElisionRunCountCopySkips(0),
    initialSummaryHostCopyElisionEventCountCopySkips(0),
    initialTrueBatchSingleRequestPrefixSkips(0),
    initialTrueBatchSingleRequestInputPackSkips(0),
    initialTrueBatchSingleRequestTargetBufferSkips(0),
    initialTrueBatchSingleRequestMatrixBufferSkips(0),
    initialTrueBatchSingleRequestDiagBufferSkips(0),
    initialTrueBatchSingleRequestMetadataBufferSkips(0),
    initialTrueBatchSingleRequestEventScoreFloorUploadSkips(0),
    initialTrueBatchSingleRequestCountCopySkips(0),
    initialTrueBatchSingleRequestRunBaseBufferEnsureSkips(0),
    initialTrueBatchSingleRequestRunBaseMaterializeSkips(0),
    initialTrueBatchSingleRequestAllCandidateCountSkips(0),
    initialTrueBatchSingleRequestAllCandidateCountBufferEnsureSkips(0),
    initialTrueBatchSingleRequestAllCandidateBaseBufferEnsureSkips(0),
    initialTrueBatchSingleRequestAllCandidateBaseUploadSkips(0),
    initialTrueBatchSingleRequestAllCandidateBasePrefixSkips(0),
    initialTrueBatchSingleRequestProposalV3StateBaseBufferEnsureSkips(0),
    initialTrueBatchSingleRequestProposalV3StateBaseUploadSkips(0),
    initialTrueBatchSingleRequestProposalV3StateCountUploadSkips(0),
    initialTrueBatchSingleRequestProposalV3SelectedBufferEnsureSkips(0),
    initialTrueBatchSingleRequestProposalV3SelectedBaseUploadSkips(0),
    initialTrueBatchSingleRequestProposalV3SelectedCompactSkips(0),
    initialTrueBatchEventBaseMaterializeSkips(0),
    initialTrueBatchEventBaseBufferEnsureSkips(0),
    initialHandoffPinnedAsyncRequested(false),
    initialHandoffPinnedAsyncActive(false),
    initialHandoffPinnedAsyncDisabledReason(SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED),
    initialHandoffPinnedAsyncSourceReadyMode(SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE),
    initialHandoffCpuPipelineRequested(false),
    initialHandoffCpuPipelineActive(false),
    initialHandoffCpuPipelineDisabledReason(
      SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED),
    initialHandoffCpuPipelineChunksApplied(0),
    initialHandoffCpuPipelineSummariesApplied(0),
    initialHandoffCpuPipelineChunksFinalized(0),
    initialHandoffCpuPipelineFinalizeCount(0),
    initialHandoffCpuPipelineOutOfOrderChunks(0),
    initialHandoffChunksTotal(0),
    initialHandoffPinnedSlots(0),
    initialHandoffPinnedBytes(0),
    initialHandoffPinnedAllocationFailures(0),
    initialHandoffPageableFallbacks(0),
    initialHandoffSyncCopies(0),
    initialHandoffAsyncCopies(0),
    initialHandoffSlotReuseWaits(0),
    initialHandoffSlotsReusedAfterMaterialize(false),
    initialSegmentedTileStateCount(0),
    initialSegmentedGroupedStateCount(0),
    initialSegmentedSingleRequestAllCandidateCountKernelSkips(0),
    initialOrderedSegmentedV3CountClearSkips(0),
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
  double initialSummaryPackSeconds;
  double initialSummaryD2HCopySeconds;
  double initialSummaryUnpackSeconds;
  double initialSummaryResultMaterializeSeconds;
  double initialHandoffAsyncD2HSeconds;
  double initialHandoffD2HWaitSeconds;
  double initialHandoffCpuApplySeconds;
  double initialHandoffCpuD2HOverlapSeconds;
  double initialHandoffDpD2HOverlapSeconds;
  double initialHandoffCriticalPathSeconds;
  double regionSingleRequestDirectReduceGpuSeconds;
  double regionSingleRequestDirectReduceDpGpuSeconds;
  double regionSingleRequestDirectReduceFilterReduceGpuSeconds;
  double regionSingleRequestDirectReduceCompactGpuSeconds;
  double regionSingleRequestDirectReduceCountD2HSeconds;
  double regionSingleRequestDirectReduceCandidateCountD2HSeconds;
  double regionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds;
  double regionSingleRequestDirectReduceFusedDpGpuSeconds;
  double regionSingleRequestDirectReduceFusedOracleDpGpuSecondsShadow;
  double regionSingleRequestDirectReduceFusedTotalGpuSeconds;
  double regionSingleRequestDirectReduceCoopDpGpuSeconds;
  double regionSingleRequestDirectReduceCoopOracleDpGpuSecondsShadow;
  double regionSingleRequestDirectReduceCoopTotalGpuSeconds;
  double regionSingleRequestDirectReducePipelineMetadataH2DSeconds;
  double regionSingleRequestDirectReducePipelineDiagGpuSeconds;
  double regionSingleRequestDirectReducePipelineEventCountGpuSeconds;
  double regionSingleRequestDirectReducePipelineEventCountD2HSeconds;
  double regionSingleRequestDirectReducePipelineEventPrefixGpuSeconds;
  double regionSingleRequestDirectReducePipelineRunCountGpuSeconds;
  double regionSingleRequestDirectReducePipelineRunCountD2HSeconds;
  double regionSingleRequestDirectReducePipelineRunPrefixGpuSeconds;
  double regionSingleRequestDirectReducePipelineRunCompactGpuSeconds;
  double regionSingleRequestDirectReducePipelineCandidatePrefixGpuSeconds;
  double regionSingleRequestDirectReducePipelineCandidateCompactGpuSeconds;
  double regionSingleRequestDirectReducePipelineCountSnapshotD2HSeconds;
  double regionSingleRequestDirectReducePipelineAccountedGpuSeconds;
  double regionSingleRequestDirectReducePipelineUnaccountedGpuSeconds;
  bool usedCuda;
  bool usedRegionTrueBatchPath;
  bool usedRegionBucketedTrueBatchPath;
  bool usedRegionPackedAggregationPath;
  bool usedRegionSingleRequestDirectReducePath;
  bool usedRegionSingleRequestDirectReduceDeferredCounts;
  bool usedInitialDirectSummaryPath;
  bool usedInitialPackedSummaryD2H;
  bool usedInitialSummaryHostCopyElision;
  bool usedInitialPinnedAsyncHandoff;
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
  uint64_t regionBucketedTrueBatchBatches;
  uint64_t regionBucketedTrueBatchRequests;
  uint64_t regionBucketedTrueBatchFusedRequests;
  uint64_t regionBucketedTrueBatchActualCells;
  uint64_t regionBucketedTrueBatchPaddedCells;
  uint64_t regionBucketedTrueBatchPaddingCells;
  uint64_t regionBucketedTrueBatchRejectedPadding;
  uint64_t regionBucketedTrueBatchShadowMismatches;
  uint64_t regionPackedAggregationRequestCount;
  uint64_t regionPackedAggregationZeroRunCandidateBufferEnsureSkips;
  uint64_t regionPackedAggregationZeroRunCandidateCountD2HSkips;
  uint64_t regionPackedAggregationNoFilterCandidateCountD2HSkips;
  uint64_t regionPackedAggregationNoFilterCandidateCountScalarH2DSkips;
  uint64_t regionPackedAggregationSliceTempOutputBufferEnsureSkips;
  uint64_t regionPackedAggregationCandidateCountClearSkips;
  uint64_t regionPackedAggregationSummaryTotalsClearSkips;
  uint64_t regionPackedAggregationInitialSummaryTotalsBufferEnsureSkips;
  uint64_t regionPackedAggregationInitialRunSummaryBufferEnsureSkips;
  uint64_t regionPackedAggregationNoFilterInitialCandidateCountBufferEnsureSkips;
  uint64_t regionPackedAggregationInitialEventBufferEnsureSkips;
  uint64_t regionPackedAggregationFinalCompactBaseBufferEnsureSkips;
  uint64_t regionPackedAggregationZeroRunTrueBatchRunCompactSkips;
  uint64_t regionPackedAggregationNoFilterReservedCopySkips;
  uint64_t regionPackedAggregationFilterReservedCopySkips;
  uint64_t regionPackedAggregationSingleCandidateFinalReduceSkips;
  uint64_t regionPackedAggregationSingleRequestFinalReduceSkips;
  uint64_t regionSingleRequestDirectReduceAttempts;
  uint64_t regionSingleRequestDirectReduceSuccesses;
  uint64_t regionSingleRequestDirectReduceFallbacks;
  uint64_t regionSingleRequestDirectReduceOverflows;
  uint64_t regionSingleRequestDirectReduceShadowMismatches;
  uint64_t regionSingleRequestDirectReduceHashCapacity;
  uint64_t regionSingleRequestDirectReduceZeroCandidateCompactBufferEnsureSkips;
  uint64_t regionSingleRequestDirectReduceCandidateCount;
  uint64_t regionSingleRequestDirectReduceEventCount;
  uint64_t regionSingleRequestDirectReduceRunSummaryCount;
  uint64_t regionSingleRequestDirectReduceAffectedStartCount;
  uint64_t regionSingleRequestDirectReduceReduceWorkItems;
  uint64_t regionSingleRequestDirectReduceFusedDpAttempts;
  uint64_t regionSingleRequestDirectReduceFusedDpEligible;
  uint64_t regionSingleRequestDirectReduceFusedDpSuccesses;
  uint64_t regionSingleRequestDirectReduceFusedDpFallbacks;
  uint64_t regionSingleRequestDirectReduceFusedDpShadowMismatches;
  uint64_t regionSingleRequestDirectReduceFusedDpRejectedByCells;
  uint64_t regionSingleRequestDirectReduceFusedDpRejectedByDiagLen;
  uint64_t regionSingleRequestDirectReduceFusedDpCells;
  uint64_t regionSingleRequestDirectReduceFusedDpRequests;
  uint64_t regionSingleRequestDirectReduceFusedDpDiagLaunchesReplaced;
  uint64_t regionSingleRequestDirectReduceCoopDpSupported;
  uint64_t regionSingleRequestDirectReduceCoopDpAttempts;
  uint64_t regionSingleRequestDirectReduceCoopDpEligible;
  uint64_t regionSingleRequestDirectReduceCoopDpSuccesses;
  uint64_t regionSingleRequestDirectReduceCoopDpFallbacks;
  uint64_t regionSingleRequestDirectReduceCoopDpShadowMismatches;
  uint64_t regionSingleRequestDirectReduceCoopDpRejectedByUnsupported;
  uint64_t regionSingleRequestDirectReduceCoopDpRejectedByCells;
  uint64_t regionSingleRequestDirectReduceCoopDpRejectedByDiagLen;
  uint64_t regionSingleRequestDirectReduceCoopDpRejectedByResidency;
  uint64_t regionSingleRequestDirectReduceCoopDpCells;
  uint64_t regionSingleRequestDirectReduceCoopDpRequests;
  uint64_t regionSingleRequestDirectReduceCoopDpDiagLaunchesReplaced;
  uint64_t regionSingleRequestDirectReducePipelineRequestCount;
  uint64_t regionSingleRequestDirectReducePipelineRowCountTotal;
  uint64_t regionSingleRequestDirectReducePipelineRowCountMax;
  uint64_t regionSingleRequestDirectReducePipelineColCountTotal;
  uint64_t regionSingleRequestDirectReducePipelineColCountMax;
  uint64_t regionSingleRequestDirectReducePipelineCellCountTotal;
  uint64_t regionSingleRequestDirectReducePipelineCellCountMax;
  uint64_t regionSingleRequestDirectReducePipelineDiagCountTotal;
  uint64_t regionSingleRequestDirectReducePipelineDiagCountMax;
  uint64_t regionSingleRequestDirectReducePipelineFilterStartCountTotal;
  uint64_t regionSingleRequestDirectReducePipelineFilterStartCountMax;
  uint64_t regionSingleRequestDirectReducePipelineDiagLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineEventCountLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineEventPrefixLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineRunCountLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineRunPrefixLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineRunCompactLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineFilterReduceLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount;
  uint64_t regionSingleRequestDirectReducePipelineDpLt1msCount;
  uint64_t regionSingleRequestDirectReducePipelineDp1To5msCount;
  uint64_t regionSingleRequestDirectReducePipelineDp5To10msCount;
  uint64_t regionSingleRequestDirectReducePipelineDp10To50msCount;
  uint64_t regionSingleRequestDirectReducePipelineDpGte50msCount;
  uint64_t regionSingleRequestDirectReducePipelineDpMaxNanoseconds;
  uint64_t initialDeviceResidencyRequestCount;
  uint64_t initialProposalV2RequestCount;
  uint64_t initialProposalDirectTopKCountClearSkips;
  uint64_t initialProposalDirectTopKSingleStateSkips;
  uint64_t initialHashReduceSingleRequestBaseBufferEnsureSkips;
  uint64_t initialHashReduceSingleRequestBaseUploadSkips;
  uint64_t initialHashReduceSingleRequestCountKernelSkips;
  uint64_t initialProposalV3RequestCount;
  uint64_t initialProposalV3SelectedStateCount;
  uint64_t initialProposalV3SelectedCountClearSkips;
  uint64_t initialProposalV3SingleStateSelectorSkips;
  uint64_t initialProposalLogicalCandidateCount;
  uint64_t initialProposalMaterializedCandidateCount;
  uint64_t initialSummaryPackedBytesD2H;
  uint64_t initialSummaryUnpackedEquivalentBytesD2H;
  uint64_t initialSummaryPackedD2HFallbacks;
  uint64_t initialSummaryHostCopyElidedBytes;
  uint64_t initialSummaryHostCopyElisionCountCopyReuses;
  uint64_t initialSummaryHostCopyElisionBaseCopyReuses;
  uint64_t initialSummaryHostCopyElisionRunCountCopySkips;
  uint64_t initialSummaryHostCopyElisionEventCountCopySkips;
  uint64_t initialTrueBatchSingleRequestPrefixSkips;
  uint64_t initialTrueBatchSingleRequestInputPackSkips;
  uint64_t initialTrueBatchSingleRequestTargetBufferSkips;
  uint64_t initialTrueBatchSingleRequestMatrixBufferSkips;
  uint64_t initialTrueBatchSingleRequestDiagBufferSkips;
  uint64_t initialTrueBatchSingleRequestMetadataBufferSkips;
  uint64_t initialTrueBatchSingleRequestEventScoreFloorUploadSkips;
  uint64_t initialTrueBatchSingleRequestCountCopySkips;
  uint64_t initialTrueBatchSingleRequestRunBaseBufferEnsureSkips;
  uint64_t initialTrueBatchSingleRequestRunBaseMaterializeSkips;
  uint64_t initialTrueBatchSingleRequestAllCandidateCountSkips;
  uint64_t initialTrueBatchSingleRequestAllCandidateCountBufferEnsureSkips;
  uint64_t initialTrueBatchSingleRequestAllCandidateBaseBufferEnsureSkips;
  uint64_t initialTrueBatchSingleRequestAllCandidateBaseUploadSkips;
  uint64_t initialTrueBatchSingleRequestAllCandidateBasePrefixSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3StateBaseBufferEnsureSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3StateBaseUploadSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3StateCountUploadSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3SelectedBufferEnsureSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3SelectedBaseUploadSkips;
  uint64_t initialTrueBatchSingleRequestProposalV3SelectedCompactSkips;
  uint64_t initialTrueBatchEventBaseMaterializeSkips;
  uint64_t initialTrueBatchEventBaseBufferEnsureSkips;
  bool initialHandoffPinnedAsyncRequested;
  bool initialHandoffPinnedAsyncActive;
  SimScanCudaInitialPinnedAsyncDisabledReason initialHandoffPinnedAsyncDisabledReason;
  SimScanCudaInitialPinnedAsyncSourceReadyMode initialHandoffPinnedAsyncSourceReadyMode;
  bool initialHandoffCpuPipelineRequested;
  bool initialHandoffCpuPipelineActive;
  SimScanCudaInitialPinnedAsyncCpuPipelineDisabledReason initialHandoffCpuPipelineDisabledReason;
  uint64_t initialHandoffCpuPipelineChunksApplied;
  uint64_t initialHandoffCpuPipelineSummariesApplied;
  uint64_t initialHandoffCpuPipelineChunksFinalized;
  uint64_t initialHandoffCpuPipelineFinalizeCount;
  uint64_t initialHandoffCpuPipelineOutOfOrderChunks;
  uint64_t initialHandoffChunksTotal;
  uint64_t initialHandoffPinnedSlots;
  uint64_t initialHandoffPinnedBytes;
  uint64_t initialHandoffPinnedAllocationFailures;
  uint64_t initialHandoffPageableFallbacks;
  uint64_t initialHandoffSyncCopies;
  uint64_t initialHandoffAsyncCopies;
  uint64_t initialHandoffSlotReuseWaits;
  bool initialHandoffSlotsReusedAfterMaterialize;
  uint64_t initialSegmentedTileStateCount;
  uint64_t initialSegmentedGroupedStateCount;
  uint64_t initialSegmentedSingleRequestAllCandidateCountKernelSkips;
  uint64_t initialOrderedSegmentedV3CountClearSkips;
  uint64_t taskCount;
  uint64_t launchCount;
  SimScanCudaInitialReduceReplayStats initialReduceReplayStats;
};

struct SimScanCudaRegionBucketedTrueBatchShape
{
  SimScanCudaRegionBucketedTrueBatchShape():rowCount(0),colCount(0) {}
  SimScanCudaRegionBucketedTrueBatchShape(int rowCountIn,int colCountIn):
    rowCount(rowCountIn),
    colCount(colCountIn)
  {}

  int rowCount;
  int colCount;
};

struct SimScanCudaRegionBucketedTrueBatchGroup
{
  SimScanCudaRegionBucketedTrueBatchGroup():
    requestBegin(0),
    requestCount(0),
    bucketRows(0),
    bucketCols(0),
    actualCells(0),
    paddedCells(0),
    bucketed(false)
  {}

  size_t requestBegin;
  size_t requestCount;
  int bucketRows;
  int bucketCols;
  uint64_t actualCells;
  uint64_t paddedCells;
  bool bucketed;
};

struct SimScanCudaRegionBucketedTrueBatchStats
{
  SimScanCudaRegionBucketedTrueBatchStats():
    batches(0),
    requests(0),
    fusedRequests(0),
    actualCells(0),
    paddedCells(0),
    paddingCells(0),
    rejectedPadding(0),
    shadowMismatches(0)
  {}

  uint64_t batches;
  uint64_t requests;
  uint64_t fusedRequests;
  uint64_t actualCells;
  uint64_t paddedCells;
  uint64_t paddingCells;
  uint64_t rejectedPadding;
  uint64_t shadowMismatches;
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

bool sim_scan_cuda_plan_region_bucketed_true_batches_for_test(
  const std::vector<SimScanCudaRegionBucketedTrueBatchShape> &shapes,
  std::vector<SimScanCudaRegionBucketedTrueBatchGroup> *groups,
  SimScanCudaRegionBucketedTrueBatchStats *stats,
  std::string *errorOut);

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
                                                                              bool *outUsedFrontierCache = NULL,
                                                                              uint64_t *outSingleStateDirectD2HSkips = NULL);

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
                                                      SimCudaPersistentSafeStoreHandle *outPersistentSafeStoreHandle = NULL,
                                                      SimScanCudaInitialSummaryChunkConsumer initialSummaryChunkConsumer =
                                                        SimScanCudaInitialSummaryChunkConsumer());

bool sim_scan_cuda_enumerate_initial_events_row_major_true_batch(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                 std::vector<SimScanCudaInitialBatchResult> *outResults,
                                                                 SimScanCudaBatchResult *batchResult,
                                                                 std::string *errorOut);

bool sim_scan_cuda_reduce_initial_run_summaries_for_test(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                                         std::vector<SimScanCudaCandidateState> *outCandidateStates,
                                                         int *outRunningMin,
                                                         SimScanCudaInitialReduceReplayStats *outReplayStats,
                                                         std::string *errorOut);

bool sim_scan_cuda_reduce_initial_ordered_segmented_v3_for_test(
  const std::vector<SimScanCudaInitialRunSummary> &summaries,
  const std::vector<int> &runBases,
  const std::vector<int> &runTotals,
  std::vector<SimScanCudaInitialBatchResult> *outResults,
  SimScanCudaBatchResult *batchResult,
  std::string *errorOut);

bool sim_scan_cuda_reduce_frontier_epoch_shadow_for_test(
  const std::vector<SimScanCudaInitialRunSummary> &summaries,
  const std::vector<uint64_t> &summaryEpochIds,
  const std::vector<uint64_t> &liveEpochIds,
  std::vector<SimScanCudaCandidateState> *outCandidateStates,
  int *outRunningMin,
  std::string *errorOut);

bool sim_scan_cuda_apply_frontier_chunk_transducer_shadow_for_test(
  const std::vector<SimScanCudaCandidateState> &incomingStates,
  int incomingRunningMin,
  const std::vector<SimScanCudaInitialRunSummary> &chunkSummaries,
  std::vector<SimScanCudaCandidateState> *outCandidateStates,
  int *outRunningMin,
  SimScanCudaFrontierDigest *outDigest,
  SimScanCudaFrontierTransducerShadowStats *outStats,
  std::string *errorOut);

bool sim_scan_cuda_reduce_frontier_chunk_transducer_segmented_shadow_for_test(
  const std::vector<SimScanCudaInitialRunSummary> &summaries,
  const std::vector<int> &runBases,
  const std::vector<int> &runTotals,
  int chunkSize,
  std::vector<SimScanCudaFrontierTransducerSegmentedShadowResult> *outResults,
  double *outShadowSeconds,
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
