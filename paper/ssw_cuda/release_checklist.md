# Release Checklist

| Item | Status | Evidence or reason |
| --- | --- | --- |
| CPU authority epoch frozen | Pass | `cpu_oracle_binary_receipt.json` |
| L1/L2 CUDA checkpoint | Pass | `preselect_receipt.json` |
| L3 CUDA endpoint checkpoint | Pass | `forward_endpoint_receipt.json` |
| Integrated forward-hybrid correctness | No-go | Phase 7 continuation contract failure |
| GPU L4 reverse-start | Not run | Not authorized after Phase 7 no-go |
| GPU L5/L6 traceback and CIGAR | Not run | Not authorized after Phase 7 no-go |
| Full L1-L7 backend | Not built | Phase 8-10 skipped |
| Fresh promotion holdout | Not run | Phase 11 skipped |
| Formal performance and B3 | Not run | B3 closed by Amdahl; Phase 12 skipped |
| User-facing safe CLI backend | Not promoted | No full correctness contract |
| Container or Apptainer image | Not produced | Release phase skipped |
| Release candidate receipt | Not produced | Release phase skipped |
| License inventory | Available | `license_inventory.tsv` |
| Publication source tables | Partial | Phase 0-7 source data only |

This repository state is not a software release candidate. Checkpoint kernels
must remain candidate-only and must not be advertised as a general replacement
for the CPU SSW authority.
