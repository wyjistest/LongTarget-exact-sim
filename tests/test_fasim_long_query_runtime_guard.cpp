#include "../fasim/long_query_runtime_guard.h"
#include "../fasim/gasal2_align_bridge.h"

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

FasimLongQueryRuntimeGuardRequest valid_request()
{
	FasimLongQueryRuntimeGuardRequest request;
	request.query_length = 4006;
	request.maximum_target_subview_length = 512;
	request.maximum_target_subview_length_known = true;
	request.scoring.match_score = 5;
	request.scoring.mismatch_penalty = 4;
	request.scoring.gap_open = 16;
	request.scoring.gap_extend = 4;
	request.scoring.numeric_path = FASIM_LONG_QUERY_NUMERIC_PATH_WORD16;
	request.device_index = 0;
	request.cuda_built = true;
	request.device_supported = true;
	request.resource_limits_available = true;
	request.default_dynamic_smem_limit_bytes = 49152;
	request.optin_dynamic_smem_limit_bytes = 101376;
	return request;
}

FasimLongQueryRuntimeDescriptor evaluate(
	const FasimLongQueryRuntimeGuardRequest &request, bool expected,
	const std::string &reasonPrefix)
{
	FasimLongQueryRuntimeDescriptor descriptor;
	std::string error;
	const bool actual = fasim_long_query_runtime_preflight(
		request, &descriptor, &error);
	require(actual == expected, "unexpected preflight result: " + error);
	require(descriptor.supported == expected,
		"descriptor support flag mismatch");
	if (expected)
	{
		require(error.empty(), "supported request returned an error");
		require(descriptor.decision == "supported",
			"supported request returned the wrong decision");
	}
	else
	{
		require(error.find(reasonPrefix) == 0,
			"unexpected failure reason: " + error);
		require(descriptor.decision == error,
			"descriptor and error reason diverged");
	}
	return descriptor;
}

}  // namespace

int main()
{
	FasimLongQueryRuntimeGuardRequest request = valid_request();
	FasimLongQueryRuntimeDescriptor descriptor =
		evaluate(request, true, "");
	require(descriptor.segment_length == 126,
		"4006 nt segment length changed");
	require(descriptor.required_dynamic_smem_bytes == 24192,
		"4006 nt shared-memory model changed");
	require(descriptor.maximum_possible_score == 2560,
		"maximum score model changed");
	require(descriptor.scoring_contract_fit &&
		descriptor.numeric_path_fit && descriptor.numeric_fit &&
		descriptor.resource_fit,
		"valid descriptor did not pass every guard layer");

	request = valid_request();
	request.maximum_target_subview_length = 0;
	request.maximum_target_subview_length_known = false;
	FasimLongQueryRuntimeDescriptor queryDescriptor;
	std::string queryError;
	require(fasim_long_query_runtime_preflight(
		request, &queryDescriptor, &queryError),
		"query-only preflight failed: " + queryError);
	require(queryDescriptor.supported &&
		!queryDescriptor.maximum_target_subview_length_known &&
		queryDescriptor.decision ==
			"query_supported_pending_target_subview",
		"query-only descriptor did not preserve its pending target state");
	request.query_length = 16897;
	require(!fasim_long_query_runtime_preflight(
		request, &queryDescriptor, &queryError) &&
		queryError.find("dynamic_shared_memory_limit_exceeded") == 0,
		"empty-output resource overflow must fail at query preflight");

	require(fasim_long_query_runtime_score_fits_int16(254),
		"score 254 must fit WORD16");
	require(fasim_long_query_runtime_score_fits_int16(255),
		"score 255 must fit WORD16");
	require(fasim_long_query_runtime_score_fits_int16(256),
		"score 256 must fit WORD16");
	require(std::string(fasim_long_query_runtime_numeric_path_name(
		FASIM_LONG_QUERY_NUMERIC_PATH_WORD16)) == "WORD16",
		"WORD16 label changed");
	int parsedDevice = -1;
	require(fasim_long_query_runtime_parse_device_index(NULL, &parsedDevice) &&
		parsedDevice == 0, "missing device selector must default to 0");
	require(fasim_long_query_runtime_parse_device_index("0", &parsedDevice) &&
		parsedDevice == 0, "device 0 selector was rejected");
	require(fasim_long_query_runtime_parse_device_index("12", &parsedDevice) &&
		parsedDevice == 12, "valid device selector was rejected");
	require(!fasim_long_query_runtime_parse_device_index("-1", &parsedDevice),
		"negative device selector must fail closed");
	require(!fasim_long_query_runtime_parse_device_index("gpu0", &parsedDevice),
		"nonnumeric device selector must fail closed");
	require(!fasim_long_query_runtime_parse_device_index("1x", &parsedDevice),
		"partially numeric device selector must fail closed");
	require(!fasim_long_query_runtime_parse_device_index("2147483648", &parsedDevice),
		"overflowing device selector must fail closed");
	require(!fasim_long_query_runtime_parse_device_index("0", NULL),
		"missing parsed-device output must fail closed");

	request = valid_request();
	request.query_length = 6553;
	request.maximum_target_subview_length = 6553;
	request.optin_dynamic_smem_limit_bytes = 1000000;
	descriptor = evaluate(request, true, "");
	require(descriptor.maximum_possible_score == 32765,
		"near-INT16 score fixture changed");

	request.query_length = 6554;
	request.maximum_target_subview_length = 6554;
	evaluate(request, false, "int16_score_range_exceeded");

	request = valid_request();
	request.query_length = 32;
	request.maximum_target_subview_length = 32;
	request.default_dynamic_smem_limit_bytes = 192;
	request.optin_dynamic_smem_limit_bytes = 192;
	descriptor = evaluate(request, true, "");
	require(descriptor.required_dynamic_smem_bytes == 192,
		"resource-limit fixture changed");
	request.optin_dynamic_smem_limit_bytes = 191;
	evaluate(request, false, "dynamic_shared_memory_limit_exceeded");

	request = valid_request();
	request.scoring.match_score = 4;
	evaluate(request, false, "unsupported_scoring_contract");
	request = valid_request();
	request.scoring.mismatch_penalty = 3;
	evaluate(request, false, "unsupported_scoring_contract");
	request = valid_request();
	request.scoring.gap_open = 15;
	evaluate(request, false, "unsupported_scoring_contract");
	request = valid_request();
	request.scoring.gap_extend = 3;
	evaluate(request, false, "unsupported_scoring_contract");
	request = valid_request();
	request.scoring.numeric_path = FASIM_LONG_QUERY_NUMERIC_PATH_BYTE8;
	evaluate(request, false, "unsupported_numeric_path");

	request = valid_request();
	request.cuda_built = false;
	evaluate(request, false, "prealign_cuda_not_built");
	request = valid_request();
	request.device_supported = false;
	request.resource_limits_available = false;
	evaluate(request, false, "unsupported_cuda_device");

	request = valid_request();
	request.query_length = 0;
	evaluate(request, false, "invalid_query_length");
	request = valid_request();
	request.query_length =
		fasim_long_query_runtime_query_length_limit() + 1;
	evaluate(request, false, "query_length_exceeds_api_limit");
	request = valid_request();
	request.maximum_target_subview_length = 0;
	evaluate(request, false, "invalid_target_subview_length");
	request = valid_request();
	request.query_length = 10;
	request.maximum_target_subview_length =
		fasim_long_query_runtime_target_subview_length_limit() + 1;
	evaluate(request, false, "target_subview_length_exceeds_api_limit");

	std::string error;
	require(!fasim_long_query_runtime_preflight(request, NULL, &error) &&
		error == "missing_runtime_descriptor",
		"missing descriptor must fail closed");

	FasimGasal2Attempt ownedTarget;
	ownedTarget.target = "ACGT";
	require(ownedTarget.target_view_valid(),
		"owned target storage must remain valid");
	std::string target = "ACGT";
	FasimGasal2Attempt validView;
	validView.set_target_view(&target, 1, 3);
	require(validView.target_view_valid(),
		"bounded target view must remain valid");
	FasimGasal2Attempt malformedView;
	malformedView.set_target_view(&target, 3, 2);
	require(!malformedView.target_view_valid(),
		"out-of-range target view must fail closed");

	std::cout << "ok\n";
	return 0;
}
