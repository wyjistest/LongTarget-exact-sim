#ifndef LONGTARGET_PREALIGN_SHARED_H
#define LONGTARGET_PREALIGN_SHARED_H

#include <cstdint>
#include <limits>
#include <string>
#include <vector>

#include "prealign_cuda.h"

static inline uint8_t prealign_shared_encode_base(unsigned char c)
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

static inline void prealign_shared_encode_sequence(const std::string &sequence,std::vector<uint8_t> &encoded)
{
  encoded.resize(sequence.size());
  for(size_t i = 0; i < sequence.size(); ++i)
  {
    encoded[i] = prealign_shared_encode_base(static_cast<unsigned char>(sequence[i]));
  }
}

static inline void prealign_shared_build_query_profile(const std::string &query,
                                                       int matchScore,
                                                       int mismatchPenalty,
                                                       std::vector<int16_t> &profile,
                                                       int &segLenOut)
{
  const int queryLength = static_cast<int>(query.size());
  const int segWidth = 32;
  const int segLen = (queryLength + segWidth - 1) / segWidth;
  segLenOut = segLen;

  profile.assign(static_cast<size_t>(5) * static_cast<size_t>(segLen) * static_cast<size_t>(segWidth), 0);

  for(int targetCode = 0; targetCode < 5; ++targetCode)
  {
    for(int lane = 0; lane < segWidth; ++lane)
    {
      for(int segIndex = 0; segIndex < segLen; ++segIndex)
      {
        const int queryIndex = lane * segLen + segIndex;
        int16_t score = 0;
        if(queryIndex < queryLength)
        {
          const uint8_t queryCode = prealign_shared_encode_base(static_cast<unsigned char>(query[static_cast<size_t>(queryIndex)]));
          if(queryCode < 4 && targetCode < 4 && static_cast<int>(queryCode) == targetCode)
          {
            score = static_cast<int16_t>(matchScore);
          }
          else
          {
            score = static_cast<int16_t>(-mismatchPenalty);
          }
        }

        profile[(static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) + static_cast<size_t>(segIndex)) *
                  static_cast<size_t>(segWidth) +
                static_cast<size_t>(lane)] = score;
      }
    }
  }
}

struct PrealignSharedQueryCache
{
  PrealignSharedQueryCache():
    cachedDevice(std::numeric_limits<int>::min()),
    cachedMatchScore(0),
    cachedMismatchPenalty(0),
    segLen(0)
  {
  }

  ~PrealignSharedQueryCache()
  {
    prealign_cuda_release_query(&handle);
  }

  bool prepare(int device,
               const std::string &query,
               int alphabetSize,
               int matchScore,
               int mismatchPenalty,
               std::string *errorOut)
  {
    if(cachedDevice == device &&
       cachedMatchScore == matchScore &&
       cachedMismatchPenalty == mismatchPenalty &&
       cachedQuery == query &&
       handle.profileDevice != 0)
    {
      return true;
    }

    prealign_cuda_release_query(&handle);
    cachedDevice = device;
    cachedMatchScore = matchScore;
    cachedMismatchPenalty = mismatchPenalty;
    cachedQuery.clear();

    prealign_shared_build_query_profile(query, matchScore, mismatchPenalty, profile, segLen);
    if(!prealign_cuda_prepare_query(&handle,
                                    profile.data(),
                                    alphabetSize,
                                    segLen,
                                    static_cast<int>(query.size()),
                                    errorOut))
    {
      prealign_cuda_release_query(&handle);
      return false;
    }

    cachedQuery = query;
    return true;
  }

  const PreAlignCudaQueryHandle &query_handle() const
  {
    return handle;
  }

  int cachedDevice;
  int cachedMatchScore;
  int cachedMismatchPenalty;
  std::string cachedQuery;
  PreAlignCudaQueryHandle handle;
  std::vector<int16_t> profile;
  int segLen;
};

#endif
