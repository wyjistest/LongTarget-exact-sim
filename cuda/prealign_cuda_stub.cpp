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
                                     string *errorOut)
{
  (void)device;
  (void)queryHost;
  (void)queryLength;
  (void)refHost;
  (void)refLength;
  (void)scoreMatrixHost;
  (void)scoreMatrixSize;
  (void)gapOpen;
  (void)gapExtend;
  if(outResult != NULL)
  {
    *outResult = PreAlignCudaForwardScoreEndResult();
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

bool prealign_cuda_forward_score_end_batch(int device,
                                           const int8_t *queriesHost,
                                           const int *queryOffsetsHost,
                                           const int *queryLengthsHost,
                                           const int8_t *refsHost,
                                           const int *refOffsetsHost,
                                           const int *refLengthsHost,
                                           int requestCount,
                                           const int8_t *scoreMatrixHost,
                                           int scoreMatrixSize,
                                           uint8_t gapOpen,
                                           uint8_t gapExtend,
                                           vector<PreAlignCudaForwardScoreEndResult> *outResults,
                                           PreAlignCudaBatchResult *batchResult,
                                           string *errorOut)
{
  (void)device;
  (void)queriesHost;
  (void)queryOffsetsHost;
  (void)queryLengthsHost;
  (void)refsHost;
  (void)refOffsetsHost;
  (void)refLengthsHost;
  (void)requestCount;
  (void)scoreMatrixHost;
  (void)scoreMatrixSize;
  (void)gapOpen;
  (void)gapExtend;
  if(outResults != NULL)
  {
    outResults->clear();
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
