#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec python3 "$ROOT/reproduce/bioinformatics/replay_phase2_traceback_cases.py" --execute "$@"
