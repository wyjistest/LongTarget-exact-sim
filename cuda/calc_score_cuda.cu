#include "calc_score_cuda.h"

#include <cuda_runtime.h>

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

static inline string cuda_error_string(cudaError_t error)
{
  const char *message = cudaGetErrorString(error);
  if(message == NULL)
  {
    return "unknown CUDA error";
  }
  return string(message);
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
                                                        string *errorOut)
{
  if(taskCount <= context.capacityTasks && targetLength <= context.capacityTargetLength &&
     permutationCount <= context.capacityPermutationCount && pairCount <= context.capacityPairCount &&
     context.targetsDevice != NULL && context.permutationsDevice != NULL && context.scoresDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityTasks, taskCount);
  const int newCapTargetLength = max(context.capacityTargetLength, targetLength);
  const int newCapPermutations = max(context.capacityPermutationCount, permutationCount);
  const int newCapPairs = max(context.capacityPairCount, pairCount);

  uint8_t *newTargetsDevice = NULL;
  uint16_t *newPermutationsDevice = NULL;
  int *newScoresDevice = NULL;

  const size_t targetsBytes = static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapTargetLength) * sizeof(uint8_t);
  const size_t permutationsBytes =
    static_cast<size_t>(newCapPermutations) * static_cast<size_t>(newCapTargetLength) * sizeof(uint16_t);
  const size_t scoresBytes = static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapPairs) * sizeof(int);

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

  context.targetsDevice = newTargetsDevice;
  context.permutationsDevice = newPermutationsDevice;
  context.scoresDevice = newScoresDevice;
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

bool calc_score_cuda_compute_pair_max_scores(const CalcScoreCudaQueryHandle &handle,
                                             const uint8_t *encodedTargetsHost,
                                             int taskCount,
                                             int targetLength,
                                             const uint16_t *permutationsHost,
                                             int permutationCount,
                                             int pairCount,
                                             vector<int> *outPairScores,
                                             CalcScoreCudaBatchResult *batchResult,
                                             string *errorOut)
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

  const size_t targetsBytes = static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t permutationsBytes =
    static_cast<size_t>(requiredPermutationCount) * static_cast<size_t>(targetLength) * sizeof(uint16_t);
  const size_t scoresBytes = static_cast<size_t>(taskCount) * static_cast<size_t>(pairCount) * sizeof(int);

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_calc_score_cuda_batch_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_calc_score_cuda_batch_capacity_locked(*context,taskCount,targetLength,requiredPermutationCount,pairCount,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->targetsDevice, encodedTargetsHost, targetsBytes, cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(context->permutationsDevice, permutationsHost, permutationsBytes, cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int blocks = taskCount * pairCount;
  const int threadsPerBlock = 64;
  const size_t sharedBytes = static_cast<size_t>(2) * static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u *
                             sizeof(int16_t);

  status = cudaEventRecord(context->startEvent);
  if(status == cudaSuccess)
  {
    calc_score_cuda_kernel<<<blocks, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileFwdDevice),
                                                                     reinterpret_cast<const int16_t *>(handle.profileRevDevice),
                                                                     context->targetsDevice,
                                                                     context->permutationsDevice,
                                                                     taskCount,
                                                                     targetLength,
                                                                     pairCount,
                                                                     handle.segLen,
                                                                     context->scoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->stopEvent);
  }
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

  outPairScores->resize(static_cast<size_t>(taskCount) * static_cast<size_t>(pairCount));
  status = cudaMemcpy(outPairScores->data(), context->scoresDevice, scoresBytes, cudaMemcpyDeviceToHost);

  if(status != cudaSuccess)
  {
    outPairScores->clear();
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(batchResult != NULL)
  {
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->usedCuda = true;
  }
  return true;
}
