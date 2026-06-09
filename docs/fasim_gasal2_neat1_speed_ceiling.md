# Fasim GASAL2 NEAT1 Speed Ceiling

This checkpoint quantifies the current NEAT1 first64 long-query speed ceiling.
It is not a completion claim, and it does not change runtime behavior.

## Source Runtime

Fresh no-probe trust runtime attribution:

```text
NEAT1 first64 fresh runtime attribution:
  baseline_wall_seconds = 86.0335
  candidate_wall_seconds = 121.948
  candidate_vs_baseline = 0.705493x
  gpu_total_seconds = 49.9507
  gpu_call_seconds = 33.6824
  kernel_seconds = 33.6745
  realpath_extend_seconds = 52.0682
  realpath_extend_align_seconds = 51.9805
  unattributed_overhead_seconds ~= 19.9291
```

This is not H2D/D2H, validation, compare, or CPU fallback. The transfer and
validation counters are tiny, compare is effectively zero, and CPU preAlign
fallback is zero.

## Ceiling Math

The current candidate loses baseline by:

```text
candidate_minus_baseline_seconds = 35.9145
```

If a future implementation removed the entire current GPU scoreInfo total but
left the rest unchanged:

```text
ideal_zero_gpu_total_wall_seconds = 71.9973
ideal_zero_gpu_total_speedup = 1.1950x
```

That is only a modest theoretical win, and it requires removing essentially all
current GPU scoreInfo cost.

If it removed only the measured GPU call/kernel portion:

```text
ideal_zero_gpu_call_wall_seconds = 88.2656
ideal_zero_gpu_call_speedup = 0.9747x
```

So kernel-only optimization is insufficient.

If it removed the CPU realpath extend work but left GPU scoreInfo unchanged:

```text
ideal_zero_realpath_extend_wall_seconds = 69.8798
ideal_zero_realpath_extend_speedup = 1.2312x
```

That is also only a modest theoretical win. realpath_extend remains a co-equal
bottleneck, not incidental overhead.

## Decision Boundary

scoreInfo-only optimization cannot justify broad replacement unless it removes
almost all GPU total. Kernel-only optimization is insufficient. The next
architecture must reduce both GPU scoreInfo work and CPU realpath extend/align
work before it can support a NEAT1-like broad replacement claim.

This keeps the full objective open:

```text
full objective remains open
```

## Gate

```bash
make check-fasim-gasal2-neat1-speed-ceiling
```
