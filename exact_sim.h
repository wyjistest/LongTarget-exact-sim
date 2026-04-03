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
    prefilterBackend("disabled"),
    prefilterHits(0),
    refineWindowCount(0),
    refineTotalBp(0) {}

  double thresholdSeconds;
  double simSeconds;
  string prefilterBackend;
  uint64_t prefilterHits;
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

inline bool exact_sim_prefilter_hits_prealign_cuda(const string &query,
                                                   const string &target,
                                                   int minScore,
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
  const int scoreFloor = minScore - exact_sim_prefilter_score_floor_delta_runtime();
  for(int k = 0; k < topK && k < static_cast<int>(peaks.size()); ++k)
  {
    const PreAlignCudaPeak &p = peaks[static_cast<size_t>(k)];
    if(p.score <= scoreFloor || p.position < 0)
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

struct ExactSimRefineWindow
{
  ExactSimRefineWindow():startJ(0),endJ(0) {}
  ExactSimRefineWindow(int n1,int n2):startJ(n1),endJ(n2) {}

  int startJ;
  int endJ;
};

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
  }
  windows.swap(merged);
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
    windows.push_back(ExactSimRefineWindow(static_cast<int>(winStart), static_cast<int>(winEnd)));
  }
  exact_sim_merge_refine_windows(windows, mergeGap);
  if(taskTiming != NULL)
  {
    taskTiming->refineWindowCount += static_cast<uint64_t>(windows.size());
    for(size_t i = 0; i < windows.size(); ++i)
    {
      const int winLen = windows[i].endJ >= windows[i].startJ ? (windows[i].endJ - windows[i].startJ + 1) : 0;
      if(winLen > 0)
      {
        taskTiming->refineTotalBp += static_cast<uint64_t>(winLen);
      }
    }
  }

  unordered_set<ExactSimTriplexKey, ExactSimTriplexKeyHash> seen;
  seen.reserve(256);

  for(size_t w = 0; w < windows.size(); ++w)
  {
    const int winStartJ = windows[w].startJ;
    const int winEndJ = windows[w].endJ;
    const int winLen = winEndJ >= winStartJ ? (winEndJ - winStartJ + 1) : 0;
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
