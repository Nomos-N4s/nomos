"""Hold the published implementation-size figures to the tree (#309).

The README's "By the Numbers" block and AGENTS.md carried "~2,800 lines -
50+ files - 10 subpackages" for a codebase that had grown to 7x that: the
counts were hand-written once and never touched again. These tests recompute
the real numbers from ``src/nomos`` on every CI run, so the claim cannot go
silently stale a second time. When one fails, update the two documents to the
measured figures - the tolerances below are wide enough that only real drift
trips them.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "nomos"

LINE_TOLERANCE = 0.10
FILE_FLOOR_SLACK = 0.75


def _measured() -> tuple[int, int, int]:
    files = [p for p in sorted(SRC.rglob("*.py")) if "__pycache__" not in p.parts]
    lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
    subpackages = [p for p in SRC.rglob("__init__.py") if p.parent != SRC]
    return len(files), lines, len(subpackages)


def _claims(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match, f"size claim not found; expected text matching {pattern!r}"
    files, lines, subpackages = (
        int(match.group("files")),
        int(match.group("lines").replace(",", "")),
        int(match.group("subpackages")),
    )
    return files, lines, subpackages


def _check(claimed_files: int, claimed_lines: int, claimed_subpackages: int):
    files, lines, subpackages = _measured()
    assert claimed_subpackages == subpackages, (
        f"claimed {claimed_subpackages} subpackages, tree has {subpackages}"
    )
    assert files >= claimed_files, f"claimed {claimed_files}+ files, tree has {files}"
    assert claimed_files >= files * FILE_FLOOR_SLACK, (
        f"'{claimed_files}+' undersells {files} files by more than 25%"
    )
    assert abs(lines - claimed_lines) <= lines * LINE_TOLERANCE, (
        f"claimed ~{claimed_lines} lines, tree has {lines} (>10% drift)"
    )


class TestPublishedSizeClaims:
    def test_readme_by_the_numbers(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        claims = _claims(
            text,
            r"~(?P<lines>[\d,]+) lines · (?P<files>\d+)\+ files · "
            r"(?P<subpackages>\d+) subpackages",
        )
        _check(*claims)

    def test_agents_md_headline(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claims = _claims(
            text,
            r"(?P<files>\d+)\+ Python files across (?P<subpackages>\d+) subpackages "
            r"\(~(?P<lines>[\d,]+) lines total",
        )
        _check(*claims)

    def test_agents_md_table_names_every_subpackage(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        direct = sorted(p.parent.name for p in SRC.glob("*/__init__.py") if p.parent != SRC)
        for package in direct:
            assert f"`{package}/`" in text, (
                f"src/nomos/{package}/ is missing from the AGENTS.md module table"
            )
