#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_frontier_log_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/out"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_frontier_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF

cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_frontier_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

env \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_GASAL2_PHASE7_FRONTIER_LOG=1 \
  "$BIN" \
  -f1 "$WORK/inputs/target.fa" \
  -f2 "$WORK/inputs/query.fa" \
  -r 0 \
  -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

python3 - "$WORK/stderr.log" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
metrics = {}
for line in text.splitlines():
    if not line.startswith("benchmark.fasim_gasal2_phase7_frontier_log_"):
        continue
    key, sep, value = line.partition("=")
    if sep:
        metrics[key] = value

required = {
    "benchmark.fasim_gasal2_phase7_frontier_log_requested": "1",
    "benchmark.fasim_gasal2_phase7_frontier_log_active": "1",
}
for key, expected in required.items():
    actual = metrics.get(key)
    if actual != expected:
        raise SystemExit(f"{key} expected {expected}, got {actual!r}")

path_text = metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_path", "")
if not path_text:
    raise SystemExit("frontier log path is empty")
digest_text = metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_digest", "")
if not digest_text:
    raise SystemExit("frontier log digest is empty")

path = Path(path_text)
if not path.is_file():
    raise SystemExit(f"frontier log path is not a file: {path}")

lines = path.read_text(encoding="utf-8").splitlines()
if len(lines) < 2:
    raise SystemExit("frontier log has no data rows")

header = lines[0]
expected_header = "\t".join([
    "task_id",
    "scoreinfo_index",
    "scoreinfo_position",
    "scoreinfo_score",
    "attempt_index",
    "attempt_start",
    "attempt_cutlength",
    "align_sw_score",
    "align_ref_begin",
    "align_ref_end",
    "align_query_begin",
    "align_query_end",
    "selected",
    "emitted_triplex_count_before",
    "emitted_triplex_count_after",
])
if header != expected_header:
    raise SystemExit(f"unexpected frontier log header: {header}")
print("ok")
PY
