#define main longtarget_cli_main
#include "../longtarget.cpp"
#undef main

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace
{

static bool expect_equal_uint64(uint64_t actual,uint64_t expected,const char *label)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr<<label<<": expected "<<expected<<", got "<<actual<<"\n";
  return false;
}

static bool expect_equal_double(double actual,double expected,const char *label)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr<<label<<": expected "<<expected<<", got "<<actual<<"\n";
  return false;
}

static bool expect_false(bool value,const char *label)
{
  if(!value)
  {
    return true;
  }
  std::cerr<<label<<": expected false, got true\n";
  return false;
}

static struct para make_para()
{
  struct para paraList;
  paraList.file1path = "./";
  paraList.file2path = "./";
  paraList.outpath = "./";
  paraList.rule = 1;
  paraList.cutLength = 8;
  paraList.strand = 1;
  paraList.overlapLength = 0;
  paraList.minScore = 0;
  paraList.detailOutput = false;
  paraList.ntMin = 0;
  paraList.ntMax = 100000;
  paraList.scoreMin = 0.0f;
  paraList.minIdentity = 0.0f;
  paraList.minStability = 0.0f;
  paraList.penaltyT = -1000;
  paraList.penaltyC = 0;
  paraList.cDistance = 15;
  paraList.cLength = 50;
  return paraList;
}

static void clear_runtime_env()
{
  unsetenv("LONGTARGET_ENABLE_CUDA");
  unsetenv("LONGTARGET_ENABLE_SIM_CUDA");
  unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION");
  unsetenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE");
  unsetenv("LONGTARGET_TWO_STAGE");
  unsetenv("LONGTARGET_PREFILTER_BACKEND");
  unsetenv("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2");
  unsetenv("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");
}

static bool test_result_defaults_and_stub_reset()
{
  bool ok = true;

  CalcScoreCudaBatchResult defaults;
  ok = expect_false(defaults.usedCuda,"default usedCuda") && ok;
  ok = expect_equal_double(defaults.gpuSeconds,0.0,"default gpu seconds") && ok;
  ok = expect_equal_double(defaults.targetH2DSeconds,0.0,"default target H2D seconds") && ok;
  ok = expect_equal_double(defaults.permutationH2DSeconds,0.0,"default permutation H2D seconds") && ok;
  ok = expect_equal_double(defaults.kernelSeconds,0.0,"default kernel seconds") && ok;
  ok = expect_equal_double(defaults.scoreD2HSeconds,0.0,"default score D2H seconds") && ok;
  ok = expect_equal_double(defaults.syncWaitSeconds,0.0,"default sync wait seconds") && ok;
  ok = expect_false(defaults.pipelineV2Enabled,"default v2 enabled") && ok;
  ok = expect_false(defaults.pipelineV2ShadowEnabled,"default v2 shadow enabled") && ok;
  ok = expect_false(defaults.pipelineV2Used,"default v2 used") && ok;
  ok = expect_false(defaults.pipelineV2Fallback,"default v2 fallback") && ok;
  ok = expect_equal_uint64(defaults.pipelineV2ShadowComparisons,0,"default v2 shadow comparisons") && ok;
  ok = expect_equal_uint64(defaults.pipelineV2ShadowMismatches,0,"default v2 shadow mismatches") && ok;
  ok = expect_equal_double(defaults.pipelineV2KernelSeconds,0.0,"default v2 kernel seconds") && ok;
  ok = expect_equal_double(defaults.pipelineV2ScoreD2HSeconds,0.0,"default v2 score D2H seconds") && ok;
  ok = expect_equal_double(defaults.pipelineV2HostReduceSeconds,0.0,"default v2 host reduce seconds") && ok;
  ok = expect_equal_uint64(defaults.targetBytesH2D,0,"default target bytes") && ok;
  ok = expect_equal_uint64(defaults.permutationBytesH2D,0,"default permutation bytes") && ok;
  ok = expect_equal_uint64(defaults.scoreBytesD2H,0,"default score bytes") && ok;

  unsigned char target = 0;
  uint16_t permutation = 0;
  std::vector<int> scores(1,123);
  CalcScoreCudaBatchResult result;
  result.usedCuda = true;
  result.targetH2DSeconds = 1.0;
  result.pipelineV2Enabled = true;
  result.pipelineV2ShadowComparisons = 7;
  std::string error;
  const bool computed =
    calc_score_cuda_compute_pair_max_scores(CalcScoreCudaQueryHandle(),
                                            &target,
                                            1,
                                            1,
                                            &permutation,
                                            1,
                                            1,
                                            &scores,
                                            &result,
                                            &error);
  ok = expect_false(computed,"stub compute") && ok;
  ok = expect_equal_uint64(scores.size(),0,"stub clears scores") && ok;
  ok = expect_false(result.usedCuda,"stub resets usedCuda") && ok;
  ok = expect_equal_double(result.targetH2DSeconds,0.0,"stub resets target H2D seconds") && ok;
  ok = expect_false(result.pipelineV2Enabled,"stub resets v2 enabled") && ok;
  ok = expect_equal_uint64(result.pipelineV2ShadowComparisons,0,"stub resets v2 comparisons") && ok;
  return ok;
}

static bool test_direct_cuda_batch_telemetry_accumulates()
{
  LongTargetExecutionMetrics metrics;
  CalcScoreCudaBatchResult batchResult;
  batchResult.usedCuda = true;
  batchResult.targetH2DSeconds = 0.1;
  batchResult.permutationH2DSeconds = 0.2;
  batchResult.kernelSeconds = 0.3;
  batchResult.scoreD2HSeconds = 0.4;
  batchResult.syncWaitSeconds = 0.5;
  batchResult.pipelineV2Enabled = true;
  batchResult.pipelineV2ShadowEnabled = true;
  batchResult.pipelineV2Used = true;
  batchResult.pipelineV2Fallback = true;
  batchResult.pipelineV2ShadowComparisons = 302;
  batchResult.pipelineV2ShadowMismatches = 0;
  batchResult.pipelineV2KernelSeconds = 0.6;
  batchResult.pipelineV2ScoreD2HSeconds = 0.7;
  batchResult.pipelineV2HostReduceSeconds = 0.8;
  batchResult.targetBytesH2D = 80;
  batchResult.permutationBytesH2D = 160;
  batchResult.scoreBytesD2H = 320;

  longtarget_record_calc_score_cuda_batch_telemetry(metrics,2,151,batchResult);

  bool ok = true;
  ok = expect_equal_uint64(metrics.calcScoreCudaGroups,1,"cuda groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPairs,302,"cuda pairs") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaTargetH2DSeconds,0.1,"target H2D seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaPermutationH2DSeconds,0.2,"permutation H2D seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaKernelSeconds,0.3,"kernel seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaScoreD2HSeconds,0.4,"score D2H seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaSyncWaitSeconds,0.5,"sync wait seconds") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2Enabled,1,"v2 enabled") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowEnabled,1,"v2 shadow enabled") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2UsedGroups,1,"v2 used groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2Fallbacks,1,"v2 fallbacks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowComparisons,302,"v2 shadow comparisons") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowMismatches,0,"v2 shadow mismatches") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaPipelineV2KernelSeconds,0.6,"v2 kernel seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaPipelineV2ScoreD2HSeconds,0.7,"v2 score D2H seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreCudaPipelineV2HostReduceSeconds,0.8,"v2 host reduce seconds") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaTargetBytesH2D,80,"target bytes") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPermutationBytesH2D,160,"permutation bytes") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaScoreBytesD2H,320,"score bytes") && ok;
  return ok;
}

static bool test_stub_empty_tasks_keep_zero_telemetry()
{
  clear_runtime_env();
  struct para paraList = make_para();
  std::vector<struct triplex> triplexes;
  LongTargetExecutionMetrics metrics;
  std::string rna = "ACGTACGT";
  std::string dna = "AAAAAAAA";
  LongTarget(paraList,rna,dna,triplexes,&metrics);

  bool ok = true;
  ok = expect_equal_uint64(metrics.calcScoreTasksTotal,0,"empty tasks total") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaGroups,0,"empty cuda groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaTasks,0,"empty cuda tasks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCpuFallbackTasks,0,"empty CPU fallback tasks") && ok;
  ok = expect_equal_double(metrics.calcScoreHostEncodeSeconds,0.0,"empty host encode seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreHostShufflePlanSeconds,0.0,"empty host shuffle seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreHostMleSeconds,0.0,"empty host MLE seconds") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2Enabled,0,"empty v2 enabled") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowEnabled,0,"empty v2 shadow enabled") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2UsedGroups,0,"empty v2 used groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2Fallbacks,0,"empty v2 fallbacks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowComparisons,0,"empty v2 comparisons") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2ShadowMismatches,0,"empty v2 mismatches") && ok;
  return ok;
}

static bool test_stub_cpu_fallback_counts_multi_length_groups()
{
  clear_runtime_env();
  struct para paraList = make_para();
  std::vector<struct triplex> triplexes;
  LongTargetExecutionMetrics metrics;
  std::string rna = "ACGTACGTACGT";
  std::string dna = "ACGTACGTGCTA";
  LongTarget(paraList,rna,dna,triplexes,&metrics);

  bool ok = true;
  ok = expect_equal_uint64(metrics.calcScoreTasksTotal,4,"CPU fallback tasks total") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaGroups,0,"CPU fallback cuda groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaTasks,0,"CPU fallback cuda tasks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCpuFallbackTasks,4,"CPU fallback tasks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCpuFallbackOther,4,"CPU fallback other") && ok;
  ok = expect_equal_uint64(metrics.calcScoreTargetBinLe8192Tasks,4,"CPU fallback target bin tasks") && ok;
  ok = expect_equal_uint64(metrics.calcScoreTargetBinLe8192Bp,24,"CPU fallback target bin bp") && ok;
  ok = expect_equal_double(metrics.calcScoreHostEncodeSeconds,0.0,"CPU fallback host encode seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreHostShufflePlanSeconds,0.0,"CPU fallback host shuffle seconds") && ok;
  ok = expect_equal_double(metrics.calcScoreHostMleSeconds,0.0,"CPU fallback host MLE seconds") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2UsedGroups,0,"CPU fallback v2 used groups") && ok;
  ok = expect_equal_uint64(metrics.calcScoreCudaPipelineV2Fallbacks,0,"CPU fallback v2 fallbacks") && ok;
  return ok;
}

} // namespace

int main()
{
  bool ok = true;
  ok = test_result_defaults_and_stub_reset() && ok;
  ok = test_direct_cuda_batch_telemetry_accumulates() && ok;
  ok = test_stub_empty_tasks_keep_zero_telemetry() && ok;
  ok = test_stub_cpu_fallback_counts_multi_length_groups() && ok;
  if(!ok)
  {
    return 1;
  }
  std::cout<<"ok\n";
  return 0;
}
