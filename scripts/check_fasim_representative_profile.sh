#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/benchmark_fasim_representative_profile.py" \
  --bin "$ROOT/fasim_longtarget_x86" \
  --profile-set representative \
  --repeat 2 \
  --require-profile \
  --expected-digest-dir "$ROOT/tests/oracle_fasim_profile/representative"
