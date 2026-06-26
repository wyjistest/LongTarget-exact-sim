# Fasim GASAL2 CPU-vs-GASAL2 Full Plain Top5 Gate

This checkpoint records the fast, non-exact full-output GASAL2 path separately
from the exact full-row equivalence path.

## Contract

```text
Path:
  CPU full plain .lite output
  vs
  GASAL2 full plain .lite output

Required:
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
  GASAL2 active = 1
  GASAL2 fallbacks = 0
  speedup reported
  full-row diff counts reported

Not required:
  full row-set equality
```

This is not a full `aligner.Align()` replacement and not a full
`.lite/TFOsorted` equivalence claim. It is a top5-equivalent fast path for
workloads where downstream interpretation accepts the top5 contract.

## Fresh chr22 Result

Command:

```bash
WORK=.tmp/measure_cpu_vs_gasal2_full_chr22_plain \
TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
BIN=.tmp/fasim_longtarget_gasal2_direct \
bash scripts/characterize_fasim_gasal2_cpu_vs_gasal2_full_plain.sh
```

Result:

```text
cpu_wall_seconds = 2275.937806
gasal2_wall_seconds = 70.154883
run_wall_speedup = 32.441616

cpu_lines = 388,502
gasal2_lines = 388,822
common_rows = 384,362
cpu_only_rows = 4,140
gasal2_only_rows = 4,460

top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true

gasal2_requests = 21,802,059
gasal2_traceback_requests = 6,910,419
gasal2_fallbacks = 0
gasal2_length_guard_fallbacks = 0
```

## Checks

Long-running characterization:

```bash
make characterize-fasim-gasal2-cpu-vs-gasal2-full-plain
```

Fast result check:

```bash
WORK=.tmp/measure_cpu_vs_gasal2_full_chr22_plain \
make check-fasim-gasal2-cpu-vs-gasal2-full-plain-result
```

## Decision

```text
CPU-vs-GASAL2 full plain:
  strong speed signal
  top5 clean
  full rows drift
  suitable only for explicit top5-oriented contract

Exact full-output path:
  use equivalence-first gate instead
  do not claim 32x full-output equivalence
```
