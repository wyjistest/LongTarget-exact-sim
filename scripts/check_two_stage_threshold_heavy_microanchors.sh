#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_two_stage_threshold_heavy_microanchors"
rm -rf "$WORK"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_heavy_microanchors.py \
    --work-dir "$WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --rna H19.fa \
    --heavy-anchor testDNA.fa \
    --tile-spec 1000:1000:2 \
    --tile-spec 2000:2000:1 >/dev/null
)

python3 - "$WORK/summary.json" "$WORK/discovery_report.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
discovery = json.load(open(sys.argv[2], "r", encoding="utf-8"))

assert summary["compare_output_mode"] == "lite"
assert summary["prefilter_backend"] == "prealign_cuda"
assert len(summary["tile_specs"]) == 2
assert len(summary["selected_microanchors"]) == 3
assert summary["decision_flags"].keys() == {
    "needs_stronger_gate",
    "needs_relaxation",
    "ready_for_broader_anchor_sweep",
}

for item in summary["selected_microanchors"]:
    assert item["length_bp"] in {1000, 2000}
    assert item["selection_rank"] >= 1
    assert Path(item["shard_path"]).exists()
    assert Path(item["report_path"]).exists()
    assert set(item["runs"]) == {"legacy", "deferred_exact", "deferred_exact_minimal_v1"}
    assert set(item["comparisons_vs_legacy"]) == {"deferred_exact", "deferred_exact_minimal_v1"}

assert discovery["report_count"] >= 3
assert len(discovery["candidates"]) >= 3
for candidate in discovery["candidates"][:3]:
    assert set(candidate["runs"]) == {"deferred_exact"}
PY

grep -q "Two-Stage Threshold Heavy Micro-Anchor Summary" "$WORK/summary.md"
grep -q "ready_for_broader_anchor_sweep" "$WORK/summary.md"

echo "ok"
