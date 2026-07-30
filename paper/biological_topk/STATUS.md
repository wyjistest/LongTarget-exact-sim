# Biological Top-K Candidate-Site Validation Status

## Current State

```text
program = biological_topk_candidate_site_validation
contract = biological_topk_candidate_site_v1
contract_status = in_validation
active_phase = 2
phase_0_status = pass
phase_1_status = pass
gpu_screen_status = experimental
bioinformatics_route = conditionally_reopened
scientific_object = clustered_TFO_query_target_candidate_site
claim_scope = set_preservation_with_top1_retention
rank_order_claim = diagnostic_only
score_representation = integral_exact
```

Phase 0 establishes an independent evidence epoch. It does not validate the
new contract or promote the GPU product status. Phase 1 freezes the scientific
object, exact contract, source universes, statistical design, experimental
estimands, operating envelope, and owner-approved fixed budget. All Phase 1
gates pass and Phase 2 is authorized. No fresh pair was selected and no new A/G
prediction ran.

## Phase 1 Evidence

```text
contract_schema_version = 2
score_integrality_supported_rows = 766261
score_nonintegral_rows = 0
n_binary_required = 124
k_min = 122
allowed_failures = 2
candidate_N_panel = 178
joint_information_probability_point = 0.9575
joint_information_probability_lcb = 0.9526
fresh_unique_query_digests = 27060
fresh_unique_target_digests_short_medium_large = 666,618,539
scheduled_elapsed_upper_95_seconds = 20576.305696676598
gpu_hours_upper_95 = 0.56136173127435929
artifact_storage_upper_95_bytes = 5508762270
max_artifact_storage_bytes = 8589934592
fixed_budget_gate_pass = true
```

The candidate panel size is the smallest solution satisfying statistical,
source-capacity, elapsed, GPU-hour, and storage gates. The owner-approved 8 GiB
quota is frozen in `owner_storage_quota_approval.json` and may not be raised
after the Phase 3 manifest projection. Phase 2 may use historical consumed data
only; fresh selection remains prohibited until Phase 3.

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
