#include "prealign_cuda.h"

using namespace std;

bool prealign_cuda_is_built()
{
  return false;
}

bool prealign_cuda_init(int device,string *errorOut)
{
  (void)device;
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool prealign_cuda_prepare_query(PreAlignCudaQueryHandle *handle,
                                 const int16_t *profileHost,
                                 int alphabetSize,
                                 int segLen,
                                 int queryLength,
                                 string *errorOut)
{
  (void)profileHost;
  (void)alphabetSize;
  (void)segLen;
  (void)queryLength;
  if(handle != NULL)
  {
    *handle = PreAlignCudaQueryHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

void prealign_cuda_release_query(PreAlignCudaQueryHandle *handle)
{
  if(handle != NULL)
  {
    *handle = PreAlignCudaQueryHandle();
  }
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  (void)topK;
  if(outPeaks != NULL)
  {
    outPeaks->clear();
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool prealign_cuda_find_column_maxima_debug(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetHost,
                                            int targetLength,
                                            vector<int> *outColumnMaxima,
                                            PreAlignCudaBatchResult *batchResult,
                                            string *errorOut)
{
  (void)handle;
  (void)encodedTargetHost;
  (void)targetLength;
  if(outColumnMaxima != NULL)
  {
    outColumnMaxima->clear();
  }
  if(batchResult != NULL)
  {
    *batchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}
