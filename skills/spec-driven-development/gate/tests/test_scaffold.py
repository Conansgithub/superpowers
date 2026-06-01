import io
import json
import os
import tempfile
import unittest
from specanchor.scaffold import detect_lang, probe_invariants, adopt


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


class TestAdopt(unittest.TestCase):
    def test_writes_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            os.makedirs(os.path.join(d, "spec"))
            self.assertEqual(adopt(d, out=io.StringIO()), 0)
            with open(os.path.join(d, ".spec-check.json")) as f:
                got = json.load(f)
            self.assertEqual(got["lang"], "go")
            self.assertEqual(got["manifests"], "spec/*/spec.md")

    def test_no_spec_dir_disables_manifests(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            self.assertEqual(adopt(d, out=io.StringIO()), 0)
            with open(os.path.join(d, ".spec-check.json")) as f:
                self.assertEqual(json.load(f)["manifests"], "")

    def test_ambiguous_lang_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            open(os.path.join(d, "setup.py"), "w").close()
            self.assertEqual(adopt(d, out=io.StringIO()), 2)

    def test_explicit_lang_skips_detection(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(adopt(d, lang="python", out=io.StringIO()), 0)
            with open(os.path.join(d, ".spec-check.json")) as f:
                self.assertEqual(json.load(f)["lang"], "python")

    def test_refuses_without_force(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                f.write("{}")
            self.assertEqual(adopt(d, out=io.StringIO()), 2)
            self.assertEqual(adopt(d, force=True, out=io.StringIO()), 0)


if __name__ == "__main__":
    unittest.main()
