#include <iostream>
#include <string.h>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include <chrono>
#include <map>
#include "ssw_cpp.h"
#include "ssw.h"
#include "sim.h"
#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"
#include "../cuda/accelign_shadow.h"
#define N 50
using std::string;
using std::cout;
using std::endl;
using std::ifstream;

struct FasimFastSimExtendProfileStats
{
	FasimFastSimExtendProfileStats() :
		inclusiveNanoseconds(0),
		exclusiveNanoseconds(0),
		exactColumnNanoseconds(0),
		scoreInfoScanNanoseconds(0),
		candidateFilterNanoseconds(0),
		recordBuildNanoseconds(0),
		alignmentReconstructNanoseconds(0),
		cigarNanoseconds(0),
		vectorPushNanoseconds(0),
		allocationNanoseconds(0),
		outputStageNanoseconds(0),
		duplicateOverlapNanoseconds(0),
		stringFormatNanoseconds(0),
		alignerAlignNanoseconds(0),
		alignerAlignCpuInternalsEnabled(0),
		alignerAlignCalls(0),
		alignerAlignTotalCells(0),
		alignerAlignTotalQueryBases(0),
		alignerAlignTotalTargetBases(0),
		alignerAlignMaxQueryLen(0),
		alignerAlignMaxTargetLen(0),
		alignerAlignRecordsConsidered(0),
		alignerAlignRecordsEmitted(0),
		alignerAlignRecordsRejectedAfterAlign(0),
		alignerAlignScoreInfoExactScoreMatches(0),
		alignerAlignScoreInfoPositionMatches(0),
		alignerAlignRequiredForCigar(0),
		alignerAlignRequiredForScore(0),
		alignerAlignRequiredForCoordinates(0),
		alignerAlignBypassShadowEnabled(0),
		alignerAlignBypassShadowBypassableRecords(0),
		alignerAlignBypassShadowNonBypassableRecords(0),
		alignerAlignBypassShadowEstSavedNanoseconds(0),
		alignerAlignBypassShadowScoreMismatches(0),
		alignerAlignBypassShadowCoordinateMismatches(0),
		alignerAlignBypassShadowCigarMissingRecords(0),
		alignBatchShadowEnabled(0),
		alignBatchShadowSupported(0),
		alignBatchShadowDisabledReason(0),
		alignBatchShadowRequestsTotal(0),
		alignBatchShadowRequestsCompared(0),
		alignBatchShadowRequestsUnsupported(0),
		alignBatchShadowQueryBases(0),
		alignBatchShadowTargetBases(0),
		alignBatchShadowCells(0),
		alignBatchShadowH2DBytes(0),
		alignBatchShadowD2HBytes(0),
		alignBatchShadowKernelNanoseconds(0),
		alignBatchShadowTotalNanoseconds(0),
		alignBatchShadowCpuReferenceNanoseconds(0),
		alignBatchShadowScoreMismatches(0),
		alignBatchShadowCoordinateMismatches(0),
		alignBatchShadowCigarMismatches(0),
		alignBatchShadowAlignmentStringMismatches(0),
		alignBatchShadowTotalMismatches(0),
		alignBatchShadowFallbacks(0),
		alignBatchShadowHasScoreContract(0),
		alignBatchShadowHasCoordinateContract(0),
		alignBatchShadowHasCigarContract(0),
		alignBatchShadowHasAlignmentStringContract(0),
		accelignShadowEnabled(0),
		accelignShadowSupported(0),
		accelignShadowDisabledReason(0),
		accelignShadowRequestsTotal(0),
		accelignShadowRequestsCompared(0),
		accelignShadowRequestsUnsupported(0),
		accelignShadowQueryBases(0),
		accelignShadowTargetBases(0),
		accelignShadowCells(0),
		accelignShadowH2DBytes(0),
		accelignShadowD2HBytes(0),
		accelignShadowKernelNanoseconds(0),
		accelignShadowTotalNanoseconds(0),
		accelignShadowCpuReferenceNanoseconds(0),
		accelignShadowScoreMismatches(0),
		accelignShadowEndpointMismatches(0),
		accelignShadowTotalMismatches(0),
		accelignShadowFallbacks(0),
		accelignShadowHasScoreContract(0),
		accelignShadowHasEndpointContract(0),
		accelignShadowHasCigarContract(0),
		accelignShadowHasAlignmentStringContract(0),
		accelignShadowUsesRuntimeOutput(0),
		preAlignFilterShadowEnabled(0),
		preAlignFilterCandidates(0),
		preAlignFilterActualEmitted(0),
		preAlignFilterActualRejected(0),
		preAlignFilterPredictedReject(0),
		preAlignFilterTrueReject(0),
		preAlignFilterFalseReject(0),
		preAlignFilterFalseKeep(0),
		preAlignFilterEstAlignCallsSaved(0),
		preAlignFilterEstAlignCellsSaved(0),
		preAlignFilterEstSavedNanoseconds(0),
		preAlignFilterActualEmittedAlignCalls(0),
		preAlignFilterActualRejectedAlignCalls(0),
		preAlignFilterActualEmittedAlignCells(0),
		preAlignFilterActualRejectedAlignCells(0),
		preAlignRejectReasonScore(0),
		preAlignRejectReasonNt(0),
		preAlignRejectReasonLength(0),
		preAlignRejectReasonCoordinates(0),
		preAlignRejectReasonOverlap(0),
		preAlignRejectReasonCigar(0),
		preAlignRejectReasonUnknown(0),
		preAlignFeatureSweepEnabled(0),
		preAlignFeatureSweepRulesTested(0),
		preAlignFeatureSweepBestZeroFalseRejectRule(0),
		preAlignFeatureSweepBestPredictedReject(0),
		preAlignFeatureSweepBestTrueReject(0),
		preAlignFeatureSweepBestFalseReject(0),
		preAlignFeatureSweepBestFalseKeep(0),
		preAlignFeatureSweepBestEstCallsSaved(0),
		preAlignFeatureSweepBestEstCellsSaved(0),
		preAlignFeatureSweepBestEstSavedNanoseconds(0),
		preAlignFeatureEmittedScoreSum(0),
		preAlignFeatureRejectedScoreSum(0),
		preAlignFeatureEmittedRankSum(0),
		preAlignFeatureRejectedRankSum(0),
		preAlignFeatureEmittedTargetLenSum(0),
		preAlignFeatureRejectedTargetLenSum(0),
		preAlignFeatureEmittedAlignCallsSum(0),
		preAlignFeatureRejectedAlignCallsSum(0),
		calls(0),
		scoreInfoRecords(0),
		recordsConsidered(0),
		recordsEmitted(0),
		recordsRejected(0)
	{
	}

	uint64_t inclusiveNanoseconds;
	uint64_t exclusiveNanoseconds;
	uint64_t exactColumnNanoseconds;
	uint64_t scoreInfoScanNanoseconds;
	uint64_t candidateFilterNanoseconds;
	uint64_t recordBuildNanoseconds;
	uint64_t alignmentReconstructNanoseconds;
	uint64_t cigarNanoseconds;
	uint64_t vectorPushNanoseconds;
	uint64_t allocationNanoseconds;
	uint64_t outputStageNanoseconds;
	uint64_t duplicateOverlapNanoseconds;
	uint64_t stringFormatNanoseconds;
	uint64_t alignerAlignNanoseconds;
	uint64_t alignerAlignCpuInternalsEnabled;
	StripedSmithWaterman::AlignerCpuInternalsProfileStats alignerAlignCpuInternals;
	uint64_t alignerAlignCalls;
	uint64_t alignerAlignTotalCells;
	uint64_t alignerAlignTotalQueryBases;
	uint64_t alignerAlignTotalTargetBases;
	uint64_t alignerAlignMaxQueryLen;
	uint64_t alignerAlignMaxTargetLen;
	uint64_t alignerAlignRecordsConsidered;
	uint64_t alignerAlignRecordsEmitted;
	uint64_t alignerAlignRecordsRejectedAfterAlign;
	uint64_t alignerAlignScoreInfoExactScoreMatches;
	uint64_t alignerAlignScoreInfoPositionMatches;
	uint64_t alignerAlignRequiredForCigar;
	uint64_t alignerAlignRequiredForScore;
	uint64_t alignerAlignRequiredForCoordinates;
	uint64_t alignerAlignBypassShadowEnabled;
	uint64_t alignerAlignBypassShadowBypassableRecords;
	uint64_t alignerAlignBypassShadowNonBypassableRecords;
	uint64_t alignerAlignBypassShadowEstSavedNanoseconds;
	uint64_t alignerAlignBypassShadowScoreMismatches;
	uint64_t alignerAlignBypassShadowCoordinateMismatches;
	uint64_t alignerAlignBypassShadowCigarMissingRecords;
	uint64_t alignBatchShadowEnabled;
	uint64_t alignBatchShadowSupported;
	uint64_t alignBatchShadowDisabledReason;
	uint64_t alignBatchShadowRequestsTotal;
	uint64_t alignBatchShadowRequestsCompared;
	uint64_t alignBatchShadowRequestsUnsupported;
	uint64_t alignBatchShadowQueryBases;
	uint64_t alignBatchShadowTargetBases;
	uint64_t alignBatchShadowCells;
	uint64_t alignBatchShadowH2DBytes;
	uint64_t alignBatchShadowD2HBytes;
	uint64_t alignBatchShadowKernelNanoseconds;
	uint64_t alignBatchShadowTotalNanoseconds;
	uint64_t alignBatchShadowCpuReferenceNanoseconds;
	uint64_t alignBatchShadowScoreMismatches;
	uint64_t alignBatchShadowCoordinateMismatches;
	uint64_t alignBatchShadowCigarMismatches;
	uint64_t alignBatchShadowAlignmentStringMismatches;
	uint64_t alignBatchShadowTotalMismatches;
	uint64_t alignBatchShadowFallbacks;
	uint64_t alignBatchShadowHasScoreContract;
	uint64_t alignBatchShadowHasCoordinateContract;
	uint64_t alignBatchShadowHasCigarContract;
	uint64_t alignBatchShadowHasAlignmentStringContract;
	uint64_t accelignShadowEnabled;
	uint64_t accelignShadowSupported;
	uint64_t accelignShadowDisabledReason;
	uint64_t accelignShadowRequestsTotal;
	uint64_t accelignShadowRequestsCompared;
	uint64_t accelignShadowRequestsUnsupported;
	uint64_t accelignShadowQueryBases;
	uint64_t accelignShadowTargetBases;
	uint64_t accelignShadowCells;
	uint64_t accelignShadowH2DBytes;
	uint64_t accelignShadowD2HBytes;
	uint64_t accelignShadowKernelNanoseconds;
	uint64_t accelignShadowTotalNanoseconds;
	uint64_t accelignShadowCpuReferenceNanoseconds;
	uint64_t accelignShadowScoreMismatches;
	uint64_t accelignShadowEndpointMismatches;
	uint64_t accelignShadowTotalMismatches;
	uint64_t accelignShadowFallbacks;
	uint64_t accelignShadowHasScoreContract;
	uint64_t accelignShadowHasEndpointContract;
	uint64_t accelignShadowHasCigarContract;
	uint64_t accelignShadowHasAlignmentStringContract;
	uint64_t accelignShadowUsesRuntimeOutput;
	uint64_t preAlignFilterShadowEnabled;
	uint64_t preAlignFilterCandidates;
	uint64_t preAlignFilterActualEmitted;
	uint64_t preAlignFilterActualRejected;
	uint64_t preAlignFilterPredictedReject;
	uint64_t preAlignFilterTrueReject;
	uint64_t preAlignFilterFalseReject;
	uint64_t preAlignFilterFalseKeep;
	uint64_t preAlignFilterEstAlignCallsSaved;
	uint64_t preAlignFilterEstAlignCellsSaved;
	uint64_t preAlignFilterEstSavedNanoseconds;
	uint64_t preAlignFilterActualEmittedAlignCalls;
	uint64_t preAlignFilterActualRejectedAlignCalls;
	uint64_t preAlignFilterActualEmittedAlignCells;
	uint64_t preAlignFilterActualRejectedAlignCells;
	uint64_t preAlignRejectReasonScore;
	uint64_t preAlignRejectReasonNt;
	uint64_t preAlignRejectReasonLength;
	uint64_t preAlignRejectReasonCoordinates;
	uint64_t preAlignRejectReasonOverlap;
	uint64_t preAlignRejectReasonCigar;
	uint64_t preAlignRejectReasonUnknown;
	uint64_t preAlignFeatureSweepEnabled;
	uint64_t preAlignFeatureSweepRulesTested;
	uint64_t preAlignFeatureSweepBestZeroFalseRejectRule;
	uint64_t preAlignFeatureSweepBestPredictedReject;
	uint64_t preAlignFeatureSweepBestTrueReject;
	uint64_t preAlignFeatureSweepBestFalseReject;
	uint64_t preAlignFeatureSweepBestFalseKeep;
	uint64_t preAlignFeatureSweepBestEstCallsSaved;
	uint64_t preAlignFeatureSweepBestEstCellsSaved;
	uint64_t preAlignFeatureSweepBestEstSavedNanoseconds;
	uint64_t preAlignFeatureEmittedScoreSum;
	uint64_t preAlignFeatureRejectedScoreSum;
	uint64_t preAlignFeatureEmittedRankSum;
	uint64_t preAlignFeatureRejectedRankSum;
	uint64_t preAlignFeatureEmittedTargetLenSum;
	uint64_t preAlignFeatureRejectedTargetLenSum;
	uint64_t preAlignFeatureEmittedAlignCallsSum;
	uint64_t preAlignFeatureRejectedAlignCallsSum;
	uint64_t calls;
	uint64_t scoreInfoRecords;
	uint64_t recordsConsidered;
	uint64_t recordsEmitted;
	uint64_t recordsRejected;
};

inline uint64_t fasim_fastsim_profile_now_nanoseconds()
{
	return static_cast<uint64_t>(
		std::chrono::duration_cast<std::chrono::nanoseconds>(
			std::chrono::steady_clock::now().time_since_epoch()).count());
}

inline void fasim_fastsim_profile_add_elapsed(uint64_t &slot, uint64_t startNanoseconds)
{
	slot += fasim_fastsim_profile_now_nanoseconds() - startNanoseconds;
}

inline uint64_t fasim_fastsim_profile_nanoseconds_from_seconds(double seconds)
{
	if (seconds <= 0.0)
	{
		return 0;
	}
	return static_cast<uint64_t>(seconds * 1000000000.0);
}

inline bool fasim_gpu_dp_column_requested_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GPU_DP_COLUMN");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gpu_dp_column_validate_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GPU_DP_COLUMN_VALIDATE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_pre_align_filter_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_PRE_ALIGN_FILTER_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_pre_align_feature_sweep_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_PRE_ALIGN_FEATURE_SWEEP");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_align_batch_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ALIGN_BATCH_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_aligner_accelign_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ACCELIGN_SHADOW");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_aligner_align_cpu_internals_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ALIGN_INTERNALS");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline int fasim_align_batch_shadow_max_requests_runtime()
{
	static const int maxRequests = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ALIGN_BATCH_SHADOW_MAX_REQUESTS");
		if (env == NULL || env[0] == '\0')
		{
			return 10000;
		}
		const int value = atoi(env);
		return value > 0 ? value : 10000;
	}();
	return maxRequests;
}

inline int fasim_aligner_accelign_shadow_max_requests_runtime()
{
	static const int maxRequests = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ACCELIGN_SHADOW_MAX_REQUESTS");
		if (env == NULL || env[0] == '\0')
		{
			return 10000;
		}
		const int value = atoi(env);
		return value > 0 ? value : 10000;
	}();
	return maxRequests;
}

inline int fasim_align_batch_shadow_request_stride_runtime()
{
	static const int stride = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ALIGN_BATCH_SHADOW_REQUEST_STRIDE");
		if (env == NULL || env[0] == '\0')
		{
			return 1;
		}
		const int value = atoi(env);
		return value > 0 ? value : 1;
	}();
	return stride;
}

inline int fasim_aligner_accelign_shadow_request_stride_runtime()
{
	static const int stride = []()
	{
		const char* env = getenv("FASIM_ALIGNER_ACCELIGN_SHADOW_REQUEST_STRIDE");
		if (env == NULL || env[0] == '\0')
		{
			return 1;
		}
		const int value = atoi(env);
		return value > 0 ? value : 1;
	}();
	return stride;
}

inline bool fasim_prealign_cuda_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ENABLE_PREALIGN_CUDA");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline int fasim_cuda_device_runtime()
{
	const char* env = getenv("FASIM_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	env = getenv("LONGTARGET_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	return -1;
}

inline int fasim_prealign_peak_suppress_bp_runtime()
{
	static const int suppressBp = []()
	{
		const char* env = getenv("FASIM_PREALIGN_PEAK_SUPPRESS_BP");
		if (env == NULL || env[0] == '\0')
		{
			return 5;
		}
		const int value = atoi(env);
		if (value <= 0)
		{
			return 5;
		}
		if (value > 1024)
		{
			return 1024;
		}
		return value;
	}();
	return suppressBp;
}

inline int fasim_prealign_cuda_topk_runtime()
{
	static const int topK = []()
	{
		const char* env = getenv("FASIM_PREALIGN_CUDA_TOPK");
		if (env == NULL || env[0] == '\0')
		{
			return 64;
		}
		int value = atoi(env);
		if (value <= 0)
		{
			return 64;
		}
		if (value > 256)
		{
			return 256;
		}
		return value;
	}();
	return topK;
}

inline uint8_t fasim_encode_base(unsigned char c)
{
	return prealign_shared_encode_base(c);
}

inline void fasim_build_query_profile(const string& query, int matchScore, int mismatchPenalty, std::vector<int16_t>& profile, int& segLenOut)
{
	prealign_shared_build_query_profile(query, matchScore, mismatchPenalty, profile, segLenOut);
}

struct mycutregion
{
	mycutregion() {};
	mycutregion(int ei, int ej) :start(ei), end(ej) {};
	int start;
	int end;
};

struct para
{
	string file1path;
	string file2path;
	string outpath;
	int corenum;
	int rule;
	int cutLength;
	int strand;
	int overlapLength;
	int minScore;
	bool detailOutput;
	bool doFastSim;
	int ntMin;
	int ntMax;
	float scoreMin;
	float minIdentity;
	float minStability;
	int penaltyT;
	int penaltyC;
	int cDistance;
	int cLength;
	// 2021-09-25 22:21:08: use this parameter to determine do fastSIM or not.
};

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src);

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut);

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings);

void cutSequence(string& seq, vector<string>& seqsVec, vector<int>& seqsStartPos,
	int cutLength, int overlapLength, int &cut_num)
{
	unsigned int pos = 0;
	int tmpa = 0;
	int tmpb = 0;
	seqsVec.clear();
	seqsStartPos.clear();
	string cutSeq;
	while (pos < seq.size())
	{
		cutSeq = seq.substr(pos, cutLength);
		seqsVec.push_back(cutSeq);
		seqsStartPos.push_back(pos);
		pos += cutLength;
		pos -= overlapLength;
		tmpa++;
	}
	cut_num = tmpa;
}

bool compMyTriplexSingle(const triplex &a, const triplex &b)
{
	return a.score > b.score;
}

bool compMyTriplexMultiple(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.stari == b.stari)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj > b.starj;
		}
	}
	else
	{
		return a.starj > b.starj;
	}

}

bool compMyTriplexMultiple2(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.endi == b.endi)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj < b.starj;
		}
	}
	else
	{
		return a.starj < b.starj;
	}

}

bool sameMyTriplex(const triplex &a, const triplex &b)
{
	if (a.stari == b.stari && a.starj == b.starj && a.endi == b.endi &&
		a.endj == b.endj && a.score == b.score)
	{
		return true;
	}
	else if (b.stari >= a.stari && b.starj >= a.starj && b.endi <= a.endi &&
		b.endj <= a.endj && b.score < a.score)
	{
		return true;
	}
	else
	{
		return false;
	}

}

struct FasimPreAlignFilterShadowRecord
{
	FasimPreAlignFilterShadowRecord() :
		predictedReject(0),
		actualEmitted(0),
		actualResolved(0),
		reason(0),
		score(0),
		scoreMargin(0),
		localRank(0),
		maxCutlength(0),
		targetLength(0),
		queryLength(0),
		position(0),
		rightTail(0),
		ambiguousBases(0),
		lowercaseBases(0),
		alignCalls(0),
		alignCells(0),
		alignNanoseconds(0)
	{
	}

	triplex candidateTriplex;
	uint8_t predictedReject;
	uint8_t actualEmitted;
	uint8_t actualResolved;
	uint8_t reason;
	int score;
	int scoreMargin;
	uint32_t localRank;
	uint32_t maxCutlength;
	uint32_t targetLength;
	uint32_t queryLength;
	uint32_t position;
	uint32_t rightTail;
	uint32_t ambiguousBases;
	uint32_t lowercaseBases;
	uint64_t alignCalls;
	uint64_t alignCells;
	uint64_t alignNanoseconds;
};

struct FasimAlignBatchShadowRequest
{
	FasimAlignBatchShadowRequest() :
		queryLength(0),
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
	string querySequence;
	string targetSequence;
	int cpuScore;
	int cpuRefBegin;
	int cpuRefEnd;
	int cpuQueryBegin;
	int cpuQueryEnd;
	uint64_t cpuNanoseconds;
};

static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_SCORE = 1;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_NT = 2;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_LENGTH = 3;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_COORDINATES = 4;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_OVERLAP = 5;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_CIGAR = 6;
static const uint8_t FASIM_PRE_ALIGN_REJECT_REASON_UNKNOWN = 7;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_BELOW_EMITTED = 1;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_MARGIN_BELOW_EMITTED = 2;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_LOCAL_RANK_AFTER_EMITTED = 3;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_TARGET_LEN_BELOW_EMITTED = 4;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_POSITION_LEFT_OF_EMITTED = 5;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_RIGHT_TAIL_BELOW_EMITTED = 6;
static const uint8_t FASIM_PRE_ALIGN_FEATURE_RULE_AMBIGUOUS_WITH_NO_EMITTED = 7;

inline bool fasim_triplex_exact_same_for_shadow(const triplex &a, const triplex &b)
{
	return a.stari == b.stari &&
	       a.endi == b.endi &&
	       a.starj == b.starj &&
	       a.endj == b.endj &&
	       a.score == b.score &&
	       a.nt == b.nt &&
	       a.identity == b.identity &&
	       a.tri_score == b.tri_score;
}

inline int fasim_pre_align_filter_max_cutlength(const StripedSmithWaterman::scoreInfo &info)
{
	const float iden = 0.6f;
	int cutlength = static_cast<int>((info.score + 24) / (9 * iden - 4)) + 1;
	if (info.position - cutlength + 1 <= 0)
	{
		cutlength = info.position + 1;
	}
	return cutlength;
}

inline bool fasim_pre_align_filter_predict_reject(const StripedSmithWaterman::scoreInfo &info,
                                                  int targetLength,
                                                  int ntMin,
                                                  const struct para &paraList)
{
	const int maxCutlength = fasim_pre_align_filter_max_cutlength(info);
	if (info.position < 0 || info.position >= targetLength)
	{
		return true;
	}
	if (info.score < paraList.scoreMin)
	{
		return true;
	}
	if (maxCutlength <= 0 || maxCutlength < ntMin)
	{
		return true;
	}
	return false;
}

inline bool fasim_pre_align_is_ambiguous_base(char base)
{
	switch (base)
	{
	case 'A':
	case 'C':
	case 'G':
	case 'T':
	case 'a':
	case 'c':
	case 'g':
	case 't':
		return false;
	default:
		return true;
	}
}

inline void fasim_pre_align_count_window_flags(const string &seq,
                                               int start,
                                               int length,
                                               uint32_t &ambiguousBases,
                                               uint32_t &lowercaseBases)
{
	ambiguousBases = 0;
	lowercaseBases = 0;
	if (start < 0 || length <= 0)
	{
		return;
	}
	const int seqLength = static_cast<int>(seq.size());
	for (int offset = 0; offset < length && start + offset < seqLength; ++offset)
	{
		const char base = seq[static_cast<size_t>(start + offset)];
		if (fasim_pre_align_is_ambiguous_base(base))
		{
			++ambiguousBases;
		}
		if (base >= 'a' && base <= 'z')
		{
			++lowercaseBases;
		}
	}
}

inline uint8_t fasim_pre_align_reject_reason_from_triplex(const triplex &atr,
                                                          const struct para &paraList,
                                                          int ntMin,
                                                          int ntMax)
{
	if (atr.score < paraList.scoreMin ||
	    atr.identity < paraList.minIdentity ||
	    atr.tri_score < paraList.minStability)
	{
		return FASIM_PRE_ALIGN_REJECT_REASON_SCORE;
	}
	if (atr.nt < ntMin)
	{
		return FASIM_PRE_ALIGN_REJECT_REASON_NT;
	}
	if (atr.nt > ntMax)
	{
		return FASIM_PRE_ALIGN_REJECT_REASON_LENGTH;
	}
	return FASIM_PRE_ALIGN_REJECT_REASON_UNKNOWN;
}

inline void fasim_pre_align_add_reject_reason(FasimFastSimExtendProfileStats *profileStats,
                                              uint8_t reason)
{
	if (profileStats == NULL)
	{
		return;
	}
	switch (reason)
	{
	case FASIM_PRE_ALIGN_REJECT_REASON_SCORE:
		++profileStats->preAlignRejectReasonScore;
		break;
	case FASIM_PRE_ALIGN_REJECT_REASON_NT:
		++profileStats->preAlignRejectReasonNt;
		break;
	case FASIM_PRE_ALIGN_REJECT_REASON_LENGTH:
		++profileStats->preAlignRejectReasonLength;
		break;
	case FASIM_PRE_ALIGN_REJECT_REASON_COORDINATES:
		++profileStats->preAlignRejectReasonCoordinates;
		break;
	case FASIM_PRE_ALIGN_REJECT_REASON_OVERLAP:
		++profileStats->preAlignRejectReasonOverlap;
		break;
	case FASIM_PRE_ALIGN_REJECT_REASON_CIGAR:
		++profileStats->preAlignRejectReasonCigar;
		break;
	default:
		++profileStats->preAlignRejectReasonUnknown;
		break;
	}
}

struct FasimPreAlignFeatureRuleStats
{
	FasimPreAlignFeatureRuleStats() :
		predictedReject(0),
		trueReject(0),
		falseReject(0),
		falseKeep(0),
		estCallsSaved(0),
		estCellsSaved(0),
		estSavedNanoseconds(0)
	{
	}

	uint64_t predictedReject;
	uint64_t trueReject;
	uint64_t falseReject;
	uint64_t falseKeep;
	uint64_t estCallsSaved;
	uint64_t estCellsSaved;
	uint64_t estSavedNanoseconds;
};

inline bool fasim_pre_align_feature_rule_matches(const FasimPreAlignFilterShadowRecord &record,
                                                 uint8_t rule,
                                                 int threshold)
{
	switch (rule)
	{
	case FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_BELOW_EMITTED:
		return record.score <= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_MARGIN_BELOW_EMITTED:
		return record.scoreMargin <= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_LOCAL_RANK_AFTER_EMITTED:
		return static_cast<int>(record.localRank) >= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_TARGET_LEN_BELOW_EMITTED:
		return static_cast<int>(record.targetLength) <= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_POSITION_LEFT_OF_EMITTED:
		return static_cast<int>(record.position) <= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_RIGHT_TAIL_BELOW_EMITTED:
		return static_cast<int>(record.rightTail) <= threshold;
	case FASIM_PRE_ALIGN_FEATURE_RULE_AMBIGUOUS_WITH_NO_EMITTED:
		(void)threshold;
		return record.ambiguousBases > 0;
	default:
		return false;
	}
}

inline FasimPreAlignFeatureRuleStats fasim_pre_align_eval_feature_rule(
	const std::vector<FasimPreAlignFilterShadowRecord> &records,
	uint8_t rule,
	int threshold)
{
	FasimPreAlignFeatureRuleStats stats;
	for (size_t i = 0; i < records.size(); ++i)
	{
		const FasimPreAlignFilterShadowRecord &record = records[i];
		const bool predictedReject =
			fasim_pre_align_feature_rule_matches(record, rule, threshold);
		if (predictedReject)
		{
			++stats.predictedReject;
			stats.estCallsSaved += record.alignCalls;
			stats.estCellsSaved += record.alignCells;
			stats.estSavedNanoseconds += record.alignNanoseconds;
			if (record.actualEmitted)
			{
				++stats.falseReject;
			}
			else
			{
				++stats.trueReject;
			}
		}
		else if (!record.actualEmitted)
		{
			++stats.falseKeep;
		}
	}
	return stats;
}

inline void fasim_pre_align_consider_feature_rule(
	const std::vector<FasimPreAlignFilterShadowRecord> &records,
	uint8_t rule,
	int threshold,
	FasimFastSimExtendProfileStats *profileStats)
{
	if (profileStats == NULL)
	{
		return;
	}
	++profileStats->preAlignFeatureSweepRulesTested;
	const FasimPreAlignFeatureRuleStats ruleStats =
		fasim_pre_align_eval_feature_rule(records, rule, threshold);
	if (ruleStats.falseReject != 0)
	{
		return;
	}
	if (profileStats->preAlignFeatureSweepBestZeroFalseRejectRule == 0 ||
	    ruleStats.estSavedNanoseconds > profileStats->preAlignFeatureSweepBestEstSavedNanoseconds ||
	    (ruleStats.estSavedNanoseconds == profileStats->preAlignFeatureSweepBestEstSavedNanoseconds &&
	     ruleStats.trueReject > profileStats->preAlignFeatureSweepBestTrueReject))
	{
		profileStats->preAlignFeatureSweepBestZeroFalseRejectRule = rule;
		profileStats->preAlignFeatureSweepBestPredictedReject = ruleStats.predictedReject;
		profileStats->preAlignFeatureSweepBestTrueReject = ruleStats.trueReject;
		profileStats->preAlignFeatureSweepBestFalseReject = ruleStats.falseReject;
		profileStats->preAlignFeatureSweepBestFalseKeep = ruleStats.falseKeep;
		profileStats->preAlignFeatureSweepBestEstCallsSaved = ruleStats.estCallsSaved;
		profileStats->preAlignFeatureSweepBestEstCellsSaved = ruleStats.estCellsSaved;
		profileStats->preAlignFeatureSweepBestEstSavedNanoseconds = ruleStats.estSavedNanoseconds;
	}
}

inline void fasim_pre_align_run_feature_sweep(
	const std::vector<FasimPreAlignFilterShadowRecord> &records,
	FasimFastSimExtendProfileStats *profileStats)
{
	if (profileStats == NULL || records.empty())
	{
		return;
	}
	profileStats->preAlignFeatureSweepEnabled = 1;

	bool haveEmitted = false;
	int minEmittedScore = 0;
	int minEmittedScoreMargin = 0;
	uint32_t maxEmittedRank = 0;
	uint32_t minEmittedTargetLen = 0;
	uint32_t minEmittedPosition = 0;
	uint32_t minEmittedRightTail = 0;
	uint32_t emittedAmbiguous = 0;

	for (size_t i = 0; i < records.size(); ++i)
	{
		const FasimPreAlignFilterShadowRecord &record = records[i];
		if (record.actualEmitted)
		{
			if (!haveEmitted)
			{
				minEmittedScore = record.score;
				minEmittedScoreMargin = record.scoreMargin;
				maxEmittedRank = record.localRank;
				minEmittedTargetLen = record.targetLength;
				minEmittedPosition = record.position;
				minEmittedRightTail = record.rightTail;
				haveEmitted = true;
			}
			if (record.score < minEmittedScore)
			{
				minEmittedScore = record.score;
			}
			if (record.scoreMargin < minEmittedScoreMargin)
			{
				minEmittedScoreMargin = record.scoreMargin;
			}
			if (record.localRank > maxEmittedRank)
			{
				maxEmittedRank = record.localRank;
			}
			if (record.targetLength < minEmittedTargetLen)
			{
				minEmittedTargetLen = record.targetLength;
			}
			if (record.position < minEmittedPosition)
			{
				minEmittedPosition = record.position;
			}
			if (record.rightTail < minEmittedRightTail)
			{
				minEmittedRightTail = record.rightTail;
			}
			if (record.ambiguousBases > 0)
			{
				++emittedAmbiguous;
			}
		}
	}
	if (!haveEmitted)
	{
		return;
	}

	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_BELOW_EMITTED,
		minEmittedScore - 1,
		profileStats);
	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_SCORE_MARGIN_BELOW_EMITTED,
		minEmittedScoreMargin - 1,
		profileStats);
	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_LOCAL_RANK_AFTER_EMITTED,
		static_cast<int>(maxEmittedRank + 1),
		profileStats);
	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_TARGET_LEN_BELOW_EMITTED,
		static_cast<int>(minEmittedTargetLen) - 1,
		profileStats);
	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_POSITION_LEFT_OF_EMITTED,
		static_cast<int>(minEmittedPosition) - 1,
		profileStats);
	fasim_pre_align_consider_feature_rule(
		records,
		FASIM_PRE_ALIGN_FEATURE_RULE_RIGHT_TAIL_BELOW_EMITTED,
		static_cast<int>(minEmittedRightTail) - 1,
		profileStats);
	if (emittedAmbiguous == 0)
	{
		fasim_pre_align_consider_feature_rule(
			records,
			FASIM_PRE_ALIGN_FEATURE_RULE_AMBIGUOUS_WITH_NO_EMITTED,
			0,
			profileStats);
	}
}

inline void fasim_align_batch_shadow_record_request(
	std::vector<FasimAlignBatchShadowRequest> &requests,
	FasimFastSimExtendProfileStats *profileStats,
	const string &query,
	const string &target,
	const StripedSmithWaterman::Alignment &cpuAlignment,
	uint64_t cpuNanoseconds)
{
	if (profileStats == NULL)
	{
		return;
	}
	++profileStats->alignBatchShadowRequestsTotal;

	const int maxRequests = fasim_align_batch_shadow_max_requests_runtime();
	const int stride = fasim_align_batch_shadow_request_stride_runtime();
	const uint64_t requestIndex = profileStats->alignBatchShadowRequestsTotal - 1;
	if (stride > 1 && (requestIndex % static_cast<uint64_t>(stride)) != 0)
	{
		++profileStats->alignBatchShadowRequestsUnsupported;
		return;
	}
	const uint64_t sampledSoFar =
		profileStats->alignBatchShadowRequestsCompared +
		static_cast<uint64_t>(requests.size());
	if (sampledSoFar >= static_cast<uint64_t>(maxRequests))
	{
		++profileStats->alignBatchShadowRequestsUnsupported;
		return;
	}

	FasimAlignBatchShadowRequest request;
	request.queryLength = static_cast<uint32_t>(query.size());
	request.targetLength = static_cast<uint32_t>(target.size());
	request.querySequence = query;
	request.targetSequence = target;
	request.cpuScore = static_cast<int>(cpuAlignment.sw_score);
	request.cpuRefBegin = cpuAlignment.ref_begin;
	request.cpuRefEnd = cpuAlignment.ref_end;
	request.cpuQueryBegin = cpuAlignment.query_begin;
	request.cpuQueryEnd = cpuAlignment.query_end;
	request.cpuNanoseconds = cpuNanoseconds;
	requests.push_back(request);
}

inline void fasim_aligner_accelign_shadow_record_request(
	std::vector<FasimAlignBatchShadowRequest> &requests,
	FasimFastSimExtendProfileStats *profileStats,
	const string &query,
	const string &target,
	const StripedSmithWaterman::Alignment &cpuAlignment,
	uint64_t cpuNanoseconds)
{
	if (profileStats == NULL)
	{
		return;
	}
	++profileStats->accelignShadowRequestsTotal;

	const int maxRequests = fasim_aligner_accelign_shadow_max_requests_runtime();
	const int stride = fasim_aligner_accelign_shadow_request_stride_runtime();
	const uint64_t requestIndex = profileStats->accelignShadowRequestsTotal - 1;
	if (stride > 1 && (requestIndex % static_cast<uint64_t>(stride)) != 0)
	{
		++profileStats->accelignShadowRequestsUnsupported;
		return;
	}
	const uint64_t sampledSoFar =
		profileStats->accelignShadowRequestsCompared +
		static_cast<uint64_t>(requests.size());
	if (sampledSoFar >= static_cast<uint64_t>(maxRequests))
	{
		++profileStats->accelignShadowRequestsUnsupported;
		return;
	}

	FasimAlignBatchShadowRequest request;
	request.queryLength = static_cast<uint32_t>(query.size());
	request.targetLength = static_cast<uint32_t>(target.size());
	request.querySequence = query;
	request.targetSequence = target;
	request.cpuScore = static_cast<int>(cpuAlignment.sw_score);
	request.cpuRefBegin = cpuAlignment.ref_begin;
	request.cpuRefEnd = cpuAlignment.ref_end;
	request.cpuQueryBegin = cpuAlignment.query_begin;
	request.cpuQueryEnd = cpuAlignment.query_end;
	request.cpuNanoseconds = cpuNanoseconds;
	requests.push_back(request);
}

inline void fasim_align_batch_shadow_finalize(
	const std::vector<FasimAlignBatchShadowRequest> &requests,
	const string &query,
	FasimFastSimExtendProfileStats *profileStats)
{
	if (profileStats == NULL)
	{
		return;
	}
	profileStats->alignBatchShadowEnabled = 1;
	profileStats->alignBatchShadowHasScoreContract = 1;
	profileStats->alignBatchShadowHasCoordinateContract = 1;
	profileStats->alignBatchShadowHasCigarContract = 0;
	profileStats->alignBatchShadowHasAlignmentStringContract = 0;

	const uint64_t totalStart = fasim_fastsim_profile_now_nanoseconds();
	for (size_t i = 0; i < requests.size(); ++i)
	{
		const FasimAlignBatchShadowRequest &request = requests[i];
		++profileStats->alignBatchShadowRequestsCompared;
		profileStats->alignBatchShadowQueryBases += request.queryLength;
		profileStats->alignBatchShadowTargetBases += request.targetLength;
		profileStats->alignBatchShadowCells +=
			static_cast<uint64_t>(request.queryLength) *
			static_cast<uint64_t>(request.targetLength);
		profileStats->alignBatchShadowCpuReferenceNanoseconds +=
			request.cpuNanoseconds;
	}
	if (requests.empty())
	{
		if (profileStats->alignBatchShadowRequestsCompared == 0 &&
		    profileStats->alignBatchShadowSupported == 0)
		{
			profileStats->alignBatchShadowDisabledReason = 4;
		}
		profileStats->alignBatchShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	if (!prealign_cuda_is_built())
	{
		profileStats->alignBatchShadowSupported = 0;
		profileStats->alignBatchShadowDisabledReason = 1;
		profileStats->alignBatchShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->alignBatchShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	string cudaError;
	if (!prealign_cuda_init(0, &cudaError))
	{
		profileStats->alignBatchShadowSupported = 0;
		profileStats->alignBatchShadowDisabledReason = 1;
		profileStats->alignBatchShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->alignBatchShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	PrealignSharedQueryCache queryCache;
	if (!queryCache.prepare(0, query, 5, 5, 4, &cudaError))
	{
		profileStats->alignBatchShadowSupported = 0;
		profileStats->alignBatchShadowDisabledReason = 2;
		profileStats->alignBatchShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->alignBatchShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	std::map<int, std::vector<size_t> > groupsByTargetLength;
	for (size_t i = 0; i < requests.size(); ++i)
	{
		groupsByTargetLength[static_cast<int>(requests[i].targetLength)].push_back(i);
	}

	for (std::map<int, std::vector<size_t> >::const_iterator groupIt =
	         groupsByTargetLength.begin();
	     groupIt != groupsByTargetLength.end();
	     ++groupIt)
	{
		const int targetLength = groupIt->first;
		const std::vector<size_t> &indices = groupIt->second;
		if (targetLength <= 0 || indices.empty())
		{
			continue;
		}

		std::vector<uint8_t> encodedTargets;
		encodedTargets.reserve(indices.size() * static_cast<size_t>(targetLength));
		for (size_t i = 0; i < indices.size(); ++i)
		{
			std::vector<uint8_t> encodedTarget;
			prealign_shared_encode_sequence(requests[indices[i]].targetSequence,
			                                encodedTarget);
			encodedTargets.insert(encodedTargets.end(),
			                      encodedTarget.begin(),
			                      encodedTarget.end());
		}

		std::vector<PreAlignCudaPeak> peaks;
		PreAlignCudaBatchResult batchResult;
		const bool ok = prealign_cuda_find_topk_column_maxima(
			queryCache.query_handle(),
			encodedTargets.data(),
			static_cast<int>(indices.size()),
			targetLength,
			1,
			&peaks,
			&batchResult,
			&cudaError);
		if (!ok || peaks.size() != indices.size())
		{
			profileStats->alignBatchShadowSupported = 0;
			profileStats->alignBatchShadowDisabledReason = 3;
			profileStats->alignBatchShadowFallbacks +=
				static_cast<uint64_t>(indices.size());
			continue;
		}

		profileStats->alignBatchShadowSupported = 1;
		profileStats->alignBatchShadowH2DBytes +=
			static_cast<uint64_t>(encodedTargets.size()) *
			static_cast<uint64_t>(sizeof(uint8_t));
		profileStats->alignBatchShadowD2HBytes +=
			static_cast<uint64_t>(peaks.size()) *
			static_cast<uint64_t>(sizeof(PreAlignCudaPeak));
		profileStats->alignBatchShadowKernelNanoseconds +=
			fasim_fastsim_profile_nanoseconds_from_seconds(batchResult.gpuSeconds);

		for (size_t i = 0; i < indices.size(); ++i)
		{
			const FasimAlignBatchShadowRequest &request = requests[indices[i]];
			const PreAlignCudaPeak &peak = peaks[i];
			if (peak.score != request.cpuScore)
			{
				++profileStats->alignBatchShadowScoreMismatches;
				++profileStats->alignBatchShadowTotalMismatches;
			}
			if (peak.position != request.cpuRefEnd)
			{
				++profileStats->alignBatchShadowCoordinateMismatches;
				++profileStats->alignBatchShadowTotalMismatches;
			}
		}
	}
	profileStats->alignBatchShadowTotalNanoseconds +=
		fasim_fastsim_profile_now_nanoseconds() - totalStart;
}

inline void fasim_aligner_accelign_shadow_finalize(
	const std::vector<FasimAlignBatchShadowRequest> &requests,
	FasimFastSimExtendProfileStats *profileStats)
{
	if (profileStats == NULL)
	{
		return;
	}
	profileStats->accelignShadowEnabled = 1;
	profileStats->accelignShadowHasScoreContract = 1;
	profileStats->accelignShadowHasEndpointContract = 1;
	profileStats->accelignShadowHasCigarContract = 0;
	profileStats->accelignShadowHasAlignmentStringContract = 0;
	profileStats->accelignShadowUsesRuntimeOutput = 0;

	const uint64_t totalStart = fasim_fastsim_profile_now_nanoseconds();
	for (size_t i = 0; i < requests.size(); ++i)
	{
		const FasimAlignBatchShadowRequest &request = requests[i];
		++profileStats->accelignShadowRequestsCompared;
		profileStats->accelignShadowQueryBases += request.queryLength;
		profileStats->accelignShadowTargetBases += request.targetLength;
		profileStats->accelignShadowCells +=
			static_cast<uint64_t>(request.queryLength) *
			static_cast<uint64_t>(request.targetLength);
		profileStats->accelignShadowCpuReferenceNanoseconds +=
			request.cpuNanoseconds;
	}
	if (requests.empty())
	{
		if (profileStats->accelignShadowRequestsCompared == 0 &&
		    profileStats->accelignShadowSupported == 0)
		{
			profileStats->accelignShadowDisabledReason = 4;
		}
		profileStats->accelignShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	if (!accelign_shadow_is_built())
	{
		profileStats->accelignShadowSupported = 0;
		profileStats->accelignShadowDisabledReason = 1;
		profileStats->accelignShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->accelignShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	string accelignError;
	if (!accelign_shadow_init(0, &accelignError))
	{
		profileStats->accelignShadowSupported = 0;
		profileStats->accelignShadowDisabledReason = 1;
		profileStats->accelignShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->accelignShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	std::vector<AccelignShadowRequest> accelignRequests;
	accelignRequests.reserve(requests.size());
	for (size_t i = 0; i < requests.size(); ++i)
	{
		AccelignShadowRequest request;
		request.queryLength = requests[i].queryLength;
		request.targetLength = requests[i].targetLength;
		request.querySequence = requests[i].querySequence;
		request.targetSequence = requests[i].targetSequence;
		request.cpuScore = requests[i].cpuScore;
		request.cpuRefEnd = requests[i].cpuRefEnd;
		request.cpuQueryEnd = requests[i].cpuQueryEnd;
		accelignRequests.push_back(request);
	}

	std::vector<AccelignShadowResult> results;
	AccelignShadowBatchResult batchResult;
	const bool ok = accelign_shadow_run_local_affine_float(
		accelignRequests,
		&results,
		&batchResult,
		&accelignError);
	if (!ok || results.size() != requests.size())
	{
		profileStats->accelignShadowSupported = 0;
		profileStats->accelignShadowDisabledReason = 3;
		profileStats->accelignShadowFallbacks +=
			static_cast<uint64_t>(requests.size());
		profileStats->accelignShadowTotalNanoseconds +=
			fasim_fastsim_profile_now_nanoseconds() - totalStart;
		return;
	}

	profileStats->accelignShadowSupported = 1;
	profileStats->accelignShadowH2DBytes += batchResult.h2dBytes;
	profileStats->accelignShadowD2HBytes += batchResult.d2hBytes;
	profileStats->accelignShadowKernelNanoseconds +=
		fasim_fastsim_profile_nanoseconds_from_seconds(batchResult.gpuSeconds);

	for (size_t i = 0; i < requests.size(); ++i)
	{
		const FasimAlignBatchShadowRequest &request = requests[i];
		const AccelignShadowResult &result = results[i];
		if (result.score != request.cpuScore)
		{
			++profileStats->accelignShadowScoreMismatches;
			++profileStats->accelignShadowTotalMismatches;
		}
		if (result.refEnd != request.cpuRefEnd ||
		    result.queryEnd != request.cpuQueryEnd)
		{
			++profileStats->accelignShadowEndpointMismatches;
			++profileStats->accelignShadowTotalMismatches;
		}
	}

	profileStats->accelignShadowTotalNanoseconds +=
		fasim_fastsim_profile_now_nanoseconds() - totalStart;
}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         const struct para &paraList,
                                         bool materializeAlignmentStrings = true,
                                         FasimFastSimExtendProfileStats *profileStats = NULL);

void fastSIM(string& strA, string& strB, string& strSrc,
	long dnaStartPos, long min_score, float parm_M,
	float parm_I, float parm_O, float parm_E,
	vector<struct triplex>& triplex_list,
	long strand, long Para, long rule,
	int ntMin, int ntMax, int penaltyT,
	int penaltyC, struct para paraList,
	bool materializeAlignmentStrings = true)
{
	int32_t maskLen = 15;
	StripedSmithWaterman::Aligner aligner;
	StripedSmithWaterman::Filter filter;
	StripedSmithWaterman::Alignment alignment;
	std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
		bool prealigned = false;
		if (fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built())
		{
			static thread_local bool cudaInitDone = false;
			static thread_local bool cudaInitOk = false;
			static thread_local PrealignSharedQueryCache queryCache;

			if (!cudaInitDone)
			{
			cudaInitDone = true;
			string cudaError;
			cudaInitOk = prealign_cuda_init(fasim_cuda_device_runtime(), &cudaError);
		}

			if (cudaInitOk)
			{
				string cudaError;
				if (!queryCache.prepare(fasim_cuda_device_runtime(), strA, 5, 5, 4, &cudaError))
				{
					cudaInitOk = false;
				}

				if (cudaInitOk && queryCache.query_handle().profileDevice != 0)
				{
					static std::vector<uint8_t> encodedTarget;
					prealign_shared_encode_sequence(strB, encodedTarget);

						std::vector<PreAlignCudaPeak> peaks;
						PreAlignCudaBatchResult batchResult;
						string cudaError;
						const int topK = fasim_prealign_cuda_topk_runtime();
						if (prealign_cuda_find_topk_column_maxima(queryCache.query_handle(),
						                                          encodedTarget.data(),
						                                          1,
						                                          static_cast<int>(encodedTarget.size()),
				                                          topK,
				                                          &peaks,
				                                          &batchResult,
				                                          &cudaError))
				{
					finalScoreInfo.clear();
					const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
					for (int k = 0; k < topK; ++k)
					{
						const PreAlignCudaPeak& p = peaks[static_cast<size_t>(k)];
						if (p.score <= min_score || p.position < 0)
						{
							continue;
						}
						bool suppressed = false;
						for (size_t s = 0; s < finalScoreInfo.size(); ++s)
						{
							if (abs(finalScoreInfo[s].position - p.position) < suppressBp)
							{
								suppressed = true;
								break;
							}
						}
						if (!suppressed)
						{
							finalScoreInfo.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
						}
					}
					prealigned = true;
				}
			}
		}
	}

	if (!prealigned)
	{
		aligner.preAlign(strA.c_str(), strB.c_str(), strB.size(), filter, &alignment, maskLen, min_score, finalScoreInfo, parm_M, parm_I);
	}
	fastSIM_extend_from_scoreinfo(aligner,
	                              filter,
	                              alignment,
	                              maskLen,
	                              strA,
	                              strB,
	                              strSrc,
	                              dnaStartPos,
	                              finalScoreInfo,
	                              triplex_list,
	                              strand,
	                              Para,
	                              rule,
	                              ntMin,
	                              ntMax,
	                              penaltyT,
	                              penaltyC,
	                              paraList,
	                              materializeAlignmentStrings,
	                              NULL);
}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         const struct para &paraList,
                                         bool materializeAlignmentStrings,
                                         FasimFastSimExtendProfileStats *profileStats)
{
	const uint64_t inclusiveStart =
		profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
	if (profileStats != NULL)
	{
		++profileStats->calls;
		profileStats->scoreInfoRecords +=
			static_cast<uint64_t>(finalScoreInfo.size());
	}
	const uint64_t allocationStart =
		profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
	vector<struct triplex> myTriplexList;
	std::vector<FasimPreAlignFilterShadowRecord> preAlignShadowRecords;
	std::vector<FasimAlignBatchShadowRequest> alignBatchShadowRequests;
	std::vector<FasimAlignBatchShadowRequest> accelignShadowRequests;
	const bool preAlignShadowEnabled =
		profileStats != NULL && fasim_pre_align_filter_shadow_enabled_runtime();
	const bool alignBatchShadowEnabled =
		profileStats != NULL && fasim_align_batch_shadow_enabled_runtime();
	const bool accelignShadowEnabled =
		profileStats != NULL && fasim_aligner_accelign_shadow_enabled_runtime();
	const bool alignerCpuInternalsEnabled =
		profileStats != NULL && fasim_aligner_align_cpu_internals_enabled_runtime();
	if (profileStats != NULL)
	{
		fasim_fastsim_profile_add_elapsed(profileStats->allocationNanoseconds,
		                                  allocationStart);
		if (alignerCpuInternalsEnabled)
		{
			profileStats->alignerAlignCpuInternalsEnabled = 1;
			profileStats->alignerAlignCpuInternals.enabled = 1;
		}
		if (preAlignShadowEnabled)
		{
			profileStats->preAlignFilterShadowEnabled = 1;
			preAlignShadowRecords.reserve(finalScoreInfo.size());
		}
		if (alignBatchShadowEnabled)
		{
			profileStats->alignBatchShadowEnabled = 1;
			alignBatchShadowRequests.reserve(
				static_cast<size_t>(fasim_align_batch_shadow_max_requests_runtime()));
		}
		if (accelignShadowEnabled)
		{
			profileStats->accelignShadowEnabled = 1;
			accelignShadowRequests.reserve(
				static_cast<size_t>(fasim_aligner_accelign_shadow_max_requests_runtime()));
		}
	}

	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	string smallSeq;
	for (int i = 0; i < finalScoreInfo.size(); i++)
	{
		const uint64_t scanStart =
			profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
		if (profileStats != NULL)
		{
			++profileStats->recordsConsidered;
			fasim_fastsim_profile_add_elapsed(profileStats->scoreInfoScanNanoseconds,
			                                  scanStart);
		}
		float Iden = 0.6;
		int cutlength, bestcutregion;
		int myflag = 0;
		StripedSmithWaterman::Alignment bestalignment;
		bestalignment.sw_score = 0;
		size_t preAlignShadowIndex = static_cast<size_t>(-1);
		uint64_t candidateAlignCalls = 0;
		uint64_t candidateAlignCells = 0;
		uint64_t candidateAlignNanoseconds = 0;
		if (preAlignShadowEnabled)
		{
			FasimPreAlignFilterShadowRecord record;
			const int preAlignMaxCutlength =
				fasim_pre_align_filter_max_cutlength(finalScoreInfo[i]);
			const int preAlignWindowStart =
				finalScoreInfo[i].position - preAlignMaxCutlength + 1;
			record.predictedReject = fasim_pre_align_filter_predict_reject(finalScoreInfo[i],
			                                                               static_cast<int>(strB.size()),
			                                                               ntMin,
			                                                               paraList) ? 1 : 0;
			record.score = finalScoreInfo[i].score;
			record.scoreMargin = finalScoreInfo[i].score - static_cast<int>(paraList.scoreMin);
			record.localRank = static_cast<uint32_t>(i + 1);
			record.maxCutlength = preAlignMaxCutlength > 0 ?
				static_cast<uint32_t>(preAlignMaxCutlength) : 0;
			record.targetLength = record.maxCutlength;
			record.queryLength = static_cast<uint32_t>(strA.size());
			record.position = finalScoreInfo[i].position >= 0 ?
				static_cast<uint32_t>(finalScoreInfo[i].position) : 0;
			record.rightTail =
				finalScoreInfo[i].position >= 0 &&
				static_cast<size_t>(finalScoreInfo[i].position) < strB.size() ?
				static_cast<uint32_t>(strB.size() -
				                      static_cast<size_t>(finalScoreInfo[i].position) - 1) :
				0;
			fasim_pre_align_count_window_flags(strB,
			                                   preAlignWindowStart,
			                                   preAlignMaxCutlength,
			                                   record.ambiguousBases,
			                                   record.lowercaseBases);
			preAlignShadowIndex = preAlignShadowRecords.size();
			preAlignShadowRecords.push_back(record);
			++profileStats->preAlignFilterCandidates;
		}
		while (Iden <= 1)
		{
			cutlength = (int)(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
			cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
			smallSeq = strB.substr(finalScoreInfo[i].position - cutlength + 1, cutlength);
				const uint64_t alignStart =
					profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
				StripedSmithWaterman::AlignerCpuInternalsProfileStats* previousInternalsStats = NULL;
				if (alignerCpuInternalsEnabled)
				{
					previousInternalsStats =
						StripedSmithWaterman::SetAlignerCpuInternalsProfileStats(
							&profileStats->alignerAlignCpuInternals);
				}
				aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &alignment, maskLen);
				if (alignerCpuInternalsEnabled)
				{
					StripedSmithWaterman::SetAlignerCpuInternalsProfileStats(previousInternalsStats);
				}
				if (profileStats != NULL)
				{
					const uint64_t alignElapsed =
						fasim_fastsim_profile_now_nanoseconds() - alignStart;
					profileStats->alignerAlignNanoseconds += alignElapsed;
					++profileStats->alignerAlignCalls;
					if (preAlignShadowEnabled)
					{
						++candidateAlignCalls;
						candidateAlignNanoseconds += alignElapsed;
					}
					profileStats->alignerAlignTotalQueryBases +=
						static_cast<uint64_t>(strA.size());
					profileStats->alignerAlignTotalTargetBases +=
						static_cast<uint64_t>(smallSeq.size());
					const uint64_t alignCells =
						static_cast<uint64_t>(strA.size()) *
						static_cast<uint64_t>(smallSeq.size());
					profileStats->alignerAlignTotalCells += alignCells;
					if (preAlignShadowEnabled)
					{
						candidateAlignCells += alignCells;
					}
					if (static_cast<uint64_t>(strA.size()) > profileStats->alignerAlignMaxQueryLen)
					{
						profileStats->alignerAlignMaxQueryLen =
							static_cast<uint64_t>(strA.size());
					}
					if (static_cast<uint64_t>(smallSeq.size()) > profileStats->alignerAlignMaxTargetLen)
					{
						profileStats->alignerAlignMaxTargetLen =
							static_cast<uint64_t>(smallSeq.size());
					}
					fasim_fastsim_profile_add_elapsed(profileStats->alignmentReconstructNanoseconds,
					                                  alignStart);
					if (alignBatchShadowEnabled)
					{
						fasim_align_batch_shadow_record_request(alignBatchShadowRequests,
						                                        profileStats,
						                                        strA,
						                                        smallSeq,
						                                        alignment,
						                                        alignElapsed);
					}
					if (accelignShadowEnabled)
					{
						fasim_aligner_accelign_shadow_record_request(accelignShadowRequests,
						                                             profileStats,
						                                             strA,
						                                             smallSeq,
						                                             alignment,
						                                             alignElapsed);
					}
				}
			if (alignment.sw_score >= finalScoreInfo[i].score)
			{
				myflag = 1;
				break;
			}
			if (alignment.sw_score > bestalignment.sw_score && alignment.ref_end == cutlength - 1)
			{
				bestalignment.sw_score = alignment.sw_score;
				bestalignment.sw_score_next_best = alignment.sw_score_next_best;
				bestalignment.ref_begin = alignment.ref_begin;
				bestalignment.ref_end = alignment.ref_end;
				bestalignment.query_begin = alignment.query_begin;
				bestalignment.query_end = alignment.query_end;
				bestalignment.ref_end_next_best = alignment.ref_end_next_best;
				bestalignment.mismatches = alignment.mismatches;
				bestalignment.cigar_string = alignment.cigar_string;
				bestalignment.cigar = alignment.cigar;
				bestcutregion = cutlength;
				myflag = 2;
			}
			Iden += 0.1;
		}
		if (myflag == 2)
		{
			alignment.sw_score = bestalignment.sw_score;
			alignment.sw_score_next_best = bestalignment.sw_score_next_best;
			alignment.ref_begin = bestalignment.ref_begin;
			alignment.ref_end = bestalignment.ref_end;
			alignment.query_begin = bestalignment.query_begin;
			alignment.query_end = bestalignment.query_end;
			alignment.ref_end_next_best = bestalignment.ref_end_next_best;
			alignment.mismatches = bestalignment.mismatches;
			alignment.cigar_string = bestalignment.cigar_string;
			alignment.cigar = bestalignment.cigar;
			cutlength = bestcutregion;
		}
		bestalignment.Clear();
		const uint64_t filterStart =
			profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
			if (alignment.sw_score != 0)
			{
				const size_t triplexListSizeBeforeConvert = myTriplexList.size();
				if (profileStats != NULL)
				{
					fasim_fastsim_profile_add_elapsed(profileStats->candidateFilterNanoseconds,
					                                  filterStart);
					++profileStats->alignerAlignRecordsConsidered;
					++profileStats->alignerAlignRequiredForCigar;
					++profileStats->alignerAlignRequiredForScore;
					++profileStats->alignerAlignRequiredForCoordinates;
					if (alignment.sw_score == finalScoreInfo[i].score)
					{
						++profileStats->alignerAlignScoreInfoExactScoreMatches;
					}
				}
				alignment.ref_begin = alignment.ref_begin + finalScoreInfo[i].position - cutlength + 1;
				alignment.ref_end = alignment.ref_end + finalScoreInfo[i].position - cutlength + 1;
				if (profileStats != NULL &&
				    (alignment.ref_begin <= finalScoreInfo[i].position &&
				     alignment.ref_end >= finalScoreInfo[i].position))
				{
					++profileStats->alignerAlignScoreInfoPositionMatches;
				}
			const uint64_t buildStart =
				profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
			convertMyTriplex(alignment,
			                 myTriplexList,
			                 strA,
			                 strB,
			                 strSrc,
			                 nt_table,
			                 dnaStartPos,
			                 rule,
			                 strand,
			                 Para,
			                 penaltyT,
			                 penaltyC,
			                 ntMin,
			                 ntMax,
			                 materializeAlignmentStrings);
			if (profileStats != NULL)
			{
				fasim_fastsim_profile_add_elapsed(profileStats->recordBuildNanoseconds,
				                                  buildStart);
				fasim_fastsim_profile_add_elapsed(profileStats->cigarNanoseconds,
				                                  buildStart);
				if (materializeAlignmentStrings)
				{
					fasim_fastsim_profile_add_elapsed(profileStats->stringFormatNanoseconds,
					                                  buildStart);
				}
			}
			if (preAlignShadowEnabled && preAlignShadowIndex < preAlignShadowRecords.size())
			{
				FasimPreAlignFilterShadowRecord &record =
					preAlignShadowRecords[preAlignShadowIndex];
				record.alignCalls = candidateAlignCalls;
				record.alignCells = candidateAlignCells;
				record.alignNanoseconds = candidateAlignNanoseconds;
				if (myTriplexList.size() > triplexListSizeBeforeConvert)
				{
					record.candidateTriplex = myTriplexList.back();
				}
				else
				{
					record.actualResolved = 1;
					record.reason = FASIM_PRE_ALIGN_REJECT_REASON_NT;
				}
			}
		}
		else if (profileStats != NULL)
		{
			fasim_fastsim_profile_add_elapsed(profileStats->candidateFilterNanoseconds,
			                                  filterStart);
			++profileStats->recordsRejected;
			if (preAlignShadowEnabled && preAlignShadowIndex < preAlignShadowRecords.size())
			{
				FasimPreAlignFilterShadowRecord &record =
					preAlignShadowRecords[preAlignShadowIndex];
				record.alignCalls = candidateAlignCalls;
				record.alignCells = candidateAlignCells;
				record.alignNanoseconds = candidateAlignNanoseconds;
				record.actualResolved = 1;
				record.reason = FASIM_PRE_ALIGN_REJECT_REASON_SCORE;
			}
		}
	}
	const uint64_t duplicateStart =
		profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	if (profileStats != NULL)
	{
		fasim_fastsim_profile_add_elapsed(profileStats->duplicateOverlapNanoseconds,
		                                  duplicateStart);
	}
	for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
	{
		triplex atr = myTriplexList[i];
		const uint64_t pushStart =
			profileStats != NULL ? fasim_fastsim_profile_now_nanoseconds() : 0;
		if (atr.identity >= paraList.minIdentity && atr.tri_score >= paraList.minStability && atr.nt >= ntMin)
		{
			triplex_list.push_back(atr);
			if (profileStats != NULL)
			{
				++profileStats->recordsEmitted;
				++profileStats->alignerAlignRecordsEmitted;
				if (preAlignShadowEnabled)
				{
					for (size_t shadowIndex = 0; shadowIndex < preAlignShadowRecords.size(); ++shadowIndex)
					{
						FasimPreAlignFilterShadowRecord &record =
							preAlignShadowRecords[shadowIndex];
						if (!record.actualResolved &&
						    fasim_triplex_exact_same_for_shadow(record.candidateTriplex, atr))
						{
							record.actualResolved = 1;
							record.actualEmitted = 1;
							break;
						}
					}
				}
			}
		}
		else if (profileStats != NULL)
		{
			++profileStats->recordsRejected;
			++profileStats->alignerAlignRecordsRejectedAfterAlign;
			if (preAlignShadowEnabled)
			{
				for (size_t shadowIndex = 0; shadowIndex < preAlignShadowRecords.size(); ++shadowIndex)
				{
					FasimPreAlignFilterShadowRecord &record =
						preAlignShadowRecords[shadowIndex];
					if (!record.actualResolved &&
					    fasim_triplex_exact_same_for_shadow(record.candidateTriplex, atr))
					{
						record.actualResolved = 1;
						record.reason = fasim_pre_align_reject_reason_from_triplex(atr,
						                                                           paraList,
						                                                           ntMin,
						                                                           ntMax);
						break;
					}
				}
			}
		}
		if (profileStats != NULL)
		{
			fasim_fastsim_profile_add_elapsed(profileStats->vectorPushNanoseconds,
			                                  pushStart);
			fasim_fastsim_profile_add_elapsed(profileStats->outputStageNanoseconds,
			                                  pushStart);
		}
	}
	if (profileStats != NULL)
	{
		if (preAlignShadowEnabled)
		{
			for (size_t shadowIndex = 0; shadowIndex < preAlignShadowRecords.size(); ++shadowIndex)
			{
				FasimPreAlignFilterShadowRecord &record =
					preAlignShadowRecords[shadowIndex];
				if (!record.actualResolved)
				{
					record.actualResolved = 1;
					record.reason = FASIM_PRE_ALIGN_REJECT_REASON_OVERLAP;
				}
				if (record.actualEmitted)
				{
					++profileStats->preAlignFilterActualEmitted;
					profileStats->preAlignFilterActualEmittedAlignCalls += record.alignCalls;
					profileStats->preAlignFilterActualEmittedAlignCells += record.alignCells;
					profileStats->preAlignFeatureEmittedScoreSum +=
						static_cast<uint64_t>(record.score > 0 ? record.score : 0);
					profileStats->preAlignFeatureEmittedRankSum += record.localRank;
					profileStats->preAlignFeatureEmittedTargetLenSum += record.targetLength;
					profileStats->preAlignFeatureEmittedAlignCallsSum += record.alignCalls;
				}
				else
				{
					++profileStats->preAlignFilterActualRejected;
					profileStats->preAlignFilterActualRejectedAlignCalls += record.alignCalls;
					profileStats->preAlignFilterActualRejectedAlignCells += record.alignCells;
					profileStats->preAlignFeatureRejectedScoreSum +=
						static_cast<uint64_t>(record.score > 0 ? record.score : 0);
					profileStats->preAlignFeatureRejectedRankSum += record.localRank;
					profileStats->preAlignFeatureRejectedTargetLenSum += record.targetLength;
					profileStats->preAlignFeatureRejectedAlignCallsSum += record.alignCalls;
					fasim_pre_align_add_reject_reason(profileStats, record.reason);
				}
				if (record.predictedReject)
				{
					++profileStats->preAlignFilterPredictedReject;
					profileStats->preAlignFilterEstAlignCallsSaved += record.alignCalls;
					profileStats->preAlignFilterEstAlignCellsSaved += record.alignCells;
					profileStats->preAlignFilterEstSavedNanoseconds += record.alignNanoseconds;
					if (record.actualEmitted)
					{
						++profileStats->preAlignFilterFalseReject;
					}
					else
					{
						++profileStats->preAlignFilterTrueReject;
					}
				}
				else if (!record.actualEmitted)
				{
					++profileStats->preAlignFilterFalseKeep;
				}
			}
			if (fasim_pre_align_feature_sweep_enabled_runtime())
			{
				fasim_pre_align_run_feature_sweep(preAlignShadowRecords, profileStats);
			}
		}
		if (alignBatchShadowEnabled)
		{
			fasim_align_batch_shadow_finalize(alignBatchShadowRequests, strA, profileStats);
		}
		if (accelignShadowEnabled)
		{
			fasim_aligner_accelign_shadow_finalize(accelignShadowRequests, profileStats);
		}
		fasim_fastsim_profile_add_elapsed(profileStats->inclusiveNanoseconds,
		                                  inclusiveStart);
		profileStats->exclusiveNanoseconds = profileStats->inclusiveNanoseconds;
	}
}

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut)
{
	int match = 0;
	int mis_match = 0;
	int nt = 0;

	float tri_score = 0.0f;
	float hashvalue = 0.0f;
	float prescore = 0.0f;
	char prechar = 0;
	char curchar = 0;

	int32_t q = alignment.ref_begin;
	int32_t p = alignment.query_begin;

	for (size_t cLoop = 0; cLoop < alignment.cigar.size(); ++cLoop)
	{
		const uint32_t cigarInt = alignment.cigar[cLoop];
		const char letter = cigar_int_to_op(cigarInt);
		const uint32_t length = cigar_int_to_len(cigarInt);
		for (uint32_t i = 0; i < length; ++i)
		{
			char refc = 0;
			char refc_src = 0;
			char readc = 0;
			bool ref_gap = false;

			if (letter == 'I')
			{
				refc = '-';
				refc_src = '-';
				readc = read_seq[static_cast<size_t>(p)];
				++p;
				ref_gap = true;
			}
			else if (letter == 'D')
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = '-';
			}
			else
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = read_seq[static_cast<size_t>(p)];
				++p;
			}

			++nt;
			if (refc == readc)
			{
				++match;
			}
			else
			{
				++mis_match;
			}

			curchar = (refc == '-') ? '-' : refc_src;
			hashvalue = triplex_score(curchar, readc, static_cast<int>(Para));

			if ((curchar == prechar) && curchar == 'T')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyT);
				hashvalue = static_cast<float>(penaltyT);
			}
			if ((curchar == prechar) && curchar == 'C')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyC);
				hashvalue = static_cast<float>(penaltyC);
			}
			prescore = hashvalue;
			if (!ref_gap)
			{
				prechar = curchar;
			}
			tri_score += hashvalue;
		}
	}

	ntOut = nt;
	identityOut = (match + mis_match) ? (static_cast<float>(100 * match) / static_cast<float>(match + mis_match)) : 0.0f;
	if (nt > 0 && nt >= ntMin && nt <= ntMax)
	{
		triScoreOut = tri_score / static_cast<float>(nt);
	}
	else
	{
		triScoreOut = 0.0f;
	}
}

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings)
{
	int nt = 0;
	float identity = 0.0f;
	float tri_score = 0.0f;
	fasim_calc_identity_and_triscore_from_cigar(alignment,
	                                            ref_seq,
	                                            read_seq,
	                                            ref_seq_src,
	                                            Para,
	                                            penaltyT,
	                                            penaltyC,
	                                            ntMin,
	                                            ntMax,
	                                            identity,
	                                            tri_score,
	                                            nt);

	string read_align;
	string ref_align_src;
	if (materializeAlignmentStrings)
	{
		string ref_align;
		getAlignment(alignment, ref_seq, read_seq, ref_seq_src, table, ref_align, read_align, ref_align_src);
	}

	int refStart;
	int refEnd;
	if ((Para > 0 && strand == 1) || (Para < 0 && strand == 0))
	{
		refStart = static_cast<int>(ref_seq.size()) - alignment.ref_end - 1;
		refEnd = static_cast<int>(ref_seq.size()) - alignment.ref_begin - 1;
	}
	else
	{
		refStart = alignment.ref_begin + 1;
		refEnd = alignment.ref_end + 1;
	}

	const float score = static_cast<float>(alignment.sw_score);
	struct triplex fullTriplex;
	fullTriplex = triplex(alignment.query_begin + 1, alignment.query_end + 1,
	                      refStart + dnaStartPos, refEnd + dnaStartPos,
	                      strand, Para, rule, nt, score, identity, tri_score,
	                      read_align, ref_align_src, 0, 0, 0, 0, 0, 0, "");
	if (nt >= ntMin)
	{
		triplex_list.push_back(fullTriplex);
	}
}

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src)
{
	// Use this function to get alignment of two sequences.
	int cLoop;
	std::vector<uint32_t> tmpCigar;
	for (cLoop = 0; cLoop < alignment.cigar.size(); cLoop++)
	{
		tmpCigar.push_back(alignment.cigar[cLoop]);
	}
	if (tmpCigar.size() > 0)
	{
		// begin to generate alignment.
		int32_t c = 0, left = 0, e = 0, qb = alignment.ref_begin, pb = alignment.query_begin;//need to CHECK
		uint32_t i;
		uint32_t j;
		while (e < tmpCigar.size() || left > 0)
		{
			int32_t count = 0;
			int32_t q = qb;
			int32_t p = pb;
			//fprintf(stdout, "Target: %8d		", q + 1);
			// DEBUG.
			//e = y + 1;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'I')
					{
						//fprintf(stdout, "-");
						ref_align = ref_align + "-";
						ref_align_src = ref_align_src + '-';
					}
					else
					{
						//fprintf(stdout, "%c", ref_seq[q]);
						ref_align = ref_align + ref_seq[q];
						ref_align_src = ref_align_src + ref_seq_src[q];
						++q;
					}
					++count;
					if (count == 60) goto step2;
				}
			}//for c = e.

		step2:
			//fprintf(stdout, "		%d\n										", q);
			q = qb;
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'M')
						//if (letter == '=')
					{
						if (table[(int)ref_seq[q]] == table[(int)read_seq[p]])
						{
							//fprintf(stdout, "|");
						}
						else
						{
							//fprintf(stdout, "*");
						}
						++q;
						++p;
					}
					else
					{
						//fprintf(stdout, "*");
						if (letter == 'I')
						{
							++p;
						}
						else
						{
							++q;
						}
					}
					++count;
					if (count == 60)
					{
						qb = q;
						goto step3;
					}
				}
			}// for c = e.
		step3:
			p = pb;
			//fprintf(stdout, "\nQuery:	%8d		", p + 1);
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; i++)
				{
					if (letter == 'D')
					{
						//fprintf(stdout, "-");
						read_align = read_align + "-";
					}
					else
					{
						//fprintf(stdout, "%c", read_seq[p]);
						read_align = read_align + read_seq[p];
						++p;
					}
					++count;
					if (count == 60)
					{
						pb = p;
						left = l - i - 1;
						e = (left == 0) ? (c + 1) : c;
						goto end;

					}
				}
			}// for c = e.
			e = c;
			left = 0;
		end:
			//fprintf(stdout, "		%d\n\n", p);
			j = 0;
			//2021-09-16 23:04:55: we don't need to print alignment, we 
			// just need to get alignment sequence.
			//cout << ref_align << " is ref_align" << endl;
			//cout << read_align << " is read_align" << endl;
		}
	}
}
