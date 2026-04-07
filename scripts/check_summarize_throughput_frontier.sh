#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_summarize_throughput_frontier"
rm -rf "$WORK"
mkdir -p "$WORK/r1" "$WORK/r2"

cat >"$WORK/r1/report.json" <<'EOF'
{
  "inputs": {"dna_basename": "anchor_a.fa"},
  "quality_gate": {
    "min_relaxed_recall": 0.7,
    "min_top_hit_retention": 0.5,
    "require_qualifying_run": false
  },
  "runs": [
    {
      "device_set": "0",
      "extend_threads": 8,
      "topk": 64,
      "suppress_bp": 0,
      "wall_seconds": 10.0,
      "comparison": {
        "relaxed": {"recall": 0.6},
        "top_hit_retention": 0.0,
        "per_output_comparisons": {
          "anchor_a-TFOsorted.lite": {
            "relaxed": {"recall": 0.6},
            "top_hit_retention": 0.0
          }
        }
      }
    },
    {
      "device_set": "0",
      "extend_threads": 8,
      "topk": 128,
      "suppress_bp": 1,
      "wall_seconds": 12.0,
      "comparison": {
        "relaxed": {"recall": 0.9},
        "top_hit_retention": 0.8,
        "per_output_comparisons": {
          "anchor_a-TFOsorted.lite": {
            "relaxed": {"recall": 0.85},
            "top_hit_retention": 0.8
          }
        }
      }
    }
  ]
}
EOF

cat >"$WORK/r2/report.json" <<'EOF'
{
  "inputs": {"dna_basename": "anchor_b.fa"},
  "quality_gate": {
    "min_relaxed_recall": 0.7,
    "min_top_hit_retention": 0.5,
    "require_qualifying_run": false
  },
  "runs": [
    {
      "device_set": "0",
      "extend_threads": 8,
      "topk": 64,
      "suppress_bp": 0,
      "wall_seconds": 9.0,
      "comparison": {
        "relaxed": {"recall": 0.72},
        "top_hit_retention": 0.4,
        "per_output_comparisons": {
          "anchor_b-TFOsorted.lite": {
            "relaxed": {"recall": 0.72},
            "top_hit_retention": 0.4
          }
        }
      }
    },
    {
      "device_set": "0",
      "extend_threads": 8,
      "topk": 128,
      "suppress_bp": 1,
      "wall_seconds": 13.0,
      "comparison": {
        "relaxed": {"recall": 0.82},
        "top_hit_retention": 0.75,
        "per_output_comparisons": {
          "anchor_b-TFOsorted.lite": {
            "relaxed": {"recall": 0.8},
            "top_hit_retention": 0.75
          }
        }
      }
    }
  ]
}
EOF

python3 "$ROOT/scripts/summarize_throughput_frontier.py" \
  --format json \
  "$WORK/r1/report.json" \
  "$WORK/r2/report.json" >"$WORK/summary.json"

python3 - "$WORK/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert summary["report_count"] == 2
assert len(summary["rows"]) == 2

rows = {
    (row["device_set"], row["extend_threads"], row["topk"], row["suppress_bp"]): row
    for row in summary["rows"]
}

fast_bad = rows[("0", 8, 64, 0)]
assert fast_bad["report_count"] == 2
assert fast_bad["zero_top_hit_reports"] == 1
assert fast_bad["all_top_hit_nonzero"] is False
assert fast_bad["qualifying_reports"] == 0

slower_good = rows[("0", 8, 128, 1)]
assert slower_good["report_count"] == 2
assert slower_good["zero_top_hit_reports"] == 0
assert slower_good["all_top_hit_nonzero"] is True
assert slower_good["qualifying_reports"] == 2
assert slower_good["min_worst_output_relaxed_recall"] == 0.8
assert slower_good["min_worst_output_top_hit_retention"] == 0.75
assert slower_good["pareto_optimal"] is True
PY

python3 "$ROOT/scripts/summarize_throughput_frontier.py" \
  "$WORK/r1/report.json" \
  "$WORK/r2/report.json" >"$WORK/summary.md"

grep -q "all_top_hit_nonzero" "$WORK/summary.md"
grep -q "pareto_optimal" "$WORK/summary.md"
grep -q "128" "$WORK/summary.md"

echo "ok"
