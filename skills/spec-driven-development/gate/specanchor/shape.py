import re

# EARS 标准类别名(值用英文);gap 是覆盖缺口标记,非 EARS 规则。
KINDS = {"invariant", "event", "unwanted", "contract", "optional", "gap"}

_SHALL_RE = re.compile(r"\bSHALL(?:\s+NOT)?\b")
_TEST_PTR_RE = re.compile(r"::[A-Za-z0-9_]+")        # file.<ext>::Func
_TAG_PTR_RE = re.compile(r"spec:INV-[A-Z]+-\d+")
_GAP_PREFIX = ("gap:", "resolver-todo:")
_WEASEL = ("适当", "合理", "尽快", "友好", "appropriate", "reasonable")

# 句子需 SHALL 的类型(gap 非规则;contract 由工件守)
_NEEDS_SHALL = {"invariant", "event", "unwanted", "optional"}


def check_shape(kind, sentence, pointer):
    """校验一行的"形状",返回 (errors, warnings)。errors 非空 + shape_strict=block → 阻断。
    只校骨架(类型枚举 / SHALL 存在 / 指针前缀与类型相符),不校语义。
    """
    errors, warnings = [], []
    if kind not in KINDS:
        errors.append(f"类型 {kind!r} 不在枚举 {sorted(KINDS)}")
        return errors, warnings  # 类型未知,后续校验无意义

    if kind in _NEEDS_SHALL and not _SHALL_RE.search(sentence):
        errors.append("陈述缺规范动词 SHALL/SHALL NOT")

    # 指针前缀须与类型相符
    if kind == "invariant":
        if not _TAG_PTR_RE.search(pointer):
            errors.append("invariant 指针须为 spec:INV-*")
    elif kind in ("event", "unwanted", "optional"):
        if not _TEST_PTR_RE.search(pointer):
            errors.append(f"{kind} 指针须为 file::Func 测试引用")
    elif kind == "contract":
        if "生成" not in pointer:
            errors.append("contract 指针须指向生成工件(含「生成」)")
    elif kind == "gap":
        if not pointer.startswith(_GAP_PREFIX):
            errors.append("gap 指针须以 gap:/resolver-todo: 起")

    # LINT(只印不拦)
    if any(w in sentence for w in _WEASEL):
        warnings.append("weasel 词(适当/合理/尽快/友好)")
    if len(_SHALL_RE.findall(sentence)) > 1:
        warnings.append("复合 SHALL,疑似两条,应拆")
    return errors, warnings


def has_shall(sentence):
    """True iff the sentence carries the SHALL/SHALL NOT normative verb."""
    return bool(_SHALL_RE.search(sentence))
