#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-670}" \
  bash "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_realpath_trust.sh"
