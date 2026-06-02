import json
import os
import tempfile
import unittest
from specanchor.manifest import parse_manifest
from specanchor.binding import OSResolver
from specanchor.langs import LANGS
from specanchor.index import build_index, emit_index

MD = (
    "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n"
    "|--|--|--|--|--|--|--|\n"
    "| DEMO-1 | 当 X，服务 SHALL Y。 | 防 Z | event | 测试: demo_test.go::TestDemo | demo/** | enforced |\n"
)


class TestBuildIndex(unittest.TestCase):
    def _idx(self, d):
        os.makedirs(os.path.join(d, "demo"))
        open(os.path.join(d, "demo", "x.go"), "w").close()
        with open(os.path.join(d, "demo_test.go"), "w") as f:
            f.write("func TestDemo(t *testing.T){}\n")
        m = parse_manifest("spec/demo/spec.md", MD)
        return build_index([m], set(), OSResolver(d, LANGS["go"]), "go", d)

    def test_row_fields(self):
        with tempfile.TemporaryDirectory() as d:
            idx = self._idx(d)
            row = idx["rules"][0]
            self.assertEqual(row["id"], "DEMO-1")
            self.assertEqual(row["category"], "event")
            self.assertEqual(row["why"], "防 Z")
            self.assertTrue(row["binding"]["resolved"])
            self.assertTrue(row["scope"]["exists"])
            self.assertTrue(row["shape"]["has_shall"])

    def test_cross_cut(self):
        with tempfile.TemporaryDirectory() as d:
            idx = self._idx(d)
            self.assertIn("DEMO-1", idx["by_path"]["demo/x.go"])
            self.assertIn("DEMO-1", idx["by_category"]["event"])
            self.assertIn("DEMO-1", idx["by_status"]["enforced"])
            self.assertIn("DEMO-1", idx["by_test"]["demo_test.go::TestDemo"])
            self.assertEqual(idx["counts"]["demo"]["enforced"], 1)
            self.assertIn("digest", idx)

    def test_emit_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            idx = self._idx(d)
            out = os.path.join(d, "spec-index.json")
            emit_index(idx, out)
            with open(out) as f:
                self.assertEqual(json.load(f)["rules"][0]["id"], "DEMO-1")


if __name__ == "__main__":
    unittest.main()
