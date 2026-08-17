from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reproduce/biological_topk"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FREEZE = load_module(
    "biological_topk_phase3_freeze",
    ROOT / "reproduce/biological_topk/freeze_fresh_holdout.py",
)
RUNNER = load_module(
    "biological_topk_phase3_runner",
    ROOT / "reproduce/biological_topk/run_fresh_holdout.py",
)
ANALYZER = load_module(
    "biological_topk_phase3_analyzer",
    ROOT / "reproduce/biological_topk/analyze_fresh_holdout.py",
)
PAPER = ROOT / "paper/biological_topk"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Phase3HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = read_tsv(FREEZE.MANIFEST_PATH)
        cls.attempts = read_tsv(FREEZE.ATTEMPT_PLAN_PATH)
        cls.plan = json.loads(FREEZE.PLAN_PATH.read_text(encoding="utf-8"))
        cls.projection = json.loads(FREEZE.RESOURCE_PROJECTION_PATH.read_text(encoding="utf-8"))
        cls.decision = json.loads(FREEZE.RESOURCE_DECISION_PATH.read_text(encoding="utf-8"))

    def test_freeze_reproduces_every_output_byte_for_byte(self) -> None:
        for path, payload in FREEZE.build().items():
            self.assertEqual(path.read_bytes(), payload, path)

    def test_panel_size_pairing_matrix_and_unique_primary_units(self) -> None:
        self.assertEqual(len(self.manifest), 178)
        self.assertEqual(
            Counter(row["query_length_stratum"] for row in self.manifest),
            Counter(FREEZE.PANEL_QUOTAS),
        )
        self.assertEqual(
            Counter(row["target_scale_stratum"] for row in self.manifest),
            Counter(FREEZE.PANEL_QUOTAS),
        )
        expected = Counter(
            {
                (query, target): count
                for query, targets in FREEZE.PAIRING_MATRIX.items()
                for target, count in targets.items()
            }
        )
        self.assertEqual(
            Counter(
                (row["query_length_stratum"], row["target_scale_stratum"])
                for row in self.manifest
            ),
            expected,
        )
        for field in (
            "query_sequence_sha256",
            "target_sequence_sha256",
            "input_pair_digest",
        ):
            self.assertEqual(len({row[field] for row in self.manifest}), 178, field)
        self.assertEqual(
            len(
                {
                    (row["query_ordinal_namespace"], row["query_source_ordinal"])
                    for row in self.manifest
                }
            ),
            178,
        )
        self.assertEqual(
            len(
                {
                    (row["target_ordinal_namespace"], row["target_source_ordinal"])
                    for row in self.manifest
                }
            ),
            178,
        )

    def test_pair_digests_are_canonical_and_have_zero_historical_overlap(self) -> None:
        indexes = FREEZE.exclusion_indexes()
        for row in self.manifest:
            identity = FREEZE.manifest_identity(row)
            payload = {key: value for key, value in identity.items() if key != "input_pair_digest"}
            self.assertEqual(FREEZE.canonical_digest(payload), row["input_pair_digest"])
            self.assertNotIn(row["query_sequence_sha256"], indexes["query_digest"])
            self.assertNotIn(row["target_sequence_sha256"], indexes["target_digest"])
            self.assertNotIn(row["input_pair_digest"], indexes["pair_digest"])
            self.assertNotIn(
                (row["query_ordinal_namespace"], row["query_source_ordinal"]),
                indexes["query_ordinal"],
            )
            self.assertNotIn(
                (row["target_ordinal_namespace"], row["target_source_ordinal"]),
                indexes["target_ordinal"],
            )

    def test_attempt_plan_has_exact_ag_identity_and_balanced_order(self) -> None:
        self.assertEqual(len(self.attempts), 368)
        by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.attempts:
            by_validation[row["validation_instance_id"]].append(row)
        self.assertEqual(len(by_validation), 184)
        identity_fields = (
            "query_ordinal_namespace",
            "query_source_ordinal",
            "query_sequence_sha256",
            "target_ordinal_namespace",
            "target_source_ordinal",
            "target_sequence_sha256",
            "assembly",
            "target_coordinate_namespace",
            "query_extraction_recipe_id",
            "target_extraction_recipe_id",
            "input_pair_digest",
            "parameter_bundle_sha256",
        )
        orders = Counter()
        for pair in by_validation.values():
            self.assertEqual({row["arm"] for row in pair}, {"A", "G"})
            for field in identity_fields:
                self.assertEqual(len({row[field] for row in pair}), 1, field)
            self.assertEqual(sorted(int(row["arm_launch_order"]) for row in pair), [1, 2])
            orders[pair[0]["pair_order"]] += 1
            self.assertEqual(len({row["artifact_root"] for row in pair}), 2)
            self.assertTrue(
                all(
                    row["comparison_policy"] == "offline_after_both_arms_terminal"
                    and row["retry_policy"] == "none"
                    for row in pair
                )
            )
        self.assertEqual(orders, Counter({"AG": 92, "GA": 92}))

    def test_technical_repeats_are_fixed_and_not_independent(self) -> None:
        repeated = [row for row in self.manifest if row["technical_repeat_count"] == "1"]
        self.assertEqual(
            Counter(row["target_scale_stratum"] for row in repeated),
            Counter({"short": 2, "medium": 2, "large": 2}),
        )
        repeat_attempts = [row for row in self.attempts if row["repeat_id"] == "1"]
        self.assertEqual(len(repeat_attempts), 12)
        self.assertTrue(all(row["primary_instance"] == "0" for row in repeat_attempts))
        self.assertTrue(all(row["independent_sample"] == "0" for row in repeat_attempts))

    def test_runtime_is_bound_to_archived_binaries(self) -> None:
        self.assertEqual(sha256_file(FREEZE.AUTHORITY_BINARY_PATH), FREEZE.AUTHORITY_BINARY_SHA256)
        self.assertEqual(sha256_file(FREEZE.CANDIDATE_BINARY_PATH), FREEZE.CANDIDATE_BINARY_SHA256)
        self.assertEqual(
            {row["binary_path"] for row in self.attempts if row["arm"] == "A"},
            {FREEZE.AUTHORITY_BINARY_PATH.relative_to(ROOT).as_posix()},
        )
        self.assertEqual(
            {row["binary_path"] for row in self.attempts if row["arm"] == "G"},
            {FREEZE.CANDIDATE_BINARY_PATH.relative_to(ROOT).as_posix()},
        )
        self.assertNotEqual(sha256_file(ROOT / "fasim_longtarget_x86"), FREEZE.AUTHORITY_BINARY_SHA256)
        self.assertNotEqual(sha256_file(ROOT / "fasim_longtarget_gasal2"), FREEZE.CANDIDATE_BINARY_SHA256)

    def test_manifest_specific_projection_includes_repeats_and_passes_fixed_budget(self) -> None:
        self.assertEqual(self.projection["resource_model_sha256"], FREEZE.RESOURCE_MODEL_SHA256)
        self.assertEqual(self.projection["primary_workload_count"], 178)
        self.assertEqual(self.projection["technical_repeat_instance_count"], 6)
        self.assertEqual(self.projection["projected_validation_instance_count"], 184)
        self.assertEqual(self.projection["projected_attempt_count"], 368)
        self.assertTrue(self.projection["technical_repeats_included"])
        self.assertEqual(self.decision["status"], "pass")
        self.assertTrue(self.decision["fixed_budget_gate_pass"])
        self.assertLessEqual(
            float(self.decision["projected_scheduled_elapsed_wall_seconds_upper_95"]),
            FREEZE.MAX_ELAPSED_SECONDS,
        )
        self.assertLessEqual(
            float(self.decision["projected_gpu_hours_upper_95"]),
            FREEZE.MAX_GPU_HOURS,
        )
        self.assertLessEqual(
            int(self.decision["projected_artifact_storage_bytes_upper_95"]),
            FREEZE.MAX_STORAGE_BYTES,
        )
        self.assertFalse(self.decision["owner_quota_may_be_raised_after_manifest_projection"])

    def test_selection_declares_only_input_side_fields(self) -> None:
        self.assertEqual(self.plan["selection_kind"], "input_only_static_source_metadata")
        self.assertEqual(self.plan["prohibited_selection_fields_used"], [])
        self.assertFalse(self.plan["new_prediction_run"])
        self.assertFalse(self.plan["scientific_output_created"])
        self.assertTrue(self.plan["exclusion_checks"]["hard_gate_pass"])

    def test_phase3_preflight_is_read_only_and_execution_is_not_yet_authorized(self) -> None:
        before_status = RUNNER.git("status", "--porcelain=v1", "--untracked-files=all")
        before_artifacts = RUNNER.ARTIFACT_ROOT.exists()
        manifest, attempts, plan, _ = RUNNER.validate_frozen_plan()
        summary = RUNNER.preflight_summary(manifest, attempts, plan)
        self.assertEqual(summary["status"], "preflight_pass")
        self.assertTrue(summary["read_only"])
        self.assertFalse(summary["scientific_output_created"])
        self.assertEqual(before_status, RUNNER.git("status", "--porcelain=v1", "--untracked-files=all"))
        self.assertEqual(before_artifacts, RUNNER.ARTIFACT_ROOT.exists())
        with self.assertRaises(RUNNER.RunnerError):
            RUNNER.execution_source_commit()

    def test_analyzer_preflight_creates_no_source_data(self) -> None:
        outputs = (
            ANALYZER.MATCHES_PATH,
            ANALYZER.WORKLOAD_METRICS_PATH,
            ANALYZER.EMPTY_PATH,
            ANALYZER.FAILURE_PATH,
            ANALYZER.BOUNDS_PATH,
            ANALYZER.RANK_PATH,
            ANALYZER.RECEIPT_PATH,
            ANALYZER.DECISION_PATH,
        )
        before = [path.exists() for path in outputs]
        summary = ANALYZER.preflight()
        self.assertEqual(summary["status"], "preflight_pass")
        self.assertTrue(summary["read_only"])
        self.assertFalse(summary["scientific_output_created"])
        self.assertEqual(before, [path.exists() for path in outputs])


if __name__ == "__main__":
    unittest.main()
