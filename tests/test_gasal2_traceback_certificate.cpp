#include "gasal2_traceback_certificate.h"

#include <cstdlib>
#include <iostream>

namespace
{

void require(bool condition, const char *message)
{
	if (!condition)
	{
		std::cerr << message << "\n";
		std::exit(1);
	}
}

}  // namespace

int main()
{
	FasimGasal2TracebackCertificateInput input;
	input.query_length = 100;
	input.target_length = 80;
	input.nt_min_length = 50;
	input.target_start = 20;
	input.score_query_end = 39;
	input.score_ref_end = 49;
	require(fasim_gasal2_traceback_certificate_kind(input) ==
	            FasimGasal2TracebackCertificateKind::None,
	        "valid descriptor must remain uncertified");

	input.score_query_end = 9;
	input.score_ref_end = 29;
	require(fasim_gasal2_traceback_certificate_kind(input) ==
	            FasimGasal2TracebackCertificateKind::ScoreEndpointSpan,
	        "short score endpoint spans must be certified before traceback");

	input.query_length = 10;
	input.target_length = 10;
	input.score_query_end = 9;
	input.score_ref_end = 29;
	require(fasim_gasal2_traceback_certificate_kind(input) ==
	            FasimGasal2TracebackCertificateKind::StaticSpan,
	        "static span proof must take priority over endpoint proof");

	input.exact_descriptor_duplicate = true;
	require(fasim_gasal2_traceback_certificate_kind(input) ==
	            FasimGasal2TracebackCertificateKind::ExactDescriptorDuplicate,
	        "exact duplicate proof must take priority");

	input.exact_descriptor_duplicate = false;
	input.query_length = 100;
	input.target_length = 80;
	input.score_query_end = -1;
	input.score_ref_end = -1;
	require(fasim_gasal2_traceback_certificate_kind(input) ==
	            FasimGasal2TracebackCertificateKind::ScoreEndpointSpan,
	        "missing score endpoints have a zero span upper bound");

	require(fasim_gasal2_traceback_actual_span_is_invalid(-1, -1, -1, -1, 50),
	        "missing traceback endpoints must fail the span contract");
	require(fasim_gasal2_traceback_actual_span_is_invalid(3, 10, 20, 29, 50),
	        "short traceback spans must fail the span contract");
	require(!fasim_gasal2_traceback_actual_span_is_invalid(0, 29, 20, 49, 50),
	        "sufficient traceback spans must remain valid");

	std::cout << "ok\n";
	return 0;
}
