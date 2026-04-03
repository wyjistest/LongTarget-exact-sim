#ifndef LONGTARGET_SIM_CUDA_RUNTIME_H
#define LONGTARGET_SIM_CUDA_RUNTIME_H

#include <cstdlib>
#include <limits>
#include <vector>

struct SimCudaWorkerAssignment
{
  SimCudaWorkerAssignment():device(0),slot(0) {}
  SimCudaWorkerAssignment(int n1,int n2):device(n1),slot(n2) {}

  int device;
  int slot;
};

inline int &simCudaDeviceOverrideRuntime()
{
  static thread_local int overrideDevice = std::numeric_limits<int>::min();
  return overrideDevice;
}

inline int simCudaDeviceRuntime()
{
  const int overrideDevice = simCudaDeviceOverrideRuntime();
  if(overrideDevice != std::numeric_limits<int>::min())
  {
    return overrideDevice;
  }
  const char *env = getenv("LONGTARGET_CUDA_DEVICE");
  if(env == NULL || env[0] == '\0')
  {
    return -1;
  }
  return atoi(env);
}

inline void sim_set_cuda_device_override(int device)
{
  simCudaDeviceOverrideRuntime() = device;
}

inline void sim_clear_cuda_device_override()
{
  simCudaDeviceOverrideRuntime() = std::numeric_limits<int>::min();
}

inline int &simCudaWorkerSlotOverrideRuntime()
{
  static thread_local int overrideSlot = std::numeric_limits<int>::min();
  return overrideSlot;
}

inline int simCudaWorkerSlotRuntime()
{
  const int overrideSlot = simCudaWorkerSlotOverrideRuntime();
  if(overrideSlot != std::numeric_limits<int>::min())
  {
    return overrideSlot;
  }
  return 0;
}

inline void sim_set_cuda_worker_slot_override(int slot)
{
  simCudaWorkerSlotOverrideRuntime() = slot > 0 ? slot : 0;
}

inline void sim_clear_cuda_worker_slot_override()
{
  simCudaWorkerSlotOverrideRuntime() = std::numeric_limits<int>::min();
}

inline int simCudaWorkersPerDeviceRuntime()
{
  static const int workersPerDevice = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_WORKERS_PER_DEVICE");
    if(env == NULL || env[0] == '\0')
    {
      return 1;
    }
    char *end = NULL;
    const long parsed = strtol(env,&end,10);
    if(end == env || parsed <= 0)
    {
      return 1;
    }
    if(parsed > 64)
    {
      return 64;
    }
    return static_cast<int>(parsed);
  }();
  return workersPerDevice;
}

inline std::vector<SimCudaWorkerAssignment> simBuildCudaWorkerAssignments(const std::vector<int> &devices,
                                                                          int workersPerDevice)
{
  if(workersPerDevice <= 0)
  {
    workersPerDevice = 1;
  }
  std::vector<SimCudaWorkerAssignment> assignments;
  assignments.reserve(devices.size() * static_cast<size_t>(workersPerDevice));
  for(size_t deviceIndex = 0; deviceIndex < devices.size(); ++deviceIndex)
  {
    for(int slot = 0; slot < workersPerDevice; ++slot)
    {
      assignments.push_back(SimCudaWorkerAssignment(devices[deviceIndex],slot));
    }
  }
  return assignments;
}

#endif
