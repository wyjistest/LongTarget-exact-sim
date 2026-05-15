# Fasim SIM-Close Learned Detector Dataset

Base branch:

```text
fasim-sim-recovery-score-landscape-detector-shadow
```

This document defines the first learned-detector milestone for SIM-close recovery. It adds a dataset/export path for offline training and evaluation of a learned SIM-gap risk detector. It does not train a model, load a model, change `FASIM_SIM_RECOVERY=1` behavior, or change default Fasim output.

## Scope

```text
Default Fasim output changed: no
SIM-close output behavior changed: no
Scoring/threshold/non-overlap behavior changed: no
GPU/filter behavior changed: no
Production learned model added: no
SIM labels used as runtime input: no
Recommended/default mode: no
```

The intended model shape is:

```text
Fasim-visible features -> learned risk detector / retriever
learned boxes or ranking -> bounded local SIM
bounded local SIM output -> deterministic guard / merge / validation
```

The learned detector must not directly predict final binding records. It may only help decide which candidate regions or candidate records deserve local SIM recovery and later deterministic filtering.

## Export

The real-corpus characterization runner accepts:

```bash
python3 scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py \
  --case LABEL DNA.fa RNA.fa \
  --validate-case LABEL \
  --learned-detector-dataset results/learned_detector_dataset.tsv \
  --learned-detector-dataset-report
```

The TSV is diagnostic/offline data. Rows come from Fasim output records, legacy SIM records when validation is requested, local executor candidates, and accepted candidates. This mix is intentional: Fasim/candidate rows represent deployable runtime candidates, while SIM rows make missed positives visible for offline taxonomy and training-set construction.

## Columns

The export includes stable identifiers, Fasim-visible geometry and score features, local recovery-box features, and post-hoc SIM labels:

```text
workload_label
run_index
candidate_id
source
validate_supported
validate_unsupported_reason
chr / genome_start / genome_end / query_start / query_end
genome_len / query_len
score / tri_score / nt / identity / mean_stability
rule / strand / direction
same_family_overlap_count
nearest_fasim_score_delta
local_rank
box_covered
box_count_covering
box_categories
cell_cost
label_available
label_in_sim
label_sim_only
label_shared_sim_close
label_guard_should_accept
label_miss_stage
```

`label_miss_stage` uses the same diagnostic vocabulary as the real-corpus miss taxonomy where possible:

```text
shared
not_box_covered
box_covered_but_executor_missing
guard_rejected
replacement_suppressed
canonicalization_mismatches
metric_ambiguity_records
extra
negative
unlabeled
```

SIM labels are post-hoc training labels only. They must not be used as runtime detector inputs, recovery-box inputs, guard inputs, replacement inputs, or output ordering inputs.

## Smoke Result

The learned-detector dataset smoke check runs the tiny validate fixture and verifies that:

```text
dataset TSV exists
header contains feature and label columns
rows are emitted
learned-detector telemetry is emitted
sim_label_columns = 1
output_mutations = 0
report states that labels are post-hoc only
```

The current smoke fixture produced 45 dataset rows across Fasim records, SIM records, executor candidates, and accepted candidates. This is only a harness check; it is not evidence that a learned detector is useful on production workloads.

## Decision

This PR should be treated as dataset/export infrastructure for the learned detector line. The companion model-shadow report is still offline and diagnostic-only; it does not add a production model or change runtime selection. A production-quality learned detector would still need broader real-corpus coverage plus held-out RNA, held-out target region, and held-out chromosome splits.

Do not train or ship a production learned detector from this report. Do not default or recommend SIM-close mode from this report.
