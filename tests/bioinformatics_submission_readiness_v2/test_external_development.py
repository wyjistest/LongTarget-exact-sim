from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "reproduce/bioinformatics_submission_readiness_v2/run_external_development.py"
SPEC = importlib.util.spec_from_file_location("v2_external_development", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["v2_external_development"] = MODULE
SPEC.loader.exec_module(MODULE)


class ExternalDevelopmentTests(unittest.TestCase):
    def test_commands_use_basename_and_expected_suffix(self) -> None:
        command = MODULE.command_for(
            "triplexator",
            Path("/tool"),
            Path("/query.fa"),
            Path("/target.fa"),
            "external-result",
        )
        self.assertEqual(command[-2:], ["-o", "external-result"])
        self.assertNotIn("/output/external-result", command)

    def test_header_only_summary_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.summary"
            path.write_text("\t".join(MODULE.SUMMARY_FIELDS) + "\n", encoding="utf-8")
            self.assertEqual(
                MODULE.validate_summary(path),
                {
                    "row_count": 0,
                    "header_only": True,
                    "sha256": MODULE.sha256(path),
                    "size_bytes": path.stat().st_size,
                },
            )

    def test_valid_data_row_is_bound_to_summary_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.summary"
            path.write_text(
                "\t".join(MODULE.SUMMARY_FIELDS)
                + "\nq\tt\t1\t0.5\t1\t0.5\t0\t0\t0\t0\n",
                encoding="utf-8",
            )
            result = MODULE.validate_summary(path)
            self.assertEqual(result["row_count"], 1)
            self.assertFalse(result["header_only"])
            self.assertEqual(result["sha256"], MODULE.sha256(path))

    def test_wrong_suffix_or_columns_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(MODULE.ExternalDevelopmentError):
                MODULE.validate_summary(root / "missing.summary")
            path = root / "bad.summary"
            path.write_text("wrong\theader\n", encoding="utf-8")
            with self.assertRaises(MODULE.ExternalDevelopmentError):
                MODULE.validate_summary(path)


if __name__ == "__main__":
    unittest.main()
