#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"

if [[ "$MODE" != "--final" && "$MODE" != "--precommit" ]]; then
  echo "usage: $0 [--final|--precommit]" >&2
  exit 2
fi

if [[ "$MODE" == "--precommit" ]]; then
  phase="${BIOLOGICAL_TOPK_PHASE:?set BIOLOGICAL_TOPK_PHASE for --precommit}"
  exec python3 "$ROOT/scripts/check_biological_topk_phase.py" \
    --phase "$phase" --mode precommit
fi

mapfile -t phases < <(
  python3 - "$ROOT/paper/biological_topk/PROGRAM_STATE.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    state = json.load(handle)
for phase in range(10):
    status = state["phase_status"][str(phase)]
    if status not in {"pending", "active", "not_authorized_previous_no_go"}:
        print(phase)
PY
)

for phase in "${phases[@]}"; do
  python3 "$ROOT/scripts/check_biological_topk_phase.py" \
    --phase "$phase" --mode postcommit
done

echo "biological Top-K aggregate checks OK"
