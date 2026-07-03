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
from specanchor.binding import OSResolver, ShellResolver, DeclarativeResolver, ResolverError
from specanchor.contracts import load_contracts, ContractError
from specanchor.refs import dangling
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
    p.add_argument("--emit-index", dest="emit_index", default=None,
                   help="write derived spec-index.json to this path")
    p.add_argument("--contracts", default=None,
                   help="declarative contracts file (non-code domains); resolves CONTRACT pointers")
    return p


def run(argv) -> int:
    if argv and argv[0] == "adopt":
        return _run_adopt(argv[1:])
    if argv and argv[0] == "init":
        return _run_init(argv[1:])
    if argv and argv[0] == "audit":
        return _run_audit(argv[1:])
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
        "index": args.emit_index,
        "contracts": args.contracts,
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
        tags = scan_dir(root, [lang.test_suffix], skip, cfg.exclude_globs)
    except OSError as e:
        print(f"spec-check: scan tags: {e}", file=sys.stderr)
        return 2

    try:
        manifests = _load_manifests(root, cfg.manifests)
    except (OSError, ManifestError) as e:
        print(f"spec-check: load manifests: {e}", file=sys.stderr)
        return 2
    req_count = sum(len(m.requirements) for m in manifests)

    if cfg.resolver:
        resolver = ShellResolver(cfg.resolver, root)
    elif cfg.contracts:
        contracts_path = os.path.join(root, cfg.contracts) if cfg.contracts_from_descriptor else cfg.contracts
        try:
            contracts = load_contracts(contracts_path)
        except ContractError as e:
            print(f"spec-check: {e}", file=sys.stderr)
            return 2
        resolver = DeclarativeResolver(root, lang, contracts)
    else:
        resolver = OSResolver(root, lang)
    res = check(invs, tags)
    try:
        cov = coverage(manifests, tags, resolver, lang.pointer_ext)
    except ResolverError as e:
        print(f"spec-check: resolver: {e}", file=sys.stderr)
        return 2
    from specanchor.shape import check_shape
    from specanchor.index import build_index, emit_index
    shape_errs = []
    for m in manifests:
        for req in m.requirements:
            errs, _ = check_shape(req.kind, req.sentence, req.pointer)
            for e in errs:
                shape_errs.append((req.id, req.module, e))
    shape_block = bool(shape_errs) and cfg.shape_strict == "block"

    dang = dangling(manifests, invs)

    if cfg.index:
        idx_path = os.path.join(root, cfg.index) if cfg.index_from_descriptor else cfg.index
        emit_index(build_index(manifests, tags, resolver, lang.pointer_ext, root), idx_path)

    blocking = (res.blocking() or cov.blocking() or shape_block or bool(dang)
                or (cfg.anchor_strict and len(res.suspect) > 0))
    for rid, mod, e in shape_errs:
        label = "SHAPE" if cfg.shape_strict == "block" else "shape"
        print(f"  {label:<9} {rid} ({mod}) — {e}", file=sys.stdout)
    for ref_id, where in dang:
        print(f"  DANGLING  {ref_id} referenced at {where} — resolves to no live rule", file=sys.stdout)
    report(sys.stdout, invs, tags, res, cov, req_count, blocking)
    return 1 if blocking else 0


def _run_audit(argv) -> int:
    p = argparse.ArgumentParser(prog="spec-check audit", add_help=True)
    p.add_argument("-root", default=".")
    p.add_argument("--audit-bare-refs", dest="audit_bare_refs", action="store_true",
                   default=False,
                   help="扫描裸方法论 token (INV-/spec:MODULE-ID)，即未包进 // spec: 或 [[ref:]] 的位置；"
                        "只打印、不改退出码 (advisory)")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    root = a.root
    try:
        descriptor = load_descriptor(root)
    except DescriptorError as e:
        print(f"spec-check: {e}", file=sys.stderr)
        return 2
    cfg = merge({}, descriptor or {})
    if cfg.lang is None or cfg.lang not in LANGS:
        print("spec-check: --lang required (no flag and no .spec-check.json lang)", file=sys.stderr)
        return 2
    lang = LANGS[cfg.lang]
    try:
        inv_path = os.path.join(root, cfg.invariants) if cfg.invariants_from_descriptor else cfg.invariants
        with open(inv_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            invs = parse_invariants(f.read())
        skip = set(_DEFAULT_SKIP)
        skip.update(cfg.skip)
        tags = scan_dir(root, [lang.test_suffix], skip, cfg.exclude_globs)
        manifests = _load_manifests(root, cfg.manifests)
    except (OSError, InvariantError, ManifestError) as e:
        print(f"spec-check: audit load: {e}", file=sys.stderr)
        return 2

    from specanchor import audit, gitinfo
    runner = gitinfo.GitRunner(root)
    git_ok = gitinfo.is_repo(runner)
    n = sum(len(m.requirements) for m in manifests)
    stale = audit.staleness(manifests, tags, ext=lang.pointer_ext, root=root,
                            runner=runner, test_suffix=lang.test_suffix) if git_ok else []
    aging = audit.stated_aging(manifests, invs, root=root, runner=runner) if git_ok else []
    dups = audit.dedup(manifests)
    prose = audit.prose_lint(manifests)
    bare = audit.bare_refs(root, exclude_globs=cfg.exclude_globs) if a.audit_bare_refs else None
    print(audit.render(stale, dups, aging, prose, [], n, git_ok, bare=bare))
    return 0


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
