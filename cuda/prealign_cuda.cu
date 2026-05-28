#include "prealign_cuda.h"

#include <cuda_runtime.h>

#include <chrono>
#include <memory>
#include <mutex>

using namespace std;
using Clock = std::chrono::steady_clock;

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

__global__ void prealign_cuda_forward_score_end_kernel(const int8_t *query,
                                                       int queryLength,
                                                       const int8_t *ref,
                                                       int refLength,
                                                       const int8_t *scoreMatrix,
                                                       int scoreMatrixSize,
                                                       int gapOpen,
                                                       int gapExtend,
                                                       PreAlignCudaForwardScoreEndResult *outResult)
{
  if(threadIdx.x != 0 || blockIdx.x != 0)
  {
    return;
  }

  extern __shared__ int forwardScoreShared[];
  int *prev = forwardScoreShared;
  int *curr = prev + queryLength + 1;
  int *gapRef = curr + queryLength + 1;

  for(int j = 0; j <= queryLength; ++j)
  {
    prev[j] = 0;
    curr[j] = 0;
    gapRef[j] = 0;
  }

  int bestScore = 0;
  int bestRefEnd = -1;
  int bestReadEnd = queryLength > 0 ? queryLength - 1 : -1;

  for(int i = 1; i <= refLength; ++i)
  {
    int gapQuery = 0;
    curr[0] = 0;
    const int refBase = static_cast<int>(ref[i - 1]);

    for(int j = 1; j <= queryLength; ++j)
    {
      const int queryBase = static_cast<int>(query[j - 1]);
      int subst = -32768;
      if(refBase >= 0 && refBase < scoreMatrixSize && queryBase >= 0 && queryBase < scoreMatrixSize)
      {
        subst = static_cast<int>(scoreMatrix[refBase * scoreMatrixSize + queryBase]);
      }

      int diag = prev[j - 1] + subst;
      int up = gapRef[j] - gapExtend;
      const int upOpen = prev[j] - gapOpen;
      if(upOpen > up)
      {
        up = upOpen;
      }
      if(up < 0)
      {
        up = 0;
      }
      gapRef[j] = up;

      int left = gapQuery - gapExtend;
      const int leftOpen = curr[j - 1] - gapOpen;
      if(leftOpen > left)
      {
        left = leftOpen;
      }
      if(left < 0)
      {
        left = 0;
      }
      gapQuery = left;

      int value = diag;
      if(up > value)
      {
        value = up;
      }
      if(left > value)
      {
        value = left;
      }
      if(value < 0)
      {
        value = 0;
      }
      curr[j] = value;

      if(value > bestScore)
      {
        bestScore = value;
        bestRefEnd = i - 1;
        bestReadEnd = j - 1;
      }
    }

    int *tmp = prev;
    prev = curr;
    curr = tmp;
  }

  outResult->score = bestScore;
  outResult->refEnd = bestRefEnd;
  outResult->readEnd = bestReadEnd;
}

__global__ void prealign_cuda_forward_score_end_batch_kernel(const int8_t *queries,
                                                             const int *queryOffsets,
                                                             const int *queryLengths,
                                                             const int8_t *refs,
                                                             const int *refOffsets,
                                                             const int *refLengths,
                                                             int requestCount,
                                                             const int8_t *scoreMatrix,
                                                             int scoreMatrixSize,
                                                             int gapOpen,
                                                             int gapExtend,
                                                             int maxQueryLength,
                                                             PreAlignCudaForwardScoreEndResult *outResults)
{
  if(threadIdx.x != 0)
  {
    return;
  }
  const int requestIndex = static_cast<int>(blockIdx.x);
  if(requestIndex >= requestCount)
  {
    return;
  }

  extern __shared__ int forwardScoreBatchShared[];
  int *prev = forwardScoreBatchShared;
  int *curr = prev + maxQueryLength + 1;
  int *gapRef = curr + maxQueryLength + 1;

  const int queryLength = queryLengths[requestIndex];
  const int refLength = refLengths[requestIndex];
  const int queryOffset = queryOffsets[requestIndex];
  const int refOffset = refOffsets[requestIndex];
  const int8_t *query = queries + queryOffset;
  const int8_t *ref = refs + refOffset;

  for(int j = 0; j <= queryLength; ++j)
  {
    prev[j] = 0;
    curr[j] = 0;
    gapRef[j] = 0;
  }

  int bestScore = 0;
  int bestRefEnd = -1;
  int bestReadEnd = queryLength > 0 ? queryLength - 1 : -1;

  for(int i = 1; i <= refLength; ++i)
  {
    int gapQuery = 0;
    curr[0] = 0;
    const int refBase = static_cast<int>(ref[i - 1]);

    for(int j = 1; j <= queryLength; ++j)
    {
      const int queryBase = static_cast<int>(query[j - 1]);
      int subst = -32768;
      if(refBase >= 0 && refBase < scoreMatrixSize && queryBase >= 0 && queryBase < scoreMatrixSize)
      {
        subst = static_cast<int>(scoreMatrix[refBase * scoreMatrixSize + queryBase]);
      }

      int diag = prev[j - 1] + subst;
      int up = gapRef[j] - gapExtend;
      const int upOpen = prev[j] - gapOpen;
      if(upOpen > up)
      {
        up = upOpen;
      }
      if(up < 0)
      {
        up = 0;
      }
      gapRef[j] = up;

      int left = gapQuery - gapExtend;
      const int leftOpen = curr[j - 1] - gapOpen;
      if(leftOpen > left)
      {
        left = leftOpen;
      }
      if(left < 0)
      {
        left = 0;
      }
      gapQuery = left;

      int value = diag;
      if(up > value)
      {
        value = up;
      }
      if(left > value)
      {
        value = left;
      }
      if(value < 0)
      {
        value = 0;
      }
      curr[j] = value;

      if(value > bestScore)
      {
        bestScore = value;
        bestRefEnd = i - 1;
        bestReadEnd = j - 1;
      }
    }

    int *tmp = prev;
    prev = curr;
    curr = tmp;
  }

  outResults[requestIndex].score = bestScore;
  outResults[requestIndex].refEnd = bestRefEnd;
  outResults[requestIndex].readEnd = bestReadEnd;
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

static inline double elapsed_seconds(Clock::time_point start,Clock::time_point end)
{
  return std::chrono::duration<double>(end - start).count();
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
  const Clock::time_point totalStart = Clock::now();

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

  const Clock::time_point h2dStart = Clock::now();
  cudaError_t status = cudaMemcpy(context->targetsDevice,
                                  encodedTargetsHost,
                                  targetsBytes,
                                  cudaMemcpyHostToDevice);
  const Clock::time_point h2dEnd = Clock::now();
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
  int maxSharedMemoryPerBlock = 0;
  status = cudaDeviceGetAttribute(&maxSharedMemoryPerBlock,
                                  cudaDevAttrMaxSharedMemoryPerBlock,
                                  handle.device);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(batchResult != NULL)
  {
    batchResult->dynamicSharedMemoryRequired = sharedBytes;
    batchResult->dynamicSharedMemoryLimit = maxSharedMemoryPerBlock > 0 ?
      static_cast<size_t>(maxSharedMemoryPerBlock) : 0;
    batchResult->deviceSharedMemoryLimit = batchResult->dynamicSharedMemoryLimit;
    batchResult->blockDim = threadsPerBlock;
    batchResult->resourceFitSupported =
      maxSharedMemoryPerBlock <= 0 || sharedBytes <= static_cast<size_t>(maxSharedMemoryPerBlock);
  }
  if(maxSharedMemoryPerBlock > 0 &&
     sharedBytes > static_cast<size_t>(maxSharedMemoryPerBlock))
  {
    if(errorOut != NULL)
    {
      *errorOut = "preAlign CUDA shared memory requirement exceeds device block limit";
    }
    return false;
  }

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
  const Clock::time_point d2hStart = Clock::now();
  status = cudaMemcpy(peaks.data(), context->peaksDevice, peaksBytes, cudaMemcpyDeviceToHost);
  const Clock::time_point d2hEnd = Clock::now();
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
    batchResult->kernelSeconds = batchResult->gpuSeconds;
    batchResult->h2dSeconds = elapsed_seconds(h2dStart,h2dEnd);
    batchResult->d2hSeconds = elapsed_seconds(d2hStart,d2hEnd);
    batchResult->totalSeconds = elapsed_seconds(totalStart,Clock::now());
  }
  return true;
}

bool prealign_cuda_forward_score_end(int device,
                                     const int8_t *queryHost,
                                     int queryLength,
                                     const int8_t *refHost,
                                     int refLength,
                                     const int8_t *scoreMatrixHost,
                                     int scoreMatrixSize,
                                     uint8_t gapOpen,
                                     uint8_t gapExtend,
                                     PreAlignCudaForwardScoreEndResult *outResult,
                                     PreAlignCudaBatchResult *batchResult,
                                     string *errorOut)
{
  if(outResult != NULL)
  {
    *outResult = PreAlignCudaForwardScoreEndResult();
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(queryHost == NULL || refHost == NULL || scoreMatrixHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing forward score input";
    }
    return false;
  }
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing forward score output";
    }
    return false;
  }
  if(queryLength <= 0 || refLength <= 0 || scoreMatrixSize <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid forward score dimensions";
    }
    return false;
  }
  const int maxShadowQueryLength = 8192;
  if(queryLength > maxShadowQueryLength)
  {
    if(errorOut != NULL)
    {
      *errorOut = "query too long for forward score shadow";
    }
    return false;
  }

  int deviceCount = 0;
  cudaError_t status = cudaGetDeviceCount(&deviceCount);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
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

  status = cudaSetDevice(device);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const Clock::time_point totalStart = Clock::now();
  const size_t queryBytes = static_cast<size_t>(queryLength) * sizeof(int8_t);
  const size_t refBytes = static_cast<size_t>(refLength) * sizeof(int8_t);
  const size_t matrixBytes =
    static_cast<size_t>(scoreMatrixSize) * static_cast<size_t>(scoreMatrixSize) * sizeof(int8_t);
  int8_t *queryDevice = NULL;
  int8_t *refDevice = NULL;
  int8_t *matrixDevice = NULL;
  PreAlignCudaForwardScoreEndResult *resultDevice = NULL;
  cudaEvent_t startEvent = NULL;
  cudaEvent_t stopEvent = NULL;

  status = cudaMalloc(reinterpret_cast<void **>(&queryDevice), queryBytes);
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&refDevice), refBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&matrixDevice), matrixBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&resultDevice), sizeof(PreAlignCudaForwardScoreEndResult));
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&startEvent);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(queryDevice != NULL) cudaFree(queryDevice);
    if(refDevice != NULL) cudaFree(refDevice);
    if(matrixDevice != NULL) cudaFree(matrixDevice);
    if(resultDevice != NULL) cudaFree(resultDevice);
    if(startEvent != NULL) cudaEventDestroy(startEvent);
    if(stopEvent != NULL) cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const Clock::time_point h2dStart = Clock::now();
  status = cudaMemcpy(queryDevice, queryHost, queryBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(refDevice, refHost, refBytes, cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(matrixDevice, scoreMatrixHost, matrixBytes, cudaMemcpyHostToDevice);
  }
  const Clock::time_point h2dEnd = Clock::now();
  if(status != cudaSuccess)
  {
    cudaFree(queryDevice);
    cudaFree(refDevice);
    cudaFree(matrixDevice);
    cudaFree(resultDevice);
    cudaEventDestroy(startEvent);
    cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const size_t sharedBytes = static_cast<size_t>(3) * static_cast<size_t>(queryLength + 1) * sizeof(int);
  status = cudaEventRecord(startEvent);
  if(status == cudaSuccess)
  {
    prealign_cuda_forward_score_end_kernel<<<1, 1, sharedBytes>>>(queryDevice,
                                                                  queryLength,
                                                                  refDevice,
                                                                  refLength,
                                                                  matrixDevice,
                                                                  scoreMatrixSize,
                                                                  static_cast<int>(gapOpen),
                                                                  static_cast<int>(gapExtend),
                                                                  resultDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(stopEvent);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(stopEvent);
  }
  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, startEvent, stopEvent);
  }
  if(status != cudaSuccess)
  {
    cudaFree(queryDevice);
    cudaFree(refDevice);
    cudaFree(matrixDevice);
    cudaFree(resultDevice);
    cudaEventDestroy(startEvent);
    cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const Clock::time_point d2hStart = Clock::now();
  status = cudaMemcpy(outResult, resultDevice, sizeof(PreAlignCudaForwardScoreEndResult), cudaMemcpyDeviceToHost);
  const Clock::time_point d2hEnd = Clock::now();

  cudaFree(queryDevice);
  cudaFree(refDevice);
  cudaFree(matrixDevice);
  cudaFree(resultDevice);
  cudaEventDestroy(startEvent);
  cudaEventDestroy(stopEvent);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->kernelSeconds = batchResult->gpuSeconds;
    batchResult->h2dSeconds = elapsed_seconds(h2dStart,h2dEnd);
    batchResult->d2hSeconds = elapsed_seconds(d2hStart,d2hEnd);
    batchResult->totalSeconds = elapsed_seconds(totalStart,Clock::now());
  }
  return true;
}

bool prealign_cuda_forward_score_end_batch(int device,
                                           const int8_t *queriesHost,
                                           const int *queryOffsetsHost,
                                           const int *queryLengthsHost,
                                           const int8_t *refsHost,
                                           const int *refOffsetsHost,
                                           const int *refLengthsHost,
                                           int requestCount,
                                           const int8_t *scoreMatrixHost,
                                           int scoreMatrixSize,
                                           uint8_t gapOpen,
                                           uint8_t gapExtend,
                                           vector<PreAlignCudaForwardScoreEndResult> *outResults,
                                           PreAlignCudaBatchResult *batchResult,
                                           string *errorOut)
{
  if(outResults != NULL)
  {
    outResults->clear();
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(outResults == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batch forward score output";
    }
    return false;
  }
  if(queriesHost == NULL || queryOffsetsHost == NULL || queryLengthsHost == NULL ||
     refsHost == NULL || refOffsetsHost == NULL || refLengthsHost == NULL ||
     scoreMatrixHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing batch forward score input";
    }
    return false;
  }
  if(requestCount <= 0 || scoreMatrixSize <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid batch forward score dimensions";
    }
    return false;
  }

  int totalQueryLength = 0;
  int totalRefLength = 0;
  int maxQueryLength = 0;
  for(int i = 0; i < requestCount; ++i)
  {
    if(queryLengthsHost[i] <= 0 || refLengthsHost[i] <= 0 ||
       queryOffsetsHost[i] < 0 || refOffsetsHost[i] < 0)
    {
      if(errorOut != NULL)
      {
        *errorOut = "invalid batch request dimensions";
      }
      return false;
    }
    totalQueryLength = max(totalQueryLength, queryOffsetsHost[i] + queryLengthsHost[i]);
    totalRefLength = max(totalRefLength, refOffsetsHost[i] + refLengthsHost[i]);
    maxQueryLength = max(maxQueryLength, queryLengthsHost[i]);
  }

  const int maxShadowQueryLength = 8192;
  if(maxQueryLength > maxShadowQueryLength)
  {
    if(errorOut != NULL)
    {
      *errorOut = "query too long for batch forward score shadow";
    }
    return false;
  }

  int deviceCount = 0;
  cudaError_t status = cudaGetDeviceCount(&deviceCount);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
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

  status = cudaSetDevice(device);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const Clock::time_point totalStart = Clock::now();
  const size_t queriesBytes = static_cast<size_t>(totalQueryLength) * sizeof(int8_t);
  const size_t refsBytes = static_cast<size_t>(totalRefLength) * sizeof(int8_t);
  const size_t offsetsBytes = static_cast<size_t>(requestCount) * sizeof(int);
  const size_t matrixBytes =
    static_cast<size_t>(scoreMatrixSize) * static_cast<size_t>(scoreMatrixSize) * sizeof(int8_t);
  const size_t resultsBytes =
    static_cast<size_t>(requestCount) * sizeof(PreAlignCudaForwardScoreEndResult);

  int8_t *queriesDevice = NULL;
  int8_t *refsDevice = NULL;
  int8_t *matrixDevice = NULL;
  int *queryOffsetsDevice = NULL;
  int *queryLengthsDevice = NULL;
  int *refOffsetsDevice = NULL;
  int *refLengthsDevice = NULL;
  PreAlignCudaForwardScoreEndResult *resultsDevice = NULL;
  cudaEvent_t startEvent = NULL;
  cudaEvent_t stopEvent = NULL;

  status = cudaMalloc(reinterpret_cast<void **>(&queriesDevice), queriesBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&refsDevice), refsBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&matrixDevice), matrixBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&queryOffsetsDevice), offsetsBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&queryLengthsDevice), offsetsBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&refOffsetsDevice), offsetsBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&refLengthsDevice), offsetsBytes);
  if(status == cudaSuccess) status = cudaMalloc(reinterpret_cast<void **>(&resultsDevice), resultsBytes);
  if(status == cudaSuccess) status = cudaEventCreate(&startEvent);
  if(status == cudaSuccess) status = cudaEventCreate(&stopEvent);
  if(status != cudaSuccess)
  {
    if(queriesDevice != NULL) cudaFree(queriesDevice);
    if(refsDevice != NULL) cudaFree(refsDevice);
    if(matrixDevice != NULL) cudaFree(matrixDevice);
    if(queryOffsetsDevice != NULL) cudaFree(queryOffsetsDevice);
    if(queryLengthsDevice != NULL) cudaFree(queryLengthsDevice);
    if(refOffsetsDevice != NULL) cudaFree(refOffsetsDevice);
    if(refLengthsDevice != NULL) cudaFree(refLengthsDevice);
    if(resultsDevice != NULL) cudaFree(resultsDevice);
    if(startEvent != NULL) cudaEventDestroy(startEvent);
    if(stopEvent != NULL) cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const Clock::time_point h2dStart = Clock::now();
  status = cudaMemcpy(queriesDevice, queriesHost, queriesBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(refsDevice, refsHost, refsBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(matrixDevice, scoreMatrixHost, matrixBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(queryOffsetsDevice, queryOffsetsHost, offsetsBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(queryLengthsDevice, queryLengthsHost, offsetsBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(refOffsetsDevice, refOffsetsHost, offsetsBytes, cudaMemcpyHostToDevice);
  if(status == cudaSuccess) status = cudaMemcpy(refLengthsDevice, refLengthsHost, offsetsBytes, cudaMemcpyHostToDevice);
  const Clock::time_point h2dEnd = Clock::now();
  if(status != cudaSuccess)
  {
    cudaFree(queriesDevice);
    cudaFree(refsDevice);
    cudaFree(matrixDevice);
    cudaFree(queryOffsetsDevice);
    cudaFree(queryLengthsDevice);
    cudaFree(refOffsetsDevice);
    cudaFree(refLengthsDevice);
    cudaFree(resultsDevice);
    cudaEventDestroy(startEvent);
    cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const size_t sharedBytes = static_cast<size_t>(3) * static_cast<size_t>(maxQueryLength + 1) * sizeof(int);
  status = cudaEventRecord(startEvent);
  if(status == cudaSuccess)
  {
    prealign_cuda_forward_score_end_batch_kernel<<<requestCount, 1, sharedBytes>>>(queriesDevice,
                                                                                  queryOffsetsDevice,
                                                                                  queryLengthsDevice,
                                                                                  refsDevice,
                                                                                  refOffsetsDevice,
                                                                                  refLengthsDevice,
                                                                                  requestCount,
                                                                                  matrixDevice,
                                                                                  scoreMatrixSize,
                                                                                  static_cast<int>(gapOpen),
                                                                                  static_cast<int>(gapExtend),
                                                                                  maxQueryLength,
                                                                                  resultsDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(stopEvent);
  if(status == cudaSuccess) status = cudaEventSynchronize(stopEvent);
  float elapsedMs = 0.0f;
  if(status == cudaSuccess) status = cudaEventElapsedTime(&elapsedMs, startEvent, stopEvent);
  if(status != cudaSuccess)
  {
    cudaFree(queriesDevice);
    cudaFree(refsDevice);
    cudaFree(matrixDevice);
    cudaFree(queryOffsetsDevice);
    cudaFree(queryLengthsDevice);
    cudaFree(refOffsetsDevice);
    cudaFree(refLengthsDevice);
    cudaFree(resultsDevice);
    cudaEventDestroy(startEvent);
    cudaEventDestroy(stopEvent);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  vector<PreAlignCudaForwardScoreEndResult> results(static_cast<size_t>(requestCount));
  const Clock::time_point d2hStart = Clock::now();
  status = cudaMemcpy(results.data(), resultsDevice, resultsBytes, cudaMemcpyDeviceToHost);
  const Clock::time_point d2hEnd = Clock::now();

  cudaFree(queriesDevice);
  cudaFree(refsDevice);
  cudaFree(matrixDevice);
  cudaFree(queryOffsetsDevice);
  cudaFree(queryLengthsDevice);
  cudaFree(refOffsetsDevice);
  cudaFree(refLengthsDevice);
  cudaFree(resultsDevice);
  cudaEventDestroy(startEvent);
  cudaEventDestroy(stopEvent);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outResults->swap(results);
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->kernelSeconds = batchResult->gpuSeconds;
    batchResult->h2dSeconds = elapsed_seconds(h2dStart,h2dEnd);
    batchResult->d2hSeconds = elapsed_seconds(d2hStart,d2hEnd);
    batchResult->totalSeconds = elapsed_seconds(totalStart,Clock::now());
  }
  return true;
}
