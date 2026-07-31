# GASAL2 GPU Screen Release Candidate Under Test

`scripts/gasal2_gpu_screen.py` is the GPU-only submission release-candidate
entry point. It reuses the existing LongTarget wrapper's FASTA, environment,
process, TFOsorted, and GPU checks. It starts only the GASAL2 candidate binary;
there is no authority-binary option and no complete CPU authority execution.

The product is frozen under test, not validated or released. Phase 4 must pass
before `accelerates` becomes a supported claim.

## Identities

```text
execution_mode = gpu-screen
scientific_contract = biological_topk_candidate_site_v1
output_schema = gasal2_candidate_sites_tsv_v1
software_epoch = submission_rc_v2
artifact_role = frozen_release_candidate_under_test
validation_status = pending_phase4
```

## Usage

```bash
python3 scripts/gasal2_gpu_screen.py \
  --query query.fa \
  --target target.fa \
  --output gpu-screen-output \
  --report gpu-screen-report.json \
  --candidate-binary fasim_longtarget_gasal2
```

The output directory contains:

- `candidate_sites.tsv`: three deterministic Top-5 rankings under the frozen
  candidate-site construction, or a legal header-only artifact;
- `contract.json`: product identity and pending-validation status; and
- `diagnostics/native-TFOsorted`: native candidate output retained only for
  audit and offline comparison, with no full-row product claim.

The standalone report validates against
`schemas/gasal2_gpu_screen_run_report_v1.schema.json`. The candidate-sites
artifact validates against the exact field order and semantic checks in
`scripts/gasal2_candidate_sites.py` and the frozen descriptor
`schemas/gasal2_candidate_sites_tsv_v1.schema.json`.

Every coordinate column in `candidate_sites.tsv` is 0-based half-open. Genomic
coordinates equal target-local coordinates plus the declared target-region
offset. The candidate-site identity digest is recomputed from the ordered
payload frozen in the schema descriptor; local cluster IDs are provenance only
and are not cross-arm equality keys.

Each ranking is descending. The score key is `(score, nt, mean_stability)`, the
stability key is `(mean_stability, nt, score)`, and the nt key is
`(nt, score, mean_stability)`. The native full-row key is the final reverse
lexicographic tie-breaker. Top-5 truncation occurs only after legacy clustering
and per-mode representative selection.

## Fail-closed envelope

The command accepts one canonical A/C/G/T query record and one canonical
A/C/G/T target record. Query length must not exceed 2,812 nt. The visible GPU
must have at least 24,000 MiB and compute capability 8.9. The backend must
report the GASAL2 score path active, at least one request, and zero fallbacks.
Missing telemetry, malformed native output, candidate-site canonicalization
failure, timeout, OOM, unsupported input, or output collision fails without
publishing a product directory.

Optional identity arguments allow a formal harness to bind source ordinals,
assembly, coordinate namespace, extraction recipes, and target genomic offset.
Defaults use full single-record FASTA local coordinates and header identities.
