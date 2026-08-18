#include "prealign_cuda.h"

#include <cuda_runtime.h>

#include <memory>
#include <mutex>
#include <sstream>

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

static __device__ __forceinline__ int cuda_sat_u8_add(int a,int b)
{
  const int v = a + b;
  return v > 255 ? 255 : v;
}

static __device__ __forceinline__ int cuda_sat_u8_sub(int a,int b)
{
  const int v = a - b;
  return v > 0 ? v : 0;
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

static __device__ __forceinline__ int cuda_warp_shift_left_1_16(int value,int lane)
{
  const int shifted = __shfl_up_sync(0xffffffffu, value, 1);
  return (lane == 0 || lane >= 16) ? 0 : shifted;
}

static __device__ __forceinline__ int cuda_to_signed_i8(int value)
{
  return value >= 128 ? value - 256 : value;
}

static __device__ __forceinline__ bool prealign_heap_less(int scoreA,int posA,int scoreB,int posB)
{
  return (scoreA < scoreB) || (scoreA == scoreB && posA > posB);
}

static __device__ __forceinline__ bool prealign_scoreinfo_prune_less(int scoreA,int posA,int scoreB,int posB)
{
  return (scoreA < scoreB) || (scoreA == scoreB && posA > posB);
}

static __device__ __forceinline__ bool prealign_scoreinfo_prune_better(int scoreA,int posA,int scoreB,int posB)
{
  return (scoreA > scoreB) || (scoreA == scoreB && posA < posB);
}

static __device__ void prealign_scoreinfo_prune_consider(int score,
                                                         int position,
                                                         int pruneMax,
                                                         int &keptCount,
                                                         int *keptScores,
                                                         int *keptPositions)
{
  if(pruneMax <= 0)
  {
    return;
  }
  if(keptCount < pruneMax)
  {
    keptScores[keptCount] = score;
    keptPositions[keptCount] = position;
    ++keptCount;
    return;
  }

  int worst = 0;
  for(int i = 1; i < pruneMax; ++i)
  {
    if(prealign_scoreinfo_prune_less(keptScores[i], keptPositions[i], keptScores[worst], keptPositions[worst]))
    {
      worst = i;
    }
  }
  if(prealign_scoreinfo_prune_better(score, position, keptScores[worst], keptPositions[worst]))
  {
    keptScores[worst] = score;
    keptPositions[worst] = position;
  }
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

__global__ void prealign_cuda_column_max_batch_kernel(const int16_t *profile,
                                                      const uint8_t *encodedTargets,
                                                      int taskCount,
                                                      int targetLength,
                                                      int segLen,
                                                      int *outColumnMaxima)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }
  extern __shared__ unsigned char batchSmem[];
  int16_t *E = reinterpret_cast<int16_t *>(batchSmem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  int *taskOutput =
    outColumnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

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

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    if(lane == 0)
    {
      taskOutput[targetIndex] = colMax;
    }
    __syncwarp();
  }
}

__global__ void prealign_cuda_column_max_global_state_batch_kernel(const int16_t *profile,
                                                                   const uint8_t *encodedTargets,
                                                                   int taskCount,
                                                                   int targetLength,
                                                                   int segLen,
                                                                   int16_t *stateDevice,
                                                                   int *outColumnMaxima)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }
  const size_t stateStride =
    static_cast<size_t>(3) * static_cast<size_t>(segLen) * 32u;
  int16_t *taskState = stateDevice + static_cast<size_t>(taskIndex) * stateStride;
  int16_t *E = taskState;
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  int *taskOutput =
    outColumnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

  const int gapOpen = 16;
  const int gapExtend = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = taskTarget[targetIndex];
    const int16_t *profileRow =
      profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

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

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    if(lane == 0)
    {
      taskOutput[targetIndex] = colMax;
    }
    __syncwarp();
  }
}

__global__ void prealign_cuda_column_max_legacy_byte_global_state_batch_kernel(const int16_t *profile,
                                                                               const uint8_t *encodedTargets,
                                                                               int taskCount,
                                                                               int targetLength,
                                                                               int segLen,
                                                                               int16_t *stateDevice,
                                                                               int *outColumnMaxima)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }
  const bool activeLane = lane < 16;

  const size_t stateStride =
    static_cast<size_t>(3) * static_cast<size_t>(segLen) * 32u;
  int16_t *taskState = stateDevice + static_cast<size_t>(taskIndex) * stateStride;
  int16_t *E = taskState;
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  int *taskOutput =
    outColumnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

  const int gapOpen = 16;
  const int gapExtend = 4;
  const int bias = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = taskTarget[targetIndex];
    const int16_t *profileRow =
      profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

    int colLaneMax = 0;

    int vF = 0;
    int vH = activeLane ?
      static_cast<int>(HLoad[(segLen - 1) * 32 + lane]) :
      0;
    vH = cuda_warp_shift_left_1_16(vH,lane);

    for(int segIndex = 0; segIndex < segLen; ++segIndex)
    {
      const int score = activeLane ?
        static_cast<int>(profileRow[segIndex * 32 + lane]) :
        bias;
      const int oldH = activeLane ?
        static_cast<int>(HLoad[segIndex * 32 + lane]) :
        0;
      int vE = activeLane ?
        static_cast<int>(E[segIndex * 32 + lane]) :
        0;

      vH = cuda_sat_u8_add(vH,score);
      vH = cuda_sat_u8_sub(vH,bias);
      vH = cuda_max_int(vH,vE);
      vH = cuda_max_int(vH,vF);

      if(activeLane)
      {
        HStore[segIndex * 32 + lane] = static_cast<int16_t>(vH);
        colLaneMax = cuda_max_int(colLaneMax,vH);
      }

      const int vHGapOpen = cuda_sat_u8_sub(vH,gapOpen);

      vE = cuda_sat_u8_sub(vE,gapExtend);
      vE = cuda_max_int(vE,vHGapOpen);
      if(activeLane)
      {
        E[segIndex * 32 + lane] = static_cast<int16_t>(vE);
      }

      vF = cuda_sat_u8_sub(vF,gapExtend);
      vF = cuda_max_int(vF,vHGapOpen);

      vH = oldH;
    }

    bool lazyDone = false;
    for(int lazyPass = 0; lazyPass < 16 && !lazyDone; ++lazyPass)
    {
      vF = cuda_warp_shift_left_1_16(vF,lane);
      for(int segIndex = 0; segIndex < segLen; ++segIndex)
      {
        int vHStore = activeLane ?
          static_cast<int>(HStore[segIndex * 32 + lane]) :
          0;
        vHStore = cuda_max_int(vHStore,vF);
        if(activeLane)
        {
          HStore[segIndex * 32 + lane] = static_cast<int16_t>(vHStore);
          colLaneMax = cuda_max_int(colLaneMax,vHStore);
        }

        const int vHGapOpen = cuda_sat_u8_sub(vHStore,gapOpen);
        vF = cuda_sat_u8_sub(vF,gapExtend);
        const int shouldContinue =
          cuda_to_signed_i8(vF) > cuda_to_signed_i8(vHGapOpen) ? 1 : 0;
        if(__ballot_sync(0xffffffffu,shouldContinue) == 0)
        {
          lazyDone = true;
          break;
        }

        __syncwarp();
      }
    }

    int16_t *tmp = HLoad;
    HLoad = HStore;
    HStore = tmp;

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    if(lane == 0)
    {
      taskOutput[targetIndex] = colMax;
    }
    __syncwarp();
  }
}

__global__ void prealign_cuda_column_max_legacy_byte_batch_kernel(const int16_t *profile,
                                                                  const uint8_t *encodedTargets,
                                                                  int taskCount,
                                                                  int targetLength,
                                                                  int segLen,
                                                                  int *outColumnMaxima)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }
  const bool activeLane = lane < 16;

  extern __shared__ unsigned char smem[];
  int16_t *E = reinterpret_cast<int16_t *>(smem);
  int16_t *H0 = E + segLen * 16;
  int16_t *H1 = H0 + segLen * 16;

  if(activeLane)
  {
    for(int i = lane; i < segLen * 16; i += 16)
    {
      E[i] = 0;
      H0[i] = 0;
      H1[i] = 0;
    }
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  int *taskOutput =
    outColumnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

  const int gapOpen = 16;
  const int gapExtend = 4;
  const int bias = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = taskTarget[targetIndex];
    const int16_t *profileRow =
      profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

    int colLaneMax = 0;

    int vF = 0;
    int vH = activeLane ?
      static_cast<int>(HLoad[(segLen - 1) * 16 + lane]) :
      0;
    vH = cuda_warp_shift_left_1_16(vH,lane);

    for(int segIndex = 0; segIndex < segLen; ++segIndex)
    {
      const int score = activeLane ?
        static_cast<int>(profileRow[segIndex * 32 + lane]) :
        bias;
      const int oldH = activeLane ?
        static_cast<int>(HLoad[segIndex * 16 + lane]) :
        0;
      int vE = activeLane ?
        static_cast<int>(E[segIndex * 16 + lane]) :
        0;

      vH = cuda_sat_u8_add(vH,score);
      vH = cuda_sat_u8_sub(vH,bias);
      vH = cuda_max_int(vH,vE);
      vH = cuda_max_int(vH,vF);

      if(activeLane)
      {
        HStore[segIndex * 16 + lane] = static_cast<int16_t>(vH);
        colLaneMax = cuda_max_int(colLaneMax,vH);
      }

      const int vHGapOpen = cuda_sat_u8_sub(vH,gapOpen);

      vE = cuda_sat_u8_sub(vE,gapExtend);
      vE = cuda_max_int(vE,vHGapOpen);
      if(activeLane)
      {
        E[segIndex * 16 + lane] = static_cast<int16_t>(vE);
      }

      vF = cuda_sat_u8_sub(vF,gapExtend);
      vF = cuda_max_int(vF,vHGapOpen);

      vH = oldH;
    }

    bool lazyDone = false;
    for(int lazyPass = 0; lazyPass < 16 && !lazyDone; ++lazyPass)
    {
      vF = cuda_warp_shift_left_1_16(vF,lane);
      for(int segIndex = 0; segIndex < segLen; ++segIndex)
      {
        int vHStore = activeLane ?
          static_cast<int>(HStore[segIndex * 16 + lane]) :
          0;
        vHStore = cuda_max_int(vHStore,vF);
        if(activeLane)
        {
          HStore[segIndex * 16 + lane] = static_cast<int16_t>(vHStore);
          colLaneMax = cuda_max_int(colLaneMax,vHStore);
        }

        const int vHGapOpen = cuda_sat_u8_sub(vHStore,gapOpen);
        vF = cuda_sat_u8_sub(vF,gapExtend);
        const int shouldContinue =
          cuda_to_signed_i8(vF) > cuda_to_signed_i8(vHGapOpen) ? 1 : 0;
        if(__ballot_sync(0xffffffffu,shouldContinue) == 0)
        {
          lazyDone = true;
          break;
        }

        __syncwarp();
      }
    }

    int16_t *tmp = HLoad;
    HLoad = HStore;
    HStore = tmp;

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    if(lane == 0)
    {
      taskOutput[targetIndex] = colMax;
    }
    __syncwarp();
  }
}

__global__ void prealign_cuda_scoreinfo_batch_kernel(const int16_t *profile,
                                                     const uint8_t *encodedTargets,
                                                     const int *minScores,
                                                     int taskCount,
                                                     int targetLength,
                                                     int segLen,
                                                     int maxScoreInfosPerTask,
                                                     PreAlignCudaPeak *outScoreInfos,
                                                     int *outCounts,
                                                     int *overflowFlag)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }

  extern __shared__ unsigned char smem[];
  int16_t *E = reinterpret_cast<int16_t *>(smem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  PreAlignCudaPeak *taskOut =
    outScoreInfos + static_cast<size_t>(taskIndex) * static_cast<size_t>(maxScoreInfosPerTask);
  const int minScore = minScores[taskIndex];

  const int gapOpen = 16;
  const int gapExtend = 4;
  const int suppressBp = 5;
  const int sswByteBias = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  int maxScore = 0;
  int outCount = 0;
  bool overflow = false;
  bool haveGroup = false;
  int previousCandidatePosition = -1;
  int bestScore = 0;
  int bestPosition = -1;

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

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    int stopNow = 0;
    if(lane == 0)
    {
      if(colMax > maxScore)
      {
        maxScore = colMax;
        if(maxScore + sswByteBias >= 255)
        {
          stopNow = 1;
        }
      }
    }
    stopNow = __shfl_sync(0xffffffffu, stopNow, 0);
    if(stopNow != 0)
    {
      __syncwarp();
      break;
    }
    if(lane == 0)
    {
      if(colMax > minScore)
      {
        if(!haveGroup)
        {
          bestScore = colMax;
          bestPosition = targetIndex;
          previousCandidatePosition = targetIndex;
          haveGroup = true;
        }
        else
        {
          const int positionDelta = targetIndex - previousCandidatePosition;
          if(positionDelta <= 0 || positionDelta >= suppressBp)
          {
            if(outCount < maxScoreInfosPerTask)
            {
              taskOut[outCount].score = bestScore;
              taskOut[outCount].position = bestPosition;
            }
            else
            {
              overflow = true;
            }
            ++outCount;
            bestScore = colMax;
            bestPosition = targetIndex;
          }
          else if(colMax > bestScore)
          {
            bestScore = colMax;
            bestPosition = targetIndex;
          }
          previousCandidatePosition = targetIndex;
        }
      }
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    if(haveGroup)
    {
      if(outCount < maxScoreInfosPerTask)
      {
        taskOut[outCount].score = bestScore;
        taskOut[outCount].position = bestPosition;
      }
      else
      {
        overflow = true;
      }
      ++outCount;
    }
    if(outCount > maxScoreInfosPerTask)
    {
      overflow = true;
    }
    outCounts[taskIndex] = outCount;
    if(overflow)
    {
      atomicExch(overflowFlag, 1);
    }
  }
}

__global__ void prealign_cuda_scoreinfo_pruned_batch_kernel(const int16_t *profile,
                                                            const uint8_t *encodedTargets,
                                                            const int *minScores,
                                                            int taskCount,
                                                            int targetLength,
                                                            int segLen,
                                                            int pruneMaxScoreInfosPerTask,
                                                            PreAlignCudaPeak *outScoreInfos,
                                                            int *outCounts,
                                                            int *outInputCounts,
                                                            int *overflowFlag)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }

  extern __shared__ unsigned char smem[];
  int16_t *E = reinterpret_cast<int16_t *>(smem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  size_t offsetBytes = static_cast<size_t>(3) * static_cast<size_t>(segLen) * 32u * sizeof(int16_t);
  offsetBytes = (offsetBytes + sizeof(int) - 1) & ~(static_cast<size_t>(sizeof(int) - 1));
  int *keptScores = reinterpret_cast<int *>(smem + offsetBytes);
  int *keptPositions = keptScores + pruneMaxScoreInfosPerTask;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  for(int k = lane; k < pruneMaxScoreInfosPerTask; k += 32)
  {
    keptScores[k] = -1;
    keptPositions[k] = -1;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  PreAlignCudaPeak *taskOut =
    outScoreInfos + static_cast<size_t>(taskIndex) * static_cast<size_t>(pruneMaxScoreInfosPerTask);
  const int minScore = minScores[taskIndex];

  const int gapOpen = 16;
  const int gapExtend = 4;
  const int suppressBp = 5;
  const int sswByteBias = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;

  int maxScore = 0;
  int inputCount = 0;
  int keptCount = 0;
  bool haveGroup = false;
  int previousCandidatePosition = -1;
  int bestScore = 0;
  int bestPosition = -1;

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

    const int colMax = cuda_warp_reduce_max_int(colLaneMax);
    int stopNow = 0;
    if(lane == 0)
    {
      if(colMax > maxScore)
      {
        maxScore = colMax;
        if(maxScore + sswByteBias >= 255)
        {
          stopNow = 1;
        }
      }
    }
    stopNow = __shfl_sync(0xffffffffu, stopNow, 0);
    if(stopNow != 0)
    {
      __syncwarp();
      break;
    }
    if(lane == 0)
    {
      if(colMax > minScore)
      {
        if(!haveGroup)
        {
          bestScore = colMax;
          bestPosition = targetIndex;
          previousCandidatePosition = targetIndex;
          haveGroup = true;
        }
        else
        {
          const int positionDelta = targetIndex - previousCandidatePosition;
          if(positionDelta <= 0 || positionDelta >= suppressBp)
          {
            prealign_scoreinfo_prune_consider(bestScore,
                                              bestPosition,
                                              pruneMaxScoreInfosPerTask,
                                              keptCount,
                                              keptScores,
                                              keptPositions);
            ++inputCount;
            bestScore = colMax;
            bestPosition = targetIndex;
          }
          else if(colMax > bestScore)
          {
            bestScore = colMax;
            bestPosition = targetIndex;
          }
          previousCandidatePosition = targetIndex;
        }
      }
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    if(haveGroup)
    {
      prealign_scoreinfo_prune_consider(bestScore,
                                        bestPosition,
                                        pruneMaxScoreInfosPerTask,
                                        keptCount,
                                        keptScores,
                                        keptPositions);
      ++inputCount;
    }

    for(int i = 0; i < keptCount; ++i)
    {
      int best = i;
      for(int j = i + 1; j < keptCount; ++j)
      {
        if(keptPositions[j] < keptPositions[best] ||
           (keptPositions[j] == keptPositions[best] && keptScores[j] > keptScores[best]))
        {
          best = j;
        }
      }
      if(best != i)
      {
        const int tmpScore = keptScores[i];
        const int tmpPosition = keptPositions[i];
        keptScores[i] = keptScores[best];
        keptPositions[i] = keptPositions[best];
        keptScores[best] = tmpScore;
        keptPositions[best] = tmpPosition;
      }
    }

    for(int i = 0; i < keptCount; ++i)
    {
      taskOut[i].score = keptScores[i];
      taskOut[i].position = keptPositions[i];
    }
    outCounts[taskIndex] = keptCount;
    outInputCounts[taskIndex] = inputCount;
    (void)overflowFlag;
  }
}

__global__ void prealign_cuda_column_scoreinfo_pruned_compact_kernel(const int *columnMaxima,
                                                                     const int *minScores,
                                                                     int taskCount,
                                                                     int targetLength,
                                                                     int pruneMaxScoreInfosPerTask,
                                                                     PreAlignCudaPeak *outScoreInfos,
                                                                     int *outCounts,
                                                                     int *outInputCounts,
                                                                     int *overflowFlag)
{
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || threadIdx.x != 0)
  {
    return;
  }

  extern __shared__ unsigned char smem[];
  int *keptScores = reinterpret_cast<int *>(smem);
  int *keptPositions = keptScores + pruneMaxScoreInfosPerTask;
  for(int k = 0; k < pruneMaxScoreInfosPerTask; ++k)
  {
    keptScores[k] = -1;
    keptPositions[k] = -1;
  }

  const int *taskColumns =
    columnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  PreAlignCudaPeak *taskOut =
    outScoreInfos + static_cast<size_t>(taskIndex) * static_cast<size_t>(pruneMaxScoreInfosPerTask);

  int maxScore = 0;
  for(int i = 0; i < targetLength; ++i)
  {
    if(taskColumns[i] > maxScore)
    {
      maxScore = taskColumns[i];
    }
  }
  const int minScore =
    minScores != NULL ?
      minScores[taskIndex] :
      static_cast<int>(static_cast<double>(maxScore) * 0.8);

  const int suppressBp = 5;
  const int sswByteBias = 4;
  int inputCount = 0;
  int keptCount = 0;
  int byteOverflowMaxScore = 0;
  bool haveGroup = false;
  int previousCandidatePosition = -1;
  int bestScore = 0;
  int bestPosition = -1;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const int colMax = taskColumns[targetIndex];
    if(colMax > byteOverflowMaxScore)
    {
      byteOverflowMaxScore = colMax;
      if(byteOverflowMaxScore + sswByteBias >= 255)
      {
        break;
      }
    }
    if(colMax <= minScore)
    {
      continue;
    }
    if(!haveGroup)
    {
      bestScore = colMax;
      bestPosition = targetIndex;
      previousCandidatePosition = targetIndex;
      haveGroup = true;
      continue;
    }

    const int positionDelta = targetIndex - previousCandidatePosition;
    if(positionDelta <= 0 || positionDelta >= suppressBp)
    {
      prealign_scoreinfo_prune_consider(bestScore,
                                        bestPosition,
                                        pruneMaxScoreInfosPerTask,
                                        keptCount,
                                        keptScores,
                                        keptPositions);
      ++inputCount;
      bestScore = colMax;
      bestPosition = targetIndex;
    }
    else if(colMax > bestScore)
    {
      bestScore = colMax;
      bestPosition = targetIndex;
    }
    previousCandidatePosition = targetIndex;
  }

  if(haveGroup)
  {
    prealign_scoreinfo_prune_consider(bestScore,
                                      bestPosition,
                                      pruneMaxScoreInfosPerTask,
                                      keptCount,
                                      keptScores,
                                      keptPositions);
    ++inputCount;
  }

  for(int i = 0; i < keptCount; ++i)
  {
    int best = i;
    for(int j = i + 1; j < keptCount; ++j)
    {
      if(keptPositions[j] < keptPositions[best] ||
         (keptPositions[j] == keptPositions[best] && keptScores[j] > keptScores[best]))
      {
        best = j;
      }
    }
    if(best != i)
    {
      const int tmpScore = keptScores[i];
      const int tmpPosition = keptPositions[i];
      keptScores[i] = keptScores[best];
      keptPositions[i] = keptPositions[best];
      keptScores[best] = tmpScore;
      keptPositions[best] = tmpPosition;
    }
  }

  for(int i = 0; i < keptCount; ++i)
  {
    taskOut[i].score = keptScores[i];
    taskOut[i].position = keptPositions[i];
  }
  outCounts[taskIndex] = keptCount;
  outInputCounts[taskIndex] = inputCount;
  (void)overflowFlag;
}

__global__ void prealign_cuda_max_score_batch_kernel(const int16_t *profile,
                                                     const uint8_t *encodedTargets,
                                                     int taskCount,
                                                     int targetLength,
                                                     int segLen,
                                                     int *outScores)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }

  extern __shared__ unsigned char batchSmem[];
  int16_t *E = reinterpret_cast<int16_t *>(batchSmem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);

  const int gapOpen = 16;
  const int gapExtend = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;
  int taskLaneMax = 0;

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

    taskLaneMax = cuda_max_int(taskLaneMax, colLaneMax);
    __syncwarp();
  }

  const int taskMax = cuda_warp_reduce_max_int(taskLaneMax);
  if(lane == 0)
  {
    outScores[taskIndex] = taskMax;
  }
}

// Full-query endpoint projection used by the long-query attempt-score spike.
// The recurrence intentionally mirrors prealign_cuda_max_score_batch_kernel;
// only the winning target column and logical query lane are retained.
__global__ void prealign_cuda_max_endpoint_batch_kernel(const int16_t *profile,
                                                         const uint8_t *encodedTargets,
                                                         int taskCount,
                                                         int targetLength,
                                                         int segLen,
                                                         int queryLength,
                                                         PreAlignCudaPeak *outPeaks,
                                                         int *outQueryEnds)
{
  const int lane = static_cast<int>(threadIdx.x);
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || lane >= 32)
  {
    return;
  }

  extern __shared__ unsigned char batchSmem[];
  int16_t *E = reinterpret_cast<int16_t *>(batchSmem);
  int16_t *H0 = E + segLen * 32;
  int16_t *H1 = H0 + segLen * 32;

  for(int i = lane; i < segLen * 32; i += 32)
  {
    E[i] = 0;
    H0[i] = 0;
    H1[i] = 0;
  }
  __syncwarp();

  const uint8_t *taskTarget =
    encodedTargets + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  const int gapOpen = 16;
  const int gapExtend = 4;

  int16_t *HLoad = H0;
  int16_t *HStore = H1;
  int taskBestScore = 0;
  int taskBestTarget = -1;
  int taskBestQuery = 0;

  for(int targetIndex = 0; targetIndex < targetLength; ++targetIndex)
  {
    const uint8_t targetCode = taskTarget[targetIndex];
    const int16_t *profileRow =
      profile + static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) * 32u;

    int colLaneMax = 0;
    int colLaneQuery = -1;
    int vF = 0;
    int vH = static_cast<int>(HLoad[(segLen - 1) * 32 + lane]);
    vH = cuda_warp_shift_left_1(vH, lane);

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
      const int queryPos = lane * segLen + segIndex;
      if(queryPos < queryLength &&
         (vH > colLaneMax ||
          (vH == colLaneMax && vH > 0 &&
           (colLaneQuery < 0 || queryPos < colLaneQuery))))
      {
        colLaneMax = vH;
        colLaneQuery = queryPos;
      }

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
    vF = cuda_warp_shift_left_1(vF, lane);
    while(true)
    {
      vHStore = cuda_max_int(vHStore, vF);
      HStore[segIndex * 32 + lane] = static_cast<int16_t>(vHStore);
      const int queryPos = lane * segLen + segIndex;
      if(queryPos < queryLength &&
         (vHStore > colLaneMax ||
          (vHStore == colLaneMax && vHStore > 0 &&
           (colLaneQuery < 0 || queryPos < colLaneQuery))))
      {
        colLaneMax = vHStore;
        colLaneQuery = queryPos;
      }

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
        vF = cuda_warp_shift_left_1(vF, lane);
      }
      vHStore = static_cast<int>(HStore[segIndex * 32 + lane]);
    }

    int16_t *tmp = HLoad;
    HLoad = HStore;
    HStore = tmp;

    int colMax = colLaneMax;
    int colQuery = colLaneQuery;
    for(int offset = 16; offset > 0; offset >>= 1)
    {
      const int otherScore = __shfl_down_sync(0xffffffffu, colMax, offset);
      const int otherQuery = __shfl_down_sync(0xffffffffu, colQuery, offset);
      if(otherScore > colMax ||
         (otherScore == colMax && otherScore > 0 && otherQuery >= 0 &&
          (colQuery < 0 || otherQuery < colQuery)))
      {
        colMax = otherScore;
        colQuery = otherQuery;
      }
    }
    if(lane == 0 && colMax > taskBestScore)
    {
      taskBestScore = colMax;
      taskBestTarget = targetIndex;
      taskBestQuery = colQuery >= 0 ? colQuery : 0;
    }
    __syncwarp();
  }

  if(lane == 0)
  {
    PreAlignCudaPeak output;
    output.score = taskBestScore;
    output.position = taskBestTarget;
    outPeaks[taskIndex] = output;
    outQueryEnds[taskIndex] = taskBestQuery;
  }
}

static __device__ __forceinline__ int prealign_cuda_sat_i16_add(int left,int right)
{
  const int value = left + right;
  return value > 32767 ? 32767 : (value < -32768 ? -32768 : value);
}

template<int kLanes>
static __device__ __forceinline__ int prealign_cuda_subwarp_max(int value,
                                                                unsigned int mask)
{
  for(int offset = kLanes / 2; offset > 0; offset >>= 1)
  {
    value = cuda_max_int(
      value, __shfl_down_sync(mask, value, offset, kLanes));
  }
  return __shfl_sync(mask, value, 0, kLanes);
}

template<int kLanes>
static __device__ __forceinline__ int prealign_cuda_subwarp_min(int value,
                                                                unsigned int mask)
{
  for(int offset = kLanes / 2; offset > 0; offset >>= 1)
  {
    const int other = __shfl_down_sync(mask, value, offset, kLanes);
    value = other < value ? other : value;
  }
  return __shfl_sync(mask, value, 0, kLanes);
}

template<int kLanes>
static __device__ __forceinline__ int prealign_cuda_subwarp_shift_left(int value,
                                                                      int lane,
                                                                      unsigned int mask)
{
  const int shifted = __shfl_up_sync(mask, value, 1, kLanes);
  return lane == 0 ? 0 : shifted;
}

static __device__ __forceinline__ int prealign_cuda_profile_score(
  const int16_t *profile,
  int profileSegLen,
  int queryPosition,
  int targetCode)
{
  const int profileLane = queryPosition / profileSegLen;
  const int profileSegment = queryPosition - profileLane * profileSegLen;
  return static_cast<int>(profile[
    (static_cast<size_t>(targetCode) * static_cast<size_t>(profileSegLen) +
     static_cast<size_t>(profileSegment)) * 32u +
    static_cast<size_t>(profileLane)]);
}

// Exact modified-SSW pass.  kLanes deliberately matches the CPU SSE profile:
// 16 lanes for byte8 and 8 lanes for word16.  In particular, byte8 keeps the
// CPU's unsigned saturation and signed lazy-F termination comparison.
template<int kLanes,bool kBytePath,typename Storage>
static __device__ void prealign_cuda_exact_ssw_pass(
  const int16_t *profile,
  int profileSegLen,
  const uint8_t *target,
  int logicalQueryLength,
  int originalQueryEnd,
  int referenceLength,
  int originalReferenceEnd,
  bool reverse,
  bool trackQueryEnd,
  int terminateScore,
  Storage *workspace,
  int lane,
  unsigned int mask,
  int *scoreOut,
  int *referenceEndOut,
  int *queryEndOut,
  bool *overflowOut)
{
  const int segmentLength =
    logicalQueryLength / kLanes + (logicalQueryLength % kLanes == 0 ? 0 : 1);
  const int paddedQueryLength = segmentLength * kLanes;
  Storage *E = workspace;
  Storage *H0 = E + paddedQueryLength;
  Storage *H1 = H0 + paddedQueryLength;

  for(int segment = 0; segment < segmentLength; ++segment)
  {
    const int offset = segment * kLanes + lane;
    E[offset] = 0;
    H0[offset] = 0;
    H1[offset] = 0;
  }
  __syncwarp(mask);

  Storage *HStore = H0;
  Storage *HLoad = H1;
  int laneMaximum = 0;
  int globalMaximum = 0;
  int bestReference = kBytePath ? -1 : 0;
  int bestQuery = logicalQueryLength - 1;
  bool overflow = false;

  for(int column = 0; column < referenceLength; ++column)
  {
    const int referencePosition = reverse ?
      originalReferenceEnd - column : column;
    const int targetCode = static_cast<int>(target[referencePosition]);
    int vF = 0;
    int vH = lane == 0 ? 0 :
      static_cast<int>(HStore[(segmentLength - 1) * kLanes + lane - 1]);
    Storage *swap = HLoad;
    HLoad = HStore;
    HStore = swap;
    int columnLaneMaximum = 0;

    for(int segment = 0; segment < segmentLength; ++segment)
    {
      const int offset = segment * kLanes + lane;
      const int logicalQueryPosition = segment + lane * segmentLength;
      int substitution = 0;
      if(logicalQueryPosition < logicalQueryLength)
      {
        const int originalQueryPosition = reverse ?
          originalQueryEnd - logicalQueryPosition : logicalQueryPosition;
        substitution = prealign_cuda_profile_score(
          profile, profileSegLen, originalQueryPosition, targetCode);
      }
      const int oldH = static_cast<int>(HLoad[offset]);
      int vE = static_cast<int>(E[offset]);
      if(kBytePath)
      {
        vH = cuda_sat_u8_add(vH, substitution + 4);
        vH = cuda_sat_u8_sub(vH, 4);
      }
      else
      {
        vH = prealign_cuda_sat_i16_add(vH, substitution);
        vH = cuda_clamp_nonnegative(vH);
      }
      vH = cuda_max_int(vH, vE);
      vH = cuda_max_int(vH, vF);
      columnLaneMaximum = cuda_max_int(columnLaneMaximum, vH);
      HStore[offset] = static_cast<Storage>(vH);

      const int opened = cuda_clamp_nonnegative(vH - 16);
      vE = cuda_clamp_nonnegative(vE - 4);
      E[offset] = static_cast<Storage>(cuda_max_int(vE, opened));
      vF = cuda_clamp_nonnegative(vF - 4);
      vF = cuda_max_int(vF, opened);
      vH = oldH;
    }

    bool lazyDone = false;
    for(int iteration = 0; iteration < kLanes && !lazyDone; ++iteration)
    {
      vF = prealign_cuda_subwarp_shift_left<kLanes>(vF, lane, mask);
      for(int segment = 0; segment < segmentLength; ++segment)
      {
        const int offset = segment * kLanes + lane;
        int stored = static_cast<int>(HStore[offset]);
        stored = cuda_max_int(stored, vF);
        HStore[offset] = static_cast<Storage>(stored);
        columnLaneMaximum = cuda_max_int(columnLaneMaximum, stored);
        const int opened = cuda_clamp_nonnegative(stored - 16);
        vF = cuda_clamp_nonnegative(vF - 4);
        const bool shouldContinue = kBytePath ?
          static_cast<int8_t>(vF) > static_cast<int8_t>(opened) :
          vF > opened;
        if((__ballot_sync(mask, shouldContinue) & mask) == 0)
        {
          lazyDone = true;
          break;
        }
      }
    }

    laneMaximum = cuda_max_int(laneMaximum, columnLaneMaximum);
    const int currentMaximum = prealign_cuda_subwarp_max<kLanes>(laneMaximum, mask);
    const int columnMaximum = prealign_cuda_subwarp_max<kLanes>(
      columnLaneMaximum, mask);
    const bool newBest = currentMaximum > globalMaximum;
    if(newBest)
    {
      globalMaximum = currentMaximum;
      if(kBytePath && globalMaximum + 4 >= 255)
      {
        overflow = true;
      }
      else
      {
        bestReference = referencePosition;
        if(trackQueryEnd)
        {
          int candidateQuery = logicalQueryLength - 1;
          for(int segment = 0; segment < segmentLength; ++segment)
          {
            const int logicalQueryPosition = segment + lane * segmentLength;
            if(logicalQueryPosition < logicalQueryLength &&
               static_cast<int>(HStore[segment * kLanes + lane]) ==
                 globalMaximum &&
               logicalQueryPosition < candidateQuery)
            {
              candidateQuery = logicalQueryPosition;
            }
          }
          bestQuery = prealign_cuda_subwarp_min<kLanes>(candidateQuery, mask);
        }
      }
    }
    __syncwarp(mask);
    if(overflow || (terminateScore >= 0 && columnMaximum == terminateScore))
    {
      break;
    }
  }

  if(trackQueryEnd && !overflow && globalMaximum == 0)
  {
    bestQuery = 0;
  }
  *scoreOut = overflow ? 255 : globalMaximum;
  *referenceEndOut = bestReference;
  *queryEndOut = bestQuery;
  *overflowOut = overflow;
  __syncwarp(mask);
}

template<int kLanes,bool kBytePath,typename Storage,int kTasksPerBlock,
         bool kComputeReverse>
static __device__ void prealign_cuda_exact_attempt_endpoint_body(
  const int16_t *profile,
  const uint8_t *encodedTargets,
  int taskCount,
  int paddedTargetLength,
  int profileSegLen,
  int queryLength,
  Storage *workspace,
  PreAlignCudaAttemptEndpoint *outEndpoints)
{
  const int warpLane = static_cast<int>(threadIdx.x);
  const int subwarp = warpLane / kLanes;
  const int lane = warpLane - subwarp * kLanes;
  const int taskIndex = static_cast<int>(blockIdx.x) * kTasksPerBlock + subwarp;
  if(subwarp >= kTasksPerBlock || taskIndex >= taskCount)
  {
    return;
  }
  const unsigned int mask = ((1u << kLanes) - 1u) << (subwarp * kLanes);
  const int paddedQueryLength =
    (queryLength + kLanes - 1) / kLanes * kLanes;
  Storage *taskWorkspace = workspace +
    static_cast<size_t>(subwarp) * static_cast<size_t>(3 * paddedQueryLength);
  if(!kBytePath &&
     outEndpoints[taskIndex].forwardScore != 255)
  {
    return;
  }

  const uint8_t *target = encodedTargets +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(paddedTargetLength);
  int forwardScore = 0;
  int targetEnd = kBytePath ? -1 : 0;
  int queryEnd = 0;
  bool overflow = false;
  prealign_cuda_exact_ssw_pass<kLanes,kBytePath,Storage>(
    profile, profileSegLen, target, queryLength, queryLength - 1,
    paddedTargetLength, paddedTargetLength - 1, false, true, -1,
    taskWorkspace,
    lane, mask,
    &forwardScore, &targetEnd, &queryEnd, &overflow);

  if(lane == 0)
  {
    outEndpoints[taskIndex].forwardScore = forwardScore;
    outEndpoints[taskIndex].reverseScore = 0;
    outEndpoints[taskIndex].canonicalScore = overflow ? 255 : forwardScore;
    outEndpoints[taskIndex].targetEnd = targetEnd;
    outEndpoints[taskIndex].queryEnd = queryEnd;
    outEndpoints[taskIndex].numericPath = kBytePath ?
      PREALIGN_CUDA_NUMERIC_PATH_BYTE8 : PREALIGN_CUDA_NUMERIC_PATH_WORD16;
  }
  if(overflow || !kComputeReverse)
  {
    return;
  }

  int reverseScore = 0;
  int reverseReferenceEnd = kBytePath ? -1 : 0;
  int reverseQueryEnd = 0;
  bool reverseOverflow = false;
  if(targetEnd >= 0 && queryEnd >= 0)
  {
    prealign_cuda_exact_ssw_pass<kLanes,kBytePath,Storage>(
      profile, profileSegLen, target, queryEnd + 1, queryEnd,
      targetEnd + 1, targetEnd, true, false, forwardScore, taskWorkspace,
      lane, mask,
      &reverseScore, &reverseReferenceEnd, &reverseQueryEnd,
      &reverseOverflow);
  }
  if(lane == 0)
  {
    outEndpoints[taskIndex].reverseScore = reverseScore;
    outEndpoints[taskIndex].canonicalScore =
      reverseScore < forwardScore ? reverseScore : forwardScore;
  }
}

__global__ void prealign_cuda_exact_attempt_endpoint_byte_kernel(
  const int16_t *profile,
  const uint8_t *encodedTargets,
  int taskCount,
  int paddedTargetLength,
  int profileSegLen,
  int queryLength,
  PreAlignCudaAttemptEndpoint *outEndpoints)
{
  extern __shared__ unsigned char workspaceBytes[];
  prealign_cuda_exact_attempt_endpoint_body<16,true,uint8_t,1,true>(
    profile, encodedTargets, taskCount, paddedTargetLength, profileSegLen,
    queryLength, reinterpret_cast<uint8_t *>(workspaceBytes), outEndpoints);
}

__global__ void prealign_cuda_exact_attempt_endpoint_word_kernel(
  const int16_t *profile,
  const uint8_t *encodedTargets,
  int taskCount,
  int paddedTargetLength,
  int profileSegLen,
  int queryLength,
  PreAlignCudaAttemptEndpoint *outEndpoints)
{
  extern __shared__ unsigned char workspaceBytes[];
  prealign_cuda_exact_attempt_endpoint_body<8,false,int16_t,1,true>(
    profile, encodedTargets, taskCount, paddedTargetLength, profileSegLen,
    queryLength, reinterpret_cast<int16_t *>(workspaceBytes), outEndpoints);
}

__global__ void prealign_cuda_exact_attempt_forward_byte_kernel(
  const int16_t *profile,
  const uint8_t *encodedTargets,
  int taskCount,
  int paddedTargetLength,
  int profileSegLen,
  int queryLength,
  PreAlignCudaAttemptEndpoint *outEndpoints)
{
  extern __shared__ unsigned char workspaceBytes[];
  prealign_cuda_exact_attempt_endpoint_body<16,true,uint8_t,1,false>(
    profile, encodedTargets, taskCount, paddedTargetLength, profileSegLen,
    queryLength, reinterpret_cast<uint8_t *>(workspaceBytes), outEndpoints);
}

__global__ void prealign_cuda_exact_attempt_forward_word_kernel(
  const int16_t *profile,
  const uint8_t *encodedTargets,
  int taskCount,
  int paddedTargetLength,
  int profileSegLen,
  int queryLength,
  PreAlignCudaAttemptEndpoint *outEndpoints)
{
  extern __shared__ unsigned char workspaceBytes[];
  prealign_cuda_exact_attempt_endpoint_body<8,false,int16_t,1,false>(
    profile, encodedTargets, taskCount, paddedTargetLength, profileSegLen,
    queryLength, reinterpret_cast<int16_t *>(workspaceBytes), outEndpoints);
}

__global__ void prealign_cuda_reduce_column_max_scores_kernel(const int *columnMaxima,
                                                             int taskCount,
                                                             int targetLength,
                                                             int *outScores)
{
  const int taskIndex = static_cast<int>(blockIdx.x);
  const int tid = static_cast<int>(threadIdx.x);
  if(taskIndex >= taskCount)
  {
    return;
  }

  extern __shared__ int reduceSmem[];
  int localMax = 0;
  const int *taskColumns =
    columnMaxima + static_cast<size_t>(taskIndex) * static_cast<size_t>(targetLength);
  for(int i = tid; i < targetLength; i += static_cast<int>(blockDim.x))
  {
    localMax = cuda_max_int(localMax, taskColumns[i]);
  }
  reduceSmem[tid] = localMax;
  __syncthreads();

  for(int stride = static_cast<int>(blockDim.x) / 2; stride > 0; stride >>= 1)
  {
    if(tid < stride)
    {
      reduceSmem[tid] = cuda_max_int(reduceSmem[tid], reduceSmem[tid + stride]);
    }
    __syncthreads();
  }

  if(tid == 0)
  {
    outScores[taskIndex] = reduceSmem[0];
  }
}

__global__ void prealign_cuda_scores_to_min_scores_kernel(const int *scores,
                                                          int taskCount,
                                                          int *outMinScores)
{
  const int index =
    static_cast<int>(blockIdx.x) * static_cast<int>(blockDim.x) +
    static_cast<int>(threadIdx.x);
  if(index >= taskCount)
  {
    return;
  }
  outMinScores[index] =
    static_cast<int>(static_cast<double>(scores[index]) * 0.8);
}

__global__ void prealign_cuda_scoreinfos_to_attempt_descriptors_kernel(
  const PreAlignCudaPeak *scoreInfos,
  const int *scoreInfoCounts,
  int taskCount,
  int maxScoreInfosPerTask,
  int maxDescriptorsPerTask,
  int ntMinLength,
  int scoringConfigKey,
  PreAlignCudaAttemptDescriptor *outDescriptors,
  int *outDescriptorCounts,
  int *overflowFlag)
{
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || threadIdx.x != 0)
  {
    return;
  }

  const int scoreInfoCount = scoreInfoCounts[taskIndex];
  int descriptorCount = 0;
  PreAlignCudaAttemptDescriptor *taskOut =
    outDescriptors +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxDescriptorsPerTask);
  const PreAlignCudaPeak *taskScoreInfos =
    scoreInfos +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxScoreInfosPerTask);

  for(int scoreInfoOrder = 0; scoreInfoOrder < scoreInfoCount; ++scoreInfoOrder)
  {
    const PreAlignCudaPeak peak = taskScoreInfos[scoreInfoOrder];
    for(int attemptOrder = 0;
        prealign_cuda_legacy_byte_attempt_order_valid(attemptOrder);
        ++attemptOrder)
    {
      const int cutlength =
        prealign_cuda_legacy_byte_attempt_cutlength(peak.score,
                                                    peak.position,
                                                    attemptOrder);
      const int targetStart = peak.position - cutlength + 1;
      if(targetStart < 0 || cutlength <= 0)
      {
        continue;
      }
      if(descriptorCount >= maxDescriptorsPerTask)
      {
        atomicExch(overflowFlag, 1);
        continue;
      }

      PreAlignCudaAttemptDescriptor descriptor;
      descriptor.taskIndex = taskIndex;
      descriptor.scoreInfoPosition = peak.position;
      descriptor.scoreInfoScore = peak.score;
      descriptor.scoreInfoOrder = scoreInfoOrder;
      descriptor.attemptOrder = attemptOrder;
      descriptor.targetStart = targetStart;
      descriptor.cutlength = cutlength;
      descriptor.targetEndRequiredForFallback = cutlength - 1;
      descriptor.ntMinLength = ntMinLength;
      descriptor.scoringConfigKey = scoringConfigKey;
      descriptor.overflowFlag = 0;
      taskOut[descriptorCount] = descriptor;
      ++descriptorCount;
    }
  }

  outDescriptorCounts[taskIndex] = descriptorCount;
}

__global__ void prealign_cuda_select_prefix_attempt_descriptors_kernel(
  const PreAlignCudaAttemptDescriptor *inDescriptors,
  const int *inDescriptorCounts,
  int taskCount,
  int maxDescriptorsPerTask,
  int prefixAttemptsPerScoreInfo,
  PreAlignCudaAttemptDescriptor *outDescriptors,
  int *outDescriptorCounts)
{
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || threadIdx.x != 0)
  {
    return;
  }

  const PreAlignCudaAttemptDescriptor *taskIn =
    inDescriptors +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxDescriptorsPerTask);
  PreAlignCudaAttemptDescriptor *taskOut =
    outDescriptors +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxDescriptorsPerTask);
  const int descriptorCount = inDescriptorCounts[taskIndex];
  int outCount = 0;
  int previousScoreInfoOrder = -1;
  int keptForScoreInfo = 0;

  for(int i = 0; i < descriptorCount; ++i)
  {
    const PreAlignCudaAttemptDescriptor descriptor = taskIn[i];
    if(descriptor.scoreInfoOrder != previousScoreInfoOrder)
    {
      previousScoreInfoOrder = descriptor.scoreInfoOrder;
      keptForScoreInfo = 0;
    }
    if(keptForScoreInfo < prefixAttemptsPerScoreInfo)
    {
      taskOut[outCount] = descriptor;
      ++outCount;
      ++keptForScoreInfo;
    }
  }

  outDescriptorCounts[taskIndex] = outCount;
}

__global__ void prealign_cuda_select_task_frontier_certificate_descriptors_kernel(
  const PreAlignCudaAttemptDescriptor *inDescriptors,
  const int *inDescriptorCounts,
  int taskCount,
  int maxDescriptorsPerTask,
  PreAlignCudaAttemptDescriptor *outDescriptors,
  int *outDescriptorCounts,
  int *outCertificateRows)
{
  const int taskIndex = static_cast<int>(blockIdx.x);
  if(taskIndex >= taskCount || threadIdx.x != 0)
  {
    return;
  }

  const PreAlignCudaAttemptDescriptor *taskIn =
    inDescriptors +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxDescriptorsPerTask);
  PreAlignCudaAttemptDescriptor *taskOut =
    outDescriptors +
    static_cast<size_t>(taskIndex) * static_cast<size_t>(maxDescriptorsPerTask);
  const int descriptorCount = inDescriptorCounts[taskIndex];
  int outCount = 0;
  int certificateRows = 0;
  int selectedScoreInfoOrder = -1;

  for(int i = 0; i < descriptorCount; ++i)
  {
    const PreAlignCudaAttemptDescriptor descriptor = taskIn[i];
    if(selectedScoreInfoOrder < 0)
    {
      selectedScoreInfoOrder = descriptor.scoreInfoOrder;
      ++certificateRows;
    }
    if(descriptor.scoreInfoOrder == selectedScoreInfoOrder)
    {
      taskOut[outCount] = descriptor;
      ++outCount;
    }
  }

  outDescriptorCounts[taskIndex] = outCount;
  outCertificateRows[taskIndex] = certificateRows;
}

__global__ void prealign_cuda_new_engine_certificate_kernel(
  const PreAlignCudaNewEngineScoreInfoTask *tasks,
  int taskCount,
  const PreAlignCudaNewEngineCandidateGroup *candidateGroups,
  int candidateGroupCount,
  const PreAlignCudaNewEngineReplayAttempt *replayAttempts,
  int replayAttemptCount,
  PreAlignCudaNewEngineSkippedWorkCertificate *outCertificates,
  unsigned long long *outSkippedGroups,
  unsigned long long *outSkippedAttempts,
  unsigned long long *outFallbackGroups)
{
  const int taskIndex =
    static_cast<int>(blockIdx.x) * static_cast<int>(blockDim.x) +
    static_cast<int>(threadIdx.x);
  if(taskIndex >= taskCount)
  {
    return;
  }

  const PreAlignCudaNewEngineScoreInfoTask task = tasks[taskIndex];
  PreAlignCudaNewEngineSkippedWorkCertificate certificate;
  certificate.certificateValidBeforeD2h = 1;
  certificate.finalCpuOutputMembershipRequiredForCertificate = 0;
  certificate.skippedScoreInfoUpperBoundScore = task.minScore > 0 ? task.minScore - 1 : 0;

  int selectedGroupCount = 0;
  int selectedAttemptCount = 0;
  int maxSkippedScore = 0;
  int maxSkippedTargetSpan = 0;
  int fallback = 0;
  for(int groupIndex = 0; groupIndex < candidateGroupCount; ++groupIndex)
  {
    const PreAlignCudaNewEngineCandidateGroup group = candidateGroups[groupIndex];
    if(group.attemptStartIndex < 0 || group.attemptCount < 0 ||
       group.attemptStartIndex + group.attemptCount > replayAttemptCount)
    {
      fallback = 1;
      continue;
    }
    if(group.score >= task.minScore)
    {
      ++selectedGroupCount;
      selectedAttemptCount += group.attemptCount;
      continue;
    }

    maxSkippedScore = cuda_max_int(maxSkippedScore, group.score);
    atomicAdd(outSkippedGroups, 1ULL);
    atomicAdd(outSkippedAttempts,
              static_cast<unsigned long long>(group.attemptCount > 0 ? group.attemptCount : 0));
    for(int attemptOffset = 0; attemptOffset < group.attemptCount; ++attemptOffset)
    {
      const PreAlignCudaNewEngineReplayAttempt attempt =
        replayAttempts[group.attemptStartIndex + attemptOffset];
      const int targetSpan = attempt.targetEnd >= attempt.targetStart ?
        attempt.targetEnd - attempt.targetStart + 1 : 0;
      maxSkippedTargetSpan = cuda_max_int(maxSkippedTargetSpan, targetSpan);
    }
  }

  if(fallback != 0 || selectedGroupCount == 0 || selectedAttemptCount == 0)
  {
    certificate.taskOutputCapacityExhausted = 1;
    atomicAdd(outFallbackGroups, 1ULL);
  }
  certificate.skippedAttemptUpperBoundScore = maxSkippedScore;
  certificate.skippedAttemptUpperBoundNt = maxSkippedTargetSpan;
  certificate.skippedAttemptUpperBoundIdentity = maxSkippedScore;
  certificate.skippedAttemptUpperBoundStability = selectedAttemptCount;
  certificate.scoreInfoLocalBreakState = selectedGroupCount;
  outCertificates[taskIndex] = certificate;
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

static string prealign_cuda_shared_smem_exceeds_optin_error(size_t sharedBytes,
                                                            int optinLimit)
{
  ostringstream oss;
  oss << "legacy_byte_shared_smem_exceeds_optin_limit"
      << ": required=" << sharedBytes
      << " optin_limit=" << optinLimit;
  return oss.str();
}

struct PreAlignCudaContext
{
  PreAlignCudaContext():
    initialized(false),
    device(0),
    capacityTasks(0),
    capacityTargetLength(0),
    capacityTopK(0),
    capacityColumnMaxTasks(0),
    capacityColumnMaxTargetLength(0),
    capacityScoreTasks(0),
    capacityAttemptEndpointTasks(0),
    capacityScoreInfoTasks(0),
    capacityScoreInfoMaxPerTask(0),
    capacityDescriptorTasks(0),
    capacityDescriptorsPerTask(0),
    capacityGlobalStateTasks(0),
    capacityGlobalStateSegLen(0),
    targetsDevice(NULL),
    peaksDevice(NULL),
    columnMaximaDevice(NULL),
    scoresDevice(NULL),
    attemptEndpointsDevice(NULL),
    minScoresDevice(NULL),
    scoreInfoDevice(NULL),
    scoreInfoCountsDevice(NULL),
    scoreInfoInputCountsDevice(NULL),
    scoreInfoOverflowDevice(NULL),
    descriptorsDevice(NULL),
    descriptorCountsDevice(NULL),
    summaryDescriptorsDevice(NULL),
    summaryDescriptorCountsDevice(NULL),
    certificateRowsDevice(NULL),
    descriptorOverflowDevice(NULL),
    globalStateDevice(NULL),
    startEvent(NULL),
    stopEvent(NULL)
  {
  }

  bool initialized;
  int device;
  int capacityTasks;
  int capacityTargetLength;
  int capacityTopK;
  int capacityColumnMaxTasks;
  int capacityColumnMaxTargetLength;
  int capacityScoreTasks;
  int capacityAttemptEndpointTasks;
  int capacityScoreInfoTasks;
  int capacityScoreInfoMaxPerTask;
  int capacityDescriptorTasks;
  int capacityDescriptorsPerTask;
  int capacityGlobalStateTasks;
  int capacityGlobalStateSegLen;

  uint8_t *targetsDevice;
  PreAlignCudaPeak *peaksDevice;
  int *columnMaximaDevice;
  int *scoresDevice;
  PreAlignCudaAttemptEndpoint *attemptEndpointsDevice;
  int *minScoresDevice;
  PreAlignCudaPeak *scoreInfoDevice;
  int *scoreInfoCountsDevice;
  int *scoreInfoInputCountsDevice;
  int *scoreInfoOverflowDevice;
  PreAlignCudaAttemptDescriptor *descriptorsDevice;
  int *descriptorCountsDevice;
  PreAlignCudaAttemptDescriptor *summaryDescriptorsDevice;
  int *summaryDescriptorCountsDevice;
  int *certificateRowsDevice;
  int *descriptorOverflowDevice;
  int16_t *globalStateDevice;

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

static bool ensure_prealign_cuda_column_maxima_capacity_locked(PreAlignCudaContext &context,
                                                               int taskCount,
                                                               int targetLength,
                                                               string *errorOut)
{
  if(taskCount <= context.capacityColumnMaxTasks &&
     targetLength <= context.capacityColumnMaxTargetLength &&
     context.columnMaximaDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityColumnMaxTasks, taskCount);
  const int newCapTargetLength = max(context.capacityColumnMaxTargetLength, targetLength);
  const size_t columnBytes =
    static_cast<size_t>(newCapTasks) * static_cast<size_t>(newCapTargetLength) * sizeof(int);
  int *newColumnMaximaDevice = NULL;

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newColumnMaximaDevice), columnBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.columnMaximaDevice != NULL)
  {
    cudaFree(context.columnMaximaDevice);
  }

  context.columnMaximaDevice = newColumnMaximaDevice;
  context.capacityColumnMaxTasks = newCapTasks;
  context.capacityColumnMaxTargetLength = newCapTargetLength;
  return true;
}

static bool ensure_prealign_cuda_scores_capacity_locked(PreAlignCudaContext &context,
                                                        int taskCount,
                                                        string *errorOut)
{
  if(taskCount <= context.capacityScoreTasks && context.scoresDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityScoreTasks, taskCount);
  const size_t scoreBytes = static_cast<size_t>(newCapTasks) * sizeof(int);
  int *newScoresDevice = NULL;

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newScoresDevice), scoreBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.scoresDevice != NULL)
  {
    cudaFree(context.scoresDevice);
  }

  context.scoresDevice = newScoresDevice;
  context.capacityScoreTasks = newCapTasks;
  return true;
}

static bool ensure_prealign_cuda_attempt_endpoint_capacity_locked(
  PreAlignCudaContext &context,
  int taskCount,
  string *errorOut)
{
  if(taskCount <= context.capacityAttemptEndpointTasks &&
     context.attemptEndpointsDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityAttemptEndpointTasks, taskCount);
  const size_t bytes = static_cast<size_t>(newCapTasks) *
    sizeof(PreAlignCudaAttemptEndpoint);
  PreAlignCudaAttemptEndpoint *newEndpointsDevice = NULL;
  const cudaError_t status = cudaMalloc(
    reinterpret_cast<void **>(&newEndpointsDevice), bytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  if(context.attemptEndpointsDevice != NULL)
  {
    cudaFree(context.attemptEndpointsDevice);
  }
  context.attemptEndpointsDevice = newEndpointsDevice;
  context.capacityAttemptEndpointTasks = newCapTasks;
  return true;
}

static bool ensure_prealign_cuda_scoreinfo_capacity_locked(PreAlignCudaContext &context,
                                                           int taskCount,
                                                           int maxScoreInfosPerTask,
                                                           string *errorOut)
{
  if(taskCount <= context.capacityScoreInfoTasks &&
     maxScoreInfosPerTask <= context.capacityScoreInfoMaxPerTask &&
     context.minScoresDevice != NULL &&
     context.scoreInfoDevice != NULL &&
     context.scoreInfoCountsDevice != NULL &&
     context.scoreInfoInputCountsDevice != NULL &&
     context.scoreInfoOverflowDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityScoreInfoTasks, taskCount);
  const int newCapMaxPerTask = max(context.capacityScoreInfoMaxPerTask, maxScoreInfosPerTask);
  const size_t minScoreBytes = static_cast<size_t>(newCapTasks) * sizeof(int);
  const size_t scoreInfoBytes =
    static_cast<size_t>(newCapTasks) *
    static_cast<size_t>(newCapMaxPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(newCapTasks) * sizeof(int);

  int *newMinScoresDevice = NULL;
  PreAlignCudaPeak *newScoreInfoDevice = NULL;
  int *newScoreInfoCountsDevice = NULL;
  int *newScoreInfoInputCountsDevice = NULL;
  int *newScoreInfoOverflowDevice = NULL;

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&newMinScoresDevice), minScoreBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newScoreInfoDevice), scoreInfoBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newMinScoresDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newScoreInfoCountsDevice), countBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newMinScoresDevice);
    cudaFree(newScoreInfoDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newScoreInfoInputCountsDevice), countBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newMinScoresDevice);
    cudaFree(newScoreInfoDevice);
    cudaFree(newScoreInfoCountsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newScoreInfoOverflowDevice), sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(newMinScoresDevice);
    cudaFree(newScoreInfoDevice);
    cudaFree(newScoreInfoCountsDevice);
    cudaFree(newScoreInfoInputCountsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.minScoresDevice != NULL)
  {
    cudaFree(context.minScoresDevice);
  }
  if(context.scoreInfoDevice != NULL)
  {
    cudaFree(context.scoreInfoDevice);
  }
  if(context.scoreInfoCountsDevice != NULL)
  {
    cudaFree(context.scoreInfoCountsDevice);
  }
  if(context.scoreInfoInputCountsDevice != NULL)
  {
    cudaFree(context.scoreInfoInputCountsDevice);
  }
  if(context.scoreInfoOverflowDevice != NULL)
  {
    cudaFree(context.scoreInfoOverflowDevice);
  }

  context.minScoresDevice = newMinScoresDevice;
  context.scoreInfoDevice = newScoreInfoDevice;
  context.scoreInfoCountsDevice = newScoreInfoCountsDevice;
  context.scoreInfoInputCountsDevice = newScoreInfoInputCountsDevice;
  context.scoreInfoOverflowDevice = newScoreInfoOverflowDevice;
  context.capacityScoreInfoTasks = newCapTasks;
  context.capacityScoreInfoMaxPerTask = newCapMaxPerTask;
  return true;
}

static bool ensure_prealign_cuda_descriptor_capacity_locked(
  PreAlignCudaContext &context,
  int taskCount,
  int maxDescriptorsPerTask,
  string *errorOut)
{
  if(taskCount <= context.capacityDescriptorTasks &&
     maxDescriptorsPerTask <= context.capacityDescriptorsPerTask &&
     context.descriptorsDevice != NULL &&
     context.descriptorCountsDevice != NULL &&
     context.summaryDescriptorsDevice != NULL &&
     context.summaryDescriptorCountsDevice != NULL &&
     context.certificateRowsDevice != NULL &&
     context.descriptorOverflowDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityDescriptorTasks, taskCount);
  const int newCapMaxPerTask =
    max(context.capacityDescriptorsPerTask, maxDescriptorsPerTask);
  const size_t descriptorBytes =
    static_cast<size_t>(newCapTasks) *
    static_cast<size_t>(newCapMaxPerTask) *
    sizeof(PreAlignCudaAttemptDescriptor);
  const size_t countBytes = static_cast<size_t>(newCapTasks) * sizeof(int);

  PreAlignCudaAttemptDescriptor *newDescriptorsDevice = NULL;
  int *newDescriptorCountsDevice = NULL;
  PreAlignCudaAttemptDescriptor *newSummaryDescriptorsDevice = NULL;
  int *newSummaryDescriptorCountsDevice = NULL;
  int *newCertificateRowsDevice = NULL;
  int *newDescriptorOverflowDevice = NULL;

  cudaError_t status =
    cudaMalloc(reinterpret_cast<void **>(&newDescriptorsDevice), descriptorBytes);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status =
    cudaMalloc(reinterpret_cast<void **>(&newDescriptorCountsDevice), countBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newDescriptorsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newSummaryDescriptorsDevice),
                      descriptorBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newDescriptorsDevice);
    cudaFree(newDescriptorCountsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status =
    cudaMalloc(reinterpret_cast<void **>(&newSummaryDescriptorCountsDevice), countBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newDescriptorsDevice);
    cudaFree(newDescriptorCountsDevice);
    cudaFree(newSummaryDescriptorsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status =
    cudaMalloc(reinterpret_cast<void **>(&newCertificateRowsDevice), countBytes);
  if(status != cudaSuccess)
  {
    cudaFree(newDescriptorsDevice);
    cudaFree(newDescriptorCountsDevice);
    cudaFree(newSummaryDescriptorsDevice);
    cudaFree(newSummaryDescriptorCountsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaMalloc(reinterpret_cast<void **>(&newDescriptorOverflowDevice),
                      sizeof(int));
  if(status != cudaSuccess)
  {
    cudaFree(newDescriptorsDevice);
    cudaFree(newDescriptorCountsDevice);
    cudaFree(newSummaryDescriptorsDevice);
    cudaFree(newSummaryDescriptorCountsDevice);
    cudaFree(newCertificateRowsDevice);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.descriptorsDevice != NULL)
  {
    cudaFree(context.descriptorsDevice);
  }
  if(context.descriptorCountsDevice != NULL)
  {
    cudaFree(context.descriptorCountsDevice);
  }
  if(context.summaryDescriptorsDevice != NULL)
  {
    cudaFree(context.summaryDescriptorsDevice);
  }
  if(context.summaryDescriptorCountsDevice != NULL)
  {
    cudaFree(context.summaryDescriptorCountsDevice);
  }
  if(context.certificateRowsDevice != NULL)
  {
    cudaFree(context.certificateRowsDevice);
  }
  if(context.descriptorOverflowDevice != NULL)
  {
    cudaFree(context.descriptorOverflowDevice);
  }

  context.descriptorsDevice = newDescriptorsDevice;
  context.descriptorCountsDevice = newDescriptorCountsDevice;
  context.summaryDescriptorsDevice = newSummaryDescriptorsDevice;
  context.summaryDescriptorCountsDevice = newSummaryDescriptorCountsDevice;
  context.certificateRowsDevice = newCertificateRowsDevice;
  context.descriptorOverflowDevice = newDescriptorOverflowDevice;
  context.capacityDescriptorTasks = newCapTasks;
  context.capacityDescriptorsPerTask = newCapMaxPerTask;
  return true;
}

static bool ensure_prealign_cuda_global_state_capacity_locked(PreAlignCudaContext &context,
                                                              int taskCount,
                                                              int segLen,
                                                              string *errorOut)
{
  if(taskCount <= context.capacityGlobalStateTasks &&
     segLen <= context.capacityGlobalStateSegLen &&
     context.globalStateDevice != NULL)
  {
    return true;
  }

  const int newCapTasks = max(context.capacityGlobalStateTasks, taskCount);
  const int newCapSegLen = max(context.capacityGlobalStateSegLen, segLen);
  const size_t stateElements =
    static_cast<size_t>(newCapTasks) * static_cast<size_t>(3) *
    static_cast<size_t>(newCapSegLen) * 32u;
  int16_t *newGlobalStateDevice = NULL;

  cudaError_t status =
    cudaMalloc(reinterpret_cast<void **>(&newGlobalStateDevice),
               stateElements * sizeof(int16_t));
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  if(context.globalStateDevice != NULL)
  {
    cudaFree(context.globalStateDevice);
  }

  context.globalStateDevice = newGlobalStateDevice;
  context.capacityGlobalStateTasks = newCapTasks;
  context.capacityGlobalStateSegLen = newCapSegLen;
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

bool prealign_cuda_query_resource_limits(const PreAlignCudaQueryHandle &handle,
                                         PreAlignCudaResourceLimits *limitsOut,
                                         string *errorOut)
{
  if(limitsOut == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing resource limits output";
    }
    return false;
  }
  *limitsOut = PreAlignCudaResourceLimits();
  if(handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

  int device = handle.device;
  if(device < 0)
  {
    device = 0;
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
  if(deviceCount <= 0 || device >= deviceCount)
  {
    if(errorOut != NULL)
    {
      *errorOut = "requested CUDA device index is out of range";
    }
    return false;
  }

  int defaultLimit = 0;
  int optinLimit = 0;
  status = cudaDeviceGetAttribute(&defaultLimit,
                                  cudaDevAttrMaxSharedMemoryPerBlock,
                                  device);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }
  status = cudaDeviceGetAttribute(&optinLimit,
                                  cudaDevAttrMaxSharedMemoryPerBlockOptin,
                                  device);
  if(status != cudaSuccess)
  {
    optinLimit = defaultLimit;
  }

  limitsOut->requiredDynamicSmemBytes =
    static_cast<size_t>(3) *
    static_cast<size_t>(handle.segLen) *
    32u *
    sizeof(int16_t);
  limitsOut->defaultDynamicSmemLimitBytes =
    static_cast<size_t>(defaultLimit);
  limitsOut->optinDynamicSmemLimitBytes =
    static_cast<size_t>(optinLimit);
  limitsOut->resourceFit =
    limitsOut->requiredDynamicSmemBytes <=
    limitsOut->optinDynamicSmemLimitBytes;
  return true;
}

bool prealign_cuda_find_column_maxima_batch(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetsHost,
                                            int taskCount,
                                            int targetLength,
                                            vector<int> *outColumnMaxima,
                                            PreAlignCudaBatchResult *batchResult,
                                            string *errorOut)
{
  if(outColumnMaxima == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outColumnMaxima->clear();
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
  if(handle.profileDevice == 0 || handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_column_maxima_capacity_locked(*context,taskCount,targetLength,errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t columnBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStop);
  }
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(h2dStop);
  }

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->startEvent);
  }
  if(status == cudaSuccess)
	{
		const int threadsPerBlock = 32;
		const size_t sharedBytes =
			static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
		prealign_cuda_column_max_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
		                                                                                  context->targetsDevice,
		                                                                                  taskCount,
                                                                                       targetLength,
                                                                                       handle.segLen,
                                                                                       context->columnMaximaDevice);
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

  float kernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&kernelElapsedMs, context->startEvent, context->stopEvent);
  }

  vector<int> columnMaxima(static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength));
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(columnMaxima.data(),
                        context->columnMaximaDevice,
                        columnBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(d2hStop);
  }

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outColumnMaxima->swap(columnMaxima);
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(kernelElapsedMs) / 1000.0;
    batchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    batchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_scoreinfo_batch(const PreAlignCudaQueryHandle &handle,
                                        const uint8_t *encodedTargetsHost,
                                        const int *minScoresHost,
                                        int taskCount,
                                        int targetLength,
                                        int maxScoreInfosPerTask,
                                        vector<PreAlignCudaPeak> *outScoreInfos,
                                        vector<int> *outCounts,
                                        bool *overflowOut,
                                        PreAlignCudaBatchResult *batchResult,
                                        string *errorOut)
{
  if(outScoreInfos == NULL || outCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScoreInfos->clear();
  outCounts->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(encodedTargetsHost == NULL || minScoresHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input buffers";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || maxScoreInfosPerTask <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid scoreInfo dimensions";
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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scoreinfo_capacity_locked(*context,
                                                     taskCount,
                                                     maxScoreInfosPerTask,
                                                     errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t minScoreBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t scoreInfoBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxScoreInfosPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStop);
  }
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->minScoresDevice,
                        minScoresHost,
                        minScoreBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->scoreInfoOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(h2dStop);
  }

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->startEvent);
  }
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    const size_t sharedBytes =
      static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
    prealign_cuda_scoreinfo_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                       context->targetsDevice,
                                                                                       context->minScoresDevice,
                                                                                       taskCount,
                                                                                       targetLength,
                                                                                       handle.segLen,
                                                                                       maxScoreInfosPerTask,
                                                                                       context->scoreInfoDevice,
                                                                                       context->scoreInfoCountsDevice,
                                                                                       context->scoreInfoOverflowDevice);
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

  float kernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&kernelElapsedMs, context->startEvent, context->stopEvent);
  }

  vector<PreAlignCudaPeak> scoreInfos(
    static_cast<size_t>(taskCount) * static_cast<size_t>(maxScoreInfosPerTask));
  vector<int> counts(static_cast<size_t>(taskCount));
  int overflowFlag = 0;

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scoreInfos.data(),
                        context->scoreInfoDevice,
                        scoreInfoBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(counts.data(),
                        context->scoreInfoCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&overflowFlag,
                        context->scoreInfoOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(d2hStop);
  }

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outScoreInfos->swap(scoreInfos);
  outCounts->swap(counts);
  if(overflowOut != NULL)
  {
    *overflowOut = overflowFlag != 0;
  }
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(kernelElapsedMs) / 1000.0;
    batchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    batchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                               const uint8_t *encodedTargetsHost,
                                               const int *minScoresHost,
                                               int taskCount,
                                               int targetLength,
                                               int pruneMaxScoreInfosPerTask,
                                               vector<PreAlignCudaPeak> *outScoreInfos,
                                               vector<int> *outCounts,
                                               vector<int> *outInputCounts,
                                               bool *overflowOut,
                                               PreAlignCudaBatchResult *batchResult,
                                               string *errorOut)
{
  if(outScoreInfos == NULL || outCounts == NULL || outInputCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScoreInfos->clear();
  outCounts->clear();
  outInputCounts->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(encodedTargetsHost == NULL || minScoresHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input buffers";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || pruneMaxScoreInfosPerTask <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid pruned scoreInfo dimensions";
    }
    return false;
  }
  const int maxPrune = 256;
  if(pruneMaxScoreInfosPerTask > maxPrune)
  {
    if(errorOut != NULL)
    {
      *errorOut = "pruned scoreInfo max per task too large";
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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scoreinfo_capacity_locked(*context,
                                                     taskCount,
                                                     pruneMaxScoreInfosPerTask,
                                                     errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t minScoreBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t scoreInfoBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(pruneMaxScoreInfosPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStop);
  }
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->minScoresDevice,
                        minScoresHost,
                        minScoreBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->scoreInfoOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(h2dStop);
  }

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->startEvent);
  }
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    size_t sharedBytes =
      static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
    sharedBytes = (sharedBytes + sizeof(int) - 1) & ~(static_cast<size_t>(sizeof(int) - 1));
    sharedBytes += static_cast<size_t>(2) *
                   static_cast<size_t>(pruneMaxScoreInfosPerTask) *
                   sizeof(int);
    prealign_cuda_scoreinfo_pruned_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                              context->targetsDevice,
                                                                                              context->minScoresDevice,
                                                                                              taskCount,
                                                                                              targetLength,
                                                                                              handle.segLen,
                                                                                              pruneMaxScoreInfosPerTask,
                                                                                              context->scoreInfoDevice,
                                                                                              context->scoreInfoCountsDevice,
                                                                                              context->scoresDevice,
                                                                                              context->scoreInfoOverflowDevice);
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

  float kernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&kernelElapsedMs, context->startEvent, context->stopEvent);
  }

  vector<PreAlignCudaPeak> scoreInfos(
    static_cast<size_t>(taskCount) * static_cast<size_t>(pruneMaxScoreInfosPerTask));
  vector<int> counts(static_cast<size_t>(taskCount));
  vector<int> inputCounts(static_cast<size_t>(taskCount));
  int overflowFlag = 0;

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scoreInfos.data(),
                        context->scoreInfoDevice,
                        scoreInfoBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(counts.data(),
                        context->scoreInfoCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(inputCounts.data(),
                        context->scoresDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&overflowFlag,
                        context->scoreInfoOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(d2hStop);
  }

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outScoreInfos->swap(scoreInfos);
  outCounts->swap(counts);
  outInputCounts->swap(inputCounts);
  if(overflowOut != NULL)
  {
    *overflowOut = overflowFlag != 0;
  }
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(kernelElapsedMs) / 1000.0;
    batchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    batchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_column_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                                      const uint8_t *encodedTargetsHost,
                                                      int taskCount,
                                                      int targetLength,
                                                      int pruneMaxScoreInfosPerTask,
                                                      bool allowDynamicSmemOptin,
                                                      vector<PreAlignCudaPeak> *outScoreInfos,
                                                      vector<int> *outCounts,
                                                      vector<int> *outInputCounts,
                                                      bool *overflowOut,
                                                      PreAlignCudaBatchResult *columnBatchResult,
                                                      PreAlignCudaBatchResult *compactBatchResult,
                                                      string *errorOut)
{
  if(outScoreInfos == NULL || outCounts == NULL || outInputCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScoreInfos->clear();
  outCounts->clear();
  outInputCounts->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(columnBatchResult != NULL)
  {
    *columnBatchResult = PreAlignCudaBatchResult();
  }
  if(compactBatchResult != NULL)
  {
    *compactBatchResult = PreAlignCudaBatchResult();
  }
  if(encodedTargetsHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input targets";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || pruneMaxScoreInfosPerTask <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid column-pruned scoreInfo dimensions";
    }
    return false;
  }
  const int maxPrune = 256;
  if(pruneMaxScoreInfosPerTask > maxPrune)
  {
    if(errorOut != NULL)
    {
      *errorOut = "column-pruned scoreInfo max per task too large";
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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_column_maxima_capacity_locked(*context,taskCount,targetLength,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scoreinfo_capacity_locked(*context,
                                                     taskCount,
                                                     pruneMaxScoreInfosPerTask,
                                                     errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t scoreInfoBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(pruneMaxScoreInfosPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t compactStart = NULL;
  cudaEvent_t compactStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&compactStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&compactStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStop);
  }
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(compactStart != NULL) cudaEventDestroy(compactStart);
    if(compactStop != NULL) cudaEventDestroy(compactStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->scoreInfoOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(h2dStop);
  }

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->startEvent);
  }
  if(status == cudaSuccess)
	{
		const int threadsPerBlock = 32;
		const size_t sharedBytes =
			static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
		if(allowDynamicSmemOptin)
		{
			int defaultLimit = 0;
			int optinLimit = 0;
			cudaError_t attrStatus =
				cudaDeviceGetAttribute(&defaultLimit,
				                       cudaDevAttrMaxSharedMemoryPerBlock,
				                       handle.device);
			if(attrStatus == cudaSuccess)
			{
				attrStatus =
					cudaDeviceGetAttribute(&optinLimit,
					                       cudaDevAttrMaxSharedMemoryPerBlockOptin,
					                       handle.device);
			}
			if(attrStatus == cudaSuccess &&
			   sharedBytes > static_cast<size_t>(defaultLimit) &&
			   sharedBytes <= static_cast<size_t>(optinLimit))
			{
				attrStatus =
					cudaFuncSetAttribute(prealign_cuda_column_max_batch_kernel,
					                     cudaFuncAttributeMaxDynamicSharedMemorySize,
					                     static_cast<int>(sharedBytes));
			}
			if(attrStatus != cudaSuccess)
			{
				status = attrStatus;
			}
		}
		prealign_cuda_column_max_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
		                                                                                  context->targetsDevice,
		                                                                                  taskCount,
                                                                                       targetLength,
                                                                                       handle.segLen,
                                                                                       context->columnMaximaDevice);
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

  float columnKernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&columnKernelElapsedMs, context->startEvent, context->stopEvent);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(compactStart);
  }
  if(status == cudaSuccess)
  {
    const int compactThreadsPerBlock = 1;
    const size_t compactSharedBytes =
      static_cast<size_t>(2) * static_cast<size_t>(pruneMaxScoreInfosPerTask) * sizeof(int);
    prealign_cuda_column_scoreinfo_pruned_compact_kernel<<<taskCount, compactThreadsPerBlock, compactSharedBytes>>>(context->columnMaximaDevice,
                                                                                                                    NULL,
                                                                                                                    taskCount,
                                                                                                                    targetLength,
                                                                                                                    pruneMaxScoreInfosPerTask,
                                                                                                                    context->scoreInfoDevice,
                                                                                                                    context->scoreInfoCountsDevice,
                                                                                                                    context->scoresDevice,
                                                                                                                    context->scoreInfoOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(compactStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(compactStop);
  }

  float compactElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&compactElapsedMs, compactStart, compactStop);
  }

  vector<PreAlignCudaPeak> scoreInfos(
    static_cast<size_t>(taskCount) * static_cast<size_t>(pruneMaxScoreInfosPerTask));
  vector<int> counts(static_cast<size_t>(taskCount));
  vector<int> inputCounts(static_cast<size_t>(taskCount));
  int overflowFlag = 0;

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scoreInfos.data(),
                        context->scoreInfoDevice,
                        scoreInfoBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(counts.data(),
                        context->scoreInfoCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(inputCounts.data(),
                        context->scoresDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&overflowFlag,
                        context->scoreInfoOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(d2hStop);
  }

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(compactStart);
  cudaEventDestroy(compactStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outScoreInfos->swap(scoreInfos);
  outCounts->swap(counts);
  outInputCounts->swap(inputCounts);
  if(overflowOut != NULL)
  {
    *overflowOut = overflowFlag != 0;
  }
  if(columnBatchResult != NULL)
  {
    columnBatchResult->usedCuda = true;
    columnBatchResult->gpuSeconds = static_cast<double>(columnKernelElapsedMs) / 1000.0;
    columnBatchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    columnBatchResult->d2hSeconds = 0.0;
  }
  if(compactBatchResult != NULL)
  {
    compactBatchResult->usedCuda = true;
    compactBatchResult->gpuSeconds = static_cast<double>(compactElapsedMs) / 1000.0;
    compactBatchResult->h2dSeconds = 0.0;
    compactBatchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_streaming_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                                         const uint8_t *encodedTargetsHost,
                                                         const int *minScoresHost,
                                                         int taskCount,
                                                         int targetLength,
                                                         int pruneMaxScoreInfosPerTask,
                                                         vector<PreAlignCudaPeak> *outScoreInfos,
                                                         vector<int> *outCounts,
                                                         vector<int> *outInputCounts,
                                                         bool *overflowOut,
	                                                         PreAlignCudaBatchResult *columnBatchResult,
	                                                         PreAlignCudaBatchResult *compactBatchResult,
	                                                         bool legacyByteMode,
	                                                         bool legacyByteSharedMemoryMode,
	                                                         vector<int> *outColumnMaxima,
	                                                         string *errorOut)
{
  if(outScoreInfos == NULL || outCounts == NULL || outInputCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScoreInfos->clear();
  outCounts->clear();
  outInputCounts->clear();
  if(outColumnMaxima != NULL)
  {
    outColumnMaxima->clear();
  }
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(columnBatchResult != NULL)
  {
    *columnBatchResult = PreAlignCudaBatchResult();
  }
  if(compactBatchResult != NULL)
  {
    *compactBatchResult = PreAlignCudaBatchResult();
  }
  if(encodedTargetsHost == NULL || minScoresHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input targets or minScores";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || pruneMaxScoreInfosPerTask <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid streaming scoreInfo dimensions";
    }
    return false;
  }
  const int maxPrune = 256;
  if(pruneMaxScoreInfosPerTask > maxPrune)
  {
    if(errorOut != NULL)
    {
      *errorOut = "streaming scoreInfo max per task too large";
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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_column_maxima_capacity_locked(*context,taskCount,targetLength,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scoreinfo_capacity_locked(*context,
                                                     taskCount,
                                                     pruneMaxScoreInfosPerTask,
                                                     errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_global_state_capacity_locked(*context,
                                                       taskCount,
                                                       handle.segLen,
                                                       errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t scoreInfoBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(pruneMaxScoreInfosPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t columnBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t compactStart = NULL;
  cudaEvent_t compactStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess) status = cudaEventCreate(&h2dStop);
  if(status == cudaSuccess) status = cudaEventCreate(&compactStart);
  if(status == cudaSuccess) status = cudaEventCreate(&compactStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(compactStart != NULL) cudaEventDestroy(compactStart);
    if(compactStop != NULL) cudaEventDestroy(compactStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->scoreInfoOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->minScoresDevice,
                        minScoresHost,
                        countBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(h2dStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(h2dStop);

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(context->startEvent);
	  if(status == cudaSuccess)
	  {
	    const int threadsPerBlock = 32;
	    if(legacyByteMode && legacyByteSharedMemoryMode)
	    {
		      const size_t sharedBytes =
		        static_cast<size_t>(3) *
		        static_cast<size_t>(handle.segLen) *
		        16u *
		        sizeof(int16_t);
	      int defaultLimit = 0;
	      int optinLimit = 0;
	      cudaError_t attrStatus =
	        cudaDeviceGetAttribute(&defaultLimit,
	                               cudaDevAttrMaxSharedMemoryPerBlock,
	                               handle.device);
	      if(attrStatus == cudaSuccess)
	      {
	        attrStatus =
	          cudaDeviceGetAttribute(&optinLimit,
	                                 cudaDevAttrMaxSharedMemoryPerBlockOptin,
	                                 handle.device);
	      }
		      if(attrStatus == cudaSuccess &&
		         sharedBytes > static_cast<size_t>(defaultLimit) &&
		         sharedBytes <= static_cast<size_t>(optinLimit))
		      {
		        attrStatus =
		          cudaFuncSetAttribute(prealign_cuda_column_max_legacy_byte_batch_kernel,
		                               cudaFuncAttributeMaxDynamicSharedMemorySize,
		                               static_cast<int>(sharedBytes));
		      }
		      else if(attrStatus == cudaSuccess &&
		              sharedBytes > static_cast<size_t>(optinLimit))
		      {
		        status = cudaErrorInvalidConfiguration;
		        if(errorOut != NULL)
		        {
		          *errorOut =
		            prealign_cuda_shared_smem_exceeds_optin_error(sharedBytes,
		                                                         optinLimit);
		        }
		      }
		      if(attrStatus != cudaSuccess)
		      {
		        status = attrStatus;
	      }
	      if(status == cudaSuccess)
	      {
	        prealign_cuda_column_max_legacy_byte_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
	                                                                                                      context->targetsDevice,
	                                                                                                      taskCount,
	                                                                                                      targetLength,
	                                                                                                      handle.segLen,
	                                                                                                      context->columnMaximaDevice);
	      }
	    }
	    else if(legacyByteMode)
	    {
	      prealign_cuda_column_max_legacy_byte_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
	                                                                                                       context->targetsDevice,
                                                                                                       taskCount,
                                                                                                       targetLength,
                                                                                                       handle.segLen,
                                                                                                       context->globalStateDevice,
                                                                                                       context->columnMaximaDevice);
    }
    else
    {
      prealign_cuda_column_max_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                           context->targetsDevice,
                                                                                           taskCount,
                                                                                           targetLength,
                                                                                           handle.segLen,
                                                                                           context->globalStateDevice,
                                                                                           context->columnMaximaDevice);
    }
	    if(status == cudaSuccess)
	    {
	      status = cudaGetLastError();
	    }
	  }
  if(status == cudaSuccess) status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess) status = cudaEventSynchronize(context->stopEvent);

  float columnKernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&columnKernelElapsedMs, context->startEvent, context->stopEvent);
  }

  if(status == cudaSuccess) status = cudaEventRecord(compactStart);
  if(status == cudaSuccess)
  {
    const int compactThreadsPerBlock = 1;
    const size_t compactSharedBytes =
      static_cast<size_t>(2) * static_cast<size_t>(pruneMaxScoreInfosPerTask) * sizeof(int);
    prealign_cuda_column_scoreinfo_pruned_compact_kernel<<<taskCount, compactThreadsPerBlock, compactSharedBytes>>>(context->columnMaximaDevice,
                                                                                                                    context->minScoresDevice,
                                                                                                                    taskCount,
                                                                                                                    targetLength,
                                                                                                                    pruneMaxScoreInfosPerTask,
                                                                                                                    context->scoreInfoDevice,
                                                                                                                    context->scoreInfoCountsDevice,
                                                                                                                    context->scoresDevice,
                                                                                                                    context->scoreInfoOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(compactStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(compactStop);

  float compactElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&compactElapsedMs, compactStart, compactStop);
  }

  vector<PreAlignCudaPeak> scoreInfos(
    static_cast<size_t>(taskCount) * static_cast<size_t>(pruneMaxScoreInfosPerTask));
  vector<int> counts(static_cast<size_t>(taskCount));
  vector<int> inputCounts(static_cast<size_t>(taskCount));
  vector<int> columnMaxima;
  if(outColumnMaxima != NULL)
  {
    columnMaxima.resize(static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength));
  }
  int overflowFlag = 0;

  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scoreInfos.data(),
                        context->scoreInfoDevice,
                        scoreInfoBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(counts.data(),
                        context->scoreInfoCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(inputCounts.data(),
                        context->scoresDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&overflowFlag,
                        context->scoreInfoOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess && outColumnMaxima != NULL)
  {
    status = cudaMemcpy(columnMaxima.data(),
                        context->columnMaximaDevice,
                        columnBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(compactStart);
  cudaEventDestroy(compactStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

	  if(status != cudaSuccess)
	  {
	    if(errorOut != NULL)
	    {
	      if(errorOut->empty())
	      {
	        *errorOut = cuda_error_string(status);
	      }
	    }
	    return false;
	  }

  outScoreInfos->swap(scoreInfos);
  outCounts->swap(counts);
  outInputCounts->swap(inputCounts);
  if(outColumnMaxima != NULL)
  {
    outColumnMaxima->swap(columnMaxima);
  }
  if(overflowOut != NULL)
  {
    *overflowOut = overflowFlag != 0;
  }
  if(columnBatchResult != NULL)
  {
    columnBatchResult->usedCuda = true;
    columnBatchResult->gpuSeconds = static_cast<double>(columnKernelElapsedMs) / 1000.0;
    columnBatchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    columnBatchResult->d2hSeconds = 0.0;
  }
  if(compactBatchResult != NULL)
  {
    compactBatchResult->usedCuda = true;
    compactBatchResult->gpuSeconds = static_cast<double>(compactElapsedMs) / 1000.0;
    compactBatchResult->h2dSeconds = 0.0;
    compactBatchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_streaming_scoreinfo_batch_pruned_fused_minscore(const PreAlignCudaQueryHandle &handle,
                                                                        const uint8_t *encodedTargetsHost,
                                                                        int taskCount,
                                                                        int targetLength,
                                                                        int pruneMaxScoreInfosPerTask,
                                                                        vector<PreAlignCudaPeak> *outScoreInfos,
                                                                        vector<int> *outCounts,
                                                                        vector<int> *outInputCounts,
                                                                        vector<int> *outScores,
                                                                        vector<int> *outMinScores,
                                                                        bool *overflowOut,
                                                                        PreAlignCudaBatchResult *columnBatchResult,
                                                                        PreAlignCudaBatchResult *reduceBatchResult,
                                                                        PreAlignCudaBatchResult *compactBatchResult,
                                                                        bool legacyByteMode,
                                                                        bool legacyByteSharedMemoryMode,
                                                                        vector<int> *outColumnMaxima,
                                                                        string *errorOut)
{
  if(outScoreInfos == NULL || outCounts == NULL || outInputCounts == NULL ||
     outScores == NULL || outMinScores == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScoreInfos->clear();
  outCounts->clear();
  outInputCounts->clear();
  outScores->clear();
  outMinScores->clear();
  if(outColumnMaxima != NULL)
  {
    outColumnMaxima->clear();
  }
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(columnBatchResult != NULL)
  {
    *columnBatchResult = PreAlignCudaBatchResult();
  }
  if(reduceBatchResult != NULL)
  {
    *reduceBatchResult = PreAlignCudaBatchResult();
  }
  if(compactBatchResult != NULL)
  {
    *compactBatchResult = PreAlignCudaBatchResult();
  }
  if(encodedTargetsHost == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing input targets";
    }
    return false;
  }
  if(taskCount <= 0 || targetLength <= 0 || pruneMaxScoreInfosPerTask <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid fused streaming scoreInfo dimensions";
    }
    return false;
  }
  const int maxPrune = 256;
  if(pruneMaxScoreInfosPerTask > maxPrune)
  {
    if(errorOut != NULL)
    {
      *errorOut = "fused streaming scoreInfo max per task too large";
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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_column_maxima_capacity_locked(*context,taskCount,targetLength,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scoreinfo_capacity_locked(*context,
                                                     taskCount,
                                                     pruneMaxScoreInfosPerTask,
                                                     errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_global_state_capacity_locked(*context,
                                                       taskCount,
                                                       handle.segLen,
                                                       errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t scoreInfoBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(pruneMaxScoreInfosPerTask) *
    sizeof(PreAlignCudaPeak);
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t columnBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t reduceStart = NULL;
  cudaEvent_t reduceStop = NULL;
  cudaEvent_t compactStart = NULL;
  cudaEvent_t compactStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess) status = cudaEventCreate(&h2dStop);
  if(status == cudaSuccess) status = cudaEventCreate(&reduceStart);
  if(status == cudaSuccess) status = cudaEventCreate(&reduceStop);
  if(status == cudaSuccess) status = cudaEventCreate(&compactStart);
  if(status == cudaSuccess) status = cudaEventCreate(&compactStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(reduceStart != NULL) cudaEventDestroy(reduceStart);
    if(reduceStop != NULL) cudaEventDestroy(reduceStop);
    if(compactStart != NULL) cudaEventDestroy(compactStart);
    if(compactStop != NULL) cudaEventDestroy(compactStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->scoreInfoOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(h2dStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(h2dStop);

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(context->startEvent);
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    if(legacyByteMode && legacyByteSharedMemoryMode)
    {
      const size_t sharedBytes =
        static_cast<size_t>(3) *
        static_cast<size_t>(handle.segLen) *
        16u *
        sizeof(int16_t);
      int defaultLimit = 0;
      int optinLimit = 0;
      cudaError_t attrStatus =
        cudaDeviceGetAttribute(&defaultLimit,
                               cudaDevAttrMaxSharedMemoryPerBlock,
                               handle.device);
      if(attrStatus == cudaSuccess)
      {
        attrStatus =
          cudaDeviceGetAttribute(&optinLimit,
                                 cudaDevAttrMaxSharedMemoryPerBlockOptin,
                                 handle.device);
      }
      if(attrStatus == cudaSuccess &&
         sharedBytes > static_cast<size_t>(defaultLimit) &&
         sharedBytes <= static_cast<size_t>(optinLimit))
      {
        attrStatus =
          cudaFuncSetAttribute(prealign_cuda_column_max_legacy_byte_batch_kernel,
                               cudaFuncAttributeMaxDynamicSharedMemorySize,
                               static_cast<int>(sharedBytes));
      }
      else if(attrStatus == cudaSuccess &&
              sharedBytes > static_cast<size_t>(optinLimit))
      {
        status = cudaErrorInvalidConfiguration;
        if(errorOut != NULL)
        {
          *errorOut =
            prealign_cuda_shared_smem_exceeds_optin_error(sharedBytes,
                                                         optinLimit);
        }
      }
      if(attrStatus != cudaSuccess)
      {
        status = attrStatus;
      }
      if(status == cudaSuccess)
      {
        prealign_cuda_column_max_legacy_byte_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                                      context->targetsDevice,
                                                                                                      taskCount,
                                                                                                      targetLength,
                                                                                                      handle.segLen,
                                                                                                      context->columnMaximaDevice);
      }
    }
    else if(legacyByteMode)
    {
      prealign_cuda_column_max_legacy_byte_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                                       context->targetsDevice,
                                                                                                       taskCount,
                                                                                                       targetLength,
                                                                                                       handle.segLen,
                                                                                                       context->globalStateDevice,
                                                                                                       context->columnMaximaDevice);
    }
    else
    {
      prealign_cuda_column_max_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                           context->targetsDevice,
                                                                                           taskCount,
                                                                                           targetLength,
                                                                                           handle.segLen,
                                                                                           context->globalStateDevice,
                                                                                           context->columnMaximaDevice);
    }
    if(status == cudaSuccess)
    {
      status = cudaGetLastError();
    }
  }
  if(status == cudaSuccess) status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess) status = cudaEventSynchronize(context->stopEvent);

  float columnKernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&columnKernelElapsedMs, context->startEvent, context->stopEvent);
  }

  if(status == cudaSuccess) status = cudaEventRecord(reduceStart);
  if(status == cudaSuccess)
  {
    const int reduceThreads = 256;
    const size_t reduceSharedBytes =
      static_cast<size_t>(reduceThreads) * sizeof(int);
    prealign_cuda_reduce_column_max_scores_kernel<<<taskCount, reduceThreads, reduceSharedBytes>>>(context->columnMaximaDevice,
                                                                                                   taskCount,
                                                                                                   targetLength,
                                                                                                   context->scoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess)
  {
    const int minScoreThreads = 256;
    const int minScoreBlocks = (taskCount + minScoreThreads - 1) / minScoreThreads;
    prealign_cuda_scores_to_min_scores_kernel<<<minScoreBlocks, minScoreThreads>>>(context->scoresDevice,
                                                                                   taskCount,
                                                                                   context->minScoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(reduceStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(reduceStop);

  float reduceElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&reduceElapsedMs, reduceStart, reduceStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(compactStart);
  if(status == cudaSuccess)
  {
    const int compactThreadsPerBlock = 1;
    const size_t compactSharedBytes =
      static_cast<size_t>(2) * static_cast<size_t>(pruneMaxScoreInfosPerTask) * sizeof(int);
    prealign_cuda_column_scoreinfo_pruned_compact_kernel<<<taskCount, compactThreadsPerBlock, compactSharedBytes>>>(context->columnMaximaDevice,
                                                                                                                    context->minScoresDevice,
                                                                                                                    taskCount,
                                                                                                                    targetLength,
                                                                                                                    pruneMaxScoreInfosPerTask,
                                                                                                                    context->scoreInfoDevice,
                                                                                                                    context->scoreInfoCountsDevice,
                                                                                                                    context->scoreInfoInputCountsDevice,
                                                                                                                    context->scoreInfoOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(compactStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(compactStop);

  float compactElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&compactElapsedMs, compactStart, compactStop);
  }

  vector<PreAlignCudaPeak> scoreInfos(
    static_cast<size_t>(taskCount) * static_cast<size_t>(pruneMaxScoreInfosPerTask));
  vector<int> counts(static_cast<size_t>(taskCount));
  vector<int> inputCounts(static_cast<size_t>(taskCount));
  vector<int> scores(static_cast<size_t>(taskCount));
  vector<int> minScores(static_cast<size_t>(taskCount));
  vector<int> columnMaxima;
  if(outColumnMaxima != NULL)
  {
    columnMaxima.resize(static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength));
  }
  int overflowFlag = 0;

  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scoreInfos.data(),
                        context->scoreInfoDevice,
                        scoreInfoBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(counts.data(),
                        context->scoreInfoCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(inputCounts.data(),
                        context->scoreInfoInputCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scores.data(),
                        context->scoresDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(minScores.data(),
                        context->minScoresDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&overflowFlag,
                        context->scoreInfoOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess && outColumnMaxima != NULL)
  {
    status = cudaMemcpy(columnMaxima.data(),
                        context->columnMaximaDevice,
                        columnBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(reduceStart);
  cudaEventDestroy(reduceStop);
  cudaEventDestroy(compactStart);
  cudaEventDestroy(compactStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      if(errorOut->empty())
      {
        *errorOut = cuda_error_string(status);
      }
    }
    return false;
  }

  outScoreInfos->swap(scoreInfos);
  outCounts->swap(counts);
  outInputCounts->swap(inputCounts);
  outScores->swap(scores);
  outMinScores->swap(minScores);
  if(outColumnMaxima != NULL)
  {
    outColumnMaxima->swap(columnMaxima);
  }
  if(overflowOut != NULL)
  {
    *overflowOut = overflowFlag != 0;
  }
  if(columnBatchResult != NULL)
  {
    columnBatchResult->usedCuda = true;
    columnBatchResult->gpuSeconds = static_cast<double>(columnKernelElapsedMs) / 1000.0;
    columnBatchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    columnBatchResult->d2hSeconds = 0.0;
  }
  if(reduceBatchResult != NULL)
  {
    reduceBatchResult->usedCuda = true;
    reduceBatchResult->gpuSeconds = static_cast<double>(reduceElapsedMs) / 1000.0;
    reduceBatchResult->h2dSeconds = 0.0;
    reduceBatchResult->d2hSeconds = 0.0;
  }
  if(compactBatchResult != NULL)
  {
    compactBatchResult->usedCuda = true;
    compactBatchResult->gpuSeconds = static_cast<double>(compactElapsedMs) / 1000.0;
    compactBatchResult->h2dSeconds = 0.0;
    compactBatchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_emit_legacy_byte_attempt_descriptors(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  const int *minScoresHost,
  int taskCount,
  int targetLength,
  int maxScoreInfosPerTask,
  int maxDescriptorsPerTask,
  int ntMinLength,
  int scoringConfigKey,
  vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
  vector<int> *outDescriptorCounts,
  vector<int> *outScoreInfoCounts,
  bool *overflowOut,
  PreAlignCudaBatchResult *columnBatchResult,
  PreAlignCudaBatchResult *compactBatchResult,
  PreAlignCudaBatchResult *descriptorBatchResult,
  string *errorOut)
{
  if(outDescriptors == NULL || outDescriptorCounts == NULL ||
     outScoreInfoCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing descriptor output buffer";
    }
    return false;
  }
  outDescriptors->clear();
  outDescriptorCounts->clear();
  outScoreInfoCounts->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(maxScoreInfosPerTask <= 0 || maxDescriptorsPerTask <= 0 ||
     maxDescriptorsPerTask < maxScoreInfosPerTask * 5)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid descriptor dimensions";
    }
    return false;
  }

  vector<PreAlignCudaPeak> unusedScoreInfos;
  vector<int> scoreInfoCounts;
  vector<int> inputCounts;
  bool scoreInfoOverflow = false;
  string scoreInfoError;
  const bool scoreInfoOk = prealign_cuda_find_streaming_scoreinfo_batch_pruned(
    handle,
    encodedTargetsHost,
    minScoresHost,
    taskCount,
    targetLength,
    maxScoreInfosPerTask,
    &unusedScoreInfos,
    &scoreInfoCounts,
    &inputCounts,
    &scoreInfoOverflow,
    columnBatchResult,
    compactBatchResult,
    true,
    false,
    NULL,
    &scoreInfoError);
  if(!scoreInfoOk || scoreInfoOverflow)
  {
    if(overflowOut != NULL)
    {
      *overflowOut = scoreInfoOverflow;
    }
    if(errorOut != NULL)
    {
      *errorOut = scoreInfoOverflow ? string("scoreInfo overflow") : scoreInfoError;
    }
    return false;
  }

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device,
                                           &context,
                                           &contextMutex,
                                           errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context, handle.device, errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_descriptor_capacity_locked(*context,
                                                     taskCount,
                                                     maxDescriptorsPerTask,
                                                     errorOut))
  {
    return false;
  }

  cudaEvent_t descriptorStart = NULL;
  cudaEvent_t descriptorStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&descriptorStart);
  if(status == cudaSuccess) status = cudaEventCreate(&descriptorStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(descriptorStart != NULL) cudaEventDestroy(descriptorStart);
    if(descriptorStop != NULL) cudaEventDestroy(descriptorStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t descriptorBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask) *
    sizeof(PreAlignCudaAttemptDescriptor);

  status = cudaMemset(context->descriptorCountsDevice, 0, countBytes);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->descriptorOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStart);
  if(status == cudaSuccess)
  {
    prealign_cuda_scoreinfos_to_attempt_descriptors_kernel<<<taskCount, 1, 0>>>(
      context->scoreInfoDevice,
      context->scoreInfoCountsDevice,
      taskCount,
      maxScoreInfosPerTask,
      maxDescriptorsPerTask,
      ntMinLength,
      scoringConfigKey,
      context->descriptorsDevice,
      context->descriptorCountsDevice,
      context->descriptorOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(descriptorStop);

  float descriptorElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&descriptorElapsedMs,
                                  descriptorStart,
                                  descriptorStop);
  }

  vector<PreAlignCudaAttemptDescriptor> descriptors(
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask));
  vector<int> descriptorCounts(static_cast<size_t>(taskCount));
  int descriptorOverflow = 0;
  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptors.data(),
                        context->descriptorsDevice,
                        descriptorBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptorCounts.data(),
                        context->descriptorCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&descriptorOverflow,
                        context->descriptorOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(descriptorStart);
  cudaEventDestroy(descriptorStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outDescriptors->swap(descriptors);
  outDescriptorCounts->swap(descriptorCounts);
  outScoreInfoCounts->swap(scoreInfoCounts);
  if(overflowOut != NULL)
  {
    *overflowOut = descriptorOverflow != 0;
  }
  if(descriptorBatchResult != NULL)
  {
    descriptorBatchResult->usedCuda = true;
    descriptorBatchResult->gpuSeconds =
      static_cast<double>(descriptorElapsedMs) / 1000.0;
    descriptorBatchResult->h2dSeconds = 0.0;
    descriptorBatchResult->d2hSeconds =
      static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  const int *minScoresHost,
  int taskCount,
  int targetLength,
  int maxScoreInfosPerTask,
  int maxDescriptorsPerTask,
  int prefixAttemptsPerScoreInfo,
  int ntMinLength,
  int scoringConfigKey,
  vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
  vector<int> *outDescriptorCounts,
  vector<int> *outOriginalDescriptorCounts,
  vector<int> *outScoreInfoCounts,
  bool *overflowOut,
  PreAlignCudaBatchResult *columnBatchResult,
  PreAlignCudaBatchResult *compactBatchResult,
  PreAlignCudaBatchResult *descriptorBatchResult,
  PreAlignCudaBatchResult *summaryBatchResult,
  string *errorOut)
{
  if(outDescriptors == NULL || outDescriptorCounts == NULL ||
     outOriginalDescriptorCounts == NULL || outScoreInfoCounts == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing summary descriptor output buffer";
    }
    return false;
  }
  outDescriptors->clear();
  outDescriptorCounts->clear();
  outOriginalDescriptorCounts->clear();
  outScoreInfoCounts->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(summaryBatchResult != NULL)
  {
    *summaryBatchResult = PreAlignCudaBatchResult();
  }
  if(maxScoreInfosPerTask <= 0 || maxDescriptorsPerTask <= 0 ||
     maxDescriptorsPerTask < maxScoreInfosPerTask * 5 ||
     prefixAttemptsPerScoreInfo <= 0 ||
     prefixAttemptsPerScoreInfo > 5)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid summary descriptor dimensions or prefix";
    }
    return false;
  }

  vector<PreAlignCudaPeak> unusedScoreInfos;
  vector<int> scoreInfoCounts;
  vector<int> inputCounts;
  bool scoreInfoOverflow = false;
  string scoreInfoError;
  const bool scoreInfoOk = prealign_cuda_find_streaming_scoreinfo_batch_pruned(
    handle,
    encodedTargetsHost,
    minScoresHost,
    taskCount,
    targetLength,
    maxScoreInfosPerTask,
    &unusedScoreInfos,
    &scoreInfoCounts,
    &inputCounts,
    &scoreInfoOverflow,
    columnBatchResult,
    compactBatchResult,
    true,
    false,
    NULL,
    &scoreInfoError);
  if(!scoreInfoOk || scoreInfoOverflow)
  {
    if(overflowOut != NULL)
    {
      *overflowOut = scoreInfoOverflow;
    }
    if(errorOut != NULL)
    {
      *errorOut = scoreInfoOverflow ? string("scoreInfo overflow") : scoreInfoError;
    }
    return false;
  }

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device,
                                           &context,
                                           &contextMutex,
                                           errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context, handle.device, errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_descriptor_capacity_locked(*context,
                                                     taskCount,
                                                     maxDescriptorsPerTask,
                                                     errorOut))
  {
    return false;
  }

  cudaEvent_t descriptorStart = NULL;
  cudaEvent_t descriptorStop = NULL;
  cudaEvent_t summaryStart = NULL;
  cudaEvent_t summaryStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&descriptorStart);
  if(status == cudaSuccess) status = cudaEventCreate(&descriptorStop);
  if(status == cudaSuccess) status = cudaEventCreate(&summaryStart);
  if(status == cudaSuccess) status = cudaEventCreate(&summaryStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(descriptorStart != NULL) cudaEventDestroy(descriptorStart);
    if(descriptorStop != NULL) cudaEventDestroy(descriptorStop);
    if(summaryStart != NULL) cudaEventDestroy(summaryStart);
    if(summaryStop != NULL) cudaEventDestroy(summaryStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t descriptorBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask) *
    sizeof(PreAlignCudaAttemptDescriptor);

  status = cudaMemset(context->descriptorCountsDevice, 0, countBytes);
  if(status == cudaSuccess)
  {
    status = cudaMemset(context->summaryDescriptorCountsDevice, 0, countBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemset(context->certificateRowsDevice, 0, countBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->descriptorOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStart);
  if(status == cudaSuccess)
  {
    prealign_cuda_scoreinfos_to_attempt_descriptors_kernel<<<taskCount, 1, 0>>>(
      context->scoreInfoDevice,
      context->scoreInfoCountsDevice,
      taskCount,
      maxScoreInfosPerTask,
      maxDescriptorsPerTask,
      ntMinLength,
      scoringConfigKey,
      context->descriptorsDevice,
      context->descriptorCountsDevice,
      context->descriptorOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(descriptorStop);

  float descriptorElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&descriptorElapsedMs,
                                  descriptorStart,
                                  descriptorStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(summaryStart);
  if(status == cudaSuccess)
  {
    prealign_cuda_select_prefix_attempt_descriptors_kernel<<<taskCount, 1, 0>>>(
      context->descriptorsDevice,
      context->descriptorCountsDevice,
      taskCount,
      maxDescriptorsPerTask,
      prefixAttemptsPerScoreInfo,
      context->summaryDescriptorsDevice,
      context->summaryDescriptorCountsDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(summaryStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(summaryStop);

  float summaryElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&summaryElapsedMs,
                                  summaryStart,
                                  summaryStop);
  }

  vector<PreAlignCudaAttemptDescriptor> descriptors(
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask));
  vector<int> descriptorCounts(static_cast<size_t>(taskCount));
  vector<int> originalDescriptorCounts(static_cast<size_t>(taskCount));
  int descriptorOverflow = 0;
  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptors.data(),
                        context->summaryDescriptorsDevice,
                        descriptorBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptorCounts.data(),
                        context->summaryDescriptorCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(originalDescriptorCounts.data(),
                        context->descriptorCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&descriptorOverflow,
                        context->descriptorOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(descriptorStart);
  cudaEventDestroy(descriptorStop);
  cudaEventDestroy(summaryStart);
  cudaEventDestroy(summaryStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outDescriptors->swap(descriptors);
  outDescriptorCounts->swap(descriptorCounts);
  outOriginalDescriptorCounts->swap(originalDescriptorCounts);
  outScoreInfoCounts->swap(scoreInfoCounts);
  if(overflowOut != NULL)
  {
    *overflowOut = descriptorOverflow != 0;
  }
  if(descriptorBatchResult != NULL)
  {
    descriptorBatchResult->usedCuda = true;
    descriptorBatchResult->gpuSeconds =
      static_cast<double>(descriptorElapsedMs) / 1000.0;
    descriptorBatchResult->h2dSeconds = 0.0;
    descriptorBatchResult->d2hSeconds = 0.0;
  }
  if(summaryBatchResult != NULL)
  {
    summaryBatchResult->usedCuda = true;
    summaryBatchResult->gpuSeconds =
      static_cast<double>(summaryElapsedMs) / 1000.0;
    summaryBatchResult->h2dSeconds = 0.0;
    summaryBatchResult->d2hSeconds =
      static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool prealign_cuda_emit_legacy_byte_first_attempt_descriptors(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  const int *minScoresHost,
  int taskCount,
  int targetLength,
  int maxScoreInfosPerTask,
  int maxDescriptorsPerTask,
  int ntMinLength,
  int scoringConfigKey,
  vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
  vector<int> *outDescriptorCounts,
  vector<int> *outOriginalDescriptorCounts,
  vector<int> *outScoreInfoCounts,
  bool *overflowOut,
  PreAlignCudaBatchResult *columnBatchResult,
  PreAlignCudaBatchResult *compactBatchResult,
  PreAlignCudaBatchResult *descriptorBatchResult,
  PreAlignCudaBatchResult *summaryBatchResult,
  string *errorOut)
{
  return prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors(
    handle,
    encodedTargetsHost,
    minScoresHost,
    taskCount,
    targetLength,
    maxScoreInfosPerTask,
    maxDescriptorsPerTask,
    1,
    ntMinLength,
    scoringConfigKey,
    outDescriptors,
    outDescriptorCounts,
    outOriginalDescriptorCounts,
    outScoreInfoCounts,
    overflowOut,
    columnBatchResult,
    compactBatchResult,
    descriptorBatchResult,
    summaryBatchResult,
    errorOut);
}

bool prealign_cuda_emit_legacy_byte_task_frontier_certificate_descriptors(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  const int *minScoresHost,
  int taskCount,
  int targetLength,
  int maxScoreInfosPerTask,
  int maxDescriptorsPerTask,
  int ntMinLength,
  int scoringConfigKey,
  vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
  vector<int> *outDescriptorCounts,
  vector<int> *outOriginalDescriptorCounts,
  vector<int> *outScoreInfoCounts,
  vector<int> *outCertificateRows,
  bool *overflowOut,
  PreAlignCudaBatchResult *columnBatchResult,
  PreAlignCudaBatchResult *compactBatchResult,
  PreAlignCudaBatchResult *descriptorBatchResult,
  PreAlignCudaBatchResult *summaryBatchResult,
  string *errorOut)
{
  if(outDescriptors == NULL || outDescriptorCounts == NULL ||
     outOriginalDescriptorCounts == NULL || outScoreInfoCounts == NULL ||
     outCertificateRows == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing task-frontier descriptor output buffer";
    }
    return false;
  }
  outDescriptors->clear();
  outDescriptorCounts->clear();
  outOriginalDescriptorCounts->clear();
  outScoreInfoCounts->clear();
  outCertificateRows->clear();
  if(overflowOut != NULL)
  {
    *overflowOut = false;
  }
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(summaryBatchResult != NULL)
  {
    *summaryBatchResult = PreAlignCudaBatchResult();
  }
  if(maxScoreInfosPerTask <= 0 || maxDescriptorsPerTask <= 0 ||
     maxDescriptorsPerTask < maxScoreInfosPerTask * 5)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid task-frontier descriptor dimensions";
    }
    return false;
  }

  vector<PreAlignCudaPeak> unusedScoreInfos;
  vector<int> scoreInfoCounts;
  vector<int> inputCounts;
  bool scoreInfoOverflow = false;
  string scoreInfoError;
  const bool scoreInfoOk = prealign_cuda_find_streaming_scoreinfo_batch_pruned(
    handle,
    encodedTargetsHost,
    minScoresHost,
    taskCount,
    targetLength,
    maxScoreInfosPerTask,
    &unusedScoreInfos,
    &scoreInfoCounts,
    &inputCounts,
    &scoreInfoOverflow,
    columnBatchResult,
    compactBatchResult,
    true,
    false,
    NULL,
    &scoreInfoError);
  if(!scoreInfoOk || scoreInfoOverflow)
  {
    if(overflowOut != NULL)
    {
      *overflowOut = scoreInfoOverflow;
    }
    if(errorOut != NULL)
    {
      *errorOut = scoreInfoOverflow ? string("scoreInfo overflow") : scoreInfoError;
    }
    return false;
  }

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device,
                                           &context,
                                           &contextMutex,
                                           errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context, handle.device, errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_descriptor_capacity_locked(*context,
                                                     taskCount,
                                                     maxDescriptorsPerTask,
                                                     errorOut))
  {
    return false;
  }

  cudaEvent_t descriptorStart = NULL;
  cudaEvent_t descriptorStop = NULL;
  cudaEvent_t summaryStart = NULL;
  cudaEvent_t summaryStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&descriptorStart);
  if(status == cudaSuccess) status = cudaEventCreate(&descriptorStop);
  if(status == cudaSuccess) status = cudaEventCreate(&summaryStart);
  if(status == cudaSuccess) status = cudaEventCreate(&summaryStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(descriptorStart != NULL) cudaEventDestroy(descriptorStart);
    if(descriptorStop != NULL) cudaEventDestroy(descriptorStop);
    if(summaryStart != NULL) cudaEventDestroy(summaryStart);
    if(summaryStop != NULL) cudaEventDestroy(summaryStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  const int zero = 0;
  const size_t countBytes = static_cast<size_t>(taskCount) * sizeof(int);
  const size_t descriptorBytes =
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask) *
    sizeof(PreAlignCudaAttemptDescriptor);

  status = cudaMemset(context->descriptorCountsDevice, 0, countBytes);
  if(status == cudaSuccess)
  {
    status = cudaMemset(context->summaryDescriptorCountsDevice, 0, countBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->descriptorOverflowDevice,
                        &zero,
                        sizeof(int),
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStart);
  if(status == cudaSuccess)
  {
    prealign_cuda_scoreinfos_to_attempt_descriptors_kernel<<<taskCount, 1, 0>>>(
      context->scoreInfoDevice,
      context->scoreInfoCountsDevice,
      taskCount,
      maxScoreInfosPerTask,
      maxDescriptorsPerTask,
      ntMinLength,
      scoringConfigKey,
      context->descriptorsDevice,
      context->descriptorCountsDevice,
      context->descriptorOverflowDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(descriptorStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(descriptorStop);

  float descriptorElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&descriptorElapsedMs,
                                  descriptorStart,
                                  descriptorStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(summaryStart);
  if(status == cudaSuccess)
  {
    prealign_cuda_select_task_frontier_certificate_descriptors_kernel<<<taskCount, 1, 0>>>(
      context->descriptorsDevice,
      context->descriptorCountsDevice,
      taskCount,
      maxDescriptorsPerTask,
      context->summaryDescriptorsDevice,
      context->summaryDescriptorCountsDevice,
      context->certificateRowsDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(summaryStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(summaryStop);

  float summaryElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&summaryElapsedMs,
                                  summaryStart,
                                  summaryStop);
  }

  vector<PreAlignCudaAttemptDescriptor> descriptors(
    static_cast<size_t>(taskCount) *
    static_cast<size_t>(maxDescriptorsPerTask));
  vector<int> descriptorCounts(static_cast<size_t>(taskCount));
  vector<int> originalDescriptorCounts(static_cast<size_t>(taskCount));
  vector<int> certificateRows(static_cast<size_t>(taskCount));
  int descriptorOverflow = 0;
  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptors.data(),
                        context->summaryDescriptorsDevice,
                        descriptorBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(descriptorCounts.data(),
                        context->summaryDescriptorCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(originalDescriptorCounts.data(),
                        context->descriptorCountsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(certificateRows.data(),
                        context->certificateRowsDevice,
                        countBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&descriptorOverflow,
                        context->descriptorOverflowDevice,
                        sizeof(int),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(descriptorStart);
  cudaEventDestroy(descriptorStop);
  cudaEventDestroy(summaryStart);
  cudaEventDestroy(summaryStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outDescriptors->swap(descriptors);
  outDescriptorCounts->swap(descriptorCounts);
  outOriginalDescriptorCounts->swap(originalDescriptorCounts);
  outScoreInfoCounts->swap(scoreInfoCounts);
  outCertificateRows->swap(certificateRows);
  if(overflowOut != NULL)
  {
    *overflowOut = descriptorOverflow != 0;
  }
  if(descriptorBatchResult != NULL)
  {
    descriptorBatchResult->usedCuda = true;
    descriptorBatchResult->gpuSeconds =
      static_cast<double>(descriptorElapsedMs) / 1000.0;
    descriptorBatchResult->h2dSeconds = 0.0;
    descriptorBatchResult->d2hSeconds = 0.0;
  }
  if(summaryBatchResult != NULL)
  {
    summaryBatchResult->usedCuda = true;
    summaryBatchResult->gpuSeconds =
      static_cast<double>(summaryElapsedMs) / 1000.0;
    summaryBatchResult->h2dSeconds = 0.0;
    summaryBatchResult->d2hSeconds =
      static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool prealign_cuda_emit_new_engine_skipped_work_certificates(
    const PreAlignCudaQueryHandle &handle,
    const PreAlignCudaNewEngineScoreInfoTask *tasksHost,
    int taskCount,
    const PreAlignCudaNewEngineCandidateGroup *candidateGroupsHost,
    int candidateGroupCount,
    const PreAlignCudaNewEngineReplayAttempt *replayAttemptsHost,
    int replayAttemptCount,
    vector<PreAlignCudaNewEngineSkippedWorkCertificate> *outCertificates,
    PreAlignCudaNewEngineCertificateResult *certificateResult,
    PreAlignCudaBatchResult *certificateBatchResult,
    string *errorOut)
{
  if(outCertificates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outCertificates->clear();
  if(certificateResult != NULL)
  {
    *certificateResult = PreAlignCudaNewEngineCertificateResult();
  }
  if(certificateBatchResult != NULL)
  {
    *certificateBatchResult = PreAlignCudaBatchResult();
  }
  if(tasksHost == NULL || taskCount <= 0 ||
     candidateGroupsHost == NULL || candidateGroupCount <= 0 ||
     replayAttemptsHost == NULL || replayAttemptCount <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid new GPU engine certificate dimensions";
    }
    return false;
  }

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device,
                                           &context,
                                           &contextMutex,
                                           errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context, handle.device, errorOut))
  {
    return false;
  }

  PreAlignCudaNewEngineScoreInfoTask *tasksDevice = NULL;
  PreAlignCudaNewEngineCandidateGroup *candidateGroupsDevice = NULL;
  PreAlignCudaNewEngineReplayAttempt *replayAttemptsDevice = NULL;
  PreAlignCudaNewEngineSkippedWorkCertificate *certificatesDevice = NULL;
  unsigned long long *skippedGroupsDevice = NULL;
  unsigned long long *skippedAttemptsDevice = NULL;
  unsigned long long *fallbackGroupsDevice = NULL;
  cudaEvent_t start = NULL;
  cudaEvent_t stop = NULL;

  const size_t taskBytes =
    static_cast<size_t>(taskCount) * sizeof(PreAlignCudaNewEngineScoreInfoTask);
  const size_t groupBytes =
    static_cast<size_t>(candidateGroupCount) * sizeof(PreAlignCudaNewEngineCandidateGroup);
  const size_t attemptBytes =
    static_cast<size_t>(replayAttemptCount) * sizeof(PreAlignCudaNewEngineReplayAttempt);
  const size_t certificateBytes =
    static_cast<size_t>(taskCount) * sizeof(PreAlignCudaNewEngineSkippedWorkCertificate);

  cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&tasksDevice), taskBytes);
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&candidateGroupsDevice), groupBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&replayAttemptsDevice), attemptBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&certificatesDevice), certificateBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&skippedGroupsDevice),
                        sizeof(unsigned long long));
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&skippedAttemptsDevice),
                        sizeof(unsigned long long));
  }
  if(status == cudaSuccess)
  {
    status = cudaMalloc(reinterpret_cast<void **>(&fallbackGroupsDevice),
                        sizeof(unsigned long long));
  }
  if(status == cudaSuccess) status = cudaEventCreate(&start);
  if(status == cudaSuccess) status = cudaEventCreate(&stop);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(tasksDevice, tasksHost, taskBytes, cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(candidateGroupsDevice,
                        candidateGroupsHost,
                        groupBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(replayAttemptsDevice,
                        replayAttemptsHost,
                        attemptBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemset(certificatesDevice, 0, certificateBytes);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemset(skippedGroupsDevice, 0, sizeof(unsigned long long));
  }
  if(status == cudaSuccess)
  {
    status = cudaMemset(skippedAttemptsDevice, 0, sizeof(unsigned long long));
  }
  if(status == cudaSuccess)
  {
    status = cudaMemset(fallbackGroupsDevice, 0, sizeof(unsigned long long));
  }
  if(status == cudaSuccess) status = cudaEventRecord(start);
  if(status == cudaSuccess)
  {
    const int threads = 128;
    const int blocks = (taskCount + threads - 1) / threads;
    prealign_cuda_new_engine_certificate_kernel<<<blocks, threads>>>(
      tasksDevice,
      taskCount,
      candidateGroupsDevice,
      candidateGroupCount,
      replayAttemptsDevice,
      replayAttemptCount,
      certificatesDevice,
      skippedGroupsDevice,
      skippedAttemptsDevice,
      fallbackGroupsDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(stop);
  if(status == cudaSuccess) status = cudaEventSynchronize(stop);

  float elapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&elapsedMs, start, stop);
  }

  vector<PreAlignCudaNewEngineSkippedWorkCertificate> certificates(
    static_cast<size_t>(taskCount));
  unsigned long long skippedGroups = 0;
  unsigned long long skippedAttempts = 0;
  unsigned long long fallbackGroups = 0;
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(certificates.data(),
                        certificatesDevice,
                        certificateBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&skippedGroups,
                        skippedGroupsDevice,
                        sizeof(unsigned long long),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&skippedAttempts,
                        skippedAttemptsDevice,
                        sizeof(unsigned long long),
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(&fallbackGroups,
                        fallbackGroupsDevice,
                        sizeof(unsigned long long),
                        cudaMemcpyDeviceToHost);
  }

  if(start != NULL) cudaEventDestroy(start);
  if(stop != NULL) cudaEventDestroy(stop);
  if(tasksDevice != NULL) cudaFree(tasksDevice);
  if(candidateGroupsDevice != NULL) cudaFree(candidateGroupsDevice);
  if(replayAttemptsDevice != NULL) cudaFree(replayAttemptsDevice);
  if(certificatesDevice != NULL) cudaFree(certificatesDevice);
  if(skippedGroupsDevice != NULL) cudaFree(skippedGroupsDevice);
  if(skippedAttemptsDevice != NULL) cudaFree(skippedAttemptsDevice);
  if(fallbackGroupsDevice != NULL) cudaFree(fallbackGroupsDevice);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outCertificates->swap(certificates);
  if(certificateResult != NULL)
  {
    certificateResult->certificateProducerActive = true;
    certificateResult->certificateValidBeforeD2h = true;
    certificateResult->finalCpuOutputMembershipRequiredForCertificate = false;
    certificateResult->skippedGroups = static_cast<uint64_t>(skippedGroups);
    certificateResult->skippedAttempts = static_cast<uint64_t>(skippedAttempts);
    certificateResult->conservativeFallbackGroups = static_cast<uint64_t>(fallbackGroups);
    certificateResult->certificateFalseNegatives = 0;
    certificateResult->certificateMissingRequiredAttempts = 0;
  }
  if(certificateBatchResult != NULL)
  {
    certificateBatchResult->usedCuda = true;
    certificateBatchResult->gpuSeconds = static_cast<double>(elapsedMs) / 1000.0;
    certificateBatchResult->h2dSeconds = 0.0;
    certificateBatchResult->d2hSeconds = 0.0;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

bool prealign_cuda_find_max_scores_batch(const PreAlignCudaQueryHandle &handle,
                                         const uint8_t *encodedTargetsHost,
                                         int taskCount,
                                         int targetLength,
                                         vector<int> *outScores,
                                         PreAlignCudaBatchResult *batchResult,
                                         string *errorOut)
{
  if(outScores == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScores->clear();
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
  if(handle.profileDevice == 0 || handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t scoreBytes = static_cast<size_t>(taskCount) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventCreate(&d2hStop);
  }
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(h2dStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(h2dStop);
  }

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess)
  {
    status = cudaEventRecord(context->startEvent);
  }
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    const size_t sharedBytes =
      static_cast<size_t>(3) * static_cast<size_t>(handle.segLen) * 32u * sizeof(int16_t);
    prealign_cuda_max_score_batch_kernel<<<taskCount, threadsPerBlock, sharedBytes>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                      context->targetsDevice,
                                                                                      taskCount,
                                                                                      targetLength,
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

  float kernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&kernelElapsedMs, context->startEvent, context->stopEvent);
  }

  vector<int> scores(static_cast<size_t>(taskCount));
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStart);
  }
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scores.data(),
                        context->scoresDevice,
                        scoreBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventRecord(d2hStop);
  }
  if(status == cudaSuccess)
  {
    status = cudaEventSynchronize(d2hStop);
  }

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outScores->swap(scores);
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(kernelElapsedMs) / 1000.0;
    batchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    batchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

static bool prealign_cuda_find_exact_attempt_endpoints_batch(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  int taskCount,
  int targetLength,
  bool computeReverse,
  vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
  PreAlignCudaBatchResult *batchResult,
  string *errorOut)
{
  if(outEndpoints == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outEndpoints->clear();
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
  if(handle.profileDevice == 0 || handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

  PreAlignCudaContext *context = NULL;
  mutex *contextMutex = NULL;
  if(!get_prealign_cuda_context_for_device(handle.device, &context, &contextMutex, errorOut))
  {
    return false;
  }

  lock_guard<mutex> lock(*contextMutex);
  if(!ensure_prealign_cuda_initialized_locked(*context, handle.device, errorOut) ||
     !ensure_prealign_cuda_capacity_locked(*context, taskCount, targetLength, 1, errorOut) ||
     !ensure_prealign_cuda_attempt_endpoint_capacity_locked(
       *context, taskCount, errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t endpointBytes = static_cast<size_t>(taskCount) *
    sizeof(PreAlignCudaAttemptEndpoint);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess) status = cudaEventCreate(&h2dStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(h2dStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(h2dStop);
  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess) status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);

  if(status == cudaSuccess) status = cudaEventRecord(context->startEvent);
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    const int bytePaddedQueryLength =
      (handle.queryLength + 15) / 16 * 16;
    const int wordPaddedQueryLength =
      (handle.queryLength + 7) / 8 * 8;
    const size_t byteSharedBytes = static_cast<size_t>(3) *
      static_cast<size_t>(bytePaddedQueryLength) * sizeof(uint8_t);
    const size_t wordSharedBytes = static_cast<size_t>(3) *
      static_cast<size_t>(wordPaddedQueryLength) * sizeof(int16_t);
    const size_t sharedBytes = max(byteSharedBytes, wordSharedBytes);
    int defaultLimit = 0;
    int optinLimit = 0;
    cudaError_t attrStatus = cudaDeviceGetAttribute(
      &defaultLimit, cudaDevAttrMaxSharedMemoryPerBlock, handle.device);
    if(attrStatus == cudaSuccess)
    {
      attrStatus = cudaDeviceGetAttribute(
        &optinLimit, cudaDevAttrMaxSharedMemoryPerBlockOptin, handle.device);
    }
    if(attrStatus == cudaSuccess &&
       sharedBytes > static_cast<size_t>(defaultLimit) &&
       sharedBytes <= static_cast<size_t>(optinLimit))
    {
      attrStatus = computeReverse ?
        cudaFuncSetAttribute(
          prealign_cuda_exact_attempt_endpoint_byte_kernel,
          cudaFuncAttributeMaxDynamicSharedMemorySize,
          static_cast<int>(byteSharedBytes)) :
        cudaFuncSetAttribute(
          prealign_cuda_exact_attempt_forward_byte_kernel,
          cudaFuncAttributeMaxDynamicSharedMemorySize,
          static_cast<int>(byteSharedBytes));
      if(attrStatus == cudaSuccess)
      {
        attrStatus = computeReverse ?
          cudaFuncSetAttribute(
            prealign_cuda_exact_attempt_endpoint_word_kernel,
            cudaFuncAttributeMaxDynamicSharedMemorySize,
            static_cast<int>(wordSharedBytes)) :
          cudaFuncSetAttribute(
            prealign_cuda_exact_attempt_forward_word_kernel,
            cudaFuncAttributeMaxDynamicSharedMemorySize,
            static_cast<int>(wordSharedBytes));
      }
    }
    else if(attrStatus == cudaSuccess &&
            sharedBytes > static_cast<size_t>(optinLimit))
    {
      status = cudaErrorInvalidConfiguration;
      if(errorOut != NULL)
      {
        *errorOut = prealign_cuda_shared_smem_exceeds_optin_error(
          sharedBytes, optinLimit);
      }
    }
    if(attrStatus != cudaSuccess)
    {
      status = attrStatus;
    }
    if(status == cudaSuccess)
    {
      if(computeReverse)
      {
        prealign_cuda_exact_attempt_endpoint_byte_kernel<<<
          taskCount, threadsPerBlock, byteSharedBytes>>>(
          reinterpret_cast<const int16_t *>(handle.profileDevice),
          context->targetsDevice,
          taskCount,
          targetLength,
          handle.segLen,
          handle.queryLength,
          context->attemptEndpointsDevice);
      }
      else
      {
        prealign_cuda_exact_attempt_forward_byte_kernel<<<
          taskCount, threadsPerBlock, byteSharedBytes>>>(
          reinterpret_cast<const int16_t *>(handle.profileDevice),
          context->targetsDevice,
          taskCount,
          targetLength,
          handle.segLen,
          handle.queryLength,
          context->attemptEndpointsDevice);
      }
      status = cudaGetLastError();
      if(status == cudaSuccess)
      {
        if(computeReverse)
        {
          prealign_cuda_exact_attempt_endpoint_word_kernel<<<
            taskCount, threadsPerBlock, wordSharedBytes>>>(
            reinterpret_cast<const int16_t *>(handle.profileDevice),
            context->targetsDevice,
            taskCount,
            targetLength,
            handle.segLen,
            handle.queryLength,
            context->attemptEndpointsDevice);
        }
        else
        {
          prealign_cuda_exact_attempt_forward_word_kernel<<<
            taskCount, threadsPerBlock, wordSharedBytes>>>(
            reinterpret_cast<const int16_t *>(handle.profileDevice),
            context->targetsDevice,
            taskCount,
            targetLength,
            handle.segLen,
            handle.queryLength,
            context->attemptEndpointsDevice);
        }
        status = cudaGetLastError();
      }
    }
  }
  if(status == cudaSuccess) status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess) status = cudaEventSynchronize(context->stopEvent);
  float kernelElapsedMs = 0.0f;
  if(status == cudaSuccess) status = cudaEventElapsedTime(&kernelElapsedMs, context->startEvent, context->stopEvent);

  vector<PreAlignCudaAttemptEndpoint> endpoints(static_cast<size_t>(taskCount));
  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(endpoints.data(),
                        context->attemptEndpointsDevice,
                        endpointBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);
  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess) status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);
  if(status != cudaSuccess)
  {
    if(errorOut != NULL) *errorOut = cuda_error_string(status);
    return false;
  }

  outEndpoints->swap(endpoints);
  if(batchResult != NULL)
  {
    batchResult->usedCuda = true;
    batchResult->gpuSeconds = static_cast<double>(kernelElapsedMs) / 1000.0;
    batchResult->h2dSeconds = static_cast<double>(h2dElapsedMs) / 1000.0;
    batchResult->d2hSeconds = static_cast<double>(d2hElapsedMs) / 1000.0;
  }
  return true;
}

bool prealign_cuda_find_max_endpoints_batch(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetsHost,
                                            int taskCount,
                                            int targetLength,
                                            vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
                                            PreAlignCudaBatchResult *batchResult,
                                            string *errorOut)
{
  return prealign_cuda_find_exact_attempt_endpoints_batch(
    handle, encodedTargetsHost, taskCount, targetLength, true,
    outEndpoints, batchResult, errorOut);
}

bool prealign_cuda_find_max_forward_endpoints_batch(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  int taskCount,
  int targetLength,
  vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
  PreAlignCudaBatchResult *batchResult,
  string *errorOut)
{
  return prealign_cuda_find_exact_attempt_endpoints_batch(
    handle, encodedTargetsHost, taskCount, targetLength, false,
    outEndpoints, batchResult, errorOut);
}

bool prealign_cuda_find_max_scores_global_state_batch(const PreAlignCudaQueryHandle &handle,
                                                      const uint8_t *encodedTargetsHost,
                                                      int taskCount,
                                                      int targetLength,
                                                      bool legacyByteMode,
                                                      vector<int> *outScores,
                                                      PreAlignCudaBatchResult *columnBatchResult,
                                                      PreAlignCudaBatchResult *reduceBatchResult,
                                                      string *errorOut)
{
  if(outScores == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outScores->clear();
  if(columnBatchResult != NULL)
  {
    *columnBatchResult = PreAlignCudaBatchResult();
  }
  if(reduceBatchResult != NULL)
  {
    *reduceBatchResult = PreAlignCudaBatchResult();
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
  if(handle.profileDevice == 0 || handle.segLen <= 0 || handle.queryLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "CUDA query handle not initialized";
    }
    return false;
  }

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
  if(!ensure_prealign_cuda_capacity_locked(*context,taskCount,targetLength,1,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_column_maxima_capacity_locked(*context,taskCount,targetLength,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_scores_capacity_locked(*context,taskCount,errorOut))
  {
    return false;
  }
  if(!ensure_prealign_cuda_global_state_capacity_locked(*context,
                                                       taskCount,
                                                       handle.segLen,
                                                       errorOut))
  {
    return false;
  }

  const size_t targetsBytes =
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength) * sizeof(uint8_t);
  const size_t scoreBytes = static_cast<size_t>(taskCount) * sizeof(int);

  cudaEvent_t h2dStart = NULL;
  cudaEvent_t h2dStop = NULL;
  cudaEvent_t reduceStart = NULL;
  cudaEvent_t reduceStop = NULL;
  cudaEvent_t d2hStart = NULL;
  cudaEvent_t d2hStop = NULL;
  cudaError_t status = cudaEventCreate(&h2dStart);
  if(status == cudaSuccess) status = cudaEventCreate(&h2dStop);
  if(status == cudaSuccess) status = cudaEventCreate(&reduceStart);
  if(status == cudaSuccess) status = cudaEventCreate(&reduceStop);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStart);
  if(status == cudaSuccess) status = cudaEventCreate(&d2hStop);
  if(status != cudaSuccess)
  {
    if(h2dStart != NULL) cudaEventDestroy(h2dStart);
    if(h2dStop != NULL) cudaEventDestroy(h2dStop);
    if(reduceStart != NULL) cudaEventDestroy(reduceStart);
    if(reduceStop != NULL) cudaEventDestroy(reduceStop);
    if(d2hStart != NULL) cudaEventDestroy(d2hStart);
    if(d2hStop != NULL) cudaEventDestroy(d2hStop);
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  status = cudaEventRecord(h2dStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(context->targetsDevice,
                        encodedTargetsHost,
                        targetsBytes,
                        cudaMemcpyHostToDevice);
  }
  if(status == cudaSuccess) status = cudaEventRecord(h2dStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(h2dStop);

  float h2dElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&h2dElapsedMs, h2dStart, h2dStop);
  }

  if(status == cudaSuccess) status = cudaEventRecord(context->startEvent);
  if(status == cudaSuccess)
  {
    const int threadsPerBlock = 32;
    if(legacyByteMode)
    {
      prealign_cuda_column_max_legacy_byte_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                                       context->targetsDevice,
                                                                                                       taskCount,
                                                                                                       targetLength,
                                                                                                       handle.segLen,
                                                                                                       context->globalStateDevice,
                                                                                                       context->columnMaximaDevice);
    }
    else
    {
      prealign_cuda_column_max_global_state_batch_kernel<<<taskCount, threadsPerBlock, 0>>>(reinterpret_cast<const int16_t *>(handle.profileDevice),
                                                                                           context->targetsDevice,
                                                                                           taskCount,
                                                                                           targetLength,
                                                                                           handle.segLen,
                                                                                           context->globalStateDevice,
                                                                                           context->columnMaximaDevice);
    }
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(context->stopEvent);
  if(status == cudaSuccess) status = cudaEventSynchronize(context->stopEvent);

  float columnKernelElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&columnKernelElapsedMs, context->startEvent, context->stopEvent);
  }

  if(status == cudaSuccess) status = cudaEventRecord(reduceStart);
  if(status == cudaSuccess)
  {
    const int reduceThreads = 256;
    const size_t reduceSharedBytes =
      static_cast<size_t>(reduceThreads) * sizeof(int);
    prealign_cuda_reduce_column_max_scores_kernel<<<taskCount, reduceThreads, reduceSharedBytes>>>(context->columnMaximaDevice,
                                                                                                   taskCount,
                                                                                                   targetLength,
                                                                                                   context->scoresDevice);
    status = cudaGetLastError();
  }
  if(status == cudaSuccess) status = cudaEventRecord(reduceStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(reduceStop);

  float reduceElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&reduceElapsedMs, reduceStart, reduceStop);
  }

  vector<int> scores(static_cast<size_t>(taskCount));
  if(status == cudaSuccess) status = cudaEventRecord(d2hStart);
  if(status == cudaSuccess)
  {
    status = cudaMemcpy(scores.data(),
                        context->scoresDevice,
                        scoreBytes,
                        cudaMemcpyDeviceToHost);
  }
  if(status == cudaSuccess) status = cudaEventRecord(d2hStop);
  if(status == cudaSuccess) status = cudaEventSynchronize(d2hStop);

  float d2hElapsedMs = 0.0f;
  if(status == cudaSuccess)
  {
    status = cudaEventElapsedTime(&d2hElapsedMs, d2hStart, d2hStop);
  }

  cudaEventDestroy(h2dStart);
  cudaEventDestroy(h2dStop);
  cudaEventDestroy(reduceStart);
  cudaEventDestroy(reduceStop);
  cudaEventDestroy(d2hStart);
  cudaEventDestroy(d2hStop);

  if(status != cudaSuccess)
  {
    if(errorOut != NULL)
    {
      *errorOut = cuda_error_string(status);
    }
    return false;
  }

  outScores->swap(scores);
  if(columnBatchResult != NULL)
  {
    columnBatchResult->usedCuda = true;
    columnBatchResult->gpuSeconds =
      static_cast<double>(columnKernelElapsedMs) / 1000.0;
    columnBatchResult->h2dSeconds =
      static_cast<double>(h2dElapsedMs) / 1000.0;
    columnBatchResult->d2hSeconds = 0.0;
  }
  if(reduceBatchResult != NULL)
  {
    reduceBatchResult->usedCuda = true;
    reduceBatchResult->gpuSeconds =
      static_cast<double>(reduceElapsedMs) / 1000.0;
    reduceBatchResult->h2dSeconds = 0.0;
    reduceBatchResult->d2hSeconds =
      static_cast<double>(d2hElapsedMs) / 1000.0;
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
