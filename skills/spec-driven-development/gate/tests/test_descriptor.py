import json
import os
import tempfile
import unittest
from specanchor.descriptor import load_descriptor, DescriptorError, merge, ResolvedConfig


class TestLoadDescriptor(unittest.TestCase):
    def test_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_descriptor(d))

    def test_valid(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"lang": "go", "skip": ["a"]}, f)
            self.assertEqual(load_descriptor(d), {"lang": "go", "skip": ["a"]})

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                f.write("{ not json")
            with self.assertRaises(DescriptorError):
                load_descriptor(d)

    def test_unknown_key(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"langz": "go"}, f)
            with self.assertRaises(DescriptorError):
                load_descriptor(d)

    def test_wrong_type(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"skip": "notalist"}, f)
            with self.assertRaises(DescriptorError):
                load_descriptor(d)

    def test_index_and_shape_strict_valid(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"lang": "go", "index": "spec-index.json", "shape_strict": "warn"}, f)
            self.assertEqual(load_descriptor(d),
                             {"lang": "go", "index": "spec-index.json", "shape_strict": "warn"})

    def test_shape_strict_bad_value(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"shape_strict": "loud"}, f)
            with self.assertRaises(DescriptorError):
                load_descriptor(d)

    def test_index_null_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"index": None}, f)
            self.assertEqual(load_descriptor(d), {"index": None})


class TestMerge(unittest.TestCase):
    def test_default_when_empty(self):
        cfg = merge({}, {})
        self.assertIsNone(cfg.lang)
        self.assertEqual(cfg.invariants, "docs/migration/INVARIANTS.md")
        self.assertFalse(cfg.invariants_from_descriptor)
        self.assertEqual(cfg.skip, [])
        self.assertFalse(cfg.anchor_strict)
        self.assertIsNone(cfg.resolver)

    def test_descriptor_supplies(self):
        cfg = merge({}, {"lang": "go", "invariants": "INV.md"})
        self.assertEqual(cfg.lang, "go")
        self.assertEqual(cfg.invariants, "INV.md")
        self.assertTrue(cfg.invariants_from_descriptor)

    def test_flag_overrides_descriptor(self):
        cfg = merge({"lang": "python"}, {"lang": "go"})
        self.assertEqual(cfg.lang, "python")

    def test_skip_from_descriptor(self):
        cfg = merge({}, {"skip": ["x", "y"]})
        self.assertEqual(cfg.skip, ["x", "y"])

    def test_flag_skip_overrides(self):
        cfg = merge({"skip": ["a"]}, {"skip": ["x"]})
        self.assertEqual(cfg.skip, ["a"])

    def test_anchor_strict_from_descriptor(self):
        cfg = merge({}, {"anchor_strict": True})
        self.assertTrue(cfg.anchor_strict)

    def test_index_shape_defaults(self):
        cfg = merge({}, {})
        self.assertIsNone(cfg.index)
        self.assertEqual(cfg.shape_strict, "block")

    def test_index_from_descriptor(self):
        cfg = merge({}, {"index": "out.json"})
        self.assertEqual(cfg.index, "out.json")
        self.assertTrue(cfg.index_from_descriptor)


if __name__ == "__main__":
    unittest.main()
