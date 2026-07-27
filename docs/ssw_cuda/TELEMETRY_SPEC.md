# SSW-CUDA Telemetry Specification

Status: Phase 0 skeleton; schemas and call-level fields are pending Phase 2.

Every attempt must bind its backend, workload and input identities, argv,
environment, source and binary digests, CPU/GPU identity, timestamps, return
code, fallback status, logs, and artifact manifest.

Mutually exclusive timing stages are:

```text
packing
H2D
pre-align
selection
forward endpoint
reverse-start
traceback
D2H
downstream triplex/stability
clustering/sort
serialization/I/O
wrapper/other
total wall
```

Stage sums must reconcile with outer wall time. CPU SSW pre-align, forward,
reverse, banded traceback, and fallback calls require independent counters.
Telemetry paths must be non-overwriting, and invalid telemetry makes an
attempt unsuccessful.
