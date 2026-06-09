# Fasim GASAL2 Score-Prepass State-Machine Characterization

This is a characterization checkpoint for the default-off segmented
score-prepass state-machine shadow.

It does not add a production path. CPU Fasim output remains the authority.

## Runtime Shape

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1
FASIM_ALIGN_GASAL2=1
```

The shadow:

```text
1. builds legacy scoreInfo extend attempts
2. uses segmented GASAL2 score-prepass over bounded query segments
3. expands selected attempts to the per-scoreInfo legacy prefix
4. runs the legacy threshold / best-end / last state machine
5. CPU-aligns only selected/fallback attempts for shadow conversion
6. compares triplexes against CPU authority
7. never writes GPU/GASAL2 output into candidate state, output, or digest
```

## Results

```text
NEAT1 first1:
  digest clean
  tasks = 48
  attempts = 2,872
  raw selected hits = 9,995
  state-machine CPU align attempts = 51
  triplex mismatches = 0
  candidate_vs_baseline = 0.530629x

NEAT1 first4:
  digest clean
  tasks = 192
  attempts = 13,028
  raw selected hits = 45,900
  state-machine CPU align attempts = 643
  triplex mismatches = 0
  candidate_vs_baseline = 0.568306x

NEAT1 first16:
  digest clean
  tasks = 768
  attempts = 53,968
  raw selected hits = 190,897
  state-machine CPU align attempts = 13,474
  triplex mismatches = 0
  candidate_vs_baseline = 0.522888x

MALAT1 first8:
  digest clean
  tasks = 1,824
  attempts = 125,088
  raw selected hits = 218,581
  state-machine CPU align attempts = 6,188
  triplex mismatches = 0
  candidate_vs_baseline = 0.702397x
```

All characterized rows had:

```text
scoreinfo_mismatches = 0
realpath_fallbacks = 0
length_guard_fallbacks = 0
state_machine_fallbacks = 0
state_machine_triplex_mismatches = 0
```

## Interpretation

The segmented state-machine consumer is correctness-clean on these bounded
NEAT1 and MALAT1 rows. That is a real improvement over the whole-query selector
boundary and over selected-only replay.

It is still not a performance candidate. The candidate runs include diagnostic
shadow overhead and remain slower than CPU baseline:

```text
NEAT1: 0.52-0.57x baseline
MALAT1 first8: 0.70x baseline
```

The main remaining cost is not GASAL2 score-only alone. The shadow still pays:

```text
real CPU scoreInfo extend path
segmented GASAL2 score-prepass
prefix-expanded state-machine CPU align/convert
```

For NEAT1 first16, state-machine CPU align attempts already reach 13,474.
For MALAT1 first8, the legacy realpath still performs 74,646 align attempts
while the state-machine shadow adds 6,188 more.

## Decision

```text
Correctness/shape:
  go as default-off shadow scaffold

Performance:
  no-go for current shadow implementation

Real path:
  no
```

Do not promote:

```text
real opt-in
GPU endpoint authority
GPU CIGAR/traceback authority
GPU/GASAL2 output authority
selected-only replay
whole-query GASAL2 selector for long queries
```

Only continue if the next implementation removes the duplicate CPU realpath
work and proves the state-machine selected/fallback CPU traceback path can
replace enough align attempts under external digest validation.

## Gates

```bash
bash scripts/characterize_fasim_gasal2_score_prepass_state_machine_consumer.sh
bash scripts/check_fasim_gasal2_score_prepass_state_machine_characterization.sh
```
