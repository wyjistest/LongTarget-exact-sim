# Canonical-Hybrid-v2 Performance Decision

The fixed A/H pilot completed all 18 preregistered validation instances from
six input-only workloads with three complete repeats. All score-, stability-,
and Nt-ranked clustered Top-5 canonical rows matched, full-output diagnostics
were 18/18, and there were no technical failures, fallbacks, timeouts, OOMs,
or replacement retries.

## Performance result

```text
performance_gate = no_go
primary aggregate A/H speedup = 0.257592x
secondary projected two-worker A/H speedup = 0.275231x
required speedup = 10.000000x
hybrid slowdown versus authority = 3.882109x
```

The primary metric is the preregistered sum of isolated authority wall seconds
divided by the sum of isolated hybrid wall seconds. The secondary metric uses
the maximum fixed-worker sum for each arm under the frozen modulo-2 mapping.
Both had to reach `>=10x`; neither did. The threshold was not changed and no
lower substitute threshold was introduced.

## Rescue decision

```text
canonical-hybrid-v2 correctness = pass
canonical-hybrid-v2 performance = no_go
B3-v2 = no_go
large B3-v2 application run authorized = false
canonical-hybrid-v2 rescue track = closed
submission route = retain CSBJ fallback
```

Canonical-hybrid-v2 remains valid evidence that GPU score selection plus
selected CPU canonical traceback can preserve the frozen correctness contract.
It is not a safe acceleration result on the fixed application-shaped pilot.
No v1 candidate-only timing, sequential verified timing, correctness-run timing,
or lower threshold is substituted for this result.

## Historical boundary

The historical records remain unchanged:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
```

The versioned v2 correctness pass and performance no-go are additive evidence;
they do not rewrite either historical decision.

Evidence receipt SHA-256: `765a77c9f3ee5a4a544a1d59a11a20868c94217843aa433942332c860dec7219`.
