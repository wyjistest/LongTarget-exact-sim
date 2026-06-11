# Fasim TFOsorted CIGAR Archive Probe

This checkpoint validates a default-off archive probe for the expensive full
`.TFOsorted` text materialization path.

## Scope

```text
FASIM_TFOSORTED_CIGAR_ARCHIVE_PROBE=1:
  diagnostic archive probe only

Archive payload:
  full output scalar fields
  CIGAR

Restore inputs:
  archive TSV
  query FASTA
  target FASTA

Not changed:
  default output behavior
  scoring
  candidate selection
  endpoint/CIGAR authority
  GASAL2 correctness contract
  TFO row sorting or merge semantics
```

The probe is not a compact final archive format. It is a runtime validation
that aligned TFO/TTS strings can be deferred and reconstructed later from
coordinates, strand, FASTA sequences, and CIGAR.

## Correctness Gate

Same-run archive restore is the correctness gate:

```text
archive full `.TFOsorted`
vs
restored `.TFOsorted` from same-run archive
```

This avoids conflating archive restore correctness with rare cross-run GASAL2
row nondeterminism.

## Results

### chr22 2Mb Smoke, Full + Archive

```text
target = .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
mode = FASIM_OUTPUT_MODE=tfosorted

archive_full_restored_match = 1
baseline_restored_match = 1
full_wall_seconds = 3.256091
archive_wall_seconds = 3.446806
restore_wall_seconds = 0.159010
full_bytes = 1,836,889
archive_bytes = 1,279,457
full_convert_alignment_seconds = 1.22986
archive_convert_alignment_seconds = 1.42279
```

This proves byte-identical same-run restoration on a small checked slice.

### chr22 2Mb Smoke, Lite + Archive

```text
target = .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
mode = FASIM_OUTPUT_MODE=lite

baseline_restored_match = 1
full_wall_seconds = 3.288558
archive_wall_seconds = 2.356873
restore_wall_seconds = 0.168472
full_convert_alignment_seconds = 1.24764
archive_convert_alignment_seconds = 0.330499
full_cpu_traceback_convert_seconds = 1.29553
archive_cpu_traceback_convert_seconds = 0.37096
```

This shows the intended performance shape: keep the normal runtime from
materializing full aligned strings, then restore full text later if needed.

### chr22 Full, Full + Archive

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
mode = FASIM_OUTPUT_MODE=tfosorted

archive_full_restored_match = 1
full_wall_seconds = 100.724228
archive_wall_seconds = 108.881667
restore_wall_seconds = 4.806259
full_bytes = 88,102,116
archive_bytes = 62,156,692
full_convert_alignment_seconds = 48.0098
archive_convert_alignment_seconds = 55.1644
```

Full + archive is expected to be slower because it writes both full text and
the archive. Its value is restore equivalence, not performance.

### chr22 Full, Lite + Archive

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
mode = FASIM_OUTPUT_MODE=lite

full_wall_seconds = 101.008951
archive_wall_seconds = 66.044326
restore_wall_seconds = 4.792546
runtime_speedup = 1.529x
full_convert_alignment_seconds = 48.2869
archive_convert_alignment_seconds = 13.0605
full_cpu_traceback_convert_seconds = 50.1539
archive_cpu_traceback_convert_seconds = 14.6504
archive_bytes = 62,156,692
```

### chr1 Full, Lite + Archive

```text
target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
mode = FASIM_OUTPUT_MODE=lite
baseline_full_wall_seconds = 563.419139
archive_wall_seconds = 371.369001
restore_wall_seconds = 19.242416
runtime_speedup = 1.517x
runtime_saved_seconds = 192.050138

baseline_full_cpu_traceback_convert_seconds = 275.076
archive_cpu_traceback_convert_seconds = 80.2493
convert_speedup = 3.428x
convert_saved_seconds = 194.8267

full_bytes = 356,712,668
archive_tsv_bytes = 253,279,549
```

This validates that an archive-style output can replace most of the expensive
CPU convert/string materialization path for the chr1 GASAL2 run. The current
TSV archive is still too large to be the final storage format.

## Decision

```text
Direct archive output:
  go as a milestone probe

Current TSV archive:
  not final storage format

Direct compact binary archive:
  smoke-clean prototype

Do not claim:
  full GASAL2 output equivalence
  aligner.Align replacement
  final compact archive format
```

The post-hoc optimized reference archive already showed that chr1 full output
can compress to about 19 MB with byte-identical restore, but that path reads the
already generated full text. The next real step is to combine both results:
write the compact archive directly at runtime without generating aligned string
columns first.

## Direct Compact Probe

`FASIM_TFOSORTED_COMPACT_ARCHIVE_PROBE=1` adds a second default-off probe that
writes a compact binary `.compact-archive.tfoa` file directly at runtime.

The format stores:

```text
delta-varint:
  QueryStart
  StartInSeq
  Score

varint:
  alignment length
  ungapped query length
  ungapped target length
  Rule
  Nt(bp)
  direction/strand flags

bytes:
  MeanStability text
  MeanIdentity text
  TFO gap mask
  TTS gap mask
```

For this probe, restore derives `QueryEnd`, `EndInSeq`, `StartInGenome`,
`EndInGenome`, `Class`, `MidPoint`, `Center`, `TFO sequence`, and
`TTS sequence` from the archive row plus query/target FASTA. The writer fails
closed if a row does not match the currently validated short-query/H19 output
shape:

```text
Direction = R
Chr = empty
StartInGenome = StartInSeq
EndInGenome = EndInSeq
Class = 0
MidPoint = Center
```

### chr22 2Mb Compact Smoke, Full + Archive

```text
mode = FASIM_OUTPUT_MODE=tfosorted

archive_full_restored_match = 1
run_wall_seconds = 3.489433
restore_wall_seconds = 0.242529
full_bytes = 1,836,889
archive_bytes = 377,114
archive_gzip_bytes = 151,520
convert_alignment_seconds = 1.39433
cpu_traceback_convert_seconds = 1.44924
```

### chr22 2Mb Compact Smoke, Lite + Archive

```text
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 2.377371
restore_wall_seconds = 0.238533
archive_bytes = 377,114
archive_gzip_bytes = 151,520
restored_bytes = 1,836,889
convert_alignment_seconds = 0.315158
cpu_traceback_convert_seconds = 0.354938
```

This is the first runtime-direct evidence that the compact archive idea can
both restore byte-identical `.TFOsorted` output and preserve the fast
`lite`-mode bypass of full aligned string materialization.

### chr22 Full Compact, Lite + Archive

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 66.373801
restore_wall_seconds = 7.997919
archive_bytes = 17,687,710
archive_gzip_bytes = 7,039,466
restored_bytes = 88,102,125
convert_alignment_seconds = 12.4588
cpu_traceback_convert_seconds = 14.0494
output_write_seconds = 1.12475
```

This keeps the runtime benefit of the TSV archive probe while reducing chr22
archive size from 62.2 MB TSV to 17.7 MB raw compact binary, or 7.0 MB after
gzip.

### chr1 Full Compact, Lite + Archive

```text
target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 375.515612
restore_wall_seconds = 32.216347
archive_bytes = 71,289,307
archive_gzip_bytes = 28,360,621
restored_bytes = 356,713,127
convert_alignment_seconds = 69.3466
cpu_traceback_convert_seconds = 77.9887
output_write_seconds = 4.63015
```

Compared with the previous chr1 full `.TFOsorted` baseline:

```text
full wall = 563.419139s
direct compact-lite wall = 375.515612s
runtime speedup = 1.500x
runtime saved = 187.903527s

full cpu traceback convert = 275.076s
direct compact cpu traceback convert = 77.9887s
convert speedup = 3.527x
convert saved = 197.0873s

full text bytes = 356,712,668
direct compact gzip bytes = 28,360,621
```

The direct compact writer therefore validates the runtime half of the archive
idea on chr1: it avoids most of the 275s aligned string materialization path.
It does not yet match the 19 MB post-hoc `opt_ref` archive, because this
runtime probe is row-oriented. The remaining storage win likely requires the
post-hoc design's block column layout and per-block dictionaries.

## Direct Column Probe

`FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1` adds a third default-off probe that
writes a block-column binary `.column-archive.tfoa` file directly at runtime.
It keeps the same restore contract as the compact probe, but buffers rows into
blocks and writes each field as a separate payload:

```text
block rows:
  65,536

delta-varint columns:
  QueryStart
  StartInSeq
  Score
  alignment length

varint columns:
  ungapped query length
  ungapped target length
  Rule
  Nt(bp)

byte columns:
  direction/strand flags
  TFO gap mask
  TTS gap mask

per-block dictionary columns:
  MeanStability
  MeanIdentity
```

The current column probe uses per-block dictionaries for the two repeated text
score columns. This keeps the direct runtime write path while recovering part
of the post-hoc column archive's storage win. The archive format version is 2
for this dictionary layout.

### chr22 2Mb Column Smoke, Full + Archive

```text
mode = FASIM_OUTPUT_MODE=tfosorted

archive_full_restored_match = 1
run_wall_seconds = 3.457412
restore_wall_seconds = 0.226333
full_bytes = 1,836,889
archive_bytes = 321,411
archive_gzip_bytes = 133,991
restored_rows = 8,291
dictionary_payloads = 2
convert_alignment_seconds = 1.41066
cpu_traceback_convert_seconds = 1.46553
```

### chr22 2Mb Column Smoke, Lite + Archive

```text
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 2.308468
restore_wall_seconds = 0.229149
archive_bytes = 321,411
archive_gzip_bytes = 133,991
restored_rows = 8,291
dictionary_payloads = 2
restored_bytes = 1,836,889
convert_alignment_seconds = 0.32878
cpu_traceback_convert_seconds = 0.368517
```

### chr22 Full Column, Lite + Archive

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 66.465195
restore_wall_seconds = 7.878062
archive_bytes = 13,783,660
archive_gzip_bytes = 5,491,182
restored_rows = 388,819
dictionary_payloads = 12
restored_bytes = 88,101,920
convert_alignment_seconds = 12.948
cpu_traceback_convert_seconds = 14.5279
output_write_seconds = 1.26732
```

Compared with the direct row compact probe on chr22:

```text
row compact gzip = 7,039,466
dictionary column gzip = 5,491,182
size reduction = 22.0%
```

Compared with the previous non-dictionary direct column probe:

```text
old column gzip = 5,979,220
dictionary column gzip = 5,491,182
size reduction = 8.2%
```

### chr1 Full Column, Lite + Archive

```text
target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
mode = FASIM_OUTPUT_MODE=lite

run_wall_seconds = 374.422819
restore_wall_seconds = 31.725864
archive_bytes = 55,223,107
archive_gzip_bytes = 22,230,378
restored_rows = 1,577,067
dictionary_payloads = 50
restored_bytes = 356,713,160
convert_alignment_seconds = 71.997
cpu_traceback_convert_seconds = 80.5742
output_write_seconds = 5.34477
```

Compared with the direct row compact probe on chr1:

```text
row compact gzip = 28,360,621
dictionary column gzip = 22,230,378
size reduction = 21.6%
```

Compared with the previous non-dictionary direct column probe:

```text
old column gzip = 24,182,057
dictionary column gzip = 22,230,378
size reduction = 8.1%
```

Compared with the previous full `.TFOsorted` baseline:

```text
full wall = 563.419139s
direct dictionary-column-lite wall = 374.422819s
runtime speedup = 1.505x
runtime saved = 188.996320s

full cpu traceback convert = 275.076s
direct dictionary-column cpu traceback convert = 80.5742s
convert speedup = 3.414x
convert saved = 194.5018s

full text bytes = 356,712,668
direct dictionary-column gzip bytes = 22,230,378
```

The dictionary block-column probe improves storage over both the row compact
writer and the first non-dictionary column writer while preserving the runtime
benefit. It still does not reach the 19 MB post-hoc `opt_ref` result; chr1
remains about 16.9% larger than that post-hoc archive. The remaining gap likely
requires a more specialized reference or block payload model, not another small
adjustment to the current row-derived field set.

## Check

```bash
make check-fasim-tfosorted-cigar-archive-probe
make check-fasim-tfosorted-compact-archive-probe
make check-fasim-tfosorted-column-archive-probe
```

The check runs the small chr22 2Mb smoke in both `tfosorted` and `lite` modes.
The `tfosorted` row proves same-run byte-identical restore; the `lite` row
proves the string-materialization bypass path remains wired.
