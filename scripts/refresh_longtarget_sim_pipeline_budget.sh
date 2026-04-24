#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage: scripts/refresh_longtarget_sim_pipeline_budget.sh \
  --top-level-budget-decision PATH \
  --sim-telemetry-budget PATH \
  --output-root DIR
EOF
}

die() {
  echo "$*" >&2
  exit 1
}

TOP_LEVEL_BUDGET_DECISION=""
SIM_TELEMETRY_BUDGET=""
OUTPUT_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --top-level-budget-decision)
      TOP_LEVEL_BUDGET_DECISION="$2"
      shift 2
      ;;
    --sim-telemetry-budget|--input-budget)
      SIM_TELEMETRY_BUDGET="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$TOP_LEVEL_BUDGET_DECISION" ]] || { usage >&2; die "--top-level-budget-decision is required"; }
[[ -n "$SIM_TELEMETRY_BUDGET" ]] || { usage >&2; die "--sim-telemetry-budget is required"; }
[[ -n "$OUTPUT_ROOT" ]] || { usage >&2; die "--output-root is required"; }

[[ -f "$TOP_LEVEL_BUDGET_DECISION" ]] || die "missing input file: $TOP_LEVEL_BUDGET_DECISION"
[[ -f "$SIM_TELEMETRY_BUDGET" ]] || die "missing input file: $SIM_TELEMETRY_BUDGET"

mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT=$(cd "$OUTPUT_ROOT" && pwd)

python3 scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_BUDGET_DECISION" \
  --input-budget "$SIM_TELEMETRY_BUDGET" \
  --output-dir "$OUTPUT_ROOT/sim_pipeline_budget"
