# Paper Benchmark Environment

## Automatically Captured Facts

The normalized machine-readable record is `reproduce/environment_manifest.json`.
It was derived from the per-run environment receipts captured by
`scripts/capture_fasim_gasal2_paper_environment.py`; dynamic utilization,
temperature, clocks, process lists, UUIDs, timestamps, and absolute working
directories are not treated as machine identity.

- OS: Ubuntu 20.04.6 LTS; kernel 5.15.0-46-generic.
- CPU: Intel Core i9-10900X, 10 physical cores and 20 logical CPUs.
- RAM: 134,745,059,328 bytes.
- GPUs: two NVIDIA GeForce RTX 4090 devices, 24,564 MiB each.
- NVIDIA driver: 555.42.06; CUDA toolkit: 12.5.82.
- Compiler: g++ 9.4.0; Python: 3.11.10.
- Figure stack: Matplotlib 3.9.1, Pillow 10.4.0, NumPy 1.26.4.
- GASAL2: commit `106d94ee53fc847214fb05f2f9f892538a5d3baf`,
  `GPU_SM_ARCH=sm_89`, `MAX_QUERY_LEN=2812`, `N_CODE=0x4E`.

## Manual Protocol Notes

- CPU affinity was not pinned and CPU frequency was not fixed. The captured
  governor was `powersave`; this limitation applies to all wall-time claims.
- GPU persistence mode was disabled and application clocks were not controlled.
- Paired order was deterministically interleaved with seed `20260715`.
- The supported low-density scheduling scope is one worker per GPU. Four- and
  six-worker configurations on two 24 GB GPUs retain OOM evidence.
- `CUDA_VISIBLE_DEVICES` was set per run by the paper harness; C1 required two
  GPUs and other GPU workloads used one visible device per worker.
- Host NVIDIA driver is not supplied by the container and must support the CUDA
  12.5 user-space stack.
