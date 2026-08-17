# Long-query GPU consumer spike v1

This is an isolated engineering spike. It does not reopen or modify any
Bioinformatics successor state.

## Contract

The `FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_V1=1` flag enables a shadow path only.
The normal CPU Fasim result remains the output authority. The shadow path must:

* use one complete query, never independent query segmentation;
* score each complete-query x target-subview attempt through the isolated CUDA
  endpoint API without entering the legacy 2812 nt GASAL2 bridge;
* compare score, query endpoint, local target endpoint, and terminal state for
  every attempt against CPU SSW before consumer selection;
* consume attempts in the exact scoreInfo/group order;
* reproduce the CPU authority's float identity-round loop literally, including
  its four-round termination behavior;
* expand selected attempts to the required group prefix before traceback;
* use CPU SSW only for the retained prefix attempts in this first spike;
* report any endpoint, selection, traceback, triplex, or fallback failure;
* never alter the normal output or silently replay the full CPU path.

This first implementation is deliberately a feasibility probe, not a GPU-owned
canonical consumer and not a release mode. A successful result authorizes only
the next implementation stage.

When compiled with `FASIM_WITH_SSW_FORWARD_CONTINUATION` and run with
`FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1`, an additional shadow mode
uses the exact GPU endpoint tuple to skip CPU forward DP and invokes CPU
canonical reverse-start/CIGAR only for retained attempts. This is a cost and
correctness bridge, not GPU traceback.

## Replacement prototype

`FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE=1` is a separate,
fail-closed development mode. It removes the in-process CPU authority consumer
and the all-attempt CPU validation oracle from the output path:

```text
stateful GPU scoreInfo
-> GPU score/endpoint for every attempt
-> exact ordered host selection
-> CPU continuation for selected attempts only
-> canonical triplex conversion and output
```

It requires `FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1`, the exact
legacy-byte streaming scoreInfo path, and the GPU min-score hot path. Missing
stateful scoreInfo, continuation failure, a fallback, or incomplete GPU
attempt coverage terminates the process instead of invoking full CPU replay.
The report uses `authority_comparison_available=0`, `validation_enabled=0`, and
`output_equal=-1`; output equality must be checked independently against a
frozen authority artifact.

This remains a hybrid prototype. CPU continuation owns reverse-start/CIGAR for
the selected attempts, so the mode must not be described as GPU-only traceback
or promoted to production from the development fixture.

Run the independent digest and performance gate with:

```bash
REPEATS=3 scripts/check_long_query_gpu_consumer_replacement_prototype_v1.sh
```

### Frozen development fixture result (2026-08-17)

For the 4,006 nt LINC01501 query and frozen 2 Mb chr22 target slice:

```text
planned task rows                 10,368
GPU endpoint attempts            981,688 / 981,688
all-attempt CPU oracle           0
full CPU consumer replay         0
selected CPU continuations       245,422
continuation failures            0
fallbacks                        0

lite output SHA-256              6f9e95ab6209d2ea053dfdef4872b6fd5616b07a9be8950976786c0a1215c226
replacement wall (3 runs)        36.5155 / 36.4520 / 36.4992 s
CPU authority wall (3 runs)      76.7816 / 77.9772 / 76.4634 s
median wall ratio                2.103652x

full TFOsorted rows              9,032
full TFOsorted SHA-256           a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b
full-output CPU/replacement wall 79.10 / 38.24 s
```

Both the lite artifact and the complete `TFOsorted` artifact were byte-identical
to their CPU authority outputs. This passes the bounded 1.5x fixture gate and
supports continuing the engineering study. This 4 kb result alone did not
validate unobserved 8-12 kb queries, remove selected CPU continuation, or
authorize a production long-query mode.

## Fresh-query promotion panel

After the 4 kb fixture passed, the first 8 kb and 12 kb promotion queries were
frozen in `fresh_long_query_promotion_panel_v1.tsv` before execution. The
selection rule is deterministic: among GENCODE v33 gene-exon-union lncRNAs not
used for the LINC01501, LINC00654, or LINC00174 diagnostics, choose the sequence
whose length is nearest to 8,192 or 12,288 nt, breaking an exact distance tie by
gene ID. Neither selected gene appeared in the existing GPU diagnostic
artifacts.

Both frozen promotion rows subsequently passed; the machine-readable results
are in `fresh_long_query_promotion_result_v1.tsv`:

```text
PCAT19      8,181 nt   CPU 157.75 s   replacement  68.90 s   2.289550073x
AL035530.2 12,397 nt   CPU 268.83 s   replacement 102.19 s   2.630687934x
```

For both rows, all 10,368 tasks completed, every planned endpoint attempt ran
on the GPU, no all-attempt CPU oracle or full CPU consumer replay ran, selected
continuation had zero failures, fallback accounting was zero, and the lite
output was byte-identical to CPU authority. These are development promotion
results on one frozen 2 Mb target slice, not a production or broad biological
validation claim.

## Hard gates

For the frozen LINC01501 fixture, all of the following are required:

* all planned attempts reach the new CUDA endpoint API with no CPU fallback;
* zero per-attempt score, query-end, local-ref-end, or terminal mismatches;
* exact GPU-vs-CPU selected attempt identity for every scoreInfo group;
* exact equality between the selected attempt prefixes and the CPU authority's
  observed ordered attempt descriptors and endpoint results;
* zero shadow/CPU triplex mismatches;
* zero missing or extra shadow rows;
* no workload-specific allowlist or special case;
* end-to-end shadow cost is measured, including score, selection, CPU traceback,
  conversion, sorting, and reporting.

The 1.5x speed gate is evaluated only after correctness is exact. This spike
still has CPU traceback authority, so it cannot support a production speed
claim by itself.

## Artifact identity

Each run records the source commit, binary digest, query/target digests, CLI
inputs, and runtime environment in the run directory selected by the script.
