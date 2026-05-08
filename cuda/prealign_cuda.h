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
    usedCuda(false),
    requestedTopK(0),
    effectiveTopK(0),
    topKClampedCount(0) {}

  double gpuSeconds;
  bool usedCuda;
  int requestedTopK;
  int effectiveTopK;
  uint64_t topKClampedCount;
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

#endif
