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
  PreAlignCudaBatchResult():gpuSeconds(0.0),h2dSeconds(0.0),d2hSeconds(0.0),usedCuda(false) {}

  double gpuSeconds;
  double h2dSeconds;
  double d2hSeconds;
  bool usedCuda;
};

struct PreAlignCudaResourceLimits
{
  PreAlignCudaResourceLimits():
    requiredDynamicSmemBytes(0),
    defaultDynamicSmemLimitBytes(0),
    optinDynamicSmemLimitBytes(0),
    resourceFit(false) {}

  size_t requiredDynamicSmemBytes;
  size_t defaultDynamicSmemLimitBytes;
  size_t optinDynamicSmemLimitBytes;
  bool resourceFit;
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

bool prealign_cuda_query_resource_limits(const PreAlignCudaQueryHandle &handle,
                                         PreAlignCudaResourceLimits *limitsOut,
                                         std::string *errorOut);

bool prealign_cuda_find_topk_column_maxima(const PreAlignCudaQueryHandle &handle,
                                           const uint8_t *encodedTargetsHost,
                                           int taskCount,
                                           int targetLength,
                                           int topK,
                                           std::vector<PreAlignCudaPeak> *outPeaks,
                                           PreAlignCudaBatchResult *batchResult,
                                           std::string *errorOut);

bool prealign_cuda_find_column_maxima_batch(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetsHost,
                                            int taskCount,
                                            int targetLength,
                                            std::vector<int> *outColumnMaxima,
                                            PreAlignCudaBatchResult *batchResult,
                                            std::string *errorOut);

bool prealign_cuda_find_scoreinfo_batch(const PreAlignCudaQueryHandle &handle,
                                        const uint8_t *encodedTargetsHost,
                                        const int *minScoresHost,
                                        int taskCount,
                                        int targetLength,
                                        int maxScoreInfosPerTask,
                                        std::vector<PreAlignCudaPeak> *outScoreInfos,
                                        std::vector<int> *outCounts,
                                        bool *overflowOut,
                                        PreAlignCudaBatchResult *batchResult,
                                        std::string *errorOut);

bool prealign_cuda_find_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                               const uint8_t *encodedTargetsHost,
                                               const int *minScoresHost,
                                               int taskCount,
                                               int targetLength,
                                               int pruneMaxScoreInfosPerTask,
                                               std::vector<PreAlignCudaPeak> *outScoreInfos,
                                               std::vector<int> *outCounts,
                                               std::vector<int> *outInputCounts,
                                               bool *overflowOut,
                                               PreAlignCudaBatchResult *batchResult,
                                               std::string *errorOut);

bool prealign_cuda_find_column_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                                      const uint8_t *encodedTargetsHost,
                                                      int taskCount,
                                                      int targetLength,
                                                      int pruneMaxScoreInfosPerTask,
                                                      bool allowDynamicSmemOptin,
                                                      std::vector<PreAlignCudaPeak> *outScoreInfos,
                                                      std::vector<int> *outCounts,
                                                      std::vector<int> *outInputCounts,
                                                      bool *overflowOut,
                                                      PreAlignCudaBatchResult *columnBatchResult,
                                                      PreAlignCudaBatchResult *compactBatchResult,
                                                      std::string *errorOut);

bool prealign_cuda_find_streaming_scoreinfo_batch_pruned(const PreAlignCudaQueryHandle &handle,
                                                         const uint8_t *encodedTargetsHost,
                                                         const int *minScoresHost,
                                                         int taskCount,
                                                         int targetLength,
                                                         int pruneMaxScoreInfosPerTask,
                                                         std::vector<PreAlignCudaPeak> *outScoreInfos,
                                                         std::vector<int> *outCounts,
                                                         std::vector<int> *outInputCounts,
                                                         bool *overflowOut,
	                                                         PreAlignCudaBatchResult *columnBatchResult,
	                                                         PreAlignCudaBatchResult *compactBatchResult,
	                                                         bool legacyByteMode,
	                                                         bool legacyByteSharedMemoryMode,
	                                                         std::vector<int> *outColumnMaxima,
	                                                         std::string *errorOut);

bool prealign_cuda_find_streaming_scoreinfo_batch_pruned_fused_minscore(const PreAlignCudaQueryHandle &handle,
                                                                        const uint8_t *encodedTargetsHost,
                                                                        int taskCount,
                                                                        int targetLength,
                                                                        int pruneMaxScoreInfosPerTask,
                                                                        std::vector<PreAlignCudaPeak> *outScoreInfos,
                                                                        std::vector<int> *outCounts,
                                                                        std::vector<int> *outInputCounts,
                                                                        std::vector<int> *outScores,
                                                                        std::vector<int> *outMinScores,
                                                                        bool *overflowOut,
                                                                        PreAlignCudaBatchResult *columnBatchResult,
                                                                        PreAlignCudaBatchResult *reduceBatchResult,
                                                                        PreAlignCudaBatchResult *compactBatchResult,
                                                                        bool legacyByteMode,
                                                                        bool legacyByteSharedMemoryMode,
                                                                        std::vector<int> *outColumnMaxima,
                                                                        std::string *errorOut);

bool prealign_cuda_find_max_scores_batch(const PreAlignCudaQueryHandle &handle,
                                         const uint8_t *encodedTargetsHost,
                                         int taskCount,
                                         int targetLength,
                                         std::vector<int> *outScores,
                                         PreAlignCudaBatchResult *batchResult,
                                         std::string *errorOut);

bool prealign_cuda_find_max_scores_global_state_batch(const PreAlignCudaQueryHandle &handle,
                                                      const uint8_t *encodedTargetsHost,
                                                      int taskCount,
                                                      int targetLength,
                                                      bool legacyByteMode,
                                                      std::vector<int> *outScores,
                                                      PreAlignCudaBatchResult *columnBatchResult,
                                                      PreAlignCudaBatchResult *reduceBatchResult,
                                                      std::string *errorOut);

#endif
