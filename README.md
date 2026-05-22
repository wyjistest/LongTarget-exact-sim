# LongTarget: lncRNA epigenetic target prediction

LongTarget predicts lncRNA DNA-binding motifs and binding sites in genomic
regions using known ncRNA/DNA base-pairing rules, including Hoogsteen and
reverse Hoogsteen rules.

This repository contains the original standalone C/C++ LongTarget runner plus
an exact-SIM development branch with opt-in CPU/CUDA acceleration experiments.
The default build and runtime behavior remain conservative; advanced lanes are
explicitly enabled through build targets or environment variables.

## Quick Start

Build the default CPU binary:

```bash
make build
```

Run the bundled sample:

```bash
./longtarget_x86 -f1 testDNA.fa -f2 H19.fa -r 0
```

Run smoke/exactness checks:

```bash
make check-smoke
make check-sample
make check-matrix
```

For a manual build without the Makefile:

```bash
g++ longtarget.cpp -O -msse2 -o LongTarget
```

## Inputs

The bundled demo files are:

- `testDNA.fa`: DNA target sequence.
- `H19.fa`: sample lncRNA sequence.

RNA FASTA headers should use a compact `>species_lncRNA` style title with no
spaces. DNA FASTA headers should use `>species|chr|start-end`, also without
spaces.

## Common Run Options

```text
f1   DNA sequence file
f2   RNA sequence file
r    base-pairing rule; 0 means all rules
O    output directory
c    segment length, default 5000
i    identity threshold, default 60
S    stability threshold, default 1.0
ni   minimum triplex length, default 20
na   maximum triplex length
pc   C penalty, default 0
pt   T penalty, default -1000
ds   distance between TFOs, default 15
lg   minimum triplex length, default 50
```

Example with explicit output and thresholds:

```bash
./longtarget_x86 -f1 testDNA.fa -f2 H19.fa -r 0 -O /tmp/longtarget-out \
  -c 6000 -i 70 -S 1.0 -ni 25 -na 1000 -pc 1 -pt -500 -ds 10 -lg 60
```

## Outputs

The full output mode writes:

- `*-TFOsorted`: all predicted triplex records.
- `*-TFOclass1`: TFO1 TTS distribution.
- `*-TFOclass2`: TFO2 TTS distribution.

For large runs, the exact-SIM branch also supports reduced output modes:

```bash
LONGTARGET_OUTPUT_MODE=tfosorted ./longtarget_x86 ...
LONGTARGET_OUTPUT_MODE=lite ./longtarget_x86 ...
```

## Accelerated Builds

CPU AVX2 build:

```bash
make build-avx2
```

CUDA build and sample smoke:

```bash
make build-cuda
make check-smoke-cuda
LONGTARGET_ENABLE_CUDA=1 TARGET=$PWD/longtarget_cuda ./scripts/run_sample_exactness.sh
```

The CUDA and two-stage lanes are opt-in. They are useful for profiling and
large-workload experiments, but each lane has its own exactness and validation
constraints. See [Advanced Runtime Details](docs/longtarget_advanced_runtime_details.md)
before enabling them for benchmark or production-style runs.

## Fasim Tools

This repository also vendors `Fasim-LongTarget` under `fasim/`:

```bash
make build-fasim
make build-fasim-cuda
```

Example CUDA preAlign run:

```bash
FASIM_OUTPUT_MODE=tfosorted FASIM_ENABLE_PREALIGN_CUDA=1 FASIM_VERBOSE=0 \
  ./fasim_longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O /tmp/fasim-out
```

Fasim throughput presets, sweeps, and comparator scripts are documented in the
advanced runtime notes.

## Documentation

- [Advanced Runtime Details](docs/longtarget_advanced_runtime_details.md):
  CUDA/SIM/Fasim/two-stage knobs, benchmark telemetry, and longer workflow
  notes moved out of this README.
- [Fasim Sharded Runner](docs/fasim_sharded_runner.md): contig-level
  process sharding, deterministic merge, and digest validation.
- [Fasim Sharded Worker Scheduler](docs/fasim_sharded_worker_scheduler.md):
  process-level worker assignment with optional GPU and CPU binding.
- [Fasim Sharded Worker Scaling](docs/fasim_sharded_worker_scaling.md):
  1/2/4 worker characterization wrapper and digest gate.
- [Fasim Sharded Workload Matrix](docs/fasim_sharded_worker_workload_matrix.md):
  multi-contig workload matrix wrapper for worker scaling reports.
- [Fasim Sharded Real Workload Matrix](docs/fasim_sharded_worker_real_workload_matrix.md):
  real chr21+chr22 digest-equal 1/2 worker characterization.
- [Fasim Sharded 4-Contig 2-GPU Characterization](docs/fasim_sharded_worker_4contig_2gpu_characterization.md):
  local 2-GPU 4-contig run with 4-worker oversubscription stress.
- [Fasim Sharded Worker Density on 2 GPUs](docs/fasim_sharded_worker_density_2gpu.md):
  local 2-GPU worker-density characterization across 1/2/3/4/6/8 workers.
- [Exact SIM Progress](EXACT_SIM_PROGRESS.md): development history and exact-SIM
  implementation notes.
- [Plans](docs/plans/): design and investigation notes for specific work items.

## Repository Layout

```text
longtarget.cpp   main LongTarget program
rules.h          base-pairing rules
sim.h            SIM local alignment implementation
stats.h          SSE2/AVX local alignment support
cuda/            CUDA kernels and support code
fasim/           vendored Fasim-LongTarget sources
scripts/         benchmark, validation, and analysis helpers
tests/           exactness fixtures and oracle data
docs/            detailed docs and plans
```

## Requirements

- Linux-like environment.
- `g++` for CPU builds.
- GNU Make for repository build/check targets.
- Optional: NVIDIA CUDA toolkit and a compatible GPU for CUDA lanes.
- RAM and CPU requirements scale with the number of lncRNAs and target region
  length; 16 GB RAM and 4 CPU cores are a practical starting point.

## License

LongTarget is distributed under the AGPLv3 license. See [LICENSE](LICENSE).

## Citation

If you use LongTarget in published work, cite the original LongTarget paper or
the citation format required by your project.
