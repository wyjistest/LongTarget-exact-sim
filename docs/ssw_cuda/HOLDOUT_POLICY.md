# SSW-CUDA Holdout Policy

Status: Phase 0 identity policy frozen; Phase 3 will add selection and overlap
checker implementations before any new CUDA holdout is selected.

The final holdout may be selected only after the full-GPU implementation
commit is frozen. Selection must load
`paper/ssw_cuda/used_input_exclusion_registry.tsv` and reject overlap in any
available query ordinal, query digest, target ordinal, target digest, or pair
digest. Ordinals are comparable only within their recorded namespace.

Pair digests use canonical compact JSON with sorted keys and this domain:

```text
schema = ssw-cuda-exclusion-pair-v1
query/target ordinal namespaces and values
query/target IDs and SHA-256 identities
query/target regions
```

The registry contains sequence digests where historical manifests provide
them and file digests where older workload manifests expose only file-level
identity. Query-only development exclusions use `NA` for target and pair
fields; their query digest remains a hard exclusion.

Fresh selection may use only pre-execution metadata such as role-local source
ordinal, sequence length, GC/repeat proxy, static maximum-score upper bound,
source grouping, and hash ordering. It may not use names, observed output,
runtime, mismatch, fallback, byte/word path observed at runtime, blacklist, or
allowlist. Runtime byte/word coverage is reported without replacement samples.

L8 full-output equality is diagnostic throughout this program and cannot be
promoted by the Phase 11 holdout.
