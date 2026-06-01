import os
import tempfile
import unittest
import spec_check


def _write(d, invariants, test_file=""):
    with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
        f.write(invariants)
    if test_file:
        with open(os.path.join(d, "x_test.go"), "w") as f:
            f.write(test_file)


def _write_manifest(d, module, body):
    md = os.path.join(d, "spec", module)
    os.makedirs(md, exist_ok=True)
    with open(os.path.join(md, "spec.md"), "w") as f:
        f.write(body)


def _run(d, *extra):
    return spec_check.run(["--lang", "go", "-invariants",
                           os.path.join(d, "INVARIANTS.md"), "-root", d, *extra])


class TestRunExitCodes(unittest.TestCase):
    def test_all_stated_ok(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-RES-1 — x\nStatus: stated\nSince: 2026-05-31\n")
            self.assertEqual(_run(d), 0)

    def test_enforced_tagged_ok(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-LEDGER-1 — x\nStatus: enforced\nSince: 2026-05-31\n",
                   "// spec:INV-LEDGER-1\n")
            self.assertEqual(_run(d), 0)

    def test_enforced_untagged_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-LEDGER-1 — x\nStatus: enforced\nSince: 2026-05-31\n")
            self.assertEqual(_run(d), 1)

    def test_violated_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-CFG-1 — x\nStatus: violated\nSince: 2026-05-31\n")
            self.assertEqual(_run(d), 1)

    def test_orphan_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-RES-1 — x\nStatus: stated\nSince: 2026-05-31\n",
                   "// spec:INV-GHOST-9\n")
            self.assertEqual(_run(d), 1)

    def test_missing_file(self):
        self.assertEqual(spec_check.run(["--lang", "go", "-invariants", "/no/such/file", "-root", "."]), 2)

    def test_missing_lang(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-RES-1 — x\nStatus: stated\nSince: 2026-05-31\n")
            self.assertEqual(spec_check.run(["-invariants", os.path.join(d, "INVARIANTS.md"), "-root", d]), 2)

    def test_non_utf8_test_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-LEDGER-1 — x\nStatus: enforced\nSince: 2026-05-31\n")
            with open(os.path.join(d, "y_test.go"), "wb") as f:
                f.write(b"\xff\xfe// spec:INV-LEDGER-1\n")
            self.assertEqual(_run(d), 0)

    def test_anchor_advisory_then_strict(self):
        inv = "### INV-LEDGER-1 — x\nHolds: refund negates the recorded delta\nStatus: enforced\nSince: 2026-05-31\n"
        with tempfile.TemporaryDirectory() as d:
            _write(d, inv, "// spec:INV-LEDGER-1 anchor:0000000\n")
            self.assertEqual(_run(d), 0)
            self.assertEqual(_run(d, "-anchor-strict"), 1)


class TestRunManifestCoverage(unittest.TestCase):
    INV = "### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n"
    HEADER = "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n"

    def test_dormant(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            self.assertEqual(_run(d), 0)

    def test_bound_to_test(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            with open(os.path.join(d, "demo_test.go"), "w") as f:
                f.write("package p\nfunc TestDemo(t *testing.T) {}\n")
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | x | 行为·当 | 测试: demo_test.go::TestDemo | enforced |\n")
            self.assertEqual(_run(d), 0)

    def test_dangling_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | x | 行为·当 | 测试: demo_test.go::TestGone | enforced |\n")
            self.assertEqual(_run(d), 1)

    def test_stated_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | x | 行为·当 | 待补 | stated |\n")
            self.assertEqual(_run(d), 0)

    def test_malformed_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | x | 行为·当 | enforced |\n")
            self.assertEqual(_run(d), 2)


if __name__ == "__main__":
    unittest.main()
