import io
import json
import os
import tempfile
import unittest
from specanchor.scaffold import detect_lang, probe_invariants


class TestDetectLang(unittest.TestCase):
    def test_go(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            self.assertEqual(detect_lang(d), "go")

    def test_python(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "pyproject.toml"), "w").close()
            self.assertEqual(detect_lang(d), "python")

    def test_none_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                detect_lang(d)

    def test_ambiguous_raises(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            open(os.path.join(d, "setup.py"), "w").close()
            with self.assertRaises(ValueError):
                detect_lang(d)


class TestProbeInvariants(unittest.TestCase):
    def test_finds_root(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "INVARIANTS.md"), "w").close()
            self.assertEqual(probe_invariants(d), "INVARIANTS.md")

    def test_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(probe_invariants(d))


if __name__ == "__main__":
    unittest.main()
