#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace
{

bool expect_equal(const char *field,int actual,int expected)
{
  if(actual == expected)
  {
    return true;
  }
  std::cerr << field << ": expected " << expected << ", got " << actual << "\n";
  return false;
}

bool check_endpoint(const PreAlignCudaAttemptEndpoint &endpoint,
                    int forwardScore,
                    int reverseScore,
                    int targetEnd,
                    int queryEnd,
                    int numericPath)
{
  bool ok = true;
  ok = expect_equal("forwardScore", endpoint.forwardScore, forwardScore) && ok;
  ok = expect_equal("reverseScore", endpoint.reverseScore, reverseScore) && ok;
  ok = expect_equal("canonicalScore", endpoint.canonicalScore,
                    forwardScore < reverseScore ? forwardScore : reverseScore) && ok;
  ok = expect_equal("targetEnd", endpoint.targetEnd, targetEnd) && ok;
  ok = expect_equal("queryEnd", endpoint.queryEnd, queryEnd) && ok;
  ok = expect_equal("numericPath", endpoint.numericPath, numericPath) && ok;
  return ok;
}

} // namespace

int main()
{
  std::string error;
  if(!prealign_cuda_is_built() || !prealign_cuda_init(0, &error))
  {
    std::cerr << "CUDA prealign unavailable: " << error << "\n";
    return 1;
  }

  const std::string query(3000, 'A');
  std::vector<int16_t> profile;
  int profileSegLen = 0;
  prealign_shared_build_query_profile(query, 5, 4, profile, profileSegLen);

  PreAlignCudaQueryHandle handle;
  if(!prealign_cuda_prepare_query(&handle, profile.data(), 5, profileSegLen,
                                  static_cast<int>(query.size()), &error))
  {
    std::cerr << "query preparation failed: " << error << "\n";
    return 1;
  }

  const int taskCount = 2;
  const int targetLength = 100;
  std::vector<uint8_t> targets(static_cast<size_t>(taskCount * targetLength), 4);
  for(int i = 0; i < targetLength; ++i)
  {
    targets[static_cast<size_t>(i)] = 0;
  }
  for(int i = 0; i < 20; ++i)
  {
    targets[static_cast<size_t>(targetLength + i)] = 0;
  }

  std::vector<PreAlignCudaAttemptEndpoint> endpoints;
  PreAlignCudaBatchResult batch;
  const bool scored = prealign_cuda_find_max_endpoints_batch(
    handle, targets.data(), taskCount, targetLength, &endpoints, &batch, &error);
  prealign_cuda_release_query(&handle);
  if(!scored)
  {
    std::cerr << "endpoint batch failed: " << error << "\n";
    return 1;
  }
  if(endpoints.size() != static_cast<size_t>(taskCount) || !batch.usedCuda)
  {
    std::cerr << "endpoint batch cardinality or CUDA authority mismatch\n";
    return 1;
  }

  bool ok = true;
  ok = check_endpoint(endpoints[0], 500, 500, 99, 99,
                      PREALIGN_CUDA_NUMERIC_PATH_WORD16) && ok;
  ok = check_endpoint(endpoints[1], 100, 100, 19, 19,
                      PREALIGN_CUDA_NUMERIC_PATH_BYTE8) && ok;
  return ok ? 0 : 1;
}
