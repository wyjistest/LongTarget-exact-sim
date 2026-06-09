# Fasim GASAL2 MALAT1 Two-Contract Recommended Runtime

This document records the recommended runtime for the scoped MALAT1-like
two-contract scoreInfo path.

It is a default-off opt-in runtime, not a broad production default.

## Command

Use a GASAL2-enabled Fasim binary:

```bash
make build-fasim-gasal2
```

Recommended MALAT1-like invocation:

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_gasal2 \
  --target MALAT1-DNAseq.fa \
  --rna MALAT1.fa \
  --rule 0 \
  --output-mode lite \
  --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32 \
  --workers 1 \
  --work-dir .tmp/fasim_gasal2_malat1_two_contract \
  --manifest run_manifest.json
```

For 19-column output checks, use:

```bash
  --output-mode tfosorted
```

The grouped preset uses complete-record grouping:

```text
--group-target-records 32
```

This is grouping complete FASTA records. It is not chunking, overlap, or an
in-process multi-GPU runtime.

## Runtime Contract

The runner option is:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32
```

It records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1
```

It sets only the no-probe two-contract runtime env stack:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
FASIM_ALIGN_GASAL2=1
```

It must reject diagnostic probe env leakage. Runtime reports must keep:

```text
probe_positive_numeric_keys = 0
```

## Recommended When

This runtime is recommended only when:

```text
recommended when:
  MALAT1-like workload shape
  complete-record group32 is acceptable
  schema=lite or schema=tfosorted row-set equality is required
  external digest gate is available
  two_contract_used == tasks
  realpath_used == tasks
  gpu_minscore_used == tasks
  fallback/mismatch counters = 0
```

The checked positive set is:

```text
MALAT1 first64
MALAT1 first128
MALAT1 first256
MALAT1 full lite
MALAT1 full TFOsorted
```

## Not Recommended When

This runtime is not recommended when:

```text
not recommended when:
  NEAT1 or broad long-query workload
  two_contract bridge launch fails
  candidate_vs_baseline <= 1.0x on the claimed workload
  diagnostic probe env is required for correctness
  endpoint/CIGAR/traceback authority is required
  direct aligner.Align replacement is required
  default production behavior is required
```

The first8 smoke is intentionally not performance evidence:

```text
first8 lite candidate_vs_baseline = 0.990695x
first8 tfosorted candidate_vs_baseline = 0.990699x
```

## Decision

```text
MALAT1-like group32 two-contract runtime:
  recommended as default-off opt-in for the checked scope

NEAT1:
  no real path

default production:
  not broad production default

full objective:
  full objective remains open
```

## Gate

Focused gate:

```bash
make check-fasim-gasal2-malat1-two-contract-recommended-runtime
```

Scoped release smoke:

```bash
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
```

Composed gate:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```
