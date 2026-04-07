#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


def _parse_starts(spec: str) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as e:
            raise RuntimeError(f"invalid --starts entry: {item}") from e
        if value <= 0:
            raise RuntimeError(f"--starts entries must be > 0: {item}")
        values.append(value)
    if not values:
        raise RuntimeError("--starts must not be empty")
    return values


def _read_single_fasta(path: Path) -> tuple[str, str]:
    header: str | None = None
    seq_parts: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip().replace("\r", "")
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                raise RuntimeError(f"expected exactly one FASTA record: {path}")
            header = line[1:].strip()
            continue
        if header is None:
            raise RuntimeError(f"missing FASTA header: {path}")
        seq_parts.append(line)
    if header is None:
        raise RuntimeError(f"empty fasta: {path}")
    seq = "".join(seq_parts)
    if not seq:
        raise RuntimeError(f"empty fasta sequence: {path}")
    return header, seq


def _output_header(source_header: str, start: int, end: int) -> str:
    parts = source_header.split("|")
    if len(parts) >= 3 and "-" in parts[-1]:
        return "|".join([*parts[:-1], f"{start}-{end}"])
    return f"{source_header}|{start}-{end}"


def _write_wrapped_fasta(path: Path, *, header: str, seq: str, line_width: int) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f">{header}\n")
        for i in range(0, len(seq), line_width):
            fh.write(seq[i : i + line_width])
            fh.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cut fixed-length anchor shards from a single-record FASTA.",
    )
    parser.add_argument("--input-fasta", required=True, help="source FASTA with exactly one record")
    parser.add_argument("--output-dir", required=True, help="directory for generated shard FASTA files")
    parser.add_argument("--starts", required=True, help="comma-separated 1-based shard start positions")
    parser.add_argument("--length", required=True, type=int, help="shard length in bp")
    parser.add_argument(
        "--output-prefix",
        default=None,
        help="filename prefix for generated shard FASTA files (default: input stem)",
    )
    parser.add_argument("--line-width", type=int, default=60, help="FASTA sequence line width (default: 60)")
    args = parser.parse_args()

    if args.length <= 0:
        raise RuntimeError("--length must be > 0")
    if args.line_width <= 0:
        raise RuntimeError("--line-width must be > 0")

    input_fasta = Path(args.input_fasta).resolve()
    if not input_fasta.exists():
        raise RuntimeError(f"missing FASTA: {input_fasta}")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    starts = _parse_starts(args.starts)
    source_header, seq = _read_single_fasta(input_fasta)
    output_prefix = args.output_prefix or input_fasta.stem

    written = 0
    for start in starts:
        end = start + args.length - 1
        if end > len(seq):
            raise RuntimeError(
                f"requested shard {start}-{end} exceeds sequence length {len(seq)} for {input_fasta}"
            )
        shard_seq = seq[start - 1 : end]
        shard_header = _output_header(source_header, start, end)
        out_path = output_dir / f"{output_prefix}_{start}_{args.length}.fa"
        _write_wrapped_fasta(
            out_path,
            header=shard_header,
            seq=shard_seq,
            line_width=args.line_width,
        )
        written += 1

    print(f"wrote {written} shard FASTA files to {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
