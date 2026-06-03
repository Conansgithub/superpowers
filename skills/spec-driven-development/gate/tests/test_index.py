import json
import os
import tempfile
import unittest
from specanchor.manifest import parse_manifest
from specanchor.binding import OSResolver
from specanchor.langs import LANGS
from specanchor.index import build_index, emit_index, _rel_at

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


class TestRelAt(unittest.TestCase):
    """Unit tests for _rel_at: at field must always be a clean repo-relative path."""

    def test_absolute_root_produces_relative_at(self):
        """_rel_at strips the absolute root prefix and emits 'spec/x.md:5'."""
        absroot = "/tmp/some/repo"
        path = os.path.join(absroot, "spec", "x.md")
        self.assertEqual(_rel_at(path, absroot, 5), "spec/x.md:5")

    def test_dot_root_strips_dot_slash(self):
        """_rel_at with root='.' strips the leading './' prefix."""
        result = _rel_at("./spec/x.md", ".", 5)
        self.assertEqual(result, "spec/x.md:5")

    def test_forward_slashes_on_all_platforms(self):
        """_rel_at always uses forward slashes regardless of os.sep."""
        absroot = os.path.join("/tmp", "repo")
        path = os.path.join(absroot, "spec", "sub", "spec.md")
        result = _rel_at(path, absroot, 19)
        self.assertNotIn("\\", result)
        self.assertEqual(result, "spec/sub/spec.md:19")

    def test_at_never_absolute_in_build_index(self):
        """Integration: build_index with an absolute root produces no absolute at values."""
        MD_ABS = (
            "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n"
            "|--|--|--|--|--|--|--|\n"
            "| ABS-1 | 当 X，服务 SHALL Y。 | 防 Z | event | 测试: demo_test.go::TestDemo | demo/** | enforced |\n"
        )
        with tempfile.TemporaryDirectory() as d:
            absroot = os.path.abspath(d)
            os.makedirs(os.path.join(absroot, "demo"))
            open(os.path.join(absroot, "demo", "x.go"), "w").close()
            with open(os.path.join(absroot, "demo_test.go"), "w") as f:
                f.write("func TestDemo(t *testing.T){}\n")
            # Use an absolute path for the manifest file, simulating -root /abs/path
            abs_spec_path = os.path.join(absroot, "spec", "demo", "spec.md")
            m = parse_manifest(abs_spec_path, MD_ABS)
            idx = build_index([m], set(), OSResolver(absroot, LANGS["go"]), "go", absroot)
            for row in idx["rules"]:
                at = row["at"]
                self.assertFalse(at.startswith("/"),
                                 f"at must not be absolute, got: {at!r}")
                self.assertFalse(at.startswith("./"),
                                 f"at must not start with ./, got: {at!r}")
                self.assertRegex(at, r"^[\w./-]+\.md:\d+$",
                                 f"at must match clean repo-relative pattern, got: {at!r}")


if __name__ == "__main__":
    unittest.main()
