import json
import os
import tempfile
import unittest
from specanchor.descriptor import load_descriptor, DescriptorError


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


if __name__ == "__main__":
    unittest.main()
