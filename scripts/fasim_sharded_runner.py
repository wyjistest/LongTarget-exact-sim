#!/usr/bin/env python3
import argparse
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


LITE_HEADER = (
    "Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\t"
    "StartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\t"
    "MeanStability"
)

TFOSORTED_HEADER = (
    "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\tStrand\t"
    "Rule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\tTFO sequence\tTTS sequence"
)


@dataclasses.dataclass(frozen=True)
class FastaRecord:
    header: str
    sequence: str


@dataclasses.dataclass(frozen=True)
class Shard:
    shard_id: str
    target_name: str
    target_start: int
    target_end: int
    shard_fasta_path: Path
    estimated_length: int
    estimated_windows: None
    estimated_cells: None


@dataclasses.dataclass(frozen=True)
class RunResult:
    label: str
    cmd: list[str]
    env_overrides: dict[str, str]
    wall_seconds: float
    stdout_path: Path
    stderr_path: Path
    output_dir: Path
    output_path: Path


@dataclasses.dataclass(frozen=True)
class CanonicalOutput:
    header: str
    rows: list[str]
    raw_records: int
    digest: str
    content: str


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _read_fasta(path: Path) -> list[FastaRecord]:
    records: list[FastaRecord] = []
    header: str | None = None
    seq_parts: list[str] = []

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append(FastaRecord(header, "".join(seq_parts)))
                header = line
                seq_parts = []
            else:
                seq_parts.append(line)

    if header is not None:
        records.append(FastaRecord(header, "".join(seq_parts)))

    return [r for r in records if r.sequence]


def _parse_target_header(record: FastaRecord) -> tuple[str, int, int]:
    if not record.header.startswith(">"):
        return record.header.strip() or "unknown", 1, len(record.sequence)

    body = record.header[1:].strip()
    parts = body.split("|")
    target_name = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else body
    start = 1
    end = len(record.sequence)

    if len(parts) >= 3:
        coord_text = parts[2].strip()
        match = re.match(r"^(-?\d+)(?:-(-?\d+))?", coord_text)
        if match:
            start = int(match.group(1))
            if match.group(2) is not None:
                end = int(match.group(2))
            else:
                end = start + len(record.sequence) - 1
        else:
            end = start + len(record.sequence) - 1

    return target_name, start, end


def _sanitize_for_path(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "target"


def _wrap_sequence(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[i : i + width] for i in range(0, len(sequence), width))


def _write_shard_fastas(records: list[FastaRecord], shard_dir: Path) -> list[Shard]:
    shard_dir.mkdir(parents=True, exist_ok=True)
    shards: list[Shard] = []

    for idx, record in enumerate(records):
        target_name, start, end = _parse_target_header(record)
        shard_id = f"shard_{idx:04d}_{_sanitize_for_path(target_name)}"
        shard_path = shard_dir / f"{shard_id}.fa"
        shard_path.write_text(
            f"{record.header}\n{_wrap_sequence(record.sequence)}\n",
            encoding="utf-8",
        )
        shards.append(
            Shard(
                shard_id=shard_id,
                target_name=target_name,
                target_start=start,
                target_end=end,
                shard_fasta_path=shard_path,
                estimated_length=len(record.sequence),
                estimated_windows=None,
                estimated_cells=None,
            )
        )

    return shards


def _parse_env_overrides(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--env must be KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--env has empty key: {item}")
        env[key] = value
    return env


def _run_fasim(
    *,
    label: str,
    fasim_bin: Path,
    target: Path,
    rna: Path,
    rule: str,
    output_mode: str,
    output_dir: Path,
    log_dir: Path,
    env_overrides: dict[str, str],
    fasim_args: list[str],
) -> RunResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(fasim_bin),
        "-f1",
        str(target),
        "-f2",
        str(rna),
        "-r",
        str(rule),
        "-O",
        str(output_dir),
    ]
    cmd.extend(fasim_args)

    env = os.environ.copy()
    env.update(env_overrides)
    env["FASIM_OUTPUT_MODE"] = output_mode
    env.setdefault("FASIM_VERBOSE", "0")

    stdout_path = log_dir / f"{label}.stdout.log"
    stderr_path = log_dir / f"{label}.stderr.log"

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    t1 = time.perf_counter()

    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit {proc.returncode}; see {stderr_path}"
        )

    output_path = _find_output_file(output_dir, output_mode)
    return RunResult(
        label=label,
        cmd=cmd,
        env_overrides=env_overrides,
        wall_seconds=t1 - t0,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_dir=output_dir,
        output_path=output_path,
    )


def _find_output_file(output_dir: Path, output_mode: str) -> Path:
    if output_mode == "lite":
        files = sorted(output_dir.glob("*-TFOsorted.lite"))
    else:
        files = [
            p
            for p in sorted(output_dir.glob("*-TFOsorted"))
            if not p.name.endswith(".lite")
        ]

    if len(files) != 1:
        names = ", ".join(p.name for p in files) or "<none>"
        raise RuntimeError(
            f"expected exactly one {output_mode} output in {output_dir}, found: {names}"
        )
    return files[0]


def _default_header(output_mode: str) -> str:
    return LITE_HEADER if output_mode == "lite" else TFOSORTED_HEADER


def _convert_sort_value(value: str) -> tuple[int, object]:
    if re.match(r"^-?\d+$", value):
        return (0, int(value))
    try:
        return (1, float(value))
    except ValueError:
        return (2, value)


def _row_sort_key(header: str, row: str) -> tuple:
    cols = header.split("\t")
    idx = {name: i for i, name in enumerate(cols)}
    parts = row.split("\t")
    preferred = [
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "Strand",
        "Rule",
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Score",
        "Nt(bp)",
        "MeanIdentity(%)",
        "MeanStability",
        "Class",
        "MidPoint",
        "Center",
        "TFO sequence",
        "TTS sequence",
    ]
    key: list[object] = []
    for name in preferred:
        pos = idx.get(name)
        if pos is not None and pos < len(parts):
            key.append((name, _convert_sort_value(parts[pos])))
    key.append(("row", row))
    return tuple(key)


def _canonical_from_rows(header: str, rows: list[str]) -> CanonicalOutput:
    unique_rows = sorted(set(rows), key=lambda row: _row_sort_key(header, row))
    content = header + "\n"
    if unique_rows:
        content += "\n".join(unique_rows) + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return CanonicalOutput(
        header=header,
        rows=unique_rows,
        raw_records=len(rows),
        digest=digest,
        content=content,
    )


def _canonicalize_file(path: Path, output_mode: str) -> CanonicalOutput:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return _canonical_from_rows(_default_header(output_mode), [])
    header = lines[0].rstrip("\r\n")
    rows = [line.rstrip("\r\n") for line in lines[1:] if line.strip()]
    return _canonical_from_rows(header, rows)


def _merge_outputs(paths: list[Path], output_mode: str, output_path: Path) -> CanonicalOutput:
    header: str | None = None
    rows: list[str] = []

    for path in paths:
        canonical = _canonicalize_file(path, output_mode)
        if header is None:
            header = canonical.header
        elif canonical.header != header:
            raise RuntimeError(f"output header mismatch in {path}")
        rows.extend(canonical.rows)

    merged = _canonical_from_rows(header or _default_header(output_mode), rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(merged.content, encoding="utf-8")
    return merged


def _shard_to_json(shard: Shard) -> dict[str, object]:
    return {
        "shard_id": shard.shard_id,
        "target_name": shard.target_name,
        "target_start": shard.target_start,
        "target_end": shard.target_end,
        "shard_fasta_path": str(shard.shard_fasta_path),
        "estimated_length": shard.estimated_length,
        "estimated_windows": shard.estimated_windows,
        "estimated_cells": shard.estimated_cells,
    }


def _run_to_json(run: RunResult) -> dict[str, object]:
    return {
        "label": run.label,
        "cmd": run.cmd,
        "env_overrides": run.env_overrides,
        "wall_seconds": run.wall_seconds,
        "stdout_path": str(run.stdout_path),
        "stderr_path": str(run.stderr_path),
        "output_dir": str(run.output_dir),
        "output_path": str(run.output_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Fasim once per target FASTA contig and deterministically merge "
            "record output. PR A intentionally supports contig-level shards only."
        )
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--rna", required=True, type=Path)
    parser.add_argument("--rule", default="0")
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
        help="Fasim record schema to merge deterministically.",
    )
    parser.add_argument(
        "--validate-single",
        action="store_true",
        help="Also run the original multi-contig target and compare canonical digest.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment override passed to every Fasim worker. Repeatable.",
    )
    parser.add_argument(
        "--fasim-arg",
        action="append",
        default=[],
        help="Extra single argument appended to each Fasim invocation. Repeatable.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    fasim_bin = args.fasim_bin.resolve()
    target = args.target.resolve()
    rna = args.rna.resolve()
    work_dir = args.work_dir.resolve()

    if not fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {fasim_bin}")
    if not target.exists():
        raise RuntimeError(f"missing target FASTA: {target}")
    if not rna.exists():
        raise RuntimeError(f"missing RNA FASTA: {rna}")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "shards").mkdir(parents=True)
    (work_dir / "logs").mkdir(parents=True)

    records = _read_fasta(target)
    if not records:
        raise RuntimeError(f"no FASTA records found in {target}")

    env_overrides = _parse_env_overrides(args.env)
    shards = _write_shard_fastas(records, work_dir / "shards")
    shard_plan_path = work_dir / "shard_plan.json"
    shard_plan_path.write_text(
        json.dumps([_shard_to_json(shard) for shard in shards], indent=2) + "\n",
        encoding="utf-8",
    )

    per_shard: list[dict[str, object]] = []
    shard_output_paths: list[Path] = []
    sharded_raw_records = 0
    sharded_unique_records = 0

    for shard in shards:
        output_dir = work_dir / "shard_outputs" / shard.shard_id
        run = _run_fasim(
            label=shard.shard_id,
            fasim_bin=fasim_bin,
            target=shard.shard_fasta_path,
            rna=rna,
            rule=str(args.rule),
            output_mode=args.output_mode,
            output_dir=output_dir,
            log_dir=work_dir / "logs",
            env_overrides=env_overrides,
            fasim_args=args.fasim_arg,
        )
        canonical = _canonicalize_file(run.output_path, args.output_mode)
        sharded_raw_records += canonical.raw_records
        sharded_unique_records += len(canonical.rows)
        shard_output_paths.append(run.output_path)
        per_shard.append(
            {
                **_shard_to_json(shard),
                "records": len(canonical.rows),
                "raw_records": canonical.raw_records,
                "digest": canonical.digest,
                "run": _run_to_json(run),
            }
        )

    merged_name = "merged-TFOsorted.lite" if args.output_mode == "lite" else "merged-TFOsorted"
    merged_output_path = work_dir / "merged" / merged_name
    merged = _merge_outputs(shard_output_paths, args.output_mode, merged_output_path)

    single_digest = None
    single_records = None
    single_raw_records = None
    single_run_json = None
    digest_match = None
    single_output_path = None
    if args.validate_single:
        single_run = _run_fasim(
            label="single",
            fasim_bin=fasim_bin,
            target=target,
            rna=rna,
            rule=str(args.rule),
            output_mode=args.output_mode,
            output_dir=work_dir / "single_output",
            log_dir=work_dir / "logs",
            env_overrides=env_overrides,
            fasim_args=args.fasim_arg,
        )
        single = _canonicalize_file(single_run.output_path, args.output_mode)
        single_digest = single.digest
        single_records = len(single.rows)
        single_raw_records = single.raw_records
        single_run_json = _run_to_json(single_run)
        single_output_path = str(single_run.output_path)
        digest_match = single.digest == merged.digest

    report = {
        "schema_version": 1,
        "mode": "contig_shards",
        "target": str(target),
        "rna": str(rna),
        "rule": str(args.rule),
        "output_mode": args.output_mode,
        "env_overrides": env_overrides,
        "shard_plan": str(shard_plan_path),
        "shard_count": len(shards),
        "shard_ids": [shard.shard_id for shard in shards],
        "per_shard": per_shard,
        "sharded_records": sharded_raw_records,
        "sharded_unique_records": sharded_unique_records,
        "merged_records": len(merged.rows),
        "merged_raw_records": merged.raw_records,
        "merged_digest": merged.digest,
        "merged_output": str(merged_output_path),
        "duplicate_records_removed": sharded_raw_records - len(merged.rows),
        "single_records": single_records,
        "single_raw_records": single_raw_records,
        "single_digest": single_digest,
        "single_output": single_output_path,
        "single_run": single_run_json,
        "single_vs_sharded_digest_match": digest_match,
    }

    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _eprint(f"error: {exc}")
        raise SystemExit(1)
