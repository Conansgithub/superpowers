#!/usr/bin/env python3
"""Portable spec-check gate. Static and fast. Not in any project's CI —
enforcement lives at the verification/finishing seams. Mirrors due's Go
cmd/ops/spec-check, made language/domain-agnostic via --lang and a resolver.
"""
import argparse
import glob
import os
import sys

from specanchor.invariant import parse_invariants, InvariantError
from specanchor.tags import scan_dir
from specanchor.manifest import parse_manifest, ManifestError
from specanchor.check import check
from specanchor.coverage import coverage
from specanchor.binding import OSResolver
from specanchor.langs import LANGS

_DEFAULT_SKIP = {".git", "node_modules", "vendor", "testdata", "conformance"}


def _build_parser():
    p = argparse.ArgumentParser(prog="spec-check", add_help=True)
    p.add_argument("-invariants", default="docs/migration/INVARIANTS.md",
                   help="path to INVARIANTS.md")
    p.add_argument("-root", default=".", help="root dir scanned for spec: tags")
    p.add_argument("-anchor-strict", dest="anchor_strict", action="store_true",
                   help="treat B4 fingerprint-drift suspects as blocking")
    p.add_argument("-manifests", default="spec/*/spec.md",
                   help="glob (relative to -root) for manifests; empty disables coverage")
    p.add_argument("--lang", required=True, choices=sorted(LANGS.keys()),
                   help="project language (selects test-file suffix + behavior regex)")
    p.add_argument("--skip", default="",
                   help="comma-separated extra directory base-names to prune")
    return p


def run(argv) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit:
        return 2  # missing --lang, bad flag, or -h all surface as usage exit
    lang = LANGS[args.lang]

    try:
        with open(args.invariants, "r", encoding="utf-8") as f:
            md = f.read()
    except OSError as e:
        print(f"spec-check: read invariants: {e}", file=sys.stderr)
        return 2
    try:
        invs = parse_invariants(md)
    except InvariantError as e:
        print(f"spec-check: parse invariants: {e}", file=sys.stderr)
        return 2

    skip = set(_DEFAULT_SKIP)
    skip.update(s for s in args.skip.split(",") if s)
    try:
        tags = scan_dir(args.root, [lang.test_suffix], skip)
    except OSError as e:
        print(f"spec-check: scan tags: {e}", file=sys.stderr)
        return 2

    try:
        manifests = _load_manifests(args.root, args.manifests)
    except (OSError, ManifestError) as e:
        print(f"spec-check: load manifests: {e}", file=sys.stderr)
        return 2
    req_count = sum(len(m.requirements) for m in manifests)

    res = check(invs, tags)
    cov = coverage(manifests, tags, OSResolver(args.root, lang), lang.pointer_ext)
    blocking = res.blocking() or cov.blocking() or (args.anchor_strict and len(res.suspect) > 0)
    report(sys.stdout, invs, tags, res, cov, req_count, blocking)
    return 1 if blocking else 0


def _load_manifests(root, pattern):
    """Glob for manifests under root and parse each. Empty pattern disables the
    check; a pattern matching nothing is not an error (dormant until first lands).
    """
    if pattern == "":
        return []
    out = []
    for p in sorted(glob.glob(os.path.join(root, pattern))):
        with open(p, "r", encoding="utf-8") as f:
            out.append(parse_manifest(p, f.read()))
    return out


def report(w, invs, tags, res, cov, req_count, blocking):
    print(f"spec-check: {len(invs)} invariants, {len(tags)} spec: tags, {req_count} manifest reqs", file=w)
    for inv_id in res.violated:
        print(f"  VIOLATED  {inv_id} — code contradicts a declared invariant", file=w)
    for req in cov.violated:
        print(f"  VIOLATED  {req.id} ({req.module}) — manifest marks this requirement violated", file=w)
    for inv_id in res.uncovered:
        print(f"  UNCOVERED {inv_id} — enforced but no test carries spec:{inv_id}", file=w)
    for req in cov.unbound:
        print(f"  UNBOUND   {req.id} at {req.file}:{req.line} — enforced but {req.pointer!r} resolves to nothing", file=w)
    for tg in res.orphans:
        print(f"  ORPHAN    spec:{tg.id} at {tg.file}:{tg.line} — no such invariant", file=w)
    for s in res.suspect:
        print(f"  SUSPECT   {s.id} at {s.where} — holds changed (live {s.want} ≠ stamped {s.got}); re-verify the test, then update the anchor", file=w)
    for inv in res.stated:
        print(f"  stated    {inv.id} (since {inv.since}) — advisory, not yet enforced", file=w)
    for req in cov.stated:
        print(f"  stated    {req.id} ({req.module}) — advisory, manifest requirement not yet enforced", file=w)
    print("spec-check: FAIL" if blocking else "spec-check: OK", file=w)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
