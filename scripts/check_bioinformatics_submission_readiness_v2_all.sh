#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"

case "$MODE" in
  --precommit)
    phase="${BIOINFORMATICS_SUBMISSION_READINESS_V2_PHASE:?set BIOINFORMATICS_SUBMISSION_READINESS_V2_PHASE}"
    exec python3 "$ROOT/scripts/check_bioinformatics_submission_readiness_v2.py" \
      --phase "$phase" --mode precommit
    ;;
  --final)
    ;;
  *)
    echo "usage: $0 [--precommit|--final]" >&2
    exit 2
    ;;
esac

phase="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["last_completed_phase"])' \
  "$ROOT/paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json")"

python3 "$ROOT/scripts/check_bioinformatics_submission_readiness_v2.py" \
  --phase "$phase" --mode postcommit

echo "Bioinformatics submission readiness v2 aggregate checks OK"
