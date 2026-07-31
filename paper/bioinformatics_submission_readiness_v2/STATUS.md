# Bioinformatics Submission Readiness v2 Status

```text
epoch_id = bioinformatics_submission_readiness_v2
baseline_commit = 739ee0a8db01f77143a5c993e6c68a56a772502b
legacy_successor_route = closed_biological_utility_gap
v2_route = conditionally_open_performance_gated
active_phase = 2
phase_0 = pass
phase_1 = pass
phase_2 = active
phase_3 = pending
phase_4 = pending
phase_5 = pending
phase_6 = pending
phase_7 = pending
gpu_screen_product_status = experimental
artifact_role = frozen_release_candidate_under_test
validation_status = pending
target_claim_status = pending_final_rc_performance_validation
```

Phase 0 was independently authorized after the previous biological-utility
program reached its immutable Phase 6 `no_go`. This new epoch does not alter or
reopen that program. It records a transparent post hoc narrowing from broad
biological-utility promotion to a GPU-only candidate-site screening product.

Phase 1 froze implementation commit
`0f04c241b6fda746f061b043aa9a9d26c79938ab`, candidate binary SHA-256
`ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9`, and
container image digest
`sha256:ab31acbf01e125f646889660f6286decfb30c015a21a30e7a60099a7fecbf530`.
The release candidate is immutable under test, but it is not validated or
released. A real-GPU host/container smoke used excluded development inputs and
is diagnostic only; it produced no formal performance estimate.

Formal external comparison, release packaging, and manuscript drafting remain
unauthorized until the decisive Phase 4 correctness and 24-hour capacity gate
passes.
