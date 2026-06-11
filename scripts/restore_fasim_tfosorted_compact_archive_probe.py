#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path


MAGIC = b"FATFOD1\0"
VERSION = 1
COMP = bytes.maketrans(b"ACGTNacgtn", b"TGCANtgcan")
CODE_TO_DIRECTION = {0: b"R", 1: b"L"}
CODE_TO_STRAND = {0: b"ParaPlus", 1: b"ParaMinus", 2: b"AntiPlus", 3: b"AntiMinus"}
HEADER = (
    b"QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    b"StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\t"
    b"Strand\tRule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\t"
    b"TFO sequence\tTTS sequence\n"
)


def read_fasta(path: Path) -> bytes:
    chunks = []
    with path.open("rb") as handle:
        for line in handle:
            if not line.startswith(b">"):
                chunks.append(line.strip().upper())
    return b"".join(chunks)


def complement(seq: bytes) -> bytes:
    return seq.translate(COMP).upper()


def reverse_complement(seq: bytes) -> bytes:
    return complement(seq)[::-1]


def target_slice(target: bytes, start: int, end: int, strand_code: int) -> bytes:
    if strand_code == 0:
        return target[start - 1 : end]
    if strand_code == 1:
        return reverse_complement(target[start : end + 1])
    if strand_code == 2:
        return target[start : end + 1][::-1].upper()
    if strand_code == 3:
        return complement(target[start - 1 : end])
    raise SystemExit(f"unknown strand code: {strand_code}")


def get_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise SystemExit("truncated varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def unzigzag(value: int) -> int:
    if value & 1:
        return -((value + 1) >> 1)
    return value >> 1


def apply_mask(ungapped: bytes, aligned_len: int, mask: bytes) -> bytes:
    out = bytearray()
    pos = 0
    for i in range(aligned_len):
        if (mask[i // 8] >> (i % 8)) & 1:
            out.append(45)
        else:
            if pos >= len(ungapped):
                raise SystemExit("mask consumed beyond ungapped sequence")
            out.append(ungapped[pos])
            pos += 1
    if pos != len(ungapped):
        raise SystemExit(f"mask consumed {pos}, expected {len(ungapped)}")
    return bytes(out)


def read_bytes(data: bytes, pos: int) -> tuple[bytes, int]:
    size, pos = get_varint(data, pos)
    value = data[pos : pos + size]
    if len(value) != size:
        raise SystemExit("truncated byte payload")
    return value, pos + size


def restore_archive(src: Path, dst: Path, query: bytes, target: bytes) -> int:
    rows = 0
    previous = [0, 0, 0]
    with src.open("rb") as archive, dst.open("wb") as out:
        if archive.read(len(MAGIC)) != MAGIC:
            raise SystemExit("bad magic")
        version_raw = archive.read(4)
        if len(version_raw) != 4:
            raise SystemExit("truncated version")
        (version,) = struct.unpack("<I", version_raw)
        if version != VERSION:
            raise SystemExit(f"bad version: {version}")
        out.write(HEADER)
        payload = archive.read()
        pos = 0
        while pos < len(payload):
            row_size, pos = get_varint(payload, pos)
            row_end = pos + row_size
            if row_end > len(payload):
                raise SystemExit("truncated row")
            row = payload[pos:row_end]
            pos = row_end
            p = 0
            deltas = []
            for i in range(3):
                encoded, p = get_varint(row, p)
                previous[i] += unzigzag(encoded)
                deltas.append(previous[i])
            qs, ss, score = deltas
            align_len, p = get_varint(row, p)
            q_len, p = get_varint(row, p)
            t_len, p = get_varint(row, p)
            rule, p = get_varint(row, p)
            nt, p = get_varint(row, p)
            flags, p = get_varint(row, p)
            direction_code = flags & 0x1
            strand_code = (flags >> 1) & 0x3
            stability, p = read_bytes(row, p)
            identity, p = read_bytes(row, p)
            tfo_mask, p = read_bytes(row, p)
            tts_mask, p = read_bytes(row, p)
            if p != len(row):
                raise SystemExit("extra row payload")
            qe = qs + q_len - 1
            se = ss + t_len - 1
            tfo = apply_mask(query[qs - 1 : qe], align_len, tfo_mask)
            tts = apply_mask(target_slice(target, ss, se, strand_code), align_len, tts_mask)
            midpoint = (qs + qe) // 2
            fields = [
                str(qs).encode(),
                str(qe).encode(),
                str(ss).encode(),
                str(se).encode(),
                CODE_TO_DIRECTION[direction_code],
                b"",
                str(ss).encode(),
                str(se).encode(),
                stability,
                identity,
                CODE_TO_STRAND[strand_code],
                str(rule).encode(),
                str(score).encode(),
                str(nt).encode(),
                b"0",
                str(midpoint).encode(),
                str(midpoint).encode(),
                tfo,
                tts,
            ]
            out.write(b"\t".join(fields) + b"\n")
            rows += 1
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query-fasta", required=True)
    parser.add_argument("--target-fasta", required=True)
    args = parser.parse_args()
    rows = restore_archive(
        Path(args.archive),
        Path(args.output),
        read_fasta(Path(args.query_fasta)),
        read_fasta(Path(args.target_fasta)),
    )
    print(f"rows={rows}")
    print(f"restored_bytes={Path(args.output).stat().st_size}")


if __name__ == "__main__":
    main()
