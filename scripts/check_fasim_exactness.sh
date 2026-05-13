#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_DIGEST_FILE="$ROOT/tests/oracle_fasim_profile/sample_lite.digest"

python3 "$ROOT/scripts/benchmark_fasim_profile.py" \
  --mode exactness \
  --bin "$ROOT/fasim_longtarget_x86" \
  --expected-digest-file "$EXPECTED_DIGEST_FILE" \
  --repeat 2
