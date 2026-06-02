import hashlib
import json
from collections import defaultdict

from .binding import classify_pointer, BindingKind
from .scope import resolve_scope
from .shape import check_shape, has_shall


def _binding(req, tags, resolver, ext):
    kind, a1, a2 = classify_pointer(req.pointer, ext)
    if kind == BindingKind.TAG:
        return {"kind": "invariant-tag", "ref": a1, "resolved": a1 in tags, "at": ""}
    if kind == BindingKind.TEST:
        return {"kind": "test", "ref": f"{a1}::{a2}",
                "resolved": resolver.test_func_exists(a1, a2), "at": a1}
    if kind == BindingKind.CONTRACT:
        return {"kind": "contract", "ref": a1,
                "resolved": resolver.artifact_exists(a1), "at": a1}
    return {"kind": "none", "ref": "", "resolved": False, "at": ""}


def build_index(manifests, tags, resolver, ext, root):
    """从已解析 manifest + tag 集 + resolver 派生结构化索引(纯静态,无 git)。"""
    tagset = {t.id for t in tags} if not isinstance(tags, set) else tags
    rules = []
    by_path = defaultdict(list)
    by_category = defaultdict(list)
    by_status = defaultdict(list)
    by_test = defaultdict(list)
    counts = defaultdict(lambda: defaultdict(int))
    digest = hashlib.sha256()

    for m in manifests:
        for req in m.requirements:
            digest.update(f"{req.id}|{req.sentence}|{req.kind}|{req.pointer}|{req.status}\n"
                          .encode("utf-8"))
            binding = _binding(req, tagset, resolver, ext)
            scope = resolve_scope(req.scope, root)
            errs, warns = check_shape(req.kind, req.sentence, req.pointer)
            row = {
                "id": req.id, "module": req.module, "status": req.status,
                "sentence": req.sentence, "why": req.why, "category": req.kind,
                "binding": binding, "scope": scope,
                "shape": {"has_shall": has_shall(req.sentence),
                          "errors": errs, "lint_warnings": warns},
                "at": f"{req.file}:{req.line}",
            }
            rules.append(row)
            for f in scope["files"]:
                by_path[f].append(req.id)
            by_category[req.kind].append(req.id)
            by_status[req.status].append(req.id)
            if binding["kind"] == "test":
                by_test[binding["ref"]].append(req.id)
            counts[req.module][req.status] += 1

    return {
        "rules": rules,
        "by_path": dict(by_path), "by_category": dict(by_category),
        "by_status": dict(by_status), "by_test": dict(by_test),
        "counts": {k: dict(v) for k, v in counts.items()},
        "digest": digest.hexdigest()[:16],
    }


def emit_index(index, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2, sort_keys=True)
