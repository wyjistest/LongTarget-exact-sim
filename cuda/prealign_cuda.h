#ifndef LONGTARGET_PREALIGN_CUDA_H
#define LONGTARGET_PREALIGN_CUDA_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#if defined(__CUDACC__)
#define LONGTARGET_PREALIGN_CUDA_HOST_DEVICE __host__ __device__
#else
#define LONGTARGET_PREALIGN_CUDA_HOST_DEVICE
#endif

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

struct PreAlignCudaAttemptDescriptor
{
  LONGTARGET_PREALIGN_CUDA_HOST_DEVICE PreAlignCudaAttemptDescriptor():
    taskIndex(-1),
    scoreInfoPosition(-1),
    scoreInfoScore(0),
    scoreInfoOrder(-1),
    attemptOrder(-1),
    targetStart(-1),
    cutlength(0),
    targetEndRequiredForFallback(0),
    ntMinLength(0),
    scoringConfigKey(0),
    overflowFlag(0) {}

  int taskIndex;
  int scoreInfoPosition;
  int scoreInfoScore;
  int scoreInfoOrder;
  int attemptOrder;
  int targetStart;
  int cutlength;
  int targetEndRequiredForFallback;
  int ntMinLength;
  int scoringConfigKey;
  int overflowFlag;
};

struct PreAlignCudaNewEngineScoreInfoTask
{
  LONGTARGET_PREALIGN_CUDA_HOST_DEVICE PreAlignCudaNewEngineScoreInfoTask():
    queryId(-1),
    queryOffset(0),
    queryLength(0),
    targetId(-1),
    targetOffset(0),
    targetLength(0),
    scoringConfigKey(0),
    minScore(0),
    outputSlot(-1),
    taskOrder(-1) {}

  int queryId;
  int queryOffset;
  int queryLength;
  int targetId;
  int targetOffset;
  int targetLength;
  int scoringConfigKey;
  int minScore;
  int outputSlot;
  int taskOrder;
};

struct PreAlignCudaNewEngineCandidateGroup
{
  LONGTARGET_PREALIGN_CUDA_HOST_DEVICE PreAlignCudaNewEngineCandidateGroup():
    scoreInfoGroupId(-1),
    score(0),
    targetEnd(-1),
    queryEnd(-1),
    candidateOrderKey(0),
    attemptStartIndex(0),
    attemptCount(0) {}

  int scoreInfoGroupId;
  int score;
  int targetEnd;
  int queryEnd;
  int candidateOrderKey;
  int attemptStartIndex;
  int attemptCount;
};

struct PreAlignCudaNewEngineReplayAttempt
{
  LONGTARGET_PREALIGN_CUDA_HOST_DEVICE PreAlignCudaNewEngineReplayAttempt():
    attemptId(-1),
    groupId(-1),
    targetStart(-1),
    targetEnd(-1),
    queryStart(-1),
    queryEnd(-1),
    legacyAttemptOrder(-1) {}

  int attemptId;
  int groupId;
  int targetStart;
  int targetEnd;
  int queryStart;
  int queryEnd;
  int legacyAttemptOrder;
};

struct PreAlignCudaNewEngineSkippedWorkCertificate
{
  LONGTARGET_PREALIGN_CUDA_HOST_DEVICE PreAlignCudaNewEngineSkippedWorkCertificate():
    skippedScoreInfoUpperBoundScore(0),
    skippedAttemptUpperBoundScore(0),
    skippedAttemptUpperBoundNt(0),
    skippedAttemptUpperBoundIdentity(0),
    skippedAttemptUpperBoundStability(0),
    taskOutputCapacityExhausted(0),
    scoreInfoLocalBreakState(0),
    certificateValidBeforeD2h(0),
    finalCpuOutputMembershipRequiredForCertificate(0) {}

  int skippedScoreInfoUpperBoundScore;
  int skippedAttemptUpperBoundScore;
  int skippedAttemptUpperBoundNt;
  int skippedAttemptUpperBoundIdentity;
  int skippedAttemptUpperBoundStability;
  int taskOutputCapacityExhausted;
  int scoreInfoLocalBreakState;
  int certificateValidBeforeD2h;
  int finalCpuOutputMembershipRequiredForCertificate;
};

LONGTARGET_PREALIGN_CUDA_HOST_DEVICE inline int
prealign_cuda_legacy_byte_attempt_cutlength(int score,
                                            int position,
                                            int attemptOrder)
{
  float identity = 0.6f;
  for(int i = 0; i < attemptOrder; ++i)
  {
    identity += 0.1f;
  }
  int cutlength =
    static_cast<int>(static_cast<int>(score + 24) /
                     (9.0f * identity - 4.0f) + 1.0f);
  cutlength = position - cutlength + 1 > 0 ? cutlength : position + 1;
  return cutlength;
}

LONGTARGET_PREALIGN_CUDA_HOST_DEVICE inline bool
prealign_cuda_legacy_byte_attempt_order_valid(int attemptOrder)
{
  float identity = 0.6f;
  for(int i = 0; i < attemptOrder; ++i)
  {
    identity += 0.1f;
  }
  return identity <= 1.0f;
}

#undef LONGTARGET_PREALIGN_CUDA_HOST_DEVICE

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

struct PreAlignCudaNewEngineCertificateResult
{
  PreAlignCudaNewEngineCertificateResult():
    certificateProducerActive(false),
    certificateValidBeforeD2h(false),
    finalCpuOutputMembershipRequiredForCertificate(false),
    skippedGroups(0),
    skippedAttempts(0),
    conservativeFallbackGroups(0),
    certificateFalseNegatives(0),
    certificateMissingRequiredAttempts(0) {}

  bool certificateProducerActive;
  bool certificateValidBeforeD2h;
  bool finalCpuOutputMembershipRequiredForCertificate;
  uint64_t skippedGroups;
  uint64_t skippedAttempts;
  uint64_t conservativeFallbackGroups;
  uint64_t certificateFalseNegatives;
  uint64_t certificateMissingRequiredAttempts;
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

bool prealign_cuda_emit_legacy_byte_attempt_descriptors(const PreAlignCudaQueryHandle &handle,
                                                        const uint8_t *encodedTargetsHost,
                                                        const int *minScoresHost,
                                                        int taskCount,
                                                        int targetLength,
                                                        int maxScoreInfosPerTask,
                                                        int maxDescriptorsPerTask,
                                                        int ntMinLength,
                                                        int scoringConfigKey,
                                                        std::vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                        std::vector<int> *outDescriptorCounts,
                                                        std::vector<int> *outScoreInfoCounts,
                                                        bool *overflowOut,
                                                        PreAlignCudaBatchResult *columnBatchResult,
                                                        PreAlignCudaBatchResult *compactBatchResult,
                                                        PreAlignCudaBatchResult *descriptorBatchResult,
                                                        std::string *errorOut);

bool prealign_cuda_emit_legacy_byte_first_attempt_descriptors(const PreAlignCudaQueryHandle &handle,
                                                              const uint8_t *encodedTargetsHost,
                                                              const int *minScoresHost,
                                                              int taskCount,
                                                              int targetLength,
                                                              int maxScoreInfosPerTask,
                                                              int maxDescriptorsPerTask,
                                                              int ntMinLength,
                                                              int scoringConfigKey,
                                                              std::vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                              std::vector<int> *outDescriptorCounts,
                                                              std::vector<int> *outOriginalDescriptorCounts,
                                                              std::vector<int> *outScoreInfoCounts,
                                                              bool *overflowOut,
                                                              PreAlignCudaBatchResult *columnBatchResult,
                                                              PreAlignCudaBatchResult *compactBatchResult,
                                                              PreAlignCudaBatchResult *descriptorBatchResult,
                                                              PreAlignCudaBatchResult *summaryBatchResult,
                                                              std::string *errorOut);

bool prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors(const PreAlignCudaQueryHandle &handle,
                                                               const uint8_t *encodedTargetsHost,
                                                               const int *minScoresHost,
                                                               int taskCount,
                                                               int targetLength,
                                                               int maxScoreInfosPerTask,
                                                               int maxDescriptorsPerTask,
                                                               int prefixAttemptsPerScoreInfo,
                                                               int ntMinLength,
                                                               int scoringConfigKey,
                                                               std::vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                               std::vector<int> *outDescriptorCounts,
                                                               std::vector<int> *outOriginalDescriptorCounts,
                                                               std::vector<int> *outScoreInfoCounts,
                                                               bool *overflowOut,
                                                               PreAlignCudaBatchResult *columnBatchResult,
                                                               PreAlignCudaBatchResult *compactBatchResult,
                                                               PreAlignCudaBatchResult *descriptorBatchResult,
                                                               PreAlignCudaBatchResult *summaryBatchResult,
                                                               std::string *errorOut);

bool prealign_cuda_emit_legacy_byte_task_frontier_certificate_descriptors(
                                                        const PreAlignCudaQueryHandle &handle,
                                                        const uint8_t *encodedTargetsHost,
                                                        const int *minScoresHost,
                                                        int taskCount,
                                                        int targetLength,
                                                        int maxScoreInfosPerTask,
                                                        int maxDescriptorsPerTask,
                                                        int ntMinLength,
                                                        int scoringConfigKey,
                                                        std::vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                        std::vector<int> *outDescriptorCounts,
                                                        std::vector<int> *outOriginalDescriptorCounts,
                                                        std::vector<int> *outScoreInfoCounts,
                                                        std::vector<int> *outCertificateRows,
                                                        bool *overflowOut,
                                                        PreAlignCudaBatchResult *columnBatchResult,
                                                        PreAlignCudaBatchResult *compactBatchResult,
                                                        PreAlignCudaBatchResult *descriptorBatchResult,
                                                        PreAlignCudaBatchResult *summaryBatchResult,
                                                        std::string *errorOut);

bool prealign_cuda_emit_new_engine_skipped_work_certificates(
    const PreAlignCudaQueryHandle &handle,
    const PreAlignCudaNewEngineScoreInfoTask *tasksHost,
    int taskCount,
    const PreAlignCudaNewEngineCandidateGroup *candidateGroupsHost,
    int candidateGroupCount,
    const PreAlignCudaNewEngineReplayAttempt *replayAttemptsHost,
    int replayAttemptCount,
    std::vector<PreAlignCudaNewEngineSkippedWorkCertificate> *outCertificates,
    PreAlignCudaNewEngineCertificateResult *certificateResult,
    PreAlignCudaBatchResult *certificateBatchResult,
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
