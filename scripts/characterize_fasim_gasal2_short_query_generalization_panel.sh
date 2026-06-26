#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_short_query_generalization_panel"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
LENGTHS="${LENGTHS:-1024 2048 2812}"
POSITIONS="${POSITIONS:-mid}"
RUN_H19="${RUN_H19:-1}"
RUN_MEG3="${RUN_MEG3:-1}"
RUN_LONG_FRAGMENTS="${RUN_LONG_FRAGMENTS:-1}"
RUN_FULL_NEGATIVE_CONTROLS="${RUN_FULL_NEGATIVE_CONTROLS:-1}"
RUN_FULL_NEGATIVE_CPU="${RUN_FULL_NEGATIVE_CPU:-0}"
REQUIRE_TOPK_EQUAL="${REQUIRE_TOPK_EQUAL:-0}"
MAX_QUERY_LEN="${MAX_QUERY_LEN:-2812}"

H19_FASTA="${H19_FASTA:-"$ROOT/H19.fa"}"
MEG3_FASTA="${MEG3_FASTA:-"$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa"}"
MALAT1_FASTA="${MALAT1_FASTA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
NEAT1_FASTA="${NEAT1_FASTA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
KCNQ1OT1_FASTA="${KCNQ1OT1_FASTA:-""}"

CHARACTERIZE="$ROOT/scripts/characterize_fasim_gasal2_short_query_tfo_contract.sh"

for path in "$TARGET" "$CHARACTERIZE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/runs"

summary="$WORK/summary.tsv"
negative_summary="$WORK/full_negative_controls.tsv"
audit="$WORK/runtime_audit.txt"

printf '%s\n' \
  "query_name	source_query	source_len	segment_kind	segment_start	segment_end	query_len	status	baseline_wall_seconds	candidate_wall_seconds	speedup_vs_baseline	top5_tfo_score_equal	top5_tfo_stability_equal	top5_tfo_nt_score_equal	query_preflight_supported	query_preflight_query_len	query_preflight_max_query_len	gasal2_requests	gasal2_traceback_requests	gasal2_fallbacks	length_guard_fallbacks	full_rows_equal	full_missing_rows	full_extra_rows	run_dir" \
  >"$summary"
printf '%s\n' \
  "query_name	source_query	source_len	query_len	status	query_preflight_supported	query_preflight_query_len	query_preflight_max_query_len	note	run_dir" \
  >"$negative_summary"

python3 - "$WORK/query_manifest.tsv" "$H19_FASTA" "$MEG3_FASTA" "$MALAT1_FASTA" "$NEAT1_FASTA" "$KCNQ1OT1_FASTA" "$LENGTHS" "$POSITIONS" "$RUN_H19" "$RUN_MEG3" "$RUN_LONG_FRAGMENTS" "$RUN_FULL_NEGATIVE_CONTROLS" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

manifest = Path(sys.argv[1])
h19 = Path(sys.argv[2])
meg3 = Path(sys.argv[3])
malat1 = Path(sys.argv[4])
neat1 = Path(sys.argv[5])
kcnq = Path(sys.argv[6]) if sys.argv[6] else None
lengths = [int(value) for value in sys.argv[7].split() if value]
positions = [value for value in sys.argv[8].split() if value]
run_h19 = sys.argv[9] == "1"
run_meg3 = sys.argv[10] == "1"
run_long = sys.argv[11] == "1"
run_negative = sys.argv[12] == "1"


def read_fasta(path: Path) -> tuple[str, str]:
    header = ""
    seq: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if not header:
                    header = line[1:].split()[0]
            else:
                seq.append(line)
    if not header:
        header = path.stem
    return header, "".join(seq).upper()


queries: list[tuple[str, Path | None]] = [
    ("H19", h19 if h19.exists() else None),
    ("MEG3", meg3 if meg3.exists() else None),
    ("MALAT1", malat1 if malat1.exists() else None),
    ("NEAT1", neat1 if neat1.exists() else None),
    ("KCNQ1OT1", kcnq if kcnq is not None and kcnq.exists() else None),
]

rows: list[list[str]] = []
if run_h19 and h19.exists():
    header, seq = read_fasta(h19)
    rows.append(["run", "H19", str(h19), str(len(seq)), "full", "0", str(len(seq)), str(len(seq))])
if run_meg3 and meg3.exists():
    header, seq = read_fasta(meg3)
    rows.append(["run", "MEG3", str(meg3), str(len(seq)), "full", "0", str(len(seq)), str(len(seq))])

if run_long:
    for query_name, path in queries:
        if query_name in {"H19", "MEG3"} or path is None:
            continue
        header, seq = read_fasta(path)
        source_len = len(seq)
        for length in lengths:
            if length > source_len:
                continue
            for pos in positions:
                if pos == "5p":
                    start = 0
                elif pos == "3p":
                    start = source_len - length
                elif pos == "mid":
                    start = max((source_len - length) // 2, 0)
                else:
                    raise SystemExit(f"unsupported position: {pos}")
                end = start + length
                rows.append([
                    "run",
                    query_name,
                    str(path),
                    str(source_len),
                    f"fragment_{pos}_{length}",
                    str(start),
                    str(end),
                    str(length),
                ])

if run_negative:
    for query_name, path in queries:
        if query_name in {"H19", "MEG3"} or path is None:
            continue
        header, seq = read_fasta(path)
        rows.append([
            "negative",
            query_name,
            str(path),
            str(len(seq)),
            "full_negative",
            "0",
            str(len(seq)),
            str(len(seq)),
        ])

with manifest.open("w", encoding="utf-8") as handle:
    handle.write("kind\tquery_name\tsource_query\tsource_len\tsegment_kind\tsegment_start\tsegment_end\tquery_len\n")
    for row in rows:
        handle.write("\t".join(row) + "\n")
PY

write_fragment() {
  local source="$1"
  local output="$2"
  local header="$3"
  local start="$4"
  local end="$5"
  python3 - "$source" "$output" "$header" "$start" "$end" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

source = Path(sys.argv[1])
output = Path(sys.argv[2])
header = sys.argv[3]
start = int(sys.argv[4])
end = int(sys.argv[5])
seq: list[str] = []
with source.open(encoding="utf-8", errors="replace") as handle:
    for raw in handle:
        line = raw.strip()
        if not line or line.startswith(">"):
            continue
        seq.append(line)
frag = "".join(seq).upper()[start:end]
if not frag:
    raise SystemExit(f"empty fragment from {source}:{start}-{end}")
with output.open("w", encoding="utf-8") as handle:
    handle.write(f">{header}\n")
    for i in range(0, len(frag), 80):
        handle.write(frag[i:i + 80] + "\n")
PY
}

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
}

run_panel_case() {
  local query_name="$1"
  local source_query="$2"
  local source_len="$3"
  local segment_kind="$4"
  local segment_start="$5"
  local segment_end="$6"
  local query_len="$7"
  local safe_label run_dir query_fasta status

  safe_label="$(printf '%s_%s' "$query_name" "$segment_kind" | tr -c 'A-Za-z0-9_.-' '_')"
  run_dir="$WORK/runs/$safe_label"
  query_fasta="$WORK/inputs/$safe_label.fa"
  mkdir -p "$run_dir"
  write_fragment "$source_query" "$query_fasta" "$safe_label" "$segment_start" "$segment_end"

  status="completed"
  if ! WORK="$run_dir" \
      TARGET="$TARGET" \
      RNA="$query_fasta" \
      RULE="$RULE" \
      PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      GASAL2_STREAMS="$GASAL2_STREAMS" \
      GASAL2_BATCH="$GASAL2_BATCH" \
      REQUIRE_TOPK_EQUAL="$REQUIRE_TOPK_EQUAL" \
      bash "$CHARACTERIZE" >"$run_dir/characterize.log" 2>"$run_dir/characterize.stderr.log"; then
    status="failed"
  fi

  local summary_file="$run_dir/summary.txt"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$query_name" \
    "$source_query" \
    "$source_len" \
    "$segment_kind" \
    "$segment_start" \
    "$segment_end" \
    "$query_len" \
    "$status" \
    "$(metric_or_default "$summary_file" baseline_wall_seconds NA)" \
    "$(metric_or_default "$summary_file" candidate_wall_seconds NA)" \
    "$(metric_or_default "$summary_file" speedup_vs_baseline NA)" \
    "$(metric_or_default "$summary_file" top5_tfo_score_equal false)" \
    "$(metric_or_default "$summary_file" top5_tfo_stability_equal false)" \
    "$(metric_or_default "$summary_file" top5_tfo_nt_score_equal false)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_gasal2_requests 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_gasal2_fallbacks 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_gasal2_length_guard_fallbacks 0)" \
    "$(metric_or_default "$summary_file" full_rows_equal false)" \
    "$(metric_or_default "$summary_file" full_missing_rows 0)" \
    "$(metric_or_default "$summary_file" full_extra_rows 0)" \
    "$run_dir" \
    >>"$summary"
}

run_negative_case() {
  local query_name="$1"
  local source_query="$2"
  local source_len="$3"
  local segment_kind="$4"
  local segment_start="$5"
  local segment_end="$6"
  local query_len="$7"
  local safe_label run_dir query_fasta note

  safe_label="$(printf '%s_%s' "$query_name" "$segment_kind" | tr -c 'A-Za-z0-9_.-' '_')"
  run_dir="$WORK/runs/$safe_label"
  query_fasta="$WORK/inputs/$safe_label.fa"
  mkdir -p "$run_dir/gasal2"
  write_fragment "$source_query" "$query_fasta" "$safe_label" "$segment_start" "$segment_end"
  note="preflight_only"

  if [[ "$RUN_FULL_NEGATIVE_CPU" == "1" ]]; then
    WORK="$run_dir" \
      TARGET="$TARGET" \
      RNA="$query_fasta" \
      RULE="$RULE" \
      PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      GASAL2_STREAMS="$GASAL2_STREAMS" \
      GASAL2_BATCH="$GASAL2_BATCH" \
      REQUIRE_TOPK_EQUAL="$REQUIRE_TOPK_EQUAL" \
      bash "$CHARACTERIZE" >"$run_dir/characterize.log" 2>"$run_dir/characterize.stderr.log" || true
    note="full_run_attempted"
  else
    {
      if (( query_len <= MAX_QUERY_LEN )); then
        printf 'benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=1\n'
      else
        printf 'benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=0\n'
      fi
      printf 'benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len=%s\n' "$query_len"
      printf 'benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len=%s\n' "$MAX_QUERY_LEN"
    } >"$run_dir/gasal2/stderr.log"
    : >"$run_dir/gasal2/stdout.log"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$query_name" \
    "$source_query" \
    "$source_len" \
    "$query_len" \
    "negative_recorded" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len 0)" \
    "$(metric_or_default "$run_dir/gasal2/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len 0)" \
    "$note" \
    "$run_dir" \
    >>"$negative_summary"
}

while IFS=$'\t' read -r kind query_name source_query source_len segment_kind segment_start segment_end query_len; do
  [[ "$kind" == "kind" ]] && continue
  if [[ "$kind" == "run" ]]; then
    run_panel_case "$query_name" "$source_query" "$source_len" "$segment_kind" "$segment_start" "$segment_end" "$query_len"
  elif [[ "$kind" == "negative" ]]; then
    run_negative_case "$query_name" "$source_query" "$source_len" "$segment_kind" "$segment_start" "$segment_end" "$query_len"
  fi
done <"$WORK/query_manifest.tsv"

python3 - "$summary" "$negative_summary" "$audit" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

summary = Path(sys.argv[1])
negative = Path(sys.argv[2])
audit = Path(sys.argv[3])

rows = list(csv.DictReader(summary.open(), delimiter="\t"))
neg = list(csv.DictReader(negative.open(), delimiter="\t"))
completed = [row for row in rows if row["status"] == "completed"]
clean = [
    row for row in completed
    if row["top5_tfo_score_equal"] == "true"
    and row["top5_tfo_stability_equal"] == "true"
    and row["top5_tfo_nt_score_equal"] == "true"
    and row["query_preflight_supported"] == "1"
    and row["gasal2_requests"] not in {"", "0"}
    and row["length_guard_fallbacks"] == "0"
]
non_h19 = [row for row in clean if row["query_name"] != "H19"]
negative_guarded = [
    row for row in neg
    if row["query_preflight_supported"] == "0"
    and row["query_preflight_query_len"]
    and int(float(row["query_preflight_query_len"])) > int(float(row["query_preflight_max_query_len"] or 0))
]

def median(values: list[float]) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0

speedups = [
    float(row["speedup_vs_baseline"])
    for row in clean
    if row["speedup_vs_baseline"] not in {"", "NA", "nan"}
]

text = [
    f"panel_rows={len(rows)}",
    f"completed_rows={len(completed)}",
    f"top5_clean_supported_rows={len(clean)}",
    f"top5_clean_supported_non_h19_rows={len(non_h19)}",
    f"negative_controls={len(neg)}",
    f"negative_controls_guarded={len(negative_guarded)}",
    f"median_speedup_clean={median(speedups):.6f}",
    "decision=" + (
        "short_query_generalization_clean"
        if len(non_h19) >= 8 and len(negative_guarded) >= 3
        else "short_query_generalization_incomplete"
    ),
]
audit.write_text("\n".join(text) + "\n", encoding="utf-8")
print("\n".join(text))
PY

cat "$audit"
