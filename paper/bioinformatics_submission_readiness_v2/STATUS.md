# Bioinformatics Submission Readiness v2 Status

```text
epoch_id = bioinformatics_submission_readiness_v2
baseline_commit = 739ee0a8db01f77143a5c993e6c68a56a772502b
legacy_successor_route = closed_biological_utility_gap
v2_route = closed_performance_or_correctness_gap
active_phase = none
phase_0 = pass
phase_1 = pass
phase_2 = pass
phase_3 = pass
phase_4 = no_go
phase_5 = not_authorized_previous_no_go
phase_6 = not_authorized_previous_no_go
phase_7 = not_authorized_previous_no_go
gpu_screen_product_status = experimental
artifact_role = frozen_release_candidate_under_test
validation_status = failed
target_claim_status = not_supported
```

Phase 0 was independently authorized after the previous biological-utility
program reached its immutable Phase 6 `no_go`. This epoch did not alter or
reopen that program. It prospectively tested a narrower GPU-only
candidate-site screening product after transparently disclosing the post hoc
scope decision.

Phase 1 froze the original release candidate. Excluded Phase 2 development
then found a genomic-coordinate identity defect, so the original artifact and
receipt remained unchanged and the independently named
`submission_rc_v2_2` epoch was created. Its exact runtime image digest was
`sha256:f04340aa1b77092c25eee50c84144adb08e6f1b48a34580f6f9c33aff3163ca7`.
The product remained experimental pending Phase 4.

Phase 2 retained every excluded development result, including two scientific
mismatches and one complete candidate-site contract pass. PATO 1.0.6 and
Triplexator v1.3.3 completed corrected basename-output development smokes.
Those diagnostics were excluded from formal inference. PATO was frozen only
as a candidate current executable comparator, and no unqualified
state-of-the-art label was assigned.

Phase 3 froze 10 fresh GENCODE/GRCh38 workloads, five paired timing repeats
per workload, 50 pair rows, and 100 arm attempts. The single primary estimand
was the validated 24-hour capacity ratio with a one-sided 95% lower-bound gate
of 10. Any technical, identity, determinism, or candidate-site contract
failure forced the complete Phase 4 gate to `performance_no_go` and made the
capacity estimand ineligible.

## Decisive Phase 4 result

Formal execution used Phase 3 commit
`53e57591da1bfe8ffa34ebe57d89a5d2cd347d29` and the exact
`submission_rc_v2_2` container. It completed under the original 12-hour clock
without retries:

```text
planned arm attempts = 100
terminal arm attempts = 100
technical successes = 100
technical failures = 0
planned pair rows = 50
technical-success pair rows = 50
candidate-site contract pass rows = 45
candidate-site contract failure rows = 5
primary capacity estimate computed = false
decision = performance_no_go
```

All five contract failures were the five frozen repeats of workload
`v2p4_w010`. The `score` and `nt` Top-5 complete sets passed in every repeat.
The `stability` comparison retained Top-1 but had one missing and one extra
Top-5 candidate site, so the required complete set was not preserved. This was
a repeatable scientific mismatch, not a technical failure.

The frozen analyzer reports `all_outputs_deterministic = false` because it
short-circuits before the determinism branch whenever not every pair is
contract-eligible. A separate diagnostic inventory found one unique
`candidate_sites.tsv` digest in each of the 20 workload-arm groups across all
five repeats. That diagnostic does not change the formal no-go and must not be
used to compute the primary capacity estimand.

Under the preregistered all-row rule, `45 != 50`; therefore the validated
24-hour capacity ratio and its confidence bound were not computed. Observed
pair timings cannot be substituted for the ineligible primary result, and the
historical 38.32x anchor remains historical only.

## Stop-loss

The Phase 4 `performance_no_go` closes the v2 Bioinformatics route. Formal
external comparison, release packaging, and Application Note drafting were
not authorized and were not executed. `gpu-screen` remains experimental, the
release candidate failed validation, and the target `accelerates` claim is not
supported for this software epoch.

Historical evidence roots and every earlier no-go remain unchanged.
