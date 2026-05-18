#ifndef LONGTARGET_ACCELIGN_SHADOW_H
#define LONGTARGET_ACCELIGN_SHADOW_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

struct AccelignShadowRequest
{
  AccelignShadowRequest()
    : queryLength(0),
      targetLength(0),
      cpuScore(0),
      cpuRefEnd(-1),
      cpuQueryEnd(-1)
  {
  }

  uint32_t queryLength;
  uint32_t targetLength;
  std::string querySequence;
  std::string targetSequence;
  int cpuScore;
  int cpuRefEnd;
  int cpuQueryEnd;
};

struct AccelignShadowResult
{
  AccelignShadowResult()
    : score(0),
      refEnd(-1),
      queryEnd(-1)
  {
  }

  int score;
  int refEnd;
  int queryEnd;
};

struct AccelignShadowBatchResult
{
  AccelignShadowBatchResult()
    : gpuSeconds(0.0),
      h2dBytes(0),
      d2hBytes(0),
      queryStagingBytes(0),
      targetStagingBytes(0),
      queryReuseActive(false),
      usedCuda(false)
  {
  }

  double gpuSeconds;
  uint64_t h2dBytes;
  uint64_t d2hBytes;
  uint64_t queryStagingBytes;
  uint64_t targetStagingBytes;
  bool queryReuseActive;
  bool usedCuda;
};

bool accelign_shadow_is_built();
bool accelign_shadow_init(int device, std::string *errorOut);

bool accelign_shadow_run_local_affine_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut);

bool accelign_shadow_run_local_affine_score_only_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut);

bool accelign_shadow_run_local_affine_score_only_one_to_all_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut);

#endif
