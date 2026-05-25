#!/usr/bin/env python3
import json
import tempfile
import threading
from pathlib import Path
from unittest import mock

import fasim_sharded_runner as runner


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "run_manifest.json"
        shard_a = runner.Shard(
            shard_id="shard_a",
            target_name="a",
            target_start=1,
            target_end=10,
            shard_fasta_path=Path(tmp) / "a.fa",
            estimated_length=10,
            estimated_windows=None,
            estimated_cells=None,
        )
        shard_b = runner.Shard(
            shard_id="shard_b",
            target_name="b",
            target_start=1,
            target_end=10,
            shard_fasta_path=Path(tmp) / "b.fa",
            estimated_length=10,
            estimated_windows=None,
            estimated_cells=None,
        )
        payload = {
            "schema_version": 1,
            "run_status": "running",
            "per_shard": [
                {"shard_id": "shard_a", "status": "planned"},
                {"shard_id": "shard_b", "status": "planned"},
            ],
        }
        manifest = runner.RunManifest(manifest_path, payload)

        write_entered = threading.Event()
        allow_first_write_to_continue = threading.Event()
        second_update_finished_before_first_write = threading.Event()

        def controlled_atomic_write(path, payload):
            if not write_entered.is_set():
                write_entered.set()
                allow_first_write_to_continue.wait(timeout=5.0)
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        def first_update():
            manifest.mark_running(shard_a, worker_id=0, gpu_id="0", cpu_core_range="0-1")

        def second_update():
            write_entered.wait(timeout=5.0)
            manifest.mark_running(shard_b, worker_id=1, gpu_id="1", cpu_core_range="2-3")
            second_update_finished_before_first_write.set()

        with mock.patch.object(runner, "_atomic_write_json", side_effect=controlled_atomic_write):
            first = threading.Thread(target=first_update)
            second = threading.Thread(target=second_update)
            first.start()
            second.start()

            assert write_entered.wait(timeout=5.0), "first manifest write did not start"
            second.join(timeout=0.2)
            assert not second_update_finished_before_first_write.is_set(), (
                "second manifest update finished before the first write completed"
            )
            assert manifest.payload["per_shard"][1]["status"] == "planned", (
                "manifest payload mutation was not serialized with manifest write"
            )

            allow_first_write_to_continue.set()
            first.join(timeout=5.0)
            second.join(timeout=5.0)
            assert not first.is_alive(), "first update thread did not finish"
            assert not second.is_alive(), "second update thread did not finish"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
