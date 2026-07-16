#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase6}"
SOURCE="$ROOT/paper/source_data"
GOAL="$ROOT/goal-final.md"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for path in \
  "$GOAL" "$ROOT/reproduce/render_figures.py" \
  "$ROOT/tests/check_render_fasim_gasal2_paper_figures.py" \
  "$ROOT/paper/captions.md" "$ROOT/paper/figures/render_manifest.tsv" \
  "$ROOT/paper/figures/source_mapping.tsv"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 6 dependency: $path" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

python3 "$ROOT/tests/check_render_fasim_gasal2_paper_figures.py"
python3 -m py_compile "$ROOT/reproduce/render_figures.py"

rm -rf "$WORK"
mkdir -p "$WORK/paper"
python3 "$ROOT/reproduce/render_figures.py" \
  --source-dir "$SOURCE" \
  --output-root "$WORK/paper" >"$WORK/render.stdout"

cmp "$ROOT/paper/captions.md" "$WORK/paper/captions.md"
diff -r "$ROOT/paper/figures" "$WORK/paper/figures"
diff -r "$ROOT/paper/tables" "$WORK/paper/tables"
diff -r "$ROOT/paper/supplementary" "$WORK/paper/supplementary"

python3 - "$ROOT" "$GOAL" <<'PY'
from __future__ import annotations

import csv
import hashlib
import math
import sys
from pathlib import Path

from PIL import Image


root, goal_path = (Path(value).resolve() for value in sys.argv[1:])
paper = root / "paper"
source = paper / "source_data"
freeze_id = "paper-data-v1-dccfd49-20260716"
figure_bases = (
    "fig1_method_fast_topk",
    "fig2_performance_generalization",
    "fig3_ablation_resources",
    "fig4_operating_envelope",
    "figS1_archive_first",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


state: dict[str, str] = {}
for raw in goal_path.read_text(encoding="utf-8").splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
active = int(state.get("active_phase", "-1"))
completed = int(state.get("last_completed_phase", "-1"))
if active < 7 or completed < 6 or state.get("phase_6_status") != "pass":
    raise SystemExit("goal state has not completed paper Phase 6")
if active == 7:
    expected = {
        "last_completed_phase": "6",
        "last_decision": "paper_figures_tables_generated",
        "last_evidence_doc": "paper/captions.md",
        "last_test_command": "make check-fasim-gasal2-paper-phase6",
        "last_commit": "figures: generate paper-ready GASAL2-LongTarget figures and tables",
    }
    for key, value in expected.items():
        if state.get(key) != value:
            raise SystemExit(f"Phase 6 terminal state mismatch: {key}")

for base in figure_bases:
    svg = paper / "figures" / f"{base}.svg"
    pdf = paper / "figures" / f"{base}.pdf"
    png = paper / "figures" / f"{base}_600dpi.png"
    for path in (svg, pdf, png):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing figure output: {path}")
    svg_text = svg.read_text(encoding="utf-8")
    if "<image" in svg_text or "nan" in svg_text.lower():
        raise SystemExit(f"raster embedding or NaN in SVG: {svg}")
    if not pdf.read_bytes().startswith(b"%PDF-"):
        raise SystemExit(f"invalid PDF header: {pdf}")
    with Image.open(png) as image:
        dpi = image.info.get("dpi", (0, 0))
        if min(image.size) < 1900 or image.width < 4000:
            raise SystemExit(f"PNG resolution too small: {png} {image.size}")
        if not all(math.isclose(value, 600, abs_tol=1) for value in dpi):
            raise SystemExit(f"PNG DPI metadata drifted: {png} {dpi}")

fig1 = (paper / "figures/fig1_method_fast_topk.svg").read_text(encoding="utf-8")
for phrase in (
    "Shared LongTarget task construction and output semantics",
    "GASAL2-LongTarget fast top-K",
    "Measured fast top-K speedup",
):
    if phrase not in fig1:
        raise SystemExit(f"Figure 1 text missing: {phrase}")
if "full-output" in fig1 or "equivalence bridge" in fig1:
    raise SystemExit("Figure 1 B2/D scope expanded beyond fast top-K")

mapping_fields, mappings = read_tsv(paper / "figures/source_mapping.tsv")
if mapping_fields != ["figure_id", "panel", "source_data_file", "filter", "output_contract"] or len(mappings) != 7:
    raise SystemExit("figure source mapping schema/count drifted")
for row in mappings:
    for source_file in row["source_data_file"].split(";"):
        if not (source / source_file).is_file():
            raise SystemExit(f"figure mapping source missing: {source_file}")
fig1_d = next(row for row in mappings if row["figure_id"] == "Figure 1" and row["panel"] == "D")
if fig1_d["output_contract"] != "fast_topk_score_stability_nt":
    raise SystemExit("Figure 1 D includes a non-fast-top-K contract")

_, manifest = read_tsv(paper / "figures/render_manifest.tsv")
if len(manifest) != 30 or {row["data_freeze_id"] for row in manifest} != {freeze_id}:
    raise SystemExit("render manifest count/freeze drifted")
for row in manifest:
    path = paper / row["path"]
    if not path.is_file() or path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
        raise SystemExit(f"render manifest mismatch: {path}")
if any(row["path"].startswith("source_data/") for row in manifest):
    raise SystemExit("render manifest included frozen inputs as generated outputs")

summary_fields, summaries = read_tsv(source / "paired_speedup_summary.tsv")
table_fields, performance = read_tsv(paper / "tables/table2_performance.tsv")
if len(performance) != len(summaries) or {row["workload_id"] for row in performance} != {row["workload_id"] for row in summaries}:
    raise SystemExit("Table 2 workload set drifted from analyzer")
summary_map = {row["workload_id"]: row for row in summaries}
for row in performance:
    source_row = summary_map[row["workload_id"]]
    if not math.isclose(float(row["median_speedup"]), float(source_row["median_paired_speedup"]), rel_tol=5e-4):
        raise SystemExit(f"Table 2 speedup drifted: {row['workload_id']}")

for name in (
    "table1_workloads", "table2_performance", "table3_correctness", "table4_ablation_resources",
):
    for suffix in ("tsv", "md", "tex"):
        if not (paper / "tables" / f"{name}.{suffix}").is_file():
            raise SystemExit(f"missing table output: {name}.{suffix}")
if not (paper / "supplementary/operating_envelope.tsv").is_file():
    raise SystemExit("supplementary operating-envelope table missing")

captions = (paper / "captions.md").read_text(encoding="utf-8")
for phrase in (
    "score/stability/Nt clustered TFO1-TFO5 contract",
    "`n=1` and no inferential interval",
    "one worker per GPU",
    "SQLite reduces memory at additional wall-time cost",
    "Source:",
):
    if phrase not in captions:
        raise SystemExit(f"caption contract missing: {phrase}")

print("GASAL2 paper Phase 6 gate OK")
print("vector_figure_sets=5")
print("png_dpi=600")
print("render_manifest_rows=30")
print("table_bundles=4")
PY

git -C "$ROOT" diff --check
echo "GASAL2 paper Phase 6 checks OK"
