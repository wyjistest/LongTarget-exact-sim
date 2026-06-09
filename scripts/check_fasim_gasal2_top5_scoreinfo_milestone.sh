#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_scoreinfo_milestone.md"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_chr21_chr22_active"}"
REQUIRE_RESULT="${REQUIRE_RESULT:-0}"

if [[ ! -s "$DOC" ]]; then
  echo "missing milestone doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" <<'PY'
import sys
from pathlib import Path

text = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
required = [
    "short-query / H19 formal GASAL2 top5 scoreInfo/preAlign artifact path",
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO=1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64",
    "FASIM_PREALIGN_CUDA_MAX_TASKS=16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512",
    "FASIM_OUTPUT_TOPK_LITE=5",
    "active_path_runs = 1/1",
    "positive_gasal2_request_runs = runs",
    "positive_exact_scoreinfo_task_runs = runs",
    "zero_gasal2_fallback_runs = runs",
    "topK-lite rank-observe telemetry is enabled, non-empty, and free of unknown rows",
    "speedup vs CPU worker wall sum = 40.119136x",
    "not full lite-output equivalence",
    "not an `aligner.Align()` replacement",
    "MALAT1/NEAT1 long-query GASAL2 path remains guarded out",
    "GASAL2_MAX_QUERY_LEN=2812",
    "segmented GASAL2 long-query probes are documented no-go",
    "direct segmented traceback shadow is correctness-clean but performance no-go",
    "pruned segmented traceback shadow is correctness-clean but performance no-go",
    "score-prepass batched shadow is stage-only",
    "CPU replay with no-last remains marginal",
    "make check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result",
    "make check-fasim-gasal2-top5-wrapper-meg3-grouped-result",
    "make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow",
    "make check-fasim-gasal2-long-query-segmented-replay-no-last",
    "make check-fasim-gasal2-top5-scoreinfo-milestone-result",
    "make check-fasim-gasal2-top5-activation-contract",
    "make check-fasim-gasal2-top5-release-smoke",
    "formal_preset_example = meg3_first32",
    "formal_preset_topk_artifact_match = true",
    "cap32_nt_score_artifact_match = false",
    "formal_preset_gasal2_requests = 63,035",
    "formal_preset_exact_scoreinfo_gpu_tasks = 1,536",
    "formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0",
    "contract smoke, not a performance claim",
    "define an explicit top5-only output contract",
]
missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit("milestone doc missing phrases: " + ", ".join(missing))
PY

if [[ "$REQUIRE_RESULT" == "1" ]]; then
  aggregate="$WORK/aggregate.tsv"
  cpu_report="$WORK/runs/chr21_chr22_r1/cpu_summary/report.json"
  candidate_report="$WORK/runs/chr21_chr22_r1/column_pruned_preset/report.json"
  if [[ ! -s "$aggregate" ]]; then
    echo "missing milestone aggregate: $aggregate" >&2
    exit 1
  fi
  if [[ ! -s "$cpu_report" || ! -s "$candidate_report" ]]; then
    echo "missing milestone report json under $WORK" >&2
    exit 1
  fi
  python3 - "$aggregate" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected exactly one aggregate row, got {len(rows)}")
row = rows[0]
for key in (
    "artifact_checked_runs",
    "top5_clean_runs",
    "active_path_runs",
    "zero_legacy_score_runs",
    "zero_overflow_runs",
    "zero_fallback_runs",
    "zero_gasal2_fallback_runs",
    "zero_length_guard_fallback_runs",
    "positive_gasal2_request_runs",
    "positive_exact_scoreinfo_task_runs",
):
    if row.get(key) != row.get("runs") or row.get("runs") != "1":
        raise SystemExit(f"{key} does not match runs=1: {row}")
if row.get("decision") != "top5_artifact_go":
    raise SystemExit(f"unexpected decision: {row}")
if row.get("speedup_vs_cpu_worker_wall_sum_min") != "40.119136":
    raise SystemExit(f"unexpected speedup: {row}")
PY
  python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
    --report "$cpu_report"
  python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
    --report "$candidate_report" \
    --same-payload-as "$cpu_report"
fi

echo "ok"
