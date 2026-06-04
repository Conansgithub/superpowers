import json
import os
import re
import subprocess


class ContractError(Exception):
    """spec/contracts.json 的结构问题 —— 大声 fail，绝不静默解绑。"""


_TYPES = {"contains", "exec", "exists"}


def load_contracts(path):
    """加载声明式契约文件 {selector: [assertion, ...]}。任一结构异常抛 ContractError。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise ContractError(f"{path}: {e}")
    if not isinstance(data, dict):
        raise ContractError(f"{path}: top level must be a JSON object")
    for selector, assertions in data.items():
        if not isinstance(assertions, list) or not assertions:
            raise ContractError(f"{path}: {selector!r} must be a non-empty list of assertions")
        for a in assertions:
            _validate(path, selector, a)
    return data


def _validate(path, selector, a):
    if not isinstance(a, dict) or a.get("type") not in _TYPES:
        raise ContractError(f"{path}: {selector!r} assertion needs type in {sorted(_TYPES)}, got {a!r}")
    t = a["type"]
    if t == "contains":
        if not isinstance(a.get("files"), list) or not a["files"]:
            raise ContractError(f"{path}: {selector!r} contains needs non-empty 'files'")
        if not a.get("all") and not a.get("none"):
            raise ContractError(f"{path}: {selector!r} contains needs 'all' or 'none'")
    elif t == "exec":
        if not isinstance(a.get("cmd"), str) or not a["cmd"]:
            raise ContractError(f"{path}: {selector!r} exec needs 'cmd' string")
    elif t == "exists":
        if not isinstance(a.get("paths"), list) or not a["paths"]:
            raise ContractError(f"{path}: {selector!r} exists needs non-empty 'paths'")


def eval_contract(assertions, root):
    """全部 assertion 通过才返回 True。静态 gate 既有 tradeoff：注释内命中算可接受假阳。"""
    return all(_eval_one(a, root) for a in assertions)


def _eval_one(a, root):
    t = a["type"]
    if t == "contains":
        return _eval_contains(a, root)
    if t == "exec":
        return _eval_exec(a, root)
    if t == "exists":
        return all(os.path.exists(os.path.join(root, p)) for p in a["paths"])
    return False


def _eval_contains(a, root):
    alls = [re.compile(p) for p in a.get("all", [])]
    nones = [re.compile(p) for p in a.get("none", [])]
    for f in a["files"]:
        try:
            with open(os.path.join(root, f), "r", encoding="utf-8", errors="surrogateescape") as fh:
                content = fh.read()
        except OSError:
            return False
        if any(rx.search(content) is None for rx in alls):
            return False
        if any(rx.search(content) is not None for rx in nones):
            return False
    return True


def _eval_exec(a, root):
    argv = [a["cmd"]] + list(a.get("args", []))
    try:
        proc = subprocess.run(argv, cwd=root)
    except OSError:
        return False
    return proc.returncode == 0
