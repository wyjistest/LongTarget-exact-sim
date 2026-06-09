#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_recommended_runtime.md"
RUNNER_DOC="$ROOT/docs/fasim_sharded_runner.md"
PRODUCT_DOC="$ROOT/docs/fasim_gasal2_top5_product_readiness.md"
BROADER_DOC="$ROOT/docs/fasim_gasal2_top5_broader_validation.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$RUNNER_DOC" "$PRODUCT_DOC" "$BROADER_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing GASAL2 top5 recommended-runtime dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$RUNNER_DOC" "$PRODUCT_DOC" "$BROADER_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
runner_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
product_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
broader_doc = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[7]).read_text(encoding="utf-8")

required_doc = [
    "GASAL2 top5 recommended runtime",
    "--gasal2-top5-column-pruned-scoreinfo",
    "default-off opt-in",
    "short-query/H19",
    "small chr22 slice",
    "chr21+chr22",
    "MEG3 grouped",
    "--group-target-records 32",
    "--workers",
    "--gpu-ids",
    "--auto-cpu-core-ranges",
    "--manifest",
    "run_fasim_gasal2_topk_lite.sh",
    "AUTO_CPU_CORE_RANGES=1",
    "CPU_POOL=0-19",
    "CPU_CORES_PER_WORKER=3",
    "RESUME=1",
    "FORCE=0",
    "--resume",
    "wrapper does not clear `OUT`",
    "wrapper summary records `shard_count` and `resumed_shards_count`",
    "topk_summary.tsv",
    "topk_rows.tsv",
    "topk-TFOsorted.lite",
    "result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "recommended when",
    "top5 broader workload validation passes",
    "top5 product-readiness passes",
    "not recommended when",
    "MALAT1/NEAT1",
    "GASAL2 selected/expanded segment traceback: no-go for real path",
    "query_len > GASAL2_MAX_QUERY_LEN",
    "scoreinfo_gasal2_active = 0",
    "wrapper fails closed before report/summary output",
    "full `.lite` output equivalence is required",
    "final all-row TFO equivalence is required",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "not broad production default",
    "full objective remains open",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-release-smoke",
    "make check-fasim-gasal2-scoreinfo-current-state",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("recommended-runtime doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("runner", runner_doc),
    ("product-readiness", product_doc),
    ("broader-validation", broader_doc),
    ("current-state", current_state),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "make check-fasim-gasal2-top5-recommended-runtime",
        "GASAL2 top5 recommended runtime",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing recommended-runtime phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-top5-recommended-runtime:\n"
    r"\tbash \./scripts/check_fasim_gasal2_top5_recommended_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-recommended-runtime target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-top5-recommended-runtime" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 recommended-runtime dependency")
if "check-fasim-gasal2-top5-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 release-smoke dependency")
PY

echo "ok"
