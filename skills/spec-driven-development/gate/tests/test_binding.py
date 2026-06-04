import os
import tempfile
import unittest
from specanchor.binding import classify_pointer, BindingKind, OSResolver, ShellResolver, DeclarativeResolver
from specanchor.langs import LANGS


class TestClassifyPointer(unittest.TestCase):
    def test_cases(self):
        cases = [
            ("spec:INV-TRACE-1 → 性质测试", BindingKind.TAG, "INV-TRACE-1", ""),
            ("测试: internal/gameapi/login_test.go::TestLogin_Envelope",
             BindingKind.TEST, "internal/gameapi/login_test.go", "TestLogin_Envelope"),
            ("生成: api/openapi.json（快照对比）", BindingKind.CONTRACT, "api/openapi.json", ""),
            ("待补", BindingKind.NONE, "", ""),
            ("版本 1.0 发布", BindingKind.NONE, "", ""),
            ("生成: docs/migration/phase-2.md（快照）", BindingKind.CONTRACT, "docs/migration/phase-2.md", ""),
            ("生成: openapi.json", BindingKind.CONTRACT, "openapi.json", ""),
            ("生成+测试: internal/gameapi/status_map_test.go::TestStatusMap",
             BindingKind.TEST, "internal/gameapi/status_map_test.go", "TestStatusMap"),
        ]
        for pointer, kind, a1, a2 in cases:
            with self.subTest(pointer=pointer):
                self.assertEqual(classify_pointer(pointer, "go"), (kind, a1, a2))


class TestOSResolver(unittest.TestCase):
    def test_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "x_test.go"), "w") as f:
                f.write("package p\nfunc TestDemo(t *testing.T) {}\n")
            with open(os.path.join(d, "art.json"), "w") as f:
                f.write("{}")
            r = OSResolver(d, LANGS["go"])
            self.assertTrue(r.test_func_exists("x_test.go", "TestDemo"))
            self.assertFalse(r.test_func_exists("x_test.go", "TestMissing"))
            self.assertFalse(r.test_func_exists("nope_test.go", "TestDemo"))
            self.assertTrue(r.artifact_exists("art.json"))
            self.assertFalse(r.artifact_exists("ghost.json"))


class TestShellResolver(unittest.TestCase):
    def test_resolves_via_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            script = os.path.join(d, "r.sh")
            with open(script, "w") as f:
                f.write('#!/bin/sh\n'
                        '[ "$1" = "test" ] && [ "$2" = "a.go" ] && [ "$3" = "T" ] && exit 0\n'
                        '[ "$1" = "artifact" ] && [ "$2" = "ok.json" ] && exit 0\n'
                        'exit 1\n')
            r = ShellResolver(f"sh {script}", d)
            self.assertTrue(r.test_func_exists("a.go", "T"))
            self.assertFalse(r.test_func_exists("a.go", "Nope"))
            self.assertTrue(r.artifact_exists("ok.json"))
            self.assertFalse(r.artifact_exists("no.json"))


class TestDeclarativeResolver(unittest.TestCase):
    def _root(self, files):
        d = tempfile.mkdtemp()
        for n, c in files.items():
            p = os.path.join(d, n); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(c)
        return d

    def test_test_verb_delegates_to_os(self):
        root = self._root({"a_test.go": "func TestFoo(t *testing.T){}\n"})
        r = DeclarativeResolver(root, LANGS["go"], {})
        self.assertTrue(r.test_func_exists("a_test.go", "TestFoo"))
        self.assertFalse(r.test_func_exists("a_test.go", "Missing"))

    def test_artifact_known_selector_runs_contract(self):
        root = self._root({"x.yaml": "key: val\n"})
        c = {"sel.check": [{"type": "contains", "files": ["x.yaml"], "all": ["key: val"]}]}
        r = DeclarativeResolver(root, LANGS["go"], c)
        self.assertTrue(r.artifact_exists("sel.check"))

    def test_artifact_unknown_selector_falls_back_to_existence(self):
        root = self._root({"real.txt": "hi\n"})
        r = DeclarativeResolver(root, LANGS["go"], {})
        self.assertTrue(r.artifact_exists("real.txt"))
        self.assertFalse(r.artifact_exists("nope.txt"))


if __name__ == "__main__":
    unittest.main()
