#include "calc_score_cuda.h"

#include <cuda_runtime.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>

using namespace std;

static __device__ __forceinline__ int cuda_max_int(int a,int b)
{
  return a > b ? a : b;
}

static __device__ __forceinline__ int cuda_clamp_nonnegative(int value)
{
  return value > 0 ? value : 0;
}

static __device__ __forceinline__ int cuda_warp_reduce_max_int(int value)
{
  for(int offset = 16; offset > 0; offset >>= 1)
  {
    value = cuda_max_int(value, __shfl_down_sync(0xffffffffu, value, offset));
  }
  return value;
}

static __device__ __forceinline__ int cuda_warp_shift_left_1(int value,int lane)
{
  const int shifted = __shfl_up_sync(0xffffffffu, value, 1);
  return lane == 0 ? 0 : shifted;
}

static __device__ __forceinline__ int striped_sw_warp(const int16_t *profile,
                                                      const uint8_t *target,
                                                      const uint16_t *permutation,
                                                      int targetLength,
                                                      int segLen,
                                                      int lane,
                                                      int16_t *E,
                                                      int16_t *H0,
                                                      int16_t *H1)
{
  const int gapOpen = 16;
  const int gapExtend = 4;
  int laneMax = 0;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = target[static_cast<int>(permutation[targetIndex])];
    const int16_t *profileRow = profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

    int vF = 0;
    int vH = static_cast<int>(HLoad[(segLen - 1) * 32 + lane]);
    vH = cuda_warp_shift_left_1(vH,lane);

    for(int segIndex = 0; segIndex < segLen; ++segIndex)
    {
      const int score = static_cast<int>(profileRow[segIndex * 32 + lane]);
      const int oldH = static_cast<int>(HLoad[segIndex * 32 + lane]);
      int vE = static_cast<int>(E[segIndex * 32 + lane]);

      vH = vH + score;
      vH = cuda_max_int(vH, vE);
      vH = cuda_max_int(vH, vF);
      vH = cuda_clamp_nonnegative(vH);

      HStore[segIndex * 32 + lane] = static_cast<int16_t>(vH);
      laneMax = cuda_max_int(laneMax, vH);

      int vHGapOpen = vH - gapOpen;
      vHGapOpen = cuda_clamp_nonnegative(vHGapOpen);

      vE = vE - gapExtend;
      vE = cuda_clamp_nonnegative(vE);
      vE = cuda_max_int(vE, vHGapOpen);
      E[segIndex * 32 + lane] = static_cast<int16_t>(vE);

      vF = vF - gapExtend;
      vF = cuda_clamp_nonnegative(vF);
      vF = cuda_max_int(vF, vHGapOpen);

      vH = oldH;
    }

    int segIndex = 0;
    int vHStore = static_cast<int>(HStore[segIndex * 32 + lane]);
    vF = cuda_warp_shift_left_1(vF,lane);

    while(true)
    {
      const int vHGapOpen = cuda_clamp_nonnegative(vHStore - gapOpen);
      const int shouldContinue = vF > vHGapOpen ? 1 : 0;
      if(__ballot_sync(0xffffffffu, shouldContinue) == 0)
      {
        break;
      }

      vHStore = cuda_max_int(vHStore, vF);
      HStore[segIndex * 32 + lane] = static_cast<int16_t>(vHStore);
      laneMax = cuda_max_int(laneMax, vHStore);

      const int vHStoreGapOpen = cuda_clamp_nonnegative(vHStore - gapOpen);
      int vE = static_cast<int>(E[segIndex * 32 + lane]);
      vE = cuda_max_int(vE, vHStoreGapOpen);
      E[segIndex * 32 + lane] = static_cast<int16_t>(vE);

      vF = vF - gapExtend;
      vF = cuda_clamp_nonnegative(vF);

      ++segIndex;
      if(segIndex >= segLen)
      {
        segIndex = 0;
        vF = cuda_warp_shift_left_1(vF,lane);
      }
      vHStore = static_cast<int>(HStore[segIndex * 32 + lane]);
    }

    int16_t *tmp = HLoad;
    HLoad = HStore;
    HStore = tmp;
  }

  laneMax = cuda_warp_reduce_max_int(laneMax);
  return laneMax;
}

__global__ void calc_score_cuda_kernel(const int16_t *profileFwd,
                                       const int16_t *profileRev,
                                       const uint8_t *encodedTargets,
                                       const uint16_t *permutations,
                                       int taskCount,
                                       int targetLength,
                                       int pairCount,
                                       int segLen,
                                       int *outScores)
{
  const int threadIndex = static_cast<int>(threadIdx.x);
  const int lane = threadIndex & 31;
  const int warpId = threadIndex >> 5;

  if(warpId >= 2)
  {
    return;
  }

  const int blockIndex = static_cast<int>(blockIdx.x);
  const int taskIndex = blockIndex / pairCount;
  const int pairIndex = blockIndex - taskIndex * pairCount;
  if(taskIndex >= taskCount)
  {
    return;
  }

  extern __shared__ int16_t sharedMem[];
  const int perWarpStride = 3 * segLen * 32;
  int16_t *warpBase = sharedMem + warpId * perWarpStride;
  int16_t *E = warpBase;
  int16_t *H0 = warpBase + segLen * 32;
  int16_t *H1 = warpBase + 2 * segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget = encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * static_cast<size_t>(targetLength);
  const uint16_t *permutation = warpId == 0 ? evenPermutation : (evenPermutation + targetLength);
  const int16_t *profile = warpId == 0 ? profileFwd : profileRev;

  const int score = striped_sw_warp(profile, taskTarget, permutation, targetLength, segLen, lane, E, H0, H1);

  __shared__ int warpScores[2];
  if(lane == 0)
  {
    warpScores[warpId] = score;
  }
  __syncthreads();
  if(threadIndex == 0)
  {
    const int maxScore = warpScores[0] > warpScores[1] ? warpScores[0] : warpScores[1];
    outScores[static_cast<size_t>(taskIndex) * static_cast<size_t>(pairCount) + static_cast<size_t>(pairIndex)] = maxScore;
  }
}

__global__ void calc_score_cuda_kernel_v2(const int16_t *profileFwd,
                                          const int16_t *profileRev,
                                          const uint8_t *encodedTargets,
                                          const uint16_t *permutations,
                                          int taskCount,
                                          int targetLength,
                                          int pairCount,
                                          int segLen,
                                          int *outOrientationScores)
{
  const int lane = static_cast<int>(threadIdx.x) & 31;
  const int blockIndex = static_cast<int>(blockIdx.x);
  const int orientationIndex = blockIndex & 1;
  const int pairTaskIndex = blockIndex >> 1;
  const int taskIndex = pairTaskIndex / pairCount;
  const int pairIndex = pairTaskIndex - taskIndex * pairCount;
  if(taskIndex >= taskCount)
  {
    return;
  }

  extern __shared__ int16_t sharedMem[];
  int16_t *E = sharedMem;
  int16_t *H0 = sharedMem + segLen * 32;
  int16_t *H1 = sharedMem + 2 * segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget = encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * static_cast<size_t>(targetLength);
  const uint16_t *permutation = orientationIndex == 0 ? evenPermutation : (evenPermutation + targetLength);
  const int16_t *profile = orientationIndex == 0 ? profileFwd : profileRev;

  const int score = striped_sw_warp(profile, taskTarget, permutation, targetLength, segLen, lane, E, H0, H1);
  if(lane == 0)
  {
    outOrientationScores[(static_cast<size_t>(taskIndex) * static_cast<size_t>(pairCount) +
                          static_cast<size_t>(pairIndex)) *
                           2u +
                         static_cast<size_t>(orientationIndex)] = score;
  }
}

static inline string cuda_error_string(cudaError_t error)
{
  const char *message = cudaGetErrorString(error);
  if(message == NULL)
  {
    return "unknown CUDA error";
  }
  return string(message);
}

static inline double calc_score_cuda_now_seconds()
{
  typedef chrono::steady_clock Clock;
  const Clock::time_point now = Clock::now();
  return chrono::duration_cast< chrono::duration<double> >(now.time_since_epoch()).count();
}

static inline bool calc_score_cuda_env_enabled(const char *name)
{
  const char *env = getenv(name);
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

static inline bool calc_score_cuda_pipeline_v2_enabled_runtime()
{
  return calc_score_cuda_env_enabled("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2");
}

static inline bool calc_score_cuda_pipeline_v2_shadow_enabled_runtime()
{
  return calc_score_cuda_pipeline_v2_enabled_runtime() &&
         calc_score_cuda_env_enabled("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");
}

static inline bool calc_score_cuda_validate_enabled_runtime()
{
  return calc_score_cuda_env_enabled("LONGTARGET_CUDA_VALIDATE");
}

struct CalcScoreCudaBatchContext
{
  CalcScoreCudaBatchContext():
    initialized(false),
    device(0),
    capacityTasks(0),
    capacityTargetLength(0),
    capacityPermutationCount(0),
    capacityPairCount(0),
    targetsDevice(NULL),
    permutationsDevice(NULL),
    scoresDevice(NULL),
    orientationScoresDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL)
  {
  }

  bool initialized;
  int device;

  int capacityTasks;
  int capacityTargetLength;
  int capacityPermutationCount;
  int capacityPairCount;

  uint8_t *targetsDevice;
  uint16_t *permutationsDevice;
  int *scoresDevice;
  int *orientationScoresDevice;

  cudaEvent_t startEvent;
  cudaEvent_t stopEvent;
};

static mutex calc_score_cuda_contexts_mutex;
static vector< unique_ptr<CalcScoreCudaBatchContext> > calc_score_cuda_contexts;
static vector< unique_ptr<mutex> > calc_score_cuda_context_mutexes;

static bool get_calc_score_cuda_batch_context_for_device(int device,
                                                         CalcScoreCudaBatchContext **contextOut,
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
  if(device >= deviceCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "requested CUDA device index is out of range";
    }
    return false;
  }

  lock_guard<mutex> lock(calc_score_cuda_contexts_mutex);
  if(calc_score_cuda_contexts.size() <= static_cast<size_t>(device))
  {
    calc_score_cuda_contexts.resize(static_cast<size_t>(device) + 1);
    calc_score_cuda_context_mutexes.resize(static_cast<size_t>(device) + 1);
  }
  if(!calc_score_cuda_contexts[static_cast<size_t>(device)])
  {
    calc_score_cuda_contexts[static_cast<size_t>(device)].reset(new CalcScoreCudaBatchContext());
  }
  if(!calc_score_cuda_context_mutexes[static_cast<size_t>(device)])
  {
    calc_score_cuda_context_mutexes[static_cast<size_t>(device)].reset(new mutex());
  }

  *contextOut = calc_score_cuda_contexts[static_cast<size_t>(device)].get();
  *mutexOut = calc_score_cuda_context_mutexes[static_cast<size_t>(device)].get();
  return true;
}

static bool ensure_calc_score_cuda_batch_initialized_locked(CalcScoreCudaBatchContext &context,int device,string *errorOut)
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

  context.initialized = true;
  context.device = device;
  return true;
}

static bool ensure_calc_score_cuda_batch_capacity_locked(CalcScoreCudaBatchContext &context,
                                                        int taskCount,
                                                        int targetLength,
                                                        int permutationCount,
                                                        int pairCount,
                                                        bool requireOrientationScores,
                                                        string *errorOut)
{
  if(taskCount <= context.capacityTasks && targetLength <= context.capacityTargetLength &&
     permutationCount <= context.capacityPermutationCount && pairCount <= context.capacityPairCount &&
     context.targetsDevice != NULL && context.permutationsDevice != NULL && context.scoresDevice != NULL &&
     (!requireOrientationScores || context.orientationScoresDevice != NULL))
  {
    return true;
  }

  const bool needsResize =
    taskCount > context.capacityTasks || targetLength > context.capacityTargetLength ||
    permutationCount > context.capacityPermutationCount || pairCount > context.capacityPairCount ||
    context.targetsDevice == NULL || context.permutationsDevice == NULL || context.scoresDevice == NULL;

  const int newCapTasks = max(context.capacityTasks, taskCount);
  const int newCapTargetLength = max(context.capacityTargetLength, targetLength);
  const int newCapPermutations = max(context.capacityPermutationCount, permutationCount);
  const int newCapPairs = max(context.capacityPairCount, pairCount);

  if(!needsResize)
  {
    int *newOrientationScoresDevice = NULL;
    const size_t orientationScoresBytes =
      static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapPairs) * 2u * sizeof(int);
    cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newOrientationScoresDevice), orientationScoresBytes);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
    context.orientationScoresDevice = newOrientationScoresDevice;
    return true;
  }

  uint8_t *newTargetsDevice = NULL;
  uint16_t *newPermutationsDevice = NULL;
  int *newScoresDevice = NULL;
  int *newOrientationScoresDevice = NULL;

  const size_t targetsBytes = static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapTargetLength) * sizeof(uint8_t);
  const size_t permutationsBytes =
    static_cast<size_t>(newCapPermutations) * static_cast<size_t>(newCapTargetLength) * sizeof(uint16_t);
  const size_t scoresBytes = static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapPairs) * sizeof(int);
  const size_t orientationScoresBytes =
    static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapPairs) * 2u * sizeof(int);

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newTargetsDevice), targetsBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newPermutationsDevice), permutationsBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newTargetsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newScoresDevice), scoresBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newTargetsDevice);
    cudaFree(newPermutationsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(requireOrientationScores)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&newOrientationScoresDevice), orientationScoresBytes);
    if(status != cudaSuccess)
    {
      cudaFree(newTargetsDevice);
      cudaFree(newPermutationsDevice);
      cudaFree(newScoresDevice);
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(status);
      }
      return false;
    }
  }

  if(context.targetsDevice != NULL)
  {
    cudaFree(context.targetsDevice);
  }
  if(context.permutationsDevice != NULL)
  {
    cudaFree(context.permutationsDevice);
  }
  if(context.scoresDevice != NULL)
  {
    cudaFree(context.scoresDevice);
  }
  if(context.orientationScoresDevice != NULL)
  {
    cudaFree(context.orientationScoresDevice);
  }

  context.targetsDevice = newTargetsDevice;
  context.permutationsDevice = newPermutationsDevice;
  context.scoresDevice = newScoresDevice;
  context.orientationScoresDevice = newOrientationScoresDevice;
  context.capacityTasks = newCapTasks;
  context.capacityTargetLength = newCapTargetLength;
  context.capacityPermutationCount = newCapPermutations;
  context.capacityPairCount = newCapPairs;
  return true;
}

bool calc_score_cuda_is_built()
{
  return true;
}

bool calc_score_cuda_init(int device,string *errorOut)
{
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
  if(device >= deviceCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "requested CUDA device index is out of range";
    }
    return false;
  }
  const cudaError_t setStatus = cudaSetDevice(device);
  if(setStatus != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(setStatus);
    }
    return false;
  }
  return true;
}

bool calc_score_cuda_prepare_query(CalcScoreCudaQueryHandle *handle,
                                   const int16_t *profileFwdHost,
                                   const int16_t *profileRevHost,
                                   int segLen,
                                   int queryLength,
                                   string *errorOut)
{
  if(handle == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output handle";
    }
    return false;
  }
  *handle = CalcScoreCudaQueryHandle();
  if(profileFwdHost == NULL || profileRevHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing query profile";
    }
    return false;
  }
  if(segLen <= 0 || queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid query dimensions";
    }
    return false;
  }

  const size_t profileEntries = static_cast<size_t>(7) * static_cast<size_t>(segLen) * static_cast<size_t>(32);
  const size_t profileBytes = profileEntries * sizeof(int16_t);

  int16_t *profileFwdDevice = NULL;
  int16_t *profileRevDevice = NULL;
  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&profileFwdDevice), profileBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&profileRevDevice), profileBytes);
  if(status != cudaSuccess)
  {
    cudaFree(profileFwdDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaMemcpy(profileFwdDevice, profileFwdHost, profileBytes, cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    cudaFree(profileFwdDevice);
    cudaFree(profileRevDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(profileRevDevice, profileRevHost, profileBytes, cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    cudaFree(profileFwdDevice);
    cudaFree(profileRevDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  int device = 0;
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  handle->device = (deviceStatus == cudaSuccess) ? device : -1;
  handle->queryLength = queryLength;
  handle->segLen = segLen;
  handle->profileFwdDevice = reinterpret_cast<uintptr_t>(profileFwdDevice);
  handle->profileRevDevice = reinterpret_cast<uintptr_t>(profileRevDevice);
  return true;
}

void calc_score_cuda_release_query(CalcScoreCudaQueryHandle *handle)
{
  if(handle == NULL)
  {
    return;
  }
  if(handle->device >= 0)
  {
    cudaSetDevice(handle->device);
  }
  if(handle->profileFwdDevice != 0)
  {
    cudaFree(reinterpret_cast<void *>(handle->profileFwdDevice));
  }
  if(handle->profileRevDevice != 0)
  {
    cudaFree(reinterpret_cast<void *>(handle->profileRevDevice));
  }
  *handle = CalcScoreCudaQueryHandle();
}

static bool calc_score_cuda_run_v1_locked(CalcScoreCudaBatchContext &context,
                                          const CalcScoreCudaQueryHandle &handle,
                                          int taskCount,
                                          int targetLength,
                                          int pairCount,
                                          bool collectTelemetry,
                                          double *kernelSecondsOut,
                                          double *syncWaitSecondsOut,
                                          string *errorOut)
{
  if(kernelSecondsOut != NULL)
  {
    *kernelSecondsOut = 0.0;
  }
  if(syncWaitSecondsOut != NULL)
  {
    *syncWaitSecondsOut = 0.0;
  }

  const int blocks = taskCount * pairCount;
  const int threadsPerBlock = 64;
  const size_t sharedBytes = static_cast<size_t>(2) * static_cast<size_t>(3) *
                             static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);

  cudaError_t status = cudaEventRecord(context.startEvent);
  if(status == cudaSuccess)
  {
    calc_score_cuda_kernel<<<blocks, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileFwdDevice),
                                                                     reinterpret_cast<const int16_t *>(handle.profileRevDevice),
                                                                     context.targetsDevice,
                                                                     context.permutationsDevice,
                                                                     taskCount,
                                                                     targetLength,
                                                                     pairCount,
                                                                     handle.segLen,
                                                                     context.scoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context.stopEvent);
  }
  if(status == cudaSuccess)
  {
    const double syncWaitStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
    status = cudaEventSynchronize(context.stopEvent);
    if(collectTelemetry && syncWaitSecondsOut != NULL)
    {
      *syncWaitSecondsOut = calc_score_cuda_now_seconds() - syncWaitStart;
    }
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context.startEvent, context.stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(kernelSecondsOut != NULL)
  {
    *kernelSecondsOut = static_cast<double>(elapsedMs) / 1000.0;
  }
  return true;
}

static bool calc_score_cuda_run_v2_locked(CalcScoreCudaBatchContext &context,
                                          const CalcScoreCudaQueryHandle &handle,
                                          int taskCount,
                                          int targetLength,
                                          int pairCount,
                                          bool collectTelemetry,
                                          double *kernelSecondsOut,
                                          double *syncWaitSecondsOut,
                                          string *errorOut)
{
  if(kernelSecondsOut != NULL)
  {
    *kernelSecondsOut = 0.0;
  }
  if(syncWaitSecondsOut != NULL)
  {
    *syncWaitSecondsOut = 0.0;
  }
  if(context.orientationScoresDevice == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing CUDA v2 orientation score buffer";
    }
    return false;
  }

  const int blocks = taskCount * pairCount * 2;
  const int threadsPerBlock = 32;
  const size_t sharedBytes = static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);

  cudaError_t status = cudaEventRecord(context.startEvent);
  if(status == cudaSuccess)
  {
    calc_score_cuda_kernel_v2<<<blocks, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileFwdDevice),
                                                                        reinterpret_cast<const int16_t *>(handle.profileRevDevice),
                                                                        context.targetsDevice,
                                                                        context.permutationsDevice,
                                                                        taskCount,
                                                                        targetLength,
                                                                        pairCount,
                                                                        handle.segLen,
                                                                        context.orientationScoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context.stopEvent);
  }
  if(status == cudaSuccess)
  {
    const double syncWaitStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
    status = cudaEventSynchronize(context.stopEvent);
    if(collectTelemetry && syncWaitSecondsOut != NULL)
    {
      *syncWaitSecondsOut = calc_score_cuda_now_seconds() - syncWaitStart;
    }
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context.startEvent, context.stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(kernelSecondsOut != NULL)
  {
    *kernelSecondsOut = static_cast<double>(elapsedMs) / 1000.0;
  }
  return true;
}

static bool calc_score_cuda_copy_v1_scores_locked(CalcScoreCudaBatchContext &context,
                                                  size_t scoreCount,
                                                  vector<int> *outPairScores,
                                                  bool collectTelemetry,
                                                  double *scoreD2HSecondsOut,
                                                  string *errorOut)
{
  if(scoreD2HSecondsOut != NULL)
  {
    *scoreD2HSecondsOut = 0.0;
  }
  outPairScores->resize(scoreCount);
  const double scoreD2HStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
  cudaError_t status = cudaMemcpy(outPairScores->data(),
                                  context.scoresDevice,
                                  scoreCount * sizeof(int),
                                  cudaMemcpyDeviceToHost);
  if(collectTelemetry && scoreD2HSecondsOut != NULL)
  {
    *scoreD2HSecondsOut = calc_score_cuda_now_seconds() - scoreD2HStart;
  }
  if(status != cudaSuccess)
  {
    outPairScores->clear();
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  return true;
}

static bool calc_score_cuda_copy_reduce_v2_scores_locked(CalcScoreCudaBatchContext &context,
                                                         size_t scoreCount,
                                                         vector<int> *outPairScores,
                                                         bool collectTelemetry,
                                                         double *scoreD2HSecondsOut,
                                                         double *hostReduceSecondsOut,
                                                         string *errorOut)
{
  if(scoreD2HSecondsOut != NULL)
  {
    *scoreD2HSecondsOut = 0.0;
  }
  if(hostReduceSecondsOut != NULL)
  {
    *hostReduceSecondsOut = 0.0;
  }

  vector<int> orientationScores(scoreCount * 2u);
  const double scoreD2HStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
  cudaError_t status = cudaMemcpy(orientationScores.data(),
                                  context.orientationScoresDevice,
                                  orientationScores.size() * sizeof(int),
                                  cudaMemcpyDeviceToHost);
  if(collectTelemetry && scoreD2HSecondsOut != NULL)
  {
    *scoreD2HSecondsOut = calc_score_cuda_now_seconds() - scoreD2HStart;
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outPairScores->resize(scoreCount);
  const double reduceStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
  for(size_t i = 0; i < scoreCount; ++i)
  {
    const int fwdScore = orientationScores[i * 2u];
    const int revScore = orientationScores[i * 2u + 1u];
    (*outPairScores)[i] = fwdScore > revScore ? fwdScore : revScore;
  }
  if(collectTelemetry && hostReduceSecondsOut != NULL)
  {
    *hostReduceSecondsOut = calc_score_cuda_now_seconds() - reduceStart;
  }
  return true;
}

bool calc_score_cuda_compute_pair_max_scores(const CalcScoreCudaQueryHandle &handle,
                                             const uint8_t *encodedTargetsHost,
                                             int taskCount,
                                             int targetLength,
                                             const uint16_t *permutationsHost,
                                             int permutationCount,
                                             int pairCount,
                                             vector<int> *outPairScores,
                                             CalcScoreCudaBatchResult *batchResult,
                                             string *errorOut,
                                             bool collectTelemetry)
{
  if(outPairScores == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outPairScores->clear();

  if(batchResult != NULL)
  {
    *batchResult = CalcScoreCudaBatchResult();
  }

  if(encodedTargetsHost == NULL || permutationsHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input data";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || permutationCount <= 0 || pairCount <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid batch dimensions";
    }
    return false;
  }
  if(handle.profileFwdDevice == 0 || handle.profileRevDevice == 0 || handle.segLen <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

  const int requiredPermutationCount = pairCount * 2;
  if(requiredPermutationCount > permutationCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "insufficient shuffle permutations for requested pairCount";
    }
    return false;
  }

  int device = handle.device;
  if(device < 0)
  {
    device = 0;
    const cudaError_t deviceStatus = cudaGetDevice(&device);
    if(deviceStatus != cudaSuccess)
    {
      if(errorOut != NULL)
      {
        *errorOut = cuda_error_string(deviceStatus);
      }
      return false;
    }
  }

  CalcScoreCudaBatchContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_calc_score_cuda_batch_context_for_device(device,&context,&contextMutex,errorOut))
  {
    return false;
  }

  const bool pipelineV2Enabled = calc_score_cuda_pipeline_v2_enabled_runtime();
  const bool pipelineV2ShadowEnabled = calc_score_cuda_pipeline_v2_shadow_enabled_runtime();
  const size_t scoreCount = static_cast<size_t>(taskCount) * static_cast<size_t>(pairCount);
  const size_t targetsBytes = static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t permutationsBytes =
    static_cast<size_t>(requiredPermutationCount) * static_cast<size_t>(targetLength) * sizeof(uint16_t);
  const size_t scoresBytes = scoreCount * sizeof(int);
  const size_t orientationScoresBytes = scoreCount * 2u * sizeof(int);

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_calc_score_cuda_batch_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_calc_score_cuda_batch_capacity_locked(*context,
                                                   taskCount,
                                                   targetLength,
                                                   requiredPermutationCount,
                                                   pairCount,
                                                   pipelineV2Enabled,
                                                   errorOut))
  {
    return false;
  }

  double targetH2DSeconds = 0.0;
  double permutationH2DSeconds = 0.0;
  double scoreD2HSeconds = 0.0;
  double syncWaitSeconds = 0.0;
  double kernelSeconds = 0.0;
  double pipelineV2KernelSeconds = 0.0;
  double pipelineV2ScoreD2HSeconds = 0.0;
  double pipelineV2HostReduceSeconds = 0.0;
  bool pipelineV2Used = false;
  bool pipelineV2Fallback = false;
  uint64_t pipelineV2ShadowComparisons = 0;
  uint64_t pipelineV2ShadowMismatches = 0;

  const double targetH2DStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
  cudaError_t status = cudaMemcpy(context->targetsDevice, encodedTargetsHost, targetsBytes, cudaMemcpyHostToDevice);
  if(collectTelemetry)
  {
    targetH2DSeconds = calc_score_cuda_now_seconds() - targetH2DStart;
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  const double permutationH2DStart = collectTelemetry ? calc_score_cuda_now_seconds() : 0.0;
  status = cudaMemcpy(context->permutationsDevice, permutationsHost, permutationsBytes, cudaMemcpyHostToDevice);
  if(collectTelemetry)
  {
    permutationH2DSeconds = calc_score_cuda_now_seconds() - permutationH2DStart;
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  bool computed = false;
  if(pipelineV2Enabled && !pipelineV2ShadowEnabled)
  {
    double v2SyncWaitSeconds = 0.0;
    string v2Error;
    if(calc_score_cuda_run_v2_locked(*context,
                                     handle,
                                     taskCount,
                                     targetLength,
                                     pairCount,
                                     collectTelemetry,
                                     &pipelineV2KernelSeconds,
                                     &v2SyncWaitSeconds,
                                     &v2Error) &&
       calc_score_cuda_copy_reduce_v2_scores_locked(*context,
                                                    scoreCount,
                                                    outPairScores,
                                                    collectTelemetry,
                                                    &pipelineV2ScoreD2HSeconds,
                                                    &pipelineV2HostReduceSeconds,
                                                    &v2Error))
    {
      pipelineV2Used = true;
      kernelSeconds = pipelineV2KernelSeconds;
      scoreD2HSeconds = pipelineV2ScoreD2HSeconds;
      syncWaitSeconds = v2SyncWaitSeconds;
      computed = true;
    }
    else
    {
      pipelineV2Fallback = true;
    }
  }

  if(!computed)
  {
    if(!calc_score_cuda_run_v1_locked(*context,
                                      handle,
                                      taskCount,
                                      targetLength,
                                      pairCount,
                                      collectTelemetry,
                                      &kernelSeconds,
                                      &syncWaitSeconds,
                                      errorOut))
    {
      return false;
    }
    if(!calc_score_cuda_copy_v1_scores_locked(*context,
                                              scoreCount,
                                              outPairScores,
                                              collectTelemetry,
                                              &scoreD2HSeconds,
                                              errorOut))
    {
      return false;
    }
    computed = true;
  }

  if(pipelineV2Enabled && pipelineV2ShadowEnabled)
  {
    vector<int> pipelineV2Scores;
    double shadowSyncWaitSeconds = 0.0;
    string shadowError;
    if(calc_score_cuda_run_v2_locked(*context,
                                     handle,
                                     taskCount,
                                     targetLength,
                                     pairCount,
                                     collectTelemetry,
                                     &pipelineV2KernelSeconds,
                                     &shadowSyncWaitSeconds,
                                     &shadowError) &&
       calc_score_cuda_copy_reduce_v2_scores_locked(*context,
                                                    scoreCount,
                                                    &pipelineV2Scores,
                                                    collectTelemetry,
                                                    &pipelineV2ScoreD2HSeconds,
                                                    &pipelineV2HostReduceSeconds,
                                                    &shadowError))
    {
      (void)shadowSyncWaitSeconds;
      pipelineV2Used = true;
      pipelineV2ShadowComparisons = static_cast<uint64_t>(scoreCount);
      for(size_t i = 0; i < scoreCount; ++i)
      {
        if((*outPairScores)[i] != pipelineV2Scores[i])
        {
          ++pipelineV2ShadowMismatches;
        }
      }

      if(pipelineV2ShadowMismatches != 0 && calc_score_cuda_validate_enabled_runtime())
      {
        fprintf(stderr,
                "CUDA calc_score v2 shadow mismatch comparisons=%llu mismatches=%llu\n",
                static_cast<unsigned long long>(pipelineV2ShadowComparisons),
                static_cast<unsigned long long>(pipelineV2ShadowMismatches));
        abort();
      }
    }
    else
    {
      pipelineV2Fallback = true;
    }
  }

  if(batchResult != NULL)
  {
    batchResult->gpuSeconds = kernelSeconds;
    batchResult->targetH2DSeconds = targetH2DSeconds;
    batchResult->permutationH2DSeconds = permutationH2DSeconds;
    batchResult->kernelSeconds = kernelSeconds;
    batchResult->scoreD2HSeconds = scoreD2HSeconds;
    batchResult->syncWaitSeconds = syncWaitSeconds;
    batchResult->pipelineV2Enabled = pipelineV2Enabled;
    batchResult->pipelineV2ShadowEnabled = pipelineV2ShadowEnabled;
    batchResult->pipelineV2Used = pipelineV2Used;
    batchResult->pipelineV2Fallback = pipelineV2Fallback;
    batchResult->pipelineV2ShadowComparisons = pipelineV2ShadowComparisons;
    batchResult->pipelineV2ShadowMismatches = pipelineV2ShadowMismatches;
    batchResult->pipelineV2KernelSeconds = pipelineV2KernelSeconds;
    batchResult->pipelineV2ScoreD2HSeconds = pipelineV2ScoreD2HSeconds;
    batchResult->pipelineV2HostReduceSeconds = pipelineV2HostReduceSeconds;
    batchResult->targetBytesH2D = static_cast<uint64_t>(targetsBytes);
    batchResult->permutationBytesH2D = static_cast<uint64_t>(permutationsBytes);
    batchResult->scoreBytesD2H = static_cast<uint64_t>(pipelineV2Enabled && !pipelineV2ShadowEnabled && pipelineV2Used ?
                                                        orientationScoresBytes :
                                                        scoresBytes);
    batchResult->usedCuda = true;
  }
  return true;
}
