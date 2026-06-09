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
    capacityColumnMaxTasks(0),
    capacityColumnMaxTargetLength(0),
    capacityScoreTasks(0),
    capacityScoreInfoTasks(0),
    capacityScoreInfoMaxPerTask(0),
    capacityGlobalStateTasks(0),
    capacityGlobalStateSegLen(0),
    targetsDevice(NULL),
    peaksDevice(NULL),
    columnMaximaDevice(NULL),
    scoresDevice(NULL),
    minScoresDevice(NULL),
    scoreInfoDevice(NULL),
    scoreInfoCountsDevice(NULL),
    scoreInfoInputCountsDevice(NULL),
    scoreInfoOverflowDevice(NULL),
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
  int capacityScoreInfoTasks;
  int capacityScoreInfoMaxPerTask;
  int capacityGlobalStateTasks;
  int capacityGlobalStateSegLen;

  uint8_t *targetsDevice;
  PreAlignCudaPeak *peaksDevice;
  int *columnMaximaDevice;
  int *scoresDevice;
  int *minScoresDevice;
  PreAlignCudaPeak *scoreInfoDevice;
  int *scoreInfoCountsDevice;
  int *scoreInfoInputCountsDevice;
  int *scoreInfoOverflowDevice;
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
      *errorOut = cuda_error_string(status);
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
      *errorOut = cuda_error_string(status);
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
