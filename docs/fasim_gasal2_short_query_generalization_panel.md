# Fasim GASAL2 Short-Query Generalization Panel

This checkpoint addresses the reviewer risk that the GASAL2 fast path could be
interpreted as an H19-specific optimization.

The result is positive, but scoped:

```text
GASAL2-LongTarget is not H19 sequence-special-cased.
It generalizes to multiple non-H19 short-query fragments under the same preset.

It is not a universal guarantee for every short query.
It is not an unsegmented full-length lncRNA accelerator.
```

## Runtime Claim

Use this wording:

```text
GASAL2-LongTarget accelerates the checked short-query LongTarget regime and
preserves clustered TFO1-TFO5 experimental prioritization for contract-clean
inputs. The current implementation boundary is the verified 2812-bp GASAL2
query contract, not a biological definition of short lncRNAs.
```

Do not claim general acceleration for full-length lncRNAs such as MALAT1,
NEAT1, or KCNQ1OT1. Those full-length inputs exceed the current unsegmented
GASAL2 contract and are recorded as guarded negative controls.

## Panel

Artifact:

```text
.tmp/characterize_fasim_gasal2_short_query_generalization_panel
```

Command used:

```bash
WORK=.tmp/characterize_fasim_gasal2_short_query_generalization_panel \
KCNQ1OT1_FASTA=.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa \
LENGTHS='1024 2048 2812' \
POSITIONS='mid' \
REQUIRE_TOPK_EQUAL=0 \
bash scripts/characterize_fasim_gasal2_short_query_generalization_panel.sh
```

The panel uses one target slice and one GASAL2 preset for all rows:

```text
target = .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
rule = 0
prune_max_per_task = 256
gasal2_streams = 3
gasal2_batch = 20000
max_query_len = 2812
```

`REQUIRE_TOPK_EQUAL=0` is intentional for the panel runner: it records boundary
mismatches instead of aborting on the first non-clean query.

## Summary

```text
panel_rows = 11
completed_rows = 11
top5_clean_supported_rows = 9
top5_clean_supported_non_h19_rows = 8
negative_controls = 3
negative_controls_guarded = 3
median_speedup_clean = 12.567938x
decision = short_query_generalization_clean
```

Clean supported non-H19 rows:

```text
MALAT1 mid 1024:   10.878950x, TFO1-TFO5 score/stability/Nt clean
MALAT1 mid 2048:   13.065239x, TFO1-TFO5 score/stability/Nt clean
MALAT1 mid 2812:   13.937434x, TFO1-TFO5 score/stability/Nt clean

NEAT1 mid 1024:    10.249075x, TFO1-TFO5 score/stability/Nt clean
NEAT1 mid 2048:    12.490691x, TFO1-TFO5 score/stability/Nt clean
NEAT1 mid 2812:    13.194703x, TFO1-TFO5 score/stability/Nt clean

KCNQ1OT1 mid 2048: 12.054916x, TFO1-TFO5 score/stability/Nt clean
KCNQ1OT1 mid 2812: 12.567938x, TFO1-TFO5 score/stability/Nt clean
```

H19 remains clean in the same matrix:

```text
H19 full 2812: 15.525062x, TFO1-TFO5 score/stability/Nt clean
```

Boundary rows that are intentionally recorded, not hidden:

```text
MEG3 full 1582:
  score clean, Nt clean, stability not clean
  speedup = 12.768138x

KCNQ1OT1 mid 1024:
  stability clean, score not clean, Nt not clean
  speedup = 11.667343x
```

These rows mean the result should be presented as a contract-checked
short-query accelerator, not as an unconditional guarantee for every short
query.

## Negative Controls

Full-length long lncRNAs are outside the current unsegmented GASAL2 query
contract:

```text
MALAT1 full:    query_len = 8708,  supported = 0, max_query_len = 2812
NEAT1 full:     query_len = 22767, supported = 0, max_query_len = 2812
KCNQ1OT1 full:  query_len = 91667, supported = 0, max_query_len = 2812
```

These are preflight-only guarded negative controls by default. They demonstrate
scope honestly without spending time on known CPU fallback executions.

## Interpretation

This panel supports:

```text
not H19-specific:
  yes

non-H19 short-query fragments:
  multiple clean rows from MALAT1, NEAT1, and KCNQ1OT1

same preset:
  yes

full-length long lncRNA acceleration:
  not claimed

all short queries guaranteed clean:
  not claimed
```

The strongest reviewer-safe statement is:

```text
The GASAL2 path is a default-off, contract-checked short-query accelerator.
It is not tuned to the H19 sequence, but eligibility must remain validated per
query/workload shape.
```

## Reproducibility Gate

Run:

```bash
make characterize-fasim-gasal2-short-query-generalization-panel
make check-fasim-gasal2-short-query-generalization-panel-result
```

`KCNQ1OT1_FASTA` is external to the repository. For the recorded artifact it was:

```text
.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa
```
