"""fastqwiper 1.1.5 (wipertools) rewritten as a pure function, as a test oracle.

It reads a file the way the tool does (gzip text mode for .gz, codecs.open otherwise) and
follows its line-by-line decisions, returning the wiped reads and the report counts. The
de.NBI validation compared it with the real tool in its pinned container on fuzzed inputs.
"""
from __future__ import annotations

import codecs
import gzip
import re
from pathlib import Path

FIELDS = ("Total lines", "Well-formed lines", "Clean reads", "Bad headers or misplaced lines",
          "fixed", "BAD SEQ lines", "BAD '+' lines", "BAD QUAL lines",
          "Reads discarded because len(SEQ) neq len(QUAL)", "Blank lines")


def wipe(path: Path, alphabet: str = "ACGTN") -> tuple[str, dict[str, int]]:
    """The reads fastqwiper keeps from `path`, and its report counts."""
    if path.stat().st_size == 0 and path.name.endswith(".gz"):
        raise ValueError("fastqwiper cannot read a zero-byte gzip file")
    handle = (gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.name.endswith(".gz")
              else codecs.open(str(path), encoding="utf-8", errors="replace"))
    reg = re.compile(f"^[{alphabet}]+$")
    n = dict.fromkeys(("tot", "blank", "bad_seq", "fixed", "bad_header", "bad_plus", "bad_qual",
                       "clean", "neq"), 0)
    header_length = 0
    out: list[str] = []

    def next_line() -> str:
        line = ""
        for line in handle:
            n["tot"] += 1
            line = line.rstrip()
            if not line:
                n["blank"] += 1
            else:
                return line
        return line

    with handle:
        for line in handle:
            n["tot"] += 1
            if not line.rstrip():
                n["blank"] += 1
                continue
            line = line.rstrip()
            header = ""
            if line.isprintable() and line.rfind("@") == 0:
                header, header_length = line, len(line)
            elif not line.isprintable():
                n["bad_header"] += 1
                rescued = line[line.rfind("@"):]
                if len(rescued) == header_length:
                    n["fixed"] += 1
                    header = rescued
            elif "@" not in line:
                n["bad_header"] += 1
            else:
                n["bad_header"] += 1
                header = line[line.rfind("@"):]
                n["fixed"] += 1
            if not header:
                continue
            seq = next_line()
            if not seq.isprintable() or not reg.match(seq):
                n["bad_seq"] += 1
                continue
            plus = next_line()
            if not plus.isprintable() or plus.find("+") != 0:
                n["bad_plus"] += 1
                continue
            qual = next_line()
            if not qual.isprintable():
                n["bad_qual"] += 1
                continue
            if not qual:
                continue
            if len(seq) == len(qual):
                out.append(f"{header}\n{seq}\n{plus}\n{qual}\n")
                n["clean"] += 1
            else:
                n["neq"] += 1
    counts = dict(zip(FIELDS, (n["tot"], n["clean"] * 4, n["clean"], n["bad_header"], n["fixed"],
                               n["bad_seq"], n["bad_plus"], n["bad_qual"], n["neq"], n["blank"]),
                      strict=True))
    return "".join(out), counts
