#include "sim_traceback_cuda.h"
#include "sim_cuda_runtime.h"

#include <algorithm>
#include <chrono>
#include <memory>
#include <mutex>

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

__device__ __forceinline__ bool sim_is_acgt(char c)
{
  return c == 'A' || c == 'C' || c == 'G' || c == 'T';
}

__device__ __forceinline__ int sim_sub_score(char a,char b,int matchScore,int mismatchScore)
{
  if(sim_is_acgt(a) && sim_is_acgt(b))
  {
    return (a == b) ? matchScore : mismatchScore;
  }
  return 0;
}

__device__ __forceinline__ bool sim_diag_blocked(const uint64_t *blockedWords,
                                                 int blockedWordStart,
                                                 int blockedWordCount,
                                                 int blockedWordStride,
                                                 int globalColStart,
                                                 int localRow,
                                                 int dpCol)
{
  if(blockedWords == NULL || blockedWordCount <= 0)
  {
    return false;
  }
  const int globalCol = globalColStart - 1 + dpCol;
  const int wordIndex = globalCol >> 6;
  const int localWord = wordIndex - blockedWordStart;
  if(localWord < 0 || localWord >= blockedWordCount)
  {
    return false;
  }
  const int stride = blockedWordStride > 0 ? blockedWordStride : blockedWordCount;
  const uint64_t word = blockedWords[static_cast<size_t>(localRow) * static_cast<size_t>(stride) + static_cast<size_t>(localWord)];
  const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<unsigned int>(globalCol) & 63u);
  return (word & mask) != 0;
}

__device__ __forceinline__ unsigned char sim_tb_get_h_state(const unsigned char *dir,
                                                            int leadingDim,
                                                            int i,
                                                            int j)
{
  if(i == 0 && j == 0)
  {
    return 0;
  }
  if(i == 0)
  {
    return 2;
  }
  if(j == 0)
  {
    return 1;
  }
  const size_t off = static_cast<size_t>(i) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
  return static_cast<unsigned char>(dir[off] & 0x03u);
}

struct SimTracebackCudaContext
{
  SimTracebackCudaContext():
    initialized(false),
    device(0),
    capacityQuery(0),
    capacityTarget(0),
    leadingDim(0),
    tileRowsCap(0),
    tileColsCap(0),
    ADevice(NULL),
    BDevice(NULL),
    dirDevice(NULL),
    bottomHDevice(NULL),
    bottomDDevice(NULL),
    rightHDevice(NULL),
    rightEDevice(NULL),
    blockedWordsDevice(NULL),
    blockedCapacityWords(0),
    opsDevice(NULL),
    opsCapacity(0),
    opsLenDevice(NULL),
    hadTieDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL)
  {
  }

  bool initialized;
  int device;
  int capacityQuery;
  int capacityTarget;
  int leadingDim;
  int tileRowsCap;
  int tileColsCap;

  char *ADevice;
  char *BDevice;

  unsigned char *dirDevice;
  int *bottomHDevice;
  int *bottomDDevice;
  int *rightHDevice;
  int *rightEDevice;

  uint64_t *blockedWordsDevice;
  size_t blockedCapacityWords;

  unsigned char *opsDevice;
  int opsCapacity;
  int *opsLenDevice;
  int *hadTieDevice;

  cudaEvent_t startEvent;
  cudaEvent_t stopEvent;
};

struct SimTracebackCudaDeviceBatchRequest
{
  int queryLength;
  int targetLength;
  int matchScore;
  int mismatchScore;
  int gapOpen;
  int gapExtend;
  int globalColStart;
  int blockedWordStart;
  int blockedWordCount;
  int blockedWordStride;
};

static mutex sim_traceback_cuda_contexts_mutex;
static vector< vector< unique_ptr<SimTracebackCudaContext> > > sim_traceback_cuda_contexts;
static vector< vector< unique_ptr<mutex> > > sim_traceback_cuda_context_mutexes;

static bool get_sim_traceback_cuda_context_for_device_slot(int device,
                                                           int slot,
                                                           SimTracebackCudaContext **contextOut,
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

  lock_guard<mutex> lock(sim_traceback_cuda_contexts_mutex);
  if(sim_traceback_cuda_contexts.size() <= static_cast<size_t>(device))
  {
    sim_traceback_cuda_contexts.resize(static_cast<size_t>(device) + 1);
    sim_traceback_cuda_context_mutexes.resize(static_cast<size_t>(device) + 1);
  }
  vector< unique_ptr<SimTracebackCudaContext> > &deviceContexts =
    sim_traceback_cuda_contexts[static_cast<size_t>(device)];
  vector< unique_ptr<mutex> > &deviceMutexes =
    sim_traceback_cuda_context_mutexes[static_cast<size_t>(device)];
  if(deviceContexts.size() <= static_cast<size_t>(slot))
  {
    deviceContexts.resize(static_cast<size_t>(slot) + 1);
    deviceMutexes.resize(static_cast<size_t>(slot) + 1);
  }
  if(!deviceContexts[static_cast<size_t>(slot)])
  {
    deviceContexts[static_cast<size_t>(slot)].reset(new SimTracebackCudaContext());
  }
  if(!deviceMutexes[static_cast<size_t>(slot)])
  {
    deviceMutexes[static_cast<size_t>(slot)].reset(new mutex());
  }

  *contextOut = deviceContexts[static_cast<size_t>(slot)].get();
  *mutexOut = deviceMutexes[static_cast<size_t>(slot)].get();
  return true;
}

static bool ensure_sim_traceback_cuda_initialized_locked(SimTracebackCudaContext &context,int device,string *errorOut)
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

static bool ensure_sim_traceback_cuda_capacity_locked(SimTracebackCudaContext &context,
                                                      int queryLength,
                                                      int targetLength,
                                                      int blockedWordCount,
                                                      string *errorOut)
{
  const int neededOps = max(1, queryLength + targetLength + 2);
  const size_t neededBlockedWords = (blockedWordCount > 0 && queryLength > 0)
                                     ? (static_cast<size_t>(queryLength) * static_cast<size_t>(blockedWordCount))
                                     : 0u;

  if(queryLength <= context.capacityQuery &&
     targetLength <= context.capacityTarget &&
     neededBlockedWords <= context.blockedCapacityWords &&
     neededOps <= context.opsCapacity)
  {
    return true;
  }

  const int newCapQuery = max(context.capacityQuery, queryLength);
  const int newCapTarget = max(context.capacityTarget, targetLength);
  const int newLeadingDim = newCapTarget + 1;
  const size_t matrixCells = static_cast<size_t>(newCapQuery + 1) * static_cast<size_t>(newLeadingDim);
  const size_t newBlockedCapWords = max(context.blockedCapacityWords, neededBlockedWords);
  const int newOpsCapacity = max(context.opsCapacity, neededOps);

  const int T = 32;
  const int newTileRowsCap = (newCapQuery + T - 1) / T;
  const int newTileColsCap = (newCapTarget + T - 1) / T;
  const size_t tileCount = static_cast<size_t>(newTileRowsCap) * static_cast<size_t>(newTileColsCap);
  const size_t boundaryCount = tileCount * static_cast<size_t>(T + 1);
  const size_t boundaryBytes = boundaryCount * sizeof(int);

  char *newADevice = NULL;
  char *newBDevice = NULL;
  unsigned char *newDirDevice = NULL;
  int *newBottomHDevice = NULL;
  int *newBottomDDevice = NULL;
  int *newRightHDevice = NULL;
  int *newRightEDevice = NULL;

  const size_t aBytes = static_cast<size_t>(newCapQuery + 1) * sizeof(char);
  const size_t bBytes = static_cast<size_t>(newCapTarget + 1) * sizeof(char);
  const size_t dirBytes = matrixCells * sizeof(unsigned char);

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newADevice), aBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newBDevice), bBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  status = cudaMalloc(reinterpret_cast<void **>(&newDirDevice), dirBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  if(boundaryCount > 0)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&newBottomHDevice), boundaryBytes);
    if(status != cudaSuccess)
    {
      cudaFree(newADevice);
      cudaFree(newBDevice);
      cudaFree(newDirDevice);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    status = cudaMalloc(reinterpret_cast<void **>(&newBottomDDevice), boundaryBytes);
    if(status != cudaSuccess)
    {
      cudaFree(newADevice);
      cudaFree(newBDevice);
      cudaFree(newDirDevice);
      cudaFree(newBottomHDevice);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    status = cudaMalloc(reinterpret_cast<void **>(&newRightHDevice), boundaryBytes);
    if(status != cudaSuccess)
    {
      cudaFree(newADevice);
      cudaFree(newBDevice);
      cudaFree(newDirDevice);
      cudaFree(newBottomHDevice);
      cudaFree(newBottomDDevice);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    status = cudaMalloc(reinterpret_cast<void **>(&newRightEDevice), boundaryBytes);
    if(status != cudaSuccess)
    {
      cudaFree(newADevice);
      cudaFree(newBDevice);
      cudaFree(newDirDevice);
      cudaFree(newBottomHDevice);
      cudaFree(newBottomDDevice);
      cudaFree(newRightHDevice);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
  }

  uint64_t *newBlockedWordsDevice = NULL;
  if(newBlockedCapWords > 0)
  {
    const size_t bytes = newBlockedCapWords * sizeof(uint64_t);
    status = cudaMalloc(reinterpret_cast<void **>(&newBlockedWordsDevice), bytes);
    if(status != cudaSuccess)
    {
      cudaFree(newADevice);
      cudaFree(newBDevice);
      cudaFree(newDirDevice);
      if(newBottomHDevice != NULL) cudaFree(newBottomHDevice);
      if(newBottomDDevice != NULL) cudaFree(newBottomDDevice);
      if(newRightHDevice != NULL) cudaFree(newRightHDevice);
      if(newRightEDevice != NULL) cudaFree(newRightEDevice);
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
  }

  unsigned char *newOpsDevice = NULL;
  int *newOpsLenDevice = NULL;
  int *newHadTieDevice = NULL;
  status = cudaMalloc(reinterpret_cast<void **>(&newOpsDevice), static_cast<size_t>(newOpsCapacity) * sizeof(unsigned char));
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newDirDevice);
    if(newBottomHDevice != NULL) cudaFree(newBottomHDevice);
    if(newBottomDDevice != NULL) cudaFree(newBottomDDevice);
    if(newRightHDevice != NULL) cudaFree(newRightHDevice);
    if(newRightEDevice != NULL) cudaFree(newRightEDevice);
    if(newBlockedWordsDevice != NULL) cudaFree(newBlockedWordsDevice);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newOpsLenDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newDirDevice);
    if(newBottomHDevice != NULL) cudaFree(newBottomHDevice);
    if(newBottomDDevice != NULL) cudaFree(newBottomDDevice);
    if(newRightHDevice != NULL) cudaFree(newRightHDevice);
    if(newRightEDevice != NULL) cudaFree(newRightEDevice);
    if(newBlockedWordsDevice != NULL) cudaFree(newBlockedWordsDevice);
    cudaFree(newOpsDevice);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newHadTieDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(newADevice);
    cudaFree(newBDevice);
    cudaFree(newDirDevice);
    if(newBottomHDevice != NULL) cudaFree(newBottomHDevice);
    if(newBottomDDevice != NULL) cudaFree(newBottomDDevice);
    if(newRightHDevice != NULL) cudaFree(newRightHDevice);
    if(newRightEDevice != NULL) cudaFree(newRightEDevice);
    if(newBlockedWordsDevice != NULL) cudaFree(newBlockedWordsDevice);
    cudaFree(newOpsDevice);
    cudaFree(newOpsLenDevice);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  if(context.ADevice != NULL) cudaFree(context.ADevice);
  if(context.BDevice != NULL) cudaFree(context.BDevice);
  if(context.dirDevice != NULL) cudaFree(context.dirDevice);
  if(context.bottomHDevice != NULL) cudaFree(context.bottomHDevice);
  if(context.bottomDDevice != NULL) cudaFree(context.bottomDDevice);
  if(context.rightHDevice != NULL) cudaFree(context.rightHDevice);
  if(context.rightEDevice != NULL) cudaFree(context.rightEDevice);
  if(context.blockedWordsDevice != NULL) cudaFree(context.blockedWordsDevice);
  if(context.opsDevice != NULL) cudaFree(context.opsDevice);
  if(context.opsLenDevice != NULL) cudaFree(context.opsLenDevice);
  if(context.hadTieDevice != NULL) cudaFree(context.hadTieDevice);

  context.capacityQuery = newCapQuery;
  context.capacityTarget = newCapTarget;
  context.leadingDim = newLeadingDim;
  context.tileRowsCap = newTileRowsCap;
  context.tileColsCap = newTileColsCap;
  context.ADevice = newADevice;
  context.BDevice = newBDevice;
  context.dirDevice = newDirDevice;
  context.bottomHDevice = newBottomHDevice;
  context.bottomDDevice = newBottomDDevice;
  context.rightHDevice = newRightHDevice;
  context.rightEDevice = newRightEDevice;

  context.blockedWordsDevice = newBlockedWordsDevice;
  context.blockedCapacityWords = newBlockedCapWords;

  context.opsDevice = newOpsDevice;
  context.opsLenDevice = newOpsLenDevice;
  context.hadTieDevice = newHadTieDevice;
  context.opsCapacity = newOpsCapacity;

  return true;
}

__global__ void sim_tb_tile_wavefront_kernel(const char *A,
                                             const char *B,
                                             int M,
                                             int N,
                                             int leadingDim,
                                             int tileDiag,
                                             int tileRows,
                                             int tileCols,
                                             int tileColsStride,
                                             int matchScore,
                                             int mismatchScore,
                                             int gapOpen,
                                             int gapExtend,
                                             int globalColStart,
                                             const uint64_t *blockedWords,
                                             int blockedWordStart,
                                             int blockedWordCount,
                                             int *bottomH,
                                             int *bottomD,
                                             int *rightH,
                                             int *rightE,
                                             unsigned char *dir)
{
  const int T = 32;
  const int lane = static_cast<int>(threadIdx.x);
  if(lane >= T)
  {
    return;
  }

  const int infNeg = -0x3f3f3f3f;

  const int tileRowStart = max(0, tileDiag - (tileCols - 1));
  const int tileRow = tileRowStart + static_cast<int>(blockIdx.x);
  const int tileCol = tileDiag - tileRow;
  if(tileRow < 0 || tileCol < 0 || tileRow >= tileRows || tileCol >= tileCols)
  {
    return;
  }

  const int iStart = tileRow * T + 1;
  const int jStart = tileCol * T + 1;
  const int height = min(T, M - tileRow * T);
  const int width = min(T, N - tileCol * T);
  if(height <= 0 || width <= 0)
  {
    return;
  }

  __shared__ int Hs[(T + 1) * (T + 1)];
  __shared__ int Ds[(T + 1) * (T + 1)];
  __shared__ int Es[(T + 1) * (T + 1)];

  const int tileIndex = tileRow * tileColsStride + tileCol;
  const int aboveIndex = (tileRow > 0) ? ((tileRow - 1) * tileColsStride + tileCol) : -1;
  const int leftIndex = (tileCol > 0) ? (tileRow * tileColsStride + (tileCol - 1)) : -1;
  const int boundaryBase = tileIndex * (T + 1);
  const int aboveBoundaryBase = aboveIndex * (T + 1);
  const int leftBoundaryBase = leftIndex * (T + 1);

  if(lane == 0)
  {
    if(tileRow == 0)
    {
      const int globalJ = (jStart - 1);
      const int h = (globalJ == 0) ? 0 : -(gapOpen + gapExtend * globalJ);
      Hs[0] = h;
      Ds[0] = infNeg;
    }
    else
    {
      Hs[0] = bottomH[aboveBoundaryBase + 0];
      Ds[0] = bottomD[aboveBoundaryBase + 0];
    }

    if(tileCol == 0)
    {
      const int globalI = (iStart - 1);
      const int h = (globalI == 0) ? 0 : -(gapOpen + gapExtend * globalI);
      Hs[0] = h;
      Es[0] = infNeg;
    }
    else
    {
      Hs[0] = rightH[leftBoundaryBase + 0];
      Es[0] = rightE[leftBoundaryBase + 0];
    }
  }
  const int idx = lane + 1;
  if(idx <= width)
  {
    if(tileRow == 0)
    {
      const int globalJ = (jStart - 1) + idx;
      const int h = (globalJ == 0) ? 0 : -(gapOpen + gapExtend * globalJ);
      Hs[idx] = h;
      Ds[idx] = infNeg;
    }
    else
    {
      Hs[idx] = bottomH[aboveBoundaryBase + idx];
      Ds[idx] = bottomD[aboveBoundaryBase + idx];
    }
  }
  if(idx <= height)
  {
    if(tileCol == 0)
    {
      const int globalI = (iStart - 1) + idx;
      const int h = (globalI == 0) ? 0 : -(gapOpen + gapExtend * globalI);
      Hs[idx * (T + 1)] = h;
      Es[idx * (T + 1)] = infNeg;
    }
    else
    {
      Hs[idx * (T + 1)] = rightH[leftBoundaryBase + idx];
      Es[idx * (T + 1)] = rightE[leftBoundaryBase + idx];
    }
  }
  __syncwarp();

  const unsigned char DIR_STATE_MASK = 0x03;
  const unsigned char DIR_D_FROM_EXT = 0x04;
  const unsigned char DIR_E_FROM_EXT = 0x08;
  const unsigned char DIR_H_TIE = 0x10;
  const unsigned char DIR_D_TIE = 0x20;
  const unsigned char DIR_E_TIE = 0x40;

  const int maxDiag = height + width;
  for(int diag = 2; diag <= maxDiag; ++diag)
  {
    const int j = lane + 1;
    const int i = diag - j;
    if(i >= 1 && i <= height && j >= 1 && j <= width)
    {
      const int dpI = tileRow * T + i;
      const int dpJ = tileCol * T + j;
      const int localRow = dpI - 1;
      const bool blocked = sim_diag_blocked(blockedWords,
                                            blockedWordStart,
                                            blockedWordCount,
                                            blockedWordCount,
                                            globalColStart,
                                            localRow,
                                            dpJ);
      const char a = A[dpI];
      const char b = B[dpJ];
      const int sub = sim_sub_score(a,b,matchScore,mismatchScore);

      const int hDiag = Hs[(i - 1) * (T + 1) + (j - 1)];
      const int diagScore = blocked ? infNeg : (hDiag + sub);

      const int hLeft = Hs[i * (T + 1) + (j - 1)];
      const int eLeft = Es[i * (T + 1) + (j - 1)];
      const int openE = hLeft - gapOpen - gapExtend;
      const int extendE = eLeft - gapExtend;
      const bool eFromExt = (extendE >= openE);
      const int eScore = eFromExt ? extendE : openE;
      const bool eTie = (openE == extendE);

      const int hUp = Hs[(i - 1) * (T + 1) + j];
      const int dUp = Ds[(i - 1) * (T + 1) + j];
      const int openD = hUp - gapOpen - gapExtend;
      const int extendD = dUp - gapExtend;
      const bool dFromExt = (extendD >= openD);
      const int dScore = dFromExt ? extendD : openD;
      const bool dTie = (openD == extendD);

      int best = diagScore;
      unsigned char bestState = 0;
      if(dScore > best)
      {
        best = dScore;
        bestState = 1;
      }
      if(eScore > best)
      {
        best = eScore;
        bestState = 2;
      }

      Hs[i * (T + 1) + j] = best;
      Ds[i * (T + 1) + j] = dScore;
      Es[i * (T + 1) + j] = eScore;

      bool hTie = false;
      if(best > infNeg)
      {
        if(bestState == 0)
        {
          hTie = (dScore == best || eScore == best);
        }
        else if(bestState == 1)
        {
          hTie = (diagScore == best || eScore == best);
        }
        else
        {
          hTie = (diagScore == best || dScore == best);
        }
      }

      unsigned char dirByte = static_cast<unsigned char>(bestState & DIR_STATE_MASK);
      if(dFromExt) dirByte |= DIR_D_FROM_EXT;
      if(eFromExt) dirByte |= DIR_E_FROM_EXT;
      if(hTie) dirByte |= DIR_H_TIE;
      if(dTie) dirByte |= DIR_D_TIE;
      if(eTie) dirByte |= DIR_E_TIE;
      const size_t off = static_cast<size_t>(dpI) * static_cast<size_t>(leadingDim) + static_cast<size_t>(dpJ);
      dir[off] = dirByte;
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    bottomH[boundaryBase + 0] = Hs[height * (T + 1) + 0];
    bottomD[boundaryBase + 0] = Ds[height * (T + 1) + 0];
    rightH[boundaryBase + 0] = Hs[0 * (T + 1) + width];
    rightE[boundaryBase + 0] = Es[0 * (T + 1) + width];
  }
  if(idx <= width)
  {
    bottomH[boundaryBase + idx] = Hs[height * (T + 1) + idx];
    bottomD[boundaryBase + idx] = Ds[height * (T + 1) + idx];
  }
  if(idx <= height)
  {
    rightH[boundaryBase + idx] = Hs[idx * (T + 1) + width];
    rightE[boundaryBase + idx] = Es[idx * (T + 1) + width];
  }
}

__global__ void sim_tb_backtrace_kernel(const unsigned char *dir,
                                        int M,
                                        int N,
                                        int leadingDim,
                                        unsigned char *opsOut,
                                        int opsCapacity,
                                        int *opsLenOut,
                                        int *hadTieOut)
{
  if(blockIdx.x != 0 || threadIdx.x != 0)
  {
    return;
  }

  const unsigned char DIR_STATE_MASK = 0x03;
  const unsigned char DIR_D_FROM_EXT = 0x04;
  const unsigned char DIR_E_FROM_EXT = 0x08;
  const unsigned char DIR_H_TIE = 0x10;
  const unsigned char DIR_D_TIE = 0x20;
  const unsigned char DIR_E_TIE = 0x40;

  int i = M;
  int j = N;
  int opsLen = 0;
  int hadTie = 0;
  unsigned char curState = sim_tb_get_h_state(dir,leadingDim,i,j);

  while(i > 0 || j > 0)
  {
    if(opsLen + 1 >= opsCapacity)
    {
      break;
    }

    if(i == 0)
    {
      opsOut[opsLen++] = 1;
      --j;
      curState = 2;
      continue;
    }
    if(j == 0)
    {
      opsOut[opsLen++] = 2;
      --i;
      curState = 1;
      continue;
    }

    const size_t off = static_cast<size_t>(i) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
    const unsigned char dirByte = dir[off];
    const unsigned char hState = static_cast<unsigned char>(dirByte & DIR_STATE_MASK);

    if(curState == 0)
    {
      if((dirByte & DIR_H_TIE) != 0)
      {
        hadTie = 1;
      }
      opsOut[opsLen++] = 0;
      --i;
      --j;
      curState = sim_tb_get_h_state(dir,leadingDim,i,j);
      continue;
    }
    if(curState == 1)
    {
      if((dirByte & DIR_D_TIE) != 0)
      {
        hadTie = 1;
      }
      if(hState == 1 && (dirByte & DIR_H_TIE) != 0)
      {
        hadTie = 1;
      }
      const bool fromExt = (dirByte & DIR_D_FROM_EXT) != 0;
      opsOut[opsLen++] = 2;
      --i;
      if(fromExt)
      {
        curState = 1;
      }
      else
      {
        curState = sim_tb_get_h_state(dir,leadingDim,i,j);
      }
      continue;
    }

    if((dirByte & DIR_E_TIE) != 0)
    {
      hadTie = 1;
    }
    if(hState == 2 && (dirByte & DIR_H_TIE) != 0)
    {
      hadTie = 1;
    }
    const bool fromExt = (dirByte & DIR_E_FROM_EXT) != 0;
    opsOut[opsLen++] = 1;
    --j;
    if(fromExt)
    {
      curState = 2;
    }
    else
    {
      curState = sim_tb_get_h_state(dir,leadingDim,i,j);
    }
  }

  *opsLenOut = opsLen;
  *hadTieOut = hadTie;
}

__global__ void sim_tb_tile_wavefront_kernel_batched(const char *A,
                                                     const char *B,
                                                     const SimTracebackCudaDeviceBatchRequest *requestMeta,
                                                     int requestCount,
                                                     int queryStride,
                                                     int targetStride,
                                                     int leadingDim,
                                                     int tileDiag,
                                                     int maxTilesPerDiag,
                                                     int tileColsStride,
                                                     int boundaryStride,
                                                     const uint64_t *blockedWords,
                                                     int blockedSliceStride,
                                                     int *bottomH,
                                                     int *bottomD,
                                                     int *rightH,
                                                     int *rightE,
                                                     unsigned char *dir)
{
  const int requestIndex = static_cast<int>(blockIdx.x) / maxTilesPerDiag;
  const int tileRank = static_cast<int>(blockIdx.x) % maxTilesPerDiag;
  if(requestIndex < 0 || requestIndex >= requestCount)
  {
    return;
  }

  const SimTracebackCudaDeviceBatchRequest meta = requestMeta[requestIndex];
  const int M = meta.queryLength;
  const int N = meta.targetLength;
  const int T = 32;
  const int tileRows = (M + T - 1) / T;
  const int tileCols = (N + T - 1) / T;
  const int tileRowStart = max(0, tileDiag - (tileCols - 1));
  const int tileRowEnd = min(tileDiag, tileRows - 1);
  const int tileCount = tileRowEnd >= tileRowStart ? (tileRowEnd - tileRowStart + 1) : 0;
  if(tileRank < 0 || tileRank >= tileCount)
  {
    return;
  }

  const int lane = static_cast<int>(threadIdx.x);
  if(lane >= T)
  {
    return;
  }

  const int tileRow = tileRowStart + tileRank;
  const int tileCol = tileDiag - tileRow;
  if(tileRow < 0 || tileCol < 0 || tileRow >= tileRows || tileCol >= tileCols)
  {
    return;
  }

  const char *requestA = A + static_cast<size_t>(requestIndex) * static_cast<size_t>(queryStride);
  const char *requestB = B + static_cast<size_t>(requestIndex) * static_cast<size_t>(targetStride);
  unsigned char *requestDir = dir + static_cast<size_t>(requestIndex) * static_cast<size_t>(leadingDim) * static_cast<size_t>(queryStride);
  int *requestBottomH = bottomH + static_cast<size_t>(requestIndex) * static_cast<size_t>(boundaryStride);
  int *requestBottomD = bottomD + static_cast<size_t>(requestIndex) * static_cast<size_t>(boundaryStride);
  int *requestRightH = rightH + static_cast<size_t>(requestIndex) * static_cast<size_t>(boundaryStride);
  int *requestRightE = rightE + static_cast<size_t>(requestIndex) * static_cast<size_t>(boundaryStride);
  const uint64_t *requestBlockedWords =
    (blockedWords != NULL && blockedSliceStride > 0) ?
    (blockedWords + static_cast<size_t>(requestIndex) * static_cast<size_t>(blockedSliceStride)) : NULL;

  const int infNeg = -0x3f3f3f3f;
  const int iStart = tileRow * T + 1;
  const int jStart = tileCol * T + 1;
  const int height = min(T, M - tileRow * T);
  const int width = min(T, N - tileCol * T);
  if(height <= 0 || width <= 0)
  {
    return;
  }

  __shared__ int Hs[(T + 1) * (T + 1)];
  __shared__ int Ds[(T + 1) * (T + 1)];
  __shared__ int Es[(T + 1) * (T + 1)];

  const int tileIndex = tileRow * tileColsStride + tileCol;
  const int aboveIndex = (tileRow > 0) ? ((tileRow - 1) * tileColsStride + tileCol) : -1;
  const int leftIndex = (tileCol > 0) ? (tileRow * tileColsStride + (tileCol - 1)) : -1;
  const int boundaryBase = tileIndex * (T + 1);
  const int aboveBoundaryBase = aboveIndex * (T + 1);
  const int leftBoundaryBase = leftIndex * (T + 1);

  if(lane == 0)
  {
    if(tileRow == 0)
    {
      const int globalJ = (jStart - 1);
      const int h = (globalJ == 0) ? 0 : -(meta.gapOpen + meta.gapExtend * globalJ);
      Hs[0] = h;
      Ds[0] = infNeg;
    }
    else
    {
      Hs[0] = requestBottomH[aboveBoundaryBase + 0];
      Ds[0] = requestBottomD[aboveBoundaryBase + 0];
    }

    if(tileCol == 0)
    {
      const int globalI = (iStart - 1);
      const int h = (globalI == 0) ? 0 : -(meta.gapOpen + meta.gapExtend * globalI);
      Hs[0] = h;
      Es[0] = infNeg;
    }
    else
    {
      Hs[0] = requestRightH[leftBoundaryBase + 0];
      Es[0] = requestRightE[leftBoundaryBase + 0];
    }
  }
  const int idx = lane + 1;
  if(idx <= width)
  {
    if(tileRow == 0)
    {
      const int globalJ = (jStart - 1) + idx;
      const int h = (globalJ == 0) ? 0 : -(meta.gapOpen + meta.gapExtend * globalJ);
      Hs[idx] = h;
      Ds[idx] = infNeg;
    }
    else
    {
      Hs[idx] = requestBottomH[aboveBoundaryBase + idx];
      Ds[idx] = requestBottomD[aboveBoundaryBase + idx];
    }
  }
  if(idx <= height)
  {
    if(tileCol == 0)
    {
      const int globalI = (iStart - 1) + idx;
      const int h = (globalI == 0) ? 0 : -(meta.gapOpen + meta.gapExtend * globalI);
      Hs[idx * (T + 1)] = h;
      Es[idx * (T + 1)] = infNeg;
    }
    else
    {
      Hs[idx * (T + 1)] = requestRightH[leftBoundaryBase + idx];
      Es[idx * (T + 1)] = requestRightE[leftBoundaryBase + idx];
    }
  }
  __syncwarp();

  const unsigned char DIR_STATE_MASK = 0x03;
  const unsigned char DIR_D_FROM_EXT = 0x04;
  const unsigned char DIR_E_FROM_EXT = 0x08;
  const unsigned char DIR_H_TIE = 0x10;
  const unsigned char DIR_D_TIE = 0x20;
  const unsigned char DIR_E_TIE = 0x40;

  const int maxDiag = height + width;
  for(int diag = 2; diag <= maxDiag; ++diag)
  {
    const int j = lane + 1;
    const int i = diag - j;
    if(i >= 1 && i <= height && j >= 1 && j <= width)
    {
      const int dpI = tileRow * T + i;
      const int dpJ = tileCol * T + j;
      const int localRow = dpI - 1;
      const bool blocked = sim_diag_blocked(requestBlockedWords,
                                            meta.blockedWordStart,
                                            meta.blockedWordCount,
                                            meta.blockedWordStride,
                                            meta.globalColStart,
                                            localRow,
                                            dpJ);
      const char a = requestA[dpI];
      const char b = requestB[dpJ];
      const int sub = sim_sub_score(a,b,meta.matchScore,meta.mismatchScore);

      const int hDiag = Hs[(i - 1) * (T + 1) + (j - 1)];
      const int diagScore = blocked ? infNeg : (hDiag + sub);

      const int hLeft = Hs[i * (T + 1) + (j - 1)];
      const int eLeft = Es[i * (T + 1) + (j - 1)];
      const int openE = hLeft - meta.gapOpen - meta.gapExtend;
      const int extendE = eLeft - meta.gapExtend;
      const bool eFromExt = (extendE >= openE);
      const int eScore = eFromExt ? extendE : openE;
      const bool eTie = (openE == extendE);

      const int hUp = Hs[(i - 1) * (T + 1) + j];
      const int dUp = Ds[(i - 1) * (T + 1) + j];
      const int openD = hUp - meta.gapOpen - meta.gapExtend;
      const int extendD = dUp - meta.gapExtend;
      const bool dFromExt = (extendD >= openD);
      const int dScore = dFromExt ? extendD : openD;
      const bool dTie = (openD == extendD);

      int best = diagScore;
      unsigned char bestState = 0;
      if(dScore > best)
      {
        best = dScore;
        bestState = 1;
      }
      if(eScore > best)
      {
        best = eScore;
        bestState = 2;
      }

      Hs[i * (T + 1) + j] = best;
      Ds[i * (T + 1) + j] = dScore;
      Es[i * (T + 1) + j] = eScore;

      bool hTie = false;
      if(best > infNeg)
      {
        if(bestState == 0)
        {
          hTie = (dScore == best || eScore == best);
        }
        else if(bestState == 1)
        {
          hTie = (diagScore == best || eScore == best);
        }
        else
        {
          hTie = (diagScore == best || dScore == best);
        }
      }

      unsigned char dirByte = static_cast<unsigned char>(bestState & DIR_STATE_MASK);
      if(dFromExt) dirByte |= DIR_D_FROM_EXT;
      if(eFromExt) dirByte |= DIR_E_FROM_EXT;
      if(hTie) dirByte |= DIR_H_TIE;
      if(dTie) dirByte |= DIR_D_TIE;
      if(eTie) dirByte |= DIR_E_TIE;
      const size_t off = static_cast<size_t>(dpI) * static_cast<size_t>(leadingDim) + static_cast<size_t>(dpJ);
      requestDir[off] = dirByte;
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    requestBottomH[boundaryBase + 0] = Hs[height * (T + 1) + 0];
    requestBottomD[boundaryBase + 0] = Ds[height * (T + 1) + 0];
    requestRightH[boundaryBase + 0] = Hs[0 * (T + 1) + width];
    requestRightE[boundaryBase + 0] = Es[0 * (T + 1) + width];
  }
  if(idx <= width)
  {
    requestBottomH[boundaryBase + idx] = Hs[height * (T + 1) + idx];
    requestBottomD[boundaryBase + idx] = Ds[height * (T + 1) + idx];
  }
  if(idx <= height)
  {
    requestRightH[boundaryBase + idx] = Hs[idx * (T + 1) + width];
    requestRightE[boundaryBase + idx] = Es[idx * (T + 1) + width];
  }
}

__global__ void sim_tb_backtrace_kernel_batched(const unsigned char *dir,
                                                const SimTracebackCudaDeviceBatchRequest *requestMeta,
                                                int requestCount,
                                                int leadingDim,
                                                int dirStride,
                                                unsigned char *opsOut,
                                                int opsStride,
                                                int *opsLenOut,
                                                int *hadTieOut)
{
  const int requestIndex = static_cast<int>(blockIdx.x);
  if(requestIndex < 0 || requestIndex >= requestCount || threadIdx.x != 0)
  {
    return;
  }

  const SimTracebackCudaDeviceBatchRequest meta = requestMeta[requestIndex];
  const unsigned char *requestDir = dir + static_cast<size_t>(requestIndex) * static_cast<size_t>(dirStride);
  unsigned char *requestOps = opsOut + static_cast<size_t>(requestIndex) * static_cast<size_t>(opsStride);
  int *requestOpsLenOut = opsLenOut + requestIndex;
  int *requestHadTieOut = hadTieOut + requestIndex;

  const unsigned char DIR_STATE_MASK = 0x03;
  const unsigned char DIR_D_FROM_EXT = 0x04;
  const unsigned char DIR_E_FROM_EXT = 0x08;
  const unsigned char DIR_H_TIE = 0x10;
  const unsigned char DIR_D_TIE = 0x20;
  const unsigned char DIR_E_TIE = 0x40;

  int i = meta.queryLength;
  int j = meta.targetLength;
  int opsLen = 0;
  int hadTie = 0;
  unsigned char curState = sim_tb_get_h_state(requestDir,leadingDim,i,j);

  while(i > 0 || j > 0)
  {
    if(opsLen + 1 >= opsStride)
    {
      break;
    }

    if(i == 0)
    {
      requestOps[opsLen++] = 1;
      --j;
      curState = 2;
      continue;
    }
    if(j == 0)
    {
      requestOps[opsLen++] = 2;
      --i;
      curState = 1;
      continue;
    }

    const size_t off = static_cast<size_t>(i) * static_cast<size_t>(leadingDim) + static_cast<size_t>(j);
    const unsigned char dirByte = requestDir[off];
    const unsigned char hState = static_cast<unsigned char>(dirByte & DIR_STATE_MASK);

    if(curState == 0)
    {
      if((dirByte & DIR_H_TIE) != 0)
      {
        hadTie = 1;
      }
      requestOps[opsLen++] = 0;
      --i;
      --j;
      curState = sim_tb_get_h_state(requestDir,leadingDim,i,j);
      continue;
    }
    if(curState == 1)
    {
      if((dirByte & DIR_D_TIE) != 0)
      {
        hadTie = 1;
      }
      if(hState == 1 && (dirByte & DIR_H_TIE) != 0)
      {
        hadTie = 1;
      }
      const bool fromExt = (dirByte & DIR_D_FROM_EXT) != 0;
      requestOps[opsLen++] = 2;
      --i;
      if(fromExt)
      {
        curState = 1;
      }
      else
      {
        curState = sim_tb_get_h_state(requestDir,leadingDim,i,j);
      }
      continue;
    }

    if((dirByte & DIR_E_TIE) != 0)
    {
      hadTie = 1;
    }
    if(hState == 2 && (dirByte & DIR_H_TIE) != 0)
    {
      hadTie = 1;
    }
    const bool fromExt = (dirByte & DIR_E_FROM_EXT) != 0;
    requestOps[opsLen++] = 1;
    --j;
    if(fromExt)
    {
      curState = 2;
    }
    else
    {
      curState = sim_tb_get_h_state(requestDir,leadingDim,i,j);
    }
  }

  *requestOpsLenOut = opsLen;
  *requestHadTieOut = hadTie;
}

} // namespace

bool sim_traceback_cuda_is_built()
{
  return true;
}

bool sim_traceback_cuda_init(int device,string *errorOut)
{
  int deviceCount = 0;
  const cudaError_t countStatus = cudaGetDeviceCount(&deviceCount);
  if(countStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(countStatus);
    return false;
  }
  if(deviceCount <= 0)
  {
    if(errorOut != NULL) *errorOut = "no CUDA devices available";
    return false;
  }
  if(device < 0)
  {
    device = 0;
  }
  if(device >= deviceCount)
  {
    if(errorOut != NULL) *errorOut = "requested CUDA device index is out of range";
    return false;
  }
  const cudaError_t setStatus = cudaSetDevice(device);
  if(setStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(setStatus);
    return false;
  }
  return true;
}

bool sim_traceback_cuda_traceback_global_affine(const char *A,
                                                const char *B,
                                                int queryLength,
                                                int targetLength,
                                                int matchScore,
                                                int mismatchScore,
                                                int gapOpen,
                                                int gapExtend,
                                                int globalColStart,
                                                const uint64_t *blockedWords,
                                                int blockedWordStart,
                                                int blockedWordCount,
                                                int blockedWordStride,
                                                vector<unsigned char> *outOpsReversed,
                                                SimTracebackCudaResult *result,
                                                string *errorOut)
{
  if(outOpsReversed == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing output buffer";
    return false;
  }
  outOpsReversed->clear();
  if(result != NULL)
  {
    *result = SimTracebackCudaResult();
  }

  if(A == NULL || B == NULL)
  {
    if(errorOut != NULL) *errorOut = "missing input sequences";
    return false;
  }
  if(queryLength < 0 || targetLength < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid sequence lengths";
    return false;
  }
  if(queryLength == 0 && targetLength == 0)
  {
    return true;
  }
  if(gapOpen < 0 || gapExtend < 0)
  {
    if(errorOut != NULL) *errorOut = "invalid gap penalties";
    return false;
  }
  if(blockedWords == NULL || blockedWordCount <= 0)
  {
    blockedWords = NULL;
    blockedWordStart = 0;
    blockedWordCount = 0;
    blockedWordStride = 0;
  }
  if(blockedWords != NULL && (blockedWordStride <= 0 || blockedWordStride < blockedWordCount))
  {
    if(errorOut != NULL) *errorOut = "invalid blocked word stride";
    return false;
  }

  int device = 0;
  const int slot = simCudaWorkerSlotRuntime();
  const cudaError_t devStatus = cudaGetDevice(&device);
  if(devStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(devStatus);
    return false;
  }

  SimTracebackCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_sim_traceback_cuda_context_for_device_slot(device,slot,&context,&contextMutex,errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_sim_traceback_cuda_initialized_locked(*context,device,errorOut))
  {
    return false;
  }
  if(!ensure_sim_traceback_cuda_capacity_locked(*context,queryLength,targetLength,blockedWordCount,errorOut))
  {
    return false;
  }

  cudaError_t status = cudaMemcpy(context->ADevice,
                                  A,
                                  static_cast<size_t>(queryLength + 1) * sizeof(char),
                                  cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMemcpy(context->BDevice,
                      B,
                      static_cast<size_t>(targetLength + 1) * sizeof(char),
                      cudaMemcpyHostToDevice);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  const size_t blockedWordsCount = (blockedWordCount > 0 && queryLength > 0)
                                    ? (static_cast<size_t>(queryLength) * static_cast<size_t>(blockedWordCount))
                                    : 0u;
  const uint64_t *blockedWordsDevice = NULL;
  if(blockedWordsCount > 0)
  {
    if(blockedWords == NULL)
    {
      if(errorOut != NULL) *errorOut = "missing blocked words";
      return false;
    }
    if(blockedWordStride == blockedWordCount)
    {
      status = cudaMemcpy(context->blockedWordsDevice,
                          blockedWords,
                          blockedWordsCount * sizeof(uint64_t),
                          cudaMemcpyHostToDevice);
    }
    else
    {
      status = cudaMemcpy2D(context->blockedWordsDevice,
                            static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                            blockedWords,
                            static_cast<size_t>(blockedWordStride) * sizeof(uint64_t),
                            static_cast<size_t>(blockedWordCount) * sizeof(uint64_t),
                            static_cast<size_t>(queryLength),
                            cudaMemcpyHostToDevice);
    }
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
    blockedWordsDevice = context->blockedWordsDevice;
  }

  status = cudaEventRecord(context->startEvent);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  const int T = 32;
  const int tileRows = (queryLength + T - 1) / T;
  const int tileCols = (targetLength + T - 1) / T;
  const int tileDiags = tileRows + tileCols - 1;
  for(int tileDiag = 0; tileDiag < tileDiags; ++tileDiag)
  {
    const int tileRowStart = max(0, tileDiag - (tileCols - 1));
    const int tileRowEnd = min(tileDiag, tileRows - 1);
    const int tiles = tileRowEnd >= tileRowStart ? (tileRowEnd - tileRowStart + 1) : 0;
    if(tiles <= 0)
    {
      continue;
    }

    sim_tb_tile_wavefront_kernel<<<tiles, 32>>>(context->ADevice,
                                                context->BDevice,
                                                queryLength,
                                                targetLength,
                                                context->leadingDim,
                                                tileDiag,
                                                tileRows,
                                                tileCols,
                                                context->tileColsCap,
                                                matchScore,
                                                mismatchScore,
                                                gapOpen,
                                                gapExtend,
                                                globalColStart,
                                                blockedWordsDevice,
                                                blockedWordStart,
                                                blockedWordCount,
                                                context->bottomHDevice,
                                                context->bottomDDevice,
                                                context->rightHDevice,
                                                context->rightEDevice,
                                                context->dirDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
  }

  status = cudaMemset(context->opsLenDevice, 0, sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMemset(context->hadTieDevice, 0, sizeof(int));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  sim_tb_backtrace_kernel<<<1, 1>>>(context->dirDevice,
                                    queryLength,
                                    targetLength,
                                    context->leadingDim,
                                    context->opsDevice,
                                    context->opsCapacity,
                                    context->opsLenDevice,
                                    context->hadTieDevice);
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

  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, context->startEvent, context->stopEvent);
  }
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  int opsLen = 0;
  int hadTie = 0;
  status = cudaMemcpy(&opsLen, context->opsLenDevice, sizeof(int), cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }
  status = cudaMemcpy(&hadTie, context->hadTieDevice, sizeof(int), cudaMemcpyDeviceToHost);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  if(opsLen < 0)
  {
    opsLen = 0;
  }
  if(opsLen > context->opsCapacity)
  {
    opsLen = context->opsCapacity;
  }

  vector<unsigned char> ops(static_cast<size_t>(opsLen));
  if(opsLen > 0)
  {
    status = cudaMemcpy(ops.data(),
                        context->opsDevice,
                        static_cast<size_t>(opsLen) * sizeof(unsigned char),
                        cudaMemcpyDeviceToHost);
    if(status != cudaSuccess)
    {
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    }
  }

  outOpsReversed->swap(ops);
  if(result != NULL)
  {
    result->usedCuda = true;
    result->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    result->hadTie = (hadTie != 0);
  }
  return true;
}

bool sim_traceback_cuda_traceback_global_affine_batch(const vector<SimTracebackCudaBatchRequest> &requests,
                                                      vector<SimTracebackCudaBatchItemResult> *outResults,
                                                      SimTracebackCudaBatchResult *batchResult,
                                                      string *errorOut)
{
  if(outResults == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }

  outResults->clear();
  if(batchResult != NULL)
  {
    *batchResult = SimTracebackCudaBatchResult();
    batchResult->requestCount = static_cast<uint64_t>(requests.size());
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }

  if(requests.empty())
  {
    return true;
  }

  outResults->assign(requests.size(), SimTracebackCudaBatchItemResult());

  vector<SimTracebackCudaBatchRequest> normalizedRequests(requests);
  vector<size_t> pendingIndices;
  pendingIndices.reserve(requests.size());
  for(size_t i = 0; i < normalizedRequests.size(); ++i)
  {
    SimTracebackCudaBatchRequest &request = normalizedRequests[i];
    SimTracebackCudaBatchItemResult &item = (*outResults)[i];
    if(request.A == NULL || request.B == NULL)
    {
      item.error = "missing input sequences";
      continue;
    }
    if(request.queryLength < 0 || request.targetLength < 0)
    {
      item.error = "invalid sequence lengths";
      continue;
    }
    if(request.gapOpen < 0 || request.gapExtend < 0)
    {
      item.error = "invalid gap penalties";
      continue;
    }
    if(request.blockedWords == NULL || request.blockedWordCount <= 0)
    {
      request.blockedWords = NULL;
      request.blockedWordStart = 0;
      request.blockedWordCount = 0;
      request.blockedWordStride = 0;
    }
    if(request.blockedWords != NULL &&
       (request.blockedWordStride <= 0 || request.blockedWordStride < request.blockedWordCount))
    {
      item.error = "invalid blocked word stride";
      continue;
    }
    if(request.queryLength == 0 || request.targetLength == 0)
    {
      if(request.targetLength > 0)
      {
        item.opsReversed.assign(static_cast<size_t>(request.targetLength),static_cast<unsigned char>(1));
      }
      else if(request.queryLength > 0)
      {
        item.opsReversed.assign(static_cast<size_t>(request.queryLength),static_cast<unsigned char>(2));
      }
      item.success = true;
      if(batchResult != NULL)
      {
        batchResult->successCount += 1;
      }
      continue;
    }
    pendingIndices.push_back(i);
  }

  if(pendingIndices.empty())
  {
    return true;
  }

  if(!sim_traceback_cuda_init(simCudaDeviceRuntime(), errorOut))
  {
    return false;
  }

  int device = 0;
  const cudaError_t devStatus = cudaGetDevice(&device);
  if(devStatus != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(devStatus);
    return false;
  }

  const int T = 32;
  const size_t maxChunkRequests = 64u;
  const size_t maxChunkMatrixCells = 64u * 1024u * 1024u;
  size_t pendingStart = 0;
  while(pendingStart < pendingIndices.size())
  {
    size_t chunkStart = pendingStart;
    size_t chunkCount = 0;
    int chunkMaxQuery = 0;
    int chunkMaxTarget = 0;
    int chunkMaxBlockedWords = 0;
    int chunkMaxTileRows = 0;
    int chunkMaxTileCols = 0;
    int chunkMaxTilesPerDiag = 0;
    int chunkMaxTileDiags = 0;

    while(pendingStart < pendingIndices.size())
    {
      const SimTracebackCudaBatchRequest &request = normalizedRequests[pendingIndices[pendingStart]];
      const int nextMaxQuery = max(chunkMaxQuery, request.queryLength);
      const int nextMaxTarget = max(chunkMaxTarget, request.targetLength);
      const size_t nextChunkCount = chunkCount + 1;
      const size_t nextMatrixCells =
        nextChunkCount *
        static_cast<size_t>(nextMaxQuery + 1) *
        static_cast<size_t>(nextMaxTarget + 1);
      if(chunkCount > 0 &&
         (nextChunkCount > maxChunkRequests || nextMatrixCells > maxChunkMatrixCells))
      {
        break;
      }

      chunkMaxQuery = nextMaxQuery;
      chunkMaxTarget = nextMaxTarget;
      chunkMaxBlockedWords = max(chunkMaxBlockedWords, request.blockedWordCount);
      const int tileRows = (request.queryLength + T - 1) / T;
      const int tileCols = (request.targetLength + T - 1) / T;
      chunkMaxTileRows = max(chunkMaxTileRows, tileRows);
      chunkMaxTileCols = max(chunkMaxTileCols, tileCols);
      chunkMaxTilesPerDiag = max(chunkMaxTilesPerDiag, min(tileRows, tileCols));
      chunkMaxTileDiags = max(chunkMaxTileDiags, max(0, tileRows + tileCols - 1));
      ++chunkCount;
      ++pendingStart;
    }

    if(chunkCount == 0)
    {
      const SimTracebackCudaBatchRequest &request = normalizedRequests[pendingIndices[pendingStart]];
      chunkMaxQuery = request.queryLength;
      chunkMaxTarget = request.targetLength;
      chunkMaxBlockedWords = request.blockedWordCount;
      const int tileRows = (request.queryLength + T - 1) / T;
      const int tileCols = (request.targetLength + T - 1) / T;
      chunkMaxTileRows = tileRows;
      chunkMaxTileCols = tileCols;
      chunkMaxTilesPerDiag = min(tileRows, tileCols);
      chunkMaxTileDiags = max(0, tileRows + tileCols - 1);
      chunkCount = 1;
      ++pendingStart;
    }

    const int queryStride = chunkMaxQuery + 1;
    const int targetStride = chunkMaxTarget + 1;
    const int leadingDim = targetStride;
    const int dirStride = queryStride * leadingDim;
    const int boundaryStride = chunkMaxTileRows * chunkMaxTileCols * (T + 1);
    const int blockedStride = chunkMaxBlockedWords;
    const size_t blockedSliceStrideWords =
      (blockedStride > 0 && chunkMaxQuery > 0) ?
      (static_cast<size_t>(chunkMaxQuery) * static_cast<size_t>(blockedStride)) : 0u;
    const int opsStride = max(1, chunkMaxQuery + chunkMaxTarget + 2);

    char *ADevice = NULL;
    char *BDevice = NULL;
    unsigned char *dirDevice = NULL;
    int *bottomHDevice = NULL;
    int *bottomDDevice = NULL;
    int *rightHDevice = NULL;
    int *rightEDevice = NULL;
    uint64_t *blockedWordsDevice = NULL;
    unsigned char *opsDevice = NULL;
    int *opsLenDevice = NULL;
    int *hadTieDevice = NULL;
    SimTracebackCudaDeviceBatchRequest *requestMetaDevice = NULL;
    cudaEvent_t startEvent = NULL;
    cudaEvent_t stopEvent = NULL;

    auto cleanupChunk = [&]() -> void
    {
      if(startEvent != NULL) cudaEventDestroy(startEvent);
      if(stopEvent != NULL) cudaEventDestroy(stopEvent);
      if(ADevice != NULL) cudaFree(ADevice);
      if(BDevice != NULL) cudaFree(BDevice);
      if(dirDevice != NULL) cudaFree(dirDevice);
      if(bottomHDevice != NULL) cudaFree(bottomHDevice);
      if(bottomDDevice != NULL) cudaFree(bottomDDevice);
      if(rightHDevice != NULL) cudaFree(rightHDevice);
      if(rightEDevice != NULL) cudaFree(rightEDevice);
      if(blockedWordsDevice != NULL) cudaFree(blockedWordsDevice);
      if(opsDevice != NULL) cudaFree(opsDevice);
      if(opsLenDevice != NULL) cudaFree(opsLenDevice);
      if(hadTieDevice != NULL) cudaFree(hadTieDevice);
      if(requestMetaDevice != NULL) cudaFree(requestMetaDevice);
    };

    auto failChunk = [&](cudaError_t status) -> bool
    {
      cleanupChunk();
      if(errorOut != NULL) *errorOut = cuda_error_string(status);
      return false;
    };

    const size_t aBytes = static_cast<size_t>(chunkCount) * static_cast<size_t>(queryStride) * sizeof(char);
    const size_t bBytes = static_cast<size_t>(chunkCount) * static_cast<size_t>(targetStride) * sizeof(char);
    const size_t dirBytes = static_cast<size_t>(chunkCount) * static_cast<size_t>(dirStride) * sizeof(unsigned char);
    const size_t boundaryBytes = static_cast<size_t>(chunkCount) * static_cast<size_t>(boundaryStride) * sizeof(int);
    const size_t blockedBytes = blockedSliceStrideWords > 0 ?
                                static_cast<size_t>(chunkCount) * blockedSliceStrideWords * sizeof(uint64_t) : 0u;
    const size_t opsBytes = static_cast<size_t>(chunkCount) * static_cast<size_t>(opsStride) * sizeof(unsigned char);
    const size_t countsBytes = static_cast<size_t>(chunkCount) * sizeof(int);
    const size_t metaBytes = static_cast<size_t>(chunkCount) * sizeof(SimTracebackCudaDeviceBatchRequest);

    cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&ADevice), aBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMalloc(reinterpret_cast<void **>(&BDevice), bBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMalloc(reinterpret_cast<void **>(&dirDevice), dirBytes);
    if(status != cudaSuccess) return failChunk(status);
    if(boundaryBytes > 0)
    {
      status = cudaMalloc(reinterpret_cast<void **>(&bottomHDevice), boundaryBytes);
      if(status != cudaSuccess) return failChunk(status);
      status = cudaMalloc(reinterpret_cast<void **>(&bottomDDevice), boundaryBytes);
      if(status != cudaSuccess) return failChunk(status);
      status = cudaMalloc(reinterpret_cast<void **>(&rightHDevice), boundaryBytes);
      if(status != cudaSuccess) return failChunk(status);
      status = cudaMalloc(reinterpret_cast<void **>(&rightEDevice), boundaryBytes);
      if(status != cudaSuccess) return failChunk(status);
    }
    if(blockedBytes > 0)
    {
      status = cudaMalloc(reinterpret_cast<void **>(&blockedWordsDevice), blockedBytes);
      if(status != cudaSuccess) return failChunk(status);
    }
    status = cudaMalloc(reinterpret_cast<void **>(&opsDevice), opsBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMalloc(reinterpret_cast<void **>(&opsLenDevice), countsBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMalloc(reinterpret_cast<void **>(&hadTieDevice), countsBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMalloc(reinterpret_cast<void **>(&requestMetaDevice), metaBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaEventCreate(&startEvent);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaEventCreate(&stopEvent);
    if(status != cudaSuccess) return failChunk(status);

    vector<SimTracebackCudaDeviceBatchRequest> requestMeta(chunkCount);
    for(size_t localIndex = 0; localIndex < chunkCount; ++localIndex)
    {
      const SimTracebackCudaBatchRequest &request = normalizedRequests[pendingIndices[chunkStart + localIndex]];
      SimTracebackCudaDeviceBatchRequest meta;
      meta.queryLength = request.queryLength;
      meta.targetLength = request.targetLength;
      meta.matchScore = request.matchScore;
      meta.mismatchScore = request.mismatchScore;
      meta.gapOpen = request.gapOpen;
      meta.gapExtend = request.gapExtend;
      meta.globalColStart = request.globalColStart;
      meta.blockedWordStart = request.blockedWordStart;
      meta.blockedWordCount = request.blockedWordCount;
      meta.blockedWordStride = blockedStride;
      requestMeta[localIndex] = meta;

      status = cudaMemcpy(ADevice + static_cast<size_t>(localIndex) * static_cast<size_t>(queryStride),
                          request.A,
                          static_cast<size_t>(request.queryLength + 1) * sizeof(char),
                          cudaMemcpyHostToDevice);
      if(status != cudaSuccess) return failChunk(status);
      status = cudaMemcpy(BDevice + static_cast<size_t>(localIndex) * static_cast<size_t>(targetStride),
                          request.B,
                          static_cast<size_t>(request.targetLength + 1) * sizeof(char),
                          cudaMemcpyHostToDevice);
      if(status != cudaSuccess) return failChunk(status);

      if(blockedSliceStrideWords > 0 &&
         request.blockedWords != NULL &&
         request.blockedWordCount > 0 &&
         request.queryLength > 0)
      {
        uint64_t *requestBlockedWordsDevice =
          blockedWordsDevice + static_cast<size_t>(localIndex) * blockedSliceStrideWords;
        status = cudaMemcpy2D(requestBlockedWordsDevice,
                              static_cast<size_t>(blockedStride) * sizeof(uint64_t),
                              request.blockedWords,
                              static_cast<size_t>(request.blockedWordStride) * sizeof(uint64_t),
                              static_cast<size_t>(request.blockedWordCount) * sizeof(uint64_t),
                              static_cast<size_t>(request.queryLength),
                              cudaMemcpyHostToDevice);
        if(status != cudaSuccess) return failChunk(status);
      }
    }

    status = cudaMemcpy(requestMetaDevice,
                        requestMeta.data(),
                        metaBytes,
                        cudaMemcpyHostToDevice);
    if(status != cudaSuccess) return failChunk(status);

    status = cudaEventRecord(startEvent);
    if(status != cudaSuccess) return failChunk(status);

    if(chunkMaxTilesPerDiag > 0 && chunkMaxTileDiags > 0)
    {
      for(int tileDiag = 0; tileDiag < chunkMaxTileDiags; ++tileDiag)
      {
        sim_tb_tile_wavefront_kernel_batched<<<static_cast<unsigned int>(chunkCount * static_cast<size_t>(chunkMaxTilesPerDiag)), 32>>>(
          ADevice,
          BDevice,
          requestMetaDevice,
          static_cast<int>(chunkCount),
          queryStride,
          targetStride,
          leadingDim,
          tileDiag,
          chunkMaxTilesPerDiag,
          chunkMaxTileCols,
          boundaryStride,
          blockedWordsDevice,
          static_cast<int>(blockedSliceStrideWords),
          bottomHDevice,
          bottomDDevice,
          rightHDevice,
          rightEDevice,
          dirDevice);
        status = cudaGetLastError();
        if(status != cudaSuccess) return failChunk(status);
      }
    }

    status = cudaMemset(opsLenDevice, 0, countsBytes);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMemset(hadTieDevice, 0, countsBytes);
    if(status != cudaSuccess) return failChunk(status);

    sim_tb_backtrace_kernel_batched<<<static_cast<unsigned int>(chunkCount), 1>>>(
      dirDevice,
      requestMetaDevice,
      static_cast<int>(chunkCount),
      leadingDim,
      dirStride,
      opsDevice,
      opsStride,
      opsLenDevice,
      hadTieDevice);
    status = cudaGetLastError();
    if(status != cudaSuccess) return failChunk(status);

    status = cudaEventRecord(stopEvent);
    if(status == cudaSuccess)
    {
      status = cudaEventSynchronize(stopEvent);
    }
    float elapsedMs = 0.0f;
    if(status == cudaSuccess)
    {
      status = cudaEventElapsedTime(&elapsedMs, startEvent, stopEvent);
    }
    if(status != cudaSuccess) return failChunk(status);

    vector<int> opsLens(chunkCount,0);
    vector<int> hadTies(chunkCount,0);
    status = cudaMemcpy(opsLens.data(), opsLenDevice, countsBytes, cudaMemcpyDeviceToHost);
    if(status != cudaSuccess) return failChunk(status);
    status = cudaMemcpy(hadTies.data(), hadTieDevice, countsBytes, cudaMemcpyDeviceToHost);
    if(status != cudaSuccess) return failChunk(status);

    const double chunkSeconds = static_cast<double>(elapsedMs) / 1000.0;
    if(batchResult != NULL)
    {
      batchResult->gpuSeconds += chunkSeconds;
      batchResult->usedCuda = true;
    }

    for(size_t localIndex = 0; localIndex < chunkCount; ++localIndex)
    {
      SimTracebackCudaBatchItemResult &item = (*outResults)[pendingIndices[chunkStart + localIndex]];
      int opsLen = opsLens[localIndex];
      if(opsLen < 0) opsLen = 0;
      if(opsLen > opsStride) opsLen = opsStride;

      vector<unsigned char> ops(static_cast<size_t>(opsLen));
      if(opsLen > 0)
      {
        status = cudaMemcpy(ops.data(),
                            opsDevice + static_cast<size_t>(localIndex) * static_cast<size_t>(opsStride),
                            static_cast<size_t>(opsLen) * sizeof(unsigned char),
                            cudaMemcpyDeviceToHost);
        if(status != cudaSuccess) return failChunk(status);
      }

      item.success = true;
      item.error.clear();
      item.opsReversed.swap(ops);
      item.tracebackResult.usedCuda = true;
      item.tracebackResult.gpuSeconds = chunkSeconds;
      item.tracebackResult.hadTie = (hadTies[localIndex] != 0);
      if(batchResult != NULL)
      {
        batchResult->successCount += 1;
        batchResult->cudaCount += 1;
      }
    }

    cleanupChunk();
  }
  return true;
}
