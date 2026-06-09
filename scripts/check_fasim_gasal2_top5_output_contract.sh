#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_output_contract.md"
CHECKER="$ROOT/scripts/check_topk_summary_digest_integrity.py"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
ACTIVATION_CHECK="$ROOT/scripts/check_fasim_gasal2_top5_activation_contract.py"

if [[ ! -s "$DOC" ]]; then
  echo "missing GASAL2 top5 output contract doc: $DOC" >&2
  exit 1
fi
if [[ ! -s "$CHECKER" ]]; then
  echo "missing topK artifact integrity checker: $CHECKER" >&2
  exit 1
fi
if [[ ! -s "$RUNNER" ]]; then
  echo "missing sharded runner: $RUNNER" >&2
  exit 1
fi
if [[ ! -s "$ACTIVATION_CHECK" ]]; then
  echo "missing GASAL2 activation contract check: $ACTIVATION_CHECK" >&2
  exit 1
fi

python3 - "$DOC" "$CHECKER" "$RUNNER" "$ACTIVATION_CHECK" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
checker = Path(sys.argv[2]).read_text(encoding="utf-8")
runner = Path(sys.argv[3]).read_text(encoding="utf-8")
activation_check = Path(sys.argv[4]).read_text(encoding="utf-8")

doc_required = [
    "--gasal2-top5-column-pruned-scoreinfo",
    "result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk_summary.tsv",
    "topk_rows.tsv",
    "topk-TFOsorted.lite",
    "score stability nt_score",
    "deterministic de-duplicated union",
    "topk_summary_only = true",
    "shard_output_topk_lite = 5",
    "topk_summary.k = 5",
    "gasal2_top5_scoreinfo_prune_max_per_task = 64",
    "exact_scoreinfo_gpu_max_per_task = 512",
    "gasal2_top5_query_preflight_supported = true",
    "gasal2_top5_query_preflight_max_query_len <= 2812",
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO=1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64",
    "FASIM_PREALIGN_CUDA_MAX_TASKS=16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512",
    "FASIM_OUTPUT_TOPK_LITE=5",
    "fasim_gasal2_requests > 0",
    "fasim_gasal2_traceback_requests > 0",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks > 0",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled = shard_count",
    "fasim_gasal2_fallbacks = 0",
    "fasim_gasal2_length_guard_fallbacks = 0",
    "topK-lite rank-observe telemetry is enabled, non-empty, and free of unknown rows",
    "make check-fasim-gasal2-top5-activation-contract",
    "full lite-output equivalence",
    "full scoreInfo/preAlign universal replacement",
    "aligner.Align replacement",
    "GPU endpoint authority",
    "GPU CIGAR / traceback authority",
    "validity for long-query MALAT1/NEAT1 GASAL2 execution",
    "segmented long-query GASAL2 traceback",
    "segmented long-query score-prepass",
    "CPU replay for long-query segmented candidates",
    "score-prepass batched shadow is stage-only",
    "direct and pruned segmented traceback shadows are performance no-go",
    "rejects segmented long-query diagnostic `--env` keys",
    "FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW",
    "Formal artifact integrity checks reject the same segmented diagnostic env keys",
    "unsupported formal env extras",
    "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST",
    "only the managed preset env and checked diagnostic overrides are accepted",
    "must match the recorded `gasal2_top5_query_preflight_max_query_len`",
    "Rows outside the checked top5 modes are not contract output",
    "make check-fasim-gasal2-top5-output-contract",
    "make check-fasim-gasal2-top5-formal-gate",
    "check_topk_summary_digest_integrity.py",
]
missing_doc = [phrase for phrase in doc_required if phrase not in doc]
if missing_doc:
    raise SystemExit(
        "GASAL2 top5 output contract doc missing phrases: "
        + ", ".join(missing_doc)
    )

checker_required = [
    'contract == "gasal2_top5_column_pruned_scoreinfo_artifact_v1"',
    'report.get("topk_summary_only") is not True',
    'report.get("shard_output_topk_lite") != FORMAL_GASAL2_TOPK',
    'topk_summary.get("k") != FORMAL_GASAL2_TOPK',
    'report.get("gasal2_top5_column_pruned_scoreinfo") is not True',
    'FORMAL_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK = 64',
    'FORMAL_EXACT_SCOREINFO_GPU_MAX_PER_TASK = 512',
    'FORMAL_GASAL2_MAX_QUERY_LEN = 2812',
    'FORMAL_GASAL2_ALLOWED_EXTRA_ENV',
    'FORMAL_GASAL2_FORBIDDEN_ENV_PREFIXES',
    '_check_formal_gasal2_query_max_env',
    'FASIM_TOP5_GASAL2_GPU_SCOREINFO',
    'FASIM_OUTPUT_TOPK_LITE',
    'FORMAL_GASAL2_REQUIRED_POSITIVE_BENCHMARKS',
    'FORMAL_GASAL2_REQUIRED_ZERO_BENCHMARKS',
    '"fasim_gasal2_requests"',
    '"fasim_gasal2_traceback_requests"',
    '"fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows"',
    '"fasim_gasal2_fallbacks"',
    '"fasim_gasal2_length_guard_fallbacks"',
    '"topk_lite_output"',
    '"topk_lite_digest"',
]
missing_checker = [phrase for phrase in checker_required if phrase not in checker]
if missing_checker:
    raise SystemExit(
        "topK artifact integrity checker missing contract checks: "
        + ", ".join(missing_checker)
    )

runner_required = [
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank"',
    '"fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows"',
]
missing_runner = [phrase for phrase in runner_required if phrase not in runner]
if missing_runner:
    raise SystemExit(
        "sharded runner missing activation checks: " + ", ".join(missing_runner)
    )

activation_check_required = [
    "zero_rows",
    "zero_max_rank",
    "unknown",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled",
]
missing_activation_check = [
    phrase for phrase in activation_check_required if phrase not in activation_check
]
if missing_activation_check:
    raise SystemExit(
        "activation contract check missing cases: "
        + ", ".join(missing_activation_check)
    )
PY

echo "ok"
