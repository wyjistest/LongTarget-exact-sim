#include "sim_scan_cuda.h"
#include "sim_cuda_runtime.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <memory>
#include <mutex>

#include <cuda_runtime.h>
#include <thrust/functional.h>
#include <thrust/device_ptr.h>
#include <thrust/execution_policy.h>
#include <thrust/reduce.h>
#include <thrust/scan.h>
#include <thrust/sort.h>
#include <thrust/system_error.h>

using namespace std;

namespace
{

const int sim_scan_cuda_max_candidates = 50;
const int sim_scan_initial_reduce_threads = 32;
const int sim_scan_initial_reduce_chunk_size_default = 256;
const int sim_scan_initial_reduce_chunk_size_min = 32;
const int sim_scan_initial_reduce_chunk_size_max = 4096;
const int sim_scan_initial_reduce_chunk_stats_count = 3;
const int sim_scan_ordered_maintenance_digest_stats_count = 14;
const int sim_scan_ordered_maintenance_digest_replacement_sequence_hash_index = 0;
const int sim_scan_ordered_maintenance_digest_running_min_sequence_hash_index = 1;
const int sim_scan_ordered_maintenance_digest_running_min_slot_sequence_hash_index = 2;
const int sim_scan_ordered_maintenance_digest_floor_change_sequence_hash_index = 3;
const int sim_scan_ordered_maintenance_digest_candidate_index_visibility_hash_index = 4;
const int sim_scan_ordered_maintenance_digest_candidate_replacement_count_index = 5;
const int sim_scan_ordered_maintenance_digest_running_min_update_count_index = 6;
const int sim_scan_ordered_maintenance_digest_running_min_slot_update_count_index = 7;
const int sim_scan_ordered_maintenance_digest_floor_change_count_index = 8;
const int sim_scan_ordered_maintenance_digest_candidate_index_existing_hit_count_index = 9;
const int sim_scan_ordered_maintenance_digest_candidate_index_miss_count_index = 10;
const int sim_scan_ordered_maintenance_digest_candidate_index_insert_count_index = 11;
const int sim_scan_ordered_maintenance_digest_candidate_index_erase_count_index = 12;
const int sim_scan_ordered_maintenance_digest_candidate_index_visibility_check_count_index = 13;
const int sim_scan_candidate_hash_capacity = 128;
const int sim_scan_candidate_hash_empty = -1;
const int sim_scan_candidate_hash_tombstone = -2;
const int sim_scan_candidate_hash_rebuild_tombstones = sim_scan_candidate_hash_capacity / 4;
const int sim_scan_online_hash_flag_empty = 0;
const int sim_scan_online_hash_flag_initializing = 1;
const int sim_scan_online_hash_flag_ready = 2;
const int sim_scan_online_hash_flag_locked = 3;

int sim_scan_cuda_initial_reduce_chunk_size_runtime()
{
  static const int chunkSize = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_CHUNK_SIZE");
    if(env == NULL || env[0] == '\0')
    {
      return sim_scan_initial_reduce_chunk_size_default;
    }
    char *end = NULL;
    long parsed = strtol(env,&end,10);
    if(end == env)
    {
      return sim_scan_initial_reduce_chunk_size_default;
    }
    if(parsed < sim_scan_initial_reduce_chunk_size_min)
    {
      return sim_scan_initial_reduce_chunk_size_min;
    }
    if(parsed > sim_scan_initial_reduce_chunk_size_max)
    {
      return sim_scan_initial_reduce_chunk_size_max;
    }
    return static_cast<int>(parsed);
  }();
  return chunkSize;
}

bool sim_scan_cuda_initial_proposal_streaming_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_STREAMING");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_initial_proposal_online_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_initial_proposal_v2_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_initial_proposal_v3_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_initial_hash_reduce_legacy_env_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_env_flag_enabled(const char *name)
{
  const char *env = getenv(name);
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

bool sim_scan_cuda_mainline_residency_runtime()
{
  const char *locateModeEnv = getenv("LONGTARGET_SIM_CUDA_LOCATE_MODE");
  const bool safeWorksetMode =
    locateModeEnv == NULL ||
    locateModeEnv[0] == '\0' ||
    strcmp(locateModeEnv,"safe_workset") == 0;
  return sim_scan_cuda_env_flag_enabled("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE") &&
         sim_scan_cuda_env_flag_enabled("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP") &&
         sim_scan_cuda_env_flag_enabled("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP") &&
         sim_scan_cuda_env_flag_enabled("LONGTARGET_ENABLE_SIM_CUDA_LOCATE") &&
         !sim_scan_cuda_env_flag_enabled("LONGTARGET_SIM_CUDA_LOCATE_FAST_SHADOW") &&
         safeWorksetMode;
}

enum SimScanCudaInitialReduceBackend
{
  SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_LEGACY = 0,
  SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_HASH = 1,
  SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_SEGMENTED = 2,
  SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_ORDERED_SEGMENTED_V3 = 3,
};

SimScanCudaInitialReduceBackend sim_scan_cuda_initial_reduce_backend_runtime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
  if(env != NULL && env[0] != '\0')
  {
    if(strcmp(env,"hash") == 0)
    {
      return SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_HASH;
    }
    if(strcmp(env,"segmented") == 0)
    {
      return SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_SEGMENTED;
    }
    if(strcmp(env,"ordered_segmented_v3") == 0 ||
       strcmp(env,"ordered-segmented-v3") == 0)
    {
      return SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_ORDERED_SEGMENTED_V3;
    }
    return SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_LEGACY;
  }
  if(sim_scan_cuda_mainline_residency_runtime())
  {
    return SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_ORDERED_SEGMENTED_V3;
  }
  return sim_scan_cuda_initial_hash_reduce_legacy_env_runtime() ?
         SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_HASH :
         SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_LEGACY;
}

bool sim_scan_cuda_initial_hash_reduce_runtime()
{
  return sim_scan_cuda_initial_reduce_backend_runtime() ==
         SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_HASH;
}

bool sim_scan_cuda_initial_segmented_reduce_runtime()
{
  const SimScanCudaInitialReduceBackend backend =
    sim_scan_cuda_initial_reduce_backend_runtime();
  return backend == SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_SEGMENTED ||
         backend == SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_ORDERED_SEGMENTED_V3;
}

size_t sim_scan_cuda_next_power_of_two(size_t value)
{
  size_t capacity = 1;
  while(capacity < value && capacity < (numeric_limits<size_t>::max() >> 1))
  {
    capacity <<= 1;
  }
  return capacity;
}

size_t sim_scan_cuda_initial_hash_reduce_capacity_runtime(int summaryCount)
{
  const size_t minCapacity = 8;
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY");
  if(env != NULL && env[0] != '\0')
  {
    char *end = NULL;
    unsigned long long parsed = strtoull(env,&end,10);
    if(end != env && parsed > 0)
    {
      return max(minCapacity,
                 sim_scan_cuda_next_power_of_two(static_cast<size_t>(parsed)));
    }
  }

  const size_t targetCapacity =
    max(minCapacity,
        static_cast<size_t>(max(summaryCount,0)) / static_cast<size_t>(4));
  return sim_scan_cuda_next_power_of_two(targetCapacity);
}

size_t sim_scan_cuda_initial_proposal_hash_capacity_runtime(int queryLength,int targetLength)
{
  const size_t maxAutoCapacity = static_cast<size_t>(1) << 24;
  const size_t minCapacity = 8;
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY");
  if(env != NULL && env[0] != '\0')
  {
    char *end = NULL;
    unsigned long long parsed = strtoull(env,&end,10);
    if(end != env && parsed >= static_cast<unsigned long long>(minCapacity))
    {
      size_t capacity = minCapacity;
      const size_t requested = static_cast<size_t>(parsed);
      while(capacity < requested && capacity < (numeric_limits<size_t>::max() >> 1))
      {
        capacity <<= 1;
      }
      return capacity;
    }
  }

  const size_t maxCells =
    static_cast<size_t>(max(queryLength,0)) * static_cast<size_t>(max(targetLength,0));
  size_t capacity = minCapacity;
  const size_t targetCapacity = min(maxAutoCapacity, max(minCapacity, maxCells / 4));
  while(capacity < targetCapacity && capacity < (numeric_limits<size_t>::max() >> 1))
  {
    capacity <<= 1;
  }
  return capacity;
}

const char *cuda_error_string(cudaError_t status)
{
  if(status == cudaSuccess)
  {
    return "success";
  }
  const char *msg = cudaGetErrorString(status);
  if(msg != NULL)
  {
    return msg;
  }
  return "unknown CUDA error";
}

void clear_sim_scan_cuda_error(string *errorOut)
{
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
}

static bool sim_scan_cuda_begin_aux_timing(struct SimScanCudaContext *context,
                                           string *errorOut);
static bool sim_scan_cuda_end_aux_timing(struct SimScanCudaContext *context,
                                         double *outSeconds,
                                         string *errorOut);

template <typename T>
static bool ensure_sim_scan_cuda_buffer(T **buffer,
                                        size_t *capacity,
                                        size_t needed,
                                        string *errorOut);

__constant__ int sim_score_matrix[128 * 128];

__device__ __forceinline__ uint64_t sim_pack_coord(uint32_t i,uint32_t j)
{
  return (static_cast<uint64_t>(i) << 32) | static_cast<uint64_t>(j);
}

__device__ __forceinline__ uint64_t sim_scan_digest_fnv_offset()
{
  return 1469598103934665603ULL;
}

__device__ __forceinline__ uint64_t sim_scan_digest_mix_u64(uint64_t hash,uint64_t value)
{
  hash ^= value;
  hash *= 1099511628211ULL;
  return hash;
}

__device__ __forceinline__ uint64_t sim_scan_digest_mix_i64(uint64_t hash,int64_t value)
{
  return sim_scan_digest_mix_u64(hash,static_cast<uint64_t>(value));
}

__device__ __forceinline__ void sim_order_state(int &score1,uint64_t &coord1,int score2,uint64_t coord2)
{
  if(score1 < score2 || (score1 == score2 && coord1 < coord2))
  {
    score1 = score2;
    coord1 = coord2;
  }
}

struct SimScanCudaContext
{
  SimScanCudaContext():
    initialized(false),
    device(0),
    capacityQuery(0),
    capacityTarget(0),
    leadingDim(0),
    ADevice(NULL),
    BDevice(NULL),
    HScoreDevice(NULL),
    HCoordDevice(NULL),
    diagH0(NULL),
    diagH1(NULL),
    diagH2(NULL),
    diagD0(NULL),
    diagD1(NULL),
    diagD2(NULL),
    diagF0(NULL),
    diagF1(NULL),
    diagF2(NULL),
    diagHc0(NULL),
    diagHc1(NULL),
    diagHc2(NULL),
    diagDc0(NULL),
    diagDc1(NULL),
    diagDc2(NULL),
    diagFc0(NULL),
    diagFc1(NULL),
    diagFc2(NULL),
    rowCountsDevice(NULL),
    rowOffsetsDevice(NULL),
    runOffsetsDevice(NULL),
    blockedWordsDevice(NULL),
    blockedWordsCapacityWords(0),
    batchBDevice(NULL),
    batchBCapacityBytes(0),
    batchHScoreDevice(NULL),
    batchHScoreCapacityCells(0),
    batchHCoordDevice(NULL),
    batchHCoordCapacityCells(0),
    batchDiagH0(NULL),
    batchDiagH1(NULL),
    batchDiagH2(NULL),
    batchDiagD1(NULL),
    batchDiagD2(NULL),
    batchDiagF1(NULL),
    batchDiagF2(NULL),
    batchDiagHc0(NULL),
    batchDiagHc1(NULL),
    batchDiagHc2(NULL),
    batchDiagDc1(NULL),
    batchDiagDc2(NULL),
    batchDiagFc1(NULL),
    batchDiagFc2(NULL),
    batchDiagCapacity(0),
    batchRowCountsDevice(NULL),
    batchRowCountsCapacity(0),
    batchRowOffsetsDevice(NULL),
    batchRowOffsetsCapacity(0),
    batchRunOffsetsDevice(NULL),
    batchRunOffsetsCapacity(0),
    batchEventTotalsDevice(NULL),
    batchEventTotalsCapacity(0),
    batchRunTotalsDevice(NULL),
    batchRunTotalsCapacity(0),
    batchEventScoreFloorsDevice(NULL),
    batchEventScoreFloorsCapacity(0),
    batchEventBasesDevice(NULL),
    batchEventBasesCapacity(0),
    batchRunBasesDevice(NULL),
    batchRunBasesCapacity(0),
    batchCandidateStatesDevice(NULL),
    batchCandidateStatesCapacity(0),
    batchCandidateCountsDevice(NULL),
    batchCandidateCountsCapacity(0),
    batchRunningMinsDevice(NULL),
    batchRunningMinsCapacity(0),
    batchAllCandidateCountsDevice(NULL),
    batchAllCandidateCountsCapacity(0),
    batchHashKeysDevice(NULL),
    batchHashKeysCapacity(0),
    batchHashFlagsDevice(NULL),
    batchHashFlagsCapacity(0),
    batchHashStatesDevice(NULL),
    batchHashStatesCapacity(0),
    proposalRowStatesDevice(NULL),
    proposalRowStatesCapacity(0),
    proposalOnlineHashKeysDevice(NULL),
    proposalOnlineHashKeysCapacity(0),
    proposalOnlineHashFlagsDevice(NULL),
    proposalOnlineHashFlagsCapacity(0),
    proposalOnlineHashStatesDevice(NULL),
    proposalOnlineHashStatesCapacity(0),
    eventsDevice(NULL),
    eventsCapacity(0),
    initialRunSummariesDevice(NULL),
    initialRunSummariesCapacity(0),
    summaryKeysDevice(NULL),
    summaryKeysCapacity(0),
    reducedKeysDevice(NULL),
    reducedKeysCapacity(0),
    batchSummaryKeysDevice(NULL),
    batchSummaryKeysCapacity(0),
    batchReducedKeysDevice(NULL),
    batchReducedKeysCapacity(0),
    reduceStatesDevice(NULL),
    reduceStatesCapacity(0),
    reducedStatesDevice(NULL),
    reducedStatesCapacity(0),
    outputCandidateStatesDevice(NULL),
    outputCandidateStatesCapacity(0),
    initialReduceReplayStatsDevice(NULL),
    initialReduceReplayStatsCapacity(0),
    summaryRowMinColsDevice(NULL),
    summaryRowMinColsCapacity(0),
    summaryRowMaxColsDevice(NULL),
    summaryRowMaxColsCapacity(0),
    rowIntervalOffsetsDevice(NULL),
    rowIntervalOffsetsCapacity(0),
    rowIntervalsDevice(NULL),
    rowIntervalsCapacity(0),
    filterStartCoordsDevice(NULL),
    filterStartCoordsCapacity(0),
    candidateStatesDevice(NULL),
    candidateCountDevice(NULL),
    filteredCandidateCountDevice(NULL),
    runningMinDevice(NULL),
    eventCountDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL),
    auxStartEvent(NULL),
    auxStopEvent(NULL),
    batchOutputCursorsDevice(NULL),
    batchOutputCursorsCapacity(0)
  {
  }

  bool initialized;
  int device;
  int capacityQuery;
  int capacityTarget;
  int leadingDim;

  char *ADevice;
  char *BDevice;

  int *HScoreDevice;
  uint64_t *HCoordDevice;

  int *diagH0;
  int *diagH1;
  int *diagH2;
  int *diagD0;
  int *diagD1;
  int *diagD2;
  int *diagF0;
  int *diagF1;
  int *diagF2;

  uint64_t *diagHc0;
  uint64_t *diagHc1;
  uint64_t *diagHc2;
  uint64_t *diagDc0;
  uint64_t *diagDc1;
  uint64_t *diagDc2;
  uint64_t *diagFc0;
  uint64_t *diagFc1;
  uint64_t *diagFc2;

  int *rowCountsDevice;
  int *rowOffsetsDevice;
  int *runOffsetsDevice;

  uint64_t *blockedWordsDevice;
  size_t blockedWordsCapacityWords;

  char *batchBDevice;
  size_t batchBCapacityBytes;
  int *batchHScoreDevice;
  size_t batchHScoreCapacityCells;
  uint64_t *batchHCoordDevice;
  size_t batchHCoordCapacityCells;
  int *batchDiagH0;
  int *batchDiagH1;
  int *batchDiagH2;
  int *batchDiagD1;
  int *batchDiagD2;
  int *batchDiagF1;
  int *batchDiagF2;
  uint64_t *batchDiagHc0;
  uint64_t *batchDiagHc1;
  uint64_t *batchDiagHc2;
  uint64_t *batchDiagDc1;
  uint64_t *batchDiagDc2;
  uint64_t *batchDiagFc1;
  uint64_t *batchDiagFc2;
  size_t batchDiagCapacity;
  int *batchRowCountsDevice;
  size_t batchRowCountsCapacity;
  int *batchRowOffsetsDevice;
  size_t batchRowOffsetsCapacity;
  int *batchRunOffsetsDevice;
  size_t batchRunOffsetsCapacity;
  int *batchEventTotalsDevice;
  size_t batchEventTotalsCapacity;
  int *batchRunTotalsDevice;
  size_t batchRunTotalsCapacity;
  int *batchEventScoreFloorsDevice;
  size_t batchEventScoreFloorsCapacity;
  int *batchEventBasesDevice;
  size_t batchEventBasesCapacity;
  int *batchRunBasesDevice;
  size_t batchRunBasesCapacity;
  SimScanCudaCandidateState *batchCandidateStatesDevice;
  size_t batchCandidateStatesCapacity;
  int *batchCandidateCountsDevice;
  size_t batchCandidateCountsCapacity;
  int *batchRunningMinsDevice;
  size_t batchRunningMinsCapacity;
  int *batchAllCandidateCountsDevice;
  size_t batchAllCandidateCountsCapacity;
  struct SimScanCudaBatchCandidateReduceKey *batchHashKeysDevice;
  size_t batchHashKeysCapacity;
  int *batchHashFlagsDevice;
  size_t batchHashFlagsCapacity;
  struct SimScanCudaCandidateReduceState *batchHashStatesDevice;
  size_t batchHashStatesCapacity;

  SimScanCudaProposalRowSummaryState *proposalRowStatesDevice;
  size_t proposalRowStatesCapacity;
  uint64_t *proposalOnlineHashKeysDevice;
  size_t proposalOnlineHashKeysCapacity;
  int *proposalOnlineHashFlagsDevice;
  size_t proposalOnlineHashFlagsCapacity;
  SimScanCudaCandidateState *proposalOnlineHashStatesDevice;
  size_t proposalOnlineHashStatesCapacity;
  SimScanCudaRowEvent *eventsDevice;
  size_t eventsCapacity;
  SimScanCudaInitialRunSummary *initialRunSummariesDevice;
  size_t initialRunSummariesCapacity;
  uint64_t *summaryKeysDevice;
  size_t summaryKeysCapacity;
  uint64_t *reducedKeysDevice;
  size_t reducedKeysCapacity;
  struct SimScanCudaBatchCandidateReduceKey *batchSummaryKeysDevice;
  size_t batchSummaryKeysCapacity;
  struct SimScanCudaBatchCandidateReduceKey *batchReducedKeysDevice;
  size_t batchReducedKeysCapacity;
  struct SimScanCudaCandidateReduceState *reduceStatesDevice;
  size_t reduceStatesCapacity;
  struct SimScanCudaCandidateReduceState *reducedStatesDevice;
  size_t reducedStatesCapacity;
  SimScanCudaCandidateState *outputCandidateStatesDevice;
  size_t outputCandidateStatesCapacity;
  unsigned long long *initialReduceReplayStatsDevice;
  size_t initialReduceReplayStatsCapacity;
  int *summaryRowMinColsDevice;
  size_t summaryRowMinColsCapacity;
  int *summaryRowMaxColsDevice;
  size_t summaryRowMaxColsCapacity;
  int *rowIntervalOffsetsDevice;
  size_t rowIntervalOffsetsCapacity;
  SimScanCudaColumnInterval *rowIntervalsDevice;
  size_t rowIntervalsCapacity;
  uint64_t *filterStartCoordsDevice;
  size_t filterStartCoordsCapacity;
  SimScanCudaCandidateState *candidateStatesDevice;
  int *candidateCountDevice;
  int *filteredCandidateCountDevice;
  int *runningMinDevice;
  int *eventCountDevice;

  cudaEvent_t startEvent;
  cudaEvent_t stopEvent;
  cudaEvent_t auxStartEvent;
  cudaEvent_t auxStopEvent;
  int *batchOutputCursorsDevice;
  size_t batchOutputCursorsCapacity;
};

struct SimScanCudaCandidateReduceState
{
  SimScanCudaCandidateState candidate;
  uint32_t bestOrder;
};

static bool sim_scan_cuda_begin_aux_timing(SimScanCudaContext *context,
                                           string *errorOut)
{
  if(context == NULL || context->auxStartEvent == NULL || context->auxStopEvent == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA aux timing events not initialized";
    }
    return false;
  }
  const cudaError_t status = cudaEventRecord(context->auxStartEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_end_aux_timing(SimScanCudaContext *context,
                                         double *outSeconds,
                                         string *errorOut)
{
  if(outSeconds != NULL)
  {
    *outSeconds = 0.0;
  }
  if(context == NULL || context->auxStartEvent == NULL || context->auxStopEvent == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA aux timing events not initialized";
    }
    return false;
  }

  cudaError_t status = cudaEventRecord(context->auxStopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->auxStopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs,
                                  context->auxStartEvent,
                                  context->auxStopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outSeconds != NULL)
  {
    *outSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }
  return true;
}

struct SimScanCudaBatchCandidateReduceKey
{
  uint32_t batchIndex;
  uint64_t startCoord;
};

LONGTARGET_SIM_SCAN_HOST_DEVICE void initSimScanCudaCandidateReduceStateFromInitialRunSummary(const SimScanCudaInitialRunSummary &summary,
                                                                                              uint32_t order,
                                                                                              SimScanCudaCandidateReduceState &state)
{
  initSimScanCudaCandidateStateFromInitialRunSummary(summary,state.candidate);
  state.bestOrder = order;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE void initSimScanCudaCandidateReduceStateFromCandidateState(const SimScanCudaCandidateState &candidate,
                                                                                            uint32_t order,
                                                                                            SimScanCudaCandidateReduceState &state)
{
  state.candidate = candidate;
  state.bestOrder = order;
}

LONGTARGET_SIM_SCAN_HOST_DEVICE bool updateSimScanCudaCandidateStateFromCandidateState(
  const SimScanCudaCandidateState &source,
  SimScanCudaCandidateState &target)
{
  const bool improved = target.score < source.score;
  if(improved)
  {
    target.score = source.score;
    target.endI = source.endI;
    target.endJ = source.endJ;
  }
  if(target.top > source.top) target.top = source.top;
  if(target.bot < source.bot) target.bot = source.bot;
  if(target.left > source.left) target.left = source.left;
  if(target.right < source.right) target.right = source.right;
  return improved;
}

struct SimScanCudaCandidateReduceMergeOp
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE SimScanCudaCandidateReduceState operator()(const SimScanCudaCandidateReduceState &lhs,
                                                                             const SimScanCudaCandidateReduceState &rhs) const
  {
    SimScanCudaCandidateReduceState merged = lhs;
    if(rhs.candidate.score > merged.candidate.score ||
       (rhs.candidate.score == merged.candidate.score && rhs.bestOrder < merged.bestOrder))
    {
      merged.candidate.score = rhs.candidate.score;
      merged.candidate.endI = rhs.candidate.endI;
      merged.candidate.endJ = rhs.candidate.endJ;
      merged.bestOrder = rhs.bestOrder;
    }
    if(merged.candidate.top > rhs.candidate.top) merged.candidate.top = rhs.candidate.top;
    if(merged.candidate.bot < rhs.candidate.bot) merged.candidate.bot = rhs.candidate.bot;
    if(merged.candidate.left > rhs.candidate.left) merged.candidate.left = rhs.candidate.left;
    if(merged.candidate.right < rhs.candidate.right) merged.candidate.right = rhs.candidate.right;
    return merged;
  }
};

struct SimScanCudaBatchCandidateReduceKeyLess
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE bool operator()(const SimScanCudaBatchCandidateReduceKey &lhs,
                                                  const SimScanCudaBatchCandidateReduceKey &rhs) const
  {
    return lhs.batchIndex < rhs.batchIndex ||
           (lhs.batchIndex == rhs.batchIndex && lhs.startCoord < rhs.startCoord);
  }
};

struct SimScanCudaBatchCandidateReduceKeyEqual
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE bool operator()(const SimScanCudaBatchCandidateReduceKey &lhs,
                                                  const SimScanCudaBatchCandidateReduceKey &rhs) const
  {
    return lhs.batchIndex == rhs.batchIndex && lhs.startCoord == rhs.startCoord;
  }
};

__device__ __forceinline__ size_t sim_scan_batch_candidate_reduce_hash_index(const SimScanCudaBatchCandidateReduceKey &key,
                                                                             size_t capacity)
{
  uint64_t mixed = key.startCoord ^ (static_cast<uint64_t>(key.batchIndex) * 0x9e3779b97f4a7c15ULL);
  mixed ^= mixed >> 33;
  mixed *= 0xff51afd7ed558ccdULL;
  mixed ^= mixed >> 33;
  return static_cast<size_t>(mixed) & (capacity - 1);
}

__device__ __forceinline__ bool sim_scan_batch_candidate_reduce_hash_merge_state(
  const SimScanCudaBatchCandidateReduceKey &key,
  const SimScanCudaCandidateReduceState &state,
  SimScanCudaBatchCandidateReduceKey *keys,
  int *flags,
  SimScanCudaCandidateReduceState *states,
  size_t capacity,
  int *overflowFlag)
{
  if(capacity == 0)
  {
    atomicExch(overflowFlag,1);
    return false;
  }

  SimScanCudaCandidateReduceMergeOp mergeOp;
  size_t slot = sim_scan_batch_candidate_reduce_hash_index(key,capacity);
  for(size_t probe = 0; probe < capacity; ++probe)
  {
    while(true)
    {
      const int flag = atomicAdd(flags + slot,0);
      if(flag == sim_scan_online_hash_flag_initializing)
      {
        continue;
      }
      if(flag == sim_scan_online_hash_flag_empty)
      {
        if(atomicCAS(flags + slot,
                     sim_scan_online_hash_flag_empty,
                     sim_scan_online_hash_flag_initializing) == sim_scan_online_hash_flag_empty)
        {
          keys[slot] = key;
          states[slot] = state;
          __threadfence();
          atomicExch(flags + slot,sim_scan_online_hash_flag_ready);
          return true;
        }
        continue;
      }

      const SimScanCudaBatchCandidateReduceKey slotKey = keys[slot];
      if(slotKey.batchIndex != key.batchIndex || slotKey.startCoord != key.startCoord)
      {
        break;
      }
      if(flag == sim_scan_online_hash_flag_locked)
      {
        continue;
      }
      if(atomicCAS(flags + slot,
                   sim_scan_online_hash_flag_ready,
                   sim_scan_online_hash_flag_locked) == sim_scan_online_hash_flag_ready)
      {
        states[slot] = mergeOp(states[slot],state);
        __threadfence();
        atomicExch(flags + slot,sim_scan_online_hash_flag_ready);
        return true;
      }
    }
    slot = (slot + 1) & (capacity - 1);
  }

  atomicExch(overflowFlag,1);
  return false;
}

struct SimScanCudaCandidateScoreGreater
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE bool operator()(const SimScanCudaCandidateState &lhs,
                                                  const SimScanCudaCandidateState &rhs) const
  {
    if(lhs.score != rhs.score)
    {
      return lhs.score > rhs.score;
    }
    const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
    const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
    if(lhsStart != rhsStart)
    {
      return lhsStart < rhsStart;
    }
    if(lhs.endI != rhs.endI)
    {
      return lhs.endI < rhs.endI;
    }
    if(lhs.endJ != rhs.endJ)
    {
      return lhs.endJ < rhs.endJ;
    }
    if(lhs.top != rhs.top)
    {
      return lhs.top < rhs.top;
    }
    if(lhs.bot != rhs.bot)
    {
      return lhs.bot < rhs.bot;
    }
    if(lhs.left != rhs.left)
    {
      return lhs.left < rhs.left;
    }
    return lhs.right < rhs.right;
  }
};

struct SimScanCudaCandidateReduceStateScoreGreater
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE bool operator()(const SimScanCudaCandidateReduceState &lhs,
                                                  const SimScanCudaCandidateReduceState &rhs) const
  {
    return SimScanCudaCandidateScoreGreater()(lhs.candidate,rhs.candidate);
  }
};

struct SimScanCudaCandidateStartCoordLess
{
  LONGTARGET_SIM_SCAN_HOST_DEVICE bool operator()(const SimScanCudaCandidateState &lhs,
                                                  const SimScanCudaCandidateState &rhs) const
  {
    return simScanCudaCandidateStateStartCoord(lhs) < simScanCudaCandidateStateStartCoord(rhs);
  }
};

__global__ void sim_scan_select_top_disjoint_candidate_states_kernel(const SimScanCudaCandidateState *sortedStates,
                                                                     int stateCount,
                                                                     int maxProposalCount,
                                                                     SimScanCudaCandidateState *selectedStates,
                                                                     int *selectedCountOut)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }

  int selectedCount = 0;
  for(int stateIndex = 0; stateIndex < stateCount && selectedCount < maxProposalCount; ++stateIndex)
  {
    const SimScanCudaCandidateState candidate = sortedStates[stateIndex];
    bool overlapsExisting = false;
    for(int selectedIndex = 0; selectedIndex < selectedCount; ++selectedIndex)
    {
      if(simScanCudaCandidateStateBoxesOverlap(candidate,selectedStates[selectedIndex]))
      {
        overlapsExisting = true;
        break;
      }
    }
    if(!overlapsExisting)
    {
      selectedStates[selectedCount++] = candidate;
    }
  }
  *selectedCountOut = selectedCount;
}

__global__ void sim_scan_select_top_disjoint_candidate_reduce_states_kernel(const SimScanCudaCandidateReduceState *sortedStates,
                                                                            int stateCount,
                                                                            int maxProposalCount,
                                                                            SimScanCudaCandidateState *selectedStates,
                                                                            int *selectedCountOut)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }

  int selectedCount = 0;
  for(int stateIndex = 0; stateIndex < stateCount && selectedCount < maxProposalCount; ++stateIndex)
  {
    const SimScanCudaCandidateState candidate = sortedStates[stateIndex].candidate;
    bool overlapsExisting = false;
    for(int selectedIndex = 0; selectedIndex < selectedCount; ++selectedIndex)
    {
      if(simScanCudaCandidateStateBoxesOverlap(candidate,selectedStates[selectedIndex]))
      {
        overlapsExisting = true;
        break;
      }
    }
    if(!overlapsExisting)
    {
      selectedStates[selectedCount++] = candidate;
    }
  }
  *selectedCountOut = selectedCount;
}

__global__ void sim_scan_select_top_disjoint_batch_candidate_reduce_states_kernel(const SimScanCudaCandidateReduceState *sortedStates,
                                                                                  const int *stateBases,
                                                                                  const int *stateCounts,
                                                                                  int batchSize,
                                                                                  int maxProposalCount,
                                                                                  SimScanCudaCandidateState *selectedStates,
                                                                                  int *selectedCountsOut)
{
  const int batchIndex = static_cast<int>(blockIdx.x);
  if(batchIndex >= batchSize || threadIdx.x != 0)
  {
    return;
  }

  const int stateBase = stateBases[batchIndex];
  const int stateCount = stateCounts[batchIndex];
  SimScanCudaCandidateState *batchSelectedStates = selectedStates + static_cast<size_t>(batchIndex) *
                                                                    static_cast<size_t>(maxProposalCount);
  int selectedCount = 0;
  for(int stateIndex = 0; stateIndex < stateCount && selectedCount < maxProposalCount; ++stateIndex)
  {
    const SimScanCudaCandidateState candidate = sortedStates[stateBase + stateIndex].candidate;
    bool overlapsExisting = false;
    for(int selectedIndex = 0; selectedIndex < selectedCount; ++selectedIndex)
    {
      if(simScanCudaCandidateStateBoxesOverlap(candidate,batchSelectedStates[selectedIndex]))
      {
        overlapsExisting = true;
        break;
      }
    }
    if(!overlapsExisting)
    {
      batchSelectedStates[selectedCount++] = candidate;
    }
  }
  selectedCountsOut[batchIndex] = selectedCount;
}

__global__ void sim_scan_select_top_batch_candidate_reduce_states_kernel(const SimScanCudaCandidateReduceState *sortedStates,
                                                                         const int *stateBases,
                                                                         const int *stateCounts,
                                                                         int batchSize,
                                                                         int maxCandidateCount,
                                                                         SimScanCudaCandidateState *selectedStates,
                                                                         int *selectedCountsOut,
                                                                         int *runningMinsOut)
{
  const int batchIndex = static_cast<int>(blockIdx.x);
  if(batchIndex >= batchSize || threadIdx.x != 0)
  {
    return;
  }

  const int stateBase = stateBases[batchIndex];
  const int stateCount = stateCounts[batchIndex];
  const int selectedCount = min(max(stateCount,0), maxCandidateCount);
  SimScanCudaCandidateState *batchSelectedStates = selectedStates + static_cast<size_t>(batchIndex) *
                                                                    static_cast<size_t>(maxCandidateCount);
  for(int stateIndex = 0; stateIndex < selectedCount; ++stateIndex)
  {
    batchSelectedStates[stateIndex] = sortedStates[stateBase + stateIndex].candidate;
  }
  selectedCountsOut[batchIndex] = selectedCount;
  runningMinsOut[batchIndex] = selectedCount > 0 ? batchSelectedStates[selectedCount - 1].score : 0;
}

__global__ void sim_scan_compact_batch_selected_candidate_states_kernel(const SimScanCudaCandidateState *batchSelectedStates,
                                                                        const int *selectedCounts,
                                                                        const int *selectedBases,
                                                                        int maxProposalCount,
                                                                        SimScanCudaCandidateState *packedSelectedStates)
{
  const int selectedIndex = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  const int batchIndex = static_cast<int>(blockIdx.y);
  const int selectedCount = selectedCounts[batchIndex];
  if(selectedIndex >= selectedCount)
  {
    return;
  }

  packedSelectedStates[selectedBases[batchIndex] + selectedIndex] =
    batchSelectedStates[static_cast<size_t>(batchIndex) * static_cast<size_t>(maxProposalCount) +
                        static_cast<size_t>(selectedIndex)];
}

__global__ void sim_scan_store_scalar_at_index_kernel(const int *valueDevice,
                                                      int *outputDevice,
                                                      int outputIndex)
{
  if(threadIdx.x != 0 || blockIdx.x != 0)
  {
    return;
  }
  outputDevice[outputIndex] = *valueDevice;
}

__global__ void sim_scan_copy_candidate_states_to_reserved_slice_kernel(const SimScanCudaCandidateState *inputStates,
                                                                        const int *inputCountDevice,
                                                                        int outputBase,
                                                                        int outputCapacity,
                                                                        SimScanCudaCandidateState *outputStates)
{
  int inputCount = *inputCountDevice;
  if(inputCount < 0)
  {
    inputCount = 0;
  }
  if(inputCount > outputCapacity)
  {
    inputCount = outputCapacity;
  }

  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= inputCount)
  {
    return;
  }
  outputStates[outputBase + idx] = inputStates[idx];
}

__global__ void sim_scan_compact_batch_reserved_candidate_states_kernel(const SimScanCudaCandidateState *reservedStates,
                                                                        const int *stateCounts,
                                                                        const int *stateInputBases,
                                                                        const int *stateOutputBases,
                                                                        SimScanCudaCandidateState *packedStates)
{
  const int batchIndex = static_cast<int>(blockIdx.y);
  const int stateIndex = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  const int stateCount = stateCounts[batchIndex];
  if(stateIndex >= stateCount)
  {
    return;
  }
  packedStates[stateOutputBases[batchIndex] + stateIndex] =
    reservedStates[stateInputBases[batchIndex] + stateIndex];
}

static bool sim_scan_select_top_disjoint_candidate_states_from_device_locked(SimScanCudaContext *context,
                                                                             SimScanCudaCandidateState *statesDevice,
                                                                             int stateCount,
                                                                             int maxProposalCount,
                                                                             vector<SimScanCudaCandidateState> *outSelectedStates,
                                                                             double *outGpuSeconds,
                                                                             string *errorOut)
{
  if(outSelectedStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing proposal helper outputs";
    }
    return false;
  }
  outSelectedStates->clear();
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = 0.0;
  }
  if(context == NULL || statesDevice == NULL || stateCount <= 0 || maxProposalCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  const int clampedProposalCount = min(maxProposalCount, sim_scan_cuda_max_candidates);
  cudaError_t status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  try
  {
    thrust::stable_sort(thrust::device,
                        thrust::device_pointer_cast(statesDevice),
                        thrust::device_pointer_cast(statesDevice + stateCount),
                        SimScanCudaCandidateScoreGreater());
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  catch(const std::exception &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  status = cudaMemset(context->candidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_select_top_disjoint_candidate_states_kernel<<<1,1>>>(statesDevice,
                                                                 stateCount,
                                                                 clampedProposalCount,
                                                                 context->candidateStatesDevice,
                                                                 context->candidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }

  int selectedCount = 0;
  status = cudaMemcpy(&selectedCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(selectedCount < 0 || selectedCount > clampedProposalCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA proposal helper returned invalid count";
    }
    return false;
  }

  outSelectedStates->resize(static_cast<size_t>(selectedCount));
  if(selectedCount > 0)
  {
    status = cudaMemcpy(outSelectedStates->data(),
                        context->candidateStatesDevice,
                        static_cast<size_t>(selectedCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      outSelectedStates->clear();
      return false;
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_select_top_disjoint_candidate_reduce_states_from_device_locked(SimScanCudaContext *context,
                                                                                    SimScanCudaCandidateReduceState *statesDevice,
                                                                                    int stateCount,
                                                                                    int maxProposalCount,
                                                                                    vector<SimScanCudaCandidateState> *outSelectedStates,
                                                                                    double *outGpuSeconds,
                                                                                    string *errorOut)
{
  if(outSelectedStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing proposal helper outputs";
    }
    return false;
  }
  outSelectedStates->clear();
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = 0.0;
  }
  if(context == NULL || statesDevice == NULL || stateCount <= 0 || maxProposalCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  const int clampedProposalCount = min(maxProposalCount, sim_scan_cuda_max_candidates);
  cudaError_t status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  try
  {
    thrust::stable_sort(thrust::device,
                        thrust::device_pointer_cast(statesDevice),
                        thrust::device_pointer_cast(statesDevice + stateCount),
                        SimScanCudaCandidateReduceStateScoreGreater());
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  catch(const std::exception &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  status = cudaMemset(context->candidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_select_top_disjoint_candidate_reduce_states_kernel<<<1,1>>>(statesDevice,
                                                                        stateCount,
                                                                        clampedProposalCount,
                                                                        context->candidateStatesDevice,
                                                                        context->candidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }

  int selectedCount = 0;
  status = cudaMemcpy(&selectedCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(selectedCount < 0 || selectedCount > clampedProposalCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA proposal helper returned invalid count";
    }
    return false;
  }

  outSelectedStates->resize(static_cast<size_t>(selectedCount));
  if(selectedCount > 0)
  {
    status = cudaMemcpy(outSelectedStates->data(),
                        context->candidateStatesDevice,
                        static_cast<size_t>(selectedCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      outSelectedStates->clear();
      return false;
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_select_top_disjoint_candidate_reduce_states_true_batch_locked(
  SimScanCudaContext *context,
  SimScanCudaCandidateReduceState *statesDevice,
  const vector<int> &stateBases,
  const vector<int> &stateCounts,
  int maxProposalCount,
  vector<int> *outSelectedCounts,
  vector<SimScanCudaCandidateState> *outPackedSelectedStates,
  double *outGpuSeconds,
  double *outD2HSeconds,
  string *errorOut)
{
  if(outSelectedCounts == NULL || outPackedSelectedStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batched proposal helper outputs";
    }
    return false;
  }
  outSelectedCounts->assign(stateCounts.size(),0);
  outPackedSelectedStates->clear();
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = 0.0;
  }
  if(outD2HSeconds != NULL)
  {
    *outD2HSeconds = 0.0;
  }
  if(context == NULL || statesDevice == NULL || stateCounts.empty() || maxProposalCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(stateBases.size() != stateCounts.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched proposal helper base/count mismatch";
    }
    return false;
  }

  const int batchSize = static_cast<int>(stateCounts.size());
  const int clampedProposalCount = min(maxProposalCount, sim_scan_cuda_max_candidates);
  if(clampedProposalCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->batchCandidateStatesDevice,
                                  &context->batchCandidateStatesCapacity,
                                  static_cast<size_t>(batchSize) * static_cast<size_t>(clampedProposalCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchCandidateCountsDevice,
                                  &context->batchCandidateCountsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->batchEventBasesDevice,
                                  stateBases.data(),
                                  static_cast<size_t>(batchSize) * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->batchCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  try
  {
    for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
    {
      const int stateCount = stateCounts[static_cast<size_t>(batchIndex)];
      const int stateBase = stateBases[static_cast<size_t>(batchIndex)];
      if(stateCount <= 1)
      {
        continue;
      }
      thrust::stable_sort(thrust::device,
                          thrust::device_pointer_cast(statesDevice + stateBase),
                          thrust::device_pointer_cast(statesDevice + stateBase + stateCount),
                          SimScanCudaCandidateReduceStateScoreGreater());
    }
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  sim_scan_select_top_disjoint_batch_candidate_reduce_states_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    statesDevice,
    context->batchEventBasesDevice,
    context->batchAllCandidateCountsDevice,
    batchSize,
    clampedProposalCount,
    context->batchCandidateStatesDevice,
    context->batchCandidateCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  double d2hSeconds = 0.0;
  std::chrono::steady_clock::time_point copyStart = std::chrono::steady_clock::now();
  status = cudaMemcpy(outSelectedCounts->data(),
                      context->batchCandidateCountsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  d2hSeconds += static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                      std::chrono::steady_clock::now() - copyStart).count()) / 1.0e9;

  int totalSelectedCount = 0;
  vector<int> selectedBases(static_cast<size_t>(batchSize),0);
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int selectedCount = (*outSelectedCounts)[static_cast<size_t>(batchIndex)];
    if(selectedCount < 0 || selectedCount > clampedProposalCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched proposal helper returned invalid count";
      }
      outPackedSelectedStates->clear();
      return false;
    }
    selectedBases[static_cast<size_t>(batchIndex)] = totalSelectedCount;
    totalSelectedCount += selectedCount;
  }

  if(totalSelectedCount > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                    &context->outputCandidateStatesCapacity,
                                    static_cast<size_t>(totalSelectedCount),
                                    errorOut))
    {
      return false;
    }
    status = cudaMemcpy(context->batchEventBasesDevice,
                        selectedBases.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    status = cudaEventRecord(context->startEvent);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int compactThreads = 256;
    const int compactBlocks = (clampedProposalCount + compactThreads - 1) / compactThreads;
    sim_scan_compact_batch_selected_candidate_states_kernel<<<dim3(static_cast<unsigned int>(compactBlocks),
                                                                   static_cast<unsigned int>(batchSize)),
                                                             compactThreads>>>(
      context->batchCandidateStatesDevice,
      context->batchCandidateCountsDevice,
      context->batchEventBasesDevice,
      clampedProposalCount,
      context->outputCandidateStatesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    status = cudaEventRecord(context->stopEvent);
    if(status == cudaSuccess)
    {
      status = cudaEventSynchronize(context->stopEvent);
    }
    float compactElapsedMs = 0.0f;
    if(status == cudaSuccess)
    {
      status = cudaEventElapsedTime(&compactElapsedMs, context->startEvent, context->stopEvent);
    }
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    elapsedMs += compactElapsedMs;

    outPackedSelectedStates->resize(static_cast<size_t>(totalSelectedCount));
    copyStart = std::chrono::steady_clock::now();
    status = cudaMemcpy(outPackedSelectedStates->data(),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(totalSelectedCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      outPackedSelectedStates->clear();
      return false;
    }
    d2hSeconds += static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                        std::chrono::steady_clock::now() - copyStart).count()) / 1.0e9;
  }

  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }
  if(outD2HSeconds != NULL)
  {
    *outD2HSeconds = d2hSeconds;
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_select_top_candidate_reduce_states_true_batch_locked(
  SimScanCudaContext *context,
  SimScanCudaCandidateReduceState *statesDevice,
  const vector<int> &stateBases,
  const vector<int> &stateCounts,
  int maxCandidateCount,
  double *outGpuSeconds,
  string *errorOut)
{
  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = 0.0;
  }
  if(context == NULL || statesDevice == NULL || stateCounts.empty() || maxCandidateCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(stateBases.size() != stateCounts.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched top-k helper base/count mismatch";
    }
    return false;
  }

  const int batchSize = static_cast<int>(stateCounts.size());
  const int clampedCandidateCount = min(maxCandidateCount, sim_scan_cuda_max_candidates);
  int totalStateCount = 0;
  for(size_t batchIndex = 0; batchIndex < stateCounts.size(); ++batchIndex)
  {
    const int stateBase = stateBases[batchIndex];
    const int stateCount = stateCounts[batchIndex];
    if(stateBase < 0 || stateCount < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched top-k helper invalid base/count";
      }
      return false;
    }
    totalStateCount = max(totalStateCount,stateBase + stateCount);
  }
  if(clampedCandidateCount <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->batchCandidateStatesDevice,
                                  &context->batchCandidateStatesCapacity,
                                  static_cast<size_t>(batchSize) * static_cast<size_t>(clampedCandidateCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchCandidateCountsDevice,
                                  &context->batchCandidateCountsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunningMinsDevice,
                                  &context->batchRunningMinsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchAllCandidateCountsDevice,
                                  &context->batchAllCandidateCountsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                  &context->reduceStatesCapacity,
                                  static_cast<size_t>(max(totalStateCount,0)),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaSuccess;
  if(totalStateCount > 0)
  {
    status = cudaMemcpy(context->reduceStatesDevice,
                        statesDevice,
                        static_cast<size_t>(totalStateCount) * sizeof(SimScanCudaCandidateReduceState),
                        cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  status = cudaMemcpy(context->batchEventBasesDevice,
                      stateBases.data(),
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->batchAllCandidateCountsDevice,
                      stateCounts.data(),
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->batchCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->batchRunningMinsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  try
  {
    for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
    {
      const int stateCount = stateCounts[static_cast<size_t>(batchIndex)];
      const int stateBase = stateBases[static_cast<size_t>(batchIndex)];
      if(stateCount <= 1)
      {
        continue;
      }
      thrust::stable_sort(thrust::device,
                          thrust::device_pointer_cast(context->reduceStatesDevice + stateBase),
                          thrust::device_pointer_cast(context->reduceStatesDevice + stateBase + stateCount),
                          SimScanCudaCandidateReduceStateScoreGreater());
    }
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  sim_scan_select_top_batch_candidate_reduce_states_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    context->reduceStatesDevice,
    context->batchEventBasesDevice,
    context->batchAllCandidateCountsDevice,
    batchSize,
    clampedCandidateCount,
    context->batchCandidateStatesDevice,
    context->batchCandidateCountsDevice,
    context->batchRunningMinsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(outGpuSeconds != NULL)
  {
    *outGpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

template <typename T>
static bool ensure_sim_scan_cuda_buffer(T **buffer,
                                        size_t *capacity,
                                        size_t needed,
                                        string *errorOut)
{
  if(buffer == NULL || capacity == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "internal error: missing CUDA buffer bookkeeping";
    }
    return false;
  }
  if(needed == 0)
  {
    return true;
  }
  if(*buffer != NULL && *capacity >= needed)
  {
    return true;
  }
  if(*buffer != NULL)
  {
    cudaFree(*buffer);
    *buffer = NULL;
    *capacity = 0;
  }
  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(buffer), needed * sizeof(T));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  *capacity = needed;
  return true;
}

static SimScanCudaCandidateState *sim_scan_cuda_handle_states_device(const SimCudaPersistentSafeStoreHandle &handle)
{
  return reinterpret_cast<SimScanCudaCandidateState *>(handle.statesDevice);
}

static SimScanCudaCandidateState *sim_scan_cuda_handle_frontier_states_device(
  const SimCudaPersistentSafeStoreHandle &handle)
{
  return reinterpret_cast<SimScanCudaCandidateState *>(handle.frontierStatesDevice);
}

static void sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(
  SimCudaPersistentSafeStoreHandle *handle,
  bool frontierValid,
  int frontierRunningMin,
  size_t frontierCount)
{
  if(handle == NULL)
  {
    return;
  }
  handle->frontierValid = frontierValid;
  handle->frontierRunningMin = frontierRunningMin;
  handle->frontierCount = frontierCount;
}

static void sim_scan_cuda_invalidate_persistent_safe_store_frontier_locked(
  SimCudaPersistentSafeStoreHandle *handle)
{
  if(handle == NULL)
  {
    return;
  }
  if(handle->frontierStatesDevice != 0)
  {
    cudaFree(reinterpret_cast<void *>(handle->frontierStatesDevice));
    handle->frontierStatesDevice = 0;
  }
  handle->frontierCapacity = 0;
  sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handle,false,0,0);
}

static bool sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
  const SimScanCudaCandidateState *frontierStatesDevice,
  int frontierCount,
  int frontierRunningMin,
  SimCudaPersistentSafeStoreHandle *handle,
  string *errorOut)
{
  if(handle == NULL || !handle->valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store frontier cache handle";
    }
    return false;
  }
  if(frontierCount < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store frontier count overflow";
    }
    return false;
  }
  if(frontierCount == 0)
  {
    sim_scan_cuda_invalidate_persistent_safe_store_frontier_locked(handle);
    sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handle,true,frontierRunningMin,0);
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(frontierStatesDevice == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store frontier source buffer";
    }
    return false;
  }

  const size_t needed = static_cast<size_t>(frontierCount);
  if(handle->frontierStatesDevice == 0 || handle->frontierCapacity < needed)
  {
    if(handle->frontierStatesDevice != 0)
    {
      cudaFree(reinterpret_cast<void *>(handle->frontierStatesDevice));
      handle->frontierStatesDevice = 0;
      handle->frontierCapacity = 0;
    }
    SimScanCudaCandidateState *frontierCopyDevice = NULL;
    cudaError_t status =
      cudaMalloc(reinterpret_cast<void **>(&frontierCopyDevice),
                 needed * sizeof(SimScanCudaCandidateState));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    handle->frontierStatesDevice = reinterpret_cast<uintptr_t>(frontierCopyDevice);
    handle->frontierCapacity = needed;
  }

  const cudaError_t status =
    cudaMemcpy(sim_scan_cuda_handle_frontier_states_device(*handle),
               frontierStatesDevice,
               needed * sizeof(SimScanCudaCandidateState),
               cudaMemcpyDeviceToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handle,true,frontierRunningMin,needed);
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_cuda_clone_persistent_safe_store_from_device_locked(const SimScanCudaCandidateState *statesDevice,
                                                                         size_t stateCount,
                                                                         int device,
                                                                         int slot,
                                                                         SimCudaPersistentSafeStoreHandle *handleOut,
                                                                         string *errorOut)
{
  if(handleOut == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store output handle";
    }
    return false;
  }
  *handleOut = SimCudaPersistentSafeStoreHandle();
  if(stateCount == 0)
  {
    handleOut->valid = true;
    handleOut->device = device;
    handleOut->slot = slot;
    sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handleOut,false,0,0);
    return true;
  }
  if(statesDevice == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store source buffer";
    }
    return false;
  }

  SimScanCudaCandidateState *copyDevice = NULL;
  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&copyDevice),
                                  stateCount * sizeof(SimScanCudaCandidateState));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(copyDevice,
                      statesDevice,
                      stateCount * sizeof(SimScanCudaCandidateState),
                      cudaMemcpyDeviceToDevice);
  if(status != cudaSuccess)
  {
    cudaFree(copyDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  handleOut->valid = true;
  handleOut->device = device;
  handleOut->slot = slot;
  handleOut->stateCount = stateCount;
  handleOut->statesDevice = reinterpret_cast<uintptr_t>(copyDevice);
  sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handleOut,false,0,0);
  return true;
}

static void clear_sim_scan_cuda_true_batch_diag_buffers(SimScanCudaContext &context)
{
  if(context.batchDiagH0 != NULL) cudaFree(context.batchDiagH0);
  if(context.batchDiagH1 != NULL) cudaFree(context.batchDiagH1);
  if(context.batchDiagH2 != NULL) cudaFree(context.batchDiagH2);
  if(context.batchDiagD1 != NULL) cudaFree(context.batchDiagD1);
  if(context.batchDiagD2 != NULL) cudaFree(context.batchDiagD2);
  if(context.batchDiagF1 != NULL) cudaFree(context.batchDiagF1);
  if(context.batchDiagF2 != NULL) cudaFree(context.batchDiagF2);
  if(context.batchDiagHc0 != NULL) cudaFree(context.batchDiagHc0);
  if(context.batchDiagHc1 != NULL) cudaFree(context.batchDiagHc1);
  if(context.batchDiagHc2 != NULL) cudaFree(context.batchDiagHc2);
  if(context.batchDiagDc1 != NULL) cudaFree(context.batchDiagDc1);
  if(context.batchDiagDc2 != NULL) cudaFree(context.batchDiagDc2);
  if(context.batchDiagFc1 != NULL) cudaFree(context.batchDiagFc1);
  if(context.batchDiagFc2 != NULL) cudaFree(context.batchDiagFc2);
  context.batchDiagH0 = NULL;
  context.batchDiagH1 = NULL;
  context.batchDiagH2 = NULL;
  context.batchDiagD1 = NULL;
  context.batchDiagD2 = NULL;
  context.batchDiagF1 = NULL;
  context.batchDiagF2 = NULL;
  context.batchDiagHc0 = NULL;
  context.batchDiagHc1 = NULL;
  context.batchDiagHc2 = NULL;
  context.batchDiagDc1 = NULL;
  context.batchDiagDc2 = NULL;
  context.batchDiagFc1 = NULL;
  context.batchDiagFc2 = NULL;
  context.batchDiagCapacity = 0;
}

static bool ensure_sim_scan_cuda_true_batch_diag_capacity_locked(SimScanCudaContext &context,
                                                                 size_t needed,
                                                                 string *errorOut)
{
  if(needed == 0)
  {
    return true;
  }
  const bool alreadyReady =
    context.batchDiagCapacity >= needed &&
    context.batchDiagH0 != NULL &&
    context.batchDiagH1 != NULL &&
    context.batchDiagH2 != NULL &&
    context.batchDiagD1 != NULL &&
    context.batchDiagD2 != NULL &&
    context.batchDiagF1 != NULL &&
    context.batchDiagF2 != NULL &&
    context.batchDiagHc0 != NULL &&
    context.batchDiagHc1 != NULL &&
    context.batchDiagHc2 != NULL &&
    context.batchDiagDc1 != NULL &&
    context.batchDiagDc2 != NULL &&
    context.batchDiagFc1 != NULL &&
    context.batchDiagFc2 != NULL;
  if(alreadyReady)
  {
    return true;
  }

  clear_sim_scan_cuda_true_batch_diag_buffers(context);
  if(!ensure_sim_scan_cuda_buffer(&context.batchDiagH0,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagH1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagH2,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagD1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagD2,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagF1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagF2,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagHc0,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagHc1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagHc2,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagDc1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagDc2,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagFc1,&context.batchDiagCapacity,needed,errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context.batchDiagFc2,&context.batchDiagCapacity,needed,errorOut))
  {
    clear_sim_scan_cuda_true_batch_diag_buffers(context);
    return false;
  }
  return true;
}

static mutex sim_scan_cuda_contexts_mutex;
static vector< vector< unique_ptr<SimScanCudaContext> > > sim_scan_cuda_contexts;
static vector< vector< unique_ptr<mutex> > > sim_scan_cuda_context_mutexes;

static bool get_sim_scan_cuda_context_for_device_slot(int device,
                                                      int slot,
                                                      SimScanCudaContext **contextOut,
                                                      mutex **mutexOut,
                                                      string *errorOut)
{
  if(contextOut == NULL || mutexOut == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "internal error: missing output pointers";
    }
    return false;
  }

  int deviceCount = 0;
  const cudaError_t countStatus = cudaGetDeviceCount(&deviceCount);
  if(countStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(countStatus);
    }
    return false;
  }
  if(deviceCount <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "no CUDA devices available";
    }
    return false;
  }
  if(device < 0)
  {
    device = 0;
  }
  if(slot < 0)
  {
    slot = 0;
  }
  if(device >= deviceCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "requested CUDA device index is out of range";
    }
    return false;
  }

  lock_guard<mutex> lock(sim_scan_cuda_contexts_mutex);
  if(sim_scan_cuda_contexts.size() <= static_cast<size_t>(device))
  {
    sim_scan_cuda_contexts.resize(static_cast<size_t>(device) + 1);
    sim_scan_cuda_context_mutexes.resize(static_cast<size_t>(device) + 1);
  }
  vector< unique_ptr<SimScanCudaContext> > &deviceContexts = sim_scan_cuda_contexts[static_cast<size_t>(device)];
  vector< unique_ptr<mutex> > &deviceMutexes = sim_scan_cuda_context_mutexes[static_cast<size_t>(device)];
  if(deviceContexts.size() <= static_cast<size_t>(slot))
  {
    deviceContexts.resize(static_cast<size_t>(slot) + 1);
    deviceMutexes.resize(static_cast<size_t>(slot) + 1);
  }
  if(!deviceContexts[static_cast<size_t>(slot)])
  {
    deviceContexts[static_cast<size_t>(slot)].reset(new SimScanCudaContext());
  }
  if(!deviceMutexes[static_cast<size_t>(slot)])
  {
    deviceMutexes[static_cast<size_t>(slot)].reset(new mutex());
  }

  *contextOut = deviceContexts[static_cast<size_t>(slot)].get();
  *mutexOut = deviceMutexes[static_cast<size_t>(slot)].get();
  return true;
}

static bool ensure_sim_scan_cuda_initialized_locked(SimScanCudaContext &context,int device,string *errorOut)
{
  const cudaError_t setStatus = cudaSetDevice(device);
  if(setStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(setStatus);
    }
    return false;
  }

  if(context.initialized)
  {
    if(context.device != device)
    {
      if(errorOut != NULL)
      {
        *errorOut = "CUDA context device mismatch";
      }
      return false;
    }
    return true;
  }

  cudaError_t status = cudaEventCreate(&context.startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventCreate(&context.stopEvent);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(context.startEvent);
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventCreate(&context.auxStartEvent);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventCreate(&context.auxStopEvent);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&context.candidateStatesDevice),
                      static_cast<size_t>(sim_scan_cuda_max_candidates) * sizeof(SimScanCudaCandidateState));
  if(status != cudaSuccess)
  {
    cudaEventDestroy(context.auxStopEvent);
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStopEvent = NULL;
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&context.candidateCountDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(context.candidateStatesDevice);
    context.candidateStatesDevice = NULL;
    cudaEventDestroy(context.auxStopEvent);
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStopEvent = NULL;
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&context.runningMinDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(context.candidateCountDevice);
    context.candidateCountDevice = NULL;
    cudaFree(context.candidateStatesDevice);
    context.candidateStatesDevice = NULL;
    cudaEventDestroy(context.auxStopEvent);
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStopEvent = NULL;
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&context.eventCountDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(context.runningMinDevice);
    context.runningMinDevice = NULL;
    cudaFree(context.candidateCountDevice);
    context.candidateCountDevice = NULL;
    cudaFree(context.candidateStatesDevice);
    context.candidateStatesDevice = NULL;
    cudaEventDestroy(context.auxStopEvent);
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStopEvent = NULL;
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&context.filteredCandidateCountDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(context.eventCountDevice);
    context.eventCountDevice = NULL;
    cudaFree(context.runningMinDevice);
    context.runningMinDevice = NULL;
    cudaFree(context.candidateCountDevice);
    context.candidateCountDevice = NULL;
    cudaFree(context.candidateStatesDevice);
    context.candidateStatesDevice = NULL;
    cudaEventDestroy(context.auxStopEvent);
    cudaEventDestroy(context.auxStartEvent);
    cudaEventDestroy(context.stopEvent);
    cudaEventDestroy(context.startEvent);
    context.auxStopEvent = NULL;
    context.auxStartEvent = NULL;
    context.stopEvent = NULL;
    context.startEvent = NULL;
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  context.initialized = true;
  context.device = device;
  return true;
}

static bool ensure_sim_scan_cuda_capacity_locked(SimScanCudaContext &context,int queryLength,int targetLength,string *errorOut)
{
  if(queryLength <= context.capacityQuery && targetLength <= context.capacityTarget)
  {
    return true;
  }

  const int newCapQuery = max(context.capacityQuery, queryLength);
  const int newCapTarget = max(context.capacityTarget, targetLength);
  const int newLeadingDim = newCapTarget + 1;
  const int diagCapacity = max(newCapQuery, newCapTarget) + 2;

  char *newADevice = NULL;
  char *newBDevice = NULL;
  int *newHScoreDevice = NULL;
  uint64_t *newHCoordDevice = NULL;
  int *newDiagH0 = NULL;
  int *newDiagH1 = NULL;
  int *newDiagH2 = NULL;
  int *newDiagD0 = NULL;
  int *newDiagD1 = NULL;
  int *newDiagD2 = NULL;
  int *newDiagF0 = NULL;
  int *newDiagF1 = NULL;
  int *newDiagF2 = NULL;
  uint64_t *newDiagHc0 = NULL;
  uint64_t *newDiagHc1 = NULL;
  uint64_t *newDiagHc2 = NULL;
  uint64_t *newDiagDc0 = NULL;
  uint64_t *newDiagDc1 = NULL;
  uint64_t *newDiagDc2 = NULL;
  uint64_t *newDiagFc0 = NULL;
  uint64_t *newDiagFc1 = NULL;
  uint64_t *newDiagFc2 = NULL;
  int *newRowCountsDevice = NULL;
  int *newRowOffsetsDevice = NULL;
  int *newRunOffsetsDevice = NULL;

  const size_t aBytes = static_cast<size_t>(newCapQuery + 1) * sizeof(char);
  const size_t bBytes = static_cast<size_t>(newCapTarget + 1) * sizeof(char);
  const size_t matrixCells = static_cast<size_t>(newCapQuery + 1) * static_cast<size_t>(newLeadingDim);
  const size_t hScoreBytes = matrixCells * sizeof(int);
  const size_t hCoordBytes = matrixCells * sizeof(uint64_t);
  const size_t diagIntsBytes = static_cast<size_t>(diagCapacity) * sizeof(int);
  const size_t diagCoordsBytes = static_cast<size_t>(diagCapacity) * sizeof(uint64_t);
  const size_t rowCountsBytes = static_cast<size_t>(newCapQuery + 1) * sizeof(int);
  const size_t rowOffsetsBytes = static_cast<size_t>(newCapQuery + 2) * sizeof(int);

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newADevice), aBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newBDevice), bBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newHScoreDevice), hScoreBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newHCoordDevice), hCoordBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagH0), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagH1), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagH2), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagD0), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagD1), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagD2), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagF0), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagF1), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagF2), diagIntsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagHc0), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagHc1), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagHc2), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagDc0), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagDc1), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagDc2), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDiagFc0), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagFc1), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    cudaFree(newDiagFc0);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDiagFc2), diagCoordsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    cudaFree(newDiagFc0);
    cudaFree(newDiagFc1);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newRowCountsDevice), rowCountsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    cudaFree(newDiagFc0);
    cudaFree(newDiagFc1);
    cudaFree(newDiagFc2);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newRowOffsetsDevice), rowOffsetsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    cudaFree(newDiagFc0);
    cudaFree(newDiagFc1);
    cudaFree(newDiagFc2);
    cudaFree(newRowCountsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newRunOffsetsDevice), rowOffsetsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newHScoreDevice);
    cudaFree(newHCoordDevice);
    cudaFree(newDiagH0);
    cudaFree(newDiagH1);
    cudaFree(newDiagH2);
    cudaFree(newDiagD0);
    cudaFree(newDiagD1);
    cudaFree(newDiagD2);
    cudaFree(newDiagF0);
    cudaFree(newDiagF1);
    cudaFree(newDiagF2);
    cudaFree(newDiagHc0);
    cudaFree(newDiagHc1);
    cudaFree(newDiagHc2);
    cudaFree(newDiagDc0);
    cudaFree(newDiagDc1);
    cudaFree(newDiagDc2);
    cudaFree(newDiagFc0);
    cudaFree(newDiagFc1);
    cudaFree(newDiagFc2);
    cudaFree(newRowCountsDevice);
    cudaFree(newRowOffsetsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.ADevice != NULL) cudaFree(context.ADevice);
  if(context.BDevice != NULL) cudaFree(context.BDevice);
  if(context.HScoreDevice != NULL) cudaFree(context.HScoreDevice);
  if(context.HCoordDevice != NULL) cudaFree(context.HCoordDevice);

  if(context.diagH0 != NULL) cudaFree(context.diagH0);
  if(context.diagH1 != NULL) cudaFree(context.diagH1);
  if(context.diagH2 != NULL) cudaFree(context.diagH2);
  if(context.diagD0 != NULL) cudaFree(context.diagD0);
  if(context.diagD1 != NULL) cudaFree(context.diagD1);
  if(context.diagD2 != NULL) cudaFree(context.diagD2);
  if(context.diagF0 != NULL) cudaFree(context.diagF0);
  if(context.diagF1 != NULL) cudaFree(context.diagF1);
  if(context.diagF2 != NULL) cudaFree(context.diagF2);

  if(context.diagHc0 != NULL) cudaFree(context.diagHc0);
  if(context.diagHc1 != NULL) cudaFree(context.diagHc1);
  if(context.diagHc2 != NULL) cudaFree(context.diagHc2);
  if(context.diagDc0 != NULL) cudaFree(context.diagDc0);
  if(context.diagDc1 != NULL) cudaFree(context.diagDc1);
  if(context.diagDc2 != NULL) cudaFree(context.diagDc2);
  if(context.diagFc0 != NULL) cudaFree(context.diagFc0);
  if(context.diagFc1 != NULL) cudaFree(context.diagFc1);
  if(context.diagFc2 != NULL) cudaFree(context.diagFc2);

  if(context.rowCountsDevice != NULL) cudaFree(context.rowCountsDevice);
  if(context.rowOffsetsDevice != NULL) cudaFree(context.rowOffsetsDevice);
  if(context.runOffsetsDevice != NULL) cudaFree(context.runOffsetsDevice);

  context.ADevice = newADevice;
  context.BDevice = newBDevice;
  context.HScoreDevice = newHScoreDevice;
  context.HCoordDevice = newHCoordDevice;

  context.diagH0 = newDiagH0;
  context.diagH1 = newDiagH1;
  context.diagH2 = newDiagH2;
  context.diagD0 = newDiagD0;
  context.diagD1 = newDiagD1;
  context.diagD2 = newDiagD2;
  context.diagF0 = newDiagF0;
  context.diagF1 = newDiagF1;
  context.diagF2 = newDiagF2;

  context.diagHc0 = newDiagHc0;
  context.diagHc1 = newDiagHc1;
  context.diagHc2 = newDiagHc2;
  context.diagDc0 = newDiagDc0;
  context.diagDc1 = newDiagDc1;
  context.diagDc2 = newDiagDc2;
  context.diagFc0 = newDiagFc0;
  context.diagFc1 = newDiagFc1;
  context.diagFc2 = newDiagFc2;

  context.rowCountsDevice = newRowCountsDevice;
  context.rowOffsetsDevice = newRowOffsetsDevice;
  context.runOffsetsDevice = newRunOffsetsDevice;

  context.capacityQuery = newCapQuery;
  context.capacityTarget = newCapTarget;
  context.leadingDim = newLeadingDim;
  return true;
}

struct SimScanCudaDiagCellState
{
  int i;
  int j;
  int hScore;
  uint64_t hCoord;
  int dScore;
  uint64_t dCoord;
  int fScore;
  uint64_t fCoord;
};

__device__ __forceinline__ void sim_scan_compute_diag_cell(const char *A,
                                                           const char *B,
                                                           int diag,
                                                           int curStartI,
                                                           int idx,
                                                           int prevStartI,
                                                           int prevLen,
                                                           int ppStartI,
                                                           int ppLen,
                                                           int Q,
                                                           int R,
                                                           int QR,
                                                           const int *prevH,
                                                           const uint64_t *prevHc,
                                                           const int *prevD,
                                                           const uint64_t *prevDc,
                                                           const int *prevF,
                                                           const uint64_t *prevFc,
                                                           const int *ppH,
                                                           const uint64_t *ppHc,
                                                           SimScanCudaDiagCellState &cell)
{
  cell.i = curStartI + idx;
  cell.j = diag - cell.i;

  int leftHScore = 0;
  uint64_t leftHCoord = sim_pack_coord(static_cast<uint32_t>(cell.i), static_cast<uint32_t>(cell.j - 1));
  int leftFScore = -Q;
  uint64_t leftFCoord = leftHCoord;
  if(cell.j > 1)
  {
    const int leftIndex = cell.i - prevStartI;
    if(leftIndex >= 0 && leftIndex < prevLen)
    {
      leftHScore = prevH[leftIndex];
      leftHCoord = prevHc[leftIndex];
      leftFScore = prevF[leftIndex];
      leftFCoord = prevFc[leftIndex];
    }
  }

  int upHScore = 0;
  uint64_t upHCoord = sim_pack_coord(static_cast<uint32_t>(cell.i - 1), static_cast<uint32_t>(cell.j));
  int upDScore = -Q;
  uint64_t upDCoord = upHCoord;
  if(cell.i > 1)
  {
    const int upIndex = cell.i - 1 - prevStartI;
    if(upIndex >= 0 && upIndex < prevLen)
    {
      upHScore = prevH[upIndex];
      upHCoord = prevHc[upIndex];
      upDScore = prevD[upIndex];
      upDCoord = prevDc[upIndex];
    }
  }

  int diagHScore = 0;
  uint64_t diagHCoord = sim_pack_coord(static_cast<uint32_t>(cell.i - 1), static_cast<uint32_t>(cell.j - 1));
  if(cell.i > 1 && cell.j > 1)
  {
    const int diagIndex = cell.i - 1 - ppStartI;
    if(diagIndex >= 0 && diagIndex < ppLen)
    {
      diagHScore = ppH[diagIndex];
      diagHCoord = ppHc[diagIndex];
    }
  }

  cell.fScore = leftFScore - R;
  cell.fCoord = leftFCoord;
  sim_order_state(cell.fScore, cell.fCoord, leftHScore - QR, leftHCoord);

  cell.dScore = upDScore - R;
  cell.dCoord = upDCoord;
  sim_order_state(cell.dScore, cell.dCoord, upHScore - QR, upHCoord);

  const unsigned char a = static_cast<unsigned char>(A[cell.i]);
  const unsigned char b = static_cast<unsigned char>(B[cell.j]);
  int hDiagScore = diagHScore + sim_score_matrix[static_cast<int>(a) * 128 + static_cast<int>(b)];
  uint64_t hDiagCoord = diagHCoord;
  if(hDiagScore <= 0)
  {
    hDiagScore = 0;
    hDiagCoord = sim_pack_coord(static_cast<uint32_t>(cell.i), static_cast<uint32_t>(cell.j));
  }

  cell.hScore = hDiagScore;
  cell.hCoord = hDiagCoord;
  sim_order_state(cell.hScore, cell.hCoord, cell.dScore, cell.dCoord);
  sim_order_state(cell.hScore, cell.hCoord, cell.fScore, cell.fCoord);
  if(cell.hScore <= 0)
  {
    cell.hScore = 0;
    cell.hCoord = sim_pack_coord(static_cast<uint32_t>(cell.i), static_cast<uint32_t>(cell.j));
  }
}

__global__ void sim_scan_diag_kernel(const char *A,
                                     const char *B,
                                     int M,
                                     int N,
                                     int leadingDim,
                                     int diag,
                                     int curStartI,
                                     int curLen,
                                     int prevStartI,
                                     int prevLen,
                                     int ppStartI,
                                     int ppLen,
                                     int Q,
                                     int R,
                                     int QR,
                                     const int *prevH,
                                     const uint64_t *prevHc,
                                     const int *prevD,
                                     const uint64_t *prevDc,
                                     const int *prevF,
                                     const uint64_t *prevFc,
                                     const int *ppH,
                                     const uint64_t *ppHc,
                                     int *curH,
                                     uint64_t *curHc,
                                     int *curD,
                                     uint64_t *curDc,
                                     int *curF,
                                     uint64_t *curFc,
                                     int *HScoreMat,
                                     uint64_t *HCoordMat)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }
  SimScanCudaDiagCellState cell;
  sim_scan_compute_diag_cell(A,
                             B,
                             diag,
                             curStartI,
                             idx,
                             prevStartI,
                             prevLen,
                             ppStartI,
                             ppLen,
                             Q,
                             R,
                             QR,
                             prevH,
                             prevHc,
                             prevD,
                             prevDc,
                             prevF,
                             prevFc,
                             ppH,
                             ppHc,
                             cell);

  curH[idx] = cell.hScore;
  curHc[idx] = cell.hCoord;
  curD[idx] = cell.dScore;
  curDc[idx] = cell.dCoord;
  curF[idx] = cell.fScore;
  curFc[idx] = cell.fCoord;

  const size_t matIndex = static_cast<size_t>(cell.i) * static_cast<size_t>(leadingDim) +
                          static_cast<size_t>(cell.j);
  HScoreMat[matIndex] = cell.hScore;
  HCoordMat[matIndex] = cell.hCoord;
}

__device__ __forceinline__ void sim_scan_write_proposal_summary(int row,
                                                                const SimScanCudaInitialRunSummary &summary,
                                                                const int *rowOffsets,
                                                                int *rowCursors,
                                                                SimScanCudaInitialRunSummary *summaries)
{
  const int writeIndex = rowOffsets[row] + rowCursors[row];
  summaries[writeIndex] = summary;
  rowCursors[row] += 1;
}

__device__ __forceinline__ size_t sim_scan_online_hash_index(uint64_t startCoord,size_t capacity)
{
  uint64_t mixed = startCoord;
  mixed ^= mixed >> 33;
  mixed *= 0xff51afd7ed558ccdULL;
  mixed ^= mixed >> 33;
  return static_cast<size_t>(mixed) & (capacity - 1);
}

__device__ __forceinline__ bool sim_scan_online_hash_merge_summary(const SimScanCudaInitialRunSummary &summary,
                                                                   uint64_t *keys,
                                                                   int *flags,
                                                                   SimScanCudaCandidateState *states,
                                                                   size_t capacity,
                                                                   int *uniqueCount,
                                                                   int *overflowFlag)
{
  if(capacity == 0)
  {
    atomicExch(overflowFlag,1);
    return false;
  }

  size_t slot = sim_scan_online_hash_index(summary.startCoord,capacity);
  for(size_t probe = 0; probe < capacity; ++probe)
  {
    while(true)
    {
      const int flag = atomicAdd(flags + slot,0);
      if(flag == sim_scan_online_hash_flag_initializing)
      {
        continue;
      }
      if(flag == sim_scan_online_hash_flag_empty)
      {
        if(atomicCAS(flags + slot,
                     sim_scan_online_hash_flag_empty,
                     sim_scan_online_hash_flag_initializing) == sim_scan_online_hash_flag_empty)
        {
          keys[slot] = summary.startCoord;
          initSimScanCudaCandidateStateFromInitialRunSummary(summary,states[slot]);
          __threadfence();
          atomicAdd(uniqueCount,1);
          atomicExch(flags + slot,sim_scan_online_hash_flag_ready);
          return true;
        }
        continue;
      }

      const uint64_t slotKey = keys[slot];
      if(slotKey != summary.startCoord)
      {
        break;
      }
      if(flag == sim_scan_online_hash_flag_locked)
      {
        continue;
      }
      if(atomicCAS(flags + slot,
                   sim_scan_online_hash_flag_ready,
                   sim_scan_online_hash_flag_locked) == sim_scan_online_hash_flag_ready)
      {
        updateSimScanCudaCandidateStateFromInitialRunSummary(summary,states[slot]);
        __threadfence();
        atomicExch(flags + slot,sim_scan_online_hash_flag_ready);
        return true;
      }
    }
    slot = (slot + 1) & (capacity - 1);
  }

  atomicExch(overflowFlag,1);
  return false;
}

__global__ void sim_scan_diag_proposal_count_kernel(const char *A,
                                                    const char *B,
                                                    int M,
                                                    int N,
                                                    int diag,
                                                    int curStartI,
                                                    int curLen,
                                                    int prevStartI,
                                                    int prevLen,
                                                    int ppStartI,
                                                    int ppLen,
                                                    int Q,
                                                    int R,
                                                    int QR,
                                                    const int *prevH,
                                                    const uint64_t *prevHc,
                                                    const int *prevD,
                                                    const uint64_t *prevDc,
                                                    const int *prevF,
                                                    const uint64_t *prevFc,
                                                    const int *ppH,
                                                    const uint64_t *ppHc,
                                                    int *curH,
                                                    uint64_t *curHc,
                                                    int *curD,
                                                    uint64_t *curDc,
                                                    int *curF,
                                                    uint64_t *curFc,
                                                    int eventScoreFloor,
                                                    SimScanCudaProposalRowSummaryState *rowStates,
                                                    int *runCounts,
                                                    int *eventCounts)
{
  (void)M;
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }

  SimScanCudaDiagCellState cell;
  sim_scan_compute_diag_cell(A,
                             B,
                             diag,
                             curStartI,
                             idx,
                             prevStartI,
                             prevLen,
                             ppStartI,
                             ppLen,
                             Q,
                             R,
                             QR,
                             prevH,
                             prevHc,
                             prevD,
                             prevDc,
                             prevF,
                             prevFc,
                             ppH,
                             ppHc,
                             cell);

  curH[idx] = cell.hScore;
  curHc[idx] = cell.hCoord;
  curD[idx] = cell.dScore;
  curDc[idx] = cell.dCoord;
  curF[idx] = cell.fScore;
  curFc[idx] = cell.fCoord;

  if(cell.hScore > eventScoreFloor)
  {
    const SimScanCudaRowEvent event = {
      cell.hScore,
      cell.hCoord,
      static_cast<uint32_t>(cell.i),
      static_cast<uint32_t>(cell.j)
    };
    if(simScanCudaProposalRowSummaryPushEvent(event,rowStates[cell.i],NULL))
    {
      runCounts[cell.i] += 1;
    }
    eventCounts[cell.i] += 1;
  }
  if(cell.j == N && simScanCudaProposalRowSummaryFlush(rowStates[cell.i],NULL))
  {
    runCounts[cell.i] += 1;
  }
}

__global__ void sim_scan_diag_proposal_write_kernel(const char *A,
                                                    const char *B,
                                                    int M,
                                                    int N,
                                                    int diag,
                                                    int curStartI,
                                                    int curLen,
                                                    int prevStartI,
                                                    int prevLen,
                                                    int ppStartI,
                                                    int ppLen,
                                                    int Q,
                                                    int R,
                                                    int QR,
                                                    const int *prevH,
                                                    const uint64_t *prevHc,
                                                    const int *prevD,
                                                    const uint64_t *prevDc,
                                                    const int *prevF,
                                                    const uint64_t *prevFc,
                                                    const int *ppH,
                                                    const uint64_t *ppHc,
                                                    int *curH,
                                                    uint64_t *curHc,
                                                    int *curD,
                                                    uint64_t *curDc,
                                                    int *curF,
                                                    uint64_t *curFc,
                                                    int eventScoreFloor,
                                                    SimScanCudaProposalRowSummaryState *rowStates,
                                                    const int *rowOffsets,
                                                    int *rowCursors,
                                                    SimScanCudaInitialRunSummary *summaries)
{
  (void)M;
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }

  SimScanCudaDiagCellState cell;
  sim_scan_compute_diag_cell(A,
                             B,
                             diag,
                             curStartI,
                             idx,
                             prevStartI,
                             prevLen,
                             ppStartI,
                             ppLen,
                             Q,
                             R,
                             QR,
                             prevH,
                             prevHc,
                             prevD,
                             prevDc,
                             prevF,
                             prevFc,
                             ppH,
                             ppHc,
                             cell);

  curH[idx] = cell.hScore;
  curHc[idx] = cell.hCoord;
  curD[idx] = cell.dScore;
  curDc[idx] = cell.dCoord;
  curF[idx] = cell.fScore;
  curFc[idx] = cell.fCoord;

  if(cell.hScore > eventScoreFloor)
  {
    const SimScanCudaRowEvent event = {
      cell.hScore,
      cell.hCoord,
      static_cast<uint32_t>(cell.i),
      static_cast<uint32_t>(cell.j)
    };
    SimScanCudaInitialRunSummary flushedSummary;
    if(simScanCudaProposalRowSummaryPushEvent(event,rowStates[cell.i],&flushedSummary))
    {
      sim_scan_write_proposal_summary(cell.i,flushedSummary,rowOffsets,rowCursors,summaries);
    }
  }
  if(cell.j == N)
  {
    SimScanCudaInitialRunSummary flushedSummary;
    if(simScanCudaProposalRowSummaryFlush(rowStates[cell.i],&flushedSummary))
    {
      sim_scan_write_proposal_summary(cell.i,flushedSummary,rowOffsets,rowCursors,summaries);
    }
  }
}

__global__ void sim_scan_diag_proposal_online_kernel(const char *A,
                                                     const char *B,
                                                     int N,
                                                     int diag,
                                                     int curStartI,
                                                     int curLen,
                                                     int prevStartI,
                                                     int prevLen,
                                                     int ppStartI,
                                                     int ppLen,
                                                     int Q,
                                                     int R,
                                                     int QR,
                                                     const int *prevH,
                                                     const uint64_t *prevHc,
                                                     const int *prevD,
                                                     const uint64_t *prevDc,
                                                     const int *prevF,
                                                     const uint64_t *prevFc,
                                                     const int *ppH,
                                                     const uint64_t *ppHc,
                                                     int *curH,
                                                     uint64_t *curHc,
                                                     int *curD,
                                                     uint64_t *curDc,
                                                     int *curF,
                                                     uint64_t *curFc,
                                                     int eventScoreFloor,
                                                     SimScanCudaProposalRowSummaryState *rowStates,
                                                     uint64_t *hashKeys,
                                                     int *hashFlags,
                                                     SimScanCudaCandidateState *hashStates,
                                                     size_t hashCapacity,
                                                     int *eventCount,
                                                     int *runSummaryCount,
                                                     int *uniqueCount,
                                                     int *overflowFlag)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }

  SimScanCudaDiagCellState cell;
  sim_scan_compute_diag_cell(A,
                             B,
                             diag,
                             curStartI,
                             idx,
                             prevStartI,
                             prevLen,
                             ppStartI,
                             ppLen,
                             Q,
                             R,
                             QR,
                             prevH,
                             prevHc,
                             prevD,
                             prevDc,
                             prevF,
                             prevFc,
                             ppH,
                             ppHc,
                             cell);

  curH[idx] = cell.hScore;
  curHc[idx] = cell.hCoord;
  curD[idx] = cell.dScore;
  curDc[idx] = cell.dCoord;
  curF[idx] = cell.fScore;
  curFc[idx] = cell.fCoord;

  if(atomicAdd(overflowFlag,0) != 0)
  {
    return;
  }

  if(cell.hScore > eventScoreFloor)
  {
    atomicAdd(eventCount,1);
    const SimScanCudaRowEvent event = {
      cell.hScore,
      cell.hCoord,
      static_cast<uint32_t>(cell.i),
      static_cast<uint32_t>(cell.j)
    };
    SimScanCudaInitialRunSummary flushedSummary;
    if(simScanCudaProposalRowSummaryPushEvent(event,rowStates[cell.i],&flushedSummary))
    {
      atomicAdd(runSummaryCount,1);
      sim_scan_online_hash_merge_summary(flushedSummary,
                                         hashKeys,
                                         hashFlags,
                                         hashStates,
                                         hashCapacity,
                                         uniqueCount,
                                         overflowFlag);
    }
  }
  if(cell.j == N)
  {
    SimScanCudaInitialRunSummary flushedSummary;
    if(simScanCudaProposalRowSummaryFlush(rowStates[cell.i],&flushedSummary))
    {
      atomicAdd(runSummaryCount,1);
      sim_scan_online_hash_merge_summary(flushedSummary,
                                         hashKeys,
                                         hashFlags,
                                         hashStates,
                                         hashCapacity,
                                         uniqueCount,
                                         overflowFlag);
    }
  }
}

__global__ void sim_scan_compact_online_candidate_states_kernel(const int *hashFlags,
                                                                const SimScanCudaCandidateState *hashStates,
                                                                size_t hashCapacity,
                                                                SimScanCudaCandidateState *outputStates,
                                                                int *outputCount)
{
  const size_t slot = static_cast<size_t>(blockIdx.x) * static_cast<size_t>(blockDim.x) +
                      static_cast<size_t>(threadIdx.x);
  if(slot >= hashCapacity)
  {
    return;
  }
  if(hashFlags[slot] != sim_scan_online_hash_flag_ready)
  {
    return;
  }
  const int outputIndex = atomicAdd(outputCount,1);
  outputStates[static_cast<size_t>(outputIndex)] = hashStates[slot];
}

__global__ void sim_scan_diag_true_batch_kernel(const char *A,
                                                const char *packedB,
                                                int batchSize,
                                                int targetStride,
                                                int M,
                                                int N,
                                                int leadingDim,
                                                int matrixStride,
                                                int diag,
                                                int curStartI,
                                                int curLen,
                                                int prevStartI,
                                                int prevLen,
                                                int ppStartI,
                                                int ppLen,
                                                int diagCapacity,
                                                int Q,
                                                int R,
                                                int QR,
                                                const int *ppH,
                                                const uint64_t *ppHc,
                                                const int *prevH,
                                                const uint64_t *prevHc,
                                                const int *prevD,
                                                const uint64_t *prevDc,
                                                const int *prevF,
                                                const uint64_t *prevFc,
                                                int *curH,
                                                uint64_t *curHc,
                                                int *curD,
                                                uint64_t *curDc,
                                                int *curF,
                                                uint64_t *curFc,
                                                int *HScoreMat,
                                                uint64_t *HCoordMat)
{
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(batchIndex >= batchSize)
  {
    return;
  }
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }

  const int i = curStartI + idx;
  const int j = diag - i;
  const char *B = packedB + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride);
  const size_t diagBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(diagCapacity);
  const size_t matrixBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride);

  int leftHScore = 0;
  uint64_t leftHCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j - 1));
  int leftFScore = -Q;
  uint64_t leftFCoord = leftHCoord;
  if(j > 1)
  {
    const int leftIndex = i - prevStartI;
    if(leftIndex >= 0 && leftIndex < prevLen)
    {
      leftHScore = prevH[diagBase + static_cast<size_t>(leftIndex)];
      leftHCoord = prevHc[diagBase + static_cast<size_t>(leftIndex)];
      leftFScore = prevF[diagBase + static_cast<size_t>(leftIndex)];
      leftFCoord = prevFc[diagBase + static_cast<size_t>(leftIndex)];
    }
  }

  int upHScore = 0;
  uint64_t upHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j));
  int upDScore = -Q;
  uint64_t upDCoord = upHCoord;
  if(i > 1)
  {
    const int upIndex = (i - 1) - prevStartI;
    if(upIndex >= 0 && upIndex < prevLen)
    {
      upHScore = prevH[diagBase + static_cast<size_t>(upIndex)];
      upHCoord = prevHc[diagBase + static_cast<size_t>(upIndex)];
      upDScore = prevD[diagBase + static_cast<size_t>(upIndex)];
      upDCoord = prevDc[diagBase + static_cast<size_t>(upIndex)];
    }
  }

  int diagHScore = 0;
  uint64_t diagHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j - 1));
  if(i > 1 && j > 1)
  {
    const int diagIndex = (i - 1) - ppStartI;
    if(diagIndex >= 0 && diagIndex < ppLen)
    {
      diagHScore = ppH[diagBase + static_cast<size_t>(diagIndex)];
      diagHCoord = ppHc[diagBase + static_cast<size_t>(diagIndex)];
    }
  }

  int fScore = leftFScore - R;
  uint64_t fCoord = leftFCoord;
  sim_order_state(fScore, fCoord, leftHScore - QR, leftHCoord);

  int dScore = upDScore - R;
  uint64_t dCoord = upDCoord;
  sim_order_state(dScore, dCoord, upHScore - QR, upHCoord);

  const unsigned char a = static_cast<unsigned char>(A[i]);
  const unsigned char b = static_cast<unsigned char>(B[j]);
  int hDiagScore = diagHScore + sim_score_matrix[static_cast<int>(a) * 128 + static_cast<int>(b)];
  uint64_t hDiagCoord = diagHCoord;
  if(hDiagScore <= 0)
  {
    hDiagScore = 0;
    hDiagCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  }

  int hScore = hDiagScore;
  uint64_t hCoord = hDiagCoord;
  sim_order_state(hScore, hCoord, dScore, dCoord);
  sim_order_state(hScore, hCoord, fScore, fCoord);
  if(hScore <= 0)
  {
    hScore = 0;
    hCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  }

  curH[diagBase + static_cast<size_t>(idx)] = hScore;
  curHc[diagBase + static_cast<size_t>(idx)] = hCoord;
  curD[diagBase + static_cast<size_t>(idx)] = dScore;
  curDc[diagBase + static_cast<size_t>(idx)] = dCoord;
  curF[diagBase + static_cast<size_t>(idx)] = fScore;
  curFc[diagBase + static_cast<size_t>(idx)] = fCoord;

  const size_t matIndex = matrixBase + static_cast<size_t>(i) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
  HScoreMat[matIndex] = hScore;
  HCoordMat[matIndex] = hCoord;
}

__global__ void sim_scan_diag_region_kernel(const char *A,
                                            const char *B,
                                            int rowStart,
                                            int colStart,
                                            int M,
                                            int N,
                                            int leadingDim,
                                            int diag,
                                            int curStartI,
                                            int curLen,
                                            int prevStartI,
                                            int prevLen,
                                            int ppStartI,
                                            int ppLen,
                                            int Q,
                                            int R,
                                            int QR,
                                            const int *prevH,
                                            const uint64_t *prevHc,
                                            const int *prevD,
                                            const uint64_t *prevDc,
                                            const int *prevF,
                                            const uint64_t *prevFc,
                                            const int *ppH,
                                            const uint64_t *ppHc,
                                            int *curH,
                                            uint64_t *curHc,
                                            int *curD,
                                            uint64_t *curDc,
                                            int *curF,
                                            uint64_t *curFc,
                                            const uint64_t *blockedWords,
                                            int blockedWordStart,
                                            int blockedWordCount,
                                            int *HScoreMat,
                                            uint64_t *HCoordMat)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }
  const int i = curStartI + idx;
  const int j = diag - i;

  (void)M;
  (void)N;

  int leftHScore = 0;
  uint64_t leftHCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j - 1));
  int leftFScore = -Q;
  uint64_t leftFCoord = leftHCoord;
  if(j > colStart)
  {
    const int leftI = i;
    const int leftIndex = leftI - prevStartI;
    if(leftIndex >= 0 && leftIndex < prevLen)
    {
      leftHScore = prevH[leftIndex];
      leftHCoord = prevHc[leftIndex];
      leftFScore = prevF[leftIndex];
      leftFCoord = prevFc[leftIndex];
    }
  }

  int upHScore = 0;
  uint64_t upHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j));
  int upDScore = -Q;
  uint64_t upDCoord = upHCoord;
  if(i > rowStart)
  {
    const int upI = i - 1;
    const int upIndex = upI - prevStartI;
    if(upIndex >= 0 && upIndex < prevLen)
    {
      upHScore = prevH[upIndex];
      upHCoord = prevHc[upIndex];
      upDScore = prevD[upIndex];
      upDCoord = prevDc[upIndex];
    }
  }

  int diagHScore = 0;
  uint64_t diagHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j - 1));
  if(i > rowStart && j > colStart)
  {
    const int diagI = i - 1;
    const int diagIndex = diagI - ppStartI;
    if(diagIndex >= 0 && diagIndex < ppLen)
    {
      diagHScore = ppH[diagIndex];
      diagHCoord = ppHc[diagIndex];
    }
  }

  int fScore = leftFScore - R;
  uint64_t fCoord = leftFCoord;
  const int fOpenScore = leftHScore - QR;
  const uint64_t fOpenCoord = leftHCoord;
  sim_order_state(fScore, fCoord, fOpenScore, fOpenCoord);

  int dScore = upDScore - R;
  uint64_t dCoord = upDCoord;
  const int dOpenScore = upHScore - QR;
  const uint64_t dOpenCoord = upHCoord;
  sim_order_state(dScore, dCoord, dOpenScore, dOpenCoord);

  bool diagAvailable = true;
  if(blockedWords != NULL && blockedWordCount > 0)
  {
    const int localRow = i - rowStart;
    const int wordIndex = (j >> 6) - blockedWordStart;
    if(localRow >= 0 && wordIndex >= 0 && wordIndex < blockedWordCount)
    {
      const size_t index = static_cast<size_t>(localRow) * static_cast<size_t>(blockedWordCount) + static_cast<size_t>(wordIndex);
      const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<unsigned int>(j) & 63u);
      diagAvailable = (blockedWords[index] & mask) == 0;
    }
  }

  int hDiagScore = 0;
  uint64_t hDiagCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  if(diagAvailable)
  {
    const unsigned char a = static_cast<unsigned char>(A[i]);
    const unsigned char b = static_cast<unsigned char>(B[j]);
    hDiagScore = diagHScore + sim_score_matrix[static_cast<int>(a) * 128 + static_cast<int>(b)];
    hDiagCoord = diagHCoord;
    if(hDiagScore <= 0)
    {
      hDiagScore = 0;
      hDiagCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
    }
  }

  int hScore = hDiagScore;
  uint64_t hCoord = hDiagCoord;
  sim_order_state(hScore, hCoord, dScore, dCoord);
  sim_order_state(hScore, hCoord, fScore, fCoord);
  if(hScore <= 0)
  {
    hScore = 0;
    hCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  }

  curH[idx] = hScore;
  curHc[idx] = hCoord;
  curD[idx] = dScore;
  curDc[idx] = dCoord;
  curF[idx] = fScore;
  curFc[idx] = fCoord;

  const size_t matIndex = static_cast<size_t>(i) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
  HScoreMat[matIndex] = hScore;
  HCoordMat[matIndex] = hCoord;
}

__global__ void sim_scan_diag_region_true_batch_kernel(const char *A,
                                                       const char *B,
                                                       int leadingDim,
                                                       int matrixStride,
                                                       int diag,
                                                       int curStartI,
                                                       int curLen,
                                                       int prevStartI,
                                                       int prevLen,
                                                       int ppStartI,
                                                       int ppLen,
                                                       int diagCapacity,
                                                       int Q,
                                                       int R,
                                                       int QR,
                                                       const int *rowStarts,
                                                       const int *colStarts,
                                                       const int *blockedBases,
                                                       const int *blockedStarts,
                                                       const int *blockedCounts,
                                                       const uint64_t *blockedWords,
                                                       const int *ppH,
                                                       const uint64_t *ppHc,
                                                       const int *prevH,
                                                       const uint64_t *prevHc,
                                                       const int *prevD,
                                                       const uint64_t *prevDc,
                                                       const int *prevF,
                                                       const uint64_t *prevFc,
                                                       int *curH,
                                                       uint64_t *curHc,
                                                       int *curD,
                                                       uint64_t *curDc,
                                                       int *curF,
                                                       uint64_t *curFc,
                                                       int *HScoreMat,
                                                       uint64_t *HCoordMat)
{
  const int batchIndex = static_cast<int>(blockIdx.y);
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= curLen)
  {
    return;
  }

  const int rowStart = rowStarts[batchIndex];
  const int colStart = colStarts[batchIndex];
  const int localI = curStartI + idx;
  const int localJ = diag - localI;
  const int i = rowStart + localI - 1;
  const int j = colStart + localJ - 1;
  const size_t diagBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(diagCapacity);
  const size_t matrixBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride);

  int leftHScore = 0;
  uint64_t leftHCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j - 1));
  int leftFScore = -Q;
  uint64_t leftFCoord = leftHCoord;
  if(localJ > 1)
  {
    const int leftIndex = localI - prevStartI;
    if(leftIndex >= 0 && leftIndex < prevLen)
    {
      leftHScore = prevH[diagBase + static_cast<size_t>(leftIndex)];
      leftHCoord = prevHc[diagBase + static_cast<size_t>(leftIndex)];
      leftFScore = prevF[diagBase + static_cast<size_t>(leftIndex)];
      leftFCoord = prevFc[diagBase + static_cast<size_t>(leftIndex)];
    }
  }

  int upHScore = 0;
  uint64_t upHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j));
  int upDScore = -Q;
  uint64_t upDCoord = upHCoord;
  if(localI > 1)
  {
    const int upIndex = (localI - 1) - prevStartI;
    if(upIndex >= 0 && upIndex < prevLen)
    {
      upHScore = prevH[diagBase + static_cast<size_t>(upIndex)];
      upHCoord = prevHc[diagBase + static_cast<size_t>(upIndex)];
      upDScore = prevD[diagBase + static_cast<size_t>(upIndex)];
      upDCoord = prevDc[diagBase + static_cast<size_t>(upIndex)];
    }
  }

  int diagHScore = 0;
  uint64_t diagHCoord = sim_pack_coord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j - 1));
  if(localI > 1 && localJ > 1)
  {
    const int diagIndex = (localI - 1) - ppStartI;
    if(diagIndex >= 0 && diagIndex < ppLen)
    {
      diagHScore = ppH[diagBase + static_cast<size_t>(diagIndex)];
      diagHCoord = ppHc[diagBase + static_cast<size_t>(diagIndex)];
    }
  }

  int fScore = leftFScore - R;
  uint64_t fCoord = leftFCoord;
  sim_order_state(fScore, fCoord, leftHScore - QR, leftHCoord);

  int dScore = upDScore - R;
  uint64_t dCoord = upDCoord;
  sim_order_state(dScore, dCoord, upHScore - QR, upHCoord);

  bool diagAvailable = true;
  const int blockedWordCount = blockedCounts[batchIndex];
  if(blockedWords != NULL && blockedWordCount > 0)
  {
    const int blockedWordStart = blockedStarts[batchIndex];
    const int wordIndex = (j >> 6) - blockedWordStart;
    if(wordIndex >= 0 && wordIndex < blockedWordCount)
    {
      const size_t blockedBase = static_cast<size_t>(blockedBases[batchIndex]);
      const size_t blockedIndex =
        blockedBase + static_cast<size_t>(localI - 1) * static_cast<size_t>(blockedWordCount) +
        static_cast<size_t>(wordIndex);
      const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<unsigned int>(j) & 63u);
      diagAvailable = (blockedWords[blockedIndex] & mask) == 0;
    }
  }

  int hDiagScore = 0;
  uint64_t hDiagCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  if(diagAvailable)
  {
    const unsigned char a = static_cast<unsigned char>(A[i]);
    const unsigned char b = static_cast<unsigned char>(B[j]);
    hDiagScore = diagHScore + sim_score_matrix[static_cast<int>(a) * 128 + static_cast<int>(b)];
    hDiagCoord = diagHCoord;
    if(hDiagScore <= 0)
    {
      hDiagScore = 0;
      hDiagCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
    }
  }

  int hScore = hDiagScore;
  uint64_t hCoord = hDiagCoord;
  sim_order_state(hScore, hCoord, dScore, dCoord);
  sim_order_state(hScore, hCoord, fScore, fCoord);
  if(hScore <= 0)
  {
    hScore = 0;
    hCoord = sim_pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
  }

  curH[diagBase + static_cast<size_t>(idx)] = hScore;
  curHc[diagBase + static_cast<size_t>(idx)] = hCoord;
  curD[diagBase + static_cast<size_t>(idx)] = dScore;
  curDc[diagBase + static_cast<size_t>(idx)] = dCoord;
  curF[diagBase + static_cast<size_t>(idx)] = fScore;
  curFc[diagBase + static_cast<size_t>(idx)] = fCoord;

  const size_t matIndex = matrixBase +
                          static_cast<size_t>(localI) * static_cast<size_t>(leadingDim) +
                          static_cast<size_t>(localJ);
  HScoreMat[matIndex] = hScore;
  HCoordMat[matIndex] = hCoord;
}

__global__ void sim_scan_count_row_events_kernel(const int *HScoreMat,int leadingDim,int M,int N,int eventScoreFloor,int *rowCounts)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  if(row > M)
  {
    return;
  }
  int localCount = 0;
  for(int j = static_cast<int>(threadIdx.x + 1); j <= N; j += static_cast<int>(blockDim.x))
  {
    const size_t matIndex = static_cast<size_t>(row) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
    localCount += (HScoreMat[matIndex] > eventScoreFloor) ? 1 : 0;
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    rowCounts[row] = shared[0];
    if(row == 1)
    {
      rowCounts[0] = 0;
    }
  }
}

__global__ void sim_scan_count_row_events_region_kernel(const int *HScoreMat,
                                                        int leadingDim,
                                                        int rowStart,
                                                        int rowCount,
                                                        int colStart,
                                                        int colEnd,
                                                        int eventScoreFloor,
                                                        int *rowCounts)
{
  const int localRow = static_cast<int>(blockIdx.x);
  if(localRow >= rowCount)
  {
    return;
  }
  const int row = rowStart + localRow;
  int localCount = 0;
  for(int j = static_cast<int>(threadIdx.x + colStart); j <= colEnd; j += static_cast<int>(blockDim.x))
  {
    const size_t matIndex = static_cast<size_t>(row) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
    localCount += (HScoreMat[matIndex] > eventScoreFloor) ? 1 : 0;
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    rowCounts[localRow] = shared[0];
  }
}

__global__ void sim_scan_compact_row_events_kernel(const int *HScoreMat,
                                                   const uint64_t *HCoordMat,
                                                   int leadingDim,
                                                   int M,
                                                   int N,
                                                   int eventScoreFloor,
                                                   const int *rowOffsets,
                                                   SimScanCudaRowEvent *events)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  if(row > M)
  {
    return;
  }

  const int tid = static_cast<int>(threadIdx.x);
  const int warp = tid >> 5;
  const int lane = tid & 31;
  const int warpsPerBlock = static_cast<int>(blockDim.x) >> 5;

  __shared__ int warpCounts[8];
  __shared__ int warpBases[8];
  __shared__ int chunkTotal;
  __shared__ int rowCursor;

  if(tid == 0)
  {
    rowCursor = 0;
  }
  __syncthreads();

  const int baseOffset = rowOffsets[row];

  for(int chunkStart = 1; chunkStart <= N; chunkStart += static_cast<int>(blockDim.x))
  {
    const int j = chunkStart + tid;
    int flag = 0;
    int score = 0;
    uint64_t coord = 0;
    if(j <= N)
    {
      const size_t matIndex = static_cast<size_t>(row) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
      score = HScoreMat[matIndex];
      coord = HCoordMat[matIndex];
      flag = (score > eventScoreFloor) ? 1 : 0;
    }

    const unsigned int ballot = __ballot_sync(0xffffffffu, flag != 0);
    const int warpCount = __popc(ballot);
    if(lane == 0)
    {
      warpCounts[warp] = warpCount;
    }
    __syncthreads();

    if(warp == 0 && lane == 0)
    {
      int sum = 0;
      for(int w = 0; w < warpsPerBlock; ++w)
      {
        warpBases[w] = sum;
        sum += warpCounts[w];
      }
      chunkTotal = sum;
    }
    __syncthreads();

    const int prefixInWarp = __popc(ballot & ((lane == 0) ? 0u : ((1u << lane) - 1u)));
    const int prefix = warpBases[warp] + prefixInWarp;
    if(flag)
    {
      SimScanCudaRowEvent event;
      event.score = score;
      event.startCoord = coord;
      event.endI = static_cast<uint32_t>(row);
      event.endJ = static_cast<uint32_t>(j);
      events[static_cast<size_t>(baseOffset + rowCursor + prefix)] = event;
    }
    __syncthreads();
    if(tid == 0)
    {
      rowCursor += chunkTotal;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_count_row_events_true_batch_kernel(const int *HScoreMat,
                                                            int leadingDim,
                                                            int matrixStride,
                                                            int M,
                                                            int N,
                                                            const int *eventScoreFloors,
                                                            int rowCountStride,
                                                            int *rowCounts)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(row > M)
  {
    return;
  }

  const int eventScoreFloor = eventScoreFloors[batchIndex];
  const size_t matrixBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride);
  int localCount = 0;
  for(int j = static_cast<int>(threadIdx.x + 1); j <= N; j += static_cast<int>(blockDim.x))
  {
    const size_t matIndex = matrixBase + static_cast<size_t>(row) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
    localCount += (HScoreMat[matIndex] > eventScoreFloor) ? 1 : 0;
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    const int rowBase = batchIndex * rowCountStride;
    rowCounts[rowBase + row] = shared[0];
    if(row == 1)
    {
      rowCounts[rowBase] = 0;
    }
  }
}

__global__ void sim_scan_prefix_sum_true_batch_kernel(const int *rowCounts,
                                                      int rowCount,
                                                      int rowCountStride,
                                                      int rowOffsetStride,
                                                      int *rowOffsets,
                                                      int *totals)
{
  const int batchIndex = static_cast<int>(blockIdx.x);
  if(threadIdx.x != 0)
  {
    return;
  }

  const int rowBase = batchIndex * rowCountStride;
  const int offsetBase = batchIndex * rowOffsetStride;
  int total = 0;
  for(int i = 0; i < rowCount; ++i)
  {
    rowOffsets[offsetBase + i] = total;
    total += rowCounts[rowBase + i];
  }
  rowOffsets[offsetBase + rowCount] = total;
  totals[batchIndex] = total;
}

__global__ void sim_scan_compact_row_events_region_kernel(const int *HScoreMat,
                                                          const uint64_t *HCoordMat,
                                                          int leadingDim,
                                                          int rowStart,
                                                          int rowCount,
                                                          int colStart,
                                                          int colEnd,
                                                          int eventScoreFloor,
                                                          const int *rowOffsets,
                                                          SimScanCudaRowEvent *events)
{
  const int localRow = static_cast<int>(blockIdx.x);
  if(localRow >= rowCount)
  {
    return;
  }
  const int row = rowStart + localRow;

  const int tid = static_cast<int>(threadIdx.x);
  const int warp = tid >> 5;
  const int lane = tid & 31;
  const int warpsPerBlock = static_cast<int>(blockDim.x) >> 5;

  __shared__ int warpCounts[8];
  __shared__ int warpBases[8];
  __shared__ int chunkTotal;
  __shared__ int rowCursor;

  if(tid == 0)
  {
    rowCursor = 0;
  }
  __syncthreads();

  const int baseOffset = rowOffsets[localRow];

  for(int chunkStart = colStart; chunkStart <= colEnd; chunkStart += static_cast<int>(blockDim.x))
  {
    const int j = chunkStart + tid;
    int flag = 0;
    int score = 0;
    uint64_t coord = 0;
    if(j <= colEnd)
    {
      const size_t matIndex = static_cast<size_t>(row) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
      score = HScoreMat[matIndex];
      coord = HCoordMat[matIndex];
      flag = (score > eventScoreFloor) ? 1 : 0;
    }

    const unsigned int ballot = __ballot_sync(0xffffffffu, flag != 0);
    const int warpCount = __popc(ballot);
    if(lane == 0)
    {
      warpCounts[warp] = warpCount;
    }
    __syncthreads();

    if(warp == 0 && lane == 0)
    {
      int sum = 0;
      for(int w = 0; w < warpsPerBlock; ++w)
      {
        warpBases[w] = sum;
        sum += warpCounts[w];
      }
      chunkTotal = sum;
    }
    __syncthreads();

    const int prefixInWarp = __popc(ballot & ((lane == 0) ? 0u : ((1u << lane) - 1u)));
    const int prefix = warpBases[warp] + prefixInWarp;
    if(flag)
    {
      SimScanCudaRowEvent event;
      event.score = score;
      event.startCoord = coord;
      event.endI = static_cast<uint32_t>(row);
      event.endJ = static_cast<uint32_t>(j);
      events[static_cast<size_t>(baseOffset + rowCursor + prefix)] = event;
    }
    __syncthreads();
    if(tid == 0)
    {
      rowCursor += chunkTotal;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_count_initial_run_summaries_kernel(const SimScanCudaRowEvent *events,
                                                            const int *rowOffsets,
                                                            int M,
                                                            int *runCounts)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  if(row > M)
  {
    return;
  }

  const int startIndex = rowOffsets[row];
  const int endIndex = rowOffsets[row + 1];
  int localCount = 0;
  for(int eventIndex = startIndex + static_cast<int>(threadIdx.x);
      eventIndex < endIndex;
      eventIndex += static_cast<int>(blockDim.x))
  {
    if(simScanCudaInitialRunStartsAt(events,startIndex,eventIndex))
    {
      ++localCount;
    }
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    runCounts[row] = shared[0];
    if(row == 1)
    {
      runCounts[0] = 0;
    }
  }
}

__global__ void sim_scan_compact_initial_run_summaries_kernel(const SimScanCudaRowEvent *events,
                                                              const int *rowOffsets,
                                                              int M,
                                                              const int *runOffsets,
                                                              SimScanCudaInitialRunSummary *summaries)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  if(row > M)
  {
    return;
  }

  const int startIndex = rowOffsets[row];
  const int endIndex = rowOffsets[row + 1];
  if(startIndex >= endIndex)
  {
    return;
  }

  const int tid = static_cast<int>(threadIdx.x);
  extern __shared__ int shared[];
  __shared__ int outputCursor;
  __shared__ int chunkOutputBase;

  if(tid == 0)
  {
    outputCursor = runOffsets[row];
  }
  __syncthreads();

  for(int chunkStart = startIndex; chunkStart < endIndex; chunkStart += static_cast<int>(blockDim.x))
  {
    const int eventIndex = chunkStart + tid;
    const int isRunStart =
      (eventIndex < endIndex && simScanCudaInitialRunStartsAt(events,startIndex,eventIndex)) ? 1 : 0;
    shared[tid] = isRunStart;
    __syncthreads();

    if(tid == 0)
    {
      int prefix = 0;
      chunkOutputBase = outputCursor;
      for(int i = 0; i < static_cast<int>(blockDim.x); ++i)
      {
        const int flag = shared[i];
        shared[i] = prefix;
        prefix += flag;
      }
      outputCursor += prefix;
    }
    __syncthreads();

    if(isRunStart != 0)
    {
      SimScanCudaInitialRunSummary summary;
      initSimCudaInitialRunSummary(events[eventIndex],summary);
      for(int runEventIndex = eventIndex + 1; runEventIndex < endIndex; ++runEventIndex)
      {
        const SimScanCudaRowEvent &event = events[runEventIndex];
        if(event.startCoord != summary.startCoord)
        {
          break;
        }
        updateSimCudaInitialRunSummary(event,summary);
      }
      summaries[chunkOutputBase + shared[tid]] = summary;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_count_initial_run_summaries_direct_true_batch_kernel(const int *HScoreMat,
                                                                              const uint64_t *HCoordMat,
                                                                              int leadingDim,
                                                                              int matrixStride,
                                                                              int M,
                                                                              int N,
                                                                              const int *eventScoreFloors,
                                                                              int rowCountStride,
                                                                              int *runCounts)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(row > M)
  {
    return;
  }

  const int eventScoreFloor = eventScoreFloors[batchIndex];
  const size_t rowBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride) +
                         static_cast<size_t>(row) * static_cast<size_t>(leadingDim);
  int localCount = 0;
  for(int j = static_cast<int>(threadIdx.x + 1); j <= N; j += static_cast<int>(blockDim.x))
  {
    const size_t matIndex = rowBase + static_cast<size_t>(j);
    const int score = HScoreMat[matIndex];
    const uint64_t startCoord = HCoordMat[matIndex];
    int prevScore = 0;
    uint64_t prevStartCoord = 0;
    if(j > 1)
    {
      prevScore = HScoreMat[matIndex - 1];
      prevStartCoord = HCoordMat[matIndex - 1];
    }
    localCount +=
      simScanCudaInitialMatrixRunStartsAt(score,
                                          startCoord,
                                          prevScore,
                                          prevStartCoord,
                                          static_cast<uint32_t>(j),
                                          eventScoreFloor) ?
      1 :
      0;
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    const int rowBaseIndex = batchIndex * rowCountStride;
    runCounts[rowBaseIndex + row] = shared[0];
    if(row == 1)
    {
      runCounts[rowBaseIndex] = 0;
    }
  }
}

__global__ void sim_scan_compact_initial_run_summaries_direct_true_batch_kernel(const int *HScoreMat,
                                                                                const uint64_t *HCoordMat,
                                                                                int leadingDim,
                                                                                int matrixStride,
                                                                                int M,
                                                                                int N,
                                                                                const int *eventScoreFloors,
                                                                                const int *runOffsets,
                                                                                int runOffsetStride,
                                                                                const int *runBases,
                                                                                SimScanCudaInitialRunSummary *summaries)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(row > M)
  {
    return;
  }

  const int tid = static_cast<int>(threadIdx.x);
  const int eventScoreFloor = eventScoreFloors[batchIndex];
  const size_t rowBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride) +
                         static_cast<size_t>(row) * static_cast<size_t>(leadingDim);
  extern __shared__ int shared[];
  __shared__ int outputCursor;
  __shared__ int chunkOutputBase;

  if(tid == 0)
  {
    outputCursor = runBases[batchIndex] + runOffsets[batchIndex * runOffsetStride + row];
  }
  __syncthreads();

  for(int chunkStart = 1; chunkStart <= N; chunkStart += static_cast<int>(blockDim.x))
  {
    const int j = chunkStart + tid;
    int isRunStart = 0;
    int score = 0;
    uint64_t startCoord = 0;
    if(j <= N)
    {
      const size_t matIndex = rowBase + static_cast<size_t>(j);
      score = HScoreMat[matIndex];
      startCoord = HCoordMat[matIndex];
      int prevScore = 0;
      uint64_t prevStartCoord = 0;
      if(j > 1)
      {
        prevScore = HScoreMat[matIndex - 1];
        prevStartCoord = HCoordMat[matIndex - 1];
      }
      isRunStart = simScanCudaInitialMatrixRunStartsAt(score,
                                                       startCoord,
                                                       prevScore,
                                                       prevStartCoord,
                                                       static_cast<uint32_t>(j),
                                                       eventScoreFloor) ?
                     1 :
                     0;
    }
    shared[tid] = isRunStart;
    __syncthreads();

    if(tid == 0)
    {
      int prefix = 0;
      chunkOutputBase = outputCursor;
      for(int i = 0; i < static_cast<int>(blockDim.x); ++i)
      {
        const int flag = shared[i];
        shared[i] = prefix;
        prefix += flag;
      }
      outputCursor += prefix;
    }
    __syncthreads();

    if(isRunStart != 0)
    {
      SimScanCudaInitialRunSummary summary;
      initSimCudaInitialRunSummaryFromCell(score,
                                           startCoord,
                                           static_cast<uint32_t>(row),
                                           static_cast<uint32_t>(j),
                                           summary);
      for(int runJ = j + 1; runJ <= N; ++runJ)
      {
        const size_t runIndex = rowBase + static_cast<size_t>(runJ);
        const int runScore = HScoreMat[runIndex];
        if(runScore <= eventScoreFloor)
        {
          break;
        }
        if(HCoordMat[runIndex] != summary.startCoord)
        {
          break;
        }
        updateSimCudaInitialRunSummaryFromCell(runScore,
                                               static_cast<uint32_t>(runJ),
                                               summary);
      }
      summaries[chunkOutputBase + shared[tid]] = summary;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_compact_region_run_summaries_direct_true_batch_kernel(const int *HScoreMat,
                                                                                const uint64_t *HCoordMat,
                                                                                int leadingDim,
                                                                                int matrixStride,
                                                                                int M,
                                                                                int N,
                                                                                const int *eventScoreFloors,
                                                                                const int *rowStarts,
                                                                                const int *colStarts,
                                                                                const int *runOffsets,
                                                                                int runOffsetStride,
                                                                                const int *runBases,
                                                                                SimScanCudaInitialRunSummary *summaries)
{
  const int row = static_cast<int>(blockIdx.x + 1);
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(row > M)
  {
    return;
  }

  const int tid = static_cast<int>(threadIdx.x);
  const int eventScoreFloor = eventScoreFloors[batchIndex];
  const int rowStart = rowStarts[batchIndex];
  const int colStart = colStarts[batchIndex];
  const uint32_t globalEndI = static_cast<uint32_t>(rowStart + row - 1);
  const size_t rowBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(matrixStride) +
                         static_cast<size_t>(row) * static_cast<size_t>(leadingDim);
  extern __shared__ int shared[];
  __shared__ int outputCursor;
  __shared__ int chunkOutputBase;

  if(tid == 0)
  {
    outputCursor = runBases[batchIndex] + runOffsets[batchIndex * runOffsetStride + row];
  }
  __syncthreads();

  for(int chunkStart = 1; chunkStart <= N; chunkStart += static_cast<int>(blockDim.x))
  {
    const int j = chunkStart + tid;
    int isRunStart = 0;
    int score = 0;
    uint64_t startCoord = 0;
    if(j <= N)
    {
      const size_t matIndex = rowBase + static_cast<size_t>(j);
      score = HScoreMat[matIndex];
      startCoord = HCoordMat[matIndex];
      int prevScore = 0;
      uint64_t prevStartCoord = 0;
      if(j > 1)
      {
        prevScore = HScoreMat[matIndex - 1];
        prevStartCoord = HCoordMat[matIndex - 1];
      }
      isRunStart = simScanCudaInitialMatrixRunStartsAt(score,
                                                       startCoord,
                                                       prevScore,
                                                       prevStartCoord,
                                                       static_cast<uint32_t>(j),
                                                       eventScoreFloor) ?
                     1 :
                     0;
    }
    shared[tid] = isRunStart;
    __syncthreads();

    if(tid == 0)
    {
      int prefix = 0;
      chunkOutputBase = outputCursor;
      for(int i = 0; i < static_cast<int>(blockDim.x); ++i)
      {
        const int flag = shared[i];
        shared[i] = prefix;
        prefix += flag;
      }
      outputCursor += prefix;
    }
    __syncthreads();

    if(isRunStart != 0)
    {
      const uint32_t globalEndJ = static_cast<uint32_t>(colStart + j - 1);
      SimScanCudaInitialRunSummary summary;
      initSimCudaInitialRunSummaryFromCell(score,
                                           startCoord,
                                           globalEndI,
                                           globalEndJ,
                                           summary);
      for(int runJ = j + 1; runJ <= N; ++runJ)
      {
        const size_t runIndex = rowBase + static_cast<size_t>(runJ);
        const int runScore = HScoreMat[runIndex];
        if(runScore <= eventScoreFloor)
        {
          break;
        }
        if(HCoordMat[runIndex] != summary.startCoord)
        {
          break;
        }
        updateSimCudaInitialRunSummaryFromCell(runScore,
                                               static_cast<uint32_t>(colStart + runJ - 1),
                                               summary);
      }
      summaries[chunkOutputBase + shared[tid]] = summary;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_count_region_run_summaries_kernel(const SimScanCudaRowEvent *events,
                                                           const int *rowOffsets,
                                                           int rowCount,
                                                           int *runCounts)
{
  const int localRow = static_cast<int>(blockIdx.x);
  if(localRow >= rowCount)
  {
    return;
  }

  const int startIndex = rowOffsets[localRow];
  const int endIndex = rowOffsets[localRow + 1];
  int localCount = 0;
  for(int eventIndex = startIndex + static_cast<int>(threadIdx.x);
      eventIndex < endIndex;
      eventIndex += static_cast<int>(blockDim.x))
  {
    if(simScanCudaInitialRunStartsAt(events,startIndex,eventIndex))
    {
      ++localCount;
    }
  }

  extern __shared__ int shared[];
  shared[threadIdx.x] = localCount;
  __syncthreads();
  for(unsigned int offset = blockDim.x / 2; offset > 0; offset >>= 1)
  {
    if(threadIdx.x < offset)
    {
      shared[threadIdx.x] += shared[threadIdx.x + offset];
    }
    __syncthreads();
  }
  if(threadIdx.x == 0)
  {
    runCounts[localRow] = shared[0];
  }
}

__global__ void sim_scan_compact_region_run_summaries_kernel(const SimScanCudaRowEvent *events,
                                                             const int *rowOffsets,
                                                             int rowCount,
                                                             const int *runOffsets,
                                                             SimScanCudaInitialRunSummary *summaries)
{
  const int localRow = static_cast<int>(blockIdx.x);
  if(localRow >= rowCount)
  {
    return;
  }

  const int startIndex = rowOffsets[localRow];
  const int endIndex = rowOffsets[localRow + 1];
  if(startIndex >= endIndex)
  {
    return;
  }

  const int tid = static_cast<int>(threadIdx.x);
  extern __shared__ int shared[];
  __shared__ int outputCursor;
  __shared__ int chunkOutputBase;

  if(tid == 0)
  {
    outputCursor = runOffsets[localRow];
  }
  __syncthreads();

  for(int chunkStart = startIndex; chunkStart < endIndex; chunkStart += static_cast<int>(blockDim.x))
  {
    const int eventIndex = chunkStart + tid;
    const int isRunStart =
      (eventIndex < endIndex && simScanCudaInitialRunStartsAt(events,startIndex,eventIndex)) ? 1 : 0;
    shared[tid] = isRunStart;
    __syncthreads();

    if(tid == 0)
    {
      int prefix = 0;
      chunkOutputBase = outputCursor;
      for(int i = 0; i < static_cast<int>(blockDim.x); ++i)
      {
        const int flag = shared[i];
        shared[i] = prefix;
        prefix += flag;
      }
      outputCursor += prefix;
    }
    __syncthreads();

    if(isRunStart != 0)
    {
      SimScanCudaInitialRunSummary summary;
      initSimCudaInitialRunSummary(events[eventIndex],summary);
      for(int runEventIndex = eventIndex + 1; runEventIndex < endIndex; ++runEventIndex)
      {
        const SimScanCudaRowEvent &event = events[runEventIndex];
        if(event.startCoord != summary.startCoord)
        {
          break;
        }
        updateSimCudaInitialRunSummary(event,summary);
      }
      summaries[chunkOutputBase + shared[tid]] = summary;
    }
    __syncthreads();
  }
}

__global__ void sim_scan_prefix_sum_kernel(const int *rowCounts,
                                           int rowCount,
                                           int *rowOffsets,
                                           int *totalEventsOut)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }
  int total = 0;
  for(int i = 0; i < rowCount; ++i)
  {
    rowOffsets[i] = total;
    total += rowCounts[i];
  }
  rowOffsets[rowCount] = total;
  *totalEventsOut = total;
}

__device__ __forceinline__ int sim_scan_candidate_min_index(const SimScanCudaCandidateState *candidates,int candidateCount)
{
  int bestIndex = 0;
  for(int i = 1; i < candidateCount; ++i)
  {
    if(candidates[i].score < candidates[bestIndex].score ||
       (candidates[i].score == candidates[bestIndex].score && i < bestIndex))
    {
      bestIndex = i;
    }
  }
  return bestIndex;
}

__device__ __forceinline__ int sim_scan_candidate_hash_index(uint64_t startCoord)
{
  uint64_t mixed = startCoord;
  mixed ^= mixed >> 33;
  mixed *= 0xff51afd7ed558ccdULL;
  mixed ^= mixed >> 33;
  return static_cast<int>(mixed) & (sim_scan_candidate_hash_capacity - 1);
}

__device__ __forceinline__ int sim_scan_candidate_hash_find(uint64_t startCoord,
                                                            const uint64_t *hashCoords,
                                                            const int *hashSlots)
{
  int slot = sim_scan_candidate_hash_index(startCoord);
  for(int probe = 0; probe < sim_scan_candidate_hash_capacity; ++probe)
  {
    const int storedSlot = hashSlots[slot];
    if(storedSlot == sim_scan_candidate_hash_empty)
    {
      return -1;
    }
    if(storedSlot >= 0 && hashCoords[slot] == startCoord)
    {
      return storedSlot;
    }
    slot = (slot + 1) & (sim_scan_candidate_hash_capacity - 1);
  }
  return -1;
}

__device__ __forceinline__ bool sim_scan_candidate_hash_insert(uint64_t startCoord,
                                                               int candidateSlot,
                                                               uint64_t *hashCoords,
                                                               int *hashSlots,
                                                               int &tombstoneCount)
{
  int slot = sim_scan_candidate_hash_index(startCoord);
  int firstTombstone = -1;
  for(int probe = 0; probe < sim_scan_candidate_hash_capacity; ++probe)
  {
    const int storedSlot = hashSlots[slot];
    if(storedSlot == sim_scan_candidate_hash_empty)
    {
      if(firstTombstone >= 0)
      {
        slot = firstTombstone;
        if(tombstoneCount > 0)
        {
          --tombstoneCount;
        }
      }
      hashCoords[slot] = startCoord;
      hashSlots[slot] = candidateSlot;
      return true;
    }
    if(storedSlot == sim_scan_candidate_hash_tombstone)
    {
      if(firstTombstone < 0)
      {
        firstTombstone = slot;
      }
    }
    else if(hashCoords[slot] == startCoord)
    {
      hashSlots[slot] = candidateSlot;
      return true;
    }
    slot = (slot + 1) & (sim_scan_candidate_hash_capacity - 1);
  }
  if(firstTombstone >= 0)
  {
    hashCoords[firstTombstone] = startCoord;
    hashSlots[firstTombstone] = candidateSlot;
    if(tombstoneCount > 0)
    {
      --tombstoneCount;
    }
    return true;
  }
  return false;
}

__device__ __forceinline__ bool sim_scan_candidate_hash_erase(uint64_t startCoord,
                                                              const uint64_t *hashCoords,
                                                              int *hashSlots,
                                                              int &tombstoneCount)
{
  int slot = sim_scan_candidate_hash_index(startCoord);
  for(int probe = 0; probe < sim_scan_candidate_hash_capacity; ++probe)
  {
    const int storedSlot = hashSlots[slot];
    if(storedSlot == sim_scan_candidate_hash_empty)
    {
      return false;
    }
    if(storedSlot >= 0 && hashCoords[slot] == startCoord)
    {
      hashSlots[slot] = sim_scan_candidate_hash_tombstone;
      ++tombstoneCount;
      return true;
    }
    slot = (slot + 1) & (sim_scan_candidate_hash_capacity - 1);
  }
  return false;
}

__device__ __forceinline__ void sim_scan_candidate_hash_rebuild(const SimScanCudaCandidateState *candidates,
                                                                int candidateCount,
                                                                uint64_t *hashCoords,
                                                                int *hashSlots,
                                                                int &tombstoneCount)
{
  for(int slot = 0; slot < sim_scan_candidate_hash_capacity; ++slot)
  {
    hashSlots[slot] = sim_scan_candidate_hash_empty;
  }
  tombstoneCount = 0;
  for(int candidateIndex = 0; candidateIndex < candidateCount; ++candidateIndex)
  {
    sim_scan_candidate_hash_insert(simScanCudaCandidateStateStartCoord(candidates[candidateIndex]),
                                   candidateIndex,
                                   hashCoords,
                                   hashSlots,
                                   tombstoneCount);
  }
}

__device__ __forceinline__ int sim_scan_candidate_min_index_warp(const SimScanCudaCandidateState *candidates,
                                                                 int candidateCount)
{
  if(candidateCount <= 0)
  {
    return -1;
  }

  const unsigned int warpMask = 0xffffffffu;
  const int lane = static_cast<int>(threadIdx.x & (sim_scan_initial_reduce_threads - 1));
  int bestIndex = -1;
  int bestScore = 0x7fffffff;
  for(int candidateIndex = lane; candidateIndex < candidateCount; candidateIndex += sim_scan_initial_reduce_threads)
  {
    const int candidateScore = candidates[candidateIndex].score;
    if(bestIndex < 0 ||
       candidateScore < bestScore ||
       (candidateScore == bestScore && candidateIndex < bestIndex))
    {
      bestIndex = candidateIndex;
      bestScore = candidateScore;
    }
  }

  for(int offset = sim_scan_initial_reduce_threads / 2; offset > 0; offset >>= 1)
  {
    const int otherIndex = __shfl_down_sync(warpMask,bestIndex,offset);
    const int otherScore = __shfl_down_sync(warpMask,bestScore,offset);
    if(otherIndex >= 0 &&
       (bestIndex < 0 ||
        otherScore < bestScore ||
        (otherScore == bestScore && otherIndex < bestIndex)))
    {
      bestIndex = otherIndex;
      bestScore = otherScore;
    }
  }

  return __shfl_sync(warpMask,bestIndex,0);
}

__device__ __forceinline__ int sim_scan_candidate_hash_find_warp(uint64_t startCoord,
                                                                 const uint64_t *hashCoords,
                                                                 const int *hashSlots)
{
  const unsigned int warpMask = 0xffffffffu;
  const int lane = static_cast<int>(threadIdx.x & (sim_scan_initial_reduce_threads - 1));
  const int startSlot = sim_scan_candidate_hash_index(startCoord);
  for(int probeBase = 0; probeBase < sim_scan_candidate_hash_capacity; probeBase += sim_scan_initial_reduce_threads)
  {
    const int probe = probeBase + lane;
    const bool active = probe < sim_scan_candidate_hash_capacity;
    const int slot = (startSlot + probe) & (sim_scan_candidate_hash_capacity - 1);
    const int storedSlot = active ? hashSlots[slot] : sim_scan_candidate_hash_empty;
    const bool isEmpty = active && storedSlot == sim_scan_candidate_hash_empty;
    const bool isMatch = active && storedSlot >= 0 && hashCoords[slot] == startCoord;
    const unsigned int emptyMask = __ballot_sync(warpMask,isEmpty);
    const unsigned int matchMask = __ballot_sync(warpMask,isMatch);

    int decision = 0;
    int decisionProbe = -1;
    if(lane == 0)
    {
      const int firstEmpty = emptyMask != 0 ? (__ffs(emptyMask) - 1) : sim_scan_initial_reduce_threads;
      const int firstMatch = matchMask != 0 ? (__ffs(matchMask) - 1) : sim_scan_initial_reduce_threads;
      if(matchMask != 0 && firstMatch < firstEmpty)
      {
        decision = 1;
        decisionProbe = probeBase + firstMatch;
      }
      else if(emptyMask != 0)
      {
        decision = 2;
      }
    }
    decision = __shfl_sync(warpMask,decision,0);
    decisionProbe = __shfl_sync(warpMask,decisionProbe,0);
    if(decision == 1)
    {
      const int slotIndex = (startSlot + decisionProbe) & (sim_scan_candidate_hash_capacity - 1);
      return hashSlots[slotIndex];
    }
    if(decision == 2)
    {
      return -1;
    }
  }
  return -1;
}

__device__ __forceinline__ bool sim_scan_candidate_hash_insert_warp(uint64_t startCoord,
                                                                    int candidateSlot,
                                                                    uint64_t *hashCoords,
                                                                    int *hashSlots,
                                                                    int &tombstoneCount)
{
  const unsigned int warpMask = 0xffffffffu;
  const int lane = static_cast<int>(threadIdx.x & (sim_scan_initial_reduce_threads - 1));
  const int startSlot = sim_scan_candidate_hash_index(startCoord);
  int firstTombstoneProbe = -1;
  for(int probeBase = 0; probeBase < sim_scan_candidate_hash_capacity; probeBase += sim_scan_initial_reduce_threads)
  {
    const int probe = probeBase + lane;
    const bool active = probe < sim_scan_candidate_hash_capacity;
    const int slot = (startSlot + probe) & (sim_scan_candidate_hash_capacity - 1);
    const int storedSlot = active ? hashSlots[slot] : sim_scan_candidate_hash_empty;
    const bool isEmpty = active && storedSlot == sim_scan_candidate_hash_empty;
    const bool isTombstone = active && storedSlot == sim_scan_candidate_hash_tombstone;
    const bool isMatch = active && storedSlot >= 0 && hashCoords[slot] == startCoord;
    const unsigned int emptyMask = __ballot_sync(warpMask,isEmpty);
    const unsigned int tombstoneMask = __ballot_sync(warpMask,isTombstone);
    const unsigned int matchMask = __ballot_sync(warpMask,isMatch);

    int chosenProbe = -1;
    int done = 0;
    if(lane == 0)
    {
      const int firstEmpty = emptyMask != 0 ? (__ffs(emptyMask) - 1) : sim_scan_initial_reduce_threads;
      const int firstMatch = matchMask != 0 ? (__ffs(matchMask) - 1) : sim_scan_initial_reduce_threads;
      const int firstChunkTombstone = tombstoneMask != 0 ? (__ffs(tombstoneMask) - 1) : sim_scan_initial_reduce_threads;

      if(matchMask != 0 && firstMatch < firstEmpty)
      {
        chosenProbe = probeBase + firstMatch;
        done = 1;
      }
      else if(emptyMask != 0)
      {
        if(firstTombstoneProbe < 0 &&
           tombstoneMask != 0 &&
           firstChunkTombstone < firstEmpty)
        {
          firstTombstoneProbe = probeBase + firstChunkTombstone;
        }
        chosenProbe = firstTombstoneProbe >= 0 ? firstTombstoneProbe : (probeBase + firstEmpty);
        done = 1;
      }
      else if(firstTombstoneProbe < 0 && tombstoneMask != 0)
      {
        firstTombstoneProbe = probeBase + firstChunkTombstone;
      }
    }
    chosenProbe = __shfl_sync(warpMask,chosenProbe,0);
    done = __shfl_sync(warpMask,done,0);
    firstTombstoneProbe = __shfl_sync(warpMask,firstTombstoneProbe,0);
    if(done != 0)
    {
      if(lane == 0)
      {
        const int slotIndex = (startSlot + chosenProbe) & (sim_scan_candidate_hash_capacity - 1);
        if(hashSlots[slotIndex] == sim_scan_candidate_hash_tombstone && tombstoneCount > 0)
        {
          --tombstoneCount;
        }
        hashCoords[slotIndex] = startCoord;
        hashSlots[slotIndex] = candidateSlot;
      }
      __syncwarp();
      return true;
    }
  }

  if(firstTombstoneProbe >= 0)
  {
    if(lane == 0)
    {
      const int slotIndex = (startSlot + firstTombstoneProbe) & (sim_scan_candidate_hash_capacity - 1);
      if(hashSlots[slotIndex] == sim_scan_candidate_hash_tombstone && tombstoneCount > 0)
      {
        --tombstoneCount;
      }
      hashCoords[slotIndex] = startCoord;
      hashSlots[slotIndex] = candidateSlot;
    }
    __syncwarp();
    return true;
  }
  __syncwarp();
  return false;
}

__device__ __forceinline__ bool sim_scan_candidate_hash_erase_warp(uint64_t startCoord,
                                                                   const uint64_t *hashCoords,
                                                                   int *hashSlots,
                                                                   int &tombstoneCount)
{
  const unsigned int warpMask = 0xffffffffu;
  const int lane = static_cast<int>(threadIdx.x & (sim_scan_initial_reduce_threads - 1));
  const int startSlot = sim_scan_candidate_hash_index(startCoord);
  for(int probeBase = 0; probeBase < sim_scan_candidate_hash_capacity; probeBase += sim_scan_initial_reduce_threads)
  {
    const int probe = probeBase + lane;
    const bool active = probe < sim_scan_candidate_hash_capacity;
    const int slot = (startSlot + probe) & (sim_scan_candidate_hash_capacity - 1);
    const int storedSlot = active ? hashSlots[slot] : sim_scan_candidate_hash_empty;
    const bool isEmpty = active && storedSlot == sim_scan_candidate_hash_empty;
    const bool isMatch = active && storedSlot >= 0 && hashCoords[slot] == startCoord;
    const unsigned int emptyMask = __ballot_sync(warpMask,isEmpty);
    const unsigned int matchMask = __ballot_sync(warpMask,isMatch);

    int decision = 0;
    int decisionProbe = -1;
    if(lane == 0)
    {
      const int firstEmpty = emptyMask != 0 ? (__ffs(emptyMask) - 1) : sim_scan_initial_reduce_threads;
      const int firstMatch = matchMask != 0 ? (__ffs(matchMask) - 1) : sim_scan_initial_reduce_threads;
      if(matchMask != 0 && firstMatch < firstEmpty)
      {
        decision = 1;
        decisionProbe = probeBase + firstMatch;
      }
      else if(emptyMask != 0)
      {
        decision = 2;
      }
    }
    decision = __shfl_sync(warpMask,decision,0);
    decisionProbe = __shfl_sync(warpMask,decisionProbe,0);
    if(decision == 1)
    {
      if(lane == 0)
      {
        const int slotIndex = (startSlot + decisionProbe) & (sim_scan_candidate_hash_capacity - 1);
        hashSlots[slotIndex] = sim_scan_candidate_hash_tombstone;
        ++tombstoneCount;
      }
      __syncwarp();
      return true;
    }
    if(decision == 2)
    {
      __syncwarp();
      return false;
    }
  }
  __syncwarp();
  return false;
}

__device__ __forceinline__ void sim_scan_candidate_hash_rebuild_warp(const SimScanCudaCandidateState *candidates,
                                                                     int candidateCount,
                                                                     uint64_t *hashCoords,
                                                                     int *hashSlots,
                                                                     int &tombstoneCount)
{
  const int lane = static_cast<int>(threadIdx.x & (sim_scan_initial_reduce_threads - 1));
  for(int slot = lane; slot < sim_scan_candidate_hash_capacity; slot += sim_scan_initial_reduce_threads)
  {
    hashSlots[slot] = sim_scan_candidate_hash_empty;
  }
  __syncwarp();
  if(lane == 0)
  {
    tombstoneCount = 0;
  }
  __syncwarp();
  for(int candidateIndex = 0; candidateIndex < candidateCount; ++candidateIndex)
  {
    sim_scan_candidate_hash_insert_warp(simScanCudaCandidateStateStartCoord(candidates[candidateIndex]),
                                        candidateIndex,
                                        hashCoords,
                                        hashSlots,
                                        tombstoneCount);
  }
  __syncwarp();
}

__device__ __forceinline__ bool sim_scan_initial_summary_is_noop(const SimScanCudaInitialRunSummary &summary,
                                                                 const SimScanCudaCandidateState *candidates,
                                                                 const uint64_t *hashCoords,
                                                                 const int *hashSlots)
{
  const int targetIndex = sim_scan_candidate_hash_find(summary.startCoord,hashCoords,hashSlots);
  if(targetIndex < 0)
  {
    return false;
  }
  const SimScanCudaCandidateState &candidate = candidates[targetIndex];
  return candidate.score >= summary.score &&
         candidate.top <= static_cast<int>(summary.endI) &&
         candidate.bot >= static_cast<int>(summary.endI) &&
         candidate.left <= static_cast<int>(summary.minEndJ) &&
         candidate.right >= static_cast<int>(summary.maxEndJ);
}

__global__ void sim_scan_reduce_region_candidate_summaries_kernel(const SimScanCudaInitialRunSummary *summaries,
                                                                  int summaryCount,
                                                                  SimScanCudaCandidateState *candidates,
                                                                  int *candidateCountInOut,
                                                                  int *runningMinInOut)
{
  if(blockIdx.x != 0 || threadIdx.x >= sim_scan_initial_reduce_threads)
  {
    return;
  }

  __shared__ SimScanCudaCandidateState sharedCandidates[sim_scan_cuda_max_candidates];
  __shared__ uint64_t sharedHashCoords[sim_scan_candidate_hash_capacity];
  __shared__ int sharedHashSlots[sim_scan_candidate_hash_capacity];
  __shared__ int sharedCandidateCount;
  __shared__ int sharedRunningMin;
  __shared__ int sharedMinIndex;
  __shared__ int sharedHashTombstones;

  const int tid = static_cast<int>(threadIdx.x);
  if(tid == 0)
  {
    int candidateCount = *candidateCountInOut;
    if(candidateCount < 0)
    {
      candidateCount = 0;
    }
    if(candidateCount > sim_scan_cuda_max_candidates)
    {
      candidateCount = sim_scan_cuda_max_candidates;
    }
    sharedCandidateCount = candidateCount;
    sharedRunningMin = 0;
    sharedMinIndex = -1;
    sharedHashTombstones = 0;
  }
  __syncwarp();

  if(tid < sharedCandidateCount)
  {
    sharedCandidates[tid] = candidates[tid];
  }
  if(tid + sim_scan_initial_reduce_threads < sharedCandidateCount)
  {
    sharedCandidates[tid + sim_scan_initial_reduce_threads] = candidates[tid + sim_scan_initial_reduce_threads];
  }
  __syncwarp();

  if(tid == 0 && sharedCandidateCount > 0)
  {
    sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
    sharedRunningMin = sharedCandidates[sharedMinIndex].score;
  }
  __syncwarp();

  if(tid == 0)
  {
    sim_scan_candidate_hash_rebuild(sharedCandidates,
                                    sharedCandidateCount,
                                    sharedHashCoords,
                                    sharedHashSlots,
                                    sharedHashTombstones);
    for(int summaryIndex = 0; summaryIndex < summaryCount; ++summaryIndex)
    {
      const SimScanCudaInitialRunSummary summary = summaries[summaryIndex];
      if(summary.score <= sharedRunningMin)
      {
        continue;
      }

      int targetIndex = sim_scan_candidate_hash_find(summary.startCoord,
                                                     sharedHashCoords,
                                                     sharedHashSlots);
      if(targetIndex < 0)
      {
        if(sharedCandidateCount == sim_scan_cuda_max_candidates)
        {
          targetIndex = sharedMinIndex;
          sim_scan_candidate_hash_erase(simScanCudaCandidateStateStartCoord(sharedCandidates[targetIndex]),
                                        sharedHashCoords,
                                        sharedHashSlots,
                                        sharedHashTombstones);
        }
        else
        {
          targetIndex = sharedCandidateCount++;
        }
        initSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[targetIndex]);
        if(!sim_scan_candidate_hash_insert(summary.startCoord,
                                           targetIndex,
                                           sharedHashCoords,
                                           sharedHashSlots,
                                           sharedHashTombstones))
        {
          sim_scan_candidate_hash_rebuild(sharedCandidates,
                                          sharedCandidateCount,
                                          sharedHashCoords,
                                          sharedHashSlots,
                                          sharedHashTombstones);
          sim_scan_candidate_hash_insert(summary.startCoord,
                                         targetIndex,
                                         sharedHashCoords,
                                         sharedHashSlots,
                                         sharedHashTombstones);
        }
        sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
        sharedRunningMin = sharedCandidates[sharedMinIndex].score;
        if(sharedHashTombstones > sim_scan_candidate_hash_rebuild_tombstones)
        {
          sim_scan_candidate_hash_rebuild(sharedCandidates,
                                          sharedCandidateCount,
                                          sharedHashCoords,
                                          sharedHashSlots,
                                          sharedHashTombstones);
        }
      }
      else
      {
        const bool improved =
          updateSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[targetIndex]);
        if(improved && targetIndex == sharedMinIndex)
        {
          sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
          sharedRunningMin = sharedCandidates[sharedMinIndex].score;
        }
      }
    }
  }
  __syncwarp();

  if(tid < sharedCandidateCount)
  {
    candidates[tid] = sharedCandidates[tid];
  }
  if(tid + sim_scan_initial_reduce_threads < sharedCandidateCount)
  {
    candidates[tid + sim_scan_initial_reduce_threads] = sharedCandidates[tid + sim_scan_initial_reduce_threads];
  }
  if(tid == 0)
  {
    *candidateCountInOut = sharedCandidateCount;
    *runningMinInOut = sharedRunningMin;
  }
}

__global__ void sim_scan_merge_candidate_states_into_frontier_kernel(const SimScanCudaCandidateState *states,
                                                                     int stateCount,
                                                                     SimScanCudaCandidateState *candidates,
                                                                     int *candidateCountInOut,
                                                                     int *runningMinInOut)
{
  if(blockIdx.x != 0 || threadIdx.x >= sim_scan_initial_reduce_threads)
  {
    return;
  }

  __shared__ SimScanCudaCandidateState sharedCandidates[sim_scan_cuda_max_candidates];
  __shared__ uint64_t sharedHashCoords[sim_scan_candidate_hash_capacity];
  __shared__ int sharedHashSlots[sim_scan_candidate_hash_capacity];
  __shared__ int sharedCandidateCount;
  __shared__ int sharedRunningMin;
  __shared__ int sharedMinIndex;
  __shared__ int sharedHashTombstones;

  const int tid = static_cast<int>(threadIdx.x);
  if(tid == 0)
  {
    int candidateCount = *candidateCountInOut;
    if(candidateCount < 0)
    {
      candidateCount = 0;
    }
    if(candidateCount > sim_scan_cuda_max_candidates)
    {
      candidateCount = sim_scan_cuda_max_candidates;
    }
    sharedCandidateCount = candidateCount;
    sharedRunningMin = 0;
    sharedMinIndex = -1;
    sharedHashTombstones = 0;
  }
  __syncwarp();

  if(tid < sharedCandidateCount)
  {
    sharedCandidates[tid] = candidates[tid];
  }
  if(tid + sim_scan_initial_reduce_threads < sharedCandidateCount)
  {
    sharedCandidates[tid + sim_scan_initial_reduce_threads] =
      candidates[tid + sim_scan_initial_reduce_threads];
  }
  __syncwarp();

  if(tid == 0 && sharedCandidateCount > 0)
  {
    sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
    sharedRunningMin = sharedCandidates[sharedMinIndex].score;
    sim_scan_candidate_hash_rebuild(sharedCandidates,
                                    sharedCandidateCount,
                                    sharedHashCoords,
                                    sharedHashSlots,
                                    sharedHashTombstones);

    for(int stateIndex = 0; stateIndex < stateCount; ++stateIndex)
    {
      const SimScanCudaCandidateState state = states[stateIndex];
      const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
      int targetIndex = sim_scan_candidate_hash_find(startCoord,
                                                     sharedHashCoords,
                                                     sharedHashSlots);
      if(targetIndex < 0)
      {
        if(sharedCandidateCount == sim_scan_cuda_max_candidates)
        {
          targetIndex = sharedMinIndex;
          sim_scan_candidate_hash_erase(simScanCudaCandidateStateStartCoord(sharedCandidates[targetIndex]),
                                        sharedHashCoords,
                                        sharedHashSlots,
                                        sharedHashTombstones);
        }
        else
        {
          targetIndex = sharedCandidateCount++;
        }
        sharedCandidates[targetIndex] = state;
        if(!sim_scan_candidate_hash_insert(startCoord,
                                           targetIndex,
                                           sharedHashCoords,
                                           sharedHashSlots,
                                           sharedHashTombstones))
        {
          sim_scan_candidate_hash_rebuild(sharedCandidates,
                                          sharedCandidateCount,
                                          sharedHashCoords,
                                          sharedHashSlots,
                                          sharedHashTombstones);
          sim_scan_candidate_hash_insert(startCoord,
                                         targetIndex,
                                         sharedHashCoords,
                                         sharedHashSlots,
                                         sharedHashTombstones);
        }
        if(sharedHashTombstones > sim_scan_candidate_hash_rebuild_tombstones)
        {
          sim_scan_candidate_hash_rebuild(sharedCandidates,
                                          sharedCandidateCount,
                                          sharedHashCoords,
                                          sharedHashSlots,
                                          sharedHashTombstones);
        }
        sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
        sharedRunningMin = sharedCandidates[sharedMinIndex].score;
        continue;
      }

      const bool improved =
        updateSimScanCudaCandidateStateFromCandidateState(state,sharedCandidates[targetIndex]);
      if(improved && targetIndex == sharedMinIndex)
      {
        sharedMinIndex = sim_scan_candidate_min_index(sharedCandidates,sharedCandidateCount);
        sharedRunningMin = sharedCandidates[sharedMinIndex].score;
      }
    }
  }
  __syncwarp();

  if(tid < sharedCandidateCount)
  {
    candidates[tid] = sharedCandidates[tid];
  }
  if(tid + sim_scan_initial_reduce_threads < sharedCandidateCount)
  {
    candidates[tid + sim_scan_initial_reduce_threads] =
      sharedCandidates[tid + sim_scan_initial_reduce_threads];
  }
  if(tid == 0)
  {
    *candidateCountInOut = sharedCandidateCount;
    *runningMinInOut = sharedRunningMin;
  }
}

__global__ void sim_scan_reduce_initial_candidate_states_kernel(const SimScanCudaInitialRunSummary *summaries,
                                                                int summaryCount,
                                                                SimScanCudaCandidateState *candidates,
                                                                int *candidateCountInOut,
                                                                int *runningMinInOut,
                                                                const int *chunkMaxScores,
                                                                int chunkSize,
                                                                unsigned long long *replayStats,
                                                                unsigned long long *orderedMaintenanceDigestStats,
                                                                SimScanCudaCandidateState *safeStoreStatesOut,
                                                                int *safeStoreCountOut)
{
  if(blockIdx.x != 0 || threadIdx.x >= sim_scan_initial_reduce_threads)
  {
    return;
  }

  __shared__ SimScanCudaCandidateState sharedCandidates[sim_scan_cuda_max_candidates];
  __shared__ uint64_t sharedHashCoords[sim_scan_candidate_hash_capacity];
  __shared__ int sharedHashSlots[sim_scan_candidate_hash_capacity];
  __shared__ SimScanCudaCandidateState sharedSafeStoreStates[sim_scan_candidate_hash_capacity];
  __shared__ uint64_t sharedSafeStoreHashCoords[sim_scan_candidate_hash_capacity];
  __shared__ int sharedSafeStoreHashSlots[sim_scan_candidate_hash_capacity];
  __shared__ int sharedCandidateCount;
  __shared__ int sharedRunningMin;
  __shared__ int sharedMinIndex;
  __shared__ int sharedHashTombstones;
  __shared__ int sharedSafeStoreCount;
  __shared__ int sharedSafeStoreHashTombstones;
  __shared__ int sharedSafeStoreInsertIndex;
  __shared__ int sharedSafeStorePrunedCount;
  __shared__ SimScanCudaInitialRunSummary sharedSummary;
  __shared__ int sharedInsertIndex;
  __shared__ int sharedNeedErase;
  __shared__ uint64_t sharedEraseCoord;
  __shared__ int sharedImproved;
  __shared__ int sharedReplayChunk;

  const int tid = static_cast<int>(threadIdx.x);
  unsigned long long localChunkCount = 0;
  unsigned long long localChunkReplayedCount = 0;
  unsigned long long localSummaryReplayCount = 0;
  uint64_t localReplacementSequenceHash = sim_scan_digest_fnv_offset();
  uint64_t localRunningMinUpdateSequenceHash = sim_scan_digest_fnv_offset();
  uint64_t localRunningMinSlotUpdateSequenceHash = sim_scan_digest_fnv_offset();
  uint64_t localFloorChangeSequenceHash = sim_scan_digest_fnv_offset();
  uint64_t localCandidateIndexVisibilityHash = sim_scan_digest_fnv_offset();
  unsigned long long localCandidateReplacementCount = 0;
  unsigned long long localRunningMinUpdateCount = 0;
  unsigned long long localRunningMinSlotUpdateCount = 0;
  unsigned long long localFloorChangeCount = 0;
  unsigned long long localCandidateIndexExistingHitCount = 0;
  unsigned long long localCandidateIndexMissCount = 0;
  unsigned long long localCandidateIndexInsertCount = 0;
  unsigned long long localCandidateIndexEraseCount = 0;
  unsigned long long localCandidateIndexVisibilityCheckCount = 0;
  if(tid == 0)
  {
    int candidateCount = *candidateCountInOut;
    if(candidateCount < 0)
    {
      candidateCount = 0;
    }
    if(candidateCount > sim_scan_cuda_max_candidates)
    {
      candidateCount = sim_scan_cuda_max_candidates;
    }
    sharedCandidateCount = candidateCount;
    sharedRunningMin = 0;
    sharedMinIndex = -1;
    sharedHashTombstones = 0;
    sharedSafeStoreCount = 0;
    sharedSafeStoreHashTombstones = 0;
    sharedSafeStoreInsertIndex = -1;
    sharedSafeStorePrunedCount = 0;
  }
  __syncwarp();

  for(int candidateIndex = tid; candidateIndex < sharedCandidateCount; candidateIndex += sim_scan_initial_reduce_threads)
  {
    sharedCandidates[candidateIndex] = candidates[candidateIndex];
  }
  __syncwarp();

  if(sharedCandidateCount > 0)
  {
    const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
    if(tid == 0)
    {
      sharedMinIndex = minIndex;
      sharedRunningMin = sharedCandidates[minIndex].score;
    }
  }
  else if(tid == 0)
  {
    sharedMinIndex = -1;
    sharedRunningMin = 0;
  }
  __syncwarp();

  sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                       sharedCandidateCount,
                                       sharedHashCoords,
                                       sharedHashSlots,
                                       sharedHashTombstones);
  if(safeStoreStatesOut != NULL)
  {
    sim_scan_candidate_hash_rebuild_warp(sharedSafeStoreStates,
                                         sharedSafeStoreCount,
                                         sharedSafeStoreHashCoords,
                                         sharedSafeStoreHashSlots,
                                         sharedSafeStoreHashTombstones);
  }

  // Preserve exact summary stream order while parallelizing the hot bookkeeping within a warp.
  const int effectiveChunkSize = chunkSize > 0 ? chunkSize : (summaryCount > 0 ? summaryCount : 1);
  const int chunkCount = summaryCount > 0 ? ((summaryCount + effectiveChunkSize - 1) / effectiveChunkSize) : 0;
  for(int chunkIndex = 0; chunkIndex < chunkCount; ++chunkIndex)
  {
    const int chunkStart = chunkIndex * effectiveChunkSize;
    const int chunkEnd = min(chunkStart + effectiveChunkSize, summaryCount);
    int localNeedsReplay = 0;
    for(int summaryIndex = chunkStart + tid; summaryIndex < chunkEnd; summaryIndex += sim_scan_initial_reduce_threads)
    {
      if(!sim_scan_initial_summary_is_noop(summaries[summaryIndex],
                                           sharedCandidates,
                                           sharedHashCoords,
                                           sharedHashSlots))
      {
        localNeedsReplay = 1;
        break;
      }
    }
    const int chunkNeedsReplay =
      (orderedMaintenanceDigestStats != NULL || safeStoreStatesOut != NULL) ? 1 :
      (__any_sync(0xffffffffu, localNeedsReplay != 0) ? 1 : 0);
    if(tid == 0)
    {
      ++localChunkCount;
      sharedReplayChunk = chunkNeedsReplay;
      if(sharedReplayChunk != 0)
      {
        ++localChunkReplayedCount;
        localSummaryReplayCount += static_cast<unsigned long long>(chunkEnd - chunkStart);
      }
    }
    __syncwarp();

    if(sharedReplayChunk == 0)
    {
      continue;
    }

    for(int summaryIndex = chunkStart; summaryIndex < chunkEnd; ++summaryIndex)
    {
      if(tid == 0)
      {
        sharedSummary = summaries[summaryIndex];
      }
      __syncwarp();

      const SimScanCudaInitialRunSummary summary = sharedSummary;
      if(safeStoreStatesOut != NULL)
      {
        const int safeStoreIndex =
          sim_scan_candidate_hash_find_warp(summary.startCoord,
                                            sharedSafeStoreHashCoords,
                                            sharedSafeStoreHashSlots);
        if(safeStoreIndex < 0)
        {
          if(tid == 0)
          {
            if(sharedSafeStoreCount < sim_scan_candidate_hash_capacity)
            {
              sharedSafeStoreInsertIndex = sharedSafeStoreCount++;
              initSimScanCudaCandidateStateFromInitialRunSummary(
                summary,sharedSafeStoreStates[sharedSafeStoreInsertIndex]);
            }
            else
            {
              sharedSafeStoreInsertIndex = -1;
            }
          }
          __syncwarp();
          if(sharedSafeStoreInsertIndex >= 0)
          {
            if(!sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                                    sharedSafeStoreInsertIndex,
                                                    sharedSafeStoreHashCoords,
                                                    sharedSafeStoreHashSlots,
                                                    sharedSafeStoreHashTombstones))
            {
              sim_scan_candidate_hash_rebuild_warp(sharedSafeStoreStates,
                                                   sharedSafeStoreCount,
                                                   sharedSafeStoreHashCoords,
                                                   sharedSafeStoreHashSlots,
                                                   sharedSafeStoreHashTombstones);
              sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                                  sharedSafeStoreInsertIndex,
                                                  sharedSafeStoreHashCoords,
                                                  sharedSafeStoreHashSlots,
                                                  sharedSafeStoreHashTombstones);
            }
          }
        }
        else
        {
          if(tid == 0)
          {
            updateSimScanCudaCandidateStateFromInitialRunSummary(
              summary,sharedSafeStoreStates[safeStoreIndex]);
          }
          __syncwarp();
        }
      }
      const int targetIndex = sim_scan_candidate_hash_find_warp(summary.startCoord,
                                                                sharedHashCoords,
                                                                sharedHashSlots);
      const int candidateCountBefore = sharedCandidateCount;
      const int runningMinBefore = sharedRunningMin;
      const int runningMinSlotBefore = sharedMinIndex;
      if(tid == 0)
      {
        ++localCandidateIndexVisibilityCheckCount;
        if(targetIndex >= 0)
        {
          ++localCandidateIndexExistingHitCount;
        }
        else
        {
          ++localCandidateIndexMissCount;
        }
      }
      if(targetIndex < 0)
      {
        if(tid == 0)
        {
          sharedNeedErase = 0;
          sharedEraseCoord = 0;
          if(sharedCandidateCount == sim_scan_cuda_max_candidates)
          {
            sharedInsertIndex = sharedMinIndex;
            sharedNeedErase = 1;
            sharedEraseCoord = simScanCudaCandidateStateStartCoord(sharedCandidates[sharedInsertIndex]);
          }
          else
          {
            sharedInsertIndex = sharedCandidateCount++;
          }
          if(candidateCountBefore == sim_scan_cuda_max_candidates)
          {
            uint64_t replacementHash = localReplacementSequenceHash;
            replacementHash =
              sim_scan_digest_mix_u64(replacementHash,static_cast<uint64_t>(summaryIndex));
            replacementHash =
              sim_scan_digest_mix_i64(replacementHash,
                                      static_cast<int64_t>(
                                        static_cast<uint32_t>(summary.startCoord >> 32)));
            replacementHash =
              sim_scan_digest_mix_i64(replacementHash,
                                      static_cast<int64_t>(
                                        static_cast<uint32_t>(summary.startCoord & 0xffffffffULL)));
            replacementHash =
              sim_scan_digest_mix_i64(replacementHash,static_cast<int64_t>(sharedInsertIndex));
            replacementHash =
              sim_scan_digest_mix_i64(replacementHash,static_cast<int64_t>(summary.score));
            localReplacementSequenceHash = replacementHash;
            ++localCandidateReplacementCount;
          }
        }
        __syncwarp();

        if(sharedNeedErase != 0)
        {
          sim_scan_candidate_hash_erase_warp(sharedEraseCoord,
                                             sharedHashCoords,
                                             sharedHashSlots,
                                             sharedHashTombstones);
        }

        if(tid == 0)
        {
          initSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[sharedInsertIndex]);
        }
        __syncwarp();

        if(!sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                                sharedInsertIndex,
                                                sharedHashCoords,
                                                sharedHashSlots,
                                                sharedHashTombstones))
        {
          sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                               sharedCandidateCount,
                                               sharedHashCoords,
                                               sharedHashSlots,
                                               sharedHashTombstones);
          sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                              sharedInsertIndex,
                                              sharedHashCoords,
                                              sharedHashSlots,
                                              sharedHashTombstones);
        }

        const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
        if(tid == 0)
        {
          sharedMinIndex = minIndex;
          sharedRunningMin = sharedCandidates[minIndex].score;
        }
        __syncwarp();

        if(sharedHashTombstones > sim_scan_candidate_hash_rebuild_tombstones)
        {
          sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                               sharedCandidateCount,
                                               sharedHashCoords,
                                               sharedHashSlots,
                                               sharedHashTombstones);
        }
      }
      else
      {
        if(tid == 0)
        {
          sharedImproved =
            updateSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[targetIndex]) ? 1 : 0;
        }
        __syncwarp();

        if(sharedImproved != 0 && targetIndex == sharedMinIndex)
        {
          const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
          if(tid == 0)
          {
            sharedMinIndex = minIndex;
            sharedRunningMin = sharedCandidates[minIndex].score;
          }
          __syncwarp();
        }
      }
      if(tid == 0)
      {
        const int candidateIndexAfter = targetIndex >= 0 ? targetIndex : sharedInsertIndex;
        const int indexInsert = targetIndex < 0 ? 1 : 0;
        const int indexErase =
          (targetIndex < 0 && candidateCountBefore == sim_scan_cuda_max_candidates) ? 1 : 0;
        if(indexInsert != 0)
        {
          ++localCandidateIndexInsertCount;
        }
        if(indexErase != 0)
        {
          ++localCandidateIndexEraseCount;
        }
        uint64_t visibilityHash = localCandidateIndexVisibilityHash;
        visibilityHash =
          sim_scan_digest_mix_u64(visibilityHash,static_cast<uint64_t>(summaryIndex));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,
                                  static_cast<int64_t>(
                                    static_cast<uint32_t>(summary.startCoord >> 32)));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,
                                  static_cast<int64_t>(
                                    static_cast<uint32_t>(summary.startCoord & 0xffffffffULL)));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(targetIndex));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(candidateIndexAfter));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(candidateCountBefore));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(sharedCandidateCount));
        visibilityHash =
          sim_scan_digest_mix_u64(visibilityHash,targetIndex >= 0 ? 1ULL : 0ULL);
        visibilityHash =
          sim_scan_digest_mix_u64(visibilityHash,targetIndex >= 0 ? 0ULL : 1ULL);
        visibilityHash =
          sim_scan_digest_mix_u64(visibilityHash,indexInsert != 0 ? 1ULL : 0ULL);
        visibilityHash =
          sim_scan_digest_mix_u64(visibilityHash,indexErase != 0 ? 1ULL : 0ULL);
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(runningMinSlotBefore));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(sharedMinIndex));
        visibilityHash =
          sim_scan_digest_mix_i64(visibilityHash,static_cast<int64_t>(summary.score));
        localCandidateIndexVisibilityHash = visibilityHash;
        if(runningMinBefore != sharedRunningMin)
        {
          uint64_t runningMinHash = localRunningMinUpdateSequenceHash;
          runningMinHash =
            sim_scan_digest_mix_u64(runningMinHash,static_cast<uint64_t>(summaryIndex));
          runningMinHash =
            sim_scan_digest_mix_i64(runningMinHash,static_cast<int64_t>(runningMinBefore));
          runningMinHash =
            sim_scan_digest_mix_i64(runningMinHash,static_cast<int64_t>(sharedRunningMin));
          localRunningMinUpdateSequenceHash = runningMinHash;
          ++localRunningMinUpdateCount;

          uint64_t floorHash = localFloorChangeSequenceHash;
          floorHash = sim_scan_digest_mix_u64(floorHash,static_cast<uint64_t>(summaryIndex));
          floorHash = sim_scan_digest_mix_i64(floorHash,static_cast<int64_t>(runningMinBefore));
          floorHash = sim_scan_digest_mix_i64(floorHash,static_cast<int64_t>(sharedRunningMin));
          localFloorChangeSequenceHash = floorHash;
          ++localFloorChangeCount;
        }
        if(runningMinSlotBefore != sharedMinIndex)
        {
          uint64_t slotHash = localRunningMinSlotUpdateSequenceHash;
          slotHash = sim_scan_digest_mix_u64(slotHash,static_cast<uint64_t>(summaryIndex));
          slotHash =
            sim_scan_digest_mix_i64(slotHash,static_cast<int64_t>(runningMinSlotBefore));
          slotHash = sim_scan_digest_mix_i64(slotHash,static_cast<int64_t>(sharedMinIndex));
          localRunningMinSlotUpdateSequenceHash = slotHash;
          ++localRunningMinSlotUpdateCount;
        }
      }
      __syncwarp();
    }
  }

  if(replayStats != NULL && tid == 0)
  {
    atomicAdd(replayStats + 0, localChunkCount);
    atomicAdd(replayStats + 1, localChunkReplayedCount);
    atomicAdd(replayStats + 2, localSummaryReplayCount);
  }
  if(tid == 0)
  {
    if(orderedMaintenanceDigestStats != NULL)
    {
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_replacement_sequence_hash_index] =
        localReplacementSequenceHash;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_running_min_sequence_hash_index] =
        localRunningMinUpdateSequenceHash;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_running_min_slot_sequence_hash_index] =
        localRunningMinSlotUpdateSequenceHash;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_floor_change_sequence_hash_index] =
        localFloorChangeSequenceHash;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_visibility_hash_index] =
        localCandidateIndexVisibilityHash;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_replacement_count_index] =
        localCandidateReplacementCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_running_min_update_count_index] =
        localRunningMinUpdateCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_running_min_slot_update_count_index] =
        localRunningMinSlotUpdateCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_floor_change_count_index] =
        localFloorChangeCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_existing_hit_count_index] =
        localCandidateIndexExistingHitCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_miss_count_index] =
        localCandidateIndexMissCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_insert_count_index] =
        localCandidateIndexInsertCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_erase_count_index] =
        localCandidateIndexEraseCount;
      orderedMaintenanceDigestStats[
        sim_scan_ordered_maintenance_digest_candidate_index_visibility_check_count_index] =
        localCandidateIndexVisibilityCheckCount;
    }
  }

  if(safeStoreStatesOut != NULL)
  {
    if(tid == 0)
    {
      sharedSafeStorePrunedCount = 0;
    }
    __syncwarp();
    for(int safeStoreIndex = tid;
        safeStoreIndex < sharedSafeStoreCount;
        safeStoreIndex += sim_scan_initial_reduce_threads)
    {
      const SimScanCudaCandidateState state = sharedSafeStoreStates[safeStoreIndex];
      const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
      const bool keepState =
        state.score > sharedRunningMin ||
        sim_scan_candidate_hash_find(startCoord,sharedHashCoords,sharedHashSlots) >= 0;
      if(keepState)
      {
        const int outputIndex = atomicAdd(&sharedSafeStorePrunedCount,1);
        safeStoreStatesOut[outputIndex] = state;
      }
    }
    __syncwarp();
    if(tid == 0 && safeStoreCountOut != NULL)
    {
      *safeStoreCountOut = sharedSafeStorePrunedCount;
    }
  }

  for(int candidateIndex = tid; candidateIndex < sharedCandidateCount; candidateIndex += sim_scan_initial_reduce_threads)
  {
    candidates[candidateIndex] = sharedCandidates[candidateIndex];
  }
  if(tid == 0)
  {
    *candidateCountInOut = sharedCandidateCount;
    *runningMinInOut = sharedRunningMin;
  }
}

__global__ void sim_scan_reduce_initial_candidate_states_true_batch_kernel(const SimScanCudaInitialRunSummary *summaries,
                                                                           const int *runBases,
                                                                           const int *runTotals,
                                                                           int batchSize,
                                                                           SimScanCudaCandidateState *batchCandidates,
                                                                           int *batchCandidateCounts,
                                                                           int *batchRunningMins,
                                                                           const int *chunkMaxScores,
                                                                           int maxChunksPerBatch,
                                                                           int chunkSize,
                                                                           unsigned long long *replayStats)
{
  const int batchIndex = static_cast<int>(blockIdx.x);
  if(batchIndex >= batchSize || threadIdx.x >= sim_scan_initial_reduce_threads)
  {
    return;
  }

  __shared__ SimScanCudaCandidateState sharedCandidates[sim_scan_cuda_max_candidates];
  __shared__ uint64_t sharedHashCoords[sim_scan_candidate_hash_capacity];
  __shared__ int sharedHashSlots[sim_scan_candidate_hash_capacity];
  __shared__ int sharedCandidateCount;
  __shared__ int sharedRunningMin;
  __shared__ int sharedMinIndex;
  __shared__ int sharedHashTombstones;
  __shared__ SimScanCudaInitialRunSummary sharedSummary;
  __shared__ int sharedInsertIndex;
  __shared__ int sharedNeedErase;
  __shared__ uint64_t sharedEraseCoord;
  __shared__ int sharedImproved;
  __shared__ int sharedReplayChunk;

  const int tid = static_cast<int>(threadIdx.x);
  const int candidateBase = batchIndex * sim_scan_cuda_max_candidates;
  const int summaryBase = runBases[batchIndex];
  const int summaryCount = runTotals[batchIndex];
  unsigned long long localChunkCount = 0;
  unsigned long long localChunkReplayedCount = 0;
  unsigned long long localSummaryReplayCount = 0;
  if(tid == 0)
  {
    int candidateCount = batchCandidateCounts[batchIndex];
    if(candidateCount < 0)
    {
      candidateCount = 0;
    }
    if(candidateCount > sim_scan_cuda_max_candidates)
    {
      candidateCount = sim_scan_cuda_max_candidates;
    }
    sharedCandidateCount = candidateCount;
    sharedRunningMin = 0;
    sharedMinIndex = -1;
    sharedHashTombstones = 0;
  }
  __syncwarp();

  for(int candidateIndex = tid; candidateIndex < sharedCandidateCount; candidateIndex += sim_scan_initial_reduce_threads)
  {
    sharedCandidates[candidateIndex] = batchCandidates[candidateBase + candidateIndex];
  }
  __syncwarp();

  if(sharedCandidateCount > 0)
  {
    const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
    if(tid == 0)
    {
      sharedMinIndex = minIndex;
      sharedRunningMin = sharedCandidates[minIndex].score;
    }
  }
  else if(tid == 0)
  {
    sharedMinIndex = -1;
    sharedRunningMin = 0;
  }
  __syncwarp();

  sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                       sharedCandidateCount,
                                       sharedHashCoords,
                                       sharedHashSlots,
                                       sharedHashTombstones);

  const int effectiveChunkSize = chunkSize > 0 ? chunkSize : (summaryCount > 0 ? summaryCount : 1);
  const int chunkCount = summaryCount > 0 ? ((summaryCount + effectiveChunkSize - 1) / effectiveChunkSize) : 0;
  for(int chunkIndex = 0; chunkIndex < chunkCount; ++chunkIndex)
  {
    const int localChunkStart = chunkIndex * effectiveChunkSize;
    const int localChunkEnd = min(localChunkStart + effectiveChunkSize, summaryCount);
    int localNeedsReplay = 0;
    for(int summaryOffset = localChunkStart + tid; summaryOffset < localChunkEnd; summaryOffset += sim_scan_initial_reduce_threads)
    {
      if(!sim_scan_initial_summary_is_noop(summaries[summaryBase + summaryOffset],
                                           sharedCandidates,
                                           sharedHashCoords,
                                           sharedHashSlots))
      {
        localNeedsReplay = 1;
        break;
      }
    }
    const int chunkNeedsReplay = __any_sync(0xffffffffu, localNeedsReplay != 0) ? 1 : 0;
    if(tid == 0)
    {
      ++localChunkCount;
      sharedReplayChunk = chunkNeedsReplay;
      if(sharedReplayChunk != 0)
      {
        ++localChunkReplayedCount;
        localSummaryReplayCount += static_cast<unsigned long long>(localChunkEnd - localChunkStart);
      }
    }
    __syncwarp();

    if(sharedReplayChunk == 0)
    {
      continue;
    }

    for(int summaryOffset = localChunkStart; summaryOffset < localChunkEnd; ++summaryOffset)
    {
      if(tid == 0)
      {
        sharedSummary = summaries[summaryBase + summaryOffset];
      }
      __syncwarp();

      const SimScanCudaInitialRunSummary summary = sharedSummary;
      const int targetIndex = sim_scan_candidate_hash_find_warp(summary.startCoord,
                                                                sharedHashCoords,
                                                                sharedHashSlots);
      if(targetIndex < 0)
      {
        if(tid == 0)
        {
          sharedNeedErase = 0;
          sharedEraseCoord = 0;
          if(sharedCandidateCount == sim_scan_cuda_max_candidates)
          {
            sharedInsertIndex = sharedMinIndex;
            sharedNeedErase = 1;
            sharedEraseCoord = simScanCudaCandidateStateStartCoord(sharedCandidates[sharedInsertIndex]);
          }
          else
          {
            sharedInsertIndex = sharedCandidateCount++;
          }
        }
        __syncwarp();

        if(sharedNeedErase != 0)
        {
          sim_scan_candidate_hash_erase_warp(sharedEraseCoord,
                                             sharedHashCoords,
                                             sharedHashSlots,
                                             sharedHashTombstones);
        }

        if(tid == 0)
        {
          initSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[sharedInsertIndex]);
        }
        __syncwarp();

        if(!sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                                sharedInsertIndex,
                                                sharedHashCoords,
                                                sharedHashSlots,
                                                sharedHashTombstones))
        {
          sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                               sharedCandidateCount,
                                               sharedHashCoords,
                                               sharedHashSlots,
                                               sharedHashTombstones);
          sim_scan_candidate_hash_insert_warp(summary.startCoord,
                                              sharedInsertIndex,
                                              sharedHashCoords,
                                              sharedHashSlots,
                                              sharedHashTombstones);
        }

        const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
        if(tid == 0)
        {
          sharedMinIndex = minIndex;
          sharedRunningMin = sharedCandidates[minIndex].score;
        }
        __syncwarp();

        if(sharedHashTombstones > sim_scan_candidate_hash_rebuild_tombstones)
        {
          sim_scan_candidate_hash_rebuild_warp(sharedCandidates,
                                               sharedCandidateCount,
                                               sharedHashCoords,
                                               sharedHashSlots,
                                               sharedHashTombstones);
        }
      }
      else
      {
        if(tid == 0)
        {
          sharedImproved =
            updateSimScanCudaCandidateStateFromInitialRunSummary(summary,sharedCandidates[targetIndex]) ? 1 : 0;
        }
        __syncwarp();

        if(sharedImproved != 0 && targetIndex == sharedMinIndex)
        {
          const int minIndex = sim_scan_candidate_min_index_warp(sharedCandidates,sharedCandidateCount);
          if(tid == 0)
          {
            sharedMinIndex = minIndex;
            sharedRunningMin = sharedCandidates[minIndex].score;
          }
          __syncwarp();
        }
      }
    }
  }

  if(replayStats != NULL && tid == 0)
  {
    atomicAdd(replayStats + 0, localChunkCount);
    atomicAdd(replayStats + 1, localChunkReplayedCount);
    atomicAdd(replayStats + 2, localSummaryReplayCount);
  }

  for(int candidateIndex = tid; candidateIndex < sharedCandidateCount; candidateIndex += sim_scan_initial_reduce_threads)
  {
    batchCandidates[candidateBase + candidateIndex] = sharedCandidates[candidateIndex];
  }
  if(tid == 0)
  {
    batchCandidateCounts[batchIndex] = sharedCandidateCount;
    batchRunningMins[batchIndex] = sharedRunningMin;
  }
}

__global__ void sim_scan_init_candidate_reduce_states_from_summaries_kernel(const SimScanCudaInitialRunSummary *summaries,
                                                                            int summaryCount,
                                                                            uint64_t *summaryKeys,
                                                                            SimScanCudaCandidateReduceState *reduceStates)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= summaryCount)
  {
    return;
  }
  summaryKeys[idx] = summaries[idx].startCoord;
  initSimScanCudaCandidateReduceStateFromInitialRunSummary(summaries[idx],
                                                           static_cast<uint32_t>(idx),
                                                           reduceStates[idx]);
}

__global__ void sim_scan_init_candidate_reduce_states_from_candidate_states_kernel(const SimScanCudaCandidateState *candidateStates,
                                                                                   int candidateCount,
                                                                                   uint64_t *candidateKeys,
                                                                                   SimScanCudaCandidateReduceState *reduceStates,
                                                                                   uint32_t orderBase)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= candidateCount)
  {
    return;
  }
  candidateKeys[idx] = simScanCudaCandidateStateStartCoord(candidateStates[idx]);
  initSimScanCudaCandidateReduceStateFromCandidateState(candidateStates[idx],
                                                        orderBase + static_cast<uint32_t>(idx),
                                                        reduceStates[idx]);
}

__global__ void sim_scan_init_batch_candidate_reduce_states_from_summaries_kernel(const SimScanCudaInitialRunSummary *summaries,
                                                                                  const int *runBases,
                                                                                  const int *runTotals,
                                                                                  int maxRunsPerBatch,
                                                                                  SimScanCudaBatchCandidateReduceKey *summaryKeys,
                                                                                  SimScanCudaCandidateReduceState *reduceStates)
{
  const int localIndex = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  const int batchIndex = static_cast<int>(blockIdx.y);
  if(localIndex >= maxRunsPerBatch)
  {
    return;
  }

  const int summaryCount = runTotals[batchIndex];
  if(localIndex >= summaryCount)
  {
    return;
  }

  const int summaryIndex = runBases[batchIndex] + localIndex;
  summaryKeys[summaryIndex].batchIndex = static_cast<uint32_t>(batchIndex);
  summaryKeys[summaryIndex].startCoord = summaries[summaryIndex].startCoord;
  initSimScanCudaCandidateReduceStateFromInitialRunSummary(summaries[summaryIndex],
                                                           static_cast<uint32_t>(summaryIndex),
                                                           reduceStates[summaryIndex]);
}

__global__ void sim_scan_hash_reduce_candidate_states_true_batch_kernel(
  const SimScanCudaBatchCandidateReduceKey *inputKeys,
  const SimScanCudaCandidateReduceState *inputStates,
  int stateCount,
  SimScanCudaBatchCandidateReduceKey *hashKeys,
  int *hashFlags,
  SimScanCudaCandidateReduceState *hashStates,
  size_t hashCapacity,
  int *overflowFlag)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount || atomicAdd(overflowFlag,0) != 0)
  {
    return;
  }

  sim_scan_batch_candidate_reduce_hash_merge_state(inputKeys[idx],
                                                   inputStates[idx],
                                                   hashKeys,
                                                   hashFlags,
                                                   hashStates,
                                                   hashCapacity,
                                                   overflowFlag);
}

__global__ void sim_scan_count_batch_hash_reduce_states_kernel(const SimScanCudaBatchCandidateReduceKey *hashKeys,
                                                               const int *hashFlags,
                                                               size_t hashCapacity,
                                                               int *batchCounts)
{
  const size_t slot = static_cast<size_t>(blockIdx.x) * static_cast<size_t>(blockDim.x) +
                      static_cast<size_t>(threadIdx.x);
  if(slot >= hashCapacity || hashFlags[slot] != sim_scan_online_hash_flag_ready)
  {
    return;
  }

  atomicAdd(batchCounts + hashKeys[slot].batchIndex,1);
}

__global__ void sim_scan_compact_batch_hash_reduce_states_kernel(const SimScanCudaBatchCandidateReduceKey *hashKeys,
                                                                 const int *hashFlags,
                                                                 const SimScanCudaCandidateReduceState *hashStates,
                                                                 size_t hashCapacity,
                                                                 const int *batchOutputBases,
                                                                 int *batchOutputCursors,
                                                                 SimScanCudaBatchCandidateReduceKey *outputKeys,
                                                                 SimScanCudaCandidateReduceState *outputStates)
{
  const size_t slot = static_cast<size_t>(blockIdx.x) * static_cast<size_t>(blockDim.x) +
                      static_cast<size_t>(threadIdx.x);
  if(slot >= hashCapacity || hashFlags[slot] != sim_scan_online_hash_flag_ready)
  {
    return;
  }

  const int batchIndex = static_cast<int>(hashKeys[slot].batchIndex);
  const int localIndex = atomicAdd(batchOutputCursors + batchIndex,1);
  const int outputIndex = batchOutputBases[batchIndex] + localIndex;
  outputKeys[outputIndex] = hashKeys[slot];
  outputStates[outputIndex] = hashStates[slot];
}

__device__ __forceinline__ bool sim_scan_keep_safe_store_candidate_state(const SimScanCudaCandidateState &state,
                                                                         const SimScanCudaCandidateState *finalCandidates,
                                                                         int finalCandidateCount,
                                                                         int runningMin)
{
  if(state.score > runningMin)
  {
    return true;
  }
  const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
  for(int candidateIndex = 0; candidateIndex < finalCandidateCount; ++candidateIndex)
  {
    if(simScanCudaCandidateStateStartCoord(finalCandidates[candidateIndex]) == startCoord)
    {
      return true;
    }
  }
  return false;
}

__global__ void sim_scan_filter_initial_safe_store_candidate_states_kernel(const SimScanCudaCandidateReduceState *reduceStates,
                                                                           int candidateCount,
                                                                           const SimScanCudaCandidateState *finalCandidates,
                                                                           int finalCandidateCount,
                                                                           int runningMin,
                                                                           SimScanCudaCandidateState *outStates,
                                                                           int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= candidateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = reduceStates[idx].candidate;
  if(!sim_scan_keep_safe_store_candidate_state(candidate,
                                               finalCandidates,
                                               finalCandidateCount,
                                               runningMin))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = candidate;
}

__global__ void sim_scan_count_batch_initial_safe_store_candidate_states_kernel(const SimScanCudaBatchCandidateReduceKey *keys,
                                                                                const SimScanCudaCandidateReduceState *states,
                                                                                int stateCount,
                                                                                const SimScanCudaCandidateState *batchFinalCandidates,
                                                                                const int *batchFinalCandidateCounts,
                                                                                const int *batchRunningMins,
                                                                                int *batchCounts)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const int batchIndex = static_cast<int>(keys[idx].batchIndex);
  if(batchFinalCandidates == NULL ||
     batchFinalCandidateCounts == NULL ||
     batchRunningMins == NULL)
  {
    atomicAdd(batchCounts + batchIndex,1);
    return;
  }
  int finalCandidateCount = batchFinalCandidateCounts[batchIndex];
  if(finalCandidateCount < 0)
  {
    finalCandidateCount = 0;
  }
  if(finalCandidateCount > sim_scan_cuda_max_candidates)
  {
    finalCandidateCount = sim_scan_cuda_max_candidates;
  }
  const SimScanCudaCandidateState candidate = states[idx].candidate;
  if(!sim_scan_keep_safe_store_candidate_state(candidate,
                                               batchFinalCandidates + static_cast<size_t>(batchIndex) * sim_scan_cuda_max_candidates,
                                               finalCandidateCount,
                                               batchRunningMins[batchIndex]))
  {
    return;
  }
  atomicAdd(batchCounts + batchIndex,1);
}

__global__ void sim_scan_compact_batch_initial_safe_store_candidate_states_kernel(const SimScanCudaBatchCandidateReduceKey *keys,
                                                                                  const SimScanCudaCandidateReduceState *states,
                                                                                  int stateCount,
                                                                                  const SimScanCudaCandidateState *batchFinalCandidates,
                                                                                  const int *batchFinalCandidateCounts,
                                                                                  const int *batchRunningMins,
                                                                                  const int *batchOutputBases,
                                                                                  int *batchOutputCursors,
                                                                                  SimScanCudaCandidateState *outputStates)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const int batchIndex = static_cast<int>(keys[idx].batchIndex);
  if(batchFinalCandidates == NULL ||
     batchFinalCandidateCounts == NULL ||
     batchRunningMins == NULL)
  {
    const int localIndex = atomicAdd(batchOutputCursors + batchIndex,1);
    outputStates[batchOutputBases[batchIndex] + localIndex] = states[idx].candidate;
    return;
  }
  int finalCandidateCount = batchFinalCandidateCounts[batchIndex];
  if(finalCandidateCount < 0)
  {
    finalCandidateCount = 0;
  }
  if(finalCandidateCount > sim_scan_cuda_max_candidates)
  {
    finalCandidateCount = sim_scan_cuda_max_candidates;
  }
  const SimScanCudaCandidateState candidate = states[idx].candidate;
  if(!sim_scan_keep_safe_store_candidate_state(candidate,
                                               batchFinalCandidates + static_cast<size_t>(batchIndex) * sim_scan_cuda_max_candidates,
                                               finalCandidateCount,
                                               batchRunningMins[batchIndex]))
  {
    return;
  }
  const int localIndex = atomicAdd(batchOutputCursors + batchIndex,1);
  outputStates[batchOutputBases[batchIndex] + localIndex] = candidate;
}

__device__ __forceinline__ bool sim_scan_contains_sorted_start_coord(const uint64_t *coords,
                                                                     int coordCount,
                                                                     uint64_t startCoord)
{
  int lo = 0;
  int hi = coordCount;
  while(lo < hi)
  {
    const int mid = lo + ((hi - lo) >> 1);
    const uint64_t value = coords[mid];
    if(value < startCoord)
    {
      lo = mid + 1;
    }
    else
    {
      hi = mid;
    }
  }
  return lo < coordCount && coords[lo] == startCoord;
}

__device__ __forceinline__ int sim_scan_find_sorted_start_coord_index(const uint64_t *coords,
                                                                      int coordCount,
                                                                      uint64_t startCoord)
{
  int lo = 0;
  int hi = coordCount;
  while(lo < hi)
  {
    const int mid = lo + ((hi - lo) >> 1);
    const uint64_t value = coords[mid];
    if(value < startCoord)
    {
      lo = mid + 1;
    }
    else
    {
      hi = mid;
    }
  }
  if(lo < coordCount && coords[lo] == startCoord)
  {
    return lo;
  }
  return -1;
}

__device__ __forceinline__ bool sim_scan_candidate_state_intersects_path_summary_device(const SimScanCudaCandidateState &candidate,
                                                                                         int summaryRowStart,
                                                                                         const int *rowMinCols,
                                                                                         const int *rowMaxCols,
                                                                                         int rowCount)
{
  const int summaryRowEnd = summaryRowStart + rowCount - 1;
  const int overlapRowStart = max(candidate.startI, summaryRowStart);
  const int overlapRowEnd = min(candidate.bot, summaryRowEnd);
  if(overlapRowEnd < overlapRowStart)
  {
    return false;
  }
  for(int row = overlapRowStart; row <= overlapRowEnd; ++row)
  {
    const int rowIndex = row - summaryRowStart;
    if(rowIndex < 0 || rowIndex >= rowCount)
    {
      break;
    }
    if(rowMinCols[rowIndex] <= candidate.right &&
       rowMaxCols[rowIndex] >= candidate.startJ)
    {
      return true;
    }
  }
  return false;
}

__device__ __forceinline__ bool sim_scan_clamp_candidate_bounds_device(const SimScanCudaCandidateState &candidate,
                                                                       int queryLength,
                                                                       int targetLength,
                                                                       int &rowStart,
                                                                       int &rowEnd,
                                                                       int &colStart,
                                                                       int &colEnd)
{
  if(candidate.startI < 1 ||
     candidate.startJ < 1 ||
     candidate.bot < candidate.startI ||
     candidate.right < candidate.startJ)
  {
    return false;
  }

  rowStart = max(1, min(candidate.startI, queryLength));
  rowEnd = max(rowStart, min(candidate.bot, queryLength));
  colStart = max(1, min(candidate.startJ, targetLength));
  colEnd = max(colStart, min(candidate.right, targetLength));
  return true;
}

__device__ __forceinline__ bool sim_scan_candidate_state_intersects_row_intervals_device(const SimScanCudaCandidateState &candidate,
                                                                                          int queryLength,
                                                                                          int targetLength,
                                                                                          const int *rowOffsets,
                                                                                          const SimScanCudaColumnInterval *intervals)
{
  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return false;
  }

  for(int row = rowStart; row <= rowEnd; ++row)
  {
    const int intervalStart = rowOffsets[row];
    const int intervalEnd = rowOffsets[row + 1];
    for(int intervalIndex = intervalStart; intervalIndex < intervalEnd; ++intervalIndex)
    {
      const SimScanCudaColumnInterval interval = intervals[intervalIndex];
      if(interval.colStart > colEnd)
      {
        break;
      }
      if(interval.colEnd >= colStart)
      {
        return true;
      }
    }
  }
  return false;
}

__device__ __forceinline__ bool sim_scan_candidate_state_intersects_dense_row_ranges_device(const SimScanCudaCandidateState &candidate,
                                                                                             int queryLength,
                                                                                             int targetLength,
                                                                                             const int *rowMinCols,
                                                                                             const int *rowMaxCols)
{
  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return false;
  }

  for(int row = rowStart; row <= rowEnd; ++row)
  {
    if(rowMinCols[row] <= colEnd &&
       rowMaxCols[row] >= colStart)
    {
      return true;
    }
  }
  return false;
}

__global__ void sim_scan_initialize_dense_row_ranges_kernel(int *rowMinCols,
                                                            int *rowMaxCols,
                                                            int rowCount,
                                                            int emptyMinValue)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= rowCount)
  {
    return;
  }
  rowMinCols[idx] = emptyMinValue;
  rowMaxCols[idx] = 0;
}

__global__ void sim_scan_accumulate_persistent_safe_store_seed_row_ranges_kernel(const SimScanCudaCandidateState *states,
                                                                                 int stateCount,
                                                                                 int queryLength,
                                                                                 int targetLength,
                                                                                 int summaryRowStart,
                                                                                 const int *summaryRowMinCols,
                                                                                 const int *summaryRowMaxCols,
                                                                                 int summaryRowCount,
                                                                                 int *seedRowMinCols,
                                                                                 int *seedRowMaxCols)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_candidate_state_intersects_path_summary_device(candidate,
                                                              summaryRowStart,
                                                              summaryRowMinCols,
                                                              summaryRowMaxCols,
                                                              summaryRowCount))
  {
    return;
  }

  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return;
  }

  for(int row = rowStart; row <= rowEnd; ++row)
  {
    atomicMin(&seedRowMinCols[row],colStart);
    atomicMax(&seedRowMaxCols[row],colEnd);
  }
}

__global__ void sim_scan_collect_persistent_safe_store_safe_windows_kernel(const SimScanCudaCandidateState *states,
                                                                           int stateCount,
                                                                           int queryLength,
                                                                           int targetLength,
                                                                           const int *seedRowMinCols,
                                                                           const int *seedRowMaxCols,
                                                                           int *outRowMinCols,
                                                                           int *outRowMaxCols,
                                                                           uint64_t *outStartCoords,
                                                                           int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_candidate_state_intersects_dense_row_ranges_device(candidate,
                                                                  queryLength,
                                                                  targetLength,
                                                                  seedRowMinCols,
                                                                  seedRowMaxCols))
  {
    return;
  }

  const int outIndex = atomicAdd(outCount,1);
  outStartCoords[outIndex] = simScanCudaCandidateStateStartCoord(candidate);

  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return;
  }
  for(int row = rowStart; row <= rowEnd; ++row)
  {
    atomicMin(&outRowMinCols[row],colStart);
    atomicMax(&outRowMaxCols[row],colEnd);
  }
}

__global__ void sim_scan_filter_persistent_safe_store_by_path_summary_kernel(const SimScanCudaCandidateState *states,
                                                                             int stateCount,
                                                                             int summaryRowStart,
                                                                             const int *rowMinCols,
                                                                             const int *rowMaxCols,
                                                                             int rowCount,
                                                                             SimScanCudaCandidateState *outStates,
                                                                             int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_candidate_state_intersects_path_summary_device(candidate,
                                                              summaryRowStart,
                                                              rowMinCols,
                                                              rowMaxCols,
                                                              rowCount))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = candidate;
}

__global__ void sim_scan_filter_persistent_safe_store_by_row_intervals_kernel(const SimScanCudaCandidateState *states,
                                                                              int stateCount,
                                                                              int queryLength,
                                                                              int targetLength,
                                                                              const int *rowOffsets,
                                                                              const SimScanCudaColumnInterval *intervals,
                                                                              SimScanCudaCandidateState *outStates,
                                                                              int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_candidate_state_intersects_row_intervals_device(candidate,
                                                               queryLength,
                                                               targetLength,
                                                               rowOffsets,
                                                               intervals))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = candidate;
}

__global__ void sim_scan_filter_persistent_safe_store_start_coords_by_row_intervals_kernel(
  const SimScanCudaCandidateState *states,
  int stateCount,
  int queryLength,
  int targetLength,
  const int *rowOffsets,
  const SimScanCudaColumnInterval *intervals,
  uint64_t *outStartCoords,
  int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_candidate_state_intersects_row_intervals_device(candidate,
                                                               queryLength,
                                                               targetLength,
                                                               rowOffsets,
                                                               intervals))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStartCoords[outIndex] = simScanCudaCandidateStateStartCoord(candidate);
}

__global__ void sim_scan_count_candidate_row_contributions_kernel(const SimScanCudaCandidateState *states,
                                                                  int stateCount,
                                                                  int queryLength,
                                                                  int targetLength,
                                                                  int *rowCounts)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(states[idx],queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    rowCounts[idx] = 0;
    return;
  }
  rowCounts[idx] = rowEnd - rowStart + 1;
}

__global__ void sim_scan_emit_candidate_row_intervals_kernel(const SimScanCudaCandidateState *states,
                                                             int stateCount,
                                                             int queryLength,
                                                             int targetLength,
                                                             const int *stateOffsets,
                                                             uint64_t *outKeys,
                                                             SimScanCudaColumnInterval *outIntervals)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  int rowStart = 0;
  int rowEnd = 0;
  int colStart = 0;
  int colEnd = 0;
  if(!sim_scan_clamp_candidate_bounds_device(states[idx],queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return;
  }
  const int base = stateOffsets[idx];
  for(int row = rowStart; row <= rowEnd; ++row)
  {
    const int writeIndex = base + (row - rowStart);
    outKeys[writeIndex] =
      (static_cast<uint64_t>(static_cast<uint32_t>(row)) << 32) |
      static_cast<uint64_t>(static_cast<uint32_t>(colStart));
    outIntervals[writeIndex] = SimScanCudaColumnInterval(colStart,colEnd);
  }
}

__global__ void sim_scan_merge_sparse_row_intervals_kernel(uint64_t *keys,
                                                           SimScanCudaColumnInterval *intervals,
                                                           int intervalCount,
                                                           int queryLength,
                                                           int *rowOffsets,
                                                           int *mergedCountOut)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }

  int writeIndex = 0;
  int nextRowToFill = 0;
  for(int row = 0; row <= queryLength + 1; ++row)
  {
    rowOffsets[row] = 0;
  }

  for(int readIndex = 0; readIndex < intervalCount; ++readIndex)
  {
    const int row = static_cast<int>(keys[readIndex] >> 32);
    if(row < 1 || row > queryLength)
    {
      continue;
    }
    const SimScanCudaColumnInterval interval = intervals[readIndex];
    const bool sameRow = writeIndex > 0 && static_cast<int>(keys[writeIndex - 1] >> 32) == row;
    if(!sameRow || interval.colStart > intervals[writeIndex - 1].colEnd + 1)
    {
      while(nextRowToFill <= row)
      {
        rowOffsets[nextRowToFill] = writeIndex;
        ++nextRowToFill;
      }
      keys[writeIndex] = keys[readIndex];
      intervals[writeIndex] = interval;
      ++writeIndex;
      continue;
    }
    if(interval.colEnd > intervals[writeIndex - 1].colEnd)
    {
      intervals[writeIndex - 1].colEnd = interval.colEnd;
    }
  }

  while(nextRowToFill <= queryLength + 1)
  {
    rowOffsets[nextRowToFill] = writeIndex;
    ++nextRowToFill;
  }
  *mergedCountOut = writeIndex;
}

__global__ void sim_scan_collect_candidate_start_coords_kernel(const SimScanCudaCandidateState *states,
                                                               int stateCount,
                                                               uint64_t *outStartCoords)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  outStartCoords[idx] = simScanCudaCandidateStateStartCoord(states[idx]);
}

__global__ void sim_scan_update_persistent_safe_store_states_kernel(SimScanCudaCandidateState *states,
                                                                    int stateCount,
                                                                    const uint64_t *updatedKeys,
                                                                    const SimScanCudaCandidateState *updatedStates,
                                                                    int updatedStateCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const uint64_t startCoord = simScanCudaCandidateStateStartCoord(states[idx]);
  const int updatedIndex = sim_scan_find_sorted_start_coord_index(updatedKeys,updatedStateCount,startCoord);
  if(updatedIndex >= 0)
  {
    states[idx] = updatedStates[updatedIndex];
  }
}

__global__ void sim_scan_filter_existing_safe_store_candidate_states_kernel(const SimScanCudaCandidateState *states,
                                                                            int stateCount,
                                                                            const SimScanCudaCandidateState *finalCandidates,
                                                                            int finalCandidateCount,
                                                                            int runningMin,
                                                                            SimScanCudaCandidateState *outStates,
                                                                            int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  if(!sim_scan_keep_safe_store_candidate_state(candidate,
                                               finalCandidates,
                                               finalCandidateCount,
                                               runningMin))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = candidate;
}

__global__ void sim_scan_filter_persistent_safe_store_excluding_start_coords_kernel(
  const SimScanCudaCandidateState *states,
  int stateCount,
  const uint64_t *excludedStartCoords,
  int excludedStartCoordCount,
  SimScanCudaCandidateState *outStates,
  int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= stateCount)
  {
    return;
  }
  const SimScanCudaCandidateState candidate = states[idx];
  const uint64_t startCoord = simScanCudaCandidateStateStartCoord(candidate);
  if(sim_scan_contains_sorted_start_coord(excludedStartCoords,
                                          excludedStartCoordCount,
                                          startCoord))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = candidate;
}

__global__ void sim_scan_extract_candidate_states_kernel(const SimScanCudaCandidateReduceState *reduceStates,
                                                         int candidateCount,
                                                         SimScanCudaCandidateState *outStates)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= candidateCount)
  {
    return;
  }
  outStates[idx] = reduceStates[idx].candidate;
}

__global__ void sim_scan_filter_candidate_states_by_allowed_start_coords_kernel(const uint64_t *candidateKeys,
                                                                                const SimScanCudaCandidateReduceState *reduceStates,
                                                                                int candidateCount,
                                                                                const uint64_t *allowedStartCoords,
                                                                                int allowedStartCoordCount,
                                                                                SimScanCudaCandidateState *outStates,
                                                                                int *outCount)
{
  const int idx = static_cast<int>(blockIdx.x * blockDim.x + threadIdx.x);
  if(idx >= candidateCount)
  {
    return;
  }
  if(!sim_scan_contains_sorted_start_coord(allowedStartCoords,
                                           allowedStartCoordCount,
                                           candidateKeys[idx]))
  {
    return;
  }
  const int outIndex = atomicAdd(outCount,1);
  outStates[outIndex] = reduceStates[idx].candidate;
}

static bool sim_scan_prepare_all_candidate_states_from_summaries(SimScanCudaContext *context,
                                                                 const SimScanCudaInitialRunSummary *summariesDevice,
                                                                 int summaryCount,
                                                                 const SimScanCudaCandidateState *finalCandidateStatesDevice,
                                                                 int finalCandidateCount,
                                                                 int runningMin,
                                                                 int *outCandidateCount,
                                                                 string *errorOut)
{
  if(outCandidateCount == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing reduced all-candidate count output";
    }
    return false;
  }
  *outCandidateCount = 0;
  if(context == NULL || summaryCount <= 0)
  {
    return true;
  }

  const size_t stateCount = static_cast<size_t>(summaryCount);
  if(!ensure_sim_scan_cuda_buffer(&context->summaryKeysDevice,
                                  &context->summaryKeysCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reducedKeysDevice,
                                  &context->reducedKeysCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                  &context->reduceStatesCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reducedStatesDevice,
                                  &context->reducedStatesCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  stateCount,
                                  errorOut))
  {
    return false;
  }

  const int reduceThreads = 256;
  const int reduceBlocks = (summaryCount + reduceThreads - 1) / reduceThreads;
  sim_scan_init_candidate_reduce_states_from_summaries_kernel<<<reduceBlocks, reduceThreads>>>(summariesDevice,
                                                                                                summaryCount,
                                                                                                context->summaryKeysDevice,
                                                                                                context->reduceStatesDevice);
  cudaError_t status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int reducedCandidateCount = 0;
  try
  {
    thrust::device_ptr<uint64_t> summaryKeysBegin = thrust::device_pointer_cast(context->summaryKeysDevice);
    thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
      thrust::device_pointer_cast(context->reduceStatesDevice);
    thrust::stable_sort_by_key(thrust::device,
                               summaryKeysBegin,
                               summaryKeysBegin + summaryCount,
                               reduceStatesBegin);
    thrust::pair< thrust::device_ptr<uint64_t>, thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
      thrust::reduce_by_key(thrust::device,
                            summaryKeysBegin,
                            summaryKeysBegin + summaryCount,
                            reduceStatesBegin,
                            thrust::device_pointer_cast(context->reducedKeysDevice),
                            thrust::device_pointer_cast(context->reducedStatesDevice),
                            thrust::equal_to<uint64_t>(),
                            SimScanCudaCandidateReduceMergeOp());
    reducedCandidateCount =
      static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->reducedKeysDevice));
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  catch(const std::exception &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA reduced candidate count overflow";
    }
    return false;
  }

  int outputCandidateCount = 0;
  if(reducedCandidateCount > 0)
  {
    const int extractThreads = 256;
    const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
    status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    sim_scan_filter_initial_safe_store_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->reducedStatesDevice,
                                                                                                   reducedCandidateCount,
                                                                                                   finalCandidateStatesDevice,
                                                                                                   finalCandidateCount,
                                                                                                   runningMin,
                                                                                                   context->outputCandidateStatesDevice,
                                                                                                   context->filteredCandidateCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    status = cudaMemcpy(&outputCandidateCount,
                        context->filteredCandidateCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  if(outputCandidateCount < 0 || outputCandidateCount > reducedCandidateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA filtered candidate count overflow";
    }
    return false;
  }
  *outCandidateCount = outputCandidateCount;
  return true;
}

static bool sim_scan_init_batch_candidate_reduce_states_from_summaries(SimScanCudaContext *context,
                                                                       const SimScanCudaInitialRunSummary *summariesDevice,
                                                                       int summaryCount,
                                                                       const int *runBasesDevice,
                                                                       const int *runTotalsDevice,
                                                                       int batchSize,
                                                                       int maxRunsPerBatch,
                                                                       string *errorOut)
{
  if(context == NULL || summaryCount <= 0 || batchSize <= 0 || maxRunsPerBatch <= 0)
  {
    return true;
  }

  const size_t stateCount = static_cast<size_t>(summaryCount);
  if(!ensure_sim_scan_cuda_buffer(&context->batchSummaryKeysDevice,
                                  &context->batchSummaryKeysCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchReducedKeysDevice,
                                  &context->batchReducedKeysCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                  &context->reduceStatesCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reducedStatesDevice,
                                  &context->reducedStatesCapacity,
                                  stateCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchAllCandidateCountsDevice,
                                  &context->batchAllCandidateCountsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }

  const int reduceThreads = 256;
  const int reduceBlocks = (maxRunsPerBatch + reduceThreads - 1) / reduceThreads;
  sim_scan_init_batch_candidate_reduce_states_from_summaries_kernel<<<dim3(static_cast<unsigned int>(reduceBlocks),
                                                                           static_cast<unsigned int>(batchSize)),
                                                                     reduceThreads>>>(summariesDevice,
                                                                                      runBasesDevice,
                                                                                      runTotalsDevice,
                                                                                      maxRunsPerBatch,
                                                                                      context->batchSummaryKeysDevice,
                                                                                      context->reduceStatesDevice);
  const cudaError_t status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_reduce_candidate_states_from_summaries_true_batch_segmented(SimScanCudaContext *context,
                                                                                 const SimScanCudaInitialRunSummary *summariesDevice,
                                                                                 int summaryCount,
                                                                                 const int *runBasesDevice,
                                                                                 const int *runTotalsDevice,
                                                                                 int batchSize,
                                                                                 int maxRunsPerBatch,
                                                                                 int *outReducedCandidateCount,
                                                                                 double *outReduceSeconds,
                                                                                 string *errorOut)
{
  if(outReducedCandidateCount == NULL || outReduceSeconds == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing segmented reduce outputs";
    }
    return false;
  }
  *outReducedCandidateCount = 0;
  *outReduceSeconds = 0.0;
  if(context == NULL || summariesDevice == NULL || summaryCount <= 0 || batchSize <= 0 || maxRunsPerBatch <= 0)
  {
    return true;
  }
  if(!sim_scan_init_batch_candidate_reduce_states_from_summaries(context,
                                                                 summariesDevice,
                                                                 summaryCount,
                                                                 runBasesDevice,
                                                                 runTotalsDevice,
                                                                 batchSize,
                                                                 maxRunsPerBatch,
                                                                 errorOut))
  {
    return false;
  }

  if(!sim_scan_cuda_begin_aux_timing(context,errorOut))
  {
    return false;
  }

  int reducedCandidateCount = 0;
  try
  {
    thrust::device_ptr<SimScanCudaBatchCandidateReduceKey> summaryKeysBegin =
      thrust::device_pointer_cast(context->batchSummaryKeysDevice);
    thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
      thrust::device_pointer_cast(context->reduceStatesDevice);
    thrust::stable_sort_by_key(thrust::device,
                               summaryKeysBegin,
                               summaryKeysBegin + summaryCount,
                               reduceStatesBegin,
                               SimScanCudaBatchCandidateReduceKeyLess());
    thrust::pair< thrust::device_ptr<SimScanCudaBatchCandidateReduceKey>,
                  thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
      thrust::reduce_by_key(thrust::device,
                            summaryKeysBegin,
                            summaryKeysBegin + summaryCount,
                            reduceStatesBegin,
                            thrust::device_pointer_cast(context->batchReducedKeysDevice),
                            thrust::device_pointer_cast(context->reducedStatesDevice),
                            SimScanCudaBatchCandidateReduceKeyEqual(),
                            SimScanCudaCandidateReduceMergeOp());
    reducedCandidateCount =
      static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->batchReducedKeysDevice));
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  catch(const std::exception &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  if(!sim_scan_cuda_end_aux_timing(context,outReduceSeconds,errorOut))
  {
    return false;
  }
  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched segmented reduced candidate count overflow";
    }
    return false;
  }

  *outReducedCandidateCount = reducedCandidateCount;
  return true;
}

static bool sim_scan_compact_batch_initial_safe_store_candidate_states_from_reduced_states(
  SimScanCudaContext *context,
  int reducedCandidateCount,
  int batchSize,
  const SimScanCudaCandidateState *batchFinalCandidateStatesDevice,
  const int *batchFinalCandidateCountsDevice,
  const int *batchRunningMinsDevice,
  int *outTotalCandidateCount,
  vector<int> *outCandidateCounts,
  vector<int> *outCandidateBases,
  double *outCompactSeconds,
  string *errorOut)
{
  if(outTotalCandidateCount == NULL ||
     outCandidateCounts == NULL ||
     outCandidateBases == NULL ||
     outCompactSeconds == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batched all-candidate outputs";
    }
    return false;
  }
  *outTotalCandidateCount = 0;
  *outCompactSeconds = 0.0;
  outCandidateCounts->assign(static_cast<size_t>(max(batchSize,0)),0);
  outCandidateBases->assign(static_cast<size_t>(max(batchSize,0)),0);
  if(context == NULL || reducedCandidateCount <= 0 || batchSize <= 0)
  {
    return true;
  }
  const chrono::steady_clock::time_point compactWallStart = chrono::steady_clock::now();

  cudaError_t status =
    cudaMemset(context->batchAllCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int extractThreads = 256;
  const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
  sim_scan_count_batch_initial_safe_store_candidate_states_kernel<<<extractBlocks, extractThreads>>>(
    context->batchReducedKeysDevice,
    context->reducedStatesDevice,
    reducedCandidateCount,
    batchFinalCandidateStatesDevice,
    batchFinalCandidateCountsDevice,
    batchRunningMinsDevice,
    context->batchAllCandidateCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  static_cast<size_t>(reducedCandidateCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchOutputCursorsDevice,
                                  &context->batchOutputCursorsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_begin_aux_timing(context,errorOut))
  {
    return false;
  }
  try
  {
    thrust::exclusive_scan(thrust::device,
                           thrust::device_pointer_cast(context->batchAllCandidateCountsDevice),
                           thrust::device_pointer_cast(context->batchAllCandidateCountsDevice) + batchSize,
                           thrust::device_pointer_cast(context->batchEventBasesDevice));
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  status = cudaMemset(context->batchOutputCursorsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  sim_scan_compact_batch_initial_safe_store_candidate_states_kernel<<<extractBlocks, extractThreads>>>(
    context->batchReducedKeysDevice,
    context->reducedStatesDevice,
    reducedCandidateCount,
    batchFinalCandidateStatesDevice,
    batchFinalCandidateCountsDevice,
    batchRunningMinsDevice,
    context->batchEventBasesDevice,
    context->batchOutputCursorsDevice,
    context->outputCandidateStatesDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(!sim_scan_cuda_end_aux_timing(context,outCompactSeconds,errorOut))
  {
    return false;
  }
  status = cudaMemcpy(outCandidateCounts->data(),
                      context->batchAllCandidateCountsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(outCandidateBases->data(),
                        context->batchEventBasesDevice,
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  int accumulatedCandidateCount = 0;
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int count = (*outCandidateCounts)[static_cast<size_t>(batchIndex)];
    if(count < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched reduced candidate count underflow";
      }
      return false;
    }
    if((*outCandidateBases)[static_cast<size_t>(batchIndex)] != accumulatedCandidateCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched safe-store candidate bases mismatch";
      }
      return false;
    }
    accumulatedCandidateCount += count;
  }
  if(accumulatedCandidateCount < 0 || accumulatedCandidateCount > reducedCandidateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched safe-store candidate count overflow";
    }
    return false;
  }
  *outTotalCandidateCount = accumulatedCandidateCount;
  if(*outCompactSeconds <= 0.0)
  {
    *outCompactSeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - compactWallStart).count()) / 1.0e9;
  }
  return true;
}

static bool sim_scan_reduce_candidate_states_from_summaries_true_batch_legacy(SimScanCudaContext *context,
                                                                              int summaryCount,
                                                                              int *outReducedCandidateCount,
                                                                              string *errorOut)
{
  if(outReducedCandidateCount == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing reduced candidate count output";
    }
    return false;
  }
  *outReducedCandidateCount = 0;
  if(context == NULL || summaryCount <= 0)
  {
    return true;
  }

  int reducedCandidateCount = 0;
  try
  {
    thrust::device_ptr<SimScanCudaBatchCandidateReduceKey> summaryKeysBegin =
      thrust::device_pointer_cast(context->batchSummaryKeysDevice);
    thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
      thrust::device_pointer_cast(context->reduceStatesDevice);
    thrust::stable_sort_by_key(thrust::device,
                               summaryKeysBegin,
                               summaryKeysBegin + summaryCount,
                               reduceStatesBegin,
                               SimScanCudaBatchCandidateReduceKeyLess());
    thrust::pair< thrust::device_ptr<SimScanCudaBatchCandidateReduceKey>,
                  thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
      thrust::reduce_by_key(thrust::device,
                            summaryKeysBegin,
                            summaryKeysBegin + summaryCount,
                            reduceStatesBegin,
                            thrust::device_pointer_cast(context->batchReducedKeysDevice),
                            thrust::device_pointer_cast(context->reducedStatesDevice),
                            SimScanCudaBatchCandidateReduceKeyEqual(),
                            SimScanCudaCandidateReduceMergeOp());
    reducedCandidateCount =
      static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->batchReducedKeysDevice));
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched reduced candidate count overflow";
    }
    return false;
  }
  *outReducedCandidateCount = reducedCandidateCount;
  return true;
}

static bool sim_scan_reduce_candidate_states_from_summaries_true_batch_hash(SimScanCudaContext *context,
                                                                            int summaryCount,
                                                                            int batchSize,
                                                                            int *outReducedCandidateCount,
                                                                            bool *outUsedHashPath,
                                                                            double *outHashReduceSeconds,
                                                                            string *errorOut)
{
  if(outReducedCandidateCount == NULL || outUsedHashPath == NULL || outHashReduceSeconds == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing hash reduce outputs";
    }
    return false;
  }
  *outReducedCandidateCount = 0;
  *outUsedHashPath = false;
  *outHashReduceSeconds = 0.0;
  if(context == NULL || summaryCount <= 0 || batchSize <= 0)
  {
    return true;
  }

  const size_t hashCapacity = sim_scan_cuda_initial_hash_reduce_capacity_runtime(summaryCount);
  if(hashCapacity == 0)
  {
    return true;
  }

  if(!ensure_sim_scan_cuda_buffer(&context->batchHashKeysDevice,
                                  &context->batchHashKeysCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchHashFlagsDevice,
                                  &context->batchHashFlagsCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchHashStatesDevice,
                                  &context->batchHashStatesCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemset(context->batchHashFlagsDevice,0,hashCapacity * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->candidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  cudaEvent_t hashStartEvent = NULL;
  cudaEvent_t hashStopEvent = NULL;
  status = cudaEventCreate(&hashStartEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventCreate(&hashStopEvent);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(hashStartEvent);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int hashThreads = 256;
  const int hashBlocks = (summaryCount + hashThreads - 1) / hashThreads;
  sim_scan_hash_reduce_candidate_states_true_batch_kernel<<<hashBlocks, hashThreads>>>(context->batchSummaryKeysDevice,
                                                                                        context->reduceStatesDevice,
                                                                                        summaryCount,
                                                                                        context->batchHashKeysDevice,
                                                                                        context->batchHashFlagsDevice,
                                                                                        context->batchHashStatesDevice,
                                                                                        hashCapacity,
                                                                                        context->candidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int overflowFlag = 0;
  status = cudaMemcpy(&overflowFlag,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(overflowFlag != 0)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    return true;
  }

  status = cudaMemset(context->batchAllCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int countThreads = 256;
  const int countBlocks = static_cast<int>((hashCapacity + static_cast<size_t>(countThreads) - 1) /
                                           static_cast<size_t>(countThreads));
  sim_scan_count_batch_hash_reduce_states_kernel<<<countBlocks, countThreads>>>(context->batchHashKeysDevice,
                                                                                context->batchHashFlagsDevice,
                                                                                hashCapacity,
                                                                                context->batchAllCandidateCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  vector<int> groupedCounts(static_cast<size_t>(batchSize),0);
  status = cudaMemcpy(groupedCounts.data(),
                      context->batchAllCandidateCountsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int reducedCandidateCount = 0;
  vector<int> groupedBases(static_cast<size_t>(batchSize),0);
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int count = groupedCounts[static_cast<size_t>(batchIndex)];
    if(count < 0)
    {
      cudaEventDestroy(hashStartEvent);
      cudaEventDestroy(hashStopEvent);
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched hash reduce count underflow";
      }
      return false;
    }
    groupedBases[static_cast<size_t>(batchIndex)] = reducedCandidateCount;
    reducedCandidateCount += count;
  }
  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    cudaEventDestroy(hashStartEvent);
    cudaEventDestroy(hashStopEvent);
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched hash reduce count overflow";
    }
    return false;
  }

  if(reducedCandidateCount > 0)
  {
    status = cudaMemcpy(context->batchEventBasesDevice,
                        groupedBases.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      cudaEventDestroy(hashStartEvent);
      cudaEventDestroy(hashStopEvent);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    status = cudaMemset(context->batchAllCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
    if(status != cudaSuccess)
    {
      cudaEventDestroy(hashStartEvent);
      cudaEventDestroy(hashStopEvent);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    sim_scan_compact_batch_hash_reduce_states_kernel<<<countBlocks, countThreads>>>(context->batchHashKeysDevice,
                                                                                     context->batchHashFlagsDevice,
                                                                                     context->batchHashStatesDevice,
                                                                                     hashCapacity,
                                                                                     context->batchEventBasesDevice,
                                                                                     context->batchAllCandidateCountsDevice,
                                                                                     context->batchReducedKeysDevice,
                                                                                     context->reducedStatesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      cudaEventDestroy(hashStartEvent);
      cudaEventDestroy(hashStopEvent);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  status = cudaEventRecord(hashStopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(hashStopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, hashStartEvent, hashStopEvent);
  }
  cudaEventDestroy(hashStartEvent);
  cudaEventDestroy(hashStopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  *outReducedCandidateCount = reducedCandidateCount;
  *outUsedHashPath = true;
  *outHashReduceSeconds = static_cast<double>(elapsedMs) / 1000.0;
  return true;
}

static bool sim_scan_reduce_candidate_states_from_summaries_true_batch(SimScanCudaContext *context,
                                                                       const SimScanCudaInitialRunSummary *summariesDevice,
                                                                       int summaryCount,
                                                                       const int *runBasesDevice,
                                                                       const int *runTotalsDevice,
                                                                       int batchSize,
                                                                       int maxRunsPerBatch,
                                                                       const SimScanCudaCandidateState *batchFinalCandidateStatesDevice,
                                                                       const int *batchFinalCandidateCountsDevice,
                                                                       const int *batchRunningMinsDevice,
                                                                       int *outTotalCandidateCount,
                                                                       vector<int> *outCandidateCounts,
                                                                       int *outReducedCandidateCount,
                                                                       vector<int> *outCandidateBases,
                                                                       SimScanCudaBatchResult *batchResult,
                                                                       string *errorOut)
{
  if(outTotalCandidateCount == NULL || outCandidateCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batched all-candidate outputs";
    }
    return false;
  }
  *outTotalCandidateCount = 0;
  outCandidateCounts->assign(static_cast<size_t>(max(batchSize,0)),0);
  if(outReducedCandidateCount != NULL)
  {
    *outReducedCandidateCount = 0;
  }
  if(outCandidateBases != NULL)
  {
    outCandidateBases->assign(static_cast<size_t>(max(batchSize,0)),0);
  }
  if(batchResult != NULL)
  {
    batchResult->initialHashReduceSeconds = 0.0;
    batchResult->usedInitialHashReducePath = false;
    batchResult->initialHashReduceFallback = false;
  }
  if(context == NULL || summaryCount <= 0 || batchSize <= 0 || maxRunsPerBatch <= 0)
  {
    return true;
  }

  if(!sim_scan_init_batch_candidate_reduce_states_from_summaries(context,
                                                                 summariesDevice,
                                                                 summaryCount,
                                                                 runBasesDevice,
                                                                 runTotalsDevice,
                                                                 batchSize,
                                                                 maxRunsPerBatch,
                                                                 errorOut))
  {
    return false;
  }

  int reducedCandidateCount = 0;
  bool usedHashReducePath = false;
  double hashReduceSeconds = 0.0;
  if(sim_scan_cuda_initial_hash_reduce_runtime())
  {
    if(!sim_scan_reduce_candidate_states_from_summaries_true_batch_hash(context,
                                                                        summaryCount,
                                                                        batchSize,
                                                                        &reducedCandidateCount,
                                                                        &usedHashReducePath,
                                                                        &hashReduceSeconds,
                                                                        errorOut))
    {
      return false;
    }
    if(!usedHashReducePath)
    {
      if(batchResult != NULL)
      {
        batchResult->initialHashReduceFallback = true;
      }
      if(!sim_scan_reduce_candidate_states_from_summaries_true_batch_legacy(context,
                                                                             summaryCount,
                                                                             &reducedCandidateCount,
                                                                             errorOut))
      {
        return false;
      }
    }
  }
  else if(!sim_scan_reduce_candidate_states_from_summaries_true_batch_legacy(context,
                                                                              summaryCount,
                                                                              &reducedCandidateCount,
                                                                              errorOut))
  {
    return false;
  }

  if(batchResult != NULL)
  {
    batchResult->usedInitialHashReducePath = usedHashReducePath;
    batchResult->initialHashReduceSeconds = hashReduceSeconds;
  }
  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched reduced candidate count overflow";
    }
    return false;
  }
  if(outReducedCandidateCount != NULL)
  {
    *outReducedCandidateCount = reducedCandidateCount;
  }
  if(reducedCandidateCount <= 0)
  {
    return true;
  }

  cudaError_t status =
    cudaMemset(context->batchAllCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int extractThreads = 256;
  const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
  sim_scan_count_batch_initial_safe_store_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->batchReducedKeysDevice,
                                                                                                      context->reducedStatesDevice,
                                                                                                      reducedCandidateCount,
                                                                                                      batchFinalCandidateStatesDevice,
                                                                                                      batchFinalCandidateCountsDevice,
                                                                                                      batchRunningMinsDevice,
                                                                                                      context->batchAllCandidateCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemcpy(outCandidateCounts->data(),
                      context->batchAllCandidateCountsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int accumulatedCandidateCount = 0;
  vector<int> outputBases(static_cast<size_t>(batchSize),0);
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int count = (*outCandidateCounts)[static_cast<size_t>(batchIndex)];
    if(count < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched reduced candidate count underflow";
      }
      return false;
    }
    outputBases[static_cast<size_t>(batchIndex)] = accumulatedCandidateCount;
    accumulatedCandidateCount += count;
  }
  if(accumulatedCandidateCount < 0 || accumulatedCandidateCount > reducedCandidateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched safe-store candidate count overflow";
    }
    return false;
  }
  if(outCandidateBases != NULL)
  {
    *outCandidateBases = outputBases;
  }
  *outTotalCandidateCount = accumulatedCandidateCount;
  return true;
}

static bool sim_scan_prepare_all_candidate_states_from_summaries_true_batch(SimScanCudaContext *context,
                                                                            const SimScanCudaInitialRunSummary *summariesDevice,
                                                                            int summaryCount,
                                                                            const int *runBasesDevice,
                                                                            const int *runTotalsDevice,
                                                                            int batchSize,
                                                                            int maxRunsPerBatch,
                                                                            const SimScanCudaCandidateState *batchFinalCandidateStatesDevice,
                                                                            const int *batchFinalCandidateCountsDevice,
                                                                            const int *batchRunningMinsDevice,
                                                                            int *outTotalCandidateCount,
                                                                            vector<int> *outCandidateCounts,
                                                                            SimScanCudaBatchResult *batchResult,
                                                                            string *errorOut)
{
  int reducedCandidateCount = 0;
  vector<int> outputBases;
  if(outTotalCandidateCount == NULL || outCandidateCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batched all-candidate outputs";
    }
    return false;
  }
  *outTotalCandidateCount = 0;
  outCandidateCounts->assign(static_cast<size_t>(max(batchSize,0)),0);
  if(context == NULL || summaryCount <= 0 || batchSize <= 0 || maxRunsPerBatch <= 0)
  {
    return true;
  }

  if(!sim_scan_reduce_candidate_states_from_summaries_true_batch(context,
                                                                 summariesDevice,
                                                                 summaryCount,
                                                                 runBasesDevice,
                                                                 runTotalsDevice,
                                                                 batchSize,
                                                                 maxRunsPerBatch,
                                                                 batchFinalCandidateStatesDevice,
                                                                 batchFinalCandidateCountsDevice,
                                                                 batchRunningMinsDevice,
                                                                 outTotalCandidateCount,
                                                                 outCandidateCounts,
                                                                 &reducedCandidateCount,
                                                                 &outputBases,
                                                                 batchResult,
                                                                 errorOut))
  {
    return false;
  }
  const int accumulatedCandidateCount = *outTotalCandidateCount;
  if(accumulatedCandidateCount <= 0)
  {
    return true;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  static_cast<size_t>(accumulatedCandidateCount),
                                  errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }
  cudaError_t status = cudaMemcpy(context->batchEventBasesDevice,
                      outputBases.data(),
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->batchAllCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  const int extractThreads = 256;
  const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
  sim_scan_compact_batch_initial_safe_store_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->batchReducedKeysDevice,
                                                                                                        context->reducedStatesDevice,
                                                                                                        reducedCandidateCount,
                                                                                                        batchFinalCandidateStatesDevice,
                                                                                                        batchFinalCandidateCountsDevice,
                                                                                                        batchRunningMinsDevice,
                                                                                                        context->batchEventBasesDevice,
                                                                                                        context->batchAllCandidateCountsDevice,
                                                                                                        context->outputCandidateStatesDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

} // namespace

bool sim_scan_cuda_is_built()
{
  return true;
}

bool sim_scan_cuda_init(int device,string *errorOut)
{
  if(device < 0)
  {
    device = 0;
  }
  const int slot = simCudaWorkerSlotRuntime();
  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  return ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut);
}

bool sim_scan_cuda_upload_persistent_safe_candidate_state_store(const SimScanCudaCandidateState *states,
                                                                size_t stateCount,
                                                                SimCudaPersistentSafeStoreHandle *handleOut,
                                                                string *errorOut)
{
  if(handleOut == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store output handle";
    }
    return false;
  }
  *handleOut = SimCudaPersistentSafeStoreHandle();
  if(stateCount > 0 && states == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store input states";
    }
    return false;
  }

  int device = 0;
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }
  if(device < 0)
  {
    device = 0;
  }

  const int slot = simCudaWorkerSlotRuntime();
  if(stateCount == 0)
  {
    handleOut->valid = true;
    handleOut->device = device;
    handleOut->slot = slot;
    sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handleOut,false,0,0);
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaCandidateState *statesDevice = NULL;
  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&statesDevice),
                                  stateCount * sizeof(SimScanCudaCandidateState));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(statesDevice,
                      states,
                      stateCount * sizeof(SimScanCudaCandidateState),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    cudaFree(statesDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  handleOut->valid = true;
  handleOut->device = device;
  handleOut->slot = slot;
  handleOut->stateCount = stateCount;
  handleOut->statesDevice = reinterpret_cast<uintptr_t>(statesDevice);
  sim_scan_cuda_reset_persistent_safe_store_frontier_metadata(handleOut,false,0,0);
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_erase_persistent_safe_candidate_state_store_start_coords(const uint64_t *startCoords,
                                                                            size_t startCoordCount,
                                                                            SimCudaPersistentSafeStoreHandle *handle,
                                                                            string *errorOut)
{
  if(handle == NULL || !handle->valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(handle->stateCount == 0 || startCoordCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(startCoords == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing start coords";
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle->device,handle->slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle->device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->filterStartCoordsDevice,
                                  &context->filterStartCoordsCapacity,
                                  startCoordCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  max(handle->stateCount,handle->frontierCount),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->filterStartCoordsDevice,
                                  startCoords,
                                  startCoordCount * sizeof(uint64_t),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int threads = 256;
  const int blocks =
    static_cast<int>((handle->stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_filter_persistent_safe_store_excluding_start_coords_kernel<<<blocks, threads>>>(
    sim_scan_cuda_handle_states_device(*handle),
    static_cast<int>(handle->stateCount),
    context->filterStartCoordsDevice,
    static_cast<int>(startCoordCount),
    context->outputCandidateStatesDevice,
    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int keptCount = 0;
  status = cudaMemcpy(&keptCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(keptCount < 0 || static_cast<size_t>(keptCount) > handle->stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store erase count overflow";
    }
    return false;
  }
  if(keptCount > 0)
  {
    status = cudaMemcpy(sim_scan_cuda_handle_states_device(*handle),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(keptCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  handle->stateCount = static_cast<size_t>(keptCount);

  if(handle->frontierValid)
  {
    int keptFrontierCount = 0;
    if(handle->frontierCount > 0)
    {
      status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      const int frontierBlocks =
        static_cast<int>((handle->frontierCount + static_cast<size_t>(threads) - 1) /
                         static_cast<size_t>(threads));
      sim_scan_filter_persistent_safe_store_excluding_start_coords_kernel<<<frontierBlocks, threads>>>(
        sim_scan_cuda_handle_frontier_states_device(*handle),
        static_cast<int>(handle->frontierCount),
        context->filterStartCoordsDevice,
        static_cast<int>(startCoordCount),
        context->outputCandidateStatesDevice,
        context->filteredCandidateCountDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      status = cudaMemcpy(&keptFrontierCount,
                          context->filteredCandidateCountDevice,
                          sizeof(int),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      if(keptFrontierCount < 0 || static_cast<size_t>(keptFrontierCount) > handle->frontierCount)
      {
        if(errorOut != NULL)
        {
          *errorOut = "persistent safe-store frontier erase count overflow";
        }
        return false;
      }
    }

    if(!sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
         keptFrontierCount > 0 ? context->outputCandidateStatesDevice : NULL,
         keptFrontierCount,
         handle->frontierRunningMin,
         handle,
         errorOut))
    {
      return false;
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_path_summary(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                int summaryRowStart,
                                                                                const vector<int> &rowMinCols,
                                                                                const vector<int> &rowMaxCols,
                                                                                vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                string *errorOut)
{
  if(outCandidateStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store filter output";
    }
    return false;
  }
  outCandidateStates->clear();
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(rowMinCols.size() != rowMaxCols.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "path summary row vector mismatch";
    }
    return false;
  }
  if(handle.stateCount == 0 || rowMinCols.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle.device,handle.slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->summaryRowMinColsDevice,
                                  &context->summaryRowMinColsCapacity,
                                  rowMinCols.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->summaryRowMaxColsDevice,
                                  &context->summaryRowMaxColsCapacity,
                                  rowMaxCols.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  handle.stateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->summaryRowMinColsDevice,
                                  rowMinCols.data(),
                                  rowMinCols.size() * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->summaryRowMaxColsDevice,
                      rowMaxCols.data(),
                      rowMaxCols.size() * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int threads = 256;
  const int blocks = static_cast<int>((handle.stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_filter_persistent_safe_store_by_path_summary_kernel<<<blocks, threads>>>(sim_scan_cuda_handle_states_device(handle),
                                                                                    static_cast<int>(handle.stateCount),
                                                                                    summaryRowStart,
                                                                                    context->summaryRowMinColsDevice,
                                                                                    context->summaryRowMaxColsDevice,
                                                                                    static_cast<int>(rowMinCols.size()),
                                                                                    context->outputCandidateStatesDevice,
                                                                                    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int outputCount = 0;
  status = cudaMemcpy(&outputCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outputCount < 0 || static_cast<size_t>(outputCount) > handle.stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store path-summary filter count overflow";
    }
    return false;
  }
  if(outputCount > 0)
  {
    outCandidateStates->resize(static_cast<size_t>(outputCount));
    status = cudaMemcpy(outCandidateStates->data(),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(outputCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outCandidateStates->clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(const SimCudaPersistentSafeStoreHandle &handle,
                                                                                 int queryLength,
                                                                                 int targetLength,
                                                                                 const vector<int> &rowOffsets,
                                                                                 const vector<SimScanCudaColumnInterval> &intervals,
                                                                                 vector<SimScanCudaCandidateState> *outCandidateStates,
                                                                                 string *errorOut)
{
  if(outCandidateStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store interval filter output";
    }
    return false;
  }
  outCandidateStates->clear();
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(queryLength < 0 || targetLength < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store interval dimensions";
    }
    return false;
  }
  if(rowOffsets.size() != static_cast<size_t>(queryLength + 2))
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store rowOffsets size mismatch";
    }
    return false;
  }
  if(handle.stateCount == 0 || intervals.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle.device,handle.slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->rowIntervalOffsetsDevice,
                                  &context->rowIntervalOffsetsCapacity,
                                  rowOffsets.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->rowIntervalsDevice,
                                  &context->rowIntervalsCapacity,
                                  intervals.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  handle.stateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->rowIntervalOffsetsDevice,
                                  rowOffsets.data(),
                                  rowOffsets.size() * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->rowIntervalsDevice,
                      intervals.data(),
                      intervals.size() * sizeof(SimScanCudaColumnInterval),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int threads = 256;
  const int blocks = static_cast<int>((handle.stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_filter_persistent_safe_store_by_row_intervals_kernel<<<blocks, threads>>>(sim_scan_cuda_handle_states_device(handle),
                                                                                      static_cast<int>(handle.stateCount),
                                                                                      queryLength,
                                                                                      targetLength,
                                                                                      context->rowIntervalOffsetsDevice,
                                                                                      context->rowIntervalsDevice,
                                                                                      context->outputCandidateStatesDevice,
                                                                                      context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int outputCount = 0;
  status = cudaMemcpy(&outputCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outputCount < 0 || static_cast<size_t>(outputCount) > handle.stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store interval filter count overflow";
    }
    return false;
  }
  if(outputCount > 0)
  {
    outCandidateStates->resize(static_cast<size_t>(outputCount));
    status = cudaMemcpy(outCandidateStates->data(),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(outputCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outCandidateStates->clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
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
  if(outStartCoords == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store interval start-coord filter output";
    }
    return false;
  }
  outStartCoords->clear();
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(queryLength < 0 || targetLength < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store interval dimensions";
    }
    return false;
  }
  if(rowOffsets.size() != static_cast<size_t>(queryLength + 2))
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store rowOffsets size mismatch";
    }
    return false;
  }
  if(handle.stateCount == 0 || intervals.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle.device,handle.slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->rowIntervalOffsetsDevice,
                                  &context->rowIntervalOffsetsCapacity,
                                  rowOffsets.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->rowIntervalsDevice,
                                  &context->rowIntervalsCapacity,
                                  intervals.size(),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->filterStartCoordsDevice,
                                  &context->filterStartCoordsCapacity,
                                  handle.stateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->rowIntervalOffsetsDevice,
                                  rowOffsets.data(),
                                  rowOffsets.size() * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->rowIntervalsDevice,
                      intervals.data(),
                      intervals.size() * sizeof(SimScanCudaColumnInterval),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int threads = 256;
  const int blocks =
    static_cast<int>((handle.stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_filter_persistent_safe_store_start_coords_by_row_intervals_kernel<<<blocks, threads>>>(
    sim_scan_cuda_handle_states_device(handle),
    static_cast<int>(handle.stateCount),
    queryLength,
    targetLength,
    context->rowIntervalOffsetsDevice,
    context->rowIntervalsDevice,
    context->filterStartCoordsDevice,
    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int outputCount = 0;
  status = cudaMemcpy(&outputCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(outputCount < 0 || static_cast<size_t>(outputCount) > handle.stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store interval start-coord filter count overflow";
    }
    return false;
  }
  if(outputCount > 0)
  {
    outStartCoords->resize(static_cast<size_t>(outputCount));
    status = cudaMemcpy(outStartCoords->data(),
                        context->filterStartCoordsDevice,
                        static_cast<size_t>(outputCount) * sizeof(uint64_t),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outStartCoords->clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static void sim_scan_build_safe_windows_from_dense_row_ranges(const vector<int> &rowMinCols,
                                                              const vector<int> &rowMaxCols,
                                                              vector<SimScanCudaSafeWindow> *outWindows)
{
  if(outWindows == NULL)
  {
    return;
  }
  outWindows->clear();
  if(rowMinCols.size() != rowMaxCols.size() || rowMinCols.size() <= 1)
  {
    return;
  }

  SimScanCudaSafeWindow activeWindow;
  bool haveActiveWindow = false;
  for(size_t row = 1; row < rowMinCols.size(); ++row)
  {
    if(rowMinCols[row] > rowMaxCols[row])
    {
      if(haveActiveWindow)
      {
        outWindows->push_back(activeWindow);
        haveActiveWindow = false;
      }
      continue;
    }

    const int rowValue = static_cast<int>(row);
    if(haveActiveWindow &&
       activeWindow.rowEnd + 1 == rowValue &&
       activeWindow.colStart == rowMinCols[row] &&
       activeWindow.colEnd == rowMaxCols[row])
    {
      activeWindow.rowEnd = rowValue;
      continue;
    }

    if(haveActiveWindow)
    {
      outWindows->push_back(activeWindow);
    }
    activeWindow = SimScanCudaSafeWindow(rowValue,rowValue,rowMinCols[row],rowMaxCols[row]);
    haveActiveWindow = true;
  }

  if(haveActiveWindow)
  {
    outWindows->push_back(activeWindow);
  }
}

static void sim_scan_build_safe_windows_from_sparse_row_intervals_host(
  int queryLength,
  const vector<int> &rowOffsets,
  const vector<SimScanCudaColumnInterval> &intervals,
  vector<SimScanCudaSafeWindow> *outWindows)
{
  if(outWindows == NULL)
  {
    return;
  }
  outWindows->clear();
  if(queryLength <= 0 || rowOffsets.size() != static_cast<size_t>(queryLength + 2))
  {
    return;
  }

  vector<SimScanCudaSafeWindow> activeWindows;

  for(int row = 1; row <= queryLength; ++row)
  {
    const int intervalStart = rowOffsets[static_cast<size_t>(row)];
    const int intervalEnd = rowOffsets[static_cast<size_t>(row + 1)];
    vector<SimScanCudaColumnInterval> rowIntervals;
    if(intervalStart >= 0 && intervalEnd >= intervalStart)
    {
      rowIntervals.reserve(static_cast<size_t>(intervalEnd - intervalStart));
      for(int intervalIndex = intervalStart; intervalIndex < intervalEnd; ++intervalIndex)
      {
        if(static_cast<size_t>(intervalIndex) >= intervals.size())
        {
          rowIntervals.clear();
          break;
        }
        rowIntervals.push_back(intervals[static_cast<size_t>(intervalIndex)]);
      }
    }

    vector<SimScanCudaSafeWindow> nextActiveWindows;
    nextActiveWindows.reserve(max(activeWindows.size(),rowIntervals.size()));
    size_t activeIndex = 0;
    size_t intervalIndex = 0;
    while(activeIndex < activeWindows.size() && intervalIndex < rowIntervals.size())
    {
      const SimScanCudaSafeWindow &activeWindow = activeWindows[activeIndex];
      const SimScanCudaColumnInterval &interval = rowIntervals[intervalIndex];
      if(activeWindow.colStart == interval.colStart &&
         activeWindow.colEnd == interval.colEnd)
      {
        SimScanCudaSafeWindow extendedWindow = activeWindow;
        extendedWindow.rowEnd = row;
        nextActiveWindows.push_back(extendedWindow);
        ++activeIndex;
        ++intervalIndex;
        continue;
      }
      if(activeWindow.colStart < interval.colStart ||
         (activeWindow.colStart == interval.colStart && activeWindow.colEnd < interval.colEnd))
      {
        outWindows->push_back(activeWindow);
        ++activeIndex;
        continue;
      }
      nextActiveWindows.push_back(
        SimScanCudaSafeWindow(row,
                              row,
                              interval.colStart,
                              interval.colEnd));
      ++intervalIndex;
    }
    while(activeIndex < activeWindows.size())
    {
      outWindows->push_back(activeWindows[activeIndex]);
      ++activeIndex;
    }
    while(intervalIndex < rowIntervals.size())
    {
      nextActiveWindows.push_back(
        SimScanCudaSafeWindow(row,
                              row,
                              rowIntervals[intervalIndex].colStart,
                              rowIntervals[intervalIndex].colEnd));
      ++intervalIndex;
    }
    activeWindows.swap(nextActiveWindows);
  }

  outWindows->insert(outWindows->end(),activeWindows.begin(),activeWindows.end());
  sort(outWindows->begin(),outWindows->end(),[](const SimScanCudaSafeWindow &lhs,
                                                const SimScanCudaSafeWindow &rhs)
  {
    if(lhs.rowStart != rhs.rowStart) return lhs.rowStart < rhs.rowStart;
    if(lhs.colStart != rhs.colStart) return lhs.colStart < rhs.colStart;
    if(lhs.rowEnd != rhs.rowEnd) return lhs.rowEnd < rhs.rowEnd;
    return lhs.colEnd < rhs.colEnd;
  });
}

static bool sim_scan_cuda_build_sparse_row_intervals_from_candidate_states_locked(
  SimScanCudaContext *context,
  const SimScanCudaCandidateState *statesDevice,
  int stateCount,
  int queryLength,
  int targetLength,
  int *outMergedIntervalCount,
  string *errorOut)
{
  if(outMergedIntervalCount != NULL)
  {
    *outMergedIntervalCount = 0;
  }
  if(context == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing SIM CUDA context";
    }
    return false;
  }
  if(queryLength < 0 || targetLength < 0 || stateCount < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid sparse row-interval dimensions";
    }
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->rowIntervalOffsetsDevice,
                                  &context->rowIntervalOffsetsCapacity,
                                  static_cast<size_t>(queryLength + 2),
                                  errorOut))
  {
    return false;
  }

  const size_t rowOffsetBytes = static_cast<size_t>(queryLength + 2) * sizeof(int);
  cudaError_t status = cudaMemset(context->rowIntervalOffsetsDevice,0,rowOffsetBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(stateCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  if(!ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(stateCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunBasesDevice,
                                  &context->batchRunBasesCapacity,
                                  static_cast<size_t>(stateCount + 1),
                                  errorOut))
  {
    return false;
  }

  const int threads = 256;
  const int blocks = max(1, (stateCount + threads - 1) / threads);
  sim_scan_count_candidate_row_contributions_kernel<<<blocks, threads>>>(statesDevice,
                                                                         stateCount,
                                                                         queryLength,
                                                                         targetLength,
                                                                         context->batchEventBasesDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->batchEventBasesDevice,
                                       stateCount,
                                       context->batchRunBasesDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int totalIntervals = 0;
  status = cudaMemcpy(&totalIntervals,
                      context->eventCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(totalIntervals <= 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  if(!ensure_sim_scan_cuda_buffer(&context->summaryKeysDevice,
                                  &context->summaryKeysCapacity,
                                  static_cast<size_t>(totalIntervals),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->rowIntervalsDevice,
                                  &context->rowIntervalsCapacity,
                                  static_cast<size_t>(totalIntervals),
                                  errorOut))
  {
    return false;
  }

  sim_scan_emit_candidate_row_intervals_kernel<<<blocks, threads>>>(statesDevice,
                                                                    stateCount,
                                                                    queryLength,
                                                                    targetLength,
                                                                    context->batchRunBasesDevice,
                                                                    context->summaryKeysDevice,
                                                                    context->rowIntervalsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  thrust::stable_sort_by_key(thrust::device_pointer_cast(context->summaryKeysDevice),
                             thrust::device_pointer_cast(context->summaryKeysDevice + totalIntervals),
                             thrust::device_pointer_cast(context->rowIntervalsDevice));
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_merge_sparse_row_intervals_kernel<<<1, 1>>>(context->summaryKeysDevice,
                                                       context->rowIntervalsDevice,
                                                       totalIntervals,
                                                       queryLength,
                                                       context->rowIntervalOffsetsDevice,
                                                       context->candidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int mergedIntervalCount = 0;
  status = cudaMemcpy(&mergedIntervalCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(mergedIntervalCount < 0 || mergedIntervalCount > totalIntervals)
  {
    if(errorOut != NULL)
    {
      *errorOut = "sparse row-interval merge count overflow";
    }
    return false;
  }
  if(outMergedIntervalCount != NULL)
  {
    *outMergedIntervalCount = mergedIntervalCount;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_cuda_select_safe_workset_windows_sparse_v1_locked(
  SimScanCudaContext *context,
  const SimCudaPersistentSafeStoreHandle &handle,
  int queryLength,
  int targetLength,
  int summaryRowStart,
  const vector<int> &rowMinCols,
  int maxWindowCount,
  SimScanCudaSafeWindowResult *outResult,
  string *errorOut)
{
  if(context == NULL || outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing sparse safe-window outputs";
    }
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  handle.stateCount,
                                  errorOut))
  {
    return false;
  }

  const int threads = 256;
  const int stateBlocks =
    max(1, static_cast<int>((handle.stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads)));
  cudaError_t status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_filter_persistent_safe_store_by_path_summary_kernel<<<stateBlocks, threads>>>(
    sim_scan_cuda_handle_states_device(handle),
    static_cast<int>(handle.stateCount),
    summaryRowStart,
    context->summaryRowMinColsDevice,
    context->summaryRowMaxColsDevice,
    static_cast<int>(rowMinCols.size()),
    context->outputCandidateStatesDevice,
    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int seedCandidateCount = 0;
  status = cudaMemcpy(&seedCandidateCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(seedCandidateCount < 0 || static_cast<size_t>(seedCandidateCount) > handle.stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "safe-window sparse seed count overflow";
    }
    return false;
  }

  int seedIntervalCount = 0;
  if(!sim_scan_cuda_build_sparse_row_intervals_from_candidate_states_locked(context,
                                                                            context->outputCandidateStatesDevice,
                                                                            seedCandidateCount,
                                                                            queryLength,
                                                                            targetLength,
                                                                            &seedIntervalCount,
                                                                            errorOut))
  {
    return false;
  }

  int affectedCandidateCount = 0;
  int finalIntervalCount = 0;
  if(seedIntervalCount > 0)
  {
    status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    sim_scan_filter_persistent_safe_store_by_row_intervals_kernel<<<stateBlocks, threads>>>(
      sim_scan_cuda_handle_states_device(handle),
      static_cast<int>(handle.stateCount),
      queryLength,
      targetLength,
      context->rowIntervalOffsetsDevice,
      context->rowIntervalsDevice,
      context->outputCandidateStatesDevice,
      context->filteredCandidateCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    status = cudaMemcpy(&affectedCandidateCount,
                        context->filteredCandidateCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(affectedCandidateCount < 0 || static_cast<size_t>(affectedCandidateCount) > handle.stateCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "safe-window sparse affected candidate count overflow";
      }
      return false;
    }

    if(affectedCandidateCount > 0)
    {
      const int finalBlocks = max(1, (affectedCandidateCount + threads - 1) / threads);
      sim_scan_collect_candidate_start_coords_kernel<<<finalBlocks, threads>>>(
        context->outputCandidateStatesDevice,
        affectedCandidateCount,
        context->filterStartCoordsDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }

    if(!sim_scan_cuda_build_sparse_row_intervals_from_candidate_states_locked(context,
                                                                              context->outputCandidateStatesDevice,
                                                                              affectedCandidateCount,
                                                                              queryLength,
                                                                              targetLength,
                                                                              &finalIntervalCount,
                                                                              errorOut))
    {
      return false;
    }
  }

  status = cudaEventRecord(context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventSynchronize(context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  float gpuMilliseconds = 0.0f;
  status = cudaEventElapsedTime(&gpuMilliseconds,context->startEvent,context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  outResult->gpuSeconds = static_cast<double>(gpuMilliseconds) / 1000.0;

  const chrono::steady_clock::time_point d2hStart = chrono::steady_clock::now();
  outResult->affectedCandidateCount = static_cast<uint64_t>(affectedCandidateCount);
  vector<int> sparseRowOffsets(static_cast<size_t>(queryLength + 2),0);
  vector<SimScanCudaColumnInterval> sparseIntervals;
  status = cudaMemcpy(sparseRowOffsets.data(),
                      context->rowIntervalOffsetsDevice,
                      sparseRowOffsets.size() * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(finalIntervalCount > 0)
  {
    sparseIntervals.resize(static_cast<size_t>(finalIntervalCount));
    status = cudaMemcpy(sparseIntervals.data(),
                        context->rowIntervalsDevice,
                        static_cast<size_t>(finalIntervalCount) * sizeof(SimScanCudaColumnInterval),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      sparseIntervals.clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  if(affectedCandidateCount > 0)
  {
    outResult->affectedStartCoords.resize(static_cast<size_t>(affectedCandidateCount));
    status = cudaMemcpy(outResult->affectedStartCoords.data(),
                        context->filterStartCoordsDevice,
                        static_cast<size_t>(affectedCandidateCount) * sizeof(uint64_t),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outResult->affectedStartCoords.clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  outResult->d2hSeconds =
    static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                          chrono::steady_clock::now() - d2hStart).count()) / 1.0e9;
  outResult->coordBytesD2H =
    static_cast<uint64_t>(sparseRowOffsets.size()) * static_cast<uint64_t>(sizeof(int)) +
    static_cast<uint64_t>(finalIntervalCount) * static_cast<uint64_t>(sizeof(SimScanCudaColumnInterval)) +
    static_cast<uint64_t>(affectedCandidateCount) * static_cast<uint64_t>(sizeof(uint64_t));

  sim_scan_build_safe_windows_from_sparse_row_intervals_host(queryLength,
                                                             sparseRowOffsets,
                                                             sparseIntervals,
                                                             &outResult->windows);
  outResult->overflowFallback = static_cast<int>(outResult->windows.size()) > maxWindowCount;
  clear_sim_scan_cuda_error(errorOut);
  return true;
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
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing safe-window output";
    }
    return false;
  }
  *outResult = SimScanCudaSafeWindowResult();
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(queryLength < 0 || targetLength < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid safe-window dimensions";
    }
    return false;
  }
  if(rowMinCols.size() != rowMaxCols.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "safe-window path summary row vector mismatch";
    }
    return false;
  }
  if(maxWindowCount <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid safe-window maxWindowCount";
    }
    return false;
  }
  if(handle.stateCount == 0 || rowMinCols.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle.device,handle.slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_capacity_locked(*context,queryLength,targetLength,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->summaryRowMinColsDevice,
                                  &context->summaryRowMinColsCapacity,
                                  max(static_cast<size_t>(queryLength + 1), rowMinCols.size()),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->summaryRowMaxColsDevice,
                                  &context->summaryRowMaxColsCapacity,
                                  max(static_cast<size_t>(queryLength + 1), rowMaxCols.size()),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->filterStartCoordsDevice,
                                  &context->filterStartCoordsCapacity,
                                  handle.stateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->summaryRowMinColsDevice,
                                  rowMinCols.data(),
                                  rowMinCols.size() * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->summaryRowMaxColsDevice,
                      rowMaxCols.data(),
                      rowMaxCols.size() * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(plannerMode == SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1)
  {
    return sim_scan_cuda_select_safe_workset_windows_sparse_v1_locked(context,
                                                                      handle,
                                                                      queryLength,
                                                                      targetLength,
                                                                      summaryRowStart,
                                                                      rowMinCols,
                                                                      maxWindowCount,
                                                                      outResult,
                                                                      errorOut);
  }

  const int rowRangeCount = queryLength + 1;
  const int threads = 256;
  const int rowBlocks = max(1, (rowRangeCount + threads - 1) / threads);
  const int stateBlocks =
    max(1, static_cast<int>((handle.stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads)));

  sim_scan_initialize_dense_row_ranges_kernel<<<rowBlocks, threads>>>(context->rowCountsDevice,
                                                                      context->rowOffsetsDevice,
                                                                      rowRangeCount,
                                                                      targetLength + 1);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_accumulate_persistent_safe_store_seed_row_ranges_kernel<<<stateBlocks, threads>>>(
    sim_scan_cuda_handle_states_device(handle),
    static_cast<int>(handle.stateCount),
    queryLength,
    targetLength,
    summaryRowStart,
    context->summaryRowMinColsDevice,
    context->summaryRowMaxColsDevice,
    static_cast<int>(rowMinCols.size()),
    context->rowCountsDevice,
    context->rowOffsetsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_initialize_dense_row_ranges_kernel<<<rowBlocks, threads>>>(context->summaryRowMinColsDevice,
                                                                      context->summaryRowMaxColsDevice,
                                                                      rowRangeCount,
                                                                      targetLength + 1);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_collect_persistent_safe_store_safe_windows_kernel<<<stateBlocks, threads>>>(
    sim_scan_cuda_handle_states_device(handle),
    static_cast<int>(handle.stateCount),
    queryLength,
    targetLength,
    context->rowCountsDevice,
    context->rowOffsetsDevice,
    context->summaryRowMinColsDevice,
    context->summaryRowMaxColsDevice,
    context->filterStartCoordsDevice,
    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaEventSynchronize(context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  float gpuMilliseconds = 0.0f;
  status = cudaEventElapsedTime(&gpuMilliseconds,context->startEvent,context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  outResult->gpuSeconds = static_cast<double>(gpuMilliseconds) / 1000.0;

  const std::chrono::steady_clock::time_point d2hStart = std::chrono::steady_clock::now();
  int affectedCandidateCount = 0;
  status = cudaMemcpy(&affectedCandidateCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(affectedCandidateCount < 0 || static_cast<size_t>(affectedCandidateCount) > handle.stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "safe-window affected candidate count overflow";
    }
    return false;
  }
  outResult->affectedCandidateCount = static_cast<uint64_t>(affectedCandidateCount);

  vector<int> denseRowMinCols(static_cast<size_t>(rowRangeCount),targetLength + 1);
  vector<int> denseRowMaxCols(static_cast<size_t>(rowRangeCount),0);
  status = cudaMemcpy(denseRowMinCols.data(),
                      context->summaryRowMinColsDevice,
                      static_cast<size_t>(rowRangeCount) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(denseRowMaxCols.data(),
                      context->summaryRowMaxColsDevice,
                      static_cast<size_t>(rowRangeCount) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(affectedCandidateCount > 0)
  {
    outResult->affectedStartCoords.resize(static_cast<size_t>(affectedCandidateCount));
    status = cudaMemcpy(outResult->affectedStartCoords.data(),
                        context->filterStartCoordsDevice,
                        static_cast<size_t>(affectedCandidateCount) * sizeof(uint64_t),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outResult->affectedStartCoords.clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  outResult->d2hSeconds =
    static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::steady_clock::now() - d2hStart).count()) / 1.0e9;
  outResult->coordBytesD2H =
    static_cast<uint64_t>(rowRangeCount) * static_cast<uint64_t>(sizeof(int) * 2) +
    static_cast<uint64_t>(affectedCandidateCount) * static_cast<uint64_t>(sizeof(uint64_t));

  sim_scan_build_safe_windows_from_dense_row_ranges(denseRowMinCols,denseRowMaxCols,&outResult->windows);
  outResult->overflowFallback = static_cast<int>(outResult->windows.size()) > maxWindowCount;

  clear_sim_scan_cuda_error(errorOut);
  return true;
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
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing safe-window execute-plan output";
    }
    return false;
  }
  *outResult = SimScanCudaSafeWindowExecutePlanResult();

  SimScanCudaSafeWindowResult safeWindowResult;
  if(!sim_scan_cuda_select_safe_workset_windows(handle,
                                                queryLength,
                                                targetLength,
                                                summaryRowStart,
                                                rowMinCols,
                                                rowMaxCols,
                                                plannerMode,
                                                maxWindowCount,
                                                &safeWindowResult,
                                                errorOut))
  {
    return false;
  }

  outResult->execWindows.swap(safeWindowResult.windows);
  outResult->windowCount = static_cast<uint64_t>(outResult->execWindows.size());
  outResult->affectedStartCount =
    static_cast<uint64_t>(safeWindowResult.affectedStartCoords.size());
  outResult->uniqueAffectedStartCoords.swap(safeWindowResult.affectedStartCoords);
  sort(outResult->uniqueAffectedStartCoords.begin(),outResult->uniqueAffectedStartCoords.end());
  outResult->uniqueAffectedStartCoords.erase(
    unique(outResult->uniqueAffectedStartCoords.begin(),
           outResult->uniqueAffectedStartCoords.end()),
    outResult->uniqueAffectedStartCoords.end());
  outResult->execBandCount = static_cast<uint64_t>(outResult->execWindows.size());
  for(size_t windowIndex = 0; windowIndex < outResult->execWindows.size(); ++windowIndex)
  {
    const SimScanCudaSafeWindow &window = outResult->execWindows[windowIndex];
    if(window.rowEnd >= window.rowStart && window.colEnd >= window.colStart)
    {
      outResult->execCellCount +=
        static_cast<uint64_t>(window.rowEnd - window.rowStart + 1) *
        static_cast<uint64_t>(window.colEnd - window.colStart + 1);
    }
  }
  outResult->overflowFallback = safeWindowResult.overflowFallback;
  outResult->emptyPlan =
    outResult->execWindows.empty() || outResult->uniqueAffectedStartCoords.empty();
  outResult->coordBytesD2H = safeWindowResult.coordBytesD2H;
  outResult->gpuSeconds = safeWindowResult.gpuSeconds;
  outResult->d2hSeconds = safeWindowResult.d2hSeconds;
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(const SimCudaPersistentSafeStoreHandle &handle,
                                                                              int maxProposalCount,
                                                                              vector<SimScanCudaCandidateState> *outSelectedStates,
                                                                              string *errorOut,
                                                                              bool *outUsedFrontierCache)
{
  if(outSelectedStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent store selector outputs";
    }
    return false;
  }
  outSelectedStates->clear();
  if(outUsedFrontierCache != NULL)
  {
    *outUsedFrontierCache = false;
  }
  if(maxProposalCount <= 0 || !handle.valid)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  const bool useFrontierCache = handle.frontierValid;
  const size_t sourceStateCount =
    useFrontierCache ? handle.frontierCount : handle.stateCount;
  SimScanCudaCandidateState *sourceStatesDevice =
    useFrontierCache ? sim_scan_cuda_handle_frontier_states_device(handle) :
                       sim_scan_cuda_handle_states_device(handle);
  if(outUsedFrontierCache != NULL)
  {
    *outUsedFrontierCache = useFrontierCache;
  }
  if(sourceStateCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(sourceStateCount > static_cast<size_t>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = useFrontierCache ? "persistent safe-store frontier count overflow" :
                                     "persistent safe-store state count overflow";
    }
    return false;
  }
  if(sourceStatesDevice == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = useFrontierCache ? "persistent safe-store frontier device pointer missing" :
                                     "persistent safe-store device pointer missing";
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle.device,handle.slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  sourceStateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status =
    cudaMemcpy(context->outputCandidateStatesDevice,
               sourceStatesDevice,
               sourceStateCount * sizeof(SimScanCudaCandidateState),
               cudaMemcpyDeviceToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  double unusedGpuSeconds = 0.0;
  return sim_scan_select_top_disjoint_candidate_states_from_device_locked(
    context,
    context->outputCandidateStatesDevice,
    static_cast<int>(sourceStateCount),
    maxProposalCount,
    outSelectedStates,
    &unusedGpuSeconds,
    errorOut);
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
  if(handleOut == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing persistent safe-store output handle";
    }
    return false;
  }
  *handleOut = SimCudaPersistentSafeStoreHandle();
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

  if(summaries.size() > static_cast<size_t>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "initial run summary count overflow";
    }
    return false;
  }

  int finalCandidateCount = static_cast<int>(finalCandidates.size());
  if(finalCandidateCount < 0)
  {
    finalCandidateCount = 0;
  }
  if(finalCandidateCount > sim_scan_cuda_max_candidates)
  {
    finalCandidateCount = sim_scan_cuda_max_candidates;
  }

  int device = 0;
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }
  if(device < 0)
  {
    device = 0;
  }

  const int slot = simCudaWorkerSlotRuntime();
  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }

  const int summaryCount = static_cast<int>(summaries.size());
  if(summaryCount > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                    &context->initialRunSummariesCapacity,
                                    static_cast<size_t>(summaryCount),
                                    errorOut))
    {
      return false;
    }
    const cudaError_t status =
      cudaMemcpy(context->initialRunSummariesDevice,
                 summaries.data(),
                 static_cast<size_t>(summaryCount) * sizeof(SimScanCudaInitialRunSummary),
                 cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  if(finalCandidateCount > 0)
  {
    const cudaError_t status =
      cudaMemcpy(context->candidateStatesDevice,
                 finalCandidates.data(),
                 static_cast<size_t>(finalCandidateCount) * sizeof(SimScanCudaCandidateState),
                 cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int allCandidateCount = 0;
  const chrono::steady_clock::time_point buildStart = chrono::steady_clock::now();
  if(summaryCount > 0 &&
     !sim_scan_prepare_all_candidate_states_from_summaries(context,
                                                           context->initialRunSummariesDevice,
                                                           summaryCount,
                                                           NULL,
                                                           0,
                                                           numeric_limits<int>::min(),
                                                           &allCandidateCount,
                                                           errorOut))
  {
    return false;
  }
  if(outBuildSeconds != NULL)
  {
    *outBuildSeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - buildStart).count()) / 1.0e9;
  }

  SimCudaPersistentSafeStoreHandle builtHandle;
  if(!sim_scan_cuda_clone_persistent_safe_store_from_device_locked(
       allCandidateCount > 0 ? context->outputCandidateStatesDevice : NULL,
       static_cast<size_t>(allCandidateCount),
       device,
       slot,
       &builtHandle,
       errorOut))
  {
    return false;
  }

  const chrono::steady_clock::time_point pruneStart = chrono::steady_clock::now();
  if(allCandidateCount > 0)
  {
    cudaError_t status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int threads = 256;
    const int blocks =
      (allCandidateCount + threads - 1) / threads;
    sim_scan_filter_existing_safe_store_candidate_states_kernel<<<blocks, threads>>>(
      sim_scan_cuda_handle_states_device(builtHandle),
      allCandidateCount,
      finalCandidateCount > 0 ? context->candidateStatesDevice : NULL,
      finalCandidateCount,
      runningMin,
      context->outputCandidateStatesDevice,
      context->filteredCandidateCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    int keptCount = 0;
    status = cudaMemcpy(&keptCount,
                        context->filteredCandidateCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(keptCount < 0 || keptCount > allCandidateCount)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
      if(errorOut != NULL)
      {
        *errorOut = "persistent safe-store prune count overflow";
      }
      return false;
    }
    if(keptCount > 0)
    {
      status = cudaMemcpy(sim_scan_cuda_handle_states_device(builtHandle),
                          context->outputCandidateStatesDevice,
                          static_cast<size_t>(keptCount) * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToDevice);
      if(status != cudaSuccess)
      {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
    builtHandle.stateCount = static_cast<size_t>(keptCount);
  }
  if(outPruneSeconds != NULL)
  {
    *outPruneSeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - pruneStart).count()) / 1.0e9;
  }

  const chrono::steady_clock::time_point frontierUploadStart = chrono::steady_clock::now();
  if(!sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
       finalCandidateCount > 0 ? context->candidateStatesDevice : NULL,
       finalCandidateCount,
       runningMin,
       &builtHandle,
       errorOut))
  {
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&builtHandle);
    return false;
  }
  if(outFrontierUploadSeconds != NULL)
  {
    *outFrontierUploadSeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - frontierUploadStart).count()) / 1.0e9;
  }

  *handleOut = builtHandle;
  builtHandle = SimCudaPersistentSafeStoreHandle();
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_cuda_rebuild_persistent_safe_candidate_state_store_from_device_locked(
  SimScanCudaContext *context,
  const uint64_t *trackedStartCoordsDevice,
  int trackedStartCoordCount,
  const SimScanCudaCandidateState *updatedStatesDevice,
  int updatedStateCount,
  const SimScanCudaCandidateState *finalCandidatesDevice,
  int finalCandidateCount,
  int runningMin,
  SimCudaPersistentSafeStoreHandle *handle,
  string *errorOut)
{
  if(context == NULL || handle == NULL || !handle->valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store rebuild inputs";
    }
    return false;
  }
  if(handle->stateCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  handle->stateCount,
                                  errorOut))
  {
    return false;
  }

  int rebuiltCount = static_cast<int>(handle->stateCount);
  if(trackedStartCoordCount > 0)
  {
    cudaError_t status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int threads = 256;
    const int blocks =
      static_cast<int>((handle->stateCount + static_cast<size_t>(threads) - 1) /
                       static_cast<size_t>(threads));
    sim_scan_filter_persistent_safe_store_excluding_start_coords_kernel<<<blocks, threads>>>(
      sim_scan_cuda_handle_states_device(*handle),
      static_cast<int>(handle->stateCount),
      trackedStartCoordsDevice,
      trackedStartCoordCount,
      context->outputCandidateStatesDevice,
      context->filteredCandidateCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    status = cudaMemcpy(&rebuiltCount,
                        context->filteredCandidateCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(rebuiltCount < 0 || static_cast<size_t>(rebuiltCount) > handle->stateCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "persistent safe-store rebuild count overflow";
      }
      return false;
    }
  }
  else if(handle->stateCount > 0)
  {
    const cudaError_t status =
      cudaMemcpy(context->outputCandidateStatesDevice,
                 sim_scan_cuda_handle_states_device(*handle),
                 handle->stateCount * sizeof(SimScanCudaCandidateState),
                 cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  if(updatedStateCount > 0)
  {
    if(rebuiltCount < 0 ||
       static_cast<size_t>(rebuiltCount) > handle->stateCount ||
       static_cast<size_t>(rebuiltCount + updatedStateCount) > handle->stateCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "persistent safe-store updated state count overflow";
      }
      return false;
    }
    const cudaError_t status =
      cudaMemcpy(context->outputCandidateStatesDevice + rebuiltCount,
                 updatedStatesDevice,
                 static_cast<size_t>(updatedStateCount) * sizeof(SimScanCudaCandidateState),
                 cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    rebuiltCount += updatedStateCount;
  }

  if(rebuiltCount > 0)
  {
    const cudaError_t status =
      cudaMemcpy(sim_scan_cuda_handle_states_device(*handle),
                 context->outputCandidateStatesDevice,
                 static_cast<size_t>(rebuiltCount) * sizeof(SimScanCudaCandidateState),
                 cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  handle->stateCount = static_cast<size_t>(rebuiltCount);

  if(handle->stateCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  cudaError_t status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int threads = 256;
  const int blocks =
    static_cast<int>((handle->stateCount + static_cast<size_t>(threads) - 1) /
                     static_cast<size_t>(threads));
  sim_scan_filter_existing_safe_store_candidate_states_kernel<<<blocks, threads>>>(
    sim_scan_cuda_handle_states_device(*handle),
    static_cast<int>(handle->stateCount),
    finalCandidateCount > 0 ? finalCandidatesDevice : NULL,
    finalCandidateCount,
    runningMin,
    context->outputCandidateStatesDevice,
    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int keptCount = 0;
  status = cudaMemcpy(&keptCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(keptCount < 0 || static_cast<size_t>(keptCount) > handle->stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store prune count overflow";
    }
    return false;
  }
  if(keptCount > 0)
  {
    status = cudaMemcpy(sim_scan_cuda_handle_states_device(*handle),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(keptCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  handle->stateCount = static_cast<size_t>(keptCount);
  if(!sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
       finalCandidateCount > 0 ? context->candidateStatesDevice : NULL,
       finalCandidateCount,
       runningMin,
       handle,
       errorOut))
  {
    return false;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_update_persistent_safe_candidate_state_store(const vector<SimScanCudaCandidateState> &updatedStates,
                                                                const vector<SimScanCudaCandidateState> &finalCandidates,
                                                                int runningMin,
                                                                SimCudaPersistentSafeStoreHandle *handle,
                                                                string *errorOut)
{
  if(handle == NULL || !handle->valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(handle->stateCount == 0)
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle->device,handle->slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle->device,errorOut))
  {
    return false;
  }

  const size_t scratchStateCapacity = max(handle->stateCount, updatedStates.size());
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  scratchStateCapacity,
                                  errorOut))
  {
    return false;
  }

  if(!updatedStates.empty())
  {
    vector<SimScanCudaCandidateState> sortedUpdatedStates = updatedStates;
    sort(sortedUpdatedStates.begin(),
         sortedUpdatedStates.end(),
         [](const SimScanCudaCandidateState &lhs,const SimScanCudaCandidateState &rhs)
         {
           return simScanCudaCandidateStateStartCoord(lhs) < simScanCudaCandidateStateStartCoord(rhs);
         });
    vector<uint64_t> updatedKeys(sortedUpdatedStates.size(),0);
    for(size_t stateIndex = 0; stateIndex < sortedUpdatedStates.size(); ++stateIndex)
    {
      updatedKeys[stateIndex] = simScanCudaCandidateStateStartCoord(sortedUpdatedStates[stateIndex]);
    }
    if(!ensure_sim_scan_cuda_buffer(&context->filterStartCoordsDevice,
                                    &context->filterStartCoordsCapacity,
                                    updatedKeys.size(),
                                    errorOut))
    {
      return false;
    }

    cudaError_t status = cudaMemcpy(context->filterStartCoordsDevice,
                                    updatedKeys.data(),
                                    updatedKeys.size() * sizeof(uint64_t),
                                    cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    status = cudaMemcpy(context->outputCandidateStatesDevice,
                        sortedUpdatedStates.data(),
                        sortedUpdatedStates.size() * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int threads = 256;
    const int blocks =
      static_cast<int>((handle->stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
    sim_scan_update_persistent_safe_store_states_kernel<<<blocks, threads>>>(sim_scan_cuda_handle_states_device(*handle),
                                                                             static_cast<int>(handle->stateCount),
                                                                             context->filterStartCoordsDevice,
                                                                             context->outputCandidateStatesDevice,
                                                                             static_cast<int>(sortedUpdatedStates.size()));
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int finalCandidateCount = static_cast<int>(finalCandidates.size());
  if(finalCandidateCount < 0)
  {
    finalCandidateCount = 0;
  }
  if(finalCandidateCount > sim_scan_cuda_max_candidates)
  {
    finalCandidateCount = sim_scan_cuda_max_candidates;
  }
  if(finalCandidateCount > 0)
  {
    cudaError_t status = cudaMemcpy(context->candidateStatesDevice,
                                    finalCandidates.data(),
                                    static_cast<size_t>(finalCandidateCount) * sizeof(SimScanCudaCandidateState),
                                    cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  cudaError_t status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  const int threads = 256;
  const int blocks =
    static_cast<int>((handle->stateCount + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_filter_existing_safe_store_candidate_states_kernel<<<blocks, threads>>>(sim_scan_cuda_handle_states_device(*handle),
                                                                                    static_cast<int>(handle->stateCount),
                                                                                    finalCandidateCount > 0 ? context->candidateStatesDevice : NULL,
                                                                                    finalCandidateCount,
                                                                                    runningMin,
                                                                                    context->outputCandidateStatesDevice,
                                                                                    context->filteredCandidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int keptCount = 0;
  status = cudaMemcpy(&keptCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(keptCount < 0 || static_cast<size_t>(keptCount) > handle->stateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "persistent safe-store prune count overflow";
    }
    return false;
  }
  if(keptCount > 0)
  {
    status = cudaMemcpy(sim_scan_cuda_handle_states_device(*handle),
                        context->outputCandidateStatesDevice,
                        static_cast<size_t>(keptCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  handle->stateCount = static_cast<size_t>(keptCount);
  if(!sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
       finalCandidateCount > 0 ? context->candidateStatesDevice : NULL,
       finalCandidateCount,
       runningMin,
       handle,
       errorOut))
  {
    return false;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

void sim_scan_cuda_release_persistent_safe_candidate_state_store(SimCudaPersistentSafeStoreHandle *handle)
{
  if(handle == NULL)
  {
    return;
  }
  if(handle->frontierStatesDevice != 0)
  {
    cudaSetDevice(handle->device);
    cudaFree(reinterpret_cast<void *>(handle->frontierStatesDevice));
  }
  if(handle->statesDevice != 0)
  {
    cudaSetDevice(handle->device);
    cudaFree(reinterpret_cast<void *>(handle->statesDevice));
  }
  *handle = SimCudaPersistentSafeStoreHandle();
}

static bool sim_scan_cuda_region_true_batch_runtime()
{
  const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

static void sim_scan_cuda_accumulate_batch_result(const SimScanCudaBatchResult &requestBatchResult,
                                                  SimScanCudaBatchResult *batchResult)
{
  if(batchResult == NULL)
  {
    return;
  }
  batchResult->gpuSeconds += requestBatchResult.gpuSeconds;
  batchResult->d2hSeconds += requestBatchResult.d2hSeconds;
  batchResult->proposalSelectGpuSeconds += requestBatchResult.proposalSelectGpuSeconds;
  batchResult->initialDiagSeconds += requestBatchResult.initialDiagSeconds;
  batchResult->initialOnlineReduceSeconds += requestBatchResult.initialOnlineReduceSeconds;
  batchResult->initialWaitSeconds += requestBatchResult.initialWaitSeconds;
  batchResult->initialCountCopySeconds += requestBatchResult.initialCountCopySeconds;
  batchResult->initialBaseUploadSeconds += requestBatchResult.initialBaseUploadSeconds;
  batchResult->initialProposalDirectTopKGpuSeconds += requestBatchResult.initialProposalDirectTopKGpuSeconds;
  batchResult->initialProposalV3GpuSeconds += requestBatchResult.initialProposalV3GpuSeconds;
  batchResult->initialProposalSelectD2HSeconds += requestBatchResult.initialProposalSelectD2HSeconds;
  batchResult->initialSyncWaitSeconds += requestBatchResult.initialSyncWaitSeconds;
  batchResult->initialScanTailSeconds += requestBatchResult.initialScanTailSeconds;
  batchResult->initialHashReduceSeconds += requestBatchResult.initialHashReduceSeconds;
  batchResult->initialSegmentedReduceSeconds += requestBatchResult.initialSegmentedReduceSeconds;
  batchResult->initialSegmentedCompactSeconds += requestBatchResult.initialSegmentedCompactSeconds;
  batchResult->initialOrderedReplaySeconds += requestBatchResult.initialOrderedReplaySeconds;
  batchResult->initialTopKSeconds += requestBatchResult.initialTopKSeconds;
  batchResult->usedCuda = batchResult->usedCuda || requestBatchResult.usedCuda;
  batchResult->usedRegionTrueBatchPath =
    batchResult->usedRegionTrueBatchPath || requestBatchResult.usedRegionTrueBatchPath;
  batchResult->usedRegionPackedAggregationPath =
    batchResult->usedRegionPackedAggregationPath || requestBatchResult.usedRegionPackedAggregationPath;
  batchResult->usedInitialDirectSummaryPath =
    batchResult->usedInitialDirectSummaryPath || requestBatchResult.usedInitialDirectSummaryPath;
  batchResult->usedInitialHashReducePath =
    batchResult->usedInitialHashReducePath || requestBatchResult.usedInitialHashReducePath;
  batchResult->usedInitialSegmentedReducePath =
    batchResult->usedInitialSegmentedReducePath || requestBatchResult.usedInitialSegmentedReducePath;
  batchResult->usedInitialDeviceResidencyPath =
    batchResult->usedInitialDeviceResidencyPath || requestBatchResult.usedInitialDeviceResidencyPath;
  batchResult->usedInitialProposalOnlinePath =
    batchResult->usedInitialProposalOnlinePath || requestBatchResult.usedInitialProposalOnlinePath;
  batchResult->usedInitialProposalV2Path =
    batchResult->usedInitialProposalV2Path || requestBatchResult.usedInitialProposalV2Path;
  batchResult->usedInitialProposalV2DirectTopKPath =
    batchResult->usedInitialProposalV2DirectTopKPath || requestBatchResult.usedInitialProposalV2DirectTopKPath;
  batchResult->usedInitialProposalV3Path =
    batchResult->usedInitialProposalV3Path || requestBatchResult.usedInitialProposalV3Path;
  batchResult->initialHashReduceFallback =
    batchResult->initialHashReduceFallback || requestBatchResult.initialHashReduceFallback;
  batchResult->initialSegmentedFallback =
    batchResult->initialSegmentedFallback || requestBatchResult.initialSegmentedFallback;
  batchResult->initialProposalOnlineFallback =
    batchResult->initialProposalOnlineFallback || requestBatchResult.initialProposalOnlineFallback;
  batchResult->regionTrueBatchRequestCount += requestBatchResult.regionTrueBatchRequestCount;
  batchResult->regionPackedAggregationRequestCount += requestBatchResult.regionPackedAggregationRequestCount;
  batchResult->initialDeviceResidencyRequestCount += requestBatchResult.initialDeviceResidencyRequestCount;
  batchResult->initialProposalV2RequestCount += requestBatchResult.initialProposalV2RequestCount;
  batchResult->initialProposalV3RequestCount += requestBatchResult.initialProposalV3RequestCount;
  batchResult->initialProposalV3SelectedStateCount += requestBatchResult.initialProposalV3SelectedStateCount;
  batchResult->initialProposalLogicalCandidateCount += requestBatchResult.initialProposalLogicalCandidateCount;
  batchResult->initialProposalMaterializedCandidateCount += requestBatchResult.initialProposalMaterializedCandidateCount;
  batchResult->initialSegmentedTileStateCount += requestBatchResult.initialSegmentedTileStateCount;
  batchResult->initialSegmentedGroupedStateCount += requestBatchResult.initialSegmentedGroupedStateCount;
  batchResult->taskCount += requestBatchResult.taskCount;
  batchResult->launchCount += requestBatchResult.launchCount;
  batchResult->initialReduceReplayStats.chunkCount += requestBatchResult.initialReduceReplayStats.chunkCount;
  batchResult->initialReduceReplayStats.chunkReplayedCount += requestBatchResult.initialReduceReplayStats.chunkReplayedCount;
  batchResult->initialReduceReplayStats.chunkSkippedCount += requestBatchResult.initialReduceReplayStats.chunkSkippedCount;
  batchResult->initialReduceReplayStats.summaryReplayCount += requestBatchResult.initialReduceReplayStats.summaryReplayCount;
}

static bool sim_scan_cuda_validate_region_request_inputs(const char *A,
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
                                                         string *errorOut)
{
  if(A == NULL || B == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input sequences";
    }
    return false;
  }
  if(scoreMatrix == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing score matrix";
    }
    return false;
  }
  if(queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid sequence dimensions";
    }
    return false;
  }
  if(rowStart < 1 || rowEnd < rowStart || rowEnd > queryLength || colStart < 1 || colEnd < colStart || colEnd > targetLength)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid region bounds";
    }
    return false;
  }
  if(gapOpen < 0 || gapExtend < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid gap penalties";
    }
    return false;
  }
  if(reduceCandidates && reduceAllCandidateStates)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA region reduce modes are mutually exclusive";
    }
    return false;
  }
  if(filterStartCoordCount < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid filterStartCoordCount";
    }
    return false;
  }
  if(filterStartCoordCount > 0 && filterStartCoords == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing filter start coords";
    }
    return false;
  }
  if(reduceAllCandidateStates && seedCandidateCount != 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA all-candidate reduce does not support seed candidates";
    }
    return false;
  }
  if(blockedWords != NULL && blockedWordCount > 0)
  {
    if(blockedWordStart < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "invalid blockedWordStart";
      }
      return false;
    }
    if(blockedWordStride <= 0 || blockedWordStride < blockedWordCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "invalid blockedWordStride";
      }
      return false;
    }
  }
  if(seedCandidateCount < 0 || seedCandidateCount > sim_scan_cuda_max_candidates)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid seedCandidateCount";
    }
    return false;
  }
  if(seedCandidateCount > 0 && seedCandidates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing seed candidates";
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_can_true_batch_region_requests(const vector<SimScanCudaRequest> &requests)
{
  if(!sim_scan_cuda_region_true_batch_runtime() || requests.empty())
  {
    return false;
  }
  const SimScanCudaRequest &first = requests[0];
  if(first.kind != SIM_SCAN_CUDA_REQUEST_REGION ||
     first.reduceCandidates ||
     !first.reduceAllCandidateStates ||
     first.seedCandidates != NULL ||
     first.seedCandidateCount != 0)
  {
    return false;
  }
  for(size_t i = 0; i < requests.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[i];
    if(request.kind != SIM_SCAN_CUDA_REQUEST_REGION ||
       request.A != first.A ||
       request.B != first.B ||
       request.queryLength != first.queryLength ||
       request.targetLength != first.targetLength ||
       request.gapOpen != first.gapOpen ||
       request.gapExtend != first.gapExtend ||
       request.scoreMatrix != first.scoreMatrix ||
       request.eventScoreFloor != first.eventScoreFloor ||
       request.reduceCandidates != first.reduceCandidates ||
       request.reduceAllCandidateStates != first.reduceAllCandidateStates ||
       request.filterStartCoords != first.filterStartCoords ||
       request.filterStartCoordCount != first.filterStartCoordCount ||
       request.seedCandidates != NULL ||
       request.seedCandidateCount != 0 ||
       request.seedRunningMin != first.seedRunningMin)
    {
      return false;
    }
  }
  return true;
}

static bool sim_scan_cuda_upload_region_common_inputs_locked(SimScanCudaContext *context,
                                                             const char *A,
                                                             const char *B,
                                                             int queryLength,
                                                             int targetLength,
                                                             const int scoreMatrix[128][128],
                                                             string *errorOut);

static bool sim_scan_cuda_upload_region_filter_start_coords_locked(SimScanCudaContext *context,
                                                                   const uint64_t *filterStartCoords,
                                                                   int filterStartCoordCount,
                                                                   string *errorOut);

static bool sim_scan_cuda_execute_region_request_locked(SimScanCudaContext *context,
                                                        int queryLength,
                                                        int targetLength,
                                                        int rowStart,
                                                        int rowEnd,
                                                        int colStart,
                                                        int colEnd,
                                                        int gapOpen,
                                                        int gapExtend,
                                                        int eventScoreFloor,
                                                        const uint64_t *blockedWords,
                                                        int blockedWordStart,
                                                        int blockedWordCount,
                                                        int blockedWordStride,
                                                        bool reduceCandidates,
                                                        bool reduceAllCandidateStates,
                                                        const uint64_t *filterStartCoords,
                                                        int filterStartCoordCount,
                                                        bool filterStartCoordsUploaded,
                                                        const SimScanCudaCandidateState *seedCandidates,
                                                        int seedCandidateCount,
                                                        int seedRunningMin,
                                                        vector<SimScanCudaCandidateState> *outCandidateStates,
                                                        int *outCandidateStateCount,
                                                        bool materializeCandidateStatesToHost,
                                                        int *outRunningMin,
                                                        int *outEventCount,
                                                        uint64_t *outRunSummaryCount,
                                                        vector<SimScanCudaRowEvent> *outEvents,
                                                        vector<int> *outRowOffsets,
                                                        SimScanCudaBatchResult *batchResult,
                                                        string *errorOut);

static bool sim_scan_cuda_enumerate_region_events_row_major_true_batch(const vector<SimScanCudaRequest> &requests,
                                                                       vector<SimScanCudaRequestResult> *outResults,
                                                                       SimScanCudaBatchResult *batchResult,
                                                                       string *errorOut);

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
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(sim_scan_cuda_can_true_batch_region_requests(requests))
  {
    return sim_scan_cuda_enumerate_region_events_row_major_true_batch(requests,
                                                                      outResults,
                                                                      batchResult,
                                                                      errorOut);
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
                                                            errorOut,
                                                            request.persistAllCandidateStatesOnDevice ?
                                                              &requestResult.persistentSafeStoreHandle :
                                                              NULL);
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
      for(size_t resultIndex = 0; resultIndex < outResults->size(); ++resultIndex)
      {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&(*outResults)[resultIndex].persistentSafeStoreHandle);
      }
      outResults->clear();
      if(batchResult != NULL)
      {
        *batchResult = SimScanCudaBatchResult();
      }
      return false;
    }

    outResults->push_back(requestResult);
    sim_scan_cuda_accumulate_batch_result(requestBatchResult,batchResult);
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_cuda_enumerate_initial_events_row_major_via_true_batch(const char *A,
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
  vector<SimScanCudaInitialBatchRequest> requests(1);
  requests[0].A = A;
  requests[0].B = B;
  requests[0].queryLength = queryLength;
  requests[0].targetLength = targetLength;
  requests[0].gapOpen = gapOpen;
  requests[0].gapExtend = gapExtend;
  requests[0].scoreMatrix = scoreMatrix;
  requests[0].eventScoreFloor = eventScoreFloor;
  requests[0].reduceCandidates = reduceCandidates;
  requests[0].proposalCandidates = proposalCandidates;
  requests[0].persistAllCandidateStatesOnDevice =
    (reduceCandidates || proposalCandidates) && outPersistentSafeStoreHandle != NULL;

  vector<SimScanCudaInitialBatchResult> results;
  SimScanCudaBatchResult trueBatchResult;
  if(!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                  &results,
                                                                  &trueBatchResult,
                                                                  errorOut))
  {
    return false;
  }
  if(results.size() != 1u)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA single initial true-batch result count mismatch";
    }
    return false;
  }

  const SimScanCudaInitialBatchResult &result = results[0];
  if(outRunSummaries != NULL)
  {
    *outRunSummaries = result.initialRunSummaries;
  }
  if(outCandidateStates != NULL)
  {
    *outCandidateStates = result.candidateStates;
  }
  if(outAllCandidateStates != NULL)
  {
    *outAllCandidateStates = result.allCandidateStates;
  }
  if(outAllCandidateStateCount != NULL)
  {
    *outAllCandidateStateCount = result.allCandidateStateCount;
  }
  if(outRunningMin != NULL)
  {
    *outRunningMin = result.runningMin;
  }
  if(outEventCount != NULL)
  {
    *outEventCount = result.eventCount;
  }
  if(outRunSummaryCount != NULL)
  {
    *outRunSummaryCount = result.runSummaryCount;
  }
  if(batchResult != NULL)
  {
    *batchResult = trueBatchResult;
  }
  if(outPersistentSafeStoreHandle != NULL)
  {
    *outPersistentSafeStoreHandle = result.persistentSafeStoreHandle;
  }
  return true;
}

static bool sim_scan_cuda_build_proposal_candidates_online_locked(SimScanCudaContext *context,
                                                                  int M,
                                                                  int N,
                                                                  int gapOpen,
                                                                  int gapExtend,
                                                                  int eventScoreFloor,
                                                                  int *outTotalEvents,
                                                                  int *outTotalRunSummaries,
                                                                  int *outAllCandidateCount,
                                                                  bool *outFallback,
                                                                  double *outDiagSeconds,
                                                                  double *outOnlineReduceSeconds,
                                                                  string *errorOut)
{
  if(context == NULL ||
     outTotalEvents == NULL ||
     outTotalRunSummaries == NULL ||
     outAllCandidateCount == NULL ||
     outFallback == NULL ||
     outDiagSeconds == NULL ||
     outOnlineReduceSeconds == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing proposal online outputs";
    }
    return false;
  }
  *outTotalEvents = 0;
  *outTotalRunSummaries = 0;
  *outAllCandidateCount = 0;
  *outFallback = false;
  *outDiagSeconds = 0.0;
  *outOnlineReduceSeconds = 0.0;
  if(M <= 0 || N <= 0)
  {
    return true;
  }

  const size_t rowCount = static_cast<size_t>(M + 1);
  const size_t hashCapacity = sim_scan_cuda_initial_proposal_hash_capacity_runtime(M,N);
  if(hashCapacity == 0)
  {
    *outFallback = true;
    return true;
  }

  if(!ensure_sim_scan_cuda_buffer(&context->proposalRowStatesDevice,
                                  &context->proposalRowStatesCapacity,
                                  rowCount,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->proposalOnlineHashKeysDevice,
                                  &context->proposalOnlineHashKeysCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->proposalOnlineHashFlagsDevice,
                                  &context->proposalOnlineHashFlagsCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->proposalOnlineHashStatesDevice,
                                  &context->proposalOnlineHashStatesCapacity,
                                  hashCapacity,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  hashCapacity,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemset(context->proposalRowStatesDevice,
                                  0,
                                  rowCount * sizeof(SimScanCudaProposalRowSummaryState));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->proposalOnlineHashFlagsDevice,0,hashCapacity * sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  const int zero = 0;
  status = cudaMemcpy(context->eventCountDevice,&zero,sizeof(int),cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->candidateCountDevice,&zero,sizeof(int),cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->filteredCandidateCountDevice,&zero,sizeof(int),cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->runningMinDevice,&zero,sizeof(int),cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int QR = gapOpen + gapExtend;
  int *ppH = context->diagH0;
  uint64_t *ppHc = context->diagHc0;
  int *prevH = context->diagH1;
  uint64_t *prevHc = context->diagHc1;
  int *curH = context->diagH2;
  uint64_t *curHc = context->diagHc2;

  int *prevD = context->diagD1;
  uint64_t *prevDc = context->diagDc1;
  int *curD = context->diagD2;
  uint64_t *curDc = context->diagDc2;

  int *prevF = context->diagF1;
  uint64_t *prevFc = context->diagFc1;
  int *curF = context->diagF2;
  uint64_t *curFc = context->diagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;

  const std::chrono::steady_clock::time_point diagStart = std::chrono::steady_clock::now();
  for(int diag = 2; diag <= M + N; ++diag)
  {
    const int curStartIHost = max(1, diag - N);
    const int curEndIHost = min(M, diag - 1);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int threadsPerBlock = 256;
    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_proposal_online_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                                      context->BDevice,
                                                                      N,
                                                                      diag,
                                                                      curStartIHost,
                                                                      curLenHost,
                                                                      prevStartI,
                                                                      prevLen,
                                                                      ppStartI,
                                                                      ppLen,
                                                                      gapOpen,
                                                                      gapExtend,
                                                                      QR,
                                                                      prevH,
                                                                      prevHc,
                                                                      prevD,
                                                                      prevDc,
                                                                      prevF,
                                                                      prevFc,
                                                                      ppH,
                                                                      ppHc,
                                                                      curH,
                                                                      curHc,
                                                                      curD,
                                                                      curDc,
                                                                      curF,
                                                                      curFc,
                                                                      eventScoreFloor,
                                                                      context->proposalRowStatesDevice,
                                                                      context->proposalOnlineHashKeysDevice,
                                                                      context->proposalOnlineHashFlagsDevice,
                                                                      context->proposalOnlineHashStatesDevice,
                                                                      hashCapacity,
                                                                      context->eventCountDevice,
                                                                      context->candidateCountDevice,
                                                                      context->filteredCandidateCountDevice,
                                                                      context->runningMinDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);

    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }
  status = cudaDeviceSynchronize();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  *outDiagSeconds =
    static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::steady_clock::now() - diagStart).count()) / 1.0e9;

  int overflow = 0;
  status = cudaMemcpy(&overflow,context->runningMinDevice,sizeof(int),cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(overflow != 0)
  {
    *outFallback = true;
    return true;
  }

  status = cudaMemcpy(outTotalEvents,
                      context->eventCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(outTotalRunSummaries,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemcpy(context->candidateCountDevice,&zero,sizeof(int),cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const std::chrono::steady_clock::time_point compactStart = std::chrono::steady_clock::now();
  const int threads = 256;
  const int blocks = static_cast<int>((hashCapacity + static_cast<size_t>(threads) - 1) / static_cast<size_t>(threads));
  sim_scan_compact_online_candidate_states_kernel<<<blocks, threads>>>(context->proposalOnlineHashFlagsDevice,
                                                                       context->proposalOnlineHashStatesDevice,
                                                                       hashCapacity,
                                                                       context->outputCandidateStatesDevice,
                                                                       context->candidateCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaDeviceSynchronize();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  *outOnlineReduceSeconds =
    static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::steady_clock::now() - compactStart).count()) / 1.0e9;

  status = cudaMemcpy(outAllCandidateCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int uniqueCount = 0;
  status = cudaMemcpy(&uniqueCount,
                      context->filteredCandidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(uniqueCount != *outAllCandidateCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA proposal online compact count mismatch";
    }
    return false;
  }

  if(*outAllCandidateCount > 1)
  {
    try
    {
      thrust::stable_sort(thrust::device,
                          thrust::device_pointer_cast(context->outputCandidateStatesDevice),
                          thrust::device_pointer_cast(context->outputCandidateStatesDevice + *outAllCandidateCount),
                          SimScanCudaCandidateStartCoordLess());
    }
    catch(const thrust::system_error &e)
    {
      if(errorOut != NULL)
      {
        *errorOut = e.what();
      }
      return false;
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

static bool sim_scan_cuda_build_initial_run_summaries_proposal_streaming_locked(SimScanCudaContext *context,
                                                                                int M,
                                                                                int N,
                                                                                int gapOpen,
                                                                                int gapExtend,
                                                                                int eventScoreFloor,
                                                                                int *outTotalEvents,
                                                                                int *outTotalRunSummaries,
                                                                                string *errorOut)
{
  if(context == NULL || outTotalEvents == NULL || outTotalRunSummaries == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing proposal streaming outputs";
    }
    return false;
  }
  *outTotalEvents = 0;
  *outTotalRunSummaries = 0;
  if(M <= 0 || N <= 0)
  {
    return true;
  }

  const size_t rowCount = static_cast<size_t>(M + 1);
  const size_t rowCountBytes = rowCount * sizeof(int);
  const size_t rowOffsetBytes = static_cast<size_t>(M + 2) * sizeof(int);
  if(!ensure_sim_scan_cuda_buffer(&context->proposalRowStatesDevice,
                                  &context->proposalRowStatesCapacity,
                                  rowCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemset(context->rowCountsDevice,0,rowCountBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->rowOffsetsDevice,0,rowOffsetBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->proposalRowStatesDevice,
                      0,
                      rowCount * sizeof(SimScanCudaProposalRowSummaryState));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int QR = gapOpen + gapExtend;
  int *ppH = context->diagH0;
  uint64_t *ppHc = context->diagHc0;
  int *prevH = context->diagH1;
  uint64_t *prevHc = context->diagHc1;
  int *curH = context->diagH2;
  uint64_t *curHc = context->diagHc2;

  int *prevD = context->diagD1;
  uint64_t *prevDc = context->diagDc1;
  int *curD = context->diagD2;
  uint64_t *curDc = context->diagDc2;

  int *prevF = context->diagF1;
  uint64_t *prevFc = context->diagFc1;
  int *curF = context->diagF2;
  uint64_t *curFc = context->diagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;

  for(int diag = 2; diag <= M + N; ++diag)
  {
    const int curStartIHost = max(1, diag - N);
    const int curEndIHost = min(M, diag - 1);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int threadsPerBlock = 256;
    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_proposal_count_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                                     context->BDevice,
                                                                     M,
                                                                     N,
                                                                     diag,
                                                                     curStartIHost,
                                                                     curLenHost,
                                                                     prevStartI,
                                                                     prevLen,
                                                                     ppStartI,
                                                                     ppLen,
                                                                     gapOpen,
                                                                     gapExtend,
                                                                     QR,
                                                                     prevH,
                                                                     prevHc,
                                                                     prevD,
                                                                     prevDc,
                                                                     prevF,
                                                                     prevFc,
                                                                     ppH,
                                                                     ppHc,
                                                                     curH,
                                                                     curHc,
                                                                     curD,
                                                                     curDc,
                                                                     curF,
                                                                     curFc,
                                                                     eventScoreFloor,
                                                                     context->proposalRowStatesDevice,
                                                                     context->rowCountsDevice,
                                                                     context->rowOffsetsDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);

    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowOffsetsDevice,
                                       M + 1,
                                       context->runOffsetsDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int totalEvents = 0;
  status = cudaMemcpy(&totalEvents,
                      context->eventCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                       M + 1,
                                       context->rowOffsetsDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int totalRunSummaries = 0;
  status = cudaMemcpy(&totalRunSummaries,
                      context->eventCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(totalRunSummaries > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                    &context->initialRunSummariesCapacity,
                                    static_cast<size_t>(totalRunSummaries),
                                    errorOut))
    {
      return false;
    }
  }

  status = cudaMemset(context->rowCountsDevice,0,rowCountBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->proposalRowStatesDevice,
                      0,
                      rowCount * sizeof(SimScanCudaProposalRowSummaryState));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  ppH = context->diagH0;
  ppHc = context->diagHc0;
  prevH = context->diagH1;
  prevHc = context->diagHc1;
  curH = context->diagH2;
  curHc = context->diagHc2;

  prevD = context->diagD1;
  prevDc = context->diagDc1;
  curD = context->diagD2;
  curDc = context->diagDc2;

  prevF = context->diagF1;
  prevFc = context->diagFc1;
  curF = context->diagF2;
  curFc = context->diagFc2;

  ppStartI = 0;
  ppLen = 0;
  prevStartI = 0;
  prevLen = 0;

  for(int diag = 2; diag <= M + N && totalRunSummaries > 0; ++diag)
  {
    const int curStartIHost = max(1, diag - N);
    const int curEndIHost = min(M, diag - 1);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int threadsPerBlock = 256;
    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_proposal_write_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                                     context->BDevice,
                                                                     M,
                                                                     N,
                                                                     diag,
                                                                     curStartIHost,
                                                                     curLenHost,
                                                                     prevStartI,
                                                                     prevLen,
                                                                     ppStartI,
                                                                     ppLen,
                                                                     gapOpen,
                                                                     gapExtend,
                                                                     QR,
                                                                     prevH,
                                                                     prevHc,
                                                                     prevD,
                                                                     prevDc,
                                                                     prevF,
                                                                     prevFc,
                                                                     ppH,
                                                                     ppHc,
                                                                     curH,
                                                                     curHc,
                                                                     curD,
                                                                     curDc,
                                                                     curF,
                                                                     curFc,
                                                                     eventScoreFloor,
                                                                     context->proposalRowStatesDevice,
                                                                     context->rowOffsetsDevice,
                                                                     context->rowCountsDevice,
                                                                     context->initialRunSummariesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);

    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  *outTotalEvents = totalEvents;
  *outTotalRunSummaries = totalRunSummaries;
  return true;
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
  if(outEventCount == NULL || outRunSummaryCount == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  if(reduceCandidates && proposalCandidates)
  {
    if(errorOut != NULL)
    {
      *errorOut = "initial CUDA proposalCandidates and reduceCandidates are mutually exclusive";
    }
    return false;
  }
  const bool extractCandidateStates = reduceCandidates || proposalCandidates;
  if(!extractCandidateStates && outRunSummaries == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing initial run summary output";
    }
    return false;
  }
  if(extractCandidateStates && (outCandidateStates == NULL || outRunningMin == NULL))
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing reduced candidate output";
    }
    return false;
  }
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
  *outEventCount = 0;
  *outRunSummaryCount = 0;
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(outPersistentSafeStoreHandle != NULL)
  {
    *outPersistentSafeStoreHandle = SimCudaPersistentSafeStoreHandle();
  }
  if(A == NULL || B == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input sequences";
    }
    return false;
  }
  if(queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid sequence dimensions";
    }
    return false;
  }
  if(gapOpen < 0 || gapExtend < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid gap penalties";
    }
    return false;
  }
  if((!proposalCandidates && !reduceCandidates) ||
     (reduceCandidates &&
      !proposalCandidates &&
      sim_scan_cuda_initial_reduce_backend_runtime() !=
        SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_LEGACY))
  {
    return sim_scan_cuda_enumerate_initial_events_row_major_via_true_batch(A,
                                                                           B,
                                                                           queryLength,
                                                                           targetLength,
                                                                           gapOpen,
                                                                           gapExtend,
                                                                           scoreMatrix,
                                                                           eventScoreFloor,
                                                                           reduceCandidates,
                                                                           proposalCandidates,
                                                                           outRunSummaries,
                                                                           outCandidateStates,
                                                                           outAllCandidateStates,
                                                                           outAllCandidateStateCount,
                                                                           outRunningMin,
                                                                           outEventCount,
                                                                           outRunSummaryCount,
                                                                           batchResult,
                                                                           errorOut,
                                                                           outPersistentSafeStoreHandle);
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_capacity_locked(*context,queryLength,targetLength,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->ADevice,
                                  A,
                                  static_cast<size_t>(queryLength + 1) * sizeof(char),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->BDevice,
                      B,
                      static_cast<size_t>(targetLength + 1) * sizeof(char),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemcpyToSymbol(sim_score_matrix, scoreMatrix, sizeof(int) * 128 * 128);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int QR = gapOpen + gapExtend;
  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int M = queryLength;
  const int N = targetLength;
  const std::chrono::steady_clock::time_point d2hStart = std::chrono::steady_clock::now();
  const bool useProposalResidencyFrontierPath =
    proposalCandidates && !reduceCandidates && outPersistentSafeStoreHandle != NULL;
  const bool requestProposalOnlinePath =
    proposalCandidates &&
    !reduceCandidates &&
    !useProposalResidencyFrontierPath &&
    sim_scan_cuda_initial_proposal_online_runtime();
  bool usedProposalOnlinePath = false;
  bool proposalOnlineFallback = false;
  double initialDiagSeconds = 0.0;
  double initialOnlineReduceSeconds = 0.0;
  const bool useProposalStreamingPath =
    proposalCandidates &&
    !reduceCandidates &&
    !useProposalResidencyFrontierPath &&
    !requestProposalOnlinePath &&
    sim_scan_cuda_initial_proposal_streaming_runtime();
  const int summaryThreads = 256;
  const int summaryBlocks = M;
  const size_t summarySharedBytes = static_cast<size_t>(summaryThreads) * sizeof(int);
  int totalEvents = 0;
  int totalRunSummaries = 0;
  int allCandidateStateCount = 0;
  if(requestProposalOnlinePath)
  {
    if(!sim_scan_cuda_build_proposal_candidates_online_locked(context,
                                                              M,
                                                              N,
                                                              gapOpen,
                                                              gapExtend,
                                                              eventScoreFloor,
                                                              &totalEvents,
                                                              &totalRunSummaries,
                                                              &allCandidateStateCount,
                                                              &proposalOnlineFallback,
                                                              &initialDiagSeconds,
                                                              &initialOnlineReduceSeconds,
                                                              errorOut))
    {
      return false;
    }
    usedProposalOnlinePath = !proposalOnlineFallback;
  }

  if(!usedProposalOnlinePath && useProposalStreamingPath)
  {
    if(!sim_scan_cuda_build_initial_run_summaries_proposal_streaming_locked(context,
                                                                            M,
                                                                            N,
                                                                            gapOpen,
                                                                            gapExtend,
                                                                            eventScoreFloor,
                                                                            &totalEvents,
                                                                            &totalRunSummaries,
                                                                            errorOut))
    {
      return false;
    }
  }
  else if(!usedProposalOnlinePath)
  {
    int *ppH = context->diagH0;
    uint64_t *ppHc = context->diagHc0;
    int *prevH = context->diagH1;
    uint64_t *prevHc = context->diagHc1;
    int *curH = context->diagH2;
    uint64_t *curHc = context->diagHc2;

    int *prevD = context->diagD1;
    uint64_t *prevDc = context->diagDc1;
    int *curD = context->diagD2;
    uint64_t *curDc = context->diagDc2;

    int *prevF = context->diagF1;
    uint64_t *prevFc = context->diagFc1;
    int *curF = context->diagF2;
    uint64_t *curFc = context->diagFc2;

    int ppStartI = 0;
    int ppLen = 0;
    int prevStartI = 0;
    int prevLen = 0;

    for(int diag = 2; diag <= M + N; ++diag)
    {
      const int curStartIHost = max(1, diag - N);
      const int curEndIHost = min(M, diag - 1);
      const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
      if(curLenHost <= 0)
      {
        continue;
      }

      const int threadsPerBlock = 256;
      const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;

      sim_scan_diag_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                        context->BDevice,
                                                        M,
                                                        N,
                                                        context->leadingDim,
                                                        diag,
                                                        curStartIHost,
                                                        curLenHost,
                                                        prevStartI,
                                                        prevLen,
                                                        ppStartI,
                                                        ppLen,
                                                        gapOpen,
                                                        gapExtend,
                                                        QR,
                                                        prevH,
                                                        prevHc,
                                                        prevD,
                                                        prevDc,
                                                        prevF,
                                                        prevFc,
                                                        ppH,
                                                        ppHc,
                                                        curH,
                                                        curHc,
                                                        curD,
                                                        curDc,
                                                        curF,
                                                        curFc,
                                                        context->HScoreDevice,
                                                        context->HCoordDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      ppStartI = prevStartI;
      ppLen = prevLen;
      prevStartI = curStartIHost;
      prevLen = curLenHost;

      std::swap(ppH, prevH);
      std::swap(ppHc, prevHc);
      std::swap(prevH, curH);
      std::swap(prevHc, curHc);

      std::swap(prevD, curD);
      std::swap(prevDc, curDc);
      std::swap(prevF, curF);
      std::swap(prevFc, curFc);
    }

    const int countThreads = 256;
    const int countBlocks = M;
    const size_t countSharedBytes = static_cast<size_t>(countThreads) * sizeof(int);
    sim_scan_count_row_events_kernel<<<countBlocks, countThreads, countSharedBytes>>>(context->HScoreDevice,
                                                                                     context->leadingDim,
                                                                                     M,
                                                                                     N,
                                                                                     eventScoreFloor,
                                                                                     context->rowCountsDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                         M + 1,
                                         context->rowOffsetsDevice,
                                         context->eventCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    status = cudaMemcpy(&totalEvents,
                        context->eventCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    if(totalEvents > 0)
    {
      if(context->eventsDevice == NULL || context->eventsCapacity < static_cast<size_t>(totalEvents))
      {
        if(context->eventsDevice != NULL)
        {
          cudaFree(context->eventsDevice);
          context->eventsDevice = NULL;
          context->eventsCapacity = 0;
        }
        cudaError_t allocStatus =
          cudaMalloc(reinterpret_cast<void **>(&context->eventsDevice),
                     static_cast<size_t>(totalEvents) * sizeof(SimScanCudaRowEvent));
        if(allocStatus != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(allocStatus);
          }
          return false;
        }
        context->eventsCapacity = static_cast<size_t>(totalEvents);
      }

      const int compactThreads = 256;
      const int compactBlocks = M;
      sim_scan_compact_row_events_kernel<<<compactBlocks, compactThreads>>>(context->HScoreDevice,
                                                                           context->HCoordDevice,
                                                                           context->leadingDim,
                                                                           M,
                                                                           N,
                                                                           eventScoreFloor,
                                                                           context->rowOffsetsDevice,
                                                                           context->eventsDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      sim_scan_count_initial_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                         context->rowOffsetsDevice,
                                                                                                         M,
                                                                                                         context->rowCountsDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                           M + 1,
                                           context->runOffsetsDevice,
                                           context->eventCountDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }

    status = cudaMemcpy(&totalRunSummaries,
                        context->eventCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  *outEventCount = static_cast<uint64_t>(totalEvents);
  const size_t maxEventsAllowed = static_cast<size_t>(M) * static_cast<size_t>(N);
  if(static_cast<size_t>(totalEvents) > maxEventsAllowed)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA event count overflow";
    }
    return false;
  }
  if(totalRunSummaries < 0 || static_cast<size_t>(totalRunSummaries) > maxEventsAllowed)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA run summary count overflow";
    }
    return false;
  }
  if(totalRunSummaries > totalEvents)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA run summary count exceeds event count";
    }
    return false;
  }
  *outRunSummaryCount = static_cast<uint64_t>(totalRunSummaries);
  if(reduceCandidates || useProposalResidencyFrontierPath)
  {
    const int zero = 0;
    status = cudaMemcpy(context->candidateCountDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    status = cudaMemcpy(context->runningMinDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int reducedCandidateCount = 0;
  int reducedRunningMin = 0;
  double proposalSelectGpuSeconds = 0.0;
  SimScanCudaInitialReduceReplayStats replayStats;
  if(totalRunSummaries > 0 && !usedProposalOnlinePath)
  {
    if(!useProposalStreamingPath)
    {
      if(context->initialRunSummariesDevice == NULL ||
         context->initialRunSummariesCapacity < static_cast<size_t>(totalRunSummaries))
      {
        if(context->initialRunSummariesDevice != NULL)
        {
          cudaFree(context->initialRunSummariesDevice);
          context->initialRunSummariesDevice = NULL;
          context->initialRunSummariesCapacity = 0;
        }
        cudaError_t allocStatus =
          cudaMalloc(reinterpret_cast<void **>(&context->initialRunSummariesDevice),
                     static_cast<size_t>(totalRunSummaries) * sizeof(SimScanCudaInitialRunSummary));
        if(allocStatus != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(allocStatus);
          }
          return false;
        }
        context->initialRunSummariesCapacity = static_cast<size_t>(totalRunSummaries);
      }

      sim_scan_compact_initial_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                           context->rowOffsetsDevice,
                                                                                                           M,
                                                                                                           context->runOffsetsDevice,
                                                                                                           context->initialRunSummariesDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }

    if(extractCandidateStates)
    {
      if(reduceCandidates || useProposalResidencyFrontierPath)
      {
        const int reduceChunkSize = sim_scan_cuda_initial_reduce_chunk_size_runtime();
        if(!ensure_sim_scan_cuda_buffer(&context->initialReduceReplayStatsDevice,
                                        &context->initialReduceReplayStatsCapacity,
                                        static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count),
                                        errorOut))
        {
          return false;
        }
        status = cudaMemset(context->initialReduceReplayStatsDevice,
                            0,
                            static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long));
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        sim_scan_reduce_initial_candidate_states_kernel<<<1, sim_scan_initial_reduce_threads>>>(context->initialRunSummariesDevice,
                                                                                                totalRunSummaries,
                                                                                                context->candidateStatesDevice,
                                                                                                context->candidateCountDevice,
                                                                                                context->runningMinDevice,
                                                                                                NULL,
                                                                                                reduceChunkSize,
                                                                                                context->initialReduceReplayStatsDevice,
                                                                                                NULL,
                                                                                                NULL,
                                                                                                NULL);
        status = cudaGetLastError();
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        status = cudaMemcpy(&reducedCandidateCount,
                            context->candidateCountDevice,
                            sizeof(int),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        status = cudaMemcpy(&reducedRunningMin,
                            context->runningMinDevice,
                            sizeof(int),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        unsigned long long replayStatsHost[sim_scan_initial_reduce_chunk_stats_count] = {0, 0, 0};
        status = cudaMemcpy(replayStatsHost,
                            context->initialReduceReplayStatsDevice,
                            static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        replayStats.chunkCount = static_cast<uint64_t>(replayStatsHost[0]);
        replayStats.chunkReplayedCount = static_cast<uint64_t>(replayStatsHost[1]);
        replayStats.summaryReplayCount = static_cast<uint64_t>(replayStatsHost[2]);
        replayStats.chunkSkippedCount =
          replayStats.chunkCount >= replayStats.chunkReplayedCount ?
          (replayStats.chunkCount - replayStats.chunkReplayedCount) : 0;
        if(reducedCandidateCount < 0)
        {
          reducedCandidateCount = 0;
        }
        if(reducedCandidateCount > sim_scan_cuda_max_candidates)
        {
          reducedCandidateCount = sim_scan_cuda_max_candidates;
        }
        if(!sim_scan_prepare_all_candidate_states_from_summaries(context,
                                                                 context->initialRunSummariesDevice,
                                                                 totalRunSummaries,
                                                                 context->candidateStatesDevice,
                                                                 reducedCandidateCount,
                                                                 reducedRunningMin,
                                                                 &allCandidateStateCount,
                                                                 errorOut))
        {
          return false;
        }
      }
      else
      {
        if(!sim_scan_prepare_all_candidate_states_from_summaries(context,
                                                                 context->initialRunSummariesDevice,
                                                                 totalRunSummaries,
                                                                 NULL,
                                                                 0,
                                                                 numeric_limits<int>::min(),
                                                                 &allCandidateStateCount,
                                                                 errorOut))
        {
          return false;
        }
      }
    }
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(extractCandidateStates)
  {
    if(outAllCandidateStateCount != NULL)
    {
      *outAllCandidateStateCount = static_cast<uint64_t>(allCandidateStateCount);
    }
    if(outRunningMin != NULL)
    {
      *outRunningMin =
        (proposalCandidates && !useProposalResidencyFrontierPath) ? 0 : reducedRunningMin;
    }
    if(outPersistentSafeStoreHandle != NULL)
    {
      if(!sim_scan_cuda_clone_persistent_safe_store_from_device_locked(context->outputCandidateStatesDevice,
                                                                       static_cast<size_t>(allCandidateStateCount),
                                                                       device,
                                                                       slot,
                                                                       outPersistentSafeStoreHandle,
                                                                       errorOut))
      {
        return false;
      }
    }
    else if(!proposalCandidates && outAllCandidateStates != NULL && allCandidateStateCount > 0)
    {
      outAllCandidateStates->resize(static_cast<size_t>(allCandidateStateCount));
      status = cudaMemcpy(outAllCandidateStates->data(),
                          context->outputCandidateStatesDevice,
                          static_cast<size_t>(allCandidateStateCount) * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        outAllCandidateStates->clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
    if(reduceCandidates || useProposalResidencyFrontierPath)
    {
      if(outCandidateStates != NULL && reducedCandidateCount > 0)
      {
        outCandidateStates->resize(static_cast<size_t>(reducedCandidateCount));
        status = cudaMemcpy(outCandidateStates->data(),
                            context->candidateStatesDevice,
                            static_cast<size_t>(reducedCandidateCount) * sizeof(SimScanCudaCandidateState),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          outCandidateStates->clear();
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
      }
    }
    else if(outCandidateStates != NULL && allCandidateStateCount > 0)
    {
      if(!sim_scan_select_top_disjoint_candidate_states_from_device_locked(context,
                                                                           context->outputCandidateStatesDevice,
                                                                           allCandidateStateCount,
                                                                           sim_scan_cuda_max_candidates,
                                                                           outCandidateStates,
                                                                           &proposalSelectGpuSeconds,
                                                                           errorOut))
      {
        return false;
      }
    }
  }
  else if(totalRunSummaries > 0 && !usedProposalOnlinePath)
  {
    outRunSummaries->resize(static_cast<size_t>(totalRunSummaries));
    status = cudaMemcpy(outRunSummaries->data(),
                        context->initialRunSummariesDevice,
                        static_cast<size_t>(totalRunSummaries) * sizeof(SimScanCudaInitialRunSummary),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outRunSummaries->clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  if(batchResult != NULL)
  {
    const bool usedDeviceResidencyPath =
      reduceCandidates && !proposalCandidates && outPersistentSafeStoreHandle != NULL;
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->d2hSeconds =
      static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - d2hStart).count()) / 1.0e9;
    batchResult->initialScanTailSeconds = batchResult->d2hSeconds;
    batchResult->proposalSelectGpuSeconds = proposalSelectGpuSeconds;
    batchResult->initialDiagSeconds = initialDiagSeconds;
    batchResult->initialOnlineReduceSeconds = initialOnlineReduceSeconds;
    batchResult->initialWaitSeconds = batchResult->d2hSeconds;
    batchResult->initialCountCopySeconds = batchResult->d2hSeconds;
    batchResult->initialBaseUploadSeconds = 0.0;
    batchResult->usedInitialDeviceResidencyPath = usedDeviceResidencyPath;
    batchResult->initialDeviceResidencyRequestCount = usedDeviceResidencyPath ? 1u : 0u;
    batchResult->usedInitialProposalOnlinePath = usedProposalOnlinePath;
    batchResult->initialProposalOnlineFallback = proposalOnlineFallback;
    batchResult->initialSyncWaitSeconds = 0.0;
    batchResult->taskCount = 1;
    batchResult->launchCount = 1;
    batchResult->initialReduceReplayStats = replayStats;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
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
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  bool anyReduceCandidates = false;
  bool anyProposalCandidates = false;
  bool anySummaryRequests = false;
  bool anyHostAllCandidateStates = false;
  int deviceResidencyRequestCount = 0;
  int proposalRequestCount = 0;
  for(size_t i = 0; i < requests.size(); ++i)
  {
    if(requests[i].reduceCandidates && requests[i].proposalCandidates)
    {
      if(errorOut != NULL)
      {
        *errorOut = "initial true batch proposalCandidates and reduceCandidates are mutually exclusive";
      }
      return false;
    }
    if(requests[i].reduceCandidates)
    {
      anyReduceCandidates = true;
      if(requests[i].persistAllCandidateStatesOnDevice)
      {
        ++deviceResidencyRequestCount;
      }
      if(!requests[i].persistAllCandidateStatesOnDevice)
      {
        anyHostAllCandidateStates = true;
      }
    }
    else if(requests[i].proposalCandidates)
    {
      anyProposalCandidates = true;
      ++proposalRequestCount;
    }
    else
    {
      anySummaryRequests = true;
    }
  }
  if(anyReduceCandidates && anyProposalCandidates)
  {
    if(errorOut != NULL)
    {
      *errorOut = "initial true batch does not support mixing reduceCandidates with proposalCandidates";
    }
    return false;
  }
  const bool anyCandidateExtraction = anyReduceCandidates || anyProposalCandidates;
  const bool useProposalV3Path =
    anyProposalCandidates && !anyReduceCandidates && sim_scan_cuda_initial_proposal_v3_runtime();
  const bool useProposalV2Path =
    anyProposalCandidates && !anyReduceCandidates && !useProposalV3Path && sim_scan_cuda_initial_proposal_v2_runtime();

  const SimScanCudaInitialBatchRequest &first = requests[0];
  if(first.A == NULL || first.B == NULL || first.scoreMatrix == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input sequences";
    }
    return false;
  }
  if(first.queryLength <= 0 || first.targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid sequence dimensions";
    }
    return false;
  }
  if(first.gapOpen < 0 || first.gapExtend < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid gap penalties";
    }
    return false;
  }
  const int batchSize = static_cast<int>(requests.size());
  const int M = first.queryLength;
  const int N = first.targetLength;
  const size_t queryBytes = static_cast<size_t>(M + 1) * sizeof(char);
  const size_t targetBytesPerRequest = static_cast<size_t>(N + 1) * sizeof(char);
  for(size_t i = 1; i < requests.size(); ++i)
  {
    const SimScanCudaInitialBatchRequest &request = requests[i];
    if(request.A == NULL || request.B == NULL || request.scoreMatrix == NULL)
    {
      if(errorOut != NULL)
      {
        *errorOut = "missing input sequences";
      }
      return false;
    }
    if(request.queryLength != M ||
       request.targetLength != N ||
       request.gapOpen != first.gapOpen ||
       request.gapExtend != first.gapExtend ||
       memcmp(request.A, first.A, queryBytes) != 0 ||
       memcmp(request.scoreMatrix, first.scoreMatrix, sizeof(int) * 128 * 128) != 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "initial true batch requires identical query, target length, gap penalties and score matrix";
      }
      return false;
    }
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_capacity_locked(*context,M,N,errorOut))
  {
    return false;
  }

  const int leadingDim = context->leadingDim;
  const int matrixStride = (M + 1) * leadingDim;
  const int diagCapacity = max(M,N) + 2;
  const int rowCountStride = M + 1;
  const int rowOffsetStride = M + 2;
  const size_t packedBChars = static_cast<size_t>(batchSize) * static_cast<size_t>(N + 1);
  const size_t batchMatrixCells = static_cast<size_t>(batchSize) * static_cast<size_t>(matrixStride);
  const size_t batchDiagCells = static_cast<size_t>(batchSize) * static_cast<size_t>(diagCapacity);
  const size_t batchRowCounts = static_cast<size_t>(batchSize) * static_cast<size_t>(rowCountStride);
  const size_t batchRowOffsets = static_cast<size_t>(batchSize) * static_cast<size_t>(rowOffsetStride);

  if(!ensure_sim_scan_cuda_buffer(&context->batchBDevice,
                                  &context->batchBCapacityBytes,
                                  packedBChars,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchHScoreDevice,
                                  &context->batchHScoreCapacityCells,
                                  batchMatrixCells,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchHCoordDevice,
                                  &context->batchHCoordCapacityCells,
                                  batchMatrixCells,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRowCountsDevice,
                                  &context->batchRowCountsCapacity,
                                  batchRowCounts,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRowOffsetsDevice,
                                  &context->batchRowOffsetsCapacity,
                                  batchRowOffsets,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunOffsetsDevice,
                                  &context->batchRunOffsetsCapacity,
                                  batchRowOffsets,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventTotalsDevice,
                                  &context->batchEventTotalsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunTotalsDevice,
                                  &context->batchRunTotalsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventScoreFloorsDevice,
                                  &context->batchEventScoreFloorsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                  &context->batchEventBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunBasesDevice,
                                  &context->batchRunBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_true_batch_diag_capacity_locked(*context,batchDiagCells,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->ADevice,
                                  first.A,
                                  queryBytes,
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  vector<char> packedB(packedBChars);
  vector<int> eventScoreFloors(static_cast<size_t>(batchSize));
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    memcpy(packedB.data() + static_cast<size_t>(batchIndex) * static_cast<size_t>(N + 1),
           requests[static_cast<size_t>(batchIndex)].B,
           targetBytesPerRequest);
    eventScoreFloors[static_cast<size_t>(batchIndex)] = requests[static_cast<size_t>(batchIndex)].eventScoreFloor;
  }
  status = cudaMemcpy(context->batchBDevice,
                      packedB.data(),
                      packedBChars * sizeof(char),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->batchEventScoreFloorsDevice,
                      eventScoreFloors.data(),
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpyToSymbol(sim_score_matrix, first.scoreMatrix, sizeof(int) * 128 * 128);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int QR = first.gapOpen + first.gapExtend;
  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int *ppH = context->batchDiagH0;
  uint64_t *ppHc = context->batchDiagHc0;
  int *prevH = context->batchDiagH1;
  uint64_t *prevHc = context->batchDiagHc1;
  int *curH = context->batchDiagH2;
  uint64_t *curHc = context->batchDiagHc2;
  int *prevD = context->batchDiagD1;
  uint64_t *prevDc = context->batchDiagDc1;
  int *curD = context->batchDiagD2;
  uint64_t *curDc = context->batchDiagDc2;
  int *prevF = context->batchDiagF1;
  uint64_t *prevFc = context->batchDiagFc1;
  int *curF = context->batchDiagF2;
  uint64_t *curFc = context->batchDiagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;
  const int threadsPerBlock = 256;
  for(int diag = 2; diag <= M + N; ++diag)
  {
    const int curStartIHost = max(1, diag - N);
    const int curEndIHost = min(M, diag - 1);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_true_batch_kernel<<<dim3(static_cast<unsigned int>(blocks), static_cast<unsigned int>(batchSize)),
                                      threadsPerBlock>>>(
      context->ADevice,
      context->batchBDevice,
      batchSize,
      N + 1,
      M,
      N,
      leadingDim,
      matrixStride,
      diag,
      curStartIHost,
      curLenHost,
      prevStartI,
      prevLen,
      ppStartI,
      ppLen,
      diagCapacity,
      first.gapOpen,
      first.gapExtend,
      QR,
      ppH,
      ppHc,
      prevH,
      prevHc,
      prevD,
      prevDc,
      prevF,
      prevFc,
      curH,
      curHc,
      curD,
      curDc,
      curF,
      curFc,
      context->batchHScoreDevice,
      context->batchHCoordDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);
    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  const int countThreads = 256;
  const size_t sharedCountBytes = static_cast<size_t>(countThreads) * sizeof(int);
  sim_scan_count_row_events_true_batch_kernel<<<dim3(static_cast<unsigned int>(M), static_cast<unsigned int>(batchSize)),
                                                countThreads,
                                                sharedCountBytes>>>(
    context->batchHScoreDevice,
    leadingDim,
    matrixStride,
    M,
    N,
    context->batchEventScoreFloorsDevice,
    rowCountStride,
    context->batchRowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_true_batch_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    context->batchRowCountsDevice,
    rowCountStride,
    rowCountStride,
    rowOffsetStride,
    context->batchRowOffsetsDevice,
    context->batchEventTotalsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const std::chrono::steady_clock::time_point d2hStart = std::chrono::steady_clock::now();
  double initialCountCopySeconds = 0.0;
  double initialBaseUploadSeconds = 0.0;
  double initialSyncWaitSeconds = 0.0;
  const size_t maxEventsPerTask = static_cast<size_t>(M) * static_cast<size_t>(N);
  vector<int> totalEventsPerTask(static_cast<size_t>(batchSize),0);
  vector<int> totalRunsPerTask(static_cast<size_t>(batchSize),0);
  int totalEvents = 0;
  try
  {
    thrust::exclusive_scan(thrust::device,
                           thrust::device_pointer_cast(context->batchEventTotalsDevice),
                           thrust::device_pointer_cast(context->batchEventTotalsDevice + batchSize),
                           thrust::device_pointer_cast(context->batchEventBasesDevice));
    const std::chrono::steady_clock::time_point countCopyStart = std::chrono::steady_clock::now();
    totalEvents = thrust::reduce(thrust::device,
                                 thrust::device_pointer_cast(context->batchEventTotalsDevice),
                                 thrust::device_pointer_cast(context->batchEventTotalsDevice + batchSize),
                                 0,
                                 thrust::plus<int>());
    initialCountCopySeconds +=
      static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - countCopyStart).count()) / 1.0e9;
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  if(totalEvents < 0 || static_cast<size_t>(totalEvents) > static_cast<size_t>(batchSize) * maxEventsPerTask)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batch event count overflow";
    }
    return false;
  }

  sim_scan_count_initial_run_summaries_direct_true_batch_kernel<<<dim3(static_cast<unsigned int>(M),
                                                                        static_cast<unsigned int>(batchSize)),
                                                                  countThreads,
                                                                  sharedCountBytes>>>(
    context->batchHScoreDevice,
    context->batchHCoordDevice,
    leadingDim,
    matrixStride,
    M,
    N,
    context->batchEventScoreFloorsDevice,
    rowCountStride,
    context->batchRowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_true_batch_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    context->batchRowCountsDevice,
    rowCountStride,
    rowCountStride,
    rowOffsetStride,
    context->batchRunOffsetsDevice,
    context->batchRunTotalsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int maxRunsPerBatch = 0;
  int totalRunSummaries = 0;
  try
  {
    thrust::exclusive_scan(thrust::device,
                           thrust::device_pointer_cast(context->batchRunTotalsDevice),
                           thrust::device_pointer_cast(context->batchRunTotalsDevice + batchSize),
                           thrust::device_pointer_cast(context->batchRunBasesDevice));
    const std::chrono::steady_clock::time_point countCopyStart = std::chrono::steady_clock::now();
    totalRunSummaries = thrust::reduce(thrust::device,
                                       thrust::device_pointer_cast(context->batchRunTotalsDevice),
                                       thrust::device_pointer_cast(context->batchRunTotalsDevice + batchSize),
                                       0,
                                       thrust::plus<int>());
    maxRunsPerBatch = thrust::reduce(thrust::device,
                                     thrust::device_pointer_cast(context->batchRunTotalsDevice),
                                     thrust::device_pointer_cast(context->batchRunTotalsDevice + batchSize),
                                     0,
                                     thrust::maximum<int>());
    initialCountCopySeconds +=
      static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - countCopyStart).count()) / 1.0e9;
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }
  if(totalRunSummaries < 0 || totalRunSummaries > totalEvents)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batch run summary count exceeds event count";
    }
    return false;
  }

  if(totalRunSummaries > 0 &&
     !ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                  &context->initialRunSummariesCapacity,
                                  static_cast<size_t>(totalRunSummaries),
                                  errorOut))
  {
    return false;
  }

  if(totalRunSummaries > 0)
  {
    sim_scan_compact_initial_run_summaries_direct_true_batch_kernel<<<dim3(static_cast<unsigned int>(M),
                                                                            static_cast<unsigned int>(batchSize)),
                                                                      countThreads,
                                                                      sharedCountBytes>>>(
      context->batchHScoreDevice,
      context->batchHCoordDevice,
      leadingDim,
      matrixStride,
      M,
      N,
      context->batchEventScoreFloorsDevice,
      context->batchRunOffsetsDevice,
      rowOffsetStride,
      context->batchRunBasesDevice,
      context->initialRunSummariesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int totalAllCandidateStates = 0;
  vector<int> allCandidateCountsPerTask;
  vector<int> proposalCandidateBasesPerTask;
  SimScanCudaInitialReduceReplayStats replayStats;
  double initialSegmentedReduceSeconds = 0.0;
  double initialSegmentedCompactSeconds = 0.0;
  double initialTopKSeconds = 0.0;
  uint64_t initialSegmentedTileStateCount = 0;
  uint64_t initialSegmentedGroupedStateCount = 0;
  bool usedInitialSegmentedReducePath = false;
  double proposalDirectTopKGpuSeconds = 0.0;
  double proposalV3GpuSeconds = 0.0;
  double proposalSelectD2HSeconds = 0.0;
  if(anyCandidateExtraction)
  {
    if(anyReduceCandidates)
    {
      const bool useOrderedSegmentedV3TopKSelector =
        sim_scan_cuda_initial_reduce_backend_runtime() ==
        SIM_SCAN_CUDA_INITIAL_REDUCE_BACKEND_ORDERED_SEGMENTED_V3;
      if(!ensure_sim_scan_cuda_buffer(&context->batchCandidateStatesDevice,
                                      &context->batchCandidateStatesCapacity,
                                      static_cast<size_t>(batchSize) * static_cast<size_t>(sim_scan_cuda_max_candidates),
                                      errorOut) ||
         !ensure_sim_scan_cuda_buffer(&context->batchCandidateCountsDevice,
                                      &context->batchCandidateCountsCapacity,
                                      static_cast<size_t>(batchSize),
                                      errorOut) ||
         !ensure_sim_scan_cuda_buffer(&context->batchRunningMinsDevice,
                                      &context->batchRunningMinsCapacity,
                                      static_cast<size_t>(batchSize),
                                      errorOut))
      {
        return false;
      }
      status = cudaMemset(context->batchCandidateCountsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      status = cudaMemset(context->batchRunningMinsDevice,0,static_cast<size_t>(batchSize) * sizeof(int));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      if(sim_scan_cuda_initial_segmented_reduce_runtime())
      {
        int reducedCandidateCount = 0;
        vector<int> prunedCandidateBasesPerTask;
        if(useOrderedSegmentedV3TopKSelector)
        {
          vector<int> reducedCandidateBasesPerTask;
          const chrono::steady_clock::time_point orderedSegmentedReduceStart =
            chrono::steady_clock::now();
          if(!sim_scan_reduce_candidate_states_from_summaries_true_batch(context,
                                                                         context->initialRunSummariesDevice,
                                                                         static_cast<int>(totalRunSummaries),
                                                                         context->batchRunBasesDevice,
                                                                         context->batchRunTotalsDevice,
                                                                         batchSize,
                                                                         maxRunsPerBatch,
                                                                         NULL,
                                                                         NULL,
                                                                         NULL,
                                                                         &totalAllCandidateStates,
                                                                         &allCandidateCountsPerTask,
                                                                         &reducedCandidateCount,
                                                                         &reducedCandidateBasesPerTask,
                                                                         batchResult,
                                                                         errorOut))
          {
            return false;
          }
          initialSegmentedReduceSeconds =
            static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                                  chrono::steady_clock::now() - orderedSegmentedReduceStart).count()) / 1.0e9;
          if(!sim_scan_select_top_candidate_reduce_states_true_batch_locked(
               context,
               context->reducedStatesDevice,
               reducedCandidateBasesPerTask,
               allCandidateCountsPerTask,
               sim_scan_cuda_max_candidates,
               &initialTopKSeconds,
               errorOut))
          {
            return false;
          }
          usedInitialSegmentedReducePath = true;
          initialSegmentedTileStateCount = static_cast<uint64_t>(totalRunSummaries);
          initialSegmentedGroupedStateCount = static_cast<uint64_t>(max(reducedCandidateCount,0));
          if(!sim_scan_compact_batch_initial_safe_store_candidate_states_from_reduced_states(
               context,
               reducedCandidateCount,
               batchSize,
               context->batchCandidateStatesDevice,
               context->batchCandidateCountsDevice,
               context->batchRunningMinsDevice,
               &totalAllCandidateStates,
               &allCandidateCountsPerTask,
               &prunedCandidateBasesPerTask,
               &initialSegmentedCompactSeconds,
               errorOut))
          {
            return false;
          }
        }
        else
        {
          const int reduceChunkSize = sim_scan_cuda_initial_reduce_chunk_size_runtime();
          if(!ensure_sim_scan_cuda_buffer(&context->initialReduceReplayStatsDevice,
                                          &context->initialReduceReplayStatsCapacity,
                                          static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count),
                                          errorOut))
          {
            return false;
          }
          status = cudaMemset(context->initialReduceReplayStatsDevice,
                              0,
                              static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long));
          if(status != cudaSuccess)
          {
            if(errorOut != NULL)
            {
              *errorOut = cuda_error_string(status);
            }
            return false;
          }
          if(!sim_scan_cuda_begin_aux_timing(context,errorOut))
          {
            return false;
          }
          sim_scan_reduce_initial_candidate_states_true_batch_kernel<<<static_cast<unsigned int>(batchSize),
                                                                       sim_scan_initial_reduce_threads>>>(context->initialRunSummariesDevice,
                                                                                                           context->batchRunBasesDevice,
                                                                                                           context->batchRunTotalsDevice,
                                                                                                           batchSize,
                                                                                                           context->batchCandidateStatesDevice,
                                                                                                           context->batchCandidateCountsDevice,
                                                                                                           context->batchRunningMinsDevice,
                                                                                                           NULL,
                                                                                                           0,
                                                                                                           reduceChunkSize,
                                                                                                           context->initialReduceReplayStatsDevice);
          status = cudaGetLastError();
          if(status != cudaSuccess)
          {
            if(errorOut != NULL)
            {
              *errorOut = cuda_error_string(status);
            }
            return false;
          }
          if(!sim_scan_cuda_end_aux_timing(context,&initialTopKSeconds,errorOut))
          {
            return false;
          }
          unsigned long long replayStatsHost[sim_scan_initial_reduce_chunk_stats_count] = {0, 0, 0};
          status = cudaMemcpy(replayStatsHost,
                              context->initialReduceReplayStatsDevice,
                              static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long),
                              cudaMemcpyDeviceToHost);
          if(status != cudaSuccess)
          {
            if(errorOut != NULL)
            {
              *errorOut = cuda_error_string(status);
            }
            return false;
          }
          replayStats.chunkCount = static_cast<uint64_t>(replayStatsHost[0]);
          replayStats.chunkReplayedCount = static_cast<uint64_t>(replayStatsHost[1]);
          replayStats.summaryReplayCount = static_cast<uint64_t>(replayStatsHost[2]);
          replayStats.chunkSkippedCount =
            replayStats.chunkCount >= replayStats.chunkReplayedCount ?
            (replayStats.chunkCount - replayStats.chunkReplayedCount) : 0;
          if(!sim_scan_reduce_candidate_states_from_summaries_true_batch_segmented(context,
                                                                                   context->initialRunSummariesDevice,
                                                                                   static_cast<int>(totalRunSummaries),
                                                                                   context->batchRunBasesDevice,
                                                                                   context->batchRunTotalsDevice,
                                                                                   batchSize,
                                                                                   maxRunsPerBatch,
                                                                                   &reducedCandidateCount,
                                                                                   &initialSegmentedReduceSeconds,
                                                                                   errorOut))
          {
            return false;
          }
          usedInitialSegmentedReducePath = true;
          initialSegmentedTileStateCount = static_cast<uint64_t>(totalRunSummaries);
          initialSegmentedGroupedStateCount = static_cast<uint64_t>(max(reducedCandidateCount,0));
          if(!sim_scan_compact_batch_initial_safe_store_candidate_states_from_reduced_states(
               context,
               reducedCandidateCount,
               batchSize,
               context->batchCandidateStatesDevice,
               context->batchCandidateCountsDevice,
               context->batchRunningMinsDevice,
               &totalAllCandidateStates,
               &allCandidateCountsPerTask,
               &prunedCandidateBasesPerTask,
               &initialSegmentedCompactSeconds,
               errorOut))
          {
            return false;
          }
        }
      }
      else
      {
        const int reduceChunkSize = sim_scan_cuda_initial_reduce_chunk_size_runtime();
        if(!ensure_sim_scan_cuda_buffer(&context->initialReduceReplayStatsDevice,
                                        &context->initialReduceReplayStatsCapacity,
                                        static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count),
                                        errorOut))
        {
          return false;
        }
        status = cudaMemset(context->initialReduceReplayStatsDevice,
                            0,
                            static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long));
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        sim_scan_reduce_initial_candidate_states_true_batch_kernel<<<static_cast<unsigned int>(batchSize),
                                                                     sim_scan_initial_reduce_threads>>>(context->initialRunSummariesDevice,
                                                                                                         context->batchRunBasesDevice,
                                                                                                         context->batchRunTotalsDevice,
                                                                                                         batchSize,
                                                                                                         context->batchCandidateStatesDevice,
                                                                                                         context->batchCandidateCountsDevice,
                                                                                                         context->batchRunningMinsDevice,
                                                                                                         NULL,
                                                                                                         0,
                                                                                                         reduceChunkSize,
                                                                                                         context->initialReduceReplayStatsDevice);
        status = cudaGetLastError();
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        unsigned long long replayStatsHost[sim_scan_initial_reduce_chunk_stats_count] = {0, 0, 0};
        status = cudaMemcpy(replayStatsHost,
                            context->initialReduceReplayStatsDevice,
                            static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
        replayStats.chunkCount = static_cast<uint64_t>(replayStatsHost[0]);
        replayStats.chunkReplayedCount = static_cast<uint64_t>(replayStatsHost[1]);
        replayStats.summaryReplayCount = static_cast<uint64_t>(replayStatsHost[2]);
        replayStats.chunkSkippedCount =
          replayStats.chunkCount >= replayStats.chunkReplayedCount ?
          (replayStats.chunkCount - replayStats.chunkReplayedCount) : 0;
        if(!sim_scan_prepare_all_candidate_states_from_summaries_true_batch(context,
                                                                            context->initialRunSummariesDevice,
                                                                            static_cast<int>(totalRunSummaries),
                                                                            context->batchRunBasesDevice,
                                                                            context->batchRunTotalsDevice,
                                                                            batchSize,
                                                                            maxRunsPerBatch,
                                                                            context->batchCandidateStatesDevice,
                                                                            context->batchCandidateCountsDevice,
                                                                            context->batchRunningMinsDevice,
                                                                            &totalAllCandidateStates,
                                                                            &allCandidateCountsPerTask,
                                                                            batchResult,
                                                                            errorOut))
        {
          return false;
        }
      }
    }
    else if(useProposalV2Path || useProposalV3Path)
    {
      if(!sim_scan_reduce_candidate_states_from_summaries_true_batch(context,
                                                                     context->initialRunSummariesDevice,
                                                                     static_cast<int>(totalRunSummaries),
                                                                     context->batchRunBasesDevice,
                                                                     context->batchRunTotalsDevice,
                                                                     batchSize,
                                                                     maxRunsPerBatch,
                                                                     NULL,
                                                                     NULL,
                                                                     NULL,
                                                                     &totalAllCandidateStates,
                                                                     &allCandidateCountsPerTask,
                                                                     NULL,
                                                                     useProposalV3Path ? &proposalCandidateBasesPerTask : NULL,
                                                                     batchResult,
                                                                     errorOut))
      {
        return false;
      }
    }
    else
    {
      if(!sim_scan_prepare_all_candidate_states_from_summaries_true_batch(context,
                                                                          context->initialRunSummariesDevice,
                                                                          static_cast<int>(totalRunSummaries),
                                                                          context->batchRunBasesDevice,
                                                                          context->batchRunTotalsDevice,
                                                                          batchSize,
                                                                          maxRunsPerBatch,
                                                                          NULL,
                                                                          NULL,
                                                                          NULL,
                                                                          &totalAllCandidateStates,
                                                                          &allCandidateCountsPerTask,
                                                                          batchResult,
                                                                          errorOut))
      {
        return false;
      }
    }
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    const std::chrono::steady_clock::time_point syncWaitStart = std::chrono::steady_clock::now();
    status = cudaEventSynchronize(context->stopEvent);
    initialSyncWaitSeconds =
      static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - syncWaitStart).count()) / 1.0e9;
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  vector<int> proposalSelectedCountsPerTask;
  vector<SimScanCudaCandidateState> packedSelectedProposalStates;
  if(useProposalV3Path)
  {
    proposalSelectedCountsPerTask.assign(static_cast<size_t>(batchSize),0);
    if(totalAllCandidateStates > 0)
    {
      if(!sim_scan_select_top_disjoint_candidate_reduce_states_true_batch_locked(context,
                                                                                 context->reducedStatesDevice,
                                                                                 proposalCandidateBasesPerTask,
                                                                                 allCandidateCountsPerTask,
                                                                                 sim_scan_cuda_max_candidates,
                                                                                 &proposalSelectedCountsPerTask,
                                                                                 &packedSelectedProposalStates,
                                                                                 &proposalV3GpuSeconds,
                                                                                 &proposalSelectD2HSeconds,
                                                                                 errorOut))
      {
        return false;
      }
    }
  }

  vector<SimScanCudaInitialRunSummary> packedSummaries;
  if(anySummaryRequests && totalRunSummaries > 0)
  {
    packedSummaries.resize(totalRunSummaries);
    status = cudaMemcpy(packedSummaries.data(),
                        context->initialRunSummariesDevice,
                        totalRunSummaries * sizeof(SimScanCudaInitialRunSummary),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      packedSummaries.clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  const std::chrono::steady_clock::time_point countCopyStart = std::chrono::steady_clock::now();
  status = cudaMemcpy(totalEventsPerTask.data(),
                      context->batchEventTotalsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(totalRunsPerTask.data(),
                      context->batchRunTotalsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  initialCountCopySeconds +=
    static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::steady_clock::now() - countCopyStart).count()) / 1.0e9;
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int taskEvents = totalEventsPerTask[static_cast<size_t>(batchIndex)];
    const int taskRuns = totalRunsPerTask[static_cast<size_t>(batchIndex)];
    if(taskEvents < 0 || static_cast<size_t>(taskEvents) > maxEventsPerTask)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batch event count overflow";
      }
      return false;
    }
    if(taskRuns < 0 || taskRuns > taskEvents)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batch run summary count overflow";
      }
      return false;
    }
  }

  vector<int> candidateCountsPerTask;
  vector<int> runningMinsPerTask;
  vector<SimScanCudaCandidateState> packedTopCandidates;
  vector<SimScanCudaCandidateState> packedAllCandidateStates;
  if(anyCandidateExtraction)
  {
    if(anyReduceCandidates)
    {
      candidateCountsPerTask.resize(static_cast<size_t>(batchSize),0);
      runningMinsPerTask.resize(static_cast<size_t>(batchSize),0);
      status = cudaMemcpy(candidateCountsPerTask.data(),
                          context->batchCandidateCountsDevice,
                          static_cast<size_t>(batchSize) * sizeof(int),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      status = cudaMemcpy(runningMinsPerTask.data(),
                          context->batchRunningMinsDevice,
                          static_cast<size_t>(batchSize) * sizeof(int),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      packedTopCandidates.resize(static_cast<size_t>(batchSize) * static_cast<size_t>(sim_scan_cuda_max_candidates));
      status = cudaMemcpy(packedTopCandidates.data(),
                          context->batchCandidateStatesDevice,
                          packedTopCandidates.size() * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        packedTopCandidates.clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
    if(totalAllCandidateStates > 0 && anyHostAllCandidateStates)
    {
      packedAllCandidateStates.resize(static_cast<size_t>(totalAllCandidateStates));
      status = cudaMemcpy(packedAllCandidateStates.data(),
                          context->outputCandidateStatesDevice,
                          static_cast<size_t>(totalAllCandidateStates) * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        packedAllCandidateStates.clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
  }

  vector<SimScanCudaInitialBatchResult> results(static_cast<size_t>(batchSize));
  double proposalSelectGpuSeconds = 0.0;
  size_t summaryCursor = 0;
  size_t allCandidateCursor = 0;
  size_t selectedProposalCursor = 0;
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const SimScanCudaInitialBatchRequest &request = requests[static_cast<size_t>(batchIndex)];
    SimScanCudaInitialBatchResult &result = results[static_cast<size_t>(batchIndex)];
    result.runningMin = 0;
    result.eventCount = static_cast<uint64_t>(totalEventsPerTask[static_cast<size_t>(batchIndex)]);
    result.runSummaryCount = static_cast<uint64_t>(totalRunsPerTask[static_cast<size_t>(batchIndex)]);
    const size_t summaryCount = static_cast<size_t>(totalRunsPerTask[static_cast<size_t>(batchIndex)]);
    const int allCandidateCountValue =
      anyCandidateExtraction ? allCandidateCountsPerTask[static_cast<size_t>(batchIndex)] : 0;
    if(allCandidateCountValue < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA batched all-candidate count underflow";
      }
      return false;
    }
    const size_t allCandidateCount = static_cast<size_t>(allCandidateCountValue);
    result.allCandidateStateCount = static_cast<uint64_t>(allCandidateCount);
    if(request.reduceCandidates || request.proposalCandidates)
    {
      if(request.persistAllCandidateStatesOnDevice)
      {
        const SimScanCudaCandidateState *allCandidateStatesDevice =
          allCandidateCount > 0 ? context->outputCandidateStatesDevice + allCandidateCursor : NULL;
        if(!sim_scan_cuda_clone_persistent_safe_store_from_device_locked(allCandidateStatesDevice,
                                                                         allCandidateCount,
                                                                         device,
                                                                         slot,
                                                                         &result.persistentSafeStoreHandle,
                                                                         errorOut))
        {
          for(size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
          {
            sim_scan_cuda_release_persistent_safe_candidate_state_store(&results[resultIndex].persistentSafeStoreHandle);
          }
          return false;
        }
      }
      else if(request.reduceCandidates)
      {
        if(allCandidateCount > 0)
        {
          result.allCandidateStates.insert(result.allCandidateStates.end(),
                                           packedAllCandidateStates.begin() + static_cast<long>(allCandidateCursor),
                                           packedAllCandidateStates.begin() + static_cast<long>(allCandidateCursor + allCandidateCount));
        }
      }
      if(request.reduceCandidates)
      {
        int candidateCount = candidateCountsPerTask[static_cast<size_t>(batchIndex)];
        if(candidateCount < 0 || candidateCount > sim_scan_cuda_max_candidates)
        {
          if(errorOut != NULL)
          {
            *errorOut = "SIM CUDA batched candidate count overflow";
          }
          return false;
        }
        result.runningMin = runningMinsPerTask[static_cast<size_t>(batchIndex)];
        if(candidateCount > 0)
        {
          const size_t candidateBase = static_cast<size_t>(batchIndex) * static_cast<size_t>(sim_scan_cuda_max_candidates);
          result.candidateStates.insert(result.candidateStates.end(),
                                        packedTopCandidates.begin() + static_cast<long>(candidateBase),
                                        packedTopCandidates.begin() + static_cast<long>(candidateBase + static_cast<size_t>(candidateCount)));
        }
      }
      else if(useProposalV3Path)
      {
        const int selectedCount = proposalSelectedCountsPerTask[static_cast<size_t>(batchIndex)];
        if(selectedCount < 0 || selectedCount > sim_scan_cuda_max_candidates)
        {
          if(errorOut != NULL)
          {
            *errorOut = "SIM CUDA batched V3 selected count overflow";
          }
          return false;
        }
        if(selectedCount > 0)
        {
          result.candidateStates.insert(result.candidateStates.end(),
                                        packedSelectedProposalStates.begin() + static_cast<long>(selectedProposalCursor),
                                        packedSelectedProposalStates.begin() +
                                          static_cast<long>(selectedProposalCursor + static_cast<size_t>(selectedCount)));
          selectedProposalCursor += static_cast<size_t>(selectedCount);
        }
      }
      else if(allCandidateCount > 0)
      {
        vector<SimScanCudaCandidateState> proposalStates;
        double requestProposalGpuSeconds = 0.0;
        const bool selectedOk =
          useProposalV2Path ?
          sim_scan_select_top_disjoint_candidate_reduce_states_from_device_locked(context,
                                                                                  context->reducedStatesDevice + allCandidateCursor,
                                                                                  static_cast<int>(allCandidateCount),
                                                                                  sim_scan_cuda_max_candidates,
                                                                                  &proposalStates,
                                                                                  &requestProposalGpuSeconds,
                                                                                  errorOut) :
          sim_scan_select_top_disjoint_candidate_states_from_device_locked(context,
                                                                           context->outputCandidateStatesDevice + allCandidateCursor,
                                                                           static_cast<int>(allCandidateCount),
                                                                           sim_scan_cuda_max_candidates,
                                                                           &proposalStates,
                                                                           &requestProposalGpuSeconds,
                                                                           errorOut);
        if(!selectedOk)
        {
          for(size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
          {
            sim_scan_cuda_release_persistent_safe_candidate_state_store(&results[resultIndex].persistentSafeStoreHandle);
          }
          return false;
        }
        proposalSelectGpuSeconds += requestProposalGpuSeconds;
        if(useProposalV2Path)
        {
          proposalDirectTopKGpuSeconds += requestProposalGpuSeconds;
        }
        result.candidateStates.swap(proposalStates);
      }
    }
    else if(summaryCount > 0)
    {
      result.initialRunSummaries.insert(result.initialRunSummaries.end(),
                                        packedSummaries.begin() + static_cast<long>(summaryCursor),
                                        packedSummaries.begin() + static_cast<long>(summaryCursor + summaryCount));
    }
    summaryCursor += summaryCount;
    allCandidateCursor += allCandidateCount;
  }
  if(summaryCursor != static_cast<size_t>(totalRunSummaries))
  {
    for(size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&results[resultIndex].persistentSafeStoreHandle);
    }
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched summary cursor mismatch";
    }
    return false;
  }
  if(allCandidateCursor != static_cast<size_t>(totalAllCandidateStates))
  {
    for(size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&results[resultIndex].persistentSafeStoreHandle);
    }
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched all-candidate cursor mismatch";
    }
    return false;
  }
  if(selectedProposalCursor != packedSelectedProposalStates.size())
  {
    for(size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
    {
      sim_scan_cuda_release_persistent_safe_candidate_state_store(&results[resultIndex].persistentSafeStoreHandle);
    }
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA batched V3 selected cursor mismatch";
    }
    return false;
  }
  *outResults = results;
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->d2hSeconds =
      static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - d2hStart).count()) / 1.0e9;
    batchResult->proposalSelectGpuSeconds = useProposalV3Path ? proposalV3GpuSeconds : proposalSelectGpuSeconds;
    batchResult->initialProposalV3GpuSeconds = proposalV3GpuSeconds;
    batchResult->initialCountCopySeconds = initialCountCopySeconds;
    batchResult->initialBaseUploadSeconds = initialBaseUploadSeconds;
    batchResult->initialProposalSelectD2HSeconds = proposalSelectD2HSeconds;
    batchResult->initialSyncWaitSeconds = initialSyncWaitSeconds;
    batchResult->initialWaitSeconds = initialSyncWaitSeconds;
    batchResult->initialScanTailSeconds = batchResult->d2hSeconds;
    batchResult->usedInitialDirectSummaryPath = true;
    batchResult->usedInitialSegmentedReducePath = usedInitialSegmentedReducePath;
    batchResult->usedInitialDeviceResidencyPath = deviceResidencyRequestCount > 0;
    batchResult->usedInitialProposalV2Path = useProposalV2Path;
    batchResult->usedInitialProposalV2DirectTopKPath = useProposalV2Path;
    batchResult->usedInitialProposalV3Path = useProposalV3Path;
    batchResult->initialSegmentedFallback = false;
    batchResult->initialDeviceResidencyRequestCount =
      static_cast<uint64_t>(max(deviceResidencyRequestCount,0));
    batchResult->initialProposalV2RequestCount =
      useProposalV2Path ? static_cast<uint64_t>(proposalRequestCount) : 0;
    batchResult->initialProposalV3RequestCount =
      useProposalV3Path ? static_cast<uint64_t>(proposalRequestCount) : 0;
    batchResult->initialProposalV3SelectedStateCount =
      useProposalV3Path ? static_cast<uint64_t>(packedSelectedProposalStates.size()) : 0;
    batchResult->initialProposalLogicalCandidateCount =
      useProposalV2Path ? static_cast<uint64_t>(max(totalAllCandidateStates,0)) : 0;
    batchResult->initialProposalMaterializedCandidateCount = 0;
    batchResult->initialProposalDirectTopKGpuSeconds = proposalDirectTopKGpuSeconds;
    batchResult->initialSegmentedReduceSeconds = initialSegmentedReduceSeconds;
    batchResult->initialSegmentedCompactSeconds = initialSegmentedCompactSeconds;
    batchResult->initialOrderedReplaySeconds = initialTopKSeconds;
    batchResult->initialTopKSeconds = initialTopKSeconds;
    batchResult->initialSegmentedTileStateCount = initialSegmentedTileStateCount;
    batchResult->initialSegmentedGroupedStateCount = initialSegmentedGroupedStateCount;
    batchResult->taskCount = static_cast<uint64_t>(batchSize);
    batchResult->launchCount = 1;
    batchResult->initialReduceReplayStats = replayStats;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_reduce_initial_run_summaries_for_test(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                         vector<SimScanCudaCandidateState> *outCandidateStates,
                                                         int *outRunningMin,
                                                         SimScanCudaInitialReduceReplayStats *outReplayStats,
                                                         string *errorOut,
                                                         SimScanCudaOrderedMaintenanceReplayDigestStats *outDigestStats,
                                                         vector<SimScanCudaCandidateState> *outSafeStoreStates)
{
  if(outCandidateStates == NULL || outRunningMin == NULL || outReplayStats == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing reducer test outputs";
    }
    return false;
  }
  outCandidateStates->clear();
  if(outSafeStoreStates != NULL)
  {
    outSafeStoreStates->clear();
  }
  *outRunningMin = 0;
  *outReplayStats = SimScanCudaInitialReduceReplayStats();
  if(outDigestStats != NULL)
  {
    *outDigestStats = SimScanCudaOrderedMaintenanceReplayDigestStats();
  }

  if(summaries.size() > static_cast<size_t>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA reducer test summary count overflow";
    }
    return false;
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }

  const int summaryCount = static_cast<int>(summaries.size());
  if(summaryCount > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                    &context->initialRunSummariesCapacity,
                                    static_cast<size_t>(summaryCount),
                                    errorOut))
    {
      return false;
    }
    cudaError_t status = cudaMemcpy(context->initialRunSummariesDevice,
                                    summaries.data(),
                                    static_cast<size_t>(summaryCount) * sizeof(SimScanCudaInitialRunSummary),
                                    cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  const bool collectDigestStats = outDigestStats != NULL;
  const bool collectSafeStoreStates = outSafeStoreStates != NULL;
  if(collectSafeStoreStates)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                    &context->outputCandidateStatesCapacity,
                                    static_cast<size_t>(max(summaryCount,1)),
                                    errorOut))
    {
      return false;
    }
  }
  const size_t replayStatsDeviceCount =
    static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) +
    (collectDigestStats ?
     static_cast<size_t>(sim_scan_ordered_maintenance_digest_stats_count) :
     static_cast<size_t>(0));
  if(!ensure_sim_scan_cuda_buffer(&context->initialReduceReplayStatsDevice,
                                  &context->initialReduceReplayStatsCapacity,
                                  replayStatsDeviceCount,
                                  errorOut))
  {
    return false;
  }

  const int zero = 0;
  cudaError_t status = cudaMemcpy(context->candidateCountDevice,
                                  &zero,
                                  sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->runningMinDevice,
                      &zero,
                      sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemset(context->initialReduceReplayStatsDevice,
                      0,
                      replayStatsDeviceCount * sizeof(unsigned long long));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(collectSafeStoreStates)
  {
    status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  const int reduceChunkSize = sim_scan_cuda_initial_reduce_chunk_size_runtime();
  unsigned long long *orderedMaintenanceDigestStatsDevice =
    collectDigestStats ?
    (context->initialReduceReplayStatsDevice + sim_scan_initial_reduce_chunk_stats_count) :
    NULL;
  if(summaryCount > 0)
  {
    sim_scan_reduce_initial_candidate_states_kernel<<<1, sim_scan_initial_reduce_threads>>>(context->initialRunSummariesDevice,
                                                                                            summaryCount,
                                                                                            context->candidateStatesDevice,
                                                                                            context->candidateCountDevice,
                                                                                            context->runningMinDevice,
                                                                                            NULL,
                                                                                            reduceChunkSize,
                                                                                            context->initialReduceReplayStatsDevice,
                                                                                            orderedMaintenanceDigestStatsDevice,
                                                                                            collectSafeStoreStates ?
                                                                                              context->outputCandidateStatesDevice : NULL,
                                                                                            collectSafeStoreStates ?
                                                                                              context->filteredCandidateCountDevice : NULL);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int candidateCount = 0;
  status = cudaMemcpy(&candidateCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(outRunningMin,
                      context->runningMinDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  unsigned long long replayStatsHost[sim_scan_initial_reduce_chunk_stats_count] = {0, 0, 0};
  status = cudaMemcpy(replayStatsHost,
                      context->initialReduceReplayStatsDevice,
                      static_cast<size_t>(sim_scan_initial_reduce_chunk_stats_count) * sizeof(unsigned long long),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  outReplayStats->chunkCount = static_cast<uint64_t>(replayStatsHost[0]);
  outReplayStats->chunkReplayedCount = static_cast<uint64_t>(replayStatsHost[1]);
  outReplayStats->summaryReplayCount = static_cast<uint64_t>(replayStatsHost[2]);
  outReplayStats->chunkSkippedCount =
    outReplayStats->chunkCount >= outReplayStats->chunkReplayedCount ?
    (outReplayStats->chunkCount - outReplayStats->chunkReplayedCount) : 0;

  if(collectDigestStats && summaryCount > 0)
  {
    unsigned long long digestStatsHost[sim_scan_ordered_maintenance_digest_stats_count] = {
      1469598103934665603ULL,
      1469598103934665603ULL,
      1469598103934665603ULL,
      1469598103934665603ULL,
      1469598103934665603ULL,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0
    };
    status = cudaMemcpy(digestStatsHost,
                        orderedMaintenanceDigestStatsDevice,
                        static_cast<size_t>(sim_scan_ordered_maintenance_digest_stats_count) *
                          sizeof(unsigned long long),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    outDigestStats->replacementSequenceHash =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_replacement_sequence_hash_index]);
    outDigestStats->runningMinUpdateSequenceHash =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_running_min_sequence_hash_index]);
    outDigestStats->runningMinSlotUpdateSequenceHash =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_running_min_slot_sequence_hash_index]);
    outDigestStats->floorChangeSequenceHash =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_floor_change_sequence_hash_index]);
    outDigestStats->candidateIndexVisibilityHash =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_visibility_hash_index]);
    outDigestStats->candidateReplacementCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_replacement_count_index]);
    outDigestStats->runningMinUpdateCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_running_min_update_count_index]);
    outDigestStats->runningMinSlotUpdateCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_running_min_slot_update_count_index]);
    outDigestStats->floorChangeCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_floor_change_count_index]);
    outDigestStats->candidateIndexExistingHitCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_existing_hit_count_index]);
    outDigestStats->candidateIndexMissCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_miss_count_index]);
    outDigestStats->candidateIndexInsertCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_insert_count_index]);
    outDigestStats->candidateIndexEraseCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_erase_count_index]);
    outDigestStats->candidateIndexVisibilityCheckCount =
      static_cast<uint64_t>(
        digestStatsHost[sim_scan_ordered_maintenance_digest_candidate_index_visibility_check_count_index]);
  }

  if(candidateCount < 0)
  {
    candidateCount = 0;
  }
  if(candidateCount > sim_scan_cuda_max_candidates)
  {
    candidateCount = sim_scan_cuda_max_candidates;
  }
  if(candidateCount > 0)
  {
    outCandidateStates->resize(static_cast<size_t>(candidateCount));
    status = cudaMemcpy(outCandidateStates->data(),
                        context->candidateStatesDevice,
                        static_cast<size_t>(candidateCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      outCandidateStates->clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  if(collectSafeStoreStates)
  {
    int safeStoreStateCount = 0;
    status = cudaMemcpy(&safeStoreStateCount,
                        context->filteredCandidateCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(safeStoreStateCount < 0)
    {
      safeStoreStateCount = 0;
    }
    if(safeStoreStateCount > summaryCount)
    {
      safeStoreStateCount = summaryCount;
    }
    if(safeStoreStateCount > 0)
    {
      outSafeStoreStates->resize(static_cast<size_t>(safeStoreStateCount));
      status = cudaMemcpy(outSafeStoreStates->data(),
                          context->outputCandidateStatesDevice,
                          static_cast<size_t>(safeStoreStateCount) *
                            sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        outSafeStoreStates->clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
}

bool sim_scan_cuda_select_top_disjoint_candidate_states(const vector<SimScanCudaCandidateState> &candidateStates,
                                                        int maxProposalCount,
                                                        vector<SimScanCudaCandidateState> *outSelectedStates,
                                                        string *errorOut)
{
  if(outSelectedStates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing proposal helper outputs";
    }
    return false;
  }
  outSelectedStates->clear();

  if(maxProposalCount <= 0 || candidateStates.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(candidateStates.size() > static_cast<size_t>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA proposal candidate count overflow";
    }
    return false;
  }

  const int clampedProposalCount = min(maxProposalCount, sim_scan_cuda_max_candidates);
  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }

  const size_t stateCount = candidateStates.size();
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  stateCount,
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->outputCandidateStatesDevice,
                                  candidateStates.data(),
                                  stateCount * sizeof(SimScanCudaCandidateState),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  double unusedGpuSeconds = 0.0;
  return sim_scan_select_top_disjoint_candidate_states_from_device_locked(context,
                                                                          context->outputCandidateStatesDevice,
                                                                          static_cast<int>(stateCount),
                                                                          clampedProposalCount,
                                                                          outSelectedStates,
                                                                          &unusedGpuSeconds,
                                                                          errorOut);
}

static bool sim_scan_cuda_upload_region_common_inputs_locked(SimScanCudaContext *context,
                                                             const char *A,
                                                             const char *B,
                                                             int queryLength,
                                                             int targetLength,
                                                             const int scoreMatrix[128][128],
                                                             string *errorOut)
{
  if(context == NULL || A == NULL || B == NULL || scoreMatrix == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing common region inputs";
    }
    return false;
  }

  cudaError_t status = cudaMemcpy(context->ADevice,
                                  A,
                                  static_cast<size_t>(queryLength + 1) * sizeof(char),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->BDevice,
                      B,
                      static_cast<size_t>(targetLength + 1) * sizeof(char),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpyToSymbol(sim_score_matrix, scoreMatrix, sizeof(int) * 128 * 128);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_upload_region_filter_start_coords_locked(SimScanCudaContext *context,
                                                                   const uint64_t *filterStartCoords,
                                                                   int filterStartCoordCount,
                                                                   string *errorOut)
{
  if(filterStartCoordCount <= 0)
  {
    return true;
  }
  if(context == NULL || filterStartCoords == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing filter start coords";
    }
    return false;
  }
  if(!ensure_sim_scan_cuda_buffer(&context->filterStartCoordsDevice,
                                  &context->filterStartCoordsCapacity,
                                  static_cast<size_t>(filterStartCoordCount),
                                  errorOut))
  {
    return false;
  }
  const cudaError_t status = cudaMemcpy(context->filterStartCoordsDevice,
                                        filterStartCoords,
                                        static_cast<size_t>(filterStartCoordCount) * sizeof(uint64_t),
                                        cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_execute_region_request_locked(SimScanCudaContext *context,
                                                        int queryLength,
                                                        int targetLength,
                                                        int rowStart,
                                                        int rowEnd,
                                                        int colStart,
                                                        int colEnd,
                                                        int gapOpen,
                                                        int gapExtend,
                                                        int eventScoreFloor,
                                                        const uint64_t *blockedWords,
                                                        int blockedWordStart,
                                                        int blockedWordCount,
                                                        int blockedWordStride,
                                                        bool reduceCandidates,
                                                        bool reduceAllCandidateStates,
                                                        const uint64_t *filterStartCoords,
                                                        int filterStartCoordCount,
                                                        bool filterStartCoordsUploaded,
                                                        const SimScanCudaCandidateState *seedCandidates,
                                                        int seedCandidateCount,
                                                        int seedRunningMin,
                                                        vector<SimScanCudaCandidateState> *outCandidateStates,
                                                        int *outCandidateStateCount,
                                                        bool materializeCandidateStatesToHost,
                                                        int *outRunningMin,
                                                        int *outEventCount,
                                                        uint64_t *outRunSummaryCount,
                                                        vector<SimScanCudaRowEvent> *outEvents,
                                                        vector<int> *outRowOffsets,
                                                        SimScanCudaBatchResult *batchResult,
                                                        string *errorOut)
{
  if(context == NULL ||
     outEvents == NULL ||
     outRowOffsets == NULL ||
     outRunningMin == NULL ||
     outEventCount == NULL ||
     outRunSummaryCount == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }

  outEvents->clear();
  outRowOffsets->clear();
  if(materializeCandidateStatesToHost)
  {
    if(outCandidateStates == NULL)
    {
      if(errorOut != NULL)
      {
        *errorOut = "missing candidate-state output buffer";
      }
      return false;
    }
    outCandidateStates->clear();
  }
  else if(outCandidateStateCount == NULL && (reduceCandidates || reduceAllCandidateStates))
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing candidate-state count output";
    }
    return false;
  }
  if(outCandidateStateCount != NULL)
  {
    *outCandidateStateCount = 0;
  }
  *outRunningMin = 0;
  *outEventCount = 0;
  *outRunSummaryCount = 0;
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }

  const int rowCount = rowEnd - rowStart + 1;
  const int colCount = colEnd - colStart + 1;
  if(rowCount <= 0 || colCount <= 0)
  {
    outRowOffsets->assign(1,0);
    return true;
  }

  if(blockedWords == NULL || blockedWordCount <= 0)
  {
    blockedWords = NULL;
    blockedWordStart = 0;
    blockedWordCount = 0;
    blockedWordStride = 0;
  }

  const uint64_t *blockedWordsDevice = NULL;
  size_t blockedWordsNeeded = 0;
  if(blockedWords != NULL && blockedWordCount > 0)
  {
    blockedWordsNeeded = static_cast<size_t>(rowCount) * static_cast<size_t>(blockedWordCount);
    if(blockedWordsNeeded > 0)
    {
      if(context->blockedWordsDevice == NULL || context->blockedWordsCapacityWords < blockedWordsNeeded)
      {
        if(context->blockedWordsDevice != NULL)
        {
          cudaFree(context->blockedWordsDevice);
          context->blockedWordsDevice = NULL;
          context->blockedWordsCapacityWords = 0;
        }
        cudaError_t allocStatus =
          cudaMalloc(reinterpret_cast<void **>(&context->blockedWordsDevice),
                     blockedWordsNeeded * sizeof(uint64_t));
        if(allocStatus != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(allocStatus);
          }
          return false;
        }
        context->blockedWordsCapacityWords = blockedWordsNeeded;
      }
      cudaError_t status = cudaSuccess;
      if(blockedWordStride == blockedWordCount)
      {
        status = cudaMemcpy(context->blockedWordsDevice,
                            blockedWords,
                            blockedWordsNeeded * sizeof(uint64_t),
                            cudaMemcpyHostToDevice);
      }
      else
      {
        status = cudaMemcpy2D(context->blockedWordsDevice,
                              static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                              blockedWords,
                              static_cast<size_t>(blockedWordStride) * sizeof(uint64_t),
                              static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                              static_cast<size_t>(rowCount),
                              cudaMemcpyHostToDevice);
      }
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      blockedWordsDevice = context->blockedWordsDevice;
    }
  }

  if(reduceAllCandidateStates && filterStartCoordCount > 0 && !filterStartCoordsUploaded)
  {
    if(!sim_scan_cuda_upload_region_filter_start_coords_locked(context,
                                                               filterStartCoords,
                                                               filterStartCoordCount,
                                                               errorOut))
    {
      return false;
    }
  }

  cudaError_t status = cudaSuccess;
  if(seedCandidateCount > 0)
  {
    status = cudaMemcpy(context->candidateStatesDevice,
                        seedCandidates,
                        static_cast<size_t>(seedCandidateCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  status = cudaMemcpy(context->candidateCountDevice,
                      &seedCandidateCount,
                      sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->runningMinDevice,
                      &seedRunningMin,
                      sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int QR = gapOpen + gapExtend;
  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int *ppH = context->diagH0;
  uint64_t *ppHc = context->diagHc0;
  int *prevH = context->diagH1;
  uint64_t *prevHc = context->diagHc1;
  int *curH = context->diagH2;
  uint64_t *curHc = context->diagHc2;

  int *prevD = context->diagD1;
  uint64_t *prevDc = context->diagDc1;
  int *curD = context->diagD2;
  uint64_t *curDc = context->diagDc2;

  int *prevF = context->diagF1;
  uint64_t *prevFc = context->diagFc1;
  int *curF = context->diagF2;
  uint64_t *curFc = context->diagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;

  const int M = queryLength;
  const int N = targetLength;
  const int diagStart = rowStart + colStart;
  const int diagEnd = rowEnd + colEnd;
  for(int diag = diagStart; diag <= diagEnd; ++diag)
  {
    const int curStartIHost = max(rowStart, diag - colEnd);
    const int curEndIHost = min(rowEnd, diag - colStart);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int threadsPerBlock = 256;
    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;

    sim_scan_diag_region_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                             context->BDevice,
                                                             rowStart,
                                                             colStart,
                                                             M,
                                                             N,
                                                             context->leadingDim,
                                                             diag,
                                                             curStartIHost,
                                                             curLenHost,
                                                             prevStartI,
                                                             prevLen,
                                                             ppStartI,
                                                             ppLen,
                                                             gapOpen,
                                                             gapExtend,
                                                             QR,
                                                             prevH,
                                                             prevHc,
                                                             prevD,
                                                             prevDc,
                                                             prevF,
                                                             prevFc,
                                                             ppH,
                                                             ppHc,
                                                             curH,
                                                             curHc,
                                                             curD,
                                                             curDc,
                                                             curF,
                                                             curFc,
                                                             blockedWordsDevice,
                                                             blockedWordStart,
                                                             blockedWordCount,
                                                             context->HScoreDevice,
                                                             context->HCoordDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);

    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  const int countThreads = 256;
  const int countBlocks = rowCount;
  const size_t countSharedBytes = static_cast<size_t>(countThreads) * sizeof(int);
  sim_scan_count_row_events_region_kernel<<<countBlocks, countThreads, countSharedBytes>>>(context->HScoreDevice,
                                                                                           context->leadingDim,
                                                                                           rowStart,
                                                                                           rowCount,
                                                                                           colStart,
                                                                                           colEnd,
                                                                                           eventScoreFloor,
                                                                                           context->rowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                       rowCount,
                                       context->rowOffsetsDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int totalEvents = 0;
  const chrono::steady_clock::time_point d2hStart = chrono::steady_clock::now();
  status = cudaMemcpy(&totalEvents,
                      context->eventCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  *outEventCount = totalEvents;

  const size_t maxEventsAllowed = static_cast<size_t>(rowCount) * static_cast<size_t>(colCount);
  const int summaryThreads = 256;
  const int summaryBlocks = rowCount;
  const size_t summarySharedBytes = static_cast<size_t>(summaryThreads) * sizeof(int);
  if(static_cast<size_t>(totalEvents) > maxEventsAllowed)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA event count overflow";
    }
    return false;
  }

  if(totalEvents > 0)
  {
    if(context->eventsDevice == NULL || context->eventsCapacity < static_cast<size_t>(totalEvents))
    {
      if(context->eventsDevice != NULL)
      {
        cudaFree(context->eventsDevice);
        context->eventsDevice = NULL;
        context->eventsCapacity = 0;
      }
      cudaError_t allocStatus =
        cudaMalloc(reinterpret_cast<void **>(&context->eventsDevice),
                   static_cast<size_t>(totalEvents) * sizeof(SimScanCudaRowEvent));
      if(allocStatus != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(allocStatus);
        }
        return false;
      }
      context->eventsCapacity = static_cast<size_t>(totalEvents);
    }

    const int compactThreads = 256;
    const int compactBlocks = rowCount;
    sim_scan_compact_row_events_region_kernel<<<compactBlocks, compactThreads>>>(context->HScoreDevice,
                                                                                 context->HCoordDevice,
                                                                                 context->leadingDim,
                                                                                 rowStart,
                                                                                 rowCount,
                                                                                 colStart,
                                                                                 colEnd,
                                                                                 eventScoreFloor,
                                                                                 context->rowOffsetsDevice,
                                                                                 context->eventsDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    if(reduceCandidates || reduceAllCandidateStates)
    {
      sim_scan_count_region_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                        context->rowOffsetsDevice,
                                                                                                        rowCount,
                                                                                                        context->rowCountsDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }

      sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                           rowCount,
                                           context->runOffsetsDevice,
                                           context->eventCountDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(reduceCandidates || reduceAllCandidateStates)
  {
    int totalRunSummaries = 0;
    status = cudaMemcpy(&totalRunSummaries,
                        context->eventCountDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(totalRunSummaries < 0 || static_cast<size_t>(totalRunSummaries) > maxEventsAllowed)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA region run summary count overflow";
      }
      return false;
    }
    if(totalRunSummaries > totalEvents)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA region run summary count exceeds event count";
      }
      return false;
    }
    *outRunSummaryCount = static_cast<uint64_t>(totalRunSummaries);
    if(totalRunSummaries > 0)
    {
      if(!ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                      &context->initialRunSummariesCapacity,
                                      static_cast<size_t>(totalRunSummaries),
                                      errorOut))
      {
        return false;
      }

      sim_scan_compact_region_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                          context->rowOffsetsDevice,
                                                                                                          rowCount,
                                                                                                          context->runOffsetsDevice,
                                                                                                          context->initialRunSummariesDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      if(reduceCandidates)
      {
        sim_scan_reduce_region_candidate_summaries_kernel<<<1, sim_scan_initial_reduce_threads>>>(context->initialRunSummariesDevice,
                                                                                                   totalRunSummaries,
                                                                                                   context->candidateStatesDevice,
                                                                                                   context->candidateCountDevice,
                                                                                                   context->runningMinDevice);
        status = cudaGetLastError();
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
      }
      else
      {
        const size_t summaryCount = static_cast<size_t>(totalRunSummaries);
        if(!ensure_sim_scan_cuda_buffer(&context->summaryKeysDevice,
                                        &context->summaryKeysCapacity,
                                        summaryCount,
                                        errorOut) ||
           !ensure_sim_scan_cuda_buffer(&context->reducedKeysDevice,
                                        &context->reducedKeysCapacity,
                                        summaryCount,
                                        errorOut) ||
           !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                        &context->reduceStatesCapacity,
                                        summaryCount,
                                        errorOut) ||
           !ensure_sim_scan_cuda_buffer(&context->reducedStatesDevice,
                                        &context->reducedStatesCapacity,
                                        summaryCount,
                                        errorOut) ||
           !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                        &context->outputCandidateStatesCapacity,
                                        summaryCount,
                                        errorOut))
        {
          return false;
        }

        const int reduceThreads = 256;
        const int reduceBlocks = (totalRunSummaries + reduceThreads - 1) / reduceThreads;
        sim_scan_init_candidate_reduce_states_from_summaries_kernel<<<reduceBlocks, reduceThreads>>>(context->initialRunSummariesDevice,
                                                                                                      totalRunSummaries,
                                                                                                      context->summaryKeysDevice,
                                                                                                      context->reduceStatesDevice);
        status = cudaGetLastError();
        if(status != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }

        int reducedCandidateCount = 0;
        try
        {
          thrust::device_ptr<uint64_t> summaryKeysBegin = thrust::device_pointer_cast(context->summaryKeysDevice);
          thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
            thrust::device_pointer_cast(context->reduceStatesDevice);
          thrust::stable_sort_by_key(thrust::device,
                                     summaryKeysBegin,
                                     summaryKeysBegin + totalRunSummaries,
                                     reduceStatesBegin);
          thrust::pair< thrust::device_ptr<uint64_t>, thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
            thrust::reduce_by_key(thrust::device,
                                  summaryKeysBegin,
                                  summaryKeysBegin + totalRunSummaries,
                                  reduceStatesBegin,
                                  thrust::device_pointer_cast(context->reducedKeysDevice),
                                  thrust::device_pointer_cast(context->reducedStatesDevice),
                                  thrust::equal_to<uint64_t>(),
                                  SimScanCudaCandidateReduceMergeOp());
          reducedCandidateCount =
            static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->reducedKeysDevice));
        }
        catch(const thrust::system_error &e)
        {
          if(errorOut != NULL)
          {
            *errorOut = e.what();
          }
          return false;
        }

        if(reducedCandidateCount < 0 || reducedCandidateCount > totalRunSummaries)
        {
          if(errorOut != NULL)
          {
            *errorOut = "SIM CUDA reduced candidate count overflow";
          }
          return false;
        }

        int outputCandidateCount = reducedCandidateCount;
        if(reducedCandidateCount > 0)
        {
          const int extractThreads = 256;
          const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
          if(filterStartCoordCount > 0)
          {
            status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
            if(status != cudaSuccess)
            {
              if(errorOut != NULL)
              {
                *errorOut = cuda_error_string(status);
              }
              return false;
            }
            sim_scan_filter_candidate_states_by_allowed_start_coords_kernel<<<extractBlocks, extractThreads>>>(context->reducedKeysDevice,
                                                                                                                context->reducedStatesDevice,
                                                                                                                reducedCandidateCount,
                                                                                                                context->filterStartCoordsDevice,
                                                                                                                filterStartCoordCount,
                                                                                                                context->outputCandidateStatesDevice,
                                                                                                                context->filteredCandidateCountDevice);
            status = cudaGetLastError();
            if(status != cudaSuccess)
            {
              if(errorOut != NULL)
              {
                *errorOut = cuda_error_string(status);
              }
              return false;
            }
            status = cudaMemcpy(&outputCandidateCount,
                                context->filteredCandidateCountDevice,
                                sizeof(int),
                                cudaMemcpyDeviceToHost);
            if(status != cudaSuccess)
            {
              if(errorOut != NULL)
              {
                *errorOut = cuda_error_string(status);
              }
              return false;
            }
          }
          else
          {
            sim_scan_extract_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->reducedStatesDevice,
                                                                                         reducedCandidateCount,
                                                                                         context->outputCandidateStatesDevice);
            status = cudaGetLastError();
            if(status != cudaSuccess)
            {
              if(errorOut != NULL)
              {
                *errorOut = cuda_error_string(status);
              }
              return false;
            }
          }
        }

        if(outputCandidateCount < 0 || outputCandidateCount > reducedCandidateCount)
        {
          if(errorOut != NULL)
          {
            *errorOut = "SIM CUDA filtered candidate count overflow";
          }
          return false;
        }
        if(outCandidateStateCount != NULL)
        {
          *outCandidateStateCount = outputCandidateCount;
        }
        if(materializeCandidateStatesToHost && outputCandidateCount > 0)
        {
          outCandidateStates->resize(static_cast<size_t>(outputCandidateCount));
          status = cudaMemcpy(outCandidateStates->data(),
                              context->outputCandidateStatesDevice,
                              static_cast<size_t>(outputCandidateCount) * sizeof(SimScanCudaCandidateState),
                              cudaMemcpyDeviceToHost);
          if(status != cudaSuccess)
          {
            outCandidateStates->clear();
            if(errorOut != NULL)
            {
              *errorOut = cuda_error_string(status);
            }
            return false;
          }
        }
        *outRunningMin = seedRunningMin;
        outEvents->clear();
        outRowOffsets->clear();
      }
    }

    if(reduceAllCandidateStates)
    {
      *outRunningMin = seedRunningMin;
      outEvents->clear();
      outRowOffsets->clear();
    }

    if(reduceCandidates)
    {
      int reducedCandidateCount = 0;
      status = cudaMemcpy(&reducedCandidateCount,
                          context->candidateCountDevice,
                          sizeof(int),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      status = cudaMemcpy(outRunningMin,
                          context->runningMinDevice,
                          sizeof(int),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      if(reducedCandidateCount < 0)
      {
        reducedCandidateCount = 0;
      }
      if(reducedCandidateCount > sim_scan_cuda_max_candidates)
      {
        reducedCandidateCount = sim_scan_cuda_max_candidates;
      }
      if(outCandidateStateCount != NULL)
      {
        *outCandidateStateCount = reducedCandidateCount;
      }
      if(materializeCandidateStatesToHost && reducedCandidateCount > 0)
      {
        outCandidateStates->resize(static_cast<size_t>(reducedCandidateCount));
        status = cudaMemcpy(outCandidateStates->data(),
                            context->candidateStatesDevice,
                            static_cast<size_t>(reducedCandidateCount) * sizeof(SimScanCudaCandidateState),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess)
        {
          outCandidateStates->clear();
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(status);
          }
          return false;
        }
      }
      outRowOffsets->assign(1,0);
    }
  }
  else
  {
    vector<int> rowOffsets(static_cast<size_t>(rowCount + 1),0);
    status = cudaMemcpy(rowOffsets.data(),
                        context->rowOffsetsDevice,
                        static_cast<size_t>(rowCount + 1) * sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    if(totalEvents > 0)
    {
      outEvents->resize(static_cast<size_t>(totalEvents));
      status = cudaMemcpy(outEvents->data(),
                          context->eventsDevice,
                          static_cast<size_t>(totalEvents) * sizeof(SimScanCudaRowEvent),
                          cudaMemcpyDeviceToHost);
      if(status != cudaSuccess)
      {
        outEvents->clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
    *outRowOffsets = rowOffsets;
    *outRunningMin = seedRunningMin;
  }

  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->d2hSeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - d2hStart).count()) / 1.0e9;
    batchResult->taskCount = 1;
    batchResult->launchCount = 1;
  }
  return true;
}

static bool sim_scan_cuda_execute_region_request_to_reserved_slice_locked(SimScanCudaContext *context,
                                                                          int queryLength,
                                                                          int targetLength,
                                                                          int rowStart,
                                                                          int rowEnd,
                                                                          int colStart,
                                                                          int colEnd,
                                                                          int gapOpen,
                                                                          int gapExtend,
                                                                          int eventScoreFloor,
                                                                          const uint64_t *blockedWords,
                                                                          int blockedWordStart,
                                                                          int blockedWordCount,
                                                                          int blockedWordStride,
                                                                          const uint64_t *filterStartCoords,
                                                                          int filterStartCoordCount,
                                                                          bool filterStartCoordsUploaded,
                                                                          int requestIndex,
                                                                          int reservedOutputBase,
                                                                          int reservedOutputCapacity,
                                                                          string *errorOut)
{
  if(context == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing CUDA context";
    }
    return false;
  }

  const int rowCount = rowEnd - rowStart + 1;
  const int colCount = colEnd - colStart + 1;
  if(rowCount <= 0 || colCount <= 0)
  {
    return true;
  }

  if(blockedWords == NULL || blockedWordCount <= 0)
  {
    blockedWords = NULL;
    blockedWordStart = 0;
    blockedWordCount = 0;
    blockedWordStride = 0;
  }

  const uint64_t *blockedWordsDevice = NULL;
  size_t blockedWordsNeeded = 0;
  if(blockedWords != NULL && blockedWordCount > 0)
  {
    blockedWordsNeeded = static_cast<size_t>(rowCount) * static_cast<size_t>(blockedWordCount);
    if(blockedWordsNeeded > 0)
    {
      if(context->blockedWordsDevice == NULL || context->blockedWordsCapacityWords < blockedWordsNeeded)
      {
        if(context->blockedWordsDevice != NULL)
        {
          cudaFree(context->blockedWordsDevice);
          context->blockedWordsDevice = NULL;
          context->blockedWordsCapacityWords = 0;
        }
        cudaError_t allocStatus =
          cudaMalloc(reinterpret_cast<void **>(&context->blockedWordsDevice),
                     blockedWordsNeeded * sizeof(uint64_t));
        if(allocStatus != cudaSuccess)
        {
          if(errorOut != NULL)
          {
            *errorOut = cuda_error_string(allocStatus);
          }
          return false;
        }
        context->blockedWordsCapacityWords = blockedWordsNeeded;
      }
      cudaError_t status = cudaSuccess;
      if(blockedWordStride == blockedWordCount)
      {
        status = cudaMemcpy(context->blockedWordsDevice,
                            blockedWords,
                            blockedWordsNeeded * sizeof(uint64_t),
                            cudaMemcpyHostToDevice);
      }
      else
      {
        status = cudaMemcpy2D(context->blockedWordsDevice,
                              static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                              blockedWords,
                              static_cast<size_t>(blockedWordStride) * sizeof(uint64_t),
                              static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                              static_cast<size_t>(rowCount),
                              cudaMemcpyHostToDevice);
      }
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
      blockedWordsDevice = context->blockedWordsDevice;
    }
  }

  if(filterStartCoordCount > 0 && !filterStartCoordsUploaded)
  {
    if(!sim_scan_cuda_upload_region_filter_start_coords_locked(context,
                                                               filterStartCoords,
                                                               filterStartCoordCount,
                                                               errorOut))
    {
      return false;
    }
  }

  const size_t maxEventsAllowed = static_cast<size_t>(rowCount) * static_cast<size_t>(colCount);
  if(!ensure_sim_scan_cuda_buffer(&context->eventsDevice,
                                  &context->eventsCapacity,
                                  maxEventsAllowed,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                  &context->initialRunSummariesCapacity,
                                  static_cast<size_t>(reservedOutputBase + reservedOutputCapacity),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaSuccess;
  const int QR = gapOpen + gapExtend;
  int *ppH = context->diagH0;
  uint64_t *ppHc = context->diagHc0;
  int *prevH = context->diagH1;
  uint64_t *prevHc = context->diagHc1;
  int *curH = context->diagH2;
  uint64_t *curHc = context->diagHc2;

  int *prevD = context->diagD1;
  uint64_t *prevDc = context->diagDc1;
  int *curD = context->diagD2;
  uint64_t *curDc = context->diagDc2;

  int *prevF = context->diagF1;
  uint64_t *prevFc = context->diagFc1;
  int *curF = context->diagF2;
  uint64_t *curFc = context->diagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;

  const int M = queryLength;
  const int N = targetLength;
  const int diagStart = rowStart + colStart;
  const int diagEnd = rowEnd + colEnd;
  for(int diag = diagStart; diag <= diagEnd; ++diag)
  {
    const int curStartIHost = max(rowStart, diag - colEnd);
    const int curEndIHost = min(rowEnd, diag - colStart);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int threadsPerBlock = 256;
    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_region_kernel<<<blocks, threadsPerBlock>>>(context->ADevice,
                                                             context->BDevice,
                                                             rowStart,
                                                             colStart,
                                                             M,
                                                             N,
                                                             context->leadingDim,
                                                             diag,
                                                             curStartIHost,
                                                             curLenHost,
                                                             prevStartI,
                                                             prevLen,
                                                             ppStartI,
                                                             ppLen,
                                                             gapOpen,
                                                             gapExtend,
                                                             QR,
                                                             prevH,
                                                             prevHc,
                                                             prevD,
                                                             prevDc,
                                                             prevF,
                                                             prevFc,
                                                             ppH,
                                                             ppHc,
                                                             curH,
                                                             curHc,
                                                             curD,
                                                             curDc,
                                                             curF,
                                                             curFc,
                                                             blockedWordsDevice,
                                                             blockedWordStart,
                                                             blockedWordCount,
                                                             context->HScoreDevice,
                                                             context->HCoordDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);

    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  const int countThreads = 256;
  const int countBlocks = rowCount;
  const size_t countSharedBytes = static_cast<size_t>(countThreads) * sizeof(int);
  sim_scan_count_row_events_region_kernel<<<countBlocks, countThreads, countSharedBytes>>>(context->HScoreDevice,
                                                                                           context->leadingDim,
                                                                                           rowStart,
                                                                                           rowCount,
                                                                                           colStart,
                                                                                           colEnd,
                                                                                           eventScoreFloor,
                                                                                           context->rowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                       rowCount,
                                       context->rowOffsetsDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_store_scalar_at_index_kernel<<<1, 1>>>(context->eventCountDevice,
                                                  context->batchEventTotalsDevice,
                                                  requestIndex);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(maxEventsAllowed == 0)
  {
    return true;
  }

  const int compactThreads = 256;
  const int compactBlocks = rowCount;
  sim_scan_compact_row_events_region_kernel<<<compactBlocks, compactThreads>>>(context->HScoreDevice,
                                                                               context->HCoordDevice,
                                                                               context->leadingDim,
                                                                               rowStart,
                                                                               rowCount,
                                                                               colStart,
                                                                               colEnd,
                                                                               eventScoreFloor,
                                                                               context->rowOffsetsDevice,
                                                                               context->eventsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int summaryThreads = 256;
  const int summaryBlocks = rowCount;
  const size_t summarySharedBytes = static_cast<size_t>(summaryThreads) * sizeof(int);
  sim_scan_count_region_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                    context->rowOffsetsDevice,
                                                                                                    rowCount,
                                                                                                    context->rowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_kernel<<<1, 1>>>(context->rowCountsDevice,
                                       rowCount,
                                       context->runOffsetsDevice,
                                       context->eventCountDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_store_scalar_at_index_kernel<<<1, 1>>>(context->eventCountDevice,
                                                  context->batchRunTotalsDevice,
                                                  requestIndex);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  sim_scan_compact_region_run_summaries_kernel<<<summaryBlocks, summaryThreads, summarySharedBytes>>>(context->eventsDevice,
                                                                                                      context->rowOffsetsDevice,
                                                                                                      rowCount,
                                                                                                      context->runOffsetsDevice,
                                                                                                      context->initialRunSummariesDevice +
                                                                                                        static_cast<size_t>(reservedOutputBase));
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_execute_homogeneous_region_request_batch_to_reserved_slices_locked(
  SimScanCudaContext *context,
  const vector<SimScanCudaRequest> &requests,
  size_t requestBegin,
  size_t requestCount,
  const vector<int> &requestCandidateBases,
  vector<int> *outEventCounts,
  vector<int> *outRunCounts,
  string *errorOut)
{
  if(context == NULL || outEventCounts == NULL || outRunCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing homogeneous region batch outputs";
    }
    return false;
  }
  outEventCounts->clear();
  outRunCounts->clear();
  if(requestCount == 0)
  {
    return true;
  }

  const SimScanCudaRequest &first = requests[requestBegin];
  const int rowCount = first.rowEnd - first.rowStart + 1;
  const int colCount = first.colEnd - first.colStart + 1;
  if(rowCount <= 0 || colCount <= 0)
  {
    outEventCounts->assign(requestCount,0);
    outRunCounts->assign(requestCount,0);
    return true;
  }

  const int batchSize = static_cast<int>(requestCount);
  const int leadingDim = colCount + 1;
  const int matrixStride = (rowCount + 1) * leadingDim;
  const int diagCapacity = max(rowCount,colCount) + 2;
  const int rowCountStride = rowCount + 1;
  const int rowOffsetStride = rowCount + 2;
  const size_t batchMatrixCells = static_cast<size_t>(batchSize) * static_cast<size_t>(matrixStride);
  const size_t batchDiagCells = static_cast<size_t>(batchSize) * static_cast<size_t>(diagCapacity);
  const size_t batchRowCounts = static_cast<size_t>(batchSize) * static_cast<size_t>(rowCountStride);
  const size_t batchRowOffsets = static_cast<size_t>(batchSize) * static_cast<size_t>(rowOffsetStride);

  if(!ensure_sim_scan_cuda_buffer(&context->batchHScoreDevice,
                                  &context->batchHScoreCapacityCells,
                                  batchMatrixCells,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchHCoordDevice,
                                  &context->batchHCoordCapacityCells,
                                  batchMatrixCells,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRowCountsDevice,
                                  &context->batchRowCountsCapacity,
                                  batchRowCounts,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRowOffsetsDevice,
                                  &context->batchRowOffsetsCapacity,
                                  batchRowOffsets,
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunOffsetsDevice,
                                  &context->batchRunOffsetsCapacity,
                                  batchRowOffsets,
                                  errorOut) ||
	     !ensure_sim_scan_cuda_buffer(&context->batchEventTotalsDevice,
	                                  &context->batchEventTotalsCapacity,
	                                  requestBegin + static_cast<size_t>(batchSize),
	                                  errorOut) ||
	     !ensure_sim_scan_cuda_buffer(&context->batchRunTotalsDevice,
	                                  &context->batchRunTotalsCapacity,
	                                  requestBegin + static_cast<size_t>(batchSize),
	                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchEventScoreFloorsDevice,
                                  &context->batchEventScoreFloorsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunBasesDevice,
                                  &context->batchRunBasesCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->summaryRowMinColsDevice,
                                  &context->summaryRowMinColsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->summaryRowMaxColsDevice,
                                  &context->summaryRowMaxColsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->rowIntervalOffsetsDevice,
                                  &context->rowIntervalOffsetsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchRunningMinsDevice,
                                  &context->batchRunningMinsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->batchAllCandidateCountsDevice,
                                  &context->batchAllCandidateCountsCapacity,
                                  static_cast<size_t>(batchSize),
                                  errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_true_batch_diag_capacity_locked(*context,batchDiagCells,errorOut))
  {
	  return false;
	}

  int *groupEventTotalsDevice = context->batchEventTotalsDevice + static_cast<ptrdiff_t>(requestBegin);
  int *groupRunTotalsDevice = context->batchRunTotalsDevice + static_cast<ptrdiff_t>(requestBegin);

  vector<int> rowStarts(static_cast<size_t>(batchSize),0);
  vector<int> colStarts(static_cast<size_t>(batchSize),0);
  vector<int> blockedBases(static_cast<size_t>(batchSize),0);
  vector<int> blockedStarts(static_cast<size_t>(batchSize),0);
  vector<int> blockedCounts(static_cast<size_t>(batchSize),0);
  vector<int> eventScoreFloors(static_cast<size_t>(batchSize),0);
  vector<int> runBases(static_cast<size_t>(batchSize),0);
  vector<uint64_t> packedBlockedWords;
  size_t totalBlockedWords = 0;

  for(size_t offset = 0; offset < requestCount; ++offset)
  {
    const SimScanCudaRequest &request = requests[requestBegin + offset];
    const int requestRowCount = request.rowEnd - request.rowStart + 1;
    const int requestColCount = request.colEnd - request.colStart + 1;
    if(requestRowCount != rowCount || requestColCount != colCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "homogeneous region batch requires identical request dimensions";
      }
      return false;
    }

    rowStarts[offset] = request.rowStart;
    colStarts[offset] = request.colStart;
    eventScoreFloors[offset] = request.eventScoreFloor;
    runBases[offset] = requestCandidateBases[requestBegin + offset];

    if(request.blockedWords != NULL && request.blockedWordCount > 0)
    {
      blockedBases[offset] = static_cast<int>(totalBlockedWords);
      blockedStarts[offset] = request.blockedWordStart;
      blockedCounts[offset] = request.blockedWordCount;
      const size_t requestBlockedWords =
        static_cast<size_t>(rowCount) * static_cast<size_t>(request.blockedWordCount);
      packedBlockedWords.resize(totalBlockedWords + requestBlockedWords);
      for(int localRow = 0; localRow < rowCount; ++localRow)
      {
        const uint64_t *src =
          request.blockedWords + static_cast<size_t>(localRow) * static_cast<size_t>(request.blockedWordStride);
        uint64_t *dst =
          packedBlockedWords.data() + totalBlockedWords +
          static_cast<size_t>(localRow) * static_cast<size_t>(request.blockedWordCount);
        memcpy(dst,src,static_cast<size_t>(request.blockedWordCount) * sizeof(uint64_t));
      }
      totalBlockedWords += requestBlockedWords;
    }
  }

  cudaError_t status = cudaMemcpy(context->summaryRowMinColsDevice,
                                  rowStarts.data(),
                                  static_cast<size_t>(batchSize) * sizeof(int),
                                  cudaMemcpyHostToDevice);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->summaryRowMaxColsDevice,
                        colStarts.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->rowIntervalOffsetsDevice,
                        blockedBases.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->batchRunningMinsDevice,
                        blockedStarts.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->batchAllCandidateCountsDevice,
                        blockedCounts.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->batchEventScoreFloorsDevice,
                        eventScoreFloors.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->batchRunBasesDevice,
                        runBases.data(),
                        static_cast<size_t>(batchSize) * sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const uint64_t *blockedWordsDevice = NULL;
  if(totalBlockedWords > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->blockedWordsDevice,
                                    &context->blockedWordsCapacityWords,
                                    totalBlockedWords,
                                    errorOut))
    {
      return false;
    }
    status = cudaMemcpy(context->blockedWordsDevice,
                        packedBlockedWords.data(),
                        totalBlockedWords * sizeof(uint64_t),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    blockedWordsDevice = context->blockedWordsDevice;
  }

  const int QR = first.gapOpen + first.gapExtend;
  int *ppH = context->batchDiagH0;
  uint64_t *ppHc = context->batchDiagHc0;
  int *prevH = context->batchDiagH1;
  uint64_t *prevHc = context->batchDiagHc1;
  int *curH = context->batchDiagH2;
  uint64_t *curHc = context->batchDiagHc2;
  int *prevD = context->batchDiagD1;
  uint64_t *prevDc = context->batchDiagDc1;
  int *curD = context->batchDiagD2;
  uint64_t *curDc = context->batchDiagDc2;
  int *prevF = context->batchDiagF1;
  uint64_t *prevFc = context->batchDiagFc1;
  int *curF = context->batchDiagF2;
  uint64_t *curFc = context->batchDiagFc2;

  int ppStartI = 0;
  int ppLen = 0;
  int prevStartI = 0;
  int prevLen = 0;
  const int threadsPerBlock = 256;
  for(int diag = 2; diag <= rowCount + colCount; ++diag)
  {
    const int curStartIHost = max(1, diag - colCount);
    const int curEndIHost = min(rowCount, diag - 1);
    const int curLenHost = curEndIHost >= curStartIHost ? (curEndIHost - curStartIHost + 1) : 0;
    if(curLenHost <= 0)
    {
      continue;
    }

    const int blocks = (curLenHost + threadsPerBlock - 1) / threadsPerBlock;
    sim_scan_diag_region_true_batch_kernel<<<dim3(static_cast<unsigned int>(blocks),
                                                  static_cast<unsigned int>(batchSize)),
                                             threadsPerBlock>>>(
      context->ADevice,
      context->BDevice,
      leadingDim,
      matrixStride,
      diag,
      curStartIHost,
      curLenHost,
      prevStartI,
      prevLen,
      ppStartI,
      ppLen,
      diagCapacity,
      first.gapOpen,
      first.gapExtend,
      QR,
      context->summaryRowMinColsDevice,
      context->summaryRowMaxColsDevice,
      context->rowIntervalOffsetsDevice,
      context->batchRunningMinsDevice,
      context->batchAllCandidateCountsDevice,
      blockedWordsDevice,
      ppH,
      ppHc,
      prevH,
      prevHc,
      prevD,
      prevDc,
      prevF,
      prevFc,
      curH,
      curHc,
      curD,
      curDc,
      curF,
      curFc,
      context->batchHScoreDevice,
      context->batchHCoordDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    ppStartI = prevStartI;
    ppLen = prevLen;
    prevStartI = curStartIHost;
    prevLen = curLenHost;

    std::swap(ppH, prevH);
    std::swap(ppHc, prevHc);
    std::swap(prevH, curH);
    std::swap(prevHc, curHc);
    std::swap(prevD, curD);
    std::swap(prevDc, curDc);
    std::swap(prevF, curF);
    std::swap(prevFc, curFc);
  }

  const int countThreads = 256;
  const size_t sharedCountBytes = static_cast<size_t>(countThreads) * sizeof(int);
  sim_scan_count_row_events_true_batch_kernel<<<dim3(static_cast<unsigned int>(rowCount),
                                                     static_cast<unsigned int>(batchSize)),
                                                countThreads,
                                                sharedCountBytes>>>(
    context->batchHScoreDevice,
    leadingDim,
    matrixStride,
    rowCount,
    colCount,
    context->batchEventScoreFloorsDevice,
    rowCountStride,
    context->batchRowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_true_batch_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    context->batchRowCountsDevice,
    rowCountStride,
    rowCountStride,
    rowOffsetStride,
    context->batchRowOffsetsDevice,
    groupEventTotalsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outEventCounts->assign(static_cast<size_t>(batchSize),0);
  status = cudaMemcpy(outEventCounts->data(),
                      groupEventTotalsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int maxEventsAllowed = rowCount * colCount;
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int eventCount = (*outEventCounts)[static_cast<size_t>(batchIndex)];
    if(eventCount < 0 || eventCount > maxEventsAllowed)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA homogeneous region batch event count overflow";
      }
      return false;
    }
  }

  sim_scan_count_initial_run_summaries_direct_true_batch_kernel<<<dim3(static_cast<unsigned int>(rowCount),
                                                                        static_cast<unsigned int>(batchSize)),
                                                                  countThreads,
                                                                  sharedCountBytes>>>(
    context->batchHScoreDevice,
    context->batchHCoordDevice,
    leadingDim,
    matrixStride,
    rowCount,
    colCount,
    context->batchEventScoreFloorsDevice,
    rowCountStride,
    context->batchRowCountsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  sim_scan_prefix_sum_true_batch_kernel<<<static_cast<unsigned int>(batchSize), 1>>>(
    context->batchRowCountsDevice,
    rowCountStride,
    rowCountStride,
    rowOffsetStride,
    context->batchRunOffsetsDevice,
    groupRunTotalsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outRunCounts->assign(static_cast<size_t>(batchSize),0);
  status = cudaMemcpy(outRunCounts->data(),
                      groupRunTotalsDevice,
                      static_cast<size_t>(batchSize) * sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  for(int batchIndex = 0; batchIndex < batchSize; ++batchIndex)
  {
    const int runCount = (*outRunCounts)[static_cast<size_t>(batchIndex)];
    if(runCount < 0 || runCount > (*outEventCounts)[static_cast<size_t>(batchIndex)])
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA homogeneous region batch run summary count overflow";
      }
      return false;
    }
  }

  sim_scan_compact_region_run_summaries_direct_true_batch_kernel<<<dim3(static_cast<unsigned int>(rowCount),
                                                                          static_cast<unsigned int>(batchSize)),
                                                                    countThreads,
                                                                    sharedCountBytes>>>(
    context->batchHScoreDevice,
    context->batchHCoordDevice,
    leadingDim,
    matrixStride,
    rowCount,
    colCount,
    context->batchEventScoreFloorsDevice,
    context->summaryRowMinColsDevice,
    context->summaryRowMaxColsDevice,
    context->batchRunOffsetsDevice,
    rowOffsetStride,
    context->batchRunBasesDevice,
    context->initialRunSummariesDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  return true;
}

static bool sim_scan_cuda_reduce_region_summary_slice_to_reserved_candidates_locked(SimScanCudaContext *context,
                                                                                    int summaryBase,
                                                                                    int summaryCount,
                                                                                    int filterStartCoordCount,
                                                                                    int requestIndex,
                                                                                    int reservedOutputBase,
                                                                                    int reservedOutputCapacity,
                                                                                    string *errorOut)
{
  if(context == NULL || summaryCount <= 0)
  {
    return true;
  }

  if(!ensure_sim_scan_cuda_buffer(&context->summaryKeysDevice,
                                  &context->summaryKeysCapacity,
                                  static_cast<size_t>(summaryCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reducedKeysDevice,
                                  &context->reducedKeysCapacity,
                                  static_cast<size_t>(summaryCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                  &context->reduceStatesCapacity,
                                  static_cast<size_t>(summaryCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->reducedStatesDevice,
                                  &context->reducedStatesCapacity,
                                  static_cast<size_t>(summaryCount),
                                  errorOut) ||
     !ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  static_cast<size_t>(summaryCount),
                                  errorOut))
  {
    return false;
  }

  const int reduceThreads = 256;
  const int reduceBlocks = (summaryCount + reduceThreads - 1) / reduceThreads;
  sim_scan_init_candidate_reduce_states_from_summaries_kernel<<<reduceBlocks, reduceThreads>>>(
    context->initialRunSummariesDevice + static_cast<size_t>(summaryBase),
    summaryCount,
    context->summaryKeysDevice,
    context->reduceStatesDevice);
  cudaError_t status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int reducedCandidateCount = 0;
  try
  {
    thrust::device_ptr<uint64_t> summaryKeysBegin = thrust::device_pointer_cast(context->summaryKeysDevice);
    thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
      thrust::device_pointer_cast(context->reduceStatesDevice);
    thrust::stable_sort_by_key(thrust::device,
                               summaryKeysBegin,
                               summaryKeysBegin + summaryCount,
                               reduceStatesBegin);
    thrust::pair< thrust::device_ptr<uint64_t>, thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
      thrust::reduce_by_key(thrust::device,
                            summaryKeysBegin,
                            summaryKeysBegin + summaryCount,
                            reduceStatesBegin,
                            thrust::device_pointer_cast(context->reducedKeysDevice),
                            thrust::device_pointer_cast(context->reducedStatesDevice),
                            thrust::equal_to<uint64_t>(),
                            SimScanCudaCandidateReduceMergeOp());
    reducedCandidateCount =
      static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->reducedKeysDevice));
  }
  catch(const thrust::system_error &e)
  {
    if(errorOut != NULL)
    {
      *errorOut = e.what();
    }
    return false;
  }

  if(reducedCandidateCount < 0 || reducedCandidateCount > summaryCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA aggregated region reduced candidate count overflow";
    }
    return false;
  }
  if(reducedCandidateCount <= 0)
  {
    return true;
  }

  int outputCandidateCount = reducedCandidateCount;
  const int extractThreads = 256;
  const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
  if(filterStartCoordCount > 0)
  {
    status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    sim_scan_filter_candidate_states_by_allowed_start_coords_kernel<<<extractBlocks, extractThreads>>>(context->reducedKeysDevice,
                                                                                                        context->reducedStatesDevice,
                                                                                                        reducedCandidateCount,
                                                                                                        context->filterStartCoordsDevice,
                                                                                                        filterStartCoordCount,
                                                                                                        context->outputCandidateStatesDevice,
                                                                                                        context->filteredCandidateCountDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    sim_scan_store_scalar_at_index_kernel<<<1, 1>>>(context->filteredCandidateCountDevice,
                                                    context->batchCandidateCountsDevice,
                                                    requestIndex);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }
  else
  {
    sim_scan_extract_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->reducedStatesDevice,
                                                                                 reducedCandidateCount,
                                                                                 context->outputCandidateStatesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    status = cudaMemcpy(context->batchCandidateCountsDevice + requestIndex,
                        &outputCandidateCount,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  const int copyBlocks = (reservedOutputCapacity + extractThreads - 1) / extractThreads;
  sim_scan_copy_candidate_states_to_reserved_slice_kernel<<<copyBlocks, extractThreads>>>(context->outputCandidateStatesDevice,
                                                                                          context->batchCandidateCountsDevice + requestIndex,
                                                                                          reservedOutputBase,
                                                                                          reservedOutputCapacity,
                                                                                          context->batchCandidateStatesDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool sim_scan_cuda_enumerate_region_events_row_major_true_batch(const vector<SimScanCudaRequest> &requests,
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
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }
  if(!sim_scan_cuda_can_true_batch_region_requests(requests))
  {
    if(errorOut != NULL)
    {
      *errorOut = "region true batch requests are not compatible";
    }
    return false;
  }

  const SimScanCudaRequest &first = requests[0];
  for(size_t i = 0; i < requests.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[i];
    if(!sim_scan_cuda_validate_region_request_inputs(request.A,
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
                                                     errorOut))
    {
      return false;
    }
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_capacity_locked(*context,first.queryLength,first.targetLength,errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_upload_region_common_inputs_locked(context,
                                                       first.A,
                                                       first.B,
                                                       first.queryLength,
                                                       first.targetLength,
                                                       first.scoreMatrix,
                                                       errorOut))
  {
    return false;
  }

  bool filterUploaded = false;
  if(first.reduceAllCandidateStates && first.filterStartCoordCount > 0)
  {
    if(!sim_scan_cuda_upload_region_filter_start_coords_locked(context,
                                                               first.filterStartCoords,
                                                               first.filterStartCoordCount,
                                                               errorOut))
    {
      return false;
    }
    filterUploaded = true;
  }

  outResults->reserve(requests.size());
  for(size_t i = 0; i < requests.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[i];
    SimScanCudaRequestResult requestResult;
    SimScanCudaBatchResult requestBatchResult;
    int requestEventCount = 0;
    if(!sim_scan_cuda_execute_region_request_locked(context,
                                                    request.queryLength,
                                                    request.targetLength,
                                                    request.rowStart,
                                                    request.rowEnd,
                                                    request.colStart,
                                                    request.colEnd,
                                                    request.gapOpen,
                                                    request.gapExtend,
                                                    request.eventScoreFloor,
                                                    request.blockedWords,
                                                    request.blockedWordStart,
                                                    request.blockedWordCount,
                                                    request.blockedWordStride,
                                                    request.reduceCandidates,
                                                    request.reduceAllCandidateStates,
                                                    request.filterStartCoords,
                                                    request.filterStartCoordCount,
                                                    filterUploaded,
                                                    request.seedCandidates,
                                                    request.seedCandidateCount,
                                                    request.seedRunningMin,
                                                    &requestResult.candidateStates,
                                                    NULL,
                                                    true,
                                                    &requestResult.runningMin,
                                                    &requestEventCount,
                                                    &requestResult.runSummaryCount,
                                                    &requestResult.events,
                                                    &requestResult.rowOffsets,
                                                    &requestBatchResult,
                                                    errorOut))
    {
      outResults->clear();
      if(batchResult != NULL)
      {
        *batchResult = SimScanCudaBatchResult();
      }
      return false;
    }
    requestResult.eventCount = static_cast<uint64_t>(requestEventCount);
    outResults->push_back(requestResult);
    sim_scan_cuda_accumulate_batch_result(requestBatchResult,batchResult);
  }

  if(batchResult != NULL)
  {
    batchResult->usedRegionTrueBatchPath = true;
    batchResult->regionTrueBatchRequestCount = static_cast<uint64_t>(requests.size());
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}

struct SimScanCudaAggregatedRegionDeviceResult
{
  SimScanCudaAggregatedRegionDeviceResult():
    candidateStatesDevice(NULL),
    candidateStateCount(0),
    eventCount(0),
    runSummaryCount(0),
    preAggregateCandidateStateCount(0),
    postAggregateCandidateStateCount(0),
    affectedStartCount(0),
    runningMin(0)
  {
  }

  SimScanCudaCandidateState *candidateStatesDevice;
  int candidateStateCount;
  uint64_t eventCount;
  uint64_t runSummaryCount;
  uint64_t preAggregateCandidateStateCount;
  uint64_t postAggregateCandidateStateCount;
  uint64_t affectedStartCount;
  int runningMin;
};

static bool sim_scan_cuda_enumerate_region_candidate_states_aggregated_device_locked(
  SimScanCudaContext *context,
  const vector<SimScanCudaRequest> &requests,
  SimScanCudaAggregatedRegionDeviceResult *outResult,
  SimScanCudaBatchResult *batchResult,
  string *errorOut)
{
  if(context == NULL || outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  *outResult = SimScanCudaAggregatedRegionDeviceResult();
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(requests.empty())
  {
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  const SimScanCudaRequest &first = requests[0];
  if(first.kind != SIM_SCAN_CUDA_REQUEST_REGION ||
     first.reduceCandidates ||
     !first.reduceAllCandidateStates ||
     first.seedCandidates != NULL ||
     first.seedCandidateCount != 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM CUDA aggregated region path requires reduceAllCandidateStates requests without seeds";
    }
    return false;
  }

  struct SimScanCudaAggregatedRegionExecutionInfo
  {
    size_t requestIndex;
    int rowCount;
    int colCount;
  };
  vector<SimScanCudaAggregatedRegionExecutionInfo> executionInfos(requests.size());
  for(size_t i = 0; i < requests.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[i];
    if(request.kind != SIM_SCAN_CUDA_REQUEST_REGION ||
       request.A != first.A ||
       request.B != first.B ||
       request.queryLength != first.queryLength ||
       request.targetLength != first.targetLength ||
       request.gapOpen != first.gapOpen ||
       request.gapExtend != first.gapExtend ||
       request.scoreMatrix != first.scoreMatrix ||
       request.eventScoreFloor != first.eventScoreFloor ||
       request.reduceCandidates != first.reduceCandidates ||
       request.reduceAllCandidateStates != first.reduceAllCandidateStates ||
       request.filterStartCoords != first.filterStartCoords ||
       request.filterStartCoordCount != first.filterStartCoordCount ||
       request.seedCandidates != NULL ||
       request.seedCandidateCount != 0 ||
       request.seedRunningMin != first.seedRunningMin)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA aggregated region path requires homogeneous requests";
      }
      return false;
    }
    if(!sim_scan_cuda_validate_region_request_inputs(request.A,
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
                                                     errorOut))
	    {
	      return false;
	    }

	    const int rowCount = request.rowEnd - request.rowStart + 1;
	    const int colCount = request.colEnd - request.colStart + 1;
    executionInfos[i].requestIndex = i;
    executionInfos[i].rowCount = rowCount;
    executionInfos[i].colCount = colCount;
  }

  stable_sort(executionInfos.begin(),
              executionInfos.end(),
              [](const SimScanCudaAggregatedRegionExecutionInfo &lhs,
                 const SimScanCudaAggregatedRegionExecutionInfo &rhs)
              {
                if(lhs.rowCount != rhs.rowCount)
                {
                  return lhs.rowCount < rhs.rowCount;
                }
                if(lhs.colCount != rhs.colCount)
                {
                  return lhs.colCount < rhs.colCount;
                }
                return lhs.requestIndex < rhs.requestIndex;
              });

  vector<SimScanCudaRequest> orderedRequests;
  orderedRequests.reserve(requests.size());
  size_t totalCandidateCapacity = 0;
  int maxRequestCandidateCapacity = 0;
  vector<int> requestCandidateBases(requests.size(),0);
  vector<int> requestCandidateCapacities(requests.size(),0);
  for(size_t i = 0; i < executionInfos.size(); ++i)
  {
    const SimScanCudaRequest &request = requests[executionInfos[i].requestIndex];
    const int rowCount = executionInfos[i].rowCount;
    const int colCount = executionInfos[i].colCount;
    orderedRequests.push_back(request);
    int requestCapacity = 0;
    if(rowCount > 0 && colCount > 0)
    {
      const size_t requestCapacitySize = static_cast<size_t>(rowCount) * static_cast<size_t>(colCount);
      if(requestCapacitySize > static_cast<size_t>(numeric_limits<int>::max()) ||
         totalCandidateCapacity > static_cast<size_t>(numeric_limits<int>::max()) - requestCapacitySize)
      {
        if(errorOut != NULL)
        {
          *errorOut = "SIM CUDA aggregated region candidate capacity overflow";
        }
        return false;
      }
      requestCapacity = static_cast<int>(requestCapacitySize);
      requestCandidateBases[i] = static_cast<int>(totalCandidateCapacity);
      requestCandidateCapacities[i] = requestCapacity;
      totalCandidateCapacity += requestCapacitySize;
      maxRequestCandidateCapacity = max(maxRequestCandidateCapacity,requestCapacity);
    }
  }

  const SimScanCudaRequest &orderedFirst = orderedRequests[0];
  if(!ensure_sim_scan_cuda_capacity_locked(*context,orderedFirst.queryLength,orderedFirst.targetLength,errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_upload_region_common_inputs_locked(context,
                                                       orderedFirst.A,
                                                       orderedFirst.B,
                                                       orderedFirst.queryLength,
                                                       orderedFirst.targetLength,
                                                       orderedFirst.scoreMatrix,
                                                       errorOut))
  {
    return false;
  }

  bool filterUploaded = false;
  if(orderedFirst.filterStartCoordCount > 0)
  {
    if(!sim_scan_cuda_upload_region_filter_start_coords_locked(context,
                                                               orderedFirst.filterStartCoords,
                                                               orderedFirst.filterStartCoordCount,
                                                               errorOut))
    {
      return false;
    }
    filterUploaded = true;
  }

  const size_t requestCount = requests.size();
  if(requestCount > 0 &&
     (!ensure_sim_scan_cuda_buffer(&context->batchEventTotalsDevice,
                                   &context->batchEventTotalsCapacity,
                                   requestCount,
                                   errorOut) ||
      !ensure_sim_scan_cuda_buffer(&context->batchRunTotalsDevice,
                                   &context->batchRunTotalsCapacity,
                                   requestCount,
                                   errorOut) ||
      !ensure_sim_scan_cuda_buffer(&context->batchCandidateCountsDevice,
                                   &context->batchCandidateCountsCapacity,
                                   requestCount,
                                   errorOut) ||
      !ensure_sim_scan_cuda_buffer(&context->batchEventBasesDevice,
                                   &context->batchEventBasesCapacity,
                                   requestCount,
                                   errorOut) ||
      !ensure_sim_scan_cuda_buffer(&context->batchRunBasesDevice,
                                   &context->batchRunBasesCapacity,
                                   requestCount,
                                   errorOut)))
  {
    return false;
  }

  if(totalCandidateCapacity > 0 &&
     (!ensure_sim_scan_cuda_buffer(&context->batchCandidateStatesDevice,
                                   &context->batchCandidateStatesCapacity,
                                   totalCandidateCapacity,
                                   errorOut) ||
      !ensure_sim_scan_cuda_buffer(&context->initialRunSummariesDevice,
                                   &context->initialRunSummariesCapacity,
                                   totalCandidateCapacity,
                                   errorOut)))
  {
    return false;
  }

  if(maxRequestCandidateCapacity > 0 &&
     !ensure_sim_scan_cuda_buffer(&context->eventsDevice,
                                  &context->eventsCapacity,
                                  static_cast<size_t>(maxRequestCandidateCapacity),
                                  errorOut))
  {
    return false;
  }

  cudaError_t status = cudaSuccess;
  if(requestCount > 0)
  {
    status = cudaMemset(context->batchEventTotalsDevice,0,requestCount * sizeof(int));
    if(status == cudaSuccess)
    {
      status = cudaMemset(context->batchRunTotalsDevice,0,requestCount * sizeof(int));
    }
    if(status == cudaSuccess)
    {
      status = cudaMemset(context->batchCandidateCountsDevice,0,requestCount * sizeof(int));
    }
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  uint64_t scanGroupCount = 0;
  uint64_t fusedRequestCount = 0;
  for(size_t i = 0; i < orderedRequests.size();)
  {
    const SimScanCudaRequest &request = orderedRequests[i];
    const int rowCount = request.rowEnd - request.rowStart + 1;
    const int colCount = request.colEnd - request.colStart + 1;
    size_t groupEnd = i + 1;
    while(groupEnd < orderedRequests.size())
    {
      const SimScanCudaRequest &candidate = orderedRequests[groupEnd];
      const int candidateRowCount = candidate.rowEnd - candidate.rowStart + 1;
      const int candidateColCount = candidate.colEnd - candidate.colStart + 1;
      if(candidateRowCount != rowCount || candidateColCount != colCount)
      {
        break;
      }
      ++groupEnd;
    }

    if(groupEnd - i > 1)
    {
      vector<int> groupEventCounts;
      vector<int> groupRunCounts;
      if(!sim_scan_cuda_execute_homogeneous_region_request_batch_to_reserved_slices_locked(context,
                                                                                           orderedRequests,
                                                                                           i,
                                                                                           groupEnd - i,
                                                                                           requestCandidateBases,
                                                                                           &groupEventCounts,
                                                                                           &groupRunCounts,
                                                                                           errorOut))
      {
        return false;
      }
      ++scanGroupCount;
      fusedRequestCount += static_cast<uint64_t>(groupEnd - i);
      i = groupEnd;
      continue;
    }

    if(!sim_scan_cuda_execute_region_request_to_reserved_slice_locked(context,
                                                                      request.queryLength,
                                                                      request.targetLength,
                                                                      request.rowStart,
                                                                      request.rowEnd,
                                                                      request.colStart,
                                                                      request.colEnd,
                                                                      request.gapOpen,
                                                                      request.gapExtend,
                                                                      request.eventScoreFloor,
                                                                      request.blockedWords,
                                                                      request.blockedWordStart,
                                                                      request.blockedWordCount,
                                                                      request.blockedWordStride,
                                                                      request.filterStartCoords,
                                                                      request.filterStartCoordCount,
                                                                      filterUploaded,
                                                                      static_cast<int>(i),
                                                                      requestCandidateBases[i],
                                                                      requestCandidateCapacities[i],
                                                                      errorOut))
    {
      return false;
    }
    ++scanGroupCount;
    ++i;
  }

  vector<int> requestEventCounts(requests.size(),0);
  vector<int> requestRunCounts(orderedRequests.size(),0);
  vector<int> requestCandidateCounts(orderedRequests.size(),0);
  vector<int> packedCandidateBases(orderedRequests.size(),0);
  double d2hSeconds = 0.0;
  if(requestCount > 0)
  {
    const chrono::steady_clock::time_point copyStart = chrono::steady_clock::now();
    status = cudaMemcpy(requestEventCounts.data(),
                        context->batchEventTotalsDevice,
                        requestCount * sizeof(int),
                        cudaMemcpyDeviceToHost);
    if(status == cudaSuccess)
    {
      status = cudaMemcpy(requestRunCounts.data(),
                          context->batchRunTotalsDevice,
                          requestCount * sizeof(int),
                          cudaMemcpyDeviceToHost);
    }
    d2hSeconds +=
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - copyStart).count()) / 1.0e9;
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  for(size_t i = 0; i < requests.size(); ++i)
  {
    const int requestCapacity = requestCandidateCapacities[i];
    const int requestEventCount = requestEventCounts[i];
    const int requestRunCount = requestRunCounts[i];
    if(requestEventCount < 0 || requestEventCount > requestCapacity)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA aggregated region event count overflow";
      }
      return false;
    }
    if(requestRunCount < 0 || requestRunCount > requestEventCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA aggregated region run summary count overflow";
      }
      return false;
    }
    outResult->eventCount += static_cast<uint64_t>(requestEventCount);
    outResult->runSummaryCount += static_cast<uint64_t>(requestRunCount);
    if(requestRunCount > 0 &&
       !sim_scan_cuda_reduce_region_summary_slice_to_reserved_candidates_locked(context,
                                                                                requestCandidateBases[i],
                                                                                requestRunCount,
                                                                                first.filterStartCoordCount,
                                                                                static_cast<int>(i),
                                                                                requestCandidateBases[i],
                                                                                requestCapacity,
                                                                                errorOut))
    {
      return false;
    }
  }

  if(requestCount > 0)
  {
    const chrono::steady_clock::time_point copyStart = chrono::steady_clock::now();
    status = cudaMemcpy(requestCandidateCounts.data(),
                        context->batchCandidateCountsDevice,
                        requestCount * sizeof(int),
                        cudaMemcpyDeviceToHost);
    d2hSeconds +=
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - copyStart).count()) / 1.0e9;
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  int packedCandidateCountInt = 0;
  for(size_t i = 0; i < requests.size(); ++i)
  {
    const int requestCandidateCount = requestCandidateCounts[i];
    if(requestCandidateCount < 0 ||
       requestCandidateCount > requestRunCounts[i] ||
       requestCandidateCount > requestCandidateCapacities[i] ||
       packedCandidateCountInt > static_cast<int>(totalCandidateCapacity) - requestCandidateCount)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA aggregated region packed candidate count overflow";
      }
      return false;
    }
    packedCandidateBases[i] = packedCandidateCountInt;
    packedCandidateCountInt += requestCandidateCount;
  }

  outResult->preAggregateCandidateStateCount = static_cast<uint64_t>(packedCandidateCountInt);
  outResult->affectedStartCount = static_cast<uint64_t>(orderedFirst.filterStartCoordCount);
  outResult->runningMin = orderedFirst.seedRunningMin;

  int reducedCandidateCount = 0;
  if(packedCandidateCountInt > 0)
  {
    if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                    &context->outputCandidateStatesCapacity,
                                    static_cast<size_t>(packedCandidateCountInt),
                                    errorOut) ||
       !ensure_sim_scan_cuda_buffer(&context->summaryKeysDevice,
                                    &context->summaryKeysCapacity,
                                    static_cast<size_t>(packedCandidateCountInt),
                                    errorOut) ||
       !ensure_sim_scan_cuda_buffer(&context->reducedKeysDevice,
                                    &context->reducedKeysCapacity,
                                    static_cast<size_t>(packedCandidateCountInt),
                                    errorOut) ||
       !ensure_sim_scan_cuda_buffer(&context->reduceStatesDevice,
                                    &context->reduceStatesCapacity,
                                    static_cast<size_t>(packedCandidateCountInt),
                                    errorOut) ||
       !ensure_sim_scan_cuda_buffer(&context->reducedStatesDevice,
                                    &context->reducedStatesCapacity,
                                    static_cast<size_t>(packedCandidateCountInt),
                                    errorOut))
    {
      return false;
    }

    status = cudaMemcpy(context->batchEventBasesDevice,
                        requestCandidateBases.data(),
                        requestCount * sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status == cudaSuccess)
    {
      status = cudaMemcpy(context->batchRunBasesDevice,
                          packedCandidateBases.data(),
                          requestCount * sizeof(int),
                          cudaMemcpyHostToDevice);
    }
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int compactThreads = 256;
    const int compactBlocks = (maxRequestCandidateCapacity + compactThreads - 1) / compactThreads;
    sim_scan_compact_batch_reserved_candidate_states_kernel<<<dim3(static_cast<unsigned int>(compactBlocks),
                                                                   static_cast<unsigned int>(requestCount)),
                                                             compactThreads>>>(context->batchCandidateStatesDevice,
                                                                               context->batchCandidateCountsDevice,
                                                                               context->batchEventBasesDevice,
                                                                               context->batchRunBasesDevice,
                                                                               context->outputCandidateStatesDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    const int reduceThreads = 256;
    const int reduceBlocks = (packedCandidateCountInt + reduceThreads - 1) / reduceThreads;
    sim_scan_init_candidate_reduce_states_from_candidate_states_kernel<<<reduceBlocks, reduceThreads>>>(
      context->outputCandidateStatesDevice,
      packedCandidateCountInt,
      context->summaryKeysDevice,
      context->reduceStatesDevice,
      0);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }

    try
    {
      thrust::device_ptr<uint64_t> summaryKeysBegin = thrust::device_pointer_cast(context->summaryKeysDevice);
      thrust::device_ptr<SimScanCudaCandidateReduceState> reduceStatesBegin =
        thrust::device_pointer_cast(context->reduceStatesDevice);
      thrust::stable_sort_by_key(thrust::device,
                                 summaryKeysBegin,
                                 summaryKeysBegin + packedCandidateCountInt,
                                 reduceStatesBegin);
      thrust::pair< thrust::device_ptr<uint64_t>, thrust::device_ptr<SimScanCudaCandidateReduceState> > reducedEnds =
        thrust::reduce_by_key(thrust::device,
                              summaryKeysBegin,
                              summaryKeysBegin + packedCandidateCountInt,
                              reduceStatesBegin,
                              thrust::device_pointer_cast(context->reducedKeysDevice),
                              thrust::device_pointer_cast(context->reducedStatesDevice),
                              thrust::equal_to<uint64_t>(),
                              SimScanCudaCandidateReduceMergeOp());
      reducedCandidateCount =
        static_cast<int>(reducedEnds.first - thrust::device_pointer_cast(context->reducedKeysDevice));
    }
    catch(const thrust::system_error &e)
    {
      if(errorOut != NULL)
      {
        *errorOut = e.what();
      }
      return false;
    }

    if(reducedCandidateCount < 0 || reducedCandidateCount > packedCandidateCountInt)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM CUDA aggregated region reduced candidate count overflow";
      }
      return false;
    }

    outResult->postAggregateCandidateStateCount = static_cast<uint64_t>(reducedCandidateCount);
    if(reducedCandidateCount > 0)
    {
      const int extractThreads = 256;
      const int extractBlocks = (reducedCandidateCount + extractThreads - 1) / extractThreads;
      sim_scan_extract_candidate_states_kernel<<<extractBlocks, extractThreads>>>(context->reducedStatesDevice,
                                                                                  reducedCandidateCount,
                                                                                  context->batchCandidateStatesDevice);
      status = cudaGetLastError();
      if(status != cudaSuccess)
      {
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outResult->candidateStatesDevice =
    reducedCandidateCount > 0 ? context->batchCandidateStatesDevice : NULL;
  outResult->candidateStateCount = reducedCandidateCount;

  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->d2hSeconds = d2hSeconds;
    batchResult->usedRegionPackedAggregationPath = true;
    batchResult->usedRegionTrueBatchPath = fusedRequestCount > 0;
    batchResult->regionTrueBatchRequestCount = fusedRequestCount;
    batchResult->regionPackedAggregationRequestCount = static_cast<uint64_t>(requests.size());
    batchResult->taskCount = scanGroupCount;
    batchResult->launchCount = scanGroupCount;
  }

  clear_sim_scan_cuda_error(errorOut);
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
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }

  SimScanCudaAggregatedRegionDeviceResult deviceResult;
  if(!sim_scan_cuda_enumerate_region_candidate_states_aggregated_device_locked(context,
                                                                               requests,
                                                                               &deviceResult,
                                                                               batchResult,
                                                                               errorOut))
  {
    return false;
  }

  outResult->eventCount = deviceResult.eventCount;
  outResult->runSummaryCount = deviceResult.runSummaryCount;
  outResult->preAggregateCandidateStateCount = deviceResult.preAggregateCandidateStateCount;
  outResult->postAggregateCandidateStateCount = deviceResult.postAggregateCandidateStateCount;
  outResult->affectedStartCount = deviceResult.affectedStartCount;
  outResult->runningMin = deviceResult.runningMin;

  if(deviceResult.candidateStateCount > 0)
  {
    outResult->candidateStates.resize(static_cast<size_t>(deviceResult.candidateStateCount));
    const chrono::steady_clock::time_point copyStart = chrono::steady_clock::now();
    const cudaError_t status = cudaMemcpy(outResult->candidateStates.data(),
                                          deviceResult.candidateStatesDevice,
                                          static_cast<size_t>(deviceResult.candidateStateCount) *
                                            sizeof(SimScanCudaCandidateState),
                                          cudaMemcpyDeviceToHost);
    const double copySeconds =
      static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                            chrono::steady_clock::now() - copyStart).count()) / 1.0e9;
    if(batchResult != NULL)
    {
      batchResult->d2hSeconds += copySeconds;
    }
    if(status != cudaSuccess)
    {
      outResult->candidateStates.clear();
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
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
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing residency output buffers";
    }
    return false;
  }
  *outResult = SimScanCudaRegionResidencyResult();
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }
  if(handle == NULL || !handle->valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid persistent safe-store handle";
    }
    return false;
  }
  if(seedCandidates.size() > static_cast<size_t>(sim_scan_cuda_max_candidates))
  {
    if(errorOut != NULL)
    {
      *errorOut = "seed frontier exceeds device candidate capacity";
    }
    return false;
  }
  if(requests.empty())
  {
    outResult->frontierStateCount = static_cast<uint64_t>(seedCandidates.size());
    if(materializeFrontierStatesToHost)
    {
      outResult->frontierStates = seedCandidates;
    }
    outResult->runningMin = seedRunningMin;
    clear_sim_scan_cuda_error(errorOut);
    return true;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(handle->device,handle->slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,handle->device,errorOut))
  {
    return false;
  }

  SimScanCudaAggregatedRegionDeviceResult aggregatedDeviceResult;
  if(!sim_scan_cuda_enumerate_region_candidate_states_aggregated_device_locked(context,
                                                                               requests,
                                                                               &aggregatedDeviceResult,
                                                                               batchResult,
                                                                               errorOut))
  {
    return false;
  }

  outResult->eventCount = aggregatedDeviceResult.eventCount;
  outResult->runSummaryCount = aggregatedDeviceResult.runSummaryCount;
  outResult->updatedStateCount =
    static_cast<uint64_t>(aggregatedDeviceResult.candidateStateCount);

  const SimScanCudaRequest &first = requests[0];
  const int trackedStartCoordCount = first.filterStartCoordCount;
  vector<SimScanCudaCandidateState> filteredSeedCandidates;
  filteredSeedCandidates.reserve(seedCandidates.size());
  if(trackedStartCoordCount > 0 && first.filterStartCoords != NULL)
  {
    for(size_t stateIndex = 0; stateIndex < seedCandidates.size(); ++stateIndex)
    {
      const uint64_t startCoord =
        simScanCudaCandidateStateStartCoord(seedCandidates[stateIndex]);
      if(!binary_search(first.filterStartCoords,
                        first.filterStartCoords + trackedStartCoordCount,
                        startCoord))
      {
        filteredSeedCandidates.push_back(seedCandidates[stateIndex]);
      }
    }
  }
  else
  {
    filteredSeedCandidates = seedCandidates;
  }

  const size_t scratchStateCapacity =
    max(handle->stateCount,
        max(max(seedCandidates.size(),handle->frontierCount),
            static_cast<size_t>(aggregatedDeviceResult.candidateStateCount)));
  if(!ensure_sim_scan_cuda_buffer(&context->outputCandidateStatesDevice,
                                  &context->outputCandidateStatesCapacity,
                                  scratchStateCapacity,
                                  errorOut))
  {
    return false;
  }

  if(!sim_scan_cuda_begin_aux_timing(context,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaSuccess;
  const int zero = 0;
  SimScanCudaCandidateState *frontierBufferDevice = context->candidateStatesDevice;
  const bool canReuseCachedFrontier = filteredSeedCandidates.empty() && handle->frontierValid;
  if(canReuseCachedFrontier)
  {
    if(trackedStartCoordCount > 0)
    {
      if(!sim_scan_cuda_upload_region_filter_start_coords_locked(context,
                                                                 first.filterStartCoords,
                                                                 trackedStartCoordCount,
                                                                 errorOut))
      {
        return false;
      }
      status = cudaMemset(context->filteredCandidateCountDevice,0,sizeof(int));
      if(status == cudaSuccess)
      {
        const int threads = 256;
        const int blocks =
          max(1,
              static_cast<int>((handle->frontierCount + static_cast<size_t>(threads) - 1) /
                               static_cast<size_t>(threads)));
        sim_scan_filter_persistent_safe_store_excluding_start_coords_kernel<<<blocks, threads>>>(
          sim_scan_cuda_handle_frontier_states_device(*handle),
          static_cast<int>(handle->frontierCount),
          context->filterStartCoordsDevice,
          trackedStartCoordCount,
          context->outputCandidateStatesDevice,
          context->filteredCandidateCountDevice);
        status = cudaGetLastError();
      }
      if(status == cudaSuccess)
      {
        status = cudaMemcpy(context->candidateCountDevice,
                            context->filteredCandidateCountDevice,
                            sizeof(int),
                            cudaMemcpyDeviceToDevice);
      }
      frontierBufferDevice = context->outputCandidateStatesDevice;
    }
    else
    {
      const int frontierCount = static_cast<int>(handle->frontierCount);
      status = cudaMemcpy(context->candidateCountDevice,
                          &frontierCount,
                          sizeof(int),
                          cudaMemcpyHostToDevice);
      frontierBufferDevice = sim_scan_cuda_handle_frontier_states_device(*handle);
    }
    if(status == cudaSuccess)
    {
      status = cudaMemcpy(context->runningMinDevice,
                          &handle->frontierRunningMin,
                          sizeof(int),
                          cudaMemcpyHostToDevice);
    }
  }
  else if(filteredSeedCandidates.empty())
  {
    status = cudaMemcpy(context->candidateCountDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  else
  {
    status = cudaMemcpy(context->candidateStatesDevice,
                        filteredSeedCandidates.data(),
                        filteredSeedCandidates.size() * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyHostToDevice);
    if(status == cudaSuccess)
    {
      const int seedCount = static_cast<int>(filteredSeedCandidates.size());
      status = cudaMemcpy(context->candidateCountDevice,
                          &seedCount,
                          sizeof(int),
                          cudaMemcpyHostToDevice);
    }
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->runningMinDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int updatedStateCount = aggregatedDeviceResult.candidateStateCount;

  sim_scan_merge_candidate_states_into_frontier_kernel<<<1, sim_scan_initial_reduce_threads>>>(
    updatedStateCount > 0 ? aggregatedDeviceResult.candidateStatesDevice : NULL,
    updatedStateCount,
    frontierBufferDevice,
    context->candidateCountDevice,
    context->runningMinDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  double residencyD2HSeconds = 0.0;
  int frontierCount = 0;
  const chrono::steady_clock::time_point countCopyStart = chrono::steady_clock::now();
  status = cudaMemcpy(&frontierCount,
                      context->candidateCountDevice,
                      sizeof(int),
                      cudaMemcpyDeviceToHost);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&outResult->runningMin,
                        context->runningMinDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  residencyD2HSeconds +=
    static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                          chrono::steady_clock::now() - countCopyStart).count()) / 1.0e9;
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(frontierCount < 0 || frontierCount > sim_scan_cuda_max_candidates)
  {
    if(errorOut != NULL)
    {
      *errorOut = "region residency frontier count overflow";
    }
    return false;
  }

  if(frontierCount > 0)
  {
    outResult->frontierStateCount = static_cast<uint64_t>(frontierCount);
    if(materializeFrontierStatesToHost)
    {
      outResult->frontierStates.resize(static_cast<size_t>(frontierCount));
      const chrono::steady_clock::time_point frontierCopyStart = chrono::steady_clock::now();
      status = cudaMemcpy(outResult->frontierStates.data(),
                          frontierBufferDevice,
                          static_cast<size_t>(frontierCount) * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyDeviceToHost);
      residencyD2HSeconds +=
        static_cast<double>(chrono::duration_cast<chrono::nanoseconds>(
                              chrono::steady_clock::now() - frontierCopyStart).count()) / 1.0e9;
      if(status != cudaSuccess)
      {
        outResult->frontierStates.clear();
        if(errorOut != NULL)
        {
          *errorOut = cuda_error_string(status);
        }
        return false;
      }
    }
  }

  if(!sim_scan_cuda_cache_persistent_safe_store_frontier_from_device_locked(
       frontierCount > 0 ? frontierBufferDevice : NULL,
       frontierCount,
       outResult->runningMin,
       handle,
       errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_rebuild_persistent_safe_candidate_state_store_from_device_locked(
       context,
       trackedStartCoordCount > 0 ? context->filterStartCoordsDevice : NULL,
       trackedStartCoordCount,
       updatedStateCount > 0 ? aggregatedDeviceResult.candidateStatesDevice : NULL,
       updatedStateCount,
       frontierCount > 0 ? frontierBufferDevice : NULL,
       frontierCount,
       outResult->runningMin,
       handle,
       errorOut))
  {
    return false;
  }

  double residencyGpuSeconds = 0.0;
  if(!sim_scan_cuda_end_aux_timing(context,&residencyGpuSeconds,errorOut))
  {
    return false;
  }
  if(batchResult != NULL)
  {
    batchResult->gpuSeconds += residencyGpuSeconds;
    batchResult->d2hSeconds += residencyD2HSeconds;
  }

  clear_sim_scan_cuda_error(errorOut);
  return true;
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
  if(outEvents == NULL ||
     outRowOffsets == NULL ||
     outCandidateStates == NULL ||
     outRunningMin == NULL ||
     outEventCount == NULL ||
     outRunSummaryCount == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  outEvents->clear();
  outRowOffsets->clear();
  outCandidateStates->clear();
  *outRunningMin = 0;
  *outEventCount = 0;
  *outRunSummaryCount = 0;
  if(batchResult != NULL)
  {
    *batchResult = SimScanCudaBatchResult();
  }

  if(!sim_scan_cuda_validate_region_request_inputs(A,
                                                   B,
                                                   queryLength,
                                                   targetLength,
                                                   rowStart,
                                                   rowEnd,
                                                   colStart,
                                                   colEnd,
                                                   gapOpen,
                                                   gapExtend,
                                                   scoreMatrix,
                                                   blockedWords,
                                                   blockedWordStart,
                                                   blockedWordCount,
                                                   blockedWordStride,
                                                   reduceCandidates,
                                                   reduceAllCandidateStates,
                                                   filterStartCoords,
                                                   filterStartCoordCount,
                                                   seedCandidates,
                                                   seedCandidateCount,
                                                   errorOut))
  {
    return false;
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(deviceStatus);
    }
    return false;
  }

  SimScanCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_scan_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_scan_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_scan_cuda_capacity_locked(*context,queryLength,targetLength,errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_upload_region_common_inputs_locked(context,
                                                       A,
                                                       B,
                                                       queryLength,
                                                       targetLength,
                                                       scoreMatrix,
                                                       errorOut))
  {
    return false;
  }
  if(!sim_scan_cuda_execute_region_request_locked(context,
                                                  queryLength,
                                                  targetLength,
                                                  rowStart,
                                                  rowEnd,
                                                  colStart,
                                                  colEnd,
                                                  gapOpen,
                                                  gapExtend,
                                                  eventScoreFloor,
                                                  blockedWords,
                                                  blockedWordStart,
                                                  blockedWordCount,
                                                  blockedWordStride,
                                                  reduceCandidates,
                                                  reduceAllCandidateStates,
                                                  filterStartCoords,
                                                  filterStartCoordCount,
                                                  false,
                                                  seedCandidates,
                                                  seedCandidateCount,
                                                  seedRunningMin,
                                                  outCandidateStates,
                                                  NULL,
                                                  true,
                                                  outRunningMin,
                                                  outEventCount,
                                                  outRunSummaryCount,
                                                  outEvents,
                                                  outRowOffsets,
                                                  batchResult,
                                                  errorOut))
  {
    return false;
  }
  clear_sim_scan_cuda_error(errorOut);
  return true;
}
