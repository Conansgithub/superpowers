import os
import re
import glob as _glob
from collections import defaultdict
from datetime import date
from . import gitinfo
from .binding import classify_pointer, BindingKind

_VAGUE = ("等", "诸如", "可能", "通常", "一般", "若干", "尽量", "适当")
_LONG = 120


def _watched_files(req, tagfile, ext, test_suffix, root):
    """规则盯哪些生产文件(相对 root 的路径,喂 git -- )。
    显式 scope → glob 字面串(git 自解析,稀少且简单);
    否则窄取绑定测试所在包的生产文件(python glob,去 *_test 后的具体文件)。"""
    cell = (req.scope or "").strip()
    if cell and cell != "—":
        return [g.split("::", 1)[0].strip() for g in cell.split(",") if g.strip()]
    kind, a1, a2 = classify_pointer(req.pointer, ext)
    test_path = a1 if kind == BindingKind.TEST else (tagfile.get(a1) if kind == BindingKind.TAG else None)
    if not test_path:
        return []
    d = os.path.dirname(os.path.join(root, test_path))
    return [os.path.relpath(p, root) for p in sorted(_glob.glob(f"{d}/*{ext}"))
            if not p.endswith(test_suffix)]


def staleness(manifests, tags, resolver=None, ext=".go", root=".", runner=None, test_suffix="_test.go"):
    tagfile = {t.id: t.file for t in tags}
    runner = runner or gitinfo.GitRunner(root)
    findings = []
    for m in manifests:
        for req in m.requirements:
            if req.status != "enforced":
                continue
            files = _watched_files(req, tagfile, ext, test_suffix, root)
            if not files:
                continue
            relmanifest = os.path.relpath(req.file, root) if os.path.isabs(req.file) else req.file
            row_commit = gitinfo.blame_line(runner, relmanifest, req.line)
            if not row_commit:
                continue
            since = gitinfo.log_since(runner, row_commit, files)
            if since:
                findings.append((req.id, req.module, since[:3]))
    return findings


def dedup(manifests):
    seen = defaultdict(list)
    for m in manifests:
        for req in m.requirements:
            seen[" ".join(req.sentence.split())].append(req.id)
    return [ids for ids in seen.values() if len(ids) > 1]


def prose_lint(manifests):
    out = []
    for m in manifests:
        for req in m.requirements:
            s = req.sentence
            for w in _VAGUE:
                if w in s:
                    out.append((req.id, f"模糊词「{w}」"))
            if len(s) > _LONG:
                out.append((req.id, f"超长句({len(s)}字)"))
    return out


def stated_aging(manifests, invs, root=".", runner=None, today=None):
    """stated 行计龄。manifest 用 git blame 日期、invariant 用 Since。返回 (id, days|None)。"""
    runner = runner or gitinfo.GitRunner(root)
    today = today or date.today()
    out = []
    for m in manifests:
        for req in m.requirements:
            if req.status != "stated":
                continue
            relmanifest = os.path.relpath(req.file, root) if os.path.isabs(req.file) else req.file
            sha = gitinfo.blame_line(runner, relmanifest, req.line)
            d = _commit_date(runner, sha) if sha else None
            out.append((req.id, (today - d).days if d else None))
    return out


def _commit_date(runner, sha):
    o, ok = runner.run(["show", "-s", "--format=%cs", sha])  # YYYY-MM-DD
    if not ok or not o.strip():
        return None
    try:
        y, mth, dy = (int(x) for x in o.strip().split("-"))
        return date(y, mth, dy)
    except ValueError:
        return None


_LEDGER_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+[a-z]?\b")


def ledger_ref(ledger_text, live_ids):
    """账本散文里 rule-ID-形 token 不在 live 集的 (id, lineno)。启发式、可能误报。"""
    out = []
    for i, line in enumerate(ledger_text.split("\n"), 1):
        for tok in _LEDGER_ID.findall(line):
            if tok not in live_ids:
                out.append((tok, i))
    return out


def render(stale, dups, aging, prose, ledger, n_rows, git_ok):
    L = [f"spec-check audit: {n_rows} rows scanned (git: {'ok' if git_ok else 'unavailable'})"]
    if stale:
        L.append(f"STALE ({len(stale)}):")
        L += [f"  {i} ({mod}) — watched code moved after row [{','.join(c)}]" for i, mod, c in stale]
    aged = sorted([(d, i) for i, d in aging if d is not None], reverse=True)
    if aged:
        L.append(f"STATED-AGING ({len(aged)}):")
        L += [f"  {i} — stated {d}d" for d, i in aged[:20]]
    if dups:
        L.append(f"DUPLICATE ({len(dups)}):")
        L += [f"  {sorted(g)} 文本相同" for g in dups]
    if prose:
        L.append(f"PROSE ({len(prose)}):")
        L += [f"  {i} — {w}" for i, w in prose]
    if ledger:
        L.append(f"LEDGER-REF? ({len(ledger)}):")
        L += [f"  {i} @ ledger:{ln} 可能悬空" for i, ln in ledger]
    total = len(stale) + len(aged) + len(dups) + len(prose) + len(ledger)
    L.append(f"audit: {total} findings (advisory — 不阻断)")
    return "\n".join(L)
