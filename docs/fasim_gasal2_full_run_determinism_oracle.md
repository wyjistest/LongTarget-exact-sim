# Fasim GASAL2 Full-Run Determinism Oracle

## Scope

This checkpoint adds an offline oracle for repeated full-run GASAL2 outputs. It
does not change Fasim runtime behavior, output generation, scoring, CIGAR,
traceback, sort/de-duplication, archive schema, scheduling, or GPU execution.

The purpose is to make later pipeline experiments reviewable. A double-buffer or
other asynchronous prototype must be compared against a known repeatability
baseline instead of treating every full-run row difference as a new regression.

## Tools

Parser/synthetic gate:

```bash
make check-fasim-gasal2-full-run-determinism-oracle-parser
```

Offline comparator:

```bash
python3 scripts/compare_fasim_full_run_determinism.py \
  --run run1.lite \
  --run run2.lite \
  --run run3.lite \
  --k 5 \
  --output-summary determinism_summary.txt \
  --output-pairs determinism_pairs.tsv
```

Optional chr22 runner:

```bash
make characterize-fasim-gasal2-full-run-determinism-chr22
make check-fasim-gasal2-full-run-determinism-chr22-result
```

The runner also supports reusing existing outputs:

```bash
REUSE_RUNS=run1.lite:run2.lite:run3.lite \
WORK=.tmp/characterize_fasim_gasal2_full_run_determinism_chr22 \
bash scripts/characterize_fasim_gasal2_full_run_determinism_chr22.sh
```

## Oracle Contract

The comparator reports:

```text
byte_stable
set_stable
multiset_stable
top5_score_stable
top5_stability_stable
top5_nt_score_stable
max_pair_set_missing / extra
max_pair_multiset_missing / extra
first_missing_set / first_extra_set
first_missing_multiset / first_extra_multiset
classification
```

Pairwise TSV rows include byte, set, multiset and top5 equality for every run
pair.

## chr22 Result

Using the already generated chr22/H19 rule-0 runs from the flush wait-state
checkpoint:

```text
work = .tmp/characterize_fasim_gasal2_full_run_determinism_chr22
runs = off, off2, telemetry-on

schema           = lite
byte_stable      = false
set_stable       = false
multiset_stable  = false

top5_score_stable     = true
top5_stability_stable = true
top5_nt_score_stable  = true

min_rows        = 388,819
max_rows        = 388,820
min_unique_rows = 386,936
max_unique_rows = 386,937

max_pair_set_missing      = 0
max_pair_set_extra        = 1
max_pair_multiset_missing = 0
max_pair_multiset_extra   = 1

classification = row_set_nondeterminism_topk_stable
```

The unstable row is:

```text
45460439 45460484 AntiMinus rule=2 query=2385..2438 score=72 nt=54
```

Pairwise result:

```text
off  vs off2: byte=false set=false multiset=false top5=true
off  vs on  : byte=false set=false multiset=false top5=true
off2 vs on  : byte=false set=true  multiset=true  top5=true
```

## Decision

The current chr22 full-output path is not byte-stable and not fully row-set
stable across the three observed runs. The instability is currently one extra
low-score row and does not affect the three top5 contracts.

Therefore, the next asynchronous or double-buffer prototype must use this
oracle as its correctness boundary:

```text
top5 contracts must remain stable
full row-set deltas must not exceed the established repeat baseline
new missing rows are a hard failure
new high-score/top5 deltas are a hard failure
```

This checkpoint does not justify enabling any asynchronous path. It only makes
the next prototype measurable.
