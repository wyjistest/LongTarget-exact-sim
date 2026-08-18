# Long-query consumer-driven lower-bound audit v1

This epoch is host-only. It does not change the CUDA kernel or the default
all-reverse exact path. The development binary optionally writes one row per
endpoint attempt with `FASIM_LONG_QUERY_GPU_CONSUMER_LOWER_BOUND_TRACE`.
`scripts/audit_long_query_consumer_lower_bound.py` then replays the original
ordered scoreInfo consumer and computes a geometry-weighted DP-cell lower
bound.

## Evidence

The real-promoter fixture was `LINC01501 (4,006 nt) x shard_0009`
(`4,942,620 bp`). The trace contains exactly 4,345,980 attempt rows and
1,086,495 scoreInfo groups across 48,432 tasks. The source target digest is
`c448a0564c4fbfb2261071885a2f83f2631323d54a5e64b5d4ed4ce57262295f`, and the
complete output digest is:

```text
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075
```

The replay matched runtime task/group/attempt and threshold/best/last counts
exactly. CPU all-attempt oracle, CPU reference replay, selected continuation
failures, and fallbacks were all zero. `audit.json` is the compact machine
readable receipt; the 354 MiB raw trace remains a local evidence artifact and
is intentionally not committed.

## Results

| Quantity | Result |
| --- | ---: |
| Full attempts | 4,345,980 |
| Ordered forward prefix attempts | 1,735,752 (39.94%) |
| Full forward-cell proxy | 1,723,797,519,544 |
| Minimum forward-cell proxy | 670,026,410,314 (38.869%) |
| Exact lazy reverse attempts | 1,086,495 (25.00%) |
| Minimum reverse-cell proxy | 430,949,379,886 (25.00%) |
| Combined F1 DP-cell proxy | 31.935% of full forward+reverse |
| Linear F1 wall projection | 209.84 s |
| 1.5x CPU budget | 241.09 s |
| 10% engineering-margin budget | 216.98 s |

The wall projection scales the measured no-trace all-reverse epoch
(`336.78 s`, `194.118 s` GPU kernel) using the measured forward-only kernel
(`134.455 s`) and the replayed cell fractions. It is a planning projection,
not a benchmark: compaction, queueing, synchronization, and occupancy losses
are not yet measured.

The diagnostic zero-kernel residuals are `142.66 s` at process-wall scope and
`68.96 s` for the consumer telemetry scope. A true cached-endpoint F0 replay
was **not executed** in this epoch; these residuals are stage-removal
diagnostics, not product runtimes and must not be reported as speedups.

## Decision

The ordered consumer lower bound is promising: the F1 projection is below the
1.5x budget with the requested margin. However, this epoch did not execute a
cached-endpoint F0 replay and emits no independent whole-target-to-subview
witness. Weighted witness coverage is therefore `0%`, F2 is conservatively
equal to F1, and CUDA implementation is **not authorized**.

The next authorized step is a witness-proxy feasibility audit. CUDA work may
start only after exact replay remains identical, weighted witness coverage
meets the frozen threshold, and a conservative projection leaves engineering
headroom. Production authorization and the Bioinformatics v2 state are
unchanged.

## Reproduction

The development binary was built from the `8670cc4` parent epoch with the
existing GASAL2 library and `prealign_cuda.o` (no `nvcc` was available on this
host). Its audit-only SHA-256 was
`97703558f722e8ca66f8750df3b98cea5fe9412e1ae3489831e2588b7cd693ef`.

Run the host replay with:

```bash
python3 scripts/audit_long_query_consumer_lower_bound.py \
  --trace /path/to/attempt_trace.tsv \
  --consumer-report /path/to/consumer.tsv \
  --output audit.json \
  --output-file /path/to/Homo_sapiens-LINC01501-shard_0009-TFOsorted \
  --expected-output-sha256 2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075 \
  --all-reverse-wall 336.78 \
  --all-reverse-kernel 194.11832934 \
  --forward-only-kernel 134.45516577 \
  --cpu-authority-wall 361.63
```

The deterministic unit test is:

```bash
python3 tests/test_long_query_consumer_lower_bound.py
```
