import os
import re
import fnmatch
from dataclasses import dataclass


@dataclass
class TagRef:
    id: str
    file: str
    line: int
    anchor: str = ""


_TAG_RE = re.compile(r"spec:(INV-[A-Z]+(?:-[A-Z]+)*-\d+)(?:\s+anchor:(?:sha-)?([0-9a-fA-F]+))?")


def extract_tags(file: str, content: str):
    """Find all spec:INV-* patterns, including inside strings/comments. Does not
    parse syntax; every occurrence counts. Trailing anchor:<hex> captured for B4.
    """
    refs = []
    for i, line in enumerate(content.split("\n")):
        for m in _TAG_RE.finditer(line):
            refs.append(TagRef(id=m.group(1), file=file, line=i + 1,
                               anchor=(m.group(2) or "").lower()))
    return refs


def _matches_exclude(rel: str, patterns) -> bool:
    rel = rel.replace(os.sep, "/")
    for pat in patterns or []:
        pat = pat.replace(os.sep, "/")
        if fnmatch.fnmatch(rel, pat):
            return True
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if fnmatch.fnmatch(rel, prefix) or rel.startswith(prefix + "/"):
                return True
    return False


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def scan_dir(root: str, suffixes, skip, exclude_globs=None):
    """Walk root, run extract_tags on every file whose name ends with one of
    suffixes. Directories whose base name is in skip are pruned. Walk order is
    sorted for determinism. `skip` is a set of directory base names.
    `exclude_globs` are root-relative glob patterns for generated artifacts.
    """
    refs = []
    exclude_globs = list(exclude_globs or [])
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in skip and not _matches_exclude(_rel(root, os.path.join(dirpath, d)), exclude_globs)
        )
        for name in sorted(filenames):
            if not any(name.endswith(s) for s in suffixes):
                continue
            path = os.path.join(dirpath, name)
            if _matches_exclude(_rel(root, path), exclude_globs):
                continue
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
                refs.extend(extract_tags(path, f.read()))
    return refs
