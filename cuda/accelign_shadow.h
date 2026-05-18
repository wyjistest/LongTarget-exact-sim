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
      usedCuda(false)
  {
  }

  double gpuSeconds;
  uint64_t h2dBytes;
  uint64_t d2hBytes;
  bool usedCuda;
};

bool accelign_shadow_is_built();
bool accelign_shadow_init(int device, std::string *errorOut);

bool accelign_shadow_run_local_affine_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut);

#endif
