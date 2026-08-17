# Bioinformatics Phase 2 Decision

The preregistered independent holdout is complete. All 36 primary formal attempts from 24 workloads are represented; the fixed pilot receipt was validated separately and excluded from the formal analysis basis. There were no technical failures, missing attempts, OOMs, timeouts, invalid reports, or telemetry errors.

The candidate matched score-ranked top 5 results in 35/36 attempts (23/24 workloads), stability-ranked top 5 results in 35/36 attempts (23/24 workloads), and Nt-ranked top 5 results in 36/36 attempts (24/24 workloads). Two attempts were scientific mismatches: `hq10_ht02` for stability ranking and `hq11_ht02` for score ranking. Full-row diagnostics also differed for `hq04_ht02` and `hq12_ht02`; full-output equality is 32/36 attempts and 20/24 workloads. Boundary ties matched in all 36 attempts.

Three verified executions published authority output: the two declared-contract mismatches and one comparator-detail failure (`hq12_ht02`). Every verified publication was independently validated as contract-safe. Repeated workload contracts and authority/candidate top-5 signatures were consistent across the preregistered three-repeat set.

No mechanism guard was inferred. GPU-only promoted coverage is 0/24 workloads, while safe verified-or-authority contract-safe coverage is 24/24 workloads.

## Decision

`verified_only_contract`

Promotion gate P1 fails because the holdout score-ranked contract is not zero-mismatch. No GPU-only safe contract is promoted. All fast contracts remain experimental and opt-in. Safe execution continues to resolve eligible named contracts through verified comparison and otherwise routes to CPU authority; mismatch or comparator failure publishes authority. Full-output and ineligible requests remain authority-routed.

No query ID, gene name, target ID, input digest, observed result, mechanism guard, blacklist, or allowlist was used to hide or route around an unfavorable row. The negative results remain represented in the generated evidence tables.
