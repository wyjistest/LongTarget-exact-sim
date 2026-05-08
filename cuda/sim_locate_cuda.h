#ifndef LONGTARGET_SIM_LOCATE_CUDA_H
#define LONGTARGET_SIM_LOCATE_CUDA_H

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "sim_scan_cuda.h"

enum SimLocateCudaMode
{
  SIM_LOCATE_CUDA_MODE_EXACT = 0,
  SIM_LOCATE_CUDA_MODE_FAST = 1,
  SIM_LOCATE_CUDA_MODE_SAFE_WORKSET = 2
};

enum SimLocateExactPrecheckMode
{
  SIM_LOCATE_EXACT_PRECHECK_OFF = 0,
  SIM_LOCATE_EXACT_PRECHECK_SHADOW = 1,
  SIM_LOCATE_EXACT_PRECHECK_ON = 2
};

inline SimLocateCudaMode parseSimLocateCudaMode(const char *env)
{
  if(env == NULL || env[0] == '\0')
  {
    return SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
  }
  if(std::strcmp(env, "fast") == 0)
  {
    return SIM_LOCATE_CUDA_MODE_FAST;
  }
  if(std::strcmp(env, "safe_workset") == 0)
  {
    return SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
  }
  return SIM_LOCATE_CUDA_MODE_EXACT;
}

inline SimLocateExactPrecheckMode parseSimLocateExactPrecheckMode(const char *env)
{
  if(env == NULL || env[0] == '\0')
  {
    return SIM_LOCATE_EXACT_PRECHECK_OFF;
  }
  if(std::strcmp(env, "shadow") == 0)
  {
    return SIM_LOCATE_EXACT_PRECHECK_SHADOW;
  }
  if(std::strcmp(env, "on") == 0)
  {
    return SIM_LOCATE_EXACT_PRECHECK_ON;
  }
  return SIM_LOCATE_EXACT_PRECHECK_OFF;
}

struct SimLocateResult
{
  SimLocateResult():
    hasUpdateRegion(false),
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0),
    locateCellCount(0),
    baseCellCount(0),
    expansionCellCount(0),
    stopByNoCross(false),
    stopByBoundary(false),
    usedCuda(false),
    gpuSeconds(0.0) {}

  bool hasUpdateRegion;
  long rowStart;
  long rowEnd;
  long colStart;
  long colEnd;
  uint64_t locateCellCount;
  uint64_t baseCellCount;
  uint64_t expansionCellCount;
  bool stopByNoCross;
  bool stopByBoundary;
  bool usedCuda;
  double gpuSeconds;
};

struct SimLocatePrecheckResult
{
  SimLocatePrecheckResult():
    attempted(false),
    confirmedNoUpdate(false),
    needsFullLocate(true),
    minRowBound(0),
    minColBound(0),
    baseCellCount(0),
    expansionCellCount(0),
    scannedCellCount(0),
    stopByNoCross(false),
    stopByBoundary(false),
    usedCuda(false),
    gpuSeconds(0.0) {}

  bool attempted;
  bool confirmedNoUpdate;
  bool needsFullLocate;
  long minRowBound;
  long minColBound;
  uint64_t baseCellCount;
  uint64_t expansionCellCount;
  uint64_t scannedCellCount;
  bool stopByNoCross;
  bool stopByBoundary;
  bool usedCuda;
  double gpuSeconds;
};

struct SimLocateFastBounds
{
  SimLocateFastBounds():
    minRowStart(1),
    minColStart(1),
    expandedByCandidates(false) {}

  long minRowStart;
  long minColStart;
  bool expandedByCandidates;
};

inline bool simLocateFastCandidateIntersectsRegion(const SimScanCudaCandidateState &candidate,
                                                   long rowStart,
                                                   long rowEnd,
                                                   long colStart,
                                                   long colEnd)
{
  return candidate.startI <= rowEnd &&
         candidate.startJ <= colEnd &&
         candidate.bot >= rowStart - 1 &&
         candidate.right >= colStart - 1;
}

inline SimLocateFastBounds computeSimLocateFastBounds(int queryLength,
                                                      int targetLength,
                                                      long rowStart,
                                                      long rowEnd,
                                                      long colStart,
                                                      long colEnd,
                                                      const SimScanCudaCandidateState *candidates,
                                                      int candidateCount,
                                                      long pad)
{
  SimLocateFastBounds bounds;
  if(queryLength > 0)
  {
    bounds.minRowStart = std::max(1L, std::min<long>(rowStart, queryLength));
  }
  if(targetLength > 0)
  {
    bounds.minColStart = std::max(1L, std::min<long>(colStart, targetLength));
  }
  if(candidates != NULL && candidateCount > 0)
  {
    bool changed = false;
    do
    {
      changed = false;
      for(int i = 0; i < candidateCount; ++i)
      {
        const SimScanCudaCandidateState &candidate = candidates[i];
        if(!simLocateFastCandidateIntersectsRegion(candidate,bounds.minRowStart,rowEnd,bounds.minColStart,colEnd))
        {
          continue;
        }
        const long nextRowStart = std::min<long>(bounds.minRowStart, candidate.startI);
        const long nextColStart = std::min<long>(bounds.minColStart, candidate.startJ);
        if(nextRowStart != bounds.minRowStart || nextColStart != bounds.minColStart)
        {
          bounds.minRowStart = std::max(1L, nextRowStart);
          bounds.minColStart = std::max(1L, nextColStart);
          bounds.expandedByCandidates = true;
          changed = true;
        }
      }
    } while(changed);
  }
  if(pad > 0)
  {
    bounds.minRowStart = std::max(1L, bounds.minRowStart - pad);
    bounds.minColStart = std::max(1L, bounds.minColStart - pad);
  }
  return bounds;
}

inline SimLocateFastBounds computeSimLocateExactPrecheckBounds(int queryLength,
                                                               int targetLength,
                                                               long rowStart,
                                                               long rowEnd,
                                                               long colStart,
                                                               long colEnd,
                                                               const SimScanCudaCandidateState *candidates,
                                                               int candidateCount)
{
  return computeSimLocateFastBounds(queryLength,
                                    targetLength,
                                    rowStart,
                                    rowEnd,
                                    colStart,
                                    colEnd,
                                    candidates,
                                    candidateCount,
                                    0);
}

inline SimLocateResult computeSimLocateFastResult(int queryLength,
                                                  int targetLength,
                                                  long rowStart,
                                                  long rowEnd,
                                                  long colStart,
                                                  long colEnd,
                                                  const SimScanCudaCandidateState *candidates,
                                                  int candidateCount,
                                                  long pad)
{
  SimLocateResult result;
  if(queryLength <= 0 ||
     targetLength <= 0 ||
     rowStart < 1 ||
     colStart < 1 ||
     rowEnd < rowStart ||
     colEnd < colStart)
  {
    return result;
  }

  const SimLocateFastBounds bounds =
    computeSimLocateFastBounds(queryLength,
                               targetLength,
                               rowStart,
                               rowEnd,
                               colStart,
                               colEnd,
                               candidates,
                               candidateCount,
                               pad);
  const long baseRowStart = std::max(1L, rowStart - std::max(0L, pad));
  const long baseColStart = std::max(1L, colStart - std::max(0L, pad));
  const long boundedRowStart = std::max(1L, std::min<long>(bounds.minRowStart, queryLength));
  const long boundedColStart = std::max(1L, std::min<long>(bounds.minColStart, targetLength));
  const uint64_t baseArea =
    static_cast<uint64_t>(std::max(0L, rowEnd - baseRowStart + 1)) *
    static_cast<uint64_t>(std::max(0L, colEnd - baseColStart + 1));
  const uint64_t closureArea =
    static_cast<uint64_t>(std::max(0L, rowEnd - boundedRowStart + 1)) *
    static_cast<uint64_t>(std::max(0L, colEnd - boundedColStart + 1));
  const bool useCandidateExpansion =
    !bounds.expandedByCandidates ||
    baseArea == 0 ||
    closureArea <= baseArea * static_cast<uint64_t>(4);
  result.hasUpdateRegion = true;
  result.rowStart = useCandidateExpansion ? boundedRowStart : baseRowStart;
  result.rowEnd = std::max(result.rowStart, std::min<long>(rowEnd, queryLength));
  result.colStart = useCandidateExpansion ? boundedColStart : baseColStart;
  result.colEnd = std::max(result.colStart, std::min<long>(colEnd, targetLength));
  return result;
}

struct SimLocateCudaRequest
{
  SimLocateCudaRequest():
    A(NULL),
    B(NULL),
    queryLength(0),
    targetLength(0),
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0),
    runningMin(0),
    gapOpen(0),
    gapExtend(0),
    scoreMatrix(NULL),
    blockedWords(NULL),
    blockedWordStride(0),
    candidates(NULL),
    candidateCount(0),
    minRowBound(1),
    minColBound(1)
  {
  }

  const char *A;
  const char *B;
  int queryLength;
  int targetLength;
  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
  int runningMin;
  int gapOpen;
  int gapExtend;
  const int (*scoreMatrix)[128];
  const uint64_t *blockedWords;
  int blockedWordStride;
  const SimScanCudaCandidateState *candidates;
  int candidateCount;
  int minRowBound;
  int minColBound;
};

struct SimLocateCudaBatchResult
{
  SimLocateCudaBatchResult():
    gpuSeconds(0.0),
    usedCuda(false),
    taskCount(0),
    launchCount(0),
    usedSharedInputBatchPath(false),
    singleRequestBatchSkips(0),
    inputH2DCopies(0),
    inputH2DCacheHits(0),
    scoreMatrixH2DCopies(0),
    scoreMatrixH2DCacheHits(0),
    blockedWordsH2DCopies(0),
    blockedWordsH2DCacheHits(0),
    candidateH2DCopies(0),
    candidateH2DCacheHits(0),
    requestH2DCopies(0),
    requestH2DCacheHits(0)
  {
  }

  double gpuSeconds;
  bool usedCuda;
  uint64_t taskCount;
  uint64_t launchCount;
  bool usedSharedInputBatchPath;
  uint64_t singleRequestBatchSkips;
  uint64_t inputH2DCopies;
  uint64_t inputH2DCacheHits;
  uint64_t scoreMatrixH2DCopies;
  uint64_t scoreMatrixH2DCacheHits;
  uint64_t blockedWordsH2DCopies;
  uint64_t blockedWordsH2DCacheHits;
  uint64_t candidateH2DCopies;
  uint64_t candidateH2DCacheHits;
  uint64_t requestH2DCopies;
  uint64_t requestH2DCacheHits;
};

bool sim_locate_cuda_is_built();
bool sim_locate_cuda_init(int device,std::string *errorOut);
bool sim_locate_cuda_locate_region(const SimLocateCudaRequest &request,
                                   SimLocateResult *outResult,
                                   std::string *errorOut);
bool sim_locate_cuda_locate_region_batch(const std::vector<SimLocateCudaRequest> &requests,
                                         std::vector<SimLocateResult> *outResults,
                                         SimLocateCudaBatchResult *batchResult,
                                         std::string *errorOut);

#endif
