#ifndef LONGTARGET_PREALIGN_CUDA_H
#define LONGTARGET_PREALIGN_CUDA_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

struct PreAlignCudaQueryHandle
{
  PreAlignCudaQueryHandle():device(-1),queryLength(0),segLen(0),alphabetSize(0),profileDevice(0) {}

  int device;
  int queryLength;
  int segLen;
  int alphabetSize;

  uintptr_t profileDevice;
};

struct PreAlignCudaPeak
{
  int score;
  int position;
};

struct PreAlignCudaBatchResult
{
  PreAlignCudaBatchResult():
    gpuSeconds(0.0),
    h2dSeconds(0.0),
    kernelSeconds(0.0),
    d2hSeconds(0.0),
    totalSeconds(0.0),
    usedCuda(false) {}

  double gpuSeconds;
  double h2dSeconds;
  double kernelSeconds;
  double d2hSeconds;
  double totalSeconds;
  bool usedCuda;
};

struct PreAlignCudaForwardScoreEndResult
{
  PreAlignCudaForwardScoreEndResult():score(0),refEnd(-1),readEnd(-1) {}

  int score;
  int refEnd;
  int readEnd;
};

bool prealign_cuda_is_built();
bool prealign_cuda_init(int device,std::string *errorOut);

bool prealign_cuda_prepare_query(PreAlignCudaQueryHandle *handle,
                                 const int16_t *profileHost,
                                 int alphabetSize,
                                 int segLen,
                                 int queryLength,
                                 std::string *errorOut);

void prealign_cuda_release_query(PreAlignCudaQueryHandle *handle);

bool prealign_cuda_find_topk_column_maxima(const PreAlignCudaQueryHandle &handle,
                                           const uint8_t *encodedTargetsHost,
                                           int taskCount,
                                           int targetLength,
                                           int topK,
                                           std::vector<PreAlignCudaPeak> *outPeaks,
                                           PreAlignCudaBatchResult *batchResult,
                                           std::string *errorOut);

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
                                     std::string *errorOut);

#endif
