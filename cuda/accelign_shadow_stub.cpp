#include "accelign_shadow.h"

bool accelign_shadow_is_built()
{
  return false;
}

bool accelign_shadow_init(int device, std::string *errorOut)
{
  (void)device;
  if (errorOut != NULL)
  {
    *errorOut = "Accelign support not built";
  }
  return false;
}

bool accelign_shadow_run_local_affine_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  (void)requests;
  if (outResults != NULL)
  {
    outResults->clear();
  }
  if (batchResult != NULL)
  {
    *batchResult = AccelignShadowBatchResult();
  }
  if (errorOut != NULL)
  {
    *errorOut = "Accelign support not built";
  }
  return false;
}

bool accelign_shadow_run_local_affine_score_only_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  return accelign_shadow_run_local_affine_float(requests,
                                                outResults,
                                                batchResult,
                                                errorOut);
}

bool accelign_shadow_run_local_affine_score_only_one_to_all_float(
  const std::vector<AccelignShadowRequest> &requests,
  std::vector<AccelignShadowResult> *outResults,
  AccelignShadowBatchResult *batchResult,
  std::string *errorOut)
{
  return accelign_shadow_run_local_affine_float(requests,
                                                outResults,
                                                batchResult,
                                                errorOut);
}
