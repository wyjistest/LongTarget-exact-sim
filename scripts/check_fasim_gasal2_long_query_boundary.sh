#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_boundary.md"
EXAMPLES_GATE="$ROOT/scripts/check_fasim_exact_scoreinfo_gpu_examples_gate.sh"

if [[ ! -s "$DOC" ]]; then
  echo "missing GASAL2 long-query boundary doc: $DOC" >&2
  exit 1
fi
if [[ ! -s "$EXAMPLES_GATE" ]]; then
  echo "missing examples boundary gate: $EXAMPLES_GATE" >&2
  exit 1
fi

python3 - "$DOC" "$EXAMPLES_GATE" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
examples = Path(sys.argv[2]).read_text(encoding="utf-8")

doc_required = [
    "GASAL2_MAX_QUERY_LEN=2812",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812",
    "MEG3 query_len = 1582",
    "MALAT1 query_len = 8708",
    "NEAT1 query_len = 22767",
    "query_preflight_supported = 1",
    "scoreinfo_gasal2_active = 1",
    "query_preflight_supported = 0",
    "scoreinfo_gasal2_active = 0",
    "top5 clean via CPU fallback",
    "GASAL2_MAX_QUERY_LEN=8708",
    "batch=20000, streams=3",
    "fails in GASAL2 allocation with CUDA out-of-memory",
    "batch=128, streams=1",
    "top5_stability_equal = false",
    "wall = 23.11s -> 95.31s",
    "GASAL2 total = 83.43s",
    "Increasing `GASAL2_MAX_QUERY_LEN` is not a valid continuation path",
    "Segmented GASAL2 long-query probes",
    "direct segmented traceback shadow",
    "gasal2_requests = 500352",
    "traceback_requests = 500352",
    "segmented shadow total ~= 64s",
    "pruned segmented traceback shadow",
    "FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=37",
    "traceback_requests = 467024",
    "segmented traceback shadow total ~= 63.52s",
    "score-prepass batched shadow",
    "traceback_requests = 0",
    "segmented score-prepass shadow total ~= 2s",
    "CPU replay with no-last",
    "malat1_first8 speedup=1.009996x",
    "malat1_first16 speedup=1.029101x",
    "malat1_first32 speedup=1.031832x",
    "malat1_first64 speedup=1.034623x",
    "malat1_first128 speedup=1.038017x",
    "first8/first16/first32/first64/first128",
    "first8/first16/first32/first64",
    "performance remains marginal",
    "Long-query workloads should remain on CPU fallback",
    "query tiling with proven top5 artifact equivalence",
    "segmented GASAL2 requests with deterministic merge",
    "docs/plans/2026-06-05-fasim-long-query-gasal2-segmented-shadow.md",
    "make check-fasim-gasal2-long-query-segmented-plan",
    "make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow",
    "make check-fasim-gasal2-long-query-segmented-replay-no-last",
    "make check-fasim-gasal2-long-query-segmented-no-last-scaling-result",
    "top5_score_equal = true",
    "top5_stability_equal = true",
    "top5_nt_score_equal = true",
    "GPU total < CPU fallback",
    "make check-fasim-gasal2-long-query-boundary",
    "make check-fasim-exact-scoreinfo-gpu-examples-gate",
]
missing_doc = [phrase for phrase in doc_required if phrase not in doc]
if missing_doc:
    raise SystemExit(
        "GASAL2 long-query boundary doc missing phrases: "
        + ", ".join(missing_doc)
    )

examples_required = [
    '"malat1_first8"',
    '"neat1_first64"',
    'query_preflight_supported="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported 0)"',
    'query_preflight_query_len="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len 0)"',
    'query_preflight_max_query_len="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len 0)"',
    '[[ "$query_preflight_supported" == "0" ]]',
    '[[ "$scoreinfo_gasal2_active" == "0" ]]',
    '[[ "$query_preflight_query_len" -gt "$query_preflight_max_query_len" ]]',
    '[[ "$gasal2_requests" == "0" ]]',
    '[[ "$gasal2_traceback_requests" == "0" ]]',
    '[[ "$exact_scoreinfo_gpu_tasks" == "0" ]]',
]
missing_examples = [phrase for phrase in examples_required if phrase not in examples]
if missing_examples:
    raise SystemExit(
        "examples gate missing long-query guard checks: "
        + ", ".join(missing_examples)
    )
PY

echo "ok"
