# Word16 global-state scalar direct-output spike v1

## Decision

```text
exactness = PASS
performance gate = FAIL
decision = NO-GO
runtime integration = forbidden
```

The spike keeps the production word16 recurrence, global H/E/H state layout,
task/block mapping, and numeric behavior.  It removes only the per-column
global maximum output and the following reduction kernel, accumulating one
deterministic scalar maximum per task instead.

Implementation source:

```text
commit 115c3fc0002b0ae04939740d27ed69f7334db015
```

## Exactness

The direct result was compared task by task with the existing column-output
plus reduction authority for query lengths:

```text
1, 31, 32, 33, 511, 2812, 4006, 8181, 12397 nt
```

All comparisons passed.  The API also has a CPU-only stub and remains unused
by the F1 runtime.

## Performance gate

The preregistered retention gate was:

```text
direct wall <= 0.85 * authority wall
```

On an RTX 4090, using 128 tasks, 5,000 nt targets, seven balanced repeats:

| Query | Authority wall | Direct wall | Direct / authority |
| ---: | ---: | ---: | ---: |
| 4,006 nt | 0.020154463 s | 0.019857026 s | 0.985242 |
| 8,181 nt | 0.106483831 s | 0.105949940 s | 0.994986 |
| 12,397 nt | 0.238655616 s | 0.238159639 s | 0.997922 |

The removed output/reduction work is therefore negligible at production-like
dimensions.  Full DP arithmetic and global H/E/H traffic dominate this stage.
No further direct-output tuning is authorized.

Run exactness with:

```bash
make check-prealign-cuda-global-state-direct
```

Machine-readable values and binary bindings are in `audit.json`.
