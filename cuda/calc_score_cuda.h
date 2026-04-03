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
  CalcScoreCudaBatchResult():gpuSeconds(0.0),usedCuda(false) {}

  double gpuSeconds;
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
                                             std::string *errorOut);

#endif
