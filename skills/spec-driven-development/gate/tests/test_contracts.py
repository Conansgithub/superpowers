import os
import tempfile
import unittest

from specanchor.contracts import load_contracts, eval_contract, ContractError


class TestContracts(unittest.TestCase):
    def _root(self, files):
        d = tempfile.mkdtemp()
        for name, content in files.items():
            p = os.path.join(d, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def test_contains_all_and_none(self):
        root = self._root({"a.yaml": "foo: 1\nbar: 2\n"})
        ok = [{"type": "contains", "files": ["a.yaml"], "all": ["foo: 1"], "none": ["nope"]}]
        self.assertTrue(eval_contract(ok, root))
        bad_all = [{"type": "contains", "files": ["a.yaml"], "all": ["missing"]}]
        self.assertFalse(eval_contract(bad_all, root))
        bad_none = [{"type": "contains", "files": ["a.yaml"], "none": ["bar: 2"]}]
        self.assertFalse(eval_contract(bad_none, root))

    def test_contains_missing_file_is_false(self):
        root = self._root({})
        self.assertFalse(eval_contract([{"type": "contains", "files": ["x.yaml"], "all": ["a"]}], root))

    def test_exists(self):
        root = self._root({"k/m.go": "package m\n"})
        self.assertTrue(eval_contract([{"type": "exists", "paths": ["k/m.go"]}], root))
        self.assertFalse(eval_contract([{"type": "exists", "paths": ["k/m.go", "absent"]}], root))

    def test_exec_exit_code(self):
        root = self._root({})
        self.assertTrue(eval_contract([{"type": "exec", "cmd": "true"}], root))
        self.assertFalse(eval_contract([{"type": "exec", "cmd": "false"}], root))

    def test_all_assertions_must_pass(self):
        root = self._root({"a.yaml": "foo\n"})
        mixed = [{"type": "contains", "files": ["a.yaml"], "all": ["foo"]},
                 {"type": "exists", "paths": ["absent"]}]
        self.assertFalse(eval_contract(mixed, root))

    def test_load_rejects_unknown_type(self):
        root = self._root({"c.json": '{"sel": [{"type": "bogus"}]}'})
        with self.assertRaises(ContractError):
            load_contracts(os.path.join(root, "c.json"))

    def test_load_rejects_non_list_entry(self):
        root = self._root({"c.json": '{"sel": {"type": "exists"}}'})
        with self.assertRaises(ContractError):
            load_contracts(os.path.join(root, "c.json"))

    def test_load_roundtrip(self):
        root = self._root({"c.json": '{"sel": [{"type": "exists", "paths": ["x"]}]}'})
        c = load_contracts(os.path.join(root, "c.json"))
        self.assertIn("sel", c)
