#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-670}" \
TRUST_PRESET="${TRUST_PRESET:-group32}" \
GROUP_TARGET_RECORDS_LIST="${GROUP_TARGET_RECORDS_LIST:-32}" \
  bash "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups.sh"
