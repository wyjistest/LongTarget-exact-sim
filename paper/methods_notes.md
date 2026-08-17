# Methods Notes

These notes are implementation- and manifest-backed source material. They do
not introduce defaults that are absent from the frozen protocol.

## Software And Build

- Paper runtime epoch: `0`; runtime commit:
  `0d11aa2d61b7ccda59b462ab8e0750dad17ee18f`.
- GASAL2 commit: `106d94ee53fc847214fb05f2f9f892538a5d3baf`.
- Checked GASAL2 constants: `GPU_SM_ARCH=sm_89`, `MAX_QUERY_LEN=2812`, and
  `N_CODE=0x4E`.
- Build and preset authority: `paper/benchmark_protocol.md`,
  `paper/workload_manifest.tsv`, and the per-pair config receipts covered by
  `paper/phase2_artifact_manifest.tsv` through
  `paper/phase4_artifact_manifest.tsv`.

## Hardware And Scheduling

- Primary machine: Intel Core i9-10900X, 10 physical cores, 128 GiB-class RAM,
  and two NVIDIA GeForce RTX 4090 GPUs with 24,564 MiB each.
- NVIDIA driver 555.42.06; CUDA toolkit 12.5.82; g++ 9.4.0; Python 3.11.10.
- CPU affinity and clocks were not fixed. The captured CPU governor was
  `powersave`; GPU persistence was disabled and application clocks were not
  controlled.
- Supported low-density overlap scope: one worker per GPU. The harness assigned
  visible devices per run. C1 used two GPUs; other GPU rows used the count in
  `paper/workload_manifest.tsv`.

## Inputs And Preprocessing

- Thirteen unique query, target, and derived inputs are defined by authority
  URL, license note, byte size, SHA-256, path convention, workload mapping and
  reconstruction command in `reproduce/input_manifest.tsv`.
- Derived chr21+chr22 input is a byte concatenation in chr21/chr22 order.
- The chr22 2 Mb target is the zero-based half-open interval
  `[10000000,12000000)`, emitted with header `chr22_slice_10m_12m` and width 80.
- Query fragment coordinates, rules, target regions, preset IDs and output
  contracts are frozen in `paper/workload_manifest.tsv`.

## Output And Correctness Contracts

- Fast top-K contract: separately compare score-, stability-, and Nt-ranked
  clustered TFO1-TFO5. Full TFOsorted row-set equality is not implied.
- Full-output contract: compare byte or row-set equality as specified by the
  workload, then apply all three clustered top-five comparators.
- Preflight guards: unsupported full-length MALAT1, NEAT1 and KCNQ1OT1 inputs
  must be rejected before GPU execution.
- Fallback, overflow, state/order violation, allocation failure and OOM evidence
  remains explicit. Mismatch pairs are retained rather than excluded.

## Experimental Design

- Pair order was deterministically interleaved AB/BA with seed `20260715`.
- Repeat counts, timeout limits, GPU counts and timing boundaries are defined per
  row by `paper/workload_manifest.tsv` and `paper/benchmark_protocol.md`.
- Wall-time comparisons require matching query/target digests, runtime epoch,
  preset, output contract and non-variant configuration.
- Two-slot comparisons use the same checked preset with synchronous and overlap
  scheduling. Archive storage, restore, merge, RSS and run-plus-merge wall time
  are reported separately. Exact-column stage and end-to-end timings are also
  reported separately.

## Statistics

- Source data freeze: `paper-data-v1-dccfd49-20260716`.
- Paired speedup is baseline wall time divided by candidate wall time for each
  compatible pair.
- Summaries report median, inclusive IQR, range and a 10,000-resample bootstrap
  95% interval with seed `20260715` when `n >= 3`; no inferential interval is
  emitted for smaller samples.
- Authority: `reproduce/analyze_results.py` and
  `paper/source_data/paired_speedup_summary.tsv`.

## Archive Merge And Fallback Semantics

- Archive-first restore must be byte-identical under the checked restore
  contract. Storage reduction is not classified as compute speedup.
- The bounded SQLite merge is exact for the checked rows and trades additional
  wall time for lower peak RSS.
- Any unsupported shape, resource guard, allocation failure or contract
  mismatch fails closed and remains represented in correctness or exclusions
  source data.
