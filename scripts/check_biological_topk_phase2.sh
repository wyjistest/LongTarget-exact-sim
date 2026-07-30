#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---postcommit}"

case "$MODE" in
  --precommit)
    checker_mode="precommit"
    ;;
  --postcommit)
    checker_mode="postcommit"
    ;;
  *)
    echo "usage: $0 [--precommit|--postcommit]" >&2
    exit 2
    ;;
esac

exec python3 "$ROOT/scripts/check_biological_topk_phase.py" \
  --phase 2 --mode "$checker_mode"
