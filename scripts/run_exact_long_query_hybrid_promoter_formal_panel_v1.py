#!/usr/bin/env python3
"""Run the authorized 36-case exact-hybrid real-promoter formal panel."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs/exact_long_query_hybrid_promoter_panel_v1"
DEFAULT_OUTPUT = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_promoter_panel_v1/formal_panel_v1"
)
PROMOTER_ROOT = Path(
    "/data/wenyujianData/linjieData/promoter_sequences/"
    "human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1"
)
CASE_RUNNER = ROOT / "scripts/run_exact_long_query_hybrid_promoter_case_v1.py"
PAIR_RUNNER = ROOT / "scripts/compare_exact_long_query_hybrid_promoter_pair_v1.py"


class PanelError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PanelError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None and rows and all(None not in row for row in rows), f"malformed TSV: {path}")
    return rows


@dataclass(frozen=True)
class PairWork:
    workload_id: str
    gene_id: str
    gene_symbol: str
    query_length_nt: int
    repeat: int
    estimated_seconds: float

    @property
    def key(self) -> str:
        return f"{self.workload_id}__repeat_{self.repeat}"


@dataclass(frozen=True)
class Slot:
    ordinal: int
    gpu: int
    cpu: str


def load_work() -> list[PairWork]:
    matrix = [
        row for row in read_tsv(DOC_ROOT / "execution_matrix.tsv")
        if row["stage"] == "fresh_full_promoter_panel"
    ]
    require(len(matrix) == 36, "formal execution matrix must contain 36 rows")
    costs = {row["gene_id"]: row for row in read_tsv(DOC_ROOT / "cost_estimate.tsv")}
    grouped: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in matrix:
        grouped.setdefault((row["workload_id"], int(row["repeat"])), []).append(row)
    result: list[PairWork] = []
    for (workload_id, repeat), rows in grouped.items():
        require(len(rows) == 2 and {row["arm"] for row in rows} == {"baseline", "candidate"}, "formal pair is incomplete")
        identities = {(row["gene_id"], row["target_artifact_id"], row["target_path"]) for row in rows}
        require(len(identities) == 1 and rows[0]["target_artifact_id"] == "logical_full_concat", "formal pair identity drift")
        gene_id = rows[0]["gene_id"]
        cost = costs[gene_id]
        result.append(PairWork(
            workload_id=workload_id,
            gene_id=gene_id,
            gene_symbol=cost["gene_symbol"],
            query_length_nt=int(cost["query_length_nt"]),
            repeat=repeat,
            estimated_seconds=(
                float(cost["estimated_baseline_seconds_per_run"])
                + float(cost["estimated_candidate_seconds_per_run"])
            ),
        ))
    require(len(result) == 18, "formal pair count must be 18")
    return sorted(result, key=lambda work: (-work.estimated_seconds, work.gene_id, work.repeat))


def parse_slots(values: Sequence[str] | None) -> list[Slot]:
    raw = list(values or ("0:0", "1:19"))
    result: list[Slot] = []
    seen_gpu: set[int] = set()
    seen_cpu: set[str] = set()
    for ordinal, value in enumerate(raw):
        gpu_text, separator, cpu = value.partition(":")
        require(separator and gpu_text.isdigit() and cpu, f"invalid slot {value!r}; expected GPU:CPU_SET")
        gpu = int(gpu_text)
        require(gpu not in seen_gpu and cpu not in seen_cpu, "slot GPU/CPU resources must be unique")
        seen_gpu.add(gpu)
        seen_cpu.add(cpu)
        result.append(Slot(ordinal=ordinal, gpu=gpu, cpu=cpu))
    require(result, "at least one execution slot is required")
    return result


def balanced_partitions(work: Sequence[PairWork], slots: Sequence[Slot]) -> list[list[PairWork]]:
    require(work and slots, "cannot partition empty work or slots")
    partitions: list[list[PairWork]] = [[] for _ in slots]
    loads = [0.0 for _ in slots]
    for item in sorted(work, key=lambda value: (-value.estimated_seconds, value.gene_id, value.repeat)):
        index = min(range(len(slots)), key=lambda value: (loads[value], value))
        partitions[index].append(item)
        loads[index] += item.estimated_seconds
    return partitions


def case_root(output: Path, work: PairWork, arm: str) -> Path:
    return output / "pairs" / work.workload_id / f"repeat_{work.repeat}" / arm


def pair_root(output: Path, work: PairWork) -> Path:
    return output / "pairs" / work.workload_id / f"repeat_{work.repeat}" / "pair"


def receipt_complete(
    path: Path,
    expected_status: str,
    *,
    workload_id: str,
    repeat: int,
    arm: str | None = None,
) -> bool:
    if not path.is_file():
        return False
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("status") == expected_status, f"existing receipt did not pass: {path}")
    require(value.get("workload_id") == workload_id, f"existing receipt workload mismatch: {path}")
    if arm is not None:
        require(value.get("repeat") == repeat and value.get("arm") == arm, f"existing case receipt identity mismatch: {path}")
    else:
        repeat_root = path.parent.parent
        require(
            Path(str(value.get("baseline_case"))) == (repeat_root / "baseline").resolve()
            and Path(str(value.get("candidate_case"))) == (repeat_root / "candidate").resolve(),
            f"existing pair receipt source binding mismatch: {path}",
        )
    return True


class Orchestrator:
    def __init__(self, output: Path, slots: Sequence[Slot], schedule: Sequence[Sequence[PairWork]]) -> None:
        self.output = output
        self.slots = tuple(slots)
        self.schedule = tuple(tuple(values) for values in schedule)
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.state: dict[str, object] = {
            "schema_version": "exact_long_query_hybrid_promoter_formal_panel_state_v1",
            "status": "running",
            "manager_pid": os.getpid(),
            "started_utc": utc_now(),
            "updated_utc": utc_now(),
            "pairs": {
                work.key: {"status": "pending", "slot": slot.ordinal}
                for slot, values in zip(self.slots, self.schedule)
                for work in values
            },
        }

    def update(self, work: PairWork, **values: object) -> None:
        with self.lock:
            pairs = self.state["pairs"]
            require(isinstance(pairs, dict), "orchestrator state pairs are malformed")
            pair_state = dict(pairs[work.key])
            pair_state.update(values)
            pairs[work.key] = pair_state
            self.state["updated_utc"] = utc_now()
            atomic_json(self.output / "state.json", self.state)

    def event(self, value: Mapping[str, object]) -> None:
        payload = {"utc": utc_now(), **value}
        line = json.dumps(payload, sort_keys=True) + "\n"
        with self.lock:
            with (self.output / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())

    def command(self, command: Sequence[str], log_prefix: Path) -> None:
        log_prefix.parent.mkdir(parents=True, exist_ok=True)
        stdout_path = Path(str(log_prefix) + ".stdout.log")
        stderr_path = Path(str(log_prefix) + ".stderr.log")
        with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
            completed = subprocess.run(command, stdout=stdout, stderr=stderr)
        require(completed.returncode == 0, f"command failed ({completed.returncode}): {' '.join(command)}")

    def run_case(self, work: PairWork, arm: str, slot: Slot) -> None:
        root = case_root(self.output, work, arm)
        receipt = root / "receipt.json"
        if receipt_complete(
            receipt,
            "complete",
            workload_id=work.workload_id,
            repeat=work.repeat,
            arm=arm,
        ):
            return
        require(not root.exists(), f"incomplete existing case root blocks resume: {root}")
        command = [
            sys.executable,
            str(CASE_RUNNER),
            "--workload-id",
            work.workload_id,
            "--arm",
            arm,
            "--repeat",
            str(work.repeat),
            "--gpu",
            str(slot.gpu),
            "--cpu-set",
            slot.cpu,
            "--output",
            str(root),
        ]
        self.command(command, self.output / "scheduler_logs" / f"{work.key}.{arm}")
        require(
            receipt_complete(
                receipt,
                "complete",
                workload_id=work.workload_id,
                repeat=work.repeat,
                arm=arm,
            ),
            f"case runner omitted receipt: {root}",
        )

    def run_pair_gate(self, work: PairWork, slot: Slot) -> None:
        root = pair_root(self.output, work)
        receipt = root / "pair-receipt.json"
        if receipt_complete(
            receipt,
            "pair_gate_pass",
            workload_id=work.workload_id,
            repeat=work.repeat,
        ):
            return
        require(not root.exists(), f"incomplete existing pair root blocks resume: {root}")
        command = [
            "taskset",
            "-c",
            slot.cpu,
            sys.executable,
            str(PAIR_RUNNER),
            "--baseline-root",
            str(case_root(self.output, work, "baseline")),
            "--candidate-root",
            str(case_root(self.output, work, "candidate")),
            "--output-root",
            str(root),
            "--promoter-root",
            str(PROMOTER_ROOT),
        ]
        self.command(command, self.output / "scheduler_logs" / f"{work.key}.pair")
        require(
            receipt_complete(
                receipt,
                "pair_gate_pass",
                workload_id=work.workload_id,
                repeat=work.repeat,
            ),
            f"pair gate omitted receipt: {root}",
        )

    def worker(self, slot: Slot, values: Sequence[PairWork]) -> None:
        for work in values:
            if self.stop.is_set():
                return
            started = time.perf_counter()
            self.update(work, status="running", started_utc=utc_now())
            self.event({"event": "pair_start", "pair": work.key, "slot": slot.ordinal})
            try:
                self.run_case(work, "baseline", slot)
                self.update(work, status="running", stage="candidate")
                self.run_case(work, "candidate", slot)
                self.update(work, status="running", stage="pair_gate")
                self.run_pair_gate(work, slot)
            except Exception as error:
                self.stop.set()
                self.update(work, status="failed", error=str(error), failed_utc=utc_now())
                self.event({"event": "pair_failed", "pair": work.key, "slot": slot.ordinal, "error": str(error)})
                raise
            self.update(
                work,
                status="complete",
                stage="complete",
                completed_utc=utc_now(),
                wall_seconds=time.perf_counter() - started,
            )
            self.event({"event": "pair_complete", "pair": work.key, "slot": slot.ordinal})

    def run(self) -> None:
        atomic_json(self.output / "state.json", self.state)
        errors: list[BaseException] = []
        threads = [
            threading.Thread(target=self._capture_worker, args=(slot, values, errors), name=f"formal-slot-{slot.ordinal}")
            for slot, values in zip(self.slots, self.schedule)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        with self.lock:
            self.state["status"] = "failed" if errors else "complete"
            self.state["completed_utc"] = utc_now()
            self.state["updated_utc"] = utc_now()
            atomic_json(self.output / "state.json", self.state)
        if errors:
            raise PanelError(f"formal panel stopped after failure: {errors[0]}")
        self.write_summary()

    def _capture_worker(self, slot: Slot, values: Sequence[PairWork], errors: list[BaseException]) -> None:
        try:
            self.worker(slot, values)
        except BaseException as error:
            with self.lock:
                errors.append(error)

    def write_summary(self) -> None:
        rows: list[dict[str, object]] = []
        by_gene: dict[str, list[dict[str, object]]] = {}
        for values in self.schedule:
            for work in values:
                baseline = json.loads((case_root(self.output, work, "baseline") / "receipt.json").read_text())
                candidate = json.loads((case_root(self.output, work, "candidate") / "receipt.json").read_text())
                pair = json.loads((pair_root(self.output, work) / "pair-receipt.json").read_text())
                require(pair["status"] == "pair_gate_pass" and all(pair["gates"].values()), "summary found failed pair")
                row = {
                    "workload_id": work.workload_id,
                    "gene_id": work.gene_id,
                    "repeat": work.repeat,
                    "baseline_wall_seconds": baseline["wall_seconds"],
                    "candidate_wall_seconds": candidate["wall_seconds"],
                    "diagnostic_speedup": float(baseline["wall_seconds"]) / float(candidate["wall_seconds"]),
                    "raw_tfosorted_sha256": pair["raw_tfosorted"]["sha256"],
                    "pair_gate_pass": True,
                }
                rows.append(row)
                by_gene.setdefault(work.gene_id, []).append(row)
        determinism = {
            gene_id: len({str(row["raw_tfosorted_sha256"]) for row in values}) == 1
            for gene_id, values in by_gene.items()
        }
        require(all(determinism.values()), "three-repeat output determinism failed")
        summary = {
            "schema_version": "exact_long_query_hybrid_promoter_formal_panel_summary_v1",
            "status": "complete",
            "pair_count": len(rows),
            "case_count": 2 * len(rows),
            "all_pair_gates_pass": True,
            "three_repeat_output_determinism": determinism,
            "diagnostic_median_speedup": statistics.median(float(row["diagnostic_speedup"]) for row in rows),
            "performance_formal": False,
            "rows": sorted(rows, key=lambda row: (str(row["gene_id"]), int(row["repeat"]))),
            "production_authorized": False,
        }
        atomic_json(self.output / "summary.json", summary)


def schedule_rows(partitions: Sequence[Sequence[PairWork]], slots: Sequence[Slot]) -> Iterable[dict[str, object]]:
    for slot, values in zip(slots, partitions):
        for ordinal, work in enumerate(values, 1):
            yield {
                "slot": slot.ordinal,
                "gpu": slot.gpu,
                "cpu_set": slot.cpu,
                "slot_order": ordinal,
                "workload_id": work.workload_id,
                "gene_id": work.gene_id,
                "gene_symbol": work.gene_symbol,
                "query_length_nt": work.query_length_nt,
                "repeat": work.repeat,
                "estimated_pair_seconds": f"{work.estimated_seconds:.3f}",
            }


def write_schedule(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = tuple(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument("--slot", action="append", help="GPU:CPU_SET; repeat for each concurrent slot")
    result.add_argument("--resume", action="store_true")
    result.add_argument("--dry-run", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    addendum = json.loads((DOC_ROOT / "formal_execution_addendum.json").read_text(encoding="utf-8"))
    require(addendum.get("formal_panel_authorized") is True, "formal execution is not authorized")
    work = load_work()
    slots = parse_slots(args.slot)
    partitions = balanced_partitions(work, slots)
    rows = list(schedule_rows(partitions, slots))
    if args.dry_run:
        print(json.dumps({
            "pair_count": len(work),
            "slots": [slot.__dict__ for slot in slots],
            "estimated_slot_seconds": [sum(item.estimated_seconds for item in values) for values in partitions],
            "schedule": rows,
        }, indent=2, sort_keys=True))
        return 0
    if args.output.exists():
        require(args.resume and args.output.is_dir(), f"output exists; use --resume: {args.output}")
        existing_schedule = read_tsv(args.output / "schedule.tsv")
        expected_schedule = [
            {key: str(value) for key, value in row.items()}
            for row in rows
        ]
        require(existing_schedule == expected_schedule, "resume schedule/resource identity mismatch")
    else:
        require(not args.resume, f"resume output does not exist: {args.output}")
        args.output.mkdir(parents=True)
        write_schedule(args.output / "schedule.tsv", rows)
        atomic_json(args.output / "launch.json", {
            "schema_version": "exact_long_query_hybrid_promoter_formal_panel_launch_v1",
            "launched_utc": utc_now(),
            "manager_pid": os.getpid(),
            "command": sys.argv,
            "slots": [slot.__dict__ for slot in slots],
            "pair_count": len(work),
            "case_count": 2 * len(work),
            "formal_execution_addendum": str((DOC_ROOT / "formal_execution_addendum.json").resolve()),
        })
    orchestrator = Orchestrator(args.output, slots, partitions)
    orchestrator.run()
    print(json.dumps(json.loads((args.output / "summary.json").read_text()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PanelError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
