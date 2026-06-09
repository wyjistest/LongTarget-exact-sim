#include <cstdlib>
#include <iostream>
#include <string>

#include "../fasim/ssw_cpp.h"

namespace
{

void require_alignment_equal(const StripedSmithWaterman::Alignment &expected,
                             const StripedSmithWaterman::Alignment &actual)
{
  if(expected.sw_score != actual.sw_score ||
     expected.sw_score_next_best != actual.sw_score_next_best ||
     expected.ref_begin != actual.ref_begin ||
     expected.ref_end != actual.ref_end ||
     expected.query_begin != actual.query_begin ||
     expected.query_end != actual.query_end ||
     expected.ref_end_next_best != actual.ref_end_next_best ||
     expected.cigar_string != actual.cigar_string ||
     expected.cigar != actual.cigar)
  {
    std::cerr << "alignment mismatch\n"
              << "expected score=" << expected.sw_score
              << " ref=" << expected.ref_begin << "-" << expected.ref_end
              << " query=" << expected.query_begin << "-" << expected.query_end
              << " cigar=" << expected.cigar_string << "\n"
              << "actual   score=" << actual.sw_score
              << " ref=" << actual.ref_begin << "-" << actual.ref_end
              << " query=" << actual.query_begin << "-" << actual.query_end
              << " cigar=" << actual.cigar_string << "\n";
    std::exit(1);
  }
}

StripedSmithWaterman::Alignment run_align(const std::string &query,
                                          const std::string &target)
{
  StripedSmithWaterman::Aligner aligner;
  StripedSmithWaterman::Filter filter;
  StripedSmithWaterman::Alignment alignment;
  if(!aligner.Align(query.c_str(), target.c_str(), static_cast<int>(target.size()), filter, &alignment, 15))
  {
    std::cerr << "Align returned false\n";
    std::exit(1);
  }
  return alignment;
}

} // namespace

int main()
{
  const std::string query = "ACGTACGTACGTACGTACGTACGT";
  const std::string target = "TTTTACGTACGTTCGTACGTACGTGGGG";

  StripedSmithWaterman::Alignment first = run_align(query, target);
  StripedSmithWaterman::Alignment second = run_align(query, target);
  require_alignment_equal(first, second);

  const std::string target_with_indel = "ACGTACGTTTACGTACGT";
  StripedSmithWaterman::Alignment third = run_align(query, target_with_indel);
  StripedSmithWaterman::Alignment fourth = run_align(query, target_with_indel);
  require_alignment_equal(third, fourth);

  return 0;
}
