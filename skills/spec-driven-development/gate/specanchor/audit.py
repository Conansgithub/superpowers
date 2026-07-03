import os
import re
import glob as _glob
import fnmatch
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


# ── 裸引用审计 (bare-refs) ────────────────────────────────────────────────────
# 裸方法论 token: INV-[A-Z]+-\d+ 或 spec:[A-Z][A-Z0-9-]+ 出现在文件中,
# 但既不在 spec:INV-X 绑定标签 (gate _TAG_RE 解析的真实 anchor)、也不在 [[ref:...]] 内的位置。
# 默认关闭 (--audit-bare-refs 才激活)、只打印不改退出码。
_BARE_INV_RE  = re.compile(r"\bINV-[A-Z][A-Z0-9]*-\d+\b")
_BARE_SPEC_RE = re.compile(r"\bspec:([A-Z][A-Z0-9-]+-\d+[a-z]?)\b")
# 绑定标签 — gate _TAG_RE 识别 spec:INV-X 出现在任意位置(不限行首)，审计同步
_BINDING_ANCHOR_RE = re.compile(r"\bspec:INV-[A-Z][A-Z0-9]*-\d+\b")
# [[ref:...]] 段: 匹配 [[ref: 后面直到第一个 ]]
_REF_BLOCK_RE = re.compile(r"\[\[ref:[^\]]*\]\]")

_BARE_REFS_TEXT_EXTS = {
    ".go", ".md", ".yaml", ".yml", ".sh", ".sql", ".toml", ".json", ".ts", ".tsx",
}
_BARE_REFS_SKIP_DIRS = {".git", "node_modules", "vendor", "testdata", "conformance",
                        "__pycache__", "dist", ".serena", ".codegraph"}


def _matches_exclude(root: str, path: str, patterns) -> bool:
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    for pat in patterns or []:
        pat = pat.replace(os.sep, "/")
        if fnmatch.fnmatch(rel, pat):
            return True
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if fnmatch.fnmatch(rel, prefix) or rel.startswith(prefix + "/"):
                return True
    return False


def bare_refs(root: str, extra_skip=None, exclude_globs=None):
    """扫 root 下所有文本文件，找裸方法论 token（既非绑定标签、又非 [[ref:]] 内）。
    返回 [(file, lineno, token)] 列表。默认关闭、不改退出码。
    """
    skip = _BARE_REFS_SKIP_DIRS | (extra_skip or set())
    exclude_globs = list(exclude_globs or [])
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in skip and not _matches_exclude(root, os.path.join(dirpath, d), exclude_globs)
        )
        for fname in sorted(filenames):
            _, ext = os.path.splitext(fname)
            if ext not in _BARE_REFS_TEXT_EXTS:
                continue
            path = os.path.join(dirpath, fname)
            if _matches_exclude(root, path, exclude_globs):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
                    lines = f.read().split("\n")
            except OSError:
                continue
            for lineno, line in enumerate(lines, 1):
                # 从行中抹去：① [[ref:...]] 段；② spec:INV-X 绑定标签（任意位置）
                # 剩余内容中出现的 INV-X 或 spec:MODULE-X 才是裸引用
                cleaned = _REF_BLOCK_RE.sub("", line)
                cleaned = _BINDING_ANCHOR_RE.sub("", cleaned)
                # 查 INV- 裸引用
                for m in _BARE_INV_RE.finditer(cleaned):
                    findings.append((path, lineno, m.group(0)))
                # 查 spec:MODULE-ID 裸引用（INV- 前缀已在上步被抹去，不会重复）
                for m in _BARE_SPEC_RE.finditer(cleaned):
                    findings.append((path, lineno, "spec:" + m.group(1)))
    return findings


def render(stale, dups, aging, prose, ledger, n_rows, git_ok, bare=None):
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
    if bare is not None:
        if bare:
            L.append(f"BARE-REFS ({len(bare)}) -- 裸方法论 token, 建议包进 [[ref:...]]:")
            for fpath, lno, tok in bare:
                L.append(f"  {fpath}:{lno}: {tok}")
        else:
            L.append("BARE-REFS: 0 — 全部已包裹 ✓")
    total = len(stale) + len(aged) + len(dups) + len(prose) + len(ledger)
    L.append(f"audit: {total} findings (advisory — 不阻断)")
    return "\n".join(L)
