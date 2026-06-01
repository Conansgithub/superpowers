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
from specanchor.binding import OSResolver, ShellResolver, ResolverError
from specanchor.langs import LANGS
from specanchor.descriptor import load_descriptor, merge, DescriptorError
from specanchor import scaffold

_DEFAULT_SKIP = {".git", "node_modules", "vendor", "testdata", "conformance"}


def _build_parser():
    p = argparse.ArgumentParser(prog="spec-check", add_help=True)
    p.add_argument("-invariants", default=None,
                   help="path to INVARIANTS.md (default docs/migration/INVARIANTS.md)")
    p.add_argument("-root", default=".", help="root dir scanned for spec: tags")
    p.add_argument("-anchor-strict", dest="anchor_strict", action="store_true",
                   default=None, help="treat B4 fingerprint-drift suspects as blocking")
    p.add_argument("-manifests", default=None,
                   help="glob (relative to -root) for manifests; empty disables coverage")
    p.add_argument("--lang", default=None, choices=sorted(LANGS.keys()),
                   help="project language (flag or .spec-check.json; required if neither)")
    p.add_argument("--skip", default=None,
                   help="comma-separated extra directory base-names to prune")
    p.add_argument("--resolver", default=None,
                   help="external command resolving coverage bindings (non-code domains)")
    return p


def run(argv) -> int:
    if argv and argv[0] == "adopt":
        return _run_adopt(argv[1:])
    if argv and argv[0] == "init":
        return _run_init(argv[1:])
    if argv and argv[0] == "check":
        argv = argv[1:]
    return _run_check(argv)


def _run_adopt(argv) -> int:
    p = argparse.ArgumentParser(prog="spec-check adopt", add_help=True)
    p.add_argument("-root", default=".")
    p.add_argument("--lang", default=None, choices=sorted(LANGS.keys()))
    p.add_argument("--skip", default=None, help="comma-separated extra skip dirs")
    p.add_argument("--force", action="store_true")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    skip = [s for s in a.skip.split(",") if s] if a.skip else None
    return scaffold.adopt(a.root, lang=a.lang, skip=skip, force=a.force)


def _run_init(argv) -> int:
    p = argparse.ArgumentParser(prog="spec-check init", add_help=True)
    p.add_argument("-root", default=".")
    p.add_argument("--lang", required=True, choices=sorted(LANGS.keys()))
    p.add_argument("--force", action="store_true")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    return scaffold.init(a.root, a.lang, force=a.force)


def _run_check(argv) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit:
        return 2  # bad flag or -h surfaces as usage exit

    root = args.root
    try:
        descriptor = load_descriptor(root)
    except DescriptorError as e:
        print(f"spec-check: {e}", file=sys.stderr)
        return 2

    flags = {
        "lang": args.lang,
        "invariants": args.invariants,
        "manifests": args.manifests,
        "anchor_strict": args.anchor_strict,
        "resolver": args.resolver,
        "skip": [s for s in args.skip.split(",") if s] if args.skip else None,
    }
    cfg = merge(flags, descriptor or {})

    if cfg.lang is None:
        print("spec-check: --lang required (no flag and no .spec-check.json lang)", file=sys.stderr)
        return 2
    lang = LANGS.get(cfg.lang)
    if lang is None:
        print(f"spec-check: unknown lang {cfg.lang!r}", file=sys.stderr)
        return 2

    invariants_path = os.path.join(root, cfg.invariants) if cfg.invariants_from_descriptor else cfg.invariants
    try:
        with open(invariants_path, "r", encoding="utf-8", errors="surrogateescape") as f:
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
    skip.update(cfg.skip)
    try:
        tags = scan_dir(root, [lang.test_suffix], skip)
    except OSError as e:
        print(f"spec-check: scan tags: {e}", file=sys.stderr)
        return 2

    try:
        manifests = _load_manifests(root, cfg.manifests)
    except (OSError, ManifestError) as e:
        print(f"spec-check: load manifests: {e}", file=sys.stderr)
        return 2
    req_count = sum(len(m.requirements) for m in manifests)

    resolver = ShellResolver(cfg.resolver, root) if cfg.resolver else OSResolver(root, lang)
    res = check(invs, tags)
    try:
        cov = coverage(manifests, tags, resolver, lang.pointer_ext)
    except ResolverError as e:
        print(f"spec-check: resolver: {e}", file=sys.stderr)
        return 2
    blocking = res.blocking() or cov.blocking() or (cfg.anchor_strict and len(res.suspect) > 0)
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
        with open(p, "r", encoding="utf-8", errors="surrogateescape") as f:
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
        print(f'  UNBOUND   {req.id} at {req.file}:{req.line} — enforced but "{req.pointer}" resolves to nothing', file=w)
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
