import os
import tempfile
import unittest
from specanchor.tags import extract_tags, scan_dir


class TestExtractTags(unittest.TestCase):
    def test_extract_two(self):
        content = (
            "func TestRefund(t *testing.T) {\n"
            "\t// spec:INV-LEDGER-1 — refund reverses recorded delta\n"
            "\t_ = 1\n"
            "}\n"
            "// also spec:INV-RES-3 here\n"
        )
        got = extract_tags("ledger_test.go", content)
        self.assertEqual(len(got), 2)
        self.assertEqual((got[0].id, got[0].line, got[0].file),
                         ("INV-LEDGER-1", 2, "ledger_test.go"))
        self.assertEqual((got[1].id, got[1].line), ("INV-RES-3", 5))

    def test_captures_anchor(self):
        got = extract_tags("x_test.go", "// spec:INV-LEDGER-1 anchor:7f3a1c\n// spec:INV-RES-3\n")
        self.assertEqual((got[0].id, got[0].anchor), ("INV-LEDGER-1", "7f3a1c"))
        self.assertEqual((got[1].id, got[1].anchor), ("INV-RES-3", ""))

    def test_accepts_sha_prefix(self):
        got = extract_tags("x_test.go", "// spec:INV-LEDGER-1 anchor:sha-7f3a1c\n")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].anchor, "7f3a1c")


class TestScanDir(unittest.TestCase):
    def test_tolerates_non_utf8_file(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "a_test.go"), "wb") as f:
                f.write(b"\xff\xfe// spec:INV-LEDGER-1\n")  # invalid UTF-8 prefix
            got = scan_dir(root, ["_test.go"], {".git"})  # must not raise
            self.assertEqual([t.id for t in got], ["INV-LEDGER-1"])

    def test_filters_suffix_and_skips_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "a_test.go"), "w") as f:
                f.write("// spec:INV-LEDGER-1\n")
            with open(os.path.join(root, "b.go"), "w") as f:  # not *_test.go → ignored
                f.write("// spec:INV-RES-3\n")
            os.makedirs(os.path.join(root, ".git"))
            with open(os.path.join(root, ".git", "c_test.go"), "w") as f:  # skipped dir
                f.write("// spec:INV-GHOST-1\n")
            got = scan_dir(root, ["_test.go"], {".git"})
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].id, "INV-LEDGER-1")


if __name__ == "__main__":
    unittest.main()
