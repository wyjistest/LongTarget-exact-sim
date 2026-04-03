#include "prealign_cuda.h"

#include <cuda_runtime.h>

#include <memory>
#include <mutex>

using namespace std;

namespace
{

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

static __device__ __forceinline__ bool prealign_heap_less(int scoreA,int posA,int scoreB,int posB)
{
  return (scoreA < scoreB) || (scoreA == scoreB && posA > posB);
}

__global__ void prealign_cuda_topk_kernel(const int16_t *profile,
                                          const uint8_t *encodedTargets,
                                          int taskCount,
                                          int targetLength,
                                          int segLen,
                                          int topK,
                                          PreAlignCudaPeak *outPeaks)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount)
  {
    return;
  }
  if(lane >= 32)
  {
    return;
  }

  extern __shared__ unsigned char smem[];
  int16_t *E = reinterpret_cast<int16_t *>(smem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  size_t offsetBytes = static_cast<size_t>(3) * static_cast<size_t>(segLen) * 32u * sizeof(int16_t);
  offsetBytes = (offsetBytes + sizeof(int) - 1) & ~(static_cast<size_t>(sizeof(int) - 1));
  int *topScores = reinterpret_cast<int *>(smem + offsetBytes);
  int *topPos = topScores + topK;

  // Init DP state.
  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  for(int k = lane; k < topK; k += 32)
  {
    topScores[k] = -1;
    topPos[k] = -1;
  }
  __syncwarp();

  const uint8_t *taskTarget = encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

  const int gapOpen = 16;
  const int gapExtend = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = taskTarget[targetIndex];
    const int16_t *profileRow = profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

    int colLaneMax = 0;

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
      colLaneMax = cuda_max_int(colLaneMax, vH);

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
      vHStore = cuda_max_int(vHStore, vF);
      HStore[segIndex * 32 + lane] = static_cast<int16_t>(vHStore);
      colLaneMax = cuda_max_int(colLaneMax, vHStore);

      const int vHGapOpen = cuda_clamp_nonnegative(vHStore - gapOpen);
      vF = cuda_clamp_nonnegative(vF - gapExtend);
      const int shouldContinue = vF > vHGapOpen ? 1 : 0;
      if(__ballot_sync(0xffffffffu, shouldContinue) == 0)
      {
        break;
      }

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

    // Reduce column max across lanes (lane 0 receives the max).
    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    if(lane == 0)
    {
      if(prealign_heap_less(topScores[0], topPos[0], colMax, targetIndex))
      {
        topScores[0] = colMax;
        topPos[0] = targetIndex;

        // Sift-down.
        int idx = 0;
        while(true)
        {
          const int left = idx * 2 + 1;
          if(left >= topK)
          {
            break;
          }
          int smallest = left;
          const int right = left + 1;
          if(right < topK && prealign_heap_less(topScores[right], topPos[right], topScores[left], topPos[left]))
          {
            smallest = right;
          }
          if(prealign_heap_less(topScores[smallest], topPos[smallest], topScores[idx], topPos[idx]))
          {
            const int tmpScore = topScores[idx];
            const int tmpPos = topPos[idx];
            topScores[idx] = topScores[smallest];
            topPos[idx] = topPos[smallest];
            topScores[smallest] = tmpScore;
            topPos[smallest] = tmpPos;
            idx = smallest;
            continue;
          }
          break;
        }
      }
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    // Sort peaks by (score desc, position asc).
    for(int i = 0; i < topK; ++i)
    {
      int best = i;
      for(int j = i + 1; j < topK; ++j)
      {
        const int scoreA = topScores[best];
        const int scoreB = topScores[j];
        if(scoreB > scoreA || (scoreB == scoreA && topPos[j] < topPos[best]))
        {
          best = j;
        }
      }
      if(best != i)
      {
        const int tmpScore = topScores[i];
        const int tmpPos = topPos[i];
        topScores[i] = topScores[best];
        topPos[i] = topPos[best];
        topScores[best] = tmpScore;
        topPos[best] = tmpPos;
      }
    }

    PreAlignCudaPeak *row = outPeaks + static_cast<size_t>(taskIndex) * static_cast<size_t>(topK);
    for(int k = 0; k < topK; ++k)
    {
      PreAlignCudaPeak p;
      p.score = topScores[k];
      p.position = topPos[k];
      row[k] = p;
    }
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

struct PreAlignCudaContext
{
  PreAlignCudaContext():
    initialized(false),
    device(0),
    capacityTasks(0),
    capacityTargetLength(0),
    capacityTopK(0),
    targetsDevice(NULL),
    peaksDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL)
  {
  }

  bool initialized;
  int device;
  int capacityTasks;
  int capacityTargetLength;
  int capacityTopK;

  uint8_t *targetsDevice;
  PreAlignCudaPeak *peaksDevice;

  cudaEvent_t startEvent;
  cudaEvent_t stopEvent;
};

static mutex prealign_cuda_contexts_mutex;
static vector< unique_ptr<PreAlignCudaContext> > prealign_cuda_contexts;
static vector< unique_ptr<mutex> > prealign_cuda_context_mutexes;

static bool get_prealign_cuda_context_for_device(int device,
                                                 PreAlignCudaContext **contextOut,
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

  lock_guard<mutex> lock(prealign_cuda_contexts_mutex);
  if(prealign_cuda_contexts.size() <= static_cast<size_t>(device))
  {
    prealign_cuda_contexts.resize(static_cast<size_t>(device) + 1);
    prealign_cuda_context_mutexes.resize(static_cast<size_t>(device) + 1);
  }
  if(!prealign_cuda_contexts[static_cast<size_t>(device)])
  {
    prealign_cuda_contexts[static_cast<size_t>(device)].reset(new PreAlignCudaContext());
  }
  if(!prealign_cuda_context_mutexes[static_cast<size_t>(device)])
  {
    prealign_cuda_context_mutexes[static_cast<size_t>(device)].reset(new mutex());
  }

  *contextOut = prealign_cuda_contexts[static_cast<size_t>(device)].get();
  *mutexOut = prealign_cuda_context_mutexes[static_cast<size_t>(device)].get();
  return true;
}

static bool ensure_prealign_cuda_initialized_locked(PreAlignCudaContext &context,int device,string *errorOut)
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

static bool ensure_prealign_cuda_capacity_locked(PreAlignCudaContext &context,int taskCount,int targetLength,int topK,string *errorOut)
{
  if(taskCount <= context.capacityTasks && targetLength <= context.capacityTargetLength &&
     topK <= context.capacityTopK && context.targetsDevice != NULL &&
     context.peaksDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityTasks, taskCount);
  const int newCapTargetLength = max(context.capacityTargetLength, targetLength);
  const int newCapTopK = max(context.capacityTopK, topK);

  uint8_t *newTargetsDevice = NULL;
  PreAlignCudaPeak *newPeaksDevice = NULL;

  const size_t targetsBytes =
    static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapTargetLength) * sizeof(uint8_t);
  const size_t peaksBytes = static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapTopK) * sizeof(PreAlignCudaPeak);

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newTargetsDevice), targetsBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newPeaksDevice), peaksBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newTargetsDevice);
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
  if(context.peaksDevice != NULL)
  {
    cudaFree(context.peaksDevice);
  }

  context.targetsDevice = newTargetsDevice;
  context.peaksDevice = newPeaksDevice;
  context.capacityTasks = newCapTasks;
  context.capacityTargetLength = newCapTargetLength;
  context.capacityTopK = newCapTopK;
  return true;
}

} // namespace

bool prealign_cuda_is_built()
{
  return true;
}

bool prealign_cuda_init(int device,string *errorOut)
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

bool prealign_cuda_prepare_query(PreAlignCudaQueryHandle *handle,
                                 const int16_t *profileHost,
                                 int alphabetSize,
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
  *handle = PreAlignCudaQueryHandle();

  if(profileHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing profile";
    }
    return false;
  }
  if(alphabetSize <= 0 || segLen <= 0 || queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid query dimensions";
    }
    return false;
  }
  if(alphabetSize > 256)
  {
    if(errorOut != NULL)
    {
      *errorOut = "alphabet size too large";
    }
    return false;
  }

  int device = 0;
  cudaError_t status = cudaGetDevice(&device);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const size_t profileBytes =
    static_cast<size_t>(alphabetSize) * static_cast<size_t>(segLen) * 32u * sizeof(int16_t);
  int16_t *profileDevice = NULL;
  status = cudaMalloc(reinterpret_cast<void **>(&profileDevice), profileBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMemcpy(profileDevice, profileHost, profileBytes, cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    cudaFree(profileDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  handle->device = device;
  handle->queryLength = queryLength;
  handle->segLen = segLen;
  handle->alphabetSize = alphabetSize;
  handle->profileDevice = reinterpret_cast<uintptr_t>(profileDevice);
  return true;
}

void prealign_cuda_release_query(PreAlignCudaQueryHandle *handle)
{
  if(handle == NULL)
  {
    return;
  }
  if(handle->profileDevice != 0)
  {
    if(handle->device >= 0)
    {
      cudaSetDevice(handle->device);
    }
    cudaFree(reinterpret_cast<void *>(handle->profileDevice));
  }
  *handle = PreAlignCudaQueryHandle();
}

bool prealign_cuda_find_topk_column_maxima(const PreAlignCudaQueryHandle &handle,
                                           const uint8_t *encodedTargetsHost,
                                           int taskCount,
                                           int targetLength,
                                           int topK,
                                           vector<PreAlignCudaPeak> *outPeaks,
                                           PreAlignCudaBatchResult *batchResult,
                                           string *errorOut)
{
  if(outPeaks == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outPeaks->clear();
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }

  if(encodedTargetsHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input targets";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid target dimensions";
    }
    return false;
  }
  if(topK <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid topK";
    }
    return false;
  }
  const int maxTopK = 256;
  if(topK > maxTopK)
  {
    if(errorOut != NULL)
    {
      *errorOut = "topK too large";
    }
    return false;
  }
  if(handle.profileDevice == 0 || handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

  const size_t targetsBytes = static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t peaksBytes = static_cast<size_t>(taskCount) * static_cast<size_t>(topK) * sizeof(PreAlignCudaPeak);

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context,handle.device,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,topK,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->targetsDevice,
                                  encodedTargetsHost,
                                  targetsBytes,
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int blocks = taskCount;
  const int threadsPerBlock = 32;
  size_t sharedBytes = static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
  sharedBytes = (sharedBytes + sizeof(int) - 1) & ~(static_cast<size_t>(sizeof(int) - 1));
  sharedBytes += static_cast<size_t>(2) * static_cast<size_t>(topK) * sizeof(int);

  status = cudaEventRecord(context->startEvent);
  if(status == cudaSuccess)
  {
    prealign_cuda_topk_kernel<<<blocks, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                        context->targetsDevice,
                                                                        taskCount,
                                                                        targetLength,
                                                                        handle.segLen,
                                                                        topK,
                                                                        context->peaksDevice);
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

  vector<PreAlignCudaPeak> peaks(static_cast<size_t>(taskCount) * static_cast<size_t>(topK));
  status = cudaMemcpy(peaks.data(), context->peaksDevice, peaksBytes, cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outPeaks->swap(peaks);
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
  }
  return true;
}
