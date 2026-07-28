# Phase 7 measurement repair 1

## Frozen failure

Phase 7 execution epoch v1 stopped before attempt 26 launched. The first 25
attempt receipts remain under `formal-v1`; they are immutable and are excluded
from the Phase 7 result table. The failing row did not start the backend, and
the v1 execution receipt records zero replacement retries.

```text
source commit       = 750fb29e7c0c989046947f86d2f5648f94fa3754
v1 plan SHA-256     = 49e4f5984fdfa32ed38f169f033deb1016027e440860c5855c5130decbf04038
completed receipts  = 25/49
failing attempt     = p7p_medium_h19_chr22_2mb_o01
stop reason         = target sequence digest drift
backend launched    = false
replacement retries = 0
```

## Root cause

The target FASTA is byte-identical to the file frozen for Phase 1. It contains
lowercase repeat-masked bases. Phase 1 defined sequence identity after ASCII
uppercase normalization, while the Phase 7 runner initially retained case in
its independent pre-run digest check.

```text
file SHA-256                      = e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea
case-preserving sequence SHA-256 = 489562b1e038519743bd0d496d60c488bcbf73d35aebaae3d5ab0081f9c5fbbc
uppercase sequence SHA-256       = 486b1c05ad0a360a0d77858ae73b25e32ec0fa851f5115b7aac69c2c9aa670dd
```

The file hash above is bound in the machine-readable receipt. The mismatch is
a runner validation defect; it is not input drift, an alignment mismatch, a
GPU failure, or an observed performance result.

## Bounded repair

Repair 1 changes only FASTA sequence validation: sequence lines are converted
to uppercase and checked against `ACGTN` before hashing. A unit test freezes
mixed-case and invalid-alphabet behavior. Backend arguments, environment,
inputs, timeouts, task density, comparator, contracts, workload count, and the
closed Amdahl decision do not change.

Epoch v2 is a complete new 49-row measurement epoch with new attempt IDs,
snapshot, receipt, comparison root, and `formal-v2` artifact root. It is not a
resume or replacement retry. Epoch v1 remains preserved as failed evidence.

```text
v2 plan SHA-256 = fb86f5539dd55d4f553edb6598de881626d70ef4913ea9ce8e0ccce4a4b0a4f1
repair count     = 1 of at most 2
```
