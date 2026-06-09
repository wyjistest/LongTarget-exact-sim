# Fasim GASAL2 MALAT1 Two-Contract Product Readiness

This is the MALAT1-like product-readiness gate for the current long-query
scoreInfo/preAlign GASAL2/GPU line.

It does not complete the full objective. It defines a narrow default-off scope
that may be treated as a scoped product candidate for MALAT1-like grouped
workloads.

## Scope

The scoped runner option is:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32
```

The scoped runtime policy is:

```text
default-off opt-in
external digest gate required
no diagnostic probe env leakage
```

The scoped output contracts currently checked are:

```text
schema=lite
schema=tfosorted
```

The candidate report records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1
```

The runtime remains a CPU-output authority path. GPU scoreInfo/minScore feeds
the existing CPU realpath consumer, but GPU endpoint, CIGAR, traceback, final
output, and digest authority remain forbidden.

## Current Positive Evidence

The no-probe runtime gates are the authoritative runtime evidence:

```bash
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
```

The current full-MALAT1 no-probe lite result is:

```text
schema = lite
rows = 98,713
digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
candidate_vs_baseline = 1.037747x
tasks = 200,400
two_contract_used = 200,400
realpath_used = 200,400
gpu_minscore_used = 200,400
gpu_scoreinfo_groups = 3,561,123
probe_positive_numeric_keys = 0
```

The current full-MALAT1 no-probe TFOsorted result is:

```text
schema = tfosorted
rows = 98,713
digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc
candidate_vs_baseline = 1.037590x
tasks = 200,400
two_contract_used = 200,400
realpath_used = 200,400
gpu_minscore_used = 200,400
gpu_scoreinfo_groups = 3,561,123
probe_positive_numeric_keys = 0
```

The current first64/first128/first256 no-probe lite results are:

```text
first64:
  rows = 9,741
  candidate_vs_baseline = 1.030868x
  tasks = 18,096
  gpu_scoreinfo_groups = 319,280
  probe_positive_numeric_keys = 0

first128:
  rows = 22,531
  candidate_vs_baseline = 1.043793x
  tasks = 40,128
  gpu_scoreinfo_groups = 715,473
  probe_positive_numeric_keys = 0

first256:
  rows = 42,504
  candidate_vs_baseline = 1.042764x
  tasks = 80,640
  gpu_scoreinfo_groups = 1,434,844
  probe_positive_numeric_keys = 0
```

The first8 smoke is correctness-clean but slightly slower:

```text
first8 lite:
  rows = 796
  candidate_vs_baseline = 0.990695x
  tasks = 1,824
  probe_positive_numeric_keys = 0

first8 tfosorted:
  rows = 796
  candidate_vs_baseline = 0.990699x
  tasks = 1,824
  probe_positive_numeric_keys = 0
```

This means the product-readiness status is scoped and workload-shape dependent,
not a broad runtime recommendation.

## Product Readiness Decision

The accepted MALAT1-like product scope would be:

```text
accepted MALAT1-like two-contract product scope:
  use only --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32
  keep the runtime default-off
  keep external digest equality as the output authority
  require two_contract_used == tasks
  require realpath_used == tasks
  require gpu_minscore_used == tasks
  require fallback/mismatch counters = 0
  require probe_positive_numeric_keys = 0
  require full row-set equality for the claimed schema
```

Current readiness:

```text
MALAT1-like group32 lite:
  product-readiness candidate

MALAT1-like group32 TFOsorted:
  product-readiness candidate

first8 tiny sample:
  correctness smoke only, not performance evidence

NEAT1:
  no broad real path

full objective:
  full objective remains open
```

## Non-Goals

This readiness gate does not claim:

```text
not universal scoreInfo/preAlign replacement
not full aligner.Align replacement
not GPU endpoint authority
not GPU CIGAR authority
not GPU traceback authority
not NEAT1 broad long-query real path
not default production path
not a replacement for the top5 artifact contract
```

## Gate

Focused readiness gate:

```bash
make check-fasim-gasal2-malat1-two-contract-product-readiness
```

Composed scoped milestone gate:

```bash
make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup
```
