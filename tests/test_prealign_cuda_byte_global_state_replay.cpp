#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace
{

std::string make_query(int length)
{
  static const char alphabet[] = "ACGT";
  std::string query;
  query.reserve(static_cast<size_t>(length));
  uint32_t state = 0x6a09e667u + static_cast<uint32_t>(length);
  for(int index = 0; index < length; ++index)
  {
    state = state * 1664525u + 1013904223u;
    query.push_back(alphabet[(state >> 29) & 3u]);
  }
  return query;
}

std::vector<uint8_t> make_targets(int taskCount,int targetLength)
{
  std::vector<uint8_t> targets(
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength));
  uint32_t state = 0xbb67ae85u;
  for(size_t index = 0; index < targets.size(); ++index)
  {
    state = state * 1103515245u + 12345u;
    targets[index] = static_cast<uint8_t>((state >> 27) % 5u);
  }
  return targets;
}

bool compare_case(const std::string &query,
                  const std::vector<uint8_t> &targets,
                  int taskCount,
                  int targetLength,
                  bool requireReplay,
                  bool requireNoReplay)
{
  std::vector<int16_t> profile;
  int segLen = 0;
  prealign_shared_build_query_profile(query,5,4,profile,segLen);
  PreAlignCudaQueryHandle handle;
  std::string error;
  if(!prealign_cuda_prepare_query(&handle,profile.data(),5,segLen,
                                  static_cast<int>(query.size()),&error))
  {
    std::cerr << "prepare failed: " << error << "\n";
    return false;
  }

  std::vector<int> authority;
  std::vector<int> candidate;
  std::vector<uint8_t> replayFlags;
  PreAlignCudaBatchResult authorityColumn;
  PreAlignCudaBatchResult authorityReduce;
  PreAlignCudaBatchResult byteBatch;
  PreAlignCudaBatchResult replayBatch;
  const bool authorityOk = prealign_cuda_find_max_scores_global_state_batch(
    handle,targets.data(),taskCount,targetLength,false,&authority,
    &authorityColumn,&authorityReduce,&error);
  const bool candidateOk =
    prealign_cuda_find_max_scores_byte_global_state_replay_batch(
      handle,targets.data(),taskCount,targetLength,&candidate,&replayFlags,
      &byteBatch,&replayBatch,&error);
  prealign_cuda_release_query(&handle);
  if(!authorityOk || !candidateOk)
  {
    std::cerr << "score failed query=" << query.size() << ": " << error << "\n";
    return false;
  }
  if(authority != candidate || replayFlags.size() != authority.size())
  {
    for(size_t index = 0; index < authority.size() && index < candidate.size(); ++index)
    {
      if(authority[index] != candidate[index])
      {
        std::cerr << "mismatch query=" << query.size() << " task=" << index
                  << " authority=" << authority[index]
                  << " candidate=" << candidate[index]
                  << " replay=" << static_cast<int>(replayFlags[index]) << "\n";
        break;
      }
    }
    return false;
  }

  int replayCount = 0;
  for(size_t index = 0; index < replayFlags.size(); ++index)
  {
    replayCount += replayFlags[index] != 0 ? 1 : 0;
    const bool expectedReplay = authority[index] > 255;
    if((replayFlags[index] != 0) != expectedReplay)
    {
      std::cerr << "certificate mismatch query=" << query.size()
                << " task=" << index << " authority=" << authority[index]
                << " replay=" << static_cast<int>(replayFlags[index]) << "\n";
      return false;
    }
  }
  if(!byteBatch.usedCuda || (requireReplay && !replayBatch.usedCuda) ||
     (requireNoReplay && replayBatch.usedCuda) ||
     (requireReplay && replayCount == 0) ||
     (requireNoReplay && replayCount != 0))
  {
    std::cerr << "unexpected replay accounting query=" << query.size()
              << " count=" << replayCount << "\n";
    return false;
  }
  std::cout << "query=" << query.size()
            << " tasks=" << taskCount
            << " target=" << targetLength
            << " replay_tasks=" << replayCount
            << " authority_kernel_seconds="
            << authorityColumn.gpuSeconds + authorityReduce.gpuSeconds
            << " byte_kernel_seconds=" << byteBatch.gpuSeconds
            << " replay_kernel_seconds=" << replayBatch.gpuSeconds << "\n";
  return true;
}

} // namespace

int main()
{
  std::string error;
  if(!prealign_cuda_is_built() || !prealign_cuda_init(0,&error))
  {
    std::cerr << "CUDA prealign unavailable: " << error << "\n";
    return 1;
  }

  const int queryLengths[] = {1,31,32,33,511,2812,4006,8181,12397};
  bool ok = true;
  for(size_t index = 0; index < sizeof(queryLengths) / sizeof(queryLengths[0]); ++index)
  {
    const int queryLength = queryLengths[index];
    ok = compare_case(make_query(queryLength),make_targets(7,193),
                      7,193,false,queryLength <= 33) && ok;
  }

  const std::string overflowQuery(511,'A');
  std::vector<uint8_t> overflowTargets = make_targets(3,193);
  for(int column = 0; column < 193; ++column)
  {
    overflowTargets[static_cast<size_t>(column)] = 0;
  }
  ok = compare_case(overflowQuery,overflowTargets,3,193,true,false) && ok;
  return ok ? 0 : 1;
}
