#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


CPP_SOURCE = r"""
#include <iostream>
#include <algorithm>
#include <string>

#include "fasim/rules.h"

static int require_equal(const std::string &label,
                         const std::string &observed,
                         const std::string &expected)
{
    if (observed == expected)
    {
        return 0;
    }
    std::cerr << label << ": expected " << expected
              << ", got " << observed << std::endl;
    return 1;
}

int main()
{
    const std::string expectedRule1 = "TTGGN";

    int failures = 0;
    failures += require_equal("legacy uppercase rule1",
                              transferString("ACGTN", 0, 1, 1),
                              expectedRule1);
    failures += require_equal("legacy lowercase rule1",
                              transferString("acgtn", 0, 1, 1),
                              expectedRule1);
    failures += require_equal("legacy mixed-case rule1",
                              transferString("aCgTn", 0, 1, 1),
                              expectedRule1);
    failures += require_equal("table lowercase rule1",
                              transferStringTableDriven("acgtn", 0, 1, 1),
                              expectedRule1);
    failures += require_equal("table mixed-case rule1",
                              transferStringTableDriven("aCgTn", 0, 1, 1),
                              expectedRule1);

    std::string complementSeq = "acgtnACGTN";
    complement(complementSeq);
    failures += require_equal("complement lowercase soft-mask",
                              complementSeq,
                              "TGCANTGCAN");

    return failures == 0 ? 0 : 1;
}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_lowercase_softmask_transform"),
    )
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    source = work_dir / "check_fasim_lowercase_softmask_transform.cpp"
    binary = work_dir / "check_fasim_lowercase_softmask_transform"
    source.write_text(textwrap.dedent(CPP_SOURCE).strip() + "\n", encoding="utf-8")

    subprocess.run(
        ["g++", "-std=c++17", "-I", str(ROOT), str(source), "-o", str(binary)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([str(binary)], cwd=ROOT, check=True)
    print("Fasim lowercase soft-mask transform checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
