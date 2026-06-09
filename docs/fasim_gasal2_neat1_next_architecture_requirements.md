# Fasim GASAL2 NEAT1 Next Architecture Requirements

This is a requirements checkpoint, not runtime code. It converts the current
NEAT1 performance evidence into minimum requirements for any future broad
scoreInfo/preAlign GPU/GASAL2 prototype.

## Evidence Basis

Derived from the NEAT1 speed ceiling:

```text
baseline_wall_seconds = 86.0335
candidate_wall_seconds = 121.948
candidate_vs_baseline = 0.705493x
ideal_zero_gpu_call_speedup = 0.9747x
ideal_zero_gpu_total_speedup = 1.1950x
ideal_zero_realpath_extend_speedup = 1.2312x
```

This means it is not enough to optimize only the CUDA kernel. It is not enough
to optimize only scoreInfo orchestration. It is not enough to optimize only CPU
realpath extend. A broad NEAT1-like replacement needs a different execution
shape.

## Required Prototype Shape

Required prototype shape:

```text
produce legacy-byte-compatible scoreInfo
avoid CPU preAlign replay
avoid current CPU realpath extend/align replay or replace it with an equivalent batched consumer
preserve scoreInfo-level single-emission semantics
prove selected-attempt output equivalence before using reduced attempts
external digest gate remains authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
```

The selected-attempt work is especially constrained: previous selected-only
replay over-emitted repeated scoreInfos, and grouped selected-only replay left a
same-count content mismatch. A reduced consumer must prove the exact output
surface before it can replace the legacy scoreInfo-level emission path.

## NEAT1 Gate

NEAT1 first64 hard gate:

```text
digest clean
scoreinfo_gasal2_active = 1
fallback = 0
scoreInfo mismatches = 0
candidate_wall_seconds < 86.0335
GPU scoreInfo plus replacement-consumer total must beat CPU fallback
kernel-only win is not sufficient
MALAT1 scoped positive must remain clean
```

If the prototype cannot reduce both GPU scoreInfo and realpath extend/align,
stop the NEAT1 broad path.

The broad co-designed scoreInfo plus replacement-consumer shadow plan is
checked by:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

That plan is the next allowed implementation direction for this requirement.

This does not close the active objective:

```text
full objective remains open
```

## Gate

```bash
make check-fasim-gasal2-neat1-next-architecture-requirements
```
