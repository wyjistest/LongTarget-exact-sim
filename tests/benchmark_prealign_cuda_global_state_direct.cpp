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
  double kernelSeconds;
};

std::string make_query(int length)
{
  static const char alphabet[] = "ACGT";
  std::string query;
  query.reserve(static_cast<size_t>(length));
  uint32_t state = 0x243f6a88u + static_cast<uint32_t>(length);
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
  uint32_t state = 0x13198a2eu;
  for(size_t index = 0; index < targets.size(); ++index)
  {
    state = state * 1103515245u + 12345u;
    targets[index] = static_cast<uint8_t>((state >> 27) % 5u);
  }
  return targets;
}

double median(std::vector<double> values)
{
  std::sort(values.begin(),values.end());
  const size_t middle = values.size() / 2;
  if(values.size() % 2 != 0) return values[middle];
  return (values[middle - 1] + values[middle]) / 2.0;
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
    handle,targets.data(),taskCount,targetLength,false,scores,&column,&reduce,error);
  sample->wallSeconds = std::chrono::duration<double>(
    std::chrono::steady_clock::now() - start).count();
  sample->kernelSeconds = column.gpuSeconds + reduce.gpuSeconds;
  return ok;
}

bool run_direct(const PreAlignCudaQueryHandle &handle,
                const std::vector<uint8_t> &targets,
                int taskCount,
                int targetLength,
                std::vector<int> *scores,
                Sample *sample,
                std::string *error)
{
  PreAlignCudaBatchResult batch;
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  const bool ok = prealign_cuda_find_max_scores_global_state_direct_batch(
    handle,targets.data(),taskCount,targetLength,scores,&batch,error);
  sample->wallSeconds = std::chrono::duration<double>(
    std::chrono::steady_clock::now() - start).count();
  sample->kernelSeconds = batch.gpuSeconds;
  return ok;
}

} // namespace

int main(int argc,char **argv)
{
  if(argc != 5)
  {
    std::cerr << "usage: " << argv[0]
              << " QUERY_LENGTH TASK_COUNT TARGET_LENGTH REPEATS\n";
    return 2;
  }
  const int queryLength = std::atoi(argv[1]);
  const int taskCount = std::atoi(argv[2]);
  const int targetLength = std::atoi(argv[3]);
  const int repeats = std::atoi(argv[4]);
  if(queryLength <= 0 || taskCount <= 0 || targetLength <= 0 || repeats < 3)
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
  std::vector<int16_t> profile;
  int segLen = 0;
  prealign_shared_build_query_profile(query,5,4,profile,segLen);
  PreAlignCudaQueryHandle handle;
  if(!prealign_cuda_prepare_query(&handle,profile.data(),5,segLen,queryLength,&error))
  {
    std::cerr << "query preparation failed: " << error << "\n";
    return 1;
  }
  const std::vector<uint8_t> targets = make_targets(taskCount,targetLength);
  std::vector<int> authority;
  std::vector<int> direct;
  Sample warmup;
  if(!run_authority(handle,targets,taskCount,targetLength,&authority,&warmup,&error) ||
     !run_direct(handle,targets,taskCount,targetLength,&direct,&warmup,&error) ||
     authority != direct)
  {
    prealign_cuda_release_query(&handle);
    std::cerr << "warmup or exactness failed: " << error << "\n";
    return 1;
  }

  std::vector<double> authorityWalls;
  std::vector<double> authorityKernels;
  std::vector<double> directWalls;
  std::vector<double> directKernels;
  for(int repeat = 0; repeat < repeats; ++repeat)
  {
    Sample authoritySample;
    Sample directSample;
    bool ok = false;
    if(repeat % 2 == 0)
    {
      ok = run_authority(handle,targets,taskCount,targetLength,&authority,
                         &authoritySample,&error) &&
           run_direct(handle,targets,taskCount,targetLength,&direct,
                      &directSample,&error);
    }
    else
    {
      ok = run_direct(handle,targets,taskCount,targetLength,&direct,
                      &directSample,&error) &&
           run_authority(handle,targets,taskCount,targetLength,&authority,
                         &authoritySample,&error);
    }
    if(!ok || authority != direct)
    {
      prealign_cuda_release_query(&handle);
      std::cerr << "repeat failed: " << error << "\n";
      return 1;
    }
    authorityWalls.push_back(authoritySample.wallSeconds);
    authorityKernels.push_back(authoritySample.kernelSeconds);
    directWalls.push_back(directSample.wallSeconds);
    directKernels.push_back(directSample.kernelSeconds);
  }
  prealign_cuda_release_query(&handle);

  const double authorityWall = median(authorityWalls);
  const double directWall = median(directWalls);
  const double authorityKernel = median(authorityKernels);
  const double directKernel = median(directKernels);
  std::cout << std::setprecision(12)
            << "{\"schema_version\":\"prealign_cuda_global_state_direct_benchmark_v1\""
            << ",\"query_length\":" << queryLength
            << ",\"task_count\":" << taskCount
            << ",\"target_length\":" << targetLength
            << ",\"repeats\":" << repeats
            << ",\"authority_wall_median_seconds\":" << authorityWall
            << ",\"direct_wall_median_seconds\":" << directWall
            << ",\"wall_ratio\":" << directWall / authorityWall
            << ",\"authority_kernel_median_seconds\":" << authorityKernel
            << ",\"direct_kernel_median_seconds\":" << directKernel
            << ",\"kernel_ratio\":" << directKernel / authorityKernel
            << ",\"scores_exact\":true}\n";
  return 0;
}
