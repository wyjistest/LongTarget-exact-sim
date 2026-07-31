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

python3 "$ROOT/scripts/check_bioinformatics_submission_readiness_v2.py" \
  --phase 0 --mode postcommit

echo "Bioinformatics submission readiness v2 aggregate checks OK"
