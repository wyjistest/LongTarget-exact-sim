#include "sim_traceback_cuda.h"

using namespace std;

bool sim_traceback_cuda_is_built()
{
  return false;
}

bool sim_traceback_cuda_init(int device,string *errorOut)
{
  (void)device;
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
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
  (void)A;
  (void)B;
  (void)queryLength;
  (void)targetLength;
  (void)matchScore;
  (void)mismatchScore;
  (void)gapOpen;
  (void)gapExtend;
  (void)globalColStart;
  (void)blockedWords;
  (void)blockedWordStart;
  (void)blockedWordCount;
  (void)blockedWordStride;
  if(outOpsReversed != NULL)
  {
    outOpsReversed->clear();
  }
  if(result != NULL)
  {
    *result = SimTracebackCudaResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
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

  outResults->resize(requests.size());
  for(size_t i = 0; i < requests.size(); ++i)
  {
    SimTracebackCudaBatchItemResult &item = (*outResults)[i];
    item = SimTracebackCudaBatchItemResult();
    item.error = "CUDA support not built";
  }
  return true;
}
