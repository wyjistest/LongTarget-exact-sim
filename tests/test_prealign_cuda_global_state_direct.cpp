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
  uint32_t state = 0x12345678u + static_cast<uint32_t>(length);
  for(int i = 0; i < length; ++i)
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
  uint32_t state = 0x9e3779b9u;
  for(int task = 0; task < taskCount; ++task)
  {
    for(int column = 0; column < targetLength; ++column)
    {
      state = state * 1103515245u + 12345u;
      uint8_t code = static_cast<uint8_t>((state >> 27) % 5u);
      if(task == 0 && column < targetLength / 2) code = 0;
      if(task == 1 && column % 7 == 0) code = 4;
      targets[static_cast<size_t>(task) * static_cast<size_t>(targetLength) +
              static_cast<size_t>(column)] = code;
    }
  }
  return targets;
}

bool check_case(int queryLength,int taskCount,int targetLength)
{
  const std::string query = make_query(queryLength);
  std::vector<int16_t> profile;
  int segLen = 0;
  prealign_shared_build_query_profile(query,5,4,profile,segLen);
  PreAlignCudaQueryHandle handle;
  std::string error;
  if(!prealign_cuda_prepare_query(&handle,profile.data(),5,segLen,
                                  queryLength,&error))
  {
    std::cerr << "prepare failed query=" << queryLength << ": " << error << "\n";
    return false;
  }

  const std::vector<uint8_t> targets = make_targets(taskCount,targetLength);
  std::vector<int> authority;
  std::vector<int> direct;
  PreAlignCudaBatchResult columnBatch;
  PreAlignCudaBatchResult reduceBatch;
  PreAlignCudaBatchResult directBatch;
  const bool authorityOk = prealign_cuda_find_max_scores_global_state_batch(
    handle,targets.data(),taskCount,targetLength,false,&authority,
    &columnBatch,&reduceBatch,&error);
  const bool directOk = prealign_cuda_find_max_scores_global_state_direct_batch(
    handle,targets.data(),taskCount,targetLength,&direct,&directBatch,&error);
  prealign_cuda_release_query(&handle);
  if(!authorityOk || !directOk)
  {
    std::cerr << "score failed query=" << queryLength << ": " << error << "\n";
    return false;
  }
  if(!columnBatch.usedCuda || !reduceBatch.usedCuda || !directBatch.usedCuda)
  {
    std::cerr << "CUDA authority flag missing query=" << queryLength << "\n";
    return false;
  }
  if(authority != direct)
  {
    for(size_t index = 0; index < authority.size() && index < direct.size(); ++index)
    {
      if(authority[index] != direct[index])
      {
        std::cerr << "mismatch query=" << queryLength << " task=" << index
                  << " authority=" << authority[index]
                  << " direct=" << direct[index] << "\n";
        break;
      }
    }
    return false;
  }
  std::cout << "query=" << queryLength
            << " tasks=" << taskCount
            << " target=" << targetLength
            << " authority_kernel_seconds="
            << columnBatch.gpuSeconds + reduceBatch.gpuSeconds
            << " direct_kernel_seconds=" << directBatch.gpuSeconds << "\n";
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
    ok = check_case(queryLengths[index],4,193) && ok;
  }
  return ok ? 0 : 1;
}
