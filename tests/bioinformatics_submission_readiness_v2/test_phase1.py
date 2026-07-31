from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CHECKER = load_module(
    "submission_readiness_v2_phase1_checker",
    ROOT / "scripts/check_bioinformatics_submission_readiness_v2.py",
)
CANDIDATE_SITES = load_module(
    "submission_readiness_v2_candidate_sites",
    ROOT / "scripts/gasal2_candidate_sites.py",
)
GPU_SCREEN = load_module(
    "submission_readiness_v2_gpu_screen",
    ROOT / "scripts/gasal2_gpu_screen.py",
)


class Phase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = json.loads(CHECKER.STATE.read_text(encoding="utf-8"))
        self.runtime = json.loads(
            (CHECKER.PAPER / "phase_1_runtime_identity.json").read_text(encoding="utf-8")
        )

    def test_four_identities_are_independent_and_exact(self) -> None:
        self.assertEqual(
            self.runtime["execution_identity"],
            {
                "execution_mode": "gpu-screen",
                "scientific_contract": "biological_topk_candidate_site_v1",
                "output_schema": "gasal2_candidate_sites_tsv_v1",
                "software_epoch": "submission_rc_v2",
            },
        )

    def test_product_remains_pending_phase4(self) -> None:
        self.assertEqual(self.state["artifact_role"], "frozen_release_candidate_under_test")
        self.assertEqual(self.state["product_status"], "experimental")
        self.assertEqual(self.state["validation_status"], "pending")
        self.assertEqual(self.runtime["validation_status"], "pending_phase4")
        self.assertFalse(self.runtime["formal_performance_claim"])

    def test_gpu_screen_has_no_authority_binary_option(self) -> None:
        destinations = {action.dest for action in GPU_SCREEN.parser()._actions}
        self.assertNotIn("authority_binary", destinations)
        self.assertNotIn("mode", destinations)
        self.assertFalse(self.runtime["complete_cpu_authority_inside_product"])

    def test_schema_descriptor_is_exact(self) -> None:
        frozen = json.loads(
            (ROOT / "schemas/gasal2_candidate_sites_tsv_v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(frozen, CANDIDATE_SITES.schema_descriptor())

    def test_downstream_work_is_not_authorized(self) -> None:
        self.assertFalse(self.state["external_comparison_authorized"])
        self.assertFalse(self.state["release_packaging_authorized"])
        self.assertFalse(self.state["submission_drafting_authorized"])

    def test_smoke_is_diagnostic_and_excluded(self) -> None:
        smoke = json.loads(
            (CHECKER.PAPER / "phase_1_smoke_receipt.json").read_text(encoding="utf-8")
        )
        self.assertTrue(smoke["development_diagnostic_only"])
        self.assertTrue(smoke["excluded_from_all_v2_formal_panels"])
        self.assertFalse(smoke["performance_estimate_generated"])


if __name__ == "__main__":
    unittest.main()
