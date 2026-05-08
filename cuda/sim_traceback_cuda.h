#ifndef LONGTARGET_SIM_TRACEBACK_CUDA_H
#define LONGTARGET_SIM_TRACEBACK_CUDA_H

#include <cstdint>
#include <string>
#include <vector>

struct SimTracebackCudaResult
{
  SimTracebackCudaResult():gpuSeconds(0.0),usedCuda(false),hadTie(false) {}

  double gpuSeconds;
  bool usedCuda;
  bool hadTie;
};

struct SimTracebackCudaBatchRequest
{
  SimTracebackCudaBatchRequest():
    A(NULL),
    B(NULL),
    queryLength(0),
    targetLength(0),
    matchScore(0),
    mismatchScore(0),
    gapOpen(0),
    gapExtend(0),
    globalColStart(0),
    blockedWords(NULL),
    blockedWordStart(0),
    blockedWordCount(0),
    blockedWordStride(0)
  {
  }

  const char *A;
  const char *B;
  int queryLength;
  int targetLength;
  int matchScore;
  int mismatchScore;
  int gapOpen;
  int gapExtend;
  int globalColStart;
  const uint64_t *blockedWords;
  int blockedWordStart;
  int blockedWordCount;
  int blockedWordStride;
};

struct SimTracebackCudaBatchItemResult
{
  SimTracebackCudaBatchItemResult():success(false),opsReversed(),tracebackResult(),error() {}

  bool success;
  std::vector<unsigned char> opsReversed;
  SimTracebackCudaResult tracebackResult;
  std::string error;
};

struct SimTracebackCudaBatchResult
{
  SimTracebackCudaBatchResult():
    gpuSeconds(0.0),
    usedCuda(false),
    requestCount(0),
    successCount(0),
    cudaCount(0),
    singleCudaRequestBatchSkips(0),
    bulkOpsD2HCopies(0),
    perRequestOpsD2HCopies(0),
    bulkInputH2DCopies(0),
    perRequestInputH2DCopies(0)
  {
  }

  double gpuSeconds;
  bool usedCuda;
  uint64_t requestCount;
  uint64_t successCount;
  uint64_t cudaCount;
  uint64_t singleCudaRequestBatchSkips;
  uint64_t bulkOpsD2HCopies;
  uint64_t perRequestOpsD2HCopies;
  uint64_t bulkInputH2DCopies;
  uint64_t perRequestInputH2DCopies;
};

bool sim_traceback_cuda_is_built();
bool sim_traceback_cuda_init(int device,std::string *errorOut);

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
                                                std::vector<unsigned char> *outOpsReversed,
                                                SimTracebackCudaResult *result,
                                                std::string *errorOut);

bool sim_traceback_cuda_traceback_global_affine_batch(const std::vector<SimTracebackCudaBatchRequest> &requests,
                                                      std::vector<SimTracebackCudaBatchItemResult> *outResults,
                                                      SimTracebackCudaBatchResult *batchResult,
                                                      std::string *errorOut);

#endif
