#include "parasail_shadow.h"

#include <chrono>
#include <sstream>

#include <parasail.h>

namespace {

uint64_t parasail_shadow_now_nanoseconds()
{
  return static_cast<uint64_t>(
    std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count());
}

double parasail_shadow_seconds_from_nanoseconds(uint64_t nanoseconds)
{
  return static_cast<double>(nanoseconds) / 1000000000.0;
}

std::string parasail_shadow_cigar_string(const uint32_t *cigar, int32_t cigarLen)
{
  std::ostringstream out;
  for (int32_t i = 0; i < cigarLen; ++i)
  {
    const uint32_t packed = cigar[i];
    const char op = (packed & 0xfU) > 8 ? 'M' : "MIDNSHP=X"[packed & 0xfU];
    const uint32_t len = packed >> 4U;
    out << len << op;
  }
  return out.str();
}

}  // namespace

bool parasail_shadow_is_built()
{
  return true;
}

bool parasail_shadow_run_local_ssw(
  const std::vector<ParasailShadowRequest> &requests,
  std::vector<ParasailShadowResult> *outResults,
  ParasailShadowBatchResult *batchResult,
  std::string *errorOut)
{
  if (outResults == NULL || batchResult == NULL)
  {
    if (errorOut != NULL)
    {
      *errorOut = "Parasail shadow output pointers are null";
    }
    return false;
  }

  outResults->clear();
  outResults->reserve(requests.size());
  *batchResult = ParasailShadowBatchResult();
  batchResult->secondaryScoreSupported = false;

  const uint64_t totalStart = parasail_shadow_now_nanoseconds();
  uint64_t profileNanoseconds = 0;
  uint64_t alignNanoseconds = 0;
  uint64_t cigarNanoseconds = 0;

  parasail_matrix_t *matrix = parasail_matrix_create("ACGTN", 5, -4);
  if (matrix == NULL)
  {
    if (errorOut != NULL)
    {
      *errorOut = "Parasail matrix creation failed";
    }
    return false;
  }
  for (int row = 0; row < 5; ++row)
  {
    parasail_matrix_set_value(matrix, row, 4, -4);
    parasail_matrix_set_value(matrix, 4, row, -4);
  }

  for (size_t i = 0; i < requests.size(); ++i)
  {
    const ParasailShadowRequest &request = requests[i];
    const uint64_t profileStart = parasail_shadow_now_nanoseconds();
    parasail_profile_t *profile = parasail_ssw_init(
      request.querySequence.c_str(),
      static_cast<int>(request.queryLength),
      matrix,
      2);
    profileNanoseconds += parasail_shadow_now_nanoseconds() - profileStart;
    if (profile == NULL)
    {
      parasail_matrix_free(matrix);
      if (errorOut != NULL)
      {
        *errorOut = "Parasail profile creation failed";
      }
      return false;
    }

    const uint64_t alignStart = parasail_shadow_now_nanoseconds();
    parasail_result_ssw_t *result = parasail_ssw_profile(
      profile,
      request.targetSequence.c_str(),
      static_cast<int>(request.targetLength),
      16,
      4);
    alignNanoseconds += parasail_shadow_now_nanoseconds() - alignStart;
    parasail_profile_free(profile);
    if (result == NULL)
    {
      parasail_matrix_free(matrix);
      if (errorOut != NULL)
      {
        *errorOut = "Parasail alignment failed";
      }
      return false;
    }

    const uint64_t cigarStart = parasail_shadow_now_nanoseconds();
    ParasailShadowResult shadowResult;
    shadowResult.score = static_cast<int>(result->score1);
    shadowResult.refBegin = static_cast<int>(result->ref_begin1);
    shadowResult.refEnd = static_cast<int>(result->ref_end1);
    shadowResult.queryBegin = static_cast<int>(result->read_begin1);
    shadowResult.queryEnd = static_cast<int>(result->read_end1);
    shadowResult.cigarString =
      parasail_shadow_cigar_string(result->cigar, result->cigarLen);
    shadowResult.secondaryScoreSupported = false;
    outResults->push_back(shadowResult);
    cigarNanoseconds += parasail_shadow_now_nanoseconds() - cigarStart;

    parasail_result_ssw_free(result);
  }

  parasail_matrix_free(matrix);
  batchResult->profileSeconds =
    parasail_shadow_seconds_from_nanoseconds(profileNanoseconds);
  batchResult->alignSeconds =
    parasail_shadow_seconds_from_nanoseconds(alignNanoseconds);
  batchResult->cigarSeconds =
    parasail_shadow_seconds_from_nanoseconds(cigarNanoseconds);
  batchResult->totalSeconds =
    parasail_shadow_seconds_from_nanoseconds(
      parasail_shadow_now_nanoseconds() - totalStart);
  return true;
}
