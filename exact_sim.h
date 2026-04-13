#ifndef LONGTARGET_EXACT_SIM_H
#define LONGTARGET_EXACT_SIM_H

#include <chrono>
#include <mutex>
#include <unordered_map>
#include <unordered_set>

#include "sim.h"
#include "cuda/prealign_cuda.h"
#include "cuda/prealign_shared.h"

struct ExactSimConfig
{
  ExactSimConfig():
    matchScore(5.0f),
    mismatchScore(-4.0f),
    gapOpen(-12.0f),
    gapExtend(-4.0f) {}

  float matchScore;
  float mismatchScore;
  float gapOpen;
  float gapExtend;
};

struct ExactSimTaskTiming
{
  ExactSimTaskTiming():
    thresholdSeconds(0.0),
    simSeconds(0.0),
    prefilterSeconds(0.0),
    twoStageGateSeconds(0.0),
    prefilterBackend("disabled"),
    prefilterHits(0),
    twoStageRefineWindowCountBeforeGate(0),
    twoStageHadAnySeed(0),
    twoStageHadAnyRefineWindowBeforeGate(0),
    refineWindowCount(0),
    refineTotalBp(0) {}

  double thresholdSeconds;
  double simSeconds;
  double prefilterSeconds;
  double twoStageGateSeconds;
  string prefilterBackend;
  uint64_t prefilterHits;
  uint64_t twoStageRefineWindowCountBeforeGate;
  uint64_t twoStageHadAnySeed;
  uint64_t twoStageHadAnyRefineWindowBeforeGate;
  uint64_t refineWindowCount;
  uint64_t refineTotalBp;
};

struct ExactSimRunContext
{
  explicit ExactSimRunContext(const string &querySequence):
    querySequenceKey(querySequence) {}

  const string &querySequenceKey;
  unordered_map<string,int> minScoreCache;
  mutex minScoreCacheMutex;
};

inline double exact_sim_now_seconds()
{
  return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

inline CalcScoreWorkspace &default_exact_sim_calc_score_workspace()
{
  static thread_local CalcScoreWorkspace workspace;
  return workspace;
}

inline int getExactReferenceMinScore(string &rnaSequence,
                                     const string &transformedSequence,
                                     ExactSimRunContext *runContext,
                                     CalcScoreWorkspace &workspace)
{
  if(runContext == NULL)
  {
    return calc_score_with_workspace(rnaSequence, transformedSequence, workspace);
  }

  {
    lock_guard<mutex> cacheLock(runContext->minScoreCacheMutex);
    unordered_map<string,int>::const_iterator cachedScore = runContext->minScoreCache.find(transformedSequence);
    if(cachedScore != runContext->minScoreCache.end())
    {
      return cachedScore->second;
    }
  }

  const int computedScore = calc_score_with_workspace(rnaSequence, transformedSequence, workspace);
  lock_guard<mutex> cacheLock(runContext->minScoreCacheMutex);
  return runContext->minScoreCache.insert(make_pair(transformedSequence, computedScore)).first->second;
}

inline void runExactReferenceSIM(string &rnaSequence,
                                 const string &transformedSequence,
                                 const string &sourceSequence,
                                 long dnaStartPos,
                                 long reverseMode,
                                 long parallelMode,
                                 long rule,
                                 const ExactSimConfig &config,
                                 int ntMin,
                                 int ntMax,
                                 int penaltyT,
                                 int penaltyC,
                                 vector<struct triplex> &triplexList,
                                 ExactSimRunContext *runContext = NULL,
                                 CalcScoreWorkspace *workspace = NULL,
                                 ExactSimTaskTiming *taskTiming = NULL)
{
  CalcScoreWorkspace &activeWorkspace = workspace != NULL ? *workspace : default_exact_sim_calc_score_workspace();
  const double thresholdStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  const int minScore = getExactReferenceMinScore(rnaSequence, transformedSequence, runContext, activeWorkspace);
  if(taskTiming != NULL)
  {
    taskTiming->thresholdSeconds += exact_sim_now_seconds() - thresholdStart;
  }

  const double simStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  SIM(rnaSequence,
      transformedSequence,
      sourceSequence,
      dnaStartPos,
      minScore,
      config.matchScore,
      config.mismatchScore,
      config.gapOpen,
      config.gapExtend,
      triplexList,
      reverseMode,
      parallelMode,
      rule,
      ntMin,
      ntMax,
      penaltyT,
      penaltyC);
  if(taskTiming != NULL)
  {
    taskTiming->simSeconds += exact_sim_now_seconds() - simStart;
  }
}

inline void runExactReferenceSIMWithMinScore(string &rnaSequence,
                                             const string &transformedSequence,
                                             const string &sourceSequence,
                                             long dnaStartPos,
                                             long reverseMode,
                                             long parallelMode,
                                             long rule,
                                             int minScore,
                                             const ExactSimConfig &config,
                                             int ntMin,
                                             int ntMax,
                                             int penaltyT,
                                             int penaltyC,
                                             vector<struct triplex> &triplexList,
                                             ExactSimTaskTiming *taskTiming = NULL)
{
  const double simStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  SIM(rnaSequence,
      transformedSequence,
      sourceSequence,
      dnaStartPos,
      minScore,
      config.matchScore,
      config.mismatchScore,
      config.gapOpen,
      config.gapExtend,
      triplexList,
      reverseMode,
      parallelMode,
      rule,
      ntMin,
      ntMax,
      penaltyT,
      penaltyC);
  if(taskTiming != NULL)
  {
    taskTiming->simSeconds += exact_sim_now_seconds() - simStart;
  }
}

inline int exact_sim_env_int_or_default(const char *name,int defaultValue)
{
  const char *env = getenv(name);
  if(env == NULL || env[0] == '\0')
  {
    return defaultValue;
  }
  char *end = NULL;
  long parsed = strtol(env,&end,10);
  if(end == env)
  {
    return defaultValue;
  }
  if(parsed < static_cast<long>(std::numeric_limits<int>::min()))
  {
    return std::numeric_limits<int>::min();
  }
  if(parsed > static_cast<long>(std::numeric_limits<int>::max()))
  {
    return std::numeric_limits<int>::max();
  }
  return static_cast<int>(parsed);
}

enum ExactSimPrefilterBackend
{
  EXACT_SIM_PREFILTER_BACKEND_SIM = 0,
  EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA = 1,
};

enum ExactSimTwoStageThresholdMode
{
  EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_LEGACY = 0,
  EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_DEFERRED_EXACT = 1,
};

enum ExactSimTwoStageDiscoveryMode
{
  EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_OFF = 0,
  EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_PREFILTER_ONLY = 1,
};

enum ExactSimTwoStageDiscoveryStatus
{
  EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_OK = 0,
  EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_EMPTY = 1,
  EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_PREFILTER_FAILED = 2,
};

struct ExactSimTwoStageDiscoverySummary
{
  ExactSimTwoStageDiscoverySummary():
    taskCount(0),
    prefilterFailedTasks(0),
    tasksWithAnySeed(0),
    tasksWithAnyRefineWindowBeforeGate(0),
    tasksWithAnyRefineWindowAfterGate(0),
    windowsBeforeGate(0),
    windowsAfterGate(0) {}

  uint64_t taskCount;
  uint64_t prefilterFailedTasks;
  uint64_t tasksWithAnySeed;
  uint64_t tasksWithAnyRefineWindowBeforeGate;
  uint64_t tasksWithAnyRefineWindowAfterGate;
  uint64_t windowsBeforeGate;
  uint64_t windowsAfterGate;
};

inline bool exact_sim_two_stage_enabled_runtime()
{
  static const bool enabled = []()
  {
    const char *env = getenv("LONGTARGET_TWO_STAGE");
    return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
  }();
  return enabled;
}

inline ExactSimPrefilterBackend exact_sim_prefilter_backend_requested_runtime()
{
  static const ExactSimPrefilterBackend backend = []()
  {
    const char *env = getenv("LONGTARGET_PREFILTER_BACKEND");
    if(env == NULL || env[0] == '\0')
    {
      return EXACT_SIM_PREFILTER_BACKEND_SIM;
    }
    string value(env);
    for(size_t i = 0; i < value.size(); ++i)
    {
      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
    }
    if(value == "prealign" || value == "prealign_cuda" || value == "prealign-cuda")
    {
      return EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA;
    }
    return EXACT_SIM_PREFILTER_BACKEND_SIM;
  }();
  return backend;
}

inline ExactSimTwoStageThresholdMode exact_sim_two_stage_threshold_mode_runtime()
{
  static const ExactSimTwoStageThresholdMode mode = []()
  {
    const char *env = getenv("LONGTARGET_TWO_STAGE_THRESHOLD_MODE");
    if(env == NULL || env[0] == '\0')
    {
      return EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_LEGACY;
    }
    string value(env);
    for(size_t i = 0; i < value.size(); ++i)
    {
      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
    }
    if(value == "deferred_exact" || value == "deferred-exact")
    {
      return EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_DEFERRED_EXACT;
    }
    return EXACT_SIM_TWO_STAGE_THRESHOLD_MODE_LEGACY;
  }();
  return mode;
}

inline ExactSimTwoStageDiscoveryMode exact_sim_two_stage_discovery_mode_runtime()
{
  static const ExactSimTwoStageDiscoveryMode mode = []()
  {
    const char *env = getenv("LONGTARGET_TWO_STAGE_DISCOVERY_MODE");
    if(env == NULL || env[0] == '\0')
    {
      return EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_OFF;
    }
    string value(env);
    for(size_t i = 0; i < value.size(); ++i)
    {
      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
    }
    if(value == "prefilter_only" || value == "prefilter-only")
    {
      return EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_PREFILTER_ONLY;
    }
    return EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_OFF;
  }();
  return mode;
}

inline const char *exact_sim_two_stage_discovery_mode_label(ExactSimTwoStageDiscoveryMode mode)
{
  return mode == EXACT_SIM_TWO_STAGE_DISCOVERY_MODE_PREFILTER_ONLY ? "prefilter_only" : "off";
}

inline ExactSimTwoStageDiscoveryStatus exact_sim_two_stage_discovery_status_from_summary(
  const ExactSimTwoStageDiscoverySummary &summary)
{
  if(summary.prefilterFailedTasks > 0)
  {
    return EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_PREFILTER_FAILED;
  }
  if(summary.tasksWithAnySeed == 0 || summary.tasksWithAnyRefineWindowBeforeGate == 0)
  {
    return EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_EMPTY;
  }
  return EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_OK;
}

inline bool exact_sim_two_stage_discovery_predicted_skip(const ExactSimTwoStageDiscoverySummary &summary)
{
  return exact_sim_two_stage_discovery_status_from_summary(summary) == EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_OK &&
         summary.tasksWithAnyRefineWindowBeforeGate > 0 &&
         summary.tasksWithAnyRefineWindowAfterGate == 0;
}

inline const char *exact_sim_two_stage_discovery_status_label(ExactSimTwoStageDiscoveryStatus status)
{
  switch(status)
  {
    case EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_EMPTY:
      return "empty";
    case EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_PREFILTER_FAILED:
      return "prefilter_failed";
    case EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_OK:
    default:
      return "ok";
  }
}

inline int exact_sim_prefilter_topk_runtime(ExactSimPrefilterBackend backend)
{
  int topk = exact_sim_env_int_or_default("LONGTARGET_PREFILTER_TOPK", 8);
  if(topk <= 0)
  {
    topk = 8;
  }
  const int maxTopk = (backend == EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA) ? 256 : K;
  if(topk > maxTopk)
  {
    topk = maxTopk;
  }
  return topk;
}

inline int exact_sim_prefilter_peak_suppress_bp_runtime()
{
  int suppress = exact_sim_env_int_or_default("LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP", 5);
  if(suppress < 0)
  {
    suppress = 0;
  }
  if(suppress > 1000000)
  {
    suppress = 1000000;
  }
  return suppress;
}

inline int exact_sim_prefilter_score_floor_delta_runtime()
{
  int delta = exact_sim_env_int_or_default("LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA", 0);
  if(delta < 0)
  {
    delta = 0;
  }
  if(delta > 1000000000)
  {
    delta = 1000000000;
  }
  return delta;
}

inline int exact_sim_refine_pad_bp_runtime()
{
  int pad = exact_sim_env_int_or_default("LONGTARGET_REFINE_PAD_BP", 64);
  if(pad < 0)
  {
    pad = 0;
  }
  if(pad > 1000000)
  {
    pad = 1000000;
  }
  return pad;
}

inline int exact_sim_refine_merge_gap_bp_runtime()
{
  int gap = exact_sim_env_int_or_default("LONGTARGET_REFINE_MERGE_GAP_BP", 32);
  if(gap < 0)
  {
    gap = 0;
  }
  if(gap > 1000000)
  {
    gap = 1000000;
  }
  return gap;
}

static inline uint8_t exact_sim_prealign_encode_base(unsigned char c)
{
  return prealign_shared_encode_base(c);
}

static inline void exact_sim_prealign_build_query_profile(const string &query,
                                                          int matchScore,
                                                          int mismatchPenalty,
                                                          vector<int16_t> &profile,
                                                          int &segLenOut)
{
  prealign_shared_build_query_profile(query, matchScore, mismatchPenalty, profile, segLenOut);
}

inline bool exact_sim_prefilter_hits_prealign_cuda_core(const string &query,
                                                        const string &target,
                                                        bool applyScoreFloor,
                                                        int scoreFloor,
                                                        const ExactSimConfig &config,
                                                        int topK,
                                                        int suppressBp,
                                                        vector<SimPrefilterHit> &hits)
{
  hits.clear();
  if(topK <= 0)
  {
    return true;
  }
  if(query.empty() || target.empty())
  {
    return true;
  }
  if(!prealign_cuda_is_built())
  {
    return false;
  }

  int matchScoreInt = static_cast<int>(config.matchScore >= 0.0f ? (config.matchScore + 0.5f) : (config.matchScore - 0.5f));
  if(matchScoreInt <= 0)
  {
    matchScoreInt = 5;
  }
  float mismatchPenaltyFloat = -config.mismatchScore;
  int mismatchPenaltyInt =
    static_cast<int>(mismatchPenaltyFloat >= 0.0f ? (mismatchPenaltyFloat + 0.5f) : (mismatchPenaltyFloat - 0.5f));
  if(mismatchPenaltyInt < 0)
  {
    mismatchPenaltyInt = 4;
  }

  const int device = simCudaDeviceRuntime();
  string cudaError;
  if(!prealign_cuda_init(device,&cudaError))
  {
    return false;
  }

  static thread_local PrealignSharedQueryCache cache;
  cudaError.clear();
  if(!cache.prepare(device, query, 5, matchScoreInt, mismatchPenaltyInt, &cudaError))
  {
    return false;
  }

  vector<uint8_t> encodedTarget;
  prealign_shared_encode_sequence(target, encodedTarget);

  vector<PreAlignCudaPeak> peaks;
  PreAlignCudaBatchResult batchResult;
  cudaError.clear();
  if(!prealign_cuda_find_topk_column_maxima(cache.query_handle(),
                                           encodedTarget.data(),
                                           1,
                                           static_cast<int>(encodedTarget.size()),
                                           topK,
                                           &peaks,
                                           &batchResult,
                                           &cudaError))
  {
    return false;
  }

  vector<PreAlignCudaPeak> kept;
  kept.reserve(static_cast<size_t>(topK));
  for(int k = 0; k < topK && k < static_cast<int>(peaks.size()); ++k)
  {
    const PreAlignCudaPeak &p = peaks[static_cast<size_t>(k)];
    if((applyScoreFloor && p.score <= scoreFloor) || p.position < 0)
    {
      continue;
    }
    bool suppressed = false;
    for(size_t s = 0; s < kept.size(); ++s)
    {
      if(abs(kept[s].position - p.position) < suppressBp)
      {
        suppressed = true;
        break;
      }
    }
    if(!suppressed)
    {
      kept.push_back(p);
    }
  }

  hits.reserve(kept.size());
  for(size_t i = 0; i < kept.size(); ++i)
  {
    const PreAlignCudaPeak &p = kept[i];

    const long seedEnd = static_cast<long>(p.position) + 1;
    const double minIdentity = 0.60;
    const double denom = (static_cast<double>(matchScoreInt) + static_cast<double>(mismatchPenaltyInt)) * minIdentity -
                         static_cast<double>(mismatchPenaltyInt);
    long approxLen = 1;
    if(denom > 0.0)
    {
      approxLen = static_cast<long>((static_cast<double>(p.score) + 24.0) / denom + 1.0);
    }
    else if(matchScoreInt > 0)
    {
      approxLen = static_cast<long>(p.score) / static_cast<long>(matchScoreInt);
    }
    if(approxLen < 1)
    {
      approxLen = 1;
    }
    if(approxLen > seedEnd)
    {
      approxLen = seedEnd;
    }
    long seedStart = seedEnd - approxLen + 1;
    if(seedStart < 1) seedStart = 1;
    if(seedEnd < seedStart) continue;

    SimPrefilterHit hit;
    hit.SCORE = static_cast<long>(p.score);
    hit.STARJ = seedStart - 1;
    hit.ENDJ = seedEnd;
    hits.push_back(hit);
  }

  sort(hits.begin(),
       hits.end(),
       [](const SimPrefilterHit &lhs,const SimPrefilterHit &rhs)
       {
         if(lhs.SCORE != rhs.SCORE) return lhs.SCORE > rhs.SCORE;
         if(lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
         return lhs.ENDJ < rhs.ENDJ;
       });
  return true;
}

inline bool exact_sim_prefilter_hits_prealign_cuda(const string &query,
                                                   const string &target,
                                                   int minScore,
                                                   const ExactSimConfig &config,
                                                   int topK,
                                                   int suppressBp,
                                                   vector<SimPrefilterHit> &hits)
{
  const int scoreFloor = minScore - exact_sim_prefilter_score_floor_delta_runtime();
  return exact_sim_prefilter_hits_prealign_cuda_core(query,
                                                     target,
                                                     true,
                                                     scoreFloor,
                                                     config,
                                                     topK,
                                                     suppressBp,
                                                     hits);
}

inline bool exact_sim_prefilter_hits_prealign_cuda_without_floor(const string &query,
                                                                 const string &target,
                                                                 const ExactSimConfig &config,
                                                                 int topK,
                                                                 int suppressBp,
                                                                 vector<SimPrefilterHit> &hits)
{
  return exact_sim_prefilter_hits_prealign_cuda_core(query,
                                                     target,
                                                     false,
                                                     0,
                                                     config,
                                                     topK,
                                                     suppressBp,
                                                     hits);
}

struct ExactSimRefineWindow
{
  ExactSimRefineWindow():
    startJ(0),
    endJ(0),
    bestSeedScore(std::numeric_limits<long>::min()),
    secondBestSeedScore(std::numeric_limits<long>::min()),
    supportCount(0) {}
  ExactSimRefineWindow(int n1,int n2):
    startJ(n1),
    endJ(n2),
    bestSeedScore(std::numeric_limits<long>::min()),
    secondBestSeedScore(std::numeric_limits<long>::min()),
    supportCount(0) {}

  int startJ;
  int endJ;
  long bestSeedScore;
  long secondBestSeedScore;
  long supportCount;
};

inline long exact_sim_refine_window_missing_score()
{
  return std::numeric_limits<long>::min();
}

inline int exact_sim_refine_window_bp(const ExactSimRefineWindow &window)
{
  return window.endJ >= window.startJ ? (window.endJ - window.startJ + 1) : 0;
}

inline long exact_sim_refine_window_margin(const ExactSimRefineWindow &window)
{
  if(window.secondBestSeedScore == exact_sim_refine_window_missing_score())
  {
    return exact_sim_refine_window_missing_score();
  }
  return window.bestSeedScore - window.secondBestSeedScore;
}

inline double exact_sim_refine_window_seed_density(const ExactSimRefineWindow &window)
{
  const int bp = exact_sim_refine_window_bp(window);
  if(bp <= 0)
  {
    return 0.0;
  }
  return static_cast<double>(window.supportCount) / static_cast<double>(bp);
}

inline void exact_sim_refine_window_note_seed_score(ExactSimRefineWindow &window,long score)
{
  if(score >= window.bestSeedScore)
  {
    window.secondBestSeedScore = window.bestSeedScore;
    window.bestSeedScore = score;
    return;
  }
  if(score > window.secondBestSeedScore)
  {
    window.secondBestSeedScore = score;
  }
}

inline void exact_sim_merge_refine_windows(vector<ExactSimRefineWindow> &windows,int mergeGap)
{
  if(windows.empty())
  {
    return;
  }

  sort(windows.begin(),
       windows.end(),
       [](const ExactSimRefineWindow &lhs,const ExactSimRefineWindow &rhs)
       {
         if(lhs.startJ != rhs.startJ) return lhs.startJ < rhs.startJ;
         return lhs.endJ < rhs.endJ;
       });

  vector<ExactSimRefineWindow> merged;
  merged.reserve(windows.size());
  merged.push_back(windows[0]);
  for(size_t i = 1; i < windows.size(); ++i)
  {
    ExactSimRefineWindow &cur = merged.back();
    const ExactSimRefineWindow &w = windows[i];
    if(w.startJ > cur.endJ + mergeGap + 1)
    {
      merged.push_back(w);
      continue;
    }
    if(w.endJ > cur.endJ)
    {
      cur.endJ = w.endJ;
    }
    if(w.bestSeedScore != exact_sim_refine_window_missing_score())
    {
      exact_sim_refine_window_note_seed_score(cur,w.bestSeedScore);
    }
    if(w.secondBestSeedScore != exact_sim_refine_window_missing_score())
    {
      exact_sim_refine_window_note_seed_score(cur,w.secondBestSeedScore);
    }
    cur.supportCount += w.supportCount;
  }
  windows.swap(merged);
}

enum ExactSimTwoStageRejectMode
{
  EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF = 0,
  EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1 = 1,
  EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2 = 2,
};

struct ExactSimTwoStageRejectConfig
{
  ExactSimTwoStageRejectConfig():
    mode(EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF),
    minPeakScore(80),
    minSupport(2),
    minMargin(6),
    strongScoreOverride(100),
    maxWindowsPerTask(8),
    maxBpPerTask(32768) {}

  ExactSimTwoStageRejectMode mode;
  long minPeakScore;
  long minSupport;
  long minMargin;
  long strongScoreOverride;
  long maxWindowsPerTask;
  long maxBpPerTask;
};

struct ExactSimTwoStageSelectiveFallbackConfig
{
  ExactSimTwoStageSelectiveFallbackConfig():
    enabled(false),
    nonEmptyMaxKeptWindows(1),
    nonEmptyMaxScoreGap(6) {}

  bool enabled;
  long nonEmptyMaxKeptWindows;
  long nonEmptyMaxScoreGap;
};

inline ExactSimTwoStageRejectMode exact_sim_two_stage_reject_mode_runtime()
{
  static const ExactSimTwoStageRejectMode mode = []()
  {
    const char *env = getenv("LONGTARGET_TWO_STAGE_REJECT_MODE");
    if(env == NULL || env[0] == '\0')
    {
      return EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF;
    }
    string value(env);
    for(size_t i = 0; i < value.size(); ++i)
    {
      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
    }
    if(value == "minimal_v1" || value == "minimal-v1")
    {
      return EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1;
    }
    if(value == "minimal_v2" || value == "minimal-v2")
    {
      return EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2;
    }
    return EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF;
  }();
  return mode;
}

inline ExactSimTwoStageSelectiveFallbackConfig exact_sim_two_stage_selective_fallback_config_runtime()
{
  ExactSimTwoStageSelectiveFallbackConfig config;
  config.enabled = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK", 0) != 0;
  config.nonEmptyMaxKeptWindows =
    exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS", 1);
  config.nonEmptyMaxScoreGap =
    exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP", 6);
  if(config.nonEmptyMaxKeptWindows < 0)
  {
    config.nonEmptyMaxKeptWindows = 0;
  }
  if(config.nonEmptyMaxScoreGap < 0)
  {
    config.nonEmptyMaxScoreGap = 0;
  }
  return config;
}

inline ExactSimTwoStageRejectConfig exact_sim_two_stage_reject_config_runtime()
{
  ExactSimTwoStageRejectConfig config;
  config.mode = exact_sim_two_stage_reject_mode_runtime();
  config.minPeakScore = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE", 80);
  config.minSupport = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_MIN_SUPPORT", 2);
  config.minMargin = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_MIN_MARGIN", 6);
  config.strongScoreOverride = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE", 100);
  config.maxWindowsPerTask = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK", 8);
  config.maxBpPerTask = exact_sim_env_int_or_default("LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK", 32768);
  if(config.minSupport < 0) config.minSupport = 0;
  if(config.maxWindowsPerTask < 0) config.maxWindowsPerTask = 0;
  if(config.maxBpPerTask < 0) config.maxBpPerTask = 0;
  return config;
}

struct ExactSimTwoStageRejectStats
{
  ExactSimTwoStageRejectStats():
    windowsRejectedByMinPeakScore(0),
    windowsRejectedBySupport(0),
    windowsRejectedByMargin(0),
    windowsTrimmedByMaxWindows(0),
    windowsTrimmedByMaxBp(0),
    singletonRescuedWindows(0),
    singletonRescuedTasks(0),
    singletonRescueBpTotal(0),
    selectiveFallbackTriggeredTasks(0),
    selectiveFallbackNonEmptyTriggeredTasks(0),
    selectiveFallbackSelectedWindows(0),
    selectiveFallbackSelectedBpTotal(0) {}

  uint64_t windowsRejectedByMinPeakScore;
  uint64_t windowsRejectedBySupport;
  uint64_t windowsRejectedByMargin;
  uint64_t windowsTrimmedByMaxWindows;
  uint64_t windowsTrimmedByMaxBp;
  uint64_t singletonRescuedWindows;
  uint64_t singletonRescuedTasks;
  uint64_t singletonRescueBpTotal;
  uint64_t selectiveFallbackTriggeredTasks;
  uint64_t selectiveFallbackNonEmptyTriggeredTasks;
  uint64_t selectiveFallbackSelectedWindows;
  uint64_t selectiveFallbackSelectedBpTotal;
};

enum ExactSimTwoStageWindowRejectReason
{
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_NONE = 0,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MIN_PEAK_SCORE = 1,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN = 2,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN = 3,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_WINDOWS = 4,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_BP = 5,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_RESCUED = 6,
  EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SELECTIVE_FALLBACK = 7,
};

struct ExactSimTwoStageWindowTrace
{
  ExactSimTwoStageWindowTrace():
    originalIndex(0),
    sortedRank(std::numeric_limits<size_t>::max()),
    beforeGate(false),
    afterGate(false),
    peakScoreOk(false),
    supportOk(false),
    marginOk(false),
    strongScoreOk(false),
    selectiveFallbackSelected(false),
    rejectReason(EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_NONE) {}

  size_t originalIndex;
  size_t sortedRank;
  ExactSimRefineWindow window;
  bool beforeGate;
  bool afterGate;
  bool peakScoreOk;
  bool supportOk;
  bool marginOk;
  bool strongScoreOk;
  bool selectiveFallbackSelected;
  ExactSimTwoStageWindowRejectReason rejectReason;
};

inline const char *exact_sim_two_stage_window_reject_reason_label(ExactSimTwoStageWindowRejectReason reason)
{
  switch(reason)
  {
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MIN_PEAK_SCORE:
      return "min_peak_score";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN:
      return "low_support_or_margin";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN:
      return "singleton_missing_margin";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_WINDOWS:
      return "max_windows";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_BP:
      return "max_bp";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_RESCUED:
      return "singleton_rescued";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SELECTIVE_FALLBACK:
      return "selective_fallback";
    case EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_NONE:
    default:
      return "kept";
  }
}

inline long exact_sim_two_stage_singleton_score_override_minimal_v2()
{
  return 85;
}

inline bool exact_sim_refine_window_is_singleton_missing_margin(const ExactSimRefineWindow &window)
{
  return window.supportCount == 1 &&
         (window.secondBestSeedScore == exact_sim_refine_window_missing_score() ||
          exact_sim_refine_window_margin(window) == exact_sim_refine_window_missing_score());
}

inline bool exact_sim_refine_window_sort_before(const ExactSimRefineWindow &lhs,
                                                const ExactSimRefineWindow &rhs)
{
  if(lhs.bestSeedScore != rhs.bestSeedScore) return lhs.bestSeedScore > rhs.bestSeedScore;
  if(lhs.supportCount != rhs.supportCount) return lhs.supportCount > rhs.supportCount;
  const long lhsMargin = exact_sim_refine_window_margin(lhs);
  const long rhsMargin = exact_sim_refine_window_margin(rhs);
  if(lhsMargin != rhsMargin) return lhsMargin > rhsMargin;
  if(lhs.startJ != rhs.startJ) return lhs.startJ < rhs.startJ;
  return lhs.endJ < rhs.endJ;
}

inline bool exact_sim_refine_window_contains(const ExactSimRefineWindow &outer,
                                             const ExactSimRefineWindow &inner)
{
  return outer.startJ <= inner.startJ && outer.endJ >= inner.endJ;
}

inline bool exact_sim_refine_window_covered_by_kept_windows(
  const ExactSimRefineWindow &candidate,
  const vector<ExactSimRefineWindow> &keptWindows)
{
  for(size_t i = 0; i < keptWindows.size(); ++i)
  {
    if(exact_sim_refine_window_contains(keptWindows[i],candidate))
    {
      return true;
    }
  }
  return false;
}

inline void exact_sim_sort_after_gate_windows_and_trace(
  vector<ExactSimRefineWindow> &windows,
  vector<ExactSimTwoStageWindowTrace> *trace)
{
  stable_sort(windows.begin(),
              windows.end(),
              [](const ExactSimRefineWindow &lhs,const ExactSimRefineWindow &rhs)
              {
                return exact_sim_refine_window_sort_before(lhs,rhs);
              });
  if(trace == NULL)
  {
    return;
  }

  vector<size_t> afterGateTraceIndices;
  afterGateTraceIndices.reserve(trace->size());
  for(size_t i = 0; i < trace->size(); ++i)
  {
    if((*trace)[i].afterGate)
    {
      afterGateTraceIndices.push_back(i);
    }
  }
  stable_sort(afterGateTraceIndices.begin(),
              afterGateTraceIndices.end(),
              [trace](size_t lhsIndex,size_t rhsIndex)
              {
                return exact_sim_refine_window_sort_before((*trace)[lhsIndex].window,
                                                           (*trace)[rhsIndex].window);
              });
  for(size_t rank = 0; rank < afterGateTraceIndices.size(); ++rank)
  {
    (*trace)[afterGateTraceIndices[rank]].sortedRank = rank;
  }
}

inline void exact_sim_apply_two_stage_reject_gate_in_place(vector<ExactSimRefineWindow> &windows,
                                                           const ExactSimTwoStageRejectConfig &config,
                                                           ExactSimTwoStageRejectStats *stats = NULL,
                                                           vector<ExactSimTwoStageWindowTrace> *trace = NULL)
{
  struct ExactSimTwoStageSingletonRescueCandidate
  {
    ExactSimRefineWindow window;
    size_t traceIndex;
    bool supportOk;
    bool marginOk;
  };

  if(trace != NULL)
  {
    trace->clear();
    trace->reserve(windows.size());
  }
  vector<ExactSimRefineWindow> kept;
  kept.reserve(windows.size());
  vector<char> keptIsSingletonRescue;
  keptIsSingletonRescue.reserve(windows.size());
  vector<size_t> keptTraceIndices;
  if(trace != NULL)
  {
    keptTraceIndices.reserve(windows.size());
  }
  vector<ExactSimTwoStageSingletonRescueCandidate> singletonCandidates;
  singletonCandidates.reserve(windows.size());
  for(size_t i = 0; i < windows.size(); ++i)
  {
    const ExactSimRefineWindow &window = windows[i];
    const long margin = exact_sim_refine_window_margin(window);
    const bool singletonMissingMargin = exact_sim_refine_window_is_singleton_missing_margin(window);
    ExactSimTwoStageWindowTrace entry;
    entry.originalIndex = i;
    entry.window = window;
    entry.beforeGate = true;
    entry.peakScoreOk = window.bestSeedScore >= config.minPeakScore;
    entry.supportOk = window.supportCount >= config.minSupport;
    entry.marginOk = margin != exact_sim_refine_window_missing_score() &&
                     margin >= config.minMargin;
    entry.strongScoreOk = window.bestSeedScore >= config.strongScoreOverride;

    if(config.mode == EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF)
    {
      entry.afterGate = true;
      if(trace != NULL)
      {
        trace->push_back(entry);
      }
      continue;
    }

    if(!entry.peakScoreOk)
    {
      if(stats != NULL)
      {
        stats->windowsRejectedByMinPeakScore += 1;
      }
      entry.rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MIN_PEAK_SCORE;
      if(trace != NULL)
      {
        trace->push_back(entry);
      }
      continue;
    }

    if(!entry.supportOk && !entry.marginOk && !entry.strongScoreOk)
    {
      entry.rejectReason = singletonMissingMargin
                             ? EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN
                             : EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;
      const bool rescueCandidate =
        config.mode == EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2 &&
        singletonMissingMargin &&
        window.bestSeedScore >= exact_sim_two_stage_singleton_score_override_minimal_v2();
      const size_t traceIndex = trace != NULL ? trace->size() : 0u;
      if(trace != NULL)
      {
        trace->push_back(entry);
      }
      if(rescueCandidate)
      {
        ExactSimTwoStageSingletonRescueCandidate candidate;
        candidate.window = window;
        candidate.traceIndex = traceIndex;
        candidate.supportOk = entry.supportOk;
        candidate.marginOk = entry.marginOk;
        singletonCandidates.push_back(candidate);
      }
      else if(stats != NULL)
      {
        if(!entry.supportOk)
        {
          stats->windowsRejectedBySupport += 1;
        }
        if(!entry.marginOk)
        {
          stats->windowsRejectedByMargin += 1;
        }
      }
      continue;
    }

    const size_t traceIndex = trace != NULL ? trace->size() : 0u;
    if(trace != NULL)
    {
      trace->push_back(entry);
    }
    kept.push_back(window);
    keptIsSingletonRescue.push_back(0);
    if(trace != NULL)
    {
      keptTraceIndices.push_back(traceIndex);
    }
  }

  if(config.mode == EXACT_SIM_TWO_STAGE_REJECT_MODE_OFF)
  {
    return;
  }

  if(config.mode == EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2 && !singletonCandidates.empty())
  {
    size_t bestIndex = 0;
    for(size_t i = 1; i < singletonCandidates.size(); ++i)
    {
      if(singletonCandidates[i].window.bestSeedScore > singletonCandidates[bestIndex].window.bestSeedScore)
      {
        bestIndex = i;
      }
    }
    for(size_t i = 0; i < singletonCandidates.size(); ++i)
    {
      if(i == bestIndex || stats == NULL)
      {
        continue;
      }
      if(!singletonCandidates[i].supportOk)
      {
        stats->windowsRejectedBySupport += 1;
      }
      if(!singletonCandidates[i].marginOk)
      {
        stats->windowsRejectedByMargin += 1;
      }
    }
    kept.push_back(singletonCandidates[bestIndex].window);
    keptIsSingletonRescue.push_back(1);
    if(trace != NULL)
    {
      keptTraceIndices.push_back(singletonCandidates[bestIndex].traceIndex);
      (*trace)[singletonCandidates[bestIndex].traceIndex].rejectReason =
        EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_RESCUED;
    }
  }

  vector<size_t> keptOrder(kept.size(),0u);
  for(size_t i = 0; i < keptOrder.size(); ++i)
  {
    keptOrder[i] = i;
  }
  stable_sort(keptOrder.begin(),
              keptOrder.end(),
              [&kept](size_t lhsIndex,size_t rhsIndex)
              {
                return exact_sim_refine_window_sort_before(kept[lhsIndex],kept[rhsIndex]);
              });

  vector<ExactSimRefineWindow> sortedKept;
  sortedKept.reserve(kept.size());
  vector<char> sortedKeptIsSingletonRescue;
  sortedKeptIsSingletonRescue.reserve(keptIsSingletonRescue.size());
  vector<size_t> sortedTraceIndices;
  if(trace != NULL)
  {
    sortedTraceIndices.reserve(keptTraceIndices.size());
  }
  for(size_t rank = 0; rank < keptOrder.size(); ++rank)
  {
    const size_t keptIndex = keptOrder[rank];
    sortedKept.push_back(kept[keptIndex]);
    sortedKeptIsSingletonRescue.push_back(keptIsSingletonRescue[keptIndex]);
    if(trace != NULL)
    {
      const size_t traceIndex = keptTraceIndices[keptIndex];
      (*trace)[traceIndex].sortedRank = rank;
      sortedTraceIndices.push_back(traceIndex);
    }
  }

  if(config.maxWindowsPerTask >= 0 && static_cast<long>(sortedKept.size()) > config.maxWindowsPerTask)
  {
    if(stats != NULL)
    {
      stats->windowsTrimmedByMaxWindows +=
        static_cast<uint64_t>(sortedKept.size() - static_cast<size_t>(config.maxWindowsPerTask));
    }
    if(trace != NULL)
    {
      for(size_t i = static_cast<size_t>(config.maxWindowsPerTask); i < sortedTraceIndices.size(); ++i)
      {
        (*trace)[sortedTraceIndices[i]].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_WINDOWS;
      }
      sortedTraceIndices.resize(static_cast<size_t>(config.maxWindowsPerTask));
    }
    sortedKept.resize(static_cast<size_t>(config.maxWindowsPerTask));
    sortedKeptIsSingletonRescue.resize(static_cast<size_t>(config.maxWindowsPerTask));
  }

  if(config.maxBpPerTask >= 0)
  {
    vector<ExactSimRefineWindow> budgeted;
    budgeted.reserve(sortedKept.size());
    vector<char> budgetedIsSingletonRescue;
    budgetedIsSingletonRescue.reserve(sortedKeptIsSingletonRescue.size());
    long totalBp = 0;
    for(size_t i = 0; i < sortedKept.size(); ++i)
    {
      const long windowBp = static_cast<long>(exact_sim_refine_window_bp(sortedKept[i]));
      if(windowBp <= 0)
      {
        continue;
      }
      if(totalBp + windowBp > config.maxBpPerTask)
      {
        if(stats != NULL)
        {
          stats->windowsTrimmedByMaxBp += 1;
        }
        if(trace != NULL)
        {
          (*trace)[sortedTraceIndices[i]].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_BP;
        }
        continue;
      }
      totalBp += windowBp;
      budgeted.push_back(sortedKept[i]);
      budgetedIsSingletonRescue.push_back(sortedKeptIsSingletonRescue[i]);
      if(trace != NULL)
      {
        (*trace)[sortedTraceIndices[i]].afterGate = true;
      }
    }
    sortedKept.swap(budgeted);
    sortedKeptIsSingletonRescue.swap(budgetedIsSingletonRescue);
  }
  else if(trace != NULL)
  {
    for(size_t i = 0; i < sortedTraceIndices.size(); ++i)
    {
      (*trace)[sortedTraceIndices[i]].afterGate = true;
    }
  }

  if(stats != NULL)
  {
    for(size_t i = 0; i < sortedKept.size(); ++i)
    {
      if(!sortedKeptIsSingletonRescue[i])
      {
        continue;
      }
      stats->singletonRescuedWindows += 1;
      stats->singletonRescuedTasks += 1;
      const int rescuedBp = exact_sim_refine_window_bp(sortedKept[i]);
      if(rescuedBp > 0)
      {
        stats->singletonRescueBpTotal += static_cast<uint64_t>(rescuedBp);
      }
    }
  }

  windows.swap(sortedKept);
}

inline void exact_sim_apply_two_stage_selective_fallback_in_place(
  vector<ExactSimRefineWindow> &windows,
  const ExactSimTwoStageSelectiveFallbackConfig &config,
  ExactSimTwoStageRejectStats *stats = NULL,
  vector<ExactSimTwoStageWindowTrace> *trace = NULL)
{
  if(!config.enabled || trace == NULL || trace->empty())
  {
    return;
  }

  const bool hadKeptWindows = !windows.empty();
  if(hadKeptWindows && (config.nonEmptyMaxKeptWindows <= 0 ||
                        static_cast<long>(windows.size()) > config.nonEmptyMaxKeptWindows))
  {
    return;
  }

  const ExactSimRefineWindow *bestKeptWindow = NULL;
  if(hadKeptWindows)
  {
    bestKeptWindow = &windows[0];
    for(size_t i = 1; i < windows.size(); ++i)
    {
      if(exact_sim_refine_window_sort_before(windows[i],*bestKeptWindow))
      {
        bestKeptWindow = &windows[i];
      }
    }
  }

  size_t bestTraceIndex = std::numeric_limits<size_t>::max();
  for(size_t i = 0; i < trace->size(); ++i)
  {
    const ExactSimTwoStageWindowTrace &entry = (*trace)[i];
    if(!entry.beforeGate || entry.afterGate)
    {
      continue;
    }
    if(entry.rejectReason != EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN)
    {
      continue;
    }
    if(!exact_sim_refine_window_is_singleton_missing_margin(entry.window))
    {
      continue;
    }
    if(entry.window.bestSeedScore < exact_sim_two_stage_singleton_score_override_minimal_v2())
    {
      continue;
    }
    if(hadKeptWindows)
    {
      if(bestKeptWindow == NULL)
      {
        continue;
      }
      if(exact_sim_refine_window_covered_by_kept_windows(entry.window,windows))
      {
        continue;
      }
      const long bestScoreGap = bestKeptWindow->bestSeedScore - entry.window.bestSeedScore;
      if(bestScoreGap > config.nonEmptyMaxScoreGap)
      {
        continue;
      }
    }
    if(bestTraceIndex == std::numeric_limits<size_t>::max() ||
       exact_sim_refine_window_sort_before(entry.window,(*trace)[bestTraceIndex].window))
    {
      bestTraceIndex = i;
    }
  }

  if(bestTraceIndex == std::numeric_limits<size_t>::max())
  {
    return;
  }

  ExactSimTwoStageWindowTrace &selected = (*trace)[bestTraceIndex];
  windows.push_back(selected.window);
  selected.afterGate = true;
  selected.selectiveFallbackSelected = true;
  selected.rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SELECTIVE_FALLBACK;
  exact_sim_sort_after_gate_windows_and_trace(windows,trace);

  if(stats != NULL)
  {
    stats->selectiveFallbackTriggeredTasks += 1;
    if(hadKeptWindows)
    {
      stats->selectiveFallbackNonEmptyTriggeredTasks += 1;
    }
    stats->selectiveFallbackSelectedWindows += 1;
    const int selectedBp = exact_sim_refine_window_bp(selected.window);
    if(selectedBp > 0)
    {
      stats->selectiveFallbackSelectedBpTotal += static_cast<uint64_t>(selectedBp);
    }
  }
}

inline uint64_t exact_sim_total_refine_window_bp(const vector<ExactSimRefineWindow> &windows)
{
  uint64_t totalBp = 0;
  for(size_t i = 0; i < windows.size(); ++i)
  {
    const int bp = exact_sim_refine_window_bp(windows[i]);
    if(bp > 0)
    {
      totalBp += static_cast<uint64_t>(bp);
    }
  }
  return totalBp;
}

inline void exact_sim_build_refine_windows_from_hits(const vector<SimPrefilterHit> &hits,
                                                     int targetLen,
                                                     int pad,
                                                     vector<ExactSimRefineWindow> &windows)
{
  windows.clear();
  windows.reserve(hits.size());
  for(size_t i = 0; i < hits.size(); ++i)
  {
    const SimPrefilterHit &h = hits[i];
    long seedStart = h.STARJ + 1;
    long seedEnd = h.ENDJ;
    if(seedStart < 1) seedStart = 1;
    if(seedEnd < seedStart) seedEnd = seedStart;
    long winStart = seedStart - static_cast<long>(pad);
    long winEnd = seedEnd + static_cast<long>(pad);
    if(winStart < 1) winStart = 1;
    if(winEnd > targetLen) winEnd = targetLen;
    if(winEnd < winStart)
    {
      continue;
    }
    ExactSimRefineWindow window(static_cast<int>(winStart), static_cast<int>(winEnd));
    window.supportCount = 1;
    exact_sim_refine_window_note_seed_score(window,h.SCORE);
    windows.push_back(window);
  }
}

struct ExactSimDeferredTwoStagePrefilterResult
{
  ExactSimDeferredTwoStagePrefilterResult():
    hadAnySeed(false),
    hadAnyRefineWindowBeforeGate(false),
    hadAnyRefineWindowAfterGate(false),
    prefilterBackend("disabled"),
    prefilterHits(0),
    windowsBeforeGate(0),
    windowsAfterGate(0) {}

  bool hadAnySeed;
  bool hadAnyRefineWindowBeforeGate;
  bool hadAnyRefineWindowAfterGate;
  string prefilterBackend;
  uint64_t prefilterHits;
  uint64_t windowsBeforeGate;
  uint64_t windowsAfterGate;
  ExactSimTwoStageRejectStats rejectStats;
  vector<ExactSimRefineWindow> windows;
};

inline bool collectExactSimTwoStageDeferredPrefilterCore(string &rnaSequence,
                                                         const string &transformedSequence,
                                                         const ExactSimConfig &config,
                                                         ExactSimDeferredTwoStagePrefilterResult &result,
                                                         ExactSimTaskTiming *taskTiming = NULL,
                                                         vector<ExactSimTwoStageWindowTrace> *trace = NULL)
{
  result = ExactSimDeferredTwoStagePrefilterResult();

  const double prefilterStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  vector<SimPrefilterHit> hits;
  if(!prealign_cuda_is_built())
  {
    return false;
  }

  const int topk = exact_sim_prefilter_topk_runtime(EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA);
  const int suppressBp = exact_sim_prefilter_peak_suppress_bp_runtime();
  if(!exact_sim_prefilter_hits_prealign_cuda_without_floor(rnaSequence,
                                                           transformedSequence,
                                                           config,
                                                           topk,
                                                           suppressBp,
                                                           hits))
  {
    if(taskTiming != NULL)
    {
      taskTiming->prefilterSeconds += exact_sim_now_seconds() - prefilterStart;
    }
    return false;
  }

  result.prefilterBackend = "prealign_cuda";
  result.prefilterHits = static_cast<uint64_t>(hits.size());
  result.hadAnySeed = !hits.empty();
  if(taskTiming != NULL)
  {
    taskTiming->prefilterBackend = result.prefilterBackend;
    taskTiming->prefilterHits += result.prefilterHits;
    taskTiming->twoStageHadAnySeed += result.hadAnySeed ? 1u : 0u;
  }
  if(hits.empty())
  {
    if(taskTiming != NULL)
    {
      taskTiming->prefilterSeconds += exact_sim_now_seconds() - prefilterStart;
    }
    return true;
  }

  const int pad = exact_sim_refine_pad_bp_runtime();
  const int mergeGap = exact_sim_refine_merge_gap_bp_runtime();
  const int targetLen = static_cast<int>(transformedSequence.size());
  exact_sim_build_refine_windows_from_hits(hits,targetLen,pad,result.windows);
  exact_sim_merge_refine_windows(result.windows,mergeGap);
  result.windowsBeforeGate = static_cast<uint64_t>(result.windows.size());
  result.hadAnyRefineWindowBeforeGate = !result.windows.empty();
  if(taskTiming != NULL)
  {
    taskTiming->twoStageRefineWindowCountBeforeGate += result.windowsBeforeGate;
    taskTiming->twoStageHadAnyRefineWindowBeforeGate += result.hadAnyRefineWindowBeforeGate ? 1u : 0u;
    taskTiming->prefilterSeconds += exact_sim_now_seconds() - prefilterStart;
  }

  const ExactSimTwoStageRejectConfig rejectConfig = exact_sim_two_stage_reject_config_runtime();
  const ExactSimTwoStageSelectiveFallbackConfig selectiveFallbackConfig =
    exact_sim_two_stage_selective_fallback_config_runtime();
  const double gateStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  exact_sim_apply_two_stage_reject_gate_in_place(result.windows,rejectConfig,&result.rejectStats,trace);
  result.windowsAfterGate = static_cast<uint64_t>(result.windows.size());
  result.hadAnyRefineWindowAfterGate = !result.windows.empty();
  if(selectiveFallbackConfig.enabled &&
     rejectConfig.mode == EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2 &&
     result.hadAnySeed &&
     result.hadAnyRefineWindowBeforeGate)
  {
    exact_sim_apply_two_stage_selective_fallback_in_place(result.windows,
                                                          selectiveFallbackConfig,
                                                          &result.rejectStats,
                                                          trace);
    result.windowsAfterGate = static_cast<uint64_t>(result.windows.size());
    result.hadAnyRefineWindowAfterGate = !result.windows.empty();
  }
  if(taskTiming != NULL)
  {
    taskTiming->twoStageGateSeconds += exact_sim_now_seconds() - gateStart;
    taskTiming->refineWindowCount += result.windowsAfterGate;
    taskTiming->refineTotalBp += exact_sim_total_refine_window_bp(result.windows);
  }
  return true;
}


struct ExactSimTriplexKey
{
  ExactSimTriplexKey():
    stari(0),
    endi(0),
    starj(0),
    endj(0),
    reverse(0),
    strand(0),
    rule(0) {}

  ExactSimTriplexKey(const triplex &t):
    stari(t.stari),
    endi(t.endi),
    starj(t.starj),
    endj(t.endj),
    reverse(t.reverse),
    strand(t.strand),
    rule(t.rule) {}

  int stari;
  int endi;
  int starj;
  int endj;
  int reverse;
  int strand;
  int rule;

  bool operator==(const ExactSimTriplexKey &rhs) const
  {
    return stari == rhs.stari &&
           endi == rhs.endi &&
           starj == rhs.starj &&
           endj == rhs.endj &&
           reverse == rhs.reverse &&
           strand == rhs.strand &&
           rule == rhs.rule;
  }
};

struct ExactSimTriplexKeyHash
{
  size_t operator()(const ExactSimTriplexKey &k) const
  {
    size_t h = 1469598103934665603ull;
    auto mix = [&](uint64_t v)
    {
      h ^= static_cast<size_t>(v + 0x9e3779b97f4a7c15ull + (h << 6) + (h >> 2));
    };
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.stari)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.endi)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.starj)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.endj)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.reverse)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.strand)));
    mix(static_cast<uint64_t>(static_cast<uint32_t>(k.rule)));
    return h;
  }
};

inline void runExactReferenceSIMTwoStageRescueWithWindows(string &rnaSequence,
                                                          const string &transformedSequence,
                                                          const string &sourceSequence,
                                                          long dnaStartPos,
                                                          long reverseMode,
                                                          long parallelMode,
                                                          long rule,
                                                          int minScore,
                                                          const ExactSimConfig &config,
                                                          int ntMin,
                                                          int ntMax,
                                                          int penaltyT,
                                                          int penaltyC,
                                                          const vector<ExactSimRefineWindow> &windows,
                                                          vector<struct triplex> &triplexList)
{
  unordered_set<ExactSimTriplexKey, ExactSimTriplexKeyHash> seen;
  seen.reserve(256);

  for(size_t w = 0; w < windows.size(); ++w)
  {
    const int winStartJ = windows[w].startJ;
    const int winEndJ = windows[w].endJ;
    const int winLen = exact_sim_refine_window_bp(windows[w]);
    if(winLen <= 0)
    {
      continue;
    }

    const string transformedWindow = transformedSequence.substr(static_cast<size_t>(winStartJ - 1), static_cast<size_t>(winLen));

    string sourceWindow;
    long dnaStartPosWindow = dnaStartPos;
    if(reverseMode == 0)
    {
      sourceWindow = sourceSequence.substr(static_cast<size_t>(winStartJ - 1), static_cast<size_t>(winLen));
      dnaStartPosWindow = dnaStartPos + (winStartJ - 1);
    }
    else
    {
      const int fullLen = static_cast<int>(sourceSequence.size());
      const int srcStartJ = fullLen - winEndJ + 1;
      if(srcStartJ < 1 || srcStartJ + winLen - 1 > fullLen)
      {
        continue;
      }
      sourceWindow = sourceSequence.substr(static_cast<size_t>(srcStartJ - 1), static_cast<size_t>(winLen));
      dnaStartPosWindow = dnaStartPos + (srcStartJ - 1);
    }

    vector<struct triplex> localTriplex;
    SIM(rnaSequence,
        transformedWindow,
        sourceWindow,
        dnaStartPosWindow,
        minScore,
        config.matchScore,
        config.mismatchScore,
        config.gapOpen,
        config.gapExtend,
        localTriplex,
        reverseMode,
        parallelMode,
        rule,
        ntMin,
        ntMax,
        penaltyT,
        penaltyC);

    for(size_t i = 0; i < localTriplex.size(); ++i)
    {
      const triplex &t = localTriplex[i];
      const ExactSimTriplexKey key(t);
      if(seen.insert(key).second)
      {
        triplexList.push_back(t);
      }
    }
  }
}

inline void runExactReferenceSIMTwoStageWithMinScore(string &rnaSequence,
                                                     const string &transformedSequence,
                                                     const string &sourceSequence,
                                                     long dnaStartPos,
                                                     long reverseMode,
                                                     long parallelMode,
                                                     long rule,
                                                     int minScore,
                                                     const ExactSimConfig &config,
                                                     int ntMin,
                                                     int ntMax,
                                                     int penaltyT,
                                                     int penaltyC,
                                                     vector<struct triplex> &triplexList,
                                                     ExactSimTaskTiming *taskTiming = NULL)
{
  const double simStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;

  const int pad = exact_sim_refine_pad_bp_runtime();
  const int mergeGap = exact_sim_refine_merge_gap_bp_runtime();

  vector<SimPrefilterHit> hits;
  ExactSimPrefilterBackend backend = exact_sim_prefilter_backend_requested_runtime();
  if(backend == EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA && !prealign_cuda_is_built())
  {
    backend = EXACT_SIM_PREFILTER_BACKEND_SIM;
  }
  const int topk = exact_sim_prefilter_topk_runtime(backend);

  bool usedPrealign = false;
  if(backend == EXACT_SIM_PREFILTER_BACKEND_PREALIGN_CUDA)
  {
    const int suppressBp = exact_sim_prefilter_peak_suppress_bp_runtime();
    if(exact_sim_prefilter_hits_prealign_cuda(rnaSequence,
                                              transformedSequence,
                                              minScore,
                                              config,
                                              topk,
                                              suppressBp,
                                              hits))
    {
      usedPrealign = true;
    }
  }
  if(taskTiming != NULL)
  {
    taskTiming->prefilterBackend = usedPrealign ? "prealign_cuda" : "sim";
    taskTiming->prefilterHits += static_cast<uint64_t>(hits.size());
  }
  if(!usedPrealign)
  {
    SIM_PREFILTER(rnaSequence,
                  transformedSequence,
                  static_cast<long>(minScore),
                  config.matchScore,
                  config.mismatchScore,
                  config.gapOpen,
                  config.gapExtend,
                  hits,
                  exact_sim_prefilter_topk_runtime(EXACT_SIM_PREFILTER_BACKEND_SIM));
  }

  const int targetLen = static_cast<int>(transformedSequence.size());
  vector<ExactSimRefineWindow> windows;
  exact_sim_build_refine_windows_from_hits(hits,targetLen,pad,windows);
  exact_sim_merge_refine_windows(windows, mergeGap);
  if(taskTiming != NULL)
  {
    taskTiming->twoStageHadAnySeed += hits.empty() ? 0u : 1u;
    taskTiming->twoStageHadAnyRefineWindowBeforeGate += windows.empty() ? 0u : 1u;
    taskTiming->twoStageRefineWindowCountBeforeGate += static_cast<uint64_t>(windows.size());
    taskTiming->refineWindowCount += static_cast<uint64_t>(windows.size());
    taskTiming->refineTotalBp += exact_sim_total_refine_window_bp(windows);
  }

  runExactReferenceSIMTwoStageRescueWithWindows(rnaSequence,
                                                transformedSequence,
                                                sourceSequence,
                                                dnaStartPos,
                                                reverseMode,
                                                parallelMode,
                                                rule,
                                                minScore,
                                                config,
                                                ntMin,
                                                ntMax,
                                                penaltyT,
                                                penaltyC,
                                                windows,
                                                triplexList);

  if(taskTiming != NULL)
  {
    taskTiming->simSeconds += exact_sim_now_seconds() - simStart;
  }
}

inline void runExactReferenceSIMTwoStage(string &rnaSequence,
                                         const string &transformedSequence,
                                         const string &sourceSequence,
                                         long dnaStartPos,
                                         long reverseMode,
                                         long parallelMode,
                                         long rule,
                                         const ExactSimConfig &config,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         vector<struct triplex> &triplexList,
                                         ExactSimRunContext *runContext = NULL,
                                         CalcScoreWorkspace *workspace = NULL,
                                         ExactSimTaskTiming *taskTiming = NULL)
{
  CalcScoreWorkspace &activeWorkspace = workspace != NULL ? *workspace : default_exact_sim_calc_score_workspace();
  const double thresholdStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  const int minScore = getExactReferenceMinScore(rnaSequence, transformedSequence, runContext, activeWorkspace);
  if(taskTiming != NULL)
  {
    taskTiming->thresholdSeconds += exact_sim_now_seconds() - thresholdStart;
  }
  runExactReferenceSIMTwoStageWithMinScore(rnaSequence,
                                          transformedSequence,
                                          sourceSequence,
                                          dnaStartPos,
                                          reverseMode,
                                          parallelMode,
                                          rule,
                                          minScore,
                                          config,
                                          ntMin,
                                          ntMax,
                                          penaltyT,
                                          penaltyC,
                                          triplexList,
                                          taskTiming);
}

inline void runExactReferenceSIMTwoStageDeferredWithMinScore(string &rnaSequence,
                                                             const string &transformedSequence,
                                                             const string &sourceSequence,
                                                             long dnaStartPos,
                                                             long reverseMode,
                                                             long parallelMode,
                                                             long rule,
                                                             int minScore,
                                                             const ExactSimConfig &config,
                                                             int ntMin,
                                                             int ntMax,
                                                             int penaltyT,
                                                             int penaltyC,
                                                             const vector<ExactSimRefineWindow> &windows,
                                                             vector<struct triplex> &triplexList,
                                                             ExactSimTaskTiming *taskTiming = NULL)
{
  const double simStart = taskTiming != NULL ? exact_sim_now_seconds() : 0.0;
  runExactReferenceSIMTwoStageRescueWithWindows(rnaSequence,
                                                transformedSequence,
                                                sourceSequence,
                                                dnaStartPos,
                                                reverseMode,
                                                parallelMode,
                                                rule,
                                                minScore,
                                                config,
                                                ntMin,
                                                ntMax,
                                                penaltyT,
                                                penaltyC,
                                                windows,
                                                triplexList);
  if(taskTiming != NULL)
  {
    taskTiming->simSeconds += exact_sim_now_seconds() - simStart;
  }
}

inline void appendExactReferenceSIMCase(string &rnaSequence,
                                        const string &sourceSequence,
                                        long dnaStartPos,
                                        long reverseMode,
                                        long parallelMode,
                                        long rule,
                                        const ExactSimConfig &config,
                                        int ntMin,
                                        int ntMax,
                                        int penaltyT,
                                        int penaltyC,
                                        vector<struct triplex> &triplexList,
                                        ExactSimRunContext *runContext = NULL,
                                        CalcScoreWorkspace *workspace = NULL,
                                        ExactSimTaskTiming *taskTiming = NULL)
{
  string transformedSequence = transferString(sourceSequence, reverseMode, parallelMode, rule);
  if (reverseMode == 1)
  {
    reverseSeq(transformedSequence);
  }
  runExactReferenceSIM(rnaSequence,
                       transformedSequence,
                       sourceSequence,
                       dnaStartPos,
                       reverseMode,
                       parallelMode,
                       rule,
                       config,
                       ntMin,
                       ntMax,
                       penaltyT,
                       penaltyC,
                       triplexList,
                       runContext,
                       workspace,
                       taskTiming);
}

inline void appendExactReferenceSIMRange(string &rnaSequence,
                                         const string &sourceSequence,
                                         long dnaStartPos,
                                         long reverseMode,
                                         long parallelMode,
                                         int firstRule,
                                         int lastRule,
                                         const ExactSimConfig &config,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         vector<struct triplex> &triplexList,
                                         ExactSimRunContext *runContext = NULL,
                                         CalcScoreWorkspace *workspace = NULL,
                                         ExactSimTaskTiming *taskTiming = NULL)
{
  for (int rule = firstRule; rule <= lastRule; ++rule)
  {
    appendExactReferenceSIMCase(rnaSequence,
                                sourceSequence,
                                dnaStartPos,
                                reverseMode,
                                parallelMode,
                                rule,
                                config,
                                ntMin,
                                ntMax,
                                penaltyT,
                                penaltyC,
                                triplexList,
                                runContext,
                                workspace,
                                taskTiming);
  }
}

#endif
