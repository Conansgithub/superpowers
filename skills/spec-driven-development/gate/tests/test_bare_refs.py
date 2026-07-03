import os
import tempfile
import unittest
from specanchor.audit import bare_refs


def _write(tmp, relpath, content):
    full = os.path.join(tmp, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


class TestBareRefsBinding(unittest.TestCase):
    """绑定标签 spec:INV-X (任意位置) 不报为裸引用。"""

    def test_binding_tag_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "pkg/x_test.go",
                   "// spec:INV-LEDGER-1 — refund\n"
                   "func TestRefund() {}\n")
            got = bare_refs(tmp)
            tokens = [tok for _, _, tok in got]
            self.assertNotIn("INV-LEDGER-1", tokens)

    def test_inline_binding_tag_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "a_test.go",
                   "\t// spec:INV-RES-2 anchor:abc123\n")
            got = bare_refs(tmp)
            self.assertEqual(got, [])

    def test_prose_comment_with_embedded_binding_tag(self):
        """// 绑定 INV-X: spec:INV-X — spec:INV-X 是真绑定标签不报，INV-X 在 [[ref:]] 内不报。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "x_test.go",
                   "// 绑定 [[ref:INV-NOTIFY-1]]: spec:INV-NOTIFY-1\n")
            got = bare_refs(tmp)
            self.assertEqual(got, [])


class TestBareRefsRefBlock(unittest.TestCase):
    """[[ref:…]] 内的 token 不报为裸引用。"""

    def test_ref_block_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "docs/design.md",
                   "设计参考 [[ref:INV-CAP-1 容量上限]] 和 [[ref:INV-RES-2]]\n")
            got = bare_refs(tmp)
            self.assertEqual(got, [])

    def test_partial_ref_block_remaining_bare(self):
        """同一行有 [[ref:]] 包裹和裸 token 时,只报裸的那个。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "notes.md",
                   "[[ref:INV-CAP-1]] 但 INV-RES-2 这里是裸的\n")
            got = bare_refs(tmp)
            tokens = [tok for _, _, tok in got]
            self.assertNotIn("INV-CAP-1", tokens)
            self.assertIn("INV-RES-2", tokens)


class TestBareRefsBareTokens(unittest.TestCase):
    """裸 INV- token 和 spec:MODULE-ID token 应被报告。"""

    def test_bare_inv_in_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "service.go",
                   "// 参见 INV-LEDGER-1 记账铁律\n"
                   "func foo() {}\n")
            got = bare_refs(tmp)
            tokens = [tok for _, _, tok in got]
            self.assertIn("INV-LEDGER-1", tokens)

    def test_bare_spec_module_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "x_test.go",
                   "// spec:BAG-10 — 列表透出\n")
            got = bare_refs(tmp)
            tokens = [tok for _, _, tok in got]
            self.assertIn("spec:BAG-10", tokens)

    def test_zero_bare_in_clean_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "clean.go",
                   "package main\nfunc main() {}\n")
            got = bare_refs(tmp)
            self.assertEqual(got, [])

    def test_exclude_globs_prune_generated_bundles(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "internal/docsportal/assets/swaggerui/bundle.js",
                   "// INV-LEDGER-1 in vendored generated bundle\n")
            _write(tmp, "service.go",
                   "// INV-AUDIT-1 real source prose\n")
            got = bare_refs(tmp, exclude_globs=["internal/docsportal/assets/**"])
            tokens = [tok for _, _, tok in got]
            self.assertNotIn("INV-LEDGER-1", tokens)
            self.assertIn("INV-AUDIT-1", tokens)


if __name__ == "__main__":
    unittest.main()
