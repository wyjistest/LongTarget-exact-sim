#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

NEAT1_RECORD_LIMITS="${NEAT1_RECORD_LIMITS:-64}" \
  bash "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_trust.sh"
