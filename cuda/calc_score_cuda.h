#ifndef LONGTARGET_CALC_SCORE_CUDA_H
#define LONGTARGET_CALC_SCORE_CUDA_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

struct CalcScoreCudaQueryHandle
{
  CalcScoreCudaQueryHandle():device(-1),queryLength(0),segLen(0),profileFwdDevice(0),profileRevDevice(0) {}

  int device;
  int queryLength;
  int segLen;

  uintptr_t profileFwdDevice;
  uintptr_t profileRevDevice;
};

struct CalcScoreCudaBatchResult
{
  CalcScoreCudaBatchResult():
    gpuSeconds(0.0),
    targetH2DSeconds(0.0),
    permutationH2DSeconds(0.0),
    kernelSeconds(0.0),
    scoreD2HSeconds(0.0),
    syncWaitSeconds(0.0),
    pipelineV2Enabled(false),
    pipelineV2ShadowEnabled(false),
    pipelineV2Used(false),
    pipelineV2Fallback(false),
    pipelineV2ShadowComparisons(0),
    pipelineV2ShadowMismatches(0),
    pipelineV2KernelSeconds(0.0),
    pipelineV2ScoreD2HSeconds(0.0),
    pipelineV2HostReduceSeconds(0.0),
    targetBytesH2D(0),
    permutationBytesH2D(0),
    scoreBytesD2H(0),
    usedCuda(false) {}

  double gpuSeconds;
  double targetH2DSeconds;
  double permutationH2DSeconds;
  double kernelSeconds;
  double scoreD2HSeconds;
  double syncWaitSeconds;
  bool pipelineV2Enabled;
  bool pipelineV2ShadowEnabled;
  bool pipelineV2Used;
  bool pipelineV2Fallback;
  uint64_t pipelineV2ShadowComparisons;
  uint64_t pipelineV2ShadowMismatches;
  double pipelineV2KernelSeconds;
  double pipelineV2ScoreD2HSeconds;
  double pipelineV2HostReduceSeconds;
  uint64_t targetBytesH2D;
  uint64_t permutationBytesH2D;
  uint64_t scoreBytesD2H;
  bool usedCuda;
};

bool calc_score_cuda_is_built();
bool calc_score_cuda_init(int device,std::string *errorOut);
bool calc_score_cuda_prepare_query(CalcScoreCudaQueryHandle *handle,
                                   const int16_t *profileFwdHost,
                                   const int16_t *profileRevHost,
                                   int segLen,
                                   int queryLength,
                                   std::string *errorOut);
void calc_score_cuda_release_query(CalcScoreCudaQueryHandle *handle);

bool calc_score_cuda_compute_pair_max_scores(const CalcScoreCudaQueryHandle &handle,
                                             const uint8_t *encodedTargetsHost,
                                             int taskCount,
                                             int targetLength,
                                             const uint16_t *permutationsHost,
                                             int permutationCount,
                                             int pairCount,
                                             std::vector<int> *outPairScores,
                                             CalcScoreCudaBatchResult *batchResult,
                                             std::string *errorOut,
                                             bool collectTelemetry = false);

#endif
