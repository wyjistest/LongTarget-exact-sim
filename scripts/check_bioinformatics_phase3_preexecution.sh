#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/reproduce/bioinformatics/run_application.py"
PLAN="$ROOT/paper/bioinformatics/application_attempt_plan.tsv"
PLAN_SHA="$ROOT/paper/bioinformatics/application_attempt_plan.sha256"
SUBSET="$ROOT/paper/bioinformatics/application_repeat_subset.tsv"
DECISION="$ROOT/paper/bioinformatics/phase3_preexecution_decision.json"
ARTIFACT_ROOT="$ROOT/.paper-artifacts/bioinformatics-phase3-application-v1"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
HISTORICAL_COMPLETION="a98d80d44d4418cdb8a67dc8d83ee41b8e599023"

for relative in \
  paper/bioinformatics/application_manifest.tsv \
  paper/bioinformatics/application_manifest.sha256 \
  paper/bioinformatics/application_protocol.md \
  paper/bioinformatics/application_attempt_plan.tsv \
  paper/bioinformatics/application_attempt_plan.sha256 \
  paper/bioinformatics/application_repeat_subset.tsv \
  paper/bioinformatics/phase3_preexecution_decision.json \
  reproduce/bioinformatics/run_application.py \
  scripts/check_bioinformatics_phase3_preexecution.sh \
  tests/check_run_bioinformatics_application.py \
  schemas/gasal2_longtarget_run_report.schema.json \
  scripts/gasal2_longtarget.py \
  scripts/compare_fasim_segmented_contract.py \
  fasim_longtarget_x86 \
  fasim_longtarget_gasal2; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe Phase 3 preexecution dependency: $relative" >&2
    exit 1
  fi
done

if [[ -e "$ARTIFACT_ROOT" || -L "$ARTIFACT_ROOT" ]]; then
  echo "Phase 3 execution marker already exists: $ARTIFACT_ROOT" >&2
  exit 1
fi

expected_manifest_sha="e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
observed_manifest_sha="$(sha256sum "$ROOT/paper/bioinformatics/application_manifest.tsv" | awk '{print $1}')"
if [[ "$observed_manifest_sha" != "$expected_manifest_sha" ]]; then
  echo "Phase 3 application manifest digest drift" >&2
  exit 1
fi
sha256sum --check --status "$ROOT/paper/bioinformatics/application_manifest.sha256"
sha256sum --check --status "$PLAN_SHA"

python3 -m py_compile "$RUNNER" "$ROOT/tests/check_run_bioinformatics_application.py"
python3 -m json.tool "$DECISION" >/dev/null
python3 "$ROOT/tests/check_run_bioinformatics_application.py"

plan_summary="$(PYTHONDONTWRITEBYTECODE=1 python3 "$RUNNER" --plan-only)"
python3 - "$plan_summary" <<'PY'
import json
import sys

summary = json.loads(sys.argv[1])
expected = {
    "attempt_count": 24,
    "attempt_counts_by_stage": {
        "pilot": 3,
        "formal_full": 3,
        "formal_repeat": 18,
    },
    "b3_promotion_feasibility": "structurally_unreachable_under_verified_only_v1",
    "full_run_decision": "pending_fixed_pilot",
    "application_execution_started": False,
}
for key, value in expected.items():
    if summary.get(key) != value:
        raise SystemExit(f"Phase 3 plan summary drift: {key}")
if summary.get("pilot_attempt_ids") != [
    "p3pilot_a_aq001_at0001",
    "p3pilot_b_aq001_at0001",
    "p3pilot_c_aq001_at0001",
]:
    raise SystemExit("Phase 3 pilot attempt identity drift")
print(f"attempt_plan_sha256={summary['attempt_plan_sha256']}")
print(f"runner_commit={summary['runner_commit']}")
print(f"runner_sha256={summary['runner_sha256']}")
PY

python3 - "$ROOT" <<'PY'
import csv
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
plan_path = root / "paper/bioinformatics/application_attempt_plan.tsv"
with plan_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 24:
    raise SystemExit("Phase 3 attempt plan row count drift")
if any(row["status"] != "preregistered_not_run" for row in rows):
    raise SystemExit("Phase 3 attempt plan contains an execution result")
if any(row["retry_policy"] != "none" for row in rows):
    raise SystemExit("Phase 3 attempt plan retry policy drift")
if any(row["worker_count"] != "2" for row in rows):
    raise SystemExit("Phase 3 attempt plan worker count drift")
if any(row["backend_timeout_seconds"] != "3600" for row in rows):
    raise SystemExit("Phase 3 attempt plan timeout drift")
if any(row["total_budget_seconds"] != "86400" for row in rows):
    raise SystemExit("Phase 3 attempt plan budget drift")

decision = json.loads(
    (root / "paper/bioinformatics/phase3_preexecution_decision.json").read_text(
        encoding="utf-8"
    )
)
if decision["phase2_decision"] != "verified_only_contract":
    raise SystemExit("Phase 2 decision drift")
if decision["b3_threshold_changed"] is not False:
    raise SystemExit("B3 threshold was changed")
if decision["b3_safe_speedup_threshold"] != 10.0:
    raise SystemExit("B3 safe speedup threshold drift")
if decision["pilot_can_promote_b3"] is not False:
    raise SystemExit("pilot was incorrectly allowed to promote B3")
if "continue_for_b3_promotion" in decision["allowed_post_pilot_decisions"]:
    raise SystemExit("illegal post-pilot decision is present")
if decision["postpilot_decision_precedence"] != [
    "blocked_by_operational_failure",
    "blocked_by_fixed_budget",
    "stop_after_pilot_futility",
]:
    raise SystemExit("post-pilot decision precedence drift")
if decision["resource_projection_conservatism_factor"] != 1.25:
    raise SystemExit("resource projection factor drift")

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
    raise SystemExit("Phase 3 preexecution requires a clean checkout: " + status.replace("\n", " | "))
PY

gpu_count="$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)"
if (( gpu_count < 2 )); then
  echo "Phase 3 preexecution requires GPU 0 and GPU 1" >&2
  exit 1
fi

if ! git -C "$ROOT" merge-base --is-ancestor "$HISTORICAL_COMPLETION" HEAD; then
  echo "historical paper completion commit is not an ancestor of HEAD" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$RUNTIME_COMMIT" -- \
  fasim cuda longtarget.cpp sim.h exact_sim.h rules.h stats.h; then
  echo "Phase 3 preexecution changed immutable runtime paths" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$HISTORICAL_COMPLETION" HEAD -- \
  paper/source_data paper/workload_manifest.tsv; then
  echo "historical frozen source data changed" >&2
  exit 1
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 3 preexecution checks OK"
echo "phase3_input_freeze=complete"
echo "phase3_protocol=complete"
echo "phase3_attempt_plan=frozen"
echo "phase3_runner=preexecution_validated"
echo "phase3_fixed_pilot=not_run"
echo "b3_promotion_feasibility=structurally_unreachable_under_verified_only_v1"
echo "formal_phase3_execution_decision=pending_fixed_pilot"
echo "application_execution_started=0"
