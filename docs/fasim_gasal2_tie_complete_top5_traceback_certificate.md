# Fasim GASAL2 Tie-Complete Top5 Traceback Certificate

This checkpoint adds default-off telemetry for a tie-complete final-top5
traceback certificate:

```bash
FASIM_GASAL2_TOP5_TRACEBACK_CERTIFICATE_SHADOW=1
```

The shadow keeps the authority path unchanged. It runs a GASAL2 score/end
prepass, records score-boundary telemetry for selected traceback attempts, and
physically runs the conservative certificate traceback set in shadow. The
shadow output is not used for scoring, endpoint, CIGAR, traceback, sorting,
dedup, non-overlap, or emitted output.

## Scope

This is a top5 artifact checkpoint only:

```text
no real pruning
no span predicate changes
fixed threshold 116 is historical oracle reference only
full lite equivalence: not claimed
full TFOsorted equivalence: not claimed
```

The historical fixed threshold result remains useful as an oracle reference, but
fixed threshold 116 is historical oracle reference only. It is not the
certificate algorithm.

## Certificate Boundary

A raw candidate rank5 threshold is unsound. High-score raw candidates can be
removed after traceback by invalid span checks, filtered_nt checks, CIGAR-
dependent filters, representative selection, or final dedup. Lower-score valid
retained rows may still enter the final top5 after those removals, and boundary
ties must be processed completely.

The only safe shape for a future real top5 certificate is:

```text
process candidates by global admissible upper-bound groups
update final retained unique top5 rows after traceback/convert/filter/dedup
stop only when all unprocessed upper bounds are strictly below rank5
retain all boundary ties
```

## Current Result

Committed result:

```text
docs/fasim_gasal2_tie_complete_top5_traceback_certificate.tsv
```

Smoke workload:

```text
chr22 slice 10M-12M, H19 query, lite output
```

Current support state:

```text
score_certificate_supported=true
stability_certificate_supported=false
nt_score_certificate_supported=false
```

Because stability and nt_score do not yet have admissible pre-traceback upper
bounds, their conservative candidate sets are all authority selected candidates.
The physical traceback set is the union of the score, stability, and nt_score
sets, so the unsupported modes force zero skipped tracebacks.

This means the current PR does not claim a working global top5 stopping
frontier. It establishes the telemetry and the conservative no-go condition:
until every published top5 ranking contract has an admissible bound, the
tie-complete certificate cannot reduce traceback work.

## Decision

Decision: `no_go_unsupported_modes`.

The telemetry is correctness-clean for the smoke workload, but it is not a
material pruning mechanism:

```text
top5 score rows/order clean
top5 stability rows/order clean
top5 nt_score rows/order clean
false_prune = 0
missing_top5_rows = 0
extra_top5_rows = 0
tracebacks_skipped = 0
```

Next work should either derive admissible pre-traceback upper bounds for
stability and nt_score, or keep the top5 certificate as a research-only
checkpoint. This PR does not implement real pruning and does not revive the
span-prune line.

## Validation

```bash
make build-fasim-gasal2 FASIM_GASAL2_TARGET=$PWD/.tmp/fasim_longtarget_gasal2_direct GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2
make check-fasim-gasal2-tie-complete-top5-traceback-certificate-parser
make check-fasim-gasal2-tie-complete-top5-traceback-certificate-smoke
make check-fasim-gasal2-tie-complete-top5-traceback-certificate-result
python3 -m py_compile scripts/summarize_fasim_gasal2_tie_complete_top5_traceback_certificate.py
git diff --check
```
