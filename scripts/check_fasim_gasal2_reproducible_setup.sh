#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH="$ROOT/patches/gasal2-fasim-bridge.patch"
SETUP="$ROOT/scripts/setup_gasal2.sh"

if [[ ! -s "$PATCH" ]]; then
  echo "missing tracked GASAL2 patch: $PATCH" >&2
  exit 1
fi

grep -q '^Subject: .*Fasim GASAL2 bridge' "$PATCH"
grep -q '^diff --git a/src/gasal.h b/src/gasal.h' "$PATCH"
grep -q '^diff --git a/src/gasal_align.cu b/src/gasal_align.cu' "$PATCH"
grep -q '^diff --git a/src/ctors.cpp b/src/ctors.cpp' "$PATCH"
grep -q 'host_cigar_offsets' "$PATCH"
grep -q 'cigar_offsets' "$PATCH"
grep -q 'cuda-12.5' "$PATCH"
grep -q 'actual_cigar_batch_bytes' "$PATCH"
grep -q 'use_cigar_offsets ? gpu_storage->cigar_offsets' "$PATCH"

if [[ ! -x "$SETUP" ]]; then
  echo "missing executable GASAL2 setup script: $SETUP" >&2
  exit 1
fi

grep -q 'https://github.com/nahmedraja/GASAL2' "$SETUP"
grep -q '106d94ee53fc847214fb05f2f9f892538a5d3baf' "$SETUP"
grep -q 'apply --check' "$SETUP"
grep -q 'patch already applied' "$SETUP"

grep -q '^GASAL2_REPO_URL ?= https://github.com/nahmedraja/GASAL2.git$' "$ROOT/Makefile"
grep -q '^GASAL2_PATCH ?= patches/gasal2-fasim-bridge.patch$' "$ROOT/Makefile"
grep -q '^setup-gasal2:' "$ROOT/Makefile"
grep -q 'scripts/setup_gasal2.sh' "$ROOT/Makefile"
grep -q -- '-I$(GASAL2_DIR)/include' "$ROOT/Makefile"
grep -q '#include "gasal_header.h"' "$ROOT/fasim/gasal2_align_bridge.cpp"

if grep -q '\.\./\.tmp/GASAL2' "$ROOT/fasim/gasal2_align_bridge.cpp"; then
  echo "bridge still hard-codes .tmp/GASAL2 include path" >&2
  exit 1
fi

echo "GASAL2 reproducible setup contract OK"
