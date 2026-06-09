# Fasim GASAL2 Top5 Scoped Completion Candidate

This checkpoint records a conditional completion candidate for the active
scoreInfo/preAlign GPU/GASAL2 objective.

It is not universal scoreInfo/preAlign replacement and not the full objective by
itself. It only applies if the product scope explicitly accepts the top5 artifact
as the output contract.

## Accepted Scope

The scoped preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The scoped result contract is:

```text
result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
```

The product output is:

```text
top5 score/stability/nt_score payload is the product output
topk-TFOsorted.lite
```

full `.lite` output and final all-row TFO are outside the accepted contract.

The scoped runtime policy is:

```text
default-off opt-in
```

## Proven Scope

The positive scope is bounded to short-query/H19 workloads:

```text
short-query/H19:
  chr21+chr22
  MEG3 grouped
```

Accepted evidence:

```text
scoreinfo_gasal2_active = 1
GASAL2 requests > 0
GASAL2 traceback requests > 0
exact scoreInfo GPU tasks > 0
zero_legacy_score_runs = 1
fallback/overflow = 0
top5 score/stability/nt_score clean
```

This is a real scoreInfo/preAlign GPU/GASAL2 path for the scoped top5 artifact.

## Guarded Scope

Long-query examples remain outside the GASAL2-active path:

```text
MALAT1/NEAT1:
  query_len > GASAL2_MAX_QUERY_LEN
  CPU fallback remains authority
  not a GASAL2-active success
  GASAL2 selected/expanded segment traceback: no-go for real path
```

The fallback policy is fail-closed, not a performance claim.

## Non-Goals

This scoped completion candidate does not claim:

```text
not `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
not full `.lite` equivalence
not final all-row TFO equivalence
not long-query GASAL2 production output
not broad production default
```

The full goal remains active unless this narrowed product scope is explicitly
accepted. If the required product remains universal scoreInfo/preAlign
replacement, long-query GASAL2 coverage, full `.lite` equivalence, endpoint
authority, CIGAR, or traceback authority, this candidate is insufficient.

## Verification

Required gates:

```bash
make check-fasim-gasal2-scoreinfo-current-state
make check-fasim-gasal2-top5-product-readiness
make check-fasim-gasal2-top5-broader-validation
make check-fasim-gasal2-top5-recommended-runtime
make check-fasim-gasal2-top5-release-smoke
make check-fasim-gasal2-full-goal-decision
```

Focused gate:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

The Full Goal Decision Audit checkpoint keeps this scoped candidate from being
treated as universal completion.

The broader scoreInfo feasibility checkpoint is:

```text
GASAL2 / GPU scoreInfo scoped feasibility checkpoint
MALAT1 streaming scoreInfo trust path: scoped go
NEAT1 streaming scoreInfo trust path: performance no-go
Broad scoreInfo/preAlign replacement: not proven
```

That checkpoint does not broaden this top5-only product contract; it only
records the separate MALAT1/NEAT1 trust boundary for the full objective.
