#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

python3 -m py_compile \
  "$ROOT/scripts/build_long_query_dynamic_gpu_manifest.py" \
  "$ROOT/scripts/long_query_dynamic_gpu_pool.py" \
  "$ROOT/scripts/run_long_query_dynamic_f1_attempt.py" \
  "$ROOT/tests/test_build_long_query_dynamic_gpu_manifest.py" \
  "$ROOT/tests/test_long_query_dynamic_gpu_pool.py" \
  "$ROOT/tests/test_run_long_query_dynamic_f1_attempt.py"
python3 "$ROOT/tests/test_build_long_query_dynamic_gpu_manifest.py" -v
python3 "$ROOT/tests/test_long_query_dynamic_gpu_pool.py" -v
python3 "$ROOT/tests/test_run_long_query_dynamic_f1_attempt.py" -v
