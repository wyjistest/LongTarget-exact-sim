#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "../fasim/rules.h"

namespace
{

void require_equal(const std::string &label,
                   const std::string &expected,
                   const std::string &actual)
{
  if(expected != actual)
  {
    std::cerr << label << " mismatch\n"
              << "expected: " << expected << "\n"
              << "actual:   " << actual << "\n";
    std::exit(1);
  }
}

void check_table_matches_legacy_for_all_modes()
{
  const std::vector<std::string> inputs = {
    "ATGCN",
    "NNNNN",
    "GATTACANNNCCGGTTAA",
    "atgcnxyz"
  };

  for(size_t i = 0; i < inputs.size(); ++i)
  {
    const std::string &seq = inputs[i];
    for(int rule = 1; rule <= 6; ++rule)
    {
      require_equal("parallel forward rule " + std::to_string(rule),
                    transferString(seq, 0, 1, rule),
                    transferStringTableDriven(seq, 0, 1, rule));
      require_equal("parallel reverse rule " + std::to_string(rule),
                    transferString(seq, 1, 1, rule),
                    transferStringTableDriven(seq, 1, 1, rule));
    }

    for(int rule = 1; rule <= 18; ++rule)
    {
      require_equal("antiparallel forward rule " + std::to_string(rule),
                    transferString(seq, 0, -1, rule),
                    transferStringTableDriven(seq, 0, -1, rule));
      require_equal("antiparallel reverse rule " + std::to_string(rule),
                    transferString(seq, 1, -1, rule),
                    transferStringTableDriven(seq, 1, -1, rule));
    }
  }
}

void check_opt_in_defaults_to_legacy()
{
  unsetenv("FASIM_TRANSFERSTRING_TABLE");
  const std::string seq = "ACGTNXacgtnx";
  require_equal("default opt-in path",
                transferString(seq, 0, 1, 1),
                transferStringTableOptIn(seq, 0, 1, 1));
}

void check_lowercase_inputs_are_normalized()
{
  const std::string seq = "ACGTNacgtnx";
  const std::string expected = "TTGGNTTGGNN";
  require_equal("legacy lowercase normalization",
                expected,
                transferString(seq, 0, 1, 1));
  require_equal("table lowercase normalization",
                expected,
                transferStringTableDriven(seq, 0, 1, 1));

  std::string src = seq;
  complement(src);
  require_equal("complement lowercase normalization",
                "TGCANTGCAN",
                src);
}

} // namespace

int main()
{
  check_table_matches_legacy_for_all_modes();
  check_opt_in_defaults_to_legacy();
  check_lowercase_inputs_are_normalized();
  return 0;
}
