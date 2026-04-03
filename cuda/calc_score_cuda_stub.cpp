#include "calc_score_cuda.h"

using namespace std;

bool calc_score_cuda_is_built()
{
  return false;
}

bool calc_score_cuda_init(int device,string *errorOut)
{
  (void)device;
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool calc_score_cuda_prepare_query(CalcScoreCudaQueryHandle *handle,
                                   const int16_t *profileFwdHost,
                                   const int16_t *profileRevHost,
                                   int segLen,
                                   int queryLength,
                                   string *errorOut)
{
  (void)profileFwdHost;
  (void)profileRevHost;
  (void)segLen;
  (void)queryLength;
  if(handle != NULL)
  {
    *handle = CalcScoreCudaQueryHandle();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

void calc_score_cuda_release_query(CalcScoreCudaQueryHandle *handle)
{
  if(handle != NULL)
  {
    *handle = CalcScoreCudaQueryHandle();
  }
}

bool calc_score_cuda_compute_pair_max_scores(const CalcScoreCudaQueryHandle &handle,
                                             const uint8_t *encodedTargetsHost,
                                             int taskCount,
                                             int targetLength,
                                             const uint16_t *permutationsHost,
                                             int permutationCount,
                                             int pairCount,
                                             vector<int> *outPairScores,
                                             CalcScoreCudaBatchResult *batchResult,
                                             string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  (void)permutationsHost;
  (void)permutationCount;
  (void)pairCount;
  if(outPairScores != NULL)
  {
    outPairScores->clear();
  }
  if(batchResult != NULL)
  {
    *batchResult = CalcScoreCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

