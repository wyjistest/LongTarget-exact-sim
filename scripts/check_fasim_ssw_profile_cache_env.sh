#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_ssw_profile_cache_env"
rm -rf "$WORK"
mkdir -p "$WORK"

strings "$BIN" >"$WORK/strings.txt"
grep -q 'FASIM_SSW_PROFILE_CACHE' "$WORK/strings.txt"
grep -q 'FASIM_SSW_PROFILE_CACHE_VALIDATE' "$WORK/strings.txt"

echo "ok"
