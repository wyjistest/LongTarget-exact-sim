#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_certificate_unit"}"

rm -rf "$WORK"
mkdir -p "$WORK"

"${CXX:-g++}" -std=c++11 -Wall -Wextra -Werror \
  -I"$ROOT/fasim" \
  "$ROOT/tests/test_gasal2_traceback_certificate.cpp" \
  -o "$WORK/test_gasal2_traceback_certificate"

"$WORK/test_gasal2_traceback_certificate"
