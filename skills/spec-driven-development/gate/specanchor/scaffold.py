import json
import os
import sys

from .langs import LANGS
from .descriptor import DESCRIPTOR_NAME

_LANG_MARKERS = {
    "go.mod": "go",
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
}
_INV_PROBE = [
    "docs/migration/INVARIANTS.md",
    "INVARIANTS.md",
    "docs/INVARIANTS.md",
    "spec/INVARIANTS.md",
]
_REFS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "references"))


def detect_lang(root):
    """Detect language from marker files. Return a name in LANGS, or raise
    ValueError on ambiguity (multiple) or no markers — never guess silently.
    """
    found = set()
    for marker, lang in _LANG_MARKERS.items():
        if os.path.exists(os.path.join(root, marker)):
            found.add(lang)
    if len(found) == 1:
        return found.pop()
    if not found:
        raise ValueError("no language markers found; pass --lang")
    raise ValueError(f"ambiguous languages {sorted(found)}; pass --lang")


def probe_invariants(root):
    """Return the first existing invariants path (relative), or None."""
    for rel in _INV_PROBE:
        if os.path.exists(os.path.join(root, rel)):
            return rel
    return None
