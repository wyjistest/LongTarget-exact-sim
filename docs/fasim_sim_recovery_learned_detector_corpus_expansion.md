# Fasim SIM-Close Learned Detector Corpus Expansion

## Corpus Gate Report

This report records the current offline learned-detector corpus gate. It does not add a runtime model, change Fasim output, or recommend/default SIM-close.

The current checked-in audit remains useful as a hard-negative and split-discipline checkpoint, but it is not broad enough for production learned-detector claims.

| Metric | Value |
| --- | --- |
| workload_count | 1 |
| family_count | 4 |
| rows | 65 |
| positive_rows | 40 |
| negative_rows | 25 |
| hard_negative_sources | fasim_supported_non_sim:25 |
| hard_negative_source_count | 1 |
| workload_heldout_degenerate | 1 |
| family_heldout_degenerate | 0 |
| heldout_workload_available | 0 |
| heldout_family_available | 1 |
| modeling_gate | collect_more_workloads |

## Decision

The next learned-detector step remains corpus expansion. The data gate blocks runtime model promotion because the audit still has one effective workload and one hard-negative source.

Proceed to offline model-shadow work only after adding multiple validate-supported workloads and a broader hard-negative source mix. SIM labels may remain offline training/evaluation labels only; they must not be used as runtime detector inputs, guard inputs, replacement inputs, or output ordering inputs.

## Scope

```text
Production model added: no
Fasim runtime changed: no
SIM-close runtime changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
SIM labels used as runtime input: no
Recommended/default mode: no
```
