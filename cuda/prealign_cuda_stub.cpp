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

bool prealign_cuda_query_resource_limits(const PreAlignCudaQueryHandle &handle,
                                         PreAlignCudaResourceLimits *limitsOut,
                                         string *errorOut)
{
  (void)handle;
  if(limitsOut != NULL)
  {
    *limitsOut = PreAlignCudaResourceLimits();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
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

bool prealign_cuda_find_column_maxima_batch(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetsHost,
                                            int taskCount,
                                            int targetLength,
                                            vector<int> *outColumnMaxima,
                                            PreAlignCudaBatchResult *batchResult,
                                            string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)maxScoreInfosPerTask;
  if(outScoreInfos != NULL)
  {
    outScoreInfos->clear();
  }
  if(outCounts != NULL)
  {
    outCounts->clear();
  }
  if(overflowOut != NULL)
  {
    *overflowOut = false;
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)pruneMaxScoreInfosPerTask;
  if(outScoreInfos != NULL)
  {
    outScoreInfos->clear();
  }
  if(outCounts != NULL)
  {
    outCounts->clear();
  }
  if(outInputCounts != NULL)
  {
    outInputCounts->clear();
  }
  if(overflowOut != NULL)
  {
    *overflowOut = false;
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  (void)pruneMaxScoreInfosPerTask;
  (void)allowDynamicSmemOptin;
  if(outScoreInfos != NULL)
  {
    outScoreInfos->clear();
  }
  if(outCounts != NULL)
  {
    outCounts->clear();
  }
  if(outInputCounts != NULL)
  {
    outInputCounts->clear();
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
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
	  (void)pruneMaxScoreInfosPerTask;
	  (void)legacyByteMode;
	  (void)legacyByteSharedMemoryMode;
  if(outScoreInfos != NULL)
  {
    outScoreInfos->clear();
  }
  if(outCounts != NULL)
  {
    outCounts->clear();
  }
  if(outInputCounts != NULL)
  {
    outInputCounts->clear();
  }
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
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  (void)pruneMaxScoreInfosPerTask;
  (void)legacyByteMode;
  (void)legacyByteSharedMemoryMode;
  if(outScoreInfos != NULL)
  {
    outScoreInfos->clear();
  }
  if(outCounts != NULL)
  {
    outCounts->clear();
  }
  if(outInputCounts != NULL)
  {
    outInputCounts->clear();
  }
  if(outScores != NULL)
  {
    outScores->clear();
  }
  if(outMinScores != NULL)
  {
    outMinScores->clear();
  }
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
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool prealign_cuda_find_max_scores_batch(const PreAlignCudaQueryHandle &handle,
                                         const uint8_t *encodedTargetsHost,
                                         int taskCount,
                                         int targetLength,
                                         vector<int> *outScores,
                                         PreAlignCudaBatchResult *batchResult,
                                         string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  if(outScores != NULL)
  {
    outScores->clear();
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
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  (void)legacyByteMode;
  if(outScores != NULL)
  {
    outScores->clear();
  }
  if(columnBatchResult != NULL)
  {
    *columnBatchResult = PreAlignCudaBatchResult();
  }
  if(reduceBatchResult != NULL)
  {
    *reduceBatchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}
