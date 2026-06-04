import json
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

    def test_shape_block_on_missing_shall(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-X-1 — x\nStatus: stated\nSince: 2026\n",
                   "func TestM(t *testing.T){}\n")
            _write_manifest(d, "m",
                "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"
                "| M-1 | 当 X，服务默认激活 | 防 Z | event | 测试: x_test.go::TestM | — | enforced |\n")
            self.assertEqual(_run(d, "-manifests", "spec/*/spec.md"), 1)  # block: 缺 SHALL

    def test_emit_index_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "### INV-X-1 — x\nStatus: stated\nSince: 2026\n",
                   "func TestM(t *testing.T){}\n")
            _write_manifest(d, "m",
                "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"
                "| M-1 | 当 X，服务 SHALL 激活 | 防 Z | event | 测试: x_test.go::TestM | — | enforced |\n")
            out = os.path.join(d, "idx.json")
            self.assertEqual(_run(d, "-manifests", "spec/*/spec.md", "--emit-index", out), 0)
            self.assertTrue(os.path.exists(out))


class TestRunManifestCoverage(unittest.TestCase):
    INV = "### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n"
    HEADER = "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"

    def test_dormant(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            self.assertEqual(_run(d), 0)

    def test_bound_to_test(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            with open(os.path.join(d, "demo_test.go"), "w") as f:
                f.write("package p\nfunc TestDemo(t *testing.T) {}\n")
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | 当 X，API SHALL Y。 | 待补 | event | 测试: demo_test.go::TestDemo | — | enforced |\n")
            self.assertEqual(_run(d), 0)

    def test_dangling_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | 当 X，API SHALL Y。 | 待补 | event | 测试: demo_test.go::TestGone | — | enforced |\n")
            self.assertEqual(_run(d), 1)

    def test_stated_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | 当 X，API SHALL Y。 | 待补 | event | 测试: demo_test.go::TestDemo | — | stated |\n")
            self.assertEqual(_run(d), 0)

    def test_malformed_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, self.INV)
            _write_manifest(d, "demo", self.HEADER + "| DEMO-1 | x | 待补 | event | enforced |\n")
            self.assertEqual(_run(d), 2)


class TestDescriptorDriven(unittest.TestCase):
    def test_descriptor_supplies_lang_and_invariants(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
                f.write("### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n")
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"lang": "go", "invariants": "INVARIANTS.md"}, f)
            self.assertEqual(spec_check.run(["-root", d]), 0)

    def test_flag_overrides_descriptor_lang(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
                f.write("### INV-LEDGER-1 — x\nStatus: enforced\nSince: 2026-06-01\n")
            with open(os.path.join(d, "x_test.go"), "w") as f:
                f.write("// spec:INV-LEDGER-1\n")
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                json.dump({"lang": "python", "invariants": "INVARIANTS.md"}, f)
            # descriptor 说 python → 扫 _test.py、漏掉 go tag → enforced 无 tag → 1
            self.assertEqual(spec_check.run(["-root", d]), 1)
            # flag 强制 go → 找到 tag → 0
            self.assertEqual(spec_check.run(["-root", d, "--lang", "go"]), 0)

    def test_malformed_descriptor_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
                f.write("### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n")
            with open(os.path.join(d, ".spec-check.json"), "w") as f:
                f.write("{ bad")
            self.assertEqual(spec_check.run(["-root", d]), 2)


class TestDispatch(unittest.TestCase):
    def test_adopt_writes_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "go.mod"), "w").close()
            self.assertEqual(spec_check.run(["adopt", "-root", d]), 0)
            with open(os.path.join(d, ".spec-check.json")) as f:
                self.assertEqual(json.load(f)["lang"], "go")

    def test_init_scaffolds(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(spec_check.run(["init", "-root", d, "--lang", "go"]), 0)
            self.assertTrue(os.path.exists(os.path.join(d, "INVARIANTS.md")))
            self.assertTrue(os.path.exists(os.path.join(d, ".spec-check.json")))

    def test_init_requires_lang(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(spec_check.run(["init", "-root", d]), 2)

    def test_explicit_check_word(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
                f.write("### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n")
            self.assertEqual(spec_check.run(
                ["check", "--lang", "go", "-invariants", os.path.join(d, "INVARIANTS.md"), "-root", d]), 0)


class TestResolverFlag(unittest.TestCase):
    HEADER = "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"

    def _tree(self, d):
        with open(os.path.join(d, "INVARIANTS.md"), "w") as f:
            f.write("### INV-RES-1 — x\nStatus: stated\nSince: 2026-06-01\n")
        md = os.path.join(d, "spec", "demo")
        os.makedirs(md)
        with open(os.path.join(md, "spec.md"), "w") as f:
            f.write(self.HEADER + "| DEMO-1 | 当 X，API SHALL Y。 | 待补 | event | 测试: ghost_test.go::TestX | — | enforced |\n")

    def test_resolver_binds_what_os_cannot(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d)
            script = os.path.join(d, "r.sh")
            with open(script, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")  # everything resolves
            inv = os.path.join(d, "INVARIANTS.md")
            # ghost_test.go::TestX 不存在：OSResolver → unbound → 1
            self.assertEqual(spec_check.run(["--lang", "go", "-invariants", inv, "-root", d]), 1)
            # shell resolver 一律连上 → bound → 0
            self.assertEqual(spec_check.run(
                ["--lang", "go", "-invariants", inv, "-root", d, "--resolver", f"sh {script}"]), 0)


class TestDeclarativeResolver(unittest.TestCase):
    """Tests that DeclarativeResolver is engaged when contracts are configured,
    distinguished from OSResolver by a NEGATIVE case: x.yaml exists (OSResolver
    would return True) but its content does NOT satisfy the contract (DeclarativeResolver
    returns False → UNBOUND → gate FAIL, rc=1).
    """
    HEADER = "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"

    def _build_tree(self, d, yaml_content):
        """Build a temp project using descriptor-driven config (no explicit flags)."""
        # .spec-check.json descriptor
        with open(os.path.join(d, ".spec-check.json"), "w") as f:
            json.dump({
                "lang": "go",
                "invariants": "INV.md",
                "manifests": "spec/*.md",
                "contracts": "contracts.json",
            }, f)
        # INV.md
        with open(os.path.join(d, "INV.md"), "w") as f:
            f.write("# INV\n")
        # spec/m.md — one enforced CONTRACT pointer
        os.makedirs(os.path.join(d, "spec"), exist_ok=True)
        with open(os.path.join(d, "spec", "m.md"), "w") as f:
            f.write(
                self.HEADER +
                "| M-1 | cfg SHALL 含 key | w | contract | 生成: x.yaml | — | enforced |\n"
            )
        # x.yaml — content controlled by caller
        with open(os.path.join(d, "x.yaml"), "w") as f:
            f.write(yaml_content)
        # contracts.json — requires "key: val" in x.yaml
        with open(os.path.join(d, "contracts.json"), "w") as f:
            json.dump({"x.yaml": [{"type": "contains", "files": ["x.yaml"], "all": ["key: val"]}]}, f)

    def test_contract_not_satisfied_blocks(self):
        """x.yaml exists but lacks 'key: val' → DeclarativeResolver False → UNBOUND → rc=1.
        If OSResolver were used instead, it would see the file exists and return True → rc=0.
        This test distinguishes the two resolvers.
        """
        with tempfile.TemporaryDirectory() as d:
            self._build_tree(d, "other: 1\n")
            self.assertEqual(spec_check.run(["-root", d]), 1)

    def test_contract_satisfied_passes(self):
        """x.yaml contains 'key: val' → DeclarativeResolver True → bound → rc=0."""
        with tempfile.TemporaryDirectory() as d:
            self._build_tree(d, "key: val\n")
            self.assertEqual(spec_check.run(["-root", d]), 0)


if __name__ == "__main__":
    unittest.main()
