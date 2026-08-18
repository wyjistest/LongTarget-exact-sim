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

bool prealign_cuda_emit_legacy_byte_attempt_descriptors(const PreAlignCudaQueryHandle &handle,
                                                        const uint8_t *encodedTargetsHost,
                                                        const int *minScoresHost,
                                                        int taskCount,
                                                        int targetLength,
                                                        int maxScoreInfosPerTask,
                                                        int maxDescriptorsPerTask,
                                                        int ntMinLength,
                                                        int scoringConfigKey,
                                                        vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                        vector<int> *outDescriptorCounts,
                                                        vector<int> *outScoreInfoCounts,
                                                        bool *overflowOut,
                                                        PreAlignCudaBatchResult *columnBatchResult,
                                                        PreAlignCudaBatchResult *compactBatchResult,
                                                        PreAlignCudaBatchResult *descriptorBatchResult,
                                                        string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)maxScoreInfosPerTask;
  (void)maxDescriptorsPerTask;
  (void)ntMinLength;
  (void)scoringConfigKey;
  if(outDescriptors != NULL)
  {
    outDescriptors->clear();
  }
  if(outDescriptorCounts != NULL)
  {
    outDescriptorCounts->clear();
  }
  if(outScoreInfoCounts != NULL)
  {
    outScoreInfoCounts->clear();
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
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool prealign_cuda_emit_legacy_byte_first_attempt_descriptors(const PreAlignCudaQueryHandle &handle,
                                                              const uint8_t *encodedTargetsHost,
                                                              const int *minScoresHost,
                                                              int taskCount,
                                                              int targetLength,
                                                              int maxScoreInfosPerTask,
                                                              int maxDescriptorsPerTask,
                                                              int ntMinLength,
                                                              int scoringConfigKey,
                                                              vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                              vector<int> *outDescriptorCounts,
                                                              vector<int> *outOriginalDescriptorCounts,
                                                              vector<int> *outScoreInfoCounts,
                                                              bool *overflowOut,
                                                              PreAlignCudaBatchResult *columnBatchResult,
                                                              PreAlignCudaBatchResult *compactBatchResult,
                                                              PreAlignCudaBatchResult *descriptorBatchResult,
                                                              PreAlignCudaBatchResult *summaryBatchResult,
                                                              string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)maxScoreInfosPerTask;
  (void)maxDescriptorsPerTask;
  (void)ntMinLength;
  (void)scoringConfigKey;
  if(outDescriptors != NULL)
  {
    outDescriptors->clear();
  }
  if(outDescriptorCounts != NULL)
  {
    outDescriptorCounts->clear();
  }
  if(outOriginalDescriptorCounts != NULL)
  {
    outOriginalDescriptorCounts->clear();
  }
  if(outScoreInfoCounts != NULL)
  {
    outScoreInfoCounts->clear();
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
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(summaryBatchResult != NULL)
  {
    *summaryBatchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

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
                                                               vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                               vector<int> *outDescriptorCounts,
                                                               vector<int> *outOriginalDescriptorCounts,
                                                               vector<int> *outScoreInfoCounts,
                                                               bool *overflowOut,
                                                               PreAlignCudaBatchResult *columnBatchResult,
                                                               PreAlignCudaBatchResult *compactBatchResult,
                                                               PreAlignCudaBatchResult *descriptorBatchResult,
                                                               PreAlignCudaBatchResult *summaryBatchResult,
                                                               string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)maxScoreInfosPerTask;
  (void)maxDescriptorsPerTask;
  (void)prefixAttemptsPerScoreInfo;
  (void)ntMinLength;
  (void)scoringConfigKey;
  if(outDescriptors != NULL)
  {
    outDescriptors->clear();
  }
  if(outDescriptorCounts != NULL)
  {
    outDescriptorCounts->clear();
  }
  if(outOriginalDescriptorCounts != NULL)
  {
    outOriginalDescriptorCounts->clear();
  }
  if(outScoreInfoCounts != NULL)
  {
    outScoreInfoCounts->clear();
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
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(summaryBatchResult != NULL)
  {
    *summaryBatchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

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
                                                               vector<PreAlignCudaAttemptDescriptor> *outDescriptors,
                                                               vector<int> *outDescriptorCounts,
                                                               vector<int> *outOriginalDescriptorCounts,
                                                               vector<int> *outScoreInfoCounts,
                                                               vector<int> *outCertificateRows,
                                                               bool *overflowOut,
                                                               PreAlignCudaBatchResult *columnBatchResult,
                                                               PreAlignCudaBatchResult *compactBatchResult,
                                                               PreAlignCudaBatchResult *descriptorBatchResult,
                                                               PreAlignCudaBatchResult *summaryBatchResult,
                                                               string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)minScoresHost;
  (void)taskCount;
  (void)targetLength;
  (void)maxScoreInfosPerTask;
  (void)maxDescriptorsPerTask;
  (void)ntMinLength;
  (void)scoringConfigKey;
  if(outDescriptors != NULL)
  {
    outDescriptors->clear();
  }
  if(outDescriptorCounts != NULL)
  {
    outDescriptorCounts->clear();
  }
  if(outOriginalDescriptorCounts != NULL)
  {
    outOriginalDescriptorCounts->clear();
  }
  if(outScoreInfoCounts != NULL)
  {
    outScoreInfoCounts->clear();
  }
  if(outCertificateRows != NULL)
  {
    outCertificateRows->clear();
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
  if(descriptorBatchResult != NULL)
  {
    *descriptorBatchResult = PreAlignCudaBatchResult();
  }
  if(summaryBatchResult != NULL)
  {
    *summaryBatchResult = PreAlignCudaBatchResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool prealign_cuda_emit_new_engine_skipped_work_certificates(
    const PreAlignCudaQueryHandle &handle,
    const PreAlignCudaNewEngineScoreInfoTask *tasksHost,
    int taskCount,
    const PreAlignCudaNewEngineCandidateGroup *candidateGroupsHost,
    int candidateGroupCount,
    const PreAlignCudaNewEngineReplayAttempt *replayAttemptsHost,
    int replayAttemptCount,
    vector<PreAlignCudaNewEngineSkippedWorkCertificate> *outCertificates,
    PreAlignCudaNewEngineCertificateResult *certificateResult,
    PreAlignCudaBatchResult *certificateBatchResult,
    string *errorOut)
{
  (void)handle;
  if(outCertificates == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffer";
    }
    return false;
  }
  outCertificates->clear();
  if(certificateResult != NULL)
  {
    *certificateResult = PreAlignCudaNewEngineCertificateResult();
  }
  if(certificateBatchResult != NULL)
  {
    *certificateBatchResult = PreAlignCudaBatchResult();
  }
  if(tasksHost == NULL || taskCount <= 0 ||
     candidateGroupsHost == NULL || candidateGroupCount <= 0 ||
     replayAttemptsHost == NULL || replayAttemptCount <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid new GPU engine certificate dimensions";
    }
    return false;
  }

  uint64_t skippedGroups = 0;
  uint64_t skippedAttempts = 0;
  uint64_t fallbackGroups = 0;
  outCertificates->assign(static_cast<size_t>(taskCount),
                          PreAlignCudaNewEngineSkippedWorkCertificate());
  for(int taskIndex = 0; taskIndex < taskCount; ++taskIndex)
  {
    const PreAlignCudaNewEngineScoreInfoTask &task = tasksHost[taskIndex];
    PreAlignCudaNewEngineSkippedWorkCertificate certificate;
    certificate.certificateValidBeforeD2h = 1;
    certificate.finalCpuOutputMembershipRequiredForCertificate = 0;
    certificate.skippedScoreInfoUpperBoundScore = task.minScore > 0 ? task.minScore - 1 : 0;
    int selectedGroupCount = 0;
    int selectedAttemptCount = 0;
    int maxSkippedScore = 0;
    int maxSkippedTargetSpan = 0;
    bool fallback = false;
    for(int groupIndex = 0; groupIndex < candidateGroupCount; ++groupIndex)
    {
      const PreAlignCudaNewEngineCandidateGroup &group = candidateGroupsHost[groupIndex];
      if(group.attemptStartIndex < 0 || group.attemptCount < 0 ||
         group.attemptStartIndex + group.attemptCount > replayAttemptCount)
      {
        fallback = true;
        continue;
      }
      if(group.score >= task.minScore)
      {
        ++selectedGroupCount;
        selectedAttemptCount += group.attemptCount;
        continue;
      }
      if(group.score > maxSkippedScore)
      {
        maxSkippedScore = group.score;
      }
      ++skippedGroups;
      skippedAttempts += static_cast<uint64_t>(group.attemptCount > 0 ? group.attemptCount : 0);
      for(int attemptOffset = 0; attemptOffset < group.attemptCount; ++attemptOffset)
      {
        const PreAlignCudaNewEngineReplayAttempt &attempt =
          replayAttemptsHost[group.attemptStartIndex + attemptOffset];
        const int targetSpan = attempt.targetEnd >= attempt.targetStart ?
          attempt.targetEnd - attempt.targetStart + 1 : 0;
        if(targetSpan > maxSkippedTargetSpan)
        {
          maxSkippedTargetSpan = targetSpan;
        }
      }
    }
    if(fallback || selectedGroupCount == 0 || selectedAttemptCount == 0)
    {
      certificate.taskOutputCapacityExhausted = 1;
      ++fallbackGroups;
    }
    certificate.skippedAttemptUpperBoundScore = maxSkippedScore;
    certificate.skippedAttemptUpperBoundNt = maxSkippedTargetSpan;
    certificate.skippedAttemptUpperBoundIdentity = maxSkippedScore;
    certificate.skippedAttemptUpperBoundStability = selectedAttemptCount;
    certificate.scoreInfoLocalBreakState = selectedGroupCount;
    (*outCertificates)[static_cast<size_t>(taskIndex)] = certificate;
  }

  if(certificateResult != NULL)
  {
    certificateResult->certificateProducerActive = true;
    certificateResult->certificateValidBeforeD2h = true;
    certificateResult->finalCpuOutputMembershipRequiredForCertificate = false;
    certificateResult->skippedGroups = skippedGroups;
    certificateResult->skippedAttempts = skippedAttempts;
    certificateResult->conservativeFallbackGroups = fallbackGroups;
    certificateResult->certificateFalseNegatives = 0;
    certificateResult->certificateMissingRequiredAttempts = 0;
  }
  if(certificateBatchResult != NULL)
  {
    certificateBatchResult->usedCuda = false;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
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

bool prealign_cuda_find_max_endpoints_batch(const PreAlignCudaQueryHandle &handle,
                                            const uint8_t *encodedTargetsHost,
                                            int taskCount,
                                            int targetLength,
                                            vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
                                            PreAlignCudaBatchResult *batchResult,
                                            string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  if(outEndpoints != NULL)
  {
    outEndpoints->clear();
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

bool prealign_cuda_find_max_forward_endpoints_batch(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  int taskCount,
  int targetLength,
  vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
  PreAlignCudaBatchResult *batchResult,
  string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)taskCount;
  (void)targetLength;
  if(outEndpoints != NULL)
  {
    outEndpoints->clear();
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

bool prealign_cuda_find_reverse_endpoints_batch(
  const PreAlignCudaQueryHandle &handle,
  const uint8_t *encodedTargetsHost,
  const PreAlignCudaAttemptEndpoint *forwardEndpointsHost,
  int taskCount,
  int targetLength,
  vector<PreAlignCudaAttemptEndpoint> *outEndpoints,
  PreAlignCudaBatchResult *batchResult,
  string *errorOut)
{
  (void)handle;
  (void)encodedTargetsHost;
  (void)forwardEndpointsHost;
  (void)taskCount;
  (void)targetLength;
  if(outEndpoints != NULL)
  {
    outEndpoints->clear();
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
