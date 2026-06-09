#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence_first64"}"
SUMMARY="$WORK/fresh.json"
BASELINE_REPORT="$WORK/audit/baseline.report.json"
CANDIDATE_REPORT="$WORK/audit/candidate.report.json"
COMPARE="$WORK/compare.txt"

for path in "$SUMMARY" "$BASELINE_REPORT" "$CANDIDATE_REPORT" "$COMPARE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing first64 TFOsorted evidence input: $path" >&2
    echo "Run: CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence" >&2
    exit 1
  fi
done

python3 - "$SUMMARY" "$BASELINE_REPORT" "$CANDIDATE_REPORT" "$COMPARE" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
baseline = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
compare = Path(sys.argv[4]).read_text(encoding="utf-8")
bench = candidate.get("fasim_benchmark_sums", {})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def num(key: str) -> float:
    value = bench.get(key, 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SystemExit(f"benchmark key {key} is not numeric: {value!r}")
    return float(value)


require("schema=tfosorted" in compare, "expected schema=tfosorted comparison")
require("baseline_rows=9741" in compare, "expected first64 baseline_rows=9741")
require("candidate_rows=9741" in compare, "expected first64 candidate_rows=9741")
require("missing_rows=0" in compare, "expected no missing rows")
require("extra_rows=0" in compare, "expected no extra rows")
require("full_rows_equal=true" in compare, "expected full row equality")
require(summary.get("audited_status") == "accepted", "audit must be accepted")
require(summary.get("baseline_digest") == summary.get("candidate_digest"), "summary digest mismatch")
require(baseline.get("merged_digest") == candidate.get("merged_digest"), "report digest mismatch")
require(summary.get("merged_records") == 9741, "expected first64 merged_records=9741")
require(baseline.get("output_mode") == "tfosorted", "baseline must be tfosorted")
require(candidate.get("output_mode") == "tfosorted", "candidate must be tfosorted")

baseline_wall = float(summary["baseline_runner_wall_seconds"])
candidate_wall = float(summary["candidate_runner_wall_seconds"])
wall_delta = candidate_wall - baseline_wall
require(wall_delta > 0.0, f"expected candidate slower in audited first64 probe, delta={wall_delta}")

two_contract = num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds")
gpu_minscore = num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds")
realpath_extend = num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds")
attempt_probe = num(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_seconds"
)
replay_probe = num(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds"
)
grouped_replay_probe = num(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds"
)
selected_only_probe = num(
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_seconds"
)
probe_seconds = attempt_probe + replay_probe + grouped_replay_probe + selected_only_probe

require(two_contract > 0.0, "expected positive two-contract GPU time")
require(gpu_minscore > 0.0, "expected positive GPU minScore time")
require(realpath_extend > 0.0, "expected positive realpath extend time")
require(probe_seconds > wall_delta, f"probe_seconds={probe_seconds} must exceed wall_delta={wall_delta}")
require(attempt_probe > wall_delta, f"attempt_probe={attempt_probe} must exceed wall_delta={wall_delta}")

require(
    int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches")) == 0,
    "score mismatches must be zero",
)
require(
    int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches")) == 0,
    "minScore mismatches must be zero",
)
require(
    int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches")) == 0,
    "scoreInfo mismatches must be zero",
)
require(
    int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks")) == 0,
    "realpath fallbacks must be zero",
)

print(f"baseline_wall={baseline_wall:.6f}")
print(f"candidate_wall={candidate_wall:.6f}")
print(f"wall_delta={wall_delta:.6f}")
print(f"candidate_vs_baseline={summary['candidate_vs_baseline']:.6f}")
print(f"two_contract_total_seconds={two_contract:.6f}")
print(f"gpu_minscore_wall_seconds={gpu_minscore:.6f}")
print(f"realpath_extend_seconds={realpath_extend:.6f}")
print(f"diagnostic_probe_seconds={probe_seconds:.6f}")
print(f"attempt_probe_seconds={attempt_probe:.6f}")
print(f"replay_probe_seconds={replay_probe:.6f}")
print(f"grouped_replay_probe_seconds={grouped_replay_probe:.6f}")
print(f"selected_only_probe_seconds={selected_only_probe:.6f}")
print("decision=audited_wall_not_real_runtime_claim")
PY
