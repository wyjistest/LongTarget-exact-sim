#include "accelign_shadow.h"

#include <accelign/one_to_all_aligner.cuh>
#include <accelign/one_to_one_aligner.cuh>
#include <accelign/sequence_converter.cuh>

#include <cuda_runtime.h>
#include <thrust/device_vector.h>
#include <thrust/host_vector.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <exception>
#include <memory>
#include <vector>

namespace
{

using AlignmentType = accelign::AlignmentType;
using PenaltyType = accelign::PenaltyType;

#ifndef FASIM_ACCELIGN_CUDA_ARCH
#define FASIM_ACCELIGN_CUDA_ARCH 890
#endif

constexpr int kAccelignCudaArch = FASIM_ACCELIGN_CUDA_ARCH;
constexpr int kAlphabetSize = 5;
constexpr AlignmentType kAlignmentType = AlignmentType::LocalAlignment;
constexpr PenaltyType kPenaltyType = PenaltyType::Affine;

using GpuAlignerFloat = accelign::GpuOneToOneStartEndPosAligner<
  kAccelignCudaArch,
  kAlphabetSize,
  float,
  kPenaltyType,
  kAlignmentType>;
using GpuScoreOnlyAlignerFloat = accelign::GpuOneToOneAligner<
  kAccelignCudaArch,
  kAlphabetSize,
  float,
  kPenaltyType,
  kAlignmentType>;
using GpuOneToAllScoreOnlyAlignerFloat = accelign::GpuOneToAllAligner<
  kAccelignCudaArch,
  kAlphabetSize,
  float,
  kPenaltyType,
  kAlignmentType>;

static uint64_t now_nanoseconds()
{
  return static_cast<uint64_t>(
    std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count());
}

static int8_t encode_base(unsigned char c)
{
  switch (c)
  {
  case 'A':
  case 'a':
    return 0;
  case 'C':
  case 'c':
    return 1;
  case 'G':
  case 'g':
    return 2;
  case 'T':
  case 't':
    return 3;
  default:
    return 4;
  }
}

static void set_error(std::string *errorOut, const std::string &message)
{
  if (errorOut != NULL)
  {
    *errorOut = message;
  }
}

static void set_cuda_error(std::string *errorOut, const char *context, cudaError_t error)
{
  if (errorOut != NULL)
  {
    *errorOut = std::string(context) + ": " + cudaGetErrorString(error);
  }
}

static bool cuda_ok(cudaError_t error, const char *context, std::string *errorOut)
{
  if (error == cudaSuccess)
  {
    return true;
  }
  set_cuda_error(errorOut, context, error);
  return false;
}

}  // namespace

bool accelign_shadow_is_built()
{
  return true;
}

bool accelign_shadow_init(int device, std::string *errorOut)
{
  if (!cuda_ok(cudaSetDevice(device), "cudaSetDevice", errorOut))
  {
    return false;
  }
  if (!cuda_ok(cudaFree(0), "cudaFree(0)", errorOut))
  {
    return false;
  }
  return true;
}

bool accelign_shadow_run_local_affine_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  if (outResults != NULL)
  {
    outResults->clear();
  }
  if (batchResult != NULL)
  {
    *batchResult = AccelignShadowBatchResult();
  }
  if (requests.empty())
  {
    return true;
  }
  if (outResults == NULL)
  {
    set_error(errorOut, "missing output result vector");
    return false;
  }

  try
  {
    cudaStream_t stream = 0;
    std::vector<int8_t> hSubjects;
    std::vector<int8_t> hQueries;
    std::vector<size_t> hSubjectOffsets;
    std::vector<size_t> hQueryOffsets;
    std::vector<int> hSubjectLengths;
    std::vector<int> hQueryLengths;

    hSubjectOffsets.reserve(requests.size());
    hQueryOffsets.reserve(requests.size());
    hSubjectLengths.reserve(requests.size());
    hQueryLengths.reserve(requests.size());

    int maximumSubjectLength = 0;
    int maximumQueryLength = 0;
    for (size_t i = 0; i < requests.size(); ++i)
    {
      const AccelignShadowRequest &request = requests[i];
      if (request.targetSequence.empty() || request.querySequence.empty())
      {
        set_error(errorOut, "Accelign shadow does not support empty sequences");
        return false;
      }
      hSubjectOffsets.push_back(hSubjects.size());
      hQueryOffsets.push_back(hQueries.size());
      hSubjectLengths.push_back(static_cast<int>(request.targetSequence.size()));
      hQueryLengths.push_back(static_cast<int>(request.querySequence.size()));
      maximumSubjectLength = std::max(maximumSubjectLength,
                                      static_cast<int>(request.targetSequence.size()));
      maximumQueryLength = std::max(maximumQueryLength,
                                    static_cast<int>(request.querySequence.size()));
      for (size_t j = 0; j < request.targetSequence.size(); ++j)
      {
        hSubjects.push_back(encode_base(
          static_cast<unsigned char>(request.targetSequence[j])));
      }
      for (size_t j = 0; j < request.querySequence.size(); ++j)
      {
        hQueries.push_back(encode_base(
          static_cast<unsigned char>(request.querySequence[j])));
      }
    }

    uint64_t h2dBytes = 0;
    h2dBytes += static_cast<uint64_t>(hSubjects.size()) * sizeof(int8_t);
    h2dBytes += static_cast<uint64_t>(hQueries.size()) * sizeof(int8_t);
    h2dBytes += static_cast<uint64_t>(hSubjectOffsets.size()) * sizeof(size_t);
    h2dBytes += static_cast<uint64_t>(hQueryOffsets.size()) * sizeof(size_t);
    h2dBytes += static_cast<uint64_t>(hSubjectLengths.size()) * sizeof(int);
    h2dBytes += static_cast<uint64_t>(hQueryLengths.size()) * sizeof(int);

    thrust::device_vector<int8_t> dSubjects = hSubjects;
    thrust::device_vector<int8_t> dQueries = hQueries;
    thrust::device_vector<size_t> dSubjectOffsets = hSubjectOffsets;
    thrust::device_vector<size_t> dQueryOffsets = hQueryOffsets;
    thrust::device_vector<int> dSubjectLengths = hSubjectLengths;
    thrust::device_vector<int> dQueryLengths = hQueryLengths;

    accelign::OneToOneSubstmatInterfaceInputData inputData;
    inputData.d_subjects = dSubjects.data().get();
    inputData.d_subjectOffsets = dSubjectOffsets.data().get();
    inputData.d_subjectLengths = dSubjectLengths.data().get();
    inputData.d_queries = dQueries.data().get();
    inputData.d_queryOffsets = dQueryOffsets.data().get();
    inputData.d_queryLengths = dQueryLengths.data().get();
    inputData.numAlignments = static_cast<int>(requests.size());
    inputData.maximumSubjectLength = maximumSubjectLength;
    inputData.maximumQueryLength = maximumQueryLength;

    int substitutionMatrix[kAlphabetSize * kAlphabetSize];
    for (int r = 0; r < kAlphabetSize; ++r)
    {
      for (int c = 0; c < kAlphabetSize; ++c)
      {
        substitutionMatrix[r * kAlphabetSize + c] =
          (r < 4 && c < 4 && r == c) ? 5 : -4;
      }
    }

    accelign::InterfaceGapScores gapInfo;
    gapInfo.gapscore = -4;
    gapInfo.gapopenscore = -16;
    gapInfo.gapextendscore = -4;

    GpuAlignerFloat gpuAligner;
    gpuAligner.setSubstitutionMatrix(substitutionMatrix, stream);

    thrust::device_vector<int> dScoreOutput(requests.size());
    thrust::device_vector<int> dQueryEndPositions(requests.size());
    thrust::device_vector<int> dSubjectEndPositions(requests.size());

    const uint64_t kernelStart = now_nanoseconds();
    if (gpuAligner.isSingleTile(inputData))
    {
      gpuAligner.executeAlignmentSingleTile(
        dScoreOutput.data().get(),
        dQueryEndPositions.data().get(),
        dSubjectEndPositions.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    else
    {
      const size_t minTempBytes =
        gpuAligner.getMinimumSuggestedTempBytes_multiTile(inputData);
      thrust::device_vector<char> dTemp(minTempBytes);
      gpuAligner.executeAlignmentMultiTile(
        dTemp.data().get(),
        dTemp.size(),
        dScoreOutput.data().get(),
        dQueryEndPositions.data().get(),
        dSubjectEndPositions.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    if (!cuda_ok(cudaStreamSynchronize(stream), "cudaStreamSynchronize", errorOut))
    {
      return false;
    }
    const uint64_t kernelElapsed = now_nanoseconds() - kernelStart;

    thrust::host_vector<int> hScoreOutput = dScoreOutput;
    thrust::host_vector<int> hQueryEndPositions = dQueryEndPositions;
    thrust::host_vector<int> hSubjectEndPositions = dSubjectEndPositions;

    outResults->resize(requests.size());
    for (size_t i = 0; i < requests.size(); ++i)
    {
      AccelignShadowResult result;
      result.score = hScoreOutput[i];
      result.queryEnd = hQueryEndPositions[i] - 1;
      result.refEnd = hSubjectEndPositions[i] - 1;
      (*outResults)[i] = result;
    }

    if (batchResult != NULL)
    {
      batchResult->gpuSeconds =
        static_cast<double>(kernelElapsed) / 1000000000.0;
      batchResult->h2dBytes = h2dBytes;
      batchResult->d2hBytes =
        static_cast<uint64_t>(requests.size()) *
        static_cast<uint64_t>(3 * sizeof(int));
      batchResult->queryStagingBytes =
        static_cast<uint64_t>(hQueries.size()) * sizeof(int8_t);
      batchResult->targetStagingBytes =
        static_cast<uint64_t>(hSubjects.size()) * sizeof(int8_t);
      batchResult->queryReuseActive = false;
      batchResult->usedCuda = true;
    }
    return true;
  }
  catch (const std::exception &ex)
  {
    set_error(errorOut, ex.what());
    return false;
  }
}

bool accelign_shadow_run_local_affine_score_only_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  if (outResults != NULL)
  {
    outResults->clear();
  }
  if (batchResult != NULL)
  {
    *batchResult = AccelignShadowBatchResult();
  }
  if (requests.empty())
  {
    return true;
  }
  if (outResults == NULL)
  {
    set_error(errorOut, "missing output result vector");
    return false;
  }

  try
  {
    cudaStream_t stream = 0;
    std::vector<int8_t> hSubjects;
    std::vector<int8_t> hQueries;
    std::vector<size_t> hSubjectOffsets;
    std::vector<size_t> hQueryOffsets;
    std::vector<int> hSubjectLengths;
    std::vector<int> hQueryLengths;

    hSubjectOffsets.reserve(requests.size());
    hQueryOffsets.reserve(requests.size());
    hSubjectLengths.reserve(requests.size());
    hQueryLengths.reserve(requests.size());

    int maximumSubjectLength = 0;
    int maximumQueryLength = 0;
    for (size_t i = 0; i < requests.size(); ++i)
    {
      const AccelignShadowRequest &request = requests[i];
      if (request.targetSequence.empty() || request.querySequence.empty())
      {
        set_error(errorOut, "Accelign score-only shadow does not support empty sequences");
        return false;
      }
      hSubjectOffsets.push_back(hSubjects.size());
      hQueryOffsets.push_back(hQueries.size());
      hSubjectLengths.push_back(static_cast<int>(request.targetSequence.size()));
      hQueryLengths.push_back(static_cast<int>(request.querySequence.size()));
      maximumSubjectLength = std::max(maximumSubjectLength,
                                      static_cast<int>(request.targetSequence.size()));
      maximumQueryLength = std::max(maximumQueryLength,
                                    static_cast<int>(request.querySequence.size()));
      for (size_t j = 0; j < request.targetSequence.size(); ++j)
      {
        hSubjects.push_back(encode_base(
          static_cast<unsigned char>(request.targetSequence[j])));
      }
      for (size_t j = 0; j < request.querySequence.size(); ++j)
      {
        hQueries.push_back(encode_base(
          static_cast<unsigned char>(request.querySequence[j])));
      }
    }

    const uint64_t queryStagingBytes =
      static_cast<uint64_t>(hQueries.size()) * sizeof(int8_t);
    const uint64_t targetStagingBytes =
      static_cast<uint64_t>(hSubjects.size()) * sizeof(int8_t);
    uint64_t h2dBytes = 0;
    h2dBytes += targetStagingBytes;
    h2dBytes += queryStagingBytes;
    h2dBytes += static_cast<uint64_t>(hSubjectOffsets.size()) * sizeof(size_t);
    h2dBytes += static_cast<uint64_t>(hQueryOffsets.size()) * sizeof(size_t);
    h2dBytes += static_cast<uint64_t>(hSubjectLengths.size()) * sizeof(int);
    h2dBytes += static_cast<uint64_t>(hQueryLengths.size()) * sizeof(int);

    thrust::device_vector<int8_t> dSubjects = hSubjects;
    thrust::device_vector<int8_t> dQueries = hQueries;
    thrust::device_vector<size_t> dSubjectOffsets = hSubjectOffsets;
    thrust::device_vector<size_t> dQueryOffsets = hQueryOffsets;
    thrust::device_vector<int> dSubjectLengths = hSubjectLengths;
    thrust::device_vector<int> dQueryLengths = hQueryLengths;

    accelign::OneToOneSubstmatInterfaceInputData inputData;
    inputData.d_subjects = dSubjects.data().get();
    inputData.d_subjectOffsets = dSubjectOffsets.data().get();
    inputData.d_subjectLengths = dSubjectLengths.data().get();
    inputData.d_queries = dQueries.data().get();
    inputData.d_queryOffsets = dQueryOffsets.data().get();
    inputData.d_queryLengths = dQueryLengths.data().get();
    inputData.numAlignments = static_cast<int>(requests.size());
    inputData.maximumSubjectLength = maximumSubjectLength;
    inputData.maximumQueryLength = maximumQueryLength;

    int substitutionMatrix[kAlphabetSize * kAlphabetSize];
    for (int r = 0; r < kAlphabetSize; ++r)
    {
      for (int c = 0; c < kAlphabetSize; ++c)
      {
        substitutionMatrix[r * kAlphabetSize + c] =
          (r < 4 && c < 4 && r == c) ? 5 : -4;
      }
    }

    accelign::InterfaceGapScores gapInfo;
    gapInfo.gapscore = -4;
    gapInfo.gapopenscore = -16;
    gapInfo.gapextendscore = -4;

    GpuScoreOnlyAlignerFloat gpuAligner;
    gpuAligner.setSubstitutionMatrix(substitutionMatrix, stream);

    thrust::device_vector<int> dScoreOutput(requests.size());

    const uint64_t kernelStart = now_nanoseconds();
    if (gpuAligner.isSingleTile(inputData))
    {
      gpuAligner.executeAlignmentSingleTile(
        dScoreOutput.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    else
    {
      const size_t minTempBytes =
        gpuAligner.getMinimumSuggestedTempBytes_multiTile(inputData);
      thrust::device_vector<char> dTemp(minTempBytes);
      gpuAligner.executeAlignmentMultiTile(
        dTemp.data().get(),
        dTemp.size(),
        dScoreOutput.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    if (!cuda_ok(cudaStreamSynchronize(stream), "cudaStreamSynchronize", errorOut))
    {
      return false;
    }
    const uint64_t kernelElapsed = now_nanoseconds() - kernelStart;

    thrust::host_vector<int> hScoreOutput = dScoreOutput;

    outResults->resize(requests.size());
    for (size_t i = 0; i < requests.size(); ++i)
    {
      AccelignShadowResult result;
      result.score = hScoreOutput[i];
      (*outResults)[i] = result;
    }

    if (batchResult != NULL)
    {
      batchResult->gpuSeconds =
        static_cast<double>(kernelElapsed) / 1000000000.0;
      batchResult->h2dBytes = h2dBytes;
      batchResult->d2hBytes =
        static_cast<uint64_t>(requests.size()) * sizeof(int);
      batchResult->queryStagingBytes = queryStagingBytes;
      batchResult->targetStagingBytes = targetStagingBytes;
      batchResult->queryReuseActive = false;
      batchResult->usedCuda = true;
    }
    return true;
  }
  catch (const std::exception &ex)
  {
    set_error(errorOut, ex.what());
    return false;
  }
}

bool accelign_shadow_run_local_affine_score_only_one_to_all_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  if (outResults != NULL)
  {
    outResults->clear();
  }
  if (batchResult != NULL)
  {
    *batchResult = AccelignShadowBatchResult();
  }
  if (requests.empty())
  {
    return true;
  }
  if (outResults == NULL)
  {
    set_error(errorOut, "missing output result vector");
    return false;
  }

  const std::string &query = requests.front().querySequence;
  if (query.empty())
  {
    set_error(errorOut, "Accelign one-to-all score-only shadow does not support empty query");
    return false;
  }
  for (size_t i = 0; i < requests.size(); ++i)
  {
    if (requests[i].querySequence != query)
    {
      set_error(errorOut, "Accelign one-to-all score-only shadow requires one query");
      return false;
    }
    if (requests[i].targetSequence.empty())
    {
      set_error(errorOut, "Accelign one-to-all score-only shadow does not support empty targets");
      return false;
    }
  }

  try
  {
    cudaStream_t stream = 0;
    std::vector<int8_t> hQuery;
    std::vector<int8_t> hSubjects;
    std::vector<size_t> hSubjectOffsets;
    std::vector<int> hSubjectLengths;

    hQuery.reserve(query.size());
    for (size_t i = 0; i < query.size(); ++i)
    {
      hQuery.push_back(encode_base(static_cast<unsigned char>(query[i])));
    }
    hSubjectOffsets.reserve(requests.size());
    hSubjectLengths.reserve(requests.size());

    int maximumSubjectLength = 0;
    for (size_t i = 0; i < requests.size(); ++i)
    {
      const AccelignShadowRequest &request = requests[i];
      hSubjectOffsets.push_back(hSubjects.size());
      hSubjectLengths.push_back(static_cast<int>(request.targetSequence.size()));
      maximumSubjectLength = std::max(maximumSubjectLength,
                                      static_cast<int>(request.targetSequence.size()));
      for (size_t j = 0; j < request.targetSequence.size(); ++j)
      {
        hSubjects.push_back(encode_base(
          static_cast<unsigned char>(request.targetSequence[j])));
      }
    }

    const uint64_t queryStagingBytes =
      static_cast<uint64_t>(hQuery.size()) * sizeof(int8_t);
    const uint64_t targetStagingBytes =
      static_cast<uint64_t>(hSubjects.size()) * sizeof(int8_t);
    uint64_t h2dBytes = 0;
    h2dBytes += targetStagingBytes;
    h2dBytes += queryStagingBytes;
    h2dBytes += static_cast<uint64_t>(hSubjectOffsets.size()) * sizeof(size_t);
    h2dBytes += static_cast<uint64_t>(hSubjectLengths.size()) * sizeof(int);

    thrust::device_vector<int8_t> dSubjects = hSubjects;
    thrust::device_vector<size_t> dSubjectOffsets = hSubjectOffsets;
    thrust::device_vector<int> dSubjectLengths = hSubjectLengths;

    accelign::OneToAllPSSMInterfaceInputData inputData;
    inputData.d_subjects = dSubjects.data().get();
    inputData.d_subjectOffsets = dSubjectOffsets.data().get();
    inputData.d_subjectLengths = dSubjectLengths.data().get();
    inputData.numAlignments = static_cast<int>(requests.size());
    inputData.maximumSubjectLength = maximumSubjectLength;

    int substitutionMatrix[kAlphabetSize * kAlphabetSize];
    for (int r = 0; r < kAlphabetSize; ++r)
    {
      for (int c = 0; c < kAlphabetSize; ++c)
      {
        substitutionMatrix[r * kAlphabetSize + c] =
          (r < 4 && c < 4 && r == c) ? 5 : -4;
      }
    }

    accelign::InterfaceGapScores gapInfo;
    gapInfo.gapscore = -4;
    gapInfo.gapopenscore = -16;
    gapInfo.gapextendscore = -4;

    GpuOneToAllScoreOnlyAlignerFloat gpuAligner;
    gpuAligner.setQuery(hQuery.data(),
                        static_cast<int>(hQuery.size()),
                        substitutionMatrix,
                        stream);

    thrust::device_vector<int> dScoreOutput(requests.size());

    const uint64_t kernelStart = now_nanoseconds();
    if (gpuAligner.isSingleTile(inputData))
    {
      gpuAligner.executeAlignmentSingleTile(
        dScoreOutput.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    else
    {
      const size_t minTempBytes =
        gpuAligner.getMinimumSuggestedTempBytes_multiTile(inputData);
      thrust::device_vector<char> dTemp(minTempBytes);
      gpuAligner.executeAlignmentMultiTile(
        dTemp.data().get(),
        dTemp.size(),
        dScoreOutput.data().get(),
        inputData,
        gapInfo,
        stream);
    }
    if (!cuda_ok(cudaStreamSynchronize(stream), "cudaStreamSynchronize", errorOut))
    {
      return false;
    }
    const uint64_t kernelElapsed = now_nanoseconds() - kernelStart;

    thrust::host_vector<int> hScoreOutput = dScoreOutput;

    outResults->resize(requests.size());
    for (size_t i = 0; i < requests.size(); ++i)
    {
      AccelignShadowResult result;
      result.score = hScoreOutput[i];
      (*outResults)[i] = result;
    }

    if (batchResult != NULL)
    {
      batchResult->gpuSeconds =
        static_cast<double>(kernelElapsed) / 1000000000.0;
      batchResult->h2dBytes = h2dBytes;
      batchResult->d2hBytes =
        static_cast<uint64_t>(requests.size()) * sizeof(int);
      batchResult->queryStagingBytes = queryStagingBytes;
      batchResult->targetStagingBytes = targetStagingBytes;
      batchResult->queryReuseActive = true;
      batchResult->usedCuda = true;
    }
    return true;
  }
  catch (const std::exception &ex)
  {
    set_error(errorOut, ex.what());
    return false;
  }
}
