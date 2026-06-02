import os
import re
from dataclasses import dataclass, field
from .invariant import STATED, ENFORCED, VIOLATED


class ManifestError(ValueError):
    """A structural problem in a manifest — fail loud, never drop a requirement."""


@dataclass
class Requirement:
    id: str
    sentence: str = ""
    kind: str = ""      # raw 类型 label
    pointer: str = ""   # raw 绑定 cell — classified at coverage time
    scope: str = ""     # raw scope cell
    why: str = ""       # raw Why cell
    status: str = ""
    module: str = ""
    file: str = ""
    line: int = 0


@dataclass
class Manifest:
    module: str
    requirements: list = field(default_factory=list)


# "## <module> — 清单" header (em-dash U+2014).
_MODULE_RE = re.compile(r"^##\s+(.+?)\s+—\s+清单\s*$")

EXPECTED_HEADER = ["编号", "陈述", "Why", "类型", "绑定", "scope", "状态"]


def _table_cells(line: str):
    """Split a markdown row into trimmed cells, dropping the bounding-pipe empties.
    A separator row (every cell only dashes/colons) returns None.
    """
    parts = line.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    cells = [p.strip() for p in parts]
    if not cells or all(c.strip("-:") == "" for c in cells):
        return None
    return cells


def _parse_status(s: str) -> str:
    if s in (STATED, ENFORCED, VIOLATED):
        return s
    raise ManifestError(f"unknown status {s!r}")


def parse_manifest(path: str, content: str) -> Manifest:
    """Parse a capability manifest. Module name from the '## <module> — 清单'
    header if present, else the parent directory. A table starts at its header
    row (first cell '编号') and ends at the first non-table line. A row with the
    wrong column count, unknown status, empty ID, or duplicate ID is an error.
    Mirrors due's Go ParseManifest.
    """
    module = os.path.basename(os.path.dirname(path))
    reqs = []
    seen = set()
    in_table = False
    for i, raw in enumerate(content.split("\n")):
        line = raw.strip()
        m = _MODULE_RE.match(line)
        if m:
            module = m.group(1)
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = _table_cells(line)
        if cells is None:
            continue
        if cells and cells[0] == "编号":
            if cells != EXPECTED_HEADER:
                raise ManifestError(
                    f"{path}:{i+1}: 表头必须为 {EXPECTED_HEADER},得到 {cells}")
            in_table = True
            continue
        if not in_table:
            continue
        if len(cells) != 7:
            raise ManifestError(f"{path}:{i+1}: expected 7 columns, got {len(cells)}")
        try:
            status = _parse_status(cells[6])
        except ManifestError as e:
            raise ManifestError(f"{path}:{i+1}: {e}")
        rid = cells[0]
        if rid == "":
            raise ManifestError(f"{path}:{i+1}: empty requirement ID")
        if rid in seen:
            raise ManifestError(f"{path}:{i+1}: duplicate requirement ID: {rid}")
        seen.add(rid)
        reqs.append(Requirement(id=rid, sentence=cells[1], why=cells[2], kind=cells[3],
                                pointer=cells[4], scope=cells[5], status=status,
                                file=path, line=i + 1))
    for r in reqs:  # backfill so rows before a late header carry the final name
        r.module = module
    return Manifest(module=module, requirements=reqs)
