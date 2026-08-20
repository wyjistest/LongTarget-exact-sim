#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace
{

struct Sample
{
  double wallSeconds;
  double byteKernelSeconds;
  double replayKernelSeconds;
  int replayTasks;
};

std::string make_query(int length)
{
  static const char alphabet[] = "ACGT";
  std::string query;
  query.reserve(static_cast<size_t>(length));
  uint32_t state = 0x3c6ef372u + static_cast<uint32_t>(length);
  for(int index = 0; index < length; ++index)
  {
    state = state * 1664525u + 1013904223u;
    query.push_back(alphabet[(state >> 29) & 3u]);
  }
  return query;
}

std::vector<uint8_t> make_targets(const std::string &query,
                                  int taskCount,
                                  int targetLength,
                                  int requestedReplayTasks)
{
  std::vector<uint8_t> targets(
    static_cast<size_t>(taskCount) * static_cast<size_t>(targetLength));
  uint32_t state = 0xa54ff53au;
  for(int task = 0; task < taskCount; ++task)
  {
    for(int column = 0; column < targetLength; ++column)
    {
      uint8_t code = 0;
      if(task < requestedReplayTasks)
      {
        code = prealign_shared_encode_base(
          static_cast<unsigned char>(query[static_cast<size_t>(column) % query.size()]));
      }
      else
      {
        state = state * 1103515245u + 12345u;
        code = static_cast<uint8_t>((state >> 27) % 5u);
      }
      targets[static_cast<size_t>(task) * static_cast<size_t>(targetLength) +
              static_cast<size_t>(column)] = code;
    }
  }
  return targets;
}

double median(std::vector<double> values)
{
  std::sort(values.begin(),values.end());
  const size_t middle = values.size() / 2;
  return values.size() % 2 != 0 ? values[middle] :
    (values[middle - 1] + values[middle]) / 2.0;
}

bool run_authority(const PreAlignCudaQueryHandle &handle,
                   const std::vector<uint8_t> &targets,
                   int taskCount,
                   int targetLength,
                   std::vector<int> *scores,
                   Sample *sample,
                   std::string *error)
{
  PreAlignCudaBatchResult column;
  PreAlignCudaBatchResult reduce;
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  const bool ok = prealign_cuda_find_max_scores_global_state_batch(
    handle,targets.data(),taskCount,targetLength,false,scores,
    &column,&reduce,error);
  sample->wallSeconds = std::chrono::duration<double>(
    std::chrono::steady_clock::now() - start).count();
  sample->byteKernelSeconds = column.gpuSeconds + reduce.gpuSeconds;
  sample->replayKernelSeconds = 0.0;
  sample->replayTasks = 0;
  return ok;
}

bool run_candidate(const PreAlignCudaQueryHandle &handle,
                   const std::vector<uint8_t> &targets,
                   int taskCount,
                   int targetLength,
                   std::vector<int> *scores,
                   Sample *sample,
                   std::string *error)
{
  std::vector<uint8_t> flags;
  PreAlignCudaBatchResult byteBatch;
  PreAlignCudaBatchResult replayBatch;
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  const bool ok = prealign_cuda_find_max_scores_byte_global_state_replay_batch(
    handle,targets.data(),taskCount,targetLength,scores,&flags,
    &byteBatch,&replayBatch,error);
  sample->wallSeconds = std::chrono::duration<double>(
    std::chrono::steady_clock::now() - start).count();
  sample->byteKernelSeconds = byteBatch.gpuSeconds;
  sample->replayKernelSeconds = replayBatch.gpuSeconds;
  sample->replayTasks = static_cast<int>(
    std::count(flags.begin(),flags.end(),static_cast<uint8_t>(1)));
  return ok;
}

} // namespace

int main(int argc,char **argv)
{
  if(argc != 6)
  {
    std::cerr << "usage: " << argv[0]
              << " QUERY_LENGTH TASK_COUNT TARGET_LENGTH REPEATS REPLAY_TASKS\n";
    return 2;
  }
  const int queryLength = std::atoi(argv[1]);
  const int taskCount = std::atoi(argv[2]);
  const int targetLength = std::atoi(argv[3]);
  const int repeats = std::atoi(argv[4]);
  const int requestedReplayTasks = std::atoi(argv[5]);
  if(queryLength <= 0 || taskCount <= 0 || targetLength <= 0 || repeats < 3 ||
     requestedReplayTasks < 0 || requestedReplayTasks > taskCount)
  {
    std::cerr << "invalid benchmark dimensions\n";
    return 2;
  }

  std::string error;
  if(!prealign_cuda_is_built() || !prealign_cuda_init(0,&error))
  {
    std::cerr << "CUDA prealign unavailable: " << error << "\n";
    return 1;
  }
  const std::string query = make_query(queryLength);
  const std::vector<uint8_t> targets = make_targets(
    query,taskCount,targetLength,requestedReplayTasks);
  std::vector<int16_t> profile;
  int segLen = 0;
  prealign_shared_build_query_profile(query,5,4,profile,segLen);
  PreAlignCudaQueryHandle handle;
  if(!prealign_cuda_prepare_query(
       &handle,profile.data(),5,segLen,queryLength,&error))
  {
    std::cerr << "query preparation failed: " << error << "\n";
    return 1;
  }

  std::vector<int> authority;
  std::vector<int> candidate;
  Sample warmupAuthority;
  Sample warmupCandidate;
  if(!run_authority(handle,targets,taskCount,targetLength,&authority,
                    &warmupAuthority,&error) ||
     !run_candidate(handle,targets,taskCount,targetLength,&candidate,
                    &warmupCandidate,&error) ||
     authority != candidate)
  {
    prealign_cuda_release_query(&handle);
    std::cerr << "warmup or exactness failed: " << error << "\n";
    return 1;
  }

  std::vector<double> authorityWalls;
  std::vector<double> authorityKernels;
  std::vector<double> candidateWalls;
  std::vector<double> byteKernels;
  std::vector<double> replayKernels;
  int observedReplayTasks = warmupCandidate.replayTasks;
  for(int repeat = 0; repeat < repeats; ++repeat)
  {
    Sample authoritySample;
    Sample candidateSample;
    bool ok = false;
    if(repeat % 2 == 0)
    {
      ok = run_authority(handle,targets,taskCount,targetLength,&authority,
                         &authoritySample,&error) &&
           run_candidate(handle,targets,taskCount,targetLength,&candidate,
                         &candidateSample,&error);
    }
    else
    {
      ok = run_candidate(handle,targets,taskCount,targetLength,&candidate,
                         &candidateSample,&error) &&
           run_authority(handle,targets,taskCount,targetLength,&authority,
                         &authoritySample,&error);
    }
    if(!ok || authority != candidate ||
       candidateSample.replayTasks != observedReplayTasks)
    {
      prealign_cuda_release_query(&handle);
      std::cerr << "repeat failed: " << error << "\n";
      return 1;
    }
    authorityWalls.push_back(authoritySample.wallSeconds);
    authorityKernels.push_back(authoritySample.byteKernelSeconds);
    candidateWalls.push_back(candidateSample.wallSeconds);
    byteKernels.push_back(candidateSample.byteKernelSeconds);
    replayKernels.push_back(candidateSample.replayKernelSeconds);
  }
  prealign_cuda_release_query(&handle);

  const double authorityWall = median(authorityWalls);
  const double candidateWall = median(candidateWalls);
  const double authorityKernel = median(authorityKernels);
  const double byteKernel = median(byteKernels);
  const double replayKernel = median(replayKernels);
  std::cout << std::setprecision(12)
            << "{\"schema_version\":\"prealign_cuda_byte_global_state_replay_benchmark_v1\""
            << ",\"query_length\":" << queryLength
            << ",\"task_count\":" << taskCount
            << ",\"target_length\":" << targetLength
            << ",\"repeats\":" << repeats
            << ",\"requested_replay_tasks\":" << requestedReplayTasks
            << ",\"observed_replay_tasks\":" << observedReplayTasks
            << ",\"authority_wall_median_seconds\":" << authorityWall
            << ",\"candidate_wall_median_seconds\":" << candidateWall
            << ",\"wall_ratio\":" << candidateWall / authorityWall
            << ",\"authority_kernel_median_seconds\":" << authorityKernel
            << ",\"byte_kernel_median_seconds\":" << byteKernel
            << ",\"word_replay_kernel_median_seconds\":" << replayKernel
            << ",\"combined_kernel_ratio\":"
            << (byteKernel + replayKernel) / authorityKernel
            << ",\"scores_exact\":true}\n";
  return 0;
}
