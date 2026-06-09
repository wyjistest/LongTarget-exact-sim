#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_broader_validation.md"
PRODUCT_DOC="$ROOT/docs/fasim_gasal2_top5_product_readiness.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
MAKEFILE="$ROOT/Makefile"

CHR21_CHR22_AGG="$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_chr21_chr22_active/aggregate.tsv"
MEG3_GROUPED_AGG="$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_meg3_full_formal_group32/aggregate.tsv"
SMALL_AGG="$ROOT/.tmp/check_fasim_gasal2_column_pruned_preset_top5_matrix/matrix/aggregate.tsv"
EXAMPLES_SUMMARY="$ROOT/.tmp/check_fasim_exact_scoreinfo_gpu_examples_gate/summary.tsv"

for path in \
  "$DOC" \
  "$PRODUCT_DOC" \
  "$CURRENT_STATE_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$MAKEFILE" \
  "$CHR21_CHR22_AGG" \
  "$MEG3_GROUPED_AGG" \
  "$SMALL_AGG" \
  "$EXAMPLES_SUMMARY"; do
  if [[ ! -s "$path" ]]; then
    echo "missing top5 broader-validation dependency: $path" >&2
    exit 1
  fi
done

python3 - \
  "$DOC" \
  "$PRODUCT_DOC" \
  "$CURRENT_STATE_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$MAKEFILE" \
  "$CHR21_CHR22_AGG" \
  "$MEG3_GROUPED_AGG" \
  "$SMALL_AGG" \
  "$EXAMPLES_SUMMARY" <<'PY'
import csv
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
product_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")
chr21_chr22_agg = Path(sys.argv[6])
meg3_grouped_agg = Path(sys.argv[7])
small_agg = Path(sys.argv[8])
examples_summary = Path(sys.argv[9])

required_doc = [
    "top5 broader workload validation",
    "--gasal2-top5-column-pruned-scoreinfo",
    "short-query positive set",
    "small chr22 slice",
    "chr21+chr22",
    "MEG3 grouped",
    "top5_artifact_go",
    "top5 score/stability/nt_score clean",
    "active_path_runs = runs",
    "positive_gasal2_request_runs = runs",
    "positive_exact_scoreinfo_task_runs = runs",
    "fallback/overflow = 0",
    "long-query guard set",
    "MALAT1 first8",
    "NEAT1 first64",
    "query_len > GASAL2_MAX_QUERY_LEN",
    "scoreinfo_gasal2_active = 0",
    "CPU fallback top5 clean",
    "not GASAL2-active evidence",
    "broader recommendation status",
    "not broad production default",
    "full objective remains open",
    "make check-fasim-gasal2-top5-broader-validation",
    "make check-fasim-gasal2-top5-recommended-runtime",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("top5 broader-validation doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("product-readiness", product_doc),
    ("current-state", current_state),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "make check-fasim-gasal2-top5-broader-validation",
        "make check-fasim-gasal2-top5-recommended-runtime",
        "top5 broader workload validation",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing broader-validation phrase: {phrase}")


def one_row_tsv(path: Path) -> dict[str, str]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    if len(rows) != 1:
        raise SystemExit(f"expected one row in {path}, got {len(rows)}")
    return rows[0]


def assert_positive_aggregate(row: dict[str, str], label: str, min_speedup: float) -> None:
    if row.get("decision") != "top5_artifact_go":
        raise SystemExit(f"{label} decision is not go: {row}")
    runs = row.get("runs")
    if runs != "1":
        raise SystemExit(f"{label} expected runs=1: {row}")
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
        if row.get(key) != runs:
            raise SystemExit(f"{label} {key} != runs: {row}")
    speedup = float(row["speedup_vs_cpu_worker_wall_sum_min"])
    if speedup < min_speedup:
        raise SystemExit(f"{label} speedup below {min_speedup}: {speedup}")


assert_positive_aggregate(one_row_tsv(chr21_chr22_agg), "chr21_chr22", 1.0)
assert_positive_aggregate(one_row_tsv(meg3_grouped_agg), "MEG3 grouped", 1.0)
assert_positive_aggregate(one_row_tsv(small_agg), "small", 1.0)

example_rows = {
    row["label"]: row
    for row in csv.DictReader(examples_summary.open(newline="", encoding="utf-8"), delimiter="\t")
}
for label in ("meg3_full", "malat1_first8", "neat1_first64"):
    if label not in example_rows:
        raise SystemExit(f"missing examples summary row: {label}")
    row = example_rows[label]
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            raise SystemExit(f"{label} {key} not true: {row}")

meg3 = example_rows["meg3_full"]
if meg3.get("query_preflight_supported") != "1" or meg3.get("scoreinfo_gasal2_active") != "1":
    raise SystemExit(f"MEG3 should be short-query GASAL2 active: {meg3}")
for key in ("gasal2_requests", "gasal2_traceback_requests", "exact_scoreinfo_gpu_tasks"):
    if int(float(meg3.get(key, "0"))) <= 0:
        raise SystemExit(f"MEG3 expected positive {key}: {meg3}")
for key in (
    "gasal2_fallbacks",
    "length_guard_fallbacks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
):
    if int(float(meg3.get(key, "0"))) != 0:
        raise SystemExit(f"MEG3 expected zero {key}: {meg3}")

for label in ("malat1_first8", "neat1_first64"):
    row = example_rows[label]
    query_len = int(row["query_preflight_query_len"])
    max_query_len = int(row["query_preflight_max_query_len"])
    if max_query_len != 2812 or query_len <= max_query_len:
        raise SystemExit(f"{label} query guard not proven: {row}")
    if row.get("query_preflight_supported") != "0":
        raise SystemExit(f"{label} should fail preflight: {row}")
    if row.get("scoreinfo_gasal2_active") != "0":
        raise SystemExit(f"{label} should not be GASAL2 active: {row}")
    for key in ("gasal2_requests", "gasal2_traceback_requests", "gasal2_fallbacks", "length_guard_fallbacks"):
        if int(float(row.get(key, "0"))) != 0:
            raise SystemExit(f"{label} expected zero {key}: {row}")

target = re.search(
    r"^check-fasim-gasal2-top5-broader-validation:\n"
    r"\tbash \./scripts/check_fasim_gasal2_top5_broader_validation\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-broader-validation target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-top5-broader-validation" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 broader-validation dependency")
PY

echo "ok"
