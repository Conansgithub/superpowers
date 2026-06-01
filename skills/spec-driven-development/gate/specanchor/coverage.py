from dataclasses import dataclass, field
from .invariant import STATED, ENFORCED, VIOLATED
from .binding import classify_pointer, BindingKind


@dataclass
class CoverageResult:
    unbound: list = field(default_factory=list)   # C1: enforced but pointer dangling
    violated: list = field(default_factory=list)   # C2: status violated
    stated: list = field(default_factory=list)     # advisory

    def blocking(self) -> bool:
        return bool(self.unbound) or bool(self.violated)


def _bound(req, tagged, resolver, ext) -> bool:
    kind, a1, a2 = classify_pointer(req.pointer, ext)
    if kind == BindingKind.TAG:
        return a1 in tagged
    if kind == BindingKind.TEST:
        return resolver.test_func_exists(a1, a2)
    if kind == BindingKind.CONTRACT:
        return resolver.artifact_exists(a1)
    return False


def coverage(manifests, tags, resolver, ext) -> CoverageResult:
    """Every enforced manifest requirement must resolve to a live binding: a tag
    for an invariant pointer, a test func for a behavior pointer, or an existing
    artifact for a contract pointer. Stated is advisory; violated blocks. Order
    mirrors manifest order (no sort). Mirrors due's Go Coverage; `ext` selects the
    language for pointer classification.
    """
    tagged = {tg.id for tg in tags}
    c = CoverageResult()
    for m in manifests:
        for req in m.requirements:
            if req.status == VIOLATED:
                c.violated.append(req)
            elif req.status == STATED:
                c.stated.append(req)
            elif req.status == ENFORCED:
                if not _bound(req, tagged, resolver, ext):
                    c.unbound.append(req)
    return c
