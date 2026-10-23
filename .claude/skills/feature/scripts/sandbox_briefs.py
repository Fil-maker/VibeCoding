"""Auditor briefs for the red check: packs of requirements (up to eight scenarios) with their tests.

Why it exists: when every new test is red, `test-auditor` agents run in parallel, one per pack of
requirements. A pack never splits a requirement; each brief holds the requirement blocks verbatim
and the test files and test names the auditor must read.
"""

from __future__ import annotations

import re
from pathlib import Path

import harness_docs as hd
import sandbox_tests as st

PACK_LIMIT = 8


def pack_blocks(blocks: list[hd.Block], limit: int = PACK_LIMIT) -> list[list[hd.Block]]:
    """Group requirement blocks into packs of at most `limit` scenarios, never splitting one."""
    packs: list[list[hd.Block]] = []
    current: list[hd.Block] = []
    count = 0
    for block in blocks:
        if current and count + block.scenarios > limit:
            packs.append(current)
            current, count = [], 0
        current.append(block)
        count += block.scenarios
    if current:
        packs.append(current)
    return packs


def delta_blocks(project: Path, change: str) -> list[hd.Block]:
    """ADDED and MODIFIED requirement blocks of a change."""
    folder = project / "openspec" / "changes" / change
    found: list[hd.Block] = []
    for path in hd.delta_files(folder).values():
        found += [
            b for b in hd.parse_blocks(hd.read_text(path)) if b.section in {"ADDED", "MODIFIED"}
        ]
    return found


def write_auditor_briefs(
    project: Path,
    sandbox: Path,
    change: str,
    out_dir: Path,
    results: list[st.TestResult],
    test_files: list[str],
) -> list[Path]:
    """Write one brief per pack; returns their paths."""
    packs = pack_blocks(delta_blocks(project, change))
    out_dir.mkdir(parents=True, exist_ok=True)
    mentions = {
        f: {int(n) for n in re.findall(r"FR-(\d+)", hd.read_text(sandbox / f))} for f in test_files
    }
    paths: list[Path] = []
    for index, pack in enumerate(packs, 1):
        frs = {b.fr for b in pack if b.fr is not None}
        files = [f for f in test_files if not mentions[f] or mentions[f] & frs]
        lines = [
            f"# Auditor brief {index} of {len(packs)}: change {change}",
            "",
            f"Sandbox: {sandbox}",
            "Audit the tests below against the requirements below. Read only the sandbox.",
            "",
            "## Requirements",
        ]
        for block in pack:
            lines += ["", block.text]
        lines += ["", "## Tests"]
        for file in files:
            names = [r.name for r in results if r.file == file and r.name]
            lines.append(f"- {file}")
            lines += [f"    - {n}" for n in names]
        path = out_dir / f"auditor-{index}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(path)
    return paths
