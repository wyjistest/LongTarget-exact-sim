# Biological Top-K Candidate-Site Validation Status

## Current State

```text
program = biological_topk_candidate_site_validation
contract = biological_topk_candidate_site_v1
contract_status = proposed
active_phase = 1
phase_0_status = pass
gpu_screen_status = experimental
bioinformatics_route = conditionally_reopened
scientific_object = clustered_TFO_query_target_candidate_site
claim_scope = set_preservation_with_top1_retention
rank_order_claim = diagnostic_only
score_representation = pending_phase1
```

Phase 0 establishes an independent evidence epoch. It does not validate the
new contract, run a fresh workload, select a fresh input pair, or promote the
GPU product status. Phase 1 is the next authorized phase but has not started;
its start receipt must bind the Phase 0 commit and its post-commit check.

## Immutable Historical Boundary

```text
strict_canonical_row_v1 = no_go
sequential_verified_v1 = no_go
canonical_hybrid_v2_correctness = pass
canonical_hybrid_v2_performance = no_go
canonical_hybrid_v2_rescue_track = closed
exact_ssw_cuda = closed
exact_ssw_cuda_final_decision = ssw_cuda_forward_or_reverse_checkpoint_only
historical_38.320882x_role = historical_candidate_performance_anchor
```

The historical files are bound by Git blob identity at execution-start commit
`2658a98fea8f34bd295892e6236607060e2f2803`. Live overview files may change in
later allowlisted phases; their frozen blobs do not.

## Phase 0 Evidence

- The clean-start check ran while the owner-provided protocol was outside the
  repository. Its status output was empty.
- `historical_blob_registry.tsv` rebuilds from `git show <start-head>:<path>`.
- `fresh_input_exclusion_registry.tsv` includes historical paper,
  Bioinformatics, canonical-hybrid-v2, SSW-CUDA, debug, adversarial, exhaustive,
  and deterministic-fuzz identities.
- Existing canonical-hybrid-v2 and final SSW-CUDA gates passed. The old paper
  Phase 0 gate correctly rejected the later SSW-CUDA runtime epoch; this guard
  result is retained rather than reclassified as a current paper-runtime pass.

Normative Phase 0 checks:

```text
python3 scripts/check_biological_topk_phase.py --phase 0 --mode precommit
python3 scripts/check_biological_topk_phase.py --phase 0 --mode postcommit
```
