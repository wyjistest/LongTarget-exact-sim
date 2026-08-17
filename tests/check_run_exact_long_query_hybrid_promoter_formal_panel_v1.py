#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_exact_long_query_hybrid_promoter_formal_panel_v1.py"
SPEC = importlib.util.spec_from_file_location("formal_promoter_panel", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FormalPromoterPanelTests(unittest.TestCase):
    def test_loads_and_balances_eighteen_longest_first_pairs(self) -> None:
        work = MODULE.load_work()
        slots = MODULE.parse_slots(None)
        partitions = MODULE.balanced_partitions(work, slots)
        self.assertEqual(len(work), 18)
        self.assertEqual([len(values) for values in partitions], [9, 9])
        loads = [sum(item.estimated_seconds for item in values) for values in partitions]
        self.assertLess(abs(loads[0] - loads[1]), max(item.estimated_seconds for item in work))
        for values in partitions:
            self.assertEqual(
                [item.estimated_seconds for item in values],
                sorted((item.estimated_seconds for item in values), reverse=True),
            )

    def test_rejects_duplicate_slot_resources(self) -> None:
        with self.assertRaises(MODULE.PanelError):
            MODULE.parse_slots(["0:0", "0:19"])
        with self.assertRaises(MODULE.PanelError):
            MODULE.parse_slots(["0:0", "1:0"])

    def test_state_update_mutates_persisted_pair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="formal-panel-state-") as temporary:
            output = Path(temporary)
            work = MODULE.load_work()[:1]
            slot = MODULE.Slot(ordinal=0, gpu=0, cpu="0")
            orchestrator = MODULE.Orchestrator(output, [slot], [work])
            orchestrator.update(work[0], status="running", stage="baseline")
            persisted = json.loads((output / "state.json").read_text())
            self.assertEqual(persisted["pairs"][work[0].key]["status"], "running")
            self.assertEqual(persisted["pairs"][work[0].key]["stage"], "baseline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
