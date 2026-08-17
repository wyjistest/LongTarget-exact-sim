#include "long_query_runtime_guard.h"

#include <algorithm>
#include <limits>
#include <sstream>

namespace
{

const int kMatchScore = 5;
const int kMismatchPenalty = 4;
const int kGapOpen = 16;
const int kGapExtend = 4;
const uint64_t kWarpWidth = 32;
const uint64_t kStatePlanes = 3;

bool reject(FasimLongQueryRuntimeDescriptor *descriptor,
	const std::string &reason, std::string *errorOut)
{
	descriptor->supported = false;
	descriptor->decision = reason;
	if (errorOut != NULL)
	{
		*errorOut = reason;
	}
	return false;
}

uint64_t required_dynamic_smem(uint64_t queryLength)
{
	if (queryLength > std::numeric_limits<uint64_t>::max() -
		(kWarpWidth - 1))
	{
		return std::numeric_limits<uint64_t>::max();
	}
	const uint64_t segmentLength =
		(queryLength + kWarpWidth - 1) / kWarpWidth;
	const uint64_t bytesPerSegment =
		kStatePlanes * kWarpWidth * sizeof(int16_t);
	if (segmentLength >
		std::numeric_limits<uint64_t>::max() / bytesPerSegment)
	{
		return std::numeric_limits<uint64_t>::max();
	}
	return segmentLength * bytesPerSegment;
}

}  // namespace

uint64_t fasim_long_query_runtime_query_length_limit()
{
	return static_cast<uint64_t>(std::numeric_limits<int>::max());
}

uint64_t fasim_long_query_runtime_target_subview_length_limit()
{
	return static_cast<uint64_t>(std::numeric_limits<int>::max());
}

uint64_t fasim_long_query_runtime_int16_score_limit()
{
	return static_cast<uint64_t>(std::numeric_limits<int16_t>::max());
}

bool fasim_long_query_runtime_score_fits_int16(uint64_t score)
{
	return score <= fasim_long_query_runtime_int16_score_limit();
}

const char *fasim_long_query_runtime_numeric_path_name(int numericPath)
{
	switch (numericPath)
	{
	case FASIM_LONG_QUERY_NUMERIC_PATH_BYTE8:
		return "BYTE8";
	case FASIM_LONG_QUERY_NUMERIC_PATH_WORD16:
		return "WORD16";
	default:
		return "UNKNOWN";
	}
}

bool fasim_long_query_runtime_preflight(
	const FasimLongQueryRuntimeGuardRequest &request,
	FasimLongQueryRuntimeDescriptor *descriptorOut,
	std::string *errorOut)
{
	if (errorOut != NULL)
	{
		errorOut->clear();
	}
	if (descriptorOut == NULL)
	{
		if (errorOut != NULL)
		{
			*errorOut = "missing_runtime_descriptor";
		}
		return false;
	}

	*descriptorOut = FasimLongQueryRuntimeDescriptor();
	FasimLongQueryRuntimeDescriptor &descriptor = *descriptorOut;
	descriptor.query_length = request.query_length;
	descriptor.maximum_target_subview_length =
		request.maximum_target_subview_length;
	descriptor.maximum_target_subview_length_known =
		request.maximum_target_subview_length_known;
	descriptor.query_length_limit =
		fasim_long_query_runtime_query_length_limit();
	descriptor.target_subview_length_limit =
		fasim_long_query_runtime_target_subview_length_limit();
	descriptor.scoring = request.scoring;
	descriptor.device_index = request.device_index;
	descriptor.cuda_built = request.cuda_built;
	descriptor.device_supported = request.device_supported;
	descriptor.resource_limits_available =
		request.resource_limits_available;
	descriptor.default_dynamic_smem_limit_bytes =
		request.default_dynamic_smem_limit_bytes;
	descriptor.optin_dynamic_smem_limit_bytes =
		request.optin_dynamic_smem_limit_bytes;
	descriptor.query_length_fit =
		request.query_length > 0 &&
		request.query_length <= descriptor.query_length_limit;
	descriptor.target_subview_length_fit =
		request.maximum_target_subview_length_known &&
		request.maximum_target_subview_length > 0 &&
		request.maximum_target_subview_length <=
			descriptor.target_subview_length_limit;
	descriptor.scoring_contract_fit =
		request.scoring.match_score == kMatchScore &&
		request.scoring.mismatch_penalty == kMismatchPenalty &&
		request.scoring.gap_open == kGapOpen &&
		request.scoring.gap_extend == kGapExtend;
	descriptor.numeric_path_fit =
		request.scoring.numeric_path ==
			FASIM_LONG_QUERY_NUMERIC_PATH_WORD16;

	if (request.query_length > 0 &&
		request.query_length <=
			std::numeric_limits<uint64_t>::max() - (kWarpWidth - 1))
	{
		descriptor.segment_length =
			(request.query_length + kWarpWidth - 1) / kWarpWidth;
	}
	descriptor.required_dynamic_smem_bytes =
		required_dynamic_smem(request.query_length);
	if (request.maximum_target_subview_length_known)
	{
		const uint64_t alignmentSpan = std::min(
			request.query_length, request.maximum_target_subview_length);
		if (alignmentSpan >
			std::numeric_limits<uint64_t>::max() /
				static_cast<uint64_t>(kMatchScore))
		{
			descriptor.maximum_possible_score =
				std::numeric_limits<uint64_t>::max();
		}
		else
		{
			descriptor.maximum_possible_score =
				alignmentSpan * static_cast<uint64_t>(kMatchScore);
		}
		descriptor.numeric_fit = fasim_long_query_runtime_score_fits_int16(
			descriptor.maximum_possible_score);
	}
	descriptor.resource_fit =
		request.cuda_built && request.device_supported &&
		request.resource_limits_available &&
		descriptor.required_dynamic_smem_bytes <=
			request.optin_dynamic_smem_limit_bytes;

	if (!request.cuda_built)
	{
		return reject(&descriptor, "prealign_cuda_not_built", errorOut);
	}
	if (request.query_length == 0)
	{
		return reject(&descriptor, "invalid_query_length", errorOut);
	}
	if (!descriptor.query_length_fit)
	{
		return reject(&descriptor,
			"query_length_exceeds_api_limit", errorOut);
	}
	if (request.maximum_target_subview_length_known &&
		request.maximum_target_subview_length == 0)
	{
		return reject(&descriptor,
			"invalid_target_subview_length", errorOut);
	}
	if (request.maximum_target_subview_length_known &&
		!descriptor.target_subview_length_fit)
	{
		return reject(&descriptor,
			"target_subview_length_exceeds_api_limit", errorOut);
	}
	if (!descriptor.scoring_contract_fit)
	{
		std::ostringstream reason;
		reason << "unsupported_scoring_contract"
		       << ":expected=5,4,16,4"
		       << ":actual=" << request.scoring.match_score << ','
		       << request.scoring.mismatch_penalty << ','
		       << request.scoring.gap_open << ','
		       << request.scoring.gap_extend;
		return reject(&descriptor, reason.str(), errorOut);
	}
	if (!descriptor.numeric_path_fit)
	{
		std::ostringstream reason;
		reason << "unsupported_numeric_path:expected=WORD16:actual="
		       << fasim_long_query_runtime_numeric_path_name(
				request.scoring.numeric_path);
		return reject(&descriptor, reason.str(), errorOut);
	}
	if (request.maximum_target_subview_length_known &&
		!descriptor.numeric_fit)
	{
		std::ostringstream reason;
		reason << "int16_score_range_exceeded:max_score="
		       << descriptor.maximum_possible_score
		       << ":limit=" << fasim_long_query_runtime_int16_score_limit();
		return reject(&descriptor, reason.str(), errorOut);
	}
	if (!request.device_supported ||
		!request.resource_limits_available)
	{
		return reject(&descriptor, "unsupported_cuda_device", errorOut);
	}
	if (!descriptor.resource_fit)
	{
		std::ostringstream reason;
		reason << "dynamic_shared_memory_limit_exceeded:required="
		       << descriptor.required_dynamic_smem_bytes
		       << ":optin_limit="
		       << descriptor.optin_dynamic_smem_limit_bytes;
		return reject(&descriptor, reason.str(), errorOut);
	}

	descriptor.supported = true;
	descriptor.decision = request.maximum_target_subview_length_known ?
		"supported" : "query_supported_pending_target_subview";
	return true;
}
