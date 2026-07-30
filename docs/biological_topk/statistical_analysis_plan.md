# Statistical Analysis Plan

## Denominator

A clean double-empty is the only exclusion from a binary denominator. It
requires both arms technically successful, identical inputs, valid outputs, and
zero sites in both arms. It is reported with `binary_success=null`; it is not a
success and receives neither recall nor precision equal to one.

Every other preregistered primary workload enters the denominator. A nonempty/G
empty, A empty/G nonempty, technical or schema failure, timeout, OOM, missing
output, identity mismatch, unsupported input discovered after execution,
ambiguity, fallback, or comparator failure is binary zero. Technical failures
also face an independent zero-count hard gate.

## Endpoints and confidence bound

The primary endpoint is score-ranked complete-set binary success. Fixed-order
secondary endpoints are stability complete-set, Nt complete-set, then score,
stability, and Nt Top-1 retention. All use the corresponding denominator,
never complete cases. Each rate uses a one-sided exact 95% Clopper-Pearson lower
bound and must have LCB at least `0.95`.

At `p_alt=0.99`, alpha `0.05`, power target `0.80`, and denominator floor 60,
exact enumeration yields `n_binary_required=124`, `k_min=122`, two allowed
failures, and power `0.871553509746...`. With conservative denominator
eligibility `p=0.75`, the smallest statistical panel is 178; its exact tail
probability is `0.955969707503...`, while panel 177 gives
`0.943581147347...`.

## Joint information planning

The candidate panel quotas are short 60, medium 59, and large 59. A CPU A
candidate count is the number of deduplicated score-ranked canonical sites,
capped at five; rankings are not added. Development workload tuples preserve
stratum, denominator eligibility, reference nonempty status, and count.

The outer bootstrap resamples independent development workloads within
stratum (`seed=20260731`, 2,000 replicates). Each resulting empirical
distribution drives complete-panel inner simulation (`seed=20260801`, initial
10,000, maximum 100,000). A panel succeeds jointly only with at least 124
eligible workloads, 60 reference-nonempty workloads, and 240 reference sites.
The 5% noninterpolated outer order statistic is the planning LCB. Inner Wilson
95% half-width must be at most `0.005` and inner draws are not scientific units.

The point joint probability is `0.9575`; the outer 5% LCB is `0.9526`; maximum
observed inner half-width is `0.0043622`. The joint information gate passes.
This is not a claim of 80% joint concordance-endpoint power.

## Ordered diagnostic

For matched identities at depth `K=5` and `p=0.90`, define
`A_d=|prefix_A(d) intersection prefix_G(d)|/d`. The finite RBO_EXT value is:

```text
(1-p) * sum(d=1..K, p^(d-1) * A_d) + p^K * A_K
```

If a list ends, later positions add no item; its seen prefix persists. If either
list is empty, the value is zero. This metric is diagnostic only.

## Current feasibility boundary

All statistical, joint-information, source-capacity, elapsed, GPU-hour, and
storage checks pass for panel 178. The owner-approved fixed storage quota is 8
GiB (`8589934592` bytes), exceeding the 95% upper projection of
`5508762270` bytes. The machine record is
`paper/biological_topk/sample_size_plan.json`. Phase 1 freezes the size but does
not select the fresh manifest; selection begins only after Phase 2 passes.
