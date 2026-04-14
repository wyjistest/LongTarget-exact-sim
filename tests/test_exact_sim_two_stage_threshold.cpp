#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <vector>

#include "../exact_sim.h"

namespace
{

static bool expect_equal_int(int actual, int expected, const char *label)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
  return false;
}

static bool expect_equal_long(long actual, long expected, const char *label)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
  return false;
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
  return false;
}

static bool expect_true(bool value, const char *label)
{
  if(value)
  {
    return true;
  }
  std::cerr << label << ": expected true, got false\n";
  return false;
}

static bool expect_false(bool value, const char *label)
{
  if(!value)
  {
    return true;
  }
  std::cerr << label << ": expected false, got true\n";
  return false;
}

static bool expect_equal_cstr(const char *actual, const char *expected, const char *label)
{
  if(std::strcmp(actual, expected) == 0)
  {
    return true;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
  return false;
}

static ExactSimRefineWindow make_window(int startJ,
                                        int endJ,
                                        long bestSeedScore,
                                        long secondBestSeedScore,
                                        long supportCount)
{
  ExactSimRefineWindow window(startJ,endJ);
  window.bestSeedScore = bestSeedScore;
  window.secondBestSeedScore = secondBestSeedScore;
  window.supportCount = supportCount;
  return window;
}

} // namespace

int main()
{
  bool ok = true;

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(10,20,95,80,1));
    windows.push_back(make_window(18,30,110,90,1));
    windows.push_back(make_window(50,60,70,std::numeric_limits<long>::min(),1));

    exact_sim_merge_refine_windows(windows,3);

    ok = expect_equal_size(windows.size(),2u,"merged window count") && ok;
    ok = expect_equal_int(windows[0].startJ,10,"merged[0].startJ") && ok;
    ok = expect_equal_int(windows[0].endJ,30,"merged[0].endJ") && ok;
    ok = expect_equal_long(windows[0].bestSeedScore,110,"merged[0].best score") && ok;
    ok = expect_equal_long(windows[0].secondBestSeedScore,95,"merged[0].second best") && ok;
    ok = expect_equal_long(windows[0].supportCount,2,"merged[0].support") && ok;
    ok = expect_equal_long(exact_sim_refine_window_margin(windows[0]),15,"merged[0].margin") && ok;
  }

  {
    ExactSimTwoStageRejectConfig config;
    config.mode = EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1;
    config.minPeakScore = 80;
    config.minSupport = 2;
    config.minMargin = 6;
    config.strongScoreOverride = 100;
    config.maxWindowsPerTask = 2;
    config.maxBpPerTask = 30;

    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(1,10,90,89,1));
    windows.push_back(make_window(20,30,95,std::numeric_limits<long>::min(),2));
    windows.push_back(make_window(40,55,105,104,1));
    windows.push_back(make_window(70,90,92,80,1));

    ExactSimTwoStageRejectStats stats;
    exact_sim_apply_two_stage_reject_gate_in_place(windows,config,&stats);

    ok = expect_equal_size(windows.size(),2u,"gated window count") && ok;
    ok = expect_equal_int(windows[0].startJ,40,"gated[0].startJ") && ok;
    ok = expect_equal_int(windows[1].startJ,20,"gated[1].startJ") && ok;
    ok = expect_equal_long(stats.windowsRejectedByMinPeakScore,0,"rejected by score") && ok;
    ok = expect_equal_long(stats.windowsRejectedBySupport,1,"rejected by support") && ok;
    ok = expect_equal_long(stats.windowsRejectedByMargin,1,"rejected by margin") && ok;
    ok = expect_equal_long(stats.windowsTrimmedByMaxWindows,1,"trimmed by max windows") && ok;
    ok = expect_equal_long(stats.windowsTrimmedByMaxBp,0,"trimmed by max bp") && ok;
  }

  {
    ExactSimTwoStageRejectConfig config;
    config.mode = EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1;
    config.minPeakScore = 80;
    config.minSupport = 2;
    config.minMargin = 6;
    config.strongScoreOverride = 100;
    config.maxWindowsPerTask = 1;
    config.maxBpPerTask = 100;

    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(1,10,70,65,2));
    windows.push_back(make_window(20,30,95,std::numeric_limits<long>::min(),1));
    windows.push_back(make_window(40,52,105,104,1));
    windows.push_back(make_window(60,72,102,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace;
    exact_sim_apply_two_stage_reject_gate_in_place(windows,config,&stats,&trace);

    ok = expect_equal_size(trace.size(),4u,"trace window count") && ok;
    ok = expect_equal_int(
           static_cast<int>(trace[0].rejectReason),
           static_cast<int>(EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MIN_PEAK_SCORE),
           "trace[0] reject reason") && ok;
    ok = expect_false(trace[0].afterGate,"trace[0] after gate") && ok;
    ok = expect_equal_cstr(
           exact_sim_two_stage_window_reject_reason_label(trace[1].rejectReason),
           "singleton_missing_margin",
           "trace[1] reject reason label") && ok;
    ok = expect_false(trace[1].afterGate,"trace[1] after gate") && ok;
    ok = expect_equal_int(
           static_cast<int>(trace[2].rejectReason),
           static_cast<int>(EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_NONE),
           "trace[2] reject reason") && ok;
    ok = expect_true(trace[2].afterGate,"trace[2] after gate") && ok;
    ok = expect_equal_int(
           static_cast<int>(trace[3].rejectReason),
           static_cast<int>(EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_MAX_WINDOWS),
           "trace[3] reject reason") && ok;
    ok = expect_false(trace[3].afterGate,"trace[3] after gate") && ok;
  }

  {
    ExactSimTwoStageRejectConfig config;
    config.mode = EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V2;
    config.minPeakScore = 80;
    config.minSupport = 2;
    config.minMargin = 6;
    config.strongScoreOverride = 100;
    config.maxWindowsPerTask = 8;
    config.maxBpPerTask = 200;

    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(1,10,85,std::numeric_limits<long>::min(),1));
    windows.push_back(make_window(20,30,90,std::numeric_limits<long>::min(),1));
    windows.push_back(make_window(40,55,105,104,1));
    windows.push_back(make_window(70,82,70,65,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace;
    exact_sim_apply_two_stage_reject_gate_in_place(windows,config,&stats,&trace);

    ok = expect_equal_size(windows.size(),2u,"minimal_v2 rescued window count") && ok;
    ok = expect_equal_int(windows[0].startJ,40,"minimal_v2 strongest kept first") && ok;
    ok = expect_equal_int(windows[1].startJ,20,"minimal_v2 rescues best singleton") && ok;
    ok = expect_false(trace[0].afterGate,"minimal_v2 lower singleton stays rejected") && ok;
    ok = expect_true(trace[1].afterGate,"minimal_v2 higher singleton rescued") && ok;
    ok = expect_equal_cstr(
           exact_sim_two_stage_window_reject_reason_label(trace[1].rejectReason),
           "singleton_rescued",
           "minimal_v2 rescued singleton label") && ok;
    ok = expect_equal_cstr(
           exact_sim_two_stage_window_reject_reason_label(trace[0].rejectReason),
           "singleton_missing_margin",
           "minimal_v2 lower singleton reject label") && ok;
    ok = expect_equal_long(stats.singletonRescuedWindows,1,"minimal_v2 rescued windows") && ok;
    ok = expect_equal_long(stats.singletonRescuedTasks,1,"minimal_v2 rescued tasks") && ok;
    ok = expect_equal_long(stats.singletonRescueBpTotal,11,"minimal_v2 rescued bp") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(3);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(1,10,85,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;
    trace[1].originalIndex = 1;
    trace[1].window = make_window(20,32,90,std::numeric_limits<long>::min(),1);
    trace[1].beforeGate = true;
    trace[1].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;
    trace[2].originalIndex = 2;
    trace[2].window = make_window(40,56,110,100,1);
    trace[2].beforeGate = true;
    trace[2].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"selective fallback adds one window") && ok;
    ok = expect_equal_int(windows[0].startJ,20,"selective fallback keeps strongest singleton") && ok;
    ok = expect_false(trace[0].afterGate,"weaker singleton stays rejected") && ok;
    ok = expect_true(trace[1].afterGate,"fallback-selected singleton becomes after-gate") && ok;
    ok = expect_true(trace[1].selectiveFallbackSelected,"selected trace flagged for fallback") && ok;
    ok = expect_equal_size(trace[1].sortedRank,0u,"fallback-selected trace rank") && ok;
    ok = expect_equal_cstr(
           exact_sim_two_stage_window_reject_reason_label(trace[1].rejectReason),
           "selective_fallback",
           "fallback-selected label") && ok;
    ok = expect_equal_long(stats.selectiveFallbackTriggeredTasks,1,"fallback triggered tasks") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedWindows,1,"fallback selected windows") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedBpTotal,13,"fallback selected bp") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(3);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(60,72,96,90,2);
    trace[0].beforeGate = true;
    trace[0].afterGate = true;
    trace[0].sortedRank = 0;
    trace[1].originalIndex = 1;
    trace[1].window = make_window(20,32,92,std::numeric_limits<long>::min(),1);
    trace[1].beforeGate = true;
    trace[1].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;
    trace[2].originalIndex = 2;
    trace[2].window = make_window(1,10,86,std::numeric_limits<long>::min(),1);
    trace[2].beforeGate = true;
    trace[2].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 5;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),2u,"non-empty ambiguity fallback adds one window") && ok;
    ok = expect_equal_int(windows[0].startJ,60,"non-empty ambiguity keeps strongest kept first") && ok;
    ok = expect_equal_int(windows[1].startJ,20,"non-empty ambiguity keeps best rejected singleton second") && ok;
    ok = expect_true(trace[0].afterGate,"non-empty ambiguity keeps prior winner after gate") && ok;
    ok = expect_equal_size(trace[0].sortedRank,0u,"non-empty ambiguity keeps winner rank") && ok;
    ok = expect_true(trace[1].afterGate,"non-empty ambiguity selected trace becomes after-gate") && ok;
    ok = expect_true(trace[1].selectiveFallbackSelected,"non-empty ambiguity marks selected trace") && ok;
    ok = expect_equal_size(trace[1].sortedRank,1u,"non-empty ambiguity selected rank") && ok;
    ok = expect_false(trace[2].afterGate,"weaker rejected singleton stays rejected") && ok;
    ok = expect_false(trace[2].selectiveFallbackSelected,"weaker rejected singleton not selected") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"non-empty ambiguity candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks,0,"non-empty ambiguity max-kept rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks,0,"non-empty ambiguity no-singleton rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedBySingletonOverrideTasks,0,"non-empty ambiguity override rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks,0,"non-empty ambiguity covered rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByScoreGapTasks,0,"non-empty ambiguity score-gap rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackTriggeredTasks,1,"non-empty ambiguity increments total fallback trigger") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyTriggeredTasks,1,"non-empty ambiguity increments dedicated trigger counter") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedWindows,1,"non-empty ambiguity selected windows") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedBpTotal,13,"non-empty ambiguity selected bp") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,102,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,90,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 5;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"wide-gap non-empty result skips fallback") && ok;
    ok = expect_equal_int(windows[0].startJ,60,"wide-gap existing gate winner preserved") && ok;
    ok = expect_false(trace[0].afterGate,"wide-gap non-empty result leaves rejected trace untouched") && ok;
    ok = expect_false(trace[0].selectiveFallbackSelected,"wide-gap non-empty result does not mark fallback") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"wide-gap candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByScoreGapTasks,1,"wide-gap score-gap rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackTriggeredTasks,0,"wide-gap non-empty result no fallback trigger") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));
    windows.push_back(make_window(90,102,94,88,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,92,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),2u,"max-kept non-empty result keeps original windows") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"max-kept candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByMaxKeptWindowsTasks,1,"max-kept rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks,0,"max-kept no singleton count") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,92,89,2);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"no-singleton non-empty result keeps original winner") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"no-singleton candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks,1,"no-singleton rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedBySingletonOverrideTasks,0,"no-singleton override rejection count") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(2);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,77,75,1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;
    trace[1].originalIndex = 1;
    trace[1].window = make_window(40,52,70,68,1);
    trace[1].beforeGate = true;
    trace[1].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 2;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    fallbackConfig.nonEmptyEnableScoreBand7579 = true;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),2u,"score-band non-empty result adds one window") && ok;
    ok = expect_equal_int(windows[0].startJ,60,"score-band non-empty keeps original winner first") && ok;
    ok = expect_equal_int(windows[1].startJ,20,"score-band non-empty rescues 75-79 candidate") && ok;
    ok = expect_true(trace[0].afterGate,"score-band candidate becomes after-gate") && ok;
    ok = expect_true(trace[0].selectiveFallbackSelected,"score-band candidate marked selected") && ok;
    ok = expect_false(trace[1].afterGate,"lt-75 candidate stays rejected") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"score-band candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks,0,"score-band no-singleton rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyTriggeredTasks,1,"score-band triggered count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedWindows,1,"score-band selected windows") && ok;
    ok = expect_equal_long(stats.selectiveFallbackSelectedBpTotal,13,"score-band selected bp") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,70,68,1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 2;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    fallbackConfig.nonEmptyEnableScoreBand7579 = true;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"lt-75 score-band result keeps original winner") && ok;
    ok = expect_false(trace[0].afterGate,"lt-75 score-band result leaves rejected trace untouched") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"lt-75 score-band candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByNoSingletonMissingMarginTasks,1,"lt-75 score-band keeps no-singleton rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyTriggeredTasks,0,"lt-75 score-band does not trigger") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(60,72,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,84,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"override-blocked non-empty result keeps original winner") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"override-blocked candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedBySingletonOverrideTasks,1,"override-blocked rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks,0,"override-blocked covered rejection count") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(10,40,96,90,2));

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(1);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(20,32,92,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    fallbackConfig.nonEmptyMaxKeptWindows = 1;
    fallbackConfig.nonEmptyMaxScoreGap = 6;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_equal_size(windows.size(),1u,"covered non-empty result keeps original winner") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyCandidateTasks,1,"covered candidate count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedAsCoveredByKeptTasks,1,"covered rejection count") && ok;
    ok = expect_equal_long(stats.selectiveFallbackNonEmptyRejectedByScoreGapTasks,0,"covered score-gap rejection count") && ok;
  }

  {
    std::vector<ExactSimRefineWindow> windows;

    ExactSimTwoStageRejectStats stats;
    std::vector<ExactSimTwoStageWindowTrace> trace(2);
    trace[0].originalIndex = 0;
    trace[0].window = make_window(1,10,84,std::numeric_limits<long>::min(),1);
    trace[0].beforeGate = true;
    trace[0].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_SINGLETON_MISSING_MARGIN;
    trace[1].originalIndex = 1;
    trace[1].window = make_window(20,32,95,90,1);
    trace[1].beforeGate = true;
    trace[1].rejectReason = EXACT_SIM_TWO_STAGE_WINDOW_REJECT_REASON_LOW_SUPPORT_OR_MARGIN;

    ExactSimTwoStageSelectiveFallbackConfig fallbackConfig;
    fallbackConfig.enabled = true;
    exact_sim_apply_two_stage_selective_fallback_in_place(windows,fallbackConfig,&stats,&trace);

    ok = expect_true(windows.empty(),"below-threshold trace does not trigger fallback") && ok;
    ok = expect_false(trace[0].selectiveFallbackSelected,"below-threshold singleton not selected") && ok;
    ok = expect_equal_long(stats.selectiveFallbackTriggeredTasks,0,"below-threshold no fallback trigger") && ok;
  }

  {
    ExactSimTwoStageRejectConfig config;
    config.mode = EXACT_SIM_TWO_STAGE_REJECT_MODE_MINIMAL_V1;
    config.minPeakScore = 80;
    config.minSupport = 2;
    config.minMargin = 6;
    config.strongScoreOverride = 100;
    config.maxWindowsPerTask = 8;
    config.maxBpPerTask = 5;

    std::vector<ExactSimRefineWindow> windows;
    windows.push_back(make_window(1,8,120,110,1));
    windows.push_back(make_window(20,26,118,112,1));

    ExactSimTwoStageRejectStats stats;
    exact_sim_apply_two_stage_reject_gate_in_place(windows,config,&stats);

    ok = expect_true(windows.empty(),"bp cap empties task") && ok;
    ok = expect_equal_long(stats.windowsTrimmedByMaxBp,2,"trimmed by bp") && ok;
  }

  {
    ExactSimTwoStageDiscoverySummary summary;
    summary.taskCount = 12;
    summary.tasksWithAnySeed = 4;
    summary.tasksWithAnyRefineWindowBeforeGate = 3;
    summary.tasksWithAnyRefineWindowAfterGate = 0;
    summary.windowsBeforeGate = 7;
    summary.windowsAfterGate = 0;

    ok = expect_equal_int(
           static_cast<int>(exact_sim_two_stage_discovery_status_from_summary(summary)),
           static_cast<int>(EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_OK),
           "predicted skip discovery status") && ok;
    ok = expect_true(exact_sim_two_stage_discovery_predicted_skip(summary),
                     "predicted skip discovery flag") && ok;
  }

  {
    ExactSimTwoStageDiscoverySummary summary;
    summary.taskCount = 12;
    summary.prefilterFailedTasks = 1;
    summary.tasksWithAnySeed = 4;
    summary.tasksWithAnyRefineWindowBeforeGate = 4;
    summary.tasksWithAnyRefineWindowAfterGate = 2;

    ok = expect_equal_int(
           static_cast<int>(exact_sim_two_stage_discovery_status_from_summary(summary)),
           static_cast<int>(EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_PREFILTER_FAILED),
           "prefilter failed discovery status") && ok;
    ok = expect_false(exact_sim_two_stage_discovery_predicted_skip(summary),
                      "prefilter failed disables predicted skip") && ok;
  }

  {
    ExactSimTwoStageDiscoverySummary summary;
    summary.taskCount = 12;

    ok = expect_equal_int(
           static_cast<int>(exact_sim_two_stage_discovery_status_from_summary(summary)),
           static_cast<int>(EXACT_SIM_TWO_STAGE_DISCOVERY_STATUS_EMPTY),
           "empty discovery status") && ok;
    ok = expect_false(exact_sim_two_stage_discovery_predicted_skip(summary),
                      "empty discovery flag") && ok;
  }

  if(!ok)
  {
    return 1;
  }

  std::cout << "ok\n";
  return 0;
}
