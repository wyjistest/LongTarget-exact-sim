#include "exact_sim.h"
#include "cuda/calc_score_cuda.h"
#include <fstream>
#include <future>
#include <sstream>
#include <thread>
using namespace std;
struct ExactFragmentInfo
{
  ExactFragmentInfo():dnaStartPos(0),skip(false) {}
  ExactFragmentInfo(const string &s1,long n1,bool n2):sequence(s1),dnaStartPos(n1),skip(n2) {}
  string sequence;
  long dnaStartPos;
  bool skip;
};

struct ExactSimTaskSpec
{
  ExactSimTaskSpec():fragmentIndex(0),dnaStartPos(0),reverseMode(0),parallelMode(0),rule(0) {}
  ExactSimTaskSpec(size_t n1,long n2,long n3,long n4,int n5,const string &s1):
    fragmentIndex(n1),dnaStartPos(n2),reverseMode(n3),parallelMode(n4),rule(n5),transformedSequence(s1) {}
  size_t fragmentIndex;
  long dnaStartPos;
  long reverseMode;
  long parallelMode;
  int rule;
  string transformedSequence;
};

struct LongTargetCudaWorkerMetrics
{
  LongTargetCudaWorkerMetrics():
    device(-1),
    slot(0),
    taskCount(0),
    thresholdSeconds(0.0),
    simSeconds(0.0),
    filterSeconds(0.0) {}

  int device;
  int slot;
  uint64_t taskCount;
  double thresholdSeconds;
  double simSeconds;
  double filterSeconds;
};

struct LongTargetCudaDeviceMetrics
{
  LongTargetCudaDeviceMetrics():
    device(-1),
    workerCount(0),
    taskCount(0),
    thresholdSeconds(0.0),
    simSeconds(0.0),
    filterSeconds(0.0) {}

  int device;
  uint64_t workerCount;
  uint64_t taskCount;
  double thresholdSeconds;
  double simSeconds;
  double filterSeconds;
};

struct LongTargetExecutionMetrics
{
  LongTargetExecutionMetrics():
    thresholdSeconds(0.0),
    simSeconds(0.0),
    postProcessSeconds(0.0),
    totalSeconds(0.0),
    thresholdBackend("cpu"),
    twoStageThresholdMode("legacy"),
    twoStageRejectMode("off"),
    twoStageDiscoveryMode("off"),
    twoStageDiscoveryStatus("off"),
    prefilterBackend("disabled"),
    prefilterHits(0),
    twoStageTasksWithAnySeed(0),
    twoStageTasksWithAnyRefineWindowBeforeGate(0),
    twoStageTasksWithAnyRefineWindowAfterGate(0),
    twoStageThresholdInvokedTasks(0),
    twoStageThresholdSkippedNoSeedTasks(0),
    twoStageThresholdSkippedNoRefineWindowTasks(0),
    twoStageThresholdSkippedAfterGateTasks(0),
    twoStageThresholdBatchCount(0),
    twoStageThresholdBatchTasksTotal(0),
    twoStageThresholdBatchSizeMax(0),
    twoStageThresholdBatchedSeconds(0.0),
    twoStageDiscoveryTaskCount(0),
    twoStageDiscoveryPrefilterFailedTasks(0),
    twoStageDiscoveryPredictedSkip(0),
    twoStageDiscoveryPredictedSkipTasks(0),
    twoStageDiscoveryPrefilterOnlySeconds(0.0),
    twoStageDiscoveryGateSeconds(0.0),
    twoStageWindowsBeforeGate(0),
    twoStageWindowsAfterGate(0),
    twoStageWindowsRejectedByMinPeakScore(0),
    twoStageWindowsRejectedBySupport(0),
    twoStageWindowsRejectedByMargin(0),
    twoStageWindowsTrimmedByMaxWindows(0),
    twoStageWindowsTrimmedByMaxBp(0),
    twoStageSingletonRescuedWindows(0),
    twoStageSingletonRescuedTasks(0),
    twoStageSingletonRescueBpTotal(0),
    twoStageSelectiveFallbackEnabled(0),
    twoStageSelectiveFallbackTriggeredTasks(0),
    twoStageSelectiveFallbackNonEmptyCandidateTasks(0),
    twoStageSelectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks(0),
    twoStageSelectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks(0),
    twoStageSelectiveFallbackNonEmptyRejectedBySingletonOverrideTasks(0),
    twoStageSelectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks(0),
    twoStageSelectiveFallbackNonEmptyRejectedByScoreGapTasks(0),
    twoStageSelectiveFallbackNonEmptyTriggeredTasks(0),
    twoStageSelectiveFallbackSelectedWindows(0),
    twoStageSelectiveFallbackSelectedBpTotal(0),
    twoStageTaskRerunEnabled(0),
    twoStageTaskRerunBudget(0),
    twoStageTaskRerunSelectedTasks(0),
    twoStageTaskRerunEffectiveTasks(0),
    twoStageTaskRerunAddedWindows(0),
    twoStageTaskRerunRefineBpTotal(0),
    twoStageTaskRerunSeconds(0.0),
    twoStageTaskRerunSelectedTasksPath(""),
    refineWindowCount(0),
    refineTotalBp(0),
    calcScoreTasksTotal(0),
    calcScoreCudaTasks(0),
    calcScoreCpuFallbackTasks(0),
    calcScoreCpuFallbackQueryGt8192(0),
    calcScoreCpuFallbackTargetGt8192(0),
    calcScoreCpuFallbackTargetGt65535(0),
    calcScoreCpuFallbackOther(0),
    calcScoreQueryLength(0),
    calcScoreTargetBinLe8192Tasks(0),
    calcScoreTargetBinLe8192Bp(0),
    calcScoreTargetBin8193To65535Tasks(0),
    calcScoreTargetBin8193To65535Bp(0),
    calcScoreTargetBinGt65535Tasks(0),
    calcScoreTargetBinGt65535Bp(0),
    calcScoreCudaTargetH2DSeconds(0.0),
    calcScoreCudaPermutationH2DSeconds(0.0),
    calcScoreCudaKernelSeconds(0.0),
    calcScoreCudaScoreD2HSeconds(0.0),
    calcScoreCudaSyncWaitSeconds(0.0),
    calcScoreHostEncodeSeconds(0.0),
    calcScoreHostShufflePlanSeconds(0.0),
    calcScoreHostMleSeconds(0.0),
    calcScoreCudaPipelineV2Enabled(0),
    calcScoreCudaPipelineV2ShadowEnabled(0),
    calcScoreCudaPipelineV2UsedGroups(0),
    calcScoreCudaPipelineV2Fallbacks(0),
    calcScoreCudaPipelineV2ShadowComparisons(0),
    calcScoreCudaPipelineV2ShadowMismatches(0),
    calcScoreCudaPipelineV2KernelSeconds(0.0),
    calcScoreCudaPipelineV2ScoreD2HSeconds(0.0),
    calcScoreCudaPipelineV2HostReduceSeconds(0.0),
    calcScoreCudaGroups(0),
    calcScoreCudaPairs(0),
    calcScoreCudaTargetBytesH2D(0),
    calcScoreCudaPermutationBytesH2D(0),
    calcScoreCudaScoreBytesD2H(0),
    simScanTasks(0),
    simScanLaunches(0),
    simTracebackCandidates(0),
    simTracebackTieCount(0) {}

  double thresholdSeconds;
  double simSeconds;
  double postProcessSeconds;
  double totalSeconds;
  string thresholdBackend;
  string twoStageThresholdMode;
  string twoStageRejectMode;
  string twoStageDiscoveryMode;
  string twoStageDiscoveryStatus;
  string prefilterBackend;
  uint64_t prefilterHits;
  uint64_t twoStageTasksWithAnySeed;
  uint64_t twoStageTasksWithAnyRefineWindowBeforeGate;
  uint64_t twoStageTasksWithAnyRefineWindowAfterGate;
  uint64_t twoStageThresholdInvokedTasks;
  uint64_t twoStageThresholdSkippedNoSeedTasks;
  uint64_t twoStageThresholdSkippedNoRefineWindowTasks;
  uint64_t twoStageThresholdSkippedAfterGateTasks;
  uint64_t twoStageThresholdBatchCount;
  uint64_t twoStageThresholdBatchTasksTotal;
  uint64_t twoStageThresholdBatchSizeMax;
  double twoStageThresholdBatchedSeconds;
  uint64_t twoStageDiscoveryTaskCount;
  uint64_t twoStageDiscoveryPrefilterFailedTasks;
  uint64_t twoStageDiscoveryPredictedSkip;
  uint64_t twoStageDiscoveryPredictedSkipTasks;
  double twoStageDiscoveryPrefilterOnlySeconds;
  double twoStageDiscoveryGateSeconds;
  uint64_t twoStageWindowsBeforeGate;
  uint64_t twoStageWindowsAfterGate;
  uint64_t twoStageWindowsRejectedByMinPeakScore;
  uint64_t twoStageWindowsRejectedBySupport;
  uint64_t twoStageWindowsRejectedByMargin;
  uint64_t twoStageWindowsTrimmedByMaxWindows;
  uint64_t twoStageWindowsTrimmedByMaxBp;
  uint64_t twoStageSingletonRescuedWindows;
  uint64_t twoStageSingletonRescuedTasks;
  uint64_t twoStageSingletonRescueBpTotal;
  uint64_t twoStageSelectiveFallbackEnabled;
  uint64_t twoStageSelectiveFallbackTriggeredTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyCandidateTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyRejectedBySingletonOverrideTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyRejectedByScoreGapTasks;
  uint64_t twoStageSelectiveFallbackNonEmptyTriggeredTasks;
  uint64_t twoStageSelectiveFallbackSelectedWindows;
  uint64_t twoStageSelectiveFallbackSelectedBpTotal;
  uint64_t twoStageTaskRerunEnabled;
  uint64_t twoStageTaskRerunBudget;
  uint64_t twoStageTaskRerunSelectedTasks;
  uint64_t twoStageTaskRerunEffectiveTasks;
  uint64_t twoStageTaskRerunAddedWindows;
  uint64_t twoStageTaskRerunRefineBpTotal;
  double twoStageTaskRerunSeconds;
  string twoStageTaskRerunSelectedTasksPath;
  uint64_t refineWindowCount;
  uint64_t refineTotalBp;
  uint64_t calcScoreTasksTotal;
  uint64_t calcScoreCudaTasks;
  uint64_t calcScoreCpuFallbackTasks;
  uint64_t calcScoreCpuFallbackQueryGt8192;
  uint64_t calcScoreCpuFallbackTargetGt8192;
  uint64_t calcScoreCpuFallbackTargetGt65535;
  uint64_t calcScoreCpuFallbackOther;
  uint64_t calcScoreQueryLength;
  uint64_t calcScoreTargetBinLe8192Tasks;
  uint64_t calcScoreTargetBinLe8192Bp;
  uint64_t calcScoreTargetBin8193To65535Tasks;
  uint64_t calcScoreTargetBin8193To65535Bp;
  uint64_t calcScoreTargetBinGt65535Tasks;
  uint64_t calcScoreTargetBinGt65535Bp;
  double calcScoreCudaTargetH2DSeconds;
  double calcScoreCudaPermutationH2DSeconds;
  double calcScoreCudaKernelSeconds;
  double calcScoreCudaScoreD2HSeconds;
  double calcScoreCudaSyncWaitSeconds;
  double calcScoreHostEncodeSeconds;
  double calcScoreHostShufflePlanSeconds;
  double calcScoreHostMleSeconds;
  uint64_t calcScoreCudaPipelineV2Enabled;
  uint64_t calcScoreCudaPipelineV2ShadowEnabled;
  uint64_t calcScoreCudaPipelineV2UsedGroups;
  uint64_t calcScoreCudaPipelineV2Fallbacks;
  uint64_t calcScoreCudaPipelineV2ShadowComparisons;
  uint64_t calcScoreCudaPipelineV2ShadowMismatches;
  double calcScoreCudaPipelineV2KernelSeconds;
  double calcScoreCudaPipelineV2ScoreD2HSeconds;
  double calcScoreCudaPipelineV2HostReduceSeconds;
  uint64_t calcScoreCudaGroups;
  uint64_t calcScoreCudaPairs;
  uint64_t calcScoreCudaTargetBytesH2D;
  uint64_t calcScoreCudaPermutationBytesH2D;
  uint64_t calcScoreCudaScoreBytesD2H;
  uint64_t simScanTasks;
  uint64_t simScanLaunches;
  uint64_t simTracebackCandidates;
  uint64_t simTracebackTieCount;
  vector<LongTargetCudaWorkerMetrics> simCudaWorkers;
  vector<LongTargetCudaDeviceMetrics> simCudaDevices;
};

enum LongTargetCalcScoreFallbackReason
{
  LONGTARGET_CALC_SCORE_FALLBACK_NONE = 0,
  LONGTARGET_CALC_SCORE_FALLBACK_QUERY_GT_8192 = 1,
  LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_8192 = 2,
  LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_65535 = 3,
  LONGTARGET_CALC_SCORE_FALLBACK_OTHER = 4
};

struct LongTargetSimScoreMatrixInt
{
  int value[128][128];
};

struct LongTargetWindowPipelineTask
{
  LongTargetWindowPipelineTask():taskIndex(0),minScore(0) {}
  LongTargetWindowPipelineTask(size_t taskIndexValue,int minScoreValue):
    taskIndex(taskIndexValue),
    minScore(minScoreValue) {}

  size_t taskIndex;
  int minScore;
};

struct LongTargetWindowPipelinePreparedBatch
{
  LongTargetWindowPipelinePreparedBatch():
    valid(false),
    usedInitialReduce(false),
    usedInitialProposals(false),
    usedInitialPinnedAsyncCpuPipeline(false),
    gpuStageNanoseconds(0)
  {
  }

  bool valid;
  bool usedInitialReduce;
  bool usedInitialProposals;
  bool usedInitialPinnedAsyncCpuPipeline;
  uint64_t gpuStageNanoseconds;
  vector<LongTargetWindowPipelineTask> batchTasks;
  string paddedQuery;
  vector<string> paddedTargets;
  vector<SimKernelContext> contexts;
  vector<SimInitialPinnedAsyncCpuPipelineApplyState> initialCpuPipelineStates;
  vector<SimScanCudaInitialBatchResult> cudaResults;
  SimScanCudaBatchResult cudaBatchResult;
};

static inline string longtargetSimInitialReduceBackendLabel()
{
  if(!simCudaInitialReduceRequestEnabledRuntime())
  {
    return "off";
  }

  const char *initialReduceBackendEnv = getenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
  if(initialReduceBackendEnv != NULL && initialReduceBackendEnv[0] != '\0')
  {
    if(strcmp(initialReduceBackendEnv,"hash") == 0)
    {
      return "hash";
    }
    if(strcmp(initialReduceBackendEnv,"segmented") == 0)
    {
      return "segmented";
    }
    if(strcmp(initialReduceBackendEnv,"ordered_segmented_v3") == 0 ||
       strcmp(initialReduceBackendEnv,"ordered-segmented-v3") == 0)
    {
      return "ordered_segmented_v3";
    }
    return "legacy";
  }

  const char *legacyHashBackendEnv = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
  if(legacyHashBackendEnv != NULL &&
     legacyHashBackendEnv[0] != '\0' &&
     strcmp(legacyHashBackendEnv,"0") != 0)
  {
    return "hash";
  }

  return (simCudaMainlineResidencyEnabledRuntime() ||
          simCudaInitialExactFrontierReplayEnabledRuntime()) ?
         "ordered_segmented_v3" : "legacy";
}

static inline string longtargetSimInitialReplayAuthorityLabel()
{
  if(simCudaInitialExactFrontierReplayEnabledRuntime() &&
     simCudaInitialReduceRequestEnabledRuntime())
  {
    return "gpu_real";
  }
  if(simCudaInitialOrderedSegmentedV3ShadowEnabledRuntime() ||
     simCudaInitialFrontierTransducerShadowEnabledRuntime())
  {
    return "gpu_shadow";
  }
  return "cpu";
}

static inline const char *longtargetSimInitialExactFrontierShadowGateDisabledReason()
{
  return simCudaInitialExactFrontierShadowGateRequestedRuntime() ?
         "missing_contract_counters" : "env_off";
}

static inline const char *longtargetSimInitialExactFrontierShadowBackendLabel()
{
  return simCudaInitialExactFrontierShadowGateRequestedRuntime() ?
         "one_chunk_stub" : "none";
}

static inline const char *longtargetSimInitialExactFrontierShadowBackendDisabledReason()
{
  return simCudaInitialExactFrontierShadowGateRequestedRuntime() ?
         "one_chunk_backend_not_implemented" : "env_off";
}

static inline size_t longtarget_window_pipeline_batch_size()
{
  static const size_t batchSize = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_WINDOW_PIPELINE_BATCH_SIZE");
    if(env == NULL || env[0] == '\0')
    {
      return static_cast<size_t>(8u);
    }
    char *end = NULL;
    long parsed = strtol(env,&end,10);
    if(end == env)
    {
      return static_cast<size_t>(8u);
    }
    if(parsed < 2)
    {
      return static_cast<size_t>(2u);
    }
    if(parsed > 64)
    {
      return static_cast<size_t>(64u);
    }
    return static_cast<size_t>(parsed);
  }();
  return batchSize;
}

static inline bool longtarget_window_pipeline_enabled_runtime(bool twoStage)
{
  return !twoStage &&
         simCudaWindowPipelineEnabledRuntime() &&
         !simFastEnabledRuntime() &&
         !simCudaValidateEnabledRuntime() &&
         sim_scan_cuda_is_built();
}

static inline SimWindowPipelineIneligibleReason longtarget_classify_window_pipeline_ineligible_reason(bool twoStage,
                                                                                                     bool simFast,
                                                                                                     bool validateMode,
                                                                                                     bool windowPipelineRuntimeEnabled,
                                                                                                     const string &rnaSequence,
                                                                                                     const ExactSimTaskSpec &task,
                                                                                                     int minScore)
{
  if(twoStage)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_TWO_STAGE;
  }
  if(simFast)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_SIM_FAST;
  }
  if(validateMode)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_VALIDATE;
  }
  if(!windowPipelineRuntimeEnabled)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_RUNTIME_DISABLED;
  }
  if(rnaSequence.empty() || rnaSequence.size() > 8192u)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_QUERY_GT_8192;
  }
  if(task.transformedSequence.empty())
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_RUNTIME_DISABLED;
  }
  if(task.transformedSequence.size() > 8192u)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_TARGET_GT_8192;
  }
  if(minScore < 0)
  {
    return SIM_WINDOW_PIPELINE_INELIGIBLE_NEGATIVE_MIN_SCORE;
  }
  return SIM_WINDOW_PIPELINE_INELIGIBLE_RUNTIME_DISABLED;
}

static inline LongTargetCalcScoreFallbackReason longtarget_classify_calc_score_fallback_reason(int queryLength,
                                                                                              int targetLength)
{
  if(queryLength > 8192)
  {
    return LONGTARGET_CALC_SCORE_FALLBACK_QUERY_GT_8192;
  }
  if(targetLength > 65535)
  {
    return LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_65535;
  }
  if(targetLength > 8192)
  {
    return LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_8192;
  }
  return LONGTARGET_CALC_SCORE_FALLBACK_OTHER;
}

static inline void longtarget_record_calc_score_target_bin(LongTargetExecutionMetrics &metrics,
                                                           int targetLength,
                                                           uint64_t taskCount)
{
  const uint64_t bp = targetLength > 0 ? taskCount * static_cast<uint64_t>(targetLength) : 0;
  if(targetLength <= 8192)
  {
    metrics.calcScoreTargetBinLe8192Tasks += taskCount;
    metrics.calcScoreTargetBinLe8192Bp += bp;
    return;
  }
  if(targetLength <= 65535)
  {
    metrics.calcScoreTargetBin8193To65535Tasks += taskCount;
    metrics.calcScoreTargetBin8193To65535Bp += bp;
    return;
  }
  metrics.calcScoreTargetBinGt65535Tasks += taskCount;
  metrics.calcScoreTargetBinGt65535Bp += bp;
}

static inline void longtarget_record_calc_score_group_result(LongTargetExecutionMetrics &metrics,
                                                             int queryLength,
                                                             int targetLength,
                                                             uint64_t taskCount,
                                                             bool usedCuda)
{
  if(usedCuda)
  {
    metrics.calcScoreCudaTasks += taskCount;
    return;
  }

  metrics.calcScoreCpuFallbackTasks += taskCount;
  switch(longtarget_classify_calc_score_fallback_reason(queryLength,targetLength))
  {
    case LONGTARGET_CALC_SCORE_FALLBACK_QUERY_GT_8192:
      metrics.calcScoreCpuFallbackQueryGt8192 += taskCount;
      break;
    case LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_65535:
      metrics.calcScoreCpuFallbackTargetGt65535 += taskCount;
      break;
    case LONGTARGET_CALC_SCORE_FALLBACK_TARGET_GT_8192:
      metrics.calcScoreCpuFallbackTargetGt8192 += taskCount;
      break;
    case LONGTARGET_CALC_SCORE_FALLBACK_OTHER:
    case LONGTARGET_CALC_SCORE_FALLBACK_NONE:
    default:
      metrics.calcScoreCpuFallbackOther += taskCount;
      break;
	  }
	}

static inline void longtarget_record_calc_score_cuda_batch_telemetry(LongTargetExecutionMetrics &metrics,
                                                                     uint64_t taskCount,
                                                                     uint64_t pairCount,
                                                                     const CalcScoreCudaBatchResult &batchResult)
{
  if(!batchResult.usedCuda)
  {
    return;
  }
  metrics.calcScoreCudaGroups += 1;
  metrics.calcScoreCudaPairs += taskCount * pairCount;
  metrics.calcScoreCudaTargetH2DSeconds += batchResult.targetH2DSeconds;
  metrics.calcScoreCudaPermutationH2DSeconds += batchResult.permutationH2DSeconds;
  metrics.calcScoreCudaKernelSeconds += batchResult.kernelSeconds;
  metrics.calcScoreCudaScoreD2HSeconds += batchResult.scoreD2HSeconds;
  metrics.calcScoreCudaSyncWaitSeconds += batchResult.syncWaitSeconds;
  if(batchResult.pipelineV2Enabled)
  {
    metrics.calcScoreCudaPipelineV2Enabled = 1;
  }
  if(batchResult.pipelineV2ShadowEnabled)
  {
    metrics.calcScoreCudaPipelineV2ShadowEnabled = 1;
  }
  if(batchResult.pipelineV2Used)
  {
    metrics.calcScoreCudaPipelineV2UsedGroups += 1;
  }
  if(batchResult.pipelineV2Fallback)
  {
    metrics.calcScoreCudaPipelineV2Fallbacks += 1;
  }
  metrics.calcScoreCudaPipelineV2ShadowComparisons += batchResult.pipelineV2ShadowComparisons;
  metrics.calcScoreCudaPipelineV2ShadowMismatches += batchResult.pipelineV2ShadowMismatches;
  metrics.calcScoreCudaPipelineV2KernelSeconds += batchResult.pipelineV2KernelSeconds;
  metrics.calcScoreCudaPipelineV2ScoreD2HSeconds += batchResult.pipelineV2ScoreD2HSeconds;
  metrics.calcScoreCudaPipelineV2HostReduceSeconds += batchResult.pipelineV2HostReduceSeconds;
  metrics.calcScoreCudaTargetBytesH2D += batchResult.targetBytesH2D;
  metrics.calcScoreCudaPermutationBytesH2D += batchResult.permutationBytesH2D;
  metrics.calcScoreCudaScoreBytesD2H += batchResult.scoreBytesD2H;
}

static inline bool longtarget_window_pipeline_overlap_enabled_runtime(bool useWindowPipeline)
{
  return useWindowPipeline &&
         simCudaWindowPipelineOverlapEnabledRuntime();
}

static inline int longtarget_prepare_exact_sim_min_score(string &rnaSequence,
                                                         const string &transformedSequence,
                                                         ExactSimRunContext &runContext,
                                                         CalcScoreWorkspace &workspace,
                                                         ExactSimTaskTiming *taskTiming)
{
  const double thresholdStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  const int minScore = getExactReferenceMinScore(rnaSequence,
                                                 transformedSequence,
                                                 &runContext,
                                                 workspace);
  if(taskTiming != NULL)
  {
    taskTiming->thresholdSeconds += exact_sim_now_seconds() - thresholdStart;
  }
  return minScore;
}

static inline const char *longtarget_two_stage_threshold_mode_label(ExactSimTwoStageThresholdMode mode)
{
  return mode == EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_DEFERRED_EXACT ? "deferred_exact" : "legacy";
}

static inline const char *longtarget_two_stage_reject_mode_label(ExactSimTwoStageRejectMode mode)
{
  switch(mode)
  {
    case EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1:
      return "minimal_v1";
    case EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2:
      return "minimal_v2";
    case EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF:
    default:
      return "off";
  }
}

static inline const char *longtarget_two_stage_discovery_mode_label(ExactSimTwoStageDiscoveryMode mode)
{
  return exact_sim_two_stage_discovery_mode_label(mode);
}

static inline string longtarget_two_stage_debug_windows_csv_path_runtime()
{
  const char *env = getenv("LONGTARGET_TWO_STAGE_DEBUG_WINDOWS_CSV");
  if(env == NULL || env[0] == '\0')
  {
    return "";
  }
  return string(env);
}

static inline string longtarget_task_strand_label(long reverseMode,long parallelMode)
{
  if(reverseMode == 0 && parallelMode == 1)
  {
    return "ParaPlus";
  }
  if(reverseMode == 1 && parallelMode == 1)
  {
    return "ParaMinus";
  }
  if(reverseMode == 1 && parallelMode == -1)
  {
    return "AntiMinus";
  }
  if(reverseMode == 0 && parallelMode == -1)
  {
    return "AntiPlus";
  }
  return "";
}

static inline string longtarget_two_stage_task_rerun_task_key(const ExactSimTaskSpec &task,
                                                              size_t fragmentLength)
{
  const long fragmentStart = task.dnaStartPos + 1;
  const long fragmentEnd = task.dnaStartPos + static_cast<long>(fragmentLength);
  ostringstream out;
  out<<task.fragmentIndex<<"\t"
     <<fragmentStart<<"\t"
     <<fragmentEnd<<"\t"
     <<task.reverseMode<<"\t"
     <<task.parallelMode<<"\t"
     <<longtarget_task_strand_label(task.reverseMode,task.parallelMode)<<"\t"
     <<task.rule;
  return out.str();
}

static inline bool longtarget_load_two_stage_task_rerun_selected_task_keys(
  const string &path,
  unordered_set<string> &selectedTaskKeys,
  string *errorMessage = NULL)
{
  selectedTaskKeys.clear();
  if(path.empty())
  {
    return true;
  }

  ifstream in(path.c_str());
  if(!in.is_open())
  {
    if(errorMessage != NULL)
    {
      *errorMessage = "failed to open selected task list";
    }
    return false;
  }

  string line;
  size_t lineNumber = 0;
  while(getline(in,line))
  {
    ++lineNumber;
    if(!line.empty() && line[line.size() - 1] == '\r')
    {
      line.erase(line.size() - 1);
    }
    if(line.empty() || line[0] == '#')
    {
      continue;
    }
    if(line == "fragment_index\tfragment_start_in_seq\tfragment_end_in_seq\treverse_mode\tparallel_mode\tstrand\trule")
    {
      continue;
    }

    vector<string> columns;
    size_t start = 0;
    while(true)
    {
      const size_t pos = line.find('\t',start);
      if(pos == string::npos)
      {
        columns.push_back(line.substr(start));
        break;
      }
      columns.push_back(line.substr(start,pos - start));
      start = pos + 1;
    }
    if(columns.size() != 7)
    {
      if(errorMessage != NULL)
      {
        ostringstream out;
        out<<"invalid selected task line "<<lineNumber<<": expected 7 tab-separated columns";
        *errorMessage = out.str();
      }
      return false;
    }

    ostringstream normalized;
    normalized<<columns[0]<<"\t"
              <<columns[1]<<"\t"
              <<columns[2]<<"\t"
              <<columns[3]<<"\t"
              <<columns[4]<<"\t"
              <<columns[5]<<"\t"
              <<columns[6];
    selectedTaskKeys.insert(normalized.str());
  }
  return true;
}

static inline string longtarget_merge_prefilter_backend(const string &current,const string &next)
{
  if(next.empty())
  {
    return current;
  }
  if(current.empty())
  {
    return next;
  }
  if(current == next)
  {
    return current;
  }
  if(current == "disabled")
  {
    return next;
  }
  if(next == "disabled")
  {
    return current;
  }
  return "mixed";
}

static inline ExactSimTwoStageDiscoverySummary longtarget_build_two_stage_discovery_summary(
  size_t taskCount,
  uint64_t prefilterFailedTasks,
  const LongTargetExecutionMetrics &metrics)
{
  ExactSimTwoStageDiscoverySummary summary;
  summary.taskCount = static_cast<uint64_t>(taskCount);
  summary.prefilterFailedTasks = prefilterFailedTasks;
  summary.tasksWithAnySeed = metrics.twoStageTasksWithAnySeed;
  summary.tasksWithAnyRefineWindowBeforeGate = metrics.twoStageTasksWithAnyRefineWindowBeforeGate;
  summary.tasksWithAnyRefineWindowAfterGate = metrics.twoStageTasksWithAnyRefineWindowAfterGate;
  summary.windowsBeforeGate = metrics.twoStageWindowsBeforeGate;
  summary.windowsAfterGate = metrics.twoStageWindowsAfterGate;
  return summary;
}

static inline void longtarget_write_two_stage_window_trace_header(ostream &out)
{
  out<<"task_index\t"
     <<"fragment_index\t"
     <<"fragment_start_in_seq\t"
     <<"fragment_end_in_seq\t"
     <<"reverse_mode\t"
     <<"parallel_mode\t"
     <<"strand\t"
     <<"rule\t"
     <<"window_id\t"
     <<"sorted_rank\t"
     <<"window_start_in_fragment\t"
     <<"window_end_in_fragment\t"
     <<"window_start_in_seq\t"
     <<"window_end_in_seq\t"
     <<"best_seed_score\t"
     <<"second_best_seed_score\t"
     <<"margin\t"
     <<"support_count\t"
     <<"window_bp\t"
     <<"before_gate\t"
     <<"after_gate\t"
     <<"peak_score_ok\t"
     <<"support_ok\t"
     <<"margin_ok\t"
     <<"strong_score_ok\t"
     <<"selective_fallback_selected\t"
     <<"reject_reason"
     <<endl;
}

static inline void longtarget_write_two_stage_window_trace_row(ostream &out,
                                                               size_t taskIndex,
                                                               const ExactSimTaskSpec &task,
                                                               size_t fragmentLength,
                                                               const ExactSimTwoStageWindowTrace &trace)
{
  const long fragmentStart = task.dnaStartPos + 1;
  const long fragmentEnd = task.dnaStartPos + static_cast<long>(fragmentLength);
  const long windowStartInSeq = task.dnaStartPos + static_cast<long>(trace.window.startJ);
  const long windowEndInSeq = task.dnaStartPos + static_cast<long>(trace.window.endJ);
  const long margin = exact_sim_refine_window_margin(trace.window);
  out<<taskIndex<<"\t"
     <<task.fragmentIndex<<"\t"
     <<fragmentStart<<"\t"
     <<fragmentEnd<<"\t"
     <<task.reverseMode<<"\t"
     <<task.parallelMode<<"\t"
     <<longtarget_task_strand_label(task.reverseMode,task.parallelMode)<<"\t"
     <<task.rule<<"\t"
     <<trace.originalIndex<<"\t";
  if(trace.sortedRank == std::numeric_limits<size_t>::max())
  {
    out<<""<<"\t";
  }
  else
  {
    out<<trace.sortedRank<<"\t";
  }
  out<<trace.window.startJ<<"\t"
     <<trace.window.endJ<<"\t"
     <<windowStartInSeq<<"\t"
     <<windowEndInSeq<<"\t"
     <<trace.window.bestSeedScore<<"\t";
  if(trace.window.secondBestSeedScore == exact_sim_refine_window_missing_score())
  {
    out<<""<<"\t";
  }
  else
  {
    out<<trace.window.secondBestSeedScore<<"\t";
  }
  if(margin == exact_sim_refine_window_missing_score())
  {
    out<<""<<"\t";
  }
  else
  {
    out<<margin<<"\t";
  }
  out<<trace.window.supportCount<<"\t"
     <<exact_sim_refine_window_bp(trace.window)<<"\t"
     <<(trace.beforeGate ? 1 : 0)<<"\t"
     <<(trace.afterGate ? 1 : 0)<<"\t"
     <<(trace.peakScoreOk ? 1 : 0)<<"\t"
     <<(trace.supportOk ? 1 : 0)<<"\t"
     <<(trace.marginOk ? 1 : 0)<<"\t"
     <<(trace.strongScoreOk ? 1 : 0)<<"\t"
     <<(trace.selectiveFallbackSelected ? 1 : 0)<<"\t"
     <<exact_sim_two_stage_window_reject_reason_label(trace.rejectReason)
     <<endl;
}

static inline void longtarget_run_exact_sim_single_stage_with_min_score(string &rnaSequence,
                                                                        const ExactSimTaskSpec &task,
                                                                        const vector<ExactFragmentInfo> &fragments,
                                                                        int minScore,
                                                                        const ExactSimConfig &exactSimConfig,
                                                                        const struct para &paraList,
                                                                        vector<struct triplex> &triplexList,
                                                                        ExactSimTaskTiming *taskTiming,
                                                                        double *filterSecondsOut);

static inline bool longtarget_task_supports_window_pipeline(const string &rnaSequence,
                                                            const ExactSimTaskSpec &task,
                                                            int minScore)
{
  return !rnaSequence.empty() &&
         !task.transformedSequence.empty() &&
         rnaSequence.size() <= 8192u &&
         task.transformedSequence.size() <= 8192u &&
         minScore >= 0 &&
         minScore <= static_cast<int>(0x7fffffff);
}

static inline bool longtarget_flush_window_pipeline_batch(string &rnaSequence,
                                                          const vector<ExactSimTaskSpec> &tasks,
                                                          const vector<ExactFragmentInfo> &fragments,
                                                          const vector<LongTargetWindowPipelineTask> &batchTasks,
                                                          const ExactSimConfig &exactSimConfig,
                                                          const struct para &paraList,
                                                          vector< vector<struct triplex> > &taskTriplexLists,
                                                          vector<ExactSimTaskTiming> &taskTimings,
                                                          vector<double> &taskFilterSeconds);

static inline bool longtarget_prepare_window_pipeline_batch_gpu(string &rnaSequence,
                                                                const vector<ExactSimTaskSpec> &tasks,
                                                                const vector<LongTargetWindowPipelineTask> &batchTasks,
                                                                const ExactSimConfig &exactSimConfig,
                                                                LongTargetWindowPipelinePreparedBatch &preparedBatch);

static inline bool longtarget_execute_window_pipeline_batch_cpu(const vector<ExactSimTaskSpec> &tasks,
                                                                const vector<ExactFragmentInfo> &fragments,
                                                                const struct para &paraList,
                                                                LongTargetWindowPipelinePreparedBatch &preparedBatch,
                                                                vector< vector<struct triplex> > &taskTriplexLists,
                                                                vector<ExactSimTaskTiming> &taskTimings,
                                                                vector<double> &taskFilterSeconds);

struct lgInfo
{
  lgInfo(){};
  lgInfo(const string &s1,const string &s2,const string &s3,const string &s4,const string &s5,const string &s6,int s7,const string &s8):lncName(s1),lncSeq(s2),species(s3),dnaChroTag(s4),fileName(s5),dnaSeq(s6),startGenome(s7),resultDir(s8) {};
  string lncName;
  string lncSeq;
  string species;
  string dnaChroTag;
  string fileName;
  string dnaSeq;
  int startGenome;
  string resultDir;
};
struct para
{
  string file1path;
  string file2path;
  string outpath;
  int rule;
  int cutLength;
  int strand;
  int overlapLength;
  int minScore;
  bool detailOutput;
  int ntMin;
  int ntMax;
  float scoreMin;
  float minIdentity;
  float minStability;
  int penaltyT;
  int penaltyC;
  int cDistance;
  int cLength;
};
void cutSequence(string& seq, vector<string>& seqsVec, vector<int>& seqsStartPos, int& cutLength, int& overlapLength,int& cut_num);
void show_help();
void initEnv(int argc,char * const *argv,struct para &paraList);
void LongTarget(struct para &paraList,string rnaSequence,string dnaSequence,vector<struct triplex> &sort_triplex_list,LongTargetExecutionMetrics *metrics=NULL);
bool comp(const triplex &a, const triplex &b);
string getStrand(int reverse,int strand);
int same_seq(string &w_str);
void printResult(string &species,struct para paraList,string &lncName,string &dnaFile,vector<struct triplex> &sort_triplex_list,string &chroTag,string &dnaSequence,int start_genome,string &c_tmp_dd,string &c_tmp_length,string &resultDir);
string readDna(string dnaFileName,string &species,string &chroTag,string &startGenome);
string readRna(string rnaFileName,string &lncName);

static inline double longtarget_now_seconds()
{
  return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

static inline bool longtarget_benchmark_enabled()
{
  const char *benchmarkEnv = getenv("LONGTARGET_BENCHMARK");
  return benchmarkEnv != NULL && benchmarkEnv[0] != '\0' && strcmp(benchmarkEnv,"0") != 0;
}

static inline bool longtarget_progress_enabled()
{
  static const bool enabled = []()
  {
    const char *progressEnv = getenv("LONGTARGET_PROGRESS");
    return progressEnv != NULL && progressEnv[0] != '\0' && strcmp(progressEnv,"0") != 0;
  }();
  return enabled;
}

static inline bool longtarget_cuda_enabled()
{
  const char *cudaEnv = getenv("LONGTARGET_ENABLE_CUDA");
  return cudaEnv != NULL && cudaEnv[0] != '\0' && strcmp(cudaEnv,"0") != 0;
}

static inline int longtarget_cuda_device()
{
  const char *deviceEnv = getenv("LONGTARGET_CUDA_DEVICE");
  if(deviceEnv == NULL || deviceEnv[0] == '\0')
  {
    return -1;
  }
  return atoi(deviceEnv);
}

static inline bool longtarget_cuda_validate_enabled()
{
  const char *validateEnv = getenv("LONGTARGET_CUDA_VALIDATE");
  return validateEnv != NULL && validateEnv[0] != '\0' && strcmp(validateEnv,"0") != 0;
}

static inline bool longtarget_calc_score_cuda_pipeline_v2_enabled()
{
  const char *env = getenv("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

static inline bool longtarget_calc_score_cuda_pipeline_v2_shadow_enabled()
{
  if(!longtarget_calc_score_cuda_pipeline_v2_enabled())
  {
    return false;
  }
  const char *env = getenv("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

static inline bool longtarget_write_tfosorted_lite_enabled()
{
  const char *env = getenv("LONGTARGET_WRITE_TFOSORTED_LITE");
  return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
}

static inline vector<int> longtarget_cuda_devices_runtime()
{
  static const vector<int> devices = []()
  {
    vector<int> parsed;
    const char *env = getenv("LONGTARGET_CUDA_DEVICES");
    if(env == NULL || env[0] == '\0')
    {
      return parsed;
    }
    const string spec(env);
    const char *p = spec.c_str();
    while(*p != '\0')
    {
      while(*p == ' ' || *p == '\t' || *p == ',')
      {
        ++p;
      }
      if(*p == '\0')
      {
        break;
      }
      char *end = NULL;
      long v = strtol(p, &end, 10);
      if(end == p)
      {
        break;
      }
      if(v >= 0 && v <= 1024)
      {
        parsed.push_back(static_cast<int>(v));
      }
      p = end;
      while(*p != '\0' && *p != ',')
      {
        ++p;
      }
    }
    sort(parsed.begin(), parsed.end());
    parsed.erase(unique(parsed.begin(), parsed.end()), parsed.end());
    return parsed;
  }();
  return devices;
}

static inline vector<SimCudaWorkerAssignment> longtarget_cuda_worker_assignments_runtime()
{
  static const vector<SimCudaWorkerAssignment> assignments = []()
  {
    vector<int> devices = longtarget_cuda_devices_runtime();
    if(devices.empty())
    {
      const int singleDevice = longtarget_cuda_device();
      if(singleDevice >= 0)
      {
        devices.push_back(singleDevice);
      }
      else if(longtarget_cuda_enabled())
      {
        devices.push_back(0);
      }
    }
    return simBuildCudaWorkerAssignments(devices,
                                         simCudaWorkersPerDeviceRuntime());
  }();
  return assignments;
}

enum LongTargetOutputMode
{
  LONGTARGET_OUTPUT_FULL = 0,
  LONGTARGET_OUTPUT_TFOSORTED = 1,
  LONGTARGET_OUTPUT_LITE = 2,
};

static inline LongTargetOutputMode longtarget_output_mode_runtime()
{
  static const LongTargetOutputMode mode = []()
  {
    const char *env = getenv("LONGTARGET_OUTPUT_MODE");
    if(env == NULL || env[0] == '\0')
    {
      return LONGTARGET_OUTPUT_FULL;
    }
    string value(env);
    for(size_t i = 0; i < value.size(); ++i)
    {
      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
    }
    if(value == "tfosorted" || value == "tfo")
    {
      return LONGTARGET_OUTPUT_TFOSORTED;
    }
    if(value == "lite" || value == "tfosorted-lite" || value == "tfo-lite")
    {
      return LONGTARGET_OUTPUT_LITE;
    }
    if(value == "full")
    {
      return LONGTARGET_OUTPUT_FULL;
    }
    return LONGTARGET_OUTPUT_FULL;
  }();
  return mode;
}

static inline void appendExactSimTask(vector<ExactSimTaskSpec> &tasks,
                                      size_t fragmentIndex,
                                      const string &fragmentSequence,
                                      long dnaStartPos,
                                      long reverseMode,
                                      long parallelMode,
                                      int rule)
{
  string transformedSequence = transferString(fragmentSequence,reverseMode,parallelMode,rule);
  if(reverseMode == 1)
  {
    reverseSeq(transformedSequence);
  }
  tasks.push_back(ExactSimTaskSpec(fragmentIndex,dnaStartPos,reverseMode,parallelMode,rule,transformedSequence));
}

static inline void appendExactSimTaskRange(vector<ExactSimTaskSpec> &tasks,
                                           size_t fragmentIndex,
                                           const string &fragmentSequence,
                                           long dnaStartPos,
                                           long reverseMode,
                                           long parallelMode,
                                           int firstRule,
                                           int lastRule)
{
  for(int rule = firstRule; rule <= lastRule; ++rule)
  {
    appendExactSimTask(tasks,fragmentIndex,fragmentSequence,dnaStartPos,reverseMode,parallelMode,rule);
  }
}

static inline void filterTriplexListInPlace(vector<struct triplex> &triplexList,const struct para &paraList)
{
  size_t writeIndex = 0;
  for(size_t readIndex = 0; readIndex < triplexList.size(); ++readIndex)
  {
    const triplex &candidate = triplexList[readIndex];
    if(candidate.score>=paraList.scoreMin&&candidate.identity>=paraList.minIdentity&&candidate.tri_score>=paraList.minStability)
    {
      if(writeIndex != readIndex)
      {
        triplexList[writeIndex] = candidate;
      }
      ++writeIndex;
    }
  }
  triplexList.resize(writeIndex);
}

static inline void longtarget_run_exact_sim_single_stage_with_min_score(string &rnaSequence,
                                                                        const ExactSimTaskSpec &task,
                                                                        const vector<ExactFragmentInfo> &fragments,
                                                                        int minScore,
                                                                        const ExactSimConfig &exactSimConfig,
                                                                        const struct para &paraList,
                                                                        vector<struct triplex> &triplexList,
                                                                        ExactSimTaskTiming *taskTiming,
                                                                        double *filterSecondsOut)
{
  runExactReferenceSIMWithMinScore(rnaSequence,
                                   task.transformedSequence,
                                   fragments[task.fragmentIndex].sequence,
                                   task.dnaStartPos,
                                   task.reverseMode,
                                   task.parallelMode,
                                   task.rule,
                                   minScore,
                                   exactSimConfig,
                                   paraList.ntMin,
                                   paraList.ntMax,
                                   paraList.penaltyT,
                                   paraList.penaltyC,
                                   triplexList,
                                   taskTiming);
  const double filterStart = longtarget_now_seconds();
  filterTriplexListInPlace(triplexList,paraList);
  if(filterSecondsOut != NULL)
  {
    *filterSecondsOut = longtarget_now_seconds() - filterStart;
  }
}

static inline bool longtarget_prepare_window_pipeline_batch_gpu(string &rnaSequence,
                                                                const vector<ExactSimTaskSpec> &tasks,
                                                                const vector<LongTargetWindowPipelineTask> &batchTasks,
                                                                const ExactSimConfig &exactSimConfig,
                                                                LongTargetWindowPipelinePreparedBatch &preparedBatch)
{
  preparedBatch = LongTargetWindowPipelinePreparedBatch();
  preparedBatch.batchTasks = batchTasks;
  if(batchTasks.size() <= 1)
  {
    return false;
  }

  const size_t batchSize = batchTasks.size();
  const long M = static_cast<long>(rnaSequence.size());
  const long N = static_cast<long>(tasks[batchTasks[0].taskIndex].transformedSequence.size());
  if(M <= 0 || N <= 0)
  {
    return false;
  }

  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  const std::chrono::steady_clock::time_point gpuStageStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();

  preparedBatch.paddedQuery = ' ' + rnaSequence;
  preparedBatch.paddedTargets.assign(batchSize,string());
  preparedBatch.contexts.reserve(batchSize);
  preparedBatch.initialCpuPipelineStates.resize(batchSize);
  vector<LongTargetSimScoreMatrixInt> scoreMatrices(batchSize);
  vector<SimScanCudaInitialBatchRequest> cudaRequests(batchSize);
  const bool useInitialProposals = simCudaInitialProposalRequestEnabledRuntime();
  const bool useInitialReduce = simCudaInitialReduceRequestEnabledRuntime();
  const bool useInitialPinnedAsyncCpuPipeline =
    !useInitialReduce &&
    !useInitialProposals &&
    simCudaInitialChunkedHandoffEnabledRuntime() &&
    simCudaInitialPinnedAsyncHandoffEnabledRuntime() &&
    simCudaInitialPinnedAsyncCpuPipelineEnabledRuntime();

  for(size_t batchOffset = 0; batchOffset < batchSize; ++batchOffset)
  {
    const ExactSimTaskSpec &task = tasks[batchTasks[batchOffset].taskIndex];
    if(static_cast<long>(task.transformedSequence.size()) != N)
    {
      return false;
    }
    preparedBatch.paddedTargets[batchOffset] = ' ' + task.transformedSequence;
    preparedBatch.contexts.emplace_back(M,N);
    initializeSimKernel(exactSimConfig.matchScore,
                        exactSimConfig.mismatchScore,
                        exactSimConfig.gapOpen,
                        exactSimConfig.gapExtend,
                        preparedBatch.contexts.back());
    fillSimScoreMatrixInt(preparedBatch.contexts.back().scoreMatrix,scoreMatrices[batchOffset].value);

    SimScanCudaInitialBatchRequest &cudaRequest = cudaRequests[batchOffset];
    cudaRequest.A = preparedBatch.paddedQuery.c_str();
    cudaRequest.B = preparedBatch.paddedTargets[batchOffset].c_str();
    cudaRequest.queryLength = static_cast<int>(M);
    cudaRequest.targetLength = static_cast<int>(N);
    cudaRequest.gapOpen = static_cast<int>(preparedBatch.contexts.back().gapOpen);
    cudaRequest.gapExtend = static_cast<int>(preparedBatch.contexts.back().gapExtend);
    cudaRequest.scoreMatrix = scoreMatrices[batchOffset].value;
    cudaRequest.eventScoreFloor = batchTasks[batchOffset].minScore;
    cudaRequest.reduceCandidates = useInitialReduce;
    cudaRequest.proposalCandidates = useInitialProposals;
    cudaRequest.persistAllCandidateStatesOnDevice =
      simCudaInitialReducePersistOnDeviceRuntime() &&
      !simCudaInitialOrderedSegmentedV3ShadowEnabledRuntime();
    if(useInitialPinnedAsyncCpuPipeline)
    {
      SimKernelContext *pipelineContext = &preparedBatch.contexts.back();
      SimInitialPinnedAsyncCpuPipelineApplyState *pipelineState =
        &preparedBatch.initialCpuPipelineStates[batchOffset];
      cudaRequest.initialSummaryChunkConsumer =
        [pipelineContext,pipelineState](const SimScanCudaInitialSummaryChunk &chunk)
        {
          applySimInitialPinnedAsyncCpuPipelineChunk(chunk.summaries,
                                                    chunk.batchIndex,
                                                    chunk.chunkIndex,
                                                    chunk.summaryBase,
                                                    static_cast<size_t>(chunk.summaryCount),
                                                    *pipelineContext,
                                                    *pipelineState);
        };
    }
  }

  if(useInitialPinnedAsyncCpuPipeline)
  {
    const bool maintainSafeStore =
      simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET ||
      simCudaProposalLoopEnabledRuntime();
    for(size_t batchOffset = 0; batchOffset < batchSize; ++batchOffset)
    {
      beginSimInitialPinnedAsyncCpuPipelineApply(0,
                                                preparedBatch.contexts[batchOffset],
                                                maintainSafeStore,
                                                preparedBatch.initialCpuPipelineStates[batchOffset]);
    }
  }

  preparedBatch.usedInitialReduce = useInitialReduce;
  preparedBatch.usedInitialProposals = useInitialProposals;
  preparedBatch.usedInitialPinnedAsyncCpuPipeline = useInitialPinnedAsyncCpuPipeline;
  string cudaError;
  if(!(sim_scan_cuda_init(simCudaDeviceRuntime(),&cudaError) &&
       sim_scan_cuda_enumerate_initial_events_row_major_true_batch(cudaRequests,
                                                                   &preparedBatch.cudaResults,
                                                                   &preparedBatch.cudaBatchResult,
                                                                   &cudaError) &&
       preparedBatch.cudaResults.size() == batchSize))
  {
    return false;
  }

  if(benchmarkEnabled)
  {
    preparedBatch.gpuStageNanoseconds = simElapsedNanoseconds(gpuStageStart);
  }
  preparedBatch.valid = true;
  return true;
}

static inline bool longtarget_execute_window_pipeline_batch_cpu(const vector<ExactSimTaskSpec> &tasks,
                                                                const vector<ExactFragmentInfo> &fragments,
                                                                const struct para &paraList,
                                                                LongTargetWindowPipelinePreparedBatch &preparedBatch,
                                                                vector< vector<struct triplex> > &taskTriplexLists,
                                                                vector<ExactSimTaskTiming> &taskTimings,
                                                                vector<double> &taskFilterSeconds)
{
  if(!preparedBatch.valid || preparedBatch.batchTasks.empty() || preparedBatch.cudaResults.size() != preparedBatch.batchTasks.size())
  {
    return false;
  }

  const size_t batchSize = preparedBatch.batchTasks.size();
  const long N = static_cast<long>(tasks[preparedBatch.batchTasks[0].taskIndex].transformedSequence.size());
  if(N <= 0)
  {
    return false;
  }

  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  uint64_t cpuApplyNanoseconds = 0;
  const std::chrono::steady_clock::time_point cpuApplyStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();

  if(benchmarkEnabled)
  {
    recordSimInitialScanGpuNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.gpuSeconds));
    recordSimInitialScanD2HNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.d2hSeconds));
    recordSimInitialScanDiagNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialDiagSeconds));
    recordSimInitialScanOnlineReduceNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialOnlineReduceSeconds));
    recordSimInitialScanWaitNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialWaitSeconds));
    recordSimInitialScanCountCopyNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialCountCopySeconds));
    recordSimInitialScanBaseUploadNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialBaseUploadSeconds));
    recordSimInitialProposalSelectD2HNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialProposalSelectD2HSeconds));
    recordSimInitialScanSyncWaitNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSyncWaitSeconds));
    recordSimInitialScanTailNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialScanTailSeconds));
    recordSimInitialHashReduceNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialHashReduceSeconds));
    recordSimInitialSegmentedReduceNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSegmentedReduceSeconds));
    recordSimInitialSegmentedCompactNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSegmentedCompactSeconds));
    recordSimInitialTopKNanoseconds(
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialTopKSeconds));
    recordSimInitialSegmentedStateStats(preparedBatch.cudaBatchResult.initialSegmentedTileStateCount,
                                        preparedBatch.cudaBatchResult.initialSegmentedGroupedStateCount);
    recordSimInitialSummaryPackedD2H(
      preparedBatch.cudaBatchResult.usedInitialPackedSummaryD2H,
      preparedBatch.cudaBatchResult.initialSummaryPackedBytesD2H,
      preparedBatch.cudaBatchResult.initialSummaryUnpackedEquivalentBytesD2H,
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSummaryPackSeconds),
      preparedBatch.cudaBatchResult.initialSummaryPackedD2HFallbacks);
    recordSimInitialSummaryHostCopyElision(
      preparedBatch.cudaBatchResult.usedInitialSummaryHostCopyElision,
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSummaryD2HCopySeconds),
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSummaryUnpackSeconds),
      simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialSummaryResultMaterializeSeconds),
      preparedBatch.cudaBatchResult.initialSummaryHostCopyElidedBytes);
    recordSimInitialPinnedAsyncHandoffStats(preparedBatch.cudaBatchResult);
    if(!preparedBatch.usedInitialReduce &&
       !preparedBatch.usedInitialProposals &&
       simCudaInitialChunkedHandoffEnabledRuntime())
    {
      recordSimInitialChunkedHandoffTransferNanoseconds(
        simSecondsToNanoseconds(preparedBatch.cudaBatchResult.d2hSeconds),
        0,
        0);
    }
  }
  recordSimInitialScanBackend(true,
                              preparedBatch.cudaBatchResult.taskCount,
                              preparedBatch.cudaBatchResult.launchCount);
  recordSimWindowPipelineBatch(static_cast<uint64_t>(batchSize));
  if(preparedBatch.usedInitialReduce)
  {
    recordSimInitialReduceReplayStats(preparedBatch.cudaBatchResult.initialReduceReplayStats);
  }
  if(preparedBatch.usedInitialProposals)
  {
    recordSimProposalGpuNanoseconds(simSecondsToNanoseconds(preparedBatch.cudaBatchResult.proposalSelectGpuSeconds));
    if(preparedBatch.cudaBatchResult.usedInitialProposalV2Path)
    {
      recordSimInitialProposalV2(1,preparedBatch.cudaBatchResult.initialProposalV2RequestCount);
    }
    if(preparedBatch.cudaBatchResult.usedInitialProposalV2DirectTopKPath)
    {
      recordSimInitialProposalDirectTopK(1,
                                         preparedBatch.cudaBatchResult.initialProposalLogicalCandidateCount,
                                         preparedBatch.cudaBatchResult.initialProposalMaterializedCandidateCount,
                                         simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialProposalDirectTopKGpuSeconds));
    }
    if(preparedBatch.cudaBatchResult.usedInitialProposalV3Path)
    {
      recordSimInitialProposalV3(1,
                                 preparedBatch.cudaBatchResult.initialProposalV3RequestCount,
                                 preparedBatch.cudaBatchResult.initialProposalV3SelectedStateCount,
                                 simSecondsToNanoseconds(preparedBatch.cudaBatchResult.initialProposalV3GpuSeconds));
    }
  }

  for(size_t batchOffset = 0; batchOffset < batchSize; ++batchOffset)
  {
    SimScanCudaInitialBatchResult &result = preparedBatch.cudaResults[batchOffset];
    recordSimInitialEvents(result.eventCount);
    recordSimInitialRunSummaries(result.runSummaryCount);
    if(preparedBatch.usedInitialReduce || preparedBatch.usedInitialProposals)
    {
      recordSimInitialAllCandidateStates(result.allCandidateStateCount);
      recordSimInitialStoreBytesD2H((preparedBatch.usedInitialProposals ||
                                     result.persistentSafeStoreHandle.valid) ?
                                    0 :
                                    (static_cast<uint64_t>(result.allCandidateStates.size()) *
                                     static_cast<uint64_t>(sizeof(SimScanCudaCandidateState))));
      if(preparedBatch.usedInitialReduce)
      {
        recordSimInitialReducedCandidates(static_cast<uint64_t>(result.candidateStates.size()));
        if(simCudaInitialExactFrontierReplayEnabledRuntime())
        {
          recordSimInitialExactFrontierReplay(
            static_cast<uint64_t>(result.candidateStates.size()),
            result.persistentSafeStoreHandle.valid);
        }
        runSimCudaInitialOrderedSegmentedV3ShadowIfEnabled(result.initialRunSummaries,
                                                           result.candidateStates,
                                                           result.runningMin,
                                                           result.allCandidateStates);
      }
      else
      {
        recordSimProposalAllCandidateStates(result.allCandidateStateCount);
        recordSimProposalBytesD2H(static_cast<uint64_t>(result.candidateStates.size()) *
                                  static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
        recordSimProposalSelected(static_cast<uint64_t>(result.candidateStates.size()));
      }
      applySimCudaInitialReduceResults(result.candidateStates,
                                       result.runningMin,
                                       result.allCandidateStates,
                                       result.persistentSafeStoreHandle,
                                       result.eventCount,
                                       preparedBatch.contexts[batchOffset],
                                       benchmarkEnabled,
                                       preparedBatch.usedInitialProposals);
    }
    else
    {
      const uint64_t summaryBytesD2H =
        static_cast<uint64_t>(result.initialRunSummaries.size()) *
        (preparedBatch.cudaBatchResult.usedInitialPackedSummaryD2H ?
         static_cast<uint64_t>(sizeof(SimScanCudaPackedInitialRunSummary16)) :
         static_cast<uint64_t>(sizeof(SimScanCudaInitialRunSummary)));
      recordSimInitialSummaryBytesD2H(summaryBytesD2H);
      if(preparedBatch.usedInitialPinnedAsyncCpuPipeline &&
         preparedBatch.cudaBatchResult.initialHandoffCpuPipelineActive)
      {
        preparedBatch.initialCpuPipelineStates[batchOffset].logicalEventCount =
          result.eventCount;
        if(preparedBatch.contexts[batchOffset].statsEnabled &&
           !preparedBatch.initialCpuPipelineStates[batchOffset].eventsSeenRecorded)
        {
          preparedBatch.contexts[batchOffset].stats.eventsSeen += result.eventCount;
          preparedBatch.initialCpuPipelineStates[batchOffset].eventsSeenRecorded = true;
        }
        finalizeSimInitialPinnedAsyncCpuPipelineApply(
          preparedBatch.contexts[batchOffset],
          preparedBatch.initialCpuPipelineStates[batchOffset],
          false);
        preparedBatch.cudaBatchResult.initialHandoffCpuPipelineChunksFinalized +=
          preparedBatch.initialCpuPipelineStates[batchOffset].chunksFinalized;
        preparedBatch.cudaBatchResult.initialHandoffCpuPipelineFinalizeCount +=
          preparedBatch.initialCpuPipelineStates[batchOffset].finalizeCount;
        preparedBatch.cudaBatchResult.initialHandoffCpuPipelineOutOfOrderChunks +=
          preparedBatch.initialCpuPipelineStates[batchOffset].outOfOrderChunks;
        if(benchmarkEnabled)
        {
          recordSimInitialPinnedAsyncCpuPipelineFinalizeStats(
            preparedBatch.initialCpuPipelineStates[batchOffset]);
        }
        finalizeSimCudaInitialRunSummariesToContext(result.initialRunSummaries,
                                                    preparedBatch.contexts[batchOffset],
                                                    benchmarkEnabled,
                                                    true);
      }
      else
      {
        applySimCudaInitialRunSummariesToContext(result.initialRunSummaries,
                                                 result.eventCount,
                                                 preparedBatch.contexts[batchOffset],
                                                 benchmarkEnabled);
      }
    }
  }

  if(benchmarkEnabled)
  {
    cpuApplyNanoseconds = simElapsedNanoseconds(cpuApplyStart);
    recordSimInitialScanNanoseconds(preparedBatch.gpuStageNanoseconds + cpuApplyNanoseconds);
  }
  const double sharedInitialSeconds =
    batchSize > 0 ? static_cast<double>(preparedBatch.gpuStageNanoseconds + cpuApplyNanoseconds) /
                    1.0e9 / static_cast<double>(batchSize) : 0.0;

  for(size_t batchOffset = 0; batchOffset < batchSize; ++batchOffset)
  {
    const LongTargetWindowPipelineTask &batchTask = preparedBatch.batchTasks[batchOffset];
    const ExactSimTaskSpec &task = tasks[batchTask.taskIndex];
    const string &sourceSequence = fragments[task.fragmentIndex].sequence;
    SimRequest request(sourceSequence,
                       task.dnaStartPos,
                       batchTask.minScore,
                       task.reverseMode,
                       task.parallelMode,
                       paraList.ntMin,
                       paraList.ntMax,
                       paraList.penaltyT,
                       paraList.penaltyC);

    recordSimSolverBackend(SIM_SOLVER_BACKEND_CUDA_WINDOW_PIPELINE);
    taskTimings[batchTask.taskIndex].simSeconds += sharedInitialSeconds;

    const double simStart = exact_sim_now_seconds();
    runSimCandidateLoop(request,
                        preparedBatch.paddedQuery.c_str(),
                        preparedBatch.paddedTargets[batchOffset].c_str(),
                        N,
                        task.rule,
                        preparedBatch.contexts[batchOffset],
                        taskTriplexLists[batchTask.taskIndex]);
    taskTimings[batchTask.taskIndex].simSeconds += exact_sim_now_seconds() - simStart;

    const double filterStart = longtarget_now_seconds();
    filterTriplexListInPlace(taskTriplexLists[batchTask.taskIndex],paraList);
    taskFilterSeconds[batchTask.taskIndex] = longtarget_now_seconds() - filterStart;
  }
  return true;
}

static inline bool longtarget_flush_window_pipeline_batch(string &rnaSequence,
                                                          const vector<ExactSimTaskSpec> &tasks,
                                                          const vector<ExactFragmentInfo> &fragments,
                                                          const vector<LongTargetWindowPipelineTask> &batchTasks,
                                                          const ExactSimConfig &exactSimConfig,
                                                          const struct para &paraList,
                                                          vector< vector<struct triplex> > &taskTriplexLists,
                                                          vector<ExactSimTaskTiming> &taskTimings,
                                                          vector<double> &taskFilterSeconds)
{
  LongTargetWindowPipelinePreparedBatch preparedBatch;
  if(!longtarget_prepare_window_pipeline_batch_gpu(rnaSequence,
                                                   tasks,
                                                   batchTasks,
                                                   exactSimConfig,
                                                   preparedBatch))
  {
    return false;
  }
  return longtarget_execute_window_pipeline_batch_cpu(tasks,
                                                      fragments,
                                                      paraList,
                                                      preparedBatch,
                                                      taskTriplexLists,
                                                      taskTimings,
                                                      taskFilterSeconds);
}

static inline void finalizeLongTargetCudaWorkerMetrics(const vector<SimCudaWorkerAssignment> &assignments,
                                                       const vector<int> &taskWorkerIndices,
                                                       const vector<ExactSimTaskTiming> &taskTimings,
                                                       const vector<double> &taskFilterSeconds,
                                                       LongTargetExecutionMetrics *metrics)
{
  if(metrics == NULL)
  {
    return;
  }

  metrics->simCudaWorkers.assign(assignments.size(),LongTargetCudaWorkerMetrics());
  metrics->simCudaDevices.clear();

  map<int,size_t> deviceMetricIndices;
  for(size_t workerIndex = 0; workerIndex < assignments.size(); ++workerIndex)
  {
    LongTargetCudaWorkerMetrics &workerMetrics = metrics->simCudaWorkers[workerIndex];
    workerMetrics.device = assignments[workerIndex].device;
    workerMetrics.slot = assignments[workerIndex].slot;

    map<int,size_t>::iterator existingDevice = deviceMetricIndices.find(assignments[workerIndex].device);
    if(existingDevice == deviceMetricIndices.end())
    {
      const size_t deviceMetricIndex = metrics->simCudaDevices.size();
      deviceMetricIndices.insert(make_pair(assignments[workerIndex].device,deviceMetricIndex));
      metrics->simCudaDevices.push_back(LongTargetCudaDeviceMetrics());
      metrics->simCudaDevices.back().device = assignments[workerIndex].device;
      existingDevice = deviceMetricIndices.find(assignments[workerIndex].device);
    }
    metrics->simCudaDevices[existingDevice->second].workerCount += 1;
  }

  for(size_t taskIndex = 0; taskIndex < taskWorkerIndices.size(); ++taskIndex)
  {
    const int workerIndex = taskWorkerIndices[taskIndex];
    if(workerIndex < 0 || static_cast<size_t>(workerIndex) >= metrics->simCudaWorkers.size())
    {
      continue;
    }

    LongTargetCudaWorkerMetrics &workerMetrics = metrics->simCudaWorkers[static_cast<size_t>(workerIndex)];
    workerMetrics.taskCount += 1;
    workerMetrics.thresholdSeconds += taskTimings[taskIndex].thresholdSeconds;
    workerMetrics.simSeconds += taskTimings[taskIndex].simSeconds;
    workerMetrics.filterSeconds += taskFilterSeconds[taskIndex];

    const size_t deviceMetricIndex = deviceMetricIndices[workerMetrics.device];
    LongTargetCudaDeviceMetrics &deviceMetrics = metrics->simCudaDevices[deviceMetricIndex];
    deviceMetrics.taskCount += 1;
    deviceMetrics.thresholdSeconds += taskTimings[taskIndex].thresholdSeconds;
    deviceMetrics.simSeconds += taskTimings[taskIndex].simSeconds;
    deviceMetrics.filterSeconds += taskFilterSeconds[taskIndex];
  }
}

static inline void printLongTargetBenchmarkMetrics(const LongTargetExecutionMetrics &metrics)
{
  uint64_t simSolverCpuCalls = 0;
  uint64_t simSolverCudaFullExactCalls = 0;
  uint64_t simSolverCudaWindowPipelineCalls = 0;
  getSimSolverBackendCounts(simSolverCpuCalls,
                            simSolverCudaFullExactCalls,
                            simSolverCudaWindowPipelineCalls);
  string simSolverBackend = "cpu";
  const int simSolverBackendModes =
    (simSolverCpuCalls > 0 ? 1 : 0) +
    (simSolverCudaFullExactCalls > 0 ? 1 : 0) +
    (simSolverCudaWindowPipelineCalls > 0 ? 1 : 0);
  if(simSolverBackendModes > 1)
  {
    simSolverBackend = "mixed";
  }
  else if(simSolverCudaWindowPipelineCalls > 0)
  {
    simSolverBackend = "cuda_window_pipeline";
  }
  else if(simSolverCudaFullExactCalls > 0)
  {
    simSolverBackend = "cuda_full_exact";
  }
  cerr<<"benchmark.sim_solver_backend="<<simSolverBackend<<endl;
  uint64_t simWindowPipelineBatches = 0;
  uint64_t simWindowPipelineTasksBatched = 0;
  uint64_t simWindowPipelineTaskFallbacks = 0;
  getSimWindowPipelineStats(simWindowPipelineBatches,
                            simWindowPipelineTasksBatched,
                            simWindowPipelineTaskFallbacks);
  uint64_t simWindowPipelineTasksConsidered = 0;
  uint64_t simWindowPipelineTasksEligible = 0;
  uint64_t simWindowPipelineIneligibleTwoStage = 0;
  uint64_t simWindowPipelineIneligibleSimFast = 0;
  uint64_t simWindowPipelineIneligibleValidate = 0;
  uint64_t simWindowPipelineIneligibleRuntimeDisabled = 0;
  uint64_t simWindowPipelineIneligibleQueryGt8192 = 0;
  uint64_t simWindowPipelineIneligibleTargetGt8192 = 0;
  uint64_t simWindowPipelineIneligibleNegativeMinScore = 0;
  uint64_t simWindowPipelineBatchRuntimeFallbacks = 0;
  getSimWindowPipelineEligibilityStats(simWindowPipelineTasksConsidered,
                                       simWindowPipelineTasksEligible,
                                       simWindowPipelineIneligibleTwoStage,
                                       simWindowPipelineIneligibleSimFast,
                                       simWindowPipelineIneligibleValidate,
                                       simWindowPipelineIneligibleRuntimeDisabled,
                                       simWindowPipelineIneligibleQueryGt8192,
                                       simWindowPipelineIneligibleTargetGt8192,
                                       simWindowPipelineIneligibleNegativeMinScore,
                                       simWindowPipelineBatchRuntimeFallbacks);
  cerr<<"benchmark.sim_window_pipeline_batches="<<simWindowPipelineBatches<<endl;
  cerr<<"benchmark.sim_window_pipeline_tasks_batched="<<simWindowPipelineTasksBatched<<endl;
  cerr<<"benchmark.sim_window_pipeline_task_fallbacks="<<simWindowPipelineTaskFallbacks<<endl;
  cerr<<"benchmark.sim_window_pipeline_tasks_considered="<<simWindowPipelineTasksConsidered<<endl;
  cerr<<"benchmark.sim_window_pipeline_tasks_eligible="<<simWindowPipelineTasksEligible<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_two_stage="<<simWindowPipelineIneligibleTwoStage<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_sim_fast="<<simWindowPipelineIneligibleSimFast<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_validate="<<simWindowPipelineIneligibleValidate<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_runtime_disabled="<<simWindowPipelineIneligibleRuntimeDisabled<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_query_gt_8192="<<simWindowPipelineIneligibleQueryGt8192<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_target_gt_8192="<<simWindowPipelineIneligibleTargetGt8192<<endl;
  cerr<<"benchmark.sim_window_pipeline_ineligible_negative_min_score="<<simWindowPipelineIneligibleNegativeMinScore<<endl;
  cerr<<"benchmark.sim_window_pipeline_batch_runtime_fallbacks="<<simWindowPipelineBatchRuntimeFallbacks<<endl;
  cerr<<"benchmark.sim_window_pipeline_overlap_enabled="
      <<(simCudaWindowPipelineOverlapEnabledRuntime() ? 1 : 0)
      <<endl;
  cerr<<"benchmark.sim_window_pipeline_overlap_batches="
      <<getSimWindowPipelineOverlapBatchCount()
      <<endl;

  uint64_t simInitialCpuCalls = 0;
  uint64_t simInitialCudaCalls = 0;
  getSimInitialScanBackendCounts(simInitialCpuCalls,simInitialCudaCalls);
  string simInitialBackend = "cpu";
  if(simInitialCudaCalls > 0)
  {
    simInitialBackend = (simInitialCpuCalls == 0) ? "cuda" : "mixed";
  }
  cerr<<"benchmark.sim_initial_backend="<<simInitialBackend<<endl;
  cerr<<"benchmark.sim_initial_reduce_backend="<<longtargetSimInitialReduceBackendLabel()<<endl;
  cerr<<"benchmark.sim_initial_replay_authority="<<longtargetSimInitialReplayAuthorityLabel()<<endl;
  cerr<<"benchmark.sim_initial_residency_mode="
      <<(simCudaMainlineResidencyEnabledRuntime() ? 1 : 0)
      <<endl;
  cerr<<"benchmark.sim_proposal_backend="
      <<(simCudaProposalLoopEnabledRuntime() ? "cuda" : "off")
      <<endl;

  uint64_t simRegionCpuCalls = 0;
  uint64_t simRegionCudaCalls = 0;
  getSimRegionScanBackendCounts(simRegionCpuCalls,simRegionCudaCalls);
  string simRegionBackend = "cpu";
  if(simRegionCudaCalls > 0)
  {
    simRegionBackend = (simRegionCpuCalls == 0) ? "cuda" : "mixed";
  }
  cerr<<"benchmark.sim_region_backend="<<simRegionBackend<<endl;
  uint64_t simRegionCalls = 0;
  uint64_t simRegionRequests = 0;
  uint64_t simRegionLaunches = 0;
  uint64_t simRegionBatchCalls = 0;
  uint64_t simRegionBatchRequests = 0;
  uint64_t simRegionSerialFallbackRequests = 0;
  getSimRegionScanTelemetryStats(simRegionCalls,
                                 simRegionRequests,
                                 simRegionLaunches,
                                 simRegionBatchCalls,
                                 simRegionBatchRequests,
                                 simRegionSerialFallbackRequests);
  cerr<<"benchmark.sim_region_calls="<<simRegionCalls<<endl;
  cerr<<"benchmark.sim_region_requests="<<simRegionRequests<<endl;
  cerr<<"benchmark.sim_region_launches="<<simRegionLaunches<<endl;
  cerr<<"benchmark.sim_region_batch_calls="<<simRegionBatchCalls<<endl;
  cerr<<"benchmark.sim_region_batch_requests="<<simRegionBatchRequests<<endl;
  cerr<<"benchmark.sim_region_serial_fallback_requests="
      <<simRegionSerialFallbackRequests<<endl;

  uint64_t simLocateCpuCalls = 0;
  uint64_t simLocateCudaCalls = 0;
  getSimLocateBackendCounts(simLocateCpuCalls,simLocateCudaCalls);
  string simLocateBackend = "cpu";
  if(simLocateCudaCalls > 0)
  {
    simLocateBackend = (simLocateCpuCalls == 0) ? "cuda" : "mixed";
  }
  cerr<<"benchmark.sim_locate_backend="<<simLocateBackend<<endl;
  uint64_t simLocateExactCalls = 0;
  uint64_t simLocateFastCalls = 0;
  uint64_t simLocateSafeWorksetCalls = 0;
  uint64_t simLocateFastFallbacks = 0;
  getSimLocateModeCounts(simLocateExactCalls,
                         simLocateFastCalls,
                         simLocateSafeWorksetCalls,
                         simLocateFastFallbacks);
  string simLocateMode = "exact";
  const bool sawLocateExact = simLocateExactCalls > 0;
  const bool sawLocateFast = simLocateFastCalls > 0 || simLocateFastFallbacks > 0;
  const bool sawLocateSafeWorkset = simLocateSafeWorksetCalls > 0;
  const int locateModeVariants =
    (sawLocateExact ? 1 : 0) +
    (sawLocateFast ? 1 : 0) +
    (sawLocateSafeWorkset ? 1 : 0);
  if(locateModeVariants > 1)
  {
    simLocateMode = "mixed";
  }
  else if(sawLocateSafeWorkset)
  {
    simLocateMode = "safe_workset";
  }
  else if(sawLocateFast)
  {
    simLocateMode = (simLocateFastFallbacks == 0) ? "fast" : "mixed";
  }
  cerr<<"benchmark.sim_locate_mode="<<simLocateMode<<endl;
  cerr<<"benchmark.sim_locate_fast_passes="<<simLocateFastCalls<<endl;
  cerr<<"benchmark.sim_locate_fast_fallbacks="<<simLocateFastFallbacks<<endl;
  uint64_t simLocateBatchCalls = 0;
  uint64_t simLocateBatchRequests = 0;
  uint64_t simLocateBatchSharedInputRequests = 0;
  uint64_t simLocateBatchSerialFallbackRequests = 0;
  uint64_t simLocateBatchLaunches = 0;
  getSimLocateBatchTelemetryStats(simLocateBatchCalls,
                                  simLocateBatchRequests,
                                  simLocateBatchSharedInputRequests,
                                  simLocateBatchSerialFallbackRequests,
                                  simLocateBatchLaunches);
  cerr<<"benchmark.sim_locate_batch_calls="<<simLocateBatchCalls<<endl;
  cerr<<"benchmark.sim_locate_batch_requests="<<simLocateBatchRequests<<endl;
  cerr<<"benchmark.sim_locate_batch_shared_input_requests="
      <<simLocateBatchSharedInputRequests<<endl;
  cerr<<"benchmark.sim_locate_batch_serial_fallback_requests="
      <<simLocateBatchSerialFallbackRequests<<endl;
  cerr<<"benchmark.sim_locate_batch_launches="<<simLocateBatchLaunches<<endl;
  uint64_t simSafeWorksetPassCount = 0;
  uint64_t simSafeWorksetFallbackInvalidStoreCount = 0;
  uint64_t simSafeWorksetFallbackNoAffectedStartCount = 0;
  uint64_t simSafeWorksetFallbackNoWorksetCount = 0;
  uint64_t simSafeWorksetFallbackInvalidBandsCount = 0;
  uint64_t simSafeWorksetFallbackScanFailureCount = 0;
  uint64_t simSafeWorksetFallbackShadowMismatchCount = 0;
  getSimSafeWorksetStats(simSafeWorksetPassCount,
                         simSafeWorksetFallbackInvalidStoreCount,
                         simSafeWorksetFallbackNoAffectedStartCount,
                         simSafeWorksetFallbackNoWorksetCount,
                         simSafeWorksetFallbackInvalidBandsCount,
                         simSafeWorksetFallbackScanFailureCount,
                         simSafeWorksetFallbackShadowMismatchCount);
  cerr<<"benchmark.sim_safe_workset_passes="<<simSafeWorksetPassCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_invalid_store="<<simSafeWorksetFallbackInvalidStoreCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_no_affected_start="<<simSafeWorksetFallbackNoAffectedStartCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_no_workset="<<simSafeWorksetFallbackNoWorksetCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_invalid_bands="<<simSafeWorksetFallbackInvalidBandsCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_scan_failure="<<simSafeWorksetFallbackScanFailureCount<<endl;
  cerr<<"benchmark.sim_safe_workset_fallback_shadow_mismatch="<<simSafeWorksetFallbackShadowMismatchCount<<endl;
  uint64_t simSafeWorksetAffectedStartCount = 0;
  uint64_t simSafeWorksetUniqueAffectedStartCount = 0;
  uint64_t simSafeWorksetInputBandCount = 0;
  uint64_t simSafeWorksetInputCellCount = 0;
  uint64_t simSafeWorksetExecBandCount = 0;
  uint64_t simSafeWorksetExecCellCount = 0;
  uint64_t simSafeWorksetCudaTaskCount = 0;
  uint64_t simSafeWorksetCudaLaunchCount = 0;
  uint64_t simSafeWorksetReturnedStateCount = 0;
  uint64_t simSafeWorksetBuildNanoseconds = 0;
  uint64_t simSafeWorksetMergeNanoseconds = 0;
  uint64_t simSafeWorksetTotalNanoseconds = 0;
  getSimSafeWorksetExecutionStats(simSafeWorksetAffectedStartCount,
                                  simSafeWorksetUniqueAffectedStartCount,
                                  simSafeWorksetInputBandCount,
                                  simSafeWorksetInputCellCount,
                                  simSafeWorksetExecBandCount,
                                  simSafeWorksetExecCellCount,
                                  simSafeWorksetCudaTaskCount,
                                  simSafeWorksetCudaLaunchCount,
                                  simSafeWorksetReturnedStateCount);
  getSimSafeWorksetTimingStats(simSafeWorksetBuildNanoseconds,
                               simSafeWorksetMergeNanoseconds,
                               simSafeWorksetTotalNanoseconds);
  const SimSafeWorksetMergeBreakdownStats simSafeWorksetMergeBreakdown =
    getSimSafeWorksetMergeBreakdownStats();
  const SimSafeStoreMergeStructureShadowStats simSafeStoreMergeStructureShadow =
    getSimSafeStoreMergeStructureShadowStats();
  cerr<<"benchmark.sim_safe_workset_affected_starts="<<simSafeWorksetAffectedStartCount<<endl;
  cerr<<"benchmark.sim_safe_workset_unique_affected_starts="<<simSafeWorksetUniqueAffectedStartCount<<endl;
  cerr<<"benchmark.sim_safe_workset_input_bands="<<simSafeWorksetInputBandCount<<endl;
  cerr<<"benchmark.sim_safe_workset_input_cells="<<simSafeWorksetInputCellCount<<endl;
  cerr<<"benchmark.sim_safe_workset_exec_bands="<<simSafeWorksetExecBandCount<<endl;
  cerr<<"benchmark.sim_safe_workset_exec_cells="<<simSafeWorksetExecCellCount<<endl;
  cerr<<"benchmark.sim_safe_workset_cuda_tasks="<<simSafeWorksetCudaTaskCount<<endl;
  cerr<<"benchmark.sim_safe_workset_cuda_launches="<<simSafeWorksetCudaLaunchCount<<endl;
  cerr<<"benchmark.sim_safe_workset_cuda_true_batch_requests="<<getSimSafeWorksetCudaTrueBatchRequestCount()<<endl;
  cerr<<"benchmark.sim_safe_workset_returned_states="<<simSafeWorksetReturnedStateCount<<endl;
  cerr<<"benchmark.sim_safe_workset_build_seconds="<<(static_cast<double>(simSafeWorksetBuildNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_seconds="<<(static_cast<double>(simSafeWorksetMergeNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_total_seconds="<<(static_cast<double>(simSafeWorksetTotalNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_materialize_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_MATERIALIZE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_candidate_erase_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_CANDIDATE_ERASE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_upsert_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPSERT_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_erase_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_ERASE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_upsert_loop_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPSERT_LOOP_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_candidate_apply_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_CANDIDATE_APPLY_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_prune_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_PRUNE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_upload_seconds="
      <<(static_cast<double>(simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPLOAD_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_unique_start_keys="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_UNIQUE_START_KEY_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_duplicate_states="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_DUPLICATE_STATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_candidate_updates="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_CANDIDATE_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_updates="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_residency_updates="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_RESIDENCY_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_affected_start_keys="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_AFFECTED_START_KEY_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_size_before="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_BEFORE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_size_after_erase="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_ERASE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_size_after_upsert="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_UPSERT_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_safe_store_size_after_prune="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_PRUNE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_prune_scanned_states="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_PRUNE_SCANNED_STATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_prune_removed_states="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_PRUNE_REMOVED_STATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_workset_merge_prune_kept_states="
      <<simSafeWorksetMergeBreakdown.get(SIM_SAFE_WORKSET_MERGE_PRUNE_KEPT_STATE_COUNT)<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_enabled="
      <<(simSafeStoreMergeStructureShadowEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_calls="
      <<simSafeStoreMergeStructureShadow.calls<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_seconds="
      <<(static_cast<double>(simSafeStoreMergeStructureShadow.nanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_digest_mismatches="
      <<simSafeStoreMergeStructureShadow.digestMismatches<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_size_mismatches="
      <<simSafeStoreMergeStructureShadow.sizeMismatches<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_candidate_mismatches="
      <<simSafeStoreMergeStructureShadow.candidateMismatches<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_order_mismatches="
      <<simSafeStoreMergeStructureShadow.orderMismatches<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_est_current_scanned_states="
      <<simSafeStoreMergeStructureShadow.estCurrentScannedStates<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_est_compact_scanned_states="
      <<simSafeStoreMergeStructureShadow.estCompactScannedStates<<endl;
  cerr<<"benchmark.sim_safe_store_merge_shadow_est_saved_scans="
      <<simSafeStoreMergeStructureShadow.estSavedScans<<endl;
  const double simSafeStoreMergeStructureShadowPruneRemovedRatio =
    simSafeStoreMergeStructureShadow.pruneScannedStates == 0
      ? 0.0
      : static_cast<double>(simSafeStoreMergeStructureShadow.pruneRemovedStates) /
        static_cast<double>(simSafeStoreMergeStructureShadow.pruneScannedStates);
  cerr<<"benchmark.sim_safe_store_merge_shadow_prune_removed_ratio="
      <<simSafeStoreMergeStructureShadowPruneRemovedRatio<<endl;
  cerr<<"benchmark.sim_safe_workset_builder_calls_after_safe_window="
      <<getSimSafeWorksetBuilderCallsAfterSafeWindow()<<endl;
  uint64_t simSafeStoreRefreshAttemptCount = 0;
  uint64_t simSafeStoreRefreshSuccessCount = 0;
  uint64_t simSafeStoreRefreshFailureCount = 0;
  uint64_t simSafeStoreRefreshTrackedStartCount = 0;
  uint64_t simSafeStoreRefreshGpuNanoseconds = 0;
  uint64_t simSafeStoreRefreshD2hNanoseconds = 0;
  uint64_t simSafeStoreInvalidatedAfterExactFallbackCount = 0;
  uint64_t simFrontierCacheInvalidateProposalEraseCount = 0;
	  uint64_t simFrontierCacheInvalidateStoreUpdateCount = 0;
	  uint64_t simFrontierCacheInvalidateReleaseOrErrorCount = 0;
	  uint64_t simFrontierCacheRebuildFromResidencyCount = 0;
	  uint64_t simFrontierCacheRebuildFromHostFinalCandidatesCount = 0;
	  uint64_t simInitialSafeStoreHandoffCreatedCount = 0;
	  uint64_t simInitialSafeStoreHandoffAvailableForLocateCount = 0;
	  uint64_t simInitialSafeStoreHandoffHostStoreEvictedCount = 0;
	  uint64_t simInitialSafeStoreHandoffHostMergeSkippedCount = 0;
	  uint64_t simInitialSafeStoreHandoffHostMergeFallbackCount = 0;
	  uint64_t simInitialSafeStoreHandoffRejectedFastShadowCount = 0;
	  uint64_t simInitialSafeStoreHandoffRejectedProposalLoopCount = 0;
	  uint64_t simInitialSafeStoreHandoffRejectedMissingGpuStoreCount = 0;
	  uint64_t simInitialSafeStoreHandoffRejectedStaleEpochCount = 0;
  getSimSafeStoreRefreshStats(simSafeStoreRefreshAttemptCount,
                              simSafeStoreRefreshSuccessCount,
                              simSafeStoreRefreshFailureCount,
                              simSafeStoreRefreshTrackedStartCount,
                              simSafeStoreRefreshGpuNanoseconds,
                              simSafeStoreRefreshD2hNanoseconds,
                              simSafeStoreInvalidatedAfterExactFallbackCount);
	  getSimFrontierCacheTransitionStats(simFrontierCacheInvalidateProposalEraseCount,
	                                     simFrontierCacheInvalidateStoreUpdateCount,
	                                     simFrontierCacheInvalidateReleaseOrErrorCount,
	                                     simFrontierCacheRebuildFromResidencyCount,
	                                     simFrontierCacheRebuildFromHostFinalCandidatesCount);
	  getSimInitialSafeStoreHandoffCompositionStats(
	    simInitialSafeStoreHandoffCreatedCount,
	    simInitialSafeStoreHandoffAvailableForLocateCount,
	    simInitialSafeStoreHandoffHostStoreEvictedCount,
	    simInitialSafeStoreHandoffHostMergeSkippedCount,
	    simInitialSafeStoreHandoffHostMergeFallbackCount,
	    simInitialSafeStoreHandoffRejectedFastShadowCount,
	    simInitialSafeStoreHandoffRejectedProposalLoopCount,
	    simInitialSafeStoreHandoffRejectedMissingGpuStoreCount,
	    simInitialSafeStoreHandoffRejectedStaleEpochCount);
  cerr<<"benchmark.sim_safe_store_refresh_attempts="<<simSafeStoreRefreshAttemptCount<<endl;
  cerr<<"benchmark.sim_safe_store_refresh_success="<<simSafeStoreRefreshSuccessCount<<endl;
  cerr<<"benchmark.sim_safe_store_refresh_failures="<<simSafeStoreRefreshFailureCount<<endl;
  cerr<<"benchmark.sim_safe_store_refresh_tracked_starts="<<simSafeStoreRefreshTrackedStartCount<<endl;
  cerr<<"benchmark.sim_safe_store_refresh_gpu_seconds="
      <<(static_cast<double>(simSafeStoreRefreshGpuNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_store_refresh_d2h_seconds="
      <<(static_cast<double>(simSafeStoreRefreshD2hNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_store_invalidated_after_exact_fallback="
      <<simSafeStoreInvalidatedAfterExactFallbackCount<<endl;
  cerr<<"benchmark.sim_frontier_invalidate_proposal_erase="
      <<simFrontierCacheInvalidateProposalEraseCount<<endl;
  cerr<<"benchmark.sim_frontier_invalidate_store_update="
      <<simFrontierCacheInvalidateStoreUpdateCount<<endl;
  cerr<<"benchmark.sim_frontier_invalidate_release_or_error="
      <<simFrontierCacheInvalidateReleaseOrErrorCount<<endl;
  cerr<<"benchmark.sim_frontier_rebuild_from_residency="
      <<simFrontierCacheRebuildFromResidencyCount<<endl;
	  cerr<<"benchmark.sim_frontier_rebuild_from_host_final_candidates="
	      <<simFrontierCacheRebuildFromHostFinalCandidatesCount<<endl;
	  const char *simInitialSafeStoreHandoffEnv =
	    getenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
	  if(simInitialSafeStoreHandoffEnv == NULL ||
	     simInitialSafeStoreHandoffEnv[0] == '\0')
	  {
	    simInitialSafeStoreHandoffEnv =
	      getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");
	  }
	  cerr<<"benchmark.sim_initial_safe_store_handoff_enabled="
	      <<((simInitialSafeStoreHandoffEnv != NULL &&
	          simInitialSafeStoreHandoffEnv[0] != '\0' &&
	          strcmp(simInitialSafeStoreHandoffEnv,"0") != 0) ? 1 : 0)<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_created="
	      <<simInitialSafeStoreHandoffCreatedCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_available_for_locate="
	      <<simInitialSafeStoreHandoffAvailableForLocateCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_host_store_evicted="
	      <<simInitialSafeStoreHandoffHostStoreEvictedCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_host_merge_skipped="
	      <<simInitialSafeStoreHandoffHostMergeSkippedCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_host_merge_fallbacks="
	      <<simInitialSafeStoreHandoffHostMergeFallbackCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_rejected_fast_shadow="
	      <<simInitialSafeStoreHandoffRejectedFastShadowCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_rejected_proposal_loop="
	      <<simInitialSafeStoreHandoffRejectedProposalLoopCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_rejected_missing_gpu_store="
	      <<simInitialSafeStoreHandoffRejectedMissingGpuStoreCount<<endl;
	  cerr<<"benchmark.sim_initial_safe_store_handoff_rejected_stale_epoch="
	      <<simInitialSafeStoreHandoffRejectedStaleEpochCount<<endl;
	  uint64_t simSafeWindowCount = 0;
  uint64_t simSafeWindowAffectedStartCount = 0;
  uint64_t simSafeWindowCoordBytesD2H = 0;
  uint64_t simSafeWindowFallbackCount = 0;
  uint64_t simSafeWindowGpuNanoseconds = 0;
  uint64_t simSafeWindowD2hNanoseconds = 0;
  uint64_t simSafeWindowExecBandCount = 0;
  uint64_t simSafeWindowExecCellCount = 0;
  uint64_t simSafeWindowRawCellCount = 0;
  uint64_t simSafeWindowRawMaxWindowCellCount = 0;
  uint64_t simSafeWindowExecMaxBandCellCount = 0;
  uint64_t simSafeWindowCoarseningInflatedCellCount = 0;
  uint64_t simSafeWindowSparseV2ConsideredCount = 0;
  uint64_t simSafeWindowSparseV2SelectedCount = 0;
  uint64_t simSafeWindowSparseV2RejectedCount = 0;
  uint64_t simSafeWindowSparseV2SavedCellCount = 0;
  uint64_t simSafeWindowPlanBandCount = 0;
  uint64_t simSafeWindowPlanCellCount = 0;
  uint64_t simSafeWindowPlanGpuNanoseconds = 0;
  uint64_t simSafeWindowPlanD2hNanoseconds = 0;
  uint64_t simSafeWindowPlanFallbackCount = 0;
	  uint64_t simSafeWindowPlanBetterThanBuilderCount = 0;
	  uint64_t simSafeWindowPlanWorseThanBuilderCount = 0;
	  uint64_t simSafeWindowPlanEqualToBuilderCount = 0;
	  uint64_t simSafeWindowFineShadowCallCount = 0;
	  uint64_t simSafeWindowFineShadowMismatchCount = 0;
	  uint64_t simSafeWindowAttemptCount = 0;
  uint64_t simSafeWindowSkippedUnconvertibleCount = 0;
  uint64_t simSafeWindowSelectedWorksetCount = 0;
  uint64_t simSafeWindowAppliedCount = 0;
  uint64_t simSafeWindowGpuBuilderFallbackCount = 0;
  uint64_t simSafeWindowGpuBuilderPassCount = 0;
  uint64_t simSafeWindowExactFallbackCount = 0;
  uint64_t simSafeWindowExactFallbackNoUpdateRegionCount = 0;
  uint64_t simSafeWindowExactFallbackRefreshSuccessCount = 0;
  uint64_t simSafeWindowExactFallbackRefreshFailureCount = 0;
  uint64_t simSafeWindowExactFallbackBaseNoUpdateCount = 0;
  uint64_t simSafeWindowExactFallbackExpansionNoUpdateCount = 0;
  uint64_t simSafeWindowExactFallbackStopNoCrossCount = 0;
  uint64_t simSafeWindowExactFallbackStopBoundaryCount = 0;
  uint64_t simSafeWindowExactFallbackBaseCellCount = 0;
  uint64_t simSafeWindowExactFallbackExpansionCellCount = 0;
  uint64_t simSafeWindowExactFallbackLocateGpuNanoseconds = 0;
  uint64_t simSafeWindowStoreInvalidationCount = 0;
  uint64_t simSafeWindowFallbackSelectorErrorCount = 0;
  uint64_t simSafeWindowFallbackOverflowCount = 0;
  uint64_t simSafeWindowFallbackEmptySelectionCount = 0;
  getSimSafeWindowStats(simSafeWindowCount,
                        simSafeWindowAffectedStartCount,
                        simSafeWindowCoordBytesD2H,
                        simSafeWindowFallbackCount,
                        simSafeWindowGpuNanoseconds,
                        simSafeWindowD2hNanoseconds);
  getSimSafeWindowExecutionStats(simSafeWindowExecBandCount,
                                 simSafeWindowExecCellCount);
  getSimSafeWindowGeometryTelemetryStats(simSafeWindowRawCellCount,
                                         simSafeWindowRawMaxWindowCellCount,
                                         simSafeWindowExecMaxBandCellCount,
                                         simSafeWindowCoarseningInflatedCellCount,
                                         simSafeWindowSparseV2ConsideredCount,
                                         simSafeWindowSparseV2SelectedCount,
                                         simSafeWindowSparseV2RejectedCount,
                                         simSafeWindowSparseV2SavedCellCount);
  getSimSafeWindowPlanStats(simSafeWindowPlanBandCount,
                            simSafeWindowPlanCellCount,
                            simSafeWindowPlanGpuNanoseconds,
                            simSafeWindowPlanD2hNanoseconds,
                            simSafeWindowPlanFallbackCount);
	  getSimSafeWindowPlanComparisonStats(simSafeWindowPlanBetterThanBuilderCount,
	                                      simSafeWindowPlanWorseThanBuilderCount,
	                                      simSafeWindowPlanEqualToBuilderCount);
	  getSimSafeWindowFineShadowStats(simSafeWindowFineShadowCallCount,
	                                  simSafeWindowFineShadowMismatchCount);
	  getSimSafeWindowPathStats(simSafeWindowAttemptCount,
                            simSafeWindowSkippedUnconvertibleCount,
                            simSafeWindowSelectedWorksetCount,
                            simSafeWindowAppliedCount,
                            simSafeWindowGpuBuilderFallbackCount,
                            simSafeWindowGpuBuilderPassCount,
                            simSafeWindowExactFallbackCount,
                            simSafeWindowStoreInvalidationCount);
  getSimSafeWindowExactFallbackOutcomeStats(simSafeWindowExactFallbackNoUpdateRegionCount,
                                            simSafeWindowExactFallbackRefreshSuccessCount,
                                            simSafeWindowExactFallbackRefreshFailureCount);
  getSimSafeWindowExactFallbackPrecheckStats(simSafeWindowExactFallbackBaseNoUpdateCount,
                                             simSafeWindowExactFallbackExpansionNoUpdateCount,
                                             simSafeWindowExactFallbackStopNoCrossCount,
                                             simSafeWindowExactFallbackStopBoundaryCount,
                                             simSafeWindowExactFallbackBaseCellCount,
                                             simSafeWindowExactFallbackExpansionCellCount,
                                             simSafeWindowExactFallbackLocateGpuNanoseconds);
  getSimSafeWindowFallbackReasonStats(simSafeWindowFallbackSelectorErrorCount,
                                      simSafeWindowFallbackOverflowCount,
                                      simSafeWindowFallbackEmptySelectionCount);
	  cerr<<"benchmark.sim_safe_window_planner_mode="
	      <<simSafeWindowCudaPlannerModeName(simSafeWindowCudaPlannerModeRuntime())<<endl;
	  cerr<<"benchmark.sim_safe_window_exec_geometry="
	      <<simSafeWindowExecGeometryName(simSafeWindowExecGeometryRuntime())<<endl;
  cerr<<"benchmark.sim_safe_window_attempts="<<simSafeWindowAttemptCount<<endl;
  cerr<<"benchmark.sim_safe_window_skipped_unconvertible="<<simSafeWindowSkippedUnconvertibleCount<<endl;
  cerr<<"benchmark.sim_safe_window_selected_worksets="<<simSafeWindowSelectedWorksetCount<<endl;
  cerr<<"benchmark.sim_safe_window_applied="<<simSafeWindowAppliedCount<<endl;
  cerr<<"benchmark.sim_safe_window_gpu_builder_fallbacks="<<simSafeWindowGpuBuilderFallbackCount<<endl;
  cerr<<"benchmark.sim_safe_window_gpu_builder_passes="<<simSafeWindowGpuBuilderPassCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallbacks="<<simSafeWindowExactFallbackCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_no_update_region="
      <<simSafeWindowExactFallbackNoUpdateRegionCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_refresh_success="
      <<simSafeWindowExactFallbackRefreshSuccessCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_refresh_failure="
      <<simSafeWindowExactFallbackRefreshFailureCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_base_no_update="
      <<simSafeWindowExactFallbackBaseNoUpdateCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_expansion_no_update="
      <<simSafeWindowExactFallbackExpansionNoUpdateCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_stop_no_cross="
      <<simSafeWindowExactFallbackStopNoCrossCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_stop_boundary="
      <<simSafeWindowExactFallbackStopBoundaryCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_base_cells="
      <<simSafeWindowExactFallbackBaseCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_expansion_cells="
      <<simSafeWindowExactFallbackExpansionCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_exact_fallback_locate_gpu_seconds="
      <<(static_cast<double>(simSafeWindowExactFallbackLocateGpuNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_window_store_invalidations="<<simSafeWindowStoreInvalidationCount<<endl;
  cerr<<"benchmark.sim_safe_window_count="<<simSafeWindowCount<<endl;
  cerr<<"benchmark.sim_safe_window_affected_starts="<<simSafeWindowAffectedStartCount<<endl;
  cerr<<"benchmark.sim_safe_window_coord_bytes_d2h="<<simSafeWindowCoordBytesD2H<<endl;
  cerr<<"benchmark.sim_safe_window_fallbacks="<<simSafeWindowFallbackCount<<endl;
  cerr<<"benchmark.sim_safe_window_fallback_selector_error="<<simSafeWindowFallbackSelectorErrorCount<<endl;
  cerr<<"benchmark.sim_safe_window_fallback_overflow="<<simSafeWindowFallbackOverflowCount<<endl;
  cerr<<"benchmark.sim_safe_window_fallback_empty_selection="<<simSafeWindowFallbackEmptySelectionCount<<endl;
  cerr<<"benchmark.sim_safe_window_gpu_seconds="<<(static_cast<double>(simSafeWindowGpuNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_window_d2h_seconds="<<(static_cast<double>(simSafeWindowD2hNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_window_exec_bands="<<simSafeWindowExecBandCount<<endl;
  cerr<<"benchmark.sim_safe_window_exec_cells="<<simSafeWindowExecCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_raw_cells="<<simSafeWindowRawCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_raw_max_window_cells="<<simSafeWindowRawMaxWindowCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_exec_max_band_cells="<<simSafeWindowExecMaxBandCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_coarsening_inflated_cells="
      <<simSafeWindowCoarseningInflatedCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_sparse_v2_considered="
      <<simSafeWindowSparseV2ConsideredCount<<endl;
  cerr<<"benchmark.sim_safe_window_sparse_v2_selected="
      <<simSafeWindowSparseV2SelectedCount<<endl;
  cerr<<"benchmark.sim_safe_window_sparse_v2_rejected="
      <<simSafeWindowSparseV2RejectedCount<<endl;
  cerr<<"benchmark.sim_safe_window_sparse_v2_saved_cells="
      <<simSafeWindowSparseV2SavedCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_plan_bands="<<simSafeWindowPlanBandCount<<endl;
  cerr<<"benchmark.sim_safe_window_plan_cells="<<simSafeWindowPlanCellCount<<endl;
  cerr<<"benchmark.sim_safe_window_plan_gpu_seconds="
      <<(static_cast<double>(simSafeWindowPlanGpuNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_window_plan_d2h_seconds="
      <<(static_cast<double>(simSafeWindowPlanD2hNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_safe_window_plan_fallbacks="<<simSafeWindowPlanFallbackCount<<endl;
  cerr<<"benchmark.sim_safe_window_plan_better_than_builder="
      <<simSafeWindowPlanBetterThanBuilderCount<<endl;
  cerr<<"benchmark.sim_safe_window_plan_worse_than_builder="
      <<simSafeWindowPlanWorseThanBuilderCount<<endl;
	  cerr<<"benchmark.sim_safe_window_plan_equal_to_builder="
	      <<simSafeWindowPlanEqualToBuilderCount<<endl;
	  cerr<<"benchmark.sim_safe_window_fine_shadow_calls="
	      <<simSafeWindowFineShadowCallCount<<endl;
	  cerr<<"benchmark.sim_safe_window_fine_shadow_mismatches="
	      <<simSafeWindowFineShadowMismatchCount<<endl;
	  uint64_t simFastWorksetBandCount = 0;
  uint64_t simFastWorksetCellCount = 0;
  uint64_t simFastSegmentCount = 0;
  uint64_t simFastDiagonalSegmentCount = 0;
  uint64_t simFastHorizontalSegmentCount = 0;
  uint64_t simFastVerticalSegmentCount = 0;
  uint64_t simFastFallbackNoWorksetCount = 0;
  uint64_t simFastFallbackAreaCapCount = 0;
  uint64_t simFastFallbackShadowRunningMinCount = 0;
  uint64_t simFastFallbackShadowCandidateCountCount = 0;
  uint64_t simFastFallbackShadowCandidateValueCount = 0;
  getSimFastPathStats(simFastWorksetBandCount,
                      simFastWorksetCellCount,
                      simFastSegmentCount,
                      simFastDiagonalSegmentCount,
                      simFastHorizontalSegmentCount,
                      simFastVerticalSegmentCount,
                      simFastFallbackNoWorksetCount,
                      simFastFallbackAreaCapCount,
                      simFastFallbackShadowRunningMinCount,
                      simFastFallbackShadowCandidateCountCount,
                      simFastFallbackShadowCandidateValueCount);
  cerr<<"benchmark.sim_fast_workset_bands="<<simFastWorksetBandCount<<endl;
  cerr<<"benchmark.sim_fast_workset_cells="<<simFastWorksetCellCount<<endl;
  cerr<<"benchmark.sim_fast_segments="<<simFastSegmentCount<<endl;
  cerr<<"benchmark.sim_fast_diagonal_segments="<<simFastDiagonalSegmentCount<<endl;
  cerr<<"benchmark.sim_fast_horizontal_segments="<<simFastHorizontalSegmentCount<<endl;
  cerr<<"benchmark.sim_fast_vertical_segments="<<simFastVerticalSegmentCount<<endl;
  cerr<<"benchmark.sim_fast_fallback_no_workset="<<simFastFallbackNoWorksetCount<<endl;
  cerr<<"benchmark.sim_fast_fallback_area_cap="<<simFastFallbackAreaCapCount<<endl;
  cerr<<"benchmark.sim_fast_fallback_shadow_running_min="<<simFastFallbackShadowRunningMinCount<<endl;
  cerr<<"benchmark.sim_fast_fallback_shadow_candidate_count="<<simFastFallbackShadowCandidateCountCount<<endl;
  cerr<<"benchmark.sim_fast_fallback_shadow_candidate_value="<<simFastFallbackShadowCandidateValueCount<<endl;

  uint64_t simTracebackCpuCalls = 0;
  uint64_t simTracebackCudaCalls = 0;
  getSimTracebackBackendCounts(simTracebackCpuCalls,simTracebackCudaCalls);
  string simTracebackBackend = "cpu";
  if(simTracebackCudaCalls > 0)
  {
    simTracebackBackend = (simTracebackCpuCalls == 0) ? "cuda" : "mixed";
  }
  cerr<<"benchmark.sim_traceback_backend="<<simTracebackBackend<<endl;
  cerr<<"benchmark.sim_cuda_worker_count="<<metrics.simCudaWorkers.size()<<endl;
  cerr<<"benchmark.sim_cuda_device_count="<<metrics.simCudaDevices.size()<<endl;
  for(size_t workerIndex = 0; workerIndex < metrics.simCudaWorkers.size(); ++workerIndex)
  {
    const LongTargetCudaWorkerMetrics &workerMetrics = metrics.simCudaWorkers[workerIndex];
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_device="<<workerMetrics.device<<endl;
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_slot="<<workerMetrics.slot<<endl;
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_tasks="<<workerMetrics.taskCount<<endl;
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_threshold_seconds="<<workerMetrics.thresholdSeconds<<endl;
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_sim_seconds="<<workerMetrics.simSeconds<<endl;
    cerr<<"benchmark.sim_cuda_worker_"<<workerIndex<<"_filter_seconds="<<workerMetrics.filterSeconds<<endl;
  }
  for(size_t deviceIndex = 0; deviceIndex < metrics.simCudaDevices.size(); ++deviceIndex)
  {
    const LongTargetCudaDeviceMetrics &deviceMetrics = metrics.simCudaDevices[deviceIndex];
    cerr<<"benchmark.sim_cuda_device_"<<deviceMetrics.device<<"_workers="<<deviceMetrics.workerCount<<endl;
    cerr<<"benchmark.sim_cuda_device_"<<deviceMetrics.device<<"_tasks="<<deviceMetrics.taskCount<<endl;
    cerr<<"benchmark.sim_cuda_device_"<<deviceMetrics.device<<"_threshold_seconds="<<deviceMetrics.thresholdSeconds<<endl;
    cerr<<"benchmark.sim_cuda_device_"<<deviceMetrics.device<<"_sim_seconds="<<deviceMetrics.simSeconds<<endl;
    cerr<<"benchmark.sim_cuda_device_"<<deviceMetrics.device<<"_filter_seconds="<<deviceMetrics.filterSeconds<<endl;
  }

  cerr<<"benchmark.prefilter_backend="<<metrics.prefilterBackend<<endl;
  cerr<<"benchmark.prefilter_hits="<<metrics.prefilterHits<<endl;
  cerr<<"benchmark.two_stage_threshold_mode="<<metrics.twoStageThresholdMode<<endl;
  cerr<<"benchmark.two_stage_reject_mode="<<metrics.twoStageRejectMode<<endl;
  cerr<<"benchmark.two_stage_tasks_with_any_seed="<<metrics.twoStageTasksWithAnySeed<<endl;
  cerr<<"benchmark.two_stage_tasks_with_any_refine_window_before_gate="<<metrics.twoStageTasksWithAnyRefineWindowBeforeGate<<endl;
  cerr<<"benchmark.two_stage_tasks_with_any_refine_window_after_gate="<<metrics.twoStageTasksWithAnyRefineWindowAfterGate<<endl;
  cerr<<"benchmark.two_stage_threshold_invoked_tasks="<<metrics.twoStageThresholdInvokedTasks<<endl;
  cerr<<"benchmark.two_stage_threshold_skipped_no_seed_tasks="<<metrics.twoStageThresholdSkippedNoSeedTasks<<endl;
  cerr<<"benchmark.two_stage_threshold_skipped_no_refine_window_tasks="<<metrics.twoStageThresholdSkippedNoRefineWindowTasks<<endl;
  cerr<<"benchmark.two_stage_threshold_skipped_after_gate_tasks="<<metrics.twoStageThresholdSkippedAfterGateTasks<<endl;
  cerr<<"benchmark.two_stage_threshold_batch_count="<<metrics.twoStageThresholdBatchCount<<endl;
  cerr<<"benchmark.two_stage_threshold_batch_tasks_total="<<metrics.twoStageThresholdBatchTasksTotal<<endl;
  cerr<<"benchmark.two_stage_threshold_batch_size_max="<<metrics.twoStageThresholdBatchSizeMax<<endl;
  cerr<<"benchmark.two_stage_threshold_batched_seconds="<<metrics.twoStageThresholdBatchedSeconds<<endl;
  cerr<<"benchmark.two_stage_windows_before_gate="<<metrics.twoStageWindowsBeforeGate<<endl;
  cerr<<"benchmark.two_stage_windows_after_gate="<<metrics.twoStageWindowsAfterGate<<endl;
  cerr<<"benchmark.two_stage_windows_rejected_by_min_peak_score="<<metrics.twoStageWindowsRejectedByMinPeakScore<<endl;
  cerr<<"benchmark.two_stage_windows_rejected_by_support="<<metrics.twoStageWindowsRejectedBySupport<<endl;
  cerr<<"benchmark.two_stage_windows_rejected_by_margin="<<metrics.twoStageWindowsRejectedByMargin<<endl;
  cerr<<"benchmark.two_stage_windows_trimmed_by_max_windows="<<metrics.twoStageWindowsTrimmedByMaxWindows<<endl;
  cerr<<"benchmark.two_stage_windows_trimmed_by_max_bp="<<metrics.twoStageWindowsTrimmedByMaxBp<<endl;
  cerr<<"benchmark.two_stage_singleton_rescued_windows="<<metrics.twoStageSingletonRescuedWindows<<endl;
  cerr<<"benchmark.two_stage_singleton_rescued_tasks="<<metrics.twoStageSingletonRescuedTasks<<endl;
  cerr<<"benchmark.two_stage_singleton_rescue_bp_total="<<metrics.twoStageSingletonRescueBpTotal<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_enabled="<<metrics.twoStageSelectiveFallbackEnabled<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_triggered_tasks="<<metrics.twoStageSelectiveFallbackTriggeredTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_candidate_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyCandidateTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_rejected_by_max_kept_windows_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_rejected_by_singleton_override_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyRejectedBySingletonOverrideTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_rejected_as_covered_by_kept_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_rejected_by_score_gap_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyRejectedByScoreGapTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_non_empty_triggered_tasks="<<metrics.twoStageSelectiveFallbackNonEmptyTriggeredTasks<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_selected_windows="<<metrics.twoStageSelectiveFallbackSelectedWindows<<endl;
  cerr<<"benchmark.two_stage_selective_fallback_selected_bp_total="<<metrics.twoStageSelectiveFallbackSelectedBpTotal<<endl;
  cerr<<"benchmark.two_stage_task_rerun_enabled="<<metrics.twoStageTaskRerunEnabled<<endl;
  cerr<<"benchmark.two_stage_task_rerun_budget="<<metrics.twoStageTaskRerunBudget<<endl;
  cerr<<"benchmark.two_stage_task_rerun_selected_tasks="<<metrics.twoStageTaskRerunSelectedTasks<<endl;
  cerr<<"benchmark.two_stage_task_rerun_effective_tasks="<<metrics.twoStageTaskRerunEffectiveTasks<<endl;
  cerr<<"benchmark.two_stage_task_rerun_added_windows="<<metrics.twoStageTaskRerunAddedWindows<<endl;
  cerr<<"benchmark.two_stage_task_rerun_refine_bp_total="<<metrics.twoStageTaskRerunRefineBpTotal<<endl;
  cerr<<"benchmark.two_stage_task_rerun_seconds="<<metrics.twoStageTaskRerunSeconds<<endl;
  cerr<<"benchmark.two_stage_task_rerun_selected_tasks_path="<<metrics.twoStageTaskRerunSelectedTasksPath<<endl;
  cerr<<"benchmark.refine_window_count="<<metrics.refineWindowCount<<endl;
  cerr<<"benchmark.refine_total_bp="<<metrics.refineTotalBp<<endl;
  cerr<<"benchmark.sim_scan_tasks="<<metrics.simScanTasks<<endl;
  cerr<<"benchmark.sim_scan_launches="<<metrics.simScanLaunches<<endl;
  cerr<<"benchmark.sim_traceback_candidates="<<metrics.simTracebackCandidates<<endl;
  const double simTracebackTieRate =
    metrics.simTracebackCandidates > 0 ? static_cast<double>(metrics.simTracebackTieCount) / static_cast<double>(metrics.simTracebackCandidates) : 0.0;
  cerr<<"benchmark.sim_traceback_tie_rate="<<simTracebackTieRate<<endl;
  uint64_t simGpuIterations = 0;
  uint64_t simGpuFullRescans = 0;
  uint64_t simGpuBlockedDiagonals = 0;
  getSimCudaFullExactStats(simGpuIterations,simGpuFullRescans,simGpuBlockedDiagonals);
  cerr<<"benchmark.sim_gpu_iterations="<<simGpuIterations<<endl;
  cerr<<"benchmark.sim_gpu_full_rescans="<<simGpuFullRescans<<endl;
  cerr<<"benchmark.sim_gpu_blocked_diagonals="<<simGpuBlockedDiagonals<<endl;
  uint64_t simBlockedPackWords = 0;
  uint64_t simBlockedMirrorBytes = 0;
  getSimBlockedMirrorStats(simBlockedPackWords,simBlockedMirrorBytes);
  cerr<<"benchmark.sim_blocked_pack_words="<<simBlockedPackWords<<endl;
  cerr<<"benchmark.sim_blocked_mirror_bytes="<<simBlockedMirrorBytes<<endl;
  uint64_t simRegionTotalCells = 0;
  uint64_t simTracebackTotalCells = 0;
  getSimWorkCellStats(simRegionTotalCells,simTracebackTotalCells);
  cerr<<"benchmark.sim_region_total_cells="<<simRegionTotalCells<<endl;
  cerr<<"benchmark.sim_traceback_total_cells="<<simTracebackTotalCells<<endl;
  uint64_t simRegionEventsTotal = 0;
  uint64_t simRegionCandidateSummariesTotal = 0;
  uint64_t simRegionEventBytesD2H = 0;
  uint64_t simRegionSummaryBytesD2H = 0;
  double simRegionCpuMergeSeconds = 0.0;
  uint64_t simLocateTotalCells = 0;
  getSimRegionReductionStats(simRegionEventsTotal,
                             simRegionCandidateSummariesTotal,
                             simRegionEventBytesD2H,
                             simRegionSummaryBytesD2H,
                             simRegionCpuMergeSeconds,
                             simLocateTotalCells);
  cerr<<"benchmark.sim_region_events_total="<<simRegionEventsTotal<<endl;
  cerr<<"benchmark.sim_region_candidate_summaries_total="<<simRegionCandidateSummariesTotal<<endl;
  cerr<<"benchmark.sim_region_event_bytes_d2h="<<simRegionEventBytesD2H<<endl;
  cerr<<"benchmark.sim_region_summary_bytes_d2h="<<simRegionSummaryBytesD2H<<endl;
  cerr<<"benchmark.sim_region_cpu_merge_seconds="<<simRegionCpuMergeSeconds<<endl;
  cerr<<"benchmark.sim_locate_total_cells="<<simLocateTotalCells<<endl;
  uint64_t simInitialEventsTotal = 0;
  uint64_t simInitialRunSummariesTotal = 0;
  uint64_t simInitialSummaryBytesD2H = 0;
  uint64_t simInitialReducedCandidatesTotal = 0;
  uint64_t simInitialAllCandidateStatesTotal = 0;
  uint64_t simInitialStoreBytesD2H = 0;
  uint64_t simInitialStoreBytesH2D = 0;
  uint64_t simInitialStoreUploadNanoseconds = 0;
  uint64_t simInitialSafeStoreFrontierBytesH2D = 0;
  uint64_t simInitialReduceChunkTotal = 0;
  uint64_t simInitialReduceChunkReplayedTotal = 0;
  uint64_t simInitialReduceSummaryReplayedTotal = 0;
  uint64_t simInitialContextApplyChunkTotal = 0;
  uint64_t simInitialContextApplyChunkSkippedTotal = 0;
  uint64_t simInitialContextApplyChunkReplayedTotal = 0;
  uint64_t simInitialContextApplySummarySkippedTotal = 0;
  uint64_t simInitialContextApplySummaryReplayedTotal = 0;
  uint64_t simInitialSummaryPackedD2HEnabledCount = 0;
  uint64_t simInitialSummaryPackedBytesD2H = 0;
  uint64_t simInitialSummaryUnpackedEquivalentBytesD2H = 0;
  double simInitialSummaryPackSeconds = 0.0;
  uint64_t simInitialSummaryPackedD2HFallbacks = 0;
  uint64_t simInitialSummaryHostCopyElisionEnabledCount = 0;
  double simInitialSummaryD2HCopySeconds = 0.0;
  double simInitialSummaryUnpackSeconds = 0.0;
  double simInitialSummaryResultMaterializeSeconds = 0.0;
  uint64_t simInitialSummaryHostCopyElidedBytes = 0;
  SimInitialPinnedAsyncHandoffStats simInitialPinnedAsyncHandoffStats;
  SimInitialChunkedHandoffStats simInitialChunkedHandoffStats;
  SimInitialSafeStoreRebuildStats simInitialSafeStoreRebuildStats;
  SimInitialSafeStorePruneIndexShadowStats simInitialSafeStorePruneIndexShadowStats;
  SimInitialSafeStorePrecombineShadowStats simInitialSafeStorePrecombineShadowStats;
  SimInitialCandidateContainerShadowStats simInitialCandidateContainerShadowStats;
  SimInitialContextApplyBreakdownStats simInitialContextApplyBreakdownStats;
  uint64_t simInitialExactFrontierReplayRequests = 0;
  uint64_t simInitialExactFrontierReplayFrontierStates = 0;
  uint64_t simInitialExactFrontierReplayDeviceSafeStores = 0;
  uint64_t simInitialExactFrontierCpuOrderedDigestAvailable = 0;
  uint64_t simInitialExactFrontierCpuUnorderedDigestAvailable = 0;
  uint64_t simInitialExactFrontierCpuMinCandidateAvailable = 0;
  uint64_t simInitialExactFrontierCpuSafeStoreDigestAvailable = 0;
  uint64_t simInitialExactFrontierCpuSafeStoreEpochAvailable = 0;
  uint64_t simInitialExactFrontierCpuSafeStoreEpoch = 0;
  uint64_t simInitialExactFrontierCpuFirstMaxAvailable = 0;
  uint64_t simInitialExactFrontierCpuTieAvailable = 0;
  uint64_t simInitialExactFrontierCpuFirstMaxTieAvailable = 0;
  getSimInitialReductionStats(simInitialEventsTotal,
                              simInitialRunSummariesTotal,
                              simInitialSummaryBytesD2H,
                              simInitialReducedCandidatesTotal,
                              simInitialAllCandidateStatesTotal,
                              simInitialStoreBytesD2H,
                              simInitialStoreBytesH2D,
                              simInitialStoreUploadNanoseconds,
                              simInitialReduceChunkTotal,
                              simInitialReduceChunkReplayedTotal,
                              simInitialReduceSummaryReplayedTotal);
		  getSimInitialSummaryPackedD2HStats(simInitialSummaryPackedD2HEnabledCount,
		                                     simInitialSummaryPackedBytesD2H,
		                                     simInitialSummaryUnpackedEquivalentBytesD2H,
		                                     simInitialSummaryPackSeconds,
		                                     simInitialSummaryPackedD2HFallbacks);
  getSimInitialSummaryHostCopyElisionStats(simInitialSummaryHostCopyElisionEnabledCount,
                                           simInitialSummaryD2HCopySeconds,
                                           simInitialSummaryUnpackSeconds,
                                           simInitialSummaryResultMaterializeSeconds,
                                           simInitialSummaryHostCopyElidedBytes);
  getSimInitialPinnedAsyncHandoffStats(simInitialPinnedAsyncHandoffStats);
  simInitialSafeStoreRebuildStats = getSimInitialSafeStoreRebuildStats();
  simInitialSafeStorePruneIndexShadowStats =
    getSimInitialSafeStorePruneIndexShadowStats();
  simInitialSafeStorePrecombineShadowStats =
    getSimInitialSafeStorePrecombineShadowStats();
  simInitialCandidateContainerShadowStats =
    getSimInitialCandidateContainerShadowStats();
  simInitialContextApplyBreakdownStats =
    getSimInitialContextApplyBreakdownStats();
  getSimInitialContextApplyChunkSkipStats(simInitialContextApplyChunkTotal,
	                                          simInitialContextApplyChunkSkippedTotal,
	                                          simInitialContextApplyChunkReplayedTotal,
	                                          simInitialContextApplySummarySkippedTotal,
	                                          simInitialContextApplySummaryReplayedTotal);
	  getSimInitialChunkedHandoffStats(simInitialChunkedHandoffStats);
	  getSimInitialExactFrontierReplayStats(simInitialExactFrontierReplayRequests,
	                                        simInitialExactFrontierReplayFrontierStates,
	                                        simInitialExactFrontierReplayDeviceSafeStores);
	  getSimInitialExactFrontierCpuContractBaselineStats(
	    simInitialExactFrontierCpuOrderedDigestAvailable,
	    simInitialExactFrontierCpuUnorderedDigestAvailable,
	    simInitialExactFrontierCpuMinCandidateAvailable,
	    simInitialExactFrontierCpuSafeStoreDigestAvailable,
	    simInitialExactFrontierCpuSafeStoreEpochAvailable,
	    simInitialExactFrontierCpuSafeStoreEpoch,
	    simInitialExactFrontierCpuFirstMaxAvailable,
	    simInitialExactFrontierCpuTieAvailable,
	    simInitialExactFrontierCpuFirstMaxTieAvailable);
	  uint64_t simSafeStoreHostEpochBumps = 0;
	  getSimSafeStoreHostEpochStats(simSafeStoreHostEpochBumps);
	  SimInitialCpuFrontierFastApplyTelemetry simInitialCpuFrontierFastApplyTelemetry;
	  getSimInitialCpuFrontierFastApplyStats(simInitialCpuFrontierFastApplyTelemetry);
	  double simInitialSafeStoreDeviceBuildSeconds = 0.0;
	  double simInitialSafeStoreDevicePruneSeconds = 0.0;
	  double simInitialSafeStoreFrontierUploadSeconds = 0.0;
  getSimInitialSafeStoreDeviceStats(simInitialSafeStoreFrontierBytesH2D,
                                    simInitialSafeStoreDeviceBuildSeconds,
                                    simInitialSafeStoreDevicePruneSeconds,
                                    simInitialSafeStoreFrontierUploadSeconds);
  uint64_t simInitialFrontierTransducerShadowCalls = 0;
  double simInitialFrontierTransducerShadowSeconds = 0.0;
  uint64_t simInitialFrontierTransducerShadowDigestD2HBytes = 0;
  uint64_t simInitialFrontierTransducerShadowSummariesReplayed = 0;
  uint64_t simInitialFrontierTransducerShadowMismatches = 0;
  getSimInitialFrontierTransducerShadowStats(
    simInitialFrontierTransducerShadowCalls,
    simInitialFrontierTransducerShadowSeconds,
    simInitialFrontierTransducerShadowDigestD2HBytes,
    simInitialFrontierTransducerShadowSummariesReplayed,
    simInitialFrontierTransducerShadowMismatches);
  uint64_t simInitialOrderedSegmentedV3ShadowCalls = 0;
  uint64_t simInitialOrderedSegmentedV3ShadowFrontierMismatches = 0;
  uint64_t simInitialOrderedSegmentedV3ShadowRunningMinMismatches = 0;
  uint64_t simInitialOrderedSegmentedV3ShadowSafeStoreMismatches = 0;
  uint64_t simInitialOrderedSegmentedV3ShadowCandidateCountMismatches = 0;
  uint64_t simInitialOrderedSegmentedV3ShadowCandidateValueMismatches = 0;
  getSimInitialOrderedSegmentedV3ShadowStats(
    simInitialOrderedSegmentedV3ShadowCalls,
    simInitialOrderedSegmentedV3ShadowFrontierMismatches,
    simInitialOrderedSegmentedV3ShadowRunningMinMismatches,
    simInitialOrderedSegmentedV3ShadowSafeStoreMismatches,
    simInitialOrderedSegmentedV3ShadowCandidateCountMismatches,
    simInitialOrderedSegmentedV3ShadowCandidateValueMismatches);
  const uint64_t simInitialReduceChunkSkippedTotal =
    simInitialReduceChunkTotal >= simInitialReduceChunkReplayedTotal ?
    (simInitialReduceChunkTotal - simInitialReduceChunkReplayedTotal) : 0;
  uint64_t simProposalAllCandidateStatesTotal = 0;
  uint64_t simProposalBytesD2H = 0;
  uint64_t simProposalSelectedTotal = 0;
  uint64_t simProposalSelectedBoxCellsTotal = 0;
  uint64_t simProposalMaterializedTotal = 0;
  uint64_t simProposalMaterializedQueryBasesTotal = 0;
  uint64_t simProposalMaterializedTargetBasesTotal = 0;
  double simProposalGpuSeconds = 0.0;
  uint64_t simProposalTracebackBatchRequests = 0;
  uint64_t simProposalTracebackBatchBatches = 0;
  uint64_t simProposalTracebackBatchSuccess = 0;
  uint64_t simProposalTracebackBatchFallbacks = 0;
  uint64_t simProposalTracebackBatchTieFallbacks = 0;
  uint64_t simProposalTracebackCudaEligible = 0;
  uint64_t simProposalTracebackCudaSizeFiltered = 0;
  uint64_t simProposalTracebackCudaBatchFailed = 0;
  uint64_t simProposalTracebackCpuDirect = 0;
  uint64_t simProposalPostScoreRejects = 0;
  uint64_t simProposalPostNtRejects = 0;
  uint64_t simProposalTracebackCpuCells = 0;
  uint64_t simProposalTracebackCudaCells = 0;
  uint64_t simProposalLoopAttempts = 0;
  uint64_t simProposalLoopShortCircuits = 0;
  uint64_t simProposalLoopInitialSources = 0;
  uint64_t simProposalLoopSafeStoreSources = 0;
  uint64_t simProposalLoopGpuSafeStoreSources = 0;
  uint64_t simProposalLoopGpuFrontierCacheSources = 0;
  uint64_t simProposalLoopGpuSafeStoreFullSources = 0;
  uint64_t simProposalLoopFallbackNoStore = 0;
  uint64_t simProposalLoopFallbackSelectorFailure = 0;
  uint64_t simProposalLoopFallbackEmptySelection = 0;
  uint64_t simProposalMaterializeCpuBackendCalls = 0;
  uint64_t simProposalMaterializeCudaBatchBackendCalls = 0;
  uint64_t simProposalMaterializeHybridBackendCalls = 0;
  uint64_t simInitialProposalV2Batches = 0;
  uint64_t simInitialProposalV2Requests = 0;
  uint64_t simInitialProposalV3Batches = 0;
  uint64_t simInitialProposalV3Requests = 0;
  uint64_t simInitialProposalV3SelectedCandidateStates = 0;
  uint64_t simInitialProposalDirectTopKBatches = 0;
  uint64_t simInitialProposalDirectTopKLogicalCandidateStates = 0;
  uint64_t simInitialProposalDirectTopKMaterializedCandidateStates = 0;
  double simInitialProposalV3GpuSeconds = 0.0;
  double simInitialProposalDirectTopKGpuSeconds = 0.0;
  double simProposalTracebackBatchGpuSeconds = 0.0;
  double simProposalPostSeconds = 0.0;
  double simDeviceKLoopSeconds = 0.0;
  uint64_t simLocateDeviceKLoopAttempts = 0;
  uint64_t simLocateDeviceKLoopShortCircuits = 0;
  getSimProposalStats(simProposalAllCandidateStatesTotal,
                      simProposalBytesD2H,
                      simProposalSelectedTotal,
                      simProposalSelectedBoxCellsTotal,
                      simProposalMaterializedTotal,
                      simProposalMaterializedQueryBasesTotal,
                      simProposalMaterializedTargetBasesTotal,
                      simProposalGpuSeconds);
  getSimProposalMaterializeBatchStats(simProposalTracebackBatchRequests,
                                      simProposalTracebackBatchBatches,
                                      simProposalTracebackBatchSuccess,
                                      simProposalTracebackBatchFallbacks,
                                      simProposalTracebackBatchTieFallbacks,
                                      simProposalTracebackBatchGpuSeconds,
                                      simProposalPostSeconds);
  getSimProposalTracebackRoutingStats(simProposalTracebackCudaEligible,
                                      simProposalTracebackCudaSizeFiltered,
                                      simProposalTracebackCudaBatchFailed,
                                      simProposalTracebackCpuDirect,
                                      simProposalPostScoreRejects,
                                      simProposalPostNtRejects,
                                      simProposalTracebackCpuCells,
                                      simProposalTracebackCudaCells);
  getSimProposalLoopStats(simProposalLoopAttempts,
                          simProposalLoopShortCircuits,
                          simProposalLoopInitialSources,
                          simProposalLoopSafeStoreSources,
                          simProposalLoopFallbackNoStore,
                          simProposalLoopFallbackSelectorFailure,
                          simProposalLoopFallbackEmptySelection);
  getSimDeviceKLoopStats(simProposalLoopGpuSafeStoreSources,
                         simProposalLoopGpuFrontierCacheSources,
                         simProposalLoopGpuSafeStoreFullSources,
                         simDeviceKLoopSeconds);
  getSimLocateDeviceKLoopStats(simLocateDeviceKLoopAttempts,
                               simLocateDeviceKLoopShortCircuits);
  getSimProposalMaterializeBackendStats(simProposalMaterializeCpuBackendCalls,
                                        simProposalMaterializeCudaBatchBackendCalls,
                                        simProposalMaterializeHybridBackendCalls);
  getSimInitialProposalV2Stats(simInitialProposalV2Batches,
                               simInitialProposalV2Requests);
  getSimInitialProposalV3Stats(simInitialProposalV3Batches,
                               simInitialProposalV3Requests,
                               simInitialProposalV3SelectedCandidateStates,
                               simInitialProposalV3GpuSeconds);
  getSimInitialProposalDirectTopKStats(simInitialProposalDirectTopKBatches,
                                       simInitialProposalDirectTopKLogicalCandidateStates,
                                       simInitialProposalDirectTopKMaterializedCandidateStates,
                                       simInitialProposalDirectTopKGpuSeconds);
  const char *simProposalMaterializeBackend = "cpu";
  switch(simProposalMaterializeBackendRuntime())
  {
    case SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK:
      simProposalMaterializeBackend = "cuda_batch_traceback";
      break;
    case SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID:
      simProposalMaterializeBackend = "hybrid";
      break;
    case SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU:
    default:
      break;
  }
  cerr<<"benchmark.sim_initial_events_total="<<simInitialEventsTotal<<endl;
  cerr<<"benchmark.sim_initial_run_summaries_total="<<simInitialRunSummariesTotal<<endl;
  cerr<<"benchmark.sim_initial_summary_bytes_d2h="<<simInitialSummaryBytesD2H<<endl;
  cerr<<"benchmark.sim_initial_summary_packed_d2h_enabled="
      <<(simInitialSummaryPackedD2HEnabledCount > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_summary_packed_bytes_d2h="
      <<simInitialSummaryPackedBytesD2H<<endl;
  cerr<<"benchmark.sim_initial_summary_unpacked_equivalent_bytes_d2h="
      <<simInitialSummaryUnpackedEquivalentBytesD2H<<endl;
  cerr<<"benchmark.sim_initial_summary_pack_seconds="<<simInitialSummaryPackSeconds<<endl;
  cerr<<"benchmark.sim_initial_summary_packed_d2h_fallbacks="
      <<simInitialSummaryPackedD2HFallbacks<<endl;
  cerr<<"benchmark.sim_initial_summary_host_copy_elision_enabled="
      <<(simInitialSummaryHostCopyElisionEnabledCount > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_summary_d2h_copy_seconds="
      <<simInitialSummaryD2HCopySeconds<<endl;
  cerr<<"benchmark.sim_initial_summary_unpack_seconds="
      <<simInitialSummaryUnpackSeconds<<endl;
  cerr<<"benchmark.sim_initial_summary_result_materialize_seconds="
      <<simInitialSummaryResultMaterializeSeconds<<endl;
  cerr<<"benchmark.sim_initial_summary_host_copy_elided_bytes="
      <<simInitialSummaryHostCopyElidedBytes<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_enabled="
      <<((simCudaInitialChunkedHandoffEnabledRuntime() &&
          simCudaInitialPinnedAsyncHandoffEnabledRuntime()) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_requested="
      <<(simCudaInitialPinnedAsyncHandoffEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_active="
      <<(simInitialPinnedAsyncHandoffStats.activeCount > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_requested_batches="
      <<simInitialPinnedAsyncHandoffStats.requestedCount<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_active_batches="
      <<simInitialPinnedAsyncHandoffStats.activeCount<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_async_disabled_reason="
      <<((simInitialPinnedAsyncHandoffStats.activeCount > 0 &&
          simInitialPinnedAsyncHandoffStats.requestedCount >
            simInitialPinnedAsyncHandoffStats.activeCount) ?
         "mixed" :
         (simInitialPinnedAsyncHandoffStats.activeCount > 0) ?
         "none" :
         simInitialPinnedAsyncHandoffDisabledReasonLabel(
           simInitialPinnedAsyncHandoffStats.disabledReason))<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_requested="
      <<(simCudaInitialPinnedAsyncCpuPipelineEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_active="
      <<(simInitialPinnedAsyncHandoffStats.cpuPipelineActiveCount > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_disabled_reason="
      <<((simInitialPinnedAsyncHandoffStats.cpuPipelineActiveCount > 0 &&
          simInitialPinnedAsyncHandoffStats.cpuPipelineRequestedCount >
            simInitialPinnedAsyncHandoffStats.cpuPipelineActiveCount) ?
         "mixed" :
         (simInitialPinnedAsyncHandoffStats.cpuPipelineActiveCount > 0) ?
         "none" :
         simInitialPinnedAsyncCpuPipelineDisabledReasonLabel(
           simInitialPinnedAsyncHandoffStats.cpuPipelineDisabledReason))<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_chunks_applied="
      <<simInitialPinnedAsyncHandoffStats.cpuPipelineChunksApplied<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_summaries_applied="
      <<simInitialPinnedAsyncHandoffStats.cpuPipelineSummariesApplied<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_chunks_finalized="
      <<simInitialPinnedAsyncHandoffStats.cpuPipelineChunksFinalized<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_finalize_count="
      <<simInitialPinnedAsyncHandoffStats.cpuPipelineFinalizeCount<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_pipeline_out_of_order_chunks="
      <<simInitialPinnedAsyncHandoffStats.cpuPipelineOutOfOrderChunks<<endl;
  cerr<<"benchmark.sim_initial_handoff_source_ready_mode="
      <<simInitialPinnedAsyncHandoffSourceReadyModeLabel(
          simInitialPinnedAsyncHandoffStats.sourceReadyMode)<<endl;
  cerr<<"benchmark.sim_initial_handoff_chunks_total="
      <<simInitialPinnedAsyncHandoffStats.chunkCount<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_slots="
      <<simInitialPinnedAsyncHandoffStats.pinnedSlots<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_bytes="
      <<simInitialPinnedAsyncHandoffStats.pinnedBytes<<endl;
  cerr<<"benchmark.sim_initial_handoff_pinned_allocation_failures="
      <<simInitialPinnedAsyncHandoffStats.pinnedAllocationFailures<<endl;
  cerr<<"benchmark.sim_initial_handoff_pageable_fallbacks="
      <<simInitialPinnedAsyncHandoffStats.pageableFallbacks<<endl;
  cerr<<"benchmark.sim_initial_handoff_sync_copies="
      <<simInitialPinnedAsyncHandoffStats.syncCopies<<endl;
  cerr<<"benchmark.sim_initial_handoff_async_copies="
      <<simInitialPinnedAsyncHandoffStats.asyncCopies<<endl;
  cerr<<"benchmark.sim_initial_handoff_slot_reuse_waits="
      <<simInitialPinnedAsyncHandoffStats.slotReuseWaits<<endl;
  cerr<<"benchmark.sim_initial_handoff_slots_reused_after_materialize="
      <<((simInitialPinnedAsyncHandoffStats.activeCount > 0 &&
          simInitialPinnedAsyncHandoffStats.slotsReusedAfterMaterializeCount ==
            simInitialPinnedAsyncHandoffStats.activeCount) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_handoff_async_d2h_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.asyncD2HNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_handoff_d2h_wait_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.d2hWaitNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_apply_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.cpuApplyNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_handoff_cpu_d2h_overlap_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.cpuD2HOverlapNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_handoff_dp_d2h_overlap_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.dpD2HOverlapNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_handoff_critical_path_seconds="
      <<(static_cast<double>(simInitialPinnedAsyncHandoffStats.criticalPathNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_reduced_candidates_total="<<simInitialReducedCandidatesTotal<<endl;
  cerr<<"benchmark.sim_initial_all_candidate_states_total="<<simInitialAllCandidateStatesTotal<<endl;
  cerr<<"benchmark.sim_initial_store_bytes_d2h="<<simInitialStoreBytesD2H<<endl;
  cerr<<"benchmark.sim_initial_store_bytes_h2d="<<simInitialStoreBytesH2D<<endl;
  cerr<<"benchmark.sim_initial_store_upload_seconds="<<(static_cast<double>(simInitialStoreUploadNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_device_build_seconds="<<simInitialSafeStoreDeviceBuildSeconds<<endl;
  cerr<<"benchmark.sim_initial_safe_store_device_prune_seconds="<<simInitialSafeStoreDevicePruneSeconds<<endl;
  cerr<<"benchmark.sim_initial_safe_store_frontier_bytes_h2d="<<simInitialSafeStoreFrontierBytesH2D<<endl;
  cerr<<"benchmark.sim_initial_safe_store_frontier_upload_seconds="<<simInitialSafeStoreFrontierUploadSeconds<<endl;
  cerr<<"benchmark.sim_initial_frontier_transducer_shadow_calls="
      <<simInitialFrontierTransducerShadowCalls<<endl;
  cerr<<"benchmark.sim_initial_frontier_transducer_shadow_seconds="
      <<simInitialFrontierTransducerShadowSeconds<<endl;
  cerr<<"benchmark.sim_initial_frontier_transducer_shadow_digest_d2h_bytes="
      <<simInitialFrontierTransducerShadowDigestD2HBytes<<endl;
  cerr<<"benchmark.sim_initial_frontier_transducer_shadow_summaries_replayed_total="
      <<simInitialFrontierTransducerShadowSummariesReplayed<<endl;
  cerr<<"benchmark.sim_initial_frontier_transducer_shadow_mismatches="
      <<simInitialFrontierTransducerShadowMismatches<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_calls="
      <<simInitialOrderedSegmentedV3ShadowCalls<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_frontier_mismatches="
      <<simInitialOrderedSegmentedV3ShadowFrontierMismatches<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_running_min_mismatches="
      <<simInitialOrderedSegmentedV3ShadowRunningMinMismatches<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_safe_store_mismatches="
      <<simInitialOrderedSegmentedV3ShadowSafeStoreMismatches<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_count_mismatches="
      <<simInitialOrderedSegmentedV3ShadowCandidateCountMismatches<<endl;
  cerr<<"benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_value_mismatches="
      <<simInitialOrderedSegmentedV3ShadowCandidateValueMismatches<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_requested="
      <<(simCudaInitialExactFrontierShadowGateRequestedRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_active=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_authority=cpu"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_disabled_reason="
      <<longtargetSimInitialExactFrontierShadowGateDisabledReason()<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_calls=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_supported=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_gate_missing_contract_counters=1"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_backend="
      <<longtargetSimInitialExactFrontierShadowBackendLabel()<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_backend_supported=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_backend_disabled_reason="
      <<longtargetSimInitialExactFrontierShadowBackendDisabledReason()<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_one_chunk_supported=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_one_chunk_calls=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_one_chunk_final_compare_supported=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_one_chunk_missing_backend="
      <<(simCudaInitialExactFrontierShadowGateRequestedRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_ordered_digest_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_unordered_digest_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_min_candidate_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_safe_store_digest_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_safe_store_epoch_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_first_max_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_tie_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_shadow_has_first_max_tie_check=0"<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_ordered_digest_available="
      <<(simInitialExactFrontierCpuOrderedDigestAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_unordered_digest_available="
      <<(simInitialExactFrontierCpuUnorderedDigestAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_min_candidate_available="
      <<(simInitialExactFrontierCpuMinCandidateAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_digest_available="
      <<(simInitialExactFrontierCpuSafeStoreDigestAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available="
      <<(simInitialExactFrontierCpuSafeStoreEpochAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch="
      <<simInitialExactFrontierCpuSafeStoreEpoch<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_bumps="
      <<simSafeStoreHostEpochBumps<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_first_max_available="
      <<(simInitialExactFrontierCpuFirstMaxAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_tie_available="
      <<(simInitialExactFrontierCpuTieAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_exact_frontier_contract_cpu_first_max_tie_available="
      <<(simInitialExactFrontierCpuFirstMaxTieAvailable > 0 ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_safe_store_host_epoch="<<simInitialExactFrontierCpuSafeStoreEpoch<<endl;
  cerr<<"benchmark.sim_safe_store_host_epoch_bumps="<<simSafeStoreHostEpochBumps<<endl;
  cerr<<"benchmark.sim_proposal_materialize_backend="<<simProposalMaterializeBackend<<endl;
  cerr<<"benchmark.sim_proposal_all_candidate_states_total="<<simProposalAllCandidateStatesTotal<<endl;
  cerr<<"benchmark.sim_proposal_bytes_d2h="<<simProposalBytesD2H<<endl;
  cerr<<"benchmark.sim_proposal_selected_total="<<simProposalSelectedTotal<<endl;
  cerr<<"benchmark.sim_proposal_selected_box_cells_total="<<simProposalSelectedBoxCellsTotal<<endl;
  cerr<<"benchmark.sim_proposal_materialized_total="<<simProposalMaterializedTotal<<endl;
  cerr<<"benchmark.sim_proposal_materialized_query_bases_total="<<simProposalMaterializedQueryBasesTotal<<endl;
  cerr<<"benchmark.sim_proposal_materialized_target_bases_total="<<simProposalMaterializedTargetBasesTotal<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_requests="<<simProposalTracebackBatchRequests<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_batches="<<simProposalTracebackBatchBatches<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_success="<<simProposalTracebackBatchSuccess<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_fallbacks="<<simProposalTracebackBatchFallbacks<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_tie_fallbacks="<<simProposalTracebackBatchTieFallbacks<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cuda_eligible="<<simProposalTracebackCudaEligible<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cuda_size_filtered="<<simProposalTracebackCudaSizeFiltered<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cuda_batch_failed="<<simProposalTracebackCudaBatchFailed<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cpu_direct="<<simProposalTracebackCpuDirect<<endl;
  cerr<<"benchmark.sim_proposal_post_score_rejects="<<simProposalPostScoreRejects<<endl;
  cerr<<"benchmark.sim_proposal_post_nt_rejects="<<simProposalPostNtRejects<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cpu_cells="<<simProposalTracebackCpuCells<<endl;
  cerr<<"benchmark.sim_proposal_traceback_cuda_cells="<<simProposalTracebackCudaCells<<endl;
  cerr<<"benchmark.sim_proposal_loop_attempts="<<simProposalLoopAttempts<<endl;
  cerr<<"benchmark.sim_proposal_loop_short_circuits="<<simProposalLoopShortCircuits<<endl;
  cerr<<"benchmark.sim_proposal_loop_source_initial="<<simProposalLoopInitialSources<<endl;
  cerr<<"benchmark.sim_proposal_loop_source_safe_store="<<simProposalLoopSafeStoreSources<<endl;
  cerr<<"benchmark.sim_proposal_loop_source_gpu_safe_store="<<simProposalLoopGpuSafeStoreSources<<endl;
  cerr<<"benchmark.sim_proposal_loop_source_gpu_frontier_cache="<<simProposalLoopGpuFrontierCacheSources<<endl;
  cerr<<"benchmark.sim_proposal_loop_source_gpu_safe_store_full="<<simProposalLoopGpuSafeStoreFullSources<<endl;
  cerr<<"benchmark.sim_proposal_loop_fallback_no_store="<<simProposalLoopFallbackNoStore<<endl;
  cerr<<"benchmark.sim_proposal_loop_fallback_selector_failure="<<simProposalLoopFallbackSelectorFailure<<endl;
  cerr<<"benchmark.sim_proposal_loop_fallback_empty_selection="<<simProposalLoopFallbackEmptySelection<<endl;
  cerr<<"benchmark.sim_locate_device_k_loop_attempts="<<simLocateDeviceKLoopAttempts<<endl;
  cerr<<"benchmark.sim_locate_device_k_loop_short_circuits="<<simLocateDeviceKLoopShortCircuits<<endl;
  cerr<<"benchmark.sim_device_k_loop_seconds="<<simDeviceKLoopSeconds<<endl;
  cerr<<"benchmark.sim_proposal_materialize_backend_cpu_calls="
      <<simProposalMaterializeCpuBackendCalls<<endl;
  cerr<<"benchmark.sim_proposal_materialize_backend_cuda_batch_calls="
      <<simProposalMaterializeCudaBatchBackendCalls<<endl;
  cerr<<"benchmark.sim_proposal_materialize_backend_hybrid_calls="
      <<simProposalMaterializeHybridBackendCalls<<endl;
  cerr<<"benchmark.sim_initial_proposal_v2_batches="<<simInitialProposalV2Batches<<endl;
  cerr<<"benchmark.sim_initial_proposal_v2_requests="<<simInitialProposalV2Requests<<endl;
  cerr<<"benchmark.sim_initial_proposal_v3_batches="<<simInitialProposalV3Batches<<endl;
  cerr<<"benchmark.sim_initial_proposal_v3_requests="<<simInitialProposalV3Requests<<endl;
  cerr<<"benchmark.sim_initial_proposal_v3_selected_candidate_states="
      <<simInitialProposalV3SelectedCandidateStates<<endl;
  cerr<<"benchmark.sim_initial_proposal_v3_gpu_seconds="<<simInitialProposalV3GpuSeconds<<endl;
  cerr<<"benchmark.sim_initial_proposal_direct_topk_batches="<<simInitialProposalDirectTopKBatches<<endl;
  cerr<<"benchmark.sim_initial_proposal_direct_topk_logical_candidate_states="
      <<simInitialProposalDirectTopKLogicalCandidateStates<<endl;
  cerr<<"benchmark.sim_initial_proposal_direct_topk_materialized_candidate_states="
      <<simInitialProposalDirectTopKMaterializedCandidateStates<<endl;
  cerr<<"benchmark.sim_initial_proposal_direct_topk_gpu_seconds="<<simInitialProposalDirectTopKGpuSeconds<<endl;
  cerr<<"benchmark.sim_initial_reduce_chunks_total="<<simInitialReduceChunkTotal<<endl;
  cerr<<"benchmark.sim_initial_reduce_chunks_replayed_total="<<simInitialReduceChunkReplayedTotal<<endl;
  cerr<<"benchmark.sim_initial_reduce_chunks_skipped_total="<<simInitialReduceChunkSkippedTotal<<endl;
  cerr<<"benchmark.sim_initial_reduce_summaries_replayed_total="<<simInitialReduceSummaryReplayedTotal<<endl;
  cerr<<"benchmark.sim_initial_context_apply_chunk_skip_enabled="
      <<(simCudaInitialContextApplyChunkSkipEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_chunks_total="<<simInitialContextApplyChunkTotal<<endl;
  cerr<<"benchmark.sim_initial_context_apply_chunks_skipped="<<simInitialContextApplyChunkSkippedTotal<<endl;
	  cerr<<"benchmark.sim_initial_context_apply_chunks_replayed="<<simInitialContextApplyChunkReplayedTotal<<endl;
	  cerr<<"benchmark.sim_initial_context_apply_summaries_skipped="<<simInitialContextApplySummarySkippedTotal<<endl;
	  cerr<<"benchmark.sim_initial_context_apply_summaries_replayed="<<simInitialContextApplySummaryReplayedTotal<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_enabled="
	      <<(simCudaInitialChunkedHandoffEnabledRuntime() ? 1 : 0)<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_rows_per_chunk="
	      <<simCudaInitialChunkedHandoffChunkRowsRuntime()<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_rows_per_chunk_source="
	      <<simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime()<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_chunks_total="
	      <<simInitialChunkedHandoffStats.chunkCount<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_summaries_replayed="
	      <<simInitialChunkedHandoffStats.summariesReplayed<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_ring_slots_configured="
	      <<simCudaInitialChunkedHandoffRingSlotsRuntime()<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_ring_slots="
	      <<simInitialChunkedHandoffStats.ringSlots<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_ring_slots_source="
	      <<simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime()<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_pinned_allocation_failures="
	      <<simInitialChunkedHandoffStats.pinnedAllocationFailures<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_pageable_fallbacks="
	      <<simInitialChunkedHandoffStats.pageableFallbacks<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_sync_copies="
	      <<simInitialChunkedHandoffStats.syncCopies<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_cpu_wait_seconds="
	      <<(static_cast<double>(simInitialChunkedHandoffStats.cpuWaitNanoseconds) / 1.0e9)<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_critical_path_d2h_seconds="
	      <<(static_cast<double>(simInitialChunkedHandoffStats.criticalPathD2HNanoseconds) / 1.0e9)<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_measured_overlap_seconds="
	      <<(static_cast<double>(simInitialChunkedHandoffStats.measuredOverlapNanoseconds) / 1.0e9)<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_fallbacks="
	      <<simInitialChunkedHandoffStats.fallbackCount<<endl;
	  cerr<<"benchmark.sim_initial_chunked_handoff_fallback_reason="
	      <<simInitialChunkedHandoffFallbackReasonLabel(simInitialChunkedHandoffStats.fallbackReason)<<endl;
	  cerr<<"benchmark.sim_initial_exact_frontier_replay_enabled="
	      <<(simCudaInitialExactFrontierReplayEnabledRuntime() ? 1 : 0)<<endl;
	  cerr<<"benchmark.sim_initial_exact_frontier_replay_requests="
	      <<simInitialExactFrontierReplayRequests<<endl;
	  cerr<<"benchmark.sim_initial_exact_frontier_replay_frontier_states="
	      <<simInitialExactFrontierReplayFrontierStates<<endl;
	  cerr<<"benchmark.sim_initial_exact_frontier_replay_device_safe_stores="
	      <<simInitialExactFrontierReplayDeviceSafeStores<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_enabled="
	      <<(simInitialCpuFrontierFastApplyTelemetry.enabledCount > 0 ? 1 : 0)<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_attempts="
	      <<simInitialCpuFrontierFastApplyTelemetry.attempts<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_successes="
	      <<simInitialCpuFrontierFastApplyTelemetry.successes<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_fallbacks="
	      <<simInitialCpuFrontierFastApplyTelemetry.fallbacks<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_shadow_mismatches="
	      <<simInitialCpuFrontierFastApplyTelemetry.shadowMismatches<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_summaries_replayed_total="
	      <<simInitialCpuFrontierFastApplyTelemetry.summariesReplayed<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_candidates_out_total="
	      <<simInitialCpuFrontierFastApplyTelemetry.candidatesOut<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_fast_apply_seconds="
	      <<(static_cast<double>(simInitialCpuFrontierFastApplyTelemetry.fastApplyNanoseconds) / 1.0e9)<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_oracle_apply_seconds_shadow="
	      <<(static_cast<double>(simInitialCpuFrontierFastApplyTelemetry.oracleApplyNanosecondsShadow) / 1.0e9)<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_rejected_by_stats="
	      <<simInitialCpuFrontierFastApplyTelemetry.rejectedByStats<<endl;
	  cerr<<"benchmark.sim_initial_cpu_frontier_fast_apply_rejected_by_nonempty_context="
	      <<simInitialCpuFrontierFastApplyTelemetry.rejectedByNonemptyContext<<endl;
	  double simInitialScanSeconds = 0.0;
	  double simInitialScanGpuSeconds = 0.0;
  double simInitialScanD2HSeconds = 0.0;
  double simInitialScanCpuMergeSeconds = 0.0;
  double simInitialScanDiagSeconds = 0.0;
  double simInitialScanOnlineReduceSeconds = 0.0;
  double simInitialScanWaitSeconds = 0.0;
  double simInitialScanCpuContextApplySeconds = 0.0;
  double simInitialScanCpuSafeStoreUpdateSeconds = 0.0;
  double simInitialScanCpuSafeStorePruneSeconds = 0.0;
  double simInitialScanCpuSafeStoreUploadSeconds = 0.0;
  double simInitialScanCountCopySeconds = 0.0;
  double simInitialScanBaseUploadSeconds = 0.0;
  double simInitialProposalSelectD2HSeconds = 0.0;
  double simInitialScanSyncWaitSeconds = 0.0;
  double simInitialScanTailSeconds = 0.0;
  double simInitialHashReduceSeconds = getSimInitialHashReduceSeconds();
  double simInitialSegmentedReduceSeconds = getSimInitialSegmentedReduceSeconds();
  double simInitialSegmentedCompactSeconds = getSimInitialSegmentedCompactSeconds();
  double simInitialTopKSeconds = getSimInitialTopKSeconds();
  const double simInitialOrderedReplaySeconds = simInitialTopKSeconds;
  uint64_t simInitialSegmentedTileStates = 0;
  uint64_t simInitialSegmentedGroupedStates = 0;
  getSimInitialSegmentedStateStats(simInitialSegmentedTileStates,
                                   simInitialSegmentedGroupedStates);
  double simLocateSeconds = 0.0;
  double simLocateGpuSeconds = 0.0;
  double simRegionScanGpuSeconds = 0.0;
  double simRegionD2HSeconds = 0.0;
  double simMaterializeSeconds = 0.0;
  double simTracebackDpSeconds = 0.0;
  double simTracebackPostSeconds = 0.0;
  getSimPhaseTimingStats(simInitialScanSeconds,
                         simInitialScanGpuSeconds,
                         simInitialScanD2HSeconds,
                         simInitialScanCpuMergeSeconds,
                         simInitialScanDiagSeconds,
                         simInitialScanOnlineReduceSeconds,
                         simInitialScanWaitSeconds,
                         simInitialScanCountCopySeconds,
                         simInitialScanBaseUploadSeconds,
                         simInitialProposalSelectD2HSeconds,
                         simInitialScanSyncWaitSeconds,
                         simInitialScanTailSeconds,
                         simLocateSeconds,
                         simLocateGpuSeconds,
                         simRegionScanGpuSeconds,
                         simRegionD2HSeconds,
                         simMaterializeSeconds,
                         simTracebackDpSeconds,
                         simTracebackPostSeconds);
  getSimInitialCpuMergeTimingStats(simInitialScanCpuContextApplySeconds,
                                   simInitialScanCpuSafeStoreUpdateSeconds,
                                   simInitialScanCpuSafeStorePruneSeconds,
                                   simInitialScanCpuSafeStoreUploadSeconds);
  const double simInitialScanCpuMergeSubtotalSeconds =
    simInitialScanCpuContextApplySeconds +
    simInitialScanCpuSafeStoreUpdateSeconds +
    simInitialScanCpuSafeStorePruneSeconds +
    simInitialScanCpuSafeStoreUploadSeconds;
  const double simInitialStoreRebuildSeconds =
    simInitialScanCpuSafeStoreUpdateSeconds +
    simInitialScanCpuSafeStorePruneSeconds;
  const double simInitialFrontierSyncSeconds =
    simInitialScanCpuSafeStoreUploadSeconds;
  const double simInitialRunSummaryPipelineSeconds =
    simInitialHashReduceSeconds +
    simInitialSegmentedReduceSeconds +
    simInitialSegmentedCompactSeconds +
    simInitialTopKSeconds;
  cerr<<"benchmark.sim_initial_scan_seconds="<<simInitialScanSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_gpu_seconds="<<simInitialScanGpuSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_d2h_seconds="<<simInitialScanD2HSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_merge_seconds="<<simInitialScanCpuMergeSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_context_apply_seconds="<<simInitialScanCpuContextApplySeconds<<endl;
  cerr<<"benchmark.sim_initial_context_apply_candidate_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_floor_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_FLOOR_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_frontier_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_FRONTIER_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_safe_store_handoff_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_candidate_erase_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_ERASE_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_candidate_insert_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_INSERT_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_candidate_sort_seconds="
      <<(static_cast<double>(simInitialContextApplyBreakdownStats.get(
           SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_SORT_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_running_min_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CONTEXT_APPLY_RUNNING_MIN_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_candidate_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_frontier_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CONTEXT_APPLY_FRONTIER_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_safe_store_handoffs="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_context_apply_noop_events="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CONTEXT_APPLY_NOOP_EVENT_COUNT)<<endl;
  const uint64_t simInitialCandidateReplayProcessed =
    simInitialContextApplyBreakdownStats.get(
      SIM_INITIAL_CANDIDATE_REPLAY_PROCESSED_COUNT);
  const uint64_t simInitialCandidateReplayFinalCandidates =
    simInitialContextApplyBreakdownStats.get(
      SIM_INITIAL_CANDIDATE_REPLAY_FINAL_CANDIDATE_COUNT);
  const double simInitialCandidateReplaySurvivalRatio =
    simInitialCandidateReplayProcessed > 0 ?
      static_cast<double>(simInitialCandidateReplayFinalCandidates) /
        static_cast<double>(simInitialCandidateReplayProcessed) :
      0.0;
  cerr<<"benchmark.sim_initial_candidate_replay_summaries="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_SUMMARY_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_processed="
      <<simInitialCandidateReplayProcessed<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_accepted="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_ACCEPTED_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_rejected_below_floor="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_REJECTED_BELOW_FLOOR_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_insertions="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_INSERTION_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_replacements="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_REPLACEMENT_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_erasures="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_ERASURE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_tie_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_TIE_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_first_max_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_REPLAY_FIRST_MAX_UPDATE_COUNT)<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_final_candidates="
      <<simInitialCandidateReplayFinalCandidates<<endl;
  cerr<<"benchmark.sim_initial_candidate_replay_survival_ratio="
      <<simInitialCandidateReplaySurvivalRatio<<endl;
  const uint64_t simInitialCandidateChurnOverwritten =
    simInitialContextApplyBreakdownStats.get(
      SIM_INITIAL_CANDIDATE_CHURN_OVERWRITTEN_UPDATES);
  const uint64_t simInitialCandidateChurnFinalSurvivor =
    simInitialContextApplyBreakdownStats.get(
      SIM_INITIAL_CANDIDATE_CHURN_FINAL_SURVIVOR_UPDATES);
  const uint64_t simInitialCandidateChurnAccepted =
    simInitialCandidateChurnOverwritten +
    simInitialCandidateChurnFinalSurvivor;
  const double simInitialCandidateChurnOverwrittenRatio =
    simInitialCandidateChurnAccepted > 0 ?
      static_cast<double>(simInitialCandidateChurnOverwritten) /
        static_cast<double>(simInitialCandidateChurnAccepted) :
      0.0;
  cerr<<"benchmark.sim_initial_candidate_churn_container_high_water="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_CONTAINER_HIGH_WATER)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_container_final_size="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_CONTAINER_FINAL_SIZE)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_cumulative_container_size="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_CUMULATIVE_CONTAINER_SIZE)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_replacement_chains="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_REPLACEMENT_CHAINS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_max_replacement_chain="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_MAX_REPLACEMENT_CHAIN)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_overwritten_updates="
      <<simInitialCandidateChurnOverwritten<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_final_survivor_updates="
      <<simInitialCandidateChurnFinalSurvivor<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_overwritten_ratio="
      <<simInitialCandidateChurnOverwrittenRatio<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_first_max_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_FIRST_MAX_UPDATES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_tie_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_TIE_UPDATES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_order_sensitive_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_ORDER_SENSITIVE_UPDATES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_heap_builds="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_HEAP_BUILDS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_heap_updates="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_HEAP_UPDATES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_churn_index_rebuilds="
      <<simInitialContextApplyBreakdownStats.get(
          SIM_INITIAL_CANDIDATE_CHURN_INDEX_REBUILDS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_enabled="
      <<(simCudaInitialCandidateContainerShadowEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_calls="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_CALLS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_seconds="
      <<(static_cast<double>(simInitialCandidateContainerShadowStats.get(
           SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_NANOSECONDS)) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_state_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_STATE_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_size_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_SIZE_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_digest_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_DIGEST_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_order_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_ORDER_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_floor_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_FLOOR_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_min_candidate_mismatches="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_MIN_CANDIDATE_MISMATCHES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_events="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EVENTS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_active_candidates="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_ACTIVE_CANDIDATES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_stale_entries="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_STALE_ENTRIES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_lazy_pops="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_LAZY_POPS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_est_saved_erasures="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EST_SAVED_ERASURES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_est_saved_index_rebuilds="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EST_SAVED_INDEX_REBUILDS)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_high_water_entries="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_HIGH_WATER_ENTRIES)<<endl;
  cerr<<"benchmark.sim_initial_candidate_container_shadow_compaction_estimate="
      <<simInitialCandidateContainerShadowStats.get(
          SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_COMPACTION_ESTIMATE)<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_safe_store_update_seconds="<<simInitialScanCpuSafeStoreUpdateSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_safe_store_prune_seconds="<<simInitialScanCpuSafeStorePruneSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_safe_store_upload_seconds="<<simInitialScanCpuSafeStoreUploadSeconds<<endl;
  cerr<<"benchmark.sim_initial_ordered_replay_seconds="<<simInitialOrderedReplaySeconds<<endl;
  cerr<<"benchmark.sim_initial_store_rebuild_seconds="<<simInitialStoreRebuildSeconds<<endl;
  cerr<<"benchmark.sim_initial_frontier_sync_seconds="<<simInitialFrontierSyncSeconds<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_calls="
      <<simInitialSafeStoreRebuildStats.updateCalls<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_summaries="
      <<simInitialSafeStoreRebuildStats.updateSummaries<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_inserted_states="
      <<simInitialSafeStoreRebuildStats.updateInsertedStates<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_merged_summaries="
      <<simInitialSafeStoreRebuildStats.updateMergedSummaries<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_store_size_before="
      <<simInitialSafeStoreRebuildStats.updateStoreSizeBefore<<endl;
  cerr<<"benchmark.sim_initial_safe_store_update_store_size_after="
      <<simInitialSafeStoreRebuildStats.updateStoreSizeAfter<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_calls="
      <<simInitialSafeStoreRebuildStats.pruneCalls<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_scanned_states="
      <<simInitialSafeStoreRebuildStats.pruneScannedStates<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_kept_states="
      <<simInitialSafeStoreRebuildStats.pruneKeptStates<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_removed_states="
      <<simInitialSafeStoreRebuildStats.pruneRemovedStates<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_kept_above_floor="
      <<simInitialSafeStoreRebuildStats.pruneKeptAboveFloor<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_kept_frontier="
      <<simInitialSafeStoreRebuildStats.pruneKeptFrontier<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_rebuild_seconds="
      <<(static_cast<double>(simInitialSafeStoreRebuildStats.pruneIndexRebuildNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_enabled="
      <<(simCudaInitialSafeStorePruneIndexShadowEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_calls="
      <<simInitialSafeStorePruneIndexShadowStats.calls<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_seconds="
      <<(static_cast<double>(simInitialSafeStorePruneIndexShadowStats.nanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_scan_seconds="
      <<(static_cast<double>(simInitialSafeStorePruneIndexShadowStats.scanNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_compact_seconds="
      <<(static_cast<double>(simInitialSafeStorePruneIndexShadowStats.compactNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_index_rebuild_seconds="
      <<(static_cast<double>(simInitialSafeStorePruneIndexShadowStats.indexRebuildNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_states_scanned="
      <<simInitialSafeStorePruneIndexShadowStats.statesScanned<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_states_kept="
      <<simInitialSafeStorePruneIndexShadowStats.statesKept<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_states_removed="
      <<simInitialSafeStorePruneIndexShadowStats.statesRemoved<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_removed_ratio="
      <<(simInitialSafeStorePruneIndexShadowStats.statesScanned == 0
           ? 0.0
           : static_cast<double>(simInitialSafeStorePruneIndexShadowStats.statesRemoved) /
               static_cast<double>(simInitialSafeStorePruneIndexShadowStats.statesScanned))<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_size_mismatches="
      <<simInitialSafeStorePruneIndexShadowStats.sizeMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_candidate_mismatches="
      <<simInitialSafeStorePruneIndexShadowStats.candidateMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_order_mismatches="
      <<simInitialSafeStorePruneIndexShadowStats.orderMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_prune_index_shadow_digest_mismatches="
      <<simInitialSafeStorePruneIndexShadowStats.digestMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_enabled="
      <<(simCudaInitialSafeStorePrecombineShadowEnabledRuntime() ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_calls="
      <<simInitialSafeStorePrecombineShadowStats.calls<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.nanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_build_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.buildNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_alloc_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.allocNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_group_build_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.groupBuildNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_compare_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.compareNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_order_compare_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.orderCompareNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_digest_seconds="
      <<(static_cast<double>(simInitialSafeStorePrecombineShadowStats.digestNanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_size_mismatches="
      <<simInitialSafeStorePrecombineShadowStats.sizeMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_candidate_mismatches="
      <<simInitialSafeStorePrecombineShadowStats.candidateMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_order_mismatches="
      <<simInitialSafeStorePrecombineShadowStats.orderMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_digest_mismatches="
      <<simInitialSafeStorePrecombineShadowStats.digestMismatches<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_input_summaries="
      <<simInitialSafeStorePrecombineShadowStats.inputSummaries<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_unique_states="
      <<simInitialSafeStorePrecombineShadowStats.uniqueStates<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_duplicate_summaries="
      <<simInitialSafeStorePrecombineShadowStats.duplicateSummaries<<endl;
  cerr<<"benchmark.sim_initial_safe_store_precombine_shadow_est_saved_upserts="
      <<simInitialSafeStorePrecombineShadowStats.estSavedUpserts<<endl;
  cerr<<"benchmark.sim_initial_scan_cpu_merge_subtotal_seconds="<<simInitialScanCpuMergeSubtotalSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_diag_seconds="<<simInitialScanDiagSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_online_reduce_seconds="<<simInitialScanOnlineReduceSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_wait_seconds="<<simInitialScanWaitSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_count_copy_seconds="<<simInitialScanCountCopySeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_base_upload_seconds="<<simInitialScanBaseUploadSeconds<<endl;
  cerr<<"benchmark.sim_initial_proposal_select_d2h_seconds="<<simInitialProposalSelectD2HSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_sync_wait_seconds="<<simInitialScanSyncWaitSeconds<<endl;
  cerr<<"benchmark.sim_initial_scan_tail_seconds="<<simInitialScanTailSeconds<<endl;
  cerr<<"benchmark.sim_initial_run_summary_pipeline_seconds="<<simInitialRunSummaryPipelineSeconds<<endl;
  cerr<<"benchmark.sim_initial_hash_reduce_seconds="<<simInitialHashReduceSeconds<<endl;
  cerr<<"benchmark.sim_initial_segmented_reduce_seconds="<<simInitialSegmentedReduceSeconds<<endl;
  cerr<<"benchmark.sim_initial_segmented_compact_seconds="<<simInitialSegmentedCompactSeconds<<endl;
  cerr<<"benchmark.sim_initial_topk_seconds="<<simInitialTopKSeconds<<endl;
  cerr<<"benchmark.sim_initial_segmented_tile_states_total="<<simInitialSegmentedTileStates<<endl;
  cerr<<"benchmark.sim_initial_segmented_grouped_states_total="<<simInitialSegmentedGroupedStates<<endl;
  cerr<<"benchmark.sim_proposal_gpu_seconds="<<simProposalGpuSeconds<<endl;
  cerr<<"benchmark.sim_proposal_traceback_batch_gpu_seconds="<<simProposalTracebackBatchGpuSeconds<<endl;
  cerr<<"benchmark.sim_proposal_post_seconds="<<simProposalPostSeconds<<endl;
  cerr<<"benchmark.sim_locate_seconds="<<simLocateSeconds<<endl;
  cerr<<"benchmark.sim_locate_gpu_seconds="<<simLocateGpuSeconds<<endl;
	  cerr<<"benchmark.sim_region_packed_requests="<<getSimRegionPackedRequestCount()<<endl;
	  SimRegionSchedulerShapeTelemetryStats simRegionSchedulerShapeStats;
	  getSimRegionSchedulerShapeTelemetryStats(simRegionSchedulerShapeStats);
	  cerr<<"benchmark.sim_region_scheduler_shape_telemetry_enabled="
	      <<(simRegionSchedulerShapeTelemetryRuntime() ? 1 : 0)<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_calls="
	      <<simRegionSchedulerShapeStats.calls<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_bands="
	      <<simRegionSchedulerShapeStats.bands<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_single_band_calls="
	      <<simRegionSchedulerShapeStats.singleBandCalls<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_affected_starts="
	      <<simRegionSchedulerShapeStats.affectedStarts<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_cells="
	      <<simRegionSchedulerShapeStats.cells<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_max_band_rows="
	      <<simRegionSchedulerShapeStats.maxBandRows<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_max_band_cols="
	      <<simRegionSchedulerShapeStats.maxBandCols<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_mergeable_calls="
	      <<simRegionSchedulerShapeStats.mergeableCalls<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_mergeable_cells="
	      <<simRegionSchedulerShapeStats.mergeableCells<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_est_launch_reduction="
	      <<simRegionSchedulerShapeStats.estimatedLaunchReduction<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_rejected_running_min="
	      <<simRegionSchedulerShapeStats.rejectedRunningMin<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_rejected_safe_store_epoch="
	      <<simRegionSchedulerShapeStats.rejectedSafeStoreEpoch<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_rejected_score_matrix="
	      <<simRegionSchedulerShapeStats.rejectedScoreMatrix<<endl;
	  cerr<<"benchmark.sim_region_scheduler_shape_rejected_filter="
	      <<simRegionSchedulerShapeStats.rejectedFilter<<endl;
	  const char *simRegionBucketedTrueBatchEnv =
	    getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_BUCKETED_TRUE_BATCH");
  cerr<<"benchmark.sim_region_bucketed_true_batch_enabled="
      <<((simRegionBucketedTrueBatchEnv != NULL &&
          simRegionBucketedTrueBatchEnv[0] != '\0' &&
          strcmp(simRegionBucketedTrueBatchEnv,"0") != 0) ? 1 : 0)<<endl;
  uint64_t simRegionBucketedTrueBatchBatches = 0;
  uint64_t simRegionBucketedTrueBatchRequests = 0;
  uint64_t simRegionBucketedTrueBatchFusedRequests = 0;
  uint64_t simRegionBucketedTrueBatchActualCells = 0;
  uint64_t simRegionBucketedTrueBatchPaddedCells = 0;
  uint64_t simRegionBucketedTrueBatchPaddingCells = 0;
  uint64_t simRegionBucketedTrueBatchRejectedPadding = 0;
  uint64_t simRegionBucketedTrueBatchShadowMismatches = 0;
  getSimRegionBucketedTrueBatchStats(simRegionBucketedTrueBatchBatches,
                                     simRegionBucketedTrueBatchRequests,
                                     simRegionBucketedTrueBatchFusedRequests,
                                     simRegionBucketedTrueBatchActualCells,
                                     simRegionBucketedTrueBatchPaddedCells,
                                     simRegionBucketedTrueBatchPaddingCells,
                                     simRegionBucketedTrueBatchRejectedPadding,
                                     simRegionBucketedTrueBatchShadowMismatches);
  cerr<<"benchmark.sim_region_bucketed_true_batch_batches="
      <<simRegionBucketedTrueBatchBatches<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_requests="
      <<simRegionBucketedTrueBatchRequests<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_fused_requests="
      <<simRegionBucketedTrueBatchFusedRequests<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_actual_cells="
      <<simRegionBucketedTrueBatchActualCells<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_padded_cells="
      <<simRegionBucketedTrueBatchPaddedCells<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_padding_cells="
      <<simRegionBucketedTrueBatchPaddingCells<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_rejected_padding="
      <<simRegionBucketedTrueBatchRejectedPadding<<endl;
  cerr<<"benchmark.sim_region_bucketed_true_batch_shadow_mismatches="
      <<simRegionBucketedTrueBatchShadowMismatches<<endl;
  const char *simRegionSingleRequestDirectReduceEnv =
    getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE");
  const char *simRegionSingleRequestDirectReduceShadowEnv =
    getenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE_SHADOW");
  const char *simRegionDirectReduceDeferredCountsEnv =
    getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS");
  const char *simRegionDeferredCountValidateEnv =
    getenv("LONGTARGET_SIM_CUDA_REGION_DEFERRED_COUNTS_VALIDATE");
  const char *simRegionDirectReducePipelineTelemetryEnv =
    getenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY");
  const char *simRegionDirectReduceFusedDpEnv =
    getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP");
  const char *simRegionDirectReduceFusedDpShadowEnv =
    getenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_SHADOW");
  const char *simRegionDirectReduceCoopDpEnv =
    getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP");
  const char *simRegionDirectReduceCoopDpShadowEnv =
    getenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_SHADOW");
  cerr<<"benchmark.sim_region_single_request_direct_reduce_enabled="
      <<((simRegionSingleRequestDirectReduceEnv != NULL &&
          simRegionSingleRequestDirectReduceEnv[0] != '\0' &&
          strcmp(simRegionSingleRequestDirectReduceEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_deferred_counts_enabled="
      <<((simRegionDirectReduceDeferredCountsEnv != NULL &&
          simRegionDirectReduceDeferredCountsEnv[0] != '\0' &&
          strcmp(simRegionDirectReduceDeferredCountsEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_enabled="
      <<((simRegionDeferredCountValidateEnv != NULL &&
          simRegionDeferredCountValidateEnv[0] != '\0' &&
          strcmp(simRegionDeferredCountValidateEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_shadow_enabled="
      <<((simRegionSingleRequestDirectReduceShadowEnv != NULL &&
          simRegionSingleRequestDirectReduceShadowEnv[0] != '\0' &&
          strcmp(simRegionSingleRequestDirectReduceShadowEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_telemetry_enabled="
      <<((simRegionDirectReducePipelineTelemetryEnv != NULL &&
          simRegionDirectReducePipelineTelemetryEnv[0] != '\0' &&
          strcmp(simRegionDirectReducePipelineTelemetryEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_enabled="
      <<((simRegionDirectReduceFusedDpEnv != NULL &&
          simRegionDirectReduceFusedDpEnv[0] != '\0' &&
          strcmp(simRegionDirectReduceFusedDpEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_shadow_enabled="
      <<((simRegionDirectReduceFusedDpShadowEnv != NULL &&
          simRegionDirectReduceFusedDpShadowEnv[0] != '\0' &&
          strcmp(simRegionDirectReduceFusedDpShadowEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_enabled="
      <<((simRegionDirectReduceCoopDpEnv != NULL &&
          simRegionDirectReduceCoopDpEnv[0] != '\0' &&
          strcmp(simRegionDirectReduceCoopDpEnv,"0") != 0) ? 1 : 0)<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_shadow_enabled="
      <<((simRegionDirectReduceCoopDpShadowEnv != NULL &&
          simRegionDirectReduceCoopDpShadowEnv[0] != '\0' &&
          strcmp(simRegionDirectReduceCoopDpShadowEnv,"0") != 0) ? 1 : 0)<<endl;
  uint64_t simRegionSingleRequestDirectReduceAttempts = 0;
  uint64_t simRegionSingleRequestDirectReduceSuccesses = 0;
  uint64_t simRegionSingleRequestDirectReduceFallbacks = 0;
  uint64_t simRegionSingleRequestDirectReduceOverflows = 0;
  uint64_t simRegionSingleRequestDirectReduceShadowMismatches = 0;
  uint64_t simRegionSingleRequestDirectReduceHashCapacityMax = 0;
  uint64_t simRegionSingleRequestDirectReduceCandidates = 0;
  uint64_t simRegionSingleRequestDirectReduceEvents = 0;
  uint64_t simRegionSingleRequestDirectReduceRunSummaries = 0;
  double simRegionSingleRequestDirectReduceGpuSeconds = 0.0;
  double simRegionSingleRequestDirectReduceDpGpuSeconds = 0.0;
  double simRegionSingleRequestDirectReduceFilterReduceGpuSeconds = 0.0;
  double simRegionSingleRequestDirectReduceCompactGpuSeconds = 0.0;
  double simRegionSingleRequestDirectReduceCountD2HSeconds = 0.0;
  double simRegionSingleRequestDirectReduceCandidateCountD2HSeconds = 0.0;
  double simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds = 0.0;
  uint64_t simRegionSingleRequestDirectReduceAffectedStarts = 0;
  uint64_t simRegionSingleRequestDirectReduceReduceWorkItems = 0;
  getSimRegionSingleRequestDirectReduceStats(
    simRegionSingleRequestDirectReduceAttempts,
    simRegionSingleRequestDirectReduceSuccesses,
    simRegionSingleRequestDirectReduceFallbacks,
    simRegionSingleRequestDirectReduceOverflows,
    simRegionSingleRequestDirectReduceShadowMismatches,
    simRegionSingleRequestDirectReduceHashCapacityMax,
    simRegionSingleRequestDirectReduceCandidates,
    simRegionSingleRequestDirectReduceEvents,
    simRegionSingleRequestDirectReduceRunSummaries,
    simRegionSingleRequestDirectReduceGpuSeconds,
    simRegionSingleRequestDirectReduceDpGpuSeconds,
    simRegionSingleRequestDirectReduceFilterReduceGpuSeconds,
    simRegionSingleRequestDirectReduceCompactGpuSeconds,
    simRegionSingleRequestDirectReduceCountD2HSeconds,
    simRegionSingleRequestDirectReduceCandidateCountD2HSeconds,
    simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds,
    simRegionSingleRequestDirectReduceAffectedStarts,
    simRegionSingleRequestDirectReduceReduceWorkItems);
  SimRegionSingleRequestDirectReducePipelineStats simRegionDirectReducePipelineStats;
  getSimRegionSingleRequestDirectReducePipelineStats(simRegionDirectReducePipelineStats);
  SimRegionSingleRequestDirectReduceFusedDpStats simRegionDirectReduceFusedDpStats;
  getSimRegionSingleRequestDirectReduceFusedDpStats(simRegionDirectReduceFusedDpStats);
  SimRegionSingleRequestDirectReduceCoopDpStats simRegionDirectReduceCoopDpStats;
  getSimRegionSingleRequestDirectReduceCoopDpStats(simRegionDirectReduceCoopDpStats);
  const SimRegionDeferredCountValidateStats simRegionDeferredCountValidateStats =
    getSimRegionDeferredCountValidateStats();
  cerr<<"benchmark.sim_region_single_request_direct_reduce_attempts="
      <<simRegionSingleRequestDirectReduceAttempts<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_successes="
      <<simRegionSingleRequestDirectReduceSuccesses<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fallbacks="
      <<simRegionSingleRequestDirectReduceFallbacks<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_overflows="
      <<simRegionSingleRequestDirectReduceOverflows<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_shadow_mismatches="
      <<simRegionSingleRequestDirectReduceShadowMismatches<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_hash_capacity_max="
      <<simRegionSingleRequestDirectReduceHashCapacityMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_candidates="
      <<simRegionSingleRequestDirectReduceCandidates<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_events="
      <<simRegionSingleRequestDirectReduceEvents<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_run_summaries="
      <<simRegionSingleRequestDirectReduceRunSummaries<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_gpu_seconds="
      <<simRegionSingleRequestDirectReduceGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_dp_gpu_seconds="
      <<simRegionSingleRequestDirectReduceDpGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_filter_reduce_gpu_seconds="
      <<simRegionSingleRequestDirectReduceFilterReduceGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_compact_gpu_seconds="
      <<simRegionSingleRequestDirectReduceCompactGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_count_d2h_seconds="
      <<simRegionSingleRequestDirectReduceCountD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_candidate_count_d2h_seconds="
      <<simRegionSingleRequestDirectReduceCandidateCountD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_deferred_count_snapshot_d2h_seconds="
      <<simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_calls="
      <<simRegionDeferredCountValidateStats.calls<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_seconds="
      <<(static_cast<double>(simRegionDeferredCountValidateStats.nanoseconds) / 1.0e9)<<endl;
  cerr<<"benchmark.sim_region_deferred_count_event_mismatches="
      <<simRegionDeferredCountValidateStats.eventMismatches<<endl;
  cerr<<"benchmark.sim_region_deferred_count_run_mismatches="
      <<simRegionDeferredCountValidateStats.runMismatches<<endl;
  cerr<<"benchmark.sim_region_deferred_count_candidate_mismatches="
      <<simRegionDeferredCountValidateStats.candidateMismatches<<endl;
  cerr<<"benchmark.sim_region_deferred_count_total_mismatches="
      <<simRegionDeferredCountValidateStats.totalMismatches<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_fallbacks="
      <<simRegionDeferredCountValidateStats.fallbacks<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_scalar_copies="
      <<simRegionDeferredCountValidateStats.scalarCopies<<endl;
  cerr<<"benchmark.sim_region_deferred_count_validate_snapshot_copies="
      <<simRegionDeferredCountValidateStats.snapshotCopies<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_affected_starts="
      <<simRegionSingleRequestDirectReduceAffectedStarts<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_reduce_work_items="
      <<simRegionSingleRequestDirectReduceReduceWorkItems<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_attempts="
      <<simRegionDirectReduceFusedDpStats.attempts<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_eligible="
      <<simRegionDirectReduceFusedDpStats.eligible<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_successes="
      <<simRegionDirectReduceFusedDpStats.successes<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_fallbacks="
      <<simRegionDirectReduceFusedDpStats.fallbacks<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_shadow_mismatches="
      <<simRegionDirectReduceFusedDpStats.shadowMismatches<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_rejected_by_cells="
      <<simRegionDirectReduceFusedDpStats.rejectedByCells<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_rejected_by_diag_len="
      <<simRegionDirectReduceFusedDpStats.rejectedByDiagLen<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_cells="
      <<simRegionDirectReduceFusedDpStats.cells<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_requests="
      <<simRegionDirectReduceFusedDpStats.requests<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_diag_launches_replaced="
      <<simRegionDirectReduceFusedDpStats.diagLaunchesReplaced<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_gpu_seconds="
      <<simRegionDirectReduceFusedDpStats.fusedDpGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_dp_oracle_gpu_seconds_shadow="
      <<simRegionDirectReduceFusedDpStats.oracleDpGpuSecondsShadow<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_fused_total_gpu_seconds="
      <<simRegionDirectReduceFusedDpStats.fusedTotalGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_supported="
      <<simRegionDirectReduceCoopDpStats.supported<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_attempts="
      <<simRegionDirectReduceCoopDpStats.attempts<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_eligible="
      <<simRegionDirectReduceCoopDpStats.eligible<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_successes="
      <<simRegionDirectReduceCoopDpStats.successes<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_fallbacks="
      <<simRegionDirectReduceCoopDpStats.fallbacks<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_shadow_mismatches="
      <<simRegionDirectReduceCoopDpStats.shadowMismatches<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_rejected_by_unsupported="
      <<simRegionDirectReduceCoopDpStats.rejectedByUnsupported<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_rejected_by_cells="
      <<simRegionDirectReduceCoopDpStats.rejectedByCells<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_rejected_by_diag_len="
      <<simRegionDirectReduceCoopDpStats.rejectedByDiagLen<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_rejected_by_residency="
      <<simRegionDirectReduceCoopDpStats.rejectedByResidency<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_cells="
      <<simRegionDirectReduceCoopDpStats.cells<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_requests="
      <<simRegionDirectReduceCoopDpStats.requests<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_diag_launches_replaced="
      <<simRegionDirectReduceCoopDpStats.diagLaunchesReplaced<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_gpu_seconds="
      <<simRegionDirectReduceCoopDpStats.coopDpGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_dp_oracle_gpu_seconds_shadow="
      <<simRegionDirectReduceCoopDpStats.oracleDpGpuSecondsShadow<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_coop_total_gpu_seconds="
      <<simRegionDirectReduceCoopDpStats.coopTotalGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_requests="
      <<simRegionDirectReducePipelineStats.requestCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_rows="
      <<simRegionDirectReducePipelineStats.rowCountTotal<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_rows_max="
      <<simRegionDirectReducePipelineStats.rowCountMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_cols="
      <<simRegionDirectReducePipelineStats.colCountTotal<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_cols_max="
      <<simRegionDirectReducePipelineStats.colCountMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_cells="
      <<simRegionDirectReducePipelineStats.cellCountTotal<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_cells_max="
      <<simRegionDirectReducePipelineStats.cellCountMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_diags="
      <<simRegionDirectReducePipelineStats.diagCountTotal<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_diags_max="
      <<simRegionDirectReducePipelineStats.diagCountMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_filter_starts="
      <<simRegionDirectReducePipelineStats.filterStartCountTotal<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_filter_starts_max="
      <<simRegionDirectReducePipelineStats.filterStartCountMax<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_diag_launches="
      <<simRegionDirectReducePipelineStats.diagLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_event_count_launches="
      <<simRegionDirectReducePipelineStats.eventCountLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_event_prefix_launches="
      <<simRegionDirectReducePipelineStats.eventPrefixLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_count_launches="
      <<simRegionDirectReducePipelineStats.runCountLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_prefix_launches="
      <<simRegionDirectReducePipelineStats.runPrefixLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_compact_launches="
      <<simRegionDirectReducePipelineStats.runCompactLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_filter_reduce_launches="
      <<simRegionDirectReducePipelineStats.filterReduceLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_candidate_prefix_launches="
      <<simRegionDirectReducePipelineStats.candidatePrefixLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_candidate_compact_launches="
      <<simRegionDirectReducePipelineStats.candidateCompactLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_count_snapshot_launches="
      <<simRegionDirectReducePipelineStats.countSnapshotLaunchCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_lt_1ms="
      <<simRegionDirectReducePipelineStats.dpLt1msCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_1_to_5ms="
      <<simRegionDirectReducePipelineStats.dp1To5msCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_5_to_10ms="
      <<simRegionDirectReducePipelineStats.dp5To10msCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_10_to_50ms="
      <<simRegionDirectReducePipelineStats.dp10To50msCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_gte_50ms="
      <<simRegionDirectReducePipelineStats.dpGte50msCount<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_dp_max_seconds="
      <<simRegionDirectReducePipelineStats.dpMaxSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_metadata_h2d_seconds="
      <<simRegionDirectReducePipelineStats.metadataH2DSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_diag_gpu_seconds="
      <<simRegionDirectReducePipelineStats.diagGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_event_count_gpu_seconds="
      <<simRegionDirectReducePipelineStats.eventCountGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_event_count_d2h_seconds="
      <<simRegionDirectReducePipelineStats.eventCountD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_event_prefix_gpu_seconds="
      <<simRegionDirectReducePipelineStats.eventPrefixGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_count_gpu_seconds="
      <<simRegionDirectReducePipelineStats.runCountGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_count_d2h_seconds="
      <<simRegionDirectReducePipelineStats.runCountD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_prefix_gpu_seconds="
      <<simRegionDirectReducePipelineStats.runPrefixGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_run_compact_gpu_seconds="
      <<simRegionDirectReducePipelineStats.runCompactGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_candidate_prefix_gpu_seconds="
      <<simRegionDirectReducePipelineStats.candidatePrefixGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_candidate_compact_gpu_seconds="
      <<simRegionDirectReducePipelineStats.candidateCompactGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_count_snapshot_d2h_seconds="
      <<simRegionDirectReducePipelineStats.countSnapshotD2HSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_accounted_gpu_seconds="
      <<simRegionDirectReducePipelineStats.accountedGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_single_request_direct_reduce_pipeline_unaccounted_gpu_seconds="
      <<simRegionDirectReducePipelineStats.unaccountedGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_scan_gpu_seconds="<<simRegionScanGpuSeconds<<endl;
  cerr<<"benchmark.sim_region_d2h_seconds="<<simRegionD2HSeconds<<endl;
  cerr<<"benchmark.sim_materialize_seconds="<<simMaterializeSeconds<<endl;
  cerr<<"benchmark.sim_traceback_dp_seconds="<<simTracebackDpSeconds<<endl;
  cerr<<"benchmark.sim_traceback_post_seconds="<<simTracebackPostSeconds<<endl;

  cerr<<"benchmark.calc_score_backend="<<metrics.thresholdBackend<<endl;
  cerr<<"benchmark.calc_score_seconds="<<metrics.thresholdSeconds<<endl;
  cerr<<"benchmark.calc_score_tasks_total="<<metrics.calcScoreTasksTotal<<endl;
  cerr<<"benchmark.calc_score_cuda_tasks="<<metrics.calcScoreCudaTasks<<endl;
  cerr<<"benchmark.calc_score_cpu_fallback_tasks="<<metrics.calcScoreCpuFallbackTasks<<endl;
  cerr<<"benchmark.calc_score_cpu_fallback_query_gt_8192="<<metrics.calcScoreCpuFallbackQueryGt8192<<endl;
  cerr<<"benchmark.calc_score_cpu_fallback_target_gt_8192="<<metrics.calcScoreCpuFallbackTargetGt8192<<endl;
  cerr<<"benchmark.calc_score_cpu_fallback_target_gt_65535="<<metrics.calcScoreCpuFallbackTargetGt65535<<endl;
  cerr<<"benchmark.calc_score_cpu_fallback_other="<<metrics.calcScoreCpuFallbackOther<<endl;
  cerr<<"benchmark.calc_score_query_length="<<metrics.calcScoreQueryLength<<endl;
  cerr<<"benchmark.calc_score_target_bin_le_8192_tasks="<<metrics.calcScoreTargetBinLe8192Tasks<<endl;
  cerr<<"benchmark.calc_score_target_bin_le_8192_bp="<<metrics.calcScoreTargetBinLe8192Bp<<endl;
  cerr<<"benchmark.calc_score_target_bin_8193_65535_tasks="<<metrics.calcScoreTargetBin8193To65535Tasks<<endl;
  cerr<<"benchmark.calc_score_target_bin_8193_65535_bp="<<metrics.calcScoreTargetBin8193To65535Bp<<endl;
  cerr<<"benchmark.calc_score_target_bin_gt_65535_tasks="<<metrics.calcScoreTargetBinGt65535Tasks<<endl;
  cerr<<"benchmark.calc_score_target_bin_gt_65535_bp="<<metrics.calcScoreTargetBinGt65535Bp<<endl;
  cerr<<"benchmark.calc_score_cuda_target_h2d_seconds="<<metrics.calcScoreCudaTargetH2DSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_permutation_h2d_seconds="<<metrics.calcScoreCudaPermutationH2DSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_kernel_seconds="<<metrics.calcScoreCudaKernelSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_score_d2h_seconds="<<metrics.calcScoreCudaScoreD2HSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_sync_wait_seconds="<<metrics.calcScoreCudaSyncWaitSeconds<<endl;
  cerr<<"benchmark.calc_score_host_encode_seconds="<<metrics.calcScoreHostEncodeSeconds<<endl;
  cerr<<"benchmark.calc_score_host_shuffle_plan_seconds="<<metrics.calcScoreHostShufflePlanSeconds<<endl;
  cerr<<"benchmark.calc_score_host_mle_seconds="<<metrics.calcScoreHostMleSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_enabled="<<metrics.calcScoreCudaPipelineV2Enabled<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_shadow_enabled="<<metrics.calcScoreCudaPipelineV2ShadowEnabled<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_used_groups="<<metrics.calcScoreCudaPipelineV2UsedGroups<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_fallbacks="<<metrics.calcScoreCudaPipelineV2Fallbacks<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_shadow_comparisons="<<metrics.calcScoreCudaPipelineV2ShadowComparisons<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_shadow_mismatches="<<metrics.calcScoreCudaPipelineV2ShadowMismatches<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_kernel_seconds="<<metrics.calcScoreCudaPipelineV2KernelSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_score_d2h_seconds="<<metrics.calcScoreCudaPipelineV2ScoreD2HSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_pipeline_v2_host_reduce_seconds="<<metrics.calcScoreCudaPipelineV2HostReduceSeconds<<endl;
  cerr<<"benchmark.calc_score_cuda_groups="<<metrics.calcScoreCudaGroups<<endl;
  cerr<<"benchmark.calc_score_cuda_pairs="<<metrics.calcScoreCudaPairs<<endl;
  cerr<<"benchmark.calc_score_cuda_target_bytes_h2d="<<metrics.calcScoreCudaTargetBytesH2D<<endl;
  cerr<<"benchmark.calc_score_cuda_permutation_bytes_h2d="<<metrics.calcScoreCudaPermutationBytesH2D<<endl;
  cerr<<"benchmark.calc_score_cuda_score_bytes_d2h="<<metrics.calcScoreCudaScoreBytesD2H<<endl;
  cerr<<"benchmark.sim_seconds="<<metrics.simSeconds<<endl;
  cerr<<"benchmark.postprocess_seconds="<<metrics.postProcessSeconds<<endl;
  cerr<<"benchmark.two_stage_discovery_mode="<<metrics.twoStageDiscoveryMode<<endl;
  cerr<<"benchmark.two_stage_discovery_status="<<metrics.twoStageDiscoveryStatus<<endl;
  cerr<<"benchmark.two_stage_discovery_task_count="<<metrics.twoStageDiscoveryTaskCount<<endl;
  cerr<<"benchmark.two_stage_discovery_prefilter_failed_tasks="<<metrics.twoStageDiscoveryPrefilterFailedTasks<<endl;
  cerr<<"benchmark.two_stage_discovery_predicted_skip="<<metrics.twoStageDiscoveryPredictedSkip<<endl;
  cerr<<"benchmark.two_stage_discovery_predicted_skip_tasks="<<metrics.twoStageDiscoveryPredictedSkipTasks<<endl;
  cerr<<"benchmark.two_stage_discovery_prefilter_only_seconds="<<metrics.twoStageDiscoveryPrefilterOnlySeconds<<endl;
  cerr<<"benchmark.two_stage_discovery_gate_seconds="<<metrics.twoStageDiscoveryGateSeconds<<endl;
  cerr<<"benchmark.total_seconds="<<metrics.totalSeconds<<endl;
}
int main(int argc, char* const* argv)
{
  struct para paraList;
  vector<struct  lgInfo>  lgList;
  initEnv(argc,argv,paraList);
  char c_dd_tmp[10];
  char c_length_tmp[10];
  int c_loop_tmp=0;
  string c_tmp_dd;
  string c_tmp_length;
  sprintf(c_dd_tmp,"%d",paraList.cDistance);
  sprintf(c_length_tmp,"%d",paraList.cLength);
  for(c_loop_tmp=0;c_loop_tmp<strlen(c_dd_tmp);c_loop_tmp++)
  {
    c_tmp_dd+=c_dd_tmp[c_loop_tmp];
  }
  for(c_loop_tmp=0;c_loop_tmp<strlen(c_length_tmp);c_loop_tmp++)
  {
    c_tmp_length+=c_length_tmp[c_loop_tmp];
  }
  string lncName;
  string lncSeq;
  string species;
  string dnaChroTag;
  string fileName;
  string dnaSeq;
  string resultDir;
  string startGenomeTmp;
  long   startGenome;
  dnaSeq=readDna(paraList.file1path,species,dnaChroTag,startGenomeTmp);
  startGenome=atoi(startGenomeTmp.c_str());
  lncSeq=readRna(paraList.file2path,lncName);
  fileName=paraList.file1path.substr(0,paraList.file1path.size()-3);
  lncName.erase(remove(lncName.begin(),lncName.end(),'\r'),lncName.end());
  lncName.erase(remove(lncName.begin(),lncName.end(),'\n'),lncName.end());
  resultDir=paraList.outpath;
  struct lgInfo algInfo;
  algInfo=lgInfo(lncName,lncSeq,species,dnaChroTag,fileName,dnaSeq,startGenome,resultDir);
  lgList.push_back(algInfo);
  int i=0;
  vector<struct triplex> sort_triplex_list;
  LongTargetExecutionMetrics metrics;
  const bool benchmarkEnabled = longtarget_benchmark_enabled();
  const bool discoveryPrefilterOnly =
    exact_sim_two_stage_enabled_runtime() &&
    exact_sim_two_stage_discovery_mode_runtime() == EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_PREFILTER_ONLY;
  const double totalStart = benchmarkEnabled ? longtarget_now_seconds() : 0.0;
  LongTarget(paraList,lgList[i].lncSeq,lgList[i].dnaSeq,sort_triplex_list,&metrics);
  if(!discoveryPrefilterOnly)
  {
    const double postProcessStart = benchmarkEnabled ? longtarget_now_seconds() : 0.0;
    printResult(lgList[i].species,paraList,lgList[i].lncName,lgList[i].fileName,sort_triplex_list,lgList[i].dnaChroTag,lgList[i].dnaSeq,lgList[i].startGenome,c_tmp_dd,c_tmp_length,lgList[i].resultDir);
    if(benchmarkEnabled)
    {
      metrics.postProcessSeconds += longtarget_now_seconds() - postProcessStart;
    }
  }
  if(benchmarkEnabled)
  {
    metrics.totalSeconds = longtarget_now_seconds() - totalStart;
    printLongTargetBenchmarkMetrics(metrics);
  }
  if(longtarget_progress_enabled())
  {
    cerr<<"finished normally"<<endl;
  }
  return 0;
}

void cutSequence(string& seq, vector<string>& seqsVec, vector<int>& seqsStartPos, int& cutLength, int& overlapLength,int &cut_num)
{
	unsigned int pos=0;
  int tmpa=0;
  int tmpb=0;
  seqsVec.clear();seqsStartPos.clear();
	string cutSeq;
  while(pos<seq.size())
	{
		cutSeq = seq.substr(pos,cutLength);
		seqsVec.push_back(cutSeq);
		seqsStartPos.push_back(pos);
		pos += cutLength;
		pos -= overlapLength;
    tmpa++;
	}
  cut_num=tmpa;
}
string readRna(string rnaFileName,string &lncName)
{
  ifstream rnaFile;
  string tmpRNA;
  string tmpStr;
  rnaFile.open(rnaFileName.c_str());
  getline(rnaFile,tmpStr);
  int i=0;
  string tmpInfo;
  for(i=0;i<tmpStr.size();i++)
  {
  	if(tmpStr[i]=='>')
  	{
  		continue;
  	}
  	tmpInfo=tmpInfo+tmpStr[i];
  }
  lncName=tmpInfo;
  if(longtarget_progress_enabled())
  {
    cerr<<lncName<<endl;
  }
  while(getline(rnaFile,tmpStr))
  {
    tmpRNA=tmpRNA+tmpStr;
  }
  return tmpRNA;
}
string readDna(string dnaFileName,string &species,string &chroTag,string &startGenome)
{
  ifstream dnaFile;
  string tmpDNA;
  string tmpStr;
  dnaFile.open(dnaFileName.c_str());
  getline(dnaFile,tmpStr);
  int i=0;
  int j=0;
  string tmpInfo;
  for(i=0;i<tmpStr.size();i++)
  {
    if(tmpStr[i]=='>')
    {
      continue;
    }
    if(tmpStr[i]=='|' &&j==0)
    {
      species=tmpInfo;
      j++;
      tmpInfo.clear();
      continue;
    }
    if(tmpStr[i]=='|'&&j==1)
    {
      chroTag=tmpInfo;
      j++;
      tmpInfo.clear();
      continue;
    }
    if(tmpStr[i]=='-'&&j==2)
    {
      startGenome=tmpInfo;
      tmpInfo.clear();
      continue;
    }
    tmpInfo=tmpInfo+tmpStr[i];
  }
  if(longtarget_progress_enabled())
  {
    cerr<<species<<endl;
    cerr<<chroTag<<endl;
    cerr<<startGenome<<endl;
  }
  while(getline(dnaFile,tmpStr))
  {
    tmpDNA=tmpDNA+tmpStr;
  }
  return tmpDNA;
}

void initEnv(int argc,char * const *argv,struct para &paraList)
{
  const char* optstring = "f:s:r:O:c:m:t:i:S:o:y:z:Y:Z:h:D:E:d";
	struct option long_options[]={
		{"f1",required_argument,NULL,'f'},
		{"f2",required_argument,NULL,'s'},
		{"ni",required_argument,NULL,'y'},
    {"na",required_argument,NULL,'z'},
    {"pc",required_argument,NULL,'Y'},
    {"pt",required_argument,NULL,'Z'},
    {"ds",required_argument,NULL,'D'},
    {"lg",required_argument,NULL,'E'},
    {0,0,0,0}
	};
  paraList.file1path="./";
  paraList.file2path="./";
  paraList.outpath="./";
  paraList.rule=0;
  paraList.cutLength=5000;
  paraList.strand=0;
  paraList.overlapLength=100;
  paraList.minScore=0;
	paraList.detailOutput=false;
  paraList.ntMin=20;
  paraList.ntMax=100000;
  paraList.scoreMin=0.0;
  paraList.minIdentity=60.0;
  paraList.minStability=1.0;
  paraList.penaltyT=-1000;
  paraList.penaltyC=0;
	paraList.cDistance=15;
  paraList.cLength=50;
  int opt;
  if(argc==1)
  {
    show_help();
  }
	while( (opt = getopt_long_only( argc, argv, optstring, long_options, NULL)) != -1 )
	{
		switch(opt)
		{
		case 'f':
			paraList.file1path = optarg;
			break;
		case 's':
			paraList.file2path = optarg;
			break;
		case 'r':
			paraList.rule = atoi(optarg);
			break;
		case 'O':
			paraList.outpath = optarg;
			break;
		case 'c':
			paraList.cutLength = atoi(optarg);
			break;
		case 'm':
			paraList.minScore = atoi(optarg);
			break;
		case 't':
			paraList.strand = atoi(optarg);
			break;
		case 'd':
			paraList.detailOutput = true;
			break;
    case 'i':
      paraList.minIdentity=atoi(optarg);
      break;
    case 'S':
      paraList.minStability=atoi(optarg);
      break;
    case 'y':
      paraList.ntMin=atoi(optarg);
      break;
    case 'z':
      paraList.ntMax=atoi(optarg);
      break;
    case 'Y':
      paraList.penaltyC=atoi(optarg);
      break;
    case 'Z':
      paraList.penaltyT=atoi(optarg);
      break;
    case 'o':
      paraList.overlapLength=atoi(optarg);
      break;
    case 'h':
      show_help();
      break;
    case 'D':
      paraList.cDistance=atoi(optarg);
      break;
    case 'E':
      paraList.cLength=atoi(optarg);
      break;
		}
	}
}
void LongTarget(struct para &paraList,string rnaSequence,string dnaSequence,vector<struct triplex>&sort_triplex_list,LongTargetExecutionMetrics *metrics)
{
  if(metrics != NULL)
  {
    metrics->calcScoreCudaPipelineV2Enabled = longtarget_calc_score_cuda_pipeline_v2_enabled() ? 1 : 0;
    metrics->calcScoreCudaPipelineV2ShadowEnabled = longtarget_calc_score_cuda_pipeline_v2_shadow_enabled() ? 1 : 0;
  }
	vector< string> dnaSequencesVec;
	vector< int> dnaSequencesStartPos;
  int cut_num=0;
	cutSequence(dnaSequence,dnaSequencesVec,dnaSequencesStartPos,paraList.cutLength,paraList.overlapLength,cut_num);
  vector<ExactFragmentInfo> fragments;
  vector<ExactSimTaskSpec> tasks;
  ExactSimConfig exactSimConfig;

  fragments.reserve(dnaSequencesVec.size());
  tasks.reserve(dnaSequencesVec.size() * 48);
	for(int i=0;i<dnaSequencesVec.size();i++)
	{
		long dnaStartPos = dnaSequencesStartPos[i];
	  if(longtarget_progress_enabled())
	  {
	    cerr<<"dnaPos="<<dnaStartPos<<endl;
	  }
    string &seq1=dnaSequencesVec[i];
    const bool skipFragment = same_seq(seq1) != 0;
    fragments.push_back(ExactFragmentInfo(seq1,dnaStartPos,skipFragment));
		if(skipFragment)
    {
      continue;
    }
    if(paraList.strand>=0)
		{
			if(paraList.rule==0)
			{
        appendExactSimTaskRange(tasks,fragments.size()-1,seq1,dnaStartPos,0,1,1,6);
        appendExactSimTaskRange(tasks,fragments.size()-1,seq1,dnaStartPos,1,1,1,6);
			}
			if(paraList.rule>0&&paraList.rule<7)
			{
        appendExactSimTask(tasks,fragments.size()-1,seq1,dnaStartPos,0,1,paraList.rule);
        appendExactSimTask(tasks,fragments.size()-1,seq1,dnaStartPos,1,1,paraList.rule);
      }
		}
		if(paraList.strand<=0)
		{
			if(paraList.rule==0)
			{
        appendExactSimTaskRange(tasks,fragments.size()-1,seq1,dnaStartPos,0,-1,1,18);
        appendExactSimTaskRange(tasks,fragments.size()-1,seq1,dnaStartPos,1,-1,1,18);
			}
			else
			{
        appendExactSimTask(tasks,fragments.size()-1,seq1,dnaStartPos,0,-1,paraList.rule);
        appendExactSimTask(tasks,fragments.size()-1,seq1,dnaStartPos,1,-1,paraList.rule);
			}
		}
	}

  ExactSimRunContext runContext(rnaSequence);
  runContext.minScoreCache.reserve(tasks.size());
  vector< vector<struct triplex> > taskTriplexLists(tasks.size());
  vector<ExactSimTaskTiming> taskTimings(tasks.size());
  vector<double> taskFilterSeconds(tasks.size(),0.0);
  vector<int> taskWorkerIndices(tasks.size(),-1);

  vector<int> taskMinScores(tasks.size(),0);
  vector<unsigned char> taskMinScoreReady(tasks.size(),0);
  const bool twoStage = exact_sim_two_stage_enabled_runtime();
  const ExactSimTwoStageThresholdMode twoStageThresholdMode = exact_sim_two_stage_threshold_mode_runtime();
  const bool deferredExactTwoStage = twoStage && twoStageThresholdMode == EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_DEFERRED_EXACT;
  const ExactSimTwoStageDiscoveryMode twoStageDiscoveryMode = exact_sim_two_stage_discovery_mode_runtime();
  const bool discoveryPrefilterOnly = twoStageDiscoveryMode == EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_PREFILTER_ONLY;
  const ExactSimTwoStageRejectMode twoStageRejectMode =
    deferredExactTwoStage ? exact_sim_two_stage_reject_mode_runtime() : EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF;
  const ExactSimTwoStageSelectiveFallbackConfig twoStageSelectiveFallbackConfig =
    exact_sim_two_stage_selective_fallback_config_runtime();
  const bool twoStageSelectiveFallbackEnabled =
    deferredExactTwoStage &&
    twoStageRejectMode == EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2 &&
    twoStageSelectiveFallbackConfig.enabled;
  const ExactSimTwoStageTaskRerunConfig twoStageTaskRerunConfig =
    exact_sim_two_stage_task_rerun_config_runtime();
  const bool twoStageTaskRerunEnabled =
    deferredExactTwoStage &&
    twoStageSelectiveFallbackEnabled &&
    twoStageTaskRerunConfig.enabled;
  vector<ExactSimDeferredTwoStagePrefilterResult> deferredPrefilterResults(tasks.size());
  vector<unsigned char> deferredTaskShouldRun(tasks.size(),0);
  vector<unsigned char> taskRerunEffective(tasks.size(),0);
  uint64_t discoveryPrefilterFailedTasks = 0;
  const string twoStageDebugWindowsCsvPath =
    deferredExactTwoStage ? longtarget_two_stage_debug_windows_csv_path_runtime() : "";
  ofstream twoStageDebugWindowsCsv;
  unordered_set<string> twoStageTaskRerunSelectedTaskKeys;

  if(discoveryPrefilterOnly && !deferredExactTwoStage)
  {
    fprintf(stderr,
            "prefilter_only discovery requires LONGTARGET_TWO_STAGE=1 and LONGTARGET_TWO_STAGE_THRESHOLD_MODE=deferred_exact\n");
    exit(2);
  }

  if(deferredExactTwoStage || discoveryPrefilterOnly)
  {
    if(exact_sim_prefilter_backend_requested_runtime() != EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA)
    {
      fprintf(stderr,
              "%s requires LONGTARGET_PREFILTER_BACKEND=prealign_cuda\n",
              discoveryPrefilterOnly ? "prefilter_only discovery" : "deferred_exact");
      exit(2);
    }
    if(exact_sim_prefilter_score_floor_delta_runtime() != 0)
    {
      fprintf(stderr,
              "%s requires LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA=0\n",
              discoveryPrefilterOnly ? "prefilter_only discovery" : "deferred_exact");
      exit(2);
    }
    if(!prealign_cuda_is_built())
    {
      fprintf(stderr,
              "%s requires prealign_cuda support in this build\n",
              discoveryPrefilterOnly ? "prefilter_only discovery" : "deferred_exact");
      exit(2);
    }
  }

  if(metrics != NULL)
  {
    metrics->twoStageThresholdMode = longtarget_two_stage_threshold_mode_label(twoStageThresholdMode);
    metrics->twoStageRejectMode = longtarget_two_stage_reject_mode_label(twoStageRejectMode);
    metrics->twoStageDiscoveryMode = longtarget_two_stage_discovery_mode_label(twoStageDiscoveryMode);
    metrics->twoStageSelectiveFallbackEnabled = twoStageSelectiveFallbackEnabled ? 1u : 0u;
    metrics->twoStageTaskRerunEnabled = twoStageTaskRerunEnabled ? 1u : 0u;
    metrics->twoStageTaskRerunBudget = static_cast<uint64_t>(twoStageTaskRerunConfig.budget);
    metrics->twoStageTaskRerunSelectedTasksPath = twoStageTaskRerunConfig.selectedTasksPath;
  }

  if(twoStageTaskRerunEnabled)
  {
    string loadError;
    if(!longtarget_load_two_stage_task_rerun_selected_task_keys(twoStageTaskRerunConfig.selectedTasksPath,
                                                                twoStageTaskRerunSelectedTaskKeys,
                                                                &loadError))
    {
      fprintf(stderr,
              "failed to load LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH=%s: %s\n",
              twoStageTaskRerunConfig.selectedTasksPath.c_str(),
              loadError.c_str());
      exit(2);
    }
  }

  if(!twoStageDebugWindowsCsvPath.empty())
  {
    twoStageDebugWindowsCsv.open(twoStageDebugWindowsCsvPath.c_str());
    if(!twoStageDebugWindowsCsv.is_open())
    {
      fprintf(stderr,
              "failed to open LONGTARGET_TWO_STAGE_DEBUG_WINDOWS_CSV=%s\n",
              twoStageDebugWindowsCsvPath.c_str());
      exit(2);
    }
    longtarget_write_two_stage_window_trace_header(twoStageDebugWindowsCsv);
  }

  bool usedCudaAny = false;
  bool usedCudaAll = true;
  double cudaThresholdSeconds = 0.0;
  uint64_t deferredThresholdBatchCount = 0;
  uint64_t deferredThresholdBatchTasksTotal = 0;
  uint64_t deferredThresholdBatchSizeMax = 0;
  double deferredThresholdBatchedSeconds = 0.0;
  const int calcScoreQueryLength = static_cast<int>(rnaSequence.size());
  const bool calcScoreTelemetryEnabled = metrics != NULL && longtarget_benchmark_enabled();
  vector<pair<int,size_t> > calcScoreTasksSorted;
  calcScoreTasksSorted.reserve(tasks.size());
  for(size_t taskIndex = 0; taskIndex < tasks.size(); ++taskIndex)
  {
    if(deferredExactTwoStage)
    {
      ExactSimDeferredTwoStagePrefilterResult result;
      vector<ExactSimTwoStageWindowTrace> windowTrace;
      vector<ExactSimTwoStageWindowTrace> *windowTracePtr =
        (twoStageSelectiveFallbackEnabled || twoStageDebugWindowsCsv.is_open()) ? &windowTrace : NULL;
      if(!collectExactSimTwoStageDeferredPrefilterCore(rnaSequence,
                                                       tasks[taskIndex].transformedSequence,
                                                       exactSimConfig,
                                                       result,
                                                       &taskTimings[taskIndex],
                                                       windowTracePtr))
      {
        if(discoveryPrefilterOnly)
        {
          discoveryPrefilterFailedTasks += 1;
          continue;
        }
        fprintf(stderr,
                "deferred_exact prefilter failed for taskIndex=%zu targetLength=%zu\n",
                taskIndex,
                tasks[taskIndex].transformedSequence.size());
        exit(2);
      }
      if(twoStageDebugWindowsCsv.is_open())
      {
        const ExactSimTaskSpec &task = tasks[taskIndex];
        const size_t fragmentLength = fragments[task.fragmentIndex].sequence.size();
        for(size_t traceIndex = 0; traceIndex < windowTrace.size(); ++traceIndex)
        {
          longtarget_write_two_stage_window_trace_row(twoStageDebugWindowsCsv,
                                                      taskIndex,
                                                      task,
                                                      fragmentLength,
                                                      windowTrace[traceIndex]);
        }
      }
      deferredPrefilterResults[taskIndex] = result;
      if(twoStageTaskRerunEnabled && !twoStageTaskRerunSelectedTaskKeys.empty())
      {
        const ExactSimTaskSpec &task = tasks[taskIndex];
        const size_t fragmentLength = fragments[task.fragmentIndex].sequence.size();
        const string taskKey = longtarget_two_stage_task_rerun_task_key(task,fragmentLength);
        if(twoStageTaskRerunSelectedTaskKeys.find(taskKey) != twoStageTaskRerunSelectedTaskKeys.end())
        {
          ExactSimTwoStageTaskRerunStats taskRerunStats;
          const bool upgraded =
            exact_sim_apply_two_stage_task_rerun_in_place(deferredPrefilterResults[taskIndex],true,&taskRerunStats);
          if(taskRerunStats.selectedTasks > 0 && metrics != NULL)
          {
            metrics->twoStageTaskRerunSelectedTasks += taskRerunStats.selectedTasks;
          }
          if(upgraded)
          {
            taskRerunEffective[taskIndex] = 1;
            taskTimings[taskIndex].refineWindowCount += taskRerunStats.addedWindowCount;
            taskTimings[taskIndex].refineTotalBp += taskRerunStats.addedBpTotal;
            if(metrics != NULL)
            {
              metrics->twoStageTaskRerunEffectiveTasks += taskRerunStats.effectiveTasks;
              metrics->twoStageTaskRerunAddedWindows += taskRerunStats.addedWindowCount;
              metrics->twoStageTaskRerunRefineBpTotal += taskRerunStats.addedBpTotal;
            }
          }
        }
      }
      if(metrics != NULL)
      {
        metrics->twoStageTasksWithAnySeed += result.hadAnySeed ? 1u : 0u;
        metrics->twoStageTasksWithAnyRefineWindowBeforeGate += result.hadAnyRefineWindowBeforeGate ? 1u : 0u;
        metrics->twoStageTasksWithAnyRefineWindowAfterGate += result.hadAnyRefineWindowAfterGate ? 1u : 0u;
        metrics->twoStageWindowsBeforeGate += result.windowsBeforeGate;
        metrics->twoStageWindowsAfterGate += result.windowsAfterGate;
        metrics->twoStageWindowsRejectedByMinPeakScore += result.rejectStats.windowsRejectedByMinPeakScore;
        metrics->twoStageWindowsRejectedBySupport += result.rejectStats.windowsRejectedBySupport;
        metrics->twoStageWindowsRejectedByMargin += result.rejectStats.windowsRejectedByMargin;
        metrics->twoStageWindowsTrimmedByMaxWindows += result.rejectStats.windowsTrimmedByMaxWindows;
        metrics->twoStageWindowsTrimmedByMaxBp += result.rejectStats.windowsTrimmedByMaxBp;
        metrics->twoStageSingletonRescuedWindows += result.rejectStats.singletonRescuedWindows;
        metrics->twoStageSingletonRescuedTasks += result.rejectStats.singletonRescuedTasks;
        metrics->twoStageSingletonRescueBpTotal += result.rejectStats.singletonRescueBpTotal;
        metrics->twoStageSelectiveFallbackTriggeredTasks += result.rejectStats.selectiveFallbackTriggeredTasks;
        metrics->twoStageSelectiveFallbackNonEmptyCandidateTasks += result.rejectStats.selectiveFallbackNonEmptyCandidateTasks;
        metrics->twoStageSelectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks += result.rejectStats.selectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks;
        metrics->twoStageSelectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks += result.rejectStats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks;
        metrics->twoStageSelectiveFallbackNonEmptyRejectedBySingletonOverrideTasks += result.rejectStats.selectiveFallbackNonEmptyRejectedBySingletonOverrideTasks;
        metrics->twoStageSelectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks += result.rejectStats.selectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks;
        metrics->twoStageSelectiveFallbackNonEmptyRejectedByScoreGapTasks += result.rejectStats.selectiveFallbackNonEmptyRejectedByScoreGapTasks;
        metrics->twoStageSelectiveFallbackNonEmptyTriggeredTasks += result.rejectStats.selectiveFallbackNonEmptyTriggeredTasks;
        metrics->twoStageSelectiveFallbackSelectedWindows += result.rejectStats.selectiveFallbackSelectedWindows;
        metrics->twoStageSelectiveFallbackSelectedBpTotal += result.rejectStats.selectiveFallbackSelectedBpTotal;
        if(!result.hadAnySeed)
        {
          metrics->twoStageThresholdSkippedNoSeedTasks += 1;
        }
        else if(!result.hadAnyRefineWindowBeforeGate)
        {
          metrics->twoStageThresholdSkippedNoRefineWindowTasks += 1;
        }
        else if(deferredPrefilterResults[taskIndex].windows.empty())
        {
          metrics->twoStageThresholdSkippedAfterGateTasks += 1;
        }
      }
      if(!deferredPrefilterResults[taskIndex].windows.empty())
      {
        deferredTaskShouldRun[taskIndex] = 1;
        calcScoreTasksSorted.push_back(make_pair(static_cast<int>(tasks[taskIndex].transformedSequence.size()), taskIndex));
      }
      continue;
    }
    calcScoreTasksSorted.push_back(make_pair(static_cast<int>(tasks[taskIndex].transformedSequence.size()), taskIndex));
  }
  if(discoveryPrefilterOnly)
  {
    if(metrics != NULL)
    {
      metrics->thresholdBackend = "skipped";
      metrics->twoStageDiscoveryTaskCount = static_cast<uint64_t>(tasks.size());
      metrics->twoStageDiscoveryPrefilterFailedTasks = discoveryPrefilterFailedTasks;
      metrics->twoStageDiscoveryPredictedSkipTasks = metrics->twoStageThresholdSkippedAfterGateTasks;
      for(size_t taskIndex = 0; taskIndex < taskTimings.size(); ++taskIndex)
      {
        metrics->prefilterBackend =
          longtarget_merge_prefilter_backend(metrics->prefilterBackend, taskTimings[taskIndex].prefilterBackend);
        metrics->prefilterHits += taskTimings[taskIndex].prefilterHits;
        metrics->twoStageDiscoveryPrefilterOnlySeconds += taskTimings[taskIndex].prefilterSeconds;
        metrics->twoStageDiscoveryGateSeconds += taskTimings[taskIndex].twoStageGateSeconds;
      }
      const ExactSimTwoStageDiscoverySummary discoverySummary =
        longtarget_build_two_stage_discovery_summary(tasks.size(), discoveryPrefilterFailedTasks, *metrics);
      metrics->twoStageDiscoveryStatus =
        exact_sim_two_stage_discovery_status_label(
          exact_sim_two_stage_discovery_status_from_summary(discoverySummary));
      metrics->twoStageDiscoveryPredictedSkip =
        exact_sim_two_stage_discovery_predicted_skip(discoverySummary) ? 1u : 0u;
    }
    return;
  }
  sort(calcScoreTasksSorted.begin(),calcScoreTasksSorted.end());

  if(metrics != NULL)
  {
    metrics->calcScoreTasksTotal += static_cast<uint64_t>(calcScoreTasksSorted.size());
    metrics->calcScoreQueryLength = static_cast<uint64_t>(calcScoreQueryLength);
    for(size_t sortedIndex = 0; sortedIndex < calcScoreTasksSorted.size();)
    {
      const int targetLength = calcScoreTasksSorted[sortedIndex].first;
      size_t groupEnd = sortedIndex;
      while(groupEnd < calcScoreTasksSorted.size() && calcScoreTasksSorted[groupEnd].first == targetLength)
      {
        ++groupEnd;
      }
      longtarget_record_calc_score_target_bin(*metrics,
                                              targetLength,
                                              static_cast<uint64_t>(groupEnd - sortedIndex));
      sortedIndex = groupEnd;
    }
  }

  bool calcScoreCoverageRecorded = false;

  if(longtarget_cuda_enabled() && calc_score_cuda_is_built() && !tasks.empty())
  {
    const int cudaDevice = longtarget_cuda_device();
    string cudaError;
    if(calc_score_cuda_init(cudaDevice,&cudaError))
    {
      CalcScoreWorkspace thresholdWorkspace;
      thresholdWorkspace.ensureQueryProfiles(rnaSequence);
      const int queryLength = thresholdWorkspace.queryLength;
      const int segWidth = 32;
      const int segLen = (queryLength + segWidth - 1) / segWidth;
      const int maxQueryLenCuda = 8192;

      if(queryLength > 0 && queryLength <= maxQueryLenCuda && segLen > 0)
      {
        vector<int16_t> profileFwd(static_cast<size_t>(7) * static_cast<size_t>(segLen) * static_cast<size_t>(segWidth),0);
        vector<int16_t> profileRev(static_cast<size_t>(7) * static_cast<size_t>(segLen) * static_cast<size_t>(segWidth),0);

        auto fillProfile = [&](const vector<unsigned char> &encodedQuery, vector<int16_t> &profile)
        {
          for(int targetProfileIndex = 1; targetProfileIndex < 7; ++targetProfileIndex)
          {
            const unsigned char targetCode = calc_score_profile_code_for_index(targetProfileIndex);
            for(int lane = 0; lane < segWidth; ++lane)
            {
              for(int segIndex = 0; segIndex < segLen; ++segIndex)
              {
                const int queryIndex = lane * segLen + segIndex;
                int16_t score = 0;
                if(queryIndex < queryLength)
                {
                  const unsigned char queryCode = encodedQuery[static_cast<size_t>(queryIndex)];
                  score = static_cast<int16_t>(thresholdWorkspace.pst.pam2[queryCode][targetCode]);
                }
                profile[(static_cast<size_t>(targetProfileIndex) * static_cast<size_t>(segLen) + static_cast<size_t>(segIndex)) *
                          static_cast<size_t>(segWidth) +
                        static_cast<size_t>(lane)] = score;
              }
            }
          }
        };

        fillProfile(thresholdWorkspace.encodedQuery,profileFwd);
        fillProfile(thresholdWorkspace.encodedReverseComplementQuery,profileRev);

        CalcScoreCudaQueryHandle cudaQuery;
        if(calc_score_cuda_prepare_query(&cudaQuery,
                                         profileFwd.data(),
                                         profileRev.data(),
                                         segLen,
                                         queryLength,
                                         &cudaError))
        {
          const CalcScoreTargetBaseLut &targetBaseLut = calc_score_target_base_lut();
          const bool validateCuda = longtarget_cuda_validate_enabled();
          calcScoreCoverageRecorded = true;

          size_t groupStart = 0;
          while(groupStart < calcScoreTasksSorted.size())
          {
            const int targetLength = calcScoreTasksSorted[groupStart].first;
            size_t groupEnd = groupStart;
            while(groupEnd < calcScoreTasksSorted.size() && calcScoreTasksSorted[groupEnd].first == targetLength)
            {
              ++groupEnd;
            }
            const size_t groupSize = groupEnd - groupStart;

            bool groupUsedCuda = false;
            if(targetLength > 0)
            {
              const double shufflePlanStart = calcScoreTelemetryEnabled ? longtarget_now_seconds() : 0.0;
              thresholdWorkspace.ensureShufflePlan(static_cast<size_t>(targetLength));
              if(calcScoreTelemetryEnabled)
              {
                const double shufflePlanSeconds = longtarget_now_seconds() - shufflePlanStart;
                metrics->calcScoreHostShufflePlanSeconds += shufflePlanSeconds;
                cudaThresholdSeconds += shufflePlanSeconds;
              }
              if(thresholdWorkspace.shufflePlanEnabled && thresholdWorkspace.useShortShufflePlan)
              {
                const double hostEncodeStart = calcScoreTelemetryEnabled ? longtarget_now_seconds() : 0.0;
                vector<uint8_t> encodedTargets(groupSize * static_cast<size_t>(targetLength));
                for(size_t groupOffset = 0; groupOffset < groupSize; ++groupOffset)
                {
                  const size_t taskIndex = calcScoreTasksSorted[groupStart + groupOffset].second;
                  const string &target = tasks[taskIndex].transformedSequence;
                  for(int i = 0; i < targetLength; ++i)
                  {
                    encodedTargets[groupOffset * static_cast<size_t>(targetLength) + static_cast<size_t>(i)] =
                      targetBaseLut.lut[static_cast<unsigned char>(target[static_cast<size_t>(i)])];
                  }
                }
                if(calcScoreTelemetryEnabled)
                {
                  const double hostEncodeSeconds = longtarget_now_seconds() - hostEncodeStart;
                  metrics->calcScoreHostEncodeSeconds += hostEncodeSeconds;
                  cudaThresholdSeconds += hostEncodeSeconds;
                }

                vector<int> pairScores;
                CalcScoreCudaBatchResult batchResult;
                const double groupStartSeconds = longtarget_now_seconds();
                if(calc_score_cuda_compute_pair_max_scores(cudaQuery,
                                                          encodedTargets.data(),
                                                          static_cast<int>(groupSize),
                                                          targetLength,
                                                          thresholdWorkspace.shufflePermutations16.data(),
                                                          CALC_SCORE_SHUFFLE_COUNT,
                                                          CALC_SCORE_MLE_COUNT + 1,
                                                          &pairScores,
                                                          &batchResult,
                                                          &cudaError,
                                                          calcScoreTelemetryEnabled))
                {
                  const double groupElapsedSeconds = longtarget_now_seconds() - groupStartSeconds;
                  cudaThresholdSeconds += groupElapsedSeconds;
                  groupUsedCuda = true;
                  usedCudaAny = true;
                  if(metrics != NULL)
                  {
                    longtarget_record_calc_score_cuda_batch_telemetry(*metrics,
                                                                      static_cast<uint64_t>(groupSize),
                                                                      static_cast<uint64_t>(CALC_SCORE_MLE_COUNT + 1),
                                                                      batchResult);
                  }
                  if(deferredExactTwoStage)
                  {
                    deferredThresholdBatchCount += 1;
                    deferredThresholdBatchTasksTotal += static_cast<uint64_t>(groupSize);
                    deferredThresholdBatchSizeMax = std::max(deferredThresholdBatchSizeMax,
                                                            static_cast<uint64_t>(groupSize));
                    deferredThresholdBatchedSeconds += groupElapsedSeconds;
                  }

                  thresholdWorkspace.ensureAa1Length(targetLength);
                  for(size_t groupOffset = 0; groupOffset < groupSize; ++groupOffset)
                  {
                    const double hostMleStart = calcScoreTelemetryEnabled ? longtarget_now_seconds() : 0.0;
                    vector<int> maxScores(static_cast<size_t>(CALC_SCORE_MLE_COUNT));
                    const int *rowScores = &pairScores[groupOffset * static_cast<size_t>(CALC_SCORE_MLE_COUNT + 1)];
                    for(int i = 0; i < CALC_SCORE_MLE_COUNT; ++i)
                    {
                      maxScores[static_cast<size_t>(i)] = rowScores[i];
                    }
                    maxScores[150] = rowScores[CALC_SCORE_MLE_COUNT];

                    double *mle_rst = mle_cen(maxScores.data(),
                                              CALC_SCORE_MLE_COUNT,
                                              thresholdWorkspace.aa1Len,
                                              queryLength,
                                              0.0,
                                              0.0,
                                              0.0);
                    int minScore = 0;
                    if(mle_rst != NULL)
                    {
                      const double lambda_tmp = mle_rst[0];
                      const double K_tmp = mle_rst[1];
                      minScore = static_cast<int>((log(K_tmp * static_cast<double>(targetLength) * static_cast<double>(queryLength)) -
                                                   log(10.0)) /
                                                    lambda_tmp +
                                                  0.5);
                      free(mle_rst);
                    }

                    const size_t taskIndex = calcScoreTasksSorted[groupStart + groupOffset].second;
                    taskMinScores[taskIndex] = minScore;
                    taskMinScoreReady[taskIndex] = 1;
                    if(calcScoreTelemetryEnabled)
                    {
                      const double hostMleSeconds = longtarget_now_seconds() - hostMleStart;
                      metrics->calcScoreHostMleSeconds += hostMleSeconds;
                      cudaThresholdSeconds += hostMleSeconds;
                    }

                    if(validateCuda)
                    {
                      CalcScoreWorkspace cpuWorkspace;
                      const int cpuMinScore = calc_score_with_workspace(rnaSequence, tasks[taskIndex].transformedSequence, cpuWorkspace);
                      if(cpuMinScore != minScore)
                      {
                        fprintf(stderr,
                                "CUDA minScore mismatch taskIndex=%zu targetLength=%d cpu=%d cuda=%d\n",
                                taskIndex,
                                targetLength,
                                cpuMinScore,
                                minScore);
                        abort();
                      }
                    }
                  }
                }
                else
                {
                  cudaThresholdSeconds += longtarget_now_seconds() - groupStartSeconds;
                }
              }
            }

            if(metrics != NULL)
            {
              longtarget_record_calc_score_group_result(*metrics,
                                                        queryLength,
                                                        targetLength,
                                                        static_cast<uint64_t>(groupSize),
                                                        groupUsedCuda);
            }
            if(!groupUsedCuda)
            {
              usedCudaAll = false;
            }

            groupStart = groupEnd;
          }

          calc_score_cuda_release_query(&cudaQuery);
        }
        else
        {
          usedCudaAll = false;
        }
      }
      else
      {
        usedCudaAll = false;
      }
    }
    else
    {
      usedCudaAll = false;
    }
  }
  else if(longtarget_cuda_enabled())
  {
    usedCudaAll = false;
  }

  if(deferredExactTwoStage)
  {
    vector<size_t> deferredCpuBatch;
    deferredCpuBatch.reserve(calcScoreTasksSorted.size());
    for(size_t sortedIndex = 0; sortedIndex < calcScoreTasksSorted.size(); ++sortedIndex)
    {
      const size_t taskIndex = calcScoreTasksSorted[sortedIndex].second;
      if(taskMinScoreReady[taskIndex] == 0)
      {
        deferredCpuBatch.push_back(taskIndex);
      }
    }
    if(!deferredCpuBatch.empty())
    {
      CalcScoreWorkspace deferredCpuWorkspace;
      const double batchStartSeconds = longtarget_now_seconds();
      for(size_t i = 0; i < deferredCpuBatch.size(); ++i)
      {
        const size_t taskIndex = deferredCpuBatch[i];
        taskMinScores[taskIndex] =
          longtarget_prepare_exact_sim_min_score(rnaSequence,
                                                 tasks[taskIndex].transformedSequence,
                                                 runContext,
                                                 deferredCpuWorkspace,
                                                 &taskTimings[taskIndex]);
        taskMinScoreReady[taskIndex] = 1;
      }
      deferredThresholdBatchCount += 1;
      deferredThresholdBatchTasksTotal += static_cast<uint64_t>(deferredCpuBatch.size());
      deferredThresholdBatchSizeMax = std::max(deferredThresholdBatchSizeMax,
                                              static_cast<uint64_t>(deferredCpuBatch.size()));
      deferredThresholdBatchedSeconds += longtarget_now_seconds() - batchStartSeconds;
    }
    if(metrics != NULL)
    {
      metrics->twoStageThresholdInvokedTasks = static_cast<uint64_t>(calcScoreTasksSorted.size());
      metrics->twoStageThresholdBatchCount = deferredThresholdBatchCount;
      metrics->twoStageThresholdBatchTasksTotal = deferredThresholdBatchTasksTotal;
      metrics->twoStageThresholdBatchSizeMax = deferredThresholdBatchSizeMax;
      metrics->twoStageThresholdBatchedSeconds = deferredThresholdBatchedSeconds;
    }
  }

  if(metrics != NULL && !calcScoreCoverageRecorded)
  {
    size_t groupStart = 0;
    while(groupStart < calcScoreTasksSorted.size())
    {
      const int targetLength = calcScoreTasksSorted[groupStart].first;
      size_t groupEnd = groupStart;
      while(groupEnd < calcScoreTasksSorted.size() && calcScoreTasksSorted[groupEnd].first == targetLength)
      {
        ++groupEnd;
      }
      longtarget_record_calc_score_group_result(*metrics,
                                                calcScoreQueryLength,
                                                targetLength,
                                                static_cast<uint64_t>(groupEnd - groupStart),
                                                false);
      groupStart = groupEnd;
    }
  }

  if(metrics != NULL)
  {
    if(usedCudaAny)
    {
      metrics->thresholdBackend = usedCudaAll ? "cuda" : "mixed";
    }
    else
    {
      metrics->thresholdBackend = "cpu";
    }
    metrics->thresholdSeconds += cudaThresholdSeconds;
  }

  if(metrics != NULL && twoStage && !deferredExactTwoStage)
  {
    metrics->twoStageThresholdInvokedTasks = static_cast<uint64_t>(tasks.size());
  }
  const bool simFast = simFastEnabledRuntime();
  const bool validateCuda = simCudaValidateEnabledRuntime();
  const bool windowPipelineRequested = simCudaWindowPipelineEnabledRuntime();
  const bool useWindowPipeline = longtarget_window_pipeline_enabled_runtime(twoStage);
  const bool useWindowPipelineOverlap = longtarget_window_pipeline_overlap_enabled_runtime(useWindowPipeline);
  vector<size_t> taskExecutionOrder;
  taskExecutionOrder.reserve(tasks.size());
  for(size_t taskIndex = 0; taskIndex < tasks.size(); ++taskIndex)
  {
    taskExecutionOrder.push_back(taskIndex);
  }
  if(useWindowPipeline)
  {
    sort(taskExecutionOrder.begin(),
         taskExecutionOrder.end(),
         [&](size_t lhs,size_t rhs)
         {
           const size_t lhsLen = tasks[lhs].transformedSequence.size();
           const size_t rhsLen = tasks[rhs].transformedSequence.size();
           if(lhsLen != rhsLen) return lhsLen < rhsLen;
           return lhs < rhs;
         });
  }
  const vector<SimCudaWorkerAssignment> cudaWorkerAssignments = longtarget_cuda_worker_assignments_runtime();
  if(!cudaWorkerAssignments.empty())
  {
    atomic<size_t> nextTask(0);
    vector<thread> workers;
    workers.reserve(cudaWorkerAssignments.size());
    for(size_t workerIndex = 0; workerIndex < cudaWorkerAssignments.size(); ++workerIndex)
    {
      const size_t capturedWorkerIndex = workerIndex;
      const SimCudaWorkerAssignment assignment = cudaWorkerAssignments[workerIndex];
      workers.push_back(thread([&, assignment, capturedWorkerIndex]()
      {
        sim_set_cuda_device_override(assignment.device);
        sim_set_cuda_worker_slot_override(assignment.slot);
        CalcScoreWorkspace calcScoreWorkspace;
        vector<LongTargetWindowPipelineTask> pendingBatchTasks;
        pendingBatchTasks.reserve(longtarget_window_pipeline_batch_size());
        long pendingTargetLength = -1;
        bool hasInFlightWindowPipeline = false;
        future<LongTargetWindowPipelinePreparedBatch> inFlightWindowPipeline;

        auto runWindowPipelineBatchFallback = [&](const vector<LongTargetWindowPipelineTask> &fallbackBatchTasks)
        {
          if(fallbackBatchTasks.empty())
          {
            return;
          }
          recordSimWindowPipelineBatchRuntimeFallback(static_cast<uint64_t>(fallbackBatchTasks.size()));
          recordSimWindowPipelineFallback(static_cast<uint64_t>(fallbackBatchTasks.size()));
          for(size_t batchOffset = 0; batchOffset < fallbackBatchTasks.size(); ++batchOffset)
          {
            const LongTargetWindowPipelineTask &batchTask = fallbackBatchTasks[batchOffset];
            longtarget_run_exact_sim_single_stage_with_min_score(rnaSequence,
                                                                 tasks[batchTask.taskIndex],
                                                                 fragments,
                                                                 batchTask.minScore,
                                                                 exactSimConfig,
                                                                 paraList,
                                                                 taskTriplexLists[batchTask.taskIndex],
                                                                 &taskTimings[batchTask.taskIndex],
                                                                 &taskFilterSeconds[batchTask.taskIndex]);
          }
        };

        auto drainInFlightWindowPipeline = [&]()
        {
          if(!hasInFlightWindowPipeline)
          {
            return;
          }
          LongTargetWindowPipelinePreparedBatch preparedBatch = inFlightWindowPipeline.get();
          hasInFlightWindowPipeline = false;
          if(!preparedBatch.valid ||
             !longtarget_execute_window_pipeline_batch_cpu(tasks,
                                                           fragments,
                                                           paraList,
                                                           preparedBatch,
                                                           taskTriplexLists,
                                                           taskTimings,
                                                           taskFilterSeconds))
          {
            runWindowPipelineBatchFallback(preparedBatch.batchTasks);
          }
        };

        auto submitWindowPipelineBatch = [&](const vector<LongTargetWindowPipelineTask> &submittedBatchTasks)
        {
          const vector<LongTargetWindowPipelineTask> batchCopy = submittedBatchTasks;
          return async(std::launch::async,[&, batchCopy]()
          {
            sim_set_cuda_device_override(assignment.device);
            sim_set_cuda_worker_slot_override(assignment.slot);
            LongTargetWindowPipelinePreparedBatch preparedBatch;
            if(!longtarget_prepare_window_pipeline_batch_gpu(rnaSequence,
                                                             tasks,
                                                             batchCopy,
                                                             exactSimConfig,
                                                             preparedBatch))
            {
              preparedBatch.batchTasks = batchCopy;
            }
            return preparedBatch;
          });
        };

        auto flushPendingWindowPipeline = [&]()
        {
          if(pendingBatchTasks.empty())
          {
            return;
          }
          vector<LongTargetWindowPipelineTask> batchToFlush;
          batchToFlush.swap(pendingBatchTasks);
          pendingTargetLength = -1;

          if(useWindowPipelineOverlap)
          {
            future<LongTargetWindowPipelinePreparedBatch> nextPreparedBatch =
              submitWindowPipelineBatch(batchToFlush);
            if(hasInFlightWindowPipeline)
            {
              recordSimWindowPipelineOverlapBatch();
              LongTargetWindowPipelinePreparedBatch preparedBatch = inFlightWindowPipeline.get();
              if(!preparedBatch.valid ||
                 !longtarget_execute_window_pipeline_batch_cpu(tasks,
                                                               fragments,
                                                               paraList,
                                                               preparedBatch,
                                                               taskTriplexLists,
                                                               taskTimings,
                                                               taskFilterSeconds))
              {
                runWindowPipelineBatchFallback(preparedBatch.batchTasks);
              }
            }
            inFlightWindowPipeline = std::move(nextPreparedBatch);
            hasInFlightWindowPipeline = true;
            return;
          }

          if(!longtarget_flush_window_pipeline_batch(rnaSequence,
                                                     tasks,
                                                     fragments,
                                                     batchToFlush,
                                                     exactSimConfig,
                                                     paraList,
                                                     taskTriplexLists,
                                                     taskTimings,
                                                     taskFilterSeconds))
          {
            runWindowPipelineBatchFallback(batchToFlush);
          }
        };

        while(true)
        {
          const size_t taskOrderIndex = nextTask.fetch_add(1, std::memory_order_relaxed);
          if(taskOrderIndex >= taskExecutionOrder.size())
          {
            break;
          }
          const size_t taskIndex = taskExecutionOrder[taskOrderIndex];
          taskWorkerIndices[taskIndex] = static_cast<int>(capturedWorkerIndex);
          const ExactSimTaskSpec &task = tasks[taskIndex];
          recordSimWindowPipelineTaskConsidered();
          if(deferredExactTwoStage && deferredTaskShouldRun[taskIndex] == 0)
          {
            recordSimWindowPipelineIneligibleTask(longtarget_classify_window_pipeline_ineligible_reason(twoStage,
                                                                                                       simFast,
                                                                                                       validateCuda,
                                                                                                       windowPipelineRequested && sim_scan_cuda_is_built(),
                                                                                                       rnaSequence,
                                                                                                       task,
                                                                                                       0));
            continue;
          }
          if(useWindowPipeline)
          {
            const int minScore =
              taskMinScoreReady[taskIndex] != 0 ?
              taskMinScores[taskIndex] :
              longtarget_prepare_exact_sim_min_score(rnaSequence,
                                                     task.transformedSequence,
                                                     runContext,
                                                     calcScoreWorkspace,
                                                     &taskTimings[taskIndex]);
            const bool canBatchTask =
              longtarget_task_supports_window_pipeline(rnaSequence,task,minScore);
            const long targetLength = static_cast<long>(task.transformedSequence.size());
            if(!canBatchTask)
            {
              recordSimWindowPipelineIneligibleTask(longtarget_classify_window_pipeline_ineligible_reason(twoStage,
                                                                                                         simFast,
                                                                                                         validateCuda,
                                                                                                         useWindowPipeline,
                                                                                                         rnaSequence,
                                                                                                         task,
                                                                                                         minScore));
              flushPendingWindowPipeline();
              recordSimWindowPipelineFallback();
              longtarget_run_exact_sim_single_stage_with_min_score(rnaSequence,
                                                                   task,
                                                                   fragments,
                                                                   minScore,
                                                                   exactSimConfig,
                                                                   paraList,
                                                                   taskTriplexLists[taskIndex],
                                                                   &taskTimings[taskIndex],
                                                                   &taskFilterSeconds[taskIndex]);
              continue;
            }
            recordSimWindowPipelineTaskEligible();
            if(!pendingBatchTasks.empty() &&
               (pendingTargetLength != targetLength ||
                pendingBatchTasks.size() >= longtarget_window_pipeline_batch_size()))
            {
              flushPendingWindowPipeline();
            }
            pendingBatchTasks.push_back(LongTargetWindowPipelineTask(taskIndex,minScore));
            pendingTargetLength = targetLength;
            if(pendingBatchTasks.size() >= longtarget_window_pipeline_batch_size())
            {
              flushPendingWindowPipeline();
            }
            continue;
          }
          recordSimWindowPipelineIneligibleTask(longtarget_classify_window_pipeline_ineligible_reason(twoStage,
                                                                                                     simFast,
                                                                                                     validateCuda,
                                                                                                     windowPipelineRequested && sim_scan_cuda_is_built(),
                                                                                                     rnaSequence,
                                                                                                     task,
                                                                                                     0));
          if(twoStage && deferredExactTwoStage)
          {
            if(taskMinScoreReady[taskIndex] == 0)
            {
              taskMinScores[taskIndex] =
                longtarget_prepare_exact_sim_min_score(rnaSequence,
                                                       task.transformedSequence,
                                                       runContext,
                                                       calcScoreWorkspace,
                                                       &taskTimings[taskIndex]);
              taskMinScoreReady[taskIndex] = 1;
            }
            runExactReferenceSIMTwoStageDeferredWithMinScore(rnaSequence,
                                                             task.transformedSequence,
                                                             fragments[task.fragmentIndex].sequence,
                                                             task.dnaStartPos,
                                                             task.reverseMode,
                                                             task.parallelMode,
                                                             task.rule,
                                                             taskMinScores[taskIndex],
                                                             exactSimConfig,
                                                             paraList.ntMin,
                                                             paraList.ntMax,
                                                             paraList.penaltyT,
                                                             paraList.penaltyC,
                                                             deferredPrefilterResults[taskIndex].windows,
                                                             taskTriplexLists[taskIndex],
                                                             &taskTimings[taskIndex]);
          }
          else
          {
            if(taskMinScoreReady[taskIndex] != 0)
            {
              if(twoStage)
              {
                runExactReferenceSIMTwoStageWithMinScore(rnaSequence,
                                                        task.transformedSequence,
                                                        fragments[task.fragmentIndex].sequence,
                                                        task.dnaStartPos,
                                                        task.reverseMode,
                                                        task.parallelMode,
                                                        task.rule,
                                                        taskMinScores[taskIndex],
                                                        exactSimConfig,
                                                        paraList.ntMin,
                                                        paraList.ntMax,
                                                        paraList.penaltyT,
                                                        paraList.penaltyC,
                                                        taskTriplexLists[taskIndex],
                                                        &taskTimings[taskIndex]);
              }
              else
              {
                runExactReferenceSIMWithMinScore(rnaSequence,
                                                 task.transformedSequence,
                                                 fragments[task.fragmentIndex].sequence,
                                                 task.dnaStartPos,
                                                 task.reverseMode,
                                                 task.parallelMode,
                                                 task.rule,
                                                 taskMinScores[taskIndex],
                                                 exactSimConfig,
                                                 paraList.ntMin,
                                                 paraList.ntMax,
                                                 paraList.penaltyT,
                                                 paraList.penaltyC,
                                                 taskTriplexLists[taskIndex],
                                                 &taskTimings[taskIndex]);
              }
            }
            else
            {
              if(twoStage)
              {
                runExactReferenceSIMTwoStage(rnaSequence,
                                             task.transformedSequence,
                                             fragments[task.fragmentIndex].sequence,
                                             task.dnaStartPos,
                                             task.reverseMode,
                                             task.parallelMode,
                                             task.rule,
                                             exactSimConfig,
                                             paraList.ntMin,
                                             paraList.ntMax,
                                             paraList.penaltyT,
                                             paraList.penaltyC,
                                             taskTriplexLists[taskIndex],
                                             &runContext,
                                             &calcScoreWorkspace,
                                             &taskTimings[taskIndex]);
              }
              else
              {
                runExactReferenceSIM(rnaSequence,
                                     task.transformedSequence,
                                     fragments[task.fragmentIndex].sequence,
                                     task.dnaStartPos,
                                     task.reverseMode,
                                     task.parallelMode,
                                     task.rule,
                                     exactSimConfig,
                                     paraList.ntMin,
                                     paraList.ntMax,
                                     paraList.penaltyT,
                                     paraList.penaltyC,
                                     taskTriplexLists[taskIndex],
                                     &runContext,
                                     &calcScoreWorkspace,
                                     &taskTimings[taskIndex]);
              }
            }
          }

          const double filterStart = metrics != NULL ? longtarget_now_seconds() : 0.0;
          filterTriplexListInPlace(taskTriplexLists[taskIndex],paraList);
          if(metrics != NULL)
          {
            taskFilterSeconds[taskIndex] = longtarget_now_seconds() - filterStart;
          }
        }
        flushPendingWindowPipeline();
        drainInFlightWindowPipeline();
        sim_clear_cuda_worker_slot_override();
        sim_clear_cuda_device_override();
      }));
    }
    for(size_t i = 0; i < workers.size(); ++i)
    {
      workers[i].join();
    }
    finalizeLongTargetCudaWorkerMetrics(cudaWorkerAssignments,
                                        taskWorkerIndices,
                                        taskTimings,
                                        taskFilterSeconds,
                                        metrics);
  }
  else
  {
#if defined(_OPENMP)
#pragma omp parallel
  {
    CalcScoreWorkspace calcScoreWorkspace;
#pragma omp for schedule(static)
    for(long taskIndex = 0; taskIndex < static_cast<long>(tasks.size()); ++taskIndex)
    {
      const ExactSimTaskSpec &task = tasks[static_cast<size_t>(taskIndex)];
      if(deferredExactTwoStage && deferredTaskShouldRun[static_cast<size_t>(taskIndex)] == 0)
      {
        continue;
      }
      if(twoStage && deferredExactTwoStage)
      {
        if(taskMinScoreReady[static_cast<size_t>(taskIndex)] == 0)
        {
          taskMinScores[static_cast<size_t>(taskIndex)] =
            longtarget_prepare_exact_sim_min_score(rnaSequence,
                                                   task.transformedSequence,
                                                   runContext,
                                                   calcScoreWorkspace,
                                                   &taskTimings[static_cast<size_t>(taskIndex)]);
          taskMinScoreReady[static_cast<size_t>(taskIndex)] = 1;
        }
        runExactReferenceSIMTwoStageDeferredWithMinScore(rnaSequence,
                                                         task.transformedSequence,
                                                         fragments[task.fragmentIndex].sequence,
                                                         task.dnaStartPos,
                                                         task.reverseMode,
                                                         task.parallelMode,
                                                         task.rule,
                                                         taskMinScores[static_cast<size_t>(taskIndex)],
                                                         exactSimConfig,
                                                         paraList.ntMin,
                                                         paraList.ntMax,
                                                         paraList.penaltyT,
                                                         paraList.penaltyC,
                                                         deferredPrefilterResults[static_cast<size_t>(taskIndex)].windows,
                                                         taskTriplexLists[static_cast<size_t>(taskIndex)],
                                                         &taskTimings[static_cast<size_t>(taskIndex)]);
      }
      else
      {
        if(taskMinScoreReady[static_cast<size_t>(taskIndex)] != 0)
        {
          if(twoStage)
          {
            runExactReferenceSIMTwoStageWithMinScore(rnaSequence,
                                                    task.transformedSequence,
                                                    fragments[task.fragmentIndex].sequence,
                                                    task.dnaStartPos,
                                                    task.reverseMode,
                                                    task.parallelMode,
                                                    task.rule,
                                                    taskMinScores[static_cast<size_t>(taskIndex)],
                                                    exactSimConfig,
                                                    paraList.ntMin,
                                                    paraList.ntMax,
                                                    paraList.penaltyT,
                                                    paraList.penaltyC,
                                                    taskTriplexLists[static_cast<size_t>(taskIndex)],
                                                    &taskTimings[static_cast<size_t>(taskIndex)]);
          }
          else
          {
            runExactReferenceSIMWithMinScore(rnaSequence,
                                             task.transformedSequence,
                                             fragments[task.fragmentIndex].sequence,
                                             task.dnaStartPos,
                                             task.reverseMode,
                                             task.parallelMode,
                                             task.rule,
                                             taskMinScores[static_cast<size_t>(taskIndex)],
                                             exactSimConfig,
                                             paraList.ntMin,
                                             paraList.ntMax,
                                             paraList.penaltyT,
                                             paraList.penaltyC,
                                             taskTriplexLists[static_cast<size_t>(taskIndex)],
                                             &taskTimings[static_cast<size_t>(taskIndex)]);
          }
        }
        else
        {
          if(twoStage)
          {
            runExactReferenceSIMTwoStage(rnaSequence,
                                         task.transformedSequence,
                                         fragments[task.fragmentIndex].sequence,
                                         task.dnaStartPos,
                                         task.reverseMode,
                                         task.parallelMode,
                                         task.rule,
                                         exactSimConfig,
                                         paraList.ntMin,
                                         paraList.ntMax,
                                         paraList.penaltyT,
                                         paraList.penaltyC,
                                         taskTriplexLists[static_cast<size_t>(taskIndex)],
                                         &runContext,
                                         &calcScoreWorkspace,
                                         &taskTimings[static_cast<size_t>(taskIndex)]);
          }
          else
          {
            runExactReferenceSIM(rnaSequence,
                                 task.transformedSequence,
                                 fragments[task.fragmentIndex].sequence,
                                 task.dnaStartPos,
                                 task.reverseMode,
                                 task.parallelMode,
                                 task.rule,
                                 exactSimConfig,
                                 paraList.ntMin,
                                 paraList.ntMax,
                                 paraList.penaltyT,
                                 paraList.penaltyC,
                                 taskTriplexLists[static_cast<size_t>(taskIndex)],
                                 &runContext,
                                 &calcScoreWorkspace,
                                 &taskTimings[static_cast<size_t>(taskIndex)]);
          }
        }
      }
      const double filterStart = metrics != NULL ? longtarget_now_seconds() : 0.0;
      filterTriplexListInPlace(taskTriplexLists[static_cast<size_t>(taskIndex)],paraList);
      if(metrics != NULL)
      {
        taskFilterSeconds[static_cast<size_t>(taskIndex)] = longtarget_now_seconds() - filterStart;
      }
    }
  }
#else
  CalcScoreWorkspace calcScoreWorkspace;
  for(size_t taskIndex = 0; taskIndex < tasks.size(); ++taskIndex)
  {
    const ExactSimTaskSpec &task = tasks[taskIndex];
    if(deferredExactTwoStage && deferredTaskShouldRun[taskIndex] == 0)
    {
      continue;
    }
    if(twoStage && deferredExactTwoStage)
    {
      if(taskMinScoreReady[taskIndex] == 0)
      {
        taskMinScores[taskIndex] =
          longtarget_prepare_exact_sim_min_score(rnaSequence,
                                                 task.transformedSequence,
                                                 runContext,
                                                 calcScoreWorkspace,
                                                 &taskTimings[taskIndex]);
        taskMinScoreReady[taskIndex] = 1;
      }
      runExactReferenceSIMTwoStageDeferredWithMinScore(rnaSequence,
                                                       task.transformedSequence,
                                                       fragments[task.fragmentIndex].sequence,
                                                       task.dnaStartPos,
                                                       task.reverseMode,
                                                       task.parallelMode,
                                                       task.rule,
                                                       taskMinScores[taskIndex],
                                                       exactSimConfig,
                                                       paraList.ntMin,
                                                       paraList.ntMax,
                                                       paraList.penaltyT,
                                                       paraList.penaltyC,
                                                       deferredPrefilterResults[taskIndex].windows,
                                                       taskTriplexLists[taskIndex],
                                                       &taskTimings[taskIndex]);
    }
    else
    {
      if(taskMinScoreReady[taskIndex] != 0)
      {
        if(twoStage)
        {
          runExactReferenceSIMTwoStageWithMinScore(rnaSequence,
                                                  task.transformedSequence,
                                                  fragments[task.fragmentIndex].sequence,
                                                  task.dnaStartPos,
                                                  task.reverseMode,
                                                  task.parallelMode,
                                                  task.rule,
                                                  taskMinScores[taskIndex],
                                                  exactSimConfig,
                                                  paraList.ntMin,
                                                  paraList.ntMax,
                                                  paraList.penaltyT,
                                                  paraList.penaltyC,
                                                  taskTriplexLists[taskIndex],
                                                  &taskTimings[taskIndex]);
        }
        else
        {
          runExactReferenceSIMWithMinScore(rnaSequence,
                                           task.transformedSequence,
                                           fragments[task.fragmentIndex].sequence,
                                           task.dnaStartPos,
                                           task.reverseMode,
                                           task.parallelMode,
                                           task.rule,
                                           taskMinScores[taskIndex],
                                           exactSimConfig,
                                           paraList.ntMin,
                                           paraList.ntMax,
                                           paraList.penaltyT,
                                           paraList.penaltyC,
                                           taskTriplexLists[taskIndex],
                                           &taskTimings[taskIndex]);
        }
      }
      else
      {
        if(twoStage)
        {
          runExactReferenceSIMTwoStage(rnaSequence,
                                       task.transformedSequence,
                                       fragments[task.fragmentIndex].sequence,
                                       task.dnaStartPos,
                                       task.reverseMode,
                                       task.parallelMode,
                                       task.rule,
                                       exactSimConfig,
                                       paraList.ntMin,
                                       paraList.ntMax,
                                       paraList.penaltyT,
                                       paraList.penaltyC,
                                       taskTriplexLists[taskIndex],
                                       &runContext,
                                       &calcScoreWorkspace,
                                       &taskTimings[taskIndex]);
        }
        else
        {
          runExactReferenceSIM(rnaSequence,
                               task.transformedSequence,
                               fragments[task.fragmentIndex].sequence,
                               task.dnaStartPos,
                               task.reverseMode,
                               task.parallelMode,
                               task.rule,
                               exactSimConfig,
                               paraList.ntMin,
                               paraList.ntMax,
                               paraList.penaltyT,
                               paraList.penaltyC,
                               taskTriplexLists[taskIndex],
                               &runContext,
                               &calcScoreWorkspace,
                               &taskTimings[taskIndex]);
        }
      }
    }
    const double filterStart = metrics != NULL ? longtarget_now_seconds() : 0.0;
    filterTriplexListInPlace(taskTriplexLists[taskIndex],paraList);
    if(metrics != NULL)
    {
      taskFilterSeconds[taskIndex] = longtarget_now_seconds() - filterStart;
    }
  }
#endif
  }

  size_t mergedTriplexCount = 0;
  auto mergePrefilterBackend = [](const string &current,const string &next) -> string
  {
    if(next.empty())
    {
      return current;
    }
    if(current.empty())
    {
      return next;
    }
    if(current == next)
    {
      return current;
    }
    if(current == "disabled")
    {
      return next;
    }
    if(next == "disabled")
    {
      return current;
    }
    return "mixed";
  };
  for(size_t taskIndex = 0; taskIndex < taskTriplexLists.size(); ++taskIndex)
  {
    mergedTriplexCount += taskTriplexLists[taskIndex].size();
    if(metrics != NULL)
    {
      metrics->thresholdSeconds += taskTimings[taskIndex].thresholdSeconds;
      metrics->simSeconds += taskTimings[taskIndex].simSeconds;
      metrics->postProcessSeconds += taskFilterSeconds[taskIndex];
      metrics->prefilterBackend = mergePrefilterBackend(metrics->prefilterBackend, taskTimings[taskIndex].prefilterBackend);
      metrics->prefilterHits += taskTimings[taskIndex].prefilterHits;
      metrics->refineWindowCount += taskTimings[taskIndex].refineWindowCount;
      metrics->refineTotalBp += taskTimings[taskIndex].refineTotalBp;
      if(taskRerunEffective[taskIndex] != 0)
      {
        metrics->twoStageTaskRerunSeconds += taskTimings[taskIndex].simSeconds;
      }
      if(twoStage && !deferredExactTwoStage)
      {
        metrics->twoStageTasksWithAnySeed += taskTimings[taskIndex].twoStageHadAnySeed;
        metrics->twoStageTasksWithAnyRefineWindowBeforeGate += taskTimings[taskIndex].twoStageHadAnyRefineWindowBeforeGate;
        metrics->twoStageWindowsBeforeGate += taskTimings[taskIndex].twoStageRefineWindowCountBeforeGate;
        if(taskTimings[taskIndex].refineWindowCount > 0)
        {
          metrics->twoStageTasksWithAnyRefineWindowAfterGate += 1;
        }
      }
    }
  }

  if(metrics != NULL && twoStage && !deferredExactTwoStage)
  {
    metrics->twoStageWindowsAfterGate = metrics->refineWindowCount;
  }

  if(metrics != NULL)
  {
    getSimScanExecutionCounts(metrics->simScanTasks,metrics->simScanLaunches);
    getSimTracebackStats(metrics->simTracebackCandidates,metrics->simTracebackTieCount);
  }

  vector<struct triplex> triplex_list;
  triplex_list.reserve(mergedTriplexCount);
  for(size_t taskIndex = 0; taskIndex < taskTriplexLists.size(); ++taskIndex)
  {
    triplex_list.insert(triplex_list.end(),taskTriplexLists[taskIndex].begin(),taskTriplexLists[taskIndex].end());
  }
  sort_triplex_list.insert(sort_triplex_list.end(),triplex_list.begin(),triplex_list.end());
}


void printResult(string &species,struct para paraList,string &lncName,string &dnaFile,vector<struct triplex> &sort_triplex_list,string &chroTag,string &dnaSequence,int start_genome,string &c_tmp_dd,string &c_tmp_length,string &resultDir)
{
  vector<struct tmp_class> w_tmp_class;
  string pre_file2=resultDir+"/"+species+"-"+lncName;
  string pre_file1=dnaFile;
  string outFilePath = pre_file2+"-"+pre_file1+"-TFOsorted";
  const LongTargetOutputMode outputMode = longtarget_output_mode_runtime();
  const bool writeTfoSorted = (outputMode != LONGTARGET_OUTPUT_LITE);
  const bool writeLite = (outputMode == LONGTARGET_OUTPUT_LITE) || longtarget_write_tfosorted_lite_enabled();
  ofstream outFile;
  if(writeTfoSorted)
  {
    outFile.open(outFilePath.c_str(),ios::trunc);
    outFile<<"QueryStart\t"<<"QueryEnd\t"<<"StartInSeq\t"<<"EndInSeq\t"<<"Direction\t"<<"StartInGenome\t"<<"EndInGenome\t"<<"MeanStability\t"<<"MeanIdentity(%)\t"<<"Strand\t"<<"Rule\t"<<"Score\t"<<"Nt(bp)\t"<<"Class\t"<<"MidPoint\t"<<"Center\t"<<"TFO sequence"<<endl;
  }

  const string outLitePath = outFilePath + ".lite";
  ofstream outLiteFile;
  if(writeLite)
  {
    outLiteFile.open(outLitePath.c_str(), ios::trunc);
    outLiteFile << "Chr\t"
                << "StartInGenome\t"
                << "EndInGenome\t"
                << "Strand\t"
                << "Rule\t"
                << "QueryStart\t"
                << "QueryEnd\t"
                << "StartInSeq\t"
                << "EndInSeq\t"
                << "Direction\t"
                << "Score\t"
                << "Nt(bp)\t"
                << "MeanIdentity(%)\t"
                << "MeanStability"
                << endl;
  }

  const bool doCluster = (outputMode == LONGTARGET_OUTPUT_FULL);
  map<size_t,size_t> class1[6],class1a[6],class1b[6];
  int class_level=5;
  if(doCluster)
  {
    cluster_triplex(paraList.cDistance,paraList.cLength, sort_triplex_list, class1, class1a, class1b, class_level);
    sort(sort_triplex_list.begin(),sort_triplex_list.end(),comp);
  }
  for(int i=0;i<sort_triplex_list.size();i++)
  {
    triplex atr=sort_triplex_list[i];
    if(doCluster && sort_triplex_list[i].motif==0)
    {
      continue;
    }
    const int motif = doCluster ? atr.motif : 0;
    const int middle = doCluster ? atr.middle : static_cast<int>((atr.stari + atr.endi) / 2);
    const int center = doCluster ? atr.center : middle;
    if(writeTfoSorted)
    {
      atr.stri_align.erase(remove(atr.stri_align.begin(),atr.stri_align.end(),'-'),atr.stri_align.end());
    }
    if(atr.starj<atr.endj)
    {
      const long genomeStart = atr.starj + start_genome - 1;
      const long genomeEnd = atr.endj + start_genome - 1;
      if(writeTfoSorted)
      {
        outFile<<atr.stari<<"\t"<<atr.endi<<"\t"<<atr.starj<<"\t"<<atr.endj<<"\t"<<"R\t"<<genomeStart<<"\t"<<genomeEnd<<"\t"<<atr.tri_score<<"\t"<<atr.identity<<"\t"<<getStrand(atr.reverse,atr.strand)<<"\t"<<atr.rule<<"\t"<<atr.score<<"\t"<<atr.nt<<"\t"<<motif<<"\t"<<middle<<"\t"<<center<<"\t"<<atr.stri_align<<endl;
      }
      if(writeLite)
      {
        outLiteFile << chroTag << "\t"
                    << genomeStart << "\t"
                    << genomeEnd << "\t"
                    << getStrand(atr.reverse, atr.strand) << "\t"
                    << atr.rule << "\t"
                    << atr.stari << "\t"
                    << atr.endi << "\t"
                    << atr.starj << "\t"
                    << atr.endj << "\t"
                    << "R\t"
                    << atr.score << "\t"
                    << atr.nt << "\t"
                    << atr.identity << "\t"
                    << atr.tri_score
                    << endl;
      }
    }
    else
    {
      const long genomeStart = atr.endj + start_genome - 1;
      const long genomeEnd = atr.starj + start_genome - 1;
      if(writeTfoSorted)
      {
        outFile<<atr.stari<<"\t"<<atr.endi<<"\t"<<atr.starj<<"\t"<<atr.endj<<"\t"<<"L\t"<<genomeStart<<"\t"<<genomeEnd<<"\t"<<atr.tri_score<<"\t"<<atr.identity<<"\t"<<getStrand(atr.reverse,atr.strand)<<"\t"<<atr.rule<<"\t"<<atr.score<<"\t"<<atr.nt<<"\t"<<motif<<"\t"<<middle<<"\t"<<center<<"\t"<<atr.stri_align<<endl;
      }
      if(writeLite)
      {
        outLiteFile << chroTag << "\t"
                    << genomeStart << "\t"
                    << genomeEnd << "\t"
                    << getStrand(atr.reverse, atr.strand) << "\t"
                    << atr.rule << "\t"
                    << atr.stari << "\t"
                    << atr.endi << "\t"
                    << atr.starj << "\t"
                    << atr.endj << "\t"
                    << "L\t"
                    << atr.score << "\t"
                    << atr.nt << "\t"
                    << atr.identity << "\t"
                    << atr.tri_score
                    << endl;
      }
    }
  }
  if(writeTfoSorted)
  {
    outFile.close();
  }
  if(writeLite)
  {
    outLiteFile.close();
  }
  int pr_loop=0;
  if(doCluster)
  {
    for(pr_loop=1;pr_loop<3;pr_loop++)
    {
      print_cluster(pr_loop,class1,start_genome-1,chroTag,dnaSequence.size(),lncName,paraList.cDistance,paraList.cLength,outFilePath,c_tmp_dd,c_tmp_length,w_tmp_class);
    }
  }
  vector<struct tmp_class>tmpClass;
  tmpClass.swap(w_tmp_class);
  for(pr_loop=0;pr_loop<6;pr_loop++)
  {
    class1[pr_loop].clear();
    class1a[pr_loop].clear();
    class1b[pr_loop].clear();
  }
}

bool comp(const triplex &a,const triplex &b)
{
  if(a.motif != b.motif) return a.motif < b.motif;
  if(a.stari != b.stari) return a.stari < b.stari;
  if(a.endi != b.endi) return a.endi < b.endi;
  if(a.starj != b.starj) return a.starj < b.starj;
  if(a.endj != b.endj) return a.endj < b.endj;
  if(a.reverse != b.reverse) return a.reverse < b.reverse;
  if(a.strand != b.strand) return a.strand < b.strand;
  if(a.rule != b.rule) return a.rule < b.rule;
  if(a.nt != b.nt) return a.nt < b.nt;
  if(a.middle != b.middle) return a.middle < b.middle;
  if(a.center != b.center) return a.center < b.center;
  if(a.neartriplex != b.neartriplex) return a.neartriplex < b.neartriplex;

  auto floatBits = [](float value) -> uint32_t
  {
    uint32_t bits = 0;
    memcpy(&bits,&value,sizeof(bits));
    return bits;
  };

  const uint32_t scoreA = floatBits(a.score);
  const uint32_t scoreB = floatBits(b.score);
  if(scoreA != scoreB) return scoreA < scoreB;
  const uint32_t identityA = floatBits(a.identity);
  const uint32_t identityB = floatBits(b.identity);
  if(identityA != identityB) return identityA < identityB;
  const uint32_t stabilityA = floatBits(a.tri_score);
  const uint32_t stabilityB = floatBits(b.tri_score);
  if(stabilityA != stabilityB) return stabilityA < stabilityB;

  if(a.stri_align != b.stri_align) return a.stri_align < b.stri_align;
  if(a.strj_align != b.strj_align) return a.strj_align < b.strj_align;
  return false;
}
string getStrand(int reverse,int strand)
{
  string Strand;
  if(reverse==0 &&strand==1)
  {
    Strand="ParaPlus";
  }
  else if(reverse==1 &&strand==1)
  {
    Strand="ParaMinus";
  }
  else if(reverse==1 &&strand==-1)
  {
    Strand="AntiMinus";
  }
  else if(reverse==0 &&strand==-1)
  {
    Strand="AntiPlus";
  }
  return Strand;
}

int same_seq(string &w_str)
{
  string A=w_str;
  int i=0;
  int a=0,c=0,g=0,t=0,u=0,n=0;
  for(i=0;i<A.size();i++)
  {
    switch(A[i])
    {
      case 'A':
      case 'a':
        a++;
        break;
      case 'C':
      case 'c':
        c++;
        break;
      case 'G':
      case 'g':
        g++;
        break;
      case 'T':
      case 't':
        t++;
        break;
      case 'U':
      case 'u':
        u++;
        break;
      case 'N':
      case 'n':
        n++;
        break;
      default:
        break;
    }
  }
  if(a==A.size())
  {
    return 1;
  }
  else if(c==A.size())
  {
    return 1;
  }
  else if(g==A.size())
  {
    return 1;
  }
  else if(t==A.size())
  {
    return 1;
  }
  else if(u==A.size())
  {
    return 1;
  }
  else if(n==A.size())
  {
    return 1;
  }
  else
  {
    return 0;
  }
}

void show_help()
{
  cout<<"This is the help page."<<endl;
  cout<<"options   Parameters      functions"<<endl;
  cout<<"f1   DNA sequence file  used to get the DNA sequence"<<endl;
  cout<<"f2   RNA sequence file  used to get the RNA sequence"<<endl;
  cout<<"r    rules              rules used to construct triplexes.int type.0 is all."<<endl;
  cout<<"O    Output path        if you define this,output result will be in the path.default is pwd"<<endl;
  cout<<"c    Cutlength          Cut sequence's length."<<endl;
  cout<<"m    min_score          Min_score...this option maybe useless.keep it for now."<<endl;
  cout<<"d    detailoutut        if you choose -d option,it will generate a triplex.detail file which describes the sequence-alignment."<<endl;
  cout<<"i    identity           a condition used to pick up triplexes.default is 60.this should be int type such as 60,not 0.6.default is 60."<<endl;
  cout<<"S    stability          a condition like identity,should be float type such as 1.0.default is 1.0."<<endl;
  cout<<"ni   ntmin              triplexes' min length.default is 20."<<endl;
  cout<<"na   ntmax              triplexes' max length.default is 100."<<endl;
  cout<<"pc   penaltyC           penalty about GG.default is 0."<<endl;
  cout<<"pt   penaltyT           penalty about AA.default is -1000."<<endl;
  cout<<"ds   c_dd               distance used by cluster function.default is 15."<<endl;
  cout<<"lg   c_length           triplexes' length threshold used in cluster function.default is 50."<<endl;
  cout<<"all parameters are listed.If you want to run a simple example,type ./LongTarget -f1 DNAseq.fa -f2 RNAseq.fa -r 0 will be OK"<<endl;
  cout<<"any problems or bugs found please send email to us:zhuhao@smu.edu.cn."<<endl;
  exit(1);
}
