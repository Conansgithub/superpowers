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


def _write_descriptor(path, descriptor):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(descriptor, f, indent=2, ensure_ascii=False)
        f.write("\n")


def adopt(root, lang=None, skip=None, force=False, out=sys.stdout):
    """Detect an existing project's language/paths and write .spec-check.json.
    Returns an exit code (0 ok, 2 usage). Never guesses an ambiguous language.
    """
    path = os.path.join(root, DESCRIPTOR_NAME)
    if os.path.exists(path) and not force:
        print(f"adopt: {DESCRIPTOR_NAME} exists; pass --force to overwrite", file=sys.stderr)
        return 2
    if lang is None:
        try:
            lang = detect_lang(root)
        except ValueError as e:
            print(f"adopt: {e}", file=sys.stderr)
            return 2
    if lang not in LANGS:
        print(f"adopt: unknown lang {lang!r}", file=sys.stderr)
        return 2

    invariants = probe_invariants(root)
    missing_inv = invariants is None
    if missing_inv:
        invariants = "docs/migration/INVARIANTS.md"
    manifests = "spec/*/spec.md" if os.path.isdir(os.path.join(root, "spec")) else ""

    descriptor = {
        "lang": lang,
        "invariants": invariants,
        "manifests": manifests,
        "skip": list(skip or []),
        "anchor_strict": False,
        "resolver": None,
    }
    _write_descriptor(path, descriptor)
    print(f"adopt: wrote {DESCRIPTOR_NAME} "
          f"(lang={lang}, invariants={invariants}, manifests={manifests or 'disabled'})", file=out)
    if missing_inv:
        print(f"adopt: no INVARIANTS.md found; defaulted to {invariants} — run 'init' or create it", file=out)
    return 0


def _template(name):
    with open(os.path.join(_REFS, name), "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def init(root, lang, force=False, out=sys.stdout):
    """Scaffold a greenfield project: INVARIANTS.md + spec/sample/spec.md +
    .spec-check.json (from the skill's reference templates). Returns an exit code.
    """
    if lang not in LANGS:
        print(f"init: unknown lang {lang!r}", file=sys.stderr)
        return 2
    rel_targets = ["INVARIANTS.md", os.path.join("spec", "sample", "spec.md"), DESCRIPTOR_NAME]
    existing = [t for t in rel_targets if os.path.exists(os.path.join(root, t))]
    if existing and not force:
        print(f"init: refusing to overwrite {existing}; pass --force", file=sys.stderr)
        return 2

    _write_text(os.path.join(root, "INVARIANTS.md"), _template("invariants-template.md"))
    _write_text(os.path.join(root, "spec", "sample", "spec.md"), _template("manifest-template.md"))
    descriptor = {
        "lang": lang,
        "invariants": "INVARIANTS.md",
        "manifests": "spec/*/spec.md",
        "skip": [],
        "anchor_strict": False,
        "resolver": None,
    }
    _write_descriptor(os.path.join(root, DESCRIPTOR_NAME), descriptor)
    print(f"init: scaffolded INVARIANTS.md, spec/sample/spec.md, {DESCRIPTOR_NAME} (lang={lang})", file=out)
    return 0
