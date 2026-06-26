# Fasim GASAL2 Phase 7 Gate C Stop Checkpoint

This checkpoint records the current Gate C result after the first1 descriptor
shadow gate. It does not complete the broad objective and does not authorize a
Gate C first64 run.

```text
phase7_gate_c_stop_checkpoint = current_source_no_go
```

## Evidence

```text
Command:
  make characterize-fasim-gasal2-phase7-gate-c-first1
  make check-fasim-gasal2-phase7-gate-c-first1-result

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 2,008
  gate_b_candidate_align_attempts = 2,008
  scoreinfo_reduced = 0
  oracle_scoreinfos = 718
  oracle_attempts = 2,872
  gpu_candidate_scoreinfos = 0
  gpu_candidate_attempts = 0
  missing_required_attempts = 0
  extra_candidate_attempts = 0
  gate_c_requested = 1
  gate_c_active = 1
  decision = phase7_gate_c_first1_no_go
  decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced
```

## Interpretation

```text
CPU-authority replay remains output-clean on first1.
Current Gate C does not generate GPU candidate descriptors.
Current Gate C does not reduce or replace scoreInfo/preAlign work.
Current Gate C source must not continue to first64 broad characterization.
No broad_replacement workload-matrix row may be added from this evidence.
```

## Stop Decision

```text
current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
gate_c_first64_allowed = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Restart Conditions

Gate C may restart only with a new GPU candidate descriptor source that proves
all of these on NEAT1 first1 before any first64 run:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
scoreinfo_reduced = 1
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
missing_required_attempts = 0
candidate_align_attempts <= 2,008
CPU aligner.Align() remains authority
GASAL2 output authority = 0
no GPU endpoint authority
no GPU CIGAR or traceback authority
```

Only after that may the roadmap proceed to the Gate C NEAT1 first64 broad
gate.
