#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/benchmark_fasim_profile.py" \
  --mode profile \
  --bin "$ROOT/fasim_longtarget_x86" \
  --require-profile
