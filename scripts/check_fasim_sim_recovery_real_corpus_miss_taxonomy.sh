#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_corpus_miss_taxonomy"
mkdir -p "$WORK"

PYTHONPATH="$ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from benchmark_fasim_sim_gap_taxonomy import RecoveryBox, TriplexRecord
from benchmark_fasim_sim_recovery_real_corpus_characterization import classify_missed_sim_records


def rec(name, start, end, qstart=1, qend=10, score=90.0, nt=50):
    raw = "\t".join(
        [
            "chr1",
            str(start),
            str(end),
            "+",
            "R",
            str(qstart),
            str(qend),
            str(qstart),
            str(qend),
            "parallel",
            f"{score:.2f}",
            str(nt),
            "99.00",
            name,
        ]
    )
    return TriplexRecord(
        raw=raw,
        chr_name="chr1",
        genome_start=start,
        genome_end=end,
        strand="+",
        rule="R",
        query_start=qstart,
        query_end=qend,
        start_in_seq=qstart,
        end_in_seq=qend,
        direction="parallel",
        score=score,
        nt=nt,
        identity=99.0,
        stability=0.0,
    )


shared = rec("shared", 10, 20)
not_box = rec("not_box", 1000, 1010)
executor_missing = rec("executor_missing", 110, 120)
guard_rejected = rec("guard_rejected", 130, 140)
replacement_suppressed = rec("replacement_suppressed", 150, 160)
canonical = rec("canonical", 170, 180)
canonical_close = rec("canonical_close", 171, 181)

taxonomy = classify_missed_sim_records(
    sim_records=[
        shared,
        not_box,
        executor_missing,
        guard_rejected,
        replacement_suppressed,
        canonical,
    ],
    sim_close_records=[shared, canonical_close],
    boxes=[
        RecoveryBox(
            family=("chr1", "+", "R"),
            genome_interval=(100, 200),
            query_interval=(1, 20),
            categories=frozenset(["smoke"]),
        )
    ],
    candidate_raw={guard_rejected.raw, replacement_suppressed.raw},
    accepted_candidate_raw={replacement_suppressed.raw},
)

assert taxonomy.sim_records == 6
assert taxonomy.shared_records == 1
assert taxonomy.missed_records == 5
assert taxonomy.not_box_covered == 1
assert taxonomy.box_covered_but_executor_missing == 1
assert taxonomy.guard_rejected == 1
assert taxonomy.replacement_suppressed == 1
assert taxonomy.canonicalization_mismatches == 1
assert taxonomy.metric_ambiguity_records == 0
PY

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_smoke "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_smoke \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --report-title "Fasim SIM-Close Recovery Real-Corpus Miss Taxonomy" \
  --base-branch fasim-sim-recovery-real-corpus-validation-coverage \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.miss_taxonomy_enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.missed_records=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.not_box_covered=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.box_covered_executor_missing=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.guard_rejected=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.replacement_suppressed=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.canonicalization_mismatches=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.tiny_smoke\.run1\.metric_ambiguity_records=0$' "$WORK/smoke.log"
grep -q '| miss_taxonomy_report | yes |' "$WORK/smoke_report.md"
grep -q 'Metric consistency note' "$WORK/smoke_report.md"
grep -q 'Do not recommend or default SIM-close mode from this PR.' "$WORK/smoke_report.md"
