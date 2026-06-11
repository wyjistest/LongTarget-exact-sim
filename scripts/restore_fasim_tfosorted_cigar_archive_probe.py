#!/usr/bin/env python3
import argparse
from pathlib import Path


COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")
HEADER = (
    "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\t"
    "Strand\tRule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\t"
    "TFO sequence\tTTS sequence\n"
)


def read_fasta(path: Path) -> str:
    parts = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith(">"):
                parts.append(line.strip().upper())
    return "".join(parts)


def complement(seq: str) -> str:
    return seq.translate(COMP).upper()


def reverse_complement(seq: str) -> str:
    return complement(seq)[::-1]


def emit_aligned(query: str, target: str, q0: int, r0: int, cigar: str) -> tuple[str, str]:
    q = q0
    r = r0
    tfo = []
    tts = []
    number = ""
    for ch in cigar:
        if ch.isdigit():
            number += ch
            continue
        if not number:
            raise SystemExit(f"bad CIGAR op without length: {cigar}")
        length = int(number)
        number = ""
        if ch in ("M", "=", "X"):
            tfo.append(query[q : q + length])
            tts.append(target[r : r + length])
            q += length
            r += length
        elif ch == "I":
            tfo.append(query[q : q + length])
            tts.append("-" * length)
            q += length
        elif ch == "D":
            tfo.append("-" * length)
            tts.append(target[r : r + length])
            r += length
        else:
            raise SystemExit(f"unsupported CIGAR op {ch!r}: {cigar}")
    if number:
        raise SystemExit(f"bad trailing CIGAR length: {cigar}")
    return "".join(tfo), "".join(tts)


def target_slice(target: str, ss: int, se: int, strand: str) -> str:
    if strand == "ParaPlus":
        return target[ss - 1 : se]
    if strand == "ParaMinus":
        return reverse_complement(target[ss : se + 1])
    if strand == "AntiPlus":
        return target[ss : se + 1][::-1].upper()
    if strand == "AntiMinus":
        return complement(target[ss - 1 : se])
    raise SystemExit(f"unknown strand: {strand}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query-fasta", required=True)
    parser.add_argument("--target-fasta", required=True)
    args = parser.parse_args()

    query = read_fasta(Path(args.query_fasta))
    target = read_fasta(Path(args.target_fasta))
    rows = 0
    with Path(args.archive).open("r", encoding="utf-8") as archive, Path(args.output).open(
        "w", encoding="utf-8"
    ) as out:
        header = archive.readline().rstrip("\n").split("\t")
        expected = [
            "QueryStart",
            "QueryEnd",
            "StartInSeq",
            "EndInSeq",
            "Direction",
            "Chr",
            "StartInGenome",
            "EndInGenome",
            "MeanStability",
            "MeanIdentity(%)",
            "Strand",
            "Rule",
            "Score",
            "Nt(bp)",
            "Class",
            "MidPoint",
            "Center",
            "CIGAR",
        ]
        if header != expected:
            raise SystemExit("bad archive header")
        out.write(HEADER)
        for line in archive:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(expected):
                raise SystemExit(f"bad field count: {len(fields)}")
            (
                qs,
                qe,
                ss,
                se,
                direction,
                chr_name,
                gs,
                ge,
                stability,
                identity,
                strand,
                rule,
                score,
                nt,
                klass,
                midpoint,
                center,
                cigar,
            ) = fields
            target_context = target_slice(target, int(ss), int(se), strand)
            tfo, tts = emit_aligned(
                query[int(qs) - 1 : int(qe)],
                target_context,
                0,
                0,
                cigar,
            )
            out.write(
                "\t".join(
                    [
                        qs,
                        qe,
                        ss,
                        se,
                        direction,
                        chr_name,
                        gs,
                        ge,
                        stability,
                        identity,
                        strand,
                        rule,
                        score,
                        nt,
                        klass,
                        midpoint,
                        center,
                        tfo,
                        tts,
                    ]
                )
                + "\n"
            )
            rows += 1
    print(f"rows={rows}")
    print(f"restored_bytes={Path(args.output).stat().st_size}")


if __name__ == "__main__":
    main()
