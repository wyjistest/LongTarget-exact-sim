#include "../cuda/prealign_cuda.h"
#include "../fasim/long_query_runtime_guard.h"

#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>

namespace
{

void require(bool condition, const std::string &message)
{
	if (!condition)
	{
		std::cerr << message << "\n";
		std::exit(1);
	}
}

FasimLongQueryRuntimeGuardRequest request_for(
	uint64_t queryLength, const PreAlignCudaResourceLimits &limits)
{
	FasimLongQueryRuntimeGuardRequest request;
	request.query_length = queryLength;
	request.maximum_target_subview_length = 1;
	request.maximum_target_subview_length_known = true;
	request.scoring.match_score = 5;
	request.scoring.mismatch_penalty = 4;
	request.scoring.gap_open = 16;
	request.scoring.gap_extend = 4;
	request.scoring.numeric_path = FASIM_LONG_QUERY_NUMERIC_PATH_WORD16;
	request.device_index = 0;
	request.cuda_built = prealign_cuda_is_built();
	request.device_supported = true;
	request.resource_limits_available = true;
	request.default_dynamic_smem_limit_bytes =
		static_cast<uint64_t>(limits.defaultDynamicSmemLimitBytes);
	request.optin_dynamic_smem_limit_bytes =
		static_cast<uint64_t>(limits.optinDynamicSmemLimitBytes);
	return request;
}

}  // namespace

int main()
{
	std::string error;
	require(prealign_cuda_init(0, &error),
		"CUDA device 0 unavailable: " + error);

	PreAlignCudaQueryHandle probe;
	probe.device = 0;
	probe.queryLength = 1;
	probe.segLen = 1;
	PreAlignCudaResourceLimits limits;
	require(prealign_cuda_query_resource_limits(probe, &limits, &error),
		"resource query failed: " + error);
	require(limits.optinDynamicSmemLimitBytes >= 192,
		"device opt-in shared-memory limit is below one segment");

	const uint64_t bytesPerSegment = 3u * 32u * sizeof(int16_t);
	const uint64_t maximumSegments =
		static_cast<uint64_t>(limits.optinDynamicSmemLimitBytes) /
		bytesPerSegment;
	const uint64_t maximumResourceFitQuery = maximumSegments * 32u;

	FasimLongQueryRuntimeDescriptor descriptor;
	FasimLongQueryRuntimeGuardRequest request =
		request_for(maximumResourceFitQuery, limits);
	require(fasim_long_query_runtime_preflight(
		request, &descriptor, &error),
		"device-derived resource limit must fit: " + error);
	require(descriptor.required_dynamic_smem_bytes <=
		descriptor.optin_dynamic_smem_limit_bytes,
		"fit descriptor exceeded the device limit");

	request.query_length = maximumResourceFitQuery + 1;
	require(!fasim_long_query_runtime_preflight(
		request, &descriptor, &error),
		"resource limit + 1 query must fail closed");
	require(error.find("dynamic_shared_memory_limit_exceeded") == 0,
		"unexpected resource overflow reason: " + error);

	PreAlignCudaQueryHandle invalidDeviceProbe = probe;
	invalidDeviceProbe.device = std::numeric_limits<int>::max();
	require(!prealign_cuda_query_resource_limits(
		invalidDeviceProbe, &limits, &error),
		"unsupported device index must fail closed");

	std::cout << "device=0"
	          << " default_smem=" << request.default_dynamic_smem_limit_bytes
	          << " optin_smem=" << request.optin_dynamic_smem_limit_bytes
	          << " maximum_resource_fit_query=" << maximumResourceFitQuery
	          << "\n";
	return 0;
}
