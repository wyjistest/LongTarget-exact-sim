#ifndef FASIM_GASAL2_TRACEBACK_CERTIFICATE_H
#define FASIM_GASAL2_TRACEBACK_CERTIFICATE_H

#include <cstddef>
#include <cstdint>

enum class FasimGasal2TracebackCertificateKind
{
	None,
	ExactDescriptorDuplicate,
	StaticSpan,
	ScoreEndpointSpan
};

struct FasimGasal2TracebackCertificateInput
{
	FasimGasal2TracebackCertificateInput() :
		query_length(0),
		target_length(0),
		nt_min_length(0),
		target_start(0),
		score_query_end(-1),
		score_ref_end(-1),
		exact_descriptor_duplicate(false)
	{
	}

	std::size_t query_length;
	std::size_t target_length;
	int nt_min_length;
	int target_start;
	int score_query_end;
	int score_ref_end;
	bool exact_descriptor_duplicate;
};

static inline bool fasim_gasal2_span_sum_below_minimum(std::size_t first,
	                                                   std::size_t second,
	                                                   int minimum)
{
	if (minimum <= 0)
	{
		return false;
	}
	const std::size_t required = static_cast<std::size_t>(minimum);
	return first < required && second < required - first;
}

static inline std::size_t fasim_gasal2_nonnegative_endpoint_span(int begin,
	                                                             int end)
{
	if (begin < 0 || end < begin)
	{
		return 0;
	}
	return static_cast<std::size_t>(
		static_cast<int64_t>(end) - static_cast<int64_t>(begin) + 1);
}

static inline FasimGasal2TracebackCertificateKind
fasim_gasal2_traceback_certificate_kind(
	const FasimGasal2TracebackCertificateInput &input)
{
	if (input.exact_descriptor_duplicate)
	{
		return FasimGasal2TracebackCertificateKind::ExactDescriptorDuplicate;
	}
	if (fasim_gasal2_span_sum_below_minimum(input.query_length,
	                                        input.target_length,
	                                        input.nt_min_length))
	{
		return FasimGasal2TracebackCertificateKind::StaticSpan;
	}
	const std::size_t querySpan =
		fasim_gasal2_nonnegative_endpoint_span(0, input.score_query_end);
	const std::size_t targetSpan =
		fasim_gasal2_nonnegative_endpoint_span(input.target_start,
		                                      input.score_ref_end);
	if (fasim_gasal2_span_sum_below_minimum(querySpan,
	                                        targetSpan,
	                                        input.nt_min_length))
	{
		return FasimGasal2TracebackCertificateKind::ScoreEndpointSpan;
	}
	return FasimGasal2TracebackCertificateKind::None;
}

static inline bool fasim_gasal2_traceback_actual_span_is_invalid(
	int queryBegin,
	int queryEnd,
	int targetBegin,
	int targetEnd,
	int ntMinimum)
{
	return fasim_gasal2_span_sum_below_minimum(
		fasim_gasal2_nonnegative_endpoint_span(queryBegin, queryEnd),
		fasim_gasal2_nonnegative_endpoint_span(targetBegin, targetEnd),
		ntMinimum);
}

#endif
