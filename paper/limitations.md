# Limitations

- The primary performance evidence comes from one machine generation with two
  24 GB NVIDIA GeForce RTX 4090 GPUs; a second GPU architecture was not tested.
- The accelerated claim is limited to the checked short-query implementation
  boundary, `query_len <= 2812`, under the fast top-K output contract. This is
  an engineering contract boundary, not a biological lncRNA definition.
- Fast top-K clustered TFO1-TFO5 equality is not a full-output replacement and
  does not imply complete TFOsorted row-set equality.
- Three of thirteen preregistered supported-query workloads have repeat-
  consistent clustered stability or Nt mismatches. All seven mismatch pairs
  remain visible in frozen source data.
- Historical full-output rows are descriptive and near parity; they do not
  support a broad full-output acceleration claim.
- Long-query evidence is bounded to dual-grid KCNQ1OT1 `max_segments=8` on
  chr22. Full 121-segment KCNQ1OT1 and full hg38 were not run, and the current
  long-query architecture remains a no-go for promotion.
- Low-density overlap is supported at one worker per 24 GB GPU. Four- and
  six-worker configurations on two GPUs retain OOM evidence and are not
  recommended.
- CPU affinity, CPU clocks, GPU application clocks and persistence mode were not
  controlled; paired ordering limits but does not remove environmental noise.
- Traceback, exact-column result materialization and CPU finalization remain
  material bottlenecks. Component-stage acceleration cannot be interpreted as
  the same end-to-end acceleration.
- Archive-first reduces storage and bounded SQLite merge reduces memory, but
  both have separate restore or merge wall-time costs.
- The work evaluates computational contracts and preserved experimental TFO
  prioritization. It does not establish biological superiority over other
  triplex-prediction methods.
- Public raw-artifact archival, permanent DOI issuance, authorship, funding and
  journal-specific formatting remain author/release tasks.
