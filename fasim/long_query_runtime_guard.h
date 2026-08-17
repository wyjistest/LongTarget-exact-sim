#ifndef FASIM_LONG_QUERY_RUNTIME_GUARD_H
#define FASIM_LONG_QUERY_RUNTIME_GUARD_H

#include <cstdint>
#include <string>

enum FasimLongQueryNumericPath
{
	FASIM_LONG_QUERY_NUMERIC_PATH_UNKNOWN = 0,
	FASIM_LONG_QUERY_NUMERIC_PATH_BYTE8 = 1,
	FASIM_LONG_QUERY_NUMERIC_PATH_WORD16 = 2
};

struct FasimLongQueryScoringContract
{
	FasimLongQueryScoringContract() :
		match_score(0),
		mismatch_penalty(0),
		gap_open(0),
		gap_extend(0),
		numeric_path(FASIM_LONG_QUERY_NUMERIC_PATH_UNKNOWN)
	{
	}

	int match_score;
	int mismatch_penalty;
	int gap_open;
	int gap_extend;
	int numeric_path;
};

struct FasimLongQueryRuntimeGuardRequest
{
	FasimLongQueryRuntimeGuardRequest() :
		query_length(0),
		maximum_target_subview_length(0),
		maximum_target_subview_length_known(false),
		device_index(-1),
		cuda_built(false),
		device_supported(false),
		resource_limits_available(false),
		default_dynamic_smem_limit_bytes(0),
		optin_dynamic_smem_limit_bytes(0)
	{
	}

	uint64_t query_length;
	uint64_t maximum_target_subview_length;
	bool maximum_target_subview_length_known;
	FasimLongQueryScoringContract scoring;
	int device_index;
	bool cuda_built;
	bool device_supported;
	bool resource_limits_available;
	uint64_t default_dynamic_smem_limit_bytes;
	uint64_t optin_dynamic_smem_limit_bytes;
};

struct FasimLongQueryRuntimeDescriptor
{
	FasimLongQueryRuntimeDescriptor() :
		query_length(0),
		maximum_target_subview_length(0),
		maximum_target_subview_length_known(false),
		query_length_limit(0),
		target_subview_length_limit(0),
		segment_length(0),
		maximum_possible_score(0),
		required_dynamic_smem_bytes(0),
		default_dynamic_smem_limit_bytes(0),
		optin_dynamic_smem_limit_bytes(0),
		device_index(-1),
		cuda_built(false),
		device_supported(false),
		resource_limits_available(false),
		query_length_fit(false),
		target_subview_length_fit(false),
		scoring_contract_fit(false),
		numeric_path_fit(false),
		numeric_fit(false),
		resource_fit(false),
		supported(false),
		decision("not_evaluated")
	{
	}

	uint64_t query_length;
	uint64_t maximum_target_subview_length;
	bool maximum_target_subview_length_known;
	uint64_t query_length_limit;
	uint64_t target_subview_length_limit;
	uint64_t segment_length;
	uint64_t maximum_possible_score;
	uint64_t required_dynamic_smem_bytes;
	uint64_t default_dynamic_smem_limit_bytes;
	uint64_t optin_dynamic_smem_limit_bytes;
	FasimLongQueryScoringContract scoring;
	int device_index;
	bool cuda_built;
	bool device_supported;
	bool resource_limits_available;
	bool query_length_fit;
	bool target_subview_length_fit;
	bool scoring_contract_fit;
	bool numeric_path_fit;
	bool numeric_fit;
	bool resource_fit;
	bool supported;
	std::string decision;
};

uint64_t fasim_long_query_runtime_query_length_limit();
uint64_t fasim_long_query_runtime_target_subview_length_limit();
uint64_t fasim_long_query_runtime_int16_score_limit();
bool fasim_long_query_runtime_score_fits_int16(uint64_t score);
const char *fasim_long_query_runtime_numeric_path_name(int numericPath);
bool fasim_long_query_runtime_parse_device_index(
	const char *value, int *deviceIndexOut);

bool fasim_long_query_runtime_preflight(
	const FasimLongQueryRuntimeGuardRequest &request,
	FasimLongQueryRuntimeDescriptor *descriptorOut,
	std::string *errorOut);

#endif
