#include "parasail_shadow.h"

bool parasail_shadow_is_built()
{
  return false;
}

bool parasail_shadow_run_local_ssw(
  const std::vector<ParasailShadowRequest> &requests,
  std::vector<ParasailShadowResult> *outResults,
  ParasailShadowBatchResult *batchResult,
  std::string *errorOut)
{
  (void)requests;
  if (outResults != NULL)
  {
    outResults->clear();
  }
  if (batchResult != NULL)
  {
    *batchResult = ParasailShadowBatchResult();
  }
  if (errorOut != NULL)
  {
    *errorOut = "Parasail support not built";
  }
  return false;
}
