#include "sim_locate_cuda.h"
#include "sim_cuda_runtime.h"

#include <memory>
#include <mutex>
#include <vector>

#include <cuda_runtime.h>

using namespace std;

namespace
{

static const char *cuda_error_string(cudaError_t status)
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

__device__ __forceinline__ void sim_locate_order_state(int &score1,
                                                       int &x1,
                                                       int &y1,
                                                       int score2,
                                                       int x2,
                                                       int y2)
{
  if(score1 < score2)
  {
    score1 = score2;
    x1 = x2;
    y1 = y2;
  }
  else if(score1 == score2)
  {
    if(x1 < x2)
    {
      x1 = x2;
      y1 = y2;
    }
    else if(x1 == x2 && y1 < y2)
    {
      y1 = y2;
    }
  }
}

__device__ __forceinline__ bool sim_locate_diag_blocked(const uint64_t *blockedWords,
                                                        int blockedWordStride,
                                                        int rowIndex,
                                                        int columnIndex)
{
  if(blockedWords == NULL || blockedWordStride <= 0)
  {
    return false;
  }
  const size_t wordIndex = static_cast<size_t>(columnIndex) >> 6;
  const uint64_t word =
    blockedWords[static_cast<size_t>(rowIndex) * static_cast<size_t>(blockedWordStride) + wordIndex];
  const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<size_t>(columnIndex) & 63);
  return (word & mask) != 0;
}

__device__ __forceinline__ int sim_locate_no_cross(const SimScanCudaCandidateState *candidates,
                                                   int candidateCount,
                                                   int m1,
                                                   int mm,
                                                   int n1,
                                                   int nn,
                                                   int *prl,
                                                   int *pcl)
{
  for(int i = 0; i < candidateCount; ++i)
  {
    const SimScanCudaCandidateState &candidate = candidates[i];
    if(candidate.startI <= mm &&
       candidate.startJ <= nn &&
       candidate.bot >= m1 - 1 &&
       candidate.right >= n1 - 1 &&
       (candidate.startI < *prl || candidate.startJ < *pcl))
    {
      if(candidate.startI < *prl)
      {
        *prl = candidate.startI;
      }
      if(candidate.startJ < *pcl)
      {
        *pcl = candidate.startJ;
      }
      return 0;
    }
  }
  return 1;
}

struct SimLocateCudaDeviceResult
{
  int hasUpdateRegion;
  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
  unsigned long long locateCellCount;
  unsigned long long baseCellCount;
  unsigned long long expansionCellCount;
  int stopByNoCross;
  int stopByBoundary;
};

struct SimLocateCudaDeviceRequest
{
  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
  int minRowBound;
  int minColBound;
  int runningMin;
  int gapOpen;
  int gapExtend;
};

struct SimLocateCudaContext
{
  SimLocateCudaContext():
    initialized(false),
    device(0),
    capacityQuery(0),
    capacityTarget(0),
    blockedCapacityWords(0),
    candidateCapacity(0),
    batchCapacity(0),
    ADevice(NULL),
    BDevice(NULL),
    inputCacheValid(false),
    inputCacheQueryLength(0),
    inputCacheTargetLength(0),
    inputCacheAHash(0),
    inputCacheBHash(0),
    scoreMatrixDevice(NULL),
    scoreMatrixCacheValid(false),
    scoreMatrixCacheHash(0),
    blockedWordsDevice(NULL),
    blockedWordsCacheValid(false),
    blockedWordsCacheCount(0),
    blockedWordsCacheStride(0),
    blockedWordsCacheHash(0),
    candidatesDevice(NULL),
    candidatesCacheValid(false),
    candidatesCacheCount(0),
    candidatesCacheHash(0),
    CCDevice(NULL),
    DDDevice(NULL),
    RRDevice(NULL),
    SSDevice(NULL),
    EEDevice(NULL),
    FFDevice(NULL),
    HHDevice(NULL),
    WWDevice(NULL),
    IIDevice(NULL),
    JJDevice(NULL),
    XXDevice(NULL),
    YYDevice(NULL),
    batchRequestsDevice(NULL),
    batchResultsDevice(NULL),
    batchCCDevice(NULL),
    batchDDDevice(NULL),
    batchRRDevice(NULL),
    batchSSDevice(NULL),
    batchEEDevice(NULL),
    batchFFDevice(NULL),
    batchHHDevice(NULL),
    batchWWDevice(NULL),
    batchIIDevice(NULL),
    batchJJDevice(NULL),
    batchXXDevice(NULL),
    batchYYDevice(NULL),
    resultDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL)
  {
  }

  bool initialized;
  int device;
  int capacityQuery;
  int capacityTarget;
  size_t blockedCapacityWords;
  int candidateCapacity;
  int batchCapacity;

  char *ADevice;
  char *BDevice;
  bool inputCacheValid;
  int inputCacheQueryLength;
  int inputCacheTargetLength;
  uint64_t inputCacheAHash;
  uint64_t inputCacheBHash;
  vector<char> inputACache;
  vector<char> inputBCache;
  int *scoreMatrixDevice;
  bool scoreMatrixCacheValid;
  uint64_t scoreMatrixCacheHash;
  int scoreMatrixHostCache[128 * 128];
  uint64_t *blockedWordsDevice;
  bool blockedWordsCacheValid;
  size_t blockedWordsCacheCount;
  int blockedWordsCacheStride;
  uint64_t blockedWordsCacheHash;
  vector<uint64_t> blockedWordsHostCache;
  SimScanCudaCandidateState *candidatesDevice;
  bool candidatesCacheValid;
  int candidatesCacheCount;
  uint64_t candidatesCacheHash;
  vector<SimScanCudaCandidateState> candidatesHostCache;

  int *CCDevice;
  int *DDDevice;
  int *RRDevice;
  int *SSDevice;
  int *EEDevice;
  int *FFDevice;
  int *HHDevice;
  int *WWDevice;
  int *IIDevice;
  int *JJDevice;
  int *XXDevice;
  int *YYDevice;

  SimLocateCudaDeviceRequest *batchRequestsDevice;
  SimLocateCudaDeviceResult *batchResultsDevice;
  int *batchCCDevice;
  int *batchDDDevice;
  int *batchRRDevice;
  int *batchSSDevice;
  int *batchEEDevice;
  int *batchFFDevice;
  int *batchHHDevice;
  int *batchWWDevice;
  int *batchIIDevice;
  int *batchJJDevice;
  int *batchXXDevice;
  int *batchYYDevice;

  SimLocateCudaDeviceResult *resultDevice;

  cudaEvent_t startEvent;
  cudaEvent_t stopEvent;
};

static uint64_t sim_locate_cuda_bytes_hash(const char *bytes,size_t count)
{
  uint64_t hash = 1469598103934665603ull;
  for(size_t i = 0; i < count; ++i)
  {
    hash ^= static_cast<uint64_t>(static_cast<unsigned char>(bytes[i]));
    hash *= 1099511628211ull;
  }
  return hash;
}

static bool sim_locate_cuda_cached_bytes_match(const vector<char> &cached,
                                               const char *bytes,
                                               size_t count)
{
  if(cached.size() != count)
  {
    return false;
  }
  for(size_t i = 0; i < count; ++i)
  {
    if(cached[i] != bytes[i])
    {
      return false;
    }
  }
  return true;
}

static void sim_locate_cuda_invalidate_input_cache(SimLocateCudaContext &context)
{
  context.inputCacheValid = false;
  context.inputCacheQueryLength = 0;
  context.inputCacheTargetLength = 0;
  context.inputCacheAHash = 0;
  context.inputCacheBHash = 0;
  context.inputACache.clear();
  context.inputBCache.clear();
}

static bool sim_locate_cuda_input_cache_matches(const SimLocateCudaContext &context,
                                                const SimLocateCudaRequest &request,
                                                uint64_t aHash,
                                                uint64_t bHash)
{
  if(!context.inputCacheValid ||
     context.inputCacheQueryLength != request.queryLength ||
     context.inputCacheTargetLength != request.targetLength ||
     context.inputCacheAHash != aHash ||
     context.inputCacheBHash != bHash)
  {
    return false;
  }
  const size_t aBytes = static_cast<size_t>(request.queryLength + 1) * sizeof(char);
  const size_t bBytes = static_cast<size_t>(request.targetLength + 1) * sizeof(char);
  return sim_locate_cuda_cached_bytes_match(context.inputACache,request.A,aBytes) &&
    sim_locate_cuda_cached_bytes_match(context.inputBCache,request.B,bBytes);
}

static void sim_locate_cuda_store_input_cache(SimLocateCudaContext &context,
                                              const SimLocateCudaRequest &request,
                                              uint64_t aHash,
                                              uint64_t bHash)
{
  const size_t aBytes = static_cast<size_t>(request.queryLength + 1) * sizeof(char);
  const size_t bBytes = static_cast<size_t>(request.targetLength + 1) * sizeof(char);
  context.inputACache.assign(request.A,request.A + aBytes);
  context.inputBCache.assign(request.B,request.B + bBytes);
  context.inputCacheQueryLength = request.queryLength;
  context.inputCacheTargetLength = request.targetLength;
  context.inputCacheAHash = aHash;
  context.inputCacheBHash = bHash;
  context.inputCacheValid = true;
}

static uint64_t sim_locate_cuda_score_matrix_hash(const int (*scoreMatrix)[128])
{
  const int *values = &scoreMatrix[0][0];
  uint64_t hash = 1469598103934665603ull;
  for(size_t i = 0; i < static_cast<size_t>(128 * 128); ++i)
  {
    hash ^= static_cast<uint64_t>(static_cast<unsigned int>(values[i]));
    hash *= 1099511628211ull;
  }
  return hash;
}

static bool sim_locate_cuda_score_matrix_cache_matches(const SimLocateCudaContext &context,
                                                       const int (*scoreMatrix)[128],
                                                       uint64_t hash)
{
  if(!context.scoreMatrixCacheValid || context.scoreMatrixCacheHash != hash)
  {
    return false;
  }
  const int *values = &scoreMatrix[0][0];
  for(size_t i = 0; i < static_cast<size_t>(128 * 128); ++i)
  {
    if(context.scoreMatrixHostCache[i] != values[i])
    {
      return false;
    }
  }
  return true;
}

static void sim_locate_cuda_store_score_matrix_cache(SimLocateCudaContext &context,
                                                     const int (*scoreMatrix)[128],
                                                     uint64_t hash)
{
  const int *values = &scoreMatrix[0][0];
  for(size_t i = 0; i < static_cast<size_t>(128 * 128); ++i)
  {
    context.scoreMatrixHostCache[i] = values[i];
  }
  context.scoreMatrixCacheHash = hash;
  context.scoreMatrixCacheValid = true;
}

static uint64_t sim_locate_cuda_words_hash(const uint64_t *words,size_t count)
{
  uint64_t hash = 1469598103934665603ull;
  for(size_t i = 0; i < count; ++i)
  {
    hash ^= words[i];
    hash *= 1099511628211ull;
  }
  return hash;
}

static void sim_locate_cuda_invalidate_blocked_words_cache(SimLocateCudaContext &context)
{
  context.blockedWordsCacheValid = false;
  context.blockedWordsCacheCount = 0;
  context.blockedWordsCacheStride = 0;
  context.blockedWordsCacheHash = 0;
  context.blockedWordsHostCache.clear();
}

static bool sim_locate_cuda_blocked_words_cache_matches(const SimLocateCudaContext &context,
                                                        const SimLocateCudaRequest &request,
                                                        size_t count,
                                                        uint64_t hash)
{
  if(!context.blockedWordsCacheValid ||
     context.blockedWordsCacheCount != count ||
     context.blockedWordsCacheStride != request.blockedWordStride ||
     context.blockedWordsCacheHash != hash ||
     context.blockedWordsHostCache.size() != count)
  {
    return false;
  }
  for(size_t i = 0; i < count; ++i)
  {
    if(context.blockedWordsHostCache[i] != request.blockedWords[i])
    {
      return false;
    }
  }
  return true;
}

static void sim_locate_cuda_store_blocked_words_cache(SimLocateCudaContext &context,
                                                      const SimLocateCudaRequest &request,
                                                      size_t count,
                                                      uint64_t hash)
{
  context.blockedWordsHostCache.assign(request.blockedWords,request.blockedWords + count);
  context.blockedWordsCacheCount = count;
  context.blockedWordsCacheStride = request.blockedWordStride;
  context.blockedWordsCacheHash = hash;
  context.blockedWordsCacheValid = true;
}

static uint64_t sim_locate_cuda_candidate_hash(const SimScanCudaCandidateState *candidates,
                                               int count)
{
  uint64_t hash = 1469598103934665603ull;
  for(int i = 0; i < count; ++i)
  {
    const SimScanCudaCandidateState &candidate = candidates[i];
    const int values[] = {candidate.score, candidate.startI, candidate.startJ,
                          candidate.endI, candidate.endJ, candidate.top,
                          candidate.bot, candidate.left, candidate.right};
    for(size_t j = 0; j < sizeof(values) / sizeof(values[0]); ++j)
    {
      hash ^= static_cast<uint64_t>(static_cast<unsigned int>(values[j]));
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

static void sim_locate_cuda_invalidate_candidates_cache(SimLocateCudaContext &context)
{
  context.candidatesCacheValid = false;
  context.candidatesCacheCount = 0;
  context.candidatesCacheHash = 0;
  context.candidatesHostCache.clear();
}

static bool sim_locate_cuda_candidates_cache_matches(const SimLocateCudaContext &context,
                                                     const SimLocateCudaRequest &request,
                                                     uint64_t hash)
{
  if(!context.candidatesCacheValid ||
     context.candidatesCacheCount != request.candidateCount ||
     context.candidatesCacheHash != hash ||
     context.candidatesHostCache.size() != static_cast<size_t>(request.candidateCount))
  {
    return false;
  }
  for(int i = 0; i < request.candidateCount; ++i)
  {
    const SimScanCudaCandidateState &cached = context.candidatesHostCache[static_cast<size_t>(i)];
    const SimScanCudaCandidateState &candidate = request.candidates[i];
    if(cached.score != candidate.score ||
       cached.startI != candidate.startI ||
       cached.startJ != candidate.startJ ||
       cached.endI != candidate.endI ||
       cached.endJ != candidate.endJ ||
       cached.top != candidate.top ||
       cached.bot != candidate.bot ||
       cached.left != candidate.left ||
       cached.right != candidate.right)
    {
      return false;
    }
  }
  return true;
}

static void sim_locate_cuda_store_candidates_cache(SimLocateCudaContext &context,
                                                  const SimLocateCudaRequest &request,
                                                  uint64_t hash)
{
  context.candidatesHostCache.assign(request.candidates,
                                     request.candidates + request.candidateCount);
  context.candidatesCacheCount = request.candidateCount;
  context.candidatesCacheHash = hash;
  context.candidatesCacheValid = true;
}

static mutex sim_locate_cuda_contexts_mutex;
static vector< vector< unique_ptr<SimLocateCudaContext> > > sim_locate_cuda_contexts;
static vector< vector< unique_ptr<mutex> > > sim_locate_cuda_context_mutexes;

static bool get_sim_locate_cuda_context_for_device_slot(int device,
                                                        int slot,
                                                        SimLocateCudaContext **contextOut,
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

  lock_guard<mutex> lock(sim_locate_cuda_contexts_mutex);
  if(sim_locate_cuda_contexts.size() <= static_cast<size_t>(device))
  {
    sim_locate_cuda_contexts.resize(static_cast<size_t>(device) + 1);
    sim_locate_cuda_context_mutexes.resize(static_cast<size_t>(device) + 1);
  }
  vector< unique_ptr<SimLocateCudaContext> > &deviceContexts =
    sim_locate_cuda_contexts[static_cast<size_t>(device)];
  vector< unique_ptr<mutex> > &deviceMutexes =
    sim_locate_cuda_context_mutexes[static_cast<size_t>(device)];
  if(deviceContexts.size() <= static_cast<size_t>(slot))
  {
    deviceContexts.resize(static_cast<size_t>(slot) + 1);
    deviceMutexes.resize(static_cast<size_t>(slot) + 1);
  }
  if(!deviceContexts[static_cast<size_t>(slot)])
  {
    deviceContexts[static_cast<size_t>(slot)].reset(new SimLocateCudaContext());
  }
  if(!deviceMutexes[static_cast<size_t>(slot)])
  {
    deviceMutexes[static_cast<size_t>(slot)].reset(new mutex());
  }

  *contextOut = deviceContexts[static_cast<size_t>(slot)].get();
  *mutexOut = deviceMutexes[static_cast<size_t>(slot)].get();
  return true;
}

static void free_sim_locate_cuda_capacity_locked(SimLocateCudaContext &context)
{
  cudaFree(context.ADevice);
  cudaFree(context.BDevice);
  cudaFree(context.blockedWordsDevice);
  cudaFree(context.candidatesDevice);
  cudaFree(context.CCDevice);
  cudaFree(context.DDDevice);
  cudaFree(context.RRDevice);
  cudaFree(context.SSDevice);
  cudaFree(context.EEDevice);
  cudaFree(context.FFDevice);
  cudaFree(context.HHDevice);
  cudaFree(context.WWDevice);
  cudaFree(context.IIDevice);
  cudaFree(context.JJDevice);
  cudaFree(context.XXDevice);
  cudaFree(context.YYDevice);
  cudaFree(context.batchRequestsDevice);
  cudaFree(context.batchResultsDevice);
  cudaFree(context.batchCCDevice);
  cudaFree(context.batchDDDevice);
  cudaFree(context.batchRRDevice);
  cudaFree(context.batchSSDevice);
  cudaFree(context.batchEEDevice);
  cudaFree(context.batchFFDevice);
  cudaFree(context.batchHHDevice);
  cudaFree(context.batchWWDevice);
  cudaFree(context.batchIIDevice);
  cudaFree(context.batchJJDevice);
  cudaFree(context.batchXXDevice);
  cudaFree(context.batchYYDevice);

  context.ADevice = NULL;
  context.BDevice = NULL;
  context.blockedWordsDevice = NULL;
  context.candidatesDevice = NULL;
  context.CCDevice = NULL;
  context.DDDevice = NULL;
  context.RRDevice = NULL;
  context.SSDevice = NULL;
  context.EEDevice = NULL;
  context.FFDevice = NULL;
  context.HHDevice = NULL;
  context.WWDevice = NULL;
  context.IIDevice = NULL;
  context.JJDevice = NULL;
  context.XXDevice = NULL;
  context.YYDevice = NULL;
  context.batchRequestsDevice = NULL;
  context.batchResultsDevice = NULL;
  context.batchCCDevice = NULL;
  context.batchDDDevice = NULL;
  context.batchRRDevice = NULL;
  context.batchSSDevice = NULL;
  context.batchEEDevice = NULL;
  context.batchFFDevice = NULL;
  context.batchHHDevice = NULL;
  context.batchWWDevice = NULL;
  context.batchIIDevice = NULL;
  context.batchJJDevice = NULL;
  context.batchXXDevice = NULL;
  context.batchYYDevice = NULL;
  context.capacityQuery = 0;
  context.capacityTarget = 0;
  context.blockedCapacityWords = 0;
  context.candidateCapacity = 0;
  context.batchCapacity = 0;
  sim_locate_cuda_invalidate_input_cache(context);
  context.scoreMatrixCacheValid = false;
  context.scoreMatrixCacheHash = 0;
  sim_locate_cuda_invalidate_blocked_words_cache(context);
  sim_locate_cuda_invalidate_candidates_cache(context);
}

static bool ensure_sim_locate_cuda_initialized_locked(SimLocateCudaContext &context,
                                                      int device,
                                                      string *errorOut)
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
  status = cudaMalloc(reinterpret_cast<void **>(&context.scoreMatrixDevice),
                      static_cast<size_t>(128 * 128) * sizeof(int));
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
  status = cudaMalloc(reinterpret_cast<void **>(&context.resultDevice), sizeof(SimLocateCudaDeviceResult));
  if(status != cudaSuccess)
  {
    cudaFree(context.scoreMatrixDevice);
    context.scoreMatrixDevice = NULL;
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

  context.initialized = true;
  context.device = device;
  return true;
}

static bool ensure_sim_locate_cuda_capacity_locked(SimLocateCudaContext &context,
                                                   int queryLength,
                                                   int targetLength,
                                                   int blockedWordStride,
                                                   int candidateCount,
                                                   string *errorOut)
{
  if(queryLength < 0 || targetLength < 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid sequence dimensions";
    }
    return false;
  }

  const size_t blockedWordsNeeded =
    (blockedWordStride > 0) ? static_cast<size_t>(queryLength + 1) * static_cast<size_t>(blockedWordStride) : 0u;
  const int candidateCapacityNeeded = (candidateCount > 0) ? candidateCount : 1;
  const bool needsArrayGrowth = queryLength > context.capacityQuery || targetLength > context.capacityTarget;
  if(needsArrayGrowth)
  {
    free_sim_locate_cuda_capacity_locked(context);

    cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&context.ADevice),
                                    static_cast<size_t>(queryLength + 1) * sizeof(char));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    status = cudaMalloc(reinterpret_cast<void **>(&context.BDevice),
                        static_cast<size_t>(targetLength + 1) * sizeof(char));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      free_sim_locate_cuda_capacity_locked(context);
      return false;
    }

    int **targetArrays[] = {&context.CCDevice, &context.DDDevice, &context.RRDevice,
                            &context.SSDevice, &context.EEDevice, &context.FFDevice};
    for(size_t i = 0; i < sizeof(targetArrays) / sizeof(targetArrays[0]); ++i)
    {
      status = cudaMalloc(reinterpret_cast<void **>(targetArrays[i]),
                          static_cast<size_t>(targetLength + 1) * sizeof(int));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL) *errorOut = cuda_error_string(status);
        free_sim_locate_cuda_capacity_locked(context);
        return false;
      }
    }

    int **queryArrays[] = {&context.HHDevice, &context.WWDevice, &context.IIDevice,
                           &context.JJDevice, &context.XXDevice, &context.YYDevice};
    for(size_t i = 0; i < sizeof(queryArrays) / sizeof(queryArrays[0]); ++i)
    {
      status = cudaMalloc(reinterpret_cast<void **>(queryArrays[i]),
                          static_cast<size_t>(queryLength + 1) * sizeof(int));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL) *errorOut = cuda_error_string(status);
        free_sim_locate_cuda_capacity_locked(context);
        return false;
      }
    }

    context.capacityQuery = queryLength;
    context.capacityTarget = targetLength;
  }

  if(blockedWordsNeeded > context.blockedCapacityWords)
  {
    cudaFree(context.blockedWordsDevice);
    context.blockedWordsDevice = NULL;
    context.blockedCapacityWords = 0;
    if(blockedWordsNeeded > 0)
    {
      const cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&context.blockedWordsDevice),
                                            blockedWordsNeeded * sizeof(uint64_t));
      if(status != cudaSuccess)
      {
        if(errorOut != NULL) *errorOut = cuda_error_string(status);
        return false;
      }
      context.blockedCapacityWords = blockedWordsNeeded;
    }
  }

  if(candidateCapacityNeeded > context.candidateCapacity)
  {
    cudaFree(context.candidatesDevice);
    context.candidatesDevice = NULL;
    context.candidateCapacity = 0;
    const cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&context.candidatesDevice),
                                          static_cast<size_t>(candidateCapacityNeeded) * sizeof(SimScanCudaCandidateState));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    context.candidateCapacity = candidateCapacityNeeded;
  }

  return true;
}

static bool ensure_sim_locate_cuda_batch_capacity_locked(SimLocateCudaContext &context,
                                                         int queryLength,
                                                         int targetLength,
                                                         int batchCount,
                                                         string *errorOut)
{
  const auto resetBatchBuffers = [&context]() -> void
  {
    cudaFree(context.batchRequestsDevice);
    cudaFree(context.batchResultsDevice);
    cudaFree(context.batchCCDevice);
    cudaFree(context.batchDDDevice);
    cudaFree(context.batchRRDevice);
    cudaFree(context.batchSSDevice);
    cudaFree(context.batchEEDevice);
    cudaFree(context.batchFFDevice);
    cudaFree(context.batchHHDevice);
    cudaFree(context.batchWWDevice);
    cudaFree(context.batchIIDevice);
    cudaFree(context.batchJJDevice);
    cudaFree(context.batchXXDevice);
    cudaFree(context.batchYYDevice);
    context.batchRequestsDevice = NULL;
    context.batchResultsDevice = NULL;
    context.batchCCDevice = NULL;
    context.batchDDDevice = NULL;
    context.batchRRDevice = NULL;
    context.batchSSDevice = NULL;
    context.batchEEDevice = NULL;
    context.batchFFDevice = NULL;
    context.batchHHDevice = NULL;
    context.batchWWDevice = NULL;
    context.batchIIDevice = NULL;
    context.batchJJDevice = NULL;
    context.batchXXDevice = NULL;
    context.batchYYDevice = NULL;
    context.batchCapacity = 0;
  };

  if(batchCount <= 0)
  {
    return true;
  }
  if(batchCount <= context.batchCapacity)
  {
    return true;
  }

  resetBatchBuffers();

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&context.batchRequestsDevice),
                                  static_cast<size_t>(batchCount) * sizeof(SimLocateCudaDeviceRequest));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    resetBatchBuffers();
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&context.batchResultsDevice),
                      static_cast<size_t>(batchCount) * sizeof(SimLocateCudaDeviceResult));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    resetBatchBuffers();
    return false;
  }

  int **targetArrays[] = {&context.batchCCDevice, &context.batchDDDevice, &context.batchRRDevice,
                          &context.batchSSDevice, &context.batchEEDevice, &context.batchFFDevice};
  for(size_t i = 0; i < sizeof(targetArrays) / sizeof(targetArrays[0]); ++i)
  {
    status = cudaMalloc(reinterpret_cast<void **>(targetArrays[i]),
                        static_cast<size_t>(batchCount) *
                        static_cast<size_t>(targetLength + 1) * sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      resetBatchBuffers();
      return false;
    }
  }

  int **queryArrays[] = {&context.batchHHDevice, &context.batchWWDevice, &context.batchIIDevice,
                         &context.batchJJDevice, &context.batchXXDevice, &context.batchYYDevice};
  for(size_t i = 0; i < sizeof(queryArrays) / sizeof(queryArrays[0]); ++i)
  {
    status = cudaMalloc(reinterpret_cast<void **>(queryArrays[i]),
                        static_cast<size_t>(batchCount) *
                        static_cast<size_t>(queryLength + 1) * sizeof(int));
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      resetBatchBuffers();
      return false;
    }
  }

  context.batchCapacity = batchCount;
  return true;
}

__device__ void sim_locate_cuda_run_request(const SimLocateCudaDeviceRequest &request,
                                            const char *A,
                                            const char *B,
                                            const int *scoreMatrix,
                                            const uint64_t *blockedWords,
                                            int blockedWordStride,
                                            const SimScanCudaCandidateState *candidates,
                                            int candidateCount,
                                            int *CC,
                                            int *DD,
                                            int *RR,
                                            int *SS,
                                            int *EE,
                                            int *FF,
                                            int *HH,
                                            int *WW,
                                            int *II,
                                            int *JJ,
                                            int *XX,
                                            int *YY,
                                            SimLocateCudaDeviceResult *result)
{
  SimLocateCudaDeviceResult out;
  out.hasUpdateRegion = 0;
  out.rowStart = 0;
  out.rowEnd = 0;
  out.colStart = 0;
  out.colEnd = 0;
  out.locateCellCount = 0;
  out.baseCellCount = 0;
  out.expansionCellCount = 0;
  out.stopByNoCross = 0;
  out.stopByBoundary = 0;

  int m1 = request.rowStart;
  int mm = request.rowEnd;
  int n1 = request.colStart;
  int nn = request.colEnd;
  int minRowBound = request.minRowBound;
  int minColBound = request.minColBound;
  if(minRowBound < 1)
  {
    minRowBound = 1;
  }
  if(minColBound < 1)
  {
    minColBound = 1;
  }
  if(minRowBound > m1)
  {
    minRowBound = m1;
  }
  if(minColBound > n1)
  {
    minColBound = n1;
  }
  if(A == NULL ||
     B == NULL ||
     scoreMatrix == NULL ||
     result == NULL ||
     m1 < 1 ||
     n1 < 1 ||
     mm < m1 ||
     nn < n1)
  {
    *result = out;
    return;
  }

  const int Q = request.gapOpen;
  const int R = request.gapExtend;
  const int QR = Q + R;
  const int negQ = -Q;
  const int runningMin = request.runningMin;

  int c = 0;
  int f = 0;
  int d = 0;
  int p = 0;
  int ci = 0;
  int cj = 0;
  int di = 0;
  int dj = 0;
  int fi = 0;
  int fj = 0;
  int pi = 0;
  int pj = 0;
  int rl = 0;
  int cl = 0;
  int limit = 0;
  int rflag = 0;
  int cflag = 0;
  int flag = 0;
  unsigned long long baseCellCount = 0;
  int stopByNoCross = 0;
  int stopByBoundary = 0;

  for(int j = nn; j >= n1; --j)
  {
    CC[j] = 0;
    EE[j] = j;
    DD[j] = negQ;
    FF[j] = j;
    RR[j] = mm + 1;
    SS[j] = mm + 1;
  }

  for(int i = mm; i >= m1; --i)
  {
    out.locateCellCount += static_cast<unsigned long long>(nn - n1 + 1);
    c = 0;
    p = 0;
    f = negQ;
    ci = i;
    fi = i;
    pi = i + 1;
    cj = nn + 1;
    fj = nn + 1;
    pj = nn + 1;
    const int *va = scoreMatrix + static_cast<int>(static_cast<unsigned char>(A[i])) * 128;
    limit = n1;
    for(int j = nn; j >= limit; --j)
    {
      f -= R;
      c -= QR;
      sim_locate_order_state(f, fi, fj, c, ci, cj);
      c = CC[j] - QR;
      ci = RR[j];
      cj = EE[j];
      d = DD[j] - R;
      di = SS[j];
      dj = FF[j];
      sim_locate_order_state(d, di, dj, c, ci, cj);
      c = 0;
      if(!sim_locate_diag_blocked(blockedWords, blockedWordStride, i, j))
      {
        c = p + va[static_cast<unsigned char>(B[j])];
      }
      if(c <= 0)
      {
        c = 0;
        ci = i;
        cj = j;
      }
      else
      {
        ci = pi;
        cj = pj;
      }
      sim_locate_order_state(c, ci, cj, d, di, dj);
      sim_locate_order_state(c, ci, cj, f, fi, fj);
      p = CC[j];
      CC[j] = c;
      pi = RR[j];
      pj = EE[j];
      RR[j] = ci;
      EE[j] = cj;
      DD[j] = d;
      SS[j] = di;
      FF[j] = dj;
      if(c > runningMin)
      {
        flag = 1;
      }
    }
    HH[i] = CC[n1];
    II[i] = RR[n1];
    JJ[i] = EE[n1];
    WW[i] = f;
    XX[i] = fi;
    YY[i] = fj;
  }
  baseCellCount = out.locateCellCount;

  for(rl = m1, cl = n1; ; )
  {
    int expanded = 0;
    for(rflag = 1, cflag = 1; (rflag && m1 > minRowBound) || (cflag && n1 > minColBound); )
    {
      if(rflag && m1 > minRowBound)
      {
        expanded = 1;
        rflag = 0;
        --m1;
        out.locateCellCount += static_cast<unsigned long long>(nn - n1 + 1);
        c = 0;
        p = 0;
        f = negQ;
        ci = m1;
        fi = m1;
        pi = m1 + 1;
        cj = nn + 1;
        fj = nn + 1;
        pj = nn + 1;
        const int *va = scoreMatrix + static_cast<int>(static_cast<unsigned char>(A[m1])) * 128;
        for(int j = nn; j >= n1; --j)
        {
          f -= R;
          c -= QR;
          sim_locate_order_state(f, fi, fj, c, ci, cj);
          c = CC[j] - QR;
          ci = RR[j];
          cj = EE[j];
          d = DD[j] - R;
          di = SS[j];
          dj = FF[j];
          sim_locate_order_state(d, di, dj, c, ci, cj);
          c = 0;
          if(!sim_locate_diag_blocked(blockedWords, blockedWordStride, m1, j))
          {
            c = p + va[static_cast<unsigned char>(B[j])];
          }
          if(c <= 0)
          {
            c = 0;
            ci = m1;
            cj = j;
          }
          else
          {
            ci = pi;
            cj = pj;
          }
          sim_locate_order_state(c, ci, cj, d, di, dj);
          sim_locate_order_state(c, ci, cj, f, fi, fj);
          p = CC[j];
          CC[j] = c;
          pi = RR[j];
          pj = EE[j];
          RR[j] = ci;
          EE[j] = cj;
          DD[j] = d;
          SS[j] = di;
          FF[j] = dj;
          if(c > runningMin)
          {
            flag = 1;
          }
          if(!rflag && ((ci > rl && cj > cl) || (di > rl && dj > cl) || (fi > rl && fj > cl)))
          {
            rflag = 1;
          }
        }
        HH[m1] = CC[n1];
        II[m1] = RR[n1];
        JJ[m1] = EE[n1];
        WW[m1] = f;
        XX[m1] = fi;
        YY[m1] = fj;
        if(!cflag && ((ci > rl && cj > cl) || (di > rl && dj > cl) || (fi > rl && fj > cl)))
        {
          cflag = 1;
        }
      }

      if(cflag && n1 > minColBound)
      {
        expanded = 1;
        cflag = 0;
        --n1;
        out.locateCellCount += static_cast<unsigned long long>(mm - m1 + 1);
        c = 0;
        f = negQ;
        cj = n1;
        fj = n1;
        const int *va = scoreMatrix + static_cast<int>(static_cast<unsigned char>(B[n1])) * 128;
        p = 0;
        ci = mm + 1;
        fi = mm + 1;
        pi = mm + 1;
        pj = n1 + 1;
        limit = mm;
        for(int i = limit; i >= m1; --i)
        {
          f -= R;
          c -= QR;
          sim_locate_order_state(f, fi, fj, c, ci, cj);
          c = HH[i] - QR;
          ci = II[i];
          cj = JJ[i];
          d = WW[i] - R;
          di = XX[i];
          dj = YY[i];
          sim_locate_order_state(d, di, dj, c, ci, cj);
          c = 0;
          if(!sim_locate_diag_blocked(blockedWords, blockedWordStride, i, n1))
          {
            c = p + va[static_cast<unsigned char>(A[i])];
          }
          if(c <= 0)
          {
            c = 0;
            ci = i;
            cj = n1;
          }
          else
          {
            ci = pi;
            cj = pj;
          }
          sim_locate_order_state(c, ci, cj, d, di, dj);
          sim_locate_order_state(c, ci, cj, f, fi, fj);
          p = HH[i];
          HH[i] = c;
          pi = II[i];
          pj = JJ[i];
          II[i] = ci;
          JJ[i] = cj;
          WW[i] = d;
          XX[i] = di;
          YY[i] = dj;
          if(c > runningMin)
          {
            flag = 1;
          }
          if(!cflag && ((ci > rl && cj > cl) || (di > rl && dj > cl) || (fi > rl && fj > cl)))
          {
            cflag = 1;
          }
        }
        CC[n1] = HH[m1];
        RR[n1] = II[m1];
        EE[n1] = JJ[m1];
        DD[n1] = f;
        SS[n1] = fi;
        FF[n1] = fj;
        if(!rflag && ((ci > rl && cj > cl) || (di > rl && dj > cl) || (fi > rl && fj > cl)))
        {
          rflag = 1;
        }
      }
    }

    const int hitConfiguredBoundary = (m1 == minRowBound && n1 == minColBound);
    const int hitFullBoundary = (m1 == 1 && n1 == 1);
    int noCross = 0;
    if(!hitConfiguredBoundary && !hitFullBoundary)
    {
      noCross = sim_locate_no_cross(candidates,candidateCount,m1,mm,n1,nn,&rl,&cl);
    }
    if(hitConfiguredBoundary || hitFullBoundary || noCross)
    {
      stopByBoundary = hitConfiguredBoundary || hitFullBoundary;
      stopByNoCross = noCross;
      break;
    }
    if(!expanded)
    {
      break;
    }
  }

  out.baseCellCount = baseCellCount;
  out.expansionCellCount = out.locateCellCount - baseCellCount;
  out.stopByNoCross = stopByNoCross;
  out.stopByBoundary = stopByBoundary;
  --m1;
  --n1;
  if(flag)
  {
    out.hasUpdateRegion = 1;
    out.rowStart = m1 + 1;
    out.rowEnd = mm;
    out.colStart = n1 + 1;
    out.colEnd = nn;
  }

  *result = out;
}

__global__ void sim_locate_cuda_kernel(const char *A,
                                       const char *B,
                                       int rowStart,
                                       int rowEnd,
                                       int colStart,
                                       int colEnd,
                                       int minRowBound,
                                       int minColBound,
                                       int runningMin,
                                       int gapOpen,
                                       int gapExtend,
                                       const int *scoreMatrix,
                                       const uint64_t *blockedWords,
                                       int blockedWordStride,
                                       const SimScanCudaCandidateState *candidates,
                                       int candidateCount,
                                       int *CC,
                                       int *DD,
                                       int *RR,
                                       int *SS,
                                       int *EE,
                                       int *FF,
                                       int *HH,
                                       int *WW,
                                       int *II,
                                       int *JJ,
                                       int *XX,
                                       int *YY,
                                       SimLocateCudaDeviceResult *result)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }

  SimLocateCudaDeviceRequest request;
  request.rowStart = rowStart;
  request.rowEnd = rowEnd;
  request.colStart = colStart;
  request.colEnd = colEnd;
  request.minRowBound = minRowBound;
  request.minColBound = minColBound;
  request.runningMin = runningMin;
  request.gapOpen = gapOpen;
  request.gapExtend = gapExtend;
  sim_locate_cuda_run_request(request,
                              A,
                              B,
                              scoreMatrix,
                              blockedWords,
                              blockedWordStride,
                              candidates,
                              candidateCount,
                              CC,
                              DD,
                              RR,
                              SS,
                              EE,
                              FF,
                              HH,
                              WW,
                              II,
                              JJ,
                              XX,
                              YY,
                              result);
}

__global__ void sim_locate_cuda_batch_kernel(const SimLocateCudaDeviceRequest *requests,
                                             int requestCount,
                                             const char *A,
                                             const char *B,
                                             const int *scoreMatrix,
                                             const uint64_t *blockedWords,
                                             int blockedWordStride,
                                             const SimScanCudaCandidateState *candidates,
                                             int candidateCount,
                                             int targetStride,
                                             int queryStride,
                                             int *CC,
                                             int *DD,
                                             int *RR,
                                             int *SS,
                                             int *EE,
                                             int *FF,
                                             int *HH,
                                             int *WW,
                                             int *II,
                                             int *JJ,
                                             int *XX,
                                             int *YY,
                                             SimLocateCudaDeviceResult *results)
{
  if(threadIdx.x != 0 || requests == NULL || results == NULL)
  {
    return;
  }
  const int batchIndex = static_cast<int>(blockIdx.x);
  if(batchIndex < 0 || batchIndex >= requestCount)
  {
    return;
  }

  sim_locate_cuda_run_request(requests[batchIndex],
                              A,
                              B,
                              scoreMatrix,
                              blockedWords,
                              blockedWordStride,
                              candidates,
                              candidateCount,
                              CC + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              DD + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              RR + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              SS + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              EE + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              FF + static_cast<size_t>(batchIndex) * static_cast<size_t>(targetStride),
                              HH + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              WW + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              II + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              JJ + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              XX + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              YY + static_cast<size_t>(batchIndex) * static_cast<size_t>(queryStride),
                              results + batchIndex);
}

static bool sim_locate_cuda_validate_request(const SimLocateCudaRequest &request,
                                             string *errorOut)
{
  if(request.A == NULL || request.B == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing input sequences";
    return false;
  }
  if(request.queryLength <= 0 || request.targetLength <= 0)
  {
    if(errorOut != NULL) *errorOut = "invalid sequence dimensions";
    return false;
  }
  if(request.rowStart < 1 || request.colStart < 1 ||
     request.rowEnd < request.rowStart || request.colEnd < request.colStart ||
     request.rowEnd > request.queryLength || request.colEnd > request.targetLength)
  {
    if(errorOut != NULL) *errorOut = "invalid locate bounds";
    return false;
  }
  if(request.gapOpen < 0 || request.gapExtend < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid gap penalties";
    return false;
  }
  if(request.scoreMatrix == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing score matrix";
    return false;
  }
  if(request.blockedWords != NULL && request.blockedWordStride <= 0)
  {
    if(errorOut != NULL) *errorOut = "invalid blocked word stride";
    return false;
  }
  if(request.candidateCount < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid candidate count";
    return false;
  }
  if(request.candidateCount > 0 && request.candidates == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing candidate states";
    return false;
  }
  if(request.minRowBound < 1 ||
     request.minColBound < 1 ||
     request.minRowBound > request.rowStart ||
     request.minColBound > request.colStart)
  {
    if(errorOut != NULL) *errorOut = "invalid locate lower bounds";
    return false;
  }
  return true;
}

static bool sim_locate_cuda_requests_share_inputs(const vector<SimLocateCudaRequest> &requests)
{
  if(requests.empty())
  {
    return true;
  }
  const SimLocateCudaRequest &base = requests[0];
  for(size_t i = 1; i < requests.size(); ++i)
  {
    const SimLocateCudaRequest &request = requests[i];
    if(request.A != base.A ||
       request.B != base.B ||
       request.queryLength != base.queryLength ||
       request.targetLength != base.targetLength ||
       request.runningMin != base.runningMin ||
       request.gapOpen != base.gapOpen ||
       request.gapExtend != base.gapExtend ||
       request.scoreMatrix != base.scoreMatrix ||
       request.blockedWords != base.blockedWords ||
       request.blockedWordStride != base.blockedWordStride ||
       request.candidates != base.candidates ||
       request.candidateCount != base.candidateCount)
    {
      return false;
    }
  }
  return true;
}

} // namespace

bool sim_locate_cuda_is_built()
{
  return true;
}

bool sim_locate_cuda_init(int device,string *errorOut)
{
  if(device < 0)
  {
    device = 0;
  }
  const int slot = simCudaWorkerSlotRuntime();
  SimLocateCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_locate_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }
  lock_guard<mutex> lock(*contextMutex);
  return ensure_sim_locate_cuda_initialized_locked(*context,device,errorOut);
}

bool sim_locate_cuda_locate_region(const SimLocateCudaRequest &request,
                                   SimLocateResult *outResult,
                                   string *errorOut)
{
  if(outResult == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  *outResult = SimLocateResult();

  if(request.A == NULL || request.B == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing input sequences";
    return false;
  }
  if(request.queryLength <= 0 || request.targetLength <= 0)
  {
    if(errorOut != NULL) *errorOut = "invalid sequence dimensions";
    return false;
  }
  if(request.rowStart < 1 || request.colStart < 1 ||
     request.rowEnd < request.rowStart || request.colEnd < request.colStart ||
     request.rowEnd > request.queryLength || request.colEnd > request.targetLength)
  {
    if(errorOut != NULL) *errorOut = "invalid locate bounds";
    return false;
  }
  if(request.gapOpen < 0 || request.gapExtend < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid gap penalties";
    return false;
  }
  if(request.scoreMatrix == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing score matrix";
    return false;
  }
  if(request.blockedWords != NULL && request.blockedWordStride <= 0)
  {
    if(errorOut != NULL) *errorOut = "invalid blocked word stride";
    return false;
  }
  if(request.candidateCount < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid candidate count";
    return false;
  }
  if(request.candidateCount > 0 && request.candidates == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing candidate states";
    return false;
  }
  if(request.minRowBound < 1 ||
     request.minColBound < 1 ||
     request.minRowBound > request.rowStart ||
     request.minColBound > request.colStart)
  {
    if(errorOut != NULL) *errorOut = "invalid locate lower bounds";
    return false;
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(deviceStatus);
    return false;
  }

  SimLocateCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_locate_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_locate_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_locate_cuda_capacity_locked(*context,
                                             request.queryLength,
                                             request.targetLength,
                                             request.blockedWordStride,
                                             request.candidateCount,
                                             errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->ADevice,
                                  request.A,
                                  static_cast<size_t>(request.queryLength + 1) * sizeof(char),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    sim_locate_cuda_invalidate_input_cache(*context);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMemcpy(context->BDevice,
                      request.B,
                      static_cast<size_t>(request.targetLength + 1) * sizeof(char),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    sim_locate_cuda_invalidate_input_cache(*context);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  sim_locate_cuda_invalidate_input_cache(*context);
  status = cudaMemcpy(context->scoreMatrixDevice,
                      request.scoreMatrix,
                      static_cast<size_t>(128 * 128) * sizeof(int),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    context->scoreMatrixCacheValid = false;
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  context->scoreMatrixCacheValid = false;

  if(request.blockedWords != NULL && request.blockedWordStride > 0)
  {
    const size_t blockedWordCount =
      static_cast<size_t>(request.queryLength + 1) * static_cast<size_t>(request.blockedWordStride);
    status = cudaMemcpy(context->blockedWordsDevice,
                        request.blockedWords,
                        blockedWordCount * sizeof(uint64_t),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      sim_locate_cuda_invalidate_blocked_words_cache(*context);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    sim_locate_cuda_invalidate_blocked_words_cache(*context);
  }

  if(request.candidateCount > 0)
  {
    status = cudaMemcpy(context->candidatesDevice,
                        request.candidates,
                        static_cast<size_t>(request.candidateCount) * sizeof(SimScanCudaCandidateState),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      sim_locate_cuda_invalidate_candidates_cache(*context);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    sim_locate_cuda_invalidate_candidates_cache(*context);
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  sim_locate_cuda_kernel<<<1, 1>>>(context->ADevice,
                                   context->BDevice,
                                   request.rowStart,
                                   request.rowEnd,
                                   request.colStart,
                                   request.colEnd,
                                   request.minRowBound,
                                   request.minColBound,
                                   request.runningMin,
                                   request.gapOpen,
                                   request.gapExtend,
                                   context->scoreMatrixDevice,
                                   (request.blockedWords != NULL && request.blockedWordStride > 0) ? context->blockedWordsDevice : NULL,
                                   request.blockedWordStride,
                                   (request.candidateCount > 0) ? context->candidatesDevice : NULL,
                                   request.candidateCount,
                                   context->CCDevice,
                                   context->DDDevice,
                                   context->RRDevice,
                                   context->SSDevice,
                                   context->EEDevice,
                                   context->FFDevice,
                                   context->HHDevice,
                                   context->WWDevice,
                                   context->IIDevice,
                                   context->JJDevice,
                                   context->XXDevice,
                                   context->YYDevice,
                                   context->resultDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  SimLocateCudaDeviceResult deviceResult;
  status = cudaMemcpy(&deviceResult,
                      context->resultDevice,
                      sizeof(SimLocateCudaDeviceResult),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  float elapsedMs = 0.0f;
  status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  outResult->hasUpdateRegion = deviceResult.hasUpdateRegion != 0;
  outResult->rowStart = static_cast<long>(deviceResult.rowStart);
  outResult->rowEnd = static_cast<long>(deviceResult.rowEnd);
  outResult->colStart = static_cast<long>(deviceResult.colStart);
  outResult->colEnd = static_cast<long>(deviceResult.colEnd);
  outResult->locateCellCount = static_cast<uint64_t>(deviceResult.locateCellCount);
  outResult->baseCellCount = static_cast<uint64_t>(deviceResult.baseCellCount);
  outResult->expansionCellCount = static_cast<uint64_t>(deviceResult.expansionCellCount);
  outResult->stopByNoCross = deviceResult.stopByNoCross != 0;
  outResult->stopByBoundary = deviceResult.stopByBoundary != 0;
  outResult->usedCuda = true;
  outResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;

  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool sim_locate_cuda_locate_region_batch(const vector<SimLocateCudaRequest> &requests,
                                         vector<SimLocateResult> *outResults,
                                         SimLocateCudaBatchResult *batchResult,
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
    *batchResult = SimLocateCudaBatchResult();
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
    if(!sim_locate_cuda_validate_request(requests[i],errorOut))
    {
      return false;
    }
  }

  if(requests.size() == 1)
  {
    SimLocateResult result;
    if(!sim_locate_cuda_locate_region(requests[0],&result,errorOut))
    {
      outResults->clear();
      if(batchResult != NULL)
      {
        *batchResult = SimLocateCudaBatchResult();
      }
      return false;
    }
    outResults->assign(1,result);
    if(batchResult != NULL)
    {
      batchResult->gpuSeconds = result.gpuSeconds;
      batchResult->usedCuda = result.usedCuda;
      batchResult->taskCount = 1;
      batchResult->launchCount = result.usedCuda ? 1 : 0;
      batchResult->usedSharedInputBatchPath = false;
      batchResult->singleRequestBatchSkips = 1;
    }
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  if(!sim_locate_cuda_requests_share_inputs(requests))
  {
    vector<SimLocateResult> results;
    results.reserve(requests.size());
    double totalGpuSeconds = 0.0;
    for(size_t i = 0; i < requests.size(); ++i)
    {
      SimLocateResult result;
      if(!sim_locate_cuda_locate_region(requests[i],&result,errorOut))
      {
        outResults->clear();
        if(batchResult != NULL)
        {
          *batchResult = SimLocateCudaBatchResult();
        }
        return false;
      }
      totalGpuSeconds += result.gpuSeconds;
      results.push_back(result);
    }
    *outResults = results;
    if(batchResult != NULL)
    {
      batchResult->gpuSeconds = totalGpuSeconds;
      batchResult->usedCuda = true;
      batchResult->taskCount = static_cast<uint64_t>(requests.size());
      batchResult->launchCount = static_cast<uint64_t>(requests.size());
      batchResult->usedSharedInputBatchPath = false;
    }
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  const SimLocateCudaRequest &base = requests[0];
  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t deviceStatus = cudaGetDevice(&device);
  if(deviceStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(deviceStatus);
    return false;
  }

  SimLocateCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_locate_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_locate_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_locate_cuda_capacity_locked(*context,
                                             base.queryLength,
                                             base.targetLength,
                                             base.blockedWordStride,
                                             base.candidateCount,
                                             errorOut))
  {
    return false;
  }
  if(!ensure_sim_locate_cuda_batch_capacity_locked(*context,
                                                   base.queryLength,
                                                   base.targetLength,
                                                   static_cast<int>(requests.size()),
                                                   errorOut))
  {
    return false;
  }

  const size_t aBytes = static_cast<size_t>(base.queryLength + 1) * sizeof(char);
  const size_t bBytes = static_cast<size_t>(base.targetLength + 1) * sizeof(char);
  const uint64_t aHash = sim_locate_cuda_bytes_hash(base.A,aBytes);
  const uint64_t bHash = sim_locate_cuda_bytes_hash(base.B,bBytes);
  cudaError_t status = cudaSuccess;
  if(sim_locate_cuda_input_cache_matches(*context,base,aHash,bHash))
  {
    if(batchResult != NULL)
    {
      batchResult->inputH2DCacheHits = 2;
    }
  }
  else
  {
    status = cudaMemcpy(context->ADevice,
                        base.A,
                        aBytes,
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      sim_locate_cuda_invalidate_input_cache(*context);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    status = cudaMemcpy(context->BDevice,
                        base.B,
                        bBytes,
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      sim_locate_cuda_invalidate_input_cache(*context);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    sim_locate_cuda_store_input_cache(*context,base,aHash,bHash);
    if(batchResult != NULL)
    {
      batchResult->inputH2DCopies = 2;
    }
  }
  const uint64_t scoreMatrixHash = sim_locate_cuda_score_matrix_hash(base.scoreMatrix);
  if(sim_locate_cuda_score_matrix_cache_matches(*context,base.scoreMatrix,scoreMatrixHash))
  {
    if(batchResult != NULL)
    {
      batchResult->scoreMatrixH2DCacheHits = 1;
    }
  }
  else
  {
    status = cudaMemcpy(context->scoreMatrixDevice,
                        base.scoreMatrix,
                        static_cast<size_t>(128 * 128) * sizeof(int),
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess)
    {
      context->scoreMatrixCacheValid = false;
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    sim_locate_cuda_store_score_matrix_cache(*context,base.scoreMatrix,scoreMatrixHash);
    if(batchResult != NULL)
    {
      batchResult->scoreMatrixH2DCopies = 1;
    }
  }
  if(base.blockedWords != NULL && base.blockedWordStride > 0)
  {
    const size_t blockedWordCount =
      static_cast<size_t>(base.queryLength + 1) * static_cast<size_t>(base.blockedWordStride);
    const uint64_t blockedWordsHash =
      sim_locate_cuda_words_hash(base.blockedWords,blockedWordCount);
    if(sim_locate_cuda_blocked_words_cache_matches(*context,base,blockedWordCount,blockedWordsHash))
    {
      if(batchResult != NULL)
      {
        batchResult->blockedWordsH2DCacheHits = 1;
      }
    }
    else
    {
      status = cudaMemcpy(context->blockedWordsDevice,
                          base.blockedWords,
                          blockedWordCount * sizeof(uint64_t),
                          cudaMemcpyHostToDevice);
      if(status != cudaSuccess)
      {
        sim_locate_cuda_invalidate_blocked_words_cache(*context);
        if(errorOut != NULL) *errorOut = cuda_error_string(status);
        return false;
      }
      sim_locate_cuda_store_blocked_words_cache(*context,base,blockedWordCount,blockedWordsHash);
      if(batchResult != NULL)
      {
        batchResult->blockedWordsH2DCopies = 1;
      }
    }
  }
  if(base.candidateCount > 0)
  {
    const uint64_t candidatesHash =
      sim_locate_cuda_candidate_hash(base.candidates,base.candidateCount);
    if(sim_locate_cuda_candidates_cache_matches(*context,base,candidatesHash))
    {
      if(batchResult != NULL)
      {
        batchResult->candidateH2DCacheHits = 1;
      }
    }
    else
    {
      status = cudaMemcpy(context->candidatesDevice,
                          base.candidates,
                          static_cast<size_t>(base.candidateCount) * sizeof(SimScanCudaCandidateState),
                          cudaMemcpyHostToDevice);
      if(status != cudaSuccess)
      {
        sim_locate_cuda_invalidate_candidates_cache(*context);
        if(errorOut != NULL) *errorOut = cuda_error_string(status);
        return false;
      }
      sim_locate_cuda_store_candidates_cache(*context,base,candidatesHash);
      if(batchResult != NULL)
      {
        batchResult->candidateH2DCopies = 1;
      }
    }
  }

  vector<SimLocateCudaDeviceRequest> deviceRequests(requests.size());
  for(size_t i = 0; i < requests.size(); ++i)
  {
    deviceRequests[i].rowStart = requests[i].rowStart;
    deviceRequests[i].rowEnd = requests[i].rowEnd;
    deviceRequests[i].colStart = requests[i].colStart;
    deviceRequests[i].colEnd = requests[i].colEnd;
    deviceRequests[i].minRowBound = requests[i].minRowBound;
    deviceRequests[i].minColBound = requests[i].minColBound;
    deviceRequests[i].runningMin = requests[i].runningMin;
    deviceRequests[i].gapOpen = requests[i].gapOpen;
    deviceRequests[i].gapExtend = requests[i].gapExtend;
  }
  status = cudaMemcpy(context->batchRequestsDevice,
                      deviceRequests.data(),
                      static_cast<size_t>(deviceRequests.size()) * sizeof(SimLocateCudaDeviceRequest),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  sim_locate_cuda_batch_kernel<<<static_cast<unsigned int>(requests.size()), 1>>>(
    context->batchRequestsDevice,
    static_cast<int>(requests.size()),
    context->ADevice,
    context->BDevice,
    context->scoreMatrixDevice,
    (base.blockedWords != NULL && base.blockedWordStride > 0) ? context->blockedWordsDevice : NULL,
    base.blockedWordStride,
    (base.candidateCount > 0) ? context->candidatesDevice : NULL,
    base.candidateCount,
    base.targetLength + 1,
    base.queryLength + 1,
    context->batchCCDevice,
    context->batchDDDevice,
    context->batchRRDevice,
    context->batchSSDevice,
    context->batchEEDevice,
    context->batchFFDevice,
    context->batchHHDevice,
    context->batchWWDevice,
    context->batchIIDevice,
    context->batchJJDevice,
    context->batchXXDevice,
    context->batchYYDevice,
    context->batchResultsDevice);
  status = cudaGetLastError();
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  vector<SimLocateCudaDeviceResult> deviceResults(requests.size());
  status = cudaMemcpy(deviceResults.data(),
                      context->batchResultsDevice,
                      static_cast<size_t>(deviceResults.size()) * sizeof(SimLocateCudaDeviceResult),
                      cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  float elapsedMs = 0.0f;
  status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  const double perRequestGpuSeconds =
    requests.empty() ? 0.0 : (static_cast<double>(elapsedMs) / 1000.0) / static_cast<double>(requests.size());
  outResults->resize(deviceResults.size());
  for(size_t i = 0; i < deviceResults.size(); ++i)
  {
    const SimLocateCudaDeviceResult &deviceResult = deviceResults[i];
    SimLocateResult &outResult = (*outResults)[i];
    outResult.hasUpdateRegion = deviceResult.hasUpdateRegion != 0;
    outResult.rowStart = static_cast<long>(deviceResult.rowStart);
    outResult.rowEnd = static_cast<long>(deviceResult.rowEnd);
    outResult.colStart = static_cast<long>(deviceResult.colStart);
    outResult.colEnd = static_cast<long>(deviceResult.colEnd);
    outResult.locateCellCount = static_cast<uint64_t>(deviceResult.locateCellCount);
    outResult.baseCellCount = static_cast<uint64_t>(deviceResult.baseCellCount);
    outResult.expansionCellCount = static_cast<uint64_t>(deviceResult.expansionCellCount);
    outResult.stopByNoCross = deviceResult.stopByNoCross != 0;
    outResult.stopByBoundary = deviceResult.stopByBoundary != 0;
    outResult.usedCuda = true;
    outResult.gpuSeconds = perRequestGpuSeconds;
  }

  if(batchResult != NULL)
  {
    batchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    batchResult->usedCuda = true;
    batchResult->taskCount = static_cast<uint64_t>(requests.size());
    batchResult->launchCount = 1;
    batchResult->usedSharedInputBatchPath = requests.size() > 1;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}
