#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT/Makefile" <<'PY'
import re
import sys
from pathlib import Path

makefile = Path(sys.argv[1]).read_text(encoding="utf-8")
root = Path(sys.argv[1]).resolve().parent


def continued_line(prefix: str) -> str:
    lines = makefile.splitlines()
    for idx, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        parts = [line.rstrip("\\").strip()]
        j = idx + 1
        while line.endswith("\\") and j < len(lines):
            line = lines[j]
            parts.append(line.rstrip("\\").strip())
            j += 1
        return " ".join(parts)
    raise SystemExit(f"missing Makefile line starting with {prefix!r}")


formal_line = continued_line("check-fasim-gasal2-top5-formal-gate:")
formal_deps = set(formal_line.split()[1:])
required_deps = {
    "check-fasim-gasal2-formal-makefile-gate",
    "check-fasim-gasal2-top5-formal-gate",
    "check-fasim-gasal2-top5-binary-guard",
    "check-fasim-gasal2-top5-output-contract",
    "check-fasim-gasal2-long-query-boundary",
    "check-fasim-gasal2-topk-lite-wrapper-contract",
    "check-fasim-top5-gasal2-gpu-scoreinfo-default-off",
    "check-fasim-top5-gasal2-gpu-scoreinfo-env",
    "check-fasim-sharded-gasal2-top5-prune-runner",
    "check-fasim-gasal2-column-pruned-preset-top5-matrix",
    "check-fasim-gasal2-top5-lowercase-input",
    "check-fasim-gasal2-formal-preset-examples",
    "check-fasim-exact-scoreinfo-gpu-examples-gate",
    "check-fasim-gasal2-top5-scoreinfo-milestone",
}
formal_target = "check-fasim-gasal2-top5-formal-gate"
expected_formal_deps = required_deps - {formal_target}
missing_deps = sorted(expected_formal_deps - formal_deps)
if missing_deps:
    raise SystemExit(
        "formal GASAL2 top5 gate missing dependencies: " + ", ".join(missing_deps)
    )

phony_targets = []
lines = makefile.splitlines()
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith(".PHONY:"):
        text = line.split(":", 1)[1].strip()
        while text.endswith("\\") and index + 1 < len(lines):
            text = text[:-1] + " " + lines[index + 1].strip()
            index += 1
        phony_targets.extend(text.split())
    index += 1
if not phony_targets:
    raise SystemExit("missing .PHONY block")
phony_targets = set(phony_targets)
missing_phony = sorted(required_deps - phony_targets)
if missing_phony:
    raise SystemExit(
        "formal GASAL2 top5 dependencies missing from .PHONY: "
        + ", ".join(missing_phony)
    )

gitignore = root / ".gitignore"
ignored = set(gitignore.read_text(encoding="utf-8").splitlines())
if "/fasim_longtarget_gasal2" not in ignored:
    raise SystemExit("missing /fasim_longtarget_gasal2 in .gitignore")

for rel in (
    "docs/fasim_sharded_runner.md",
    "docs/fasim_gasal2_longtarget_bridge.md",
):
    doc = root / rel
    text = doc.read_text(encoding="utf-8")
    if "check-fasim-gasal2-formal-makefile-gate" not in text:
        raise SystemExit(
            f"{rel} does not mention check-fasim-gasal2-formal-makefile-gate"
        )
    if "check-fasim-gasal2-top5-output-contract" not in text:
        raise SystemExit(
            f"{rel} does not mention check-fasim-gasal2-top5-output-contract"
        )
    if "check-fasim-gasal2-top5-scoreinfo-milestone-result" not in text:
        raise SystemExit(
            f"{rel} does not mention scoreInfo milestone result gate"
        )
    if "check-fasim-gasal2-long-query-boundary" not in text:
        raise SystemExit(
            f"{rel} does not mention check-fasim-gasal2-long-query-boundary"
        )
    if "check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow" not in text:
        raise SystemExit(
            f"{rel} does not mention segmented pruned traceback shadow gate"
        )
    if "check-fasim-gasal2-long-query-segmented-replay-no-last" not in text:
        raise SystemExit(
            f"{rel} does not mention segmented replay no-last gate"
        )
    if "docs/fasim_gasal2_top5_output_contract.md" not in text:
        raise SystemExit(
            f"{rel} does not mention docs/fasim_gasal2_top5_output_contract.md"
        )
    if "docs/fasim_gasal2_long_query_boundary.md" not in text:
        raise SystemExit(
            f"{rel} does not mention docs/fasim_gasal2_long_query_boundary.md"
        )
    if "top5 preset therefore uses `20000` as its\ndefault GASAL2 batch size" in text:
        raise SystemExit(f"{rel} contains stale GASAL2 top5 batch-size default")

formal_column_pruned_phrase = (
    "formal `--gasal2-top5-column-pruned-scoreinfo` preset additionally sets"
)
formal_rank_observe_phrase = (
    "`FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1`"
)
formal_prealign_max_tasks_phrase = "`FASIM_PREALIGN_CUDA_MAX_TASKS=16384`"
batch_limit_phrase = (
    "`FASIM_ALIGN_GASAL2_BATCH` remains an allowed diagnostic override, "
    "but the formal preset rejects values above `30000`"
)
streams_limit_phrase = (
    "`FASIM_ALIGN_GASAL2_STREAMS` remains an allowed diagnostic override, "
    "but the formal preset rejects values above `16`, non-integers, "
    "and non-positive values"
)
query_limit_phrase = (
    "`FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` remains an allowed diagnostic override, "
    "but the formal preset rejects values above `2812`, non-integers, "
    "and non-positive values"
)
query_report_phrase = (
    "formal preset records `gasal2_top5_query_preflight_supported`, "
    "`gasal2_top5_query_preflight_query_len`, and "
    "`gasal2_top5_query_preflight_max_query_len` in `report.json` "
    "and `run_manifest.json`"
)
query_manifest_match_phrase = (
    "formal artifact integrity checks require manifest query-preflight fields "
    "to match the report"
)
query_internal_check_phrase = (
    "formal artifact integrity checks also require query length to be within "
    "the recorded max query length"
)
managed_env_integrity_phrase = (
    "formal artifact integrity checks require managed preset `env_overrides`, "
    "including `FASIM_PREALIGN_CUDA_MAX_TASKS=16384`, to match the formal preset"
)
examples_active_column_phrase = (
    "examples gate reports `scoreinfo_gasal2_active` so guarded long-query CPU "
    "fallback rows cannot be mistaken for active GASAL2/exact-scoreInfo shards"
)
matrix_active_runs_phrase = (
    "bounded matrix aggregate reports `active_path_runs` so top5-clean rows must "
    "also prove active GASAL2/exact-scoreInfo coverage"
)
manifest_env_integrity_phrase = (
    "formal artifact integrity checks also require manifest `env_snapshot` "
    "to carry the same managed preset values"
)
benchmark_integrity_phrase = (
    "formal artifact integrity checks recompute the active-path requirement "
    "from `fasim_benchmark_sums`"
)
rank_observe_integrity_phrase = (
    "formal artifact integrity checks also require topK-lite scoreInfo-rank "
    "observe telemetry to be enabled, non-empty, and free of unknown rows"
)
topk_summary_object_integrity_phrase = (
    "artifact integrity checks require the `topk_summary` report object to match "
    "the topK summary and rows artifacts"
)
query_resume_bounds_phrase = (
    "Formal resume requires the same verified query-preflight length bounds "
    "before reusing shards"
)
segmented_env_reject_phrase = (
    "rejects long-query segmented diagnostic env keys such as "
    "`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW`"
)
segmented_env_integrity_phrase = (
    "Formal artifact integrity checks reject the same segmented diagnostic env keys"
)
unsupported_env_integrity_phrase = (
    "They also reject unsupported formal env extras such as "
    "`FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST`"
)
query_max_env_match_phrase = (
    "must match the recorded `gasal2_top5_query_preflight_max_query_len`"
)
formal_non_goal_phrase = (
    "formal GASAL2 top5 artifact path is not full lite-output equivalence "
    "and is not an `aligner.Align()` replacement"
)
formal_wrapper_phrase = (
    "`run_fasim_gasal2_topk_lite.sh` defaults to the formal "
    "`--gasal2-top5-column-pruned-scoreinfo` runner preset"
)
legacy_wrapper_phrase = (
    "`LEGACY_DIRECT=1` keeps the older direct-env wrapper path available "
    "for investigation only"
)
wrapper_contract_gate_phrase = "check-fasim-gasal2-topk-lite-wrapper-contract"
for rel in (
    "docs/fasim_sharded_runner.md",
    "docs/fasim_gasal2_longtarget_bridge.md",
):
    text = (root / rel).read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    if formal_column_pruned_phrase not in text:
        raise SystemExit(
            f"{rel} does not document formal column-pruned managed env"
        )
    if formal_rank_observe_phrase not in text:
        raise SystemExit(
            f"{rel} does not document formal topK-lite rank observe telemetry"
        )
    if formal_prealign_max_tasks_phrase not in text:
        raise SystemExit(
            f"{rel} does not document formal preAlign max-tasks setting"
        )
    if batch_limit_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal GASAL2 batch limit")
    if streams_limit_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal GASAL2 streams limit")
    if query_limit_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal GASAL2 query limit")
    if query_report_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal GASAL2 query report fields")
    if query_manifest_match_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 query manifest matching"
        )
    if query_internal_check_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 query internal checks"
        )
    if managed_env_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 managed env integrity checks"
        )
    if examples_active_column_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document GASAL2 examples active-path column"
        )
    if matrix_active_runs_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document GASAL2 matrix active-path aggregate"
        )
    if manifest_env_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 manifest env integrity checks"
        )
    if benchmark_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 benchmark integrity checks"
        )
    if rank_observe_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 rank observe integrity checks"
        )
    if topk_summary_object_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document topK summary object integrity checks"
        )
    if query_resume_bounds_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document formal GASAL2 resume query bounds"
        )
    if segmented_env_reject_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document segmented diagnostic env rejection"
        )
    if segmented_env_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document segmented diagnostic env integrity rejection"
        )
    if unsupported_env_integrity_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document unsupported formal env integrity rejection"
        )
    if query_max_env_match_phrase not in normalized_text:
        raise SystemExit(
            f"{rel} does not document query max env/preflight matching"
        )
    if formal_non_goal_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal GASAL2 non-goals")
    if formal_wrapper_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document formal topK-lite wrapper default")
    if legacy_wrapper_phrase not in normalized_text:
        raise SystemExit(f"{rel} does not document legacy topK-lite wrapper escape hatch")
    if wrapper_contract_gate_phrase not in text:
        raise SystemExit(f"{rel} does not mention topK-lite wrapper contract gate")

examples_gate = root / "scripts/check_fasim_exact_scoreinfo_gpu_examples_gate.sh"
examples_text = examples_gate.read_text(encoding="utf-8")
if "scoreinfo_gasal2_active" not in examples_text:
    raise SystemExit("examples gate does not report scoreinfo_gasal2_active")
if "query_preflight_supported\" == \"0\"" not in examples_text:
    raise SystemExit("examples gate does not keep explicit long-query guard checks")

milestone = root / "docs/fasim_gasal2_top5_scoreinfo_milestone.md"
if not milestone.exists():
    raise SystemExit("missing GASAL2 top5 scoreInfo milestone doc")
milestone_text = " ".join(milestone.read_text(encoding="utf-8").split())
for phrase in (
    "short-query / H19 formal GASAL2 top5 scoreInfo/preAlign artifact path",
    "active_path_runs = 1/1",
    "speedup vs CPU worker wall sum = 40.119136x",
    "not full lite-output equivalence",
    "not an `aligner.Align()` replacement",
    "MALAT1/NEAT1 long-query GASAL2 path remains guarded out",
):
    if phrase not in milestone_text:
        raise SystemExit(f"milestone doc missing phrase: {phrase}")

print("ok")
PY
