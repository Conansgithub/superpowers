import unittest
from specanchor.coverage import coverage
from specanchor.manifest import Manifest, Requirement
from specanchor.tags import TagRef
from specanchor.invariant import ENFORCED, STATED, VIOLATED


class FakeResolver:
    def __init__(self, funcs=None, arts=None):
        self.funcs = funcs or {}
        self.arts = arts or {}

    def test_func_exists(self, file, fn):
        return self.funcs.get(f"{file}::{fn}", False)

    def artifact_exists(self, path):
        return self.arts.get(path, False)


def req(rid, kind, pointer, status):
    return Requirement(id=rid, kind=kind, pointer=pointer, status=status,
                       module="m", file="spec/m/spec.md", line=1)


class TestCoverage(unittest.TestCase):
    def test_mixed(self):
        res = FakeResolver(funcs={"login_test.go::TestOK": True},
                           arts={"api/openapi.json": True})
        tags = [TagRef(id="INV-TRACE-1", file="t_test.go", line=1)]
        manifests = [Manifest(module="m", requirements=[
            req("M-1", "铁律", "spec:INV-TRACE-1", ENFORCED),               # bound (tag)
            req("M-2", "行为·当", "测试: login_test.go::TestOK", ENFORCED),    # bound (test)
            req("M-3", "接口", "生成: api/openapi.json", ENFORCED),           # bound (artifact)
            req("M-4", "铁律", "spec:INV-GHOST-9", ENFORCED),               # UNBOUND
            req("M-5", "行为·若", "测试: login_test.go::TestGone", ENFORCED),  # UNBOUND
            req("M-6", "行为·当", "待补", STATED),                            # advisory
            req("M-7", "接口", "生成: api/openapi.json", VIOLATED),           # violated → block
        ])]
        c = coverage(manifests, tags, res, "go")
        self.assertEqual([r.id for r in c.unbound], ["M-4", "M-5"])
        self.assertEqual([r.id for r in c.stated], ["M-6"])
        self.assertEqual([r.id for r in c.violated], ["M-7"])
        self.assertTrue(c.blocking())

    def test_all_bound_or_stated_not_blocking(self):
        res = FakeResolver(arts={"api/a.json": True})
        manifests = [Manifest(module="m", requirements=[
            req("M-1", "接口", "生成: api/a.json", ENFORCED),
            req("M-2", "行为·当", "待补", STATED),
        ])]
        self.assertFalse(coverage(manifests, [], res, "go").blocking())

    def test_empty_not_blocking(self):
        self.assertFalse(coverage([], [], FakeResolver(), "go").blocking())


if __name__ == "__main__":
    unittest.main()
