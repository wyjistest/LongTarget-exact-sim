from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from reproduce.biological_topk_successor import analyze_phase4, freeze_phase3, run_phase4


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
V1 = ROOT / "paper/biological_topk"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class SuccessorPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = read_tsv(PAPER / "fresh_holdout_manifest.tsv")
        cls.attempts = read_tsv(PAPER / "fresh_holdout_attempt_plan.tsv")
        cls.plan = json.loads((PAPER / "fresh_holdout_plan.json").read_text(encoding="utf-8"))
        cls.projection = json.loads((PAPER / "fresh_holdout_resource_projection.json").read_text(encoding="utf-8"))
        cls.decision = json.loads((PAPER / "fresh_holdout_resource_decision.json").read_text(encoding="utf-8"))

    def test_panel_is_new_and_globally_unique(self) -> None:
        self.assertEqual(len(self.manifest), 178)
        for field in ("query_sequence_sha256", "target_sequence_sha256", "input_pair_digest"):
            self.assertEqual(len({row[field] for row in self.manifest}), 178, field)
        old = read_tsv(V1 / "fresh_holdout_manifest.tsv")
        self.assertFalse({row["query_sequence_sha256"] for row in old} & {row["query_sequence_sha256"] for row in self.manifest})
        self.assertFalse({row["target_sequence_sha256"] for row in old} & {row["target_sequence_sha256"] for row in self.manifest})
        self.assertFalse({row["input_pair_digest"] for row in old} & {row["input_pair_digest"] for row in self.manifest})

    def test_panel_and_attempt_quotas_are_frozen(self) -> None:
        self.assertEqual(Counter(row["query_length_stratum"] for row in self.manifest), Counter({"short": 60, "medium": 59, "large": 59}))
        self.assertEqual(Counter(row["target_scale_stratum"] for row in self.manifest), Counter({"short": 60, "medium": 59, "large": 59}))
        self.assertEqual(len(self.attempts), 368)
        by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.attempts:
            by_validation[row["validation_instance_id"]].append(row)
        self.assertEqual(len(by_validation), 184)
        self.assertEqual(Counter(pair[0]["pair_order"] for pair in by_validation.values()), Counter({"AG": 92, "GA": 92}))
        self.assertTrue(all({row["arm"] for row in pair} == {"A", "G"} for pair in by_validation.values()))
        self.assertTrue(all(row["artifact_root"].startswith(".paper-artifacts/biological-topk-successor/fresh-holdout/") for row in self.attempts))

    def test_manifest_specific_resource_gate_includes_all_reservations(self) -> None:
        values = self.projection["projection"]
        self.assertEqual(values["predecessor_retained_bytes"], 7_142_325_727)
        self.assertGreater(values["successor_tracked_bytes_through_phase2"], 0)
        self.assertEqual(values["successor_phase3_phase4_tracked_reservation_bytes"], 256 * 1024**2)
        self.assertEqual(values["raw_g_telemetry_reservation_bytes"], 1536 * 1024**2)
        self.assertEqual(values["fixed_total_artifact_storage_bytes"], 64 * 1024**3)
        self.assertGreater(values["artifact_storage_margin_bytes"], 0)
        self.assertTrue(self.decision["fixed_budget_gate_pass"])
        self.assertTrue(self.decision["phase_4_execution_authorized"])

    def test_selection_and_preflights_are_input_only_and_read_only(self) -> None:
        self.assertEqual(self.plan["selection_kind"], "input_only_static_source_metadata")
        self.assertEqual(self.plan["prohibited_selection_fields_used"], [])
        self.assertFalse(self.plan["new_prediction_run"])
        self.assertFalse(self.plan["scientific_output_created"])
        self.assertEqual(self.plan["predecessor_phase4_input_overlap_count"], 0)
        self.assertEqual(run_phase4.preflight_summary(*run_phase4.validate_frozen_plan()[:3])["status"], "preflight_pass")
        self.assertEqual(analyze_phase4.preflight()["status"], "preflight_pass")

    def test_telemetry_gzip_is_deterministic_and_lossless(self) -> None:
        payload = (b'{"event":1}\n' * 1000) + b"end\n"
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            first_source = root / "first.json"
            second_source = root / "second.json"
            first_source.write_bytes(payload)
            second_source.write_bytes(payload)
            first = root / "first.json.gz"
            second = root / "second.json.gz"
            first_receipt = run_phase4.gzip_file_deterministic(first_source, first)
            second_receipt = run_phase4.gzip_file_deterministic(second_source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes()[4:8], b"\0\0\0\0")
            self.assertEqual(gzip.decompress(first.read_bytes()), payload)
            self.assertEqual(first_receipt["uncompressed_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(first_receipt["compressed_sha256"], second_receipt["compressed_sha256"])


if __name__ == "__main__":
    unittest.main()
