#ifndef LONGTARGET_PARASAIL_SHADOW_H
#define LONGTARGET_PARASAIL_SHADOW_H

#include <cstdint>
#include <string>
#include <vector>

struct ParasailShadowRequest
{
  ParasailShadowRequest()
    : queryLength(0),
      targetLength(0),
      cpuScore(0),
      cpuRefBegin(0),
      cpuRefEnd(0),
      cpuQueryBegin(0),
      cpuQueryEnd(0),
      cpuNanoseconds(0)
  {
  }

  uint32_t queryLength;
  uint32_t targetLength;
  std::string querySequence;
  std::string targetSequence;
  int cpuScore;
  int cpuRefBegin;
  int cpuRefEnd;
  int cpuQueryBegin;
  int cpuQueryEnd;
  std::string cpuCigarString;
  uint64_t cpuNanoseconds;
};

struct ParasailShadowResult
{
  ParasailShadowResult()
    : score(0),
      refBegin(0),
      refEnd(0),
      queryBegin(0),
      queryEnd(0),
      secondaryScoreSupported(false)
  {
  }

  int score;
  int refBegin;
  int refEnd;
  int queryBegin;
  int queryEnd;
  std::string cigarString;
  bool secondaryScoreSupported;
};

struct ParasailShadowBatchResult
{
  ParasailShadowBatchResult()
    : profileSeconds(0.0),
      alignSeconds(0.0),
      cigarSeconds(0.0),
      totalSeconds(0.0),
      secondaryScoreSupported(false)
  {
  }

  double profileSeconds;
  double alignSeconds;
  double cigarSeconds;
  double totalSeconds;
  bool secondaryScoreSupported;
};

bool parasail_shadow_is_built();

bool parasail_shadow_run_local_ssw(
  const std::vector<ParasailShadowRequest> &requests,
  std::vector<ParasailShadowResult> *outResults,
  ParasailShadowBatchResult *batchResult,
  std::string *errorOut);

#endif
