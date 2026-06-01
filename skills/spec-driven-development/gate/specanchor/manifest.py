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
    kind: str = ""      # raw 哪类 label
    pointer: str = ""   # raw 连到哪 cell — classified at coverage time
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
        if cells[0] == "编号":
            in_table = True
            continue
        if not in_table:
            continue
        if len(cells) != 5:
            raise ManifestError(f"{path}:{i+1}: expected 5 columns, got {len(cells)}")
        try:
            status = _parse_status(cells[4])
        except ManifestError as e:
            raise ManifestError(f"{path}:{i+1}: {e}")
        rid = cells[0]
        if rid == "":
            raise ManifestError(f"{path}:{i+1}: empty requirement ID")
        if rid in seen:
            raise ManifestError(f"{path}:{i+1}: duplicate requirement ID: {rid}")
        seen.add(rid)
        reqs.append(Requirement(id=rid, sentence=cells[1], kind=cells[2],
                                pointer=cells[3], status=status, file=path, line=i + 1))
    for r in reqs:  # backfill so rows before a late header carry the final name
        r.module = module
    return Manifest(module=module, requirements=reqs)
