# Fasim GASAL2 Phase 7 v3 Next Source Design

This checkpoint defines the only valid next Path B design step after the real
narrow certificate coverage proof ruled out the existing exact-column GPU
scoreInfo source.

It is design-only. It does not add runtime code, does not claim performance,
and does not allow GASAL2/GPU endpoint, CIGAR, traceback, output, or digest to
become authority.

```text
phase7_broad_restart_v3_next_source_design = defined
phase7_broad_restart_v3_next_source_status = design_only
phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why A New Source Is Required

The current v3 source family has been exhausted:

```text
all-column certificate:
  Gate v3.1 pass
  not replayable
  candidate_attempts = 168,730,848
  candidate_attempt_ratio = 58,750.30x
  do_not_continue_all_column_replay = 1

bounded narrow probe:
  plumbing works
  false negatives remain
  missing required attempts remain
  do_not_continue_bounded_narrow_probe = 1

existing exact-column GPU scoreInfo:
  non-opt-in launch fails
  shared-memory opt-in launches but scoreInfo mismatches
  previous_exact_column_candidate_status = no_go
  do_not_continue_existing_exact_column_gpu_scoreinfo = 1
```

The direct prerequisite is:

```text
phase7_broad_restart_v3_real_narrow_certificate_coverage_proof =
  exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
phase7_broad_restart_v3_next_gate =
  different_exact_scoreinfo_source_or_seed_certificate
```

## Allowed Next Sources

Only two source families are allowed to continue Path B.

```text
allowed_source_1 = different_exact_scoreinfo_compatible_gpu_execution
allowed_source_2 = seed_or_index_certificate
```

### Source 1: Different Exact ScoreInfo-Compatible GPU Execution

This source must reproduce the legacy scoreInfo candidate contract directly,
but through a different execution design than the existing exact-column GPU
source.

Examples of allowed design differences:

```text
SSW-compatible byte/word scoreInfo execution
lower-shared-memory exact-column execution
two-stage exact scoreInfo reduction
query/profile resident scoreInfo pass
```

Required proof before replay:

```text
descriptor_source_before_cpu_scoreinfo = 1
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < 168,730,848
candidate_attempts < reference_align_attempts required before v3.2
```

### Source 2: Seed Or Index Certificate

This source may avoid reproducing all scoreInfo internals only if it proves the
candidate coverage contract independently.

Allowed shape:

```text
seed hits or index intervals become candidate descriptors
candidate certificate compares descriptors against CPU-required attempts
CPU scoreInfo/preAlign is not run for every task before descriptor generation
CPU aligner.Align() remains output authority
```

Required proof before replay:

```text
descriptor_source_before_cpu_scoreinfo = 1
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < 168,730,848
candidate_attempts < reference_align_attempts required before v3.2
```

## Gate Sequence

The next implementation must be staged. Do not skip directly to first64.

```text
first1_descriptor_smoke_before_replay = 1
first64_broad_gate_only_after_first1_replay = 1
```

### Gate v3.1a: First1 Descriptor Smoke

Required telemetry:

```text
gpu_or_native_candidate_scoreinfos > 0
gpu_or_native_candidate_attempts > 0
descriptor_source_before_cpu_scoreinfo = 1
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_checked = 1
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < 168,730,848
```

Stop if:

```text
candidate descriptors are empty
CPU scoreInfo/preAlign is still doing baseline work
false negatives appear
missing required attempts appear
candidate attempts grow toward all-column replay scale
```

### Gate v3.2: First1 CPU-Authority Replay

Required telemetry:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
fallback_accounting_clean = true
```

Authority remains:

```text
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

Stop if:

```text
output differs
fallbacks hide the candidate path
Align-side attempts are not reduced
```

### Gate v3.3: First64 Broad Gate

Required telemetry:

```text
full_rows_equal = true
digest_match = true
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
```

Only after this gate may the workload matrix add:

```text
contract = broad_replacement
```

## Forbidden Shortcuts

```text
no broad_replacement workload-matrix row
do not use top5-only evidence
do not use output drift as speedup
do not use all-column replay as a runtime candidate
do not use the bounded narrow probe as a coverage proof
do not use the existing exact-column GPU scoreInfo source
do not let GPU endpoint/CIGAR/traceback/output become authority
```

## Decision

This checkpoint does not pass Gate v3.1 or Gate v3.2. It only turns the
current `different_exact_scoreinfo_source_or_seed_certificate` next gate into a
testable design contract.

```text
phase7_broad_restart_v3_next_source_design = defined
phase7_broad_restart_v3_next_source_status = design_only
phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
claimed_broad_replacement_rows = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
