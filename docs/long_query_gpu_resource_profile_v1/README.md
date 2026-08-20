# Long-query GPU resource profile preparation v1

## Scope

This checkpoint performs static preparation only. It does not run a CUDA
kernel, change a production runtime, or modify the active full-concat shadow.
It prepares the next independent Nsight Compute epoch for main scoreInfo and
F1 Round 0.

## Model correction

The initial `be506be` receipt incorrectly applied the F1
`ceil(query_length / 16) * 16` workspace formula to the main scoreInfo kernel.
The main kernel launch actually allocates each state buffer as
`ceil(query_length / 32) * 16` elements. The corrected values below are bound
to the host launch expression and replace the main residency values in
`be506be`; that earlier receipt must not be used for resource decisions.

## Tool correction

Nsight Compute is installed but was not on `PATH` during the prior profiling
epoch:

```text
path     /opt/nvidia/nsight-compute/2024.2.1/ncu
version  2024.2.1.0 (build 34372528)
```

The older `long_query_f1_round_profile_v1` receipt remains immutable. Its
statement that Nsight Compute was unavailable describes the old discovery
result; it is corrected here rather than rewriting that frozen receipt.

Hardware performance counters are currently restricted by the NVIDIA driver:

```text
RmProfilingAdminOnly = 1
passwordless sudo    = no
```

The profile runner therefore fails closed before execution for the current
unprivileged account. After the active full-concat gate, the profiling epoch
requires either an administrator-authorized counter configuration or an
interactive privileged run. This checkpoint does not change the driver.

## Static kernel resources

`cuda/prealign_cuda.cu` was compiled offline for `sm_89` with CUDA 12.5.82 and
`-Xptxas=-v`. This object is a resource probe, not a runtime candidate.

| Kernel | Registers/thread | Stack | Spills |
| --- | ---: | ---: | ---: |
| main scoreInfo byte column maximum | 26 | 0 | 0 |
| F1 forward byte | 38 | 0 | 0 |
| F1 reverse byte | 40 | 0 | 0 |
| uint8 min-score | 32 | 0 | 0 |

The RTX 4090 device limits were queried without launching a kernel:

```text
SM count                         128
shared memory / SM          102,400 B
default shared / block       49,152 B
opt-in shared / block       101,376 B
maximum threads / SM           1,536
maximum blocks / SM                24
warp size                           32
```

Registers do not limit either target kernel at its 32-thread launch geometry.
Dynamic shared memory is the first static residency limit.

## Residency model

The current main scoreInfo kernel stores three `int16_t` byte-state arrays.
The current F1 forward kernel already stores three `uint8_t` arrays. Predicted
resident blocks per SM are:

| Query | Main current shared / blocks | Main uint8 three-state shared / blocks | Main uint8 two-state shared / blocks | F1 current shared / blocks | F1 two-state shared / blocks |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 8,000 | 24,000 B / 4 | 12,000 B / 8 | 8,000 B / 12 | 24,000 B / 4 | 16,000 B / 6 |
| 11,498 | 34,560 B / 2 | 17,280 B / 5 | 11,520 B / 8 | 34,512 B / 2 | 23,008 B / 4 |
| 12,397 | 37,248 B / 2 | 18,624 B / 5 | 12,416 B / 8 | 37,200 B / 2 | 24,800 B / 4 |

These are resource ceilings, not speedup predictions. Runtime occupancy can be
lower, and more resident blocks help only if the kernel has enough ready work
and is latency- or occupancy-limited.

## Candidate boundaries

### Main scoreInfo

The first bounded design candidate is exact `uint8_t` state for the existing
byte recurrence. Merely changing three state arrays from `int16_t` to `uint8_t`
halves the shared footprint. A second, higher-risk candidate would prove that
the two alternating H arrays can be represented by one in-place H state,
reducing the current footprint by two thirds.

This authorizes Nsight profiling and dependency proof work only. No kernel is
authorized until runtime metrics confirm shared-memory residency or memory
dependency stalls, and the candidate still requires byte-identical scoreInfo
and complete output.

### F1 Round 0

F1 byte state is already `uint8_t`. An in-place H design would reduce its
shared footprint by one third and raises the 11.5 kb static ceiling from two
to four blocks per SM. This passes the preregistered 25% static footprint
screen, but it does not yet prove a 25% reduction in executed DP cells or
state-memory traffic. F1 implementation therefore remains unauthorized until
Nsight data and a recurrence dependency audit support it.

Generic two-tasks-per-warp packing remains out of scope because its prior
prototype regressed performance.

## Next profiling epoch

After the full-concat AB/BA shadow completes, profile one representative
launch of each kernel on an otherwise idle GPU:

```text
main:
    prealign_cuda_column_max_legacy_byte_batch_kernel

F1 Round 0:
    first matching prealign_cuda_exact_attempt_forward_byte_kernel launch
```

Collect:

```text
LaunchStats
Occupancy
SpeedOfLight
MemoryWorkloadAnalysis
ComputeWorkloadAnalysis
SchedulerStats
WarpStateStats
SourceCounters
```

The profile must bind a new source commit and binary digest, use the frozen
2 Mb input, retain the exact complete output digest, and record that Nsight
kernel replay timings are diagnostic rather than production wall time.

The default-safe runner is:

```bash
make check-long-query-ncu-profile-preflight-v1
```

It only inspects the tool and permission contract. Actual collection requires
`scripts/run_long_query_ncu_profile_v1.sh --execute main` or
`--execute f1-round0`, all source/input/binary digest environment variables,
an idle CUDA host, an external GPU lock, and authorized hardware counters.
The runner profiles one matching launch, requires the complete output digest
and zero fallback markers, and exports both `.ncu-rep` and raw CSV artifacts.

The main kernel implementation gate remains at least `1.5x` stage speedup.
The F1 gate additionally requires a design-level reduction of at least 25% in
DP work or state traffic before a bounded kernel spike.

Machine-readable residency values are in `static_model.json` and can be
regenerated with:

```bash
python3 scripts/model_long_query_gpu_resources_v1.py \
  --source-commit c4c3510b8fef7215b54c2ba35132f84fa33467a3 \
  --output docs/long_query_gpu_resource_profile_v1/static_model.json
```
