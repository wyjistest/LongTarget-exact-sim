# Fasim GPU DP+column Auto Policy

Base branch:

```text
fasim-gpu-dp-column-compact-threshold
```

This stacked PR adds a default-off size-gated policy for the compact GPU
DP+column path. It does not default GPU execution, change scoring, change
thresholds, change non-overlap behavior, change output format, or touch
SIM-close/recovery behavior.

## Modes

Default mode is unchanged. Without `FASIM_GPU_DP_COLUMN_AUTO=1`, Fasim keeps
the existing CPU/table path unless the user explicitly enables the manual GPU
path with `FASIM_GPU_DP_COLUMN=1`.

Manual GPU mode is unchanged:

```bash
FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN=1 \
FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1
```

Auto mode is default-off:

```bash
FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN_AUTO=1
```

When AUTO is requested, Fasim estimates GPU task windows and DP cells from the
input workload before CUDA initialization. If both thresholds match, AUTO
enables the existing compact GPU DP+column path. Otherwise it stays on the
table-only CPU path.

## Initial Gate

The conservative defaults come from the #81 threshold characterization:

```text
FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1500000000
FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=128
```

#81 showed the synthetic crossover between 64 GPU windows / 785,740,288 DP
cells and 128 GPU windows / 1,571,480,576 DP cells. The 17kb humanLncAtlas case
was below the gate and lost to table-only, while the 508kb case was above the
gate and won.

Both thresholds must match:

```text
observed_cells >= min_cells
observed_windows >= min_windows
```

The thresholds can be overridden for characterization:

```bash
FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=<n>
FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=<n>
```

## Telemetry

AUTO adds these profile metrics:

```text
fasim_gpu_dp_column_auto_requested
fasim_gpu_dp_column_auto_active
fasim_gpu_dp_column_auto_min_cells
fasim_gpu_dp_column_auto_min_windows
fasim_gpu_dp_column_auto_observed_cells
fasim_gpu_dp_column_auto_observed_windows
fasim_gpu_dp_column_auto_disabled_reason
fasim_gpu_dp_column_auto_selected_path
fasim_gpu_dp_column_auto_threshold_matched
```

`fasim_gpu_dp_column_auto_disabled_reason` uses numeric codes:

```text
0 = none
1 = below_threshold
2 = cuda_unavailable
3 = manual_gpu_requested
4 = non_fastsim
```

`fasim_gpu_dp_column_auto_selected_path` uses numeric codes:

```text
0 = table
1 = compact_gpu
2 = manual_gpu
```

## Expected Behavior

Tiny, medium, and 17kb workloads should report AUTO requested but inactive,
with `selected_path=0` and `disabled_reason=1` when they are below threshold.

Window-heavy synthetic and 508kb workloads should report AUTO requested,
threshold matched, and active when CUDA is available. Their output digest must
match table-only mode, and validation mismatch counters must remain zero when
`FASIM_GPU_DP_COLUMN_VALIDATE=1` is also requested.

AUTO does not enable validation by default. Validation remains controlled by
`FASIM_GPU_DP_COLUMN_VALIDATE=1`.

## Decision

This is a default-off policy candidate, not a global default. The current
recommended opt-in remains:

```bash
FASIM_TRANSFERSTRING_TABLE=1
```

For large workloads, the candidate combination is:

```bash
FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN_AUTO=1
```

Do not make GPU DP+column default from this PR. Keep AUTO opt-in until broader
real-corpus validation confirms that the threshold avoids small-workload
slowdowns while preserving digest exactness.
