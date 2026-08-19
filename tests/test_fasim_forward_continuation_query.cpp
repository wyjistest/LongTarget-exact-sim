#include <cstdlib>
#include <iostream>
#include <string>

#include "../fasim/ssw_cpp.h"

namespace
{

void require(bool condition, const char* message)
{
	if (!condition)
	{
		std::cerr << message << '\n';
		std::exit(1);
	}
}

void require_equal(const StripedSmithWaterman::Alignment& expected,
	const StripedSmithWaterman::Alignment& actual)
{
	require(expected.sw_score == actual.sw_score, "score mismatch");
	require(expected.sw_score_next_best == actual.sw_score_next_best,
		"second score mismatch");
	require(expected.ref_begin == actual.ref_begin, "ref begin mismatch");
	require(expected.ref_end == actual.ref_end, "ref end mismatch");
	require(expected.query_begin == actual.query_begin, "query begin mismatch");
	require(expected.query_end == actual.query_end, "query end mismatch");
	require(expected.ref_end_next_best == actual.ref_end_next_best,
		"second ref end mismatch");
	require(expected.cigar_string == actual.cigar_string, "CIGAR string mismatch");
	require(expected.cigar == actual.cigar, "CIGAR mismatch");
}

void require_primary_equal(const StripedSmithWaterman::Alignment& expected,
	const StripedSmithWaterman::Alignment& actual)
{
	require(expected.sw_score == actual.sw_score, "primary score mismatch");
	require(expected.ref_begin == actual.ref_begin, "primary ref begin mismatch");
	require(expected.ref_end == actual.ref_end, "primary ref end mismatch");
	require(expected.query_begin == actual.query_begin,
		"primary query begin mismatch");
	require(expected.query_end == actual.query_end, "primary query end mismatch");
	require(expected.cigar_string == actual.cigar_string,
		"primary CIGAR string mismatch");
	require(expected.cigar == actual.cigar, "primary CIGAR mismatch");
}

} // namespace

int main()
{
	const std::string query(80, 'A');
	const std::string target = std::string("CCCC") + query + "GGGG";
	StripedSmithWaterman::Aligner aligner(5, 4, 16, 4);
	StripedSmithWaterman::Filter filter;
	StripedSmithWaterman::Alignment authority;
	require(aligner.Align(query.c_str(), target.c_str(),
		static_cast<int>(target.size()), filter, &authority, 40),
		"authority alignment failed");

	StripedSmithWaterman::ForwardEndpoint endpoint;
	endpoint.score1 = authority.sw_score;
	endpoint.score2 = 0;
	endpoint.ref_end1 = authority.ref_end;
	endpoint.query_end1 = authority.query_end;
	endpoint.ref_end2 = -1;
	endpoint.numeric_path = 2;

	StripedSmithWaterman::ForwardContinuationQuery prepared;
	require(aligner.PrepareForwardContinuationQuery(query.c_str(), &prepared),
		"prepared query build failed");
	require(prepared.ready(), "prepared query not ready");

	StripedSmithWaterman::ForwardContinuationProfileStats before =
		StripedSmithWaterman::ForwardContinuationProfileSnapshot();
	StripedSmithWaterman::ForwardContinuationProfileSetEnabled(true);
	StripedSmithWaterman::Alignment legacy;
	StripedSmithWaterman::Alignment reused;
	require(aligner.AlignFromForward(query.c_str(), target.c_str(),
		static_cast<int>(target.size()), filter, endpoint, &legacy, 40),
		"legacy continuation failed");
	require(aligner.AlignFromForward(prepared, target.c_str(),
		static_cast<int>(target.size()), filter, endpoint, &reused, 40),
		"prepared continuation failed");
	StripedSmithWaterman::ForwardContinuationProfileSetEnabled(false);
	StripedSmithWaterman::ForwardContinuationProfileStats after =
		StripedSmithWaterman::ForwardContinuationProfileSnapshot();

	require_primary_equal(authority, legacy);
	require_equal(legacy, reused);
	require(after.calls - before.calls == 2, "profile call accounting mismatch");
	require(after.query_bytes - before.query_bytes == query.size(),
		"prepared query was translated per call");
	require(after.ref_bytes - before.ref_bytes == 2 * target.size(),
		"reference byte accounting mismatch");

	StripedSmithWaterman::Aligner other(5, 4, 16, 4);
	StripedSmithWaterman::Alignment rejected;
	require(!other.AlignFromForward(prepared, target.c_str(),
		static_cast<int>(target.size()), filter, endpoint, &rejected, 40),
		"prepared query owner guard failed");
	return 0;
}
