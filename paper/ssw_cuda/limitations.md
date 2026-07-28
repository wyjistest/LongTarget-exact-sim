# Limitations

- The exact evidence stops at independent L1/L2 and L3 checkpoints. L4-L7 were
  not implemented and promoted as a full GPU path.
- Phase 7 used consumed regression inputs and development workloads. It did not
  consume a fresh promotion holdout.
- The integrated forward-hybrid failed once after 665,562 successful CPU
  continuations in the first large chr21 observation. The available aggregate
  telemetry does not identify the exact selected attempt or differing endpoint
  field, so no DP tie-cell root-cause claim is made.
- Phase 7 stopped after that correctness failure. Only one overhead and one
  medium performance observation completed; no formal median speedup is
  reported.
- The completed observations were slower than their CPU references. These are
  checkpoint reference ratios, not formal speedup claims.
- The Amdahl ceiling applies to the frozen backend scope and measured CPU
  workloads. It closes the 10x B3 route; it does not prove that every possible
  future architecture is limited to the same ceiling.
- L8 is diagnostic only. Neither row-set equality nor artifact-inventory
  equality may be described as a general full-output replacement contract.
- Same-model dual RTX 4090 determinism was tested for the Phase 5/6 checkpoint
  subsets. Cross-architecture GPU determinism was not established.
- No Phase 8-12 full backend, fresh holdout, application panel, CLI promotion,
  container, release candidate, or archive was produced.
- The default CPU authority and historical verified contracts remain required
  for user-facing results.
