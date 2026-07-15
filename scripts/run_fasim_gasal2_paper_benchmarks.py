#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RUNTIME_EPOCH = 0
REQUIRED_COLUMNS = (
    "workload_id",
    "claim_id",
    "family",
    "role",
    "query_id",
    "query_path",
    "query_sha256",
    "query_start_nt",
    "query_end_nt",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_path",
    "target_sha256",
    "target_region",
    "rule",
    "baseline_mode",
    "candidate_mode",
    "output_contract",
    "required_pairs",
    "requires_gpu_count",
    "max_wall_seconds",
    "preset_id",
    "preregistered",
    "adapter_id",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(payload: dict[str, object]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def resolve_path(raw: str, manifest: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    root_candidate = ROOT / path
    if root_candidate.exists():
        return root_candidate
    return manifest.parent / path


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit("workload manifest has no header")
        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise SystemExit("workload manifest missing fields: " + ",".join(missing))
        rows = list(reader)
    ids = [row["workload_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("workload manifest contains duplicate workload_id")
    if ids != sorted(ids):
        raise SystemExit("workload manifest must be stable-sorted by workload_id")
    digest_cache: dict[Path, str] = {}
    for row in rows:
        for key in REQUIRED_COLUMNS:
            if not row.get(key):
                raise SystemExit(f"{row.get('workload_id', 'unknown')}: empty manifest field {key}")
        if row["preregistered"] != "1":
            raise SystemExit(f"{row['workload_id']}: workload is not preregistered")
        try:
            start = int(row["query_start_nt"])
            end = int(row["query_end_nt"])
            length = int(row["query_length_nt"])
            required_pairs = int(row["required_pairs"])
            int(row["requires_gpu_count"])
            int(row["max_wall_seconds"])
            int(row["rule"])
        except ValueError as exc:
            raise SystemExit(f"{row['workload_id']}: invalid numeric manifest field") from exc
        if start < 0 or end <= start or end - start != length or required_pairs < 0:
            raise SystemExit(f"{row['workload_id']}: invalid query interval or repeat count")
        for path_key, digest_key in (
            ("query_path", "query_sha256"),
            ("target_path", "target_sha256"),
        ):
            artifact = resolve_path(row[path_key], path)
            if not artifact.is_file():
                raise SystemExit(f"{row['workload_id']}: missing input {artifact}")
            digest = digest_cache.setdefault(artifact, sha256(artifact))
            if digest != row[digest_key]:
                raise SystemExit(f"{row['workload_id']}: {path_key} digest mismatch")
    return rows


def pair_order(seed: int, workload_id: str, pair_id: int) -> tuple[str, list[str]]:
    parity = int(hashlib.sha256(f"{seed}:{workload_id}".encode()).hexdigest()[:8], 16) % 2
    ab = (pair_id + parity) % 2 == 0
    return ("AB", ["baseline", "candidate"]) if ab else ("BA", ["candidate", "baseline"])


def run_id(workload_id: str, pair_id: int, mode: str, warmup: bool = False) -> str:
    if warmup:
        return f"{workload_id}__warmup__{mode}__{RUNTIME_EPOCH}"
    return f"{workload_id}__pair{pair_id:02d}__{mode}__{RUNTIME_EPOCH}"


def config_payload(
    row: dict[str, str],
    manifest: Path,
    binary: Path,
    binary_digest: str,
    pair_id: int,
    mode: str,
    seed: int,
    warmup: bool = False,
) -> dict[str, object]:
    order_name, _ = pair_order(seed, row["workload_id"], pair_id)
    payload: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id(row["workload_id"], pair_id, mode, warmup),
        "workload_id": row["workload_id"],
        "pair_id": pair_id,
        "mode": mode,
        "warmup": warmup,
        "warmup_run_id": run_id(row["workload_id"], 0, mode, True),
        "pair_order": order_name,
        "seed": seed,
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "manifest": str(manifest),
        "manifest_row": row,
        "binary": str(binary),
        "binary_sha256": binary_digest,
    }
    payload["config_digest_sha256"] = canonical_digest(payload)
    return payload


def build_plan(
    rows: list[dict[str, str]], manifest: Path, binary: Path, seed: int
) -> dict[str, object]:
    binary_digest = sha256(binary)
    runs: list[dict[str, object]] = []
    warmups: list[dict[str, object]] = []
    for row in rows:
        if row["adapter_id"] == "preflight_guard" or row["role"] == "negative_control":
            payload = config_payload(row, manifest, binary, binary_digest, 0, "preflight", seed)
            runs.append(payload)
            continue
        for mode in ("baseline", "candidate"):
            warmups.append(
                {
                    "workload_id": row["workload_id"],
                    "mode": mode,
                    "run_id": f"{row['workload_id']}__warmup__{mode}__{RUNTIME_EPOCH}",
                }
            )
        for pair_id_value in range(1, int(row["required_pairs"]) + 1):
            _, modes = pair_order(seed, row["workload_id"], pair_id_value)
            for order_index, mode in enumerate(modes):
                payload = config_payload(
                    row,
                    manifest,
                    binary,
                    binary_digest,
                    pair_id_value,
                    mode,
                    seed,
                )
                payload["order_index"] = order_index
                runs.append(payload)
    return {
        "schema_version": 1,
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "seed": seed,
        "workload_count": len(rows),
        "run_count": len(runs),
        "warmups": warmups,
        "runs": runs,
    }


def visible_gpu_count() -> int:
    if os.environ.get("FASIM_PAPER_HARNESS_TEST_MODE") == "1":
        try:
            return int(os.environ.get("FASIM_PAPER_TEST_GPU_COUNT", "0"))
        except ValueError:
            return 0
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None:
        values = [value.strip() for value in visible.split(",") if value.strip() not in ("", "-1")]
        return len(values)
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if line.startswith("GPU "))


def read_single_fasta(path: Path) -> tuple[str, str]:
    header = ""
    sequence: list[str] = []
    headers = 0
    with path.open(encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                headers += 1
                if not header:
                    header = line[1:].split()[0]
                continue
            sequence.append(line.upper())
    if headers != 1 or not sequence:
        raise SystemExit(f"expected one-record FASTA: {path}")
    return header, "".join(sequence)


def write_fasta(path: Path, header: str, sequence: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f">{header}\n")
        for index in range(0, len(sequence), 80):
            handle.write(sequence[index : index + 80] + "\n")


def materialize_inputs(row: dict[str, str], manifest: Path, run_dir: Path) -> tuple[Path, Path]:
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    query_source = resolve_path(row["query_path"], manifest)
    query_header, query_sequence = read_single_fasta(query_source)
    start = int(row["query_start_nt"])
    end = int(row["query_end_nt"])
    if end > len(query_sequence):
        raise SystemExit(f"{row['workload_id']}: query interval exceeds source")
    query = inputs / "query.fa"
    write_fasta(query, f"{query_header}_{start}_{end}", query_sequence[start:end])

    target_source = resolve_path(row["target_path"], manifest)
    region = row["target_region"]
    if region == "full":
        target = target_source
    elif region.startswith("slice:"):
        bounds = region.removeprefix("slice:").split("-", 1)
        if len(bounds) != 2:
            raise SystemExit(f"{row['workload_id']}: malformed target region")
        target_start, target_end = (int(value) for value in bounds)
        target_header, target_sequence = read_single_fasta(target_source)
        if target_start < 0 or target_end <= target_start or target_end > len(target_sequence):
            raise SystemExit(f"{row['workload_id']}: target region out of bounds")
        target = inputs / "target.fa"
        write_fasta(target, f"{target_header}|slice|{target_start}-{target_end}", target_sequence[target_start:target_end])
    else:
        raise SystemExit(f"{row['workload_id']}: unsupported target region {region!r}")
    return query, target


def base_gasal2_env() -> dict[str, str]:
    return {
        "FASIM_VERBOSE": "0",
        "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
        "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
        "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
        "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
        "FASIM_ALIGN_GASAL2_STREAMS": "3",
        "FASIM_ALIGN_GASAL2_BATCH": "20000",
    }


def env_command(environment: dict[str, str], command: list[str]) -> list[str]:
    return ["env", *[f"{key}={value}" for key, value in sorted(environment.items())], *command]


def adapter_command(
    row: dict[str, str], mode: str, binary: Path, query: Path, target: Path, run_dir: Path
) -> list[str]:
    adapter = row["adapter_id"]
    output = run_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    if adapter == "synthetic_test":
        if os.environ.get("FASIM_PAPER_HARNESS_TEST_MODE") != "1":
            raise SystemExit("synthetic_test adapter is test-only")
        try:
            sleep_seconds = float(os.environ.get("FASIM_PAPER_TEST_SLEEP_SECONDS", "0"))
        except ValueError as exc:
            raise SystemExit("invalid FASIM_PAPER_TEST_SLEEP_SECONDS") from exc
        if sleep_seconds < 0:
            raise SystemExit("FASIM_PAPER_TEST_SLEEP_SECONDS must be nonnegative")
        return [
            sys.executable,
            "-c",
            (
                "import time; from pathlib import Path; "
                f"time.sleep({sleep_seconds!r}); "
                "Path('output/result.txt').write_text('ok\\n'); print('synthetic=1')"
            ),
        ]
    if adapter == "formal_topk_sharded":
        command = [
            sys.executable,
            str(ROOT / "scripts/fasim_sharded_runner.py"),
            "--fasim-bin",
            str(binary),
            "--target",
            str(target),
            "--rna",
            str(query),
            "--rule",
            row["rule"],
            "--work-dir",
            str(output),
            "--output-mode",
            "lite",
            "--topk-summary",
            "5",
            "--topk-summary-only",
            "--workers",
            row["requires_gpu_count"],
            "--gpu-ids",
            ",".join(str(index) for index in range(int(row["requires_gpu_count"]))),
            "--force",
        ]
        if mode == "candidate":
            command.append("--gasal2-top5-column-pruned-scoreinfo")
        return command
    if adapter == "direct_tfo_contract":
        environment = {"FASIM_OUTPUT_MODE": "tfosorted", "FASIM_VERBOSE": "0"}
        if mode == "candidate":
            environment.update(base_gasal2_env())
        return env_command(
            environment,
            [str(binary), "-f1", str(target), "-f2", str(query), "-r", row["rule"], "-O", str(output)],
        )
    if adapter == "direct_two_slot":
        environment = base_gasal2_env()
        environment["FASIM_OUTPUT_MODE"] = "lite"
        if mode == "baseline":
            environment["FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER"] = "1"
        else:
            environment["FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP"] = "1"
        return env_command(
            environment,
            [str(binary), "-f1", str(target), "-f2", str(query), "-r", row["rule"], "-O", str(output)],
        )
    if adapter == "segmented_max8":
        environment = {
            "BIN": str(binary),
            "WORK": str(output),
            "TARGET": str(target),
            "RNA": str(query),
            "KCNQ1OT1_FASTA": str(query),
            "SEGMENT_LEN": "2048",
            "SEGMENT_OVERLAP": "512",
            "GRID_SHIFTS": "0 256",
            "MAX_SEGMENTS": "8",
            "RESUME": "1",
            "EXACT_SCOREINFO_PRUNED": "1" if mode == "candidate" else "0",
        }
        return env_command(
            environment,
            ["bash", str(ROOT / "scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh")],
        )
    if adapter in {"historical_descriptive", "archive_pair", "exact_column_pair"}:
        raise SystemExit(f"adapter {adapter} is preregistered for a phase-specific paired driver")
    raise SystemExit(f"unknown paper benchmark adapter: {adapter}")


GPU_SAMPLE_HEADER = (
    "timestamp,measurement_status,gpu_index,memory_used_mib,memory_total_mib,"
    "utilization_gpu_percent,temperature_gpu_c,power_draw_w,clocks_sm_mhz\n"
)


def gpu_sample_rows() -> list[str]:
    timestamp = datetime.now(timezone.utc).isoformat()
    if shutil.which("nvidia-smi") is None:
        return [f"{timestamp},unavailable,NA,NA,NA,NA,NA,NA,NA"]
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                (
                    "--query-gpu=index,memory.used,memory.total,utilization.gpu,"
                    "temperature.gpu,power.draw,clocks.current.sm"
                ),
                "--format=csv,noheader,nounits",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [f"{timestamp},unavailable,NA,NA,NA,NA,NA,NA,NA"]
    if result.returncode != 0 or not result.stdout.strip():
        return [f"{timestamp},unavailable,NA,NA,NA,NA,NA,NA,NA"]
    return [
        f"{timestamp},available," + ",".join(part.strip() for part in line.split(","))
        for line in result.stdout.splitlines()
    ]


def sample_gpu(path: Path) -> None:
    path.write_text(GPU_SAMPLE_HEADER + "\n".join(gpu_sample_rows()) + "\n", encoding="utf-8")


class GpuSampler:
    def __init__(self, path: Path, interval_seconds: float = 0.25) -> None:
        self.path = path
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="paper-gpu-sampler", daemon=True)

    def _run(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            handle.write(GPU_SAMPLE_HEADER)
            while True:
                for row in gpu_sample_rows():
                    handle.write(row + "\n")
                handle.flush()
                if self.stop_event.wait(self.interval_seconds):
                    break

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=15)
        if self.thread.is_alive():
            raise SystemExit("GPU sampler did not stop")


def execute_run(
    row: dict[str, str],
    manifest: Path,
    binary: Path,
    pair_id_value: int,
    mode: str,
    seed: int,
    artifact_root: Path,
    resume: bool,
    warmup: bool = False,
) -> dict[str, object]:
    required_gpus = int(row["requires_gpu_count"])
    available_gpus = visible_gpu_count()
    if required_gpus > available_gpus:
        raise SystemExit(
            f"blocked_reason=insufficient_visible_gpus required={required_gpus} available={available_gpus}"
        )
    binary_digest = sha256(binary)
    config = config_payload(
        row,
        manifest,
        binary,
        binary_digest,
        pair_id_value,
        mode,
        seed,
        warmup,
    )
    destination = artifact_root / str(config["run_id"])
    receipt_path = destination / "run-complete.json"
    if destination.exists():
        if not receipt_path.is_file():
            raise SystemExit(f"incomplete receipt for run ID: {config['run_id']}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("config_digest_sha256") != config["config_digest_sha256"]:
            raise SystemExit(f"config digest mismatch for run ID: {config['run_id']}")
        if not resume:
            raise SystemExit(f"duplicate run ID: {config['run_id']}")
        return {"status": "reused", "run_id": config["run_id"], "run_dir": str(destination)}

    if (
        not warmup
        and mode in {"baseline", "candidate"}
        and os.environ.get("FASIM_PAPER_HARNESS_TEST_MODE") != "1"
    ):
        warmup_receipt = artifact_root / str(config["warmup_run_id"]) / "run-complete.json"
        if not warmup_receipt.is_file():
            raise SystemExit(f"missing warmup receipt: {warmup_receipt}")

    artifact_root.mkdir(parents=True, exist_ok=True)
    temporary = artifact_root / f".{config['run_id']}.partial.{os.getpid()}"
    if temporary.exists():
        raise SystemExit(f"temporary run path already exists: {temporary}")
    temporary.mkdir()
    atomic_json(temporary / "run-config.json", config)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/capture_fasim_gasal2_paper_environment.py"),
            "--output",
            str(temporary / "environment.json"),
        ],
        check=True,
    )
    query, target = materialize_inputs(row, manifest, temporary)

    if mode == "preflight":
        correctness = {
            "schema_version": 1,
            "status": "guarded" if int(row["query_length_nt"]) > 2812 else "supported",
            "supported": int(row["query_length_nt"]) <= 2812,
            "reason": "query_length_contract" if int(row["query_length_nt"]) > 2812 else "within_contract",
        }
        atomic_json(temporary / "correctness.json", correctness)
        (temporary / "stdout.log").write_text("preflight only\n", encoding="utf-8")
        (temporary / "stderr.log").write_text("", encoding="utf-8")
        (temporary / "time.txt").write_text("", encoding="utf-8")
        sample_gpu(temporary / "gpu-memory.csv")
        execution = {"returncode": 0, "wall_seconds": 0.0, "timed": False, "command": ["preflight_guard"]}
    else:
        command = adapter_command(row, mode, binary, query, target, temporary)
        time_command = command
        timed = Path("/usr/bin/time").is_file()
        if timed:
            time_command = ["/usr/bin/time", "-v", "-o", str(temporary / "time.txt"), *command]
        else:
            (temporary / "time.txt").write_text("", encoding="utf-8")
        started = time.perf_counter()
        timed_out = False
        sampler = GpuSampler(temporary / "gpu-memory.csv")
        sampler.start()
        with (temporary / "stdout.log").open("w", encoding="utf-8") as stdout, (
            temporary / "stderr.log"
        ).open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(
                time_command,
                cwd=temporary,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                returncode = process.wait(timeout=int(row["max_wall_seconds"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                returncode = 124
            finally:
                sampler.stop()
        wall = time.perf_counter() - started
        execution = {
            "returncode": returncode,
            "wall_seconds": wall,
            "timed": timed,
            "timed_out": timed_out,
            "command": command,
        }
        if timed_out:
            correctness = {"schema_version": 1, "status": "technical_failure", "reason": "timeout"}
        elif returncode != 0:
            correctness = {
                "schema_version": 1,
                "status": "technical_failure",
                "reason": "nonzero_exit",
            }
        else:
            correctness = {
                "schema_version": 1,
                "status": (
                    "synthetic_clean"
                    if row["adapter_id"] == "synthetic_test"
                    else "pending_pair_comparison"
                ),
            }
        atomic_json(temporary / "correctness.json", correctness)
    atomic_json(temporary / "execution.json", execution)
    if execution["returncode"] != 0:
        failed = artifact_root / f"{config['run_id']}.failed.{time.time_ns()}"
        os.replace(temporary, failed)
        if execution.get("timed_out"):
            raise SystemExit(f"paper benchmark command timed out: {failed}")
        raise SystemExit(f"paper benchmark command failed: {failed}")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/collect_fasim_gasal2_paper_run.py"),
            "--run-dir",
            str(temporary),
            "--output",
            str(temporary / "summary.json"),
        ],
        check=True,
    )
    receipt = {
        "schema_version": 1,
        "status": "complete",
        "run_id": config["run_id"],
        "config_digest_sha256": config["config_digest_sha256"],
        "summary_sha256": sha256(temporary / "summary.json"),
        "stdout_sha256": sha256(temporary / "stdout.log"),
        "stderr_sha256": sha256(temporary / "stderr.log"),
    }
    atomic_json(temporary / "run-complete.json", receipt)
    os.replace(temporary, destination)
    return {"status": "completed", "run_id": config["run_id"], "run_dir": str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "paper/workload_manifest.tsv")
    parser.add_argument("--binary", type=Path, default=ROOT / ".tmp/fasim_longtarget_gasal2_direct")
    parser.add_argument("--artifact-root", type=Path, default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze")
    parser.add_argument("--workload-id")
    parser.add_argument("--pair-id", type=int)
    parser.add_argument("--mode", choices=("baseline", "candidate", "preflight"))
    parser.add_argument("--seed", type=int, default=20260715)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--warmup", action="store_true")
    args = parser.parse_args()

    if not args.binary.is_file():
        raise SystemExit(f"missing paper benchmark binary: {args.binary}")
    rows = load_manifest(args.manifest)
    if args.workload_id:
        rows = [row for row in rows if row["workload_id"] == args.workload_id]
        if not rows:
            raise SystemExit(f"unknown workload ID: {args.workload_id}")
    plan = build_plan(rows, args.manifest, args.binary, args.seed)
    if args.dry_run:
        json.dump(plan, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(rows) != 1 or args.mode is None:
        raise SystemExit("execution requires one --workload-id and --mode")
    row = rows[0]
    if args.warmup:
        if args.mode == "preflight":
            raise SystemExit("preflight guard does not use warmup")
        pair_id_value = 0
    elif args.mode == "preflight":
        if row["adapter_id"] != "preflight_guard" and row["role"] != "negative_control":
            raise SystemExit("preflight mode is only valid for a guard workload")
        pair_id_value = 0
    else:
        if args.pair_id is None:
            raise SystemExit("paired execution requires --pair-id")
        pair_id_value = args.pair_id
        if pair_id_value < 1 or pair_id_value > int(row["required_pairs"]):
            raise SystemExit("pair ID is outside the preregistered range")
    result = execute_run(
        row,
        args.manifest,
        args.binary,
        pair_id_value,
        args.mode,
        args.seed,
        args.artifact_root,
        args.resume,
        args.warmup,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
