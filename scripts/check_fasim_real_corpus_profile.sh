#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/benchmark_fasim_real_corpus_profile.py" \
  --bin "$ROOT/fasim_longtarget_x86" \
  --dna "$ROOT/testDNA.fa" \
  --rna "$ROOT/H19.fa" \
  --label tiny_smoke \
  --repeat 2 \
  --require-profile \
  --expected-digest-file "$ROOT/tests/oracle_fasim_profile/sample_lite.digest"
