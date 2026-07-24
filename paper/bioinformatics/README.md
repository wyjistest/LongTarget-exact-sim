# Bioinformatics Application Note Submission Track

This directory is the authority for the new submission track. It does not
replace or rewrite the frozen paper evidence under `paper/source_data/`.

## Phase 0 receipt

```text
checked_at = 2026-07-24
submission_baseline_commit = a98d80d44d4418cdb8a67dc8d83ee41b8e599023
branch = gasal2-kcnq1ot1-focused-review
historical_completion_is_ancestor = 1
historical_aggregate_check = pass
historical_aggregate_command = make check-fasim-gasal2-paper-prep
historical_paper_runtime_epoch = 0
historical_paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
historical_paper_data_freeze = paper-data-v1-dccfd49-20260716
submission_software_epoch = 1
runtime_behavior_change = 0
new_benchmark_started = 0
```

The pre-phase working tree contained only the owner-provided untracked
`goal-bioinformatics.md`. The baseline commit is the completed historical
paper package, and the ancestry check returned zero.

## Capability audit

| Capability | Current state | Existing authority | Submission gap |
| --- | --- | --- | --- |
| user-facing wrapper/CLI | Missing | `scripts/run_fasim_gasal2_paper_benchmarks.py` is a research harness, not a user command | Build one contract-aware entry point in Phase 1 |
| input guard | Partial | Manifest, digest and query-length checks in `scripts/run_fasim_gasal2_paper_benchmarks.py`; runtime preflight in `fasim/Fasim-LongTarget.cpp` | Add complete FASTA, contract, environment and output preflight to the user entry point |
| authority/candidate comparator | Available for reuse | `scripts/compare_fasim_segmented_contract.py` and `scripts/compare_fasim_tfosorted_tfo_contract.py` | Integrate without duplicating ranking logic |
| JSON run report | Partial | Atomic benchmark receipts and summaries from `scripts/run_fasim_gasal2_paper_benchmarks.py` | Define and validate a user-facing report schema in Phase 1 |
| container/environment lock | Partial | `reproduce/Dockerfile`, `reproduce/environment_manifest.json`, and `reproduce/environment.md` | Validate the release-candidate install and smoke workflow in Phase 5 |
| CI | Missing | No `.github/` or GitLab CI configuration exists | Add CPU smoke and contract validation in Phase 5 |
| external-tool wrapper | Missing | Literature inventory only in `paper/related_work_inventory.tsv` | Select, pin and run at least one external tool in Phase 4 |
| public release metadata | Partial | `LICENSE` and `paper/RELEASE_CHECKLIST.md` | Owner-approved citation, release, archive and DOI metadata remain open |
| manuscript template | Partial | `paper/outline.md` and `reproduce/render_manuscript_source_kit.py` | Produce the Bioinformatics-sized manuscript package in Phase 7 |

The detailed, machine-readable classification is
`paper/bioinformatics/gap_register.tsv`.

## Epoch and data rules

The following rules are fixed for every later phase:

```text
historical source data stays immutable
submission software changes tracked separately
new holdout and application data receive new freeze ID
```

User-interface, validation, documentation, packaging and independent
orchestration changes belong to `submission_software_epoch = 1`. Any later
change to Fasim, CUDA, the GASAL2 bridge, sorting, clustering, output contracts
or production binary behavior must start a new paper runtime epoch and
invalidate affected historical benchmark claims until rerun.

## Phase 0 boundaries

- The official journal URLs were revisited on 2026-07-24. Direct and browser
  access reached a Cloudflare security challenge; the exact live-page content
  verification remains a classified gap rather than an invented success.
- No C, C++ or CUDA source was changed.
- No holdout, application, external-tool or performance benchmark was started.
- Phase 1 may build the user workflow. Holdout and application execution remain
  prohibited until their manifests are frozen in Phases 2 and 3.

## Phase 2 receipt

```text
checked_at = 2026-07-24
freeze_id = bioinformatics-phase2-holdout-v1-9e293b2c
manifest_sha256 = 9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6
formal_attempts = 36/36
formal_workloads = 24/24
scientific_mismatches = 2
technical_failures = 0
verified_fallbacks = 3
phase2_decision = verified_only_contract
gpu_only_contract_promoted = 0
safe_resolution = verified_or_authority
```

The fixed pilot receipt was validated and excluded from formal source data.
All formal rows, including the two scientific mismatches and four full-row
diagnostics, remain represented. Safe mode continues to verify eligible named
contracts and publish authority on mismatch or comparator failure; full-output
and ineligible requests use CPU authority. Fast-only output remains explicit
experimental opt-in.
