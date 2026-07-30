#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---postcommit}"

case "$MODE" in
  --precommit) checker_mode=precommit ;;
  --postcommit|--final) checker_mode=postcommit ;;
  *) echo "usage: $0 [--precommit|--postcommit|--final]" >&2; exit 2 ;;
esac

exec python3 "$ROOT/scripts/check_biological_topk_successor_phase.py" \
  --phase 3 --mode "$checker_mode"
