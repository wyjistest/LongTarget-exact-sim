#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_corpus_recall_repair"
mkdir -p "$WORK"

PYTHONPATH="$ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from benchmark_fasim_sim_gap_taxonomy import RecoveryBox, TriplexRecord
from benchmark_fasim_sim_recovery_real_corpus_characterization import (
    evaluate_recall_repair_strategy,
)


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
            "0.00",
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


fasim = rec("fasim", 10, 20)
shared = rec("shared", 100, 110)
guard_candidate = rec("guard_candidate", 120, 130, score=88.0, nt=50)
box_candidate = rec("box_candidate", 300, 310)
extra = rec("extra", 140, 150)

result = evaluate_recall_repair_strategy(
    strategy="smoke_relaxed",
    boxes=[
        RecoveryBox(
            family=("chr1", "+", "R"),
            genome_interval=(90, 160),
            query_interval=(1, 20),
            categories=frozenset(["base"]),
        ),
        RecoveryBox(
            family=("chr1", "+", "R"),
            genome_interval=(290, 320),
            query_interval=(1, 20),
            categories=frozenset(["expanded"]),
        ),
    ],
    full_search_cells=10000,
    fasim_records=[fasim],
    sim_records=[shared, guard_candidate, box_candidate],
    baseline_shared_raw={shared.raw},
    baseline_not_box_covered_raw={box_candidate.raw},
    baseline_guard_rejected_raw={guard_candidate.raw},
    candidate_raw={shared.raw, guard_candidate.raw, box_candidate.raw, extra.raw},
    accepted_candidate_raw={shared.raw, guard_candidate.raw, box_candidate.raw, extra.raw},
    suppressed_fasim_raw={fasim.raw},
    output_mutations=0,
)

assert result.shared_records == 3
assert result.missed_records == 0
assert result.recovered_from_box_expansion == 1
assert result.recovered_from_guard_relaxation == 1
assert result.extra_vs_sim == 1
assert result.output_mutations == 0
PY

FASIM_SIM_RECOVERY_RECALL_REPAIR_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 \
python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_smoke "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_smoke \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --recall-repair-shadow \
  --report-title "Fasim SIM-Close Recovery Real-Corpus Recall Repair" \
  --base-branch fasim-sim-recovery-real-corpus-miss-taxonomy \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_recall_repair\.tiny_smoke\.baseline_current\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_recall_repair\.tiny_smoke\.baseline_current\.recall_vs_sim=100\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_recall_repair\.tiny_smoke\.baseline_current\.output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_recall_repair\.total\.enabled=1$' "$WORK/smoke.log"
grep -q '| recall_repair_shadow | yes |' "$WORK/smoke_report.md"
grep -q 'Recall Repair Shadow' "$WORK/smoke_report.md"
grep -q 'Do not recommend or default SIM-close mode from this PR.' "$WORK/smoke_report.md"
