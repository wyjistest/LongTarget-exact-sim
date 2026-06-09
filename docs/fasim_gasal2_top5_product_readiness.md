# Fasim GASAL2 Top5 Product Readiness

This is the top5-only product-readiness gate for the current scoreInfo/preAlign
GASAL2 line.

It does not complete the full objective. It defines the narrow opt-in scope that
could be intentionally accepted as product behavior if the project chooses a
top5-only artifact path.

## Scope

The scoped preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The scoped runtime policy is:

```text
default-off opt-in
```

The scoped output contract is:

```text
result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
```

The contract artifacts are:

```text
topk_summary.tsv
topk_rows.tsv
topk-TFOsorted.lite
report.json
run_manifest.json
```

full `.lite` output is not contract output. final all-row TFO equivalence is not
claimed by this scope.

## Current Positive Evidence

The current positive evidence is bounded to short-query/H19 workloads:

```text
chr21+chr22:
  top5 score/stability/nt_score clean
  scoreinfo_gasal2_active = 1
  GASAL2 requests > 0
  GASAL2 traceback requests > 0
  exact scoreInfo GPU tasks > 0
  fallback/overflow = 0

MEG3 grouped:
  complete-record grouping path clean
  top5 score/stability/nt_score clean
  scoreinfo_gasal2_active = 1
  GASAL2 requests > 0
  GASAL2 traceback requests > 0
  exact scoreInfo GPU tasks > 0
  fallback/overflow = 0
```

This is enough for a milestone. It is not enough for a universal replacement.

## Product Readiness Decision

The accepted top5-only product scope would be:

```text
accepted top5-only product scope:
  use only the top5 artifact contract
  keep the preset default-off opt-in
  keep full output outside the contract
  keep long-query fallback policy explicit
  require broader workload validation before recommending the preset broadly
```

The current readiness decision is:

```text
short-query/H19 top5 artifact:
  product-readiness candidate

MEG3 grouped top5 wrapper:
  product-readiness candidate

broader workload validation:
  recorded by make check-fasim-gasal2-top5-broader-validation
  still not enough for broad production default

full objective:
  full objective remains open
```

The top5 broader workload validation checkpoint is:

```bash
make check-fasim-gasal2-top5-broader-validation
```

It validates the current short-query positive set and the MALAT1/NEAT1
long-query guard set. Passing it means the opt-in product-readiness candidate
has a bounded workload table; it does not make the preset a broad production
default.

The focused top5 release smoke is:

```bash
make check-fasim-gasal2-top5-release-smoke
```

It composes the real wrapper smoke, formal preset examples, product-readiness,
recommended-runtime, and scoped-completion checks. This is a contract smoke, not
a performance claim.

Latest focused release-smoke result:

```text
formal_preset_example = meg3_first32
formal_preset_topk_artifact_match = true
cap32_nt_score_artifact_match = false
formal_preset_gasal2_requests = 63,035
formal_preset_exact_scoreinfo_gpu_tasks = 1,536
formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0
```

The speedup value is intentionally recorded only as a no-claim smoke boundary.
This gate proves the scoped top5 artifact contract activates and matches the
checked topK payload; it does not prove performance readiness.

The GASAL2 top5 recommended runtime checkpoint is:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

The top5 scoped completion candidate checkpoint is:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

That gate records the default-off recommended invocation for the bounded
short-query/H19 top5 contract. The full objective remains open.

## Long-Query Policy

The current long-query fallback policy is not a performance claim. It is a
fail-closed guard.

```text
GASAL2_MAX_QUERY_LEN = 2812
```

MALAT1/NEAT1 are outside the current GASAL2-active path:

```text
MALAT1/NEAT1:
  query_len > GASAL2_MAX_QUERY_LEN
  no real path
  must fail closed
  GASAL2 selected/expanded segment traceback: no-go for real path
```

If a future long-query path is pursued, it needs different evidence:

```text
scoreinfo_gasal2_active = 1
top5 score/stability/nt_score clean
GASAL2/exact scoreInfo fallback = 0
GPU/GASAL2 total < CPU fallback
```

## Non-Goals

This readiness gate does not claim:

```text
not full scoreInfo/preAlign universal replacement
not full `.lite` output equivalence
not final all-row TFO equivalence
not `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
not long-query MALAT1/NEAT1 GASAL2 production output
not default production path
```

## Gate

Focused product-readiness gate:

```bash
make check-fasim-gasal2-top5-product-readiness
```

Current-state gate:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

The current-state gate includes this readiness checkpoint. Passing it means the
top5 milestone has a documented opt-in product-readiness boundary; it does not
mean the original full objective is complete.
