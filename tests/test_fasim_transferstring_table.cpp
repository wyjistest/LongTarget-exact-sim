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

bool env_enabled(const char *name)
{
  const char *value = std::getenv(name);
  return value != NULL && value[0] != '\0' && value[0] != '0';
}

void check_runtime_selection()
{
  const char *explicitValue = std::getenv("FASIM_TRANSFERSTRING_TABLE");
  const bool expected = explicitValue != NULL && explicitValue[0] != '\0' ?
      explicitValue[0] != '0' :
      env_enabled("FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER") ||
      env_enabled("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
  if(fasim_transfer_string_table_requested_runtime() != expected)
  {
    std::cerr << "runtime table selection mismatch\n";
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

void check_runtime_dispatch_matches_legacy()
{
  const std::string seq = "ACGTNXacgtnx";
  require_equal("runtime dispatch",
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
  check_runtime_selection();
  check_table_matches_legacy_for_all_modes();
  check_runtime_dispatch_matches_legacy();
  check_lowercase_inputs_are_normalized();
  return 0;
}
