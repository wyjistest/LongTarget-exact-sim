# Fasim Real-Corpus Profile

Base branch:

```text
fasim-representative-profile
```

This PR adds an external-input profiling runner for larger Fasim workloads and
records two local humanLncAtlas profiles. It does not commit the corpus files and
does not change Fasim behavior.

## Scope

#48 showed a synthetic signal:

```text
DP/scoring ~= 55-60%
DP + column ~= 82-86%
```

That made DP + column max the only plausible GPU target, but it was still a
weak signal because all fixtures were deterministic scale-ups from the tiny repo
fixture.

This PR asks the same question on external local FASTA inputs:

```text
Does DP + column stay near 80-90% on larger real-shaped data?
Or does window generation become a first-order cost?
```

## Runner

Use:

```bash
FASIM_REAL_CORPUS_DNA=/path/to/dna.fa \
FASIM_REAL_CORPUS_RNA=/path/to/rna.fa \
FASIM_REAL_CORPUS_LABEL=real_corpus \
FASIM_REAL_CORPUS_REPEAT=2 \
make benchmark-fasim-real-corpus-profile
```

The target runs:

```text
FASIM_PROFILE=1
FASIM_OUTPUT_MODE=lite
FASIM_VERBOSE=0
FASIM_EXTEND_THREADS=1
```

`check-fasim-real-corpus-profile` is intentionally a tiny smoke check using the
checked-in `testDNA.fa` / `H19.fa` oracle. It validates the runner, repeat digest
stability, and telemetry parsing without depending on external corpus files.

## Local External Profiles

These profiles were run on local humanLncAtlas FASTA pairs available on this
machine. The input files are not committed to the repo. The labels below describe
the workload shape rather than serving as portable corpus identifiers.

### human_lnc_atlas_17kb_target

```text
DNA sequence length ~= 17.8k
RNA sequence length ~= 1.5k
repeat = 2
canonical digest = sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
canonical output records = 0
windows = 4
dp_cells = 220,155,624
candidates = 57
final_hits = 0
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.000081 | 0.17% |
| window generation | 0.012684 | 26.24% |
| DP scoring | 0.022267 | 46.06% |
| column max | 0.013076 | 27.05% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000003 | 0.01% |
| output | 0.000000 | 0.00% |

| Accelerated fraction | 5x | 10x | 20x | 50x |
| --- | ---: | ---: | ---: | ---: |
| DP only (46.06%) | 1.584x | 1.708x | 1.778x | 1.823x |
| DP + column (73.11%) | 2.409x | 2.924x | 3.274x | 3.528x |
| DP + column + local (73.11%) | 2.409x | 2.924x | 3.274x | 3.528x |

### human_lnc_atlas_508kb_target

```text
DNA sequence length ~= 508k
RNA sequence length ~= 1.5k
repeat = 2
canonical digest = sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221
canonical output records = 34
windows = 104
dp_cells = 6,312,369,024
candidates = 1,367
final_hits = 34
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.002774 | 0.24% |
| window generation | 0.310493 | 26.82% |
| DP scoring | 0.541930 | 46.81% |
| column max | 0.298963 | 25.82% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000061 | 0.01% |
| output | 0.000156 | 0.01% |

| Accelerated fraction | 5x | 10x | 20x | 50x |
| --- | ---: | ---: | ---: | ---: |
| DP only (46.81%) | 1.599x | 1.728x | 1.801x | 1.848x |
| DP + column (72.63%) | 2.387x | 2.888x | 3.226x | 3.470x |
| DP + column + local (72.63%) | 2.387x | 2.888x | 3.226x | 3.470x |

## Decision

```text
real-corpus runner: pass
canonical digest stability: pass
DP-only GPU: no
DP + column-only GPU: weaker than #48 synthetic signal
window generation: now first-order, about 26-27%
```

The local external profiles do not support jumping directly to a narrow
DP+column CUDA prototype as the next engineering PR. On these workloads,
DP+column is only about `73%`, so even a 50x acceleration of that fraction is
estimated around `3.5x` total. Window generation is too large to ignore.

Recommended next step:

```text
fasim window-generation decomposition
```

That PR should split `fasim_window_generation_seconds` into at least:

```text
cutSequence
transferString
reverse/reverse-complement
source transform
encoded target build
batch flush overhead
```

Only after that should we choose between:

```text
1. GPU DP + column + window-prep batch prototype
2. CPU/SIMD window-generation optimization
3. conservative filter
4. stop GPU work for Fasim until a larger real corpus says otherwise
```

## Boundaries

```text
no algorithm change
no output change
no CUDA kernel
no conservative/approximate filter
no threshold change
no non-overlap behavior change
no speedup claim
```
