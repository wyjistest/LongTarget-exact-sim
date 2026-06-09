#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_product_readiness.md"
BROADER_VALIDATION_DOC="$ROOT/docs/fasim_gasal2_top5_broader_validation.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
OUTPUT_CONTRACT_DOC="$ROOT/docs/fasim_gasal2_top5_output_contract.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$BROADER_VALIDATION_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$OUTPUT_CONTRACT_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing top5 product-readiness dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$BROADER_VALIDATION_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$OUTPUT_CONTRACT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
broader_validation = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
output_contract = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "top5-only product-readiness gate",
    "--gasal2-top5-column-pruned-scoreinfo",
    "accepted top5-only product scope",
    "default-off opt-in",
    "result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk_summary.tsv",
    "topk_rows.tsv",
    "topk-TFOsorted.lite",
    "full `.lite` output is not contract output",
    "final all-row TFO equivalence is not claimed",
    "short-query/H19",
    "chr21+chr22",
    "MEG3 grouped",
    "broader workload validation",
    "make check-fasim-gasal2-top5-broader-validation",
    "make check-fasim-gasal2-top5-release-smoke",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-scoped-completion-candidate",
    "top5 score/stability/nt_score clean",
    "scoreinfo_gasal2_active = 1",
    "GASAL2 requests > 0",
    "GASAL2 traceback requests > 0",
    "exact scoreInfo GPU tasks > 0",
    "fallback/overflow = 0",
    "long-query fallback policy",
    "MALAT1/NEAT1",
    "no real path",
    "GASAL2 selected/expanded segment traceback: no-go for real path",
    "GASAL2_MAX_QUERY_LEN = 2812",
    "query_len > GASAL2_MAX_QUERY_LEN",
    "must fail closed",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "make check-fasim-gasal2-top5-product-readiness",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "full objective remains open",
    "contract smoke, not a performance claim",
    "formal_preset_example = meg3_first32",
    "formal_preset_topk_artifact_match = true",
    "cap32_nt_score_artifact_match = false",
    "formal_preset_gasal2_requests = 63,035",
    "formal_preset_exact_scoreinfo_gpu_tasks = 1,536",
    "formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("top5 product-readiness doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("broader-validation", broader_validation),
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("output-contract", output_contract),
):
    for phrase in (
        "make check-fasim-gasal2-top5-product-readiness",
        "make check-fasim-gasal2-top5-broader-validation",
        "make check-fasim-gasal2-top5-recommended-runtime",
        "make check-fasim-gasal2-top5-scoped-completion-candidate",
        "top5-only product-readiness",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing product-readiness phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-top5-product-readiness:\n"
    r"\tbash \./scripts/check_fasim_gasal2_top5_product_readiness\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-product-readiness target")

release_smoke_target = re.search(
    r"^check-fasim-gasal2-top5-release-smoke:.*check-fasim-gasal2-topk-lite-wrapper-contract.*check-fasim-gasal2-formal-preset-examples.*check-fasim-gasal2-top5-product-readiness.*check-fasim-gasal2-top5-recommended-runtime.*check-fasim-gasal2-top5-scoped-completion-candidate",
    makefile,
    flags=re.MULTILINE,
)
if not release_smoke_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-release-smoke target")
if ".PHONY: check-fasim-gasal2-top5-release-smoke" not in makefile:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-release-smoke .PHONY declaration")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-top5-product-readiness" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 product-readiness dependency")
if "check-fasim-gasal2-top5-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 release-smoke dependency")
PY

echo "ok"
