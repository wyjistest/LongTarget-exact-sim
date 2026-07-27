#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_ROOT="$ROOT/.paper-artifacts/bioinformatics-phase3-application-v1"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
HISTORICAL_COMPLETION="a98d80d44d4418cdb8a67dc8d83ee41b8e599023"

for relative in \
  paper/bioinformatics/application_attempt_plan.tsv \
  paper/bioinformatics/application_attempt_plan.sha256 \
  paper/bioinformatics/application_repeat_subset.tsv \
  paper/bioinformatics/phase3_preexecution_decision.json \
  paper/bioinformatics/application_pilot_receipt.json \
  paper/bioinformatics/application_pilot_artifacts.tsv \
  paper/bioinformatics/application_pilot_artifacts.sha256 \
  paper/bioinformatics/application_resource_projection.json \
  paper/bioinformatics/phase3_postpilot_decision.json \
  reproduce/bioinformatics/run_application.py \
  scripts/check_bioinformatics_phase3_pilot.sh \
  tests/check_run_bioinformatics_application.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe Phase 3 pilot dependency: $relative" >&2
    exit 1
  fi
done

if [[ ! -d "$ARTIFACT_ROOT/pilot" || -L "$ARTIFACT_ROOT" ]]; then
  echo "Phase 3 fixed pilot artifact root is missing or unsafe" >&2
  exit 1
fi
for forbidden in \
  "$ARTIFACT_ROOT/formal-full" \
  "$ARTIFACT_ROOT/formal-repeat" \
  "$ARTIFACT_ROOT/formal-budget.json" \
  "$ARTIFACT_ROOT/formal-full-index.json" \
  "$ARTIFACT_ROOT/formal-repeat-index.json"; do
  if [[ -e "$forbidden" || -L "$forbidden" ]]; then
    echo "formal Phase 3 execution marker exists: $forbidden" >&2
    exit 1
  fi
done

(
  cd "$ROOT/paper/bioinformatics"
  sha256sum --check --status application_attempt_plan.sha256
  sha256sum --check --status application_pilot_artifacts.sha256
)

python3 -m py_compile \
  "$ROOT/reproduce/bioinformatics/run_application.py" \
  "$ROOT/tests/check_run_bioinformatics_application.py"
for document in \
  application_pilot_receipt.json \
  application_resource_projection.json \
  phase3_preexecution_decision.json \
  phase3_postpilot_decision.json; do
  python3 -m json.tool "$ROOT/paper/bioinformatics/$document" >/dev/null
done

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/tests/check_run_bioinformatics_application.py"

python3 - "$ROOT" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
bio = root / "paper/bioinformatics"

receipt_path = bio / "application_pilot_receipt.json"
projection_path = bio / "application_resource_projection.json"
decision_path = bio / "phase3_postpilot_decision.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
projection = json.loads(projection_path.read_text(encoding="utf-8"))
decision = json.loads(decision_path.read_text(encoding="utf-8"))

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

if decision["pilot_receipt_sha256"] != digest(receipt_path):
    raise SystemExit("post-pilot decision pilot receipt digest drift")
if decision["resource_projection_sha256"] != digest(projection_path):
    raise SystemExit("post-pilot decision projection digest drift")
if receipt["resource_projection_sha256"] != digest(projection_path):
    raise SystemExit("pilot receipt projection digest drift")
if decision["selected_decision"] != "stop_after_pilot_futility":
    raise SystemExit("Phase 3 post-pilot decision drift")
if decision["b3_status"] != "no_go":
    raise SystemExit("claim B3 status drift")
if decision["formal_execution_started"] is not False:
    raise SystemExit("formal execution status drift")
if projection["within_fixed_budget"] is not True:
    raise SystemExit("pilot resource projection unexpectedly exceeds fixed budget")
if projection["projected_total_wall_seconds"] > projection["fixed_budget_seconds"]:
    raise SystemExit("pilot resource projection arithmetic drift")

observed = receipt["observed"]
if observed["safe_speedup_vs_authority"] >= 1.0:
    raise SystemExit("fixed pilot unexpectedly records safe acceleration")
if observed["safe_wall_reduction_seconds"] >= 0.0:
    raise SystemExit("fixed pilot unexpectedly records a wall-time reduction")
if receipt["formal_source_data"] is not False:
    raise SystemExit("pilot was incorrectly admitted to formal source data")
if receipt["candidate_only_is_safe_acceleration"] is not False:
    raise SystemExit("candidate-only evidence was mislabeled as safe acceleration")

status = subprocess.run(
    [
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignored=no",
    ],
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout
if status:
    raise SystemExit("Phase 3 pilot audit requires a clean checkout: " + status.replace("\n", " | "))

print(f"pilot_receipt_sha256={digest(receipt_path)}")
print(f"resource_projection_sha256={digest(projection_path)}")
print(f"safe_speedup_vs_authority={observed['safe_speedup_vs_authority']}")
print(f"projected_total_wall_seconds={projection['projected_total_wall_seconds']}")
PY

if ! git -C "$ROOT" merge-base --is-ancestor "$HISTORICAL_COMPLETION" HEAD; then
  echo "historical paper completion commit is not an ancestor of HEAD" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$RUNTIME_COMMIT" -- \
  fasim cuda longtarget.cpp sim.h exact_sim.h rules.h stats.h; then
  echo "Phase 3 pilot changed immutable runtime paths" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$HISTORICAL_COMPLETION" HEAD -- \
  paper/source_data paper/workload_manifest.tsv; then
  echo "historical frozen source data changed" >&2
  exit 1
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 3 fixed pilot checks OK"
echo "phase3_fixed_pilot=complete"
echo "pilot_formal_source_data=0"
echo "pilot_technical_failures=0"
echo "pilot_fallbacks=0"
echo "pilot_timeouts=0"
echo "pilot_ooms=0"
echo "b3_promotion_feasibility=structurally_unreachable_under_verified_only_v1"
echo "b3_status=no_go"
echo "formal_phase3_execution_started=0"
echo "formal_phase3_execution_decision=stop_after_pilot_futility"
