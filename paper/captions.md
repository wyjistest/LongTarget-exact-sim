# Figure Captions

## Figure 1. Contract-aware fast top-K execution

**A**, shared LongTarget task construction and downstream clustered TFO1-TFO5 semantics. **B1**, Fasim-LongTarget peak-guided reduction and CPU exact alignment. **B2**, the checked GASAL2 fast top-K path; no full-output replacement is implied. **C**, conceptual execution patterns. **D**, five paired H19 chr21+chr22 fast top-K runs on the recorded two-GPU machine; points are paired speedups and the line is the median. Source: `paper/source_data/paired_speedups.tsv`.

## Figure 2. Primary performance and preregistered generalization

**A**, five paired H19 chr21+chr22 fast top-K speedups with the median and deterministic bootstrap 95% interval. **B**, median paired speedup for 13 preregistered supported-query workloads under the score/stability/Nt clustered TFO1-TFO5 contract. Circles denote 10 contract-clean workloads; crosses retain three mismatch workloads. Labels report paired `n`; four breadth rows have `n=1` and no inferential interval. Hardware is the machine recorded in the frozen source data. Source: `paired_speedups.tsv`, `paired_speedup_summary.tsv`, and `generalization.tsv`.

## Figure 3. Scheduling, exact-column, work-volume, and resource ablations

**A**, paired two-slot versus synchronous GASAL2 speedups on chr21 and chr22 (`n=5` each, one worker per GPU), with median bootstrap 95% intervals. **B**, median exact-column stage and end-to-end speedups for H19 2 Mb and a KCNQ1OT1 2048-nt segment (`n=3` each); stage gains are not interpreted as equal end-to-end gains. **C**, measured device-memory and host-RSS peaks. **D**, candidate-to-baseline GASAL2 request and traceback count ratios computed from frozen run rows; both remain unchanged. All paired output gates were clean and fallbacks were zero. Source: `paired_speedups.tsv`, `paired_speedup_summary.tsv`, `ablation.tsv`, `resources.tsv`, and `benchmark_runs.tsv`.

## Figure 4. Operating envelope

Speedup by workload and output contract, with a dashed 1x parity line. Shapes distinguish full-output, short integrated, long-query boundary, and bounded max8 contracts. The max8 KCNQ1OT1 point has three paired repeats; historical full-output and boundary points are descriptive `n=1` evidence. Negative, fallback, and below-promotion results are retained. Source: `paper/source_data/operating_envelope.tsv`.

## Figure S1. Archive-first storage and bounded-memory merge

**A**, text and lossless archive bytes across three paired H19 2 Mb runs. **B**, peak RSS for in-memory and SQLite exact merge across three 150,000-row synthetic repetitions. **C**, median complete run plus restore and merge wall times. All six comparisons restored or merged byte-identical output. SQLite reduces memory at additional wall-time cost; storage reduction is not reported as compute acceleration. Source: `paper/source_data/archive_first.tsv`.
