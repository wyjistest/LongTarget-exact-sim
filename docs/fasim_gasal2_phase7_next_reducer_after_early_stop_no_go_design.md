# Fasim GASAL2 Phase 7 Next Reducer After Early-Stop No-Go Design

This is a docs-only design checkpoint after measured Phase 7 early-stop
runtime failed the NEAT1 first1 correctness gate.

It is not runtime code, not a broad completion claim, and not permission to use
GASAL2 endpoint/CIGAR/traceback/output as authority.

```text
phase7_next_reducer_after_early_stop_no_go_design = defined
```

## Stop Evidence

The measured early-stop runtime candidate is stopped:

```text
early_stop_runtime_first1 = correctness_no_go

neat1_first1:
  digest_match = 0
  full_rows_equal = 0
  missing_rows = 7
  extra_rows = 5
  triplex_mismatches = 12
  candidate_align_attempts = 1,309
  reference_align_attempts = 2,872
  align_attempt_reduction = 1,563
  decision = phase7_frontier_early_stop_runtime_first1_no_go
```

Interpretation:

```text
The candidate reduced CPU Align attempts, but it changed output. Output drift
cannot be counted as speedup. Do not continue the measured early-stop
candidate to NEAT1 first64.
```

## Root Cause Boundary

The failed runtime candidate combined two separate ideas:

```text
1. coverage:
   use segmented GASAL2 score prepass to provide candidate attempts

2. reduction:
   stop CPU traceback replay after a scoreInfo-local selected attempt
```

The frontier-log characterization showed that scoreInfo-local early stop is a
plausible reducer only after exact coverage is already available. The measured
runtime failed because the runtime candidate did not first prove that the
candidate stream covered the CPU-authority frontier needed to reproduce output.

The next design must therefore be coverage-first:

```text
candidate coverage before candidate reduction
coverage-first all-attempt CPU replay before any GASAL2-pruned candidate stream
```

## Authority

Allowed:

```text
CPU aligner.Align() remains authority
CPU converted rows remain row/output/digest authority
GASAL2 may propose candidate descriptors only after coverage proof
```

Forbidden:

```text
GASAL2 output authority = 0
no GPU endpoint authority
no GPU CIGAR or traceback authority
no direct continuation of the failed early-stop runtime candidate to first64
no broad completion from first1-only evidence
no broad completion unless scoreInfo/preAlign work and Align-side work are both reduced
```

## Next Architecture

The next architecture should split Phase 7 into three gates.

### Gate A: all-attempt early-stop runtime first1

Goal:

```text
Run the measured CPU-authority early-stop reducer over the complete built
attempt stream, not over a segmented GASAL2-pruned candidate stream.
```

Required behavior:

```text
build all legacy attempts for each scoreInfo
preserve legacy scoreInfo order
preserve legacy attempt order
CPU aligner.Align() evaluates each attempted row
after a scoreInfo-local selected row, skip only later attempts in that same scoreInfo
no GASAL2 candidate pruning
no GASAL2 endpoint/CIGAR/traceback/output authority
```

Gate:

```text
NEAT1 first1:
  digest_match = 1 or full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts < reference_align_attempts
```

Expected role:

```text
This proves that runtime early-stop itself can be correct when coverage is
complete. It does not prove broad completion because scoreInfo/preAlign work is
not reduced yet.
```

Current evidence:

```text
status = correctness_go_needs_first64
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts = 2,008
reference_align_attempts = 2,872
align_attempt_reduction = 864
candidate_vs_baseline = near_parity_across_reruns
decision = phase7_all_attempt_early_stop_runtime_first1_go
```

### Gate B: all-attempt early-stop runtime first64

Run only if Gate A passes.

Gate:

```text
NEAT1 first64:
  digest_match = 1 or full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts < reference_align_attempts
  candidate_wall_seconds < baseline_wall_seconds
```

Decision:

```text
If Gate B is correctness-clean but not faster, keep it as diagnostic only.
If Gate B is faster but scoreInfo/preAlign work is unchanged, it still cannot
complete the broad objective.
```

Current evidence:

```text
status = correctness_go_near_parity_not_broad
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts = 140,087
reference_align_attempts = 211,976
align_attempt_reduction = 71,889
candidate_vs_baseline = near_parity_across_reruns
decision = phase7_all_attempt_early_stop_runtime_first64_go
```

### Gate C: coverage-preserving GPU candidate generator

Run only after Gate A and Gate B establish a correct CPU-authority reduction
target. Gate A and Gate B now satisfy correctness and Align-side reduction, but
they do not satisfy broad completion because scoreInfo/preAlign work is still
CPU work and first64 wall time is only near parity.

Goal:

```text
Introduce a GASAL2 or GPU-assisted candidate generator only if it preserves the
all-attempt early-stop frontier.
```

Required proof:

```text
candidate coverage before candidate reduction
no selected frontier false negatives
no task-local frontier drift
no scoreInfo-local emission drift
same row set as Gate A/Gate B CPU-authority output
```

Gate:

```text
NEAT1 first1:
  digest_match = 1 or full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  candidate_align_attempts <= Gate A candidate_align_attempts
  scoreInfo/preAlign work reduced or replaced
```

Broad completion still requires:

```text
NEAT1 first64:
  full claimed output contract clean
  candidate_wall_seconds < baseline_wall_seconds
  candidate_vs_baseline > 1.0
  scoreInfo/preAlign work must be reduced before broad completion
  Align-side work must be reduced or replaced before broad completion
```

## Stop Conditions

Stop this line if:

```text
Gate A changes output
Gate A does not reduce Align attempts
Gate B changes output
Gate B is slower or not materially faster
Gate C cannot preserve coverage
Gate C reduces candidate work but changes row/output/digest authority
```

## Decision

```text
If Gate A fails:
  stop Phase 7 reducer work until the legacy state machine has a stronger
  runtime representation.

If Gate A passes but Gate B is no-go:
  keep all-attempt early stop as a small diagnostic only.

If Gate B passes but Gate C cannot reduce scoreInfo/preAlign work:
  do not call the broad objective complete.

If Gate C passes first1 and first64:
  add a broad_replacement workload matrix row only after all Phase 6 Path B
  requirements pass.
```

Current status:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Gate C Design

```text
phase7_gate_c_gpu_candidate_generator_design = defined

Document:
  docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md

Design:
  coverage-preserving GPU candidate generator
  candidate coverage before candidate reduction
  all-attempt early-stop frontier remains the comparison target

Requirement:
  scoreInfo/preAlign work reduced or replaced
  candidate_align_attempts <= Gate B candidate_align_attempts
  workload matrix broad_replacement row is forbidden until Gate C first64 passes

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no real opt-in

Current status:
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```
