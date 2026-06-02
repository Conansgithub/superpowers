import re

# rule-ID 形:AUTH-3 / RC-2 / INV-X-1 / COCKPIT-17 / SVCREG-9b...(末段含数字,可带单字母后缀)
_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+[a-z]?$")


def _is_rule_id(tok):
    return "::" not in tok and bool(_ID_RE.match(tok))


def referenced_ids(invs):
    """结构化 rule-ID 引用 (id, where)。当前来源:invariant 的
    'Guarded by: <manifest-ID>'(命名规则、非 test::Func、非 —)。"""
    out = []
    for inv in invs:
        v = (inv.guarded_by or "").strip()
        if not v or v == "—" or "::" in v:
            continue
        for tok in re.split(r"[,\s]+", v):
            if _is_rule_id(tok):
                out.append((tok, f"INVARIANTS:{inv.id} Guarded by"))
    return out


def dangling(manifests, invs):
    """被结构化指针引用、却解析不到任何 live 规则的 ID 列表 [(id, where), ...]。
    纯静态、无 git。superseded 不豁免:引用须指向 live 继任者。"""
    live = {r.id for m in manifests for r in m.requirements}
    live |= {inv.id for inv in invs}
    return [(rid, where) for rid, where in referenced_ids(invs) if rid not in live]
