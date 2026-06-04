import os
import re
import shlex
import subprocess
from enum import Enum
from typing import Protocol

from .contracts import eval_contract


class BindingKind(Enum):
    NONE = 0
    TAG = 1       # spec:INV-* — an invariant tag in the test tree
    TEST = 2      # file.<ext>::Func — a behavior's guarding test
    CONTRACT = 3  # a generated artifact path (OpenAPI, golden file)


_PTR_TAG_RE = re.compile(r"spec:(INV-[A-Z]+-\d+)")
# Path-like token ending in an extension; gated on the 生成 marker so it never
# fires on prose like "版本 1.0".
_PTR_PATH_RE = re.compile(r"([\w][\w./-]*\.[A-Za-z0-9]+)")


def _ptr_test_re(ext: str):
    # ([^\s|（()]+\.<ext>)::([A-Za-z0-9_]+) — ASCII func names, matching Go.
    return re.compile(r"([^\s|（()]+\." + re.escape(ext) + r")::([A-Za-z0-9_]+)")


def classify_pointer(pointer: str, ext: str):
    """Inspect a manifest '连到哪' cell → (kind, a1, a2):
    TAG→(invID,""), TEST→(file,func), CONTRACT→(path,""). Order matters: a tag
    wins over a path, and a '::' test ref wins over a bare path, so a behavior
    pointer is never mistaken for a contract. `ext` is the active language's
    source extension. Mirrors due's classifyPointer (which hardcodes ext=go).
    """
    m = _PTR_TAG_RE.search(pointer)
    if m:
        return BindingKind.TAG, m.group(1), ""
    m = _ptr_test_re(ext).search(pointer)
    if m:
        return BindingKind.TEST, m.group(1), m.group(2)
    if "生成" in pointer:
        m = _PTR_PATH_RE.search(pointer)
        if m:
            return BindingKind.CONTRACT, m.group(1), ""
    return BindingKind.NONE, "", ""


class Resolver(Protocol):
    def test_func_exists(self, file: str, fn: str) -> bool: ...
    def artifact_exists(self, path: str) -> bool: ...


class OSResolver:
    """Resolves bindings against the filesystem, joining every path to root.
    `lang` supplies the verified-behavior declaration (Go 'func fn(', Py 'def fn(').
    """

    def __init__(self, root: str, lang):
        self.root = root
        self.lang = lang

    def test_func_exists(self, file: str, fn: str) -> bool:
        try:
            with open(os.path.join(self.root, file), "r", encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
        except OSError:
            return False
        # Plain substring scan; a decl inside a comment/string is an accepted
        # false positive for a static gate (same tradeoff as due).
        return self.lang.behavior_decl(fn) in content

    def artifact_exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.root, path))


class ResolverError(Exception):
    pass


class ShellResolver:
    """Resolves coverage bindings by shelling out, for non-code domains. The
    binding is passed as argv: '<cmd> test <file> <fn>' or '<cmd> artifact <path>',
    run with cwd=root. Exit 0 = resolved, non-zero = not. No timeout (static gate).
    """

    def __init__(self, cmd, root):
        self._cmd = cmd
        self._argv = shlex.split(cmd)
        self.root = root

    def _ok(self, *parts) -> bool:
        try:
            proc = subprocess.run(self._argv + list(parts), cwd=self.root)
        except OSError as e:
            raise ResolverError(f"{self._cmd!r}: {e}")
        return proc.returncode == 0

    def test_func_exists(self, file: str, fn: str) -> bool:
        return self._ok("test", file, fn)

    def artifact_exists(self, path: str) -> bool:
        return self._ok("artifact", path)


class DeclarativeResolver:
    """test → 委托现有 OSResolver（185 条 TEST 绑定零分歧）；artifact → 已登记 selector
    跑声明式契约，未登记则回退 OSResolver 文件存在性（保现存 contract 行不破）。"""

    def __init__(self, root, lang, contracts):
        self._os = OSResolver(root, lang)
        self._root = root
        self._contracts = contracts

    def test_func_exists(self, file: str, fn: str) -> bool:
        return self._os.test_func_exists(file, fn)

    def artifact_exists(self, path: str) -> bool:
        if path in self._contracts:
            return eval_contract(self._contracts[path], self._root)
        return self._os.artifact_exists(path)
