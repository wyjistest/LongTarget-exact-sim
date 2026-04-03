#include "sim_locate_cuda.h"

using namespace std;

bool sim_locate_cuda_is_built()
{
  return false;
}

bool sim_locate_cuda_init(int device,string *errorOut)
{
  (void)device;
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_locate_cuda_locate_region(const SimLocateCudaRequest &request,
                                   SimLocateResult *outResult,
                                   string *errorOut)
{
  (void)request;
  if(outResult != NULL)
  {
    *outResult = SimLocateResult();
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}

bool sim_locate_cuda_locate_region_batch(const vector<SimLocateCudaRequest> &requests,
                                         vector<SimLocateResult> *outResults,
                                         SimLocateCudaBatchResult *batchResult,
                                         string *errorOut)
{
  if(outResults == NULL)
  {
    if(errorOut != NULL)
    {
      *errorOut = "missing output buffers";
    }
    return false;
  }
  outResults->clear();
  if(batchResult != NULL)
  {
    *batchResult = SimLocateCudaBatchResult();
  }
  if(requests.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(errorOut != NULL)
  {
    *errorOut = "CUDA support not built";
  }
  return false;
}
