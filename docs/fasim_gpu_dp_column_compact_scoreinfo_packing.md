# Fasim GPU DP+column Compact ScoreInfo Packing

Base branch:

```text
fasim-gpu-dp-column-post-topk-align
```

This stacked PR adds a default-off compact scoreInfo packing path for
`FASIM_GPU_DP_COLUMN=1`. It reuses the already-returned GPU post-TopK column
peaks to build CPU-compatible scoreInfo records during extension, avoiding the
per-window full-column scoreInfo transfer for non-overflow tasks in the opt-in
compact path.

Compact packing is guarded by a non-oracle TopK overflow check. If the final
returned TopK peak is still above the current `minScore`, the task falls back to
the full-column exact scoreInfo path. This preserves exactness for overflow
tasks while keeping compact packing for the common bounded case.

## Environment

```text
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1
FASIM_GPU_DP_COLUMN_VALIDATE=1   # optional post-hoc validation
```

`FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` is not default. The existing
`FASIM_GPU_DP_COLUMN=1` path remains full-column exact unless this compact env
is explicitly set.

## Telemetry

```text
fasim_gpu_dp_column_compact_scoreinfo_requested
fasim_gpu_dp_column_compact_scoreinfo_active
fasim_gpu_dp_column_compact_scoreinfo_records
fasim_gpu_dp_column_compact_scoreinfo_d2h_bytes
fasim_gpu_dp_column_compact_scoreinfo_mismatches
fasim_gpu_dp_column_compact_scoreinfo_fallbacks
fasim_gpu_dp_column_exact_scoreinfo_extend_calls
fasim_gpu_dp_column_exact_scoreinfo_extend_d2h_bytes
```

`exact_scoreinfo_extend_*` tracks the full-column exact scoreInfo calls made by
the extension path. It is expected to be non-zero for the current full-column
GPU mode. In compact mode it should be limited to TopK overflow fallback tasks.

## Tiny Exactness Check

| Mode | Digest | Compact active | Compact records | Compact D2H bytes | Exact extend calls | Exact extend D2H bytes | Compact mismatches | Compact fallbacks | GPU fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| full-column exact | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 0 | 0 | 0 | 4 | 69,856 | 0 | 0 | 0 |
| compact scoreInfo | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 1 | 78 | 8,192 | 0 | 0 | 0 | 0 | 0 |

The compact path preserves the tiny canonical digest while removing full-column
exact scoreInfo calls from extension.

## HumanLncAtlas Guarded Smoke

| Workload | Digest | Records | Compact records | Compact D2H bytes | TopK overflow windows | Exact fallback calls | Exact fallback D2H bytes | ScoreInfo mismatches | GPU fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| human_lnc_atlas_17kb_target | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | 256 | 32,768 | 1 | 1 | 20,000 | 0 | 0 |
| human_lnc_atlas_508kb_target | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | 7,599 | 851,968 | 12 | 12 | 240,000 | 0 | 0 |

The first unguarded compact smoke showed human scoreInfo mismatches only on
TopK overflow/truncation windows. The guarded path keeps those windows exact
and leaves the rest on compact post-TopK packing.

This is a performance-path step only; it does not change scoring, threshold,
non-overlap, output format, or default GPU enablement.

## Decision

Keep `FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` default-off. Use it for further
GPU DP+column characterization, especially humanLncAtlas and larger workloads,
before making any performance recommendation.

Forbidden-scope check:

```text
default GPU enablement: no
scoring/threshold/non-overlap/output change: no
digest relaxation: no
SIM-close/recovery change: no
speedup recommendation: no
```
