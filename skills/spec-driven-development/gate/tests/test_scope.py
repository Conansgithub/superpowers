import os
import tempfile
import unittest
from specanchor.scope import resolve_scope


class TestResolveScope(unittest.TestCase):
    def test_dash_is_unscoped_ok(self):
        with tempfile.TemporaryDirectory() as d:
            r = resolve_scope("—", d)
            self.assertEqual(r["globs"], [])
            self.assertTrue(r["exists"])

    def test_glob_hits_files(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "internal", "auth"))
            open(os.path.join(d, "internal", "auth", "x.go"), "w").close()
            r = resolve_scope("internal/auth/**", d)
            self.assertTrue(r["exists"])
            self.assertIn("internal/auth/x.go", r["files"])

    def test_glob_misses(self):
        with tempfile.TemporaryDirectory() as d:
            r = resolve_scope("internal/nope/**", d)
            self.assertFalse(r["exists"])
            self.assertEqual(r["files"], [])

    def test_multi_glob_comma(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "a"))
            open(os.path.join(d, "a", "x.go"), "w").close()
            r = resolve_scope("a/**, b/**", d)
            self.assertTrue(r["exists"])
            self.assertEqual(r["globs"], ["a/**", "b/**"])


if __name__ == "__main__":
    unittest.main()
